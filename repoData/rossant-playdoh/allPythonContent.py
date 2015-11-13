__FILENAME__ = connectionerror
from playdoh import *
from numpy import *
from numpy.random import rand
from pylab import *
import time

class ConnectionError(ParallelTask):
    def initialize(self, iterations):
        self.iterations = iterations
        self.iteration = 0

    def send_boundaries(self):
        if 'left' in self.tubes_out:
            self.push('left', None)
        if 'right' in self.tubes_out:
            self.push('right', None)
    
    def recv_boundaries(self):
        if 'right' in self.tubes_in:
            self.pop('right')
        if 'left' in self.tubes_in:
            self.pop('left')

    def start(self):
        for self.iteration in xrange(self.iterations):
            log_info("Iteration %d/%d" % (self.iteration+1, self.iterations))
            self.send_boundaries()
            self.recv_boundaries()
    
    def get_result(self):
        return None

if __name__ == '__main__':
    n = 6

    for i in xrange(n):
        p = Process(target=open_server, args=(2718+i,1,0))
        p.start()
    
#    machines = []
    machines = [('localhost',2718+i) for i in xrange(n)]
#    machines.append(('192.168.1.59', 2718))
    
    allocation = allocate(machines=machines)
    nodes = len(allocation)
    
    topology = []
    for i in xrange(nodes-1):
        topology.append(('right', i, i+1))
        topology.append(('left', i+1, i))
    
    task = start_task(ConnectionError,
                      topology=topology,
                      allocation=allocation,
                      args=(20,))

    result = task.get_result()
    
    
    close_servers(machines)
    
########NEW FILE########
__FILENAME__ = linuxbug
from playdoh import *
from test import *
from multiprocessing import Process
from numpy.random import rand
from numpy import max, mean
import time, sys

iterations = 500

class TaskTest(ParallelTask):
    def initialize(self, cpu):
        self.cpu = cpu
    
    def start(self):
        for i in xrange(iterations):
            print i
            sys.stdout.flush()
            if self.node.index==0:
                [self.tubes.push('tube%d' % j, rand(100,100)) for j in xrange(1, self.cpu)]
                [self.tubes.pop('tube%dbis' % j) for j in xrange(1, self.cpu)]
            for index in xrange(1,self.cpu):
                if self.node.index==index:
                    self.tubes.pop('tube%d' % index)
                    self.tubes.push('tube%dbis' % index, rand(100,100))
    
    def get_result(self):
        return None
    


if __name__ == '__main__':

    cpu = MAXCPU-1
    topology = []
    for i in xrange(1,cpu):
        topology.extend([('tube%d' % i, 0, i),
                         ('tube%dbis' % i, i, 0)])
        
    for i in xrange(1):
        print i
        task = start_task(TaskTest, topology = topology, 
                          cpu = cpu,
                          args=(cpu,))
        #time.sleep(2)
        result = task.get_result()






########NEW FILE########
__FILENAME__ = shared
import multiprocessing, sys, os, time, ctypes, numpy, cPickle
from multiprocessing import Process, sharedctypes, Pipe
from numpy import ctypeslib, mean

def make_common_item(v):
    shape = v.shape
    mapping = {
        numpy.dtype(numpy.float64):ctypes.c_double,
        numpy.dtype(numpy.int32):ctypes.c_int,
        }
    ctype = mapping.get(v.dtype, None)
    if ctype is not None:
        v = v.flatten()
        v = sharedctypes.Array(ctype, v, lock=False)
    return v, shape

def make_numpy_item((v, shape)):
    try:
        v = ctypeslib.as_array(v)
        v.shape = shape
    except:
        pass
    return v

def fun(conn, x):
    y = make_numpy_item(x)
    print y.shape, mean(mean(y))
    sys.stdout.flush()
    time.sleep(5)

if __name__ == '__main__':
    cols = 2 # BUG: cols=2
    x = numpy.random.rand(2000000,cols)
    print x.shape, mean(mean(x))
    
    x2 = x
    x2 = make_common_item(x) # comment this to check that the 2 subprocesses use much less memory
    
    parent_conn1, child_conn1 = Pipe()
    p1 = Process(target=fun, args=(child_conn1,x2))
    p1.start()
    
    parent_conn2, child_conn2 = Pipe()
    p2 = Process(target=fun, args=(child_conn2,x2))
    p2.start()
    
    p1.join()
    p1.terminate()
    
    p2.join()
    p2.terminate()
    
    print "Done"

########NEW FILE########
__FILENAME__ = build_html
import os
os.chdir('../../docs_sphinx')
os.system('sphinx-build -b html . ../docs')  # a to force

########NEW FILE########
__FILENAME__ = generate_examples
import os, re, glob, inspect, compiler, unicodedata, fnmatch
os.chdir('../../examples')

class GlobDirectoryWalker:
    # a forward iterator that traverses a directory tree

    def __init__(self, directory, pattern="*"):
        self.stack = [directory]
        self.pattern = pattern
        self.files = []
        self.index = 0

    def __getitem__(self, index):
        while 1:
            try:
                file = self.files[self.index]
                self.index = self.index + 1
            except IndexError:
                # pop next directory from stack
                self.directory = self.stack.pop()
                self.files = os.listdir(self.directory)
                self.index = 0
            else:
                # got a filename
                fullname = os.path.join(self.directory, file)
                if os.path.isdir(fullname) and not os.path.islink(fullname):
                    self.stack.append(fullname)
                if fnmatch.fnmatch(file, self.pattern):
                    return fullname

examplesfnames = [fname for fname in GlobDirectoryWalker('.', '*.py') if 'external' not in fname]
examplespaths = []
examplesbasenames = []
for f in examplesfnames:
    path, file = os.path.split(f)
    path = os.path.normpath(path)
    if path == '.': path = ''
    else: path = path + '_'
    filebase, ext = os.path.splitext(file)
    examplespaths.append(path)
    examplesbasenames.append(filebase)
examplescode = [open(fname, 'r').read() for fname in examplesfnames]
examplesdocs = []
examplesafterdoccode = []
examplesdocumentablenames = []
for code in examplescode:
    codesplit = code.split('\n')
    readingdoc = False
    doc = []
    afterdoccode = ''
    for i in range(len(codesplit)):
        stripped = codesplit[i].strip()
        if stripped[:3] == '"""' or stripped[:3] == "'''":
            if not readingdoc:
                readingdoc = True
            else:
                afterdoccode = '\n'.join(codesplit[i + 1:])
                break
        elif readingdoc:
            doc.append(codesplit[i])
        elif not stripped or stripped[0] == '#':
            pass
        else:
            break
    doc = '\n'.join(doc)
    # next line replaces unicode characters like e-acute with standard ascii representation
    examplesdocs.append(unicodedata.normalize('NFKD', unicode(doc, 'latin-1')).encode('ascii', 'ignore'))
    examplesafterdoccode.append(afterdoccode)
    examplesdocumentablenames.append([])
#    try:
#        examplesdocumentablenames.append(set(compiler.compile(code, '', 'exec').co_names) & documentable_names)
#    except SyntaxError:
#        print code
#        raise
examples = zip(examplesfnames, examplespaths, examplesbasenames, examplescode, examplesdocs, examplesafterdoccode, examplesdocumentablenames)
os.chdir('../docs_sphinx')
for fname, path, basename, code, docs, afterdoccode, documentables in examples:
    title = 'Example: ' + basename
    if len(path): title += ' (' + path[:-1] + ')'
    output = '.. currentmodule:: playdoh\n\n'
    output += '.. _example-' + path + basename + ':\n\n'
    if len(documentables):
        output += '.. index::\n'
        for dname in documentables:
            output += '   pair: example usage; ' + dname + '\n'
        output += '\n'
    output += title + '\n' + '=' * len(title) + '\n\n'
    output += docs + '\n\n::\n\n'
    output += '\n'.join(['    ' + line for line in afterdoccode.split('\n')])
    output += '\n\n'
    open('examples-' + path + basename + '.txt', 'w').write(output)


########NEW FILE########
__FILENAME__ = benchmark_single
"""
Brian example
"""
import playdoh

def fun(taum):
    from brian import *
    taum *= ms
    taue = 5 * ms
    taui = 10 * ms
    Vt = -50 * mV
    Vr = -60 * mV
    El = -49 * mV
    
    eqs = Equations('''
    dv/dt  = (ge+gi-(v-El))/taum : volt
    dge/dt = -ge/taue : volt
    dgi/dt = -gi/taui : volt
    ''')
    
    P = NeuronGroup(4000, model=eqs, threshold=Vt, reset=Vr, refractory=5 * ms)
    P.v = Vr
    P.ge = 0 * mV
    P.gi = 0 * mV
    
    Pe = P.subgroup(3200)
    Pi = P.subgroup(800)
    we = (60 * 0.27 / 10) * mV # excitatory synaptic weight (voltage)
    wi = (-20 * 4.5 / 10) * mV # inhibitory synaptic weight
    Ce = Connection(Pe, P, 'ge', weight=we, sparseness=0.02)
    Ci = Connection(Pi, P, 'gi', weight=wi, sparseness=0.02)
    P.v = Vr + rand(len(P)) * (Vt - Vr)
    
    # Record the number of spikes
    Me = PopulationSpikeCounter(Pe)
    Mi = PopulationSpikeCounter(Pi)
    
    net = Network(P, Ce, Ci, Me, Mi)
    
    net.run(1 * second)
    
    return Me.nspikes, Mi.nspikes

if __name__ == '__main__':
    taums = [5]*3
    
    import time
    t1 = time.clock()
    result = playdoh.map(fun, [i for i in taums], cpu=3)
    d = time.clock()-t1
    
    print result
    print "simulation last %.2f seconds with playdoh and %d CPUs" % (d, len(taums))
    
    
    t1 = time.clock()
    result2 = []
    for i in xrange(len(taums)):
        t0 = time.clock()
        r = fun(taums[i])
        d0 = time.clock()-t0
        print "simulation %d last %.2f seconds" % (i, d0)
        result2.append(r)
    d2 = time.clock()-t1
    
    speedup = d2/d
    
    print result2
    print "simulation last %.2f seconds in serial and 1 CPU" % (d2)
    
    print
    print "speed-up: %.2f x" % speedup
########NEW FILE########
__FILENAME__ = example_brian
"""
Brian example
"""
import playdoh
from numpy import *
from brian import *

def fun(taum):
    taum *= ms
    
    taue = 5 * ms
    taui = 10 * ms
    Vt = -50 * mV
    Vr = -60 * mV
    El = -49 * mV
    
    eqs = Equations('''
    dv/dt  = (ge+gi-(v-El))/taum : volt
    dge/dt = -ge/taue : volt
    dgi/dt = -gi/taui : volt
    ''')
    
    P = NeuronGroup(4000, model=eqs, threshold=Vt, reset=Vr, refractory=5 * ms)
    P.v = Vr
    P.ge = 0 * mV
    P.gi = 0 * mV
    
    Pe = P.subgroup(3200)
    Pi = P.subgroup(800)
    we = (60 * 0.27 / 10) * mV # excitatory synaptic weight (voltage)
    wi = (-20 * 4.5 / 10) * mV # inhibitory synaptic weight
    Ce = Connection(Pe, P, 'ge', weight=we, sparseness=0.02)
    Ci = Connection(Pi, P, 'gi', weight=wi, sparseness=0.02)
    P.v = Vr + rand(len(P)) * (Vt - Vr)
    
    # Record the number of spikes
    Me = PopulationSpikeCounter(Pe)
    Mi = PopulationSpikeCounter(Pi)
    # A population rate monitor
    M = PopulationRateMonitor(P)
    
    run(1 * second)
    
    return Me.nspikes, Mi.nspikes

if __name__ == '__main__':
    taums = linspace(5, 25, 2)
    
    import time
    t1 = time.clock()
    result = playdoh.map(fun, [i for i in taums], cpu=2)
    d = time.clock()-t1
    
    print result
    print "simulation last %.2f seconds" % d
########NEW FILE########
__FILENAME__ = example_map
from playdoh import *

def fun(x):
    return x**2

if __name__ == '__main__':
    print map(fun, [1,2], cpu=2)


########NEW FILE########
__FILENAME__ = example_map_async
from playdoh import *

def fun(x):
    return x**2

if __name__ == '__main__':
    task = map_async(fun, [1,2], cpu=2)
    print task.get_result()


########NEW FILE########
__FILENAME__ = example_maximize
from playdoh import *

def fun(x):
    import numpy
    if x.ndim == 1:
        x = x.reshape((1,-1))
    result = numpy.exp(-(x**2).sum(axis=0))
    return result

if __name__ == '__main__':
    from numpy import *
    dimension = 4
    initrange = tile([-10,10], (dimension,1))
    results = maximize(fun,
                       popsize = 10000,
                       maxiter = 10,
                       cpu = 1,
                       codedependencies = [],
                       returninfo = True,
                       initrange = initrange)
    print_table(results)
########NEW FILE########
__FILENAME__ = example_maximize_class
from playdoh import *
from numpy import exp, tile

class FitnessTest(Fitness):
    def initialize(self):
        self.a = self.shared_data['a']
    
    def evaluate(self, x):
        if self.dimension == 1:
            x = x.reshape((1,-1))
        result = self.a*exp(-(x**2).sum(axis=0))
        return result

if __name__ == '__main__':
    dimension = 2
    initrange = tile([-10,10], (dimension,1))
    results = maximize(FitnessTest,
                       popsize = 1000,
                       maxiter = 10,
                       cpu = 2,
                       shared_data = {'a': 3},
                       codedependencies = [],
                       initrange = initrange)
    print_table(results)
    
########NEW FILE########
__FILENAME__ = example_maximize_dependencies
from playdoh import *
from numpy import *
from expfun import fun

if __name__ == '__main__':
    dimension = 4
    initrange = tile([-10,10], (dimension,1))
    results = maximize(fun,
                       popsize = 10000,
                       maxiter = 10,
                       cpu = 1,
                       machines = ['localhost'],
                       codedependencies = ['expfun.py', 'expfun2.py'],
                       initrange = initrange)
    print_table(results)
########NEW FILE########
__FILENAME__ = example_maximize_groups
from playdoh import *

def fun(x,y,shared_data,groups):
    import numpy
    n = len(x)
    result = numpy.zeros(n)
    x0 = numpy.kron(shared_data['x0'], numpy.ones(n/groups))
    y0 = numpy.kron(shared_data['y0'], numpy.ones(n/groups))
    result = numpy.exp(-(x-x0)**2-(y-y0)**2)
    return result

if __name__ == '__main__':    
    results = maximize(fun,
                       popsize = 10000,
                       maxiter = 10,
                       groups = 3,
                       cpu = 2,
                       shared_data={'x0': [0,1,2], 'y0':[3,4,5]},
                       x_initrange = [-10,10],
                       y_initrange = [-10,10])
    print_table(results)
    
########NEW FILE########
__FILENAME__ = example_monte_carlo
from playdoh import *
import numpy as np

class PiMonteCarlo(ParallelTask): # This class derives from the ParallelTask
    def initialize(self, n):
        # Specifies the samples number on this node
        self.n = n
    
    def start(self):
        # Draw n points uniformly in [0,1]^2
        samples = np.random.rand(2,self.n)
        # Counts the number of points inside the quarter unit circle
        self.count = np.sum(samples[0,:]**2+samples[1,:]**2<1)
    
    def get_result(self):
        # Returns the result
        return self.count
    
def pi_montecarlo(samples, nodes):
    # Calculates the number of samples for each node
    split_samples = [samples/nodes]*nodes
    # Launches the task on the local CPUs
    task = start_task(PiMonteCarlo, # name of the task class
                      cpu = nodes, # use <nodes> CPUs on the local machine
                      args=(split_samples,)) # arguments of MonteCarlo.initialize as a list, 
                                             # node #i receives split_samples[i] as argument
    # Retrieves the result, as a list with one element returned by MonteCarlo.get_result per node
    result = task.get_result()
    # Returns the estimation of Pi
    return sum(result)*4.0/samples

if __name__ == '__main__':
    # Evaluates Pi with 10,000 samples and 2 CPUs
    print pi_montecarlo(1000000, 2)

########NEW FILE########
__FILENAME__ = example_optim1

from playdoh import *
from multiprocessing import Process
from threading import Thread
import sys, time, unittest, numpy
from numpy import inf, ones, zeros, exp,sin
from numpy.random import rand
from pylab import *
from time import sleep


test_fun=4
if test_fun==1:
#sphere  
    def fun(x1,x2,x3,x4,x5):
        return x1**2+x2**2+x3**2+x4**2+x5**2
    min_dom=-5.12
    max_dom=5.12

if test_fun==2:
##schwefel  solution  (-420.9687....)
    def fun(x1,x2,x3,x4,x5):
        from numpy import sqrt,sin,abs
        return 418.9829*5+x1*sin(sqrt(abs(x1)))+x2*sin(sqrt(abs(x2)))+x3*sin(sqrt(abs(x3)))+x4*sin(sqrt(abs(x4)))+x5*sin(sqrt(abs(x5)))
    min_dom=-512.03
    max_dom=511.97
if test_fun==3:
#Rastrigin solution (0,0,0...)
    def fun(x1,x2,x3,x4,x5):
        from numpy import cos,pi
        return 10.*+x1**2-10*cos(2*pi*x1)+x2**2-10*cos(2*pi*x2)+x3**2-10*cos(2*pi*x3)+x4**2-10*cos(2*pi*x4)+x5**2-10*cos(2*pi*x5)
    min_dom=-5.12
    max_dom=5.12
if test_fun==4:
#Rosenbrock solution (1,1,1...)
    def fun(x1,x2,x3,x4,x5):
        sleep(.1)
        return 100*(-x2+x1**2)**2+(x1-1)**2+100*(-x3+x2**2)**2+(x2-1)**2+100*(-x4+x3**2)**2+(x3-1)**2+100*(-x5+x4**2)**2+(x4-1)**2
    min_dom=-2.048
    max_dom=2.048
    
if test_fun==5:
#Ackley solution (0.0.0.0...)
    def fun(x1,x2,x3,x4,x5):
        from numpy import exp,sqrt
        return 20+exp(1)-20*exp(-0.2*sqrt(0.2*(x1**2+x2**2+x3**2+x4**2+x5**2)))
    min_dom=-2.048
    max_dom=2.048
    
if test_fun==6:   
    def fun(x1,x2,x3,x4,x5):
        from numpy import exp
    #    print x1
        return 1-exp(-(x1*x1+x2*x2+x3*x3+x4*x4+x5*x5))
    min_dom=-2.
    max_dom=2.


if __name__ == '__main__':
    
    nbr_iterations=50
    
    nbr_particles=1000
    nbr_cpu=2
    
    scale_dom=2./3
    optCMA=dict()
    optCMA['proportion_selective']=0.5
    optCMA['returninfo']=True
    result_CMA = minimize(fun,
                      algorithm = CMAES,
                      maxiter = nbr_iterations,
                      popsize = nbr_particles,  
                      groups=2,
                     scaling='mapminmax',
                      cpu = nbr_cpu,
                    ##  x1 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom], x2 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x3 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom],x4 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x5 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom])
                      x1 = [min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom], x2 =[min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],x3 = [min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],x4 =[min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],x5 =[min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],
                      returninfo=True,
                      #optparams=optCMA
                      )
        
    print result_CMA[0].best_pos,result_CMA[1].best_pos
    plot( result_CMA[0].info['best_fitness'])
    plot( result_CMA[1].info['best_fitness'])
    show()

########NEW FILE########
__FILENAME__ = example_optim2

from playdoh import *
from multiprocessing import Process
from threading import Thread
import sys, time, unittest, numpy
from numpy import inf, ones, zeros, exp,sin
from numpy.random import rand
from pylab import *

test_fun=2
if test_fun==1:
#sphere  
    def fun(x):
        return sum(x**2, axis=0)
    min_dom=-5.12
    max_dom=5.12

if test_fun==2:
##schwefel  solution  (-420.9687....)
    def fun(x):
        from numpy import sqrt,sin,abs
        return 418.9829*x.shape[0]+sum(x*sin(sqrt(abs(x))), axis=0)
    min_dom=-512.03
    max_dom=511.97
if test_fun==3:
#Rastrigin solution (0,0,0...)
    def fun(x):
        from numpy import cos,pi
        return 10+sum(x**2-10*cos(2*pi*x), axis=0)
    min_dom=-5.12
    max_dom=5.12





if __name__ == '__main__':
    
    nbr_iterations=200   
    nbr_particles=200
    nbr_cpu=2  
    scale_dom=2./3
    nbr_dim=5
    initrange=hstack((scale_dom*min_dom*ones((nbr_dim,1)),scale_dom*max_dom*ones((nbr_dim,1))))
    bounds=hstack((min_dom*ones((nbr_dim,1)),max_dom*ones((nbr_dim,1))))
    print initrange
    optCMA=dict()
    optCMA['proportion_selective']=0.5
    result_CMA = minimize(fun,
                      algorithm = CMAES,
                      maxiter = nbr_iterations,
                      popsize = nbr_particles,  
                      #scaling='mapminmax',
                      groups=2,
                      cpu = nbr_cpu,
                      initrange=initrange,
                      bounds=bounds,
                      returninfo=True,
                      #optparams=optCMA
                      )

    print result_CMA[0].best_pos
    




########NEW FILE########
__FILENAME__ = example_pde
from playdoh import *
import numpy as np
import pylab as pl
from scipy.sparse import lil_matrix

class HeatSolver(ParallelTask):
    """
    2D heat equation solver
    """
    def initialize(self, X, dx, dt, iterations):
        self.X = X # matrix with the function values and the boundary values
        # X must contain the borders of the neighbors ("overlapping Xs")
        self.n = X.shape[0]
        self.dx = dx
        self.dt = dt
        self.iterations = iterations
        self.iteration = 0

    def send_boundaries(self):
        if 'left' in self.tubes_out:
            self.push('left', self.X[:,1])
        if 'right' in self.tubes_out:
            self.push('right', self.X[:,-2])
    
    def recv_boundaries(self):
        if 'right' in self.tubes_in:
            self.X[:,0] = self.pop('right')
        if 'left' in self.tubes_in:
            self.X[:,-1] = self.pop('left')
    
    def update_matrix(self):
        """
        Implements the numerical scheme for the PDE
        """
        Xleft, Xright = self.X[1:-1,:-2], self.X[1:-1,2:]
        Xtop, Xbottom = self.X[:-2,1:-1], self.X[2:,1:-1]
        self.X[1:-1,1:-1] += self.dt*(Xleft+Xright+Xtop+Xbottom-4*self.X[1:-1,1:-1])/self.dx**2

    def start(self):
        for self.iteration in xrange(self.iterations):
            self.send_boundaries()
            self.recv_boundaries()
            self.update_matrix()
    
    def get_result(self):
        return self.X[1:-1,1:-1]
    
    def get_info(self):
        return self.iteration

def heat2d(n, nodes):
    # split is the grid size on each node, without the boundaries
    split = [(n-2)*1.0/nodes for _ in xrange(nodes)]
    split = np.array(split, dtype=int)
    split[-1] = n-2-np.sum(split[:-1])
    
    dx=2./n
    dt = dx**2*.2
    iterations = 500
    
    # dirac function at t=0
    y = np.zeros((n,n))
    y[n/2,n/2] = 1./dx**2
    
    # split y horizontally
    split_y = []
    j = 0
    for i in xrange(nodes):
        size = split[i]
        split_y.append(y[:,j:j+size+2])
        j += size
    
    # double linear topology 
    topology = []
    for i in xrange(nodes-1):
        topology.append(('right', i, i+1))
        topology.append(('left', i+1, i))
    
    # starts the task
    task = start_task(HeatSolver, # name of the task class
                      cpu = nodes, # use <nodes> CPUs on the local machine
                      topology = topology,
                      args=(split_y, dx, dt, iterations))
                                              
    # Retrieves the result, as a list with one element returned by MonteCarlo.get_result per node
    result = task.get_result()
    result = np.hstack(result)
    
    return result

if __name__ == '__main__':
    result = heat2d(100,2)
    pl.hot()
    pl.imshow(result)

#    x = np.linspace(-1.,1.,98)
#    X,Y= np.meshgrid(x,x)
#    import matplotlib.pyplot as plt
#    from matplotlib import cm
#    from mpl_toolkits.mplot3d import Axes3D
#    fig = pl.figure()
#    ax = fig.add_subplot(111, projection='3d')
#    ax.plot_wireframe(X,Y,result)

    pl.show()
########NEW FILE########
__FILENAME__ = expfun
from expfun2 import fun2

def fun(x):
    if x.ndim == 1:
        x = x.reshape((1,-1))
    result = fun2(x)
    return result
########NEW FILE########
__FILENAME__ = expfun2
from numpy import exp

def fun2(x):
    return exp(-(x**2).sum(axis=0))
########NEW FILE########
__FILENAME__ = gui
from Tkinter import *
from threading import Thread
import playdoh, os

def get_available_resources(server):
    try:
        obj = playdoh.get_available_resources(server)[0]
        msg = None
    except:
        obj = None
        msg = "Unable to connect to %s:%s" % server
    return obj, msg

def get_my_resources(server):
    try:
        obj = playdoh.get_my_resources(server)[0]
        msg = None
    except:
        obj = None
        msg = "Unable to connect to %s:%s" % server
    return obj, msg

def set_my_resources(server, cpu, gpu):
#    try:
    obj = playdoh.request_resources(server, CPU=cpu, GPU=gpu)
    msg = None
#    except:
#        obj = None
#        msg = "Unable to connect to %s:%s" % server
    return obj, msg




class PlaydohGUI:
    def __init__(self, master):
        self.master = master
        frame = Frame(master)
        self.frame = frame
        self.sliders = {}
        #self.total_resources = None
        self.server = None
        
        try:
            self.servers = playdoh.USERPREF['favoriteservers']
        except:
            self.servers = ['']
        
        self.textbox_server = Text(width=35, height=1)
        self.textbox_server.grid(row=0,columnspan=2)
        self.textbox_server.insert(END, '')
        
        self.yScroll = Scrollbar(master, orient=VERTICAL)
        self.yScroll.grid(row=1, column=1)
        self.listbox_servers = Listbox(width=30, height=1, yscrollcommand=self.yScroll.set,
                                       activestyle=None)
        self.yScroll["command"] = self.listbox_servers.yview
        self.listbox_servers.grid(row=1,column=0)
#        self.listbox_servers.insert(END, '')
        for server in self.servers:
            self.listbox_servers.insert(END, server)
#        self.poll() # start polling the list
        
        self.button_info = Button(master, text="Retrieve info from the server", 
                                    width=32, height=1, font="Arial 11 bold",
                                    command=self.get_info)
        self.button_info.grid(row=2,columnspan=2)
        
        self.textbox_info = Text(width=35, height=10)
        self.textbox_info.grid(row=3,columnspan=2)
        self.textbox_info.insert(END, "Idle resources:\nCPU:  \nGPU:  \n\nAllocated resources\nCPU:  \nGPU:  \n")

        Label(text="Number of CPUs").grid(row=4, column=0)
        self.set_slider('CPU', 0, row=4, column=1, callback=self.callback_cpu)

        Label(text="Number of GPUs").grid(row=5, column=0)
        self.set_slider('GPU', 0, row=5, column=1, callback=self.callback_gpu)
        
        self.button_launch = Button(master, text="Set units", width=35, height=2,
                                    foreground="blue", font="Arial 11 bold",
                                    command=self.set_units)
        self.button_launch.grid(row=6,columnspan=2)
        
        self.button_exit = Button(master, text="Exit", width=35, height=1,
                                    font="Arial 11 bold", command=self.exit)
        self.button_exit.grid(row=7,columnspan=2)

#    def poll(self):
#        now = self.listbox_servers.curselection()
#        if now != self.current:
#            self.list_has_changed(now)
#            self.current = now
#        self.after(250, self.poll)
        
    def disable_buttons(self):
        self.button_info.config(state = DISABLED)
        self.button_launch.config(state = DISABLED)
        self.button_exit.config(state = DISABLED)
   
    def enable_buttons(self):
        self.button_info['state'] = NORMAL
        self.button_launch['state'] = NORMAL
        self.button_exit['state'] = NORMAL
   
    def set_slider(self, name, units, row, column, callback):
        self.sliders[name] = Scale(self.master, from_=0, to=units,
                            command = callback,
                            orient=HORIZONTAL)
        self.sliders[name].grid(row=row,column=column)
   
    def update_sliders(self, cpu, gpu):
        self.set_slider('CPU', cpu, row=4, column=1, callback=self.callback_cpu)
        self.set_slider('GPU', gpu, row=5, column=1, callback=self.callback_gpu)
   
    def callback_cpu(self, value):
        self.cpu = int(value)

    def callback_gpu(self, value):
        self.gpu = int(value)
    
    def get_server(self):
        server = str(self.textbox_server.get(1.0, END).strip(" \n\r"))
        if server == '':
            index = self.listbox_servers.nearest(0)
            server = self.servers[index]
            if server == '':
                log_warn("No server selected")
                return
        fullserver = server
        self.server_address = server
        l = server.split(':')
        if len(l) == 1:
            server, port = l[0], str(DEFAULT_PORT)
        elif len(l) == 2:
            server, port = l[0], l[1]
        else:
            raise Exception("server IP must be 'IP:port'")
        server = server.strip()
        port = int(port.strip())
        self.server = (server, port)
        return fullserver
    
    def _get_info(self):
        self.disable_buttons()
        self.get_server()
        
        try:
            playdoh.GC.set([self.server])
            disconnect = playdoh.GC.connect()
            resources, msg = get_available_resources(self.server)
            if msg is not None: playdoh.log_warn(msg)
        
            self.textbox_info.delete("2.5", "2.6")
            self.textbox_info.insert("2.5", resources['CPU'])
            self.textbox_info.delete("3.5", "3.6")
            self.textbox_info.insert("3.5", resources['GPU'])
            self.update_sliders(resources['CPU'], resources['GPU'])
            
            resources, msg = get_my_resources(self.server)
            if msg is not None: playdoh.log_warn(msg)
            self.textbox_info.delete("6.5", "6.6")
            self.textbox_info.insert("6.5", resources['CPU'])
            self.textbox_info.delete("7.5", "7.6")
            self.textbox_info.insert("7.5", resources['GPU'])
            for r in sorted(resources.keys()):
                if resources[r] is not None:
                    self.cpu = int(resources[r])
                    self.sliders[r].set(self.cpu)
            if disconnect: playdoh.GC.disconnect()
        
        except:
            playdoh.log_warn("Unable to connect to the server")
            
        self.enable_buttons()
            
    def get_info(self):
        server = self.get_server()
        if (server not in self.servers) and (server != ''):
            self.servers.append(server)
            self.listbox_servers.insert(END, server)
            playdoh.USERPREF['favoriteservers'] = self.servers
            playdoh.USERPREF.save()
        playdoh.log_info("Connecting to %s" % server)
        if os.name != 'posix':
            Thread(target=self._get_info).start()
        else:
            self._get_info()
        
    def _set_units(self):
        self.disable_buttons()
        self.get_server()
        
        playdoh.GC.set([self.server])
        disconnect = playdoh.GC.connect()
        
        set_my_resources(self.server, self.cpu, self.gpu)
        self._get_info()
                
        if disconnect: playdoh.GC.disconnect()
        
        self.enable_buttons()
        
    def set_units(self):
        if os.name != 'posix':
            Thread(target=self._set_units).start()
        else:
            self._set_units()

    def exit(self):
        self.frame.quit()




if __name__ == '__main__':
    root = Tk()
    
    # Window resizable
    root.resizable(True, True)
    
    # Size of the window
    w = 400
    h = 480
    
    # Centers window on the screen
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws/2) - (w/2)
    y = (hs/2) - (h/2)
    
    root.geometry("%dx%d%+d%+d" % (w, h, x, y))
    app = PlaydohGUI(root)
    root.mainloop()

########NEW FILE########
__FILENAME__ = performance_opt
from playdoh import *
from multiprocessing import Process
from threading import Thread
import sys, time, unittest, numpy
from numpy import inf, ones, zeros, exp,sin
from numpy.random import rand
from pylab import *


def alloc(n):
    allocation = {}
#    machines = [(LOCAL_IP, 2718),
#            ('LOCAL_IP', 2718),
#            ('LOCAL_IP', 2718)]
    machines = [(LOCAL_IP, 2718),
                ('129.199.82.3', 2718),
                ('129.199.82.36', 2718)]
    maxcpu = 2
    if n<=maxcpu:
        allocation[machines[0]] = n
    elif n<=2*maxcpu:
        allocation[machines[0]] = maxcpu
        allocation[machines[1]] = n-maxcpu
    elif n<=3*maxcpu:
        allocation[machines[0]] = maxcpu
        allocation[machines[1]] = maxcpu
        allocation[machines[2]] = n-2*maxcpu
    return allocation


test_fun=1

if test_fun==1:
##schwefel  solution  (-420.9687....)


    def fun(a,x1,x2,x3,x4,x5,x6,x7,x8,x9,x10):
        from numpy import sqrt,sin,abs,zeros
        import time
        output=zeros(len(x1))

        for isample in xrange(len(x1)):
            output[isample]=418.9829*10+x1[isample]*sin(sqrt(abs(x1[isample])))+x2[isample]*sin(sqrt(abs(x2[isample])))+x3[isample]*sin(sqrt(abs(x3[isample])))+x4[isample]*sin(sqrt(abs(x4[isample])))+x5[isample]*sin(sqrt(abs(x5[isample])))+x6[isample]*sin(sqrt(abs(x6[isample])))+x7[isample]*sin(sqrt(abs(x7[isample])))+x8[isample]*sin(sqrt(abs(x8[isample])))+x9[isample]*sin(sqrt(abs(x9[isample])))+x10[isample]*sin(sqrt(abs(x10[isample])))
            #print a 
            time.sleep(a)

        return output
    min_dom=-512.03
    max_dom=511.97


if test_fun==2:
#Rosenbrock solution (1,1,1...)
    def fun(x1,x2,x3,x4,x5,x6,x7,x8,x9,x10):

        return 100*(-x2+x1**2)**2+(x1-1)**2+100*(-x3+x2**2)**2+(x2-1)**2+100*(-x4+x3**2)**2+(x3-1)**2+100*(-x5+x4**2)**2+(x4-1)**2+100*(-x6+x5**2)**2+(x5-1)**2+100*(-x7+x6**2)**2+(x6-1)**2+100*(-x8+x7**2)**2+(x7-1)**2+100*(-x9+x8**2)**2+(x8-1)**2
    min_dom=-2.048
    max_dom=2.048
            
if __name__ == '__main__':
    
    nbr_iterations=100
    
    nbr_particles=50
    nbr_cpu=array([1,2])
    
    scale_dom=0.75
    
    pause_values=array([0.000001,0.00001,0.0001])

    time_PSO=zeros((len(nbr_cpu),len(pause_values)))
    time_GA=zeros((len(nbr_cpu),len(pause_values)))
                  
    test_fun=1
    for itopology in xrange(len(nbr_cpu)):
        for ipause in xrange(len(pause_values)):
    
    
            t0 = time.time()
            result_PSO = minimize(fun,
                          algorithm = PSO,
                          ndimensions = 10,
                          other_param=pause_values[ipause],
                              niterations = nbr_iterations,
                              nparticles = nbr_particles,  
                        #  scaling='mapminmax',
                          cpu = nbr_cpu[itopology],
                        ##  x1 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom], x2 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x3 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom],x4 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x5 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom])
                          x1 = [min_dom,min_dom,max_dom,max_dom], x2 =[min_dom,min_dom,max_dom,max_dom],x3 = [min_dom,min_dom,max_dom,max_dom],x4 =[min_dom,min_dom,max_dom,max_dom],x5 =[min_dom,min_dom,max_dom,max_dom],
                                            x6 = [min_dom,min_dom,max_dom,max_dom], x7 =[min_dom,min_dom,max_dom,max_dom],x8 = [min_dom,min_dom,max_dom,max_dom],x9 =[min_dom,min_dom,max_dom,max_dom],x10 =[min_dom,min_dom,max_dom,max_dom],
        
                              returninfo=True
                              #allocation=alloc(nbr_cpu)
                              )
            time_PSO[itopology,ipause]= time.time()-t0
      
        
            t0 = time.time()
            result_GA = minimize(fun,
                          algorithm = GA,
                          other_param=pause_values[ipause],
                          ndimensions = 10,
                              niterations = nbr_iterations,
                              nparticles = nbr_particles,  
                          cpu = nbr_cpu[itopology],
                          x1 = [min_dom,min_dom,max_dom,max_dom], x2 =[min_dom,min_dom,max_dom,max_dom],x3 = [min_dom,min_dom,max_dom,max_dom],x4 =[min_dom,min_dom,max_dom,max_dom],x5 =[min_dom,min_dom,max_dom,max_dom],
                          x6 = [min_dom,min_dom,max_dom,max_dom], x7 =[min_dom,min_dom,max_dom,max_dom],x8 = [min_dom,min_dom,max_dom,max_dom],x9 =[min_dom,min_dom,max_dom,max_dom],x10 =[min_dom,min_dom,max_dom,max_dom],                          
                          returninfo=True)
        
            time_GA[itopology,ipause]= time.time()-t0
        
    figure(2)
    plot(pause_values,time_PSO[0,:],'-o')
    plot(pause_values,time_PSO[1,:],'-o')
    plot(pause_values,time_GA[0,:],'--o')
    plot(pause_values,time_GA[1,:],'--o')
   # print 'Solution:  CMA: ',result_CMA[0]#,'PSO: ',result_PSO[0]#,'GA: ',result_GA[0]
   # plot(fitness_CMA)
#    plot(fitness_PSO)
#    print result_PSO[0]
#        plot(fitness_GA)


    show()


########NEW FILE########
__FILENAME__ = performance_opt_distant
from playdoh import *
from multiprocessing import Process
from threading import Thread
import sys, time, unittest, numpy
from numpy import inf, ones, zeros, exp,sin
from numpy.random import rand
from pylab import *


def alloc(n):
    allocation = {}
#    machines = [(LOCAL_IP, 2718),
#            ('LOCAL_IP', 2718),
#            ('LOCAL_IP', 2718)]
    machines = [(LOCAL_IP, 2718),
                ('129.199.82.3', 2718),
                ('129.199.82.36', 2718)]
    maxcpu = 2
    if n<=maxcpu:
        allocation[machines[0]] = n
    elif n<=2*maxcpu:
        allocation[machines[0]] = maxcpu
        allocation[machines[1]] = n-maxcpu
    elif n<=3*maxcpu:
        allocation[machines[0]] = maxcpu
        allocation[machines[1]] = maxcpu
        allocation[machines[2]] = n-2*maxcpu
    return allocation


test_fun=1

if test_fun==1:
##schwefel  solution  (-420.9687....)
    def fun(x1,x2,x3,x4,x5,x6,x7,x8,x9,x10):
        from numpy import sqrt,sin,abs
        return 418.9829*10+x1*sin(sqrt(abs(x1)))+x2*sin(sqrt(abs(x2)))+x3*sin(sqrt(abs(x3)))+x4*sin(sqrt(abs(x4)))+x5*sin(sqrt(abs(x5)))
        +x6*sin(sqrt(abs(x6)))+x7*sin(sqrt(abs(x7)))+x8*sin(sqrt(abs(x8)))+x9*sin(sqrt(abs(x9)))+x10*sin(sqrt(abs(x10)))
    min_dom=-512.03
    max_dom=511.97


if test_fun==2:
#Rosenbrock solution (1,1,1...)
    def fun(x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,A):
        print A
        return 100*(-x2+x1**2)**2+(x1-1)**2+100*(-x3+x2**2)**2+(x2-1)**2+100*(-x4+x3**2)**2+(x3-1)**2+100*(-x5+x4**2)**2+(x4-1)**2+100*(-x6+x5**2)**2+(x5-1)**2+100*(-x7+x6**2)**2+(x6-1)**2+100*(-x8+x7**2)**2+(x7-1)**2+100*(-x9+x8**2)**2+(x8-1)**2
    min_dom=-2.048
    max_dom=2.048





if __name__ == '__main__':
    
    nbr_iterations=50
    
    nbr_particles=50
    nbr_cpu=1
    
    scale_dom=0.75
    optCMA=dict()
    optCMA['proportion_selective']=0.1
    optCMA['returninfo']=True
    result_CMA = minimize(fun,
                      algorithm = CMAES,
                      ndimensions = 10,
                      niterations = nbr_iterations,
                      nparticles = nbr_particles,  
                      scaling='mapminmax',
                      cpu = nbr_cpu,
                    ##  x1 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom], x2 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x3 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom],x4 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x5 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom])
                      x1 = [min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom], x2 =[min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],x3 = [min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],x4 =[min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],x5 =[min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],
                    x6 = [min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom], x7 =[min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],x8 = [min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],x9 =[min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],x10 =[min_dom,scale_dom*min_dom,scale_dom*max_dom,max_dom],
                      returninfo=True,
                      optparams=optCMA)
    print len(result_CMA)
    fitness_CMA=result_CMA[1][0]
#
##    exit()
    fitness_CMA=result_CMA[2][0]
    figure(1)
    subplot(411)
    plot(result_CMA[2][0])
    subplot(412)
    plot(result_CMA[2][1].T)
    subplot(413)
    plot(result_CMA[2][2].T)
    subplot(414)
    plot(result_CMA[2][3].T)
    
    result_PSO = minimize(fun,
                  algorithm = PSO,
                  ndimensions = 10,
                      niterations = nbr_iterations,
                      nparticles = nbr_particles,  
                #  scaling='mapminmax',
                  cpu = nbr_cpu,
                ##  x1 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom], x2 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x3 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom],x4 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x5 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom])
                  x1 = [min_dom,min_dom,max_dom,max_dom], x2 =[min_dom,min_dom,max_dom,max_dom],x3 = [min_dom,min_dom,max_dom,max_dom],x4 =[min_dom,min_dom,max_dom,max_dom],x5 =[min_dom,min_dom,max_dom,max_dom],
                                    x6 = [min_dom,min_dom,max_dom,max_dom], x7 =[min_dom,min_dom,max_dom,max_dom],x8 = [min_dom,min_dom,max_dom,max_dom],x9 =[min_dom,min_dom,max_dom,max_dom],x10 =[min_dom,min_dom,max_dom,max_dom],

                      returninfo=True
                      #allocation=alloc(nbr_cpu)
                      )

    fitness_PSO=result_PSO[2][0]


    result_GA = minimize(fun,
                  algorithm = GA,
                  ndimensions = 5,
                      niterations = nbr_iterations,
                      nparticles = nbr_particles,  
                #  scaling='mapminmax',
                  cpu = nbr_cpu,
                ##  x1 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom], x2 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x3 = [min_dom,3./4*min_dom,3./4*max_dom,max_dom],x4 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom],x5 =[min_dom,3./4*min_dom,3./4*max_dom,max_dom])
                  x1 = [min_dom,min_dom,max_dom,max_dom], x2 =[min_dom,min_dom,max_dom,max_dom],x3 = [min_dom,min_dom,max_dom,max_dom],x4 =[min_dom,min_dom,max_dom,max_dom],x5 =[min_dom,min_dom,max_dom,max_dom],
                      returninfo=True)

    fitness_GA=result_GA[2][0]
    
    figure(2)
    print 'Solution:  CMA: ',result_CMA[0],'PSO: ',result_PSO[0],'GA: ',result_GA[0]
    plot(fitness_CMA)
    plot(fitness_PSO)
    print result_PSO[0]
    plot(fitness_GA)


    show()


########NEW FILE########
__FILENAME__ = create_dist
import os


os.chdir('../../.')  # work from project root
os.system('python setup.py bdist_wininst')
os.system('python setup.py sdist --formats=gztar,zip')

########NEW FILE########
__FILENAME__ = register_pypi
'''
NOTE: you need a .pypirc file to do this, you may need to set the
HOME env to where it is saved. Also note that any spaces in the
filename of HOME will cause it to not work, so use old style 8.3
equivalent name.

Also note that manifest.in may not work right with this?
'''

import os

os.chdir('../../.')  # work from project root
os.system('python setup.py register')
# os.system('python setup.py sdist bdist_wininst upload')

########NEW FILE########
__FILENAME__ = allocate
"""
Command-line tool for resource allocation. Can be executed in command line like this:

    Usage: python allocate.py server nbr type [options]
    
    Arguments:
      server                the IP address of the Playdoh server
      nbr                   the number of resources to allocate to this client
      type                  the resource type: ``'CPU'`` or ``'GPU'``
    
    Options:
      -h, --help            show this help message and exit
      -p PORT, --port=PORT  port (default: 2718)
"""
from playdoh import *
import sys, optparse

def main():
    parser = optparse.OptionParser(usage = "usage: python allocate.py server nbr type")
#    parser.add_option("-c", "--cpu", dest="cpu", default=MAXCPU,
#                      help="number of CPUs (default: MAXCPU)", metavar="CPU")
#    parser.add_option("-g", "--gpu", dest="gpu", default=MAXGPU,
#                      help="number of GPUs (default: MAXGPU)", metavar="GPU")
    parser.add_option("-p", "--port", dest="port", default=DEFAULT_PORT,
                      help="port (default: %s)" % DEFAULT_PORT, metavar="PORT")
    
    (options, args) = parser.parse_args()
    if len(args)==0:
        print "You must specify the server IP address"
        return
    server = args[0]
    port = int(options.port)
    # only the server = get idle resources
    if len(args) == 1:
        resources = get_available_resources((server, port))
        my_resources = get_my_resources((server, port))
        for type in ['CPU', 'GPU']:
            print "%d %s(s) available, %d allocated, on %s" % (resources[0][type], type, my_resources[0][type], server)
    else:
        nbr = int(args[1])
        type = args[2][:3].upper()
        request_resources((server, port), **{type: nbr})
        resources = get_my_resources((server, port))
        print "%d %s(s) allocated to you on %s" % (resources[0][type], type, server)
    
if __name__ == '__main__':
    main()
    
########NEW FILE########
__FILENAME__ = closeserver
"""
Close Playdoh servers. Can be executed in command line like this:

    Usage: python closeserver.py server1:port1 server2:port2 ... [options]
    
    Options:
      -h, --help            show this help message and exit
      -p, --port            specify a port for all servers
  
A port can be specified for every server with the syntax ``IP:port``. Also,
the option --port allows to specify the same port for all servers.
"""
from playdoh import *
import sys, optparse

def main():
    MAXGPU = get_gpu_count()
        
    parser = optparse.OptionParser(usage = "usage: python closeserver.py server1 server2 ... [options]")
    parser.add_option("-p", "--port", dest="port", default=DEFAULT_PORT,
                      help="port (default: %s)" % DEFAULT_PORT, metavar="PORT")
    
    servers = []
    (options, args) = parser.parse_args()
    for arg in args:
        if ':' in arg:
            server, port = arg.split(':')
            port = int(port)
        else:
            server = arg
            port = int(options.port)
        servers.append((server, port))
    if len(servers) == 0: servers = ['localhost']
    log_info("Closing %d server(s)" % len(servers))
    close_servers(servers)
    
if __name__ == '__main__':
    main()
    
########NEW FILE########
__FILENAME__ = cmaes
from playdoh import *
from test import *
import numpy, sys, time
from numpy import int32, ceil

def fitness_fun(x):
    if x.ndim == 1:
        x = x.reshape((1,-1))
    result = numpy.exp(-(x**2).sum(axis=0))
    return result

if __name__ == '__main__':
    nlocal = 2
    
    # List of machines external IP addresses
    machines = []
    local_machines = [('localhost', 2718+i) for i in xrange(nlocal)]
    machines.extend(local_machines)
    
    for m in local_machines:
        Process(target=open_server, args=(m[1],1,0)).start()
        time.sleep(.2)
        
    # State space dimension (D)
    dimension = 10
    
    # ``initrange`` is a Dx2 array with the initial intervals for every dimension 
    initrange = numpy.tile([-10.,10.], (dimension,1))
    
    result = maximize(fitness_fun,
                      algorithm = CMAES,
                      maxiter = 100,
                      popsize = 1000,
                      machines = machines,
                      initrange = initrange)
    
    time.sleep(.2)
    close_servers(machines)
    
    print result.best_pos


########NEW FILE########
__FILENAME__ = connection_old
from debugtools import *
from userpref import *
import multiprocessing, multiprocessing.connection, threading, logging
import os, sys, zlib, cPickle, time, traceback, gc, socket, base64, math, binascii, hashlib

BUFSIZE = 2048
try:
    LOCAL_IP = socket.gethostbyname(socket.gethostname())
except:
    LOCAL_IP = '127.0.0.1'

__all__ = ['accept', 'connect', 'LOCAL_IP']

class Connection(object):
    """
    Handles chunking and compression of data.
    
    To minimise data transfers between machines, we can use data compression,
    which this Connection handles automatically.
    """
    def __init__(self, conn, chunked=True, compressed=False):
        self.conn = conn
        self.chunked = chunked
        self.compressed = compressed
        self.BUFSIZE = BUFSIZE
        
    def send(self, obj):
        s = cPickle.dumps(obj, -1)
        if self.compressed:
            s = zlib.compress(s)
        if self.chunked:
            l = int(math.ceil(float(len(s))/self.BUFSIZE))
            # len(s) is a multiple of BUFSIZE, padding right with spaces
            s = s.ljust(l*self.BUFSIZE)
            l = "%08d" % l
            try:
                self.conn.sendall(l)
                self.conn.sendall(s)
            except:
                log_warn("Connection error")
        else:
            self.conn.sendall(s)
            
    def recv(self):
        if self.chunked:
            # Gets the first 8 bytes to retrieve the number of packets.
            l = ""
            n = 8
            while n > 0:
                l += self.conn.recv(n)
                n -= len(l)
            # BUG: sometimes l is filled with spaces??? setting l=1 in this case
            # (not a terrible solution)
            try:
                l = int(l)
            except:
                log_warn("transfer error, the paquet size was empty")
                l = 1
            
            length = l*self.BUFSIZE
            s = ""
            # Ensures that all data have been received
            while len(s) < length:
                data = self.conn.recv(self.BUFSIZE)
                s += data
        else:
            s = self.conn.recv()
        # unpads spaces on the right
        s = s.rstrip()
        if self.compressed:
            s = zlib.decompress(s)
        return cPickle.loads(s)
    
#    def recv(self):
#        for i in xrange(5):
#            try:
#                data = self._recv()
#                break
#            except Exception as e:
#                if i==4: raise Exception("Connection error")
#                log_warn("Connection error: %s" % str(e))
#                time.sleep(.1*(i+1))
#        return data
    
    def close(self):
        if self.conn is not None:
            r = self.conn.close()
            self.conn = None




def accept(address):
    """
    Accepts a connection and returns a connection object.
    """
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        for i in xrange(5):
            try:
    #            log_debug("trying to bind the socket...")
                s.bind(address)
                s.listen(5)
    #            log_debug("the socket is now listening")
                break
            except:
                if i<4:
                    t = .25*2**i
                    log_debug("unable to bind the socket, trying again in %.2f seconds..." % t)
                    time.sleep(t)
                else:
                    log_debug("unable to bind the socket")
                    raise Exception("unable to bind the socket")
        try:
            conn, addr = s.accept()
        except:
            raise Exception("unable to accept incoming connections")
        conn = Connection(conn)
        
        auth = conn.recv()
        if auth == hashlib.md5(USERPREF['authkey']).hexdigest():
            conn.send('right authkey')
            break
        else:
            log_warn("Wrong authkey, listening to new connection")
            conn.send('wrong authkey')
            continue
        s.close()
        time.sleep(.1)
        
    # The client can send its id at each connection, otherwise it can be retrieved
    # from the socket.accept() function.
#    clientid = conn.recv()
#    if clientid is None:
#        clientid = addr[0]
#    log_debug("client address: %s" % clientid)
    
    return conn, addr[0]

def connect(address):
    """
    Connects to a server and returns a Connection object.
    """
    def _create_connection():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for i in xrange(5):
            try:
                s.connect(address)
                break
            except:
                if i<4:
                    t = .1*2**i
                    log_debug("client: unable to connect, trying again in %.2f seconds..." % t)
                    time.sleep(t)
                else:
                    msg = "unable to connect to '%s' on port %d" % address
                    log_warn(msg)
                    raise Exception(msg)
                    return None
        conn = Connection(s)
        return conn

    hash = hashlib.md5(USERPREF['authkey']).hexdigest()
    
    for i in xrange(4):
        try:
            conn = _create_connection()
            conn.send(hash)
            resp = conn.recv()
            break
        except Exception as e:
            log_warn("Connection error: %s, trying again... (%d/4)" % (str(e), i+1))
            time.sleep(.1*2**i)
    
    if resp == 'wrong authkey':
        raise Exception("Wrong authentication key")
    
    # sends the client id to the server
#    conn.send(clientid)
    time.sleep(.05) # waits a bit for the server to be ready to receive
    return conn
########NEW FILE########
__FILENAME__ = heat_equation
"""
PDE parallel numerical solver.
This example shows how to numerically solve the heat equation on a square
in parallel. 
"""
from playdoh import *
from numpy import *
from pylab import *

# Any task class must derive from the ParallelTask
class HeatSolver(ParallelTask):
    def initialize(self, X, dx, dt, iterations):
        # X is a matrix with the function values and the boundary values
        # X must contain the borders of the neighbors ("overlapping Xs")

        debug_level()
        
        self.X = X 
        self.n = X.shape[0]
        self.dx = dx
        self.dt = dt
        self.iterations = iterations
        self.iteration = 0

    def send_boundaries(self):
        # Send boundaries of the grid to the neighbors
        if 'left' in self.tubes_out:
            self.push('left', self.X[:,1])
        if 'right' in self.tubes_out:
            self.push('right', self.X[:,-2])
    
    def recv_boundaries(self):
        # Receive boundaries of the grid from the neighbors
        if 'right' in self.tubes_in:
            self.X[:,0] = self.pop('right')
        if 'left' in self.tubes_in:
            self.X[:,-1] = self.pop('left')
    
    def update_matrix(self):
        # Implement the numerical scheme for the PDE
        Xleft, Xright = self.X[1:-1,:-2], self.X[1:-1,2:]
        Xtop, Xbottom = self.X[:-2,1:-1], self.X[2:,1:-1]
        self.X[1:-1,1:-1] += self.dt*(Xleft+Xright+Xtop+Xbottom-4*self.X[1:-1,1:-1])/self.dx**2

    def start(self):
        # Run the numerical integration of the PDE
        for self.iteration in xrange(self.iterations):
            log_info("Iteration %d/%d" % (self.iteration+1, self.iterations))
            self.send_boundaries()
            self.recv_boundaries()
            self.update_matrix()
    
    def get_result(self):
        # Return the result
        return self.X[1:-1,1:-1]

def heat2d(n, iterations, nodes = None, machines = []):
    # Default allocation
    allocation = allocate(machines=machines, cpu=nodes)
    nodes = len(allocation)
    
    # ``split`` is the grid size on each node, without the boundaries
    split = [(n-2)*1.0/nodes for _ in xrange(nodes)]
    split = array(split, dtype=int)
    split[-1] = n-2-sum(split[:-1])
    
    dx=2./n
    dt = dx**2*.2
    
    # y is a Dirac function at t=0
    y = zeros((n,n))
    y[n/2,n/2] = 1./dx**2
    
    # Split y horizontally
    split_y = []
    j = 0
    for i in xrange(nodes):
        size = split[i]
        split_y.append(y[:,j:j+size+2])
        j += size
    
    # Define a double linear topology 
    topology = []
    for i in xrange(nodes-1):
        topology.append(('right', i, i+1))
        topology.append(('left', i+1, i))
    
    # Start the task
    task = start_task(HeatSolver, # name of the task class
                      topology=topology,
                      allocation=allocation,
                      args=(split_y, dx, dt, iterations)) # arguments of the ``initialize`` method
                                     
    # Retrieve the result, as a list with one element returned by ``MonteCarlo.get_result`` per node
    result = task.get_result()
    result = hstack(result)
    
    return result

if __name__ == '__main__':
    nlocal = 2
    
    # List of machines external IP addresses
    machines = []
    local_machines = [('localhost', 2718+i) for i in xrange(nlocal)]
    machines.extend(local_machines)
    
    for m in local_machines:
        Process(target=open_server, args=(m[1],1,0)).start()
    
    result = heat2d(50, 50, machines=machines)
    
    close_servers(local_machines)
    
########NEW FILE########
__FILENAME__ = modelfitting
'''
Model fitting example using several machines.
Before running this example, you must start the Playdoh server on the remote machines.
'''
from brian import loadtxt, ms, Equations
from brian.library.modelfitting import *
from multiprocessing import Process
from playdoh import *

if __name__ == '__main__':
    nlocal = 2
    
    # List of machines external IP addresses
    machines = []
    local_machines = [('localhost', 2718+i) for i in xrange(nlocal)]
    machines.extend(local_machines)
    
    for m in local_machines:
        Process(target=open_server, args=(m[1],1,0)).start()
    
    equations = Equations('''
        dV/dt=(R*I-V)/tau : 1
        I : 1
        R : 1
        tau : second
    ''')
    input = loadtxt('current.txt')
    spikes = loadtxt('spikes.txt')
    results = modelfitting( model = equations,
                            reset = 0,
                            threshold = 1,
                            data = spikes,
                            input = input,
                            dt = .1*ms,
                            popsize = 1000,
                            maxiter = 5,
                            delta = 4*ms,
                            unit_type = 'CPU',
                            machines = machines,
                            R = [1.0e9, 9.0e9],
                            tau = [10*ms, 40*ms],
                            refractory = [0*ms, 10*ms])
    print_table(results)


    close_servers(local_machines)
########NEW FILE########
__FILENAME__ = monte_carlo
"""
Monte Carlo simulation example of pi estimation.
This example shows how to use the Playdoh interface
to execute loosely coupled parallel tasks.
"""
from playdoh import *
import numpy as np

# Any task class must derive from the ParallelTask
class PiMonteCarlo(ParallelTask): 
    def initialize(self, n):
        # Specify the number of samples on this node
        self.n = n
    
    def start(self):
        # Draw n points uniformly in [0,1]^2
        samples = np.random.rand(2,self.n)
        # Count the number of points inside the quarter unit circle
        self.count = np.sum(samples[0,:]**2+samples[1,:]**2<1)
    
    def get_result(self):
        # Return the result
        return self.count
    
def pi_montecarlo(samples, machines):
    allocation = allocate(machines=machines, unit_type='CPU')
    nodes = len(allocation)
    # Calculate the number of samples for each node
    split_samples = [samples/nodes]*nodes
    # Launch the task on the local CPUs
    task = start_task(PiMonteCarlo, # name of the task class
                      allocation = allocation,
                      args=(split_samples,)) # arguments of MonteCarlo.initialize as a list, 
                                             # node #i receives split_samples[i] as argument
    # Retrieve the result, as a list with one element returned by MonteCarlo.get_result per node
    result = task.get_result()
    # Return the estimation of Pi
    return sum(result)*4.0/samples

if __name__ == '__main__':
    machines = ['localhost'
                ]

    nlocal = 2
    
    # List of machines external IP addresses
    machines = []
    local_machines = [('localhost', 2718+i) for i in xrange(nlocal)]
    machines.extend(local_machines)
    
    for m in local_machines:
        Process(target=open_server, args=(m[1],1,0)).start()
    
    result = pi_montecarlo(1000000, machines)
    print result
    
    close_servers(local_machines)
    
########NEW FILE########
__FILENAME__ = openserver
"""
Start a Playdoh server. Can be executed in command line like this:

    Usage: python openserver.py [options]
    
    Options:
      -h, --help            show this help message and exit
      -c CPU, --cpu=CPU     number of CPUs (default: MAXCPU)
      -g GPU, --gpu=GPU     number of GPUs (default: MAXGPU)
      -p PORT, --port=PORT  port (default: 2718)
"""
from playdoh import *
import sys, optparse

def main(port=None, maxcpu=None, maxgpu=None):
    MAXGPU = get_gpu_count()
        
    parser = optparse.OptionParser(usage = "usage: python server.py [options]")
    parser.add_option("-c", "--cpu", dest="cpu", default=MAXCPU,
                      help="number of CPUs (default: MAXCPU)", metavar="CPU")
    parser.add_option("-g", "--gpu", dest="gpu", default=MAXGPU,
                      help="number of GPUs (default: MAXGPU)", metavar="GPU")
    parser.add_option("-p", "--port", dest="port", default=DEFAULT_PORT,
                      help="port (default: %s)" % DEFAULT_PORT, metavar="PORT")
    
    (options, args) = parser.parse_args()
    
    if port is None: port = int(options.port)
    if maxcpu is None: maxcpu = int(options.cpu)
    if maxgpu is None: maxgpu = int(options.gpu)
    
    open_server(port=port,
                maxcpu=maxcpu,
                maxgpu=maxgpu)
    
if __name__ == '__main__':
    main(maxcpu=4,port=2718)
    
########NEW FILE########
__FILENAME__ = openservers
from playdoh import *
import os, threading

def open(n, port):
    os.system("python openserver.py -c %d -g 0 -p %d" % (n, 2718+port))

n = 6
cpus = [1,1,1,1,1,2]
for port in xrange(n):
    cpu = cpus[port]
    t = threading.Thread(target=open, args=(cpu, port))
    t.start()


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Brian documentation build configuration file, created by
# sphinx-quickstart on Wed Apr 30 17:21:19 2008.
#
# This file is execfile()d with the current directory set to
# its containing dir.
#
# The contents of this file are pickled, so don't put values in
# the namespace
# that aren't pickleable (module imports are okay, they're
# removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys
import os

building_as = 'html'

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.ifconfig',
              'sphinx.ext.graphviz', 'sphinx.ext.inheritance_diagram',
              'sphinx.ext.pngmath']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Playdoh'
copyright = '2011, Cyrille Rossant, Bertrand Fontaine, Dan Goodman'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '0.3'
# The full version, including alpha/beta/rc tags.
release = '0.3.1'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
unused_docs = ['completecontents']

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

html_theme = "default"
html_theme_options = {
    'sidebarbgcolor': '#ccccff',
    'sidebartextcolor': '#000000',
    'sidebarlinkcolor': '#0000a8',
    }

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
html_logo = 'logo.png'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.
#html_use_opensearch = False

# Output file base name for HTML help builder.
htmlhelp_basename = 'Playdohdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
# latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
# latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class
# [howto/manual]).
# latex_documents = [
#  ('index', 'Playdoh.tex', 'Playdoh Documentation', 'Cyrille Rossant',
# 'Bertrand Fontaine',
#   'Dan Goodman', 'manual'),
# ]

# The name of an image file (relative to this directory) to place at the
# top of the title page.
# latex_logo = None

# Additional stuff for the LaTeX preamble.
# latex_preamble = ''

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_use_modindex = True

########NEW FILE########
__FILENAME__ = allocation
"""
Resource allocation example showing how to allocate manually
resources on the servers.
The Playdoh server must run on the local machine and on
the default port (2718 by default)
for this script to work.
"""
from playdoh import *


# It can also be a list of server IP addresses
servers = 'localhost'

# Allocate automatically the maximum number of resources on the
# specified servers
alloc = allocate(servers)

# alloc is an Allocation object, it can be used as a dictionary
for machine, count in alloc.iteritems():
    print "%d CPUs allocated on machine %s" % (count, str(machine))

########NEW FILE########
__FILENAME__ = external_module
def external_fun(x):
    return x + 1

########NEW FILE########
__FILENAME__ = gpu
"""
Example of :func:`map` with a function loading CUDA code and running on GPUs.
"""
from playdoh import *
from numpy import *
import pycuda


# The function loading the CUDA code
def fun(scale):
    # The CUDA code, which multiplies a vector by a scale factor.
    code = '''
    __global__ void test(double *x, int n)
    {
     int i = blockIdx.x * blockDim.x + threadIdx.x;
     if(i>=n) return;
     x[i] *= %d;
    }
    ''' % scale

    # Compile the CUDA code to GPU code
    mod = pycuda.compiler.SourceModule(code)

    # Transform the CUDA function into a Python function
    f = mod.get_function('test')

    # Create a vector on the GPU filled with 8 ones
    x = pycuda.gpuarray.to_gpu(ones(8))

    # Start the function on the GPU
    f(x, int32(8), block=(8, 1, 1))

    # Load the result from the GPU to the CPU
    y = x.get()

    # Finally, return the result
    return y

# This line is required on Windows, any call to a Playdoh function
# must be done after this line on this OS.
# See http://docs.python.org/library/multiprocessing.html#windows
if __name__ == '__main__':
    # Execute ``fun(2)`` and ``fun(3)`` on 1 GPU on this machine
    # and return the result.
    if CANUSEGPU:
        print map(fun, [2, 3], gpu=1)

########NEW FILE########
__FILENAME__ = heat_equation
"""
PDE parallel numerical solver.
This example shows how to numerically solve the heat equation on a square
in parallel.
"""
from playdoh import *
from numpy import *
from pylab import *


# Any task class must derive from the ParallelTask
class HeatSolver(ParallelTask):
    def initialize(self, X, dx, dt, iterations):
        # X is a matrix with the function values and the boundary values
        # X must contain the borders of the neighbors ("overlapping Xs")
        self.X = X
        self.n = X.shape[0]
        self.dx = dx
        self.dt = dt
        self.iterations = iterations
        self.iteration = 0

    def send_boundaries(self):
        # Send boundaries of the grid to the neighbors
        if 'left' in self.tubes_out:
            self.push('left', self.X[:, 1])
        if 'right' in self.tubes_out:
            self.push('right', self.X[:, -2])

    def recv_boundaries(self):
        # Receive boundaries of the grid from the neighbors
        if 'right' in self.tubes_in:
            self.X[:, 0] = self.pop('right')
        if 'left' in self.tubes_in:
            self.X[:, -1] = self.pop('left')

    def update_matrix(self):
        # Implement the numerical scheme for the PDE
        Xleft, Xright = self.X[1:-1, :-2], self.X[1:-1, 2:]
        Xtop, Xbottom = self.X[:-2, 1:-1], self.X[2:, 1:-1]
        self.X[1:-1, 1:-1] += self.dt * (Xleft + Xright + Xtop + Xbottom - \
            4 * self.X[1:-1, 1:-1]) / self.dx ** 2

    def start(self):
        # Run the numerical integration of the PDE
        for self.iteration in xrange(self.iterations):
            log_info("Iteration %d/%d" % (self.iteration + 1,
                                          self.iterations))
            self.send_boundaries()
            self.recv_boundaries()
            self.update_matrix()

    def get_result(self):
        # Return the result
        return self.X[1:-1, 1:-1]


def heat2d(n, iterations, nodes=None, machines=[]):
    # Default allocation
    allocation = allocate(machines=machines, cpu=nodes)
    nodes = len(allocation)

    # ``split`` is the grid size on each node, without the boundaries
    split = [(n - 2) * 1.0 / nodes for _ in xrange(nodes)]
    split = array(split, dtype=int)
    split[-1] = n - 2 - sum(split[:-1])

    dx = 2. / n
    dt = dx ** 2 * .2

    # y is a Dirac function at t=0
    y = zeros((n, n))
    y[n / 2, n / 2] = 1. / dx ** 2

    # Split y horizontally
    split_y = []
    j = 0
    for i in xrange(nodes):
        size = split[i]
        split_y.append(y[:, j:j + size + 2])
        j += size

    # Define a double linear topology
    topology = []
    for i in xrange(nodes - 1):
        topology.append(('right', i, i + 1))
        topology.append(('left', i + 1, i))

    # Start the task
    task = start_task(HeatSolver,  # name of the task class
                      topology=topology,
                      allocation=allocation,
                      args=(split_y, dx, dt, iterations))  # arguments of the
                                                           # ``initialize``
                                                           # method

    # Retrieve the result, as a list with one element returned
    # by ``MonteCarlo.get_result`` per node
    result = task.get_result()
    result = hstack(result)

    return result


if __name__ == '__main__':
    result = heat2d(50, 50, nodes=MAXCPU - 1)
#    hot()
#    imshow(result)
#    show()

########NEW FILE########
__FILENAME__ = map
"""
Simple example of the :func:`map` function.
"""
from playdoh import *


# The function to parallelize
def fun(x):
    return x ** 2


# This line is required on Windows, any call to a Playdoh function
# must be done after this line on this OS.
# See http://docs.python.org/library/multiprocessing.html#windows
if __name__ == '__main__':
    # Execute ``fun(1)`` and ``fun(2)`` in parallel on two CPUs on this machine
    # and return the result.
    print map(fun, [1, 2], cpu=2)

########NEW FILE########
__FILENAME__ = map_async
"""
Example usage of the asynchronous version of :func:`map`.
"""
from playdoh import *
import time


# The function to parallelize
def fun(x):
    # Simulate a 1 second long processing
    time.sleep(1)
    return x ** 2


# This line is required on Windows, any call to a Playdoh function
# must be done after this line on this OS.
# See http://docs.python.org/library/multiprocessing.html#windows
if __name__ == '__main__':
    # Execute ``fun(1)`` and ``fun(2)`` in parallel on two CPUs on this
    # machine.
    # The ``map_async`` function returns immediately a ``Task`` object
    # which allows to get the results later.
    task = map_async(fun, [1, 2], cpu=2)

    # Get the job results
    print task.get_result()

########NEW FILE########
__FILENAME__ = map_dependencies
"""
Example usage of :func:`map` with a function that has module dependencies.
"""
from playdoh import *


# Import an external module in the same folder
from external_module import external_fun


# The function to parallelize
def fun(x):
    # Use the function defined in the external module
    return external_fun(x) ** 2

# This line is required on Windows, any call to a Playdoh function
# must be done after this line on this OS.
# See http://docs.python.org/library/multiprocessing.html#windows
if __name__ == '__main__':
    # Execute ``fun(1)`` and ``fun(2)`` in parallel on two CPUs on this machine
    # and return the result.
    # The ``codedependencies`` argument contains the list of external Python
    # modules
    # to transfer on the machines executing the task. It is only needed when
    # using
    # remote machines, and not when using CPUs on the local machine.
    print map(fun, [1, 2], codedependencies=['external_module.py'])

########NEW FILE########
__FILENAME__ = map_lambda
"""
Simple example of the :func:`map` function with a lambda function.
"""
from playdoh import *


# This line is required on Windows, any call to a Playdoh function
# must be done after this line on this OS.
# See http://docs.python.org/library/multiprocessing.html#windows
if __name__ == '__main__':
    # Execute ``lambda(1)`` and ``lambda(2)`` in parallel on two CPUs
    # on this machine
    # and return the result.
    print map(lambda x: x * x, [1, 2], cpu=2)

########NEW FILE########
__FILENAME__ = map_shared
"""
Example usage of the :func:`map` function with shared data.
"""
from playdoh import *
from numpy.random import rand


# The function to parallelize. The extra argument ``shared_data`` is a
# read-only dictionary
# residing is shared memory on the computer. It can contain large NumPy arrays
# used by
# all the CPUs to execute the function.
def fun(x, shared_data):
    return x + shared_data['x0']


# This line is required on Windows, any call to a Playdoh function
# must be done after this line on this OS.
# See http://docs.python.org/library/multiprocessing.html#windows
if __name__ == '__main__':
    # Execute two function evaluations with a large NumPy array in shared data.
    map(fun,
        [rand(100000, 2), rand(100000, 2)],
        cpu=2,
        shared_data={'x0': rand(100000, 2)})

########NEW FILE########
__FILENAME__ = maximize
"""
Simple example of :func:`maximize`.
"""
from playdoh import *
import numpy


# The fitness function to maximize
def fun(x):
    return numpy.exp(-x ** 2)


if __name__ == '__main__':
    # Maximize the fitness function in parallel
    results = maximize(fun,
                       popsize=10000,  # size of the population
                       maxiter=10,  # maximum number of iterations
                       cpu=1,  # number of CPUs to use on the local machine
                       x_initrange=[-10, 10])  # initial interval for
                                               # the ``x`` parameter

    # Display the final result in a table
    print_table(results)

########NEW FILE########
__FILENAME__ = maximize_class
"""
Example of :func:`maximize` by using a fitness function implemented in a class.
Using a class allows to have an initialization at the beginning of the
optimization.
"""
from playdoh import *
from numpy import exp, tile


# The class must derive from the ``Fitness`` class.
class FitnessTest(Fitness):
    # This method allows to initialize some data. Parameters
    # can be passed using the ``initargs`` and ``initkwds``
    # arguments of ``maximize``.
    def initialize(self, a):
        self.a = a

    # This method is called at every iteration.
    def evaluate(self, x):
        return exp(-((x - self.a) ** 2))


if __name__ == '__main__':
    # Maximize the fitness function in parallel
    results = maximize(FitnessTest,
                       popsize=10000,  # size of the population
                       maxiter=10,  # maximum number of iterations
                       cpu=1,  # number of CPUs to use on the local machine
                       args=(3,),  # parameters for the ``initialize`` method
                       x_initrange=[-10, 10])  # initial interval for the
                                               # ``x`` parameter

    # Display the final result in a table
    print_table(results)

########NEW FILE########
__FILENAME__ = maximize_groups
"""
Example of :func:`maximize` with several groups. Groups allow to optimize
a fitness function with different parameters in parallel but by
vectorizing the fitness evaluation for all groups.
"""
from playdoh import *
import numpy


# The fitness function is a Gaussian with different centers for
# different groups ``shared_data`` contains the different centers.
def fun(x, y, nodesize, shared_data, groups):
    # Expand ``x0`` and ``y0`` to match the total population size
    x0 = numpy.kron(shared_data['x0'], numpy.ones(nodesize / groups))
    y0 = numpy.kron(shared_data['y0'], numpy.ones(nodesize / groups))
    # Compute the Gaussian for all centers in a vectorized fashion
    result = numpy.exp(-(x - x0) ** 2 - (y - y0) ** 2)
    return result


if __name__ == '__main__':
    # Maximize the fitness function in parallel
    results = maximize(fun,
                       popsize=50,  # size of the population for each group
                       maxiter=10,  # maximum number of iterations
                       cpu=1,  # number of CPUs to use on the local machine
                       groups=3,  # number of groups
                       algorithm=CMAES,  # optimization algorithm, can be PSO,
                                         # GA or CMAES
                       shared_data={'x0': [0, 1, 2],  # centers of the Gaussian
                                                      # for each group
                                    'y0': [3, 4, 5]},
                       x_initrange=[-10, 10],  # initial interval for the
                                                 # ``x`` parameter
                       y_initrange=[-10, 10])  # initial interval for the
                                                 # ``y`` parameter

    # Display the final result in a table
    print_table(results)

########NEW FILE########
__FILENAME__ = maximize_matrix
"""
Example of :func:`maximize` with a fitness function accepting arrays
rather than keyword arguments.
"""
from playdoh import *
import numpy


def fun(x):
    if x.ndim == 1:
        x = x.reshape((1, -1))
    result = numpy.exp(-(x ** 2).sum(axis=0))
    return result


if __name__ == '__main__':
    # State space dimension (D)
    dimension = 4

    # ``initrange`` is a Dx2 array with the initial intervals for every
    # dimension
    initrange = numpy.tile([-10., 10.], (dimension, 1))

    # Maximize the fitness function in parallel
    results = maximize(fun,
                       popsize=10000,  # size of the population
                       maxiter=10,  # maximum number of iterations
                       cpu=1,  # number of CPUs to use on the local machine
                       initrange=initrange)

    # Display the final result in a table
    print_table(results)

########NEW FILE########
__FILENAME__ = monte_carlo
"""
Monte Carlo simulation example of pi estimation.
This example shows how to use the Playdoh interface
to execute loosely coupled parallel tasks.
"""
from playdoh import *
import numpy as np


# Any task class must derive from the ParallelTask
class PiMonteCarlo(ParallelTask):
    def initialize(self, n):
        # Specify the number of samples on this node
        self.n = n

    def start(self):
        # Draw n points uniformly in [0,1]^2
        samples = np.random.rand(2, self.n)
        # Count the number of points inside the quarter unit circle
        self.count = np.sum(samples[0, :] ** 2 + samples[1, :] ** 2 < 1)

    def get_result(self):
        # Return the result
        return self.count


def pi_montecarlo(samples, nodes):
    # Calculate the number of samples for each node
    split_samples = [samples / nodes] * nodes
    # Launch the task on the local CPUs
    task = start_task(PiMonteCarlo,  # name of the task class
                      cpu=nodes,  # use <nodes> CPUs on the local machine
                      args=(split_samples,))  # arguments of
                                              # MonteCarlo.initialize
                                              # as a list,
                                              # node #i receives
                                              # split_samples[i]
                                              # as argument
    # Retrieve the result, as a list with one element returned
    # by MonteCarlo.get_result per node
    result = task.get_result()

    # Return the estimation of Pi
    return sum(result) * 4.0 / samples


if __name__ == '__main__':
    # Evaluate Pi with 10,000 samples and 2 CPUs
    print pi_montecarlo(1000000, 2)

########NEW FILE########
__FILENAME__ = resources
"""
Resource allocation example showing how to allocate resources on the servers.
The Playdoh server must run on the local machine and on the default port
(2718 by default)
for this script to work.
"""
from playdoh import *


# It can also be a list of server IP addresses
servers = 'localhost'

# Get all the allocated resources on the servers
# total_resources[0]['CPU'] is a dictionary where keys are client IP
# addresses and values are the number of CPUs allocated to the corresponding
# clients
total_resources = get_server_resources(servers)
print "Total allocated resources:", total_resources[0]['CPU']

# Get the idle resources on the specified servers
# idle_resources[0]['CPU'] is the number of CPUs available on the first server
# This number includes the already allocated resources for this client
idle_resources = get_available_resources(servers)
print "%d idle CPUs" % idle_resources[0]['CPU']

# Get the resources allocated to this client on the specified servers
# my_resources['CPU'] is the number of CPUs allocated on the servers for this
# client
my_resources = get_my_resources(servers)
print "%d CPUs allocated to me" % my_resources[0]['CPU']

# Allocate as many CPUs as possible on the specified servers for this client
n = request_all_resources(servers, 'CPU')
print "Just allocated %d CPUs on the server" % n[0]

my_resources = get_my_resources(servers)
print "%d CPUs allocated to me now" % my_resources[0]['CPU']

total_resources = get_server_resources(servers)
print "Total allocated resources now:", total_resources[0]['CPU']

########NEW FILE########
__FILENAME__ = asyncjobhandler
"""
Asynchronous Job Manager
"""
from cache import *
from gputools import *
from pool import *
from rpc import *
from resources import *
from numpy import sum
import cPickle
import os
import os.path
import time
import hashlib
import random
import traceback


__all__ = ['Job', 'JobRun', 'AsyncJobHandler', 'submit_jobs']


class Job(object):
    jobdir = JOBDIR

    def __init__(self, function, *args, **kwds):
        """
        Constructor.

        *Arguments*

        `function`
          The function to evaluate, it is a native Python function. Function
          serialization should take care of ensuring that this function is
          correctly defined in the namespace.

        `*args, **kwds`
          The arguments of the function.
        """
        self.function = function
        self.args = args
        self.kwds = kwds
        self.result = None
        self.status = 'queued'

    def compute_id(self):
        """
        Computes a unique identifier of the job.
        """
        m = hashlib.sha1()
        pid = os.getpid()  # current process id
#        t = int(time.time() * 10000) % 1000000  # time
        s = str(self.function)  # function name
        s += cPickle.dumps(self.args, -1)  # args dump
        s += cPickle.dumps(self.kwds, -1)  # args dump
        m.update(str(random.random()))  # random number
        m.update(str(pid))
        m
        m.update(s)
        hash = m.hexdigest()
        self._id = hash
        return self._id

    def get_id(self):
        if not hasattr(self, '_id'):
            self.compute_id()
        return self._id
    id = property(get_id)

    def get_filename(self):
        return os.path.join(Job.jobdir, self.id + '.pkl')
    filename = property(get_filename)

    def evaluate(self):
        """
        Evaluates the function on the given arguments.
        """
        try:
            self.status = 'processing'
            self.result = self.function(*self.args, **self.kwds)
            self.status = 'finished'
        except Exception as inst:
            # add the traceback to the exception
            msg = traceback.format_exc()
            inst.traceback = msg
            log_warn("An exception has occurred in %s, print exc.traceback \
where exc is the Exception object returned by playdoh.map" %
                self.function.__name__)
            self.result = inst
            self.status = 'crashed'
        return self.result

    def record(self):
        """
        Records the job after evaluation on the disk.
        """
        if not os.path.exists(self.jobdir):
            log_debug("creating '%s' folder for code pickling" % self.jobdir)
            os.mkdir(self.jobdir)
        log_debug("writing '%s'" % self.filename)

        # delete shared data before pickling
        if 'shared_data' in self.kwds:
            del self.kwds['shared_data']

        file = open(self.filename, 'wb')
        cPickle.dump(self, file, -1)
        file.close()

    @staticmethod
    def load(id):
        """
        Returns the Job object stored in the filesystem using its identifier.
        """
        try:
            filename = os.path.join(Job.jobdir, id + '.pkl')
            log_debug("opening file '%s'" % filename)
            file = open(filename, 'rb')
            job = cPickle.load(file)
            file.close()
#            time.sleep(.005)
        except IOError:
            log_debug("file '%s' not found" % filename)
            job = None
        except EOFError:
            log_debug("EOF error with '%s', trying again..." % filename)
            time.sleep(.2)
            file = open(filename, 'rb')
            job = cPickle.load(file)
            file.close()
        return job

    @staticmethod
    def erase(id):
        """
        Erases the Job object stored in the filesystem using its identifier.
        """
        filename = os.path.join(Job.jobdir, id + '.pkl')
        log_debug("erasing '%s'" % filename)
        try:
            os.remove(filename)
        except:
            log_warn("Unable to erase <%s>" % filename)

    @staticmethod
    def erase_all():
        """
        Erases all Job objects stored in the filesystem.
        """
        files = os.listdir(Job.jobdir)
        log_debug("erasing all files in '%s'" % Job.jobdir)
        [os.remove(os.path.join(Job.jobdir, filename)) for filename in files]


def eval_job(job, shared_data={}):
    """
    Evaluates a job. Must be global to be passed to CustomPool.
    Handles Exceptions.
    """
    if len(shared_data) > 0:
        job.kwds['shared_data'] = shared_data
    result = job.evaluate()
    job.record()
    return result


class AsyncJobHandler(object):
    """
    A Handler object handling asynchronous job management, on the server side.
    """
    def __init__(self):
        """
        max_cpu is the maximum number of CPUs dedicated to the cluster
        idem for max_gpu
        None = use all CPUs/GPUs available
        """
        self.handlers = []
        self.cpu = MAXCPU
        self.gpu = 0
        self.pool = None
        self.cpool = None
        self.jobs = {}

    def add_jobs(self, jobs):
        for job in jobs:
            self.jobs[job.id] = job
        return [job.id for job in jobs]

    def initialize_cpool(self, type, units, do_redirect):
        pool = self.pools[type]
#        status = pool.get_status()
        unitindices = pool.get_idle_units(units)
        if len(unitindices) != units:
            msg = "not enough %s(s) available, exiting now" % (type)
            log_warn(msg)
            raise Exception(msg)
        log_debug("found %d %s(s) available: %s" % (units, type,
                                                    str(unitindices)))

        self.cpool = CustomPool(unitindices, unittype=type,
                                do_redirect=do_redirect)
        # links the global Pool object to the CustomPool object
        self.cpool.pool = pool

    def submit(self, jobs, type='CPU', units=None, shared_data={},
               do_redirect=None):
        """
        Submit jobs.

        *Arguments*

        `jobs`
          A list of Job objects.
        """
        job_ids = self.add_jobs(jobs)
        # By default, use all resources assigned to the current client
        # for this handler.
        # If units is set, then use only this number of units
#        if units is None:
#            units = self.resources[type][self.client]

        # find idle units
        if units is None:
            log_warn("units should not be None in submit")

        if self.cpool is None:
            self.initialize_cpool(type, units, do_redirect)
        else:
            self.cpool.set_units(units)

        pool_ids = self.cpool.submit_tasks(eval_job, shared_data, jobs)
        for i in xrange(len(jobs)):
            id = job_ids[i]
            self.jobs[id].pool_id = pool_ids[i]

        return job_ids

    def get_pool_ids(self, job_ids):
        """
        Converts job ids (specific to AsyncJobHander) to pool ids
        (specific to the CustomPool object)
        """
        return [self.jobs[id].pool_id for id in job_ids]

    def get_status(self, job_ids):
        if job_ids is None:
            statuss = None
            raise Exception("The job identifiers must be specified")
        else:
            statuss = []
            for id in job_ids:
                job = Job.load(id)
                if job is not None:
                    log_debug("job file '%s' found" % id)
                    status = job.status
                elif id in self.jobs.keys():
                    log_debug("job file '%s' not found" % id)
                    status = self.jobs[id].status
                else:
                    log_warn("job '%s' not found" % id)
                    status = None
                statuss.append(status)
        return statuss

    def get_results(self, job_ids):
        if job_ids is None:
            results = None
            raise Exception("Please specify job identifiers.")
        else:
            results = []
            for id in job_ids:
                job = Job.load(id)
                if job is not None:
                    result = job.result
                else:
                    # if job is None, it means that it probably has
                    # not finished yet
                    result = None
#                    if self.pool is not None:
                    log_debug("Tasks have not finished yet, waiting...")
                    self.cpool.join()
                    job = Job.load(id)
                    if job is not None:
                        result = job.result
                results.append(result)
        return results

    def has_finished(self, job_ids):
        if self.cpool is not None:
            pool_ids = self.get_pool_ids(job_ids)
            return self.cpool.has_finished(pool_ids)
        else:
            log_warn("The specified job identifiers haven't been found")
            return None

    def erase(self, job_ids):
        log_debug("Erasing job results")
        [Job.erase(id) for id in job_ids]

    def close(self):
        if hasattr(self, 'cpool'):
            if self.cpool is not None:
                self.cpool.close()
            else:
                log_warn("The pool object has already been closed")

    def kill(self):
        # TODO: jobids?
        if self.cpool is not None:
            self.cpool.kill()
        else:
            log_warn("The pool object has already been killed")


class JobRun(object):
    """
    Contains information about a parallel map that has been launched
    by the ``map_async`` function.

    Methods:

    ``get_status()``
        Returns the current status of the jobs.

    ``get_result(jobids=None)``
        Returns the result. Blocks until the jobs have finished.
        You can specify jobids to retrieve only some of the results,
        in that case it must
        be a list of job identifiers.
    """
    def __init__(self, type, jobs, machines=[]):
        self.type = type
        self.jobs = jobs
        self.machines = machines  # list of Machine object
        self._machines = [m.to_tuple() for m in self.machines]
        self.local = None
        self.jobids = None

    def set_local(self, v):
        self.local = v

    def set_jobids(self, jobids):
        self.jobids = jobids

    def get_machines(self):
        return self._machines

    def get_machine_index(self, machine):
        for i in xrange(len(self.machines)):
            if (self.machines[i] == machine):
                return i

    def concatenate(self, lists):
        lists2 = []
        [lists2.extend(l) for l in lists]
        return lists2

    def get_status(self):
        GC.set(self.get_machines(), handler_class=AsyncJobHandler)
        disconnect = GC.connect()

        status = GC.get_status(self.jobids)

        if disconnect:
            GC.disconnect()

        return self.concatenate(status)

    def get_results(self, ids=None):
        if ids is None:
            ids = self.jobids
        GC.set(self.get_machines(), handler_class=AsyncJobHandler)
        disconnect = GC.connect()

        if not self.local:
            log_info("Retrieving job results...")
        results = GC.get_results(ids)
        GC.erase(self.jobids)
        if disconnect:
            GC.disconnect()

#        clients = RpcClients(self.get_machines(),
#            handler_class=AsyncJobHandler)
#        clients.connect()
#        results = clients.get_results(self.jobids)
#        clients.erase(self.jobids)
#        clients.disconnect()

        results = self.concatenate(results)
        if self.local:
            close_servers(self.get_machines())
        return results

    def get_result(self):
        return self.get_results()

    def __repr__(self):
        nmachines = len(self.machines)
        if nmachines > 1:
            plural = 's'
        else:
            plural = ''
        return "<Task: %d jobs on %d machine%s>" % (len(self.jobs),
                                                    nmachines, plural)


def create_jobs(fun, argss, kwdss):
    """
    Create Job objects
    """
    jobs = []
    k = len(argss)  # number of non-named arguments
    keys = kwdss.keys()  # keyword arguments

    i = 0  # task index
    while True:
        try:
            args = [argss[l][i] for l in xrange(k)]
            kwds = dict([(key, kwdss[key][i]) for key in keys])
        except:
            break
        jobs.append(Job(fun, *args, **kwds))
        i += 1
    return jobs


def split_jobs(jobs, machines, allocation):
    """
    Splits jobs among workers
    """
    total_units = allocation.total_units
    njobs = len(jobs)

    # charge[i] is the number of jobs on machine #i
    i = 0  # worker index
    charge = []
    for m in machines:
        nbr_units = allocation[m]  # number of workers on this machine
        charge.append(nbr_units * njobs / total_units)
        i += 1
    charge[-1] = njobs - sum(charge[:-1], dtype=int)

    sjobs = []
    i = 0  # worker index
    total = 0  # total jobs
    for m in machines:
        k = charge[i]
        sjobs.append(jobs[total:(total + k)])
        total += k
        i += 1
        if total >= njobs:
            break
    return sjobs


def submit_jobs(fun,
                allocation,
                unit_type='CPU',
                shared_data={},
                local=None,
                do_redirect=None,
                argss=[],
                kwdss={}):
    """
    Submit map jobs. Use ``map_async`` instead.
    """
    machines = allocation.machines

    # creates Job objects
    jobs = create_jobs(fun, argss, kwdss)

    # creates a JobRun object
    myjobs = JobRun(unit_type, jobs, machines)

    # splits jobs
    sjobs = split_jobs(jobs, machines, allocation)
    units = [allocation[m] for m in myjobs.get_machines()]

    # are jobs running locally?
    if local is None and (len(machines) == 1) and (machines[0].ip == LOCAL_IP):
        myjobs.set_local(True)
    if local is not None:
        myjobs.set_local(local)

    GC.set(myjobs.get_machines(), handler_class=AsyncJobHandler)
    disconnect = GC.connect()

    # Submits jobs to the machines
#    clients = RpcClients(myjobs.get_machines(), handler_class=AsyncJobHandler)

    jobids = GC.submit(sjobs, type=unit_type, units=units,
                       shared_data=shared_data,
                       do_redirect=do_redirect)

    if disconnect:
        GC.disconnect()

    # Records job ids
    myjobs.set_jobids(jobids)

    return myjobs

########NEW FILE########
__FILENAME__ = baserpc
"""
Native Python RPC Layer
"""
from debugtools import *
from codehandler import *
from connection import *
from userpref import *
from subprocess import Popen, PIPE
import threading
import os
import time
from Queue import Queue

__all__ = ['DEFAULT_PORT', 'BaseRpcServer', 'BaseRpcClient', 'BaseRpcClients',
           'open_base_server', 'close_base_servers',
           'open_restart_server', 'restart'
#           'DistantException'
           ]

DEFAULT_PORT = USERPREF['port']


def open_base_server(port=None):
    BaseRpcServer(port=port).listen()


def close_base_servers(addresses):
    if type(addresses) is str:
        addresses = [(addresses, DEFAULT_PORT)]
    if type(addresses) is tuple:
        addresses = [addresses]
    BaseRpcClients(addresses).close_server()


#class DistantException(Exception):
#    """
#    Distant Exception class. Allows to re-raise exception on the client,
#    giving the filename and the line number of the original server-side
#    exception.
#    """
#    def __init__(self, exception = None):
#        if type(exception) == str:
#            exception = Exception(exception)
#        self.exception = exception
#        try:
#            self.filename = __file__
#            if os.path.splitext(__file__)[1] == '.pyc':
#                self.filename = __file__[:-1]
#        except:
#            self.filename = 'unknown'
#        try:
#            self.line = sys._getframe(1).f_lineno
#        except:
#            self.line = 0
#        try:
#            self.function = sys._getframe(1).f_code.co_name
#        except:
#            self.function = 'unknown'
#
#    def setinfo(self):
#        (self.filename, self.line, self.function, self.text) =
#               traceback.extract_tb(sys.exc_info()[2])[-1]
#
#    def __str__(self):
#        s = "A distant exception happened in:"
#        s += "\n  File \"%s\", line %d, in %s" % (self.filename,
#           self.line, str(self.function))
#        s += "\n    %s" % str(self.exception)
#        return s


class BaseRpcServer(object):
    def __init__(self, port=None, bindip=''):
        """
        to be implemented by a deriving class:
        initialize()
        process(client, procedure)
        shutdown()
        """
        if port is None:
            port = DEFAULT_PORT
        self.port = port
        self.address = (bindip, self.port)
        self.bool_shutdown = False

        # HACK: to fix windows bug: the server must not accept while
        # restarting subprocesses
        self.temp_result = None
        self.wait_before_accept = False
        self.acceptqueue = Queue()

    def serve(self, conn, client):
        # called in a new thread
        keep_connection = None  # allows to receive several procedures
                                # during the same session
        # None : close connection at the next iteration
        # False : close connection now
        # True : keep connection for now

        while keep_connection is not False:
            log_debug("server: serving client <%s>..." % str(client))
            procedure = conn.recv()
            log_debug("server: procedure '%s' received" % procedure)

            if procedure == 'keep_connection':
                keep_connection = True
                continue  # immediately waits for a procedure
            elif procedure == 'close_connection':
                keep_connection = False
                break  # close connection
            elif procedure == 'shutdown':
                log_debug("server: shutdown signal received")
                keep_connection = False
                self.bool_shutdown = True
                break  # closes the connection immediately
            elif procedure == 'get_temp_result':
                log_debug("sending temp result")
                conn.send(self.temp_result)
                self.temp_result = None
                keep_connection = False
                break

            # Mechanism to close the connection while processing a procedure
            # used to fix a bug: Processes shouldn't be started on Windows
            # while a connection is opened
            if (hasattr(procedure, 'close_connection_temp') and
                    procedure.close_connection_temp):
                log_debug("closing connection while processing procedure %s" %
                    str(procedure))
                self.wait_before_accept = True
#                conn.close()
#                conn = None

            # Dispatches the procedure to the handler unless the procedure
            # asks the server to close the handler or itself
            log_debug("server: processing procedure")
#            if procedure is not None:
            result = self.process(client, procedure)
#            else:
#                log_debug("Connection error happened, exiting")
#                result = None
#                break

            if (hasattr(procedure, 'close_connection_temp') and
                    procedure.close_connection_temp):
                self.temp_result = result
                # make sure that the accepting thread is waiting now
                time.sleep(.1)
                self.wait_before_accept = False
                self.acceptqueue.put(True)
                keep_connection = False
            else:
                log_debug("server: returning the result to the client")
                conn.send(result)

            if keep_connection is None:
                keep_connection = False

        if conn is not None:
            conn.close()
            conn = None
        log_debug("server: connection closed")

    def listen(self):
        """
        Listens to incoming connections and create one handler for each
        new connection.
        """
        conn = None
        threads = []
        index = 0

        # Initializing
        log_debug("Initializing server with IP %s on port %d" % (LOCAL_IP,
                                                                 self.port))
        self.initialize()

        while not self.bool_shutdown:
            try:
                log_debug("server: waiting for incoming connection on port \
                    %d..." % self.address[1])
                if self.wait_before_accept:
                    log_debug("waiting before accepting a connection...")
#                    time.sleep(USERPREF['wait_before_accept'])
                    self.acceptqueue.get()
                    log_debug("I can accept now!")
                conn, client = accept(self.address)  # accepts an incoming
                                                     # connection
                log_debug("Server established a connection with client %s on \
                           port %d" % (client, self.address[1]))
            except:
                log_warn("server: connection NOT established, closing now")
                break

            thread = threading.Thread(target=self.serve, args=(conn, client))
            thread.start()
            threads.append(thread)
            index += 1
            time.sleep(.1)

        # Closes the connection at the end of the server lifetime
        if conn is not None:
            conn.close()
            conn = None

        # closing
        log_debug("Closing server")
        self.shutdown()

        for i in xrange(len(threads)):
            log_debug("joining thread %d/%d" % (i + 1, len(threads)))
            threads[i].join(.1)

    def initialize(self):
        log_warn("server: 'initialize' method not implemented")

    def process(self, client, procedure):
        log_warn("server: 'process' method not implemented")
        return procedure

    def shutdown(self):
        log_warn("server: 'shutdown' method not implemented")


class BaseRpcClient(object):
    """
    RPC Client constructor.
    """
    def __init__(self, server):
        self.conn = None
        if type(server) is tuple:
            server, port = server
        else:
            port = None
        self.server = server
        if port is None:
            port = DEFAULT_PORT
        self.port = port
        self.keep_connection = False

    def open_connection(self, trials=None):
        log_debug("client: connecting to '%s' on port %d" % (self.server,
                                                             self.port))
        try:
            self.conn = connect((self.server, self.port), trials)
        except:
            log_warn("Error when connecting to '%s' on port %d" % (self.server,
                                                                   self.port))
            self.conn = None

    def close_connection(self):
        log_debug("client: closing connection")
        if self.conn is not None:
            self.conn.close()
        self.conn = None

    def is_connected(self):
        return self.conn is not None

    def execute(self, procedure):
        """
        Calls a procedure on the server from the client.
        """
        if not self.is_connected():
            self.keep_connection = False
            self.open_connection()

        log_debug("client: sending procedure '%s'" % procedure)
        try:
            self.conn.send(procedure)
        except:
            log_warn("client: connection lost while sending the procedure,\
                      connecting again...")
            self.open_connection()
            self.conn.send(procedure)

        # handling special mechanism to close the connection while processing
        # the procedure
        if (hasattr(procedure, 'close_connection_temp') and
                procedure.close_connection_temp):
            log_debug("closing the connection while processing the procedure")
            self.close_connection()
            log_debug("waiting...")
            time.sleep(.5)
            log_debug("opening the connection again")
            self.open_connection()
            self.conn.send("get_temp_result")
            log_debug("receiving temp result")
            result = self.conn.recv()
            log_debug("temp result received! closing connection")
            self.close_connection()
            log_debug("connection closed()")
        else:
            log_debug("client: receiving result")
            try:
                result = self.conn.recv()
            except:
                log_warn("client: connection lost while retrieving the result,\
                          connecting again...")
                self.open_connection()
                result = self.conn.recv()

            if not self.keep_connection:
                self.close_connection()

        # re-raise the Exception on the client if one was raised on the server
        if isinstance(result, Exception):
            raise result
        # Handling list of exceptions
#        if type(result) is list:
#            raise result[0]
#            exceptions = []
#            for r in result:
#                if isinstance(r, Exception):
#                    exceptions.append(str(r))
#            if len(exceptions)>0:
#                raise Exception("\n".join(exceptions))

        return result

    def connect(self, trials=None):
        self.keep_connection = True
        self.open_connection(trials)
        if self.conn is not None:
            self.conn.send('keep_connection')

    def disconnect(self):
        self.keep_connection = False
        if self.conn is not None:
            self.conn.send('close_connection')
        self.close_connection()

    def close_server(self):
        """
        Closes the server from the client.
        """
        if not self.is_connected():
            self.open_connection()
        log_debug("client: sending the shutdown signal")
        self.conn.send('shutdown')
        self.close_connection()


class BaseRpcClients(object):
    def __init__(self, servers):
        self.servers = servers
        self.clients = [BaseRpcClient(server) for server in servers]
        self.results = {}

    def open_threads(self, targets, argss=None, indices=None):
        if indices is None:
            indices = xrange(len(self.servers))
        if argss is None:
            argss = [()] * len(indices)
        threads = []
        for i in xrange(len(indices)):
            thread = threading.Thread(target=targets[i],
                                      args=argss[i])
            thread.start()
            threads.append(thread)
        [thread.join() for thread in threads]

    def _execute(self, index, procedure):
        log_debug("_execute %s" % str(procedure))
#        if self.clients[index].is_connected():
        self.results[index] = self.clients[index].execute(procedure)
#        else:
#            log_warn("The connection to client %d has been lost" % index)
#            self.results[index] = None

    def execute(self, procedures, indices=None):
        """
        Makes simultaneously (multithreading) several calls to different
        RPC servers.
        """
        if indices is None:
            indices = xrange(len(self.servers))
        results = []
        self.exceptions = []
        self.open_threads([self._execute] * len(indices),
                          [(indices[i], procedures[i]) for i in
                                xrange(len(indices))],
                          indices)

#        if len(self.exceptions)>0:
#            raise Exception("\n".join(self.exceptions))
        for i in indices:
            if i in self.results.keys():
                result = self.results[i]
            else:
                result = None
            results.append(result)
        return results

    def is_connected(self):
        return [c.is_connected() for c in self.clients]

    def connect(self, trials=None):
        self.open_threads([client.connect for client in self.clients],
                          argss=[(trials,)] * len(self.clients))

    def disconnect(self):
        self.open_threads([client.disconnect for client in self.clients])

    def close_server(self):
        self.open_threads([client.close_server for client in self.clients])


def open():
    import playdoh
    scriptdir = os.path.join(os.path.dirname(playdoh.__file__), 'scripts')
    os.chdir(scriptdir)
    cpu = playdoh.MAXCPU
    gpu = playdoh.get_gpu_count()
    port = playdoh.DEFAULT_PORT
    os.system("python open.py %d %d %d" % (cpu, gpu, port))


def kill_linux():
    """
    Kill all Python processes except the RestartRpcServer
    """
    pid = str(os.getpid())
    cmd = "ps -ef | grep python | awk '{print $2}'"
    r = commands.getoutput(cmd)
    r = r.split('\n')
    if pid in r:
        r.remove(pid)
    n = len(r)
    r = ' '.join(r)
    cmd = 'kill %s' % r
    os.system(cmd)
    return n


def kill_windows():
    pid = str(os.getpid())
    cmd = ['tasklist', "/FO", "LIST", "/FI", "IMAGENAME eq python.exe"]
    r = Popen(cmd, stdout=PIPE).communicate()[0]
    r = r.split("\n")
    ps = []
    for line in r:
        if line[:3] == 'PID':
            ps.append(line[4:].strip())
    if pid in ps:
        ps.remove(pid)
    n = len(ps)
    args = " ".join(["/pid %s" % p for p in ps])
    cmd = "taskkill /F %s" % args
    os.system(cmd)
    return n


def kill():
    if os.name == 'posix':
                n = kill_linux()
    else:
        n = kill_windows()
    return n


class RestartRpcServer(BaseRpcServer):
    def initialize(self):
        log_info("waiting to kill...")
        self.thread = None

    def _open(self):
        open()

    def open(self):
        self.thread = threading.Thread(target=self._open)
        self.thread.start()

    def process(self, client, procedure):
        n = None
        if procedure == 'kill':
            n = kill()
            log_info("%d processes killed" % n)
        elif procedure == 'open':
            n = None
            self.open()
        elif procedure == 'restart':
            n = kill()
            log_info("%d processes killed" % n)
            self.open()
        return n

    def shutdown(self):
        pass


def open_restart_server():
    RestartRpcServer(port=27182).listen()


def restart(server=None, procedure=None):
    if server is None:
        server = 'localhost'
    if procedure is None:
        procedure = 'restart'
    c = BaseRpcClient((server, 27182))
    c.execute(procedure)

########NEW FILE########
__FILENAME__ = cache
import os.path

# creates the user directory
BASEDIR = os.path.join(os.path.realpath(os.path.expanduser('~')), '.playdoh')
CACHEDIR = os.path.join(BASEDIR, 'cache')
JOBDIR = os.path.join(BASEDIR, 'jobs')

if not os.path.exists(BASEDIR):
    os.mkdir(BASEDIR)

if not os.path.exists(CACHEDIR):
    os.mkdir(CACHEDIR)

if not os.path.exists(JOBDIR):
    os.mkdir(JOBDIR)

########NEW FILE########
__FILENAME__ = cloudpickle
"""
This class is defined to override standard pickle functionality

The goals of it follow:
-Serialize lambdas and nested functions to compiled byte code
-Deal with main module correctly
-Deal with other non-serializable objects

It does not include an unpickler, as standard python unpickling suffices

Copyright (c) 2009 `PiCloud, Inc. <http://www.picloud.com>`_.
All rights reserved.

email: contact@picloud.com

The cloud package is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This package is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this package; if not, see
http://www.gnu.org/licenses/lgpl-2.1.html
"""

import ctypes
import os
import pickle
import struct
import sys
import types
from functools import partial
import itertools
from copy_reg import _extension_registry
#, _inverted_registry, _extension_cache
import new
import dis
import email

#relevant opcodes
STORE_GLOBAL = chr(dis.opname.index('STORE_GLOBAL'))
DELETE_GLOBAL = chr(dis.opname.index('DELETE_GLOBAL'))
LOAD_GLOBAL = chr(dis.opname.index('LOAD_GLOBAL'))
GLOBAL_OPS = [STORE_GLOBAL, DELETE_GLOBAL, LOAD_GLOBAL]

HAVE_ARGUMENT = chr(dis.HAVE_ARGUMENT)
EXTENDED_ARG = chr(dis.EXTENDED_ARG)


try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
#from util import islambda
#from util import xrange_helper
import xrange_helper


def islambda(func):
    return func.func_name == '<lambda>'

# debug variables intended for developer use:
printSerialization = False
printMemoization = False

useForcedImports = True  # Should I use forced imports for tracking?


class CloudPickler(pickle.Pickler):

    dispatch = pickle.Pickler.dispatch.copy()
    savedForceImports = False

    def __init__(self, file, protocol=None, min_size_to_save=0):
        pickle.Pickler.__init__(self, file, protocol)
        self.modules = set()  # set of modules needed to depickle

    # block broken objects
    def save_unsupported(self, obj, pack=None):
        raise pickle.PicklingError("Cannot pickle objects of type %s" %
                type(obj))
    dispatch[buffer] = save_unsupported
    dispatch[types.GeneratorType] = save_unsupported

    # python2.6+ supports slice pickling. some py2.5 extensions might as well.
    # We just test it
    try:
        slice(0, 1).__reduce__()
    except TypeError:  # can't pickle -
        dispatch[slice] = save_unsupported

    # email LazyImporters cannot be saved!
    dispatch[email.LazyImporter] = save_unsupported

    # itertools objects do not pickle!
    for v in itertools.__dict__.values():
        if type(v) is type:
            dispatch[v] = save_unsupported

    def save_dict(self, obj):
        """hack fix
        If the dict is a global, deal with it in a special way
        """
        # print 'saving', obj
        if obj is __builtins__:
            self.save_reduce(_get_module_builtins, (), obj=obj)
        else:
            pickle.Pickler.save_dict(self, obj)
    dispatch[pickle.DictionaryType] = save_dict

    def save_module(self, obj, pack=struct.pack):
        """
        Save a module as an import
        """
        # print 'try save import', obj.__name__
        self.modules.add(obj)
        # self.save_reduce(__import__,(obj.__name__,{},{},['.']), obj=obj)
        self.save_reduce(subimport, (obj.__name__,), obj=obj)
    dispatch[types.ModuleType] = save_module  # new type

    def save_codeobject(self, obj, pack=struct.pack):
        """
        Save a code object
        """
        # print 'try to save codeobj: ', obj
        args = (
            obj.co_argcount, obj.co_nlocals, obj.co_stacksize,
            obj.co_flags, obj.co_code,
            obj.co_consts, obj.co_names, obj.co_varnames,
            obj.co_filename, obj.co_name,
            obj.co_firstlineno, obj.co_lnotab, obj.co_freevars,
            obj.co_cellvars
        )
        self.save_reduce(types.CodeType, args, obj=obj)
    dispatch[types.CodeType] = save_codeobject  # new type

    def save_function(self, obj, name=None, pack=struct.pack):
        """ Registered with the dispatch to handle all function types.

        Determines what kind of function obj is (e.g. lambda, defined at
        interactive prompt, etc) and handles the pickling appropriately.
        """
        write = self.write

        name = obj.__name__
        modname = pickle.whichmodule(obj, name)
        themodule = sys.modules[modname]

        if modname == '__main__':
            themodule = None

        if themodule:
            self.modules.add(themodule)

        # if func is lambda, def'ed at prompt, is in main, or is nested, then
        # we'll pickle the actual function object rather than simply saving a
        # reference (as is done in default pickler), via save_function_tuple.
        if islambda(obj) or obj.func_code.co_filename == '<stdin>' or\
                themodule == None:
            # Force server to import modules that have been imported in main
            modList = None
            if themodule == None and not self.savedForceImports:
                mainmod = sys.modules['__main__']
                if useForcedImports and hasattr(mainmod,
                                                '___pyc_forcedImports__'):
                    modList = list(mainmod.___pyc_forcedImports__)
                self.savedForceImports = True
            self.save_function_tuple(obj, modList)
            return
        else:   # func is nested
            klass = getattr(themodule, name, None)
            if klass is None or klass is not obj:
                self.save_function_tuple(obj, [themodule])
                return

        if obj.__dict__:
            # essentially save_reduce, but workaround needed to avoid recursion
            self.save(_restore_attr)
            write(pickle.MARK + pickle.GLOBAL + modname + '\n' + name + '\n')
            self.memoize(obj)
            self.save(obj.__dict__)
            write(pickle.TUPLE + pickle.REDUCE)
        else:
            write(pickle.GLOBAL + modname + '\n' + name + '\n')
            self.memoize(obj)
    dispatch[types.FunctionType] = save_function

    def save_function_tuple(self, func, forced_imports):
        """  Pickles an actual func object.

        A func comprises: code, globals, defaults, closure, and dict.  We
        extract and save these, injecting reducing functions at certain points
        to recreate the func object.  Keep in mind that some of these pieces
        can contain a ref to the func itself.  Thus, a naive save on these
        pieces could trigger an infinite loop of save's.  To get around that,
        we first create a skeleton func object using just the code (this is
        safe, since this won't contain a ref to the func), and memoize it as
        soon as it's created.  The other stuff can then be filled in later.
        """
        save = self.save
        write = self.write

        # save the modules (if any)
        if forced_imports:
            write(pickle.MARK)
            save(_modules_to_main)
            # print 'forced imports are', forced_imports

            forced_names = map(lambda m: m.__name__, forced_imports)
            save((forced_names,))

            #save((forced_imports,))
            write(pickle.REDUCE)
            write(pickle.POP_MARK)

        code, globals, defaults, closure, dict = \
            CloudPickler.extract_func_data(func)

        save(_fill_function)  # skeleton function updater
        write(pickle.MARK)    # beginning of tuple that _fill_function expects

        # create a skeleton function object and memoize it
        save(_make_skel_func)
        save((code, len(closure)))
        write(pickle.REDUCE)
        self.memoize(func)

        # save the rest of the func data needed by _fill_function
        save(globals)
        save(defaults)
        save(closure)
        save(dict)
        write(pickle.TUPLE)
        write(pickle.REDUCE)  # applies _fill_function on the tuple

    @staticmethod
    def extract_code_globals(co):
        """
        Find all globals names read or written to by codeblock co
        """
        code = co.co_code
        names = co.co_names
        out_names = set()

        n = len(code)
        i = 0
        extended_arg = 0
        while i < n:
            op = code[i]

            i = i + 1
            if op >= HAVE_ARGUMENT:
                oparg = ord(code[i]) + ord(code[i + 1]) * 256 + extended_arg
                extended_arg = 0
                i = i + 2
                if op == EXTENDED_ARG:
                    extended_arg = oparg * 65536L
                if op in GLOBAL_OPS:
                    out_names.add(names[oparg])
        #print 'extracted', out_names, ' from ', names
        return out_names

    @staticmethod
    def extract_func_data(func):
        """
        Turn the function into a tuple of data necessary to recreate it:
            code, globals, defaults, closure, dict
        """
        code = func.func_code

        # extract all global ref's
        func_global_refs = CloudPickler.extract_code_globals(code)
        if code.co_consts:   # see if nested function have any global refs
            for const in code.co_consts:
                if type(const) is types.CodeType and const.co_names:
                    func_global_refs = func_global_refs.union(
                                    CloudPickler.extract_code_globals(const))
        # process all variables referenced by global environment
        globals = {}
        for var in func_global_refs:
            # Some names, such as class functions are not global - we don't
            # need them
            # PEP8 CHANGE:
            # if func.func_globals.has_key(var):
            if var in func.func_globals:
                globals[var] = func.func_globals[var]

        # defaults requires no processing
        defaults = func.func_defaults

        def get_contents(cell):
            try:
                return cell.cell_contents
            except ValueError:  # cell is empty error on not yet assigned
                raise pickle.PicklingError('Function to be pickled has free \
                    variables that are referenced before assignment in \
                    enclosing scope')

        # process closure
        if func.func_closure:
            closure = map(get_contents, func.func_closure)
        else:
            closure = []

        # save the dict
        dict = func.func_dict

        if printSerialization:
            outvars = ['code: ' + str(code)]
            outvars.append('globals: ' + str(globals))
            outvars.append('defaults: ' + str(defaults))
            outvars.append('closure: ' + str(closure))
            print 'function ', func, 'is extracted to: ', ', '.join(outvars)

        return (code, globals, defaults, closure, dict)

    def save_global(self, obj, name=None, pack=struct.pack):
        write = self.write
#        memo = self.memo

        if name is None:
            name = obj.__name__

        modname = getattr(obj, "__module__", None)
        if modname is None:
            modname = pickle.whichmodule(obj, name)

        try:
            __import__(modname)
            themodule = sys.modules[modname]
        except (ImportError, KeyError, AttributeError):  # should never occur
            raise pickle.PicklingError(
                "Can't pickle %r: Module %s cannot be found" %
                (obj, modname))

        if modname == '__main__':
            themodule = None

        if themodule:
            self.modules.add(themodule)

        sendRef = True
        typ = type(obj)
        # print 'saving', obj, typ
        try:
            try:  # Deal with case when getattribute fails with exceptions
                klass = getattr(themodule, name)
            except (AttributeError):
                if modname == '__builtin__':  # new.* are misrepeported
                    modname = 'new'
                    __import__(modname)
                    themodule = sys.modules[modname]
                    try:
                        klass = getattr(themodule, name)
                    except AttributeError:
                        # print themodule, name, obj, type(obj)
                        raise pickle.PicklingError("Can't pickle builtin %s" %
                            obj)
                else:
                    raise

        except (ImportError, KeyError, AttributeError):
            if typ == types.TypeType or typ == types.ClassType:
                sendRef = False
            else:  # we can't deal with this
                raise
        else:
            if klass is not obj and (typ == types.TypeType or\
                    typ == types.ClassType):
                sendRef = False
        if not sendRef:
            # note: Third party types might crash this - add better checks!
            d = dict(obj.__dict__)  # copy dict proxy to a dict
            d.pop('__dict__', None)
            d.pop('__weakref__', None)
            self.save_reduce(type(obj), (obj.__name__, obj.__bases__,
                                   d), obj=obj)
            return

        if self.proto >= 2:
            code = _extension_registry.get((modname, name))
            if code:
                assert code > 0
                if code <= 0xff:
                    write(pickle.EXT1 + chr(code))
                elif code <= 0xffff:
                    write("%c%c%c" % (pickle.EXT2, code & 0xff, code >> 8))
                else:
                    write(pickle.EXT4 + pack("<i", code))
                return

        write(pickle.GLOBAL + modname + '\n' + name + '\n')
        self.memoize(obj)
    dispatch[types.ClassType] = save_global
    dispatch[types.BuiltinFunctionType] = save_global
    dispatch[types.TypeType] = save_global

    def save_instancemethod(self, obj):
        # Memoization rarely is ever useful due to python bounding
        self.save_reduce(types.MethodType, (obj.im_func,
                                            obj.im_self, obj.im_class),
                                            obj=obj)
    dispatch[types.MethodType] = save_instancemethod

    def save_inst(self, obj):
        # Hack to detect PIL Image instances without importing Imaging
        if hasattr(obj, 'im') and hasattr(obj, 'palette') and \
                'Image' in obj.__module__:
            self.save_image(obj)
        else:
            pickle.Pickler.save_inst(self, obj)
    dispatch[types.InstanceType] = save_inst

    def save_xrange(self, obj):
        """Save an xrange object in python 2.5
        Python 2.6 supports this natively
        Code based on a stackoverflow answer from Denis Otkidach"""
        c_range_obj = xrange_helper.xrangeToCType(obj)
        self.save_reduce(_build_xrange, (c_range_obj.start, c_range_obj.step,
                                        c_range_obj.len))

    # python2.6+ supports xrange pickling. some py2.5 extensions might as well.
    # We just test it
    try:
        xrange(0).__reduce__()
    except TypeError:  # can't pickle -- use PiCloud pickler
        dispatch[xrange] = save_xrange

    def save_partial(self, obj):
        """Partial objects do not serialize correctly in python2.x -- \
            this fixes the bugs"""
        self.save_reduce(_genpartial, (obj.func, obj.args, obj.keywords))

    dispatch[partial] = save_partial

    def save_file(self, obj):
        """Save a file"""
        import StringIO as pystringIO  # we can't use cStringIO as it lacks\
            # the name attribute
        from ..transport.adapter import SerializingAdapter

        if not hasattr(obj, 'name') or  not hasattr(obj, 'mode'):
            raise pickle.PicklingError("Cannot pickle files that do not map to\
                    an actual file")
        if obj.name == '<stdout>':
            return self.save_reduce(getattr, (sys, 'stdout'), obj=obj)
        if obj.name == '<stderr>':
            return self.save_reduce(getattr, (sys, 'stderr'), obj=obj)
        if obj.name == '<stdin>':
            raise pickle.PicklingError("Cannot pickle standard input")
        if  hasattr(obj, 'isatty') and obj.isatty():
            raise pickle.PicklingError("Cannot pickle files that map to\
                    tty objects")
        if 'r' not in obj.mode:
            raise pickle.PicklingError("Cannot pickle files that are not\
                    opened for reading")
        name = obj.name
        try:
            fsize = os.stat(name).st_size
        except OSError:
            raise pickle.PicklingError("Cannot pickle file %s as it cannot\
                be stat" % name)

        if obj.closed:
            # create an empty closed string io
            retval = pystringIO.StringIO("")
            retval.close()
        elif not fsize:  # empty file
            retval = pystringIO.StringIO("")
            try:
                tmpfile = file(name)
                tst = tmpfile.read(1)
            except IOError:
                raise pickle.PicklingError("Cannot pickle file %s as it cannot\
                    be read" % name)
            tmpfile.close()
            if tst != '':
                raise pickle.PicklingError("Cannot pickle file %s as it does\
                    not appear to map to a physical, real file" % name)
        elif fsize > SerializingAdapter.maxTransmitData:
            raise pickle.PicklingError("Cannot pickle file %s as it exceeds\
                        cloudconf.py's max_transmit_data of %d" %
                                    (name, SerializingAdapter.maxTransmitData))
        else:
            try:
                tmpfile = file(name)
                contents = tmpfile.read(SerializingAdapter.maxTransmitData)
                tmpfile.close()
            except IOError:
                raise pickle.PicklingError("Cannot pickle file %s as it \
                        cannot be read" % name)
            retval = pystringIO.StringIO(contents)
            curloc = obj.tell()
            retval.seek(curloc)

        retval.name = name
        self.save(retval)  # save stringIO
        self.memoize(obj)

    dispatch[file] = save_file
    """Special functions for Add-on libraries"""

    """numpy ufunc hack"""
    try:
        import numpy
        numpy_tst_mods = ['numpy', 'scipy.special']

        def save_ufunc(self, obj):
            name = obj.__name__
            for tst_mod_name in self.numpy_tst_mods:
                tst_mod = sys.modules.get(tst_mod_name, None)
                if tst_mod:
                    if name in tst_mod.__dict__:
                        self.save_reduce(_getobject, (tst_mod_name, name))
                        return
            raise pickle.PicklingError('cannot save %s. Cannot resolve\
                what module it is defined in' % str(obj))

        dispatch[numpy.ufunc] = save_ufunc

    except ImportError:
        pass

    """Python Imaging Library"""
    def save_image(self, obj):
        if not obj.im and obj.fp and 'r' in obj.fp.mode and obj.fp.name \
            and not obj.fp.closed and (not hasattr(obj, 'isatty') or \
                    not obj.isatty()):
            # if image not loaded yet -- lazy load
            self.save_reduce(_lazyloadImage, (obj.fp,), obj=obj)
        else:
            # image is loaded - just transmit it over
            self.save_reduce(_generateImage, (obj.size, obj.mode,
                                              obj.tostring()), obj=obj)

    """
    def memoize(self, obj):
        pickle.Pickler.memoize(self, obj)
        if printMemoization:
            print 'memoizing ' + str(obj)
    """


# Shorthands for legacy support


def dump(obj, file, protocol=2):
    CloudPickler(file, protocol).dump(obj)


def dumps(obj, protocol=2):
    file = StringIO()

    cp = CloudPickler(file, protocol)
    cp.dump(obj)

    # print 'cloud dumped', str(obj), str(cp.modules)

    return file.getvalue()


# hack for __import__ not working as desired
def subimport(name):
    __import__(name)
    return sys.modules[name]


# restores function attributes
def _restore_attr(obj, attr):
    for key, val in attr.items():
        setattr(obj, key, val)
    return obj


def _get_module_builtins():
    return pickle.__builtins__


def _modules_to_main(modList):
    """Force every module in modList to be placed into main"""
    if not modList:
        return

    main = sys.modules['__main__']
    for modname in modList:
        if type(modname) is str:
            try:
                mod = __import__(modname)
            except ImportError, i:
                sys.stderr.write('warning: could not import %s\n.\
            Your function may unexpectedly error due to this import failing; \
A version mismatch is likely.  Specific error was %s\n\n' % (modname, str(i)))
            else:
                setattr(main, mod.__name__, mod)
        else:
            # REVERSE COMPATIBILITY FOR CLOUD CLIENT 1.5 (WITH EPD)
            # In old version actual module was sent
            setattr(main, modname.__name__, modname)


# object generators:
def _build_xrange(start, step, len):
    """Built xrange explicitly"""
    baserange = xrange(0)
    c_range_obj = xrange_helper.xrangeToCType(baserange)
    c_range_obj.start = start
    c_range_obj.step = step
    c_range_obj.len = len
    return baserange


def _genpartial(func, args, kwds):
    if not args:
        args = ()
    if not kwds:
        kwds = {}
    return partial(func, *args, **kwds)


def _fill_function(func, globals, defaults, closure, dict):
    """ Fills in the rest of function data into the skeleton function object
        that were created via _make_skel_func().
         """
    func.func_globals.update(globals)
    func.func_defaults = defaults
    func.func_dict = dict

    if len(closure) != len(func.func_closure):
        raise pickle.UnpicklingError("closure lengths don't match up")
    for i in range(len(closure)):
        _change_cell_value(func.func_closure[i], closure[i])

    return func


def _make_skel_func(code, num_closures):
    """ Creates a skeleton function object that contains just the provided
        code and the correct number of cells in func_closure.  All other
        func attributes (e.g. func_globals) are empty.
    """
    # build closure (cells):
    cellnew = ctypes.pythonapi.PyCell_New
    cellnew.restype = ctypes.py_object
    cellnew.argtypes = (ctypes.py_object,)
    dummy_closure = tuple(map(lambda i: cellnew(None), range(num_closures)))

    return types.FunctionType(code, {'__builtins__': __builtins__},
                              None, None, dummy_closure)


# this piece of opaque code is needed below to modify 'cell' contents
cell_changer_code = new.code(
    1, 1, 2, 0,
    ''.join([
        chr(dis.opmap['LOAD_FAST']), '\x00\x00',
        chr(dis.opmap['DUP_TOP']),
        chr(dis.opmap['STORE_DEREF']), '\x00\x00',
        chr(dis.opmap['RETURN_VALUE'])
    ]),
    (), (), ('newval',), '<nowhere>', 'cell_changer', 1, '', ('c',), ()
)


def _change_cell_value(cell, newval):
    """ Changes the contents of 'cell' object to newval """
    return new.function(cell_changer_code, {}, None, (), (cell,))(newval)


"""Constructors for 3rd party libraries"""


def _getobject(modname, attribute):
    mod = __import__(modname)
    return mod.__dict__[attribute]


def _generateImage(size, mode, str_rep):
    """Generate image from string representation"""
    import Image
    i = Image.new(mode, size)
    i.fromstring(str_rep)
    return i


def _lazyloadImage(fp):
    import Image
    fp.seek(0)  # works in almost any case
    return Image.open(fp)

########NEW FILE########
__FILENAME__ = codedependency
"""
This effectively  walks through module import statements recursively to find
all modules that a given one depends on.
It furthermore manages the packaging of newly found dependencies when requested

ISSUES: For speed, this does not use pathhooks unless imp.find_module fails.
Consequently, if modules can be found in two different sys.path entries,
the order
processed by this module may differ from the python import system
Entirely arbitrary pathhooks are not supported for now - only ZipImporter
    (specifically importers with a archive attribute)

There are some hacks to deal with transmitting archives -- we coerce archives
to be stored
to cloud.archives/archive.
An eventual goal is to clean up the hackish pathhook support code

Copyright (c) 2009 `PiCloud, Inc. <http://www.picloud.com>`_.
All rights reserved.

email: contact@picloud.com

The cloud package is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This package is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this package; if not, see
http://www.gnu.org/licenses/lgpl-2.1.html
"""

from __future__ import with_statement
import os
import sys
import modulefinder
import imp
import marshal
import dis

#from ..serialization import cloudpickle
import cloudpickle
import logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s,%(msecs)03d  %(levelname)-8s  \
                        %(module)-16s  L:%(lineno)03d  P:%(process)-4d  \
                        T:%(thread)-4d  %(message)s",
                    datefmt='%H:%M:%S')
cloudLog = logging.getLogger(__name__)

#from .. import cloudconfig as cc
#cloudLog = logging.getLogger("Cloud.Transport")

LOAD_CONST = chr(dis.opname.index('LOAD_CONST'))
IMPORT_NAME = chr(dis.opname.index('IMPORT_NAME'))
STORE_NAME = chr(dis.opname.index('STORE_NAME'))
STORE_GLOBAL = chr(dis.opname.index('STORE_GLOBAL'))
STORE_OPS = [STORE_NAME, STORE_GLOBAL]
HAVE_ARGUMENT = chr(dis.HAVE_ARGUMENT)

ZIP_IMPORT = -9  # custom imp-like type code


class DependencyManager(modulefinder.ModuleFinder):
    """
    Based off of module finder.

    Features:
    -IgnoreList to ignore base python packages for performance purposes
    -Timestamp tracking
    -'Snapshots' to determine new modules
    -Warnings on using custom C extensions

    Note: This is not thread safe: The user of this is responsible for
    locking it down

    TODO: Be smart with using import hooks (get_code)
    """

    @staticmethod
    def formatIgnoreList(unformattedList):
        """Format the ignore list"""

        builtins = sys.builtin_module_names

        ignoreList = {}
        for module in unformattedList:
            modname = module.strip()
            if modname[0] == '#' or modname[0] == ';':
                continue
            modname = modname.split('.')

            if modname[-1] == '*':
                ignoreList[tuple(modname[:-1])] = True
            else:
                # set to False if .* isn't required
                ignoreList[tuple(modname)] = True

        #add builtins:
        for builtin in builtins:
            ignoreList[(builtin, )] = True

        return ignoreList

    def __init__(self, path=sys.path, debug=0, excludes=[], replace_paths=[]):
        modulefinder.ModuleFinder.__init__(self, path, debug, None,
                                           replace_paths)
        self.ignoreList = self.formatIgnoreList(excludes)
        self.lastSnapshot = set()  # tracking
        self.transitError = set()  # avoid excessive extension warnings

        # analyze main which is not transmitted
        m = sys.modules['__main__']
        if hasattr(m, '__file__') and cloudpickle.useForcedImports:
            self.inject_module(m)
            # if main imports a.b we might not see that b has been loaded
            # The below is a hack to detect this case:
            checkModules = self.modules.keys() + self.get_ignored_modules()
            for mod in checkModules:
                self.msgout(2, "inspect", m)
                if '.' in mod:
                    loadedmod = sys.modules.get(mod)
                    # if mod is not loaded, import is triggered in a function:
                    if loadedmod:
                        if not hasattr(m, '___pyc_forcedImports__'):
                            m.___pyc_forcedImports__ = set()
                        m.___pyc_forcedImports__.add(loadedmod)

    def shouldIgnore(self, modname):
        """Check ignoreList to determine if this module should
            not be processed"""
        modname = tuple(modname.split('.'))

        if modname in self.ignoreList:
            return True
        for i in range(1, len(modname)):
            tst = modname[0:-i]
            # print 'doing test', tst
            val = self.ignoreList.get(tst)
            if val:  # Must be true
                return True
        return False

    def load_package(self, fqname, pathname, archive_name=None):
        """Fix bug with not passing parent into find_module"""
        self.msgin(2, "load_package", fqname, pathname)
        newname = modulefinder.replacePackageMap.get(fqname)
        if newname:
            fqname = newname

        if archive_name:  # part of an archive
            m = self.add_module(fqname,
                                filename=archive_name,
                                path=[pathname] + \
                                modulefinder.packagePathMap.get(fqname,
                                                                []),
                                is_archive=True)
        else:
            # As per comment in modulefinder, simulate runtime __path__
            # additions.
            m = self.add_module(fqname,
                                filename=pathname + '/__init__.py',
                                path=[pathname] + \
                                    modulefinder.packagePathMap.get(fqname,
                                                                    []))

        # Bug fix.  python2.6 modulefinder doesn't pass parent to find_module
        fp, buf, stuff = self.find_module("__init__", m.__path__, parent=m)

        self.load_module(fqname, fp, buf, stuff)
        self.msgout(2, "load_package ->", m)
        return m

    def inject_module(self, mod):
        """High level module adding.
        This adds an actual module from sys.modules into the finder
        """

        mname = mod.__name__
        if mname in self.modules:
            return
        if self.shouldIgnore(mname):
            return

        if mname == '__main__':  # special case
            searchnames = []
            dirs, mod = os.path.split(mod.__file__)
            searchname = mod.split('.', 1)[0]  # extract fully qualified name
        else:
            searchnames = mname.rsplit('.', 1)
            # must load parents first...
            pkg = searchnames[0]

            if len(searchnames) > 1 and pkg not in self.modules:
                self.inject_module(sys.modules[pkg])

            searchname = searchnames[-1]
        if len(searchnames) > 1:  # this module has a parent - resolve it
            path = sys.modules[pkg].__path__
        else:
            path = None

        try:
            fp, pathname, stuff = self.find_module(searchname, path)
            self.load_module(mname, fp, pathname, stuff)
        except ImportError:  # Ignore import errors
            pass

    def add_module(self, fqname, filename, path=None, is_archive=False):
        """Save timestamp here"""
        if fqname in self.modules:
            return self.modules[fqname]
        # print 'pre-adding %s' % fqname
        if not filename:  # ignore any builtin or extension
            return

        if is_archive:
            # module's filename is set to the actual archive
            relfilename = os.path.split(filename)[1]
            # cloudpickle needs to know about this to deserialize correctly:
        else:
            # get relative path:
            numsplits = fqname.count('.') + 1
            relfilename = ""
            absfilename = filename
            for i in xrange(numsplits):
                absfilename, tmp = os.path.split(absfilename)
                relfilename = tmp + '/' + relfilename
                if '__init__' in tmp:
                    # additional split as this is a package and
                    # __init__ is not in fqname
                    absfilename, tmp = os.path.split(absfilename)
                    relfilename = tmp + '/' + relfilename
            relfilename = relfilename[:-1]  # remove terminating /

        self.modules[fqname] = m = modulefinder.Module(fqname,
                                                       relfilename, path)
        # picloud: Timestamp module for update checks
        m.timestamp = long(os.path.getmtime(filename))
        m.is_archive = is_archive
        return m

    """Manually try to find name on sys.path_hooks
    Some code taken from python3.1 implib"""
    def _path_hooks(self, path):
        """Search path hooks for a finder for 'path'.
        """
        hooks = sys.path_hooks
        for hook in hooks:
            try:
                finder = hook(path)
                sys.path_importer_cache[path] = finder
                return finder
            except ImportError:
                continue
        return None

    def manual_find(self, name, path):
        """Load with pathhooks. Return none if fails to load or if default
        importer must be used
        Otherwise returns loader object, path_loader_handles"""
        finder = None
        for entry in path:
            try:
                finder = sys.path_importer_cache[entry]
            except KeyError:
                finder = self._path_hooks(entry)
            if finder:
                loader = finder.find_module(name)
                if loader:
                    return loader, entry
        return None, None  # nothing found!

    def find_module(self, name, path, parent=None):
        """find_module using ignoreList
        TODO: Somehow use pathhooks here
        """
        if parent is not None:
            # assert path is not None
            fullname = parent.__name__ + '.' + name
        else:
            fullname = name
        # print 'test to ignore %s -- %s -- %s' % (fullname, parent, path)

        if self.shouldIgnore(fullname):
            self.msgout(3, "find_module -> Ignored", fullname)
            # PEP8 CHANGE
            raise ImportError(name)

        if path is None:
            if name in sys.builtin_module_names:
                return (None, None, ("", "", imp.C_BUILTIN))

            path = sys.path
        # print 'imp is scanning for %s at %s' % (name, path)
        try:
            return imp.find_module(name, path)
        except ImportError:
            # try path hooks
            loader, ldpath = self.manual_find(name, path)
            if not loader:
                raise
            #We now have a PEP 302 loader object. Internally, we must format it

            if not hasattr(loader, 'archive') or not hasattr(loader,
                                                             'get_code'):
                if fullname not in self.transitError:
                    cloudLog.warn("Cloud cannot transmit python module '%s'.\
                    It needs to be imported by a %s path hook, but such a path\
                    hook \
                    does not provide both the \
                    'archive' and 'get_code' property..  Import errors may\
                    result;\
                    please see PiCloud documentation." % (fullname,
                                                          str(loader)))
                    self.transitError.add(fullname)
                raise

            return (None,  ldpath + '/' + name, (loader, name, ZIP_IMPORT))

    def get_ignored_modules(self):
        """Return list of modules that are used but were ignored"""
        ignored = []
        for name in self.badmodules:
            if self.shouldIgnore(name):
                ignored.append(name)
        return ignored

    def any_missing_maybe(self):
        """Return two lists, one with modules that are certainly missing
        and one with modules that *may* be missing. The latter names could
        either be submodules *or* just global names in the package.

        The reason it can't always be determined is that it's impossible to
        tell which names are imported when "from module import *" is done
        with an extension module, short of actually importing it.

        PiCloud: Use ignoreList
        """
        missing = []
        maybe = []
        for name in self.badmodules:
            if self.shouldIgnore(name):
                continue
            i = name.rfind(".")
            if i < 0:
                missing.append(name)
                continue
            subname = name[i + 1:]
            pkgname = name[:i]
            pkg = self.modules.get(pkgname)
            if pkg is not None:
                if pkgname in self.badmodules[name]:
                    # The package tried to import this module itself and
                    # failed. It's definitely missing.
                    missing.append(name)
                elif subname in pkg.globalnames:
                    # It's a global in the package: definitely not missing.
                    pass
                elif pkg.starimports:
                    # It could be missing, but the package did an "import *"
                    # from a non-Python module, so we simply can't be sure.
                    maybe.append(name)
                else:
                    # It's not a global in the package, the package didn't
                    # do funny star imports, it's very likely to be missing.
                    # The symbol could be inserted into the package from the
                    # outside, but since that's not good style we simply list
                    # it missing.
                    missing.append(name)
            else:
                missing.append(name)
        missing.sort()
        maybe.sort()
        return missing, maybe

    def load_module(self, fqname, fp, pathname, file_info):
        suffix, mode, type = file_info
        #PiCloud: Warn on C extensions and __import_
        self.msgin(2, "load_module", fqname, fp and "fp", pathname)
        if type == ZIP_IMPORT:
            #archive (as suffix) is an PEP 302 importer that implements
            # archive and get_code
            #pathname is used to access the file within the loader
            archive = suffix
            #mode is the actual name we want to read
            name = mode
            if archive.is_package(name):  # use load_package with archive set
                m = self.load_package(fqname, pathname,
                                      archive_name=archive.archive)
                return m
            else:
                try:
                    co = archive.get_code(name)
                except ImportError:
                    cloudLog.warn("Cloud cannot read '%s' within '%s'. \
                        Import errors may result; \
                    please see PiCloud documentation." % (fqname,
                                                          archive.archive))
                    raise
                m = self.add_module(fqname, archive.archive, is_archive=True)
        else:
            if type == imp.PKG_DIRECTORY:
                m = self.load_package(fqname, pathname)
                self.msgout(2, "load_module ->", m)
                return m
            elif type == imp.PY_SOURCE:
                try:
                    co = compile(fp.read() + '\n', pathname, 'exec')
                except SyntaxError:  # compilation fail.
                    cloudLog.warn("Syntax error in %s. Import errors may\
                        occur in rare situations." % pathname)
                    raise ImportError("Syntax error in %s" % pathname)

            elif type == imp.PY_COMPILED:
                if fp.read(4) != imp.get_magic():
                    cloudLog.warn("Magic number on %s is invalid.  Import\
                        errors may occur in rare situations." % pathname)
                    self.msgout(2, "raise ImportError: Bad magic number",
                                pathname)
                    raise ImportError("Bad magic number in %s" % pathname)
                fp.read(4)
                co = marshal.load(fp)
            elif type == imp.C_EXTENSION:
                if fqname not in self.transitError:
                    cloudLog.warn("Cloud cannot transmit python extension\
                        '%s' located at '%s'.  Import errors may result;\
                        please see PiCloud documentation." % (fqname,
                                                              pathname))
                    self.transitError.add(fqname)
                raise ImportError(fqname)
            else:
                co = None
            m = self.add_module(fqname, filename=pathname)
        if co:
            if self.replace_paths:
                co = self.replace_paths_in_code(co)
            m.__code__ = co
            names = co.co_names
            if names and '__import__' in names:
                #PiCloud: Warn on __import__
                    cloudLog.warn('__import__ found within %s. Cloud cannot\
                    follow these \
                    dependencies. You MAY see importerror cloud exceptions.\
                    For more information,\
                    consult the PiCloud manual'
                    % fqname)
            self.scan_code(co, m)
        self.msgout(2, "load_module ->", m)
        return m

    def getUpdatedSnapshot(self):
        """Return any new myMods values since this was last called"""

        outList = []
        for modname, modobj in self.modules.items():
            if modname not in self.lastSnapshot:
                if modobj.is_archive:  # check if archive has already been sent
                    archive = modobj.__file__
                    if archive in self.lastSnapshot:
                        continue
                    else:
                        self.lastSnapshot.add(archive)
                outList.append((modobj.__file__, modobj.timestamp,
                                modobj.is_archive))
                self.lastSnapshot.add(modname)
        return outList


class FilePackager(object):
    """This class is responsible for the packaging of files"""
    """This is not thread safe"""

    fileCollection = None
    ARCHIVE_PATH = 'cloud.archive/'  # location where archives are extracted

    def __init__(self, path_infos=None):
        """path_infos is a list of (paths relative to site-packages,
        archive)"""
        self.fileCollection = {}
        if path_infos:
            for relPath, archive in path_infos:
                if archive:
                    self.addArchive(relPath)
                else:
                    self.addRelativePath(relPath)

    def addArchive(self, archive_name):
        for site in sys.path:
            if site.endswith(archive_name):
                self.fileCollection[self.ARCHIVE_PATH + archive_name] = site

    def addRelativePath(self, relPath):
        """Add a file by relative path to the File Transfer"""
        for site in sys.path:
            if site != '':
                site += '/'
            tst = os.path.join(site, relPath.encode())
            if os.path.exists(tst):
                self.fileCollection[relPath] = tst
                return
        from ..cloud import CloudException
        raise CloudException('FilePackager: %s not found on sys.path' %
            relPath)

    def getTarball(self):
        try:
            from cStringIO import StringIO
        except ImportError:
            from StringIO import StringIO
        import tarfile

        outfile = StringIO()
        tfile = tarfile.open(name='transfer.tar', fileobj=outfile, mode='w')
        tfile.dereference = True

        for arcname, fname in self.fileCollection.items():
            tfile.add(name=fname, arcname=arcname, recursive=False)
        tfile.close()

        return outfile.getvalue()

########NEW FILE########
__FILENAME__ = codehandler
from ..rpc import *
from ..filetransfer import *
from ..cache import *
from ..debugtools import *
import inspect
import os
import os.path
import sys
import cPickle
import imp
import hashlib
from cloudpickle import dumps, dump


SYSPATH = sys.path[:]


__all__ = ['PicklableClass', 'pickle_class', 'send_dependencies', 'dump']


class PicklableClass(object):
    """
    Makes a class picklable and allows the creation of an instance of
    this class
    on a remote computer. The source code of the class is saved in a string
    and recorded at runtime on the file system before being dynamically
    imported.
    This basic class doesn't handle dependencies with external files.
    """
    codedir = CACHEDIR

    def __init__(self, myclass):
        self.__name__ = self.classname = myclass.__name__
        self.pkl = dumps(myclass)
        try:
            self.source = inspect.getsource(myclass).strip()
        except:
            log_debug("could not get the source code of the function or \
                class <%s>" % self.__name__)
            self.source = ""
        sha = hashlib.sha1()
        sha.update(self.source)
#        sha.update(str(random.random())) # HACK to avoid conflicts between
#        local and remote scripts
        self.hash = sha.hexdigest()
        self.isfunction = inspect.isfunction(myclass)
        if self.isfunction:
            self.arglist = inspect.getargspec(myclass)[0]
        self.distant_dir = os.path.join(self.codedir, self.hash)
        self.codedependencies = []
#        self.isloaded = False

    def set_code_dependencies(self, codedependencies=[]):
        self.codedependencies = codedependencies

    def load_pkl(self):
        global SYSPATH
        sys.path = SYSPATH[:]
        log_debug("Adding directory <%s> to sys.path" % self.distant_dir)
        sys.path.append(self.distant_dir)
#        log_debug(sys.path)
#        self.isloaded = True

    def load_modules(self):
        """
        Loads the dependencies
        """
        loadedmodules = {}
        for m in self.codedependencies:
            name = m
            name = name.replace('.py', '')
            name = name.replace('//', '.')
            name = name.replace('/', '.')
            name = name.replace('\\\\', '.')
            name = name.replace('\\', '.')
            loadedmodules[name] = imp.load_source(name,
                                            os.path.join(self.distant_dir, m))
        return loadedmodules

    def __call__(self, *args, **kwds):
        """
        Instantiates an object of the class.
        """
#        if not self.isloaded:
        self.load_pkl()
        self.load_modules()
        myclass = cPickle.loads(self.pkl)
        return myclass(*args, **kwds)


def get_dirname(myclass):
    modulename = myclass.__module__
    module = sys.modules[modulename]
    if hasattr(module, '__file__'):
        # path of the file where the class is defined
        path = os.path.realpath(module.__file__)
    else:
        # otherwise : current path
        path = os.path.realpath(os.getcwd())
    dirname, filename = os.path.split(path)
    return dirname


def get_dependencies(myclass, dirname=None):
    if dirname is None:
        dirname = get_dirname(myclass)
    filelist = []
    for dir, dirnames, filenames in os.walk(dirname):
        for name in filenames:
            filename = os.path.realpath(name)
            ext = os.path.splitext(filename)[1]
            if ext == '.py':
                filelist.append(os.path.join(dir, name))
    return filelist


def pickle_class(myclass):
    return PicklableClass(myclass)


def send_dependencies(servers, myclass, dependencies=[]):
    dirname = get_dirname(myclass)
    pklclass = pickle_class(myclass)
#    if dependencies is None:
#        dependencies = get_dependencies(myclass, dirname)
    if dependencies is None:
        dependencies = []
    dep = []
    if len(dependencies) > 0:
        to_filenames = [os.path.join(pklclass.distant_dir,
                                     os.path.relpath(filename, dirname))\
                                     for filename in dependencies]
        dep = [os.path.relpath(filename, dirname) for filename in dependencies]
        log_info("Sending code dependencies (%d file(s))" % len(to_filenames))
        send_files(servers, dependencies, to_filenames)
    pklclass.set_code_dependencies(dep)
    return pklclass

########NEW FILE########
__FILENAME__ = xrange_helper
"""
XRange serialization routines
CTypes Extraction code based on a stack overflow answer by Denis Otkidach

Copyright (c) 2009 `PiCloud, Inc. <http://www.picloud.com>`_.
All rights reserved.

email: contact@picloud.com

The cloud package is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This package is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this package; if not, see
http://www.gnu.org/licenses/lgpl-2.1.html
"""

import ctypes


PyObject_HEAD = [('ob_refcnt', ctypes.c_size_t),
                 ('ob_type', ctypes.c_void_p)]


class XRangeType(ctypes.Structure):
    _fields_ = PyObject_HEAD + [
        ('start', ctypes.c_long),
        ('step', ctypes.c_long),
        ('len', ctypes.c_long),
    ]


def xrangeToCType(xrangeobj):
    """Cast a xrange to a C representation of it
    Fields modified in the C Representation effect the xrangeobj
    """
    return ctypes.cast(ctypes.c_void_p(id(xrangeobj)),
                                         ctypes.POINTER(XRangeType)).contents


"""Encoding (generally for placing within a JSON object):"""


def encodeMaybeXrange(obj, allowLists=True):
    """Encode an object that might be an xrange
    Supports lists (1 level deep) as well"""
    if isinstance(obj, xrange):
        c_xrange = xrangeToCType(obj)
        return ['xrange', c_xrange.start, c_xrange.step, c_xrange.len]
    if allowLists and isinstance(obj, list):
        return [encodeMaybeXrange(elm, allowLists=False) for elm in obj]
    return obj


def decodeMaybeXrange(obj, allowLists=True):
    """Decode a JSON-encoded object that might be an xrange"""
    if isinstance(obj, list):
        if len(obj) == 4 and obj[0] == 'xrange':  # an xrange object
            outrange = xrange(0)
            c_xrange = xrangeToCType(outrange)  # get pointer
            c_xrange.start = obj[1]
            c_xrange.step = obj[2]
            c_xrange.len = obj[3]
            return outrange
        elif allowLists:  # decode internal xranges
            return [decodeMaybeXrange(elm, allowLists=False) for elm in obj]
    return obj


def decodeXrangeList(obj):
    """Decode a list of elements and encoded xranges into a single list"""
    # outer layer might be an xrange
    obj = decodeMaybeXrange(obj, allowLists=False)
    if isinstance(obj, xrange):
        return list(obj)  # convert to list
    outlst = []
    for elem in obj:
        if isinstance(elem, list) and len(elem) == 4 and elem[0] == 'xrange':
            outlst.extend(decodeMaybeXrange(elem, allowLists=False))
        else:
            outlst.append(elem)
    return outlst


"""Support for piece-wise xranges - effectively a list of xranges"""


class piecewiseXrange(list):
    def __init__(self):
        self._xrangeMode = False

    def toXrangeMode(self):
        """Turn on xrange iterator"""
        self._xrangeMode = True

    def myIter(self):
        """Ideally, this would overload __iter__, but that presents
        massive pickling issues"""
        if self._xrangeMode:
            return self.xrangeIter
        else:
            return self.__iter__

    def xrangeIter(self):  # use a generator to iterate
        for elm in self.__iter__():
            if isinstance(elm, xrange):
                for subelm in elm:
                    yield subelm
            else:
                yield elm


def xrangeIter(lst):
    """Return correct iterator"""
    if isinstance(lst, piecewiseXrange):
        return lst.myIter()()
    else:
        return lst.__iter__()


def filterXrangeList(func, xrange_list):
    """ Input is a list of xranges and integers
        This returns a similarly formatted output where func(elem)
        evaluates to True
        If an xrange reduces to one element, it just inserts an integer
    """

    if not hasattr(xrange_list, '__iter__') or \
            isinstance(xrange_list, xrange):
        xrange_list = [xrange_list]

    single_range = 2  # if > 0, then outList is just a single xrange
    no_xrange_output = True  # outList has no xranges inserted

    outList = piecewiseXrange()
    for elm in xrange_list:
        if isinstance(elm, (int, long)):  # elm is
            if func(elm):
                outList.append(elm)
                single_range = 0  # individual elements present -
                                  # so not single xrange
        elif isinstance(elm, xrange):
            cxrange = xrangeToCType(elm)
            step = cxrange.step
            basenum = None
            for num in elm:  # iterate through xrange
                if func(num):
                    if basenum == None:
                        basenum = num
                else:
                    if basenum != None:  # push back xrange
                        # only one element: push an integer
                        if num - step == basenum:
                            outList.append(basenum)
                            single_range = 0
                        else:
                            outList.append(xrange(basenum, num, step))
                            single_range -= 1
                            no_xrange_output = False
                        basenum = None
            if basenum != None:  # cleanup
                num += step
                if num - step == basenum:  # only one element: push an integer
                    outList.append(basenum)
                    single_range = 0
                else:
                    outList.append(xrange(basenum, num, step))
                    single_range -= 1
                    no_xrange_output = False
        else:
            raise TypeError('%s (type %s) is not of type int, \
                long or xrange' % (elm, type(elm)))

    if outList:
        if not no_xrange_output:
            if single_range > 0:  # only one xrange appended - just return it
                return outList[0]
            else:
                outList.toXrangeMode()
    return outList


def iterateXRangeLimit(obj, limit):
    """Generate xrange lists based on some limit.
    Assumes obj is an xrange, or xrange list, or None
    May also return single xrange objects"""
    def innerGenerator(obj):
        if not obj:  # empty list/non case
            yield obj
            return

        if isinstance(obj, xrange):
            if len(obj) <= limit:
                yield obj
                return
            # use default algorithm if longer
            obj = [obj]

        # main algorithm
        outlist = []
        cnt = 0  # number of items appended
        for xr in obj:
            if isinstance(xr, (int, long)):
                outlist.append(xr)
                cnt += 1
                if cnt >= limit:
                    yield outlist
                    outlist = []
                    cnt = 0
            elif isinstance(xr, xrange):
                while True:
                    if len(xr) + cnt <= limit:
                        outlist.append(xr)
                        cnt += len(xr)
                        break
                    else:  # break apart xrange
                        oldlen = len(xr)
                        allowed = limit - cnt
                        c_xrange = xrangeToCType(xr)
                        breakpoint = c_xrange.start + c_xrange.step * allowed
                        to_app = xrange(c_xrange.start, breakpoint,\
                                        c_xrange.step)
                        outlist.append(to_app)
                        yield outlist
                        outlist = []
                        cnt = 0
                        xr = xrange(breakpoint, breakpoint + \
                        (oldlen - allowed) * c_xrange.step, c_xrange.step)
                if len(outlist) >= limit:
                    yield outlist
                    outlist = []

            else:
                raise TypeError('%s (type %s) is not of type int,\
                    long or xrange' % (xr, type(xr)))
        if outlist:
            yield outlist
    return innerGenerator(obj)

"""
Quick unit test
(TODO: Move to unit tests)
"""

if __name__ == '__main__':

    for m in [xrange(0, 10, 2), xrange(0, 1), xrange(0), xrange(0, -2),
                                    xrange(0, 6), xrange(0, 7, 3)]:
        me = encodeMaybeXrange(m)
        n = decodeMaybeXrange(me)
        print m, me, n

        #split
        print list(iterateXRangeLimit(m, 1000))
        print list(iterateXRangeLimit(m, 3))
        print [list(x[0]) if type(x) is list else x \
            for x in iterateXRangeLimit(m, 3)]

    xrl = filterXrangeList(lambda x: x % 10, xrange(10, 100))
    print xrl

    lmt = list(iterateXRangeLimit(xrl, 15))
    print lmt

    lmt_read = [[list(x) for x in y] for y in lmt]
    lmt2 = [reduce(lambda x, y: x + y, x) for x in lmt_read]
    print lmt2

    lenz = [len(x) for x in lmt2]
    print lenz

    print list(iterateXRangeLimit(range(25), 13))

########NEW FILE########
__FILENAME__ = connection
from debugtools import *
from userpref import *
from multiprocessing.connection import Listener, Client, AuthenticationError
import cPickle
import time
import socket


BUFSIZE = 1024 * 32
try:
    LOCAL_IP = socket.gethostbyname(socket.gethostname())
except:
    LOCAL_IP = '127.0.0.1'


__all__ = ['accept', 'connect', 'LOCAL_IP']


class Connection(object):
    """
    Handles chunking and compression of data.

    To minimise data transfers between machines, we can use data compression,
    which this Connection handles automatically.
    """
    def __init__(self, conn, chunked=False, compressed=False):
        self.conn = conn
        self.chunked = chunked
        self.compressed = compressed
        self.BUFSIZE = BUFSIZE

    def send(self, obj):
        s = cPickle.dumps(obj, -1)
        self.conn.send(s)

    def recv(self):
        trials = 5
        for i in xrange(trials):
            try:
                s = self.conn.recv()
                break
            except Exception as e:
                log_warn("Connection error (%d/%d): %s" %
                    (i + 1, trials, str(e)))
                time.sleep(.1 * 2 ** i)
                if i == trials - 1:
                    return None
        return cPickle.loads(s)

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None


def accept(address):
    """
    Accept a connection and return a Connection object.
    """
    while True:
        try:
            listener = Listener(address, authkey=USERPREF['authkey'])
            conn = listener.accept()
            break
        except Exception:
            log_warn("The authentication key is not correct")
            listener.close()
            del listener
            time.sleep(.1)
    client = listener.last_accepted
    return Connection(conn), client[0]


def connect(address, trials=None):
    """
    Connect to a server and return a Connection object.
    """
    if trials is None:
        trials = USERPREF['connectiontrials']
    conn = None
    t0 = time.time()
    timeout = USERPREF['connectiontimeout']
    for i in xrange(trials):
        try:
            conn = Client(address, authkey=USERPREF['authkey'])
            break
        except AuthenticationError as e:
            log_warn("Authentication error: %s" % str(e))
            break
        except Exception as e:
            if time.time() > t0 + timeout:
                log_warn("Connection timed out, unable to connect to %s"\
                         % str(address))
                break
            log_debug("Connection error: %s, trying again... (%d/%d)" %
                (str(e), i + 1, trials))
            if i == trials - 1:
                log_warn("Connection error: %s" % e)
            time.sleep(.1 * 2 ** i)
    if conn is None:
        return None
    return Connection(conn)

########NEW FILE########
__FILENAME__ = debugtools
from userpref import *
import logging
import os.path
import time
import traceback
import sys


def setup_logging(level):
    if level == logging.DEBUG:
        logging.basicConfig(level=level,
                            format="%(asctime)s,%(msecs)03d  \
%(levelname)-7s  P:%(process)-4d  \
T:%(thread)-4d  %(message)s",
                            datefmt='%H:%M:%S')
    else:
        logging.basicConfig(level=level,
                            stream=sys.stdout,
                            format="%(message)s")
    return logging.getLogger('playdoh')


def get_caller():
    tb = traceback.extract_stack()[-3]
    module = os.path.splitext(os.path.basename(tb[0]))[0].ljust(18)
    line = str(tb[1]).ljust(4)
#    func = tb[2].ljust(18)
#    return "L:%s  %s  %s" % (line, module, func)
    return "L:%s  %s" % (line, module)


def log_debug(obj):
    # HACK: bug fix for deadlocks when logger level is not debug
    time.sleep(.002)
    if level == logging.DEBUG:
        string = str(obj)
        string = get_caller() + string
        logger.debug(string)


def log_info(obj):
    if level == logging.DEBUG:
        obj = get_caller() + str(obj)
    logger.info(obj)


def log_warn(obj):
    if level == logging.DEBUG:
        obj = get_caller() + str(obj)
    logger.warn(obj)


def debug_level():
    logger.setLevel(logging.DEBUG)


def info_level():
    logger.setLevel(logging.INFO)


def warning_level():
    logger.setLevel(logging.WARNING)


# Set logging level to INFO by default
level = eval('logging.%s' % USERPREF['loglevel'])
logger = setup_logging(level)


__all__ = ['log_debug', 'log_info', 'log_warn',
           #'logging', 'setup_logging', 'logger',
           'debug_level', 'info_level', 'warning_level']


if __name__ == '__main__':
    log_debug("hello world")
    log_info("hello world")

########NEW FILE########
__FILENAME__ = filetransfer
"""
Allows to transfer files via RPC. Used for Python modules transmission.
"""
from rpc import *
from debugtools import *
from cache import *
import os.path
import shutil
import base64


def readbinary(filename):
    """
    Converts a binary file into a Python list of chars so that it can
    be pickled without problem.
    """
    binfile = open(filename, 'rb')
    data = binfile.read()
    binfile.close()
    data_base64 = base64.b64encode(data)
    return data_base64


def writebinary(filename, data_base64):
    """
    Writes data stored in datalist (returned by readbinary) into filename.
    """
    binfile = open(filename, 'wb')
    data = base64.b64decode(data_base64)
    binfile.write(data)
    binfile.close()
    return


class FileTransferHandler(object):
#    basedir = os.path.realpath(os.path.dirname(__file__)) # module dir
    basedir = BASEDIR  # user dir

    def save_files(self, files, filenames):
        """
        Saves files on the disk.
        """
        for file, filename in zip(files, filenames):
            # real path to the file on the server
            filename = os.path.realpath(os.path.join(self.basedir, filename))

            # folder on the server
            dirname = os.path.dirname(filename)

            # creates the folder if needed
            if not os.path.exists(dirname):
                try:
                    log_debug("server: creating '%s' folder" % dirname)
                    os.mkdir(dirname)
                except:
                    log_warn("server: error while creating '%s'" % dirname)

            log_debug("server: writing '%s'" % filename)
            writebinary(filename, file)
        return True

    def erase_files(self, filenames=None, dirs=None):
        if filenames is None:
            filenames = []
        if dirs is None:
            dirs = []
        # Deletes filenames
        for filename in filenames:
            filename = os.path.realpath(os.path.join(self.basedir, filename))
            log_debug("server: erasing '%s'" % filename)
            os.remove(filename)
        # Deletes directories
        for dir in dirs:
            dir = os.path.realpath(os.path.join(self.basedir, dir))
            try:
                log_debug("server: erasing '%s' folder" % filename)
                shutil.rmtree(dir)
            except Exception:
                log_warn("server: an error occured when erasing the folder")
        return True


def send_files(machines, from_filenames, to_filenames=None, to_dir=None):
    if type(machines) is str:
        machines = [machines]
    if type(from_filenames) is str:
        from_filenames = [from_filenames]
    if type(to_filenames) is str:
        to_filenames = [to_filenames]
    if len(machines) == 0:
        log_debug("No machines to send files")
        return

    if to_filenames is None:
        if to_dir is None:
            raise Exception("If 'to_filenames' is not specified, you must \
                             specify 'to_dir'")
        else:
            basedir = os.path.commonprefix(from_filenames)
            to_filenames = [os.path.join(to_dir,
                                         os.path.relpath(file, basedir))
                                         for file in from_filenames]
    files = [readbinary(filename) for filename in from_filenames]

    GC.set(machines, handler_class=FileTransferHandler, handler_id="savefiles")
    disconnect = GC.connect()
    result = GC.save_files([files] * len(machines),
                           [to_filenames] * len(machines))
    GC.delete_handler()
    GC.set(machines)  # forget the handler_class/id

    if disconnect:
        GC.disconnect()

#    clients.disconnect()
    return result


def erase_files(machines, filenames=None, dirs=None):
    if type(machines) is str:
        machines = [machines]
    if type(filenames) is str:
        filenames = [filenames]
    if type(dirs) is str:
        dirs = [dirs]

    if filenames is None and dirs is None:
        raise Exception("Both 'filenames' and 'dirs' cannot be None.")

    GC.set(machines, handler_class=FileTransferHandler, handler_id="savefiles")
    disconnect = GC.connect()

#    clients = RpcClients(machines, handler_class=FileTransferHandler,
#               handler_id="savefiles")
#    clients.connect()
#    clients.add_handler([FileTransferHandler]*len(machines))
    result = GC.erase_files([filenames] * len(machines),
                            [dirs] * len(machines))
    GC.delete_handler()

    if disconnect:
        GC.disconnect()

#    clients.disconnect()
    return result

########NEW FILE########
__FILENAME__ = gputools
__all__ = ['initialise_cuda', 'pycuda', 'MAXGPU', 'CANUSEGPU',
           'set_gpu_device', 'close_cuda', 'get_gpu_count']

try:
    from debugtools import *
    import atexit
    import pycuda
    import pycuda.compiler
    import pycuda.gpuarray
    import pycuda.driver as drv
    import multiprocessing
    pycuda.context = None
    pycuda.isinitialised = False
    MAXGPU = 0
    CANUSEGPU = True

    def get_gpu_count():
        """
        Return the total number of GPUs without initializing PyCUDA on the
        current process.
        """
        pool = multiprocessing.Pool(1)
        result = pool.apply(initialise_cuda)
        return result

    def initialise_cuda():
        """
        Initialize PyCUDA on the current process.
        """
        global MAXGPU
        if not pycuda.isinitialised:
#            log_debug("drvinit")
            drv.init()
            pycuda.isinitialised = True
#            log_debug("drvdevicecount")
            MAXGPU = drv.Device.count()
            log_debug("PyCUDA initialized, %d GPU(s) found" % MAXGPU)
        return MAXGPU

    def set_gpu_device(n):
        """
        Make PyCUDA use GPU number n in the system.
        """
#        log_debug(inspect.stack()[1][3])
        initialise_cuda()
        log_debug("Setting PyCUDA context number %d" % n)
        try:
            pycuda.context.detach()
        except:
            log_debug("Couldn't detach PyCUDA context")
            pass
        if n < MAXGPU:
            pycuda.context = drv.Device(n).make_context()
        else:
            pycuda.context = drv.Device(MAXGPU - 1).make_context()
            log_warn("Unable to set GPU device %d, setting device %d instead" %
                (n, MAXGPU - 1))

    def close_cuda():
        """
        Closes the current PyCUDA context. MUST be called at the end of the
        script.
        """
        log_debug("Trying to close current PyCUDA context")
        if pycuda.context is not None:
            try:
                log_debug("Closing current PyCUDA context")
                pycuda.context.pop()
                pycuda.context = None
            except:
                log_warn("A problem occurred when closing PyCUDA context")

    atexit.register(close_cuda)

except:
    MAXGPU = 0
    CANUSEGPU = False
    pycuda = None

    def get_gpu_count():
        """
        Return the total number of GPUs, 0 here because PyCUDA doesn't \
        appear to be installed.
        """
        return 0

    def initialise_cuda():
        return 0

    def set_gpu_device(n):
        log_warn("PyCUDA not available")
        pass

    def close_cuda():
        pass

########NEW FILE########
__FILENAME__ = interface
from asyncjobhandler import *
from synchandler import *
from optimization import *
from rpc import *
from debugtools import *
from gputools import *
from resources import *
from codehandler import *
from numpy import ndarray, float, floor, log10, inf, ones
from numpy.random import rand
import datetime
import inspect


__all__ = ['remote', 'map_async', 'minimize_async', 'maximize_async',
           'map', 'minimize', 'maximize',
           'start_task', 'start_optimization',
           'print_table']


def remote(f, machines, codedependencies=[]):
    if type(machines) is not list:
        machines = [machines]

    def f0(x):
        return f()

    r = map(f0, [None], machines=machines, codedependencies=codedependencies)
    if len(machines) == 1:
        return r[0]
    else:
        return r


def map_async(fun, *argss, **kwdss):
    """
    Asynchronous version of ``map``. Return a :class:`JobRun` object
    which allows to poll the jobs'
    status asynchronously and retrieve the results later.

    The :func:`map` function is equivalent to ``map_async(...).get_results()``.
    """
    allocation = kwdss.pop('allocation', None)
    shared_data = kwdss.pop('shared_data', {})
    do_redirect = kwdss.pop('do_redirect', None)
    cpu = kwdss.pop('cpu', None)
    gpu = kwdss.pop('gpu', None)
    machines = kwdss.pop('machines', [])
    unit_type = kwdss.pop('unit_type', 'CPU')
    total_units = kwdss.pop('total_units', None)
    codedependencies = kwdss.pop('codedependencies', None)
    disconnect = kwdss.pop('disconnect', True)

    if not inspect.isfunction(fun):
        raise Exception("The first argument of 'map' must be a valid \
            Python function (or a lambda function)")

    # Default allocation of resources
    if allocation is None:
        allocation = allocate(machines=machines,
                              total_units=total_units,
                              unit_type=unit_type,
                              cpu=cpu,
                              gpu=gpu)
    else:
        # if allocation is explicitely specified, then not local
        local = False
    local = allocation.local

    GC.set(allocation.machine_tuples, handler_class=AsyncJobHandler)
    GC.connect()

    # Send dependencies
    if not local:
        fun_pkl = send_dependencies(allocation.machine_tuples, fun,
                                    codedependencies)
    else:
        fun_pkl = pickle_class(fun)

    if not local:
        log_info("Submitting jobs to the servers")
    myjobs = submit_jobs(fun_pkl, argss=argss, kwdss=kwdss,
                         allocation=allocation,
                         unit_type=allocation.unit_type,
                         do_redirect=do_redirect,
                         local=local,
                         shared_data=shared_data)

    if disconnect:
        GC.disconnect()

    return myjobs


def map(*args, **kwds):
    """
    Parallel version of the built-in ``map`` function.
    Executes the function ``fun`` with the arguments ``*argss`` and
    keyword arguments ``**kwdss`` across CPUs on one or several computers.
    Each argument and keyword argument is a list with the arguments
    of every job.
    This function returns the result as a list, one item per job.
    If an exception occurs within the function, :func:`map` returns
    the Exception object as a result. This object has an extra attribute,
    ``traceback``, which contains the traceback of the exception.

    Special keyword arguments:

    ``cpu=MAXCPU``
        Total number of CPUs to distribute the function over.
        If ``machines`` is not specified or is an empty list,
        only CPUs on the local computer will be used.
        The total number of CPUs is obtained with the global
        variable ``MAXCPU``. By default, all CPUs on the machine
        are used.

    ``gpu=0``
        If the function loads CUDA code using the PyCUDA package,
        Playdoh is able to distribute it across GPUs on one or
        several machines. In this case, ``gpu`` is the total
        number of GPUs to use and works the same way as ``cpu``.

        .. seealso:: User guide :ref:`gpu`.

    ``machines=[]``
        The list of computers to distribute the function over.
        Items can be either IP addresses as strings, or tuples
        ``('IP', port)`` where ``port`` is an integer giving
        the port over which the Playdoh server is listening
        on the remote computer. The default port is obtained
        with the global variable ``DEFAULT_PORT``.

    ``allocation=None``
        Resource allocation is normally done automatically assuming
        that all CPUs are equivalent. However, it can also be done
        manually by specifying the number of CPUs to use on every
        computer. It is done with the :func:`allocate` function.

        .. seealso:: User guide for :ref:`allocation`.

    ``shared_data={}``
        Large data objects (NumPy arrays) can be shared across CPUs
        running on the same
        computer, but they must be read-only. The ``shared_data``
        argument is a
        dictionary: keys are variable names and values are large
        NumPy arrays that should be stored in shared memory
        on every computer if possible.

        .. seealso:: User guide for :ref:`shared_data`.

    ``codedependencies=[]``
        If the function to distribute uses external Python modules,
        these modules must be transported to every machine along
        with the function code. The ``codedependencies`` argument
        contains the list of these modules' pathnames relatively
        to the directory where the function's module is defined.

        .. seealso:: User guide for :ref:`code_transport`.
    """
    kwds['disconnect'] = False
    myjobs = map_async(*args, **kwds)
    results = myjobs.get_results()
    GC.disconnect()
    return results


def minimize_async(fun,
             popsize=100,
             maxiter=5,
             algorithm=CMAES,
             allocation=None,
             unit_type='CPU',
             shared_data={},
             maximize=False,
             groups=1,
             cpu=None,
             gpu=None,
             total_units=None,
             codedependencies=None,
             optparams={},
             machines=[],
             returninfo=False,
             bounds=None,
             initrange=None,
             scaling=None,
             do_redirect=None,
             args=(),
             kwds={},
             **params):
    """
    Asynchronous version of :func:`minimize`. Returns an
    :class:`OptimizationRun` object.
    """

    # Make sure the parameters are float numbers
    for k, v in params.iteritems():
        if type(v) is tuple or type(v) is list:
            for i in xrange(len(v)):
                if type(v[i]) is int:
                    v[i] = float(v[i])

    argtype = 'matrix'  # keywords or matrix argument for the fitness function
    if bounds is not None and initrange is not None:
        pass
#        ndimensions = bounds.shape[0]
    elif bounds is not None:
#        ndimensions = bounds.shape[0]
        initrange = bounds
    elif initrange is not None:
        bounds = ones(initrange.shape)
        bounds[:, 0] = -inf
        bounds[:, 1] = inf
#        ndimensions = bounds.shape[0]
    else:
        argtype = 'keywords'
#        ndimensions = len(params)
        params4 = {}
        for k in params.keys():
            ksplit = k.split('_')
            k0 = '_'.join(ksplit[:-1])
            k1 = ksplit[-1]
            if len(ksplit) > 1 and k1 in ['bounds', 'initrange'] and \
                    k0 not in params4.keys():
                params4[k0] = [-inf, None, None, inf]
            if len(ksplit) == 1 or k1 not in ['bounds', 'initrange']:
                params4[k] = params[k]
        for name in params4.keys():
            name_bound = '%s_bounds' % name
            name_init = '%s_initrange' % name
            if name_bound in params.keys():
                params4[name][0] = params[name_bound][0]
                params4[name][1] = params[name_bound][0]
                params4[name][2] = params[name_bound][1]
                params4[name][3] = params[name_bound][1]
            if name_init in params.keys():
                params4[name][1] = params[name_init][0]
                params4[name][2] = params[name_init][1]
        params = params4
    if bounds is not None:
        bounds = bounds.astype(float)
    if initrange is not None:
        initrange = initrange.astype(float)

    # Default allocation of resources
    if allocation is None:
        allocation = allocate(machines=machines,
                              total_units=total_units,
                              unit_type=unit_type,
                              cpu=cpu,
                              gpu=gpu)
    else:
        # if allocation is explicitely specified, then not local
        local = False

    local = allocation.local

    GC.set(allocation.machine_tuples)
    disconnect = GC.connect()

    # Send dependencies
    if not local:
        fun_pkl = send_dependencies(allocation.machine_tuples, fun,
                                    codedependencies)
    else:
        fun_pkl = pickle_class(fun)

    task = start_optimization(fun_pkl,
                              maxiter,
                              popsize=popsize,
                              local=local,
                              groups=groups,
                              maximize=maximize,
                              algorithm=algorithm,
                              allocation=allocation,
                              optparams=optparams,
                              shared_data=shared_data,
                              argtype=argtype,
                              unit_type=unit_type,
                              initrange=initrange,
                              bounds=bounds,
                              scaling=scaling,
                              return_info=returninfo,
                              do_redirect=do_redirect,
                              initargs=args,
                              initkwds=kwds,
                              **params)

    if disconnect:
        GC.disconnect()

    return task


def minimize(*args, **kwds):
    """
    Minimize a fitness function in parallel across CPUs on one or several
    computers.

    Arguments:

    ``fitness``
        The first argument is the fitness function. There are four
        possibilities:
        it can be a Python function or a Python class (deriving from
        :class:`Fitness`).
        It can also accept either keyword named arguments (like
        ``fitness(**kwds)``)
        or a ``DxN`` matrix (like ``fitness(X)``) where there are ``D``
        dimensions in the
        parameter space and ``N`` particles.

        Using a class rather than a function allows to implement an
        initialization step
        at the beginning of the optimization. See the reference for
        :class:`Fitness`.

        If the fitness is a simple keyword-like Python function, it must have
        the right keyword arguments.
        For example, if there are two parameters ``x`` and ``y`` to optimize,
        the fitness function
        must be like ``def fitness(x,y):``. If it's a matrix-like function,
        it must accept a single argument
        which is a matrix: ``def fitness(X):``.

        Fitness functions can also accept static arguments, given in the
        :func:`minimize` functions
        and alike with the ``args`` and ``kwds`` parameters (see below).

        In addition, the fitness function can accept several special keyword
        arguments:

        ``dimension``
            The dimension of the state space, or the number of optimizing
            parameters

        ``popsize``
            The total population size for each group across all nodes.

        ``subpopsize``
            The population size for each group on this node.

        ``groups``
            The number of groups.

        ``nodesize``
            The population size for all groups on this node.

        ``nodecount``
            The number of nodes used for this optimization.

        ``shared_data``
            The dictionary with shared data.

        ``unit_type``
            The unit type, ``CPU`` or ``GPU``.

        For example, use the following syntax to retrieve within the function
        the shared data dictionary and the size of the population on the
        current node:
        ``def fitness(X, shared_data, nodesize):``.


    ``popsize=100``
        Size of the population. If there are several groups, it is the size
        of the population for every group.

    ``maxiter=5``
        Maximum number of iterations.

    ``algorithm=PSO``
        Optimization algorithm. For now, it can be :class:`PSO`, :class:`GA`
        or :class:`CMAES`.

    ``allocation=None``
        :class:`Allocation` object.

        .. seealso:: User guide for :ref:`allocation`.

    ``shared_data={}``
        Dictionary containing shared data between CPUs on a same computer.

        .. seealso:: User guide for :ref:`shared_data`.

    ``groups=1``
        Number of groups. Allows to optimize independently several populations
        by using a single vectorized call to the fitness function at every
        iteration.

        .. seealso:: User guide for :ref:`groups`.

    ``cpu=MAXCPU``
        Total number of CPUs to use.

    ``gpu=0``
        If the fitness function loads CUDA code using the PyCUDA package,
        several
        GPUs can be used. In this case, ``gpu`` is the total number of GPUs.

    ``codedependencies=[]``
        List of dependent modules.

        .. seealso:: User guide for :ref:`code_transport`.

    ``optparams={}``
        Optimization algorithm parameters. It is a dictionary: keys are
        parameter names,
        values are parameter values or lists of parameters (one value per
        group).
        This argument is specific to the optimization
        algorithm used. See :class:`PSO`, :class:`GA`, :class:`CMAES`.

    ``machines=[]``
        List of machines to distribute the optimization over.

    ``scaling=None``
        Specify the scaling used for the parameters during the optimization.
        It can be ``None`` or ``'mapminmax'``. It is ``None``
        by default (no scaling), and ``mapminmax`` by default for the
        CMAES algorithm.

    ``returninfo=False``
        Boolean specifying whether information about the optimization
        should be returned with the results.

    ``args=()``
        With fitness functions, arguments of the fitness function in addition
        of the
        optimizing parameters.
        With fitness classes, arguments of the ``initialize`` method of the
        :class:`Fitness` class.
        When using a fitness keyword-like function, the arguments must be
        before the optimizing
        parameters, i.e. like ``def fitness(arg1, arg2, x1, x2):``.

    ``kwds={}``
        With fitness functions, keyword arguments of the fitness function in
        addition of the
        optimizing parameters.
        With fitness classes, keyword arguments of the ``initialize`` method
        of the :class:`Fitness` class.

    ``bounds=None``
        Used with array-like fitness functions only.
        This argument is a Dx2 NumPy array with the boundaries of the parameter
        space.
        The first column contains the minimum values acceptable for
        the parameters
        (or -inf), the second column contains the maximum values
        (or +inf).

    ``initrange=None``
        Used with array-like fitness functions only.
        This argument is a Dx2 NumPy array with the initial range in which
        the parameters should be sampled at the algorithm initialization.

    ``**params``
        Used with keyword-like fitness functions only.
        For every parameter <paramname>, the initial sampling interval
        can be specified with the keyword ``<paramname>_initrange`` which is
        a tuple with two values ``(min,max)``.
        The boundaries can be specified with the keyword ``<paramname>_bound``
        which is a tuple with two values ``(min,max)``.
        For example, if there is a single parameter in the fitness function,
        ``def fitness(x):``,
        use the following syntax:
        ``minimize(..., x_initrange=(-1,1), x_bounds=(-10,10))``.

    Return an :class:`OptimizationResult` object with the following attributes:

    ``best_pos``
        Minimizing position found by the algorithm. For array-like fitness
        functions,
        it is a single vector if there is one group, or a list of vectors.
        For keyword-like fitness functions, it is a dictionary
        where keys are parameter names and values are numeric values. If there
        are several groups,
        it is a list of dictionaries.

    ``best_fit``
        The value of the fitness function for the best positions. It is a
        single value if
        there is one group, or it is a list if there are several groups.

    ``info``
        A dictionary containing various information about the optimization.

        .. seealso:: User guide for :ref:`optinfo`.
    """
#    returninfo = kwds.pop('returninfo', None)
    task = minimize_async(*args, **kwds)
    return task.get_result()


def maximize_async(*args, **kwds):
    """
    Asynchronous version of :func:`maximize`. Returns an
    :class:`OptimizationRun` object.
    """
    kwds['maximize'] = True
    return minimize_async(*args, **kwds)


def maximize(*args, **kwds):
    """
    Maximize a fitness function in parallel across CPUs on one or several
    computers. Completely analogous to :func:`minimize`.
    """
#    returninfo = kwds.pop('returninfo', None)
    task = maximize_async(*args, **kwds)
    return task.get_result()


def print_quantity(x, precision=3):
    if x == 0.0:
        u = 0
    elif abs(x) == inf:
        return 'NaN'
    else:
        u = int(3 * floor((log10(abs(x)) + 1) / 3))
    y = float(x / (10 ** u))
    s = ('%2.' + str(precision) + 'f') % y
    if (y > 0) & (y < 10.0):
        s = '  ' + s
    elif (y > 0) & (y < 100.0):
        s = ' ' + s
    if (y < 0) & (y > -10.0):
        s = ' ' + s
    elif (y < 0) & (y > -100.0):
        s = '' + s
    if u is not 0:
        su = 'e'
        if u > 0:
            su += '+'
        su += str(u)
    else:
        su = ''
    return s + su


def print_row(name, values, colwidth):
    spaces = ' ' * (colwidth - len(name))
    print name + spaces,
    if type(values) is not list and type(values) is not ndarray:
        values = [values]
    for value in values:
        s = print_quantity(value)
        spaces = ' ' * (colwidth - len(s))
        print s + spaces,
    print


def print_table(results, precision=4, colwidth=16):
    """
    Displays the results of an optimization in a table.

    Arguments:

    ``results``
        The results returned by the ``minimize`` of ``maximize`` function.

    ``precision = 4``
        The number of decimals to print for the parameter values.

    ``colwidth = 16``
        The width of the columns in the table.
    """
#    if type(results['best_fit']) is not list:
#        group_count = 1
#    else:
#        group_count = len(results['best_fit'])
    group_count = results.groups

    print "RESULTS"
    print '-' * colwidth * (group_count + 1)

    if group_count > 1:
        print ' ' * colwidth,
        for i in xrange(group_count):
            s = 'Group %d' % i
            spaces = ' ' * (colwidth - len(s))
            print s + spaces,
        print

    best_pos = results.best_pos

    if best_pos is None:
        log_warn("The optimization results are not valid")
        return

    if group_count == 1:
        best_pos = [best_pos]
    if results.parameters.argtype != 'keywords':
#    keys = results.keys()
#    keys.sort()
#    if 'best_pos' in keys:
#        best_pos = results['best_pos']
#        if best_pos.ndim == 1:
#            best_pos = best_pos.reshape((-1,1))
#        for i in xrange(best_pos.shape[0]):
        for i in xrange(len(best_pos[0])):
#            val = best_pos[i,:]
            val = [best_pos[k][i] for k in xrange(len(best_pos))]
            print_row("variable #%d" % (i + 1), val, colwidth)
    else:
        keys = best_pos[0].keys()
        keys.sort()
        for key in keys:
            val = [results[i].best_pos[key] for i in xrange(group_count)]
#            if key[0:8] != 'best_fit':
            print_row(key, val, colwidth)

    val = [results[i].best_fit for i in xrange(group_count)]
    print_row('best fit', val, colwidth)
    print


def start_task(task_class,
               task_id=None,
               topology=[],
               nodes=None,  # nodes can be specified manually
               allocation=None,  # in general, allocation is specified
               machines=[],
               total_units=None,
               unit_type='CPU',
               cpu=None,
               gpu=None,
               local=None,
               codedependencies=None,
               pickle_task=True,
               shared_data={},
               do_redirect=None,
               args=(),
               kwds={}):
    """
    Launches a parallel task across CPUs on one or several computers.

    Arguments:

    ``task_class``
        The class implementing the task, must derive from the base class
        ``ParallelTask``.

    ``task_id=None``
        The name of this particular task run. It should be unique, by default
        it is randomly
        generated based on the date and time of the launch. It is used to
        retrieve the results.

    ``topology=[]``
        The network topology. It defines the list of tubes used by the task.
        It is a list of tuples ``(tubename, source, target)`` where
        ``tubename`` is the name of the tube, ``source`` is an integer
        giving the
        node index of the source, ``target`` is the node index of the target.
        Node indices start at 0.

    ``cpu=None``
        The total number of CPUs to use.

    ``gpu=None``
        When using GPUs, the total number of GPUs to use.

    ``machines=[]``
        The list of machine IP addresses to launch the task over.

    ``allocation=None``
        The allocation object returned by the ``allocate`` function.

    ``codedependencies``
        The list of module dependencies.

    ``shared_data={}``
        Shared data.

    ``args=()``
        The arguments to the ``initialize`` method of the task. Every argument
        item
        is a list with one element per node.

    ``kwds={}``
        The keyword arguments to the ``initialize`` method of the task. Every
        value is a list with one element per node.
    """
    # Default task id
    if task_id is None:
        now = datetime.datetime.now()
        task_id = "task-%d%d%d-%d%d%d-%.4d" % (now.year, now.month, now.day,
                                              now.hour, now.minute, now.second,
                                              int(rand() * 1000))

    # Default allocation of resources
    if allocation is None:
        allocation = allocate(machines=machines,
                              total_units=total_units,
                              unit_type=unit_type,
                              cpu=cpu,
                              gpu=gpu)

    machines = allocation.machines
    unit_type = allocation.unit_type
    total_units = allocation.total_units

    # list of nodes on every machine
    nodes_on_machines = dict([(m, []) for m in machines])
    # Creates a Nodes list from an allocation
    if nodes is None:
        nodes = []
        index = 0
        for m in machines:
            units = allocation[m]
            for unitidx in xrange(units):
                nodes.append(Node(index, m, unit_type, unitidx))
                nodes_on_machines[m].append(index)
                index += 1

    mytask = TaskRun(task_id, unit_type, machines, nodes, args, kwds)

    if local is None:
        local = allocation.local
    mytask.set_local(local)

    # Gets the args and kwds of each machine
    argss = args
    kwdss = kwds
    k = len(argss)  # number of non-named arguments
    keys = kwdss.keys()  # keyword arguments

    # Duplicates non-list args
    argss = list(argss)
    for l in xrange(k):
        if type(argss[l]) is not list:
            argss[l] = [argss[l]] * len(nodes)

    # Duplicates non-list kwds
    for key in keys:
        if type(kwdss[key]) is not list:
            kwdss[key] = [kwdss[key]] * len(nodes)

    # Now, argss is a list of list and kwdss a dict of lists
    # argss[l][i] is the list of arg #l for node #i
    # we must convert it so that
    argss2 = [[] for _ in xrange(k)]
    kwdss2 = dict([(key, []) for key in keys])
    for i in xrange(len(machines)):
        m = machines[i]
        local_nodes = nodes_on_machines[m]
        for l in xrange(k):
            argss2[l].append([argss[l][ln] for ln in local_nodes])
        for key in keys:
            kwdss2[key].append([kwdss[key][ln] for ln in local_nodes])

    GC.set(allocation.machine_tuples)
    disconnect = GC.connect()

    if pickle_task:
        if not local:
            task_class_pkl = send_dependencies(allocation.machine_tuples,
                                               task_class, codedependencies)
        else:
            task_class_pkl = pickle_class(task_class)
    else:
        task_class_pkl = task_class

    n = len(allocation.machines)
    GC.set(allocation.machine_tuples, handler_class=SyncHandler,
           handler_id=task_id)

    # BUG: when there is shared_data, the processes are relaunched => bug
    # on windows when a socket connection is open: the connection is "forked"
    # to the subprocesses and the server is not reachable anymore
    if len(shared_data) > 0:
        close_connection_temp = True
    else:
        close_connection_temp = False

    if not local:
        log_info("Submitting the task to %d server(s)" % n)
    GC.submit([task_class_pkl] * n,
              [task_id] * n,
              [topology] * n,
              [nodes] * n,
              # local nodes
              [[nodes[i] for i in nodes_on_machines[m]] for m in machines],
              [unit_type] * n,
              do_redirect=[do_redirect] * n,
              shared_data=[shared_data] * n,
              _close_connection_temp=close_connection_temp)

    if close_connection_temp:
        GC.connect()

    if not local:
        log_info("Initializing task")
    GC.initialize(*argss2, **kwdss2)

    if not local:
        log_info("Starting task")
    GC.start()

    if disconnect:
        GC.disconnect()
    return mytask


def start_optimization(fitness_class,
                       maxiter=5,
                       popsize=100,
                       groups=1,
                       algorithm=PSO,
                       maximize=False,
                       task_id=None,
                       unit_type='CPU',
                       nodes=None,
                       allocation=None,
                       local=None,
                       shared_data={},
                       optparams={},
                       scaling=None,
                       initrange=None,
                       bounds=None,
                       argtype='keywords',
                       return_info=False,
                       do_redirect=None,
                       initargs=(),
                       initkwds={},
                       **parameters):
    """
    Starts an optimization. Use ``minimize_async`` and ``maximize_async``
    instead.
    """
    nodecount = allocation.total_units
    topology = algorithm.get_topology(nodecount)

    parameters = OptimizationParameters(scaling=scaling,
                                        argtype=argtype,
                                        initrange=initrange,
                                        bounds=bounds,
                                        **parameters)

    args = (algorithm,
            fitness_class,
            maximize,
            maxiter,
            scaling,
            popsize,
            nodecount,
            groups,
            return_info,
            parameters,
            optparams,
            initargs,
            initkwds)

    task = start_task(Optimization,
                      task_id,
                      topology,
                      unit_type=unit_type,
                      nodes=nodes,
                      local=local,
                      allocation=allocation,
                      shared_data=shared_data,
                      codedependencies=[],
                      pickle_task=False,
                      do_redirect=do_redirect,
                      args=args)

    return OptimizationRun(task)

########NEW FILE########
__FILENAME__ = algorithm
from ..synchandler import *
from ..debugtools import *
from optimization import *
from numpy import zeros, tile, mod
from numpy.random import rand, seed
import os
from time import time
__all__ = ['OptimizationAlgorithm']


class OptimizationAlgorithm(object):
    def __init__(self,
                 index,
                 nodes,
                 tubes,
                 popsize,
                 subpopsize,
                 nodesize,
                 groups,
                 return_info,
                 maxiter,
                 scaling,
                 parameters,
                 optparams):
        self.index = index
        self.nodes = nodes
        self.nodecount = len(nodes)
        self.scaling = scaling
        self.node = nodes[index]
        self.tubes = tubes
        self.return_info = return_info
        self.popsize = popsize
        self.subpopsize = subpopsize
        self.nodesize = nodesize
        self.groups = groups

#        self.nparticles = nparticles # number of columns of X
#        self.ntotal_particles = ntotal_particles

        self.ndimensions = parameters.param_count  # number of rows of X
        self.parameters = parameters
        self.maxiter = maxiter
        self.optparams = optparams

    @staticmethod
    def default_optparams():
        """
        MUST BE OVERRIDEN
        Returns the default values for optparams
        """
        return {}

    @staticmethod
    def get_topology(node_count):
        """
        MUST BE OVERRIDEN
        Returns the list of tubes (name, i1, i2)
        as a function of the number of nodes
        """
        return []

    def initialize(self):
        """
        MAY BE OVERRIDEN
        Initializes the optimization algorithm.
        X is the matrix of initial particle positions.
        X.shape == (ndimensions, particles)
        """
        pass

    def initialize_particles(self):
        """
        MAY BE OVERRIDEN
        Sets the initial positions of the particles
        By default, samples uniformly
        params is a list of tuples (bound_min, init_min, init_max, bound_max)
        """
        # initializes the particles
        if os.name == 'posix':
            t = time()
            t = mod(int(t * 10000), 1000000)
            seed(int(t + self.index * 1000))

        if self.parameters.argtype == 'keywords':
            params = [self.parameters.params[name]\
                       for name in self.parameters.param_names]
            X = zeros((self.ndimensions, self.nodesize))
            for i in xrange(len(params)):
                value = params[i]
                if len(value) == 2:
                    # One default interval,
                    # no boundary counditions on parameters
                    X[i, :] = value[0] + (value[1] - value[0]) \
                    * rand(self.nodesize)
                elif len(value) == 4:
                    # One default interval,
                    # value = [min, init_min, init_max, max]
                    X[i, :] = value[1] + (value[2] - value[1])\
                     * rand(self.nodesize)
            self.X = X
        else:
            initmin = tile(self.parameters.initrange[:, 0].reshape((-1, 1)),\
                            (1, self.nodesize))
            initmax = tile(self.parameters.initrange[:, 1].reshape((-1, 1)),\
                            (1, self.nodesize))
            self.X = initmin + (initmax - initmin) * \
            rand(self.ndimensions, self.nodesize)

#    def set_boundaries(self, params):
#        """
#        MAY BE OVERRIDEN
#        Sets the boundaries as a
#        ndimensionsx2 array, boundaries[i,:]=[min,max] for
#        parameter #i
#        """
#        boundaries = zeros((self.ndimensions, 2))
#        for i in xrange(len(params)):
#            value = params[i]
#            if len(value) == 2:
#                # One default interval, no boundary
#                counditions on parameters
#                boundaries[i,:] = [-inf, inf]
#            elif len(value) == 4:
#                # One default interval,
#                  value = [min, init_min, init_max, max]
#                boundaries[i,:] = [value[0], value[3]]
#        self.boundaries = boundaries

    def pre_fitness(self):
        """
        MAY BE OVERRIDEN
        """
        pass

    def post_fitness(self, fitness):
        """
        MAY BE OVERRIDEN
        """
        return fitness

    def iterate(self, iteration, fitness):
        """
        MUST BE OVERRIDEN
        """
        pass

    def get_info(self):
        """
        MAY BE OVERRIDEN
        """
        pass

    def get_result(self):
        """
        MUST BE OVERRIDEN
        Returns (X_best, fitness_best)
        X_best.shape = (ndimensions, groups)
        fitness_best.shape = (groups)
        """
        pass

########NEW FILE########
__FILENAME__ = cma_es
from ..synchandler import *
from ..debugtools import *
from optimization import *
from algorithm import *
from cma_utils import *
from numpy import zeros, ones, array, \
inf, tile, maximum, minimum, argsort, \
argmin, floor, where, unique, squeeze, mod
from numpy.random import seed
from scipy import linalg
import os
from time import time

__all__ = ['CMAES']


class CMAES(OptimizationAlgorithm):
    """
    Covariance Matrix Adaptation Evolution Strategy algorithm
    See the
    `wikipedia entry on CMAES <http://en.wikipedia.org/wiki/CMA - ES>`__
    and also the author's website <http://www.lri.fr/~hansen/cmaesintro.html>`

    Optimization parameters:

    ``proportion_selective = 0.5``
        This parameter (refered to as mu in the CMAES algorithm) is the
        proportion (out of 1) of the entire population that is selected and
        used to update the generative distribution. (note for different groups
        case: this parameter can only have one value, i.e. every group
        will have the same value (the first of the list))

    ``bound_strategy = 1``:
        In the case of a bounded problem, there are two ways to handle the new
        generated points which fall outside the boundaries.
        (note for different groups case: this parameter can only have one
        value, i.e. every group will have the same
        value (the first of the list))

        ``bound_strategy = 1``. With this strategy, every point outside the
        domain is repaired, i.e. it is projected to its nearset possible
        value :math:`x_{repaired}`. In other words, components that are
        infeasible in :math:`x` are set to the (closest) boundary value
        in :math:`x_{repaired}` The fitness function on the repaired search
        points is evaluated and a penalty which depends on the distance to
        the repaired solution is added
        :math:`f_{fitness}(x) = f(x_{repaired})+\gamma \|x-x_{repaired}\|^{2}`
        The repaired solution is disregarded afterwards.

        ``bound_strategy = 2``. With this strategy any infeasible solution x is
        resampled until it become feasible. It should be used only if the
        optimal solution is not close to the infeasible domain.

    See p.28 of <http://www.lri.fr/~hansen/cmatutorial.pdf> for more details
    ``gamma``:

        ``gamma`` is the weight :math:`\gamma` in the previously introduced
        penalty function. (note for different groups case: this parameter can
        only have one value, i.e. every group will have the same
        value (the first of the list))
    """
    @staticmethod
    def default_optparams():
        """
        Returns the default values for optparams
        """
        optparams = dict()
        optparams['proportion_selective'] = 0.5
        optparams['alpha'] = 500   # Boundaries and Constraints:
        optparams['bound_strategy'] = 1
        return optparams

    @staticmethod
    def get_topology(node_count):
        topology = []
        # 0 is the master, 1..n are the workers
        if node_count > 1:
            for i in xrange(1, node_count):
                topology.extend([('to_master_%d' % i, i, 0),
                                 ('to_worker_%d' % i, 0, i)])
        return topology

    def initialize(self):
        """
        Initializes the optimization algorithm. X is the matrix of initial
        particle positions.
        """
        if os.name == 'posix':
            t = time()
            t = mod(int(t * 10000), 1000000)
            seed(int(t + self.index * 1000))

        initial_solution = zeros(self.ndimensions)

        self.bound_strategy = self.optparams['bound_strategy'][0]
        self.mu = floor(self.popsize *\
                                    self.optparams['proportion_selective'][0])
        opt = dict()
        opt['CMAmu'] = self.mu
        opt['popsize'] = self.popsize
        opt['maxiter'] = self.maxiter + 1
        opt['verb_disp'] = False
        self.es = [0] * self.groups
        for igroup in xrange(self.groups):
            self.es[igroup] = CMAEvolutionStrategy(initial_solution, .1, opt)
            self.es[igroup].sigma_iter = []
            self.es[igroup].iteration = 0

        self.alpha = array(self.optparams['alpha'])
        if self.scaling == None:
            self.Xmin = tile(self.boundaries[:, 0].\
                            reshape(self.ndimensions, 1), (1, self.nodesize))
            self.Xmax = tile(self.boundaries[:, 1].\
                             reshape(self.ndimensions, 1), (1, self.nodesize))
        else:
            self.Xmin = tile(self.parameters.scaling_func(self.\
            boundaries[:, 0]).reshape(self.ndimensions, 1), (1, self.nodesize))
            self.Xmax = tile(self.parameters.scaling_func(self.\
            boundaries[:, 1]).reshape(self.ndimensions, 1), (1, self.nodesize))

        # Preparation of the optimization algorithm

        self.fitness_gbest = inf * ones((self.groups, self.mu))
        self.X_gbest = zeros((self.groups, self.ndimensions, self.mu))
        if self.mu <= self.subpopsize:
            self.fitness_lbest = inf * ones((self.groups, self.mu))
            self.X_lbest = zeros((self.groups, self.ndimensions, self.mu))
        else:
            self.fitness_lbest = inf * ones((self.groups, self.subpopsize))
            self.X_lbest = zeros((self.groups, self.ndimensions,\
                                                         self.subpopsize))

        if self.return_info:
            self.best_fitness = zeros((self.groups, self.maxiter))
            self.best_particule = zeros((self.groups, self.ndimensions,\
                                                                self.maxiter))
            self.dist_mean = zeros((self.groups, self.ndimensions,\
                                                             self.maxiter))
            self.dist_std = zeros((self.groups, self.ndimensions,\
                                                                 self.maxiter))

        self.mean_distr = zeros((self.groups, self.ndimensions))
        self.std_distr = zeros((self.groups, self.ndimensions))
        self.C = zeros((self.groups, self.ndimensions, self.ndimensions))
        self.D = zeros((self.groups, self.ndimensions))
        self.B = zeros((self.groups, self.ndimensions, self.ndimensions))
        self.iteration = 0
        self.X_best_of_all = zeros((self.groups, self.ndimensions))
        self.fitness_best_of_all = [inf] * ones(self.groups)

    def initialize_particles(self):
        self.X = zeros((self.ndimensions, self.nodesize))
        if self.parameters.argtype == 'keywords':
            params = self.parameters.params
            params = [self.parameters.params[name] for name in\
                                                self.parameters.param_names]
            init_mean = zeros(len(params))
            init_std = zeros(len(params))
            for i in xrange(len(params)):
                value = params[i]
                value = array(value).astype('float')
                if len(value) == 2:
                    init_mean[i] = array((value[1] + value[0]) / 2)
                    init_std[i] = array((value[1] - value[0]) / 6)
                elif len(value) == 4:
                    init_mean[i] = array((value[2] + value[1]) / 2)
                    init_std[i] = array((value[2] - value[1]) / 6)
#                print name, init_mean[i], init_std[i], value[2] , value[1]

        else:
            init_range = self.parameters.initrange
            init_mean = (init_range[:, 1] + init_range[:, 0]) / 2
            init_std = (init_range[:, 1] - init_range[:, 0]) / 6

        if self.scaling is not None:
            init_mean = self.parameters.scaling_func(init_mean)
            init_std = 2 * init_std / (self.parameters.scaling_factor_b\
                                           - self.parameters.scaling_factor_a)

        for igroup in xrange(self.groups):
            self.es[igroup].sigma = init_std
            self.es[igroup].mean = init_mean
        self.X = array(self.es[0].ask(number=self.nodesize)).T

    def communicate_before_update(self):
        ## the workers send their mu best positions and fitness and
        ## the master receives them
        if self.index > 0:
            # WORKERS
#            log.info("I'm worker #%d" % self.index)

            # sends the mu best local position and their fitness
            to_master = 'to_master_%d' % self.index
            self.tubes.push(to_master, (self.X_lbest, self.fitness_lbest))

        else:
            # MASTER
            if len(self.nodes) == 1:   # if only one worker sort the particles
                self.X_gbest = self.X_lbest
                self.fitness_gbest = self.fitness_lbest
                for igroup in xrange(self.groups):
                    indices_population_sorted = argsort(self.\
                                        fitness_gbest[igroup, :])[0:self.mu]
                    self.fitness_gbest[igroup, :] = self.\
                               fitness_gbest[igroup, indices_population_sorted]
                    self.X_gbest[igroup, :, :] = self.X_gbest[igroup, :,\
                                                   indices_population_sorted].T
            else:
                # receives the best from workers
                #if len(self.nodes)>1:
                fitness_temp = zeros((self.groups, self.popsize))
                X_temp = zeros((self.groups, self.ndimensions, self.popsize))
                ind_data = 0
                # list of incoming tubes, ie from workers
                for node in self.nodes:

                    if node.index != 0:
                        tube = 'to_master_%d' % node.index
                        self.X_lbest, self.fitness_lbest = self.tubes.pop(tube)

                    for igroup in xrange(self.groups):
                        worker_len = len(self.fitness_lbest[igroup, :])
                        fitness_temp[igroup, ind_data:ind_data + worker_len] =\
                                                  self.fitness_lbest[igroup, :]
                        X_temp[igroup, :, ind_data:ind_data + worker_len] =\
                                                     self.X_lbest[igroup, :, :]
                    ind_data = ind_data + worker_len

                for igroup in xrange(self.groups):
                    indices_population_sorted = argsort(fitness_temp[igroup,\
                                                                :])[0:self.mu]
                    self.fitness_gbest[igroup, :] = fitness_temp[igroup,\
                                                    indices_population_sorted]
                    self.X_gbest[igroup, :, :] = X_temp[igroup, :,\
                                                  indices_population_sorted].T

    def communicate_after_update(self):
     ##the workers send their mu best positions and
     ## fitness and the mater receives them
        if self.index > 0:
            # WORKERS
#            log.info("I'm worker #%d" % self.index)
            # receives the updated generation distribution parameters
            to_worker = 'to_worker_%d' % self.index
            # set the new distribution in the CMA class
            (mean, sigma, C, D, B) = self.tubes.pop(to_worker)
            for igroup in xrange(self.groups):
                self.es[igroup].sigma = sigma[igroup, :]
                self.es[igroup].mean = mean[igroup, :]
                self.es[igroup].C = C[igroup, :]
                self.es[igroup].D = D[igroup, :]
                self.es[igroup].B = B[igroup, :]

        else:
            # MASTER
            # sends the updated distribution parameters
            for node in self.nodes:  # list of outcoming tubes, ie to workers
                if node.index == 0:
                    continue
                tube = 'to_worker_%d' % node.index
                self.tubes.push(tube, (self.mean_distr, self.std_distr,\
                                                      self.C, self.D, self.B))

    def find_best_local(self):
        for igroup in xrange(self.groups):
            fitness = self.fitness[igroup * self.subpopsize:(igroup + 1) *\
                                                              self.subpopsize]
            if self.mu <= self.subpopsize:
                indices_population_sorted = argsort(fitness)[0:self.mu]
            else:
                indices_population_sorted = argsort(fitness)
            self.fitness_lbest[igroup, :] = self.fitness[igroup *\
                                   self.subpopsize + indices_population_sorted]
            self.X_lbest[igroup, :, :] = self.X[:, igroup * self.subpopsize +\
                                                     indices_population_sorted]

    def iterate(self, iteration, fitness):
        self.iteration = iteration
        self.fitness = fitness
        # find mu best local
        self.find_best_local()
        # communicate with other nodes
        self.communicate_before_update()
        # updates the particle positions (only on MASTER)
        if self.index == 0:
            for igroup in xrange(self.groups):
                self.es[igroup].tell(self.X_gbest[igroup, :, :].T,\
                                                 self.fitness_gbest[igroup, :])
                self.mean_distr[igroup, :] = self.es[igroup].mean
                self.std_distr[igroup, :] = self.es[igroup].sigma
                self.es[igroup].sigma_iter.append(self.es[igroup].sigma)
                self.es[igroup].iteration = iteration
                self.C[igroup, :] = self.es[igroup].C
                self.D[igroup, :] = self.es[igroup].D
                self.B[igroup, :] = self.es[igroup].B
                ind_best = argmin(self.fitness_gbest[igroup, :])
                best_fitness = min(self.fitness_gbest[igroup, :])
                if self.fitness_best_of_all[igroup] > best_fitness:
                    self.X_best_of_all[igroup, :] = self.X_gbest[igroup, :,\
                                                                     ind_best]
                    self.fitness_best_of_all[igroup] = best_fitness
#                print self.fitness_best_of_all
        # the master send the new distribution parameters,
        # the workers receive them
        self.communicate_after_update()

        if self.return_info:
            self.collect_info()
        #new particules are generated

        for igroup in xrange(self.groups):
            if self.bound_strategy is not 2:
                # get list of new solutions
                temp = self.es[igroup].ask(number=self.subpopsize)
                for k in xrange(self.subpopsize):
                    self.X[:, igroup * self.subpopsize + k] = temp[k]

            else:  # resample until everything is in the boundaries
                temp = self.es[igroup].ask(number=self.subpopsize)
                self.Xtemp = zeros((self.ndimensions, self.subpopsize))
                for k in range(self.subpopsize):
                    self.Xtemp[:, k] = temp[k]

                self.Xtemp_new = maximum(self.Xtemp, self.Xmin[:,\
                                                             :self.subpopsize])
                self.Xtemp_new = minimum(self.Xtemp, self.Xmax[:,\
                                                             :self.subpopsize])
                self.ind_changed_sample = unique(where(self.Xtemp_new !=\
                                                                self.Xtemp)[1])
                self.ind_changed = where(self.Xtemp_new != self.Xtemp)
                #print len(self.ind_changed_sample)
                while len(self.ind_changed_sample) != 0:
                    #print len(self.ind_changed_sample)
                    temp = self.es[igroup].ask(number=len(self.ind_changed[0]))
                    for k in xrange(len(self.ind_changed[0])):
                        self.Xtemp[self.ind_changed[0][k],\
                      self.ind_changed[1][k]] = temp[k][self.ind_changed[0][k]]
                    self.Xtemp_new = maximum(self.Xtemp,\
                                                self.Xmin[:, :self.subpopsize])
                    self.Xtemp_new = minimum(self.Xtemp,\
                                                self.Xmax[:, :self.subpopsize])
                    self.ind_changed_sample = unique(where(self.Xtemp_new !=\
                                                                self.Xtemp)[1])
                    self.ind_changed = where(self.Xtemp_new != self.Xtemp)
                self.X[:, igroup * self.subpopsize:(igroup + 1) *\
                                            self.subpopsize] = self.Xtemp_new

    def pre_fitness(self):
        if self.bound_strategy == 1:
            if any(self.boundaries[:, 0] != -inf) or\
                                            any(self.boundaries[:, 1] != inf):
                self.Xold = self.X
                self.X = maximum(self.X, self.Xmin)
                self.X = minimum(self.X, self.Xmax)
                self.ind_changed = unique(where(self.X != self.Xold)[1])
                #print len(self.ind_changed)

    def post_fitness(self, fitness):
        #print fitness
        if self.bound_strategy == 1:
            if any(self.boundaries[:, 0] != -inf) or\
                                             any(self.boundaries[:, 1] != inf):
                if len(self.ind_changed) is not 0:
                    fitness[self.ind_changed] = fitness[self.ind_changed] +\
                                      self.alpha[0] * linalg.norm(self.Xold[:,\
                        self.ind_changed] - self.X[:, self.ind_changed]) ** 2
                self.X = self.Xold

        return fitness

    def collect_info(self):
        for igroup in xrange(self.groups):
            if self.index == 0:  # only mater info
                self.best_fitness[igroup, self.iteration] = \
                                            self.fitness_best_of_all[igroup]
                self.dist_std[igroup, :, self.iteration] =\
                                                   self.std_distr[igroup, :]
                if self.scaling == None:
                    self.dist_mean[igroup, :, self.iteration] =\
                                                   self.mean_distr[igroup, :]
                    self.best_particule[igroup, :, self.iteration] =\
                                                self.X_best_of_all[igroup, :]
                else:
                    self.dist_mean[igroup, :, self.iteration] =\
                                         self.parameters.unscaling_func(self.\
                                                        mean_distr[igroup, :])
                    self.best_particule[igroup, :, self.iteration] =\
                                         self.parameters.unscaling_func(self.\
                                                     X_best_of_all[igroup, :])

    def get_info(self):
        info = list()
        if self.return_info:
            for igroup in xrange(self.groups):
                temp = dict()
                temp['dist_std'] = squeeze(self.dist_std[igroup, 0, :])
                temp['dist_mean'] = squeeze(self.dist_mean[igroup, :, :])
                temp['best_fitness'] = squeeze(self.best_fitness[igroup, :])
                temp['best_position'] = squeeze(self.\
                                               best_particule[igroup, :, :])
                info.append(temp)
        return info

    def get_result(self):
        best_position = list()
        best_fitness = list()
        self.scaling = None
        for igroup in xrange(self.groups):
            if self.index == 0:
                best_position.append(self.X_best_of_all[igroup, :])
                best_fitness.append(self.fitness_best_of_all[igroup])
            else:
                best_position, best_fitness = [], []
        return (best_position, best_fitness)

########NEW FILE########
__FILENAME__ = cma_utils

# Copyright 2008, Nikolaus Hansen.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License, version 2,
#    as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import numpy as nu
from numpy import array, log, sqrt, sum


# __all__ = ['fmin', 'CMAEvolutionStrategy', 'plotdata', ...]  # TODO

class _Struct(dict):
# class Bunch(dict):    # struct and dictionary
    def __init__(self, **kw):
        dict.__init__(self, kw)
        self.__dict__ = self


class _GenoPheno(object):
    """Genotype-phenotype transformation for convenient scaling.
    """
    def pheno(self, x):
        y = array(x)
        if self.scales != 1:   # just for efficiency
            y = self.scales * y
            # print 'transformed to phenotyp'
        if self.typical_x != 0:
            y = y + self.typical_x
        return y

    def geno(self, y):
        x = array(y)
        if self.typical_x != 0:
            x = x - self.typical_x
        if self.scales != 1:   # just for efficiency
            x = x / self.scales   # for each element in y
        return x

    def __init__(self, scaling=None, typical_x=None):
        if nu.size(scaling) > 1 or scaling:
            self.scales = scaling    # CAVE: is not a copy
        else:
            self.scales = 1

        if nu.size(typical_x) > 1 or typical_x:
            self.typical_x = typical_x
        else:
            self.typical_x = 0


def defaultOptions(tolfun=1e-12,  # prefered termination criterion
           tolfunhist=0,
           tolx=1e-11,
           tolfacupx=1e3,  # terminate on divergent behavior
           ftarget=-nu.inf,   # target function value
           maxiter='long(1e3 * N ** 2/sqrt(popsize))',
           maxfevals=nu.inf,
           evalparallel=False,   # not too useful so far
           termination_callback=None,
           verb_disp=100,
           verb_log=1,
           verb_filenameprefix='outcmaes',
           verb_append=0,
           popsize='4+int(3 * log(N))',
           restarts=0,
           incpopsize=2,
           updatecovwait=None,   # TODO: rename: updatedistribution?
           seed=None,
           CMAon=True,
           CMAdiagonal='0 * 100 * N/sqrt(popsize)',
           CMAmu=None,     # default is lambda/2,
           CMArankmu=True,
           CMArankmualpha=0.3,
           CMAteststds=None,
           CMAeigenmethod=0,
           noise_reevalfrac=0.0,   # 0.05, not yet working
           noise_eps=1e-7,
           scaling_of_variables=None,
           typical_x=None):

    opts = locals()
    return opts  # assembles the keyword-arguments in a dictionary


def _evalOption(o, default, loc=None):
    """Evaluates input o as option in environment loc
    """
    if o == str(o):
        val = eval(o, globals(), loc)
    else:
        val = o
    if val in (None, (), [], ''):   # TODO: {} in the list gives an error
        val = eval(str(default), globals(), loc)
    return val

#____________________________________________________________
#____________________________________________________________
#


class CMAEvolutionStrategy(object):
    """CMA-ES stochastic optimizer class with ask-and-tell interface

    """

    def __init__(self, x0, sigma0, inopts={}):
        """
        :Parameters:
            x0 -- initial solution, starting point
            sigma0 -- initial standard deviation.  The problem
                variables should have been scaled, such that a single
                standard deviation on all variables is useful and the
                optimum is expected to lie within x0 +- 3 * sigma0.
            inopts -- options, a dictionary according to the parameter list
              of function fmin(), see there and defaultOptions()
        """

        #____________________________________________________________
        self.inargs = locals().copy()
        del self.inargs['self']
        self.inopts = inopts
        defopts = defaultOptions()
        opts = defopts.copy()
        if inopts:
            if not isinstance(inopts, dict):
                raise Exception('options argument must be a dict')
            for key in inopts.keys():
                opts[key] = inopts[key]

        if x0 == str(x0):
            self.mean = array(eval(x0))
        else:
            self.mean = array(x0, copy=True)
        self.x0 = self.mean.copy()

        if self.mean.ndim != 1:
            pass

        self.N = self.mean.shape[0]
        N = self.N
        self.mean.resize(N)  # 1-D array
        self.sigma = sigma0

        popsize = _evalOption(opts['popsize'], defopts['popsize'], locals())

        # extract/expand options
        for key in opts.keys():
            if key.find('filename') < 0:
                opts[key] = _evalOption(opts[key], defopts[key], locals())
            elif not opts[key]:
                opts[key] = defopts[key]

        self.opts = opts

        self.gp = _GenoPheno(opts['scaling_of_variables'], opts['typical_x'])
        self.mean = self.gp.geno(self.mean)
        self.fmean = 0.              # TODO name should change?
        self.fmean_noise_free = 0.   # for output only

        self.sp = self._computeParameters(N, popsize, opts)
        self.sp0 = self.sp

        # initialization of state variables
        self.countiter = 0
        self.countevals = 0
        self.ps = nu.zeros(N)
        self.pc = nu.zeros(N)

        stds = nu.ones(N)
        if self.opts['CMAteststds'] not in (None, (), []):
            stds = self.opts['CMAteststds']
            if nu.size(stds) != N:
                pass
        if self.opts['CMAdiagonal'] > 0:
            self.B = array(1)
            self.C = stds ** 2
        else:
            self.B = nu.eye(N)
            self.C = nu.diag(stds ** 2)
        self.D = stds
        self.dC = nu.diag(self.C)

        self.flgtelldone = True
        self.itereigenupdated = self.countiter
        self.noiseS = 0   # noise "signal"
        self.hsiglist = []
        self.opts_in = inopts

        if opts['seed'] is None:
            nu.random.seed()
            opts['seed'] = 1e9 * nu.random.rand()
        opts['seed'] = int(opts['seed'])
        nu.random.seed(opts['seed'])

        out = {}
        # out.best = _Struct()
        out['best_f'] = nu.inf
        out['best_x'] = []
        out['best_evals'] = 0
        out['hsigcount'] = 0
        self.out = out

        self.const = _Struct()
        self.const.chiN = N ** 0.5 * (1 - 1. / (4. * N) + 1. / (21. * N ** 2))
                      #   ||N(0, I)|| == norm(randn(N, 1))
                                      # normalize recombination weights array

        # attribute for stopping criteria in function stop
        self.stoplastiter = 0
        self.manualstop = 0
        self.fit = _Struct()
        self.fit.fit = []    # not really necessary
        self.fit.hist = []

#        if self.opts['verb_log'] > 0 and not self.opts['verb_append']:
#            self.writeHeaders()
#            self.writeOutput()
        if self.opts['verb_append'] > 0:
            self.countevals = self.opts['verb_append']

        # say hello
        if opts['verb_disp'] > 0:
            if self.sp.mu == 1:
                print '(%d, %d)-CMA-ES' % (self.sp.mu, self.sp.popsize),
            else:
                print '(%d_w, %d)-CMA-ES' % (self.sp.mu, self.sp.popsize),
            print '(mu_w=%2.1f, w_1=%d%%)' % (self.sp.mueff, int(100 *\
                                                         self.sp.weights[0])),
            print 'in dimension %d ' % N  # + func.__name__
            if opts['CMAdiagonal'] and self.sp.CMAon:
                s = ''
                if opts['CMAdiagonal'] is not True:
                    s = ' for '
                    if opts['CMAdiagonal'] < nu.inf:
                        s += str(int(opts['CMAdiagonal']))
                    else:
                        s += str(nu.floor(opts['CMAdiagonal']))
                    s += ' iterations'
                    s += ' (1/ccov=' + str(round(1. / (self.sp.c1 + \
                                                        self.sp.cmu))) + ')'
                print '   Covariance matrix is diagonal' + s

    #____________________________________________________________
    #____________________________________________________________

    def _getmean(self):
        """mean value of the sample distribution, this is not a copy.
        """
        return self.mean

    def _setmean(self, m):
        """mean value setter, does not copy
        """
        self.mean = m

    #____________________________________________________________
    #____________________________________________________________
    def ask(self, number=None, xmean=None, sigma=1):
        """Get new candidate solutions, sampled from a multi-variate
           normal distribution.
        :Parameters:
            number -- number of returned solutions, by default the
                population size popsize (AKA lambda).
            xmean -- sequence of distribution means, if
               number > len(xmean) the last entry is used for the
               remaining samples.
            sigma -- multiplier for internal sample width (standard
               deviation)
        :Returns:
            sequence of N-dimensional candidate solutions to be evaluated
        :Example:
            X = es.ask()  # get list of new solutions
            fit = []
            for x in X:
                fit.append(cma.fcts.rosen(x))  # call func rosen
            es.tell(X, fit)
        """
        #________________________________________________________
        #
        def gauss(N):
            r = nu.random.randn(N)
            # r = r * sqrt(N / sum(r ** 2))
            return r

        #________________________________________________________
        #
        if number is None or number < 1:
            number = self.sp.popsize
        if xmean is None:
            xmean = self.mean
        sigma = sigma * self.sigma

##        sample distribution
        self.pop = []
        if self.flgtelldone:   # could be done in tell()!?
            self.flgtelldone = False
            self.ary = []

        for k in xrange(number):
            # use mirrors for mu=1
            if self.sp.mu == 1 and nu.mod(len(self.ary), 2) == 1:
                self.ary.append(-self.ary[-1])
            # regular sampling
            elif 1 < 2 or self.N > 40:
                self.ary.append(nu.dot(self.B, self.D * gauss(self.N)))
            # sobol numbers, quasi-random, derandomized, not in use
            else:
                if self.countiter == 0 and k == 0:
                    pass

            self.pop.append(self.gp.pheno(xmean + sigma * self.ary[-1]))

        return self.pop

    #____________________________________________________________
    #____________________________________________________________
    #
    def _updateBD(self):
        # itereigenupdated is always up-to-date in the diagonal case
        # just double check here
        if self.itereigenupdated == self.countiter:
            return

        self.C = 0.5 * (self.C + self.C.T)
        if self.opts['CMAeigenmethod'] == -1:
            if 1 < 3:  # import pygsl on the fly
                if self.opts['CMAeigenmethod'] == -1:
                    pass

            else:  # assumes pygsl.eigen was imported above
                pass

            idx = nu.argsort(self.D)
            self.D = self.D[idx]
            # self.B[i] is the i+1-th row and not an eigenvector
            self.B = self.B[:, idx]

        elif self.opts['CMAeigenmethod'] == 0:
            # self.B[i] is a row and not an eigenvector
            self.D, self.B = nu.linalg.eigh(self.C)
            idx = nu.argsort(self.D)
            self.D = self.D[idx]
            self.B = self.B[:, idx]
        else:   # is overall two;ten times slower in 10;20-D
            pass
        if 11 < 3 and any(abs(sum(self.B[:, 0:self.N - 1] *\
                                                  self.B[:, 1:], 0)) > 1e-6):
            print 'B is not orthogonal'
            #print self.D
            print sum(self.B[:, 0:self.N - 1] * self.B[:, 1:], 0)
        else:
            pass
        self.D **= 0.5
        self.itereigenupdated = self.countiter

    #

    def readProperties(self):
        """reads dynamic parameters from property file
        """
        print 'not yet implemented'

    #____________________________________________________________
    #____________________________________________________________
    def _computeParameters(self, N, popsize, opts, ccovfac=1, verbose=True):
        """Compute strategy parameters mainly depending on
        population size """
        #____________________________________________________________
        # learning rates cone and cmu as a function
        # of the degrees of freedom df
        def cone(df, mu, N):
            return 1. / (df + 2. * sqrt(df) + float(mu) / N)

        def cmu(df, mu, alphamu):
            return (alphamu + mu - 2. + 1. / mu) / (df + 4. *\
                                                         sqrt(df) + mu / 2.)

        #____________________________________________________________
        sp = _Struct()  # just a hack
        sp.popsize = int(popsize)
        sp.mu_f = sp.popsize / 2.0   # float value of mu

        if opts['CMAmu'] != None:
            sp.mu_f = opts['CMAmu']

        sp.mu = int(sp.mu_f + 0.49999)  # round down for x.5
        sp.weights = log(sp.mu_f + 0.5) - log(1. + nu.arange(sp.mu))
        sp.weights /= sum(sp.weights)
        sp.mueff = 1. / sum(sp.weights ** 2)
        sp.cs = (sp.mueff + 2) / (N + sp.mueff + 3)
        sp.cc = 4. / (N + 4.)
        sp.cc_sep = sp.cc
        sp.rankmualpha = _evalOption(opts['CMArankmualpha'], 0.3)
        sp.c1 = ccovfac * min(1, sp.popsize / 6) * cone((N ** 2 + N) /\
                                                               2, sp.mueff, N)
        sp.c1_sep = ccovfac * cone(N, sp.mueff, N)
        if -1 > 0:
            sp.c1 = 0.
            print 'c1 is zero'
        if opts['CMArankmu'] != 0:   # also empty
            sp.cmu = min(1 - sp.c1, ccovfac * cmu((N ** 2 + N) /\
                                                  2, sp.mueff, sp.rankmualpha))
            sp.cmu_sep = min(1 - sp.c1_sep, ccovfac *\
                                              cmu(N, sp.mueff, sp.rankmualpha))
        else:
            sp.cmu = sp.cmu_sep = 0

        sp.CMAon = sp.c1 + sp.cmu > 0
        # print sp.c1_sep / sp.cc_sep

        if not opts['CMAon'] and opts['CMAon'] not in (None, [], ()):
            sp.CMAon = False
            # sp.c1 = sp.cmu = sp.c1_sep = sp.cmu_sep = 0
        sp.damps = (1 + 2 * max(0, sqrt((sp.mueff - 1) / (N + 1)) - 1)) + sp.cs
        if 11 < 3:
            sp.damps = 30 * sp.damps
            print 'damps is', sp.damps
        sp.kappa = 1
        if sp.kappa != 1:
            print '  kappa =', sp.kappa
        if verbose:
            if not sp.CMAon:
                print 'covariance matrix adaptation turned off'
            if opts['CMAmu'] != None:
                pass
                #print 'mu =', sp.mu_f

        return sp   # the only existing reference to sp is passed here

    #____________________________________________________________
    #____________________________________________________________
    #____________________________________________________________
    #____________________________________________________________

    def tell(self, points, function_values, function_values_reevaluated=None):
        """Pass objective function values to CMA-ES to prepare for next
        iteration

        :Arguments:
           points -- list or array of candidate solution points,
              most presumably before delivered by method ask().
           function_values -- list or array of objective function values
              associated to the respective points. Beside termination
              decisions, only the ranking of values in function_values
              is used.
        :Details: tell() updates the parameters of the multivariate
            normal search distribtion, namely covariance matrix and
            step-size and updates also the number of function evaluations
            countevals.
        """
    #____________________________________________________________

        lam = len(points)
        pop = self.gp.geno(points)
#        print pop.shape
        if lam != array(function_values).shape[0]:
            pass
        if lam < 3:
            raise Exception('population is too small')
        N = self.N
        if lam != self.sp.popsize:
            #print 'WARNING: population size has changed'
            # TODO: when the population size changes, sigma
            #    should have been updated before
            self.sp = self._computeParameters(N, lam, self.opts)
        sp = self.sp

        self.countiter += 1   # >= 1 now
        self.countevals += sp.popsize
        flgseparable = self.opts['CMAdiagonal'] is True \
                       or self.countiter <= self.opts['CMAdiagonal']
        if not flgseparable and len(self.C.shape) == 1:
            self.B = nu.eye(N)  # identity(N)
            self.C = nu.diag(self.C)
            idx = nu.argsort(self.D)
            self.D = self.D[idx]
            self.B = self.B[:, idx]

        fit = self.fit   # make short cut
        fit.idx = nu.argsort(function_values)
        fit.fit = array(function_values)[fit.idx]

        fit.hist.insert(0, fit.fit[0])
        if len(fit.hist) > 10 + 30 * N / sp.popsize:
            fit.hist.pop()

        # compute new mean and sort pop
        mold = self.mean
        pop = array(pop)[fit.idx]  # only arrays can be multiple indexed
        self.mean = mold + self.sp.kappa ** -1 * \
                    (sum(sp.weights * array(pop[0:sp.mu]).T, 1) - mold)

        # evolution paths
        self.ps = (1 - sp.cs) * self.ps + \
                  (sqrt(sp.cs * (2 - sp.cs) * sp.mueff) / self.sigma) \
                  * nu.dot(self.B, (1. / self.D) * nu.dot(self.B.T,
                                        self.sp.kappa * (self.mean - mold)))

        # "hsig"
        hsig = (sqrt(sum(self.ps ** 2)) / sqrt(1 - (1 - sp.cs) ** (2 *\
                                                            self.countiter))
                / self.const.chiN) < 1.4 + 2. / (N + 1)

        if 11 < 3:   # diagnostic data
            self.out['hsigcount'] += 1 - hsig
            if not hsig:
                self.hsiglist.append(self.countiter)
        if 11 < 3:   # diagnostic message
            if not hsig:
                print self.countiter, ': hsig-stall'
        if 11 < 3:   # for testing purpose
            hsig = 1
            if self.countiter == 1:
                print 'hsig=1'
        cc = sp.cc
        if flgseparable:
            cc = sp.cc_sep

        self.pc = (1 - cc) * self.pc + \
                  hsig * sqrt(cc * (2 - cc) * sp.mueff) \
                  * self.sp.kappa * (self.mean - mold) / self.sigma

        # covariance matrix adaptation

#        print self.sigma_iter
        #sp.CMAon=False

        if self.iteration > 60:
            if self.sigma_iter[self.iteration][0] -\
                              self.sigma_iter[self.iteration - 60][0] < 10e-12:
                sp.CMAon = False

        if sp.CMAon:
            assert sp.c1 + sp.cmu < sp.mueff / N
            # default full matrix case
            if not flgseparable:
                Z = (pop[0:sp.mu] - mold) / self.sigma
                if 11 < 3:
                    # TODO: here optional the Suttorp update

                    # CAVE: how to integrate the weights
                    self.itereigenupdated = self.countiter
                else:
                    Z = nu.dot((sp.cmu * sp.weights) * Z.T, Z)
                    if 11 > 3:  # 3 to 5 times slower
                        Z = nu.zeros((N, N))
                        for k in xrange(sp.mu):
                            z = (pop[k] - mold)
                            Z += nu.outer((sp.cmu * sp.weights[k] /\
                                                       self.sigma ** 2) * z, z)
                    self.C = (1 - sp.c1 - sp.cmu) * self.C + \
                             nu.outer(sp.c1 * self.pc, self.pc) + Z
                    self.dC = nu.diag(self.C)

            else:  # separable/diagonal linear case
                c1, cmu = sp.c1_sep, sp.cmu_sep
                assert(c1 + cmu <= 1)
                Z = nu.zeros(N)
                for k in xrange(sp.mu):
                    z = (pop[k] - mold) / self.sigma   # TODO see above
                    Z += sp.weights[k] * z * z   # is 1-D
                self.C = (1 - c1 - cmu) * self.C + c1 * self.pc *\
                                                            self.pc + cmu * Z

                self.dC = self.C
                self.D = sqrt(self.C)   # C is a 1 - D array
                self.itereigenupdated = self.countiter

        # step-size adaptation, adapt sigma
        self.sigma *= nu.exp(min(1, (sp.cs / sp.damps) *
                                (sqrt(sum(self.ps ** 2)) /\
                                                         self.const.chiN - 1)))
        self.flgtelldone = True
        self._updateBD()

########NEW FILE########
__FILENAME__ = ga
from ..synchandler import *
from ..debugtools import *
from optimization import *
from algorithm import *
from numpy import inf, zeros, tile, nonzero, \
maximum, minimum, ceil, floor, argsort, array, \
sort, mod, cumsum, sum, arange, ones, argmin, squeeze
from numpy.random import rand, randint, randn

__all__ = ['GA']


class GA(OptimizationAlgorithm):
    """
    Standard genetic algorithm.
    See the
    `wikipedia entry on GA <http://en.wikipedia.org/wiki/Genetic_algorithm>`__

    If more than one worker is used, it works in an island topology, i.e. as a
    coarse - grained parallel genetic algorithms which assumes
    a population on each of the computer nodes and migration of individuals
    among the nodes.

    Optimization parameters:

    ``proportion_parents = 1``
        proportion (out of 1) of the entire population taken
        as potential parents.

    ``migration_time_interval = 20``
           whenever more than one worker is used, it is the number of
           iteration at which a migration happens.
           (note for different groups case: this parameter can only have
           one value, i.e. every group will have the same value
           (the first of the list))

    ``proportion_migration = 0.2``
          proportion (out of 1) of the island population that will migrate to
          the next island (the best one) and also the worst that will be
          replaced by the best of the previous island. (note for different
          groups case: this parameter can only have one value, i.e. every group
          will have the same value (the first of the list))


    ``proportion_xover = 0.65``
        proportion (out of 1) of the entire population which will
        undergo a cross over.

    ``proportion_elite = 0.05``
        proportion (out of 1) of the entire population which will be kept
        for the next generation based on their best fitness.

        The proportion of mutation is automatically set to
         ``1 - proportion_xover - proportion_elite``.

    ``func_selection = 'stoch_uniform'``
        This function define the way the parents are chosen
        (it is the only one available). It lays out a line in
        which each parent corresponds to a section of the line of length
        proportional to its scaled value. The algorithm moves along the
        line in steps of equal size. At each step, the algorithm allocates
        a parent from the section it lands on. The first step is
        a uniform random number less than the step size.


    ``func_xover = 'intermediate'``

        ``func_xover`` specifies the function that performs the crossover.
         The following ones are available:

        * `intermediate`: creates children by taking a random weighted average
           of the parents. You can specify the weights by a single parameter,
           ``ratio_xover`` (which is 0.5 by default). The function creates the
           child from parent1 and parent2 using the  following formula::

              child = parent1 + rand * Ratio * ( parent2 - parent1)

        * `discrete_random`: creates a random binary vector and selects the
           genes where the vector is a 1 from the first parent, and the gene
           where the vector is a 0 from the second parent, and combines the
           genes to form the child.

        * `one_point`: chooses a random integer n between 1 and ndimensions
          and then selects vector entries numbered less than or equal to n
          from the first parent. It then Selects vector entries numbered
          greater than n from the second parent. Finally, it concatenates
          these entries to form a child vector.

        * `two_points`: it selects two random integers m and n between 1 and
           ndimensions. The function selects vector entries numbered less than
           or equal to m from the first parent. Then it selects vector entries
           numbered from m + 1 to n, inclusive, from the second parent. Then
           it selects vector entries numbered greater than n from the first
           parent. The algorithm then concatenates these genes to form
           a single gene.

        * `heuristic`: returns a child that lies on the line containing the two
          parents, a small distance away from the parent with the better
          fitness value in the direction away from the parent with the worse
          fitness value. You can specify how far the child is from the
          better parent by the parameter ``ratio_xover``
          (which is 0.5 by default)

        * `linear_combination`: creates children that are linear combinations
          of the two parents with  the parameter ``ratio_xover``
          (which is 0.5 by default and should be between 0 and 1)::

              child = parent1 + Ratio * ( parent2 - parent1)

          For  ``ratio_xover = 0.5`` every child is an arithmetic mean of
          two parents.

    ``func_mutation = 'gaussian'``

        This function define how the genetic algorithm makes small random
        changes in the individuals in the population to create mutation
        children. Mutation provides genetic diversity and enable the genetic
        algorithm to search a broader space. Different options are available:

        * `gaussian`: adds a random number taken from a Gaussian distribution
          with mean 0 to each entry of the parent vector.

          The 'scale_mutation' parameter (0.8 by default) determines the
          standard deviation at the first generation by
          ``scale_mutation * (Xmax - Xmin)`` where
          Xmax and Xmin are the boundaries.

          The 'shrink_mutation' parameter (0.2 by default) controls how the
          standard deviation shrinks as generations go by::

              :math:`sigma_{i} = \sigma_{i-1}(1-shrink_{mutation} * i/maxiter)`
              at iteration i.

        * `uniform`: The algorithm selects a fraction of the vector entries of
          an individual for mutation, where each entry has a probability
          ``mutation_rate`` (default is 0.1) of being mutated. In the second
          step, the algorithm replaces each selected entry by a random number
          selected uniformly from the range for that entry.

    """
    @staticmethod
    def default_optparams():
        """
        Returns the default values for optparams
        """
        optparams = dict()
        optparams['proportion_elite'] = 0.05
        # proportion_mutation + proportion_xover + proportion_elite = 1
        optparams['proportion_xover'] = 0.65
        optparams['func_scale'] = 'ranking'
        optparams['func_selection'] = 'stoch_uniform'
        optparams['func_xover'] = 'intermediate'
        optparams['func_mutation'] = 'uniform'
        optparams['scale_mutation'] = 0.8
        optparams['shrink_mutation'] = 0.02
        optparams['mutation_rate'] = 0.1
        optparams['migration_time_interval'] = 20
        optparams['proportion_migration'] = 0.2
        optparams['proportion_parents'] = 1
        optparams['ratio_xover'] = 0.5
        return optparams

    @staticmethod
    def get_topology(node_count):
        topology = []
        # 0 is the master, 1..n are the workers
        if node_count > 1:
            for i in xrange(0, node_count):
                topology.extend([('to_next_island_%d' %\
                i, i, mod(i + 1, node_count))])
        return topology

    def initialize(self):
        """
        Initializes the optimization algorithm. X is the
        matrix of initial particle positions.
        X.shape == (ndimensions, nparticles)
        """
        self.time_from_last_migration = 1
        self.fitness_best_of_all = inf

        self.D = self.ndimensions
        self.N = self.subpopsize
        self.nbr_elite = ceil(array(self.optparams['proportion_elite'])\
                                                  * self.N).astype('int')
        self.nbr_xover = floor(array(self.optparams['proportion_xover'])\
                                                   * self.N).astype('int')
        self.mutation_rate = self.optparams['mutation_rate']
        self.nbr_mutation = self.N - self.nbr_elite - self.nbr_xover
        self.nbr_offspring = self.nbr_xover + self.nbr_mutation
        self.nbr_migrants = int(ceil(self.N *\
                               self.optparams['proportion_migration'][0]))
        self.nbr_parents = self.N
        self.migration_time_interval = \
                         int(self.optparams['migration_time_interval'][0])

        if self.scaling == None:
            self.Xmin = tile(self.boundaries[:, 0].\
                              reshape(self.ndimensions, 1), (1, self.nodesize))
            self.Xmax = tile(self.boundaries[:, 1].\
                              reshape(self.ndimensions, 1), (1, self.nodesize))
        else:
            self.Xmin = tile(self.parameters.\
                                scaling_func(self.boundaries[:, 0]).\
                              reshape(self.ndimensions, 1), (1, self.nodesize))
            self.Xmax = tile(self.parameters.\
                               scaling_func(self.boundaries[:, 1]).\
                              reshape(self.ndimensions, 1), (1, self.nodesize))

        # Preparation of the optimization algorithm
        self.fitness_lbest = inf * ones(self.subpopsize)
        self.fitness_gbest = [inf] * ones(self.groups)
        self.X_lbest = zeros((self.groups, self.ndimensions, self.subpopsize))
        self.X_gbest = zeros((self.groups, self.ndimensions))
        self.best_fitness = zeros((self.groups, self.maxiter))
        self.best_particule = zeros((self.groups,\
                                              self.ndimensions, self.maxiter))
        self.X_best_of_all = zeros((self.groups, self.ndimensions))
        self.fitness_best_of_all = [inf] * ones(self.groups)
        self.X_migrants = zeros((self.ndimensions, self.nbr_migrants *\
                                                                 self.groups))
        self.fitness_migrants = zeros(self.nbr_migrants * self.groups)
        self.sigmaMutation = zeros(self.groups)
        for igroup in xrange(self.groups):
            if  self.optparams['func_mutation'][igroup] == 'gaussian':

                Xmin = self.boundaries[:, 0]
                Xmax = self.boundaries[:, 1]
                if (Xmin != -inf * ones(self.D)).any() and (Xmax != inf *\
                                                           ones(self.D)).any():
                    self.sigmaMutation[igroup] = self.\
                            optparams['scale_mutation'][igroup] * (Xmax - Xmin)
                else:      # if boudneries are infinite
                    self.sigmaMutation[igroup] = self.\
                                 optparams['scale_mutation'][igroup] * 1000
#                                 (self.parameters.scaling_factor_b -\
#                                  self.parameters.scaling_factor_a))

    def communicate(self):
        #there is communication only if there are several island
        if len(self.nodes) > 1:

            # sends the  best local position
            # and their fitness to the next neighbouring island
            to_next_island = 'to_next_island_%d' % self.index
            self.tubes.push(to_next_island, (self.X_migrants,\
                                                        self.fitness_migrants))

            # receive the best from the previous neighbouring island
            # (take the next island tude of the previous island)
            from_previous_island = 'to_next_island_%d' %\
                                           mod(self.index - 1, len(self.nodes))
            a, b = self.tubes.pop(from_previous_island)
            for igroup in xrange(self.groups):
                self.X[:, (igroup + 1) * self.subpopsize -\
                           self.nbr_migrants:(igroup + 1) * self.subpopsize] =\
                           a[:, igroup * self.nbr_migrants:(1 + igroup) *\
                           self.nbr_migrants]
                self.fitness[(igroup + 1) * self.subpopsize -\
                           self.nbr_migrants:(igroup + 1) * self.subpopsize] =\
                            b[igroup * self.nbr_migrants:(1 + igroup) *\
                            self.nbr_migrants]
        else:
            pass

    def iterate(self, iteration, fitness):

        self.iteration = iteration
        self.fitness = fitness
        # resort the population from best to worst
        for igroup in xrange(self.groups):
            fitness = self.fitness[igroup * self.subpopsize:(igroup + 1) *\
                                                               self.subpopsize]
            indices_Population_sorted = argsort(fitness)
            self.X[:, igroup * self.subpopsize:(igroup + 1) *\
                                         self.subpopsize] = self.X[:, igroup *\
                                   self.subpopsize + indices_Population_sorted]
            self.fitness[igroup * self.subpopsize:(igroup + 1) *\
                                      self.subpopsize] = self.fitness[igroup *\
                                  self.subpopsize + indices_Population_sorted]

        #migrate if if it is time to do so
        #(communicate does smth if  there is more than one worker)
        if len(self.nodes) > 1:
            if  self.time_from_last_migration == self.migration_time_interval:
                for igroup in xrange(self.groups):
                    self.X_migrants[:, igroup *\
                        self.nbr_migrants:(igroup + 1) * self.nbr_migrants] =\
                                  self.X[:, igroup * self.subpopsize:igroup *\
                                  self.subpopsize + self.nbr_migrants]
                    self.fitness_migrants[igroup *\
                                   self.nbr_migrants:(igroup + 1) *\
                                   self.nbr_migrants] = self.fitness[igroup *\
                                   self.subpopsize:igroup * self.subpopsize +\
                                   self.nbr_migrants]

                self.communicate()
                self.time_from_last_migration = 0
                #print 'migration happened!'
            else:
                self.time_from_last_migration += 1

        for igroup in xrange(self.groups):
            self.igroup = igroup
            self.X_group = self.X[:, igroup * self.subpopsize:(igroup + 1) *\
                                                             self.subpopsize]
            self.fitness_group = self.fitness[igroup *\
                               self.subpopsize:(igroup + 1) * self.subpopsize]
            ##rescale fitness
            self.fitness_scaled = self.scale_fitness()
             ### select parents ######
            self.parents_indices = self.select_parents()
            #compute the island elite from the fitness
            # that has been just computed for X
            self.fitness_lElite, self.X_lElite, self.X_bestIsland,\
                                  self.fitness_bestIsland = self.find_elite()
            ind_best = argmin(self.fitness_group)
            if self.fitness_best_of_all[igroup] > self.fitness_group[ind_best]:
                self.X_best_of_all[igroup, :] = self.X_group[:, ind_best]
                self.fitness_best_of_all[igroup] =\
                                                   self.fitness_group[ind_best]

            ## reproduction: recombine parents with xover and mutation
            self.X[:, igroup * self.subpopsize:(igroup + 1) *\
                                           self.subpopsize] = self.recombine()

#        print self.fitness_best_of_all

        self.collect_info()

        # Boundary checking
        self.X = maximum(self.X, self.Xmin)
        self.X = minimum(self.X, self.Xmax)

    def collect_info(self):
        for igroup in xrange(self.groups):
            self.best_fitness[igroup, self.iteration] = \
                                               self.fitness_best_of_all[igroup]
            self.best_particule[igroup, :, self.iteration] =\
                                                  self.X_best_of_all[igroup, :]

    def get_info(self):
        info = list()
        if self.return_info is True:
            for igroup in xrange(self.groups):
                temp = dict()
                temp['best_fitness'] = squeeze(self.best_fitness[igroup, :])
                temp['best_position'] =\
                                    squeeze(self.best_particule[igroup, :, :])

                info.append(temp)
        return  info

#    def get_result(self):
#        return self.X_best_of_all, self.fitness_best_of_all

    def scale_fitness(self):
        ### rescale the fitness values of the entire population###
        if self.optparams['func_scale'][self.igroup] == 'ranking':
            fitness_scaled = arange(self.N, 0, -1.)
        return fitness_scaled

    def select_parents(self):
        #In a strict generational replacement scheme
        #the size of the mating pool is always equal
        #to the size of the population.

        ### Stochastic univerasl uniform
        if self.optparams['func_selection'][self.igroup] == 'stoch_uniform':
            # wheel has the length of the entire population
            wheel = cumsum(self.fitness_scaled / sum(self.fitness_scaled))
            parents_indices = zeros((self.nbr_parents), 'int')
            stepSize = 1. / self.nbr_parents
            position = rand(1) * stepSize
            lowest = 1

            for iparent in range((self.nbr_parents)):
                # find the wheel position
                for ipos in arange(lowest, wheel.shape[0]):
                    # if the step fall in this chunk ipos of the wheel
                    if(position < wheel[ipos]):
                        parents_indices[iparent] = ipos
                        lowest = ipos
                        break
                position = position + stepSize

        return parents_indices

    def find_elite(self):
        fitness_lElite = self.fitness_group[:self.nbr_elite[self.igroup]]
        X_lElite = self.X_group[:, :self.nbr_elite[self.igroup]]
        fitness_bestIsland = self.fitness_group[0]
        X_bestIsland = self.X_group[:, 0]
        return fitness_lElite, X_lElite, X_bestIsland, fitness_bestIsland

    def recombine(self):
        Xnew = zeros((self.D, self.N))
        Xnew = self.do_crossover(Xnew)
        Xnew = self.do_mutation(Xnew)
        Xnew = self.include_elite(Xnew)
        return Xnew

    def do_crossover(self, Xnew):
        ### CROSSOVER
        if self.optparams['func_xover'][self.igroup] == 'discrete_random':
            for ixover in range(self.nbr_xover[self.igroup]):
                parent1_ind = self.parents_indices[randint(self.nbr_parents,\
                                                                    size=1)[0]]
                parent2_ind = parent1_ind
                # make sure the two parents are not the same
                while parent1_ind == parent2_ind:
                    parent2_ind = self.parents_indices[randint(\
                                                  self.nbr_parents, size=1)[0]]
                vec = randint(0, 2, self.D)
                Xnew[nonzero(vec), ixover] = self.X_group[nonzero(vec),\
                                                                   parent1_ind]
                vec = abs(vec - 1)
                Xnew[nonzero(vec), ixover] = self.X_group[nonzero(vec),\
                                                                   parent2_ind]

        if self.optparams['func_xover'][self.igroup] == 'one_point':
            for ixover in range(self.nbr_xover[self.igroup]):
                parent1_ind = self.parents_indices[randint(self.nbr_parents,\
                                                                   size=1)[0]]
                parent2_ind = parent1_ind
                while parent1_ind == parent2_ind:
                    parent2_ind = self.parents_indices[randint(\
                                                 self.nbr_parents, size=1)[0]]

                split_point = randint(self.D, size=1)[0]
                if split_point != 0:
                    Xnew[:split_point, ixover] = self.X_group[:split_point,\
                                                                   parent1_ind]
                else:
                    Xnew[split_point, ixover] = self.X_group[split_point,\
                                                                   parent1_ind]
                if split_point != self.D:
                    Xnew[split_point:, ixover] = self.X_group[split_point:,\
                                                                   parent2_ind]
                else:
                    Xnew[split_point, ixover] = self.X_group[split_point,\
                                                                   parent2_ind]

        if self.optparams['func_xover'][self.igroup] == 'two_points':
            for ixover in range(self.nbr_xover[self.igroup]):
                parent1_ind = self.parents_indices[randint(self.nbr_parents,\
                                                                    size=1)[0]]
                parent2_ind = parent1_ind
                while parent1_ind == parent2_ind:
                    parent2_ind = self.parents_indices[randint(\
                                                  self.nbr_parents, size=1)[0]]

                split_points1 = randint(self.D, size=1)
                split_points2 = split_points1
                while split_points1 == split_points2:
                    split_points2 = randint(self.D, size=1)
                split_points = sort(array([split_points1, split_points2]))

                if split_points[0] != 0:
                    Xnew[:split_points[0], ixover] = \
                                    self.X_group[:split_points[0], parent1_ind]
                else:
                    Xnew[split_points[0], ixover] = \
                                     self.X_group[split_points[0], parent1_ind]

                Xnew[split_points[0]:split_points[1], ixover] = \
                     self.X_group[split_points[0]:split_points[1], parent2_ind]

                if split_points[1] != self.D:
                    Xnew[split_points[1]:, ixover] = \
                                    self.X_group[split_points[1]:, parent1_ind]
                else:
                    Xnew[split_points[1], ixover] = \
                                     self.X_group[split_points[1], parent1_ind]

        if self.optparams['func_xover'][self.igroup] == 'heuristic':
            for ixover in range(self.nbr_xover[self.igroup]):
                parent1_ind = self.parents_indices[randint(self.nbr_parents,\
                                                                   size=1)[0]]
                parent2_ind = parent1_ind
                while parent1_ind == parent2_ind:
                    parent2_ind = self.parents_indices[randint(\
                                                 self.nbr_parents, size=1)[0]]

                if self.fitness_group[parent1_ind] >= \
                                              self.fitness_group[parent2_ind]:
                    Xnew[:, ixover] = self.X_group[:, parent2_ind] + \
                                 self.optparams['ratio_xover'][self.igroup] *\
                                   (self.X_group[:, parent1_ind] -\
                                   self.X_group[:, parent2_ind])
                else:
                    Xnew[:, ixover] = self.X_group[:, parent1_ind] + \
                                 self.optparams['ratio_xover'][self.igroup] *\
                                              (self.X_group[:, parent2_ind] -\
                                                 self.X_group[:, parent1_ind])

        if self.optparams['func_xover'][self.igroup] == 'intermediate':
            for ixover in range(self.nbr_xover[self.igroup]):
                parent1_ind = self.parents_indices[randint(self.nbr_parents,\
                                                                   size=1)[0]]
                parent2_ind = parent1_ind
                while parent1_ind == parent2_ind:
                    parent2_ind = self.parents_indices[randint(\
                                                 self.nbr_parents, size=1)[0]]
                Xnew[:, ixover] = self.X_group[:, parent1_ind] + (-0.25 +\
                                                       1.25 * rand(self.D)) *\
                                             (self.X_group[:, parent2_ind] -\
                                               self.X_group[:, parent1_ind])

        if self.optparams['func_xover'][self.igroup] == 'linear_combination':
            for ixover in range(self.nbr_xover[self.igroup]):
                parent1_ind = self.parents_indices[randint(self.nbr_parents,\
                                                                    size=1)[0]]
                parent2_ind = parent1_ind
                while parent1_ind == parent2_ind:
                    parent2_ind = self.parents_indices[randint(\
                                                  self.nbr_parents, size=1)[0]]

                Xnew[:, ixover] = self.X_group[:, parent1_ind] + \
                                 self.optparams['ratio_xover'][self.igroup] *\
                                              (self.X_group[:, parent2_ind] -\
                                                self.X_group[:, parent1_ind])
        return Xnew

    def do_mutation(self, Xnew):
                #### MUTATION
        if self.optparams['func_mutation'][self.igroup] == 'gaussian':
            for imut in range(self.nbr_mutation[self.igroup]):
                Xnew[:, self.nbr_xover[self.igroup] + imut] = \
self.X_group[:, self.parents_indices[randint(self.nbr_parents, size=1)[0]]] +\
self.sigmaMutation[self.igroup] * randn(self.D)
            self.sigmaMutation[self.igroup] =\
                         self.sigmaMutation[self.igroup] *\
                         (1 - self.optparams['shrink_mutation'][self.igroup] *\
                                                 self.iteration / self.maxiter)

        if self.optparams['func_mutation'][self.igroup] == 'uniform':

            for imut in range(self.nbr_mutation[self.igroup]):

                Xnew[:, self.nbr_xover[self.igroup] + imut] = \
   self.X_group[:, self.parents_indices[randint(self.nbr_parents, size=1)[0]]]
                for idim in xrange(self.ndimensions):
                    if rand() < self.mutation_rate[self.igroup]:
                        Xnew[idim, self.nbr_xover[self.igroup] + imut] = \
                            Xnew[idim, self.nbr_xover[self.igroup] + imut] +\
                            (self.Xmax[idim, 0] - self.Xmin[idim, 0]) * rand()
        return Xnew

    def include_elite(self, Xnew):
        ### add the current elite to the next  generation

        Xnew[:, self.nbr_xover[self.igroup] + self.nbr_mutation[self.igroup]:]\
                                                                = self.X_lElite
        return Xnew

    def get_result(self):

        best_position = list()
        best_fitness = list()
        for igroup in xrange(self.groups):
            if self.index == 0:
                if self.scaling == None:
                    best_position.append(self.X_best_of_all[igroup, :])
                    best_fitness.append(self.fitness_best_of_all[igroup])
                else:
                    best_position.append(self.parameters.\
                           unscaling_func(self.X_best_of_all[igroup, :]))
                    best_fitness.append(self.fitness_best_of_all[igroup])

            else:
                best_position, best_fitness = [], []
#        print best_position
        return (best_position, best_fitness)

########NEW FILE########
__FILENAME__ = optimization
from numpy import array, sort,\
zeros, inf, squeeze, zeros_like
import inspect
from algorithm import *
from pso import *
from ..codehandler import *
from ..debugtools import *
from ..rpc import *
from ..synchandler import *
from ..gputools import *

__all__ = ['Optimization', 'OptimizationParameters',
           'Fitness', 'OptimizationRun', 'OptimizationResult']


class OptimizationParameters(object):
    """Internal class used to manipulate optimization parameters.
    It basically handles conversion between parameter dictionaries and arrays.

    Initialized with arguments:

    ``**params``
        Parameters list ``param_name=[bound_min, min_ max, bound_max]``

    **Methods**

    .. method:: get_initial_param_values(N)

        Returns initial parameter values sampled uniformly within the parameter
        interval given in the constructor of the class. ``N`` is the number
        of particles. The result is a dictionary ``{param_name=values}`` where
        values is a vector of values.

    .. method:: set_constraints()

        Returns the constraints for each parameter. The result is
        (min_values, max_values) where each variable is a vector containing
        the minimum and maximum values for each parameter.

    .. method:: get_param_values(X)

        Converts an array containing parameter values into a dictionary.

    .. method:: get_param_matrix(param_values)

        Converts a dictionary containing parameter values into an array.
    """
    def __init__(self,
                 scaling=None,
                 initrange=None,
                 bounds=None,
                 argtype='keywords',
                 **params):
        self.scaling = scaling
        self.initrange = initrange
        self.bounds = bounds
        self.argtype = argtype
        if argtype == 'keywords':
            self.params = params
            self.param_names = sort(params.keys())
            self.param_count = len(params)
        else:
            self.param_count = initrange.shape[0]

    def set_constraints(self):
        """
        Returns constraints of a given model
        returns min_values, max_values
        min_values is an array of length p where p is the number of parameters
        min_values[i] is the minimum value for parameter i
        """

        if self.argtype == 'matrix':
            # TODO BERTRAND: scaling
            boundaries = zeros((self.initrange.shape[0], 2))
            self.scaling_factor_a = []
            self.scaling_factor_b = []
            for idim in xrange(self.initrange.shape[0]):
                if self.bounds is None:
                    boundaries[idim, :] = [-inf, inf]
                    #used for the scaling
                    self.scaling_factor_a.append(self.initrange[idim, 0])
                    self.scaling_factor_b.append(self.initrange[idim, 1])
                else:
                    boundaries[idim, :] = \
                    [self.bounds[idim, 0], self.bounds[idim, 1]]
                    #used for the scaling
                    self.scaling_factor_a.append(self.bounds[idim, 0])
                    self.scaling_factor_b.append(self.bounds[idim, 1])

        else:
            param_names = self.param_names
            boundaries = zeros((len(param_names), 2))
            self.scaling_factor_a = []
            self.scaling_factor_b = []
            icount = 0
            for key in param_names:
                value = self.params[key]
                # No boundary conditions if only two values are given
                if len(value) == 2:
                    # One default interval,
                    #no boundary counditions on parameters
                    boundaries[icount, :] = [-inf, inf]
                    #used for the scaling
                    self.scaling_factor_a.append(value[0])
                    self.scaling_factor_b.append(value[-1])
                elif len(value) == 4:
                    # One default interval,
                    #value = [min, init_min, init_max, max]
                    boundaries[icount, :] = [value[0], value[3]]
                    #used for the scaling
                    self.scaling_factor_a.append(value[1])
                    self.scaling_factor_b.append(value[2])
                icount += 1
        self.scaling_factor_a = array(self.scaling_factor_a)
        self.scaling_factor_b = array(self.scaling_factor_b)
        self.boundaries = boundaries
        return boundaries

    def scaling_func(self, x):
        x = squeeze(x)
        x_new = zeros_like(x)
        if x.ndim == 1:
            for idim in xrange(len(x)):
                x_new[idim] = 2 * x[idim] / (self.scaling_factor_b[idim] - \
                self.scaling_factor_a[idim]) + (self.scaling_factor_a[idim] + \
                self.scaling_factor_b[idim]) / (self.scaling_factor_a[idim] - \
                self.scaling_factor_b[idim])
        else:
            for idim in xrange(x.shape[0]):
                x_new[idim, :] = 2 * x[idim, :] / \
                (self.scaling_factor_b[idim] - \
                self.scaling_factor_a[idim]) + (self.scaling_factor_a[idim] + \
                self.scaling_factor_b[idim]) / (self.scaling_factor_a[idim] - \
                self.scaling_factor_b[idim])
        return x_new

    def unscaling_func(self, x):
        x = squeeze(x)
        x_new = zeros_like(x)
        if x.ndim == 1:
            for idim in xrange(len(x)):
                x_new[idim] = (self.scaling_factor_b[idim] - \
                self.scaling_factor_a[idim]) / \
                2 * (x_new[idim] - (self.scaling_factor_a[idim] \
                + self.scaling_factor_b[idim]) / \
                (self.scaling_factor_a[idim] - \
                 self.scaling_factor_b[idim]))
        else:
            for idim in xrange(x.shape[0]):
                x_new[idim] = (self.scaling_factor_b[idim] - \
                self.scaling_factor_a[idim]) / 2 * (x_new[idim] - \
                (self.scaling_factor_a[idim] + self.scaling_factor_b[idim]) / \
                (self.scaling_factor_a[idim] - self.scaling_factor_b[idim]))
        return x_new

    def get_param_values(self, X):
        """
        Converts a matrix containing param values into a dictionary
        (from the algorithm to the fitness (unscale))
        """
        param_values = {}
        if X.ndim <= 1:
            X = X.reshape((-1, 1))
        for i in range(len(self.param_names)):
            if self.scaling == None:
                param_values[self.param_names[i]] = X[i, :]
            else:
                param_values[self.param_names[i]] =\
                (self.scaling_factor_b[i] -\
                self.scaling_factor_a[i]) / 2 * (X[i, :]\
                 - (self.scaling_factor_a[i] +\
                self.scaling_factor_b[i]) / (self.scaling_factor_a[i] - \
                self.scaling_factor_b[i]))
        return param_values

    def get_param_matrix(self, param_values):
        """
        Converts a dictionary containing param values
        into a matrix (from the fitness to the algorithm (scale))
        """
        p = self.param_count
        # Number of parameter values (number of particles)
        n = len(param_values[self.param_names[0]])
        X = zeros((p, n))
        for i in range(p):
            if self.scaling == None:
                X[i, :] = param_values[self.param_names[i]]
            else:
                X[i, :] = 2 * param_values[self.param_names[i]] / \
                (self.scaling_factor_b[i] - self.scaling_factor_a[i]) + \
                (self.scaling_factor_a[i] + self.scaling_factor_b[i]) / \
                (self.scaling_factor_a[i] - self.scaling_factor_b[i])
        return X


class Optimization(ParallelTask):
    def initialize(self, algorithm,
                         fitness_class,
                         maximize,
                         maxiter,
                         scaling,
                         popsize,
                         nodecount,
                         groups,
                         return_info,
                         parameters,
                         optparams,
                         init_args,
                         init_kwds,
                         ):
        """
        Initializes the optimization.
        algorithm: optimization algorithm class
        fitness_class: the class implementing the fitness function
        maxiter: number of iterations
        groups: number of groups
        parameters: OptimizationParameters object
        optparams: dict containing the parameters specific to the algorithm
        """
        log_debug("Optimization initialization")
        self.algorithm = algorithm
        self.fitness_class = fitness_class
        self.maximize = maximize
        self.scaling = scaling
        self.return_info = return_info
        self.dimension = parameters.param_count
        self.maxiter = maxiter
        self.parameters = parameters
        self.iteration = 0
        self.nodeidx = self.index
        self.init_args = init_args
        self.init_kwds = init_kwds

        if type(self.fitness_class) == PicklableClass:
            self.isfunction = self.fitness_class.isfunction
            if self.isfunction:
                self.arglist = self.fitness_class.arglist
        else:
            self.isfunction = inspect.isfunction(self.fitness_class)
            if self.isfunction:
                self.arglist = inspect.getargspec(self.fitness_class)[0]

        # dict {group: particles} for each group on this node
#        self.this_groups = groups.groups_by_node[self.node.index]
        # total number of particles on this node
#        self.particles = self.groups.particles_in_nodes[self.node.index]

        # number of groups
        self.groups = groups
        # makes popsize a multiple of node_count
        # size of the subpopulation of each group on each node
        self.subpopsize = popsize / nodecount
        # size of the population of each group (split across nodes)
        self.popsize = self.subpopsize * nodecount
        # number of nodes
        self.nodecount = nodecount
        # total size on each node
        self.nodesize = groups * self.subpopsize

        # optparams is a dict {key: val} or dict{key: [val1, val2...]}
        # if one wants to use different values with different groups
        # the following converts optparams to the second case and
        # fills it with default values if the key is not specified in optparams
        default_optparams = self.algorithm.default_optparams()
        optparamskeys = default_optparams.keys()
#        self.optparams = dict([(k, []) for k in optparamskeys])
        for key in optparamskeys:
            # fills with default value if needed
            if key not in optparams.keys():
                optparams[key] = default_optparams[key]
            # converts to a list if not already a list (one element per group)
            if type(optparams[key]) is not list:
                optparams[key] = [optparams[key]] * groups
        self.optparams = optparams

        self.initialize_algorithm()
        self.initialize_fitness_class()

    def initialize_algorithm(self):
        log_debug("Algorithm initialization")
        self.engine = self.algorithm(self.index,
                                    self.nodes,
                                    self.tubes,
                                    self.popsize,
                                    self.subpopsize,
                                    self.nodesize,
                                    self.groups,
                                    self.return_info,
                                    self.maxiter,
                                    self.scaling,
                                    self.parameters,
                                    self.optparams)

        self.engine.boundaries = self.parameters.set_constraints()
        self.engine.initialize()
        self.engine.initialize_particles()
        self.X = self.engine.X

    def initialize_fitness_class(self):
        """
        Initializes the fitness object, or function
        if fitness_class is not a class but a function
        """
        if self.isfunction:
            self.fitness_object = self.fitness_class
        else:
            self.fitness_object = self.fitness_class(
                                                 self.parameters.param_count,
                                                 self.popsize,
                                                 self.subpopsize,
                                                 self.groups,
                                                 self.nodesize,
                                                 self.nodecount,
                                                 self.shared_data,
                                                 self.unit_type,
                                                 self.init_args,
                                                 self.init_kwds)

    def get_fitness(self):
        if self.parameters.argtype == 'matrix':
            param_values = {}
        else:
            param_values = self.parameters.get_param_values(self.X)
        kwds = param_values
        if self.isfunction:
            # Pass special keyword arguments to the function
            for k in self.arglist:
                if hasattr(self, k):
                    kwds[k] = getattr(self, k)

            # add init_args/kwds to the function if using a fitness function
            args = self.init_args
            for k, v in self.init_kwds.iteritems():
                kwds[k] = v
        else:
            args = ()

        if self.parameters.argtype == 'keywords':
            self.fitness = self.fitness_object(*args, **kwds)
        else:
            self.fitness = self.fitness_object(self.X, *args, **kwds)

        return self.fitness

    def start(self):
        log_debug("Starting optimization")

        # main loop
        for self.iteration in xrange(self.maxiter):
            # Print Iteration i/n only once on each machine
            # TODO: not use unitidx to be more general
            if self.unitidx == 0:
                log_info("Iteration %d/%d" \
                         % (self.iteration + 1, self.maxiter))
            else:
                log_debug("Iteration %d/%d" %\
                           (self.iteration + 1, self.maxiter))
            # pre-fitness
#            for group, engine in self.engines.iteritems():
#                engine.pre_fitness()
            self.engine.pre_fitness()

            # evaluates the fitness
#            log_debug("Get fitness")
            fitness = self.get_fitness()
            # MAXIMIZE
            if self.maximize:
                fitness *= -1

#            fitness_split = self.groups.split_matrix(fitness, self.node.index)

            # post-fitness
#            for group, engine in self.engines.iteritems():
#                fitness=engine.post_fitness(fitness_split[group])
            self.engine.post_fitness(fitness)

            # iterate the algorithm on each group
#            new_X_split = {}
#            for group, engine in self.engines.iteritems():
#                engine.iterate(self.iteration, fitness_split[group])
#                new_X_split[group] = engine.X
#            self.X = self.groups.concatenate_matrix\
            #(new_X_split, self.node.index)
            self.engine.iterate(self.iteration, fitness)
            self.X = self.engine.X

#        if self.unit_type == 'GPU':
#            close_cuda()

#        self.X_best_split = {}
#        self.fitness_best_split = {}
#        for group, engine in self.engines.iteritems():
#            self.X_best_split[group], self.fitness_best_split[group]\
#             = engine.get_result()
#            # MAXIMIZE
#            if self.maximize:
#                self.fitness_best_split[group] =\
#           -self.fitness_best_split[group]

        # WARNING: only node 0 returns the result
        self.best_X, self.best_fit = self.engine.get_result()

        if self.maximize:
            self.best_fit = [-bf for bf in self.best_fit]

    def get_info(self):
#        info = {}
#        for group, engine in self.engines.iteritems():
#            info[group] = engine.get_info()
        return self.engine.get_info()

    def get_result(self):
        """
        Returns a tuple (best_pos, best_fit, info).
        Each one is a dict {group: value}
        """
        # ONLY node 0 returns the result
        if self.index != 0:
            return [], [], []
        info = self.get_info()
        if self.parameters.argtype == 'keywords':
            best_pos = []            for group in xrange(self.groups):
                group_best_X = self.best_X[group]
                if self.groups == 1:
                    group_best_X = [group_best_X]
                group_best_X = array(group_best_X)
                group_best_pos = self.parameters.\
                get_param_values(self.best_X[group])
                best_pos.append(group_best_pos)
#                for k in self.parameters.param_names:
#                    best_pos[k].append(group_best_pos[k][0])
        else:
            best_pos = self.best_X
        return best_pos, self.best_fit, info


class OptimizationRun(object):
    """
    Contains information about a parallel optimization that has been launched
    with the ``minimize_async`` or ``maximize_async`` function.

    Methods:

    ``get_info()``
        Return information about the current optimization asynchronously.

    ``get_result()``
        Return the result as an :class:`OptimizationResult` instance.
        Block until the optimization has finished.
    """
    def __init__(self, taskrun):
        self.taskrun = taskrun

    def get_info(self, node=0):
        # returns only info about node 0
        info = array(self.taskrun.get_info())
        return list(info[node])

    def get_result(self):
        """
        Returns a tuple (best_pos, best_fit, info) if returninfo is True,
            or (best_pos, best_fit) otherwise.
        If there is a single group:
            best_pos is a dict {param_name: value}
            best_fit is a number
            info is any object
        Otherwise:
            best_pos is a dict {param_name: values (list of values for groups)}
            best_fit is a list [group: value]
            info is a dict{group: info}
        """

#        result = self.taskrun.get_result()
#
#        groups = self.taskrun.args[7]
#        parameters = self.taskrun.args[8]
#
#        # all nodes return the same result
#        best_pos, best_fit, info = result[0]
##        if groups.group_count == 1:
#        if groups == 1:
##            best_pos = best_pos[0]
#            best_fit = best_fit[0]
#            info = info[0]
##            best_pos = parameters.get_param_values(best_X)
#            if parameters.argtype == 'keywords':
#                for k in parameters.param_names:
#                    best_pos[k] = best_pos[k][0]
#            else:
#                best_pos = best_pos.flatten()
#
#        if groups > 1:
#            best_fit = list(best_fit)
#
#        if parameters.argtype == 'keywords':
#            result = best_pos
#            result['best_fit'] = best_fit
#        else:
#            result = {}
#            result['best_pos'] = best_pos
#            result['best_fit'] = best_fit
#
#        if returninfo:
#            return result, info
#        else:
#            return result

        result = self.taskrun.get_result()

        return OptimizationResult(result, self.taskrun.args)


class GroupOptimizationResult(object):
    def __init__(self, group, best_pos, best_fit, info={}):
        self.group = group
        self.best_pos = best_pos
        self.best_fit = best_fit
        self.info = info

    def __getitem__(self, key):
        if type(key) is str:
            return self.best_pos[key]

    def __repr__(self):
        return ("Best position for group %d: " \
                % self.group) + str(self.best_pos)


class OptimizationResult(object):
    """
    Type of objects returned by optimization functions.

    Attributes:

    ``best_pos``
        Minimizing position found by the algorithm.
        For array-like fitness functions,
        it is a single vector if there is one group,
        or a list of vectors.
        For keyword-like fitness functions, it is a dictionary
        where keys are parameter names and values are numeric values.
        If there are several groups, it is a list of dictionaries.

    ``best_fit``
        The value of the fitness function for the best positions.
        It is a single value i there is one group, or it is a list
        if there are several groups.

    ``info``
        A dictionary containing various information
        about the optimization.

    Also, the following syntax is possible with an
    ``OptimizationResult`` instance ``or``. The ``key`` is either
    an optimizing parameter name for keyword-like fitness functions,
    or a dimension index for array-like fitness functions.

    ``or[key]``
        it is the best ``key`` parameter found (single value),
        or the list of the best parameters ``key`` found for all groups.

    ``or[i]``
        where ``i`` is a group index. This object has attributes
        ``best_pos``, ``best_fit``, ``info`` but only for group ``i``.

    ``or[i][key]``
        where ``i`` is a group index, is the same as ``or[i].best_pos[key]``.
    """
    def __init__(self, result, args):
        self.result = result
        self.args = args
        self.groups = args[7]
        self.returninfo = args[8]
        self.parameters = args[9]
        self.best_pos = self.best_fit = self.info = None

        # all nodes return the same result
#        if self.returninfo:
        try:
            self.best_pos, self.best_fit, self.info = result[0]
        except:
            log_warn("An exception occurred on the servers")
            return

        if self.parameters.argtype == 'keywords':
            self.best_pos = [dict([(key, self.best_pos[i][key][0])\
                             for key in self.best_pos[i].keys()])
                             for i in xrange(len(self.best_pos))]
            self.best_params = dict([(key, [self.best_pos[i][key]\
                                     for i in xrange(len(self.best_pos))])
                                     for key in self.best_pos[0].keys()])

        self.results = []
        for i in xrange(self.groups):
            groupresult = GroupOptimizationResult(i,
                                                  self.best_pos[i],
                                                  self.best_fit[i])
            if self.returninfo:
                groupresult.info = self.info[i]
            self.results.append(groupresult)
        # flatten lists if only 1 group
        if self.groups == 1:
            self.best_pos = self.best_pos[0]
            self.best_fit = self.best_fit[0]
            if self.returninfo:
                self.info = self.info[0]

    def __getitem__(self, key):
        if type(key) is str:
            if self.groups == 1:
                return self.best_pos[key]
            else:
                return [self.best_pos[g][key] for g in xrange(self.groups)]
        if type(key) is int:
            return self.results[key]

    def __repr__(self):
        result = "Best position: " + str(self.best_pos)
        result += "\n"
        result += "Best fitness: " + str(self.best_fit)
        return result


class Fitness(object):
    """
    The base class from which any fitness class must derive.
    When using several CPUs or several machines, every node contains
    its own instance of this class.
    The derived class must implement two methods:

    ``initialize(self, *args, **kwds)``
        This method initializes the fitness function at the beginning
        of the optimization. The arguments are provided from an optimization
        function like :func:`minimize` or :func:`maximize`, with the
        parameters ``args`` and ``kwds``.

    ``evaluate(self, **kwds)``.
        This method evaluates the fitness against particle positions.
        For keyword-like fitness functions, ``kwds`` is a dictionary where
        keys are parameter names, and values are vectors of parameter values.
        This method must return a vector with fitness values for all particles.

    In addition, several properties are available in this class:

    ``self.dimension``
        The dimension of the state space, or the number of optimizing
         parameters

    ``self.popsize``
        The total population size for each group across all nodes.

    ``self.subpopsize``
        The population size for each group on this node.

    ``self.groups``
        The number of groups.

    ``self.nodesize``
        The population size for all groups on this node.

    ``self.nodecount``
        The number of nodes used for this optimization.

    ``self.shared_data``
        The dictionary with shared data.

    ``self.unit_type``
        The unit type, ``CPU`` or ``GPU``.
    """
    def __init__(self,   dimension,
                         popsize,
                         subpopsize,
                         groups,
                         nodesize,
                         nodecount,
                         shared_data,
                         unit_type,
                         init_args,
                         init_kwds):
        self.dimension = dimension
        self.popsize = popsize
        self.subpopsize = subpopsize
        self.groups = groups
        self.nodesize = nodesize
        self.nodecount = nodecount
        self.shared_data = shared_data
        self.unit_type = unit_type
        self.init_args = init_args
        self.init_kwds = init_kwds
        self.initialize(*init_args, **init_kwds)

    def initialize(self, *args, **kwds):
        log_debug("<initialize> method not implemented")

    def evaluate(self, *args, **kwds):
        raise Exception("<evaluate> method not implemented")

    def __call__(self, *args, **kwds):
        return self.evaluate(*args, **kwds)

########NEW FILE########
__FILENAME__ = pso
from ..synchandler import *
from ..debugtools import *
from algorithm import *
from numpy import zeros, ones, inf, tile,\
nonzero, isscalar, maximum, minimum, kron, squeeze
from numpy.random import rand


__all__ = ['PSO']


class PSO(OptimizationAlgorithm):
    """
    Particle Swarm Optimization algorithm.
    See the
    `wikipedia entry on PSO
    <http://en.wikipedia.org/wiki/Particle_swarm_optimization>`__.

    Optimization parameters:

    ``omega``
        The parameter ``omega`` is the "inertial constant"

    ``cl``
        ``cl`` is the "local best" constant affecting how much
         the particle's personal best position influences its movement.

    ``cg``
        ``cg`` is the "global best" constant affecting how much the global best
        position influences each particle's movement.

    See the
    `wikipedia entry on PSO
    <http://en.wikipedia.org/wiki/Particle_swarm_optimization>`__
    for more details (note that they use ``c_1`` and ``c_2`` instead of ``cl``
    and ``cg``). Reasonable values are (.9, .5, 1.5), but experimentation
    with other values is a good idea.
    """
    @staticmethod
    def default_optparams():
        """
        Returns the default values for optparams
        """
        optparams = dict(omega=.8,
                         cl=.1,
                         cg=.1)
        return optparams

    @staticmethod
    def get_topology(node_count):
        topology = []
        # 0 is the master, 1..n are the workers
        if node_count > 1:
            for i in xrange(1, node_count):
                topology.extend([('to_master_%d' % i, i, 0),
                                 ('to_worker_%d' % i, 0, i)])
        return topology

    def initialize(self):
        """
        Initializes the optimization algorithm. X is the matrix of initial
        particle positions. X.shape == (ndimensions, nparticles)
        """
        # self.optparams[k] is a list (one element per group)
        self.omega = tile(kron(self.optparams['omega'],\
                                                       ones(self.subpopsize)),\
                                                         (self.ndimensions, 1))
        self.cl = tile(kron(self.optparams['cl'], ones(self.subpopsize)),\
                                                         (self.ndimensions, 1))
        self.cg = tile(kron(self.optparams['cg'], ones(self.subpopsize)),\
                                                         (self.ndimensions, 1))

        self.V = zeros((self.ndimensions, self.nodesize))

        if self.scaling == None:
            self.Xmin = tile(self.boundaries[:, 0].\
                            reshape(self.ndimensions, 1), (1, self.nodesize))
            self.Xmax = tile(self.boundaries[:, 1].\
                            reshape(self.ndimensions, 1), (1, self.nodesize))
        else:
            self.Xmin = tile(self.parameters.scaling_func(self.\
          boundaries[:, 0]).reshape(self.ndimensions, 1), (1, self.nodesize))
            self.Xmax = tile(self.parameters.\
             scaling_func(self.boundaries[:, 1]).reshape(self.ndimensions, 1),\
                                                           (1, self.nodesize))

        # Preparation of the optimization algorithm
        self.fitness_lbest = inf * ones(self.nodesize)
        self.fitness_gbest = inf * ones(self.groups)
        self.X_lbest = zeros((self.ndimensions, self.nodesize))
        self.X_gbest = zeros((self.ndimensions, self.groups))
        self.best_fitness = zeros((self.maxiter, self.groups))
        self.best_particule = zeros((self.ndimensions, self.maxiter,\
                                                                 self.groups))

    def get_global_best(self):
        """
        Returns the global best pos/fit on the current machine
        """
        for group in xrange(self.groups):
            fitness = self.fitness[group * self.subpopsize:(group + 1) *\
                                                             self.subpopsize]
            X = self.X[:, group * self.subpopsize:(group + 1) *\
                                                             self.subpopsize]
            min_fitness = fitness.min()
            if min_fitness < self.fitness_gbest[group]:
                index_gbest = nonzero(fitness == min_fitness)[0]
                if not(isscalar(index_gbest)):
                    index_gbest = index_gbest[0]
                self.X_gbest[:, group] = X[:, index_gbest]
                self.fitness_gbest[group] = min_fitness
        return self.fitness_gbest

    def get_local_best(self):
        indices_lbest = nonzero(self.fitness < self.fitness_lbest)[0]
        if (len(indices_lbest) > 0):
            self.X_lbest[:, indices_lbest] = self.X[:, indices_lbest]
            self.fitness_lbest[indices_lbest] = self.fitness[indices_lbest]

    def communicate(self):
        # communicate with master to have the absolute global best
        if self.index > 0:
            # WORKERS
            log_debug("I'm worker #%d" % self.index)

            # sends the temp global best to the master
            to_master = 'to_master_%d' % self.index
            self.tubes.push(to_master, (self.X_gbest, self.fitness_gbest))

            # receives the absolute global best from the master
            to_worker = 'to_worker_%d' % self.index
            (self.X_gbest, self.fitness_gbest) = self.tubes.pop(to_worker)
        else:
            # MASTER
            log_debug("I'm the master (#%d)" % self.index)

            # best values for each node, including the master (current node)
            X_gbest = self.X_gbest
            fitness_gbest = self.fitness_gbest

            # receives the temp global best from the workers
            for node in self.nodes:  # list of incoming tubes, ie from workers
                if node.index == 0:
                    continue
                tube = 'to_master_%d' % node.index
                log_debug("Receiving best values from <%s>..." % tube)
                X_gbest_tmp, fitness_gbest_tmp = self.tubes.pop(tube)

                for group in xrange(self.groups):
                    # this one is better
                    if fitness_gbest_tmp[group] < fitness_gbest[group]:
                        X_gbest[:, group] = X_gbest_tmp[:, group]
                        fitness_gbest[group] = fitness_gbest_tmp[group]

            # sends the absolute global best to the workers
            for node in self.nodes:  # list of outcoming tubes, ie to workers
                if node.index == 0:
                    continue
                tube = 'to_worker_%d' % node.index
                self.tubes.push(tube, (X_gbest, fitness_gbest))

            self.X_gbest = X_gbest
            self.fitness_gbest = fitness_gbest

    def update(self):
        # update matrix
        rl = rand(self.ndimensions, self.nodesize)
        rg = rand(self.ndimensions, self.nodesize)
        X_gbest_expanded = kron(self.X_gbest, ones((1, self.subpopsize)))
        self.V = self.omega * self.V + self.cl * rl *\
                                                   (self.X_lbest - self.X) +\
                                     self.cg * rg * (X_gbest_expanded - self.X)
        self.X = self.X + self.V

        # constrain boundaries
        self.X = maximum(self.X, self.Xmin)
        self.X = minimum(self.X, self.Xmax)

    def iterate(self, iteration, fitness):
        """
        Must return the new population
        """
#        log_debug("iteration %d/%d" % (iteration+1, self.iterations))
        self.iteration = iteration
        self.fitness = fitness

        # get local/global best on this machine
        self.get_local_best()
        self.get_global_best()

        # communicate with other nodes to have
        #the absolute global best position
        self.communicate()

        # updates the particle positions
        self.update()

        if self.return_info is True:
            self.collect_info()

    def collect_info(self):
#        print self.iteration
        self.best_fitness[self.iteration, :] = self.fitness_gbest
        self.best_particule[:, self.iteration, :] = self.X_gbest

    def get_info(self):
        info = list()
        if self.return_info is True:
            for igroup in xrange(self.groups):
                temp = dict()
                temp['best_fitness'] = squeeze(self.best_fitness[:, igroup])
                temp['best_position'] = squeeze(self.best_particule[:, :,\
                                                                     igroup])
                info.append(temp)

        return info

    def get_result(self):
        """
        Returns (X_best, fitness_best)
        """

        best_position = list()
        best_fitness = list()
        for igroup in xrange(self.groups):
            if self.index == 0:
                if self.scaling == None:
                    best_position.append(squeeze(self.X_gbest[:, igroup]))
                    best_fitness.append(self.fitness_gbest[igroup])
                else:
                    best_position.append(squeeze(self.parameters.\
                                    unscaling_func(self.X_gbest[:, igroup])))
                    best_fitness.append(self.fitness_best_of_all[igroup])

            else:
                best_position, best_fitness = [], []
#        print best_position, best_fitness
        return (best_position, best_fitness)

########NEW FILE########
__FILENAME__ = pool
"""
Custom Pool class, allowing to process tasks in a queue and change dynamically
the number of CPUs to use.
"""
from gputools import *
from debugtools import *
import multiprocessing
import threading
import sys
import os
import time
import gc
import ctypes
import numpy
import traceback
import cPickle
import zlib
import math
from multiprocessing import Process, Pipe, sharedctypes, Lock
from threading import Thread
from numpy import array, nonzero, ctypeslib

try:
    MAXCPU = multiprocessing.cpu_count()
except:
    MAXCPU = 0


__all__ = ['MAXCPU', 'CustomPool', 'Pool', 'make_common', 'make_numpy',
           'get_cpu_count']


def get_cpu_count():
    return multiprocessing.cpu_count()


class CustomConnection(object):
    """
    Handles chunking and compression of data.
    """
    def __init__(self, conn, index, lock=None, chunked=False,
                 compressed=False):
        self.conn = conn
        self.chunked = chunked
        self.compressed = compressed
        self.index = index
        self.lock = lock
        self.BUFSIZE = 2048

    def send(self, obj):
        s = cPickle.dumps(obj, -1)

        log_debug("acquiring lock")
        if self.lock is not None:
            self.lock.acquire()

        if self.compressed:
            s = zlib.compress(s)
        if self.chunked:
#            l = int(math.ceil(float(len(s))/self.BUFSIZE))
#            n = l*self.BUFSIZE
            # len(s) is a multiple of BUFSIZE, padding right with spaces
#            s = s.ljust(n)
#            l = "%08d" % l
#            try:
            # length of the message
            n = len(s)
            l = int(math.ceil(float(n) / self.BUFSIZE))
            log_debug("pipe %d: %d bytes to send in %d packet(s)" %
                (self.index, n, l))
            self.conn.send(n)
            time.sleep(.001)
            for i in xrange(l):
                log_debug("pipe %d: sending packet %d/%d" %
                    (self.index, i + 1, l))
                data = s[i * self.BUFSIZE:(i + 1) * self.BUFSIZE]
#                ar = arr.array('c', data)
#                self.conn.send_bytes(ar)
                self.conn.send_bytes(data)
                time.sleep(.001)
            log_debug("pipe %d: sent %d bytes" % (self.index, n))
#            except:
#                log_warn("Connection error")
        else:
            self.conn.send(s)

        log_debug("releasing lock")
        if self.lock is not None:
            self.lock.release()

    def recv(self):
        if self.chunked:
            # Gets the first 8 bytes to retrieve the number of packets.
#            l = ""
#            n = 8
#            while n > 0:
#                l += self.conn.recv(n)
#                n -= len(l)
            # BUG: sometimes l is filled with spaces??? setting l=1 in this
            # case (not a terrible solution)
#            try:
#                l = int(l)
#            except:
#                log_warn("transfer error, the paquet size was empty")
#                l = 1

            n = int(self.conn.recv())
            log_debug("pipe %d: %d bytes to receive" % (self.index, n))
#            length = l*self.BUFSIZE
            s = ""
            # Ensures that all data have been received
#            for i in xrange(l):# len(s) < length:
            while len(s) < n:
#                ar = arr.array('c', [0]*self.BUFSIZE)
                log_debug("pipe %d: receiving packet..." % (self.index))
#                n = self.conn.recv_bytes_into(ar)
#                s += ar.tostring()
                s += self.conn.recv_bytes()
#                if not self.conn.poll(.01): break
                time.sleep(.001)
            log_debug("pipe %d: received %d bytes" % (self.index, len(s)))
        else:
            s = self.conn.recv()
        # unpads spaces on the right
#        s = s.rstrip()
        if self.compressed:
            s = zlib.decompress(s)
        return cPickle.loads(s)

    def close(self):
        self.conn.close()

#class CustomPipe(object):
#    def __init__(self):
#        # TODO: try to fix the linux bug
##        log_debug("calling Pipe()")
#        parent_conn, child_conn = Pipe()
#        self.parent_conn = CustomConnection(parent_conn)
#        self.child_conn = CustomConnection(child_conn)


def getCustomPipe(index):
    parent_conn, child_conn = Pipe()
    parent_lock = Lock()
    child_lock = Lock()
    return (CustomConnection(parent_conn, index, parent_lock),
            CustomConnection(child_conn, index, child_lock))
#    cpipe = CustomPipe()
#    return cpipe.parent_conn, cpipe.child_conn


class Task(object):
    def __init__(self, fun, do_redirect=None, *args, **kwds):
        self.fun = fun
        self.args = args
        self.kwds = kwds
        self.do_redirect = do_redirect
        self.set_queued()

    def set_queued(self):
        self._status = 'queued'

    def set_processing(self):
        self._status = 'processing'

    def set_finished(self):
        self._status = 'finished'

    def set_crashed(self):
        self._status = 'crashed'

    def set_killed(self):
        self._status = 'killed'

    def get_status(self):
        return self._status
    status = property(get_status)


def eval_task(index, child_conns, parent_conns, shared_data, task, type):
    """
    Evaluates the task on unit index of given type ('CPU' or 'GPU')
    """
    if type == 'GPU':
        set_gpu_device(index)
        if task.do_redirect:
            sys.stdin = file(os.devnull)
            sys.stdout = file(os.devnull)
        if task.do_redirect is None and os.name == 'posix':
            log_warn("WARNING: specify do_redirect=True if CUDA code is not\
                compiling. see \
                <http://playdoh.googlecode.com/svn/docs/playdoh.html#gpu>")
    log_info("Evaluating task on %s #%d" % (type, index + 1))
    # shared data: if there is shared data, pass it in the task's kwds
    # task fun must have fun(..., shared_data={})
    if len(shared_data) > 0:
        task.kwds['shared_data'] = shared_data
    result = task.fun(*task.args, **task.kwds)
#    log_debug("Task successfully evaluated on %s #%d..." % (type, index))
    if type == 'GPU':
#        set_gpu_device(0)
        close_cuda()  # ensures that the context specific to the process is
                      # closed at the process termination
    child_conns[index].send(result)


def make_common_item(v):
    if isinstance(v, numpy.ndarray):
        shape = v.shape
        mapping = {
            numpy.dtype(numpy.float64): ctypes.c_double,
            numpy.dtype(numpy.int32): ctypes.c_int,
            }
        ctype = mapping.get(v.dtype, None)
        if ctype is not None:
            log_debug('converting numpy array to common array')
            v = v.flatten()
            v = sharedctypes.Array(ctype, v, lock=False)
    else:
        # shape = None means that v is not an array and should not be converted
        # back as numpy item
        shape = None
    return v, shape


def make_numpy_item((v, shape)):
    if shape is not None:
        try:
            v = ctypeslib.as_array(v)
            v.shape = shape
            log_debug('converting common array to numpy array')
        except:
            log_debug('NOT converting common array to numpy array')
            pass
    return v


def make_common(shared_data):
    shared_data = dict([(k, make_common_item(v)) for k, v in \
                        shared_data.iteritems()])
    return shared_data


def make_numpy(common_shared_data):
#    shared_args = common_shared_data[1]
#    shared_kwds = common_shared_data[2]
#    args = [make_numpy_item(v) for v in shared_args]
    shared_data = dict([(k, make_numpy_item(v)) for k, v in \
                        common_shared_data.iteritems()])
#    return (common_shared_data[0], args, kwds)
    return shared_data


def process_fun(index, child_conns, parent_conns, shared_data):
    """
    This function is executed on a child process.
    conn is a connection to the parent
    """
    shared_data = make_numpy(shared_data)
    conn = child_conns[index]
    while True:
        log_debug('process_fun waiting...')
        try:
            fun, args, kwds = conn.recv()
        except Exception:
            log_warn(traceback.format_exc())
        log_debug('process_fun received function <%s>' % fun)
        if fun is None:
            break
        # the manager can poll for the process status by sending
        # '_process_status',
        # if it answers 'idle' then it's idle, otherwise it means that it
        # is busy.
#        if fun == '_process_status':
#            log_debug('sending <idle>')
#            conn.send('idle')
#            continue
        try:
            result = fun(index, child_conns, parent_conns,
                         shared_data, *args, **kwds)
        except Exception:
            log_warn(str(fun))
            log_warn(traceback.format_exc())
        del fun, args, kwds, result
        gc.collect()
    log_debug('process_fun finished')

#    close_cuda()

    conn.close()


class Pool(object):
    def __init__(self, workers, npipes=2, globs=None):
        self.workers = workers
        if globs is None:
            globs = globals()
        self.globals = globs
        self.npipes = npipes  # number of pipes/unit

        self.parent_conns = [None] * (workers * npipes)
        self.child_conns = [None] * (workers * npipes)
        self.processes = [None] * (workers)
        self.pids = [None] * (workers)
        self.status = [None] * (workers)

        self.launch_workers()

    def launch_workers(self, units=None, shared_data={}):
        log_debug("launching subprocesses...")
        if units is None:
            units = range(self.workers)
        elif type(units) is int:
            units = range(units)

        # create pipes
        for i in xrange(self.npipes):
            for unit in units:
                pconn, cconn = getCustomPipe(unit + i * self.workers)
                self.parent_conns[unit + i * self.workers] = pconn
                self.child_conns[unit + i * self.workers] = cconn
#        log_debug((self.npipes, units, self.parent_conns))

        # create processes
        for unit in units:
            p = Process(target=process_fun, args=(unit,
                                                  self.child_conns,
                                                  self.parent_conns,
                                                  shared_data))
            p.start()
            self.pids[unit] = p.pid
            self.processes[unit] = p
            self.status[unit] = 'idle'
            time.sleep(.01)

    def close_workers(self, units):
        log_debug("closing the subprocesses...")
        # close pipes
        for i in xrange(self.npipes):
            for unit in units:
                self.parent_conns[unit + i * self.workers].close()
                self.child_conns[unit + i * self.workers].close()

        # close processes
        for unit in units:
            p = self.processes[unit]
            p.terminate()
            del p

    def restart_workers(self, units=None, shared_data={}):
        shared_data = make_common(shared_data)
        if units is None:
            units = range(self.workers)
        elif type(units) is int:
            units = range(units)

        log_debug("restarting the subprocesses...")
        self.close_workers(units)
        time.sleep(.5)
        self.launch_workers(units, shared_data)
        log_debug("restarted the subprocesses!")

#        for unit in units:
#            pconn, cconn = Pipe()
#            self.parent_conns[unit]= pconn
#            self.child_conns[unit] = cconn
#
#            p = Process(target=process_fun, args=(unit,
#                                                  self.child_conns,
#                                                  self.parent_conns,
#                                                  shared_data))
#            p.start()
#            self.pids[unit] = p.pid
#            self.processes[unit] = p

    def set_status(self, index, status):
        self.status[index] = status

    def get_status(self):
        return self.status

    def get_idle_units(self, n):
        """
        Returns the indices of n idle units
        """
        status = self.get_status()
        unitindices = []
        for i in xrange(len(status)):
            if status[i] == 'idle':
                unitindices.append(i)
            if len(unitindices) == n:
                break
        return unitindices

    def execute(self, index, fun, *args, **kwds):
        self.parent_conns[index].send((fun, args, kwds))

    def __getitem__(self, index):
        """
        Allows to use the following syntax:
            pool[i].fun(*args, **kwds)
        instead of
            pool.execute(i, fun, *args, **kwds)
        """
        class tmp(object):
            def __init__(self, obj):
                self.obj = obj

            def __getattr__(self, name):
                if name == 'recv':
                    #self.obj.parent_conns[index].recv()
                    return lambda: self.obj.recv(unitindices=[index])
                if name == 'send':
                    #self.obj.parent_conns[index].send(data)
                    return lambda data:\
                                    self.obj.send(data, unitindices=[index])
                function = self.obj.globals[name]
                return lambda *args, **kwds: self.obj.execute(index, function,
                                                              *args, **kwds)
        t = tmp(self)
        return t

    def send(self, data, unitindices=None, confirm=False):
        """
        Sends data to all workers on this machine or only to the specified
        workers (unitindices).
        data must be a tuple (fun, args, kwds). Numpy arrays in args and kwds
        will be shared
        to save memory.
        """

        # TEST
        confirm = False

        if unitindices is None:
            unitindices = xrange(self.workers)
        if not confirm:
            [self.parent_conns[i].send(data) for i in unitindices]
        else:
            while True:
                [self.parent_conns[i].send(data) for i in unitindices]
                # if send OK, terminate, otherwise, send again to the units
                # which returned False
                unitindices = nonzero(array([not self.parent_conns[i].recv()
                    for i in unitindices]))[0]
                if len(unitindices) == 0:
                    break
                log_debug("pickling error, sending data again")

    def recv(self, unitindices=None):  # ,discard = None, keep = None):
        """
        Receives data from all workers on this machine or only to the specified
        workers (unitindices).
        Discard allows to discard sent data as soon as data==discard
        keep is the opposite of discard: it allows to recv a specific data
        """
        if unitindices is None:
            unitindices = xrange(self.workers)
        result = []
        i = 0
#        discarded = []
#        kept = []
#        log_debug((unitindices, self.parent_conns))
        while i < len(unitindices):
            ui = unitindices[i]
            r = self.parent_conns[ui].recv()
#            log_debug('recv <%s, %s>' % (str(r), str(type(r))))
#            if (discard is not None) and (r == discard):
#                discarded.append(ui)
#                continue
#            if (keep is not None) and (r != keep):
#                kept.append(ui)
#                continue
            result.append(r)
            i += 1
#        if discard is not None:
#            return result, discarded
#        elif kept is not None:
#            return result, kept
#        else:
        return result

    def map(self, fun, args, unitindices=None):
        """
        Maps a function with a list of arguments. We always have:
            len(args) == self.workers
        NOTE: fun must accept 3 arguments before 'args':
            index, child_conns, parent_conns
        """
        if unitindices is None:
            unitindices = xrange(self.workers)
        for i in xrange(len(args)):
            arg = args[i]
#            self.set_status(i, 'busy')
            self.execute(unitindices[i], fun, *arg)
        results = []
        for i in xrange(len(args)):
            results.append(self.parent_conns[unitindices[i]].recv())
#            self.set_status(i, 'idle')
        return results

    def _close(self, i):
        try:
            log_debug("sending shutdown connection to subprocess %d" % i)
            self.parent_conns[i].send((None, (), {}))
        except:
            log_warn("unable to send shutdown connection to subprocess %d" % i)
#        self.parent_conns[i].close()
        self.processes[i].join(.1)
        self.processes[i].terminate()

    def close(self):
        threads = []
        for i in xrange(self.workers):
            t = Thread(target=self._close, args=(i,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join(.1)

#    def join(self):
#        self.close()
#
#    def terminate(self):
#        self.close()


class CustomPool(object):
    """
    Custom Pool class. Allows to evaluate asynchronously any number of tasks
    over any number of CPUs/GPUs. The number of CPUs/GPUs can be changed
    dynamically.
    Tasks statuses can be retrieved at any time.

    Transparent support for both CPUs and GPUs.

    No exception handling here : the function to be mapped is assumed to handle
    exceptions, and return (not raise) an Exception object if any exception
    occured.
    """
    def __init__(self, units, unittype='CPU', do_redirect=None):
        """
        units is either a list of unit indices, or an integer (number of
        units)
        """
        if type(units) is not int:
            self.unitindices = units
            units = len(units)
        else:
            self.unitindices = range(units)
        self.units = units  # number of CPUs/GPUs
        self.type = unittype
        self.pool = None
        self.running = True  # set to False to stop the pool properly
        self.tasks = []  # task queue
        self.current_step = 0  # current iteration step
        self.thread = None
        self.results = {}
        self.do_redirect = do_redirect

    def _run(self):
#        prevunits = self.units

        # IMPORTANT
        # self.pool can be set by an external class, so that the same
        # pool can be associated to multiple CustomPools
        if self.pool is None:
            log_debug("The multiprocessing pool wasn't initialized,\
                       initializing now")
            self.pool = self.create_pool(self.units)

        # the pool is now busy
        [self.pool.set_status(i, 'busy') for i in self.unitindices]

        if len(self.shared_data) > 0:
            self.pool.restart_workers(self.unitindices,
                                      shared_data=self.shared_data)

        i = self.current_step  # current step, task index is i+j

        while (i < len(self.tasks)) and self.running:
            units = self.units
            if units == 0:
                log_warn("No units available, terminating now")
                return
#            if (prevunits is not units):
#                log_info("Changing the number of units from %d to %d"\
#                               % (prevunits, units))
#                self.pool.close()
#                self.pool.join()
#                self.pool = multiprocessing.Pool(units)

            # Selects tasks to evaluate on the units
            local_tasks = self.tasks[i:i + units]
            if len(local_tasks) == 0:
                log_warn("There is no task to process")
                return

            log_debug("Processing tasks #%d to #%d..." % (i + 1,
                                                         i + len(local_tasks)))

            # Sends the tasks to the pool of units
            [task.set_processing() for task in local_tasks]
            local_results = self.pool.map(eval_task,
                                          [(local_tasks[j], self.type) for j in
                                                xrange(len(local_tasks))],
                                          unitindices=self.unitindices)

            for j in xrange(len(local_results)):
                result = local_results[j]
                self.results[i + j] = result
                if isinstance(result, Exception):
                    self.tasks[i + j].set_crashed()
                else:
                    self.tasks[i + j].set_finished()
            log_info("Tasks #%d to #%d finished" %
                        (i + 1, i + len(local_tasks)))

#            prevunits = units
            i += len(local_tasks)
            self.current_step = i

        # the pool is now available
        [self.pool.set_status(i, 'idle') for i in self.unitindices]

        log_debug("All tasks finished")

    def _create_tasks(self, fun, *argss, **kwdss):
        """
        Creates tasks from a function and a list of arguments
        """
        tasks = []
        k = len(argss)  # number of non-named arguments
        keys = kwdss.keys()  # keyword arguments

        i = 0  # task index
        while True:
            try:
                args = [argss[l][i] for l in xrange(k)]
                kwds = dict([(key, kwdss[key][i]) for key in keys])
            except:
                break
            task = Task(fun, self.do_redirect, *args, **kwds)  # do_redirect
            tasks.append(task)
            i += 1

        return tasks

    def set_units(self, units):
        log_debug("setting units to %d" % units)
        # TODO
#        log_debug(self.unitindices)
        self.unitindices = self.pool.get_idle_units(units)
#        log_debug(self.unitindices)
        self.units = units

    def add_tasks(self, fun, *argss, **kwdss):
        new_tasks = self._create_tasks(fun, *argss, **kwdss)
        log_debug("Adding %d tasks" % len(new_tasks))
        n = len(self.tasks)  # current number of tasks
        self.tasks.extend(new_tasks)
        ids = range(n, n + len(new_tasks))
        for id in ids:
            self.results[id] = None
        return ids

    def run_thread(self):
        log_debug("running thread")
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def submit_tasks(self, fun, shared_data, *argss, **kwdss):
        """
        Evaluates fun on a list of arguments and keywords over a pool of CPUs.
        Same as Pool.map, except that the number of CPUs can be changed during
        the processing of the queue. Also, it is a non-blocking call (separate
        thread).

        Exception handling must be performed inside fun : if an Exception
        occurs,
        fun must return the Exception object.
        """
        self.shared_data = shared_data
        ids = self.add_tasks(fun, *argss, **kwdss)
        # Launches the new tasks if the previous ones have stopped.
        if self.thread is None or not self.thread.is_alive():
            self.run_thread()
        return ids

    def clear_tasks(self):
        log_debug("clearing all pool tasks")
        self.running = False
        self.join()
        self.tasks = []
        self.current_step = 0
        self.thread = None
        self.results = {}
        self.running = True

    @staticmethod
    def create_pool(units=MAXCPU):
        if units > 0:
            log_debug("Creating multiprocessing pool with %d units" % units)
#            return multiprocessing.Pool(units)
            return Pool(units)  # Pool class defined above instead of the
                                # multiprocessing.Pool
        else:
            log_debug("NOT creating multiprocessing pool with 0 unit!")
            return None

    @staticmethod
    def close_pool(pool):
        log_debug("Closing multiprocessing pool")
        pool.terminate()
        pool.join()

    def map(self, fun, shared_data, *argss, **kwdss):
        ids = self.submit_tasks(fun, shared_data, *argss, **kwdss)
        return self.get_results(ids)

    def get_status(self, ids):
        """
        Returns the status of each task. Non-blocking call.
        """
        return [self.tasks[id].status for id in ids]

    def get_results(self, ids):
        """
        Returns the result. Blocking call.
        """
        self.join()
        return [self.results[id] for id in ids]

    def join(self):
        if self.thread is not None:
            log_debug("joining CustomPool thread")
            self.thread.join()
        else:
            log_debug("tried to join CustomPool thread but it wasn't active")
        [self.pool.set_status(i, 'idle') for i in self.unitindices]

    def has_finished(self, ids):
        for s in self.get_status(ids):
            if s is not "finished":
                return False
        return True

    def close(self):
        """
        Waits for the current processings to terminate then terminates the job
        processing.
        """
        self.running = False
        self.join()

        for i in xrange(len(self.tasks)):
            if (self.tasks[i].status == 'queued'):
                self.tasks[i].set_killed()

        if self.pool is not None:
            log_debug("closing pool of processes")
            self.pool.close()

    def kill(self):
        """
        Kills immediately the task processing.
        """
        self.running = False

        if self.pool is not None:
            self.pool.close()
#            self.pool.terminate()
#            self.pool.join()
            self.pool = None

        del self.thread

        for i in xrange(len(self.tasks)):
            if (self.tasks[i].status == 'queued' or
                    self.tasks[i].status == 'processing'):
                self.tasks[i].set_killed()

########NEW FILE########
__FILENAME__ = resources
from debugtools import *
from pool import MAXCPU
from gputools import *
from baserpc import DEFAULT_PORT, LOCAL_IP
from rpc import *
from multiprocessing import Process
import numpy


def get_server_resources(servers):
    """
    Get the complete resource allocation on the specified servers.

    Arguments:

    ``servers``
        The list of the servers. Every item is a string with the IP address of
        the server, or a tuple ``(IP, port)``.

    Return an object ``resources``, which is a list of dictionaries that can be
    used like this:
    ``nbr = resources[serverindex][type][client]``, where:

    * ``serverindex`` is the index of the server in the ``servers`` argument,
    * ``type is ``'CPU'`` or ``'GPU'``,
    * ``client`` is the IP address of the client, or ``ME`` if it corresponds
      to this client,
      i.e. the computer which made the call to ``get_server_resources``,
    * ``nbr`` is the number of ``type``(s) allocated to ``client`` on server
      ``serverindex``.
    """
    if type(servers) is not list:
        servers = [servers]
    GC.set(servers)
    disconnect = GC.connect(raiseiferror=True)
    client_name = GC.get_client_name()
    result = GC.execute_native('get_all_resources')
    for i in xrange(len(result)):
        # replaces my IP by 'ME'
        for typ in result[i].keys():
            if result[i][typ] is not None and \
                    client_name[i] in result[i][typ].keys():
                result[i][typ]['ME'] = result[i][typ][client_name[i]]
                del result[i][typ][client_name[i]]
    if disconnect:
        GC.disconnect()
    return result


def get_my_resources(servers):
    """
    Get the resources allocated to this client on the specified servers.

    Arguments:

    ``servers``
        The list of the servers. Every item is a string with the IP address
        of the server,
        or a tuple ``(IP, port)``.

    Return an object ``resources``, which is a dictionary where keys are
    ``'CPU'`` or ``'GPU'``,
    and values are the number of allocated resources for this client.
    """
    result = get_server_resources(servers)
    for r in result:
        for typ, res in r.iteritems():
            if res is not None and 'ME' in res.keys():
                r[typ] = res['ME']
            else:
                r[typ] = 0
    return result


def get_available_resources(servers):
    """
    Get the total number of (potentially) available resources for this client
    on the specified servers, i.e. the number of idle resources (allocated
    to no one)
    plus the resources already allocated to this client.

    Arguments:

    ``servers``
        The list of the servers. Every item is a string with the IP address of
        the server,
        or a tuple ``(IP, port)``.

    Return an object ``resources``, which is a dictionary where keys are
    ``'CPU'`` or ``'GPU'``,
    and values are the number of idle resources for this client.
    """
    if type(servers) is not list:
        servers = [servers]
    GC.set(servers)
    disconnect = GC.connect(raiseiferror=True)
    resources = get_server_resources(servers)
    total_resources = get_total_resources(servers)
    idle_resources = [None] * len(servers)
    for i in xrange(len(total_resources)):
        idle_resources[i] = {}
        for r in ['CPU', 'GPU']:
            if resources[i][r] is None:
                idle_resources[i][r] = 0
            else:
                idle_resources[i][r] = total_resources[i][r] - \
                    sum(resources[i][r].values())
                if 'ME' in resources[i][r].keys():
                    idle_resources[i][r] += resources[i][r]['ME']
    if disconnect:
        GC.disconnect()
    return idle_resources


def request_resources(servers, **resources):
    """
    Allocate resources for this client on the specified servers.

    Arguments:

    ``servers``
        The list of the servers. Every item is a string with the IP address
        of the server,
        or a tuple ``(IP, port)``.

    ``**resources``
        A dictionary where keys are ``'CPU'` or ``'GPU'`` and values are lists
        with the number of
        CPUs or GPUs to allocate on each server.

    Example: ``request_resources('bobs-machine.university.com', CPU=2)``
    """
    if type(servers) is not list:
        servers = [servers]
    for k, v in resources.iteritems():
        if type(resources[k]) is not list:
            resources[k] = [v]
    GC.set(servers)
    disconnect = GC.connect(raiseiferror=True)
    result = GC.execute_native('request_resources', **resources)
    if disconnect:
        GC.disconnect()
    return result


def request_all_resources(servers, type, skip=[], units=None):
    """
    Allocate resources optimally for this client on the specified servers, i.e.
    as many resources as possible.

    Arguments:

    ``servers``
        The list of the servers. Every item is a string with the IP address of
        the server,
        or a tuple ``(IP, port)``.

    ``type``
        The unit type: ``'CPU'` or ``'GPU'``.

    Return a list with the number of resources that just have been allocated
    for every server.

    Example: ``n = request_all_resources('bobs-machine.university.com',
    type='CPU')[0]``
    """
    # skip is a list of server indices to skip
    if __builtins__['type'](servers) is not list:
        servers = [servers]
    GC.set(servers)
    disconnect = GC.connect(raiseiferror=True)
    maxunits = GC.execute_native('get_total_resources')
    resources = GC.execute_native('get_all_resources')
    params = {type: []}
    clients = GC.get_client_name()
    for i in xrange(len(servers)):
        if resources[i][type] is not None:
            if clients[i] in resources[i][type].keys():
                del resources[i][type][clients[i]]
            busy = sum([r for r in resources[i][type].itervalues()])
        else:
            busy = 0
        n = maxunits[i][type] - busy
        # if units is set, the number of units is at most units
        if units is not None:
            n = min(n, units)
        if n <= 0:
            log_warn("there are no resources left on the server: %d %s out\
                        of %d are used" % (busy, type, maxunits[i][type]))
            n = 0
        params[type].append(n)

    # skip some servers
    for typ in params.keys():
        for i in skip:
            params[type][i] = None

    request_resources(servers, **params)
    if disconnect:
        GC.disconnect()
    return params[type]


def get_total_resources(servers):
    """
    Return the total number of resources available to the clients on the given
    server.
    It is a dict resources[type]=nbr
    """
    if type(servers) is not list:
        servers = [servers]
    GC.set(servers)
    disconnect = GC.connect(raiseiferror=True)
    result = GC.execute_native('get_total_resources')
    if disconnect:
        GC.disconnect()
    return result


def set_total_resources(server, **resources):
    """
    Specify the total number of resources available on the given server
    """
    GC.set(server)
    disconnect = GC.connect(raiseiferror=True)
    result = GC.execute_native('set_total_resources', **resources)
    if disconnect:
        GC.disconnect()
    return result


class Allocation(object):
    """
    Contain information about resource allocation on remote machines.
    Is returned by the :func:`allocate` function.

    Attributes:

    ``self.total_units``
        Total number of units.

    ``self.allocation``
        Allocation dictionary, were keys are machine tuples (IP, port) and
        values are the number
        of resources allocated to the client.
    """
    def __init__(self, servers=[],
                       total_units=None,
                       unit_type='CPU',
                       cpu=None,
                       gpu=None,
                       allocation=None,
                       local=None):
        if type(servers) is not list:
            servers = [servers]
        self.servers = servers
        self.total_units = total_units
        self.unit_type = unit_type
        self.cpu = cpu
        self.gpu = gpu
        # Determines whether the run is local or not
        if local is not None:
            self.local = local
        else:
            self.local = (type(servers) is list and len(servers) == 0)
        if cpu is not None:
            self.unit_type = 'CPU'
            self.total_units = cpu
        elif gpu is not None:
            self.unit_type = 'GPU'
            self.total_units = gpu
        elif total_units is not None:
            self.unit_type = unit_type
            self.total_units = total_units
        elif servers == []:
            # Default: use all resources possible
            if unit_type == 'CPU':
                self.total_units = numpy.inf  # MAXCPU-1
            if unit_type == 'GPU':
#                MAXGPU = initialise_cuda()
                self.total_units = numpy.inf  # MAXGPU
        self.allocation = {}
        if allocation is None:
            self.allocate()
        else:
            self.allocation = allocation
            self.machines = self.get_machines()
            self.total_units = numpy.sum(allocation.values())
            self.local = False

    def allocate(self):
        # Creates the allocation dict
        if self.local:
            # creates the local server
            if self.unit_type == 'CPU':
                self.total_units = min(self.total_units, MAXCPU)
                args = (DEFAULT_PORT, self.total_units, 0, True)
            if self.unit_type == 'GPU':
                MAXGPU = get_gpu_count()
                #MAXGPU = #initialise_cuda() # THIS VERSION NOT SAFE ON LINUX
                self.total_units = min(self.total_units, MAXGPU)
                args = (DEFAULT_PORT, 0, self.total_units, True)
            self.allocation[(LOCAL_IP, DEFAULT_PORT)] = self.total_units
            p = Process(target=open_server, args=args)
            p.start()
        else:

            GC.set(self.servers)
            disconnect = GC.connect(raiseiferror=True)

            for i in xrange(len(self.servers)):
                server = self.servers[i]
                if type(server) is str:
                    server = (server, DEFAULT_PORT)
                if server[0] == 'localhost' or server[0] == '127.0.0.1':
                    server = (LOCAL_IP, server[1])
                self.servers[i] = server

            units = get_my_resources(self.servers)
            units = numpy.array([u[self.unit_type] for u in units],
                                   dtype=numpy.int)

            # allocate optimally servers with no resource allocated yet
            notalreadyallocated = numpy.nonzero(numpy.array(units,
                                                dtype=numpy.int) == 0)[0]
            alreadyallocated = numpy.nonzero(numpy.array(units,
                                                dtype=numpy.int) > 0)[0]
            if len(notalreadyallocated) > 0:
                newunits = request_all_resources(self.servers,
                                                 skip=list(alreadyallocated),
                                                           type=self.unit_type)
                newunits = numpy.array([u for u in newunits if u is not None],
                                        dtype=numpy.int)
                units[notalreadyallocated] = newunits
            # keep servers with units available
#            ind2 = numpy.nonzero(numpy.array(newunits,dtype=int)>0)[0]
            if (self.total_units is not None) and\
                    (numpy.sum(units) > self.total_units):
                # indices of servers with too much units
                ind = numpy.nonzero(numpy.cumsum(units) > self.total_units)[0]
                units[ind] = 0
                units[ind[0]] = self.total_units - numpy.sum(units)
            self.total_units = numpy.sum(units)
            for i in xrange(len(self.servers)):
                self.allocation[self.servers[i]] = units[i]
            if disconnect:
                GC.disconnect()
        self.machines = self.get_machines()
        if not self.local:
            log_info("Using %d %s(s) on %d machine(s)" % (self.total_units,
                                                          self.unit_type,
                                                          len(self.machines)))
        else:
            log_info("Using %d %s(s) on the local machine" % (self.total_units,
                                                              self.unit_type))
        return self.allocation

    def get_machines(self):
        """
        Gets the machines list from an allocation, sorted alphabetically.
        Allocation is a dict {('IP', port): nbr}
        """
        machines = [m for m in self.allocation.keys()
                                if self.allocation[m] > 0]
        machines = [Machine(m) for m in machines]
        machines.sort(cmp=lambda m1, m2: cmp(m1.to_tuple(), m2.to_tuple()))
        return machines

    def get_machine_tuples(self):
        return [m.to_tuple() for m in self.machines]

    machine_tuples = property(get_machine_tuples)

    def iteritems(self):
        return self.allocation.iteritems()

    def keys(self):
        return self.allocation.keys()

    def __getitem__(self, key):
        if type(key) is Machine:
            key = key.to_tuple()
        return self.allocation[key]

    def __repr__(self):
        if self.servers is None or self.servers == []:
            strmachines = "the local machine"
        else:
            strmachines = "%d machine(s)" % len(self.servers)
        return "<Allocation of %d %s(s) on %s>" % (self.total_units,
                                                   self.unit_type,
                                                   strmachines)

    def __len__(self):
        return self.total_units


def allocate(machines=[],
             total_units=None,
             unit_type='CPU',
             allocation=None,
             local=None,
             cpu=None,
             gpu=None):
    """
    Automatically allocate resources on different machines using available
    resources.
    Return an :class:`Allocation` object which can be passed to Playdoh
    functions like :func:`map`,
    :func:`minimize`, etc.

    Arguments:

    ``machines=[]``
        The list of machines to use, as a list of strings (IP addresses)
        or tuples
        (IP address and port number).

    ``cpu=None``
        The total number of CPUs to use.

    ``gpu=None``
        The total number of GPUs to use.

    ``allocation=None``
        This argument is specified when using manual resource allocation.
        In this case,
        ``allocation`` must be a dictionary with machine IP addresses as
        keys and
        resource number as values. The unit type must also be specified.

    ``unit_type='CPU'``
        With manual resource allocation, specify the unit type: ``CPU``
        or ``GPU``.
    """
    al = Allocation(machines, total_units, unit_type, cpu, gpu, allocation,
                    local)
    return al

########NEW FILE########
__FILENAME__ = rpc
from debugtools import *
from gputools import *
from pool import *
from connection import *
from baserpc import *
from numpy import array
import time
import traceback


__all__ = ['RpcServer', 'RpcClient', 'RpcClients',
           'Machine', 'GlobalConnection', 'GC',
           'Procedure', 'open_server', 'close_servers']


def open_server(port=None, maxcpu=None, maxgpu=None, local=None):
    """
    Start the Playdoh server.

    Arguments:

    ``port=DEFAULT_PORT``
        The port (integer) of the Playdoh server. The default is DEFAULT_PORT,
        which is 2718.

    ``maxcpu=MAXCPU``
        The total number of CPUs the Playdoh server can use. ``MAXCPU`` is the
        total number of CPUs on the computer.

    ``maxgpu=MAXGPU``
        The total number of GPUs the Playdoh server can use. ``MAXGPU`` is the
        total number of GPUs on the computer, if PyCUDA is installed.
    """
    if maxcpu is not None:
        globals()['MAXCPU'] = maxcpu
    else:
        maxcpu = MAXCPU
    if maxgpu is not None:
        globals()['MAXGPU'] = maxgpu
    else:
        maxgpu = get_gpu_count()
    if port is None:
        port = DEFAULT_PORT
    if not local:
        log_info("Opening Playdoh server on port %d with %d CPU(s) and %d \
GPU(s)" % (port, maxcpu, maxgpu))
    RpcServer(port=port).listen()


def close_servers(addresses):
    """
    Close the specified Playdoh server(s) remotely.

    Arguments:

    ``addresses``
        The list of the Playdoh server addresses to shutdown.
    """
    if type(addresses) is str:
        addresses = [(addresses, DEFAULT_PORT)]
    if type(addresses) is tuple:
        addresses = [addresses]
    RpcClients(addresses).close_server()


class GlobalConnection(object):
    def __init__(self, servers=None, handler_class=None, handler_id=None):
        self.clients = None
        self.set(servers, handler_class, handler_id)

    def set(self, servers=None, handler_class=None, handler_id=None):
        if type(servers) is not list:
            servers = [servers]
        self.servers = servers
        self.handler_class = handler_class
        self.handler_id = handler_id
        if self.clients is not None:
            self.clients.handler_class = handler_class
            self.clients.handler_id = handler_id

    def connect(self, raiseiferror=False, trials=None):
        """
        Connects if needed and returns True if the caller must disconnect
        manually
        """
        if array(self.connected).all():
            return False
        log_debug("Connecting to %d server(s), class=%s, id=<%s>" % \
                    (len(self.servers),
                     self.handler_class,
                     self.handler_id))
        self.clients = RpcClients(self.servers,
                                  self.handler_class,
                                  self.handler_id)
        self.clients.connect(trials)
        boo = array(self.clients.is_connected()).all()
        if raiseiferror:
            if not boo:
                raise Exception("Connection error")
        return boo

    def is_connected(self):
        return (self.clients != None) and (self.clients.is_connected())
    connected = property(is_connected)

    def disconnect(self):
        log_debug("Disconnecting from servers")
        if self.clients is not None:
            self.clients.disconnect()
        self.clients = None

    def execute_native(self, method, *args, **kwds):
        return self.clients.execute_native(method, *args, **kwds)

    def add_handler(self, handler_id, handler_class):
        self.handler_id = handler_id
        self.handler_class = handler_class
        self.clients.add_handler(handler_id, handler_class)

    def __getattr__(self, name):
        return getattr(self.clients, name)

GC = GlobalConnection()


class Machine(object):
    def __init__(self, arg, port=DEFAULT_PORT):
        """
        Represents a machine.

        arg can be a string IP or a tuple (IP, port)
        """
        if type(arg) is str:
            self.ip = arg
            self.port = port
        elif type(arg) is tuple:
            self.ip, self.port = arg
        elif type(arg) is Machine:
            self.ip = arg.ip
            self.port = arg.port
        # HACK
        if self.ip == 'localhost':
            self.ip = LOCAL_IP

    def to_tuple(self):
        return (self.ip, self.port)

    def __repr__(self):
        return "<machine '%s' on port %d>" % (self.ip, self.port)

    def __eq__(self, y):
        return (self.ip == y.ip) and (self.port == y.port)


class DistantException(object):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg


class Procedure(object):
    """
    A procedure sent by a client to a server.
    object handler_id, instance of handler_class, call of
    method_name(*args, **kwds)
    """
    def __init__(self, handler_class, handler_id, name, args, kwds):
        self.handler_class = handler_class
        if handler_class is not None:
            self.handler_class_name = handler_class.__name__
        else:
            # handler_class = None means that the method is a method of
            # the RpcServer not a method of handler_class
            self.handler_class_name = 'native'
        if args is None:
            args = ()
        if kwds is None:
            kwds = {}
        self.handler_id = handler_id
        self.name = name
        self.args = args
        self.kwds = kwds

    def is_native(self):
        return self.handler_class_name == 'native'

    def __repr__(self):
        return "%s.%s" % (self.handler_class_name, self.name)

#def get_max_gpu(conn):
#    MAXGPU = initialise_cuda()
#    close_cuda()
#    conn.send(MAXGPU)
#    conn.close()
#    return MAXGPU


class RpcServer(BaseRpcServer):
    def initialize(self):
        global MAXGPU
#        if CANUSEGPU and type(MAXGPU) is not int:
##            MAXGPU = initialise_cuda()
#            # can't initialize CUDA before working, otherwise bugs appear
#            # on Linux
#            # so initializing CUDA in a separated process just to retrieve
             # the number of GPUs!
#            parent_conn, child_conn = Pipe()
#            p=multiprocessing.Process(target=get_max_gpu, args=(child_conn,))
#            p.start()
#            MAXGPU=parent_conn.recv()
##            log_debug("found %d" % MAXGPU)
#            p.join()
        if type(MAXGPU) is not int:
            MAXGPU = get_gpu_count()

        self.pools = {}
        # when creating a CustomPool, set its pool property to this if using
        # CPUs
        self.pools['CPU'] = CustomPool.create_pool(MAXCPU)
        if CANUSEGPU:
            self.pools['GPU'] = CustomPool.create_pool(MAXGPU)
        else:
            self.pools['GPU'] = None

        # resources currently assigned to every client
        self.resources = {}
        self.resources['CPU'] = {}
        if CANUSEGPU:
            self.resources['GPU'] = {}
        else:
            self.resources['GPU'] = None

        # total number of resources available on the server
        self.total_resources = {}
        self.total_resources['CPU'] = MAXCPU
        if CANUSEGPU:
            self.total_resources['GPU'] = MAXGPU
        else:
            self.total_resources['GPU'] = 0

        self.handlers = {}
        # dict handler_id => client associated to the handler
        self.handler_clients = {}

    def get_client_name(self, client):
        return client

    def request_resources(self, client, **resources):
        """
        Allocates units type to client
        type is CPU or GPU
        """
        for type, units in resources.iteritems():
            if units is None:
                continue
            if self.resources[type] is not None:
                res = min(units, self.total_resources[type])
                log_info("Assigning %d %s(s) to client '%s'" % (res, type,
                                                                client))
                self.resources[type][client] = res
#                self.resources[type][client] = units
            else:
                log_warn("no %s(s) are available on this server" % type)

    def get_all_resources(self, client):
        """
        resources['CPU']['client'] = nbr
        """
        return self.resources

    def set_total_resources(self, client, **total_resources):
        total = dict(CPU=get_cpu_count(), GPU=get_gpu_count())
        for type, units in total_resources.iteritems():
            units = min(units, total[type])
            log_info("Changing the total number of resources available on \
the server: %d %s(s)" % (units, type))
            self.total_resources[type] = units

        # changing allocated resources
        for typ in self.resources.keys():
            if self.resources[typ] is not None:
                for client in self.resources[typ].keys():
                    self.resources[typ][client] = \
                        min(self.total_resources[typ],
                            self.resources[typ][client])
        for handler in self.handlers.itervalues():
            handler.resources = self.resources

    def get_total_resources(self, client):
        """
        Returns the total number of resources available on the server
        for every type of resource
        """
        return self.total_resources

    def add_handler(self, client, handler_id, handler_class):
        log_debug("server: creating new handler '%s', '%s' instance, for\
                    client '%s'" % (handler_id, handler_class, client))
        self.handlers[handler_id] = handler_class()  # Object initialization
        self.handlers[handler_id].client = client  # client IP
        self.handlers[handler_id].this_machine = Machine(LOCAL_IP, self.port)
        self.handlers[handler_id].handler_id = handler_id
        self.handlers[handler_id].pools = self.pools  # the handler objects can
                                    # access to the global pools

        for typ in self.resources.keys():
            # assigning MAXtyp units by default
            if self.resources[typ] is not None and \
                    client not in self.resources[typ]:
                log_debug("Default assignment of %d %s(s) to client '%s'" %
                    (self.total_resources[typ], typ, client))
                self.resources[typ][client] = self.total_resources[typ]

        self.handlers[handler_id].resources = self.resources

        # handler_id corresponds to client
        self.handler_clients[handler_id] = client
#        self.update_resources()

    def delete_handler(self, client, handler_id):
        if handler_id is None:
            handler_id = client
        log_debug("server: deleting handler '%s'" % handler_id)
        del self.handlers[handler_id]
        del self.handler_clients[handler_id]

    def process(self, client, procedure):
        if client == '127.0.0.1':
            client = LOCAL_IP
        if procedure.is_native():
            # call self.name(*args, **kwds)
#            try:
            result = getattr(self, procedure.name)(client, *procedure.args,
                                                   **procedure.kwds)
#            except Exception as e:
#                log_warn("The procedure '%s' is not valid" % procedure.name)
#                result = e
        else:
            # Default handler id is the client IP
            if procedure.handler_id is None:
                procedure.handler_id = client
            # creates the handler if it doesn't exist
            if procedure.handler_id not in self.handlers.keys():
                self.add_handler(client, procedure.handler_id,
                                 procedure.handler_class)
            # call self.handlers[id](*args, **kwds)
            try:
                result = getattr(self.handlers[procedure.handler_id],
                                               procedure.name)(*procedure.args,
                                                              **procedure.kwds)
            except:
                msg = traceback.format_exc()
                log_warn(msg)
                result = DistantException(msg)
        return result

    def restart(self, client):
        log_info("Restarting the server")
        self.shutdown()
        time.sleep(.5)
        self.initialize()

    def shutdown(self):
        for id, handler in self.handlers.iteritems():
            if hasattr(handler, 'close'):
                log_debug("closing handler '%s'" % id)
                handler.close()
        for type, pool in self.pools.iteritems():
            if pool is not None:
                log_debug("closing pool of %s" % type)
                pool.close()


class RpcClient(BaseRpcClient):
    def __init__(self, server, handler_class=None, handler_id=None):
        BaseRpcClient.__init__(self, server)
        self.handler_class = handler_class
        self.handler_id = handler_id

    def execute_method(self, handler_class, handler_id, method,
                       *args, **kwds):
        procedure = Procedure(handler_class, handler_id, method,
                              args, kwds)
        result = self.execute(procedure)
        if type(result) is DistantException:
            print result.msg
            raise result
        return result

    def execute_native(self, method, *args, **kwds):
        return self.execute_method(None, None, method,
                                   *args, **kwds)

    def set_handler_id(self, handler_id):
        log_debug("client: setting handler id='%s'" % str(handler_id))
        self.handler_id = handler_id

    def set_handler_class(self, handler_class):
        log_debug("client: setting handler class='%s'" % str(handler_class))
        self.handler_class = handler_class

    def add_handler(self, handler_id, handler_class=None):
        self.set_handler_id(handler_id)
        if handler_class is not None:
            self.set_handler_class(handler_class)
        log_debug("client: adding handler '%s'" % str(handler_id))
        return self.execute_native('add_handler', self.handler_id,
                                   self.handler_class)

    def delete_handler(self, handler_id=None):
        log_debug("client: deleting handler '%s'" % str(handler_id))
        return self.execute_native('delete_handler', handler_id)

    def restart(self):
        self.execute_native('restart')

    def __getattr__(self, method):
        log_debug("getting attribute '%s'" % method)
        return lambda *args, **kwds: self.execute_method(self.handler_class,
                                                         self.handler_id,
                                                         method,
                                                         *args,
                                                         **kwds)


class RpcClients(BaseRpcClients):
    def __init__(self, servers, handler_class=None, handler_id=None):
        if type(servers) is str:
            servers = [servers]
        if type(servers) is tuple:
            servers = [servers]
        self.servers = servers
        self.handler_class = handler_class
        self.handler_id = handler_id

        self.clients = [RpcClient(server, handler_class, handler_id) \
                            for server in servers]
        self.results = {}

        self.indices = None

    def distribute(self, handler_class, handler_id, name, *argss, **kwdss):
        if self.indices is None:
            self.indices = xrange(len(self.servers))

        # True if the connection must be closed on the server side while
        # processing the procedure
        close_connection_temp = kwdss.pop('_close_connection_temp', False)

        procedures = []
        k = len(argss)  # number of non-named arguments
        keys = kwdss.keys()  # keyword arguments

        # Duplicates non-list args
        argss = list(argss)
        for l in xrange(k):
            if type(argss[l]) is not list:
                argss[l] = [argss[l]] * len(self.indices)

        # Duplicates non-list kwds
        for key in keys:
            if type(kwdss[key]) is not list:
                kwdss[key] = [kwdss[key]] * len(self.indices)

        for i in xrange(len(self.indices)):
            args = [argss[l][i] for l in xrange(k)]
            kwds = dict([(key, kwdss[key][i]) for key in keys])
            procedure = Procedure(handler_class, handler_id, name,
                                  args, kwds)

            # close conn on the server while processing the procedure
            procedure.close_connection_temp = close_connection_temp

            procedures.append(procedure)

        return self.execute(procedures, indices=self.indices)

    def set_client_indices(self, indices):
        """
        Set the client indices to connect to. None by default = connect
        to all clients
        """
        self.indices = indices

    def execute_native(self, method, *argss, **kwdss):
        return self.distribute(None, None, method, *argss, **kwdss)

    def add_handler(self, handler_id, handler_class=None):
        self.handler_id = handler_id
        self.handler_class = handler_class
        return self.distribute(None, None, 'add_handler',
                               [handler_id] * len(self.servers),
                               [handler_class] * len(self.servers))

    def delete_handler(self, handler_id=None):
        if handler_id is None:
            handler_id = self.handler_id
        return self.distribute(None, None, 'delete_handler',
                               [handler_id] * len(self.servers))

    def __getattr__(self, name):
        return lambda *argss, **kwdss: self.distribute(self.handler_class,
                                                       self.handler_id,
                                                       name,
                                                       *argss,
                                                       **kwdss)

########NEW FILE########
__FILENAME__ = client_gui
#!/usr/bin/env python

# generated by wxGlade 0.6.3

"""
Client GUI for Playdoh. This tool allows to get idle resources
on remote servers
and to allocate resources to the current client.
"""

from playdoh import *
try:
    import wx
    from wx import Frame
except ImportError:
    log_info("wx is not installed, the GUI will not be available.")
    # HACK: if wx is not available, Frame is just a standard class instead
    # of a wx class
    Frame = object
import numpy
from threading import Thread

# begin wxGlade: extracode
# end wxGlade


class Proxy(object):
    def __init__(self, frame):
        self.frame = frame
        self.t = None

    def get_server(self, text):
        msg = None
        server = str(text.strip(" \n\r"))
        l = server.split(':')
        if len(l) == 1:
            server, port = l[0], str(DEFAULT_PORT)
        elif len(l) == 2:
            server, port = l[0], l[1]
        else:
            msg = "server IP must be 'IP:port'"
            log_warn(msg)
        server = server.strip()
        port = int(port.strip())
        return (server, port)

    def _get_resources(self, server):
        try:
            GC.set([server])
            disconnect = GC.connect(raiseiferror=True, trials=1)
            if not numpy.array(GC.connected).all():
                pass  # raise Exception()
            available_resources = get_available_resources([server])[0]
            my_resources = get_my_resources([server])[0]
            if disconnect:
                GC.disconnect()
        except Exception as e:
            log_warn(e)
            available_resources, my_resources = None, None
        resources = available_resources, my_resources
        self.frame.update_info(resources)

    def get_resources(self, server):
        if self.t is not None:
            self.t.join()
        t = Thread(target=self._get_resources, args=(server,))
        t.start()
        self.t = t

    def get_info(self, server, idle_resources, my_resources):
        text = "Resources allocated on %s, port %d\n" % server
        for unit_type in ['CPU', 'GPU']:
            text += "%d %s(s) idle, including %d allocated to you\n" % \
                   (idle_resources[unit_type],
                    unit_type,
                    my_resources[unit_type])
        return text

    def _request_resources(self, server, cpu, gpu):
        try:
            GC.set([server])
            disconnect = GC.connect(raiseiferror=True, trials=1)
            request_resources([server], CPU=cpu, GPU=gpu)
            self._get_resources(server)
            if disconnect:
                GC.disconnect()
        except Exception as e:
            log_warn(e)

    def request_resources(self, server, cpu, gpu):
        if self.t is not None:
            self.t.join()
        t = Thread(target=self._request_resources, args=(server, cpu, gpu))
        t.start()
        self.t = t

    def exit(self):
        if self.t is not None:
            self.t.join()
        GC.disconnect()


class MyFrame(Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.combo_box = wx.ComboBox(self, -1,
                                     choices=USERPREF['favoriteservers'],
                                     style=wx.CB_DROPDOWN | wx.CB_DROPDOWN)
        self.button_get_info = wx.Button(self, -1, "Get info")
        self.text_info = wx.TextCtrl(self, -1, "",
                    style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_LINEWRAP)
        self.text_cpu = wx.TextCtrl(self, -1, "0 CPU(s)")
        self.slider_cpu = wx.Slider(self, -1, 0, 0, 0,
                                    style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.text_gpu = wx.TextCtrl(self, -1, "0 GPU(s)")
        self.slider_gpu = wx.Slider(self, -1, 0, 0, 0,
                                    style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.button_allocate = wx.Button(self, -1, "Allocate")
        self.button_exit = wx.Button(self, -1, "Exit")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON,
                  self.event_get_info, self.button_get_info)
        self.Bind(wx.EVT_COMMAND_SCROLL,
                  self.event_scroll_cpu, self.slider_cpu)
        self.Bind(wx.EVT_COMMAND_SCROLL,
                  self.event_scroll_gpu, self.slider_gpu)
        self.Bind(wx.EVT_BUTTON,
                  self.event_allocate, self.button_allocate)
        self.Bind(wx.EVT_BUTTON,
                  self.event_exit, self.button_exit)
        # end wxGlade

        self.proxy = Proxy(self)
        self.servers = USERPREF['favoriteservers']
        self.server = None
        self.resources = None

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle("Playdoh Client GUI")
        self.SetSize((380, 350))
        self.combo_box.SetSelection(0)
        self.text_cpu.Enable(False)
        self.text_gpu.Enable(False)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3.Add(self.combo_box, 0, wx.EXPAND, 0)
        sizer_4.Add(self.button_get_info, 1, wx.EXPAND, 0)
        sizer_3.Add(sizer_4, 1, wx.EXPAND, 0)
        sizer_3.Add(self.text_info, 4, wx.EXPAND, 0)
        sizer_5.Add(self.text_cpu, 1, wx.EXPAND, 0)
        sizer_5.Add(self.slider_cpu, 2, wx.EXPAND, 0)
        sizer_5.Add(self.text_gpu, 1, wx.EXPAND, 0)
        sizer_5.Add(self.slider_gpu, 2, wx.EXPAND, 0)
        sizer_3.Add(sizer_5, 1, wx.EXPAND, 0)
        sizer_6.Add(self.button_allocate, 1, wx.EXPAND, 0)
        sizer_6.Add(self.button_exit, 1, wx.EXPAND, 0)
        sizer_3.Add(sizer_6, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_3)
        self.Layout()
        # end wxGlade

    def enable(self):
        self.button_get_info.Enable()
        self.button_allocate.Enable()
        self.slider_cpu.Enable()
        self.slider_gpu.Enable()

    def disable(self):
        self.button_get_info.Disable()
        self.button_allocate.Disable()
        self.slider_cpu.Disable()
        self.slider_gpu.Disable()

    def update_info(self, resources):
        self.idle_resources, self.my_resources = resources

        self.enable()

        if self.idle_resources is None and self.my_resources is None:
            return

        # set text info
        text = self.proxy.get_info(self.server,
                                   self.idle_resources, self.my_resources)
        self.text_info.Clear()
        self.text_info.AppendText(text)

        maxcpu = self.idle_resources['CPU']
        cpu = self.my_resources['CPU']
#        if cpu == 0: cpu = maxcpu

        maxgpu = self.idle_resources['GPU']
        gpu = self.my_resources['GPU']
#        if gpu == 0: gpu = maxgpu

        self.slider_cpu.SetMax(maxcpu)
        self.slider_cpu.SetValue(cpu)
        self.text_cpu.Clear()
        self.text_cpu.AppendText("%d CPU(s)" % self.slider_cpu.GetValue())

        self.slider_gpu.SetMax(maxgpu)
        self.slider_gpu.SetValue(gpu)
        self.text_gpu.Clear()
        self.text_gpu.AppendText("%d GPU(s)" % self.slider_gpu.GetValue())

    def event_get_info(self, event):  # wxGlade: MyFrame.<event_handler>
        server = self.combo_box.GetValue()
        if server not in self.servers:
            self.servers.append(str(server))
            USERPREF['favoriteservers'] = self.servers
            # USERPREF.save()

        self.server = self.proxy.get_server(server)
        self.proxy.get_resources(self.server)

        self.disable()

    def event_stop(self, event):  # wxGlade: MyFrame.<event_handler>
        print "Event handler `event_stop' not implemented"
        event.Skip()

    def event_scroll_cpu(self, event):  # wxGlade: MyFrame.<event_handler>
        self.text_cpu.Clear()
        self.text_cpu.AppendText("%d CPU(s)" % self.slider_cpu.GetValue())

    def event_scroll_gpu(self, event):  # wxGlade: MyFrame.<event_handler>
        self.text_gpu.Clear()
        self.text_gpu.AppendText("%d GPU(s)" % self.slider_gpu.GetValue())

    def event_allocate(self, event):  # wxGlade: MyFrame.<event_handler>
        cpu = self.slider_cpu.GetValue()
        gpu = self.slider_gpu.GetValue()
        self.proxy.request_resources(self.server, cpu, gpu)

    def event_exit(self, event):  # wxGlade: MyFrame.<event_handler>
        self.Close(True)

# end of class MyFrame


def gui():
    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    frame_1 = MyFrame(None, -1, "")
    app.SetTopWindow(frame_1)
    frame_1.Show()
    app.MainLoop()

if __name__ == "__main__":
    gui()

########NEW FILE########
__FILENAME__ = console
#!/usr/bin/env python

from playdoh import *
import os
import optparse
import playdoh
import time


def _open_server(cpu, gpu, port, background=True):
    scriptdir = os.path.join(os.path.dirname(playdoh.__file__),
                                             'scripts')
    cmd = "python \"%s\" %d %d %d" % (os.path.join(scriptdir, 'open.py'),
                                                   cpu, gpu, port)

    # run in background:
    if background:
        if os.name == 'nt':
            cmd = 'start ' + cmd
        else:
            cmd = cmd + ' &'

    os.system(cmd)
    time.sleep(1)


def _open_restart_server():
    scriptdir = os.path.join(os.path.dirname(playdoh.__file__), 'scripts')
    os.system("python %s" % (os.path.join(scriptdir, 'openrestart.py')))


def get_units(args):
    try:
        nbr = int(args[0])
    except:
        nbr = -1  # means ALL
    type = args[1][:3].upper()
    if type not in ['CPU', 'GPU']:
        log_warn("the unit type must be either CPU or GPU instead of %s,\
            using CPU now" % type)
        type = 'CPU'
    return nbr, type


def get_server(string):
    if ':' in string:
        server, port = string.split(':')
        port = int(port)
    else:
        server = string
        port = DEFAULT_PORT
    return (server, port)


def parse_open(args):
    # get the total number of GPUs on this machine
    MAXGPU = get_gpu_count()

    cpu = MAXCPU
    gpu = MAXGPU
    port = DEFAULT_PORT

    if len(args) <= 1:
        if len(args) == 1:
            port = int(args[0])
    elif len(args) <= 3:
        nbr, type = get_units(args)
        if type == 'CPU':
            cpu = nbr
        if type == 'GPU':
            gpu = nbr
        if len(args) == 3:
            port = int(args[2])
    elif len(args) <= 5:
        nbr, type = get_units(args[:2])
        if type == 'CPU':
            cpu = nbr
        if type == 'GPU':
            gpu = nbr
        nbr, type = get_units(args[2:4])
        if type == 'CPU':
            cpu = nbr
        if type == 'GPU':
            gpu = nbr
        if len(args) == 5:
            port = int(args[4])
    return cpu, gpu, port


def parse_close(args):
    servers = []
    for arg in args:
        servers.append(get_server(arg))
    if len(servers) == 0:
        servers = [('localhost', DEFAULT_PORT)]
    return servers


def parse_get(args):
    if len(args) == 0:
        return None
    server, port = get_server(args[0])

    # only the server = get idle resources
    if len(args) == 1:
        resources = get_available_resources((server, port))
        my_resources = get_my_resources((server, port))
        for type in ['CPU', 'GPU']:
            print "%d %s(s) available, %d allocated, on %s" %\
                (resources[0][type], type, my_resources[0][type], server)
    elif len(args) == 2:
        if args[1] == 'all':
            # get all resources
            resources = get_server_resources((server, port))[0]
            for type in ['CPU', 'GPU']:
                if resources[type] is None:
                    print "No %ss available" % type
                    continue
                if len(resources[type]) == 0:
                    print "No %ss allocated" % type
                for client in resources[type]:
                    print "%d %s(s) allocated to %s" %\
                        (resources[type][client], type, client.lower())
    return resources


def parse_request(args):
    if len(args) == 0:
        return None
    server, port = get_server(args[0])

    params = {}
    paramsall = []  # types for which allocate all resources
    nbr, type = get_units(args[1:3])
    if nbr >= 0:
        params[type] = nbr
    else:
        paramsall.append(type)
    if len(args) > 3:
        nbr2, type2 = get_units(args[3:5])
        if nbr2 >= 0:
            params[type2] = nbr2
        else:
            paramsall.append(type2)

    # request some resources
    if len(params) > 0:
        request_resources((server, port), **params)

    # request all resources
    for type in paramsall:
        request_all_resources((server, port), type)

    resources = get_my_resources((server, port))[0]
    keys = resources.keys()
    keys.sort()
    for type in keys:
        print "%d %s(s) allocated to you on %s" % (resources[type],
                                                             type, server)

    return resources


def parse_set(args):
    if len(args) == 0:
        return None
    server, port = ('localhost', DEFAULT_PORT)
    params = {}
    if len(args) >= 2:
        nbr, type = get_units(args[:2])
        params[type] = nbr
    if len(args) >= 4:
        nbr, type = get_units(args[2:4])
        params[type] = nbr
    if 'CPU' in params.keys():
        if params['CPU'] == -1:
            params['CPU'] = get_cpu_count()
    if 'GPU' in params.keys():
        if params['GPU'] == -1:
            params['GPU'] = get_gpu_count()
    set_total_resources((server, port), **params)
    res = get_total_resources((server, port))[0]
    for type in ['CPU', 'GPU']:
        print "%d total %s(s) available on this machine" % (res[type], type)
    return True


def run_console():
    usage = """
    This tool allows you to open/close a server, obtain the available
    resources on distant servers and allocate resources. Here are a
    few usage examples:

        # open the server with all possible resources
        playdoh open

        # open the server with 4 CPUs and 1 GPU
        playdoh open 4 CPU 1 GPU

        # change the total number of resources available on this machine
        playdoh set 2 CPUs 0 GPU

        # show the available resources/all resources on the given server
        playdoh get bobs-machine.university.com [all]

        # request 2 CPUs and 1 GPU on the server
        playdoh request bobs-machine.university.com 2 CPUs 1 GPU

        # request all resources on the server
        playdoh request bobs-machine.university.com all CPUs all GPUs

        # close the server on this machine
        playdoh close

        # close a server remotely
        playdoh close bobs-machine.university.com
    """

    parser = optparse.OptionParser(usage=usage)

    parser.add_option("-b", "--background",
                          dest="background",
                          default="True",
                          help="open the server in background")

    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.print_help()
    elif args[0] == 'open':
        cpu, gpu, port = parse_open(args[1:])
        _open_server(cpu, gpu, port, options.background == "True")
        # open_server(maxcpu=cpu, maxgpu=gpu, port=port)
    elif args[0] == 'close':
        servers = parse_close(args[1:])
        log_info("Closing %d server(s)" % len(servers))
        close_servers(servers)
    elif args[0] == 'getall':
        print "%d,%d" % (get_cpu_count(), get_gpu_count())
    elif args[0] == 'get':
        if parse_get(args[1:]) is None:
            parser.print_help()
    elif args[0] == 'request':
        if parse_request(args[1:]) is None:
            parser.print_help()
    elif args[0] == 'set':
        if parse_set(args[1:]) is None:
            parser.print_help()
    elif args[0] == 'openrestart':
        # start the restart server, always running on port 27182,
        # allowing to kill/restart/start
        # the Playdoh server remotely
        _open_restart_server()
    elif args[0] == 'remote':
        """
        Open remotely a Playdoh server
            playdoh remote open localhost

        Kill remotely a Playdoh server, even if it is blocked
            playdoh remote kill localhost

        Kill and open a new Playdoh server
            playdoh remote restart localhost
        """
        server = procedure = None
        if len(args) >= 2:
            procedure = args[1]
        if len(args) >= 3:
            server = args[2]
        restart(server, procedure)
    else:
        parser.print_help()


if __name__ == '__main__':
    run_console()

########NEW FILE########
__FILENAME__ = open
if __name__ == '__main__':
    from playdoh import *
    import sys
    if len(sys.argv) <= 1:
        cpu = get_cpu_count()
        gpu = get_gpu_count()
        port = DEFAULT_PORT
    else:
        cpu = int(sys.argv[1])
        gpu = int(sys.argv[2])
        port = int(sys.argv[3])
        if cpu == -1:
            cpu = get_cpu_count()
        if gpu == -1:
            gpu = get_gpu_count()
    open_server(maxcpu=cpu, maxgpu=gpu, port=port)

########NEW FILE########
__FILENAME__ = openrestart
if __name__ == '__main__':
    from playdoh import *
    open_restart_server()

########NEW FILE########
__FILENAME__ = synchandler
from baserpc import *
from rpc import *
from gputools import *
from resources import *
from debugtools import *
from codehandler import *
from threading import Thread, Lock
from Queue import Queue

import sys
import time
import traceback
import os

__all__ = ['SyncHandler', 'Tubes', 'Node',
           'ParallelTask', 'TaskRun']


class Node(object):
    def __init__(self, index, machine, type, unitidx=0):
        """
        A Node represents an abstract working unit in the graph. It is uniquely
        identified by an integer between 0 and N-1 if there are N nodes in the
        graphs.
        A Node can be mapped to a CPU/GPU or to a machine (type='CPU', 'GPU' or
        'machine').
        'unitidx' is then the CPU/GPU index between 0 and K-1 (K-core machine),
        and machine is
        a Machine object.
        """
        self.index = index
        self.machine = Machine(machine)
        self.type = type
        self.unitidx = unitidx

    def __repr__(self):
        return '<Node %d on %s, %s %d>' % (self.index,
                                           self.machine,
                                           self.type,
                                           self.unitidx + 1)


class TubeIn(object):
    def __init__(self, name):
        """
        Represents a one-way communication between two Nodes.
        Node A sends an object to Node B and B waits until it receives the
        object.
        Objects are stored in a FIFO queue. This object is *stored on the
        target* (Node B).

        The name is used by the source to identify the tube on the target Node.
        """
#        log_debug('creating Tube <%s>' % name)
        self.name = name
        self._queue = None

    def get_queue(self):
        if self._queue is None:
            self._queue = Queue()
        return self._queue

    queue = property(get_queue)

    def pop(self):
        """
        Removes and returns an item from the queue. If the queue is empty,
        blocks
        until it is not.
        """
#        return self.child_conns[self.unitidx].recv()
        log_debug("popping tube <%s>..." % self.name)
        data = self.queue.get(True)
        log_debug("tube <%s> popped!" % self.name)
        return data

    def local_push(self, obj):
        """
        Puts an object into the queue. Not blocking.
        Is called remotely by the source machine.
        """
        log_debug('local pushing tube <%s>' % self.name)
        self.queue.put(obj)

    def empty(self):
        return self.queue.empty()

    def __repr__(self):
        return "<TubeIn '%s'>" % (self.name)


class TubeOut(object):
    def __init__(self, name, to_node, task_id, this_machine):
#        log_debug('creating Tube <%s> to %s' % (name, str(to_node)))
        self.name = name
        self.to_node = to_node
        self.task_id = task_id
        self.this_machine = this_machine

    def push(self, obj):
        # different machine
        if self.to_node.machine == self.this_machine:
            log_debug('pushing tube <%s> (same machine)' % self.name)
#            while True:
            self.parent_conns[self.to_node.unitidx].send(('_push',
                                                          (self.name, obj),
                                                           {}))
#                if self.parent_conns[self.to_node.unitidx].recv():
#                    break
#                log_debug("pickling error, sending data again")
        # same machine
        else:
#            log_debug(str((self.to_node.machine, self.this_machine)))
            log_debug('pushing tube <%s> (different machine)' % self.name)

            # send distant push to the server using the second channel
            args = (self.to_node,
                    self.name,
                    obj)
            i = self.unitidx + (len(self.child_conns) / 2)
            self.child_conns[i].send(('_distant_push', args, {}))

    def __repr__(self):
        return "<TubeOut '%s' connected to %s>" % (self.name,
                                                   str(self.to_node))


class Tubes(object):
    def __init__(self, tubes_in, tubes_out):
        self.tubes_in = tubes_in
        self.tubes_out = tubes_out

    def get_tubes_in(self):
        names = self.tubes_in.keys()
        names.sort()
        return names

    def get_tubes_out(self):
        names = self.tubes_out.keys()
        names.sort()
        return names

    def pop(self, name):
#        log_debug('in'+name+str(self.tubes_in))
        obj = self.tubes_in[name].pop()
        # BUG FIX FOR LINUX
        time.sleep(.01)
        return obj

    def push(self, name, obj):
#        log_debug('out'+name+str(self.tubes_out))
        self.tubes_out[name].push(obj)
        # BUG FIX FOR LINUX
        time.sleep(.01)

    def register(self, index, child_conns, parent_conns):
        for tube in self.tubes_out.itervalues():
            tube.unitidx = index
            tube.child_conns = child_conns
            tube.parent_conns = parent_conns

    def __repr__(self):
        return '<Tubes object, tubes_in=%s, tubes_out=%s>' % \
                (str(self.tubes_in), str(self.tubes_out))


#class Result(object):
#    def __init__(self, result):
#        self.result = result


def process_serve(unitindex, child_conns, parent_conns, shared_data,
                  task_class, all_nodes, index, tubes, unit_type, do_redirect):
    """
    Process server.
    This function is called on the processes of the current machine. It
    handles task initializing and launching, and allows to poll for the task's
    status asynchronously.
    shared_data is a read-only dict in shared memory (only numpy arrays)
    index is the Node index
    """
    # allows the tubes to access the connections to other processes
    tubes.register(unitindex, child_conns, parent_conns)

    # Opens the PyCUDA context at the beginning
#    if unit_type == 'GPU':
#        set_gpu_device(unitindex)
#        if task.do_redirect:
#            sys.stdin = file(os.devnull)
#            sys.stdout = file(os.devnull)

#    if unit_type == 'GPU':
#        set_gpu_device(unitindex)

    task = task_class(index, unitindex, all_nodes, tubes,
                      shared_data, unit_type)
    thread = None
#    node = all_nodes[index]
    conn = child_conns[unitindex]

    def execute(m, a, k):
        log_debug('executing method <%s>' % m)
        if hasattr(task, m):
#            result = getattr(task, m)(*a, **k)
            try:
                result = getattr(task, m)(*a, **k)
            except:
                log_warn("An exception occurred in sub-process #%d" %
                    (unitindex))
                exc = traceback.format_exc()
                log_warn(exc)
                #log_warn("An exception occurred in the task: "+str(e))
                result = None
        else:
            log_warn('Task object has no method <%s>' % m)
            result = None
#        log_debug('execute function finished with result <%s>' % str(result))
        return result

    def start(m, a, k):
        if unit_type == 'GPU':
            set_gpu_device(unitindex)
            if do_redirect:
                sys.stdin = file(os.devnull)
                sys.stdout = file(os.devnull)
            if do_redirect is None and os.name == 'posix':
                log_warn("WARNING: specify do_redirect=True if CUDA code is \
                    not compiling. see \
                    <http://playdoh.googlecode.com/svn/docs/playdoh.html#gpu>")
        execute(m, a, k)

        # get the result
#        log_debug("get_result")
        result = execute('get_result', (), {})

        # send it to the local server
#        log_debug("sending result to the local server")
        i = unitindex + (len(child_conns) / 2)
        child_conns[i].send(('send_result', (result,), {}))

        if unit_type == 'GPU':
            close_cuda()

    while True:
        log_debug('process_serve %d waiting...' % unitindex)
#        received = conn.recv()
#        log_debug('process_serve received <%s>' % str(received))
#        try:
        # HACK: sometimes, pickling error on Linux
#        while True:
#            try:
        method, args, kwds = conn.recv()
#                conn.send(True) # OK
#                break
#            except:
#                conn.send(False) # NOT OK, send again

#        except:
#            log_warn("connection has been closed")
#            continue
        log_debug('process_serve %d received method <%s>' % (unitindex,
                                                             method))
        if method is None:
#            log_debug("SENDING FINISHED TO LOCAL SERVER")
            conn.send(None)
            break
#        elif method == '_process_status':
#            continue
#        elif method is '_join':
#            thread.join()
        elif method == '_push':
            tubes.tubes_in[args[0]].local_push(args[1])  # args = (name, obj)
#            conn.send(None)
        elif method == 'start':
            thread = Thread(target=start, args=(method, args, kwds))
#            log_debug('starting thread...')
            thread.start()
#        elif method == '_get_status':
#            if thread is None:
#                status = 'not started'
#            elif thread.is_alive():
#                status = 'running'
#            else:
#                status = 'finished'
#            log_debug('status is <%s>' % status)
#            conn.send(status)
        elif method == '_pass':
            log_debug('pass!')
            time.sleep(.2)
        else:
            result = execute(method, args, kwds)
            conn.send(result)
    log_debug('process_serve finished')


class SyncHandler(object):
    def __init__(self):
        self.tubes_in = {}
        self.tubes_out = {}
        self.thread = None
        self.result = None
        self.unitindices = []
        self.resultqueue = None
        self.pool = None
        self.clients = None

        # used to wait for process_serve before sending initialize
        self.initqueue = Queue()

    def create_tubes(self):
        for i in xrange(len(self.nodes)):
            node = self.nodes[i]
            # change the unitindex to match idle units
            node.unitidx = self.unitindices[i]
            tubes_in = {}
            tubes_out = {}
            for (name, i1, i2) in self.topology:
                if i1 == node.index:
                    to_node = [n for n in self.all_nodes if n.index == i2][0]
                    tubes_out[name] = TubeOut(name,
                                              to_node,
                                              self.task_id,
                                              self.local_machine)
                if i2 == node.index:
                    tubes_in[name] = TubeIn(name)
            self.tubes[node.unitidx] = Tubes(tubes_in, tubes_out)
            log_debug('Tubes created for node %s: %s' %
                (str(node), str(self.tubes[node.unitidx])))

    def submit(self, task_class, task_id, topology, all_nodes, local_nodes,
               type='CPU', shared_data={}, do_redirect=None):
        """
        Called by the launcher client, submits the task, the
        topology of the graph
        (with abstract nodes indexed by an integer), and a mapping
        assigning each node
        to an actual computing unit in the current machine.
        topology is a dict {pipe_name: (index1, index2)}
        mapping is a dict {index: Node}
        WARNING: Nodes in mapping should contain the Process indices
        that are idle
        """
        # If no local nodes
        if len(local_nodes) == 0:
            log_info("No nodes are being used on this machine")
            return
        self.topology = topology
        self.all_nodes = all_nodes
        self.nodes = local_nodes  # local nodes
        self.local_machine = local_nodes[0].machine
        self.type = type
        self.task_id = task_id
        self.task_class = task_class
        self.tubes = {}  # dict {unitidx: Tubes object}

        # computing the number of units to use on this computer
        unitindices = {}
        for n in self.nodes:
            unitindices[n.unitidx] = None
        self.units = len(unitindices)

        # finds idle units
        self.pool = self.pools[type]
        self.pool.globals = globals()
        # gets <self.units> idle units
        self.unitindices = self.pool.get_idle_units(self.units)
        for n in self.nodes:
            # WARNING: reassign idle units to nodes,
            # unitidx=0 ==> unitidx = first idle unit
            # Node unitidxs must be a consecutive list
#            log_debug(self.unitindices)
#            log_debug(n.unitidx)
            n.unitidx = self.unitindices[n.unitidx]

        self.create_tubes()

        # relaunch the needed units and give them the shared data
        # which must be specified in submit
        if len(shared_data) > 0:
            self.pool.restart_workers(self.unitindices, shared_data)

        # launch the process server on every unit
        for node in self.nodes:
            self.pool.set_status(node.unitidx, 'busy')
            self.pool[node.unitidx].process_serve(task_class,
                                                  self.all_nodes,
                                                  node.index,
                                                  self.tubes[node.unitidx],
                                                             type,
                                                             do_redirect)

        # now initialize can begin
        log_debug("<submit> has finished!")

        # used to wait for the task to finish
        self.resultqueue = dict([(i, Queue()) for i in self.unitindices])

        self.initqueue.put(True)

    def distant_push(self, node, tube, data):
        log_debug('distant push to %s for %s' % (str(node), str(tube)))
        self.pool.send(('_push', (tube, data), {}),
                                                unitindices=[node.unitidx],
                                                             confirm=True)

    def initialize(self, *argss, **kwdss):
        # argss[i] is a list of arguments of rank i for initialize,
        # one per node on this machine

        log_debug("Waiting for <submit> to finish...")
        self.initqueue.get()
        time.sleep(.1)

        log_info("Initializing task <%s>" % self.task_class.__name__)

        k = len(argss)  # number of non-named arguments
        keys = kwdss.keys()  # keyword arguments

        for i in xrange(len(self.unitindices)):
            args = [argss[l][i] for l in xrange(k)]
            kwds = dict([(key, kwdss[key][i]) for key in keys])
            self.pool.send(('initialize', args, kwds),
                            unitindices=[self.unitindices[i]], confirm=True)
        return self.pool.recv(unitindices=self.unitindices)

    def initialize_clients(self):
        # get the list of individual machines
        _machines = [node.machine.to_tuple() for node in self.all_nodes]
        self.distant_machines = []
        for m in _machines:
            if (m not in self.distant_machines) and \
                    (m != self.local_machine.to_tuple()):
                self.distant_machines.append(m)

        # initialize RpcClients
#        log_info("CONNECTING")
        self.clients = RpcClients(self.distant_machines,
                             handler_class=SyncHandler,
                             handler_id=self.task_id)
        self.clients.connect()
        self.clients_lock = Lock()

    def clients_push(self, to_node, name, obj):
        machine = to_node.machine.to_tuple()
        index = self.distant_machines.index(machine)
        log_debug("server: relaying subprocess for distant push \
                    to node <%s>" % str(to_node))

#        log_debug("ACQUIRING CLIENT LOCK")
        self.clients_lock.acquire()
        self.clients.set_client_indices([index])
#        log_debug("DISTANT PUSH")
        self.clients.distant_push(to_node, name, obj)
#        log_debug("RELEASING CLIENT LOCK")
        self.clients_lock.release()

    def close_clients(self):
        if self.clients is None:
            return
        self.clients.set_client_indices(None)
        self.clients.disconnect()

    def recv_from_children(self, index):
        while True:
#            log_debug("LOCAL SERVER WAITING %d" % index)
            r = self.pool.recv(unitindices=[self.pool.workers + index])[0]
#            log_debug("LOCAL SERVER RECV")# % str(r))

#            if r is None:
#                log_server("LOCAL SERVER exiting")
#                break

            result, args, kwds = r

            # distant push
            if result == '_distant_push':
                to_node, name, obj = args

                self.clients_push(to_node, name, obj)
#                client = RpcClient(machine, handler_class=SyncHandler,
#                           handler_id=task_id)
#                client.distant_push(to_node, name, obj)

            # retrieve result and quit the loop on the server
            elif result == 'send_result':
#                self.task_result = args[0]
                log_debug("server: received result from subprocesses")
                self.resultqueue[index].put(args[0])
                break

#        if index == self.unitindices[0]:
#            time.sleep(1)
#            log_info("CLEARING POOL")
#            self.clear_pool()
#            log_debug("CLOSING RPCCLIENTS")
#            self.close_clients()
#        log_debug("RECV FROM CHILDREN FINISHED")

    def start(self):
        log_info("Starting task")
        self.pool.send(('start', (), {}), unitindices=self.unitindices,
                                      confirm=True)

        self.initialize_clients()

        # listen for children subprocesses
        self.recv_thread = {}  # dict([(i, None) for i in self.unitindices])
        for i in self.unitindices:
            self.recv_thread[i] = Thread(target=self.recv_from_children,
                                         args=(i,))
            self.recv_thread[i].start()

    def clear_pool(self):
        if self.pool is None:
            return
        [self.pool.set_status(i, 'idle') for i in self.unitindices]
        # closes process_serve
        log_info("Terminating task")
        self.pool.send((None, (), {}), unitindices=self.unitindices,
                                   confirm=True)

    def get_info(self, *args, **kwds):
        """
        Obtains information about the running task
        """
        log_info("Getting task information...")

        k = len(args)  # number of non-named arguments
        keys = kwds.keys()  # keyword arguments

        for i in xrange(len(self.unitindices)):
            args = [argss[l][i] for l in xrange(k)]
            kwds = dict([(key, kwdss[key][i]) for key in keys])
            self.pool.send(('get_info', args, kwds),
                            unitindices=[self.unitindices[i]],
                            confirm=True)

        info = self.pool.recv(unitindices=self.unitindices)
        return info

#    def wait(self):
#        """
#        Once the task has been started, waits until it has finished
#        """
#        # HACK: unblocks the connection on the pool (cannot send() while
#        # another thread recv() in process_serve)
##        self.pool.send(('_pass', (), {}), unitindices=self.unitindices)
##        log_debug((self.unitindices, self.pool.workers))
#        pipes = [i+self.pool.workers for i in self.unitindices]
#        log_debug('waiting on pipes %s...' % str(pipes))
#        # unit indices of units which have not finished yet
##        leftindices = list(set(self.unitindices).difference(self.finished))
#
#        # receives "task finished" on the second channel
#        self.pool.recv(unitindices=pipes)

#    def get_status(self):
#        log_debug("Getting task status...")
#        self.pool.send(('_get_status', (), {}), unitindices=self.unitindices)
#        return self.pool.recv(unitindices=self.unitindices, discard=
#        'task finished')

    def get_result(self):
        """
        Blocks until the task has completed
        """
        # wait
        # TODO: implement WAIT with a Queue instead of a long recv in a
        # dedicated channel
#        pipes = [i+self.pool.workers for i in self.unitindices]
#        log_debug('waiting on pipes %s...' % str(pipes))
        # receive "task finished" on the second channel
#        self.pool.recv(unitindices=pipes)
#        log_debug("joining local server thread")
        if self.resultqueue is not None:
            log_debug("server: waiting for the task to finish")
            results = [self.resultqueue[i].get() \
                            for i in self.resultqueue.keys()]

#        for i in self.recv_thread.keys():
#            self.recv_thread[i].join()

        time.sleep(.1)
        self.clear_pool()
        self.close_clients()

        return results


class TaskRun(object):
    """
    Contains information about a parallel task that has been launched
    by the :func:`start_task` function.

    Methods:

    ``get_info()``
        Returns information about the current run asynchronously.

    ``get_result()``
        Returns the result. Blocks until the task has finished.
    """
    def __init__(self, task_id, type, machines, nodes, args, kwds):
        self.task_id = task_id
        self.nodes = dict([(node.index, node) for node in nodes])
        self.machines = machines  # list of Machine object
        self.type = type
        self._machines = [m.to_tuple() for m in self.machines]
        self.local = None
        # arguments of the task initialization
        self.args, self.kwds = args, kwds

    def set_local(self, v):
        log_debug("setting local to %s" % str(v))
        self.local = v

    def get_machines(self):
        return self._machines

    def get_machine_index(self, machine):
        for i in xrange(len(self.machines)):
            if (self.machines[i] == machine):
                return i

    def concatenate(self, l):
        """
        Concatenates an object returned by RpcClients to a list
        adapted to the list
        of nodes
        """
        newl = {}
        for i, n in self.nodes.iteritems():
            machine_index = self.get_machine_index(n.machine)
            unit_index = n.unitidx
            newl[i] = l[machine_index][unit_index]
        newl = [newl[i] for i in xrange(len(self.nodes))]
        return newl

    def get_info(self):
        GC.set(self.get_machines(), handler_class=SyncHandler,
                                 handler_id=self.task_id)
        disconnect = GC.connect()
        log_info("Retrieving task info")
        info = GC.get_info()
        if disconnect:
            GC.disconnect()
        return self.concatenate(info)

    def get_result(self):
        if not self.local:
            time.sleep(2)
        else:
            time.sleep(.1)
        GC.set(self.get_machines(), handler_class=SyncHandler,
                                 handler_id=self.task_id)
        disconnect = GC.connect()
        if not self.local:
            log_info("Retrieving task results")
        result = GC.get_result()
        if disconnect:
            GC.disconnect()
        result = self.concatenate(result)
        if self.local:
            close_servers(self.get_machines())
        return result

    def __repr__(self):
        units = len(self.nodes)
        if units > 1:
            plural = 's'
        else:
            plural = ''
        return "<Task '%s' on %d machines and %d %s%s>" % (self.task_id,
                                                          len(self.machines),
                                                          len(self.nodes),
                                                          self.type,
                                                          plural)


class ParallelTask(object):
    """
    The base class from which any parallel task must derive.

    Three methods must be implemented:

    ``initialize(self, *args, **kwds)``
        Initialization function, with any arguments and keyword arguments,
        which
        are specified at runtime in the :func:`start_task` function.

    ``start(self)``
        Start the task.

    ``get_result(self)``
        Return the result.

    One method can be implemented.

    ``get_info(self)``
        Return information about the task. Can be called asynchronously at
        any time
        by the client, to obtain for example the current iteration number.

    Two methods from the base class are available:

    ``push(self, name, data)``
        Put some ``data`` into the tube ``name``. Named tubes are
        associated to a single source
        and a single target. Only the source can call this method.
        Note that several tubes in the network can have
        the same name, but two tubes entering or exiting a given
        node cannot have the same name.

    ``pop(self, name)``
        Pop data in the tube ``name``: return the first item in
        the tube (FIFO queue) and remove it.
        If the tube is empty, block until the source put some
        data into it. The call to this method
        is equivalent to a synchronisation barrier.

    Finally, the following read-only attributes are available:

    ``self.index``
        The index of the current node, between 0 and n-1 if there
        are n nodes in the network.

    ``self.unitidx``
        The index of the CPU or GPU on the machine running the
        current node.

    ``self.shared_data``
        The shared data dictionary (see :ref:`shared_data`).

    ``self.unit_type``
        The unit type on this node, ``'CPU'`` or ``'GPU'``.

    ``self.tubes_in``
        The list of the incoming tube names on the current node.

    ``self.tubes_out``
        The list of the outcoming tube names on the current node.
    """
    def __init__(self, index, unitidx, nodes, tubes, shared_data, unit_type):
        self.index = index
        self.unitidx = unitidx
        self.nodeidx = index
        self.nodes = nodes
        self.node = nodes[index]
        self.tubes = tubes
        self.shared_data = shared_data
        self.unit_type = unit_type
        self.tubes_in = self.tubes.get_tubes_in()
        self.tubes_out = self.tubes.get_tubes_out()

    def pop(self, name):
        return self.tubes.pop(name)

    def push(self, name, data):
        self.tubes.push(name, data)

    def initialize(self):
        log_warn("The <initialize> method of a parallel task may \
be implemented")

    def start(self):
        log_warn("The <start method> of a parallel task must be \
implemented")

    def get_result(self):
        """
        Default behavior: returns self.result
        """
        return self.result

    def get_info(self):
        log_warn("The <get_info> method of a parallel task may be \
implemented")

########NEW FILE########
__FILENAME__ = userpref
from cache import *
#from debugtools import *
#from .debugtools import level
import os
import os.path
import imp

__all__ = ['DEFAULTPREF', 'USERPREF']

# Default preference values
DEFAULTPREF = {}
# authentication key in the network
DEFAULTPREF['authkey'] = 'playdohauthkey'

# default port
DEFAULTPREF['port'] = 2718

# default port
DEFAULTPREF['connectiontrials'] = 5

# default connectiontimeout (in s)
DEFAULTPREF['connectiontimeout'] = 30

# default port
DEFAULTPREF['favoriteservers'] = []

# default port
DEFAULTPREF['loglevel'] = 'INFO'


class UserPref(object):
    """
    User preferences. Allows to load and save user preference by getting
    the default value if it is not specified by the user, or by loading/saving
    to a file in ``~/.playdoh/userpref.py`` which must defines a dictionary
    named ``USERPREF``.
    To load a user preference, use ``USERPREF[key]`` where ``USERPREF`` is
    a global variable.
    """
    def __init__(self):
        self.preffile = os.path.join(BASEDIR, 'userpref.py')
        self.userpref = {}
        self.load_default()
        self.load()

    def load_default(self):
        """
        Load default values
        """
        for key, val in DEFAULTPREF.iteritems():
            self.userpref[key] = DEFAULTPREF[key]

    def load(self):
        """
        Load values from the user preference file
        """
        if os.path.exists(self.preffile):
            module = imp.load_source('userpref', self.preffile)
            userpref = getattr(module, 'USERPREF')
            for key, val in userpref.iteritems():
                self.userpref[key] = val

    def save(self):
        string = "USERPREF = {}\n"
        for key in self.userpref.keys():
            val = self.userpref[key]
            if type(val) is str or type(val) is unicode:
                string += "USERPREF['%s'] = '%s'\n" % (key, str(val))
            else:
                string += "USERPREF['%s'] = %s\n" % (key, str(val))
        f = open(self.preffile, 'w')
        f.write(string)
        f.close()

    def __getitem__(self, key):
        if key not in self.userpref.keys():
            self.userpref[key] = None
        return self.userpref[key]

    def __setitem__(self, key, val):
        self.userpref[key] = val

USERPREF = UserPref()

########NEW FILE########
__FILENAME__ = import1
import numpy
from import2 import square


def funimp(n):
    return square(numpy.arange(n))

########NEW FILE########
__FILENAME__ = import2
def square(x):
    return x * x

########NEW FILE########
__FILENAME__ = testclass
from import1 import funimp


class TestClass(object):
    def fun(self, n):
        return funimp(n)

########NEW FILE########
__FILENAME__ = test
import unittest
import os
import os.path
import re
import time
import multiprocessing
from playdoh import *


class BaseLocalhostTest(unittest.TestCase):
    def setUp(self):
        log_debug("STARTING SERVER FOR TEST %str" % self.id())
        self.p = multiprocessing.Process(target=open_base_server)
        self.p.start()
        time.sleep(.1)

    def tearDown(self):
        log_debug("CLOSING SERVER")
        close_base_servers('localhost')
        self.p.join(3.0)
        time.sleep(.2)


class LocalhostTest(unittest.TestCase):
    def setUp(self):
        if hasattr(self, 'maxcpu'):
            maxcpu = self.maxcpu
        else:
            maxcpu = None
        if hasattr(self, 'maxgpu'):
            maxgpu = self.maxgpu
        else:
            maxgpu = None

        log_debug("STARTING SERVER FOR TEST %str" % self.id())
        self.p = multiprocessing.Process(target=open_server,
                                         args=(None, maxcpu, maxgpu))
        self.p.start()
        time.sleep(.1)

    def tearDown(self):
        log_debug("CLOSING SERVER")
        close_servers('localhost')
        self.p.join(3.0)
        time.sleep(.2)


def all_tests(folder=None):
    if folder is None:
        folder = os.path.dirname(os.path.realpath(__file__))
    pattern = '^(test_[^.]+).py$'
    files = os.listdir(folder)
    files = [file for file in files if re.match(pattern, file)]

    suites = []
    for file in files:
        if file in skip:
            continue
        modulename = re.sub(pattern, '\\1', file)
        module = __import__(modulename)
        try:
            suites.append(module.test_suite())
        except:
            log_warn("module '%s' has no method 'test_suite'" % modulename)

    allsuites = unittest.TestSuite(suites)
    return allsuites


def test():
    unittest.main(defaultTest='all_tests')


skip = ['test_examples.py']


if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = test_asyncjobhandler
from playdoh import *
from test import *
from multiprocessing import Process
import sys
import time
import unittest


def fun(x):
    return x * x


class ASyncJobHandlerTest(LocalhostTest):
    def test_1(self):
        # new connection to localhost
        client = RpcClient('localhost', handler_class=AsyncJobHandler)
        client.connect()
        jobs = [Job(fun, i) for i in xrange(6)]

        jobids = client.submit(jobs, units=2)

        time.sleep(2)
        status = client.get_status(jobids)
        for s in status:
            self.assertEqual(s, 'finished')

        results = client.get_results(jobids)
        client.disconnect()

        for i in xrange(len(results)):
            self.assertEqual(results[i], i * i)

        # erases the jobs
        [Job.erase(id) for id in jobids]


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(ASyncJobHandlerTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_baserpc
from playdoh import *
from test import *
import sys
import time
import unittest


class BaseRpcTest(BaseLocalhostTest):
    def test_1(self):
        client = BaseRpcClient('localhost')
        self.assertEqual(client.execute("hello world"), "hello world")

    def test_2(self):
        client = BaseRpcClient('localhost')
        client.connect()
        self.assertEqual(client.execute("hello world"), "hello world")
        client.disconnect()


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(BaseRpcTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cmaes
from playdoh import *
from test import *
import numpy
import sys
import time
from numpy import int32, ceil


def fitness_fun(x):
    return numpy.exp(-x * x)


class CMAESTest(unittest.TestCase):
    def test_1(self):
        time.sleep(.2)
        result = maximize(fitness_fun,
                          algorithm=CMAES,
                          maxiter=3,
                          popsize=1000,
                          cpu=1,
                          x_initrange=[-5, 5])
        self.assertTrue(abs(result[0]['x']) < .1)

    def test_2(self):
        p1 = Process(target=open_server, args=(2718, 1, 0))
        p1.start()
        time.sleep(.2)

        p2 = Process(target=open_server, args=(2719, 1, 0))
        p2.start()
        time.sleep(.2)

        machines = [('localhost', 2718), ('localhost', 2719)]
        result = maximize(fitness_fun,
                          algorithm=CMAES,
                          maxiter=3,
                          popsize=1000,
                          machines=machines,
                          x_initrange=[-5, 5])
        self.assertTrue(abs(result[0]['x']) < .1)

        close_servers(machines)
        time.sleep(.2)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(CMAESTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_codehandler
from playdoh import *
from test import *
from imports.testclass import TestClass
import unittest
import cPickle
import time


class TestHandler(object):
    def test(self, pkl_class):
        o = pkl_class()
        return o.fun(3)


class CodePickleTest(LocalhostTest):
    def test_1(self):
        pkl_class = pickle_class(TestClass)
        send_dependencies('localhost', TestClass)

        client = RpcClient('localhost', handler_class=TestHandler)
        result = client.test(pkl_class)
        [self.assertEqual(result[i], i * i) for i in xrange(2)]


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(CodePickleTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_connection
from playdoh import *
from test import *
from multiprocessing import Process
from threading import Thread
import sys
import time
import unittest
import gc
import cPickle
from numpy.random import rand


def serve():
    # echo server
    conn, client = accept(('', 2718))
    while True:
        data = conn.recv()
        if data is None:
            break
        log_debug("received %d" % len(data))
        conn.send(data)
    conn.close()


class ConnectionTest(unittest.TestCase):
    def test_1(self):
        p = Process(target=serve)
        p.start()

        conn = connect(('localhost', 2718))
        for i in xrange(20):
            data = cPickle.dumps(rand(100, 100) * 100000)
            log_debug("%d, sending %d" % (i, len(data)))
            conn.send(data)
            data2 = conn.recv()
            self.assertEqual(data, data2)
        conn.send(None)
        conn.close()
        p.terminate()
        p.join()


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(ConnectionTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_examples
from test import *
import os
import sys
import time
import playdoh


class ExamplesTest(unittest.TestCase):
    def test_1(self):
        examples_dir = '../examples'
        os.chdir(examples_dir)
        skip = ['external_module.py', 'resources.py', 'allocation.py']
        files = os.listdir('.')
        for file in files:
            if file in skip:
                continue
            if os.path.splitext(file)[1] == '.py':
                log_info("Running %s..." % file)
                os.system('python %s' % file)
                time.sleep(.5)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(ExamplesTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_filetransfer
from playdoh import *
from test import *
from multiprocessing import Process
import sys
import time
import unittest
import gc


class FileTransferTest(LocalhostTest):
    def test_1(self):
        filename = os.path.realpath(__file__)
        result = send_files('localhost', filename, 'cache/TEST_codepickle.py')
        self.assertEqual(result[0], True)

        result = erase_files('localhost', 'cache/TEST_codepickle.py')
        self.assertEqual(result[0], True)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(FileTransferTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_ga
from playdoh import *
from test import *
import numpy
import sys
import time
from numpy import int32, ceil


def fitness_fun(x):
    return numpy.exp(-x * x)


class GATest(unittest.TestCase):
    def test_1(self):
        result = maximize(fitness_fun,
                          algorithm=GA,
                          maxiter=3,
                          popsize=1000,
                          cpu=3,
                          x_initrange=[-5, 5])
        self.assertTrue(abs(result[0]['x']) < .1)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(GATest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_gpu
# -*- coding: utf-8 -*-
from playdoh import *
from test import *
from multiprocessing import Process
from numpy import int32, ones, hstack
import time


code = '''
__global__ void test(double *x, int n)
{
 int i = blockIdx.x * blockDim.x + threadIdx.x;
 if(i>=n) return;
 x[i] *= 2.0;
}
'''


def run(index=0):
    set_gpu_device(index)

    n = 100
    mod = pycuda.compiler.SourceModule(code)
    f = mod.get_function('test')
    x = pycuda.gpuarray.to_gpu(ones(n))
    f(x, int32(n), block=(n, 1, 1))
    y = x.get()
    close_cuda()

    if max(y) == min(y) == 2:
        log_info("GPU test #%d PASSED" % (index + 1))
    else:
        log_warn("GPU test #%d FAILED" % (index + 1))

    return y


def pycuda_fun(n=100):

    import pycuda
    from numpy import ones, int32
    code = '''
    __global__ void test(double *x, int n)
    {
     int i = blockIdx.x * blockDim.x + threadIdx.x;
     if(i>=n) return;
     x[i] *= 2.0;
    }
    '''

    mod = pycuda.compiler.SourceModule(code)
    f = mod.get_function('test')
    x = pycuda.gpuarray.to_gpu(ones(n))
    f(x, int32(n), block=(n, 1, 1))
    y = x.get()
    return y


class GpuTest(unittest.TestCase):
    def test_1(self):

        if not CANUSEGPU:
            log_warn("PyCUDA is not installed, can't use GPU")
            return

        p1 = Process(target=run, args=(0,))
        p1.start()
        time.sleep(.2)

        p2 = Process(target=run, args=(1,))
        p2.start()
        time.sleep(.2)

        p1.join()
        p2.join()

        log_info("GPU tests passed")

    def test_2(self):
        log_info("test2")
        if not CANUSEGPU:
            log_warn("PyCUDA is not installed, can't use GPU")
            return

        r = map(pycuda_fun, [100, 100], gpu=1)
        r = hstack(r)
        b = r.max() == r.min() == 2
        if b:
            log_info("GPU jobs passed")
        else:
            log_warn("GPU jobs failed")
        self.assertTrue(b)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(GpuTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_map
from playdoh import *
from test import *
from multiprocessing import Process
import sys
import time
import unittest


def fun(x):
    return x * x


class MapTest(LocalhostTest):
    def test_1(self):
        r = map(fun, [1, 2, 3, 4], machines='localhost')
        self.assertEqual(r, [1, 4, 9, 16])
        set_total_resources(['localhost'], CPU=2)
        r = map(fun, [1, 2, 3, 4], machines='localhost')
        self.assertEqual(r, [1, 4, 9, 16])


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(MapTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pool
from playdoh import *
import time
import unittest
import sys
from numpy import arange, max
from numpy.random import rand


def fun(x, y, wait=.1):
    time.sleep(wait)
    return x + y


def test_numpy(index, child_conns, parent_conns, x):
    conn = child_conns[index]
    time.sleep(1)
    conn.send(x)


def serve(index, child_conns, parent_conns):
    log_info("Serving started")
    while True:
        str = child_conns[index].recv()
        if str is None:
            break
        log_info("Hello %s" % str)
    log_info("Serving finished")


class PoolTest(unittest.TestCase):
    def test_1(self):
        p = CustomPool(2)
        results = p.map(fun, {}, [1, 2], [3, 4])
        self.assertEqual(results[0], 4)
        self.assertEqual(results[1], 6)

        p.clear_tasks()

        ids = p.submit_tasks(fun, {}, [1, 2], [3, 4])
        self.assertEqual(ids[1], 1)  # checks that the tasks have been cleared
        self.assertEqual(p.get_results(ids)[1], 6)

        p.close()

    def test_2(self):
        p = CustomPool(2)
        ilist = arange(10)

        ids1 = p.submit_tasks(fun, {}, x=ilist, y=10 * ilist)
        time.sleep(.5)
        ids2 = p.submit_tasks(fun, {}, x=ilist, y=10 * ilist)

        for _ in xrange(5):
            if p.has_finished(ids2):
                break
            log_debug("waiting")
            time.sleep(.5)
        self.assertEqual(p.has_finished(ids2), True)

        results1 = p.get_results(ids1)
        results2 = p.get_results(ids2)

        p.close()

        for i in ilist:
            self.assertEqual(results1[i], results2[i])
            self.assertEqual(results1[i], 11 * i)

    def test_status(self):
        pool = Pool(3)
        # 3 CPUs

        p = CustomPool([1, 2])
        # Using only CPU #1 and #2
        p.pool = pool

        ilist = arange(2)

        ids1 = p.submit_tasks(fun, {}, x=ilist, y=10 * ilist,
                                    wait=[1] * len(ilist))
        time.sleep(.1)
        self.assertEqual(p.pool.get_status(), ['idle', 'busy', 'busy'])

        results1 = p.get_results(ids1)
        time.sleep(.1)
        self.assertEqual(p.pool.get_status(), ['idle'] * 3)

        p.close()

        for i in ilist:
            self.assertEqual(results1[i], 11 * i)

    def test_pools(self):
        """
        This test illustrates how a single pool of processes
        (as many processes as CPUs)
        can be used with multiple CustomPool objects.
        """
        pool = CustomPool.create_pool(4)

        cp1 = CustomPool([0])
        cp1.pool = pool

        cp2 = CustomPool([1, 2, 3])
        # the two CustomPool objects refer to the same Pool object.
        cp2.pool = pool

        self.assertEqual(pool.get_status(), ['idle'] * 4)

        ids1 = cp1.submit_tasks(fun, {}, [1, 2], [3, 4], [1] * 4)
        time.sleep(.1)
        self.assertEqual(pool.get_status(), ['busy', 'idle', 'idle', 'idle'])

        ids2 = cp2.submit_tasks(fun, {}, [1, 2, 3], [5, 6, 7], [1] * 3)
        time.sleep(.1)
        self.assertEqual(pool.get_status(), ['busy', 'busy', 'busy', 'busy'])

        r1 = cp1.get_results(ids1)
        r2 = cp2.get_results(ids2)

        time.sleep(.1)
        self.assertEqual(pool.get_status(), ['idle'] * 4)

        self.assertEqual(r1[1], 6)
        self.assertEqual(r2[-1], 10)

        pool.close()


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(PoolTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pso
from playdoh import *
from test import *
import numpy
import sys
import time
from numpy import int32, ceil


def fitness_fun(x_0):
    # test parameter name with '_'
    return numpy.exp(-x_0 * x_0)


def fitness_gpu(x):
    code = '''
    __global__ void test(double *x, int n)
    {
     int i = blockIdx.x * blockDim.x + threadIdx.x;
     if(i>=n) return;
     x[i] *= x[i];
    }
    '''
    n = len(x)

    mod = pycuda.compiler.SourceModule(code)
    f = mod.get_function('test')
    x2 = pycuda.gpuarray.to_gpu(x)
    f(x2, int32(n), block=(128, 1, 1), grid=(int(ceil(float(n) / 128)), 1))
    y = x2.get()
    return y


class PsoTest(unittest.TestCase):
    def test_1(self):
        result = maximize(fitness_fun,
                          algorithm=PSO,
                          maxiter=3,
                          popsize=1000,
                          cpu=1,
                          x_0_initrange=[-5, 5])
        self.assertTrue(abs(result[0]['x_0']) < .1)

    def test_gpu(self):
        if CANUSEGPU:
            result = minimize(fitness_gpu,
                              algorithm=PSO,
                              maxiter=3,
                              popsize=1024,
                              gpu=1,
                              x_initrange=[-5, 5])

            self.assertTrue(abs(result[0]['x']) < .1)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(PsoTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_resources
from playdoh import *
from test import *
from multiprocessing import Process
from threading import Thread
import sys
import time
import unittest
import gc
import cPickle


class ResourcesTest(LocalhostTest):
    def test_1(self):
        cpu = get_total_resources('localhost')[0]['CPU']
        set_total_resources('localhost', CPU=cpu - 1)
        resources = get_total_resources('localhost')[0]
        self.assertEqual(resources['CPU'], cpu - 1)

    def test_2(self):
        request_resources('localhost', CPU=2)
        resources = get_my_resources('localhost')[0]
        self.assertEqual(resources['CPU'], 2)

    def test_optimal(self):
        set_total_resources('localhost', CPU=3)
        request_all_resources('localhost', 'CPU')
        self.assertEqual(get_my_resources('localhost')[0]['CPU'], 3)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(ResourcesTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_rpc
from playdoh import *
from test import *
from multiprocessing import Process
from threading import Thread
import sys
import time


class TestHandler(object):
    def __init__(self):
        self.x = 0

    def set(self, x):
        self.x = x

    def test(self, y):
        return self.x + y

    def test1(self):
        log_info("ONE: %d" % self.x)
        time.sleep(1)
        log_info("ONE AGAIN: %d" % self.x)
        return self.x

    def test2(self):
        log_info("TWO")
        self.x = 10


class RpcTest(LocalhostTest):
    def atest_1(self):
        client = RpcClient('localhost', handler_class=TestHandler)
        client.connect()
        client.set(1)
        self.assertEqual(client.test(2), 3)
        client.set_handler_id('new_handler')  # creates a new handler
        self.assertEqual(client.test(3), 3)
        client.disconnect()

    def test_clients(self):
        servers = [('127.0.0.10', 2719), ('127.0.0.20', 2720)]

        p1 = Process(target=open_server, args=(servers[0][1], 1))
        p1.start()

        p2 = Process(target=open_server, args=(servers[1][1], 1))
        p2.start()

        clients = RpcClients(servers, handler_class=TestHandler)
        clients.connect()
        clients.set([10, 20])
        results = clients.test([1, 2])
        self.assertEqual(results[0], 11)
        self.assertEqual(results[1], 22)

        clients.set_client_indices([0])
        clients.set([100])
        results = clients.test([1])
        self.assertEqual(results[0], 101)

        clients.set_client_indices([1])
        clients.set([200])
        clients.set_client_indices(None)
        results = clients.test([1, 1])
        self.assertEqual(results[0], 101)
        self.assertEqual(results[1], 201)

        clients.disconnect()
        close_servers(servers)

        p1.join()
        p2.join()
        p1.terminate()
        p2.terminate()

    def _concurrent1(self):
        client = RpcClient('localhost', handler_class=TestHandler)
        self.r1 = client.test1()

    def _concurrent2(self):
        client = RpcClient('localhost', handler_class=TestHandler)
        self.r2 = client.test2()

    def atest_concurrent(self):
        """
        Two clients simultaneously connect to the same server, the
        two connections are simultaneously active.
        """
        # the first thread displays a variable on the distant handler
        # twice, within a 1 second interval
        t1 = Thread(target=self._concurrent1)
        t1.start()

        time.sleep(.05)

        # the second thread changes the value of the variable during
        # that second
        t2 = Thread(target=self._concurrent2)
        t2.start()

        t1.join()
        t2.join()

        self.assertEqual(self.r1, 10)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(RpcTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_synchandler
from playdoh import *
from test import *
from multiprocessing import Process
from numpy.random import rand
from numpy import max
import time


class TaskTest1(ParallelTask):
    def initialize(self, x):
        self.x = x

    def start(self):
        self.result = self.x ** 2

    def get_result(self):
        return self.result


class TaskTest2(TaskTest1):
    def start(self):
#        log_debug(self.tubes)
        self.result = self.x ** 2
        if self.node.index == 0:
#            log_info('I am 0, pushing now')
            self.tubes.push('tube1', 1)
        if self.node.index == 1:
#            log_info('I am 1, popping now')
            self.result += self.tubes.pop('tube1')


class TaskTest4(ParallelTask):
    def initialize(self, x, iterations):
        self.x = x
        self.iterations = iterations

    def start(self):
        for self.iteration in xrange(self.iterations):
#            log_debug('ITERATION %d' % self.iteration)
            self.tubes.push('right', self.x + 1)
            self.x += self.tubes.pop('right')
            time.sleep(.3)
        self.result = self.x

    def get_info(self):
        return self.iteration

    def get_result(self):
        return self.result


class TaskTestShared(ParallelTask):
    def start(self):
        self.result = None
        time.sleep(1)


class SynchandlerTest(unittest.TestCase):
    def test_1(self):
        """
        No tube test
        """
        time.sleep(2)
        x = rand(10)

        allocation = allocate(cpu=1)
        task = start_task(TaskTest1,
                          allocation=allocation,
                          args=(x,))

        result = task.get_result()
        self.assertTrue(max(abs(result - x ** 2)) < 1e-9)

    def test_2(self):
        """
        1 tube on a single machine with 2 CPUs
        """
        time.sleep(2)

        topology = [('tube1', 0, 1)]

        task = start_task(TaskTest2,
                          topology=topology,
                          cpu=2,
                          args=(3,))
        result = task.get_result()
        self.assertEqual(result, [9, 10])

    def test_3(self):
        """
        1 tube on two machines with 1 CPU each
        """
        time.sleep(2)

        p1 = Process(target=open_server, args=(2718, 1, 0))
        p1.start()
        time.sleep(.2)

        p2 = Process(target=open_server, args=(2719, 1, 0))
        p2.start()
        time.sleep(.2)

        machine1 = (LOCAL_IP, 2718)
        machine2 = (LOCAL_IP, 2719)
        machines = [machine1, machine2]
        task_id = "my_task"
        type = 'CPU'

        topology = [('tube1', 0, 1)]

        allocation = allocate(allocation={machine1: 1, machine2: 1},
                                          unit_type=type)

        task = start_task(TaskTest2, task_id, topology,
                          unit_type=type,
                          allocation=allocation,
                          args=(3,))
        result = task.get_result()

        self.assertEqual(result, [9, 10])
        close_servers([machine1, machine2])
        time.sleep(.2)

    def test_4(self):
        """
        4 nodes, 2 machines with 2 CPUs
        """
        time.sleep(2)

        p1 = Process(target=open_server, args=(2718, 2, 0))
        p1.start()
        time.sleep(.2)

        p2 = Process(target=open_server, args=(2719, 2, 0))
        p2.start()
        time.sleep(.2)

        machine1 = (LOCAL_IP, 2718)
        machine2 = (LOCAL_IP, 2719)
        machines = [machine1, machine2]
        task_id = "my_task"
        type = 'CPU'

        topology = [('right', 0, 1),
                    ('right', 1, 2),
                    ('right', 2, 3),
                    ('right', 3, 0)
                    ]

        allocation = allocate(allocation={machine1: 2, machine2: 2},
                                          unit_type=type)
        task = start_task(TaskTest4, task_id, topology,
                          unit_type=type,
                          codedependencies=[],
                          allocation=allocation,
                          args=(0, 3))

        result = task.get_result()
        self.assertEqual(result, [7, 7, 7, 7])

        close_servers([machine1, machine2])
        time.sleep(.2)

    def test_shared(self):
        time.sleep(2)

        topology = []
        x = rand(10)
        shared_data = {'x': x}
        allocation = allocate(cpu=2)

        task = start_task(TaskTestShared,
                          topology=topology,
                          allocation=allocation)
        task.get_result()


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(SynchandlerTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_userpref
from playdoh import *
from test import *


class UserPrefTest(unittest.TestCase):
    def test_1(self):
        self.assertEqual(type(USERPREF['connectiontrials']), int)
        prevport = USERPREF['port']
        USERPREF['port'] = 123456
        self.assertEqual(USERPREF['port'], 123456)
        USERPREF['port'] = prevport


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(UserPrefTest)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
