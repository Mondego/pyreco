__FILENAME__ = cleanup_examples

#
# Cleans up by deleting object files, executable, and _output directory.
# Use after run_examples to clean up stuff not needed on webpages.

import os,sys,glob
import shutil

examples_dir = os.path.abspath('./examples')
print "Will remove all _output, _plots, and build directories from ",examples_dir
ans = raw_input("Ok? ")
if ans.lower() not in ['y','yes']:
    print "Aborting."
    sys.exit()

os.chdir(examples_dir)
exdirlist = []
for (dirpath, subdirs, files) in os.walk('.'):
    currentdir = os.path.abspath(os.getcwd())
    os.chdir(os.path.abspath(dirpath))
    
    print 'In directory ',dirpath
    
    if os.path.isdir('_output'):
        shutil.rmtree('./_output')
    if os.path.isdir('_plots'):
        shutil.rmtree('./_plots')
    if os.path.isdir('build'):
        shutil.rmtree('./build')
        
    os.chdir(currentdir)


########NEW FILE########
__FILENAME__ = petsc_hello_world
#!/usr/bin/env python
# encoding: utf-8
r"""
This script is for testing petsc4py setup. If you
run this script with four processes as follows: ::

    $ mpiexec -n 4 python petsc_hello_world.py 

Then the expected output should look like the following: ::
        
    Hello World! From process 3 out of 4 process(es).
    Hello World! From process 1 out of 4 process(es).
    Hello World! From process 0 out of 4 process(es).
    Hello World! From process 2 out of 4 process(es).

"""
from petsc4py import PETSc

rank = PETSc.COMM_WORLD.getRank()
size = PETSc.COMM_WORLD.getSize()

print 'Hello World! From process {rank} out of {size} process(es).'.format(rank=rank,size=size)

########NEW FILE########
__FILENAME__ = .kslrun
account            = 'k47'
job_name           = 'petclaw_job'
wall_time          = '15:00'
 

########NEW FILE########
__FILENAME__ = advect
#!/usr/bin/env python
import sys

try:
    import numpy as np
    from petsc4py import PETSc
except:
    sys.path.append("/opt/share/ksl/petsc4py/dev-aug29/ppc450d/lib/python/")
    sys.path.append("/opt/share/ksl/numpy/dev-aug29/ppc450d/lib/python/")
    
    import numpy as np
    from petsc4py import PETSc

class PetCLAW:
    def advection1D(self, M, cfl, T):
        '''Script to solve 1D advection equation:
        q_t + q_x = 0
        Using first-order finite differences'''
        
        da = PETSc.DA().create([M])
        da.setUniformCoordinates() # solves the problem from 0 to 1
        da.view()

        xvec = da.getCoordinates()
        xvec.view()
        x = xvec.getArray()
        
        h = x[1]-x[0]
        k=cfl*h
        
        fg = da.createGlobalVector()
        fl = da.createLocalVector()
        
        N=int(round(T/k))
        
        # Initial condition:
        q = np.exp(-10*(x-0.5)**2)
        fg.setArray(q)
        da.globalToLocal(fg,fl)

        fg.view()
        
        for n in xrange(N+1):
            q = fl.getArray()
            q[1:]=q[1:]-cfl*(q[1:]-q[:-1])
            fl.setArray(q)
            da.localToGlobal(fl,fg)            
            fg.view()
            da.globalToLocal(fg,fl)

    def run(self):
        OptDB = PETSc.Options()
        M = OptDB.getInt('M', 16)
        cfl = OptDB.getReal('cfl',0.95)
        T = OptDB.getReal('T',2.)
        self.advection1D(M, cfl, T)
        print 'Done'
        return
          
if __name__ == '__main__':
    PetCLAW().run()
          

    
    

########NEW FILE########
__FILENAME__ = advect_annotated
#!/usr/bin/env python
import numpy as np
from petsc4py import PETSc

class PetCLAW:
    def advection1D(self, M, cfl, T):
        '''Script to solve 1D advection equation:
        q_t + q_x = 0
        Using first-order finite differences'''
        
        # PETSc DA object, which handles structured grids, here are
        # requesting M global points 
        da = PETSc.DA().create([M])
        print da.getSizes()

        ranges = da.getRanges()
        print ranges[0][1] - ranges[0][0]
        

        # this solves the problem on the domain [0 1] by default
        da.setUniformCoordinates() 

        # view commands dump to the screen
        da.view()

        # this gets the coordinate vector, this is akin to the
        # linspace(0,1,M) command 
        xvec = da.getCoordinates()
        xvec.view()
        # access the local data array within the globally distributed
        # vector 
        x = xvec.getArray()

        h = x[1]-x[0]
        k=cfl*h

        # global vector represents coordinated data with other
        # processors 
        fg = da.createGlobalVector()
        # local vector represents local data that is not shared
        fl = da.createLocalVector()

        # we will operate on the local vector, then coordinate with
        # other processors on the global vector 

        N=int(round(T/k))
        
        # Initial condition:
        q = np.exp(-10*(x-0.5)**2)
        # this is a little tricky.  the local vector contains ghost
        # points, which represents data that comes in from the global
        # vector when we are coordinating.  On the other hand, the
        # global vector only ever contains the data we own.  So when
        # we set initial conditions, we do it on the global vector,
        # then scatter to the local  
        fg.setArray(q)
        da.globalToLocal(fg,fl)

        # this should dump the properly set initial conditions
        fg.view()
        
        for n in xrange(N+1):
            # grab the working array out of the local vector
            # (including ghost points)
            q = fl.getArray()

            # operate on the local data
            q[1:]=q[1:]-cfl*(q[1:]-q[:-1])

            # restore the working array
            fl.setArray(q)

            # this is a local update, the local array in the local
            # vector is copied into the corresponding local array in
            # the global vector, ghost points are discarded 
            da.localToGlobal(fl,fg)
            
            fg.view()
            # this is a global update coordinated over all processes.
            # The local array in the global vector is copied into the
            # corresponding local array in the local vector.
            # In addition, the ghost values needed to operate locally
            # are sent over MPI to the correct positions in the local
            # array in the local vector.
            da.globalToLocal(fg,fl)

    def run(self):
        OptDB = PETSc.Options()
        M = OptDB.getInt('M', 16)
        cfl = OptDB.getReal('cfl',0.95)
        T = OptDB.getReal('T',2.)
        self.advection1D(M, cfl, T)
        print 'Done'
        return
          
if __name__ == '__main__':
    PetCLAW().run()
          

    
    

########NEW FILE########
__FILENAME__ = clawdata2pyclaw
"""
Script to convert Clawpack 4.6.x problem setup to PyClaw setup.
Automatically writes a basic PyClaw script with all the options
from the setrun.py in the current directory.  Also generates a 
Makefile and a wrapper for qinit.f.  Additional wrappers will be
needed for any other custom Fortan code, such as setaux, b4step, etc.

If you try this out, please raise issues in the PyClaw tracker for 
anything that doesn't work.
"""
import setrun

rundata=setrun.setrun()
clawdata=rundata.clawdata
probdata=rundata.probdata
ndim = clawdata.ndim

print "Writing run.py..."
outfile = 'pyclaw/run.py'
output=open(outfile,'w')

output.write("#!/usr/bin/env python\n")
output.write("# encoding: utf-8\n\n")


# write wrappers for Fortran functions
output.write("def fortran_qinit_wrapper(solver,state):\n")
output.write('    """\nWraps Fortran routine qinit.f"""\n')
output.write("    grid = state.grid\n")
output.write("    meqn = state.num_eqn\n")
output.write("    maux = state.num_aux\n")
output.write("    mbc = solver.num_ghost\n")
output.write("    q = state.q\n")
output.write("    aux = state.aux\n")
output.write("    t = state.t\n")
output.write("    mx = grid.num_cells[0]\n")
output.write("    dx = grid.delta[0]\n")
output.write("    xlower = grid.lower[0]\n")
if ndim>1:
    output.write("    my = grid.num_cells[1]\n")
    output.write("    dy = grid.delta[1]\n")
    output.write("    ylower = grid.lower[1]\n")
if ndim>2:
    output.write("    mz = grid.num_cells[2]\n")
    output.write("    dz = grid.delta[2]\n")
    output.write("    zlower = grid.lower[2]\n")

output.write("\n")
output.write("    import problem\n")
if ndim==1:
    output.write("    state.q = problem.qinit(mx,meqn,mbc,mx,xlower,dx,maux,aux)")
elif ndim==2:
    output.write("    state.q = problem.qinit(mx,meqn,mbc,mx,my,xlower,ylower,dx,dy,maux,aux)")
elif ndim==3:
    output.write("    state.q = problem.qinit(mx,meqn,mbc,mx,my,mz,xlower,ylower,zlower,dx,dy,dz,maux,aux)")
output.write("\n\n\n")


output.write("# Start main script")
output.write("import numpy as np\n")
output.write("import pyclaw\n\n")

output.write("solver = pyclaw.ClawSolver%sD()\n" % ndim)
output.write("import riemann\n")
output.write("solver.rp = riemann.<RIEMANN SOLVER NAME HERE>\n\n")

import pyclaw
exec("solver = pyclaw.ClawSolver%sD()" % ndim)
output.write("#Set all solver attributes\n")
solver_attrs = clawdata.__dict__
for key,value in solver_attrs.iteritems():
    if hasattr(solver,key):
        output.write("solver.%s = %s\n" % (key,value))
output.write("\n")

output.write("""\n\
# Choice of BCs at lower and upper:\n\
#   0 => user specified (must modify bcN.f to use this option)\n\
#   1 => extrapolation (non-reflecting outflow)\n\
#   2 => periodic (must specify this at both boundaries)\n\
#   3 => solid wall for systems where q(2) is normal velocity\n""")

output.write("solver.bc_lower[0] = %s\n" % clawdata.bc_xlower)
output.write("solver.bc_upper[0] = %s\n" % clawdata.bc_xupper)
if ndim>1:
    output.write("solver.bc_lower[1] = %s\n" % clawdata.bc_ylower)
    output.write("solver.bc_upper[1] = %s\n" % clawdata.bc_yupper)
if ndim>2:
    output.write("solver.bc_lower[2] = %s\n" % clawdata.bc_zlower)
    output.write("solver.bc_upper[2] = %s\n" % clawdata.bc_zupper)
output.write("\n")

output.write("solver.max_steps = %s\n" % clawdata.steps_max)
output.write("solver.num_waves = %s\n" % clawdata.mwaves)
output.write("solver.limiters = %s\n" % clawdata.limiter)
output.write("\n")

output.write("""
# Source terms splitting:\n\
#   src_split == 0  => no source term (src routine never called)\n\
#   src_split == 1  => Godunov (1st order) splitting used, \n\
#   src_split == 2  => Strang (2nd order) splitting used,  not recommended.\n""")
output.write("solver.source_split = %s\n" % clawdata.src_split)
output.write("\n")

output.write("# Initialize domain\n")
output.write("x = pyclaw.Dimension(%s,%s,%s)\n" % (clawdata.xlower,clawdata.xupper,clawdata.mx))
if ndim>1:
    output.write("y = pyclaw.Dimension(%s,%s,%s)\n" % (clawdata.ylower,clawdata.yupper,clawdata.my))
if ndim>2:
    output.write("z = pyclaw.Dimension(%s,%s,%s)\n" % (clawdata.zlower,clawdata.zupper,clawdata.mz))

output.write("domain = pyclaw.Domain")
if ndim == 1:
    output.write("(x)")
elif ndim == 2:
    output.write("(x,y)")
elif ndim == 3:
    output.write("(x,y,z)")
output.write("\n\n")

output.write("# Initialize state\n")
output.write("num_eqn = %s\n" % clawdata.meqn)
output.write("num_aux = %s\n" % clawdata.maux)
output.write("state = pyclaw.State(domain,num_eqn,num_aux)\n")
output.write("state.capa_index = %s" % clawdata.mcapa)

output.write("# Set problem data\n")
for param,value in probdata.iteritems():
    output.write("state.problem_data['%s']=%s\n" % (param,value))

output.write("\n")

output.write("# Initialize controller and solution\n")
output.write("claw = pyclaw.Controller()\n")
output.write("claw.solution = pyclaw.Solution(state,domain)\n")
output.write("claw.solution.t = %s\n" % clawdata.t0)
output.write("claw.solver = solver\n")
output.write("claw.tfinal = %s\n" % clawdata.output_tfinal)
output.write("claw.output_style = %s\n" % clawdata.output_style)
output.write("claw.num_output_times = %s\n" % clawdata.output_ntimes)
output.write("claw.verbosity = %s\n" % clawdata.verbosity)

output.write("\nstatus = claw.run()\n\n\n")

output.close()


# Write Makefile
print "Writing Makefile..."
makefile = 'pyclaw/Makefile' # To avoid stomping existing Makefile
outmake=open(makefile,'w')

outmake.write("all:\n\tmake classic1.so\n\tmake problem.so\n\n")

outmake.write("# Put all problem-specific Fortran files here:\n")
outmake.write("problem.so: qinit.f setaux.f src.f mapc2p.f\n\t")
outmake.write(r"""$(F2PY) -m problem -c $^""")
outmake.write("\n\n")
outmake.write(r"""include $(PYCLAW)/Makefile.common""")
outmake.write("\n\n")
outmake.close()

print """Don't forget to do the following manually:\n\
         1. interleave your Fortran code \n\
         2. Fill in the Riemann solver in run.py\n\
         3. Add 'cf2py intent(out) q' to your qinit.f\n\
         3. write any code needed to replicate setprob.f functionality."""

########NEW FILE########
__FILENAME__ = dmpfor_test
from petsc4py import PETSc
import numpy as np
import DMPFOR



global_nx =3
global_ny =2
dof=4

da = PETSc.DA().create(dim=2,
dof=dof,
sizes=[global_nx, global_ny], 
#periodic_type = PETSc.DA.PeriodicType.GHOSTED_XYZ,
#stencil_type=self.STENCIL,
#stencil_width=2,
comm=PETSc.COMM_WORLD)


gVec = da.createGlobalVector()
lVec = da.createLocalVector()




ranges = da.getRanges()

nx_start = ranges[0][0]
nx_end = ranges[0][1]
ny_start = ranges[1][0]
ny_end = ranges[1][1]

nx = nx_end - nx_start
ny = ny_end - ny_start


q = np.empty((dof, nx, ny), order='F')

for i in range(0,nx):
    for j in range(0,ny):
        for k in range(0,dof):
            q[k,i,j] = k+10*i+100*j

gVec.array = q

q = gVec.array.reshape((dof, nx, ny), order='F')

print "da array from python"
print q


print "da array from fortran"
DMPFOR.dmpfor(q,dof,nx,ny)


print "da array from python after rolling axises using rollaxis"
rolled_q_1 = np.rollaxis(q,0,3)
rolled_q_1 = np.reshape(rolled_q_1,(nx,ny,dof),order='F')
print rolled_q_1
print "da array from fortran after rolling axises using rollaxis"
DMPFOR.dmpfor(rolled_q_1,nx,ny,dof)


print "da array from python after rolling axises using element by element copy"
rolled_q_2 = np.empty((nx,ny,dof),order='F')
for i in range(0,nx):
    for j in range(0,ny):
        for k in range(0,dof):
            rolled_q_2[i,j,k] = q[k,i,j]
print rolled_q_2
print "da array from fortran after rolling axises using element by element copy"
DMPFOR.dmpfor(rolled_q_2,nx,ny,dof)








########NEW FILE########
__FILENAME__ = driver
#!/usr/bin/env python
from petsc4py import PETSc

class PetCLAW:
  def advection1D(self, N):
    '''David: If you put in the linear algebra that you need (comments), I will move it to code'''
    da = PETSc.DA().create([N])
    da.view()
    f = da.createGlobalVector()
    f.view()
    a = f.getArray()
    for i in range(f.getSize()):
      a[i] = i*i
    f.view()
    return

  def run(self):
    self.advection1D(10)
    print 'Done'
    return

if __name__ == '__main__':
  PetCLAW().run()

########NEW FILE########
__FILENAME__ = fPyWrapperExample
from numpy import *
from FRS import vec_rp
q = random.random((2,800))
aux = random.random((2,800))
waves, s = vec_rp(2,q[:,0:799],q[:,1:800],aux[:,0:799],aux[:,1:800])
print waves
print s




########NEW FILE########
__FILENAME__ = RiemannSolver
from numpy import random, empty,zeros
#from numpy import *
from FRS import vec_rp, pw_rp
from time import clock
from pylab import plot,  figure




class RiemannSolver:
  

    def __init__(self, timeSteps, mwaves, mx, meqn, maux, q = None, aux = None):
       
        self.timeSteps = timeSteps
        self.mwaves = mwaves
        self.mx = mx
        self.meqn = meqn
        self.maux = maux
        if q is not None:
            self.q = q
        if aux is not None:
            self.aux = aux

    def solveVectorized(self, timer = None):
       
        if timer is not None:
            print "Solving... vectorized"
            start = clock()

        for counter in range(self.timeSteps):
            waves, s = vec_rp(self.mwaves,self.q[:,0:self.mx-1],self.q[:,1:self.mx],self.aux[:,0:self.mx-1],self.aux[:,1:self.mx])

        if timer is not None:
            end = clock()
            self.elapsedTime = end-start
            print "elapsed time: ", self.elapsedTime, " seconds"

        return waves, s




    def solvePointwize(self, timer = None):

        timeSteps, mwaves, mx, meqn, maux, q , aux = self.timeSteps, self.mwaves, self.mx, self.meqn, self.maux, self.q , self.aux
        waves = zeros((meqn, mwaves, mx))
        s = zeros((mwaves, mx))
        if timer is not None:
            print "Solving... point-wize"
            start = clock()

        for counter in range(timeSteps):
            for i in range(1,mx-1):  #from 1 to mx-1 unlike fortran (from 1 to mx-2 means including mx-2)
                waves[:,:,i], s[:,i] = pw_rp(mwaves,q[:,i],q[:,i+1],aux[:,i],aux[:,i+1]) # instead of pw_rp(mwaves,q[:,i-1],q[:,i],aux[:,i-1],aux[:,i]) due to the
                                                                                         # differences in indexing among fortran and python

        if timer is not None:
            end = clock()
            self.elapsedTime = end-start
            print "elapsed time: ", self.elapsedTime, " seconds"

        return waves, s
        

        

if __name__ == "__main__":
    rs = RiemannSolver( 1, 2, 2**10, 2, 2)
    
    rs.q = random.random((rs.meqn,rs.mx))   
    rs.aux = random.random((rs.maux,rs.mx))

    
    waves1, s1  = rs.solveVectorized(timer = True)

    
    waves2, s2  = rs.solvePointwize(timer = True)
   

########NEW FILE########
__FILENAME__ = riemannSolverAssertion
import RiemannSolver
from RiemannSolver import *
from numpy import load, absolute


tolerance = 0.00005
print "This script asserts the results for input read from data files q.npy and aux.npy with tolerance =", tolerance



rs = RiemannSolver( 10, 2, 2**15, 2, 2)
    
rs.q = load("q.npy")
rs.aux = load("aux.npy")

wavesRead = load("waves.npy")
sRead = load("s.npy")

waves1, s1  = rs.solveVectorized(timer = True)
#waves2, s2  = rs.solvePointwize(timer = True)

assert (absolute(wavesRead - waves1)< tolerance).all()
assert (absolute(sRead -s1)< tolerance).all()


########NEW FILE########
__FILENAME__ = riemannSolverDemo

import RiemannSolver
from RiemannSolver import *
from pylab import plot,  figure, suptitle

rs = RiemannSolver(timeSteps =1, mwaves = 2, mx = 800, meqn = 2, maux = 2)
    
rs.q = random.random((rs.meqn,rs.mx))
rs.aux = random.random((rs.maux,rs.mx))
waves1, s1  = rs.solveVectorized(timer = True)
waves2, s2  = rs.solvePointwize(timer = True)



figure(1)
waveIndex = 0
componentIndex = 0

suptitle("Figure 1: shows the curve of wave number {0}, for the component number {1}".format(waveIndex+1, componentIndex+2))	
plot(waves1[componentIndex,waveIndex,:], "g")

########NEW FILE########
__FILENAME__ = riemannSolverSerialTimer
import RiemannSolver
from RiemannSolver import *
from numpy import empty
from pylab import plot,  figure, suptitle



print "Testing for different number of time steps ..."
noOfTestSamples = 10
max_mx = 101 
max_timeSteps = 101 

timesStepsValues = empty((noOfTestSamples ))
timeResultsVectorized =empty((noOfTestSamples ))
timeResultsPointwise =empty((noOfTestSamples ))
# error when max_mx is devisible by noOfTestSamples. size of arrays should be noOfTestSamples-1, use j to decide what to plot






rs = RiemannSolver(timeSteps = max_timeSteps/noOfTestSamples, mwaves = 2, mx=max_mx , meqn = 2, maux = 2)  


rs.q = random.random((rs.meqn,rs.mx))
rs.aux = random.random((rs.maux,rs.mx))

j = 0
for i in range(max_timeSteps/noOfTestSamples, max_timeSteps, max_timeSteps/noOfTestSamples):
	timesStepsValues[j] = i
	rs.timeSteps = i
	print
	print "Iteration",j+1,"of", noOfTestSamples
	print "Number of time steps is", i
	
	waves1, s1  = rs.solveVectorized(timer = True)
	timeResultsVectorized[j] = rs.elapsedTime
	
	
	
	waves2, s2  = rs.solvePointwize(timer = True)
	timeResultsPointwise[j] = rs.elapsedTime
	
	
	j= j+1


figure(1)	
suptitle("Figure 1 shows the the execution time for different timeStep values\n for the vectorized solver in green and pointwize solver in blue")	

plot(timesStepsValues, timeResultsVectorized, "go-")

#figure(2)
#suptitle( "Figure 2 shows the the execution time for different timeStep values\n for the pointwize solver, mx = {0}".format(max_mx))	
plot(timesStepsValues, timeResultsPointwise, "bo-")
	
	




print "Testing for different sizes of mx ..."
noOfTestSamples = 10
max_mx = 101 
max_timeSteps = 101 

mxValues = empty((noOfTestSamples ))
timeResultsVectorized =empty((noOfTestSamples ))
timeResultsPointwise =empty((noOfTestSamples ))
# error when max_mx is devisible by noOfTestSamples. size of arrays should be noOfTestSamples-1, use j to decide what to plot






rs = RiemannSolver(timeSteps = max_timeSteps, mwaves = 2, mx=max_mx/noOfTestSamples , meqn = 2, maux = 2)  


rs.q = random.random((rs.meqn,rs.mx))
rs.aux = random.random((rs.maux,rs.mx))





 




j = 0
for i in range(max_mx/noOfTestSamples, max_mx,max_mx/noOfTestSamples):
	mxValues[j] = i
	rs.mx = i
	print
	print "Iteration",j+1,"of", noOfTestSamples
	print "mx is", i
	
	rs.q = random.random((rs.meqn,rs.mx))
	rs.aux = random.random((rs.maux,rs.mx))
	
	waves1, s1  = rs.solveVectorized(timer = True)
	timeResultsVectorized[j] = rs.elapsedTime
	
	
	
	waves2, s2  = rs.solvePointwize(timer = True)
	timeResultsPointwise[j] = rs.elapsedTime
	
	
	j= j+1
	
figure(2)
suptitle("Figure 2 shows the the execution time for different mx values\n for the vectorized solver in green and pointwize solver in blue")	
plot(mxValues, timeResultsVectorized, "go-")

#figure(4)
#suptitle("Figure 4 shows the the execution time for different mx values\n for the pointwize solver, timeSteps = {0}".format(max_timeSteps))	
plot(mxValues, timeResultsPointwise, "bo-")





########NEW FILE########
__FILENAME__ = setplot

""" 
Set up the plot figures, axes, and items to be done for each frame.

This module is imported by the plotting routines and then the
function setplot is called to set the plot parameters.
    
""" 

#--------------------------
def setplot(plotdata):
#--------------------------
    
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    
    """ 


    from visclaw import colormaps
    from matplotlib import cm

    plotdata.clearfigures()  # clear any old figures,axes,items data
    

    # Figure for pressure
    # -------------------

    plotfigure = plotdata.new_plotfigure(name='Density', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = 'auto'
    plotaxes.title = 'Density'
    plotaxes.scaled = True      # so aspect ratio is 1
    plotaxes.afteraxes = label_axes

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_schlieren')
    #plotitem.pcolor_cmin = 0.5
    #plotitem.pcolor_cmax=3.5
    plotitem.plot_var = 0
    plotitem.add_colorbar = False
    plotitem.show = True       # show on plot?
    

    plotfigure = plotdata.new_plotfigure(name='Tracer', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = 'auto'
    plotaxes.title = 'Tracer'
    plotaxes.scaled = True      # so aspect ratio is 1
    plotaxes.afteraxes = label_axes

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.pcolor_cmin = 0.
    plotitem.pcolor_cmax=1.0
    plotitem.plot_var = 4
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = False
    plotitem.show = True       # show on plot?
    

    plotfigure = plotdata.new_plotfigure(name='Energy', figno=2)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = 'auto'
    plotaxes.title = 'Energy'
    plotaxes.scaled = True      # so aspect ratio is 1
    plotaxes.afteraxes = label_axes

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.pcolor_cmin = 2.
    plotitem.pcolor_cmax=18.0
    plotitem.plot_var = 3
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = False
    plotitem.show = True       # show on plot?
    



    # Parameters used only when creating html and/or latex hardcopy
    # e.g., via visclaw.frametools.printframes:

    plotdata.printfigs = True                # print figures
    plotdata.print_format = 'png'            # file format
    plotdata.print_framenos = 'all'          # list of frames to print
    plotdata.print_fignos = 'all'            # list of figures to print
    plotdata.html = True                     # create html files of plots?
    plotdata.html_homelink = '../README.html'   # pointer for top of index
    plotdata.latex = True                    # create latex file of plots?
    plotdata.latex_figsperline = 2           # layout of plots
    plotdata.latex_framesperline = 1         # layout of plots
    plotdata.latex_makepdf = False           # also run pdflatex?

    return plotdata

def label_axes(current_data):
    import matplotlib.pyplot as plt
    plt.xlabel('z')
    plt.ylabel('r')
    #plt.draw()
    

########NEW FILE########
__FILENAME__ = shockbubble
#!/usr/bin/env python
# encoding: utf-8

import numpy as np
from scipy import integrate

gamma = 1.4
gamma1 = gamma - 1.
x0=0.5; y0=0.; r0=0.2
xshock = 0.2
pinf=5.

def inrad(y,x):
    return (np.sqrt((x-x0)**2+(y-y0)**2)<r0)

def ycirc(x,ymin,ymax):
    if r0**2>((x-x0)**2):
        return max(min(y0 + np.sqrt(r0**2-(x-x0)**2),ymax) - ymin,0.)
    else:
        return 0

def qinit(state,rhoin=0.1):
    r"""
    Initialize data with a shock at x=xshock and a low-density bubble (of density rhoin)
    centered at (x0,y0) with radius r0.
    """
    rhoout = 1.
    pout   = 1.
    pin    = 1.

    rinf = (gamma1 + pinf*(gamma+1.))/ ((gamma+1.) + gamma1*pinf)
    vinf = 1./np.sqrt(gamma) * (pinf - 1.) / np.sqrt(0.5*((gamma+1.)/gamma) * pinf+0.5*gamma1/gamma)
    einf = 0.5*rinf*vinf**2 + pinf/gamma1
    
    x =state.grid.x.center
    y =state.grid.y.center
    Y,X = np.meshgrid(y,x)
    r = np.sqrt((X-x0)**2 + (Y-y0)**2)

    #First set the values for the cells that don't intersect the bubble boundary
    state.q[0,:,:] = rinf*(X<xshock) + rhoin*(r<=r0) + rhoout*(r>r0)
    state.q[1,:,:] = rinf*vinf*(X<xshock)
    state.q[2,:,:] = 0.
    state.q[3,:,:] = einf*(X<xshock) + (pin*(r<=r0) + pout*(r>r0))/gamma1
    state.q[4,:,:] = 1.*(r<=r0)

    #Now average for the cells on the edge of the bubble
    d2 = np.linalg.norm(state.grid.d)/2.
    dx = state.grid.d[0]
    dy = state.grid.d[1]
    dx2 = state.grid.d[0]/2.
    dy2 = state.grid.d[1]/2.
    for i in xrange(state.q.shape[1]):
        for j in xrange(state.q.shape[2]):
            ydown = y[j]-dy2
            yup   = y[j]+dy2
            if abs(r[i,j]-r0)<d2:
                infrac,abserr = integrate.quad(ycirc,x[i]-dx2,x[i]+dx2,args=(ydown,yup),epsabs=1.e-8,epsrel=1.e-5)
                infrac=infrac/(dx*dy)
                state.q[0,i,j] = rhoin*infrac + rhoout*(1.-infrac)
                state.q[3,i,j] = (pin*infrac + pout*(1.-infrac))/gamma1
                state.q[4,i,j] = 1.*infrac


def auxinit(state):
    """
    aux[0,i,j] = y-coordinate of cell center for cylindrical source terms
    """
    y=state.grid.y.center
    for j,ycoord in enumerate(y):
        state.aux[0,:,j] = ycoord


def shockbc(state,dim,t,qbc,mbc):
    """
    Incoming shock at left boundary.
    """
    if dim.nstart == 0:

        rinf = (gamma1 + pinf*(gamma+1.))/ ((gamma+1.) + gamma1*pinf)
        vinf = 1./np.sqrt(gamma) * (pinf - 1.) / np.sqrt(0.5*((gamma+1.)/gamma) * pinf+0.5*gamma1/gamma)
        einf = 0.5*rinf*vinf**2 + pinf/gamma1

        for i in xrange(mbc):
            qbc[0,i,...] = rinf
            qbc[1,i,...] = rinf*vinf
            qbc[2,i,...] = 0.
            qbc[3,i,...] = einf
            qbc[4,i,...] = 0.

def dq_Euler_radial(solver,state,dt):
    """
    Geometric source terms for Euler equations with radial symmetry.
    Integrated using a 2-stage, 2nd-order Runge-Kutta method.
    This is a SharpClaw-style source term routine.
    """
    
    ndim = 2

    q   = state.q
    aux = state.aux

    rad = aux[0,:,:]

    rho = q[0,:,:]
    u   = q[1,:,:]/rho
    v   = q[2,:,:]/rho
    press  = gamma1 * (q[3,:,:] - 0.5*rho*(u**2 + v**2))

    dq = np.empty(q.shape)

    dq[0,:,:] = -dt*(ndim-1)/rad * q[2,:,:]
    dq[1,:,:] = -dt*(ndim-1)/rad * rho*u*v
    dq[2,:,:] = -dt*(ndim-1)/rad * rho*v*v
    dq[3,:,:] = -dt*(ndim-1)/rad * v * (q[3,:,:] + press)
    dq[4,:,:] = 0

    return dq

def step_Euler_radial(solver,state,dt):
    """
    Geometric source terms for Euler equations with radial symmetry.
    Integrated using a 2-stage, 2nd-order Runge-Kutta method.
    This is a Clawpack-style source term routine.
    """
    
    dt2 = dt/2.
    ndim = 2

    aux=state.aux
    q = state.q

    rad = aux[0,:,:]

    rho = q[0,:,:]
    u   = q[1,:,:]/rho
    v   = q[2,:,:]/rho
    press  = gamma1 * (q[3,:,:] - 0.5*rho*(u**2 + v**2))

    qstar = np.empty(q.shape)

    qstar[0,:,:] = q[0,:,:] - dt2*(ndim-1)/rad * q[2,:,:]
    qstar[1,:,:] = q[1,:,:] - dt2*(ndim-1)/rad * rho*u*v
    qstar[2,:,:] = q[2,:,:] - dt2*(ndim-1)/rad * rho*v*v
    qstar[3,:,:] = q[3,:,:] - dt2*(ndim-1)/rad * v * (q[3,:,:] + press)

    rho = qstar[0,:,:]
    u   = qstar[1,:,:]/rho
    v   = qstar[2,:,:]/rho
    press  = gamma1 * (qstar[3,:,:] - 0.5*rho*(u**2 + v**2))

    q[0,:,:] = q[0,:,:] - dt*(ndim-1)/rad * qstar[2,:,:]
    q[1,:,:] = q[1,:,:] - dt*(ndim-1)/rad * rho*u*v
    q[2,:,:] = q[2,:,:] - dt*(ndim-1)/rad * rho*v*v
    q[3,:,:] = q[3,:,:] - dt*(ndim-1)/rad * v * (qstar[3,:,:] + press)


def shockbubble(use_petsc=False,iplot=False,htmlplot=False,outdir='./_output',solver_type='classic'):
    """
    Solve the Euler equations of compressible fluid dynamics.
    This example involves a bubble of dense gas that is impacted by a shock.
    """

    if use_petsc:
        import petclaw as pyclaw
    else:
        import pyclaw

    if solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver2D()
        solver.dq_src=dq_Euler_radial
    else:
        solver = pyclaw.ClawSolver2D()
        solver.dim_split = 0
        solver.order_trans = 2
        solver.limiters = [4,4,4,4,2]
        solver.step_src=step_Euler_radial

    solver.mwaves = 5
    solver.bc_lower[0]=pyclaw.BC.custom
    solver.bc_upper[0]=pyclaw.BC.outflow
    solver.bc_lower[1]=pyclaw.BC.reflecting
    solver.bc_upper[1]=pyclaw.BC.outflow

    #Aux variable in ghost cells doesn't matter
    solver.aux_bc_lower[0]=pyclaw.BC.outflow
    solver.aux_bc_upper[0]=pyclaw.BC.outflow
    solver.aux_bc_lower[1]=pyclaw.BC.outflow
    solver.aux_bc_upper[1]=pyclaw.BC.outflow

    # Initialize grid
    mx=320; my=80
    x = pyclaw.Dimension('x',0.0,2.0,mx)
    y = pyclaw.Dimension('y',0.0,0.5,my)
    grid = pyclaw.Grid([x,y])
    meqn = 5
    maux=8
    state = pyclaw.State(grid,meqn,maux)

    state.aux_global['gamma']= gamma
    state.aux_global['gamma1']= gamma1

    qinit(state)
    auxinit(state)

    solver.user_bc_lower=shockbc

    claw = pyclaw.Controller()
    claw.tfinal = 0.75
    claw.solution = pyclaw.Solution(state)
    claw.solver = solver
    claw.nout = 10
    claw.outdir = outdir

    # Solve
    status = claw.run()

    if htmlplot:  pyclaw.plot.html_plot(outdir=outdir)
    if iplot:     pyclaw.plot.interactive_plot(outdir=outdir)

    return claw.solution.q

if __name__=="__main__":
    from pyclaw.util import run_app_from_main
    output = run_app_from_main(shockbubble)

########NEW FILE########
__FILENAME__ = test_mpi4py
from mpi4py import MPI  
comm = MPI.COMM_WORLD 
size = comm.Get_size()
rank = comm.Get_rank()
x = rank
print 'x before', x
max_x =comm.reduce( sendobj=x, op=MPI.MAX,  root=0)
x = comm.bcast(max_x, root=0)
print 'x after', x


########NEW FILE########
__FILENAME__ = test_rescale
#!/usr/bin/env python
import sys

try:
    import numpy
except:
    sys.path.append("/opt/share/ksl/numpy/dev-aug29/ppc450d/lib/python/")
    import numpy

import ksl_rescale 

a=numpy.array([[1,2],[3,4]],dtype=float,order='FORTRAN')
print a
print "rescaling by 2!"
ksl_rescale.rescale(a,2.0)
print a

########NEW FILE########
__FILENAME__ = acoustics_1d
#!/usr/bin/env python
# encoding: utf-8

r"""
One-dimensional acoustics
=========================

Solve the (linear) acoustics equations:

.. math:: 
    p_t + K u_x & = 0 \\ 
    u_t + p_x / \rho & = 0.

Here p is the pressure, u is the velocity, K is the bulk modulus,
and :math:`\rho` is the density.

The initial condition is a Gaussian and the boundary conditions are periodic.
The final solution is identical to the initial data because both waves have
crossed the domain exactly once.
"""
    
def setup(use_petsc=False,kernel_language='Fortran',solver_type='classic',outdir='./_output',weno_order=5, 
        time_integrator='SSP104', disable_output=False):
    """
    This example solves the 1-dimensional acoustics equations in a homogeneous
    medium.
    """
    from numpy import sqrt, exp, cos
    from clawpack import riemann

    #=================================================================
    # Import the appropriate classes, depending on the options passed
    #=================================================================
    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    #========================================================================
    # Instantiate the solver and define the system of equations to be solved
    #========================================================================
    if kernel_language == 'Fortran':
        riemann_solver = riemann.acoustics_1D
    elif kernel_language=='Python': 
        riemann_solver = riemann.acoustics_1D_py.acoustics_1D

    if solver_type=='classic':
        solver = pyclaw.ClawSolver1D(riemann_solver)
        solver.limiters = pyclaw.limiters.tvd.MC
    elif solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver1D(riemann_solver)
        solver.weno_order=weno_order
        solver.time_integrator=time_integrator
    else: raise Exception('Unrecognized value of solver_type.')

    solver.kernel_language=kernel_language

    #========================================================================
    # Instantiate the domain and set the boundary conditions
    #========================================================================
    x = pyclaw.Dimension('x',0.0,1.0,100)
    domain = pyclaw.Domain(x)
    num_eqn = 2
    state = pyclaw.State(domain,num_eqn)

    solver.bc_lower[0] = pyclaw.BC.periodic
    solver.bc_upper[0] = pyclaw.BC.periodic

    #========================================================================
    # Set problem-specific variables
    #========================================================================
    rho = 1.0
    bulk = 1.0

    state.problem_data['rho']=rho
    state.problem_data['bulk']=bulk
    state.problem_data['zz']=sqrt(rho*bulk) # Impedance
    state.problem_data['cc']=sqrt(bulk/rho) # Sound speed
 

    #========================================================================
    # Set the initial condition
    #========================================================================
    xc=domain.grid.x.centers
    beta=100; gamma=0; x0=0.75
    state.q[0,:] = exp(-beta * (xc-x0)**2) * cos(gamma * (xc - x0))
    state.q[1,:] = 0.

    solver.dt_initial=domain.grid.delta[0]/state.problem_data['cc']*0.1

    #========================================================================
    # Set up the controller object
    #========================================================================
    claw = pyclaw.Controller()
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir
    claw.keep_copy = True
    claw.num_output_times = 5
    if disable_output:
        claw.output_format = None
    claw.tfinal = 1.0
    claw.setplot = setplot

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for pressure
    plotfigure = plotdata.new_plotfigure(name='Pressure', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.axescmd = 'subplot(211)'
    plotaxes.ylimits = [-.2,1.0]
    plotaxes.title = 'Pressure'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    plotitem.kwargs = {'linewidth':2,'markersize':5}
    
    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.axescmd = 'subplot(212)'
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = [-.5,1.1]
    plotaxes.title = 'Velocity'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 1
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    plotitem.kwargs = {'linewidth':3,'markersize':5}
    
    return plotdata

def run_and_plot(**kwargs):
    claw = setup(kwargs)
    claw.run()
    from clawpack.pyclaw import plot
    plot.interactive_plot(setplot=setplot)

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = test_acoustics
def test_1d_acoustics():
    """test_1d_acoustics

    tests against known classic, sharpclaw, and high-order weno results """

    import acoustics_1d

    def verify_expected(expected):
        """ binds the expected value to the acoustics_verify methods """
        def acoustics_verify(claw):
            from clawpack.pyclaw.util import check_diff
            import numpy as np

            # tests are done across the entire domain of q normally
            q0=claw.frames[0].state.get_q_global()
            qfinal=claw.frames[claw.num_output_times].state.get_q_global()

            # and q_global is only returned on process 0
            if q0 != None and qfinal != None:
                q0 = q0.reshape([-1])
                qfinal = qfinal.reshape([-1])
                dx=claw.solution.domain.grid.delta[0]
                test = dx*np.sum(np.abs(qfinal-q0))
                return check_diff(expected, test, abstol=1e-4)
            else:
                return
        return acoustics_verify

    from clawpack.pyclaw.util import gen_variants

    classic_tests = gen_variants(acoustics_1d.setup, verify_expected(0.00104856594174),
                                 kernel_languages=('Python','Fortran'), solver_type='classic', disable_output=True)

    sharp_tests_rk   = gen_variants(acoustics_1d.setup, verify_expected(0.000298879563857),
                                 kernel_languages=('Python','Fortran'), solver_type='sharpclaw',
                                 time_integrator='SSP104', disable_output=True)

    sharp_tests_lmm   = gen_variants(acoustics_1d.setup, verify_expected(0.00227996627104),
                                 kernel_languages=('Python','Fortran'), solver_type='sharpclaw',
                                 time_integrator='SSPMS32', disable_output=True)

    weno_tests    = gen_variants(acoustics_1d.setup, verify_expected(0.000153070447918),
                                 kernel_languages=('Fortran',), solver_type='sharpclaw',
                                 time_integrator='SSP104', weno_order=17, disable_output=True)

    from itertools import chain
    for test in chain(classic_tests, sharp_tests_rk, sharp_tests_lmm, weno_tests):
        yield test

########NEW FILE########
__FILENAME__ = acoustics_2d
#!/usr/bin/env python
# encoding: utf-8
r"""
Two-dimensional acoustics
=========================

Solve the (linear) acoustics equations:

.. math:: 
    p_t + K (u_x + v_y) & = 0 \\ 
    u_t + p_x / \rho & = 0 \\
    v_t + p_y / \rho & = 0.

Here p is the pressure, (u,v) is the velocity, K is the bulk modulus,
and :math:`\rho` is the density.
"""
 
import numpy as np

def setup(kernel_language='Fortran',use_petsc=False,outdir='./_output',solver_type='classic',
        time_integrator='SSP104', disable_output=False):
    """
    Example python script for solving the 2d acoustics equations.
    """
    from clawpack import riemann
    if use_petsc:
        from clawpack import petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type=='classic':
        solver=pyclaw.ClawSolver2D(riemann.acoustics_2D)
        solver.dimensional_split=True
        solver.cfl_max = 0.5
        solver.cfl_desired = 0.45
    elif solver_type=='sharpclaw':
        solver=pyclaw.SharpClawSolver2D(riemann.acoustics_2D)
        solver.time_integrator=time_integrator
        if solver.time_integrator=='SSP104':
            solver.cfl_max = 0.5
            solver.cfl_desired = 0.45
        elif solver.time_integrator=='SSPMS32':
            solver.cfl_max = 0.2
            solver.cfl_desired = 0.16
        else:
            raise Exception('CFL desired and CFL max have not been provided for the particular time integrator.')

    
    solver.limiters = pyclaw.limiters.tvd.MC

    solver.bc_lower[0]=pyclaw.BC.extrap
    solver.bc_upper[0]=pyclaw.BC.extrap
    solver.bc_lower[1]=pyclaw.BC.extrap
    solver.bc_upper[1]=pyclaw.BC.extrap

    # Initialize domain
    mx=100; my=100
    x = pyclaw.Dimension('x',-1.0,1.0,mx)
    y = pyclaw.Dimension('y',-1.0,1.0,my)
    domain = pyclaw.Domain([x,y])

    num_eqn = 3
    state = pyclaw.State(domain,num_eqn)

    rho = 1.0
    bulk = 4.0
    cc = np.sqrt(bulk/rho)
    zz = rho*cc
    state.problem_data['rho']= rho
    state.problem_data['bulk']=bulk
    state.problem_data['zz']= zz
    state.problem_data['cc']=cc

    qinit(state)

    claw = pyclaw.Controller()
    claw.keep_copy = True
    if disable_output:
        claw.output_format = None
    claw.solution = pyclaw.Solution(state,domain)
    solver.dt_initial=np.min(domain.grid.delta)/state.problem_data['cc']*solver.cfl_desired

    claw.solver = solver
    claw.outdir = outdir

    num_output_times = 10
    
    claw.num_output_times = num_output_times

    claw.tfinal = 0.12

    claw.setplot = setplot

    return claw

def qinit(state,width=0.2):
    
    grid = state.grid
    x =grid.x.centers
    y =grid.y.centers
    Y,X = np.meshgrid(y,x)
    r = np.sqrt(X**2 + Y**2)

    state.q[0,:,:] = (np.abs(r-0.5)<=width)*(1.+np.cos(np.pi*(r-0.5)/width))
    state.q[1,:,:] = 0.
    state.q[2,:,:] = 0.



#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 

    import os
    if os.path.exists('./1drad/_output'):
        qref_dir = os.path.abspath('./1drad/_output')
    else:
        qref_dir = None
        print "Directory ./1drad/_output not found"

    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data
    
    # Figure for pressure
    plotfigure = plotdata.new_plotfigure(name='Pressure', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Pressure'
    plotaxes.scaled = True      # so aspect ratio is 1

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 0
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True

    # Figure for scatter plot
    plotfigure = plotdata.new_plotfigure(name='scatter', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Scatter plot'

    # Set up for item on these axes: scatter of 2d data
    plotitem = plotaxes.new_plotitem(plot_type='1d_from_2d_data')
    
    def p_vs_r(current_data):
        # Return radius of each patch cell and p value in the cell
        from pylab import sqrt
        x = current_data.x
        y = current_data.y
        r = sqrt(x**2 + y**2)
        q = current_data.q
        p = q[0,:,:]
        return r,p

    plotitem.map_2d_to_1d = p_vs_r
    plotitem.plot_var = 0
    plotitem.plotstyle = 'ob'
    
    return plotdata

    
if __name__=="__main__":
    import sys
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = test_2d_acoustics
def test_2d_acoustics():
    """test_2d_acoustics"""

    def verify_data(data_filename):
        def verify(claw):
            """ verifies 2d homogeneous acoustics from a previously verified run """
            import os
            import numpy as np
            from clawpack.pyclaw.util import check_diff


            #grabs parallel results to process 0, None to other processes
            test_q=claw.solution.state.get_q_global()

            if test_q is not None:
                test_pressure = test_q[0,:,:]
                thisdir = os.path.dirname(__file__)
                expected_pressure = np.loadtxt(os.path.join(thisdir,data_filename))
                return check_diff(expected_pressure, test_pressure, reltol=1e-3)
            else:
                return
        return verify

    from clawpack.pyclaw.util import gen_variants
    import acoustics_2d

    classic_tests = gen_variants(acoustics_2d.setup, verify_data('verify_classic.txt'),
                                 kernel_languages=('Fortran',), solver_type='classic', disable_output=True)

    sharp_tests_rk   = gen_variants(acoustics_2d.setup, verify_data('verify_sharpclaw.txt'),
                                 kernel_languages=('Fortran',), solver_type='sharpclaw', 
                                 time_integrator='SSP104', disable_output=True)

    sharp_tests_lmm   = gen_variants(acoustics_2d.setup, verify_data('verify_sharpclaw_lmm.txt'),
                                 kernel_languages=('Fortran',), solver_type='sharpclaw', 
                                 time_integrator='SSPMS32', disable_output=True)

    from itertools import chain
    for test in chain(classic_tests, sharp_tests_rk, sharp_tests_lmm):
        yield test

########NEW FILE########
__FILENAME__ = acoustics_2d_interface
#!/usr/bin/env python
# encoding: utf-8
r"""
Two-dimensional variable-coefficient acoustics
==============================================

Solve the variable-coefficient acoustics equations:

.. math:: 
    p_t + K(x,y) (u_x + v_y) & = 0 \\ 
    u_t + p_x / \rho(x,y) & = 0 \\
    v_t + p_y / \rho(x,y) & = 0.

Here p is the pressure, (u,v) is the velocity, :math:`K(x,y)` is the bulk modulus,
and :math:`\rho(x,y)` is the density.
"""
 
import numpy as np

def setup(kernel_language='Fortran',use_petsc=False,outdir='./_output',solver_type='classic',
        time_integrator='SSP104',lim_type=2,disable_output=False):
    """
    Example python script for solving the 2d acoustics equations.
    """
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type=='classic':
        solver=pyclaw.ClawSolver2D(riemann.vc_acoustics_2D)
        solver.dimensional_split=False
        solver.limiters = pyclaw.limiters.tvd.MC
    elif solver_type=='sharpclaw':
        solver=pyclaw.SharpClawSolver2D(riemann.vc_acoustics_2D)
        solver.time_integrator=time_integrator
        if time_integrator=='SSPMS32':
            solver.cfl_max = 0.25
            solver.cfl_desired = 0.24


    solver.bc_lower[0]=pyclaw.BC.wall
    solver.bc_upper[0]=pyclaw.BC.extrap
    solver.bc_lower[1]=pyclaw.BC.wall
    solver.bc_upper[1]=pyclaw.BC.extrap
    solver.aux_bc_lower[0]=pyclaw.BC.wall
    solver.aux_bc_upper[0]=pyclaw.BC.extrap
    solver.aux_bc_lower[1]=pyclaw.BC.wall
    solver.aux_bc_upper[1]=pyclaw.BC.extrap

    # Initialize domain
    mx=200; my=200
    x = pyclaw.Dimension('x',-1.0,1.0,mx)
    y = pyclaw.Dimension('y',-1.0,1.0,my)
    domain = pyclaw.Domain([x,y])

    num_eqn = 3
    num_aux = 2 # density, sound speed
    state = pyclaw.State(domain,num_eqn,num_aux)

    # Cell centers coordinates
    grid = state.grid
    Y,X = np.meshgrid(grid.y.centers,grid.x.centers)

    # Set aux arrays
    rhol = 4.0
    rhor = 1.0
    bulkl = 4.0
    bulkr = 4.0
    cl = np.sqrt(bulkl/rhol)
    cr = np.sqrt(bulkr/rhor)
    state.aux[0,:,:] = rhol*(X<0.) + rhor*(X>=0.) # Density
    state.aux[1,:,:] = cl*(X<0.) + cr*(X>=0.) # Sound speed

    # Set initial condition
    x0 = -0.5; y0 = 0.
    r = np.sqrt((X-x0)**2 + (Y-y0)**2)
    width=0.1; rad=0.25
    state.q[0,:,:] = (np.abs(r-rad)<=width)*(1.+np.cos(np.pi*(r-rad)/width))
    state.q[1,:,:] = 0.
    state.q[2,:,:] = 0.

    claw = pyclaw.Controller()
    claw.keep_copy = True
    if disable_output:
        claw.output_format = None
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir=outdir
    claw.num_output_times = 20
    claw.write_aux_init = True
    claw.setplot = setplot
    if use_petsc:
        claw.output_options = {'format':'binary'}

    # Solve
    claw.tfinal = 0.6

    return claw


#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 

    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data
    
    # Figure for pressure
    plotfigure = plotdata.new_plotfigure(name='Pressure', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Pressure'
    plotaxes.scaled = True      # so aspect ratio is 1

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 0
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True
    plotitem.pcolor_cmin = 0.0
    plotitem.pcolor_cmax=1.0
    

    # Figure for x-velocity plot
    plotfigure = plotdata.new_plotfigure(name='x-Velocity', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'u'

    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 1
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True
    plotitem.pcolor_cmin = -0.3
    plotitem.pcolor_cmax=   0.3
    
    return plotdata

if __name__=="__main__":
    import sys
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = test_acoustics_2d_variable
def test_acoustics_2d_variable():
    """Test variable-coefficient 2D acoustics"""

    import acoustics_2d_interface

    def verify_classic_acoustics(controller):
        import os
        from clawpack.pyclaw.util import check_diff
        import numpy as np
        """ Verifies 2d variable-coefficient acoustics from a previously verified classic run """

        state = controller.frames[controller.num_output_times].state
        dx, dy = controller.solution.domain.grid.delta
        test_q=state.get_q_global()

        if test_q != None:
            thisdir = os.path.dirname(__file__)
            expected_pressure = np.loadtxt(os.path.join(thisdir,'pressure_classic.txt'))
            test_pressure = test_q[0,:,:]
            #test_err = dx*dy*np.linalg.norm(expected_pressure-test_pressure)
            test_err = np.max(np.abs(expected_pressure[:]-test_pressure[:]))
            return check_diff(0, test_err, abstol=1e-1)


    from clawpack.pyclaw.util import gen_variants

    classic_tests = gen_variants(acoustics_2d_interface.setup, verify_classic_acoustics,
                                 solver_type='classic', disable_output=True)

    sharp_tests_rk   = gen_variants(acoustics_2d_interface.setup, verify_classic_acoustics,
                                 solver_type='sharpclaw', time_integrator='SSP104', disable_output=True)

    sharp_tests_lmm   = gen_variants(acoustics_2d_interface.setup, verify_classic_acoustics, lim_type=1,
                                 solver_type='sharpclaw', time_integrator='SSPMS32', disable_output=True)

    from itertools import chain
    for test in chain(classic_tests, sharp_tests_rk, sharp_tests_lmm):
        yield test

########NEW FILE########
__FILENAME__ = test_acoustics_2d_variable_io
def test_acoustics_2d_variable_io():
    """Test I/O on variable-coefficient 2D acoustics application"""

    import acoustics_2d_interface

    def verify_acoustics_io(controller):
        """ Verifies I/O on 2d variable-coefficient acoustics application"""
        import os
        from clawpack.pyclaw.util import check_diff
        import numpy as np
        from clawpack.pyclaw import Solution
        
        thisdir = os.path.dirname(__file__)
        verify_dir = os.path.join(thisdir,'./io_test_verification')
        
        # Expected solution
        sol_0_expected = Solution()
        sol_0_expected.read(0,path=verify_dir,file_format='ascii',
                               file_prefix=None,read_aux=True)
        expected_aux = sol_0_expected.state.aux

        sol_20_expected = Solution()
        sol_20_expected.read(20,path=verify_dir,file_format='ascii',
                               file_prefix=None,read_aux=False)
        expected_q = sol_20_expected.state.q

        # Test solution
        sol_0_test = Solution()
        sol_0_test.read(0,path=controller.outdir,
                        file_format=controller.output_format,
                        file_prefix=None,read_aux=True,
                        options=controller.output_options)
        test_aux = sol_0_test.state.get_aux_global()

        sol_20_test = Solution()
        sol_20_test.read(20,path=controller.outdir,
                        file_format=controller.output_format,
                        file_prefix=None,read_aux=False,
                        options=controller.output_options)
        test_q = sol_20_test.state.get_q_global()


        test_passed = True
        if test_q is not None:
            q_err = check_diff(expected_q, test_q, reltol=1e-4)
            if q_err is not None:
                return q_err
        else:
            return

        if test_aux is not None:
            aux_err = check_diff(expected_aux, test_aux, reltol=1e-4)
            if aux_err is not None:
                return aux_err
        else:
            return


    from clawpack.pyclaw.util import gen_variants
    tempdir = './_io_test_results'
    classic_tests = gen_variants(acoustics_2d_interface.setup, verify_acoustics_io,
                                 solver_type='classic', outdir=tempdir)


    import shutil
    from itertools import chain
    try:
        for test in chain(classic_tests):
            yield test
    finally:
        ERROR_STR= """Error removing %(path)s, %(error)s """
        try:
            shutil.rmtree(tempdir )
        except OSError as (errno, strerror):
            print ERROR_STR % {'path' : tempdir, 'error': strerror }

########NEW FILE########
__FILENAME__ = acoustics_3d_interface
#!/usr/bin/env python
# encoding: utf-8

import numpy as np

def setup(use_petsc=False,outdir='./_output',solver_type='classic',disable_output=False,**kwargs):
    """
    Example python script for solving the 3d acoustics equations.
    """
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type=='classic':
        solver=pyclaw.ClawSolver3D(riemann.vc_acoustics_3D)
        solver.limiters = pyclaw.limiters.tvd.MC
    elif solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver3D(riemann.vc_acoustics_3D)
        
    else:
        raise Exception('Unrecognized solver_type.')


    solver.bc_lower[0]=pyclaw.BC.periodic
    solver.bc_upper[0]=pyclaw.BC.periodic
    solver.bc_lower[1]=pyclaw.BC.periodic
    solver.bc_upper[1]=pyclaw.BC.periodic
    solver.bc_lower[2]=pyclaw.BC.periodic
    solver.bc_upper[2]=pyclaw.BC.periodic

    solver.aux_bc_lower[0]=pyclaw.BC.periodic
    solver.aux_bc_upper[0]=pyclaw.BC.periodic
    solver.aux_bc_lower[1]=pyclaw.BC.periodic
    solver.aux_bc_upper[1]=pyclaw.BC.periodic
    solver.aux_bc_lower[2]=pyclaw.BC.periodic
    solver.aux_bc_upper[2]=pyclaw.BC.periodic

    app = None
    if 'test' in kwargs:
        test = kwargs['test']
        if test == 'homogeneous':
            app = 'test_homogeneous'
        elif test == 'heterogeneous':
            app = 'test_heterogeneous'
        else: raise Exception('Unrecognized test')

    if app == 'test_homogeneous':
        if solver_type=='classic':
            solver.dimensional_split=True
        else:
            solver.lim_type = 1

        solver.limiters = [4]
        
        mx=256; my=4; mz=4
        zr = 1.0  # Impedance in right half
        cr = 1.0  # Sound speed in right half

    if app == 'test_heterogeneous' or app == None:
        if solver_type=='classic':
            solver.dimensional_split=False
        
        solver.bc_lower[0]    =pyclaw.BC.wall
        solver.bc_lower[1]    =pyclaw.BC.wall
        solver.bc_lower[2]    =pyclaw.BC.wall
        solver.aux_bc_lower[0]=pyclaw.BC.wall
        solver.aux_bc_lower[1]=pyclaw.BC.wall
        solver.aux_bc_lower[2]=pyclaw.BC.wall
        mx=30; my=30; mz=30
        zr = 2.0  # Impedance in right half
        cr = 2.0  # Sound speed in right half

    solver.limiters = pyclaw.limiters.tvd.MC

    # Initialize domain
    x = pyclaw.Dimension('x',-1.0,1.0,mx)
    y = pyclaw.Dimension('y',-1.0,1.0,my)
    z = pyclaw.Dimension('z',-1.0,1.0,mz)
    domain = pyclaw.Domain([x,y,z])

    num_eqn = 4
    num_aux = 2 # density, sound speed
    state = pyclaw.State(domain,num_eqn,num_aux)

    zl = 1.0  # Impedance in left half
    cl = 1.0  # Sound speed in left half

    grid = state.grid
    grid.compute_c_centers()
    X,Y,Z = grid._c_centers

    state.aux[0,:,:,:] = zl*(X<0.) + zr*(X>=0.) # Impedance
    state.aux[1,:,:,:] = cl*(X<0.) + cr*(X>=0.) # Sound speed

    x0 = -0.5; y0 = 0.; z0 = 0.
    if app == 'test_homogeneous':
        r = np.sqrt((X-x0)**2)
        width=0.2
        state.q[0,:,:,:] = (np.abs(r)<=width)*(1.+np.cos(np.pi*(r)/width))

    elif app == 'test_heterogeneous' or app == None:
        r = np.sqrt((X-x0)**2 + (Y-y0)**2 + (Z-z0)**2)
        width=0.1
        state.q[0,:,:,:] = (np.abs(r-0.3)<=width)*(1.+np.cos(np.pi*(r-0.3)/width))

    else: raise Exception('Unexpected application')
        
    state.q[1,:,:,:] = 0.
    state.q[2,:,:,:] = 0.
    state.q[3,:,:,:] = 0.

    claw = pyclaw.Controller()
    claw.keep_copy = True
    if disable_output:
       claw.output_format = None
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir

    # Solve
    claw.tfinal = 2.0
    return claw


if __name__=="__main__":
    import sys
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup)

########NEW FILE########
__FILENAME__ = test_3d_acoustics
import os
from itertools import chain

import numpy as np

from clawpack.pyclaw.util import gen_variants
from clawpack.pyclaw.util import check_diff

import acoustics_3d_interface


def test_3d_acoustics():
    """ Tests for homogeneous and heterogeneous 3D acoustics"""

    def acoustics_verify_homogeneous(claw):
        """ Regression test for 3D homogeneous acoustics equations.
        """

        pinitial = claw.frames[0].state.get_q_global()
        pfinal = claw.frames[claw.num_output_times].state.get_q_global()

        if pinitial is not None:
            pinitial = pinitial[0, :, :, :].reshape(-1)
            pfinal = pfinal[0, :, :, :].reshape(-1)
            grid = claw.solution.state.grid
            final_difference = np.prod(grid.delta)*np.linalg.norm(pfinal-pinitial, ord=1)
            return check_diff(0., final_difference, abstol=1e-1)
        else:
            # In parallel, we check values only for the rank 0 process
            return

    def acoustics_verify_heterogeneous(claw):
        """ Regression test for 3D heterogeneous acoustics equations
        """

        pinitial = claw.frames[0].state.get_q_global()
        pfinal = claw.frames[claw.num_output_times].state.get_q_global()

        if pinitial is not None:
            pfinal = pfinal[0, :, :, :].reshape(-1)
            thisdir = os.path.dirname(__file__)
            verify_pfinal = np.loadtxt(os.path.join(thisdir, 'verify_classic_heterogeneous.txt'))
            norm_err = np.linalg.norm(pfinal-verify_pfinal)
            return check_diff(0, norm_err, abstol=10.)
        else:
            # In parallel, we check values only for the rank 0 process
            return

    classic_homogeneous_tests = gen_variants(acoustics_3d_interface.setup, acoustics_verify_homogeneous,
                                             kernel_languages=('Fortran',),
                                             solver_type='classic', test='homogeneous',
                                             disable_output=True)

    classic_heterogeneous_tests = gen_variants(acoustics_3d_interface.setup, acoustics_verify_heterogeneous,
                                               kernel_languages=('Fortran',),
                                               solver_type='classic', test='heterogeneous',
                                               disable_output=True)

    sharp_homogeneous_tests = gen_variants(acoustics_3d_interface.setup, acoustics_verify_homogeneous,
                                           kernel_languages=('Fortran',),
                                           solver_type='sharpclaw', test='homogeneous',
                                           disable_output=True)

    sharp_heterogeneous_tests = gen_variants(acoustics_3d_interface.setup, acoustics_verify_heterogeneous,
                                             kernel_languages=('Fortran',),
                                             solver_type='sharpclaw', test='heterogeneous',
                                             disable_output=True)

    for test in chain(classic_homogeneous_tests, classic_heterogeneous_tests, sharp_homogeneous_tests,
                      sharp_heterogeneous_tests):
        yield test

########NEW FILE########
__FILENAME__ = advection_1d
#!/usr/bin/env python
# encoding: utf-8

r"""
One-dimensional advection
=========================

Solve the linear advection equation:

.. math:: 
    q_t + u q_x & = 0.

Here q is the density of some conserved quantity and u is the velocity.

The initial condition is a Gaussian and the boundary conditions are periodic.
The final solution is identical to the initial data because the wave has
crossed the domain exactly once.
"""

def setup(nx=100, kernel_language='Python', use_petsc=False, solver_type='classic', weno_order=5, 
        time_integrator='SSP104', outdir='./_output'):
    import numpy as np
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type=='classic':
        if kernel_language == 'Fortran':
            solver = pyclaw.ClawSolver1D(riemann.advection_1D)
        elif kernel_language=='Python': 
            solver = pyclaw.ClawSolver1D(riemann.advection_1D_py.advection_1D)
    elif solver_type=='sharpclaw':
        if kernel_language == 'Fortran':
            solver = pyclaw.SharpClawSolver1D(riemann.advection_1D)
        elif kernel_language=='Python': 
            solver = pyclaw.SharpClawSolver1D(riemann.advection_1D_py.advection_1D)
        solver.weno_order=weno_order
        solver.time_integrator=time_integrator
    else: raise Exception('Unrecognized value of solver_type.')

    solver.kernel_language = kernel_language

    solver.bc_lower[0] = 2
    solver.bc_upper[0] = 2

    x = pyclaw.Dimension('x',0.0,1.0,nx)
    domain = pyclaw.Domain(x)
    num_eqn = 1
    state = pyclaw.State(domain,num_eqn)
    state.problem_data['u']=1.

    grid = state.grid
    xc=grid.x.centers
    beta=100; gamma=0; x0=0.75
    state.q[0,:] = np.exp(-beta * (xc-x0)**2) * np.cos(gamma * (xc - x0))

    claw = pyclaw.Controller()
    claw.keep_copy = True
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver

    if outdir is not None:
        claw.outdir = outdir
    else:
        claw.output_format = None

    claw.tfinal =1.0
    claw.setplot = setplot

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    plotdata.clearfigures()  # clear any old figures,axes,items data

    plotfigure = plotdata.new_plotfigure(name='q', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.ylimits = [-.2,1.0]
    plotaxes.title = 'q'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    plotitem.kwargs = {'linewidth':2,'markersize':5}
    
    return plotdata

 
if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = test_advection
def test_1d_advection():
    """test_1d_advection

    tests against expected classic, sharpclaw, and high-order weno results """

    import advection_1d

    def verify_expected(expected):
        """ given an expected value, returns a verification function """
        def advection_verify(claw):
            from clawpack.pyclaw.util import check_diff
            import numpy as np

            q0=claw.frames[0].state.get_q_global()
            qfinal=claw.frames[claw.num_output_times].state.get_q_global()

            if q0 != None and qfinal != None:
                dx=claw.solution.domain.grid.delta[0]
                test = dx*np.linalg.norm(qfinal-q0,1)
                return check_diff(expected, test, reltol=1e-4)
            else:
                return
        return advection_verify

    from clawpack.pyclaw.util import gen_variants

    classic_tests = gen_variants(advection_1d.setup, verify_expected(3.203924e-04),
                                 kernel_languages=('Python','Fortran'),
                                 solver_type='classic', outdir=None)

    sharp_tests_rk  = gen_variants(advection_1d.setup, verify_expected(1.163605e-05),
                                 kernel_languages=('Python','Fortran'),
                                 solver_type='sharpclaw',time_integrator='SSP104', outdir=None)

    sharp_tests_lmm = gen_variants(advection_1d.setup, verify_expected(3.39682948116e-05),
                                 kernel_languages=('Python','Fortran'),
                                 solver_type='sharpclaw',time_integrator='SSPMS32', outdir=None)

    weno_tests = gen_variants(advection_1d.setup, verify_expected(7.489618e-06),
                                 kernel_languages=('Fortran',), solver_type='sharpclaw', 
                                 time_integrator='SSP104', weno_order=17,
                                 outdir=None)

    from itertools import chain
    for test in chain(classic_tests, sharp_tests_rk, sharp_tests_lmm, weno_tests):
        yield test

if __name__=='__main__':
    test_1d_advection()

########NEW FILE########
__FILENAME__ = variable_coefficient_advection
#!/usr/bin/env python
# encoding: utf-8
r"""
One-dimensional advection with variable velocity
================================================

Solve the conservative variable-coefficient advection equation:

.. math:: q_t + (u(x)q)_x = 0.

Here q is the density of some conserved quantity and u(x) is the velocity.
The velocity field used is

.. math:: u(x) = 2 + sin(2\pi x).

The boundary conditions are periodic.
The initial data get stretched and compressed as they move through the
fast and slow parts of the velocity field.
"""


import numpy as np

def qinit(state):

    # Initial Data parameters
    ic = 3
    beta = 100.
    gamma = 0.
    x0 = 0.3
    x1 = 0.7
    x2 = 0.9

    x =state.grid.x.centers
    
    # Gaussian
    qg = np.exp(-beta * (x-x0)**2) * np.cos(gamma * (x - x0))
    # Step Function
    qs = (x > x1) * 1.0 - (x > x2) * 1.0
    
    if   ic == 1: state.q[0,:] = qg
    elif ic == 2: state.q[0,:] = qs
    elif ic == 3: state.q[0,:] = qg + qs


def auxinit(state):
    # Initilize petsc Structures for aux
    xc=state.grid.x.centers
    state.aux[0,:] = np.sin(2.*np.pi*xc)+2
    

def setup(use_petsc=False,solver_type='classic',kernel_language='Python',outdir='./_output'):
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type=='classic':
        if kernel_language == 'Fortran':
            solver = pyclaw.ClawSolver1D(riemann.vc_advection_1D)
        elif kernel_language=='Python': 
            solver = pyclaw.ClawSolver1D(riemann.vc_advection_1D_py.vc_advection_1D)
    elif solver_type=='sharpclaw':
        if kernel_language == 'Fortran':
            solver = pyclaw.SharpClawSolver1D(riemann.vc_advection_1D)
        elif kernel_language=='Python': 
            solver = pyclaw.SharpClawSolver1D(riemann.vc_advection_1D_py.vc_advection_1D)
        solver.weno_order=weno_order
    else: raise Exception('Unrecognized value of solver_type.')

    solver.kernel_language = kernel_language

    solver.limiters = pyclaw.limiters.tvd.MC
    solver.bc_lower[0] = 2
    solver.bc_upper[0] = 2
    solver.aux_bc_lower[0] = 2
    solver.aux_bc_upper[0] = 2

    xlower=0.0; xupper=1.0; mx=100
    x    = pyclaw.Dimension('x',xlower,xupper,mx)
    domain = pyclaw.Domain(x)
    num_aux=1
    num_eqn = 1
    state = pyclaw.State(domain,num_eqn,num_aux)

    qinit(state)
    auxinit(state)

    claw = pyclaw.Controller()
    claw.outdir = outdir
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver

    claw.tfinal = 1.0
    claw.setplot = setplot
    claw.keep_copy = True
    
    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='q', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.ylimits = [-.1,1.1]
    plotaxes.title = 'q'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    plotitem.kwargs = {'linewidth':2,'markersize':5}
    
    return plotdata

 
if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = advection_2d
#!/usr/bin/env python
# encoding: utf-8
r"""
Two-dimensional advection
=========================

Solve the two-dimensional linear advection equation

.. math:: 
    q_t + (uq)_x + (vq)_y & = 0

Here q is a conserved quantity, and (u,v) is the velocity vector.
"""

import numpy as np

def qinit(state):

    # Set initial conditions for q.
    # Sample scalar equation with data that is piecewise constant with
    # q = 1.0  if  0.1 < x < 0.6   and   0.1 < y < 0.6
    #     0.1  otherwise
    
    x = state.grid.x.centers
    y = state.grid.y.centers
    for i in range(len(x)):
        for j in range(len(y)):
            if x[i] > 0.0 and x[i] < 0.5 and y[j]>0.0 and y[j] < 0.5:
                state.q[:,i,j] = 1.0
            else:
                state.q[:,i,j] = 0.1
                
def setup(use_petsc=False,outdir='./_output',solver_type='classic'):
    """
    Example python script for solving the 2d advection equation.
    """
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type=='classic':
        solver = pyclaw.ClawSolver2D(riemann.advection_2D)
        solver.dimensional_split = 1
        solver.limiters = pyclaw.limiters.tvd.vanleer
    elif solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver2D(riemann.advection_2D)

    solver.bc_lower[0] = pyclaw.BC.periodic
    solver.bc_upper[0] = pyclaw.BC.periodic
    solver.bc_lower[1] = pyclaw.BC.periodic
    solver.bc_upper[1] = pyclaw.BC.periodic

    solver.cfl_max=1.0
    solver.cfl_desired = 0.9

    #===========================================================================
    # Initialize domain, then initialize the solution associated to the domain and
    # finally initialize aux array
    #===========================================================================

    # Domain:
    mx=50; my=50
    x = pyclaw.Dimension('x',0.0,1.0,mx)
    y = pyclaw.Dimension('y',0.0,1.0,my)
    domain = pyclaw.Domain([x,y])

    num_eqn = 1
    state = pyclaw.State(domain,num_eqn)

    state.problem_data['u'] = 0.5 # Parameters (global auxiliary variables)
    state.problem_data['v'] = 1.0

    # Initial solution
    # ================
    qinit(state) # This function is defined above


    #===========================================================================
    # Set up controller and controller parameters
    #===========================================================================
    claw = pyclaw.Controller()
    claw.tfinal = 2.0
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir
    claw.setplot = setplot
    claw.keep_copy = True

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for pcolor plot
    plotfigure = plotdata.new_plotfigure(name='q[0]', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'q[0]'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 0
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.pcolor_cmin = 0.0
    plotitem.pcolor_cmax = 1.0
    plotitem.add_colorbar = True
    
    # Figure for contour plot
    plotfigure = plotdata.new_plotfigure(name='contour', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'q[0]'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_contour')
    plotitem.plot_var = 0
    plotitem.contour_nlevels = 20
    plotitem.contour_min = 0.01
    plotitem.contour_max = 0.99
    plotitem.amr_contour_colors = ['b','k','r']
    
    return plotdata

    
if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = advection_annulus
#!/usr/bin/env python
# encoding: utf-8
r"""
Advection in an annular domain
==============================

Solve the linear advection equation:

.. math:: 
    q_t + (u(x,y) q)_x + (v(x,y) q)_y & = 0.

Here q is the density of some conserved quantity and (u,v) is the velocity
field.  We take a rotational velocity field: :math:`u = \cos(\theta), v = \sin(\theta)`.

This is the simplest example that shows how to use a mapped grid in PyClaw.
"""


#===========================================================================
# Import libraries
#===========================================================================
import numpy as np

def mapc2p_annulus(grid,mC):
    """
    Specifies the mapping to curvilinear coordinates.

    Takes as input: array_list made by x_coordinates, y_ccordinates in the map 
                    space.
    Returns as output: array_list made by x_coordinates, y_ccordinates in the 
                       physical space.

    Inputs: mC = list composed by two arrays 
                 [array ([xc1, xc2, ...]), array([yc1, yc2, ...])]

    Output: pC = list composed by two arrays 
                 [array ([xp1, xp2, ...]), array([yp1, yp2, ...])]
    """  
    # Define new empty list
    pC = []

    # Populate it with the physical coordinates 
    # Polar coordinates (x coordinate = radius,  y coordinate = theta)
    pC.append(mC[0][:]*np.cos(mC[1][:]))
    pC.append(mC[0][:]*np.sin(mC[1][:]))
    
    return pC


def qinit(state,mx,my):
    """
    Initialize with two Gaussian pulses.
    """

    # The following parameters match the vaules used in clawpack
    # ==========================================================
    # First gaussian pulse
    A1    = 1.    # Amplitude
    beta1 = 40.   # Decay factor
    x1    = -0.5  # x-coordinate of the centers
    y1    = 0.    # y-coordinate of the centers

    # Second gaussian pulse
    A2    = -1.   # Amplitude
    beta2 = 40.   # Decay factor
    x2    = 0.5   # x-coordinate of the centers
    y2    = 0.    # y-coordinate of the centers

    
    # Compute location of all grid cell centers coordinates and store them
    state.grid.compute_p_centers(recompute=True)

    xp = state.grid.p_centers[0]
    yp = state.grid.p_centers[1]
    state.q[0,:,:] = A1*np.exp(-beta1*(np.square(xp-x1) + np.square(yp-y1)))\
                   + A2*np.exp(-beta2*(np.square(xp-x2) + np.square(yp-y2)))


def setaux(state,mx,my):
    """ 
    Set auxiliary array
    aux[0,i,j] is edges velocity at "left" boundary of grid point (i,j)
    aux[1,i,j] is edges velocity at "bottom" boundary of grid point (i,j)
    aux[2,i,j] = kappa  is ratio of cell area to (dxc * dyc)
    """    
    
    # Compute location of all grid cell corner coordinates and store them
    state.grid.compute_p_edges(recompute=True)

    # Get grid spacing
    dxc = state.grid.delta[0]
    dyc = state.grid.delta[1]
    pcorners = state.grid.p_edges

    aux = velocities_capa(pcorners[0],pcorners[1],dxc,dyc)
    return aux


def velocities_upper(state,dim,t,auxbc,num_ghost):
    """
    Set the velocities for the ghost cells outside the outer radius of the annulus.
    """
    from mapc2p import mapc2p

    grid=state.grid
    mx = grid.num_cells[0]
    my = grid.num_cells[1]
    dxc = grid.delta[0]
    dyc = grid.delta[1]

    if dim == grid.dimensions[0]:
        xc1d = grid.lower[0]+dxc*(np.arange(mx+num_ghost,mx+2*num_ghost+1)-num_ghost)
        yc1d = grid.lower[1]+dyc*(np.arange(my+2*num_ghost+1)-num_ghost)
        yc,xc = np.meshgrid(yc1d,xc1d)

        xp,yp = mapc2p(xc,yc)

        auxbc[:,-num_ghost:,:] = velocities_capa(xp,yp,dxc,dyc)

    else:
        raise Exception('Custum BC for this boundary is not appropriate!')


def velocities_lower(state,dim,t,auxbc,num_ghost):
    """
    Set the velocities for the ghost cells outside the inner radius of the annulus.
    """
    from mapc2p import mapc2p

    grid=state.grid
    my = grid.num_cells[1]
    dxc = grid.delta[0]
    dyc = grid.delta[1]

    if dim == grid.dimensions[0]:
        xc1d = grid.lower[0]+dxc*(np.arange(num_ghost+1)-num_ghost)
        yc1d = grid.lower[1]+dyc*(np.arange(my+2*num_ghost+1)-num_ghost)
        yc,xc = np.meshgrid(yc1d,xc1d)

        xp,yp = mapc2p(xc,yc)

        auxbc[:,0:num_ghost,:] = velocities_capa(xp,yp,dxc,dyc)

    else:
        raise Exception('Custum BC for this boundary is not appropriate!')


def velocities_capa(xp,yp,dx,dy):

    mx = xp.shape[0]-1
    my = xp.shape[1]-1
    aux = np.empty((3,mx,my), order='F')

    # Bottom-left corners
    xp0 = xp[:mx,:my]
    yp0 = yp[:mx,:my]

    # Top-left corners
    xp1 = xp[:mx,1:]
    yp1 = yp[:mx,1:]

    # Top-right corners
    xp2 = xp[1:,1:]
    yp2 = yp[1:,1:]

    # Top-left corners
    xp3 = xp[1:,:my]
    yp3 = yp[1:,:my]

    # Compute velocity component
    aux[0,:mx,:my] = (stream(xp1,yp1)- stream(xp0,yp0))/dy
    aux[1,:mx,:my] = -(stream(xp3,yp3)- stream(xp0,yp0))/dx

    # Compute area of the physical element
    area = 1./2.*( (yp0+yp1)*(xp1-xp0) +
                   (yp1+yp2)*(xp2-xp1) +
                   (yp2+yp3)*(xp3-xp2) +
                   (yp3+yp0)*(xp0-xp3) )
    
    # Compute capa 
    aux[2,:mx,:my] = area/(dx*dy)

    return aux

    
def stream(xp,yp):
    """ 
    Calculates the stream function in physical space.
    Clockwise rotation. One full rotation corresponds to 1 (second).
    """
    streamValue = np.pi*(xp**2 + yp**2)

    return streamValue


def setup(use_petsc=False,outdir='./_output',solver_type='classic'):
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type == 'classic':
        solver = pyclaw.ClawSolver2D(riemann.vc_advection_2D)
        solver.dimensional_split = 0
        solver.transverse_waves = 2
        solver.order = 2
    elif solver_type == 'sharpclaw':
        solver = pyclaw.SharpClawSolver2D(riemann.vc_advection_2D)

    solver.bc_lower[0] = pyclaw.BC.extrap
    solver.bc_upper[0] = pyclaw.BC.extrap
    solver.bc_lower[1] = pyclaw.BC.periodic
    solver.bc_upper[1] = pyclaw.BC.periodic

    solver.aux_bc_lower[0] = pyclaw.BC.custom
    solver.aux_bc_upper[0] = pyclaw.BC.custom
    solver.user_aux_bc_lower = velocities_lower
    solver.user_aux_bc_upper = velocities_upper
    solver.aux_bc_lower[1] = pyclaw.BC.periodic
    solver.aux_bc_upper[1] = pyclaw.BC.periodic

    solver.dt_initial = 0.1
    solver.cfl_max = 0.5
    solver.cfl_desired = 0.2

    solver.limiters = pyclaw.limiters.tvd.vanleer

    #===========================================================================
    # Initialize domain and state, then initialize the solution associated to the 
    # state and finally initialize aux array
    #===========================================================================
    # Domain:
    xlower = 0.2
    xupper = 1.0
    mx = 40

    ylower = 0.0
    yupper = np.pi*2.0
    my = 120

    x = pyclaw.Dimension('x',xlower,xupper,mx)
    y = pyclaw.Dimension('y',ylower,yupper,my)
    domain = pyclaw.Domain([x,y])
    domain.grid.mapc2p = mapc2p_annulus # Override default_mapc2p function implemented in geometry.py

    # State:
    num_eqn = 1  # Number of equations
    state = pyclaw.State(domain,num_eqn)

    
    # Set initial solution
    # ====================
    qinit(state,mx,my) # This function is defined above

    # Set auxiliary array
    # ===================
    state.aux = setaux(state,mx,my) # This function is defined above
    state.index_capa = 2

    
    #===========================================================================
    # Set up controller and controller parameters
    #===========================================================================
    claw = pyclaw.Controller()
    claw.keep_copy = False
    claw.output_style = 1
    claw.num_output_times = 10
    claw.tfinal = 1.0
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir
    claw.setplot = setplot
    claw.keep_copy = True

    return claw


#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """
    from mapc2p import mapc2p
    import numpy as np
    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data
    
    # Figure for pcolor plot
    plotfigure = plotdata.new_plotfigure(name='q[0]', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = 'auto'
    plotaxes.title = 'q[0]'
    plotaxes.afteraxes = "pylab.axis('scaled')" 

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 0
    plotitem.pcolor_cmap = colormaps.red_yellow_blue
    plotitem.pcolor_cmin = -1.
    plotitem.pcolor_cmax = 1.
    plotitem.add_colorbar = True
    plotitem.MappedGrid = True
    plotitem.mapc2p = mapc2p


    # Figure for contour plot
    plotfigure = plotdata.new_plotfigure(name='contour', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = 'auto'
    plotaxes.title = 'q[0]'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_contour')
    plotitem.plot_var = 0
    plotitem.contour_levels = np.linspace(-0.9, 0.9, 10)
    plotitem.contour_colors = 'k'
    plotitem.patchedges_show = 1
    plotitem.MappedGrid = True
    plotitem.mapc2p = mapc2p

    return plotdata

 
if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = mapc2p


def mapc2p(xc,yc):
    """
    Specifies the mapping to curvilinear coordinates    
    """
    import numpy as np

    # Polar coordinates (x coordinate = radius,  y coordinate = theta)
    xp = xc * np.cos(yc)
    yp = xc * np.sin(yc)
    return xp,yp

########NEW FILE########
__FILENAME__ = burgers_1d
#!/usr/bin/env python
# encoding: utf-8

r"""
Burgers' equation
=========================

Solve the inviscid Burgers' equation:

.. math:: 
    q_t + \frac{1}{2} (q^2)_x & = 0.

This is a nonlinear PDE often used as a very simple
model for fluid dynamics.

The initial condition is sinusoidal, but after a short time a shock forms
(due to the nonlinearity).
"""

def setup(use_petsc=0,kernel_language='Fortran',outdir='./_output',solver_type='classic'):
    """
    Example python script for solving the 1d Burgers equation.
    """

    import numpy as np
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    #===========================================================================
    # Setup solver and solver parameters
    #===========================================================================
    if solver_type=='sharpclaw':
        if kernel_language=='Python': 
            solver = pyclaw.SharpClawSolver1D(riemann.burgers_1D_py.burgers_1D)
        elif kernel_language=='Fortran':
            solver = pyclaw.SharpClawSolver1D(riemann.burgers_1D)
    else:
        if kernel_language=='Python': 
            solver = pyclaw.ClawSolver1D(riemann.burgers_1D_py.burgers_1D)
        elif kernel_language=='Fortran':
            solver = pyclaw.ClawSolver1D(riemann.burgers_1D)
        solver.limiters = pyclaw.limiters.tvd.vanleer

    solver.kernel_language = kernel_language
        
    solver.bc_lower[0] = pyclaw.BC.periodic
    solver.bc_upper[0] = pyclaw.BC.periodic

    #===========================================================================
    # Initialize domain and then initialize the solution associated to the domain
    #===========================================================================
    x = pyclaw.Dimension('x',0.0,1.0,500)
    domain = pyclaw.Domain(x)
    num_eqn = 1
    state = pyclaw.State(domain,num_eqn)

    grid = state.grid
    xc=grid.x.centers
    state.q[0,:] = np.sin(np.pi*2*xc) + 0.50
    state.problem_data['efix']=True

    #===========================================================================
    # Setup controller and controller parameters. Then solve the problem
    #===========================================================================
    claw = pyclaw.Controller()
    claw.tfinal =0.5
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir
    claw.setplot = setplot
    claw.keep_copy = True

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='q[0]', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = [-1., 2.]
    plotaxes.title = 'q[0]'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    
    return plotdata


if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)


########NEW FILE########
__FILENAME__ = compare_solvers
#!/usr/bin/env python
# encoding: utf-8

from clawpack import pyclaw
import numpy as np
import logging

def debug_loggers():
    """
    Turn on maximimum debugging from all loggers.
    """

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.propagate = True


def disable_loggers():
    """
    Disable all loggers (quiet runs)
    """

    root_logger = logging.getLogger()
    root_logger.disabled = True

from clawpack.riemann import advection_1D
fsolver_1D = pyclaw.ClawSolver1D(advection_1D)
fsolver_1D.kernel_language = 'Fortran'

from clawpack.riemann import advection_1D_py
pysolver_1D = pyclaw.ClawSolver1D(advection_1D_py.advection_1D)
pysolver_1D.kernel_language = 'Python'

from clawpack.riemann import shallow_roe_with_efix_2D
fsolver_2D = pyclaw.ClawSolver2D(shallow_roe_with_efix_2D)
fsolver_2D.kernel_language = 'Fortran'

solvers_1D = {
    'current_fortran' : fsolver_1D,
    'current_python'  : pysolver_1D
}

solvers_2D = {
    'current_fortran' : fsolver_2D
}

new_solvers_1D = {}

# Here we try and bring in "experimental" solvers for comparison
# If we can't bring in the solver, complain and move on...

try:
    from clawpack.pyclaw.examples import iso_c_advection

    iso_c_solver = iso_c_advection.ISO_C_ClawSolver1D(None, 'clawpack.pyclaw')

    iso_c_solver.kernel_language = 'Fortran'
    iso_c_solver.rp = iso_c_advection.iso_c_rp1_advection(1.0)
    iso_c_solver.num_waves = 1

    new_solvers_1D['iso_c'] = iso_c_solver

except (ImportError, OSError) as err:
    print "Unable to import ISO C variant", err

solvers_1D.update(new_solvers_1D)


def verify_1D(dx, q0, qfinal):
    if q0 is not None and qfinal is not None:
        test = dx*np.linalg.norm(qfinal-q0,1)
        return test

def verify_2D(dx, qfinal):
    if qfinal is not None:
        test = dx*np.linalg.norm(qfinal)
        return test

def compare_1D(nx=1000):
    """
    Tests a variety of Riemann solver ideas on 1D advection
    """

    import compare_solvers
    import time

    solvers = compare_solvers.solvers_1D

    times, tests = {}, {}

    for name, solver in solvers.iteritems():
        solver.bc_lower[0] = pyclaw.BC.periodic
        solver.bc_upper[0] = pyclaw.BC.periodic

        from clawpack.pyclaw.examples.advection_1d import advection
        claw = advection.advection(nx=nx,outdir=compare_solvers.outdir)
        claw.solver = solver
        claw.keep_copy = True

        # benchmark
        t0 = time.clock()
        claw.run()
        t1 = time.clock()
        t = t1-t0
        times[name] = t

        # verify
        test = verify_1D(claw.solution.domain.grid.delta[0],
                         claw.frames[0].state.get_q_global(),
                         claw.frames[claw.num_output_times].state.get_q_global())
        tests[name] = test

    return times, tests


def compare_2D(nx=(250,250)):
    """
    Tests a variety of Riemann solver ideas on 2D shallow water equation
    """
    import compare_solvers
    import time

    solvers = compare_solvers.solvers_2D

    times, tests = {}, {}

    for name, solver in solvers.iteritems():
        solver.num_waves = 3
        solver.bc_lower[0] = pyclaw.BC.extrap
        solver.bc_upper[0] = pyclaw.BC.wall
        solver.bc_lower[1] = pyclaw.BC.extrap
        solver.bc_upper[1] = pyclaw.BC.wall

        solver.limiters = pyclaw.limiters.tvd.MC
        solver.dimensional_split=1

        from clawpack.pyclaw.examples.shallow_2d import shallow2D
        claw = shallow2D.shallow2D(outdir=compare_solvers.outdir)
        claw.solver = solver
        claw.keep_copy = True

        t0 = time.clock()
        claw.run()
        t1 = time.clock()
        t = t1-t0
        times[name] = t

        # verify
        test = verify_2D(claw.solution.domain.grid.delta[0],
                         claw.frames[claw.num_output_times].state.get_q_global())
        tests[name] = test

    return times, tests

if __name__=="__main__":
    import compare_solvers
    disable_loggers()
#    debug_loggers()

    import sys

    vis = True
    
    if vis:
        compare_solvers.outdir='./_output'
    else:
        compare_solvers.outdir = None
        
    if len(sys.argv) > 1:
        nx_1D = int(sys.argv[1])
    else:
        nx_1D = 500

    if len(sys.argv) > 2:
        # '(2,2)' -> (2,2)
        nx_2D = tuple(int(i) for i in argv.split(','))
    else:
        nx_2D = 100,100

    def print_time_accuracy(times, tests, solvers):
        print "\n=====TIME====="
        for name in solvers.keys():
            print "%-25s: %g" % (name, times[name])

        print "\n===ACCURACY==="
        for name in solvers.keys():
            print "%-25s: %g" % (name, tests[name])

    compare_solvers.tfinal = 1.0
    print "\nRiemann comparison on 1D advection to t=%g with %d grid points" % \
        (compare_solvers.tfinal, nx_1D)

    times, tests = compare_1D(nx=nx_1D)

    print_time_accuracy(times, tests, compare_solvers.solvers_1D)

    compare_solvers.tfinal = 2.5
    print ("\nRiemann comparison on 2D shallow water equation to t=%g" + \
               " with %dx%d grid points") % ((compare_solvers.tfinal,) + nx_2D)

    times, tests = compare_2D(nx=nx_2D)

    print_time_accuracy(times, tests, compare_solvers.solvers_2D)

########NEW FILE########
__FILENAME__ = shocksine
#!/usr/bin/env python
# encoding: utf-8
r"""Shu-Osher problem.
   1D compressible inviscid flow (Euler equations)."""

import numpy as np
gamma = 1.4
gamma1 = gamma - 1.

a = np.array([[0., 0., 0., 0., 0., 0., 0.],
              [.3772689153313680, 0., 0., 0., 0., 0., 0.],
              [.3772689153313680, .3772689153313680, 0., 0., 0., 0., 0.],
              [.2429952205373960, .2429952205373960, .2429952205373960, 0., 0., 0., 0.],
              [.1535890676951260, .1535890676951260, .1535890676951260, .2384589328462900, 0., 0., 0.]])

c = np.array([0., .3772689153313680, .7545378306627360, .7289856616121880, .6992261359316680])

b = np.array([.206734020864804, .206734020864804, .117097251841844, .181802560120140, .287632146308408])

def setup(use_petsc=False,iplot=False,htmlplot=False,outdir='./_output',solver_type='sharpclaw',
        kernel_language='Fortran',use_char_decomp=False):
    """
    Solve the Euler equations of compressible fluid dynamics.
    This example involves a shock wave impacting a sinusoidal density field.
    """
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if kernel_language =='Python':
        rs = riemann.euler_1D_py.euler_roe_1D
    elif kernel_language =='Fortran':
        rs = riemann.euler_with_efix_1D

    if solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver1D(rs)
        solver.time_integrator = 'RK'
        solver.a, solver.b, solver.c = a, b, c
        solver.cfl_desired = 0.6
        solver.cfl_max = 0.7
        if use_char_decomp:
            try:
                import sharpclaw1
                solver.fmod = sharpclaw1
                solver.tfluct_solver = True
                solver.lim_type = 2     # WENO reconstruction 
                solver.char_decomp = 2  # characteristic-wise reconstruction
            except ImportError:
                pass
    else:
        solver = pyclaw.ClawSolver1D(rs)

    solver.kernel_language = kernel_language

    solver.bc_lower[0]=pyclaw.BC.extrap
    solver.bc_upper[0]=pyclaw.BC.extrap

    # Initialize domain
    mx=400;
    x = pyclaw.Dimension('x',-5.0,5.0,mx)
    domain = pyclaw.Domain([x])
    state = pyclaw.State(domain,solver.num_eqn)

    state.problem_data['gamma']= gamma
    state.problem_data['gamma1']= gamma1
    if kernel_language =='Python':
        state.problem_data['efix'] = False

    xc =state.grid.x.centers
    epsilon=0.2
    state.q[0,:] = (xc<-4.)*3.857143 + (xc>=-4.)*(1+epsilon*np.sin(5*xc))
    velocity = (xc<-4.)*2.629369
    state.q[1,:] = velocity * state.q[0,:]
    pressure = (xc<-4.)*10.33333 + (xc>=-4.)*1.
    state.q[2,:] = pressure/gamma1 + 0.5 * state.q[0,:] * velocity**2

    claw = pyclaw.Controller()
    claw.tfinal = 1.8
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.num_output_times = 10
    claw.outdir = outdir
    claw.setplot = setplot

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='Density', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Density'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    
    # Figure for q[1]
    plotfigure = plotdata.new_plotfigure(name='Energy', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Energy'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d')
    plotitem.plot_var = 2
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    
    return plotdata

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = test_shocksine
def test_shocksine():
    """ tests against expected sharpclaw results """
    import shocksine
    from clawpack.pyclaw.util import test_app, check_diff

    def verify_shocksine(controller):
        """ given an expected value, returns a verification function """
        import numpy as np
        import os

        test_solution = controller.solution.state.get_q_global()

        if test_solution != None:
            thisdir = os.path.dirname(__file__)
            expected_density = np.loadtxt(os.path.join(thisdir,'shocksine_regression_density.txt'))
            test_density = test_solution[0,:]
            test_err = np.linalg.norm(expected_density-test_density)
            return check_diff(0, test_err, abstol=1.e-4)


    return test_app(shocksine.setup, verify_shocksine, {})

if __name__=='__main__':
    test_shocksine()

########NEW FILE########
__FILENAME__ = test_woodward_colella_blast
def test_woodward_colella_blast():
    """ tests against expected sharpclaw results """
    import woodward_colella_blast
    from clawpack.pyclaw.util import test_app, check_diff

    def verify_woodward_colella_blast(controller):
        """ given an expected value, returns a verification function """
        import numpy as np
        import os

        test_solution = controller.solution.state.get_q_global()

        if test_solution != None:
            thisdir = os.path.dirname(__file__)
            expected_density = np.loadtxt(os.path.join(thisdir,'blast_regression_density.txt'))
            test_density = test_solution[0,:]
            test_err = np.linalg.norm(expected_density-test_density)
            return check_diff(0, test_err, abstol=1.e-4)


    return test_app(woodward_colella_blast.setup, verify_woodward_colella_blast, {})

if __name__=='__main__':
    test_woodward_colella_blast()

########NEW FILE########
__FILENAME__ = woodward_colella_blast
#!/usr/bin/env python
# encoding: utf-8
r"""
Woodward-Colella blast wave problem
===================================

Solve the one-dimensional Euler equations for inviscid, compressible flow:

.. math::
    \rho_t + (\rho u)_x & = 0 \\
    (\rho u)_t + (\rho u^2 + p)_x & = 0 \\
    E_t + (u (E + p) )_x & = 0.

The fluid is an ideal gas, with pressure given by :math:`p=\rho (\gamma-1)e` where
e is internal energy.

This script runs the Woodward-Colella blast wave interaction problem,
involving the collision of two shock waves.
"""
try:
    import sharpclaw1
except ImportError:
    import os
    from clawpack.pyclaw.util import inplace_build
    this_dir = os.path.dirname(__file__)
    if this_dir == '':
        this_dir = os.path.abspath('.')
    inplace_build(this_dir)
    try:
        # Now try to import again
        import sharpclaw1
    except ImportError:
        import sys
        print >> sys.stderr, "***\nUnable to import problem module or automatically build, try running (in the directory of this file):\n python setup.py build_ext -i\n***"
        raise

gamma = 1.4
gamma1 = gamma - 1.

def setup(use_petsc=False,outdir='./_output',solver_type='sharpclaw',kernel_language='Fortran'):
    """
    Solve the Euler equations of compressible fluid dynamics.
    This example involves a pair of interacting shock waves.
    The conserved quantities are density, momentum density, and total energy density.
    """
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if kernel_language =='Python':
        rs = riemann.euler_1D_py.euler_roe_1D
    elif kernel_language =='Fortran':
        rs = riemann.euler_with_efix_1D

    if solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver1D(rs)
        solver.time_integrator = 'SSP33'
        solver.cfl_max = 0.65
        solver.cfl_desired = 0.6
        try:
            import sharpclaw1
            solver.fmod = sharpclaw1
            solver.tfluct_solver = True
            solver.lim_type = 1     # TVD reconstruction 
            solver.char_decomp = 2  # characteristic-wise reconstructiong
        except ImportError:
            pass
    elif solver_type=='classic':
        solver = pyclaw.ClawSolver1D(rs)
        solver.limiters = 4

    solver.kernel_language = kernel_language

    solver.bc_lower[0]=pyclaw.BC.wall
    solver.bc_upper[0]=pyclaw.BC.wall

    # Initialize domain
    mx=800;
    x = pyclaw.Dimension('x',0.0,1.0,mx)
    domain = pyclaw.Domain([x])
    state = pyclaw.State(domain,solver.num_eqn)

    state.problem_data['gamma']= gamma
    state.problem_data['gamma1']= gamma1
    if kernel_language =='Python':
        state.problem_data['efix'] = False

    state.q[0,:] = 1.
    state.q[1,:] = 0.
    x =state.grid.x.centers
    state.q[2,:] = ( (x<0.1)*1.e3 + (0.1<=x)*(x<0.9)*1.e-2 + (0.9<=x)*1.e2 ) / gamma1

    claw = pyclaw.Controller()
    claw.tfinal = 0.038
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.num_output_times = 10
    claw.outdir = outdir
    claw.setplot = setplot
    claw.keep_copy = True

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='Density', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    #plotaxes.xlimits = [-5.0,5.0]
    #plotaxes.ylimits = [0,4.0]
    plotaxes.title = 'Density'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    
    # Figure for q[1]
    plotfigure = plotdata.new_plotfigure(name='Energy', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Energy'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d')
    plotitem.plot_var = 2
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    
    return plotdata

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = euler_2d
#!/usr/bin/env python
# encoding: utf-8

"""
2D compressible flow
================================

Solve the Euler equations of compressible fluid dynamics:

.. math::
    \rho_t + (\rho u)_x + (\rho v)_y & = 0 \\
    (\rho u)_t + (\rho u^2 + p)_x + (\rho uv)_y & = 0 \\
    (\rho v)_t + (\rho uv)_x + (\rho v^2 + p)_y & = 0 \\
    E_t + (u (E + p) )_x + (v (E + p))_y & = 0.

Here h is the depth, (u,v) is the velocity, and g is the gravitational constant.
"""
from clawpack import pyclaw
from clawpack import riemann

solver = pyclaw.ClawSolver2D(riemann.euler_4wave_2D)
solver.all_bcs = pyclaw.BC.extrap

domain = pyclaw.Domain([0.,0.],[1.,1.],[200,200])
solution = pyclaw.Solution(solver.num_eqn,domain)
gamma = 1.4
solution.problem_data['gamma']  = gamma

# Set initial data
xx,yy = domain.grid.p_centers
l = xx<0.5; r = xx>=0.5; b = yy<0.5; t = yy>=0.5
solution.q[0,...] = 2.*l*t + 1.*l*b + 1.*r*t + 3.*r*b
solution.q[1,...] = 0.75*t - 0.75*b
solution.q[2,...] = 0.5*l  - 0.5*r
solution.q[3,...] = 0.5*solution.q[0,...]*(solution.q[1,...]**2+solution.q[2,...]**2) + 1./(gamma-1.)

claw = pyclaw.Controller()
claw.tfinal = 0.3
claw.solution = solution
claw.solver = solver

status = claw.run()

#plot_results()

def load_frame(frame_number):
    from clawpack.pyclaw import Solution

    return Solution(frame_number)

def plot_frame(frame):
    import matplotlib.pyplot as plt
    q = frame.q
    x, y = frame.state.grid.c_centers
    plt.pcolormesh(x, y, q[0,...])

def plot_results():
    from clawpack.visclaw import iplot
    ip = iplot.Iplot(load_frame,plot_frame)
    ip.plotloop()

########NEW FILE########
__FILENAME__ = quadrants
#!/usr/bin/env python
# encoding: utf-8

"""
Solve the Euler equations of compressible fluid dynamics.
"""
from clawpack import pyclaw
from clawpack import riemann

solver = pyclaw.ClawSolver2D(riemann.euler_4wave_2D)
solver.all_bcs = pyclaw.BC.extrap

domain = pyclaw.Domain([0.,0.],[1.,1.],[100,100])
solution = pyclaw.Solution(solver.num_eqn,domain)
gamma = 1.4
solution.problem_data['gamma']  = gamma
solver.dimensional_split = False
solver.transverse_waves = 2

# Set initial data
xx,yy = domain.grid.p_centers
l = xx<0.8; r = xx>=0.8; b = yy<0.8; t = yy>=0.8
solution.q[0,...] = 1.5*r*t + 0.532258064516129*l*t + 0.137992831541219*l*b + 0.532258064516129*r*b
u = 0.*r*t + 1.206045378311055*l*t + 1.206045378311055*l*b + 0.*r*b
v = 0.*r*t + 0.*l*t + 1.206045378311055*l*b + 1.206045378311055*r*b
p = 1.5*r*t + 0.3*l*t + 0.029032258064516*l*b + 0.3*r*b
solution.q[1,...] = solution.q[0,...] * u
solution.q[2,...] = solution.q[0,...] * v
solution.q[3,...] = 0.5*solution.q[0,...]*(u**2+v**2) + p/(gamma-1.)

#solver.evolve_to_time(solution,tend=0.3)
claw = pyclaw.Controller()
claw.tfinal = 0.8
claw.solution = solution
claw.solver = solver

status = claw.run()

#pyclaw.plot.interactive_plot()

########NEW FILE########
__FILENAME__ = shockbubble_scipy
#!/usr/bin/env python
# encoding: utf-8

import numpy as np
from scipy import integrate

gamma = 1.4
gamma1 = gamma - 1.
x0=0.5; y0=0.; r0=0.2
xshock = 0.2
pinf=5.

def inrad(y,x):
    return (np.sqrt((x-x0)**2+(y-y0)**2)<r0)

def ycirc(x,ymin,ymax):
    if r0**2>((x-x0)**2):
        return max(min(y0 + np.sqrt(r0**2-(x-x0)**2),ymax) - ymin,0.)
    else:
        return 0

def qinit(state,rhoin=0.1,bubble_shape='circle'):
    r"""
    Initialize data with a shock at x=xshock and a low-density bubble (of density rhoin)
    centersed at (x0,y0) with radius r0.
    """
    rhoout = 1.
    pout   = 1.
    pin    = 1.

    rinf = (gamma1 + pinf*(gamma+1.))/ ((gamma+1.) + gamma1*pinf)
    vinf = 1./np.sqrt(gamma) * (pinf - 1.) / np.sqrt(0.5*((gamma+1.)/gamma) * pinf+0.5*gamma1/gamma)
    einf = 0.5*rinf*vinf**2 + pinf/gamma1
    
    x =state.grid.x.centers
    y =state.grid.y.centers
    Y,X = np.meshgrid(y,x)
    if bubble_shape=='circle':
        r = np.sqrt((X-x0)**2 + (Y-y0)**2)
    elif bubble_shape=='rectangle':
        z = np.dstack((np.abs(X-x0),np.abs(Y-y0)))
        r = np.max(z,axis=2)
    elif bubble_shape=='triangle':
        r = np.abs(X-x0) + np.abs(Y-y0)

    #First set the values for the cells that don't intersect the bubble boundary
    state.q[0,:,:] = rinf*(X<xshock) + rhoin*(r<=r0) + rhoout*(r>r0)*(X>xshock)
    state.q[1,:,:] = rinf*vinf*(X<xshock)
    state.q[2,:,:] = 0.
    state.q[3,:,:] = einf*(X<xshock) + (pin*(r<=r0) + pout*(r>r0)*(X>xshock))/gamma1
    state.q[4,:,:] = 1.*(r<=r0)

    #Now average for the cells on the edges of the bubble
    d2 = np.linalg.norm(state.grid.delta)/2.
    dx = state.grid.delta[0]
    dy = state.grid.delta[1]
    dx2 = state.grid.delta[0]/2.
    dy2 = state.grid.delta[1]/2.
    for i in xrange(state.q.shape[1]):
        for j in xrange(state.q.shape[2]):
            ydown = y[j]-dy2
            yup   = y[j]+dy2
            if abs(r[i,j]-r0)<d2:
                infrac,abserr = integrate.quad(ycirc,x[i]-dx2,x[i]+dx2,args=(ydown,yup),epsabs=1.e-8,epsrel=1.e-5)
                infrac=infrac/(dx*dy)
                state.q[0,i,j] = rhoin*infrac + rhoout*(1.-infrac)
                state.q[3,i,j] = (pin*infrac + pout*(1.-infrac))/gamma1
                state.q[4,i,j] = 1.*infrac


def auxinit(state):
    """
    aux[0,i,j] = y-coordinate of cell centers for cylindrical source terms
    """
    y=state.grid.y.centers
    for j,ycoord in enumerate(y):
        state.aux[0,:,j] = ycoord


def shockbc(state,dim,t,qbc,num_ghost):
    """
    Incoming shock at left boundary.
    """
    rinf = (gamma1 + pinf*(gamma+1.))/ ((gamma+1.) + gamma1*pinf)
    vinf = 1./np.sqrt(gamma) * (pinf - 1.) / np.sqrt(0.5*((gamma+1.)/gamma) * pinf+0.5*gamma1/gamma)
    einf = 0.5*rinf*vinf**2 + pinf/gamma1

    for i in xrange(num_ghost):
        qbc[0,i,...] = rinf
        qbc[1,i,...] = rinf*vinf
        qbc[2,i,...] = 0.
        qbc[3,i,...] = einf
        qbc[4,i,...] = 0.

def dq_Euler_radial(solver,state,dt):
    """
    Geometric source terms for Euler equations with radial symmetry.
    Integrated using a 2-stage, 2nd-order Runge-Kutta method.
    This is a SharpClaw-style source term routine.
    """
    
    ndim = 2

    q   = state.q
    aux = state.aux

    rad = aux[0,:,:]

    rho = q[0,:,:]
    u   = q[1,:,:]/rho
    v   = q[2,:,:]/rho
    press  = gamma1 * (q[3,:,:] - 0.5*rho*(u**2 + v**2))

    dq = np.empty(q.shape)

    dq[0,:,:] = -dt*(ndim-1)/rad * q[2,:,:]
    dq[1,:,:] = -dt*(ndim-1)/rad * rho*u*v
    dq[2,:,:] = -dt*(ndim-1)/rad * rho*v*v
    dq[3,:,:] = -dt*(ndim-1)/rad * v * (q[3,:,:] + press)
    dq[4,:,:] = 0

    return dq

def step_Euler_radial(solver,state,dt):
    """
    Geometric source terms for Euler equations with radial symmetry.
    Integrated using a 2-stage, 2nd-order Runge-Kutta method.
    This is a Clawpack-style source term routine.
    """
    
    dt2 = dt/2.
    ndim = 2

    aux=state.aux
    q = state.q

    rad = aux[0,:,:]

    rho = q[0,:,:]
    u   = q[1,:,:]/rho
    v   = q[2,:,:]/rho
    press  = gamma1 * (q[3,:,:] - 0.5*rho*(u**2 + v**2))

    qstar = np.empty(q.shape)

    qstar[0,:,:] = q[0,:,:] - dt2*(ndim-1)/rad * q[2,:,:]
    qstar[1,:,:] = q[1,:,:] - dt2*(ndim-1)/rad * rho*u*v
    qstar[2,:,:] = q[2,:,:] - dt2*(ndim-1)/rad * rho*v*v
    qstar[3,:,:] = q[3,:,:] - dt2*(ndim-1)/rad * v * (q[3,:,:] + press)

    rho = qstar[0,:,:]
    u   = qstar[1,:,:]/rho
    v   = qstar[2,:,:]/rho
    press  = gamma1 * (qstar[3,:,:] - 0.5*rho*(u**2 + v**2))

    q[0,:,:] = q[0,:,:] - dt*(ndim-1)/rad * qstar[2,:,:]
    q[1,:,:] = q[1,:,:] - dt*(ndim-1)/rad * rho*u*v
    q[2,:,:] = q[2,:,:] - dt*(ndim-1)/rad * rho*v*v
    q[3,:,:] = q[3,:,:] - dt*(ndim-1)/rad * v * (qstar[3,:,:] + press)


def shockbubble(use_petsc=False,outdir='./_output',solver_type='classic'):
    """
    Solve the Euler equations of compressible fluid dynamics.
    This example involves a bubble of dense gas that is impacted by a shock.
    """
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver2D(riemann.euler_5wave_2D)
        solver.dq_src=dq_Euler_radial
        solver.weno_order=5
        solver.lim_type=2
    else:
        solver = pyclaw.ClawSolver2D(riemann.euler_5wave_2D)
        solver.dimensional_split = 0
        solver.transverse_waves = 2
        solver.limiters = [4,4,4,4,2]
        solver.step_source=step_Euler_radial

    solver.bc_lower[0]=pyclaw.BC.custom
    solver.bc_upper[0]=pyclaw.BC.extrap
    solver.bc_lower[1]=pyclaw.BC.wall
    solver.bc_upper[1]=pyclaw.BC.extrap

    #Aux variable in ghost cells doesn't matter
    solver.aux_bc_lower[0]=pyclaw.BC.extrap
    solver.aux_bc_upper[0]=pyclaw.BC.extrap
    solver.aux_bc_lower[1]=pyclaw.BC.extrap
    solver.aux_bc_upper[1]=pyclaw.BC.extrap

    # Initialize domain
    mx=160; my=40
    x = pyclaw.Dimension('x',0.0,2.0,mx)
    y = pyclaw.Dimension('y',0.0,0.5,my)
    domain = pyclaw.Domain([x,y])
    num_eqn = 5
    num_aux=1
    state = pyclaw.State(domain,num_eqn,num_aux)

    state.problem_data['gamma']= gamma
    state.problem_data['gamma1']= gamma1

    qinit(state)
    auxinit(state)

    solver.user_bc_lower=shockbc

    claw = pyclaw.Controller()
    claw.tfinal = 0.75
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.num_output_times = 10
    claw.outdir = outdir

    return claw


if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    from clawpack.pyclaw.examples import shock_bubble_interaction
    output = run_app_from_main(shockbubble,shock_bubble_interaction.setplot)

########NEW FILE########
__FILENAME__ = shock_bubble_interaction
#!/usr/bin/env python
# encoding: utf-8

import numpy as np

gamma = 1.4
gamma1 = gamma - 1.
x0=0.5; y0=0.; r0=0.2
xshock = 0.2


def ycirc(x,ymin,ymax):
    if ((x-x0)**2)<(r0**2):
        return max(min(y0 + np.sqrt(r0**2-(x-x0)**2),ymax) - ymin,0.)
    else:
        return 0

def qinit(state,x0=0.5,y0=0.,r0=0.2,rhoin=0.1,pinf=5.):
    from scipy import integrate

    grid = state.grid

    rhoout = 1.
    pout   = 1.
    pin    = 1.

    rinf = (gamma1 + pinf*(gamma+1.))/ ((gamma+1.) + gamma1*pinf)
    vinf = 1./np.sqrt(gamma) * (pinf - 1.) / np.sqrt(0.5*((gamma+1.)/gamma) * pinf+0.5*gamma1/gamma)
    einf = 0.5*rinf*vinf**2 + pinf/gamma1
    
    # Create an array with fortran native ordering
    x =grid.x.centers
    y =grid.y.centers
    Y,X = np.meshgrid(y,x)
    r = np.sqrt((X-x0)**2 + (Y-y0)**2)

    state.q[0,:,:] = rinf*(X<xshock) + rhoin*(r<=r0) + rhoout*(r>r0)*(X>=xshock)
    state.q[1,:,:] = rinf*vinf*(X<xshock)
    state.q[2,:,:] = 0.
    state.q[3,:,:] = einf*(X<xshock) + (pin*(r<=r0) + pout*(r>r0)*(X>=xshock))/gamma1
    state.q[4,:,:] = 1.*(r<=r0)

    #Now average for the cells on the edge of the bubble
    d2 = np.linalg.norm(state.grid.delta)/2.
    dx = state.grid.delta[0]
    dy = state.grid.delta[1]
    dx2 = state.grid.delta[0]/2.
    dy2 = state.grid.delta[1]/2.
    for i in xrange(state.q.shape[1]):
        for j in xrange(state.q.shape[2]):
            ydown = y[j]-dy2
            yup   = y[j]+dy2
            if abs(r[i,j]-r0)<d2:
                infrac,abserr = integrate.quad(ycirc,x[i]-dx2,x[i]+dx2,args=(ydown,yup),epsabs=1.e-8,epsrel=1.e-5)
                infrac=infrac/(dx*dy)
                state.q[0,i,j] = rhoin*infrac + rhoout*(1.-infrac)
                state.q[3,i,j] = (pin*infrac + pout*(1.-infrac))/gamma1
                state.q[4,i,j] = 1.*infrac

def auxinit(state):
    """
    aux[1,i,j] = y-coordinate of cell centers for cylindrical source terms
    """
    x=state.grid.x.centers
    y=state.grid.y.centers
    for j,ycoord in enumerate(y):
        state.aux[0,:,j] = ycoord

def shockbc(state,dim,t,qbc,num_ghost):
    """
    Incoming shock at left boundary.
    """
    for (i,state_dim) in enumerate(state.patch.dimensions):
        if state_dim.name == dim.name:
            dim_index = i
            break
      
    pinf=5.
    rinf = (gamma1 + pinf*(gamma+1.))/ ((gamma+1.) + gamma1*pinf)
    vinf = 1./np.sqrt(gamma) * (pinf - 1.) / np.sqrt(0.5*((gamma+1.)/gamma) * pinf+0.5*gamma1/gamma)
    einf = 0.5*rinf*vinf**2 + pinf/gamma1

    for i in xrange(num_ghost):
        qbc[0,i,...] = rinf
        qbc[1,i,...] = rinf*vinf
        qbc[2,i,...] = 0.
        qbc[3,i,...] = einf
        qbc[4,i,...] = 0.

def step_Euler_radial(solver,state,dt):
    """
    Geometric source terms for Euler equations with radial symmetry.
    Integrated using a 2-stage, 2nd-order Runge-Kutta method.
    This is a Clawpack-style source term routine.
    """
    
    dt2 = dt/2.
    ndim = 2

    aux=state.aux
    q = state.q

    rad = aux[0,:,:]

    rho = q[0,:,:]
    u   = q[1,:,:]/rho
    v   = q[2,:,:]/rho
    press  = gamma1 * (q[3,:,:] - 0.5*rho*(u**2 + v**2))

    qstar = np.empty(q.shape)

    qstar[0,:,:] = q[0,:,:] - dt2*(ndim-1)/rad * q[2,:,:]
    qstar[1,:,:] = q[1,:,:] - dt2*(ndim-1)/rad * rho*u*v
    qstar[2,:,:] = q[2,:,:] - dt2*(ndim-1)/rad * rho*v*v
    qstar[3,:,:] = q[3,:,:] - dt2*(ndim-1)/rad * v * (q[3,:,:] + press)

    rho = qstar[0,:,:]
    u   = qstar[1,:,:]/rho
    v   = qstar[2,:,:]/rho
    press  = gamma1 * (qstar[3,:,:] - 0.5*rho*(u**2 + v**2))

    q[0,:,:] = q[0,:,:] - dt*(ndim-1)/rad * qstar[2,:,:]
    q[1,:,:] = q[1,:,:] - dt*(ndim-1)/rad * rho*u*v
    q[2,:,:] = q[2,:,:] - dt*(ndim-1)/rad * rho*v*v
    q[3,:,:] = q[3,:,:] - dt*(ndim-1)/rad * v * (qstar[3,:,:] + press)


def dq_Euler_radial(solver,state,dt):
    """
    Geometric source terms for Euler equations with radial symmetry.
    Integrated using a 2-stage, 2nd-order Runge-Kutta method.
    This is a SharpClaw-style source term routine.
    """
    
    ndim = 2

    q   = state.q
    aux = state.aux

    rad = aux[0,:,:]

    rho = q[0,:,:]
    u   = q[1,:,:]/rho
    v   = q[2,:,:]/rho
    press  = gamma1 * (q[3,:,:] - 0.5*rho*(u**2 + v**2))

    dq = np.empty(q.shape)

    dq[0,:,:] = -dt*(ndim-1)/rad * q[2,:,:]
    dq[1,:,:] = -dt*(ndim-1)/rad * rho*u*v
    dq[2,:,:] = -dt*(ndim-1)/rad * rho*v*v
    dq[3,:,:] = -dt*(ndim-1)/rad * v * (q[3,:,:] + press)
    dq[4,:,:] = 0

    return dq

def setup(use_petsc=False,kernel_language='Fortran',solver_type='classic',
          outdir='_output', disable_output=False, mx=320, my=80, tfinal=0.6,
          num_output_times = 10):
    """
    Solve the Euler equations of compressible fluid dynamics.
    This example involves a bubble of dense gas that is impacted by a shock.
    """
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if kernel_language != 'Fortran':
        raise Exception('Unrecognized value of kernel_language for Euler Shockbubble')

    
    if solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver2D(riemann.euler_5wave_2D)
        solver.dq_src=dq_Euler_radial
        solver.weno_order=5
        solver.lim_type=2
    else:
        solver = pyclaw.ClawSolver2D(riemann.euler_5wave_2D)
        solver.limiters = [4,4,4,4,2]
        solver.step_source=step_Euler_radial

    # Initialize domain
    x = pyclaw.Dimension('x',0.0,2.0,mx)
    y = pyclaw.Dimension('y',0.0,0.5,my)
    domain = pyclaw.Domain([x,y])

    num_aux=1
    state = pyclaw.State(domain,solver.num_eqn,num_aux)
    state.problem_data['gamma']= gamma
    state.problem_data['gamma1']= gamma1

    qinit(state)
    auxinit(state)

    solver.cfl_max = 0.5
    solver.cfl_desired = 0.45
    solver.dt_initial=0.005
    solver.user_bc_lower=shockbc
    solver.source_split = 1
    solver.bc_lower[0]=pyclaw.BC.custom
    solver.bc_upper[0]=pyclaw.BC.extrap
    solver.bc_lower[1]=pyclaw.BC.wall
    solver.bc_upper[1]=pyclaw.BC.extrap
    #Aux variable in ghost cells doesn't matter
    solver.aux_bc_lower[0]=pyclaw.BC.extrap
    solver.aux_bc_upper[0]=pyclaw.BC.extrap
    solver.aux_bc_lower[1]=pyclaw.BC.extrap
    solver.aux_bc_upper[1]=pyclaw.BC.extrap

    claw = pyclaw.Controller()
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver

    claw.keep_copy = True
    if disable_output:
        claw.output_format = None
    claw.tfinal = tfinal
    claw.num_output_times = num_output_times
    claw.outdir = outdir
    claw.setplot = setplot

    return claw

    
#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data
    
    # Pressure plot
    plotfigure = plotdata.new_plotfigure(name='Density', figno=0)

    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Density'
    plotaxes.scaled = True      # so aspect ratio is 1
    plotaxes.afteraxes = label_axes

    plotitem = plotaxes.new_plotitem(plot_type='2d_schlieren')
    plotitem.plot_var = 0
    plotitem.add_colorbar = False
    

    # Tracer plot
    plotfigure = plotdata.new_plotfigure(name='Tracer', figno=1)

    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Tracer'
    plotaxes.scaled = True      # so aspect ratio is 1
    plotaxes.afteraxes = label_axes

    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.pcolor_cmin = 0.
    plotitem.pcolor_cmax=1.0
    plotitem.plot_var = 4
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = False
    

    # Energy plot
    plotfigure = plotdata.new_plotfigure(name='Energy', figno=2)

    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Energy'
    plotaxes.scaled = True      # so aspect ratio is 1
    plotaxes.afteraxes = label_axes

    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.pcolor_cmin = 2.
    plotitem.pcolor_cmax=18.0
    plotitem.plot_var = 3
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = False
    
    return plotdata

def label_axes(current_data):
    import matplotlib.pyplot as plt
    plt.xlabel('z')
    plt.ylabel('r')
    

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)


########NEW FILE########
__FILENAME__ = test_euler2d_shockbubble
def test_2d_euler_shockbubble():
    """test_2d_euler_shockbubble"""
    def verify_classic_shockbubble(controller):
        """ verifies 2d euler shockbubble from a previously verified classic run """

        import os
        from clawpack.pyclaw.util import check_diff
        import numpy as np

        test_q=controller.solution.state.get_q_global()


        if test_q != None:
            thisdir = os.path.dirname(__file__)
            expected_density = np.loadtxt(os.path.join(thisdir,'verify_shockbubble_classic.txt'))
            test_density = test_q[0,:,:]
            test_err = np.linalg.norm(expected_density-test_density)
            expected_err = 0
            return check_diff(expected_err, test_err, abstol=1e-12)

    try:
        import scipy
    except ImportError:
        from nose import SkipTest
        raise SkipTest("Unable to import scipy, is it installed?")

    import shock_bubble_interaction
    
    from clawpack.pyclaw.util import gen_variants
    for test in gen_variants(shock_bubble_interaction.setup, verify_classic_shockbubble, 
                             kernel_languages=('Fortran',),
                             solver_type='classic', disable_output=True,
                             mx=160, my=40, tfinal=0.2, num_output_times=1):
        yield test

########NEW FILE########
__FILENAME__ = iso_c_advection
import ctypes
import os.path

class iso_c_rp1_advection():

    def __init__(self, u):
        this_path = os.path.dirname(__file__)
        self._dll = ctypes.CDLL(os.path.join(this_path, '_iso_c_advection.so'))
        self.context = ctypes.c_void_p()
        self._u = ctypes.c_double(u)
        self._dll.rp1_advection_new(ctypes.byref(self._u),
                                   ctypes.byref(self.context))
        self.num_eqn = 1
        self.num_waves = 1
        self._rp = self._dll.rp1_advection_c

    def __del__(self):
        self._dll.rp1_advection_delete(ctypes.byref(self.context))

########NEW FILE########
__FILENAME__ = iso_c_solver
import ctypes
import os.path
import numpy as np

from clawpack.pyclaw import ClawSolver1D

class iso_c_step1():

    def __init__(self):
        this_path = os.path.dirname(__file__)
        self._dll = ctypes.CDLL(os.path.join(this_path, 'iso_c_classic1.so'))

        # work arrays
        self.allocated = False
        self._f = None
        self._wave = None
        self._s = None
        self._amdq = None
        self._apdq = None
        self._dtdx = None

    def allocate(self, mx, num_eqn, num_ghost, num_waves):

        # these are work arrays, so order doesn't really matter
        self._f = np.empty((2*num_ghost + mx, num_eqn), dtype=np.double)
        self._wave = np.empty((num_eqn, num_waves, 2*num_ghost + mx),
                              dtype=np.double)
        self._s = np.empty((num_waves, 2*num_ghost+mx), dtype=np.double)
        self._amdq = np.empty((num_eqn, 2*num_ghost + mx), dtype=np.double)
        self._apdq = np.empty((num_eqn, 2*num_ghost + mx), dtype=np.double)
        self._dtdx = np.empty((2*num_ghost + mx), dtype=np.double)
        self.allocated = True

    def step1(self,
              py_num_ghost,
              py_mx,
              qbc,
              auxbc,
              py_dx,
              py_dt,
              method,
              mthlim,
              fwave,
              rp):
        r"""
        Take one time step on the homogeneous hyperbolic system.

        This function directly wraps the Clawpack step1 call, and is responsible
        for translating Pythonic data structures into their C/Fortran
        equivalents.
        """

        from ctypes import c_int, c_double, c_bool, byref

        # a real solver object would be caching/verifying these values, this is
        # just scaffolding

        py_num_eqn, mxbc = qbc.shape
        num_eqn = c_int(py_num_eqn)

        mthlim = np.asarray(mthlim, dtype=np.int)
        py_num_waves = mthlim.shape[0]
        num_waves = c_int(py_num_waves)

        py_num_aux, mxauxbc = auxbc.shape
        num_aux = c_int(py_num_aux)

        cfl = c_double()
        use_fwave = c_bool(False)

        num_ghost = c_int(py_num_ghost)
        mx = c_int(py_mx)

        dx = c_double(py_dx)
        dt = c_double(py_dt)

        if not self.allocated:
            self.allocate(py_mx, py_num_eqn, py_num_ghost, py_num_waves)


        def to_double_ref(nparray):
            return nparray.ctypes.data_as(ctypes.POINTER(ctypes.c_double))


        def to_int_ref(nparray):
            return nparray.ctypes.data_as(ctypes.POINTER(ctypes.c_int))


        self._dll.step1_c(byref(num_eqn),
                          byref(num_waves),
                          byref(num_ghost),
                          byref(num_aux),
                          byref(mx),
                          to_double_ref(qbc),
                          to_double_ref(auxbc),
                          byref(dx),
                          byref(dt),
                          to_int_ref(method),
                          to_int_ref(mthlim),
                          byref(cfl),
                          to_double_ref(self._f),
                          to_double_ref(self._wave),
                          to_double_ref(self._s),
                          to_double_ref(self._amdq),
                          to_double_ref(self._apdq),
                          to_double_ref(self._dtdx),
                          byref(use_fwave),
                          byref(rp._rp),
                          byref(rp.context))


        return qbc, cfl.value


class ISO_C_ClawSolver1D(ClawSolver1D):

    def __init__(self,riemann_solver=None,claw_package=None):
        r"""
        Create 1d ISO C Clawpack solver

        See :class:`ClawSolver1D` for more info.
        """

        self.iso_c_step1 = iso_c_step1()


        super(ISO_C_ClawSolver1D,self).__init__(riemann_solver,claw_package)


    def step_hyperbolic(self,solution):
        r"""
        Take one time step on the homogeneous hyperbolic system.

        :Input:
        - *solution* - (:class:`~pyclaw.solution.Solution`) Solution that
        will be evolved
        """

        state = solution.states[0]
        grid = state.grid

        self._apply_q_bcs(state)
        if state.num_aux > 0:
            self._apply_aux_bcs(state)

        num_eqn,num_ghost = state.num_eqn,self.num_ghost

        mx = grid.num_cells[0]
        dx,dt = grid.delta[0],self.dt
        dtdx = np.zeros( (mx+2*num_ghost) ) + dt/dx

        self.qbc,cfl = self.iso_c_step1.step1(num_ghost, mx, self.qbc,
                                              self.auxbc, dx, dt, self._method,
                                              self._mthlim,self.fwave,
                                              self.rp)
        self.cfl.update_global_max(cfl)
        state.set_q_from_qbc(num_ghost,self.qbc)


        if state.num_aux > 0:
            state.set_aux_from_auxbc(num_ghost,self.auxbc)

########NEW FILE########
__FILENAME__ = kpp
#!/usr/bin/env python
# encoding: utf-8
r"""
A non-convex flux scalar model
==============================

Solve the equation:

.. math:: 
    q_t + (\sin(q))_x + (\cos(q))_y & = 0

first proposed by Kurganov, Petrova, and Popov.  It is challenging for schemes
with low numerical viscosity to capture the solution accurately.
"""
import numpy as np

def qinit(state,rad=1.0):
    x = state.grid.x.centers
    y = state.grid.y.centers
    Y,X = np.meshgrid(y,x)
    r = np.sqrt(X**2 + Y**2)

    state.q[0,:,:] = 0.25*np.pi + 3.25*np.pi*(r<=rad)


def setup(use_petsc=False,outdir='./_output',solver_type='classic'):
    """
    Example python script for solving the 2d KPP equations.
    """
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver2D(riemann.kpp_2D)
    else:
        solver = pyclaw.ClawSolver2D(riemann.kpp_2D)

    solver.bc_lower[0]=pyclaw.BC.extrap
    solver.bc_upper[0]=pyclaw.BC.extrap
    solver.bc_lower[1]=pyclaw.BC.extrap
    solver.bc_upper[1]=pyclaw.BC.extrap

    # Initialize domain
    mx=200; my=200
    x = pyclaw.Dimension('x',-2.0,2.0,mx)
    y = pyclaw.Dimension('y',-2.0,2.0,my)
    domain = pyclaw.Domain([x,y])
    state = pyclaw.State(domain,solver.num_eqn)

    qinit(state)

    solver.dimensional_split = 1
    solver.cfl_max = 1.0
    solver.cfl_desired = 0.9
    solver.limiters = pyclaw.limiters.tvd.minmod

    claw = pyclaw.Controller()
    claw.tfinal = 1.0
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.num_output_times = 10
    claw.setplot = setplot
    claw.keep_copy = True

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for pcolor plot
    plotfigure = plotdata.new_plotfigure(name='q[0]', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'q[0]'
    plotaxes.afteraxes = "pylab.axis('scaled')" 

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 0
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.pcolor_cmin = 0.0
    plotitem.pcolor_cmax = 3.5*3.14
    plotitem.add_colorbar = True
    
    # Figure for contour plot
    plotfigure = plotdata.new_plotfigure(name='contour', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'q[0]'
    plotaxes.afteraxes = "pylab.axis('scaled')" 

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_contour')
    plotitem.plot_var = 0
    plotitem.contour_nlevels = 20
    plotitem.contour_min = 0.01
    plotitem.contour_max = 3.5*3.15
    plotitem.amr_contour_colors = ['b','k','r']
    
    return plotdata


if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = setplot

""" 
Set up the plot figures, axes, and items to be done for each frame.

This module is imported by the plotting routines and then the
function setplot is called to set the plot parameters.
    
""" 

#--------------------------
def setplot(plotdata):
#--------------------------
    
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    
    """ 


    from visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data
    

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='Water height', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = 'auto'
    plotaxes.title = 'Water height'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 0
    plotitem.pcolor_cmap = colormaps.red_yellow_blue
    plotitem.pcolor_cmin = 0.5
    plotitem.pcolor_cmax = 1.5
    plotitem.add_colorbar = True
    plotitem.show = True       # show on plot?
    

    # Scatter plot of q[0]
    plotfigure = plotdata.new_plotfigure(name='Scatter plot of h', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = [0., 2.5]
    plotaxes.ylimits = [0., 2.1]
    plotaxes.title = 'Scatter plot of h'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_from_2d_data')
    plotitem.plot_var = 0
    def q_vs_radius(current_data):
        from numpy import sqrt
        x = current_data.x
        y = current_data.y
        r = sqrt(x**2 + y**2)
        q = current_data.q[0,:,:]
        return r,q
    plotitem.map_2d_to_1d = q_vs_radius
    plotitem.plotstyle = 'o'


    # Figure for q[1]
    plotfigure = plotdata.new_plotfigure(name='Momentum in x direction', figno=2)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = [-2.5, 2.5]
    plotaxes.ylimits = [-2.5, 2.5]
    plotaxes.title = 'Momentum in x direction'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 1
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True
    plotitem.show = False       # show on plot?
    

    # Figure for q[2]
    plotfigure = plotdata.new_plotfigure(name='Momentum in y direction', figno=3)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = [-2.5, 2.5]
    plotaxes.ylimits = [-2.5, 2.5]
    plotaxes.title = 'Momentum in y direction'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 2
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True
    plotitem.show = False       # show on plot?
    
    return plotdata

########NEW FILE########
__FILENAME__ = shallow2D
#!/usr/bin/env python
# encoding: utf-8

"""
2D shallow water equations.
"""
#===========================================================================
# Import libraries
#===========================================================================

import numpy as np
#from petclaw import plot
#import pdb  # Debugger

def init(state):
    # Initial solution
    # ================
    # Riemann states of the dam break problem
    radDam = 0.2
    hl = 2.
    ul = 0.
    vl = 0.
    hr = 1.
    ur = 0.
    vr = 0.
    
    x0=0.5
    y0=0.5
    xCenter = state.grid.x.centers
    yCenter = state.grid.y.centers
    
    Y,X = np.meshgrid(yCenter,xCenter)
    r = np.sqrt((X-x0)**2 + (Y-y0)**2)
    state.q[0,:,:] = hl*(r<=radDam) + hr*(r>radDam)
    state.q[1,:,:] = hl*ul*(r<=radDam) + hr*ur*(r>radDam)
    state.q[2,:,:] = hl*vl*(r<=radDam) + hr*vr*(r>radDam)


    
def shallow2D(use_petsc=False,outdir='./_output',solver_type='classic', disable_output=False):
    #===========================================================================
    # Import libraries
    #===========================================================================
    import numpy as np
    import clawpack.peanoclaw as peanoclaw
    import clawpack.riemann as riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        import clawpack.pyclaw as pyclaw

    #===========================================================================
    # Setup solver and solver parameters
    #===========================================================================
    subdivisionFactor = 6
    if solver_type == 'classic':
        solver = pyclaw.ClawSolver2D(riemann.shallow_roe_with_efix_2D)
        solver.limiters = pyclaw.limiters.tvd.MC
        solver.dimensional_split=1
    elif solver_type == 'sharpclaw':
        solver = pyclaw.SharpClawSolver2D(riemann.shallow_roe_with_efix_2D)
    peanoSolver = peanoclaw.Solver(solver, (1./3.)/subdivisionFactor, init)
    
    solver.dt_initial = 1.0

    solver.bc_lower[0] = pyclaw.BC.wall
    solver.bc_upper[0] = pyclaw.BC.wall
    solver.bc_lower[1] = pyclaw.BC.wall
    solver.bc_upper[1] = pyclaw.BC.wall
    
    #===========================================================================
    # Initialize domain and state, then initialize the solution associated to the 
    # state and finally initialize aux array
    #===========================================================================

    # Domain:
    from clawpack.pyclaw import geometry
    print(geometry.__file__)
    xlower = 0.0
    xupper = 1.0
    mx = subdivisionFactor
    ylower = 0.0
    yupper = 1.0
    my = subdivisionFactor
    x = pyclaw.Dimension('x',xlower,xupper,mx)
    y = pyclaw.Dimension('y',ylower,yupper,my)
    domain = geometry.Domain([x,y])

    num_eqn = 3  # Number of equations
    state = pyclaw.State(domain,num_eqn)

    grav = 1.0 # Parameter (global auxiliary variable)
    state.problem_data['grav'] = grav
    
    #===========================================================================
    # Set up controller and controller parameters
    #===========================================================================
    claw = pyclaw.Controller()
    claw.tfinal = 0.1
    claw.solution = peanoclaw.solution.Solution(state,domain)
    claw.solver = peanoSolver
    claw.outdir = outdir
    if disable_output:
        claw.output_format = None
    claw.num_output_times = 5

    return claw


if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(shallow2D)
    print 'Error: ', output






########NEW FILE########
__FILENAME__ = test_identical_grids
from nose.plugins.attrib import attr

if __name__=="__main__":
    import nose
    nose.main()
    
    
def qinit(state,hl,ul,vl,hr,ur,vr,radDam):
    import numpy as np
    x0=0.5
    y0=0.5
    xCenter = state.grid.x.centers
    yCenter = state.grid.y.centers
    Y,X = np.meshgrid(yCenter,xCenter)
    r = np.sqrt((X-x0)**2 + (Y-y0)**2)
    state.q[0,:,:] = hl*(r<=radDam) + hr*(r>radDam)
    state.q[1,:,:] = hl*ul*(r<=radDam) + hr*ur*(r>radDam)
    state.q[2,:,:] = hl*vl*(r<=radDam) + hr*vr*(r>radDam)
    
def setup_solver():
    import pyclaw
    import peanoclaw
    solver = pyclaw.ClawSolver2D()
    solver.limiters = pyclaw.limiters.tvd.MC
    solver.dimensional_split=1

    import riemann
    solver.rp = riemann.rp2_shallow_roe_with_efix
    solver.num_waves = 3

    solver.bc_lower[0] = pyclaw.BC.extrap
    solver.bc_upper[0] = pyclaw.BC.extrap
    solver.bc_lower[1] = pyclaw.BC.wall
    solver.bc_upper[1] = pyclaw.BC.wall
    
    return solver

@attr(petsc=False)
@attr(peanoclaw=True)
def test_3x3_grid():
    r"""This test simply solves a 3x3 grid, once with PyClaw and once as one patch 
    with PeanoClaw. In the end it checks if the resulting qbcs match.
    """
    #===========================================================================
    # Import libraries
    #===========================================================================
    import numpy as np
    import pyclaw
    import peanoclaw

    #===========================================================================
    # Setup solver and solver parameters for PyClaw run
    #===========================================================================
    pyclaw_solver = setup_solver()
    
    #===========================================================================
    # Setup solver and solver parameters for PeanoClaw run
    #===========================================================================
    peanoclaw_solver = setup_solver()
    peano_solver = peanoclaw.Solver(peanoclaw_solver, 1.0)

    #===========================================================================
    # Initialize domain and state, then initialize the solution associated to the 
    # state and finally initialize aux array
    #===========================================================================

    # Domain:
    xlower = 0.0
    xupper = 1.0
    mx = 3
    ylower = 0.0
    yupper = 1.0
    my = 3
    x = pyclaw.Dimension('x',xlower,xupper,mx)
    y = pyclaw.Dimension('y',ylower,yupper,my)
    domain = pyclaw.Domain([x,y])

    num_eqn = 3  # Number of equations
    pyclaw_state = pyclaw.State(domain,num_eqn)
    peanoclaw_state = pyclaw.State(domain, num_eqn)

    grav = 1.0 # Parameter (global auxiliary variable)
    pyclaw_state.problem_data['grav'] = grav
    peanoclaw_state.problem_data['grav'] = grav

    # Initial solution
    # ================
    # Riemann states of the dam break problem
    damRadius = 0.2
    hl = 2.
    ul = 0.
    vl = 0.
    hr = 1.
    ur = 0.
    vr = 0.
    
    qinit(pyclaw_state,hl,ul,vl,hr,ur,vl,damRadius) # This function is defined above
    qinit(peanoclaw_state,hl,ul,vl,hr,ur,vl,damRadius) # This function is defined above

    tfinal = 1.0
    #===========================================================================
    # Set up controller and controller parameters for PyClaw run
    #===========================================================================
    pyclaw_controller = pyclaw.Controller()
    pyclaw_controller.tfinal = tfinal
    pyclaw_controller.solution = pyclaw.Solution(pyclaw_state,domain)
    pyclaw_controller.solver = pyclaw_solver
    pyclaw_controller.num_output_times = 1
    
    pyclaw_controller.run()
    
    #===========================================================================
    # Set up controller and controller parameters for PyClaw run
    #===========================================================================
    peanoclaw_controller = pyclaw.Controller()
    peanoclaw_controller.tfinal = tfinal
    peanoclaw_controller.solution = pyclaw.Solution(peanoclaw_state,domain)
    peanoclaw_controller.solver = peano_solver
    peanoclaw_controller.num_output_times = 1
    
    peanoclaw_controller.run()
    
    assert(np.max(np.abs(pyclaw_solver.qbc - peanoclaw_solver.qbc)) < 1e-9)
    
    

########NEW FILE########
__FILENAME__ = test_peano_solver
from nose.plugins.attrib import attr

if __name__=="__main__":
    import nose
    nose.main()
    
    
def test_initialization():
    from pyclaw.clawpack.clawpack import ClawSolver2D
    
    solver = ClawSolver2D()
    
    import peanoclaw
    peano_solver = peanoclaw.Solver(solver, 1.0)
    
    import inspect
    for member in inspect.getmembers(peano_solver):
        if(not member[0].startswith("_") and not inspect.ismethod(member[1])):
            print(member[0])
    for member in inspect.getmembers(solver):
        if(not member[0].startswith("_") and not inspect.ismethod(member[1])):
            print(member[0])
    
########NEW FILE########
__FILENAME__ = psystem_2d
#!/usr/bin/env python
# encoding: utf-8
r"""
Two-dimensional p-system
==============================

Solve the two-dimensional generalization of the p-system:

.. math:: 
    \epsilon_t - u_x - v_y & = 0 \\
    \rho(x,y) u_t - \sigma(\epsilon,x,y)_x & = 0 \\
    \rho(x,y) v_t - \sigma(\epsilon,x,y)_y & = 0.

We take :math:`\sigma = e^{K(x,y)\epsilon} - 1`, and the
material coefficients :math:`\rho,K` vary in a checkerboard
pattern.  The resulting dynamics lead to solitary waves,
though much more resolution is needed in order to see them.

This example shows how to set an aux array, use a b4step function,
use gauges, compute output functionals, and restart a simulation
from a checkpoint.
"""


import numpy as np

def qinit(state,A,x0,y0,varx,vary):
    r""" Set initial conditions:
         Gaussian stress, zero velocities."""
    yy,xx = state.grid.c_centers
    stress=A*np.exp(-(xx-x0)**2/(2*varx)-(yy-y0)**2/(2*vary)) #sigma(@t=0)
    stress_rel=state.aux[2,:]
    K=state.aux[1,:]

    state.q[0,:,:]=np.where(stress_rel==1,1,0)*stress/K+np.where(stress_rel==2,1,0)*np.log(stress+1)/K
    state.q[1,:,:]=0; state.q[2,:,:]=0

def setaux(x,y, KA=1, KB=4, rhoA=1, rhoB=4, stress_rel=2):
    r"""Return an array containing the values of the material
        coefficients.

        aux[0,i,j] = rho(x_i, y_j)              (material density)
        aux[1,i,j] = K(x_i, y_j)                (bulk modulus)
        aux[2,i,j] = stress-strain relation type at (x_i, y_j)
    """
    alphax=0.5; deltax=1.
    alphay=0.5; deltay=1.
    
    medium_type = 'checkerboard'

    aux = np.empty((4,len(x),len(y)), order='F')
    if medium_type == 'checkerboard':
        # xfrac and yfrac are x and y relative to deltax and deltay resp.
        xfrac=x-np.floor(x/deltax)*deltax
        yfrac=y-np.floor(y/deltay)*deltay
        # create a meshgrid out of xfrac and yfrac
        [yf,xf]=np.meshgrid(yfrac,xfrac)
        # density 
        aux[0,:,:]=rhoA*(xf<=alphax*deltax)*(yf<=alphay*deltay)\
                  +rhoA*(xf >alphax*deltax)*(yf >alphay*deltay)\
                  +rhoB*(xf >alphax*deltax)*(yf<=alphay*deltay)\
                  +rhoB*(xf<=alphax*deltax)*(yf >alphay*deltay)
        #Young modulus
        aux[1,:,:]=KA*(xf<=alphax*deltax)*(yf<=alphay*deltay)\
                  +KA*(xf >alphax*deltax)*(yf >alphay*deltay)\
                  +KB*(xf >alphax*deltax)*(yf<=alphay*deltay)\
                  +KB*(xf<=alphax*deltax)*(yf >alphay*deltay)
        # linearity of material
        aux[2,:,:]=stress_rel
    elif medium_type == 'sinusoidal' or medium_type == 'smooth_checkerboard':
        [yy,xx]=np.meshgrid(y,x)
        Amp_rho=np.abs(rhoA-rhoB)/2; offset_p=(rhoA+rhoB)/2
        Amp_K=np.abs(KA-KB)/2; offset_E=(KA+KB)/2
        if medium_type == 'sinusoidal':
            frec_x=2*np.pi/deltax; frec_y=2*np.pi/deltay
            fun=np.sin(frec_x*xx)*np.sin(frec_y*yy)
        else:
            sharpness=10
            fun_x=xx*0; fun_y=yy*0
            for i in xrange(0,1+int(np.ceil((x[-1]-x[0])/(deltax*0.5)))):
                fun_x=fun_x+(-1)**i*np.tanh(sharpness*(xx-deltax*i*0.5))
            for i in xrange(0,1+int(np.ceil((y[-1]-y[0])/(deltay*0.5)))):
                fun_y=fun_y+(-1)**i*np.tanh(sharpness*(yy-deltay*i*0.5))
            fun=fun_x*fun_y
        aux[0,:,:]=Amp_rho*fun+offset_p
        aux[1,:,:]=Amp_K*fun+offset_E
        aux[2,:,:]=stress_rel
    return aux

def b4step(solver,state):
    r"""Put in aux[3,:,:] the value of q[0,:,:] (eps). 
        This is required in rptpv.f.
        Only used by classic (not SharpClaw).
    """
    state.aux[3,:,:] = state.q[0,:,:]

def compute_stress(state):
    """ Compute stress from strain and store in state.p."""
    K=state.aux[1,:,:]
    stress_rel=state.aux[2,:,:]
    eps=state.q[0,:,:]
    state.p[0,:,:] = np.where(stress_rel==1,1,0) * K*eps \
                    +np.where(stress_rel==2,1,0) * (np.exp(eps*K)-1) \
 

def total_energy(state):
    rho = state.aux[0,:,:]; K = state.aux[1,:,:]
    
    u = state.q[1,:,:]/rho
    v = state.q[2,:,:]/rho
    kinetic=rho * (u**2 + v**2)/2.

    eps = state.q[0,:,:]
    sigma = np.exp(K*eps) - 1.
    potential = (sigma-np.log(sigma+1.))/K

    dx=state.grid.delta[0]; dy=state.grid.delta[1]
    
    state.F[0,:,:] = (potential+kinetic)*dx*dy 

def gauge_stress(q,aux):
    p = np.exp(q[0]*aux[1])-1
    return [p,10*p]

def setup(kernel_language='Fortran',
              use_petsc=False,outdir='./_output',solver_type='classic',
              disable_output=False, cells_per_layer=30, tfinal=18.):

    """
    Solve the p-system in 2D with variable coefficients
    """
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    # material parameters
    KA=1.;   rhoA=1.
    KB=4.;   rhoB=4.
    stress_rel=2;

    # Domain
    x_lower=0.25; x_upper=20.25
    y_lower=0.25; y_upper=20.25
    # cells per layer
    mx=(x_upper-x_lower)*cells_per_layer; 
    my=(y_upper-y_lower)*cells_per_layer
    # Initial condition parameters
    initial_amplitude=10.
    x0=0.25 # Center of initial perturbation
    y0=0.25 # Center of initial perturbation
    varx=0.5; vary=0.5 # Width of initial perturbation

    # Boundary conditions
    bc_x_lower=pyclaw.BC.wall; bc_x_upper=pyclaw.BC.extrap
    bc_y_lower=pyclaw.BC.wall; bc_y_upper=pyclaw.BC.extrap

    num_output_times=10

    if solver_type=='classic':
        solver = pyclaw.ClawSolver2D(riemann.psystem_2D)
        solver.dimensional_split=False
        solver.cfl_max = 0.9
        solver.cfl_desired = 0.8
        solver.limiters = pyclaw.limiters.tvd.superbee
    elif solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver2D(riemann.psystem_2D)

    if kernel_language != 'Fortran':
        raise Exception('Unrecognized value of kernel_language for 2D psystem')

    solver.bc_lower     = [bc_x_lower, bc_y_lower]
    solver.bc_upper     = [bc_x_upper, bc_y_upper]
    solver.aux_bc_lower = [bc_x_lower, bc_y_lower]
    solver.aux_bc_upper = [bc_x_upper, bc_y_upper]

    solver.fwave = True
    solver.before_step = b4step

    #controller
    claw = pyclaw.Controller()
    claw.tfinal = tfinal
    claw.solver = solver
    claw.outdir = outdir
    
    # restart options
    restart_from_frame = None

    if restart_from_frame is None:
        x = pyclaw.Dimension('x',x_lower,x_upper,mx)
        y = pyclaw.Dimension('y',y_lower,y_upper,my)
        domain = pyclaw.Domain([x,y])
        num_eqn = 3
        num_aux = 4
        state = pyclaw.State(domain,num_eqn,num_aux)
        state.mF = 1
        state.mp = 1

        grid = state.grid
        state.aux = setaux(grid.x.centers,grid.y.centers,KA,KB,rhoA,rhoB,stress_rel)
        #Initial condition
        qinit(state,initial_amplitude,x0,y0,varx,vary)

        claw.solution = pyclaw.Solution(state,domain)
        claw.num_output_times = num_output_times

    else:
        claw.solution = pyclaw.Solution(restart_from_frame, format='petsc',read_aux=False)
        claw.solution.state.mp = 1
        grid = claw.solution.domain.grid
        claw.solution.state.aux = setaux(grid.x.centers,grid.y.centers)
        claw.num_output_times = num_output_times - restart_from_frame
        claw.start_frame = restart_from_frame

    #claw.p_function = p_function
    if disable_output:
        claw.output_format = None
    claw.compute_F = total_energy
    claw.compute_p = compute_stress
    claw.write_aux_init = False

    grid.add_gauges([[0.25,0.25],[17.85,1.25],[3.25,18.75],[11.75,11.75]])
    solver.compute_gauge_values = gauge_stress
    state.keep_gauges = True
    claw.setplot = setplot
    claw.keep_copy = True

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data
    
    # Figure for strain
    plotfigure = plotdata.new_plotfigure(name='Stress', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Strain'
    plotaxes.xlimits = [0.,20.]
    plotaxes.ylimits = [0.,20.]
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = stress
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True
    
    return plotdata

def stress(current_data):    
    import numpy as np
    from psystem_2d import setaux
    aux = setaux(current_data.x[:,0],current_data.y[0,:])
    q = current_data.q
    return np.exp(aux[1,...]*q[0,...])-1.


if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = test_2d_psystem
def test_2d_psystem():
    """test_2d_psystem"""

    def verify_data():
        def verify(controller):
            """ verifies gauge values generated by 2d psystem application 
            from a previously verified run """
            
            import os
            import numpy as np
            from clawpack.pyclaw.util import check_diff

            test_state = controller.solution.state

            gauge_files = test_state.grid.gauge_files
            test_gauge_data_mem = test_state.gauge_data
            expected_gauges=[]
            thisdir = os.path.dirname(__file__)
            
            expected_list=[]
            error_list=[]
            test_passed = True
            if test_gauge_data_mem is not None:
                for i, gauge in enumerate(gauge_files):
                    test_gauge_data_io = np.loadtxt(gauge.name)
                    verify_file = os.path.join(thisdir,'verify_' +
                                            gauge.name.split('/')[-1])
                    expected_gauges.append(np.loadtxt(verify_file))
                    return_value_mem = check_diff(expected_gauges[i], 
                    test_gauge_data_mem[i], reltol=1e-4)
                    return_value_io = check_diff(expected_gauges[i], 
                    test_gauge_data_io, reltol=1e-4)
                    
                    if (return_value_mem is not None or
                        return_value_io is not None):
                        expected_list.append(return_value_mem[0])
                        error_list.append([return_value_mem[1],return_value_io[1]])
                        test_passed = False


                if test_passed:
                    return None
                else:
                    return(expected_list, error_list,return_value_io[2] ,'')
            else:
                return
                
        return verify

    from clawpack.pyclaw.util import gen_variants
    import psystem_2d
    import shutil
    tempdir = './_for_temp_pyclaw_test'
    classic_tests = gen_variants(psystem_2d.setup, verify_data(),
                                 kernel_languages=('Fortran',), 
                                 solver_type='classic', 
                                 outdir=tempdir, cells_per_layer=10,
                                 tfinal=40)
    from itertools import chain

    try:
        for test in chain(classic_tests):
            yield test

    finally:
        
        try:
            from petsc4py import PETSc
            PETSc.COMM_WORLD.Barrier()
        except ImportError:
            print """Unable to import petsc4py.
                   This should not be a problem unless you
                   are trying to run in parallel."""
        
        
        ERROR_STR= """Error removing %(path)s, %(error)s """
        try:         
            shutil.rmtree(tempdir )
        except OSError as (errno, strerror):
            print ERROR_STR % {'path' : tempdir, 'error': strerror }
            
        


########NEW FILE########
__FILENAME__ = shallow_water_shocktube
#!/usr/bin/env python
# encoding: utf-8

r"""
Shallow water flow
==================

Solve the one-dimensional shallow water equations:

.. math::
    h_t + (hu)_x + (hv)_y & = 0 \\
    (hu)_t + (hu^2 + \frac{1}{2}gh^2)_x + (huv)_y & = 0 \\
    (hv)_t + (huv)_x + (hv^2 + \frac{1}{2}gh^2)_y & = 0.

Here h is the depth, (u,v) is the velocity, and g is the gravitational constant.
"""

    
def setup(use_petsc=False,kernel_language='Fortran',outdir='./_output',solver_type='classic'):
    #===========================================================================
    # Import libraries
    #===========================================================================
    import numpy as np
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if kernel_language =='Python':
        rs = riemann.shallow_1D_py.shallow_1D
    elif kernel_language =='Fortran':
        rs = riemann.shallow_roe_with_efix_1D
 
    if solver_type == 'classic':
        solver = pyclaw.ClawSolver1D(rs)
        solver.limiters = pyclaw.limiters.tvd.vanleer
    elif solver_type == 'sharpclaw':
        solver = pyclaw.SharpClawSolver1D(rs)

    #===========================================================================
    # Setup solver and solver parameters
    #===========================================================================
    solver.kernel_language=kernel_language

    solver.bc_lower[0] = pyclaw.BC.extrap
    solver.bc_upper[0] = pyclaw.BC.extrap

    #===========================================================================
    # Initialize domain and then initialize the solution associated to the domain
    #===========================================================================
    xlower = -5.0
    xupper = 5.0
    mx = 500
    x = pyclaw.Dimension('x',xlower,xupper,mx)
    domain = pyclaw.Domain(x)
    num_eqn = 2
    state = pyclaw.State(domain,num_eqn)

    # Parameters
    state.problem_data['grav'] = 1.0
    
    xc = state.grid.x.centers

    IC='2-shock'
    x0=0.

    if IC=='dam-break':
        hl = 3.
        ul = 0.
        hr = 1.
        ur = 0.
        state.q[0,:] = hl * (xc <= x0) + hr * (xc > x0)
        state.q[1,:] = hl*ul * (xc <= x0) + hr*ur * (xc > x0)
    elif IC=='2-shock':
        hl = 1.
        ul = 1.
        hr = 1.
        ur = -1.
        state.q[0,:] = hl * (xc <= x0) + hr * (xc > x0)
        state.q[1,:] = hl*ul * (xc <= x0) + hr*ur * (xc > x0)
    elif IC=='perturbation':
        eps=0.1
        state.q[0,:] = 1.0 + eps*np.exp(-(xc-x0)**2/0.5)
        state.q[1,:] = 0.

    #===========================================================================
    # Setup controller and controller paramters
    #===========================================================================
    claw = pyclaw.Controller()
    claw.keep_copy = True
    claw.tfinal = 2.0
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir
    claw.setplot = setplot

    return claw


#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='Water height', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = [-5.0,5.0]
    plotaxes.title = 'Water height'
    plotaxes.axescmd = 'subplot(211)'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    plotitem.kwargs = {'linewidth':3}

    # Figure for q[1]
    #plotfigure = plotdata.new_plotfigure(name='Momentum', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.axescmd = 'subplot(212)'
    plotaxes.xlimits = [-5.0,5.0]
    plotaxes.title = 'Momentum'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d')
    plotitem.plot_var = 1
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    plotitem.kwargs = {'linewidth':3}
    
    return plotdata


if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = radial_dam_break
#!/usr/bin/env python
# encoding: utf-8

"""
Solve the 2D shallow water equations:

.. :math:
    h_t + (hu)_x + (hu)_y & = 0 \\
    (hu)_t + (
"""
#===========================================================================
# Import libraries
#===========================================================================

import numpy as np

def qinit(state,hl,ul,vl,hr,ur,vr,radDam):
    x0=0.
    y0=0.
    xCenter = state.grid.x.centers
    yCenter = state.grid.y.centers
    Y,X = np.meshgrid(yCenter,xCenter)
    r = np.sqrt((X-x0)**2 + (Y-y0)**2)
    state.q[0,:,:] = hl*(r<=radDam) + hr*(r>radDam)
    state.q[1,:,:] = hl*ul*(r<=radDam) + hr*ur*(r>radDam)
    state.q[2,:,:] = hl*vl*(r<=radDam) + hr*vr*(r>radDam)

    
def setup(use_petsc=False,outdir='./_output',solver_type='classic'):
    #===========================================================================
    # Import libraries
    #===========================================================================
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    #===========================================================================
    # Setup solver and solver parameters
    #===========================================================================
    if solver_type == 'classic':
        solver = pyclaw.ClawSolver2D(riemann.shallow_roe_with_efix_2D)
        solver.limiters = pyclaw.limiters.tvd.MC
        solver.dimensional_split=1
    elif solver_type == 'sharpclaw':
        solver = pyclaw.SharpClawSolver2D(riemann.shallow_roe_with_efix_2D)

    solver.bc_lower[0] = pyclaw.BC.extrap
    solver.bc_upper[0] = pyclaw.BC.wall
    solver.bc_lower[1] = pyclaw.BC.extrap
    solver.bc_upper[1] = pyclaw.BC.wall

    #===========================================================================
    # Initialize domain and state, then initialize the solution associated to the 
    # state and finally initialize aux array
    #===========================================================================

    # Domain:
    xlower = -2.5
    xupper = 2.5
    mx = 150
    ylower = -2.5
    yupper = 2.5
    my = 150
    x = pyclaw.Dimension('x',xlower,xupper,mx)
    y = pyclaw.Dimension('y',ylower,yupper,my)
    domain = pyclaw.Domain([x,y])

    state = pyclaw.State(domain,solver.num_eqn)

    grav = 1.0 # Parameter (global auxiliary variable)
    state.problem_data['grav'] = grav

    # Initial solution
    # ================
    # Riemann states of the dam break problem
    damRadius = 0.5
    hl = 2.
    ul = 0.
    vl = 0.
    hr = 1.
    ur = 0.
    vr = 0.
    
    qinit(state,hl,ul,vl,hr,ur,vr,damRadius) # This function is defined above

    #===========================================================================
    # Set up controller and controller parameters
    #===========================================================================
    claw = pyclaw.Controller()
    claw.tfinal = 2.5
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir
    claw.num_output_times = 10
    claw.setplot = setplot
    claw.keep_copy = True

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='Water height', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = [-2.5, 2.5]
    plotaxes.ylimits = [-2.5, 2.5]
    plotaxes.title = 'Water height'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 0
    plotitem.pcolor_cmap = colormaps.red_yellow_blue
    plotitem.pcolor_cmin = 0.5
    plotitem.pcolor_cmax = 1.5
    plotitem.add_colorbar = True
    
    # Scatter plot of q[0]
    plotfigure = plotdata.new_plotfigure(name='Scatter plot of h', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = [0., 2.5]
    plotaxes.ylimits = [0., 2.1]
    plotaxes.title = 'Scatter plot of h'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_from_2d_data')
    plotitem.plot_var = 0
    def q_vs_radius(current_data):
        from numpy import sqrt
        x = current_data.x
        y = current_data.y
        r = sqrt(x**2 + y**2)
        q = current_data.q[0,:,:]
        return r,q
    plotitem.map_2d_to_1d = q_vs_radius
    plotitem.plotstyle = 'o'


    # Figure for q[1]
    plotfigure = plotdata.new_plotfigure(name='Momentum in x direction', figno=2)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = [-2.5, 2.5]
    plotaxes.ylimits = [-2.5, 2.5]
    plotaxes.title = 'Momentum in x direction'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 1
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True
    plotitem.show = False       # show on plot?
    

    # Figure for q[2]
    plotfigure = plotdata.new_plotfigure(name='Momentum in y direction', figno=3)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = [-2.5, 2.5]
    plotaxes.ylimits = [-2.5, 2.5]
    plotaxes.title = 'Momentum in y direction'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 2
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True
    plotitem.show = False       # show on plot?
    
    return plotdata


if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = Rossby_wave
#!/usr/bin/env python
# encoding: utf-8
"""
2D shallow water equations on a spherical surface. The approximation of the 
three-dimensional equations is restricted to the surface of the sphere. 
Therefore only the solution on the surface is updated. 

Reference: Logically Rectangular Grids and Finite Volume Methods for PDEs in 
           Circular and Spherical Domains. 
           By Donna A. Calhoun, Christiane Helzel, and Randall J. LeVeque
           SIAM Review 50 (2008), 723-752. 
"""

import math
import os
import sys

import numpy as np

from clawpack import pyclaw
from clawpack import riemann
from clawpack.pyclaw.util import inplace_build

try:
    import problem
    import classic2

except ImportError:
    this_dir = os.path.dirname(__file__)
    if this_dir == '':
        this_dir = os.path.abspath('.')
    inplace_build(this_dir)

    try:
        # Now try to import again
        import problem
        import classic2
    except ImportError:
        print >> sys.stderr, "***\nUnable to import problem module or automatically build, try running (in the directory of this file):\n python setup.py build_ext -i\n***"
        raise


# Nondimensionalized radius of the earth
Rsphere = 1.0


def fortran_src_wrapper(solver,state,dt):
    """
    Wraps Fortran src2.f routine. 
    src2.f contains the discretization of the source term.
    """
    # Some simplifications
    grid = state.grid

    # Get parameters and variables that have to be passed to the fortran src2
    # routine.
    mx, my = grid.num_cells[0], grid.num_cells[1]
    num_ghost = solver.num_ghost
    xlower, ylower = grid.lower[0], grid.lower[1]
    dx, dy = grid.delta[0], grid.delta[1]
    q = state.q
    aux = state.aux
    t = state.t

    # Call src2 function
    state.q = problem.src2(mx,my,num_ghost,xlower,ylower,dx,dy,q,aux,t,dt,Rsphere)


def mapc2p_sphere_nonvectorized(grid,mC):
    """
    Maps to points on a sphere of radius Rsphere. Nonvectorized version (slow).
    
    Takes as input: array_list made by x_coordinates, y_ccordinates in the map 
                    space.

    Returns as output: array_list made by x_coordinates, y_ccordinates in the 
                       physical space.

    Inputs: mC = list composed by two arrays
                 [array ([xc1, xc2, ...]), array([yc1, yc2, ...])]

    Output: pC = list composed by three arrays
                 [array ([xp1, xp2, ...]), array([yp1, yp2, ...]), array([zp1, zp2, ...])]

    NOTE: this function is not used in the standard script.
    """

    # Get number of cells in both directions
    mx, my = grid.num_cells[0], grid.num_cells[1]

    # Define new list of numpy array, pC = physical coordinates
    pC = []

    for i in range(mx):
        for j in range(my):
            xc = mC[0][i][j]
            yc = mC[1][i][j]

            # Ghost cell values outside of [-3,1]x[-1,1] get mapped to other
            # hemisphere:
            if (xc >= 1.0):
                xc = xc - 4.0
            if (xc <= -3.0):
                xc = xc + 4.0

            if (yc >= 1.0):
                yc = 2.0 - yc
                xc = -2.0 - xc

            if (yc <= -1.0):
                yc = -2.0 - yc
                xc = -2.0 - xc

            if (xc <= -1.0):
                # Points in [-3,-1] map to lower hemisphere - reflect about x=-1
                # to compute x,y mapping and set sgnz appropriately:
                xc = -2.0 - xc
                sgnz = -1.0
            else:
                sgnz = 1.0

            sgnxc = math.copysign(1.0,xc)
            sgnyc = math.copysign(1.0,yc)

            xc1 = np.abs(xc)
            yc1 = np.abs(yc)
            d = np.maximum(np.maximum(xc1,yc1), 1.0e-10)     

            DD = Rsphere*d*(2.0 - d) / np.sqrt(2.0)
            R = Rsphere
            centers = DD - np.sqrt(np.maximum(R**2 - DD**2, 0.0))
            
            xp = DD/d * xc1
            yp = DD/d * yc1

            if (yc1 >= xc1):
                yp = centers + np.sqrt(np.maximum(R**2 - xp**2, 0.0))
            else:
                xp = centers + np.sqrt(np.maximum(R**2 - yp**2, 0.0))

            # Compute physical coordinates
            zp = np.sqrt(np.maximum(Rsphere**2 - (xp**2 + yp**2), 0.0))
            pC.append(xp*sgnxc)
            pC.append(yp*sgnyc)
            pC.append(zp*sgnz)

    return pC


def mapc2p_sphere_vectorized(grid,mC):
    """
    Maps to points on a sphere of radius Rsphere. Vectorized version (fast).  

    Takes as input: array_list made by x_coordinates, y_ccordinates in the map 
                    space.

    Returns as output: array_list made by x_coordinates, y_ccordinates in the 
                       physical space.

    Inputs: mC = list composed by two arrays
                 [array ([xc1, xc2, ...]), array([yc1, yc2, ...])]

    Output: pC = list composed by three arrays
                 [array ([xp1, xp2, ...]), array([yp1, yp2, ...]), array([zp1, zp2, ...])]

    NOTE: this function is used in the standard script.
    """

    # Get number of cells in both directions
    mx, my = grid.num_cells[0], grid.num_cells[1]
    
    # 2D array useful for the vectorization of the function
    sgnz = np.ones((mx,my))

    # 2D coordinates in the computational domain
    xc = mC[0][:][:]
    yc = mC[1][:][:]

    # Compute 3D coordinates in the physical domain
    # =============================================

    # Note: yc < -1 => second copy of sphere:
    ij2 = np.where(yc < -1.0)
    xc[ij2] = -xc[ij2] - 2.0;
    yc[ij2] = -yc[ij2] - 2.0;

    ij = np.where(xc < -1.0)
    xc[ij] = -2.0 - xc[ij]
    sgnz[ij] = -1.0;
    xc1 = np.abs(xc)
    yc1 = np.abs(yc)
    d = np.maximum(xc1,yc1)
    d = np.maximum(d, 1e-10)
    D = Rsphere*d*(2-d) / np.sqrt(2)
    R = Rsphere*np.ones((np.shape(d)))

    centers = D - np.sqrt(R**2 - D**2)
    xp = D/d * xc1
    yp = D/d * yc1

    ij = np.where(yc1==d)
    yp[ij] = centers[ij] + np.sqrt(R[ij]**2 - xp[ij]**2)
    ij = np.where(xc1==d)
    xp[ij] = centers[ij] + np.sqrt(R[ij]**2 - yp[ij]**2)
    
    # Define new list of numpy array, pC = physical coordinates
    pC = []

    xp = np.sign(xc) * xp
    yp = np.sign(yc) * yp
    zp = sgnz * np.sqrt(Rsphere**2 - (xp**2 + yp**2))
    
    pC.append(xp)
    pC.append(yp)
    pC.append(zp)

    return pC


def qinit(state,mx,my):
    r"""
    Initialize solution with 4-Rossby-Haurwitz wave.

    NOTE: this function is not used in the standard script.
    """
    # Parameters
    a = 6.37122e6     # Radius of the earth
    Omega = 7.292e-5  # Rotation rate
    G = 9.80616       # Gravitational acceleration

    K = 7.848e-6   
    t0 = 86400.0     
    h0 = 8.e3         # Minimum fluid height at the poles        
    R = 4.0

    # Compute the the physical coordinates of the cells' centerss
    state.grid.compute_p_centers(recompute=True)
 
    for i in range(mx):
        for j in range(my):
            xp = state.grid.p_centers[0][i][j]
            yp = state.grid.p_centers[1][i][j]
            zp = state.grid.p_centers[2][i][j]

            rad = np.maximum(np.sqrt(xp**2 + yp**2),1.e-6)

            if (xp >= 0.0 and yp >= 0.0):
                theta = np.arcsin(yp/rad) 
            elif (xp <= 0.0 and yp >= 0.0):
                theta = np.pi - np.arcsin(yp/rad)
            elif (xp <= 0.0 and yp <= 0.0):
                 theta = -np.pi + np.arcsin(-yp/rad)
            elif (xp >= 0.0 and yp <= 0.0):
                theta = -np.arcsin(-yp/rad)

            # Compute phi, at north pole: pi/2 at south pool: -pi/2
            if (zp >= 0.0): 
                phi =  np.arcsin(zp/Rsphere) 
            else:
                phi = -np.arcsin(-zp/Rsphere)  
        
            xp = theta 
            yp = phi 


            bigA = 0.5*K*(2.0*Omega + K)*np.cos(yp)**2.0 + \
                   0.25*K*K*np.cos(yp)**(2.0*R)*((1.0*R+1.0)*np.cos(yp)**2.0 + \
                   (2.0*R*R - 1.0*R - 2.0) - 2.0*R*R*(np.cos(yp))**(-2.0))
            bigB = (2.0*(Omega + K)*K)/((1.0*R + 1.0)*(1.0*R + 2.0)) * \
                   np.cos(yp)**R*( (1.0*R*R + 2.0*R + 2.0) - \
                   (1.0*R + 1.0)**(2)*np.cos(yp)**2 )
            bigC = 0.25*K*K*np.cos(yp)**(2*R)*( (1.0*R + 1.0)* \
                   np.cos(yp)**2 - (1.0*R + 2.0))


            # Calculate local longitude-latitude velocity vector
            # ==================================================
            Uin = np.zeros(3)

            # Longitude (angular) velocity component
            Uin[0] = (K*np.cos(yp)+K*np.cos(yp)**(R-1.)*( R*np.sin(yp)**2.0 - \
                     np.cos(yp)**2.0)*np.cos(R*xp))*t0

            # Latitude (angular) velocity component
            Uin[1] = (-K*R*np.cos(yp)**(R-1.0)*np.sin(yp)*np.sin(R*xp))*t0

            # Radial velocity component
            Uin[2] = 0.0 # The fluid does not enter in the sphere
            

            # Calculate velocity vetor in cartesian coordinates
            # =================================================
            Uout = np.zeros(3)

            Uout[0] = (-np.sin(xp)*Uin[0]-np.sin(yp)*np.cos(xp)*Uin[1])
            Uout[1] = (np.cos(xp)*Uin[0]-np.sin(yp)*np.sin(xp)*Uin[1])
            Uout[2] = np.cos(yp)*Uin[1]

            # Set the initial condition
            # =========================
            state.q[0,i,j] =  h0/a + (a/G)*( bigA + bigB*np.cos(R*xp) + \
                              bigC*np.cos(2.0*R*xp))
            state.q[1,i,j] = state.q[0,i,j]*Uout[0] 
            state.q[2,i,j] = state.q[0,i,j]*Uout[1] 
            state.q[3,i,j] = state.q[0,i,j]*Uout[2] 


def qbc_lower_y(state,dim,t,qbc,num_ghost):
    """
    Impose periodic boundary condition to q at the bottom boundary for the 
    sphere. This function does not work in parallel.
    """
    for j in range(num_ghost):
        qbc1D = np.copy(qbc[:,:,2*num_ghost-1-j])
        qbc[:,:,j] = qbc1D[:,::-1]


def qbc_upper_y(state,dim,t,qbc,num_ghost):
    """
    Impose periodic boundary condition to q at the top boundary for the sphere.
    This function does not work in parallel.
    """
    my = state.grid.num_cells[1]
    for j in range(num_ghost):
        qbc1D = np.copy(qbc[:,:,my+num_ghost-1-j])
        qbc[:,:,my+num_ghost+j] = qbc1D[:,::-1]


def auxbc_lower_y(state,dim,t,auxbc,num_ghost):
    """
    Impose periodic boundary condition to aux at the bottom boundary for the 
    sphere.
    """
    grid=state.grid

    # Get parameters and variables that have to be passed to the fortran src2
    # routine.
    mx, my = grid.num_cells[0], grid.num_cells[1]
    xlower, ylower = grid.lower[0], grid.lower[1]
    dx, dy = grid.delta[0],grid.delta[1]

    # Impose BC
    auxtemp = auxbc.copy()
    auxtemp = problem.setaux(mx,my,num_ghost,mx,my,xlower,ylower,dx,dy,auxtemp,Rsphere)
    auxbc[:,:,:num_ghost] = auxtemp[:,:,:num_ghost]

def auxbc_upper_y(state,dim,t,auxbc,num_ghost):
    """
    Impose periodic boundary condition to aux at the top boundary for the 
    sphere. 
    """
    grid=state.grid

    # Get parameters and variables that have to be passed to the fortran src2
    # routine.
    mx, my = grid.num_cells[0], grid.num_cells[1]
    xlower, ylower = grid.lower[0], grid.lower[1]
    dx, dy = grid.delta[0],grid.delta[1]
    
    # Impose BC
    auxtemp = auxbc.copy()
    auxtemp = problem.setaux(mx,my,num_ghost,mx,my,xlower,ylower,dx,dy,auxtemp,Rsphere)
    auxbc[:,:,-num_ghost:] = auxtemp[:,:,-num_ghost:]


def setup(use_petsc=False,solver_type='classic',outdir='./_output', disable_output=False):
    if use_petsc:
        raise Exception("petclaw does not currently support mapped grids (go bug Lisandro who promised to implement them)")

    if solver_type != 'classic':
        raise Exception("Only Classic-style solvers (solver_type='classic') are supported on mapped grids")

    solver = pyclaw.ClawSolver2D(riemann.shallow_sphere_2D)
    solver.fmod = classic2

    # Set boundary conditions
    # =======================
    solver.bc_lower[0] = pyclaw.BC.periodic
    solver.bc_upper[0] = pyclaw.BC.periodic
    solver.bc_lower[1] = pyclaw.BC.custom  # Custom BC for sphere
    solver.bc_upper[1] = pyclaw.BC.custom  # Custom BC for sphere

    solver.user_bc_lower = qbc_lower_y
    solver.user_bc_upper = qbc_upper_y

    # Auxiliary array
    solver.aux_bc_lower[0] = pyclaw.BC.periodic
    solver.aux_bc_upper[0] = pyclaw.BC.periodic
    solver.aux_bc_lower[1] = pyclaw.BC.custom  # Custom BC for sphere
    solver.aux_bc_upper[1] = pyclaw.BC.custom  # Custom BC for sphere

    solver.user_aux_bc_lower = auxbc_lower_y
    solver.user_aux_bc_upper = auxbc_upper_y


    # Dimensional splitting ?
    # =======================
    solver.dimensional_split = 0
 
    # Transverse increment waves and transverse correction waves are computed 
    # and propagated.
    # =======================================================================
    solver.transverse_waves = 2
    
    # Use source splitting method
    # ===========================
    solver.source_split = 2

    # Set source function
    # ===================
    solver.step_source = fortran_src_wrapper

    # Set the limiter for the waves
    # =============================
    solver.limiters = pyclaw.limiters.tvd.MC


    #===========================================================================
    # Initialize domain and state, then initialize the solution associated to the 
    # state and finally initialize aux array
    #===========================================================================
    # Domain:
    xlower = -3.0
    xupper = 1.0
    mx = 40

    ylower = -1.0
    yupper = 1.0
    my = 20

    # Check whether or not the even number of cells are used in in both 
    # directions. If odd numbers are used a message is print at screen and the 
    # simulation is interrputed.
    if(mx % 2 != 0 or my % 2 != 0):
        message = 'Please, use even numbers of cells in both direction. ' \
                  'Only even numbers allow to impose correctly the boundary ' \
                  'conditions!'
        raise ValueError(message)


    x = pyclaw.Dimension('x',xlower,xupper,mx)
    y = pyclaw.Dimension('y',ylower,yupper,my)
    domain = pyclaw.Domain([x,y])
    dx = domain.grid.delta[0]
    dy = domain.grid.delta[1]

    # Define some parameters used in Fortran common blocks 
    solver.fmod.comxyt.dxcom = dx
    solver.fmod.comxyt.dycom = dy
    solver.fmod.sw.g = 11489.57219  
    solver.rp.comxyt.dxcom = dx
    solver.rp.comxyt.dycom = dy
    solver.rp.sw.g = 11489.57219  

    # Define state object
    # ===================
    num_aux = 16 # Number of auxiliary variables
    state = pyclaw.State(domain,solver.num_eqn,num_aux)

    # Override default mapc2p function
    # ================================
    state.grid.mapc2p = mapc2p_sphere_vectorized
        

    # Set auxiliary variables
    # =======================
    
    # Get lower left corner coordinates 
    xlower,ylower = state.grid.lower[0],state.grid.lower[1]

    num_ghost = 2
    auxtmp = np.ndarray(shape=(num_aux,mx+2*num_ghost,my+2*num_ghost), dtype=float, order='F')
    auxtmp = problem.setaux(mx,my,num_ghost,mx,my,xlower,ylower,dx,dy,auxtmp,Rsphere)
    state.aux[:,:,:] = auxtmp[:,num_ghost:-num_ghost,num_ghost:-num_ghost]

    # Set index for capa
    state.index_capa = 0

    # Set initial conditions
    # ====================== 
    # 1) Call fortran function
    qtmp = np.ndarray(shape=(solver.num_eqn,mx+2*num_ghost,my+2*num_ghost), dtype=float, order='F')
    qtmp = problem.qinit(mx,my,num_ghost,mx,my,xlower,ylower,dx,dy,qtmp,auxtmp,Rsphere)
    state.q[:,:,:] = qtmp[:,num_ghost:-num_ghost,num_ghost:-num_ghost]

    # 2) call python function define above
    #qinit(state,mx,my)


    #===========================================================================
    # Set up controller and controller parameters
    #===========================================================================
    claw = pyclaw.Controller()
    claw.keep_copy = True
    if disable_output:
        claw.output_format = None
    claw.output_style = 1
    claw.num_output_times = 10
    claw.tfinal = 10
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir

    return claw

        
if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup)


def plot_on_sphere():
    """
    Plots the solution of the shallow water on a sphere in the 
    rectangular computational domain. The user can specify the name of the solution
    file and its path. If these are not given, the script checks 
    whether the solution fort.q0000 in ./_output exists and plots it. If it it does
    not exist an error message is printed at screen.
    The file must be ascii and clawpack format.

    To use this, you must first install the basemap toolkit; see
    http://matplotlib.org/basemap/users/installing.html.

    This function also shows how to manually read and plot the solution stored in
    an ascii file written by pyclaw, without using the pyclaw.io.ascii routines.
    """

    import matplotlib.pyplot as plt

    # Nondimensionalized radius of the earth
    Rsphere = 1.0

    def contourLineSphere(fileName='fort.q0000',path='./_output'):
        """
        This function plots the contour lines on a spherical surface for the shallow
        water equations solved on a sphere.
        """  
     
        # Open file
        # =========
        
        # Concatenate path and file name
        pathFileName = path + "/" + fileName

        f = file(pathFileName,"r")

        # Read file header
        # ================
        # The information contained in the first two lines are not used.
        unused = f.readline()  # patch_number
        unused = f.readline() # AMR_level

        # Read mx, my, xlow, ylow, dx and dy
        line = f.readline()
        sline = line.split()
        mx = int(sline[0])

        line = f.readline()
        sline = line.split()
        my = int(sline[0])

        line = f.readline()
        sline = line.split()
        xlower = float(sline[0])

        line = f.readline()
        sline = line.split()
        ylower = float(sline[0])

        line = f.readline()
        sline = line.split()
        dx = float(sline[0])

        line = f.readline()
        sline = line.split()
        dy = float(sline[0])


        # Patch:
        # ====
        xupper = xlower + mx * dx
        yupper = ylower + my * dy

        x = pyclaw.Dimension('x',xlower,xupper,mx)
        y = pyclaw.Dimension('y',ylower,yupper,my)
        patch = pyclaw.Patch([x,y])


        # Override default mapc2p function
        # ================================
        patch.mapc2p = mapc2p_sphere_vectorized


        # Compute the physical coordinates of each cell's centers
        # ======================================================
        patch.compute_p_centers(recompute=True)
        xp = patch._p_centers[0]
        yp = patch._p_centers[1]
        zp = patch._p_centers[2]

        patch.compute_c_centers(recompute=True)
        xc = patch._c_centers[0]
        yc = patch._c_centers[1]
        
        # Define arrays of conserved variables
        h = np.zeros((mx,my))
        hu = np.zeros((mx,my))
        hv = np.zeros((mx,my))
        hw = np.zeros((mx,my))

        # Read solution
        for j in range(my):
            tmp = np.fromfile(f,dtype='float',sep=" ",count=4*mx)
            tmp = tmp.reshape((mx,4))
            h[:,j] = tmp[:,0]
            hu[:,j] = tmp[:,1]
            hv[:,j] = tmp[:,2]
            hw[:,j] = tmp[:,3]

        
        # Plot solution in the computational domain
        # =========================================

        # Fluid height
        plt.figure()
        CS = plt.contour(xc,yc,h)
        plt.title('Fluid height (computational domain)')
        plt.xlabel('xc')
        plt.ylabel('yc')
        plt.clabel(CS, inline=1, fontsize=10)
        plt.show()



########NEW FILE########
__FILENAME__ = setplot
""" 
Set up the plot figures, axes, and items to be done for each frame.

This module is imported by the plotting routines and then the
function setplot is called to set the plot parameters.
    
""" 
import numpy as np


#--------------------------
def setplot(plotdata):
#--------------------------
    
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    
    """

    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data
    
    
    # Figure for pcolor plot
    plotfigure = plotdata.new_plotfigure(name='Water height', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = [-3.0, 1.0]
    plotaxes.ylimits = [-1.0, 1.0]
    plotaxes.title = 'Water height'
    plotaxes.scaled = True

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_contour')
    plotitem.plot_var = 0
    plotitem.contour_levels = np.linspace(-1.59729945e-03, 1.59729945e-03, 200)
    plotitem.contour_colors = 'k'
    plotitem.patchedges_show = 1

    plotitem.show = True       # show on plot?

    return plotdata

########NEW FILE########
__FILENAME__ = test_shallow_sphere
def test_shallow_sphere():
    """Test solution of shallow water equations on the sphere."""
    import Rossby_wave

    def verify_shallow_sphere(claw):
        import os
        import numpy as np
        from clawpack.pyclaw.util import check_diff

        test_q = claw.frames[-1].state.get_q_global()
        test_height = test_q[0,:,:]

        thisdir = os.path.dirname(__file__)
        data_filename='swsphere_height.txt'
        expected_height = np.loadtxt(os.path.join(thisdir,data_filename))
        test_err = np.linalg.norm(expected_height-test_height)
        expected_err = 0
        return check_diff(expected_err, test_err, abstol=1e-4)

    from clawpack.pyclaw.util import test_app
    kwargs = {}   
    kwargs['disable_output']= True
    return test_app(Rossby_wave.setup,
                    verify_shallow_sphere,
                    kwargs)


########NEW FILE########
__FILENAME__ = stegoton
#!/usr/bin/env python
# encoding: utf-8
r"""
Solitary wave formation in periodic nonlinear elastic media
===========================================================

Solve a one-dimensional nonlinear elasticity system:

.. math::
    \epsilon_t + u_x & = 0 \\
    (\rho(x) u)_t + \sigma(\epsilon,x)_x & = 0.

Here :math:`\epsilon` is the strain, :math:`\sigma` is the stress, 
u is the velocity, and :math:`\rho(x)` is the density.  
We take the stress-strain relation :math:`\sigma = e^{K(x)\epsilon}-1`;
:math:`K(x)` is the linearized bulk modulus.
Note that the density and bulk modulus may depend explicitly on x.

The problem solved here is based on [LeVYon03]_.  An initial hump
evolves into two trains of solitary waves.

"""
import numpy as np


def qinit(state,ic=2,a2=1.0,xupper=600.):
    x = state.grid.x.centers
    
    if ic==1: #Zero ic
        state.q[:,:] = 0.
    elif ic==2:
        # Gaussian
        sigma = a2*np.exp(-((x-xupper/2.)/10.)**2.)
        state.q[0,:] = np.log(sigma+1.)/state.aux[1,:]
        state.q[1,:] = 0.


def setaux(x,rhoB=4,KB=4,rhoA=1,KA=1,alpha=0.5,xlower=0.,xupper=600.,bc=2):
    aux = np.empty([3,len(x)],order='F')
    xfrac = x-np.floor(x)
    #Density:
    aux[0,:] = rhoA*(xfrac<alpha)+rhoB*(xfrac>=alpha)
    #Bulk modulus:
    aux[1,:] = KA  *(xfrac<alpha)+KB  *(xfrac>=alpha)
    aux[2,:] = 0. # not used
    return aux

    
def b4step(solver,state):
    #Reverse velocity at trtime
    #Note that trtime should be an output point
    if state.t>=state.problem_data['trtime']-1.e-10 and not state.problem_data['trdone']:
        #print 'Time reversing'
        state.q[1,:]=-state.q[1,:]
        state.q=state.q
        state.problem_data['trdone']=True
        if state.t>state.problem_data['trtime']:
            print 'WARNING: trtime is '+str(state.problem_data['trtime'])+\
                ' but velocities reversed at time '+str(state.t)
    #Change to periodic BCs after initial pulse 
    if state.t>5*state.problem_data['tw1'] and solver.bc_lower[0]==0:
        solver.bc_lower[0]=2
        solver.bc_upper[0]=2
        solver.aux_bc_lower[0]=2
        solver.aux_bc_upper[0]=2


def zero_bc(state,dim,t,qbc,num_ghost):
    """Set everything to zero"""
    if dim.on_upper_boundary:
        qbc[:,-num_ghost:]=0.

def moving_wall_bc(state,dim,t,qbc,num_ghost):
    """Initial pulse generated at left boundary by prescribed motion"""
    if dim.on_lower_boundary:
        qbc[0,:num_ghost]=qbc[0,num_ghost] 
        t=state.t; t1=state.problem_data['t1']; tw1=state.problem_data['tw1']
        a1=state.problem_data['a1'];
        t0 = (t-t1)/tw1
        if abs(t0)<=1.: vwall = -a1*(1.+np.cos(t0*np.pi))
        else: vwall=0.
        for ibc in xrange(num_ghost-1):
            qbc[1,num_ghost-ibc-1] = 2*vwall*state.aux[1,ibc] - qbc[1,num_ghost+ibc]



def setup(use_petsc=0,kernel_language='Fortran',solver_type='classic',outdir='./_output'):
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if kernel_language=='Python':
        rs = riemann.nonlinear_elasticity_1D_py.nonlinear_elasticity_1D
    elif kernel_language=='Fortran':
        rs = riemann.nonlinear_elasticity_fwave_1D

    if solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver1D(rs)
        solver.char_decomp=0
    else:
        solver = pyclaw.ClawSolver1D(rs)

    solver.kernel_language = kernel_language

    solver.bc_lower[0] = pyclaw.BC.custom
    solver.bc_upper[0] = pyclaw.BC.extrap

    #Use the same BCs for the aux array
    solver.aux_bc_lower[0] = pyclaw.BC.extrap
    solver.aux_bc_upper[0] = pyclaw.BC.extrap

    xlower=0.0; xupper=300.0
    cells_per_layer=12; mx=int(round(xupper-xlower))*cells_per_layer
    x = pyclaw.Dimension('x',xlower,xupper,mx)
    domain = pyclaw.Domain(x)
    state = pyclaw.State(domain,solver.num_eqn)

    #Set global parameters
    alpha = 0.5
    KA    = 1.0
    KB    = 4.0
    rhoA  = 1.0
    rhoB  = 4.0
    state.problem_data = {}
    state.problem_data['t1']    = 10.0
    state.problem_data['tw1']   = 10.0
    state.problem_data['a1']    = 0.1
    state.problem_data['alpha'] = alpha
    state.problem_data['KA'] = KA
    state.problem_data['KB'] = KB
    state.problem_data['rhoA'] = rhoA
    state.problem_data['rhoB'] = rhoB
    state.problem_data['trtime'] = 999999999.0
    state.problem_data['trdone'] = False

    #Initialize q and aux
    xc=state.grid.x.centers
    state.aux=setaux(xc,rhoB,KB,rhoA,KA,alpha,xlower=xlower,xupper=xupper)
    qinit(state,ic=1,a2=1.0,xupper=xupper)

    tfinal=500.; num_output_times = 20;

    solver.max_steps = 5000000
    solver.fwave = True 
    solver.before_step = b4step 
    solver.user_bc_lower=moving_wall_bc
    solver.user_bc_upper=zero_bc

    claw = pyclaw.Controller()
    claw.output_style = 1
    claw.num_output_times = num_output_times
    claw.tfinal = tfinal
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.setplot = setplot
    claw.keep_copy = True

    return claw


#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='Stress', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.title = 'Stress'
    plotaxes.ylimits = [-0.1,1.0]

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = stress
    plotitem.kwargs = {'linewidth':2}
    
    # Figure for q[1]
    plotfigure = plotdata.new_plotfigure(name='Velocity', figno=2)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = [-.5,0.1]
    plotaxes.title = 'Velocity'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = velocity
    plotitem.kwargs = {'linewidth':2}
    
    return plotdata

 
def velocity(current_data):
    """Compute velocity from strain and momentum"""
    from stegoton import setaux
    aux=setaux(current_data.x,rhoB=4,KB=4)
    velocity = current_data.q[1,:]/aux[0,:]
    return velocity

def stress(current_data):
    """Compute stress from strain and momentum"""
    from stegoton import setaux
    from clawpack.riemann.nonlinear_elasticity_1D_py import sigma 
    aux=setaux(current_data.x)
    epsilon = current_data.q[0,:]
    stress = sigma(epsilon,aux[1,:])
    return stress

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = traffic
#!/usr/bin/env python
# encoding: utf-8

def setup(use_petsc=0,outdir='./_output',solver_type='classic'):
    """
    Example python script for solving 1d traffic model:

    $$ q_t + umax( q(1-q) )_x = 0.$$
    """

    import numpy as np
    from clawpack import riemann

    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    #===========================================================================
    # Setup solver and solver parameters
    #===========================================================================
    if solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver1D(riemann.traffic_1D)
    else:
        solver = pyclaw.ClawSolver1D(riemann.traffic_1D)

    solver.bc_lower[0] = pyclaw.BC.extrap
    solver.bc_upper[0] = pyclaw.BC.extrap

    #===========================================================================
    # Initialize domain and then initialize the solution associated to the domain
    #===========================================================================
    x = pyclaw.Dimension('x',-1.0,1.0,500)
    domain = pyclaw.Domain(x)
    num_eqn = 1
    state = pyclaw.State(domain,num_eqn)

    grid = state.grid
    xc=grid.x.centers

    state.q[0,:] = 0.75*(xc<0) + 0.1*(xc>0.) 

    state.problem_data['efix']=True
    state.problem_data['umax']=1.

    #===========================================================================
    # Setup controller and controller parameters. Then solve the problem
    #===========================================================================
    claw = pyclaw.Controller()
    claw.tfinal =2.0
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir
    claw.setplot = setplot
    claw.keep_copy = True

    return claw

#--------------------------
def setplot(plotdata):
#--------------------------
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    """ 
    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='q[0]', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.ylimits = [-0.1, 1.1]
    plotaxes.title = 'q[0]'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    
    return plotdata


if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(setup,setplot)

########NEW FILE########
__FILENAME__ = burgers1D
#!/usr/bin/env python
# encoding: utf-8

def burgers(iplot=1,htmlplot=0,outdir='./_output'):
    """
    Example from Chapter 11 of LeVeque, Figure 11.8.
    Shows decay of an initial wave packet to an N-wave with Burgers' equation.
    """
    import numpy as np

    from clawpack import pyclaw
    from clawpack import riemann

    solver = pyclaw.ClawSolver1D(riemann.burgers_1D)

    solver.num_waves = 1
    solver.limiters = pyclaw.limiters.tvd.MC
    solver.bc_lower[0] = pyclaw.BC.periodic
    solver.bc_upper[0] = pyclaw.BC.periodic

    #===========================================================================
    # Initialize grids and then initialize the solution associated to the grid
    #===========================================================================
    x = pyclaw.Dimension('x',-8.0,8.0,1000)
    domain = pyclaw.Domain(x)
    num_eqn = 1
    state = pyclaw.State(domain,num_eqn)

    xc=domain.grid.x.centers
    state.q[0,:] = (xc>-np.pi)*(xc<np.pi)*(2.*np.sin(3.*xc)+np.cos(2.*xc)+0.2)
    state.q[0,:] = state.q[0,:]*(np.cos(xc)+1.)
    state.problem_data['efix']=True

    #===========================================================================
    # Setup controller and controller parameters. Then solve the problem
    #===========================================================================
    claw = pyclaw.Controller()
    claw.tfinal = 6.0
    claw.num_output_times   = 30
    claw.solution = pyclaw.Solution(state,domain)
    claw.solver = solver
    claw.outdir = outdir

    return claw

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(burgers)

########NEW FILE########
__FILENAME__ = setplot

""" 
Set up the plot figures, axes, and items to be done for each frame.

This module is imported by the plotting routines and then the
function setplot is called to set the plot parameters.
    
""" 

#--------------------------
def setplot(plotdata):
#--------------------------
    
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    
    """ 

    plotdata.clearfigures()  # clear any old figures,axes,items data


    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='q[0]', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes(name='Solution')
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = [-3., 6.]
    plotaxes.title = 'q[0]'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(name='solution', plot_type='1d')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    plotitem.show = True       # show on plot?
    
    # Parameters used only when creating html and/or latex hardcopy
    # e.g., via visclaw.frametools.printframes:

    plotdata.printfigs = True                # print figures
    plotdata.print_format = 'png'            # file format
    plotdata.print_framenos = 'all'          # list of frames to print
    plotdata.print_fignos = 'all'            # list of figures to print
    plotdata.html = True                     # create html files of plots?
    plotdata.latex = True                    # create latex file of plots?
    plotdata.latex_figsperline = 2           # layout of plots
    plotdata.latex_framesperline = 1         # layout of plots
    plotdata.latex_makepdf = False           # also run pdflatex?

    return plotdata

    

########NEW FILE########
__FILENAME__ = inclusion
#!/usr/bin/env python
# encoding: utf-8
r"""
Variable-coefficient elasticity example.
"""
import numpy as np
t0wall  = 0.025
tperiod = 0.05

def moving_wall_bc(state,dim,t,qbc,num_ghost):
    x = state.grid.x.centers_with_ghost(num_ghost)[:num_ghost]
    if t<t0wall:
        s = np.sin(np.pi*t/tperiod)
    else:
        s = 0.

    for i in range(num_ghost):
        # First reflect-extrapolate
        qbc[:,i,:] = qbc[:,2*num_ghost-i-1,:]
        # Now set velocity
        qbc[3,i,:] = 2.0*s - qbc[3,i,:]
        qbc[4,i,:] =       - qbc[4,i,:]
    

#def no_stress_bc(state,dim,t,qbc,num_ghost):
#    """No-stress boundary condition: sigma_{12} = sigma_{11} = 0"""
#    if state.grid.on_lower_boundary[idim]:
#        jghost = 
#    # First extrapolate
#    tmp = qbc[:,:,self.num_ghost]
#    tmp = np.tile(tmp,(1,1,num_ghost))
#    qbc[:,i,: = tmp
#
#    # Then negate the sig12 and sig11 components

def integrate_displacement(solver,state):
    aux[5,:,:] = aux[5,:,:] + dt*q[3,:,:]
    aux[6,:,:] = aux[6,:,:] + dt*q[4,:,:]


def inclusion():
    from clawpack import pyclaw
    from clawpack import riemann

    solver=pyclaw.ClawSolver2D(riemann.vc_elasticity_2D)
    solver.dimensional_split = False
    solver.transverse_waves = 2
    solver.limiters = pyclaw.limiters.tvd.MC


    mx = 200
    my = 100
    num_aux = 7
    domain = pyclaw.Domain( (0.,0.),(2.,1.),(mx,my) )
    state = pyclaw.State(domain,solver.num_eqn,num_aux)
    solution = pyclaw.Solution(state,domain)


    solver.bc_lower[0] = pyclaw.BC.custom
    solver.user_bc_lower=moving_wall_bc
    solver.bc_upper[0] = pyclaw.BC.extrap
    solver.bc_lower[1] = pyclaw.BC.periodic  # No stress
    solver.bc_upper[1] = pyclaw.BC.periodic  # No stress

    solver.aux_bc_lower[0] = pyclaw.BC.extrap
    solver.aux_bc_upper[0] = pyclaw.BC.extrap
    solver.aux_bc_lower[1] = pyclaw.BC.extrap
    solver.aux_bc_upper[1] = pyclaw.BC.extrap

    rho1 = 1.0
    lam1 = 200.
    mu1  = 100.

    rho2 = 1.0
    lam2 = 2.0
    mu2  = 1.0


    # set aux arrays
    #  aux[0,i,j] = density rho in (i,j) cell
    #  aux[1,i,j] = lambda in (i,j) cell
    #  aux[2,i,j] = mu in (i,j) cell
    #  aux[3,i,j] = cp in (i,j) cell
    #  aux[4,i,j] = cs in (i,j) cell
    #  aux[5,i,j] = xdisp in (i,j) cell
    #  aux[6,i,j] = ydisp in (i,j) cell

    xx,yy = domain.grid.p_centers
    inbar = (0.5<xx)*(xx<1.5)*(0.4<yy)*(yy<0.6)
    outbar = 1 - inbar
    aux = state.aux
    aux[0,:,:] = rho1 * inbar + rho2 * outbar
    aux[1,:,:] = lam1 * inbar + lam2 * outbar
    aux[2,:,:] = mu1  * inbar + mu2  * outbar
    bulk       = aux[1,:,:] + 2.*aux[2,:,:]
    aux[3,:,:] = np.sqrt(bulk/aux[0,:,:])
    aux[4,:,:] = np.sqrt(aux[2,:,:]/aux[0,:,:])
    aux[5,:,:] = 0.
    aux[6,:,:] = 0.


    # set initial condition
    state.q[:,:,:] = 0.


    claw = pyclaw.Controller()
    claw.solver = solver
    claw.solution = solution
    claw.num_output_times = 20
    claw.tfinal = 0.5

    return claw


if __name__ == '__main__':
    claw = inclusion()
    claw.run()

    from clawpack.pyclaw import plot
    plot.interactive_plot()


########NEW FILE########
__FILENAME__ = setplot

""" 
Set up the plot figures, axes, and items to be done for each frame.

This module is imported by the plotting routines and then the
function setplot is called to set the plot parameters.
    
""" 

import os
if os.path.exists('./1drad/_output'):
    qref_dir = os.path.abspath('./1drad/_output')
else:
    qref_dir = None
    print "Directory ./1drad/_output not found"


#--------------------------
def setplot(plotdata):
#--------------------------
    
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    
    """ 


    from clawpack.visclaw import colormaps

    plotdata.clearfigures()  # clear any old figures,axes,items data
    

    # Figure for pressure
    # -------------------

    plotfigure = plotdata.new_plotfigure(name='Pressure', figno=0)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = 'auto'
    plotaxes.title = 'Pressure'
    plotaxes.scaled = True      # so aspect ratio is 1

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 0
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True
    plotitem.show = True       # show on plot?
    

    # Figure for x-velocity plot
    # -----------------------
    
    plotfigure = plotdata.new_plotfigure(name='x-Velocity', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = 'auto'
    plotaxes.title = 'u'

    plotitem = plotaxes.new_plotitem(plot_type='2d_pcolor')
    plotitem.plot_var = 1
    plotitem.pcolor_cmap = colormaps.yellow_red_blue
    plotitem.add_colorbar = True
    plotitem.show = True       # show on plot?
    
    # Parameters used only when creating html and/or latex hardcopy
    # e.g., via visclaw.frametools.printframes:

    plotdata.printfigs = True                # print figures
    plotdata.print_format = 'png'            # file format
    plotdata.print_framenos = 'all'          # list of frames to print
    plotdata.print_fignos = 'all'            # list of figures to print
    plotdata.html = True                     # create html files of plots?
    plotdata.html_homelink = '../README.html'   # pointer for top of index
    plotdata.latex = True                    # create latex file of plots?
    plotdata.latex_figsperline = 2           # layout of plots
    plotdata.latex_framesperline = 1         # layout of plots
    plotdata.latex_makepdf = False           # also run pdflatex?

    return plotdata

########NEW FILE########
__FILENAME__ = acoustics_simple_waves
#!/usr/bin/env python
# encoding: utf-8
    
def fig_31_38(kernel_language='Fortran',solver_type='classic',iplot=False,htmlplot=False,outdir='./_output'):
    r"""Produces the output shown in Figures 3.1 and 3.8 of the FVM book.
    These involve simple waves in the acoustics system."""
    from clawpack import pyclaw
    import numpy as np

    #=================================================================
    # Import the appropriate solver type, depending on the options passed
    #=================================================================
    if solver_type=='classic':
        solver = pyclaw.ClawSolver1D()
    elif solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver1D()
    else: raise Exception('Unrecognized value of solver_type.')

    #========================================================================
    # Instantiate the solver and define the system of equations to be solved
    #========================================================================
    solver.kernel_language=kernel_language
    from clawpack.riemann import rp_acoustics
    solver.num_waves=rp_acoustics.num_waves
    if kernel_language=='Python': 
        solver.rp = rp_acoustics.rp_acoustics_1d
 
    solver.limiters = pyclaw.limiters.tvd.MC
    solver.bc_lower[0] = pyclaw.BC.wall
    solver.bc_upper[0] = pyclaw.BC.extrap

    #========================================================================
    # Instantiate the grid and set the boundary conditions
    #========================================================================
    x = pyclaw.Dimension('x',-1.0,1.0,800)
    grid = pyclaw.Grid(x)
    num_eqn = 2
    state = pyclaw.State(grid,num_eqn)

    #========================================================================
    # Set problem-specific variables
    #========================================================================
    rho = 1.0
    bulk = 0.25
    state.problem_data['rho']=rho
    state.problem_data['bulk']=bulk
    state.problem_data['zz']=np.sqrt(rho*bulk)
    state.problem_data['cc']=np.sqrt(bulk/rho)

    #========================================================================
    # Set the initial condition
    #========================================================================
    xc=grid.x.center
    beta=100; gamma=0; x0=0.75
    state.q[0,:] = 0.5*np.exp(-80 * xc**2) + 0.5*(np.abs(xc+0.2)<0.1)
    state.q[1,:] = 0.
    
    #========================================================================
    # Set up the controller object
    #========================================================================
    claw = pyclaw.Controller()
    claw.solution = pyclaw.Solution(state)
    claw.solver = solver
    claw.outdir = outdir
    claw.tfinal = 3.0
    claw.num_output_times   = 30

    # Solve
    status = claw.run()

    # Plot results
    if htmlplot:  pyclaw.plot.html_plot(outdir=outdir)
    if iplot:     pyclaw.plot.interactive_plot(outdir=outdir)

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(fig_31_38)

########NEW FILE########
__FILENAME__ = setplot

""" 
Set up the plot figures, axes, and items to be done for each frame.

This module is imported by the plotting routines and then the
function setplot is called to set the plot parameters.
    
""" 

#--------------------------
def setplot(plotdata):
#--------------------------
    
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    
    """ 


    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='Pressure', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.axescmd = 'subplot(211)'
    
    #plotaxes.xlimits = [0.,150.]
    plotaxes.ylimits = [-1.,1.0]
    plotaxes.title = 'Pressure'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    plotitem.show = True       # show on plot?
    plotitem.kwargs = {'linewidth':2,'markersize':5}
    


    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.axescmd = 'subplot(212)'
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = [-1.,1.]
    plotaxes.title = 'Velocity'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 1
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    plotitem.show = True       # show on plot?
    plotitem.kwargs = {'linewidth':3,'markersize':5}
    

    # Parameters used only when creating html and/or latex hardcopy
    # e.g., via visclaw.frametools.printframes:

    plotdata.printfigs = True                # print figures
    plotdata.print_format = 'png'            # file format
    plotdata.print_framenos = 'all'          # list of frames to print
    plotdata.print_fignos = 'all'            # list of figures to print
    plotdata.html = True                     # create html files of plots?
    plotdata.html_homelink = '../README.html'
    plotdata.latex = True                    # create latex file of plots?
    plotdata.latex_figsperline = 2           # layout of plots
    plotdata.latex_framesperline = 1         # layout of plots
    plotdata.latex_makepdf = False           # also run pdflatex?

    return plotdata

 

########NEW FILE########
__FILENAME__ = advection
#!/usr/bin/env python
# encoding: utf-8
IC='gauss_square'
if IC=='gauss_square':
    beta=200.; x0=0.3; mx=100
elif IC=='wavepacket':
    beta=100.; x0=0.5; mx=100

def fig_61_62_63(kernel_language='Python',iplot=False,htmlplot=False,solver_type='classic',outdir='./_output'):
    """
    Compare several methods for advecting a Gaussian and square wave.

    The settings coded here are for Figure 6.1(a).
    For Figure 6.1(b), set solver.order=2.
    For Figure 6.2(a), set solver.order=2 and solver.limiters = pyclaw.limiters.tvd.minmod
    For Figure 6.2(b), set solver.order=2 and solver.limiters = pyclaw.limiters.tvd.superbee
    For Figure 6.2(c), set solver.order=2 and solver.limiters = pyclaw.limiters.tvd.MC

    For Figure 6.3, set IC='wavepacket' and other options as appropriate.
    """
    import numpy as np
    from clawpack import pyclaw

    if solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver1D()
    else:
        solver = pyclaw.ClawSolver1D()

    solver.kernel_language = kernel_language
    from clawpack.riemann import rp_advection
    solver.num_waves = rp_advection.num_waves
    if solver.kernel_language=='Python': 
        solver.rp = rp_advection.rp_advection_1d

    solver.bc_lower[0] = 2
    solver.bc_upper[0] = 2
    solver.limiters = 0
    solver.order = 1
    solver.cfl_desired = 0.8

    x = pyclaw.Dimension('x',0.0,1.0,mx)
    grid = pyclaw.Grid(x)
    num_eqn = 1
    state = pyclaw.State(grid,num_eqn)
    state.problem_data['u']=1.

    xc=grid.x.center
    if IC=='gauss_square':
        state.q[0,:] = np.exp(-beta * (xc-x0)**2) + (xc>0.6)*(xc<0.8)
    elif IC=='wavepacket':
        state.q[0,:] = np.exp(-beta * (xc-x0)**2) * np.sin(80.*xc)
    else:
        raise Exception('Unrecognized initial condition specification.')

    claw = pyclaw.Controller()
    claw.solution = pyclaw.Solution(state)
    claw.solver = solver
    claw.outdir = outdir

    claw.tfinal =10.0
    status = claw.run()

    if htmlplot:  pyclaw.plot.html_plot(outdir=outdir)
    if iplot:     pyclaw.plot.interactive_plot(outdir=outdir)

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(fig_61_62_63)

########NEW FILE########
__FILENAME__ = setplot

""" 
Set up the plot figures, axes, and items to be done for each frame.

This module is imported by the plotting routines and then the
function setplot is called to set the plot parameters.
    
""" 
from advection import beta, x0, IC

#--------------------------
def setplot(plotdata):
#--------------------------
    
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    
    """ 


    plotdata.clearfigures()  # clear any old figures,axes,items data



    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='q[0]', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes(name='Solution')
    plotaxes.xlimits = 'auto'
    if IC=='gauss_square':
        plotaxes.ylimits = [-0.5, 1.5]
    elif IC=='wavepacket':
        plotaxes.ylimits = [-1.0, 1.5]
    plotaxes.title = 'q[0]'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(name='solution', plot_type='1d')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    plotaxes.afteraxes = plot_true_soln
    plotitem.show = True       # show on plot?
    
    # Parameters used only when creating html and/or latex hardcopy
    # e.g., via visclaw.frametools.printframes:

    plotdata.printfigs = True                # print figures
    plotdata.print_format = 'png'            # file format
    plotdata.print_framenos = 'all'          # list of frames to print
    plotdata.print_fignos = 'all'            # list of figures to print
    plotdata.html = True                     # create html files of plots?
    plotdata.latex = True                    # create latex file of plots?
    plotdata.latex_figsperline = 2           # layout of plots
    plotdata.latex_framesperline = 1         # layout of plots
    plotdata.latex_makepdf = False           # also run pdflatex?
    
    return plotdata


#-------------------
def plot_true_soln(current_data):
#-------------------
    from numpy import linspace, mod, exp, sin
    from pylab import plot
    xtrue = linspace(0.,1.,1000)
    t = current_data.t
    xshift = xtrue - t
    # periodic boundary conditions
    xshift = mod(xshift, 1.0)
    if IC=='gauss_square':
        x1 = 0.6; x2 = 0.8
        qtrue = exp(-beta * (xshift-x0)**2) + (xshift>0.6)*(xshift<0.8)
    elif IC=='wavepacket':
        qtrue = exp(-beta * (xshift-x0)**2) * sin(80.*xshift)
    plot(xtrue, qtrue, 'r')

########NEW FILE########
__FILENAME__ = acoustics
#!/usr/bin/env python
# encoding: utf-8
    
def acoustics(use_petsc=False,kernel_language='Fortran',solver_type='classic',iplot=False,htmlplot=False,outdir='./_output',weno_order=5):
    """
    This example solves the 1-dimensional acoustics equations in a homogeneous
    medium.
    """
    import numpy as np

    #=================================================================
    # Import the appropriate classes, depending on the options passed
    #=================================================================
    if use_petsc:
        import clawpack.petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if solver_type=='classic':
        solver = pyclaw.ClawSolver1D()
    elif solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver1D()
        solver.weno_order=weno_order
    else: raise Exception('Unrecognized value of solver_type.')

    #========================================================================
    # Instantiate the solver and define the system of equations to be solved
    #========================================================================
    solver.kernel_language=kernel_language
    from clawpack.riemann import rp_acoustics
    solver.num_waves=rp_acoustics.num_waves
    if kernel_language=='Python': 
        solver.rp = rp_acoustics.rp_acoustics_1d
 
    solver.limiters = pyclaw.limiters.tvd.MC
    solver.bc_lower[0] = pyclaw.BC.wall
    solver.bc_upper[0] = pyclaw.BC.wall

    solver.cfl_desired = 1.0
    solver.cfl_max     = 1.0

    #========================================================================
    # Instantiate the grid and set the boundary conditions
    #========================================================================
    x = pyclaw.Dimension('x',0.0,1.0,200)
    grid = pyclaw.Grid(x)
    num_eqn = 2
    state = pyclaw.State(grid,num_eqn)

    #========================================================================
    # Set problem-specific variables
    #========================================================================
    rho = 1.0
    bulk = 1.0
    state.problem_data['rho']=rho
    state.problem_data['bulk']=bulk
    state.problem_data['zz']=np.sqrt(rho*bulk)
    state.problem_data['cc']=np.sqrt(bulk/rho)

    #========================================================================
    # Set the initial condition
    #========================================================================
    xc=grid.x.center
    state.q[0,:] = np.cos(2*np.pi*xc)
    state.q[1,:] = 0.
    
    #========================================================================
    # Set up the controller object
    #========================================================================
    claw = pyclaw.Controller()
    claw.solution = pyclaw.Solution(state)
    claw.solver = solver
    claw.outdir = outdir
    claw.num_output_times = 40
    claw.tfinal = 2.0

    # Solve
    status = claw.run()

    # Plot results
    if htmlplot:  pyclaw.plot.html_plot(outdir=outdir)
    if iplot:     pyclaw.plot.interactive_plot(outdir=outdir)

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(acoustics)

########NEW FILE########
__FILENAME__ = setplot

""" 
Set up the plot figures, axes, and items to be done for each frame.

This module is imported by the plotting routines and then the
function setplot is called to set the plot parameters.
    
""" 

#--------------------------
def setplot(plotdata):
#--------------------------
    
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    
    """ 


    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='Pressure', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.axescmd = 'subplot(211)'
    
    #plotaxes.xlimits = [0.,150.]
    plotaxes.ylimits = [-1.,1.0]
    plotaxes.title = 'Pressure'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    plotitem.show = True       # show on plot?
    plotitem.kwargs = {'linewidth':2,'markersize':5}
    


    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.axescmd = 'subplot(212)'
    plotaxes.xlimits = 'auto'
    plotaxes.ylimits = [-1.,1.]
    plotaxes.title = 'Velocity'

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 1
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    plotitem.show = True       # show on plot?
    plotitem.kwargs = {'linewidth':3,'markersize':5}
    

    # Parameters used only when creating html and/or latex hardcopy
    # e.g., via visclaw.frametools.printframes:

    plotdata.printfigs = True                # print figures
    plotdata.print_format = 'png'            # file format
    plotdata.print_framenos = 'all'          # list of frames to print
    plotdata.print_fignos = 'all'            # list of figures to print
    plotdata.html = True                     # create html files of plots?
    plotdata.html_homelink = '../README.html'
    plotdata.latex = True                    # create latex file of plots?
    plotdata.latex_figsperline = 2           # layout of plots
    plotdata.latex_framesperline = 1         # layout of plots
    plotdata.latex_makepdf = False           # also run pdflatex?

    return plotdata

 

########NEW FILE########
__FILENAME__ = acoustics
#!/usr/bin/env python
# encoding: utf-8
    
def acoustics(solver_type='classic',iplot=True,htmlplot=False,outdir='./_output',problem='figure 9.4'):
    """
    This example solves the 1-dimensional variable-coefficient acoustics
    equations in a medium with a single interface.
    """
    from numpy import sqrt, abs

    from clawpack import pyclaw

    if solver_type=='classic':
        solver = pyclaw.ClawSolver1D()
    elif solver_type=='sharpclaw':
        solver = pyclaw.SharpClawSolver1D()
    else: raise Exception('Unrecognized value of solver_type.')

    solver.num_waves=2
    solver.limiters = pyclaw.limiters.tvd.MC
    solver.bc_lower[0] = pyclaw.BC.extrap
    solver.bc_upper[0] = pyclaw.BC.extrap
    solver.aux_bc_lower[0] = pyclaw.BC.extrap
    solver.aux_bc_upper[0] = pyclaw.BC.extrap

    x = pyclaw.Dimension('x',-5.0,5.0,500)
    grid = pyclaw.Grid(x)
    num_eqn = 2
    num_aux = 2
    state = pyclaw.State(grid,num_eqn,num_aux)

    if problem == 'figure 9.4':
        rhol = 1.0
        cl   = 1.0
        rhor = 2.0
        cr   = 0.5
    elif problem == 'figure 9.5':
        rhol = 1.0
        cl   = 1.0
        rhor = 4.0
        cr   = 0.5
    zl = rhol*cl
    zr = rhor*cr
    xc = grid.x.center

    state.aux[0,:] = (xc<=0)*zl + (xc>0)*zr  # Impedance
    state.aux[1,:] = (xc<=0)*cl + (xc>0)*cr  # Sound speed

    # initial condition: half-ellipse
    state.q[0,:] = sqrt(abs(1.-(xc+3.)**2))*(xc>-4.)*(xc<-2.)
    state.q[1,:] = state.q[0,:] + 0.

    claw = pyclaw.Controller()
    claw.solution = pyclaw.Solution(state)
    claw.solver = solver
    claw.tfinal = 5.0
    claw.num_output_times   = 10

    # Solve
    status = claw.run()

    # Plot results
    if htmlplot:  pyclaw.plot.html_plot(outdir=outdir)
    if iplot:     pyclaw.plot.interactive_plot(outdir=outdir)

if __name__=="__main__":
    from clawpack.pyclaw.util import run_app_from_main
    output = run_app_from_main(acoustics)

########NEW FILE########
__FILENAME__ = setplot

""" 
Set up the plot figures, axes, and items to be done for each frame.

This module is imported by the plotting routines and then the
function setplot is called to set the plot parameters.
    
""" 

#--------------------------
def setplot(plotdata):
#--------------------------
    
    """ 
    Specify what is to be plotted at each frame.
    Input:  plotdata, an instance of visclaw.data.ClawPlotData.
    Output: a modified version of plotdata.
    
    """ 


    plotdata.clearfigures()  # clear any old figures,axes,items data

    # Figure for q[0]
    plotfigure = plotdata.new_plotfigure(name='Pressure', figno=1)

    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.axescmd = 'subplot(211)'
    
    plotaxes.xlimits = [-5.,5.]
    plotaxes.ylimits = [-.2,1.5]
    plotaxes.title = 'Pressure'
    plotaxes.afteraxes = plotint

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 0
    plotitem.plotstyle = '-o'
    plotitem.color = 'b'
    plotitem.show = True       # show on plot?
    plotitem.kwargs = {'linewidth':2,'markersize':5}
    


    # Set up for axes in this figure:
    plotaxes = plotfigure.new_plotaxes()
    plotaxes.axescmd = 'subplot(212)'
    plotaxes.xlimits = [-5.,5.]
    plotaxes.ylimits = [-.5,1.1]
    plotaxes.title = 'Velocity'
    plotaxes.afteraxes = plotint

    # Set up for item on these axes:
    plotitem = plotaxes.new_plotitem(plot_type='1d_plot')
    plotitem.plot_var = 1
    plotitem.plotstyle = '-'
    plotitem.color = 'b'
    plotitem.show = True       # show on plot?
    plotitem.kwargs = {'linewidth':3,'markersize':5}
    

    # Parameters used only when creating html and/or latex hardcopy
    # e.g., via visclaw.frametools.printframes:

    plotdata.printfigs = True                # print figures
    plotdata.print_format = 'png'            # file format
    plotdata.print_framenos = 'all'          # list of frames to print
    plotdata.print_fignos = 'all'            # list of figures to print
    plotdata.html = True                     # create html files of plots?
    plotdata.html_homelink = '../README.html'
    plotdata.latex = True                    # create latex file of plots?
    plotdata.latex_figsperline = 2           # layout of plots
    plotdata.latex_framesperline = 1         # layout of plots
    plotdata.latex_makepdf = False           # also run pdflatex?

    return plotdata

def plotint(current_data):
    import matplotlib.pyplot as plt
    plt.plot([0,0],[-0.5,1.5],'--')

########NEW FILE########
__FILENAME__ = cfl
r"""
Module for the CFL object.
"""
class CFL(object):
    """ Parallel CFL object, responsible for computing the
    Courant-Friedrichs-Lewy condition across all processes.
    """

    def __init__(self, global_max):
        from petsc4py import PETSc
        self._local_max = global_max
        self._global_max = global_max
        self._reduce_vec = PETSc.Vec().createWithArray([0])
        
    def get_global_max(self):
        r"""
        Compute the maximum CFL number over all processes for the current step.

        This is used to determine whether the CFL condition was
        violated and adjust the timestep.
        """
        self._reduce_vec.array = self._local_max
        self._global_max = self._reduce_vec.max()[1]
        return self._global_max

    def get_cached_max(self):
        return self._global_max

    def set_local_max(self,new_local_max):
        self._local_max = new_local_max

    def update_global_max(self,new_local_max):
        self._reduce_vec.array = new_local_max
        self._global_max = self._reduce_vec.max()[1]


########NEW FILE########
__FILENAME__ = solver
r"""
Module containing the PetClaw solvers

This file currently only exists so that these solvers have a different
__module__ property, used by pyclaw.solver.Solver.__init__ to
determine the containing claw_package to use.
"""

from __future__ import absolute_import
from clawpack import pyclaw

class ClawSolver1D(pyclaw.ClawSolver1D):
    r"""
    Parallel solver for 1D problems using classic Clawpack algorithms.
    """

    __doc__ += pyclaw.util.add_parent_doc(pyclaw.ClawSolver1D)

class ClawSolver2D(pyclaw.ClawSolver2D):
    r"""
    Parallel solver for 2D problems using classic Clawpack algorithms.
    """

    __doc__ += pyclaw.util.add_parent_doc(pyclaw.ClawSolver2D)
    
class ClawSolver3D(pyclaw.ClawSolver3D):
    r"""
    Parallel solver for 3D problems using classic Clawpack algorithms.
    """

    __doc__ += pyclaw.util.add_parent_doc(pyclaw.ClawSolver3D)

########NEW FILE########
__FILENAME__ = controller
"""
Module for PetClaw controller class.
"""

from clawpack import pyclaw

class Controller(pyclaw.controller.Controller):
    """ Parallel Controller Class

    Defaults to petsc output_format, logs only from process 0.
    """
    
    __doc__ += pyclaw.util.add_parent_doc(pyclaw.controller.Controller)

    def __init__(self):
        super(Controller,self).__init__()

        self.output_format = 'petsc'

    def is_proc_0(self):
        from petsc4py import PETSc
        rank = PETSc.Comm.getRank(PETSc.COMM_WORLD)
        return rank == 0

    def log_info(self, str):
        import logging
        if self.is_proc_0():
            logging.info(str)
        else:
            pass

########NEW FILE########
__FILENAME__ = geometry
#!/usr/bin/env python
# encoding: utf-8
r"""
Module containing petclaw.geometry.
"""

from clawpack import pyclaw
from clawpack.pyclaw import geometry as pyclaw_geometry

class Patch(pyclaw_geometry.Patch):
    """Parallel Patch class.
    """

    __doc__ += pyclaw.util.add_parent_doc(pyclaw_geometry.Patch)
    
    def __init__(self,dimensions):
        
        super(Patch,self).__init__(dimensions)

        self._da = self._create_DA()
        ranges = self._da.getRanges()
        grid_dimensions = []
        for i,nrange in enumerate(ranges):
            lower = self.lower_global[i] + nrange[0]*self.delta[i]
            upper = self.lower_global[i] + nrange[1]*self.delta[i]
            num_cells   = nrange[1]-nrange[0]

            grid_dimensions.append(pyclaw_geometry.Dimension(lower,upper,
                                        num_cells,name=dimensions[i].name))


            if nrange[0] == 0:
                grid_dimensions[-1].on_lower_boundary = True
            else:
                grid_dimensions[-1].on_lower_boundary = False

            if nrange[1] == self.num_cells_global[i]:
                grid_dimensions[-1].on_upper_boundary = True
            else:
                grid_dimensions[-1].on_upper_boundary = False  

        self.grid = pyclaw_geometry.Grid(grid_dimensions)

    def _create_DA(self):
        r"""Returns a PETSc DA and associated global Vec.
        Note that no local vector is returned.
        """
        from petsc4py import PETSc

        if hasattr(PETSc.DA, 'PeriodicType'):
            if self.num_dim == 1:
                periodic_type = PETSc.DA.PeriodicType.X
            elif self.num_dim == 2:
                periodic_type = PETSc.DA.PeriodicType.XY
            elif self.num_dim == 3:
                periodic_type = PETSc.DA.PeriodicType.XYZ
            else:
                raise Exception("Invalid number of dimensions")

            DA = PETSc.DA().create(dim=self.num_dim,
                                          dof=1,
                                          sizes=self.num_cells_global,
                                          periodic_type = periodic_type,
                                          stencil_width=0,
                                          comm=PETSc.COMM_WORLD)
        else:
            DA = PETSc.DA().create(dim=self.num_dim,
                                          dof=1,
                                          sizes=self.num_cells_global,
                                          boundary_type = PETSc.DA.BoundaryType.PERIODIC,
                                          stencil_width=0,
                                          comm=PETSc.COMM_WORLD)

        return DA

# ============================================================================
#  PetClaw Domain object definition
# ============================================================================
class Domain(pyclaw_geometry.Domain):
    r""" Parallel Domain Class    
    """
    
    __doc__ += pyclaw.util.add_parent_doc(pyclaw.ClawSolver2D)

    def __init__(self,geom):
        if not isinstance(geom,list):
            geom = [geom]
        if isinstance(geom[0],Patch):
            self.patches = geom
        elif isinstance(geom[0],pyclaw_geometry.Dimension):
            self.patches = [Patch(geom)]



########NEW FILE########
__FILENAME__ = petsc
#!/usr/bin/env python
# encoding: utf-8
r"""
Routines for reading and writing a petsc-style output file.

These routines preserve petclaw/pyclaw syntax for i/o while taking advantage of
PETSc's parallel i/o capabilities to allow for parallel reads and writes of
frame data.
"""

from petsc4py import PETSc
import pickle
import os
    

def write(solution,frame,path='./',file_prefix='claw',write_aux=False,
          options={},write_p=False):
    r"""
        Write out pickle and PETSc data files representing the
        solution.  Common data is written from process 0 in pickle
        files.  Shared data is written from all processes into PETSc
        data files.
        
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) pyclaw
       object to be output
     - *frame* - (int) Frame number
     - *path* - (string) Root path
     - *file_prefix* - (string) Prefix for the file name. ``default =
        'claw'``
     - *write_aux* - (bool) Boolean controlling whether the associated 
       auxiliary array should be written out. ``default = False``     
     - *options* - (dict) Optional argument dictionary, see 
        `PETScIO Option Table`_
     
     .. _`PETScIO Option Table`:
     
     format   : one of 'ascii' or 'binary'
     clobber  : if True (Default), files will be overwritten
    """    
    # Option parsing
    option_defaults = {'format':'binary','clobber':True}
  
    for k in option_defaults.iterkeys():
        if options.has_key(k):
            pass
        else:
            options[k] = option_defaults[k]
 
    clobber = options['clobber']
    file_format = options['format']

    if solution.num_aux == 0:
        write_aux = False

    filenames = set_filenames(frame,path,file_format,file_prefix,write_aux)
       
    if not clobber:
        for f in filenames.values():
            if os.path.exists(f):
                raise IOError('Cowardly refusing to clobber %s!' % f)

    rank =  PETSc.Comm.getRank(PETSc.COMM_WORLD)
    if rank==0:
        metadata_file = open(filenames['metadata'],'wb')
        # explicitly dumping a dictionary here to help out anybody trying to read the pickle file
        sol_dict = {'t':solution.t,'num_eqn':solution.num_eqn,'nstates':len(solution.states),
                         'num_aux':solution.num_aux,'num_dim':solution.domain.num_dim,
                         'write_aux':write_aux,
                         'problem_data' : solution.problem_data,
                         'mapc2p': solution.state.grid.mapc2p,
                         'file_format':file_format}
        if write_p:
            sol_dict['num_eqn'] = solution.mp

        pickle.dump(sol_dict, metadata_file)

    q_viewer, aux_viewer = set_up_viewers(filenames,file_format.lower(),
                                          write_aux,PETSc.Viewer.Mode.WRITE)

    
    for state in solution.states:
        patch = state.patch
        if rank==0:
            pickle.dump({'level':patch.level,
                         'names':patch.name,'lower':patch.lower_global,
                         'num_cells':patch.num_cells_global,'delta':patch.delta}, metadata_file)
#       we will reenable this bad boy when we switch over to petsc-dev
#        state.q_da.view(q_viewer)
        if write_p:
            state.gpVec.view(q_viewer)
        else:
            state.gqVec.view(q_viewer)
        
        if write_aux:
            state.gauxVec.view(aux_viewer)
    
    q_viewer.flush()
    if aux_viewer is not None:
        aux_viewer.flush()
    q_viewer.destroy() # Destroys aux_viewer also
    if rank==0:
        metadata_file.close()


def read(solution,frame,path='./',file_prefix='claw',read_aux=False,options={}):
    r"""
    Read in pickles and PETSc data files representing the solution
    
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) Solution object to 
       read the data into.
     - *frame* - (int) Frame number to be read in
     - *path* - (string) Path to the current directory of the file
     - *file_prefix* - (string) Prefix of the files to be read in.  
       ``default = 'fort'``
     - *read_aux* (bool) Whether or not an auxiliary file will try to be read 
       in.  ``default = False``
     - *options* - (dict) Optional argument dictionary, see 
       `PETScIO Option Table`_
    
    .. _`PETScIO Option Table`:
    
    format   : one of 'ascii' or 'binary'
     
    """

    if options.has_key('format'):
        file_format = options['format']
    else:
        file_format = 'binary'

    filenames = set_filenames(frame,path,file_format,file_prefix,read_aux)

    if read_aux:
        if not os.path.exists(filenames['aux']):
            # If no aux file for this frame, assume it is time-independent
            filenames['aux'] = os.path.join(path, '%s_aux.ptc' % file_prefix) + str(0).zfill(4)

    try:
        metadata_file = open(filenames['metadata'],'rb')
    except IOError:
        print "Error: file " + filenames['metadata'] + " does not exist or is unreadable."
        raise

    # this dictionary is mostly holding debugging information, only nstates is needed
    # most of this information is explicitly saved in the individual patches
    value_dict = pickle.load(metadata_file)
    nstates    = value_dict['nstates']                    
    num_dim       = value_dict['num_dim']
    num_aux       = value_dict['num_aux']
    num_eqn       = value_dict['num_eqn']

    if read_aux and not os.path.exists(filenames['aux']):
        # Don't abort if aux file is missing
        from warnings import warn
        aux_file_path = os.path.join(path,filenames['aux'])
        warn('read_aux=True but aux file %s does not exist' % aux_file_path)
        read_aux = False

    q_viewer, aux_viewer = set_up_viewers(filenames,file_format.lower(),
                                          read_aux,PETSc.Viewer.Mode.READ)

    patches = []
    for m in xrange(nstates):
        patch_dict = pickle.load(metadata_file)

        level   = patch_dict['level']
        names   = patch_dict['names']
        lower   = patch_dict['lower']
        n       = patch_dict['num_cells']
        d       = patch_dict['delta']

        from clawpack import petclaw
        dimensions = []
        for i in xrange(num_dim):
            dimensions.append(
                petclaw.Dimension(names[i],lower[i],lower[i] + n[i]*d[i],n[i]))
        patch = petclaw.Patch(dimensions)
        patch.level = level 
        state = petclaw.State(patch,num_eqn,num_aux)
        state.t = value_dict['t']
        state.problem_data = value_dict.get('problem_data',{})
        if value_dict.has_key('mapc2p'):
            # If no mapc2p is provided, leave the default identity map in grid
            state.grid.mapc2p = value_dict['mapc2p']

#       DA View/Load is broken in Petsc-3.1.8, we can load/view the DA if needed in petsc-3.2
#       state.q_da.load(q_viewer)
        state.gqVec.load(q_viewer)
        
        if read_aux:
            state.gauxVec.load(aux_viewer)
        
        solution.states.append(state)
        patches.append(state.patch)
    solution.domain = petclaw.geometry.Domain(patches)

    metadata_file.close()
    q_viewer.destroy() # Destroys aux_viewer also


def read_t(frame,path='./',file_prefix='claw'):
    r"""Read only the petsc.pkl file and return the data
    
    :Input:
     - *frame* - (int) Frame number to be read in
     - *path* - (string) Path to the current directory of the file
     - *file_prefix* - (string) Prefix of the files to be read in.  
       ``default = 'claw'``
     
    :Output:
     - (list) List of output variables
      - *t* - (int) Time of frame
      - *num_eqn* - (int) Number of equations in the frame
      - *npatches* - (int) Number of patches
      - *num_aux* - (int) Auxillary value in the frame
      - *num_dim* - (int) Number of dimensions in q and aux
    
    """
    import logging
    logger = logging.getLogger('io')

    base_path = os.path.join(path,)
    path = os.path.join(base_path, '%s.pkl' % file_prefix) + str(frame).zfill(4)
    try:
        f = open(path,'rb')
    except IOError:
        print "Error: file " + path + " does not exist or is unreadable."
        raise
    logger.debug("Opening %s file." % path)
    patch_dict = pickle.load(f)

    t      = patch_dict['t']
    num_eqn   = patch_dict['num_eqn']
    nstates = patch_dict['nstates']                    
    num_aux   = patch_dict['num_aux']                    
    num_dim   = patch_dict['num_dim']

    f.close()
        
    return t,num_eqn,nstates,num_aux,num_dim


def set_up_viewers(filenames,file_format,do_aux,mode):
    v = PETSc.Viewer()
    opts = {}
    if file_format == 'ascii':
        create_viewer = v.createASCII
    elif file_format == 'vtk':
        create_viewer = v.createASCII
        opts['format'] = PETSc.Viewer.Format.ASCII_VTK
    elif file_format == 'hdf5':
        create_viewer = v.createHDF5
    elif file_format == 'netcdf':
        create_viewer = v.createNetCDF
    elif file_format == 'binary':
        if hasattr(PETSc.Viewer,'createMPIIO'):
            create_viewer = v.createMPIIO
        else:
            create_viewer = v.createBinary
    else:
        raise IOError('PETSc has no viewer for the output format %s ' % file_format)

    q_viewer = create_viewer(filenames['q'], mode, **opts)
    if do_aux:
        aux_viewer = create_viewer(filenames['aux'], mode, **opts)
    else: 
        aux_viewer = None

    return q_viewer, aux_viewer


def set_filenames(frame,path,file_format,file_prefix,do_aux):
    filenames = {}
    filenames['metadata'] = os.path.join(path, '%s.pkl' % file_prefix) + str(frame).zfill(4)
    if file_format == 'vtk':
        filenames['q'] = os.path.join(path, file_prefix+str(frame).zfill(4)+'.vtk')
    else:
        filenames['q'] = os.path.join(path, '%s.ptc' % file_prefix) + str(frame).zfill(4)

    if do_aux:
        filenames['aux'] = os.path.join(path, '%s_aux.ptc' % file_prefix) + str(frame).zfill(4)

    return filenames

########NEW FILE########
__FILENAME__ = plot
def interactive_plot(outdir='./_output',file_format='petsc',setplot=None):
    """
    Convenience function for launching an interactive plotting session.
    """
    from clawpack.pyclaw.plot import plot
    plot(setplot,outdir=outdir,file_format=file_format,iplot=True,htmlplot=False)

def html_plot(outdir='./_output',file_format='petsc',setplot=None):
    """
    Convenience function for creating html page with plots.
    """
    from clawpack.pyclaw.plot import plot
    plot(setplot,outdir=outdir,file_format=file_format,htmlplot=True,iplot=False)

def plotPetsc(clawobj,delay=1):
    """
    Takes either a controller or solution object and prints each frame
    using PETSc.Viewer.
    """
    from petsc4py import PETSc
    from clawpack.pyclaw import controller, solution

    if isinstance(clawobj,controller.Controller):
        for n in xrange(0,clawobj.num_output_times):
            sol = clawobj.frames[n]
            viewer = PETSc.Viewer.DRAW(sol.patch.gqVec.comm)
            OptDB = PETSc.Options()
            OptDB['draw_pause'] = delay
            viewer(sol.patch.gqVec)

    elif isinstance(clawobj,solution.Solution):
        viewer = PETSc.Viewer.DRAW(clawobj.patch.gqVec.comm)
        OptDB = PETSc.Options()
        OptDB['draw_pause'] = -1
        viewer(clawobj.patch.gqVec)



########NEW FILE########
__FILENAME__ = solver
#!/usr/bin/env python
# encoding: utf-8
r"""
Module containing SharpClaw solvers for PetClaw
"""

from __future__ import absolute_import
from clawpack import pyclaw

class SharpClawSolver1D(pyclaw.SharpClawSolver1D):
    """1D parallel SharpClaw solver.
    """

    __doc__ += pyclaw.util.add_parent_doc(pyclaw.SharpClawSolver2D)

    
class SharpClawSolver2D(pyclaw.SharpClawSolver2D):
    """2D parallel SharpClaw solver. 
    """

    __doc__ += pyclaw.util.add_parent_doc(pyclaw.SharpClawSolver2D)


class SharpClawSolver3D(pyclaw.SharpClawSolver3D):
    """3D parallel SharpClaw solver. 
    """

    __doc__ += pyclaw.util.add_parent_doc(pyclaw.SharpClawSolver3D)

########NEW FILE########
__FILENAME__ = solution
from clawpack import pyclaw
from clawpack.pyclaw.solution import Solution

class Solution(Solution):
    """ Parallel Solution class.
    """
    __doc__ += pyclaw.util.add_parent_doc(pyclaw.Solution)

########NEW FILE########
__FILENAME__ = state
import clawpack.pyclaw

class State(clawpack.pyclaw.State):
    """Parallel State class"""

    __doc__ += clawpack.pyclaw.util.add_parent_doc(clawpack.pyclaw.state)

    @property
    def num_eqn(self):
        r"""(int) - Number of unknowns (components of q)"""
        if self.q_da is None:
            raise Exception('state.num_eqn has not been set.')
        else: return self.q_da.dof

    @property
    def mp(self):
        r"""(int) - Number of derived quantities (components of p)"""
        if self._p_da is None:
            raise Exception('state.mp has not been set.')
        else: return self._p_da.dof
    @mp.setter
    def mp(self,mp):
        if self._p_da is not None:
            raise Exception('You cannot change state.mp after p is initialized.')
        else:
            self._p_da = self._create_DA(mp)
            self.gpVec = self._p_da.createGlobalVector()

    @property
    def mF(self):
        r"""(int) - Number of derived quantities (components of p)"""
        if self._F_da is None:
            raise Exception('state.mF has not been set.')
        else: return self._F_da.dof
    @mF.setter
    def mF(self,mF):
        if self._F_da is not None:
            raise Exception('You cannot change state.mp after p is initialized.')
        else:
            self._F_da = self._create_DA(mF)
            self.gFVec = self._F_da.createGlobalVector()

    @property
    def num_aux(self):
        r"""(int) - Number of auxiliary fields"""
        if self.aux_da is None: return 0
        else: return self.aux_da.dof

    @property
    def q(self):
        r"""
        Array to store solution (q) values.

        Settting state.num_eqn automatically allocates space for q, as does
        setting q itself.
        """
        if self.q_da is None: return 0
        shape = self.grid.num_cells
        shape.insert(0,self.num_eqn)
        q=self.gqVec.getArray().reshape(shape, order = 'F')
        return q
    @q.setter
    def q(self,val):
        num_eqn = val.shape[0]
        if self.gqVec is None: self._init_q_da(num_eqn)
        self.gqVec.setArray(val.reshape([-1], order = 'F'))

    @property
    def p(self):
        r"""
        Array containing values of derived quantities for output.
        """
        if self._p_da is None: return 0
        shape = self.grid.num_cells
        shape.insert(0,self.mp)
        p=self.gpVec.getArray().reshape(shape, order = 'F')
        return p
    @p.setter
    def p(self,val):
        mp = val.shape[0]
        if self.gpVec is None: self.init_p_da(mp)
        self.gpVec.setArray(val.reshape([-1], order = 'F'))

    @property
    def F(self):
        r"""
        Array containing pointwise values (densities) of output functionals.
        This is just used as temporary workspace before summing.
        """
        if self._F_da is None: return 0
        shape = self.grid.num_cells
        shape.insert(0,self.mF)
        F=self.gFVec.getArray().reshape(shape, order = 'F')
        return F
    @F.setter
    def fset(self,val):
        mF = val.shape[0]
        if self.gFVec is None: self.init_F_da(mF)
        self.gFVec.setArray(val.reshape([-1], order = 'F'))

    @property
    def aux(self):
        """
        We never communicate aux values; every processor should set its own ghost cell
        values for the aux array.  The global aux vector is used only for outputting
        the aux values to file; everywhere else we use the local vector.
        """
        if self.aux_da is None: return None
        shape = self.grid.num_cells
        shape.insert(0,self.num_aux)
        aux=self.gauxVec.getArray().reshape(shape, order = 'F')
        return aux
    @aux.setter
    def aux(self,val):
        # It would be nice to make this work also for parallel
        # loading from a file.
        if self.aux_da is None: 
            num_aux=val.shape[0]
            self._init_aux_da(num_aux)
        self.gauxVec.setArray(val.reshape([-1], order = 'F'))
    @property
    def num_dim(self):
        return self.patch.num_dim


    def __init__(self,geom,num_eqn,num_aux=0):
        r"""
        Here we don't call super because q and aux must be properties in PetClaw
        but should not be properties in PyClaw.

        :attributes:
        patch - The patch this state lives on
        """

        from clawpack.pyclaw import geometry
        if isinstance(geom,geometry.Patch):
            self.patch = geom
        elif isinstance(geom,geometry.Domain):
            self.patch = geom.patches[0]
        else:
            raise Exception("""A PetClaw State object must be initialized with
                             a PyClaw Patch or Domain object.""")

        self.aux_da = None
        self.q_da = None

        self._p_da = None
        self.gpVec = None

        self._F_da = None
        self.gFVec = None

        # ========== Attribute Definitions ===================================
        self.problem_data = {}
        r"""(dict) - Dictionary of global values for this patch, 
            ``default = {}``"""
        self.t=0.
        r"""(float) - Current time represented on this patch, 
            ``default = 0.0``"""
        self.index_capa = -1
        self.keep_gauges = False
        r"""(bool) - Keep gauge values in memory for every time step, 
        ``default = False``"""
        self.gauge_data = []
        r"""(list) - List of numpy.ndarray objects. Each element of the list
        stores the values of the corresponding gauge if ``keep_gauges`` is set
        to ``True``"""

        self._init_q_da(num_eqn)
        if num_aux>0: self._init_aux_da(num_aux)

    def _init_aux_da(self,num_aux,num_ghost=0):
        r"""
        Initializes PETSc DA and global & local Vectors for handling the
        auxiliary array, aux. 
        
        Initializes aux_da, gauxVec and lauxVec.
        """
        self.aux_da = self._create_DA(num_aux,num_ghost)
        self.gauxVec = self.aux_da.createGlobalVector()
        self.lauxVec = self.aux_da.createLocalVector()
 
    def _init_q_da(self,num_eqn,num_ghost=0):
        r"""
        Initializes PETSc DA and Vecs for handling the solution, q. 
        
        Initializes q_da, gqVec and lqVec.
        """
        self.q_da = self._create_DA(num_eqn,num_ghost)
        self.gqVec = self.q_da.createGlobalVector()
        self.lqVec = self.q_da.createLocalVector()

    def _create_DA(self,dof,num_ghost=0):
        r"""Returns a PETSc DA and associated global Vec.
        Note that no local vector is returned.
        """
        from petsc4py import PETSc

        #Due to the way PETSc works, we just make the patch always periodic,
        #regardless of the boundary conditions actually selected.
        #This works because in solver.qbc() we first call globalToLocal()
        #and then impose the real boundary conditions (if non-periodic).

        if hasattr(PETSc.DA, 'PeriodicType'):
            if self.num_dim == 1:
                periodic_type = PETSc.DA.PeriodicType.X
            elif self.num_dim == 2:
                periodic_type = PETSc.DA.PeriodicType.XY
            elif self.num_dim == 3:
                periodic_type = PETSc.DA.PeriodicType.XYZ
            else:
                raise Exception("Invalid number of dimensions")

            DA = PETSc.DA().create(dim=self.num_dim,
                                          dof=dof,
                                          sizes=self.patch.num_cells_global,
                                          periodic_type = periodic_type,
                                          stencil_width=num_ghost,
                                          comm=PETSc.COMM_WORLD)
        else:
            DA = PETSc.DA().create(dim=self.num_dim,
                                          dof=dof,
                                          sizes=self.patch.num_cells_global,
                                          boundary_type = PETSc.DA.BoundaryType.PERIODIC,
                                          stencil_width=num_ghost,
                                          comm=PETSc.COMM_WORLD)

        return DA


    def get_qbc_from_q(self,num_ghost,qbc):
        """
        Returns q with ghost cells attached, by accessing the local vector.
        """
        shape = [n + 2*num_ghost for n in self.grid.num_cells]
        
        self.q_da.globalToLocal(self.gqVec, self.lqVec)
        shape.insert(0,self.num_eqn)
        return self.lqVec.getArray().reshape(shape, order = 'F')
            
    def get_auxbc_from_aux(self,num_ghost,auxbc):
        """
        Returns aux with ghost cells attached, by accessing the local vector.
        """
        shape = [n + 2*num_ghost for n in self.grid.num_cells]
        
        self.aux_da.globalToLocal(self.gauxVec, self.lauxVec)
        shape.insert(0,self.num_aux)
        return self.lauxVec.getArray().reshape(shape, order = 'F')

    def set_num_ghost(self,num_ghost):
        r"""
        This is a hack to deal with the fact that petsc4py
        doesn't allow us to change the stencil_width (num_ghost).

        Instead, we initially create DAs with stencil_width=0.
        Then, in solver.setup(), we call this function to replace
        those DAs with new ones that have the right stencil width.

        This could be made more efficient using some PETSc calls,
        but it only happens once so it seems not to be worth it.
        """
        q0 = self.q.copy()
        self._init_q_da(self.num_eqn,num_ghost)
        self.q = q0

        if self.aux is not None:
            aux0 = self.aux.copy()
            self._init_aux_da(self.num_aux,num_ghost)
            self.aux = aux0

    def sum_F(self,i):
        return self.gFVec.strideNorm(i,0)

    def get_q_global(self):
        r"""
        Returns a copy of the global q array on process 0, otherwise returns None
        """
        from petsc4py import PETSc
        q_natural = self.q_da.createNaturalVec()
        self.q_da.globalToNatural(self.gqVec, q_natural)
        scatter, q0Vec = PETSc.Scatter.toZero(q_natural)
        scatter.scatter(q_natural, q0Vec, False, PETSc.Scatter.Mode.FORWARD)
        rank = PETSc.COMM_WORLD.getRank()
        if rank == 0:
            shape = self.patch.num_cells_global
            shape.insert(0,self.num_eqn)
            q0=q0Vec.getArray().reshape(shape, order = 'F').copy()
        else:
            q0=None
        
        scatter.destroy()
        q0Vec.destroy()

        return q0

    def get_aux_global(self):
        r"""
        Returns a copy of the global aux array on process 0, otherwise returns None
        """
        from petsc4py import PETSc
        aux_natural = self.aux_da.createNaturalVec()
        self.aux_da.globalToNatural(self.gauxVec, aux_natural)
        scatter, aux0Vec = PETSc.Scatter.toZero(aux_natural)
        scatter.scatter(aux_natural, aux0Vec, False, PETSc.Scatter.Mode.FORWARD)
        rank = PETSc.COMM_WORLD.getRank()
        if rank == 0:
            shape = self.patch.num_cells_global
            shape.insert(0,self.num_aux)
            aux0=aux0Vec.getArray().reshape(shape, order = 'F').copy()
        else:
            aux0=None
        
        scatter.destroy()
        aux0Vec.destroy()

        return aux0

########NEW FILE########
__FILENAME__ = fcompiler

def get_fcompiler():
    import numpy.distutils.fcompiler
    numpy.distutils.log.set_verbosity(-1)
    fc = numpy.distutils.fcompiler.new_fcompiler()
    fc.customize()
    return fc

if __name__=="__main__":
    fc = get_fcompiler()
    import sys
    if sys.argv[1] == 'get_compiler':
        print fc.compiler_f77[0]
    elif sys.argv[1] == 'get_flags':
        print ' '.join(fc.compiler_f77[1:])

########NEW FILE########
__FILENAME__ = cfl
r"""
Module for the CFL object, which is responsible for computing and enforcing the
Courant-Friedrichs-Lewy condition.
"""

class CFL(object):
    def __init__(self, global_max):
        self._global_max = global_max
        
    def get_global_max(self):
        r"""
        Compute the maximum CFL number over all processes for the current step.

        This is used to determine whether the CFL condition was
        violated and adjust the timestep.
        """
        return self._global_max

    def get_cached_max(self):
        return self._global_max

    def set_local_max(self,new_local_max):
        self._global_max = new_local_max

    def update_global_max(self,new_local_max):
        self._global_max = new_local_max


########NEW FILE########
__FILENAME__ = solver
r"""
Module containing the classic Clawpack solvers.

This module contains the pure and wrapped classic clawpack solvers.  All 
clawpack solvers inherit from the :class:`ClawSolver` superclass which in turn 
inherits from the :class:`~pyclaw.solver.Solver` superclass.  These
are both pure virtual classes; the only solver classes that should be instantiated
are the dimension-specific ones, :class:`ClawSolver1D` and :class:`ClawSolver2D`.
"""

from clawpack.pyclaw.util import add_parent_doc
from clawpack.pyclaw.solver import Solver
from clawpack.pyclaw.limiters import tvd

# ============================================================================
#  Generic Clawpack solver class
# ============================================================================
class ClawSolver(Solver):
    r"""
    Generic classic Clawpack solver
    
    All Clawpack solvers inherit from this base class.
    
    .. attribute:: mthlim 
    
        Limiter(s) to be used.  Specified either as one value or a list.
        If one value, the specified limiter is used for all wave families.
        If a list, the specified values indicate which limiter to apply to
        each wave family.  Take a look at pyclaw.limiters.tvd for an enumeration.
        ``Default = limiters.tvd.minmod``
    
    .. attribute:: order
    
        Order of the solver, either 1 for first order (i.e., Godunov's method)
        or 2 for second order (Lax-Wendroff-LeVeque).
        ``Default = 2``
    
    .. attribute:: source_split
    
        Which source splitting method to use: 1 for first 
        order Godunov splitting and 2 for second order Strang splitting.
        ``Default = 1``
        
    .. attribute:: fwave
    
        Whether to split the flux jump (rather than the jump in Q) into waves; 
        requires that the Riemann solver performs the splitting.  
        ``Default = False``
        
    .. attribute:: step_source
    
        Handle for function that evaluates the source term.  
        The required signature for this function is:

        def step_source(solver,state,dt)
    
    .. attribute:: before_step
    
        Function called before each time step is taken.
        The required signature for this function is:
        
        def before_step(solver,solution)

    .. attribute:: kernel_language

        Specifies whether to use wrapped Fortran routines ('Fortran')
        or pure Python ('Python').  ``Default = 'Fortran'``.
    
    .. attribute:: verbosity

        The level of detail of logged messages from the Fortran solver.
        ``Default = 0``.

    """
    
    # ========== Generic Init Routine ========================================
    def __init__(self,riemann_solver=None,claw_package=None):
        r"""
        See :class:`ClawSolver` for full documentation.

        Output:
        - (:class:`ClawSolver`) - Initialized clawpack solver
        """
        self.num_ghost = 2
        self.limiters = tvd.minmod
        self.order = 2
        self.source_split = 1
        self.fwave = False
        self.step_source = None
        self.before_step = None
        self.kernel_language = 'Fortran'
        self.verbosity = 0
        self.cfl_max = 1.0
        self.cfl_desired = 0.9
        self._mthlim = self.limiters
        self._method = None

        # Call general initialization function
        super(ClawSolver,self).__init__(riemann_solver,claw_package)
    
    # ========== Time stepping routines ======================================
    def step(self,solution):
        r"""
        Evolve solution one time step

        The elements of the algorithm for taking one step are:
        
        1. The :meth:`before_step` function is called
        
        2. A half step on the source term :func:`step_source` if Strang splitting is 
           being used (:attr:`source_split` = 2)
        
        3. A step on the homogeneous problem :math:`q_t + f(q)_x = 0` is taken
        
        4. A second half step or a full step is taken on the source term
           :func:`step_source` depending on whether Strang splitting was used 
           (:attr:`source_split` = 2) or Godunov splitting 
           (:attr:`source_split` = 1)

        This routine is called from the method evolve_to_time defined in the
        pyclaw.solver.Solver superclass.

        :Input:
         - *solution* - (:class:`~pyclaw.solution.Solution`) solution to be evolved
         
        :Output: 
         - (bool) - True if full step succeeded, False otherwise
        """

        if self.before_step is not None:
            self.before_step(self,solution.states[0])

        if self.source_split == 2 and self.step_source is not None:
            self.step_source(self,solution.states[0],self.dt/2.0)
    
        self.step_hyperbolic(solution)

        # Check here if the CFL condition is satisfied. 
        # If not, return # immediately to evolve_to_time and let it deal with
        # picking a new step size (dt).
        if self.cfl.get_cached_max() >= self.cfl_max:
            return False

        if self.step_source is not None:
            # Strang splitting
            if self.source_split == 2:
                self.step_source(self,solution.states[0],self.dt/2.0)

            # Godunov Splitting
            if self.source_split == 1:
                self.step_source(self,solution.states[0],self.dt)
                
        return True
            
    def _check_cfl_settings(self):
        pass

    def _allocate_workspace(self,solution):
        pass

    def step_hyperbolic(self,solution):
        r"""
        Take one homogeneous step on the solution.
        
        This is a dummy routine and must be overridden.
        """
        raise Exception("Dummy routine, please override!")

    def _set_mthlim(self):
        r"""
        Convenience routine to convert users limiter specification to 
        the format understood by the Fortran code (i.e., a list of length num_waves).
        """
        self._mthlim = self.limiters
        if not isinstance(self.limiters,list): self._mthlim=[self._mthlim]
        if len(self._mthlim)==1: self._mthlim = self._mthlim * self.num_waves
        if len(self._mthlim)!=self.num_waves:
            raise Exception('Length of solver.limiters is not equal to 1 or to solver.num_waves')
 
    def _set_method(self,state):
        r"""
        Set values of the solver._method array required by the Fortran code.
        These are algorithmic parameters.
        """
        import numpy as np
        #We ought to put method and many other things in a Fortran
        #module and set the fortran variables directly here.
        self._method =np.empty(7, dtype=int,order='F')
        self._method[0] = self.dt_variable
        self._method[1] = self.order
        if self.num_dim==1:
            self._method[2] = 0  # Not used in 1D
        elif self.dimensional_split:
            self._method[2] = -1  # First-order dimensional splitting
        else:
            self._method[2] = self.transverse_waves
        self._method[3] = self.verbosity
        self._method[4] = 0  # Not used for PyClaw (would be self.source_split)
        self._method[5] = state.index_capa + 1
        self._method[6] = state.num_aux

    def setup(self,solution):
        r"""
        Perform essential solver setup.  This routine must be called before
        solver.step() may be called.
        """
        # This is a hack to deal with the fact that petsc4py
        # doesn't allow us to change the stencil_width (num_ghost)
        solution.state.set_num_ghost(self.num_ghost)
        # End hack

        self._check_cfl_settings()

        self._set_mthlim()
        if(self.kernel_language == 'Fortran'):
            if self.fmod is None:
                so_name = 'clawpack.pyclaw.classic.classic'+str(self.num_dim)
                self.fmod = __import__(so_name,fromlist=['clawpack.pyclaw.classic'])
            self._set_fortran_parameters(solution)
            self._allocate_workspace(solution)
        elif self.num_dim>1:
            raise Exception('Only Fortran kernels are supported in multi-D.')

        self._allocate_bc_arrays(solution.states[0])

        super(ClawSolver,self).setup(solution)


    def _set_fortran_parameters(self,solution):
        r"""
        Pack parameters into format recognized by Clawpack (Fortran) code.

        Sets the solver._method array and the cparam common block for the Riemann solver.
        """
        self._set_method(solution.state)
        # The reload here is necessary because otherwise the common block
        # cparam in the Riemann solver doesn't get flushed between running
        # different tests in a single Python session.
        reload(self.fmod)
        solution.state.set_cparam(self.fmod)
        solution.state.set_cparam(self.rp)

    def __del__(self):
        r"""
        Delete Fortran objects, which otherwise tend to persist in Python sessions.
        """
        if(self.kernel_language == 'Fortran'):
            del self.fmod

        super(ClawSolver,self).__del__()


# ============================================================================
#  ClawPack 1d Solver Class
# ============================================================================
class ClawSolver1D(ClawSolver):
    r"""
    Clawpack evolution routine in 1D
    
    This class represents the 1d clawpack solver on a single grid.  Note that 
    there are routines here for interfacing with the fortran time stepping 
    routines and the Python time stepping routines.  The ones used are 
    dependent on the argument given to the initialization of the solver 
    (defaults to python).
    
    """

    __doc__ += add_parent_doc(ClawSolver)

    def __init__(self, riemann_solver=None, claw_package=None):
        r"""
        Create 1d Clawpack solver

        Output:
        - (:class:`ClawSolver1D`) - Initialized 1d clawpack solver
        
        See :class:`ClawSolver1D` for more info.
        """   
        self.num_dim = 1

        super(ClawSolver1D,self).__init__(riemann_solver, claw_package)


    # ========== Homogeneous Step =====================================
    def step_hyperbolic(self,solution):
        r"""
        Take one time step on the homogeneous hyperbolic system.

        :Input:
         - *solution* - (:class:`~pyclaw.solution.Solution`) Solution that 
           will be evolved
        """
        import numpy as np

        state = solution.states[0]
        grid = state.grid

        self._apply_q_bcs(state)
        if state.num_aux > 0:
            self._apply_aux_bcs(state)
            
        num_eqn,num_ghost = state.num_eqn,self.num_ghost
          
        if(self.kernel_language == 'Fortran'):
            mx = grid.num_cells[0]
            dx,dt = grid.delta[0],self.dt
            dtdx = np.zeros( (mx+2*num_ghost) ) + dt/dx
            rp1 = self.rp.rp1._cpointer
            
            self.qbc,cfl = self.fmod.step1(num_ghost,mx,self.qbc,self.auxbc,dx,dt,self._method,self._mthlim,self.fwave,rp1)
            
        elif(self.kernel_language == 'Python'):
 
            q   = self.qbc
            aux = self.auxbc
            # Limiter to use in the pth family
            limiter = np.array(self._mthlim,ndmin=1)  
        
            dtdx = np.zeros( (2*self.num_ghost+grid.num_cells[0]) )

            # Find local value for dt/dx
            if state.index_capa>=0:
                dtdx = self.dt / (grid.delta[0] * state.aux[state.index_capa,:])
            else:
                dtdx += self.dt/grid.delta[0]
        
            # Solve Riemann problem at each interface
            q_l=q[:,:-1]
            q_r=q[:,1:]
            if state.aux is not None:
                aux_l=aux[:,:-1]
                aux_r=aux[:,1:]
            else:
                aux_l = None
                aux_r = None
            wave,s,amdq,apdq = self.rp(q_l,q_r,aux_l,aux_r,state.problem_data)
            
            # Update loop limits, these are the limits for the Riemann solver
            # locations, which then update a grid cell value
            # We include the Riemann problem just outside of the grid so we can
            # do proper limiting at the grid edges
            #        LL    |                               |     UL
            #  |  LL |     |     |     |  ...  |     |     |  UL  |     |
            #              |                               |

            LL = self.num_ghost - 1
            UL = self.num_ghost + grid.num_cells[0] + 1 

            # Update q for Godunov update
            for m in xrange(num_eqn):
                q[m,LL:UL] -= dtdx[LL:UL]*apdq[m,LL-1:UL-1]
                q[m,LL-1:UL-1] -= dtdx[LL-1:UL-1]*amdq[m,LL-1:UL-1]
        
            # Compute maximum wave speed
            cfl = 0.0
            for mw in xrange(wave.shape[1]):
                smax1 = np.max(dtdx[LL:UL]*s[mw,LL-1:UL-1])
                smax2 = np.max(-dtdx[LL-1:UL-1]*s[mw,LL-1:UL-1])
                cfl = max(cfl,smax1,smax2)

            # If we are doing slope limiting we have more work to do
            if self.order == 2:
                # Initialize flux corrections
                f = np.zeros( (num_eqn,grid.num_cells[0] + 2*self.num_ghost) )
            
                # Apply Limiters to waves
                if (limiter > 0).any():
                    wave = tvd.limit(state.num_eqn,wave,s,limiter,dtdx)

                # Compute correction fluxes for second order q_{xx} terms
                dtdxave = 0.5 * (dtdx[LL-1:UL-1] + dtdx[LL:UL])
                if self.fwave:
                    for mw in xrange(wave.shape[1]):
                        sabs = np.abs(s[mw,LL-1:UL-1])
                        om = 1.0 - sabs*dtdxave[:UL-LL]
                        ssign = np.sign(s[mw,LL-1:UL-1])
                        for m in xrange(num_eqn):
                            f[m,LL:UL] += 0.5 * ssign * om * wave[m,mw,LL-1:UL-1]
                else:
                    for mw in xrange(wave.shape[1]):
                        sabs = np.abs(s[mw,LL-1:UL-1])
                        om = 1.0 - sabs*dtdxave[:UL-LL]
                        for m in xrange(num_eqn):
                            f[m,LL:UL] += 0.5 * sabs * om * wave[m,mw,LL-1:UL-1]

                # Update q by differencing correction fluxes
                for m in xrange(num_eqn):
                    q[m,LL:UL-1] -= dtdx[LL:UL-1] * (f[m,LL+1:UL] - f[m,LL:UL-1]) 

        else: raise Exception("Unrecognized kernel_language; choose 'Fortran' or 'Python'")

        self.cfl.update_global_max(cfl)
        state.set_q_from_qbc(num_ghost,self.qbc)
        if state.num_aux > 0:
            state.set_aux_from_auxbc(num_ghost,self.auxbc)
   

# ============================================================================
#  ClawPack 2d Solver Class
# ============================================================================
class ClawSolver2D(ClawSolver):
    r"""
    2D Classic (Clawpack) solver.

    Solve using the wave propagation algorithms of Randy LeVeque's
    Clawpack code (www.clawpack.org).

    In addition to the attributes of ClawSolver1D, ClawSolver2D
    also has the following options:
    
    .. attribute:: dimensional_split
    
        If True, use dimensional splitting (Godunov splitting).
        Dimensional splitting with Strang splitting is not supported
        at present but could easily be enabled if necessary.
        If False, use unsplit Clawpack algorithms, possibly including
        transverse Riemann solves.

    .. attribute:: transverse_waves
    
        If dimensional_split is True, this option has no effect.  If
        dim_plit is False, then transverse_waves should be one of
        the following values:

        ClawSolver2D.no_trans: Transverse Riemann solver
        not used.  The stable CFL for this algorithm is 0.5.  Not recommended.
        
        ClawSolver2D.trans_inc: Transverse increment waves are computed
        and propagated.

        ClawSolver2D.trans_cor: Transverse increment waves and transverse
        correction waves are computed and propagated.

    Note that only the fortran routines are supported for now in 2D.
    """

    __doc__ += add_parent_doc(ClawSolver)
    
    no_trans  = 0
    trans_inc = 1
    trans_cor = 2

    def __init__(self,riemann_solver=None, claw_package=None):
        r"""
        Create 2d Clawpack solver
        
        See :class:`ClawSolver2D` for more info.
        """   
        self.dimensional_split = True
        self.transverse_waves = self.trans_inc

        self.num_dim = 2

        self.aux1 = None
        self.aux2 = None
        self.aux3 = None
        self.work = None

        super(ClawSolver2D,self).__init__(riemann_solver, claw_package)

    def _check_cfl_settings(self):
        if (not self.dimensional_split) and (self.transverse_waves==0):
            cfl_recommended = 0.5
        else:
            cfl_recommended = 1.0

        if self.cfl_max > cfl_recommended:
            import warnings
            warnings.warn('cfl_max is set higher than the recommended value of %s' % cfl_recommended)
            warnings.warn(str(self.cfl_desired))


    def _allocate_workspace(self,solution):
        r"""
        Pack parameters into format recognized by Clawpack (Fortran) code.

        Sets the method array and the cparam common block for the Riemann solver.
        """
        import numpy as np

        state = solution.state

        num_eqn,num_aux,num_waves,num_ghost,aux = state.num_eqn,state.num_aux,self.num_waves,self.num_ghost,state.aux

        #The following is a hack to work around an issue
        #with f2py.  It involves wastefully allocating three arrays.
        #f2py seems not able to handle multiple zero-size arrays being passed.
        # it appears the bug is related to f2py/src/fortranobject.c line 841.
        if(aux == None): num_aux=1

        grid  = state.grid
        maxmx,maxmy = grid.num_cells[0],grid.num_cells[1]
        maxm = max(maxmx, maxmy)

        # These work arrays really ought to live inside a fortran module
        # as is done for sharpclaw
        self.aux1 = np.empty((num_aux,maxm+2*num_ghost),order='F')
        self.aux2 = np.empty((num_aux,maxm+2*num_ghost),order='F')
        self.aux3 = np.empty((num_aux,maxm+2*num_ghost),order='F')
        mwork = (maxm+2*num_ghost) * (5*num_eqn + num_waves + num_eqn*num_waves)
        self.work = np.empty((mwork),order='F')


    # ========== Hyperbolic Step =====================================
    def step_hyperbolic(self,solution):
        r"""
        Take a step on the homogeneous hyperbolic system using the Clawpack
        algorithm.

        Clawpack is based on the Lax-Wendroff method, combined with Riemann
        solvers and TVD limiters applied to waves.
        """
        if(self.kernel_language == 'Fortran'):
            state = solution.states[0]
            grid = state.grid
            dx,dy = grid.delta
            mx,my = grid.num_cells
            maxm = max(mx,my)
            
            self._apply_q_bcs(state)
            if state.num_aux > 0:
                self._apply_aux_bcs(state)
            qold = self.qbc.copy('F')
            
            rpn2 = self.rp.rpn2._cpointer
            rpt2 = self.rp.rpt2._cpointer

            if self.dimensional_split:
                #Right now only Godunov-dimensional-splitting is implemented.
                #Strang-dimensional-splitting could be added following dimsp2.f in Clawpack.

                self.qbc, cfl_x = self.fmod.step2ds(maxm,self.num_ghost,mx,my, \
                      qold,self.qbc,self.auxbc,dx,dy,self.dt,self._method,self._mthlim,\
                      self.aux1,self.aux2,self.aux3,self.work,1,self.fwave,rpn2,rpt2)

                self.qbc, cfl_y = self.fmod.step2ds(maxm,self.num_ghost,mx,my, \
                      self.qbc,self.qbc,self.auxbc,dx,dy,self.dt,self._method,self._mthlim,\
                      self.aux1,self.aux2,self.aux3,self.work,2,self.fwave,rpn2,rpt2)

                cfl = max(cfl_x,cfl_y)

            else:

                self.qbc, cfl = self.fmod.step2(maxm,self.num_ghost,mx,my, \
                      qold,self.qbc,self.auxbc,dx,dy,self.dt,self._method,self._mthlim,\
                      self.aux1,self.aux2,self.aux3,self.work,self.fwave,rpn2,rpt2)

            self.cfl.update_global_max(cfl)
            state.set_q_from_qbc(self.num_ghost,self.qbc)
            if state.num_aux > 0:
                state.set_aux_from_auxbc(self.num_ghost,self.auxbc)

        else:
            raise NotImplementedError("No python implementation for step_hyperbolic in 2D.")

# ============================================================================
#  ClawPack 3d Solver Class
# ============================================================================
class ClawSolver3D(ClawSolver):
    r"""
    3D Classic (Clawpack) solver.

    Solve using the wave propagation algorithms of Randy LeVeque's
    Clawpack code (www.clawpack.org).

    In addition to the attributes of ClawSolver, ClawSolver3D
    also has the following options:
    
    .. attribute:: dimensional_split
    
        If True, use dimensional splitting (Godunov splitting).
        Dimensional splitting with Strang splitting is not supported
        at present but could easily be enabled if necessary.
        If False, use unsplit Clawpack algorithms, possibly including
        transverse Riemann solves.

    .. attribute:: transverse_waves
    
        If dimensional_split is True, this option has no effect.  If
        dim_plit is False, then transverse_waves should be one of
        the following values:

        ClawSolver3D.no_trans: Transverse Riemann solver
        not used.  The stable CFL for this algorithm is 0.5.  Not recommended.
        
        ClawSolver3D.trans_inc: Transverse increment waves are computed
        and propagated.

        ClawSolver3D.trans_cor: Transverse increment waves and transverse
        correction waves are computed and propagated.

    Note that only Fortran routines are supported for now in 3D --
    there is no pure-python version.
    """

    __doc__ += add_parent_doc(ClawSolver)

    no_trans  = 0
    trans_inc = 11
    trans_cor = 22

    def __init__(self, riemann_solver=None, claw_package=None):
        r"""
        Create 3d Clawpack solver
        
        See :class:`ClawSolver3D` for more info.
        """   
        # Add the functions as required attributes
        self.dimensional_split = True
        self.transverse_waves = self.trans_cor

        self.num_dim = 3

        self.aux1 = None
        self.aux2 = None
        self.aux3 = None
        self.work = None

        super(ClawSolver3D,self).__init__(riemann_solver, claw_package)

    # ========== Setup routine =============================   
    def _allocate_workspace(self,solution):
        r"""
        Allocate auxN and work arrays for use in Fortran subroutines.
        """
        import numpy as np

        state = solution.states[0]

        num_eqn,num_aux,num_waves,num_ghost,aux = state.num_eqn,state.num_aux,self.num_waves,self.num_ghost,state.aux

        #The following is a hack to work around an issue
        #with f2py.  It involves wastefully allocating three arrays.
        #f2py seems not able to handle multiple zero-size arrays being passed.
        # it appears the bug is related to f2py/src/fortranobject.c line 841.
        if(aux == None): num_aux=1

        grid  = state.grid
        maxmx,maxmy,maxmz = grid.num_cells[0],grid.num_cells[1],grid.num_cells[2]
        maxm = max(maxmx, maxmy, maxmz)

        # These work arrays really ought to live inside a fortran module
        # as is done for sharpclaw
        self.aux1 = np.empty((num_aux,maxm+2*num_ghost,3),order='F')
        self.aux2 = np.empty((num_aux,maxm+2*num_ghost,3),order='F')
        self.aux3 = np.empty((num_aux,maxm+2*num_ghost,3),order='F')
        mwork = (maxm+2*num_ghost) * (31*num_eqn + num_waves + num_eqn*num_waves)
        self.work = np.empty((mwork),order='F')


    # ========== Hyperbolic Step =====================================
    def step_hyperbolic(self,solution):
        r"""
        Take a step on the homogeneous hyperbolic system using the Clawpack
        algorithm.

        Clawpack is based on the Lax-Wendroff method, combined with Riemann
        solvers and TVD limiters applied to waves.
        """
        if(self.kernel_language == 'Fortran'):
            state = solution.states[0]
            grid = state.grid
            dx,dy,dz = grid.delta
            mx,my,mz = grid.num_cells
            maxm = max(mx,my,mz)
            
            self._apply_q_bcs(state)
            if state.num_aux > 0:
                self._apply_aux_bcs(state)
            qnew = self.qbc
            qold = qnew.copy('F')
            
            rpn3  = self.rp.rpn3._cpointer
            rpt3  = self.rp.rpt3._cpointer
            rptt3 = self.rp.rptt3._cpointer

            if self.dimensional_split:
                #Right now only Godunov-dimensional-splitting is implemented.
                #Strang-dimensional-splitting could be added following dimsp2.f in Clawpack.

                q, cfl_x = self.fmod.step3ds(maxm,self.num_ghost,mx,my,mz, \
                      qold,qnew,self.auxbc,dx,dy,dz,self.dt,self._method,self._mthlim,\
                      self.aux1,self.aux2,self.aux3,self.work,1,self.fwave,rpn3,rpt3,rptt3)

                q, cfl_y = self.fmod.step3ds(maxm,self.num_ghost,mx,my,mz, \
                      q,q,self.auxbc,dx,dy,dz,self.dt,self._method,self._mthlim,\
                      self.aux1,self.aux2,self.aux3,self.work,2,self.fwave,rpn3,rpt3,rptt3)

                q, cfl_z = self.fmod.step3ds(maxm,self.num_ghost,mx,my,mz, \
                      q,q,self.auxbc,dx,dy,dz,self.dt,self._method,self._mthlim,\
                      self.aux1,self.aux2,self.aux3,self.work,3,self.fwave,rpn3,rpt3,rptt3)

                cfl = max(cfl_x,cfl_y,cfl_z)

            else:

                q, cfl = self.fmod.step3(maxm,self.num_ghost,mx,my,mz, \
                      qold,qnew,self.auxbc,dx,dy,dz,self.dt,self._method,self._mthlim,\
                      self.aux1,self.aux2,self.aux3,self.work,self.fwave,rpn3,rpt3,rptt3)

            self.cfl.update_global_max(cfl)
            state.set_q_from_qbc(self.num_ghost,self.qbc)
            if state.num_aux > 0:
                state.set_aux_from_auxbc(self.num_ghost,self.auxbc)

        else:
            raise NotImplementedError("No python implementation for step_hyperbolic in 3D.")

########NEW FILE########
__FILENAME__ = controller
#!/usr/bin/env python
# encoding: utf-8
r"""
Controller for basic computation and plotting setup.

This module defines the Pyclaw controller class.  It can be used to perform
simulations in a convenient manner similar to that available in previous
versions of Clawpack, i.e. with output_style and
output time specification.  It also can be used to set up easy plotting and 
running of compiled fortran binaries.
"""

import logging
import sys
import os
import copy

from .solver import Solver
from .util import FrameCounter
from .util import LOGGING_LEVELS

class Controller(object):
    r"""Controller for pyclaw simulation runs and plotting
            
    :Initialization:
    
        Input: None
    
    :Examples:

        >>> import clawpack.pyclaw as pyclaw
        >>> x = pyclaw.Dimension('x',0.,1.,100)
        >>> domain = pyclaw.Domain((x))
        >>> state = pyclaw.State(domain,3,2)
        >>> claw = pyclaw.Controller()
        >>> claw.solution = pyclaw.Solution(state,domain)
        >>> claw.solver = pyclaw.ClawSolver1D()
    """

    def __getattr__(self, key):
        if key in ('t','num_eqn','mp','mF','q','p','F','aux','capa',
                   'problem_data','num_aux',
                   'num_dim', 'p_centers', 'p_edges', 'c_centers', 'c_edges',
                   'num_cells', 'lower', 'upper', 'delta', 'centers', 'edges',
                   'gauges', 'num_eqn', 'num_aux', 'grid', 'problem_data'):
            return self._get_solution_attribute(key)
        else:
            raise AttributeError("'Controller' object has no attribute '"+key+"'")

    def _get_solution_attribute(self, name):
        r"""
        Return solution attribute
        
        :Output:
         - (id) - Value of attribute from ``solution``
        """
        return getattr(self.solution,name)
 

    #  ======================================================================
    #   Property Definitions
    #  ======================================================================
    @property
    def verbosity(self):
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value):
        self._verbosity = value
        # Only adjust console logger; leave file logger alone
        self.logger.handlers[1].setLevel(LOGGING_LEVELS[value])

    @property
    def outdir_p(self):
        r"""(string) - Directory to use for writing derived quantity files"""
        return os.path.join(self.outdir,'_p')
    @property
    def F_path(self):
        r"""(string) - Full path to output file for functionals"""
        return os.path.join(self.outdir,self.F_file_name+'.txt')

    #  ======================================================================
    #   Initialization routines
    #  ======================================================================
    def __init__(self):
        r"""
        Initialization routine for a Controller object.
        
        See :class:`Controller` for full documentation.
        """
        
        import numpy as np

        self.viewable_attributes = ['xdir','rundir','outdir','overwrite',
                        'xclawcmd','xclawout','xclawerr','runmake','savecode',
                        'solver','keep_copy','write_aux_init',
                        'write_aux_always','output_format',
                        'output_file_prefix','output_options','num_output_times',
                        'output_style','verbosity']
        r"""(list) - Viewable attributes of the `:class:`~pyclaw.controller.Controller`"""

        # Global information for running and/or plotting
        self.xdir = os.getcwd()
        r"""(string) - Executable path, executes xclawcmd in xdir"""
        self.rundir = os.getcwd()
        r"""(string) - Directory to run from (containing \*.data files), uses 
        \*.data from rundir"""
        self.outdir = os.getcwd()+'/_output'
        r"""(string) - Output directory, directs output files to outdir"""
        self.overwrite = True
        r"""(bool) - Ok to overwrite old result in outdir, ``default = True``"""

        self.xclawcmd = 'xclaw'
        r"""(string) - Command to execute (if using fortran), defaults to xclaw or
        xclaw.exe if cygwin is being used (which it checks vis sys.platform)"""
        if sys.platform == 'cygwin':
            self.xclawcmd = 'xclaw.exe'

        self.start_frame = 0
        self.xclawout = None
        r"""(string) - Where to write timestep messages"""
        self.xclawerr = None
        r"""(string) - Where to write error messages"""
        self.runmake = False
        r"""(bool) - Run make in xdir before xclawcmd"""
        self.savecode = False
        r"""(bool) - Save a copy of \*.f files in outdir"""
        
        self.setplot = None

        # Solver information
        self.solution = None
        self.solver = None
        r"""(:class:`~pyclaw.solver.Solver`) - Solver object"""
        
        # Output parameters for run convenience method
        self.keep_copy = False 
        r"""(bool) - Keep a copy in memory of every output time, 
        ``default = False``"""
        self.frames = []
        r"""(list) - List of saved frames if ``keep_copy`` is set to ``True``"""
        self.write_aux_init = False
        r"""(bool) - Write out initial auxiliary array, ``default = False``"""
        self.write_aux_always = False
        r"""(bool) - Write out auxiliary array at every time step, 
        ``default = False``"""
        self.output_format = 'ascii'
        r"""(list of strings) - Format or list of formats to output the data, 
        if this is None, no output is performed.  See _pyclaw_io for more info
        on available formats.  ``default = 'ascii'``"""
        self.output_file_prefix = None
        r"""(string) - File prefix to be appended to output files, 
        ``default = None``"""
        self.output_options = {}
        r"""(dict) - Output options passed to function writing and reading 
        data in output_format's format.  ``default = {}``"""
        
        self.logger = logging.getLogger('pyclaw.controller')

        # Classic output parameters, used in run convenience method
        self.tfinal = 1.0
        r"""(float) - Final time output, ``default = 1.0``"""
        self.output_style = 1
        r"""(int) - Time output style, ``default = 1``"""
        self.verbosity = 3
        r"""(int) - Level of output to screen; ``default = 3``"""
        self.num_output_times = 10                  # Outstyle 1 defaults
        r"""(int) - Number of output times, only used with ``output_style = 1``,
        ``default = 10``"""
        self.out_times = np.linspace(0.0,self.tfinal,self.num_output_times
                                     -self.start_frame) # Outstyle 2
        r"""(int) - Output time list, only used with ``output_style = 2``,
        ``default = numpy.linspace(0.0,tfinal,num_output_times)``"""
        
        self.nstepout = 1               # Outstyle 3 defaults
        r"""(int) - Number of steps between output, only used with 
        ``output_style = 3``, ``default = 1``"""
        
        # Data objects
        self.plotdata = None
        r"""(:class:`~visclaw.data.ClawPlotData`) - An instance of a 
        :class:`~visclaw.data.ClawPlotData` object defining the 
        objects plot parameters."""
        
        # Derived quantity p
        self.file_prefix_p = 'claw_p'
        r"""(string) - File prefix to be prepended to derived quantity output files"""
        self.compute_p = None
        r"""(function) - function that computes derived quantities"""
        
        # functionals
        self.compute_F = None
        r"""(function) - Function that computes density of functional F"""
        self.F_file_name = 'F'
        r"""(string) - Name of text file containing functionals"""

    # ========== Access methods ===============================================
    def __str__(self):        
        output = "Controller attributes:\n"
        for attr in self.viewable_attributes:
            value = getattr(self,attr)
            output = output + "  %s = %s \n" % (attr,value)
        output = output + '\n'
        if self.plotdata is not None:
            output = output + "  Data "+str(self.plotdata)+"\n"
        if self.solver is not None:
            output = output + "  Solver "+str(self.solver)+"\n"
        if len(self.frames) > 0:
            output = output + "  Frames \n"
            for frame in self.frames:
                output = output + "    " + str(frame) + "\n"
        return output
        
    # ========== Properties ==================================================
    
    def check_validity(self):
        r"""Check that the controller has been properly set up and is ready to run.

            Also checks validity of the solver, solution and states.
        """
        # Check to make sure we have a valid solver to use
        if self.solver is None:
            raise Exception("No solver set in controller.")
        if not isinstance(self.solver,Solver):
            raise Exception("Solver is not of correct type.")
        valid, reason = self.solver.is_valid()
        if not valid:
            raise Exception("The solver failed to initialize properly because "+reason) 
            
        # Check to make sure the initial solution is valid
        if not self.solution.is_valid():
            raise Exception("Initial solution is not valid.")
        if not all([state.is_valid() for state in self.solution.states]):
            raise Exception("Initial states are not valid.")
        
 
    # ========== Plotting methods ============================================        
    def set_plotdata(self):
        from clawpack.visclaw import data
        from clawpack.visclaw import frametools
        plotdata = data.ClawPlotData()
        plotdata.setplot = self.setplot
        self.plotdata = frametools.call_setplot(self.setplot,plotdata)
        plotdata._mode = 'iplotclaw'

    def load_frame(self,frame_number):
        try: 
            return self.frames[frame_number]
        except IndexError:
            print "Cannot plot frame %s; only %s frames available" % (frame_number, len(self.frames))

    def plot_frame(self, frame):
        if self.plotdata is None:
            self.set_plotdata()

        if frame is not None:
            frameno = self.frames.index(frame)
            from clawpack.visclaw import frametools
            frametools.plot_frame(frame, self.plotdata, frameno=frameno)

    def plot(self):
        """Plot from memory."""
        if len(self.frames) == 0:  # No frames to plot
            print "No frames to plot.  Did you forget to run, or to set keep_copy=True?"
            return

        from clawpack.visclaw import iplot

        if self.plotdata is None:
            self.set_plotdata()

        ip = iplot.Iplot(self.load_frame,self.plot_frame)
        ip.plotloop()

    # ========== Solver convenience methods ==================================
    def run(self):
        r"""
        Convenience routine that will evolve solution based on the 
        traditional clawpack output and run parameters.
        
        This function uses the run parameters and solver parameters to evolve
        the solution to the end time specified in run_data, outputting at the
        appropriate times.
        
        :Input:
            None
            
        :Ouput:
            (dict) - Return a dictionary of the status of the solver.
        """
        import numpy as np

        if self.solver is None or self.solution is None:
            raise Exception('To run, a Controller must have a Solver and a Solution.')

        self.start_frame = self.solution.start_frame
        if len(self.solution.patch.grid.gauges)>0:
            self.solution.patch.grid.setup_gauge_files(self.outdir)
        frame = FrameCounter()

        frame.set_counter(self.start_frame)
                    
        if not self.solver._is_set_up:
            self.solver.setup(self.solution)
            self.solver.dt = self.solver.dt_initial
            
        self.check_validity()

        # Write initial gauge values
        self.solver.write_gauge_values(self.solution)

        # Output styles
        if self.output_style == 1:
            output_times = np.linspace(self.solution.t,
                    self.tfinal,self.num_output_times+1)
        elif self.output_style == 2:
            output_times = self.out_times
        elif self.output_style == 3:
            output_times = np.ones((self.num_output_times+1
                                    -self.start_frame))
        else:
            raise Exception("Invalid output style %s" % self.output_style)  

        if len(output_times) == 0:
            print "No valid output times; halting."
            if self.t == self.tfinal:
                print "Simulation has already reached tfinal."
            return None
         
        # Output and save initial frame
        if self.keep_copy:
            self.frames.append(copy.deepcopy(self.solution))
        if self.output_format is not None:
            if os.path.exists(self.outdir) and self.overwrite==False:
                raise Exception("Refusing to overwrite existing output data. \
                 \nEither delete/move the directory or set controller.overwrite=True.")
            if self.compute_p is not None:
                self.compute_p(self.solution.state)
                self.solution.write(frame,self.outdir_p,
                                        self.output_format,
                                        self.file_prefix_p,
                                        write_aux = False,
                                        options = self.output_options,
                                        write_p = True) 

            write_aux = (self.write_aux_always or self.write_aux_init)
            self.solution.write(frame,self.outdir,
                                        self.output_format,
                                        self.output_file_prefix,
                                        write_aux,
                                        self.output_options)

        self.write_F('w')

        self.log_info("Solution %s computed for time t=%f" % 
                        (frame,self.solution.t) )

        for t in output_times[1:]:                
            if self.output_style < 3:
                status = self.solver.evolve_to_time(self.solution,t)
            else:
                # Take nstepout steps and output
                for n in xrange(self.nstepout):
                    status = self.solver.evolve_to_time(self.solution)
            frame.increment()
            if self.keep_copy:
                # Save current solution to dictionary with frame as key
                self.frames.append(copy.deepcopy(self.solution))
            if self.output_format is not None:
                if self.compute_p is not None:
                    self.compute_p(self.solution.state)
                    self.solution.write(frame,self.outdir_p,
                                            self.output_format,
                                            self.file_prefix_p,
                                            write_aux = False, 
                                            options = self.output_options,
                                            write_p = True) 
                
                self.solution.write(frame,self.outdir,
                                            self.output_format,
                                            self.output_file_prefix,
                                            self.write_aux_always,
                                            self.output_options)
            self.write_F()

            self.log_info("Solution %s computed for time t=%f"
                % (frame,self.solution.t))
            for gfile in self.solution.state.grid.gauge_files: 
                gfile.flush()
            
        for gfile in self.solution.state.grid.gauge_files: gfile.close()

        self.solution._start_frame = len(self.frames)

        # Return the current status of the solver
        return status
    
    # ========== Advanced output methods ==================================

    def write_F(self,mode='a'):
        if self.compute_F is not None:
            self.compute_F(self.solution.state)
            F = [0]*self.solution.state.mF
            for i in xrange(self.solution.state.mF):
                F[i] = self.solution.state.sum_F(i)
            if self.is_proc_0():
                t=self.solution.t
                F_file = open(self.F_path,mode)
                F_file.write(str(t)+' '+' '.join(str(j) for j in F) + '\n')
                F_file.close()
    
    def is_proc_0(self):
        return True

    def log_info(self, str):
        self.logger.info(str)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = geometry
#!/usr/bin/env python
# encoding: utf-8
r"""
Module containing all Pyclaw solution objects
"""

import numpy as np

# ============================================================================
#  Default function definitions
# ============================================================================

# Default mapc2p function
def default_mapc2p(patch,x):
    r"""
    Returns the physical coordinate of the point x
    
    This is the stub function which simply returns the identity
    """
    return x


class Grid(object):
    r"""
    Basic representation of a single grid in Pyclaw
    
    :Dimension information:
    
        Each dimension has an associated name with it that can be accessed via
        that name such as ``grid.x.num_cells`` which would access the x dimension's
        number of cells.
    
    :Properties:

        If the requested property has multiple values, a list will be returned
        with the corresponding property belonging to the dimensions in order.
         
    :Initialization:
    
        Input:
         - *dimensions* - (list of :class:`Dimension`) Dimensions that are to 
           be associated with this grid
            
        Output:
         - (:class:`grid`) Initialized grid object

    A PyClaw grid is usually constructed from a tuple of PyClaw Dimension objects:

	>>> from clawpack.pyclaw.geometry import Dimension, Grid      
	>>> x = Dimension('x',0.,1.,10)
        >>> y = Dimension('y',-1.,1.,25)
        >>> grid = Grid((x,y))
        >>> print grid
        Dimension x:  (num_cells,delta,[lower,upper]) = (10,0.1,[0.0,1.0])
        Dimension y:  (num_cells,delta,[lower,upper]) = (25,0.08,[-1.0,1.0])
        >>> grid.num_dim
        2
        >>> grid.num_cells
        [10, 25]
        >>> grid.lower
        [0.0, -1.0]
        >>> grid.delta # Returns [dx, dy]
        [0.1, 0.08]

    A grid can be extended to higher dimensions using the add_dimension() method:

        >>> z=Dimension('z',-2.0,2.0,21)
        >>> grid.add_dimension(z)
        >>> grid.num_dim
        3
        >>> grid.num_cells
        [10, 25, 21]
        >>> grid.c_edges[0][0,0,0]
        0.0
        >>> grid.c_edges[1][0,0,0]
        -1.0
        >>> grid.c_edges[2][0,0,0]
        -2.0
    """

    def __getattr__(self,key):
        # Provide dimension attribute lists when requested from Grid object.
        # Note that this only gets called when one requests an attribute
        # that the grid doesn't possess.
        if key in ['num_cells','lower','upper','delta','units','centers','edges',
                    'on_lower_boundary','on_upper_boundary']:
            return self.get_dim_attribute(key)
        else:
            raise AttributeError("'Grid' object has no attribute '"+key+"'")

    # ========== Property Definitions ========================================
    @property
    def num_dim(self):
        r"""(int) - Number of dimensions"""
        return len(self._dimensions)
    @property
    def dimensions(self):
        r"""(list) - List of :class:`Dimension` objects defining the 
                grid's extent and resolution"""
        return [getattr(self,name) for name in self._dimensions]
    @property
    def p_centers(self):
        r"""(list of ndarray(...)) - List containing the arrays locating
                  the physical locations of cell centers, see 
                  :meth:`compute_p_centers` for more info."""
        self.compute_p_centers(self)
        return self._p_centers
    _p_centers = None
    @property
    def p_edges(self):
        r"""(list of ndarray(...)) - List containing the arrays locating
                  the physical locations of cell edges, see 
                  :meth:`compute_p_edges` for more info."""
        self.compute_p_edges(self)
        return self._p_edges
    _p_edges = None
    @property
    def c_centers(self):
        r"""(list of ndarray(...)) - List containing the arrays locating
                  the computational locations of cell centers, see 
                  :meth:`compute_c_centers` for more info."""
        self.compute_c_centers(self)
        return self._c_centers
    _c_centers = None
    def c_centers_with_ghost(self,num_ghost):
        r"""(list of ndarray(...)) - List containing the arrays locating
                the computational locations of cell centers, see 
                :meth:`compute_c_centers` for more info."""
        self.compute_c_centers_with_ghost(self,num_ghost,recompute=True)
        return self._c_centers_with_ghost
    _c_centers_with_ghost = None
    @property
    def c_edges(self):
        r"""(list of ndarray(...)) - List containing the arrays locating
                  the computational locations of cell edges, see 
                  :meth:`compute_c_edges` for more info."""
        self.compute_c_edges(self)
        return self._c_edges
    _c_edges = None
    def c_edges_with_ghost(self):
        r"""(list of ndarray(...)) - List containing the arrays locating
                  the computational locations of cell edges, see 
                  :meth:`compute_c_edges` for more info."""
        self.compute_c_edges_with_ghost(self)
        return self._c_edges_with_ghost
    _c_edges_with_ghost = None
       
    
    # ========== Class Methods ===============================================
    def __init__(self,dimensions):
        r"""
        Instantiate a Grid object
        
        See :class:`Grid` for more info.
        """
        
        # ========== Attribute Definitions ===================================
        self.mapc2p = default_mapc2p
        r"""(func) - Coordinate mapping function"""
        self.gauges = []
        r"""(list) - List of gauges' indices to be filled by add_gauges
        method.
        """
        self.gauge_file_names  = []
        r"""(list) - List of file names to write gauge values to"""
        self.gauge_files = []
        r"""(list) - List of file objects to write gauge values to"""
        self.gauge_dir_name = '_gauges'
        r"""(string) - Name of the output directory for gauges. If the
        `Controller` class is used to run the application, this directory by
        default will be created under the `Controller` `outdir` directory.
        """
        self.num_ghost = None

        # Dimension parsing
        if isinstance(dimensions,Dimension):
            dimensions = [dimensions]
        self._dimensions = []
        for dim in dimensions:
            self.add_dimension(dim)

        super(Grid,self).__init__()
    
    
    def __str__(self):
	output = ''
        output += '\n'.join((str(getattr(self,dim)) for dim in self._dimensions))
        return output
    
    
    # ========== Dimension Manipulation ======================================
    def add_dimension(self,dimension):
        r"""
        Add the specified dimension to this patch
        
        :Input:
         - *dimension* - (:class:`Dimension`) Dimension to be added
        """

        # Add dimension to name list and as an attribute
        if dimension.name in self._dimensions:
            raise Exception('Unable to add dimension. A dimension'\
             +' of the same name: {name}, already exists.'\
             .format(name=dimension.name))

        self._dimensions.append(dimension.name)
        setattr(self,dimension.name,dimension)
        
        
    def get_dim_attribute(self,attr):
        r"""
        Returns a tuple of all dimensions' attribute attr
        """
        return [getattr(dim,attr) for dim in self.dimensions]
    
    
    # ========== Copy functionality ==========================================
    def __copy__(self):
        return self.__class__(self)
        
    # ========== Grid Operations =============================================
    def compute_p_centers(self, recompute=False):
        r"""Calculates the :attr:`p_centers` array, which contains the physical
        coordinates of the cell centers when a mapping is used.

        grid._p_centers is a list of numpy arrays.  Each array has shape equal
        to the shape of the grid; the number of arrays is equal to the 
        dimension of the embedding space for the mapping.
        
        This array is computed only when requested and then stored for later 
        use unless the recompute flag is set to True (you may want to do this
        for time-dependent mappings).
        
        Access the resulting physical coordinate array via the corresponding
        dimensions or via the computational grid properties :attr:`p_centers`.
        
        :Input:
         - *recompute* - (bool) Whether to force a recompute of the arrays
        """
        
        if recompute or not len(self._p_centers) == len(self._dimensions):
            # Initialize array
            self._p_centers = [None]*self.num_dim

            # Special case
            if self.num_dim == 1:
                self._p_centers[0] = self.mapc2p(self,self.dimensions[0].centers)
            # Higer dimensional calculate center arrays
            else:
                index = np.indices(self.num_cells)
                array_list = []
                for i,center_array in enumerate(self.get_dim_attribute('centers')):
                    #We could just use indices directly and deal with
                    #numpy arrays instead of lists of numpy arrays
                    array_list.append(center_array[index[i,...]])
            
                self._p_centers = self.mapc2p(self,array_list)
 

    def compute_p_edges(self, recompute=False):
        r"""Calculates the :attr:`p_edges` array
        
        This array is computed only when requested and then stored for later 
        use unless the recompute flag is set to True (you may want to do this
        for time dependent mappings).
        
        Access the resulting physical coordinate array via the corresponding
        dimensions or via the computational grid properties :attr:`p_edges`.
        
        :Input:
         - *recompute* - (bool) Whether to force a recompute of the arrays
        """
        
        if recompute or not len(self._p_edges) == len(self._dimensions):
            # Initialize array
            self._p_edges = [None for i in xrange(self.num_dim)]

            if self.num_dim == 1:        
                self._p_edges[0] = self.mapc2p(self,self.dimensions[0].edges)
            else:
                index = np.indices([n+1 for n in self.num_cells])
                array_list = []
                for i,edge_array in enumerate(self.get_dim_attribute('edges')):
                    #We could just use indices directly and deal with
                    #numpy arrays instead of lists of numpy arrays
                    array_list.append(edge_array[index[i,...]])
            
                self._p_edges = self.mapc2p(self,array_list)
            

    def compute_c_centers(self, recompute=False):
        r"""
        Calculate the :attr:`c_centers` array
        
        This array is computed only when requested and then stored for later
        use unless the recompute flag is set to True.
        
        Access the resulting computational coodinate array via the
        corresponding dimensions or via the computational grid properties
        :attr:`c_centers`.
        
        :Input:
         - *recompute* - (bool) Whether to force a recompute of the arrays
        """
        
        if recompute or (self._c_centers is None):
            self._c_centers = [None]*self.num_dim
            
            # For one dimension, the center and edge arrays are equivalent
            if self.num_dim == 1:
                self._c_centers[0] = self.dimensions[0].centers
            else:
                index = np.indices(self.num_cells)
                self._c_centers = []
                for i,center_array in enumerate(self.get_dim_attribute('centers')):
                    #We could just use indices directly and deal with
                    #numpy arrays instead of lists of numpy arrays
                    self._c_centers.append(center_array[index[i,...]])

    def compute_c_centers_with_ghost(self, num_ghost,recompute=False):
        r"""
        Calculate the :attr:`c_centers_with_ghost` array
        
        This array is computed only when requested and then stored for later
        use unless the recompute flag is set to True.
        
        Access the resulting computational coodinate array via the
        corresponding dimensions or via the computational grid properties
        :attr:`c_centers_with_ghost`.
        
        :Input:
         - *recompute* - (bool) Whether to force a recompute of the arrays
        """
        self.num_ghost = num_ghost
        if recompute or (self._c_centers_with_ghost is None):
            self._c_centers_with_ghost = [None]*self.num_dim
            
            # For one dimension, the center and edge arrays are equivalent
            for i in xrange(0,self.num_dim):
                self.dimensions[i]._centers_with_ghost = None
                self.dimensions[i]._c_centers_with_ghost = None
                self.dimensions[i].num_ghost = num_ghost

            if self.num_dim == 1:
                self._c_centers_with_ghost[0] = self.dimensions[0].centers_with_ghost
            else:
                index = np.indices(n+2.0*num_ghost for n in self.num_cells)
                self._c_centers_with_ghost = []
                for i,center_array in enumerate(self.get_dim_attribute('centers_with_ghost')):
                    #We could just use indices directly and deal with
                    #numpy arrays instead of lists of numpy arrays
                    self._c_centers_with_ghost.append(center_array[index[i,...]])

    def compute_c_edges(self, recompute=False):
        r"""
        Calculate the :attr:`c_edges` array
        
        This array is computed only when requested and then stored for later
        use unless the recompute flag is set to True.
        
        Access the resulting computational coodinate array via the
        corresponding dimensions or via the computational grid properties
        :attr:`c_edges`.
        
        :Input:
         - *recompute* - (bool) Whether to force a recompute of the arrays
        """
        if recompute or (self._c_edges is None):
            self._c_edges = [None]*self.num_dim

            if self.num_dim == 1:
                self._c_edges[0] = self.dimensions[0].edges
            else:
                index = np.indices(n+1 for n in self.num_cells)
                self._c_edges = []
                for i,edge_array in enumerate(self.get_dim_attribute('edges')):
                    #We could just use indices directly and deal with
                    #numpy arrays instead of lists of numpy arrays
                    self._c_edges.append(edge_array[index[i,...]])
            
    def compute_c_edges_with_ghost(self, num_ghost,recompute=False):
        r"""
        Calculate the :attr:`c_centers_with_ghost` array
        
        This array is computed only when requested and then stored for later
        use unless the recompute flag is set to True.
        
        Access the resulting computational coodinate array via the
        corresponding dimensions or via the computational grid properties
        :attr:`c_centers_with_ghost`.
        
        :Input:
         - *recompute* - (bool) Whether to force a recompute of the arrays
        """
        self.num_ghost = num_ghost
        if recompute or (self._c_edges_with_ghost is None):
            self._c_edges_with_ghost = [None]*self.num_dim

            # For one dimension, the center and edge arrays are equivalent
            for i in xrange(0,self.num_dim):
                self.dimensions[i]._edges_with_ghost = None
                self.dimensions[i].num_ghost = num_ghost

            if self.num_dim == 1:
                self._c_edges_with_ghost[0] = self.dimensions[0].edges_with_ghost
            else:
                index = np.indices(n+2.0*num_ghost+1 for n in self.num_cells)
                self._c_edges_with_ghost = []
                for i,center_array in enumerate(self.get_dim_attribute('edges_with_ghost')):
                    #We could just use indices directly and dneal with
                    #numpy arrays instead of lists of numpy arrays
                    self._c_edges_with_ghost.append(center_array[index[i,...]])

    # ========================================================================
    #  Gauges
    # ========================================================================
    def add_gauges(self,gauge_coords):
        r"""
        Determine the cell indices of each gauge and make a list of all gauges
        with their cell indices.  
        """
        from numpy import floor
        
        for gauge in gauge_coords: 
            # Check if gauge belongs to this grid:
            if all(self.lower[n]<=gauge[n]<self.upper[n] for n in range(self.num_dim)):
                # Set indices relative to this grid
                gauge_index = [int(round((gauge[n]-self.lower[n])/self.delta[n])) 
                               for n in xrange(self.num_dim)]
                gauge_file_name = 'gauge'+'_'.join(str(coord) for coord in gauge)+'.txt'
                self.gauge_file_names.append(gauge_file_name)
                self.gauges.append(gauge_index)

    def setup_gauge_files(self,outdir):
        r"""
        Creates and opens file objects for gauges.
        """
        import os
        gauge_path = os.path.join(outdir,self.gauge_dir_name)
        if not os.path.exists(gauge_path):
            try:
                os.makedirs(gauge_path)
            except OSError:
                print "gauge directory already exists, ignoring"
        
        for gauge in self.gauge_file_names: 
            gauge_file = os.path.join(gauge_path,gauge)
            if os.path.isfile(gauge_file): 
                 os.remove(gauge_file)
            self.gauge_files.append(open(gauge_file,'a'))


   
# ============================================================================
#  Dimension Object
# ============================================================================
class Dimension(object):
    r"""
    Basic class representing a dimension of a Patch object
    
    :Initialization:
    
    Input:
     - *name* - (string) string Name of dimension
     - *lower* - (float) Lower extent of dimension
     - *upper* - (float) Upper extent of dimension
     - *n* - (int) Number of cells
     - *units* - (string) Type of units, used for informational purposes only
       
    Output:
     - (:class:`Dimension`) - Initialized Dimension object

    Example:

    >>> from clawpack.pyclaw.geometry import Dimension
    >>> x = Dimension('x',0.,1.,100)
    >>> print x
    Dimension x:  (num_cells,delta,[lower,upper]) = (100,0.01,[0.0,1.0])
    >>> x.name
    'x'
    >>> x.num_cells
    100
    >>> x.delta
    0.01
    >>> x.edges[0]
    0.0
    >>> x.edges[1]
    0.01
    >>> x.edges[-1]
    1.0
    >>> x.centers[-1]
    0.995
    >>> len(x.centers)
    100
    >>> len(x.edges)
    101
    """
    
    # ========== Property Definitions ========================================
    @property
    def delta(self):
        r"""(float) - Size of an individual, computational cell"""
        return (self.upper-self.lower) / float(self.num_cells)
    @property
    def edges(self):
        r"""(ndarrary(:)) - Location of all cell edge coordinates
        for this dimension"""
        if self._edges is None:
            self._edges = np.empty(self.num_cells+1)   
            for i in xrange(0,self.num_cells+1):
                self._edges[i] = self.lower + i*self.delta
        return self._edges
    _edges = None
    @property
    def centers(self):
        r"""(ndarrary(:)) - Location of all cell center coordinates
        for this dimension"""
        if self._centers is None:
            self._centers = np.empty(self.num_cells)
            for i in xrange(0,self.num_cells):
                self._centers[i] = self.lower + (i+0.5)*self.delta
        return self._centers
    _centers = None
    @property
    def centers_with_ghost(self):
        r"""(ndarrary(:)) - Location of all cell center coordinates
        for this dimension, including centers of ghost cells."""
        centers = self.centers
        num_ghost  = self.num_ghost
        if self._centers_with_ghost is None:
            pre  = np.linspace(self.lower-(num_ghost-0.5)*self.delta,self.lower-0.5*self.delta,num_ghost)
            post = np.linspace(self.upper+0.5*self.delta, self.upper+(num_ghost-0.5)*self.delta,num_ghost)
            self._centers_with_ghost = np.hstack((pre,centers,post))
        return self._centers_with_ghost #np.hstack((pre,centers,post))
    _centers_with_ghost = None
    @property
    def edges_with_ghost(self):
        edges   = self.edges
        num_ghost  = self.num_ghost
        if self._edges_with_ghost is None:
            pre  = np.linspace(self.lower-(num_ghost)*self.delta,self.lower-self.delta,num_ghost)
            post = np.linspace(self.upper+self.delta, self.upper+(num_ghost)*self.delta,num_ghost)
            self._edges_with_ghost = np.hstack((pre,edges,post))
        return self._edges_with_ghost
    _edges_with_ghost = None
    
    def __init__(self, *args, **kargs):
        r"""
        Creates a Dimension object
        
        See :class:`Dimension` for full documentation
        """
        
        # ========== Class Data Attributes ===================================
        self.name = 'x'
        r"""(string) Name of this coordinate dimension (e.g. 'x')"""
        self.num_cells = None
        r"""(int) - Number of cells in this dimension :attr:`units`"""
        self.lower = 0.0
        r"""(float) - Lower computational dimension extent"""
        self.upper = 1.0
        r"""(float) - Upper computational dimension extent"""
        self.on_lower_boundary = None
        r"""(bool) - Whether the dimension is crossing a lower boundary."""
        self.on_upper_boundary = None
        r"""(bool) - Whether the dimension is crossing an upper boundary."""
        self.units = None
        r"""(string) Corresponding physical units of this dimension (e.g. 
        'm/s'), ``default = None``"""
        self.num_ghost = None

        # Parse args
        if isinstance(args[0],float):
            self.lower = float(args[0])
            self.upper = float(args[1])
            self.num_cells = int(args[2])
        elif isinstance(args[0],basestring):
            self.name = args[0]
            self.lower = float(args[1])
            self.upper = float(args[2])
            self.num_cells = int(args[3])
        else:
            raise Exception("Invalid initializer for Dimension.")
        
        for (k,v) in kargs.iteritems():
            setattr(self,k,v)

    def __str__(self):
        output = "Dimension %s" % self.name
        if self.units:
            output += " (%s)" % self.units
        output += ":  (num_cells,delta,[lower,upper]) = (%s,%s,[%s,%s])" \
            % (self.num_cells,self.delta,self.lower,self.upper)
        return output
        

# ============================================================================
#  Pyclaw Patch object definition
# ============================================================================
class Patch(object):
    """
    :Global Patch information:
    
        Each patch has a value for :attr:`level` and :attr:`patch_index`.
    """
    # Global properties
    @property
    def num_cells_global(self): 
        r"""(list) - List of the number of cells in each dimension"""
        return self.get_dim_attribute('num_cells')
    @property
    def lower_global(self):
        r"""(list) - Lower coordinate extents of each dimension"""
        return self.get_dim_attribute('lower')
    @property
    def upper_global(self):
        r"""(list) - Upper coordinate extends of each dimension"""
        return self.get_dim_attribute('upper')
    @property
    def num_dim(self):
        r"""(int) - Number of dimensions"""
        return len(self._dimensions)
    @property
    def dimensions(self):
        r"""(list) - List of :class:`Dimension` objects defining the 
                grid's extent and resolution"""
        return [getattr(self,name) for name in self._dimensions]
    @property
    def delta(self):
        r"""(list) - List of computational cell widths"""
        return self.get_dim_attribute('delta')
    @property
    def name(self):
        r"""(list) - List of names of each dimension"""
        return self._dimensions

    def __init__(self,dimensions):
        self.level = 1
        r"""(int) - AMR level this patch belongs to, ``default = 1``"""
        self.patch_index = 1
        r"""(int) - Patch number of current patch, ``default = 0``"""

        if isinstance(dimensions,Dimension):
            dimensions = [dimensions]
        self._dimensions = []
        for dim in dimensions:
            dim.on_lower_boundary = True
            dim.on_upper_boundary = True
            self.add_dimension(dim)

        self.grid = Grid(dimensions)


        super(Patch,self).__init__()

    def add_dimension(self,dimension):
        r"""
        Add the specified dimension to this patch
        
        :Input:
         - *dimension* - (:class:`Dimension`) Dimension to be added
        """

        # Add dimension to name list and as an attribute
        if dimension.name in self._dimensions:
            raise Exception('Unable to add dimension. A dimension'\
             +' of the same name: {name}, already exists.'\
             .format(name=dimension.name))

        self._dimensions.append(dimension.name)
        setattr(self,dimension.name,dimension)
  
    def get_dim_attribute(self,attr):
        r"""
        Returns a tuple of all dimensions' attribute attr
        """
        return [getattr(getattr(self,name),attr) for name in self._dimensions]
    def __deepcopy__(self,memo={}):
        import copy
        result = self.__class__(copy.deepcopy(self.dimensions))
        result.__init__(copy.deepcopy(self.dimensions))
        
        for attr in ('level','patch_index'):
            setattr(result,attr,copy.deepcopy(getattr(self,attr)))
        
        return result
        
    def __str__(self):
        output = "Patch %s:\n" % self.patch_index
        output += '\n'.join((str(getattr(self,dim)) for dim in self._dimensions))
        return output
    
# ============================================================================
#  Pyclaw Domain object definition
# ============================================================================
class Domain(object):
    r"""
    A Domain is a list of Patches.
    
    A Domain may be initialized in the following ways:

        1. Using 3 arguments, which are in order
            - A list of the lower boundaries in each dimension
            - A list of the upper boundaries in each dimension
            - A list of the number of cells to be used in each dimension

        2. Using a single argument, which is
            - A list of dimensions; or
            - A list of patches.

    :Examples:

        >>> from clawpack import pyclaw
        >>> domain = pyclaw.Domain( (0.,0.), (1.,1.), (100,100))
        >>> print domain.num_dim
        2
        >>> print domain.grid.num_cells
        [100, 100]
    """
    @property
    def num_dim(self):
        r"""(int) - :attr:`Patch.num_dim` of base patch"""
        return self._get_base_patch_attribute('num_dim')
    @property
    def patch(self):
        r"""(:class:`Patch`) - First patch is returned"""
        return self.patches[0]
    @property
    def grid(self):
        r"""(list) - :attr:`Patch.grid` of base patch"""
        return self._get_base_patch_attribute('grid')
 
    def __init__(self,*arg):
        if len(arg)>1:
            lower = arg[0]
            upper = arg[1]
            n     = arg[2]
            dims = []
            names = ['x','y','z']
            names = names[:len(n)+1]
            for low,up,nn,name in zip(lower,upper,n,names):
                dims.append(Dimension(low,up,nn,name=name))
            self.patches = [Patch(dims)]
        else:
            geom = arg[0]
            if not isinstance(geom,list) and not isinstance(geom,tuple):
                geom = [geom]
            if isinstance(geom[0],Patch):
                self.patches = geom
            elif isinstance(geom[0],Dimension):
                self.patches = [Patch(geom)]

    def _get_base_patch_attribute(self, name):
        r"""
        Return base patch attribute name
        
        :Output:
         - (id) - Value of attribute from ``self.patches[0]``
        """
        return getattr(self.patches[0],name)
 

    def __deepcopy__(self,memo={}):
        import copy
        result = self.__class__(copy.deepcopy(self.patches))
        result.__init__(copy.deepcopy(self.patches))

        return result

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = ascii
#!/usr/bin/env python
# encoding: utf-8
r"""
Routines for reading and writing an ascii output file
"""

import os,sys
import logging
import numpy as np
import pickle

from ..util import read_data_line

logger = logging.getLogger('io')

def write(solution,frame,path,file_prefix='fort',write_aux=False,
                    options={},write_p=False):
    r"""
    Write out ascii data file
    
    Write out an ascii file formatted identical to the fortran clawpack files
    including writing out fort.t, fort.q, and fort.aux if necessary.  Note
    that there are some parameters that assumed to be the same for every patch
    in this format which is not necessarily true for the actual data objects.
    Make sure that if you use this output format that all of you patchs share
    the appropriate values of num_dim, num_eqn, num_aux, and t.  Only supports up to
    3 dimensions.
    
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) Pyclaw object to be 
       output.
     - *frame* - (int) Frame number
     - *path* - (string) Root path
     - *file_prefix* - (string) Prefix for the file name.  ``default = 'fort'``
     - *write_aux* - (bool) Boolean controlling whether the associated 
       auxiliary array should be written out.  ``default = False``
     - *options* - (dict) Dictionary of optional arguments dependent on 
       the format being written.  ``default = {}``
    """
    try:
        # Create file name
        file_name = '%s.t%s' % (file_prefix,str(frame).zfill(4))
        f = open(os.path.join(path,file_name),'w')
        
        # Header for fort.txxxx file
        f.write("%18.8e     time\n" % solution.t)
        f.write("%5i                  num_eqn\n" % solution.num_eqn)
        f.write("%5i                  nstates\n" % len(solution.states))
        f.write("%5i                  num_aux\n" % solution.num_aux)
        f.write("%5i                  num_dim\n" % solution.domain.num_dim)
        f.close()
        
        # Open fort.qxxxx for writing
        file_name = 'fort.q%s' % str(frame).zfill(4)
        q_file = open(os.path.join(path,file_name),'w')
        
        # If num_aux != 0 then we open up a file to write it out as well
        if solution.num_aux > 0 and write_aux:
            file_name = 'fort.a%s' % str(frame).zfill(4)
            aux_file = open(os.path.join(path,file_name),'w')
        
        for state in solution.states:
            patch = state.patch

            write_patch_header(q_file,patch)
            
            if write_p:
                q = state.p
            else:
                q = state.q

            write_array(q_file, patch, q)

            if state.num_aux > 0 and write_aux:
                write_patch_header(aux_file,state.patch)
                write_array(aux_file,patch,state.aux)

        q_file.close()

        if state.num_aux > 0 and write_aux:
            aux_file.close()

    except IOError, (errno, strerror):
        logger.error("Error writing file: %s" % os.path.join(path,file_name))
        logger.error("I/O error(%s): %s" % (errno, strerror))
        raise 
    except:
        logger.error("Unexpected error:", sys.exc_info()[0])
        raise

    pickle_filename = os.path.join(path, '%s.pkl' % file_prefix) + str(frame).zfill(4)
    pickle_file = open(pickle_filename,'wb')
    sol_dict = {'t':solution.t,'num_eqn':solution.num_eqn,'nstates':len(solution.states),
                     'num_aux':solution.num_aux,'num_dim':solution.domain.num_dim,
                     'write_aux':write_aux,
                     'problem_data' : solution.problem_data,
                     'mapc2p': solution.state.grid.mapc2p}
    if write_p:
        sol_dict['num_eqn'] = solution.mp

    pickle.dump(sol_dict, pickle_file)
    pickle_file.close()


def write_patch_header(f,patch):
    f.write("%5i                  patch_number\n" % patch.patch_index)
    f.write("%5i                  AMR_level\n" % patch.level)
    for dim in patch.dimensions:
        f.write("%5i                  m%s\n" % (dim.num_cells,dim.name))
    for dim in patch.dimensions:
        f.write("%18.8e     %slow\n" % (dim.lower,dim.name))
    for dim in patch.dimensions:
        f.write("%18.8e     d%s\n" % (dim.delta,dim.name))
    
    f.write("\n")


def write_array(f,patch,q):
    """
    Write a single array to output file f as ASCII text.

    The variable q here may in fact refer to q or to aux.
    """

    dims = patch.dimensions
    if patch.num_dim == 1:
        for k in xrange(dims[0].num_cells):
            for m in xrange(q.shape[0]):
                f.write("%18.8e" % q[m,k])
            f.write('\n')
    elif patch.num_dim == 2:
        for j in xrange(dims[1].num_cells):
            for k in xrange(dims[0].num_cells):
                for m in xrange(q.shape[0]):
                    f.write("%18.8e" % q[m,k,j])
                f.write('\n')    
            f.write('\n')
    elif patch.num_dim == 3:
        for l in xrange(dims[2].num_cells):
            for j in xrange(dims[1].num_cells):
                for k in xrange(dims[0].num_cells):
                    for m in xrange(q.shape[0]):
                        f.write("%18.8e" % q[m,k,j,l])
                    f.write('\n')
                f.write('\n')    
            f.write('\n')
    else:
        raise Exception("Dimension Exception in writing fort file.")


def read(solution,frame,path='./',file_prefix='fort',read_aux=False,
                options={}):
    r"""
    Read in a set of ascii formatted files
    
    This routine reads the ascii formatted files corresponding to the classic
    clawpack format 'fort.txxxx', 'fort.qxxxx', and 'fort.axxxx' or 'fort.aux'
    Note that the fort prefix can be changed.
    
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) Solution object to 
       read the data into.
     - *frame* - (int) Frame number to be read in
     - *path* - (string) Path to the current directory of the file
     - *file_prefix* - (string) Prefix of the files to be read in.  
       ``default = 'fort'``
     - *read_aux* (bool) Whether or not an auxillary file will try to be read 
       in.  ``default = False``
     - *options* - (dict) Dictionary of optional arguments dependent on 
       the format being read in.  ``default = {}``
    """

    pickle_filename = os.path.join(path, '%s.pkl' % file_prefix) + str(frame).zfill(4)
    problem_data = None
    mapc2p = None
    try:
        if os.path.exists(pickle_filename):
            pickle_file = open(pickle_filename,'rb')
            value_dict = pickle.load(pickle_file)
            problem_data = value_dict.get('problem_data',None)
            mapc2p       = value_dict.get('mapc2p',None)
    except IOError:
        logger.info("Unable to open pickle file %s" % (pickle_filename))


    # Construct path names
    base_path = os.path.join(path,)
    q_fname = os.path.join(base_path, '%s.q' % file_prefix) + str(frame).zfill(4)

    # Read in values from fort.t file:
    [t,num_eqn,nstates,num_aux,num_dim] = read_t(frame,path,file_prefix)

    patches = []
    
    # Read in values from fort.q file:
    try:
        f = open(q_fname,'r')
    except IOError:
        print "Error: file " + q_fname + " does not exist or is unreadable."
        raise
    
    n = np.zeros((num_dim))
    d = np.zeros((num_dim))
    lower = np.zeros((num_dim))

    # Loop through every patch setting the appropriate information
    for m in xrange(nstates):
    
        # Read in base header for this patch
        patch_index = read_data_line(f,data_type=int)
        level       = read_data_line(f,data_type=int)
        for i in xrange(num_dim):
            n[i] = read_data_line(f,data_type=int)
        for i in xrange(num_dim):
            lower[i] = read_data_line(f)
        for i in xrange(num_dim):
            d[i] = read_data_line(f)
    
        blank = f.readline()
    
        # Construct the patch
        # Since we do not have names here, we will construct the patch with
        # dimension names x,y,z
        names = ['x','y','z']
        import clawpack.pyclaw as pyclaw
        Dim = pyclaw.Dimension
        dimensions = [Dim(names[i],lower[i],lower[i] + n[i]*d[i],n[i]) for i in xrange(num_dim)]
        patch = pyclaw.geometry.Patch(dimensions)
        state= pyclaw.state.State(patch,num_eqn,num_aux)
        state.t = t
        state.problem_data = problem_data
        if mapc2p is not None:
            # If no mapc2p the default in the identity map in grid will be used
            state.grid.mapc2p = mapc2p

        if num_aux > 0:   
            state.aux[:]=0.
        
        # Fill in q values
        state.q = read_array(f, state, num_eqn)

        # Add AMR attributes:
        patch.patch_index = patch_index
        patch.level = level

        # Add new patch to solution
        solution.states.append(state)
        patches.append(state.patch)
    solution.domain = pyclaw.geometry.Domain(patches)
    f.close()

    # Read auxillary file if available and requested
    # Matching dimension parameter tolerances
    ABS_TOL = 1e-8
    REL_TOL = 1e-15
    if solution.states[0].num_aux > 0 and read_aux:
        # Check for aux file
        fname1 = os.path.join(base_path,'%s.a' % file_prefix)+str(frame).zfill(4)
        fname2 = os.path.join(base_path,'%s.a' % file_prefix)+str(0).zfill(4)
        if os.path.exists(fname1):
            # aux file specific to this frame:
            fname = fname1
        elif os.path.exists(fname2):
            # Assume that aux data from initial time is valid for all frames:
            fname = fname2
            # Note that this is generally not true when AMR is used.
            # Should give a better warning message in line below where
            # IOError exception is raised.
        else:
            logger.info("Unable to open auxillary file %s or %s" % (fname1,fname2))
            return
            
        # Found a valid path, try to open and read it
        try:
            f = open(fname,'r')
        except IOError:
            logger.error("File %s was not able to be read." % fname)
            raise
            
        # Read in aux file
        for state in solution.states:
            patch = state.patch
            # Fetch correct patch
            patch_index = read_data_line(f,data_type=int)
    
            # These should match this patch already, raise exception otherwise
            if not (patch.level == read_data_line(f,data_type=int)):
                raise IOError("Patch level in aux file header did not match patch no %s." % patch.patch_index)
            for dim in patch.dimensions:
                num_cells = read_data_line(f,data_type=int)
                if not dim.num_cells == num_cells:
                    raise Exception("Dimension %s's num_cells in aux file header did not match patch no %s." % (dim.name,patch.patch_index))
            for dim in patch.dimensions:
                lower = read_data_line(f,data_type=float)
                if np.abs(lower - dim.lower) > ABS_TOL + REL_TOL * np.abs(dim.lower):
                    raise Exception('Value of lower in aux file does not match.')
            for dim in patch.dimensions:
                delta = read_data_line(f,data_type=float)
                if np.abs(delta - dim.delta) > ABS_TOL + REL_TOL * np.abs(dim.delta):
                    raise Exception('Value of delta in aux file does not match.')

            blank = f.readline()
    
            state.aux = read_array(f, state, num_aux)

        f.close()
        
            
def read_t(frame,path='./',file_prefix='fort'):
    r"""Read only the fort.t file and return the data
    
    :Input:
     - *frame* - (int) Frame number to be read in
     - *path* - (string) Path to the current directory of the file
     - *file_prefix* - (string) Prefix of the files to be read in.  
       ``default = 'fort'``
     
    :Output:
     - (list) List of output variables
     - *t* - (int) Time of frame
     - *num_eqn* - (int) Number of equations in the frame
     - *nstates* - (int) Number of states
     - *num_aux* - (int) Auxillary value in the frame
     - *num_dim* - (int) Number of dimensions in q and aux
    
    """

    base_path = os.path.join(path,)
    path = os.path.join(base_path, '%s.t' % file_prefix) + str(frame).zfill(4)
    logger.debug("Opening %s file." % path)
    try:
        f = open(path,'r')
    except(IOError):
        print "Error: file " + path + " does not exist or is unreadable."
        raise
        
    t = read_data_line(f)
    num_eqn = read_data_line(f,data_type=int)
    nstates = read_data_line(f,data_type=int)
    num_aux = read_data_line(f,data_type=int)
    num_dim = read_data_line(f,data_type=int)
    
    f.close()
        
    return t,num_eqn,nstates,num_aux,num_dim


def read_array(f, state, num_var):
    """
    Read in an array from an ASCII output file.  

    The variable q here may in fact refer to q or to aux.

    This routine supports the possibility that the values
    q[:,i,j,k] (for a fixed i,j,k) have been split over multiple lines, because
    some packages write just 4 values per line.
    For Clawpack 6.0, we plan to make all packages write
    q[:,i,j,k] on a single line.  This routine can then be simplified.
    """
    patch = state.patch
    q_shape = [num_var] + patch.num_cells_global
    q = np.zeros(q_shape)


    if patch.num_dim == 1:
        for i in xrange(patch.dimensions[0].num_cells):
            l = []
            while len(l)<num_var:
                line = f.readline()
                l = l + line.split()
            for m in xrange(num_var):
                q[m,i] = float(l[m])
    elif patch.num_dim == 2:
        for j in xrange(patch.dimensions[1].num_cells):
            for i in xrange(patch.dimensions[0].num_cells):
                l = []
                while len(l)<num_var:
                    line = f.readline()
                    l = l + line.split()
                for m in xrange(num_var):
                    q[m,i,j] = float(l[m])
            blank = f.readline()
    elif patch.num_dim == 3:
        for k in xrange(patch.dimensions[2].num_cells):
            for j in xrange(patch.dimensions[1].num_cells):
                for i in xrange(patch.dimensions[0].num_cells):
                    l=[]
                    while len(l) < num_var:
                        line = f.readline()
                        l = l + line.split()
                    for m in xrange(num_var):
                        q[m,i,j,k] = float(l[m])
                blank = f.readline()
            blank = f.readline()
    else:
        msg = "Read only supported up to 3d."
        logger.critical(msg)
        raise Exception(msg)

    return q


########NEW FILE########
__FILENAME__ = binary
#!/usr/bin/env python
# encoding: utf-8
r"""
Routines for reading a raw binary output file from AMRClaw.
Note that there is no corresponding output option in PyClaw,
which is why there is no "write" function here (the code that
writes these files is in AMRClaw, in Fortran).
"""

import os
import logging

from ..util import read_data_line
import numpy as np
import clawpack.pyclaw as pyclaw

logger = logging.getLogger('pyclaw.io')


def read(solution,frame,path='./',file_prefix='fort',read_aux=False,
                options={}):
    r"""
    Read in a set of raw binary files
    
    This routine reads the binary formatted files 
    fort.txxxx contains info about frame
    fort.qxxxx still contains headers for each grid patch
    fort.bxxxx is binary dump of data from all patches.
    fort.axxxx is binary dump of aux arrays from all patches.

    Note that the fort prefix can be changed.
    
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) Solution object to 
       read the data into.
     - *frame* - (int) Frame number to be read in
     - *path* - (string) Path to the current directory of the file
     - *file_prefix* - (string) Prefix of the files to be read in.  
       ``default = 'fort'``
     - *read_aux* (bool) Whether or not an auxillary file will try to be read 
       in.  ``default = False``
     - *options* - (dict) Dictionary of optional arguments dependent on 
       the format being read in.  ``default = {}``
    """
    
    # Construct path names
    base_path = os.path.join(path,)
    q_fname = os.path.join(base_path, '%s.q' % file_prefix) + str(frame).zfill(4)
    b_fname = os.path.join(base_path, '%s.b' % file_prefix) + str(frame).zfill(4)

    # Read in values from fort.t file:
    [t,num_eqn,nstates,num_aux,num_dim,num_ghost] = read_t(frame,path,file_prefix)

    patches = []
    
    # Read in values from fort.q file:
    try:
        b_file = open(b_fname,'rb')
    except IOError:
        print "Error: file " + b_fname + " does not exist or is unreadable."
        raise IOError("Could not read binary file %s" % b_fname)

    qdata = np.fromfile(file=b_file, dtype=np.float64)

    i_start_patch = 0  # index into qdata for start of next patch

    try:
        f = open(q_fname,'r')
    except(IOError):
        print "Error: file " + q_fname + " does not exist or is unreadable."
        raise

   
    # Loop through every patch setting the appropriate information
    # for ng in range(len(solution.patchs)):
    for m in xrange(nstates):
    
        # Read in base header for this patch
        patch_index = read_data_line(f,data_type=int)
        level = read_data_line(f,data_type=int)
        n = np.zeros((num_dim))
        lower = np.zeros((num_dim))
        d = np.zeros((num_dim))
        for i in xrange(num_dim):
            n[i] = read_data_line(f,data_type=int)
        for i in xrange(num_dim):
            lower[i] = read_data_line(f)
        for i in xrange(num_dim):
            d[i] = read_data_line(f)
    
        blank = f.readline()
    
        # Construct the patch
        # Since we do not have names here, we will construct the patch with
        # the assumed dimensions x,y,z
        names = ['x','y','z']
        dimensions = []
        for i in xrange(num_dim):
            dimensions.append(
                pyclaw.geometry.Dimension(names[i],lower[i],lower[i] + n[i]*d[i],n[i]))
        patch = pyclaw.geometry.Patch(dimensions)
        state= pyclaw.state.State(patch,num_eqn,num_aux)
        state.t = t

        if num_aux > 0:   
            state.aux[:]=0.
        
        # Fill in q values
        if patch.num_dim == 1:
            ##  NOT YET TESTED ##
            mx = patch.dimensions[0].num_cells
            meqn = state.num_eqn
            mbc = num_ghost
            i_end_patch = i_start_patch + meqn*(mx+2*mbc)
            qpatch = qdata[i_start_patch:i_end_patch]
            qpatch = np.reshape(qpatch, (meqn,mx+2*mbc), \
                        order='F')
            state.q = qpatch[:,mbc:-mbc]
            i_start_patch = i_end_patch  # prepare for next patch

        elif patch.num_dim == 2:
            ## FIXED FOR BINARY ##
            mx = patch.dimensions[0].num_cells
            my = patch.dimensions[1].num_cells
            meqn = state.num_eqn
            mbc = num_ghost
            i_end_patch = i_start_patch + meqn*(mx+2*mbc)*(my+2*mbc)
            qpatch = qdata[i_start_patch:i_end_patch]
            qpatch = np.reshape(qpatch, (meqn,mx+2*mbc,my+2*mbc), \
                        order='F')
            state.q = qpatch[:,mbc:-mbc,mbc:-mbc]
            i_start_patch = i_end_patch  # prepare for next patch

        elif patch.num_dim == 3:
            ##  NOT YET TESTED ##
            mx = patch.dimensions[0].num_cells
            my = patch.dimensions[1].num_cells
            mz = patch.dimensions[2].num_cells
            meqn = state.num_eqn
            mbc = num_ghost
            i_end_patch = i_start_patch + \
                        meqn*(mx+2*mbc)*(my+2*mbc)*(mz+2*mbc)
            qpatch = qdata[i_start_patch:i_end_patch]
            qpatch = np.reshape(qpatch, \
                        (meqn,mx+2*mbc,my+2*mbc,mz+2*mbc), \
                        order='F')
            state.q = qpatch[:,mbc:-mbc,mbc:-mbc,mbc:-mbc]
            i_start_patch = i_end_patch  # prepare for next patch

        else:
            msg = "Read only supported up to 3d."
            logger.critical(msg)
            raise Exception(msg)
    
        # Add AMR attributes:
        patch.patch_index = patch_index
        patch.level = level

        # Add new patch to solution
        solution.states.append(state)
        patches.append(state.patch)
    solution.domain = pyclaw.geometry.Domain(patches)
        
    #-------------
    # aux file:
    #-------------

    # Read auxillary file if available and requested
    if solution.states[0].num_aux > 0 and read_aux:
        # Check for aux file
        fname1 = os.path.join(base_path,'%s.a' % file_prefix)+str(frame).zfill(4)
        fname2 = os.path.join(base_path,'%s.a' % file_prefix)+str(0).zfill(4)
        if os.path.exists(fname1):
            fname = fname1
        elif os.path.exists(fname2):
            fname = fname2
        else:
            logger.info("Unable to open auxillary file %s or %s" % (fname1,fname2))
            return
            
        # Found a valid path, try to open and read it
        try:
            b_file = open(fname,'rb')
            auxdata = np.fromfile(file=b_file, dtype=np.float64)
        except IOError:
            print "Error: file " + fname + " does not exist or is unreadable."
            raise IOError("Could not read binary file %s" % fname)

        i_start_patch = 0  # index into auxdata for start of next patch
        for state in solution.states:
            patch = state.patch

            # Fill in aux values
            if patch.num_dim == 1:
                ##  NOT YET TESTED ##
                mx = patch.dimensions[0].num_cells
                maux = state.num_aux
                mbc = num_ghost
                i_end_patch = i_start_patch + maux*(mx+2*mbc)
                auxpatch = auxdata[i_start_patch:i_end_patch]
                auxpatch = np.reshape(auxpatch, (maux,mx+2*mbc), \
                            order='F')
                state.aux = auxpatch[:,mbc:-mbc]
                i_start_patch = i_end_patch  # prepare for next patch

            elif patch.num_dim == 2:
                ## FIXED FOR BINARY ##
                mx = patch.dimensions[0].num_cells
                my = patch.dimensions[1].num_cells
                maux = state.num_aux
                mbc = num_ghost
                i_end_patch = i_start_patch + maux*(mx+2*mbc)*(my+2*mbc)
                auxpatch = auxdata[i_start_patch:i_end_patch]
                auxpatch = np.reshape(auxpatch, (maux,mx+2*mbc,my+2*mbc), \
                            order='F')
                state.aux = auxpatch[:,mbc:-mbc,mbc:-mbc]
                i_start_patch = i_end_patch  # prepare for next patch

            elif patch.num_dim == 3:
                ##  NOT YET TESTED ##
                mx = patch.dimensions[0].num_cells
                my = patch.dimensions[1].num_cells
                mz = patch.dimensions[2].num_cells
                maux = state.num_aux
                mbc = num_ghost
                i_end_patch = i_start_patch + \
                            maux*(mx+2*mbc)*(my+2*mbc)*(mz+2*mbc)
                auxpatch = auxdata[i_start_patch:i_end_patch]
                auxpatch = np.reshape(auxpatch, \
                            (maux,mx+2*mbc,my+2*mbc,mz+2*mbc), \
                            order='F')
                state.aux = auxpatch[:,mbc:-mbc,mbc:-mbc,mbc:-mbc]
                i_start_patch = i_end_patch  # prepare for next patch

            else:
                logger.critical("Read aux only up to 3d is supported.")
                raise Exception("Read aux only up to 3d is supported.")

            
def read_t(frame,path='./',file_prefix='fort'):
    r"""Read only the fort.t file and return the data


    Note that this version reads in the extra value for num_ghost so that we
    can extract only the data that's relevant.
    
    :Input:
     - *frame* - (int) Frame number to be read in
     - *path* - (string) Path to the current directory of the file
     - *file_prefix* - (string) Prefix of the files to be read in.  
       ``default = 'fort'``
     
    :Output:
     - (list) List of output variables
     - *t* - (int) Time of frame
     - *num_eqn* - (int) Number of equations in the frame
     - *nstates* - (int) Number of states
     - *num_aux* - (int) Auxillary value in the frame
     - *num_dim* - (int) Number of dimensions in q and aux
     - *num_ghost* - (int) Number of ghost cells on each side
    
    """

    base_path = os.path.join(path,)
    path = os.path.join(base_path, '%s.t' % file_prefix) + str(frame).zfill(4)
    try:
        logger.debug("Opening %s file." % path)
        f = open(path,'r')
        
        t = read_data_line(f)
        num_eqn = read_data_line(f, data_type=int)
        nstates = read_data_line(f, data_type=int)
        num_aux = read_data_line(f, data_type=int)
        num_dim = read_data_line(f, data_type=int)
        num_ghost = read_data_line(f, data_type=int)
        
        f.close()
    except(IOError):
        raise
    except:
        logger.error("File " + path + " should contain t, num_eqn, nstates, num_aux, num_dim")
        print "File " + path + " should contain t, num_eqn, nstates, num_aux, num_dim"
        raise
        
    return t,num_eqn,nstates,num_aux,num_dim,num_ghost


########NEW FILE########
__FILENAME__ = hdf5
#!/usr/bin/env python
# encoding: utf-8
r"""
Routines for reading and writing a HDF5 output file

This module reads and writes hdf5 files via either of the following modules:
    h5py - http://code.google.com/p/h5py/
    PyTables - http://www.pytables.org/moin

It will first try h5py and then PyTables and use the correct calls
according to whichever is present on the system.  We recommend that you use
h5py as it is a minimal wrapper to the HDF5 library and will create 

To install either, you must also install the hdf5 library from the website:
    http://www.hdfgroup.org/HDF5/release/obtain5.html
    
:Authors:
    Kyle T. Mandli (2009-02-13) Initial version
"""
# ============================================================================
#      Copyright (C) 2009 Kyle T. Mandli <mandli@amath.washington.edu>
#
#  Distributed under the terms of the Berkeley Software Distribution (BSD) 
#  license
#                     http://www.opensource.org/licenses/
# ============================================================================

import os
import logging

import clawpack.pyclaw.solution

logger = logging.getLogger('pyclaw.io')

# Import appropriate hdf5 package
use_h5py = False
use_PyTables = False
try:
    import h5py
    use_h5py = True
except:
    pass
if not use_h5py:
    try:
        import tables
        use_PyTables = True
    except:
        error_msg = ("Could not import h5py or PyTables, please install " +
            "either h5py or PyTables.  See the doc_string for more " +
            "information.")
        raise Exception(error_msg)

if not use_h5py and not use_PyTables:
    logging.critical("Could not import h5py or PyTables!")

def write(solution,frame,path,file_prefix='claw',write_aux=False,
                options={},write_p=False):
    r"""
    Write out a Solution to a HDF5 file.
    
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) Pyclaw solution 
       object to input into
     - *frame* - (int) Frame number
     - *path* - (string) Root path
     - *file_prefix* - (string) Prefix for the file name.  ``default = 'claw'``
     - *write_aux* - (bool) Boolean controlling whether the associated 
       auxiliary array should be written out.  ``default = False``     
     - *options* - (dict) Optional argument dictionary, see 
       `HDF5 Option Table`_
    
    .. _`HDF5 Option Table`:
    
    +-----------------+------------------------------------------------------+
    | Key             | Value                                                |
    +=================+======================================================+
    | compression     | (None, string ["gzip" | "lzf" | "szip"] or int 0-9)  |
    |                 | Enable dataset compression. DEFLATE, LZF and (where  |
    |                 | available) SZIP are supported. An integer is         |
    |                 | interpreted as a GZIP level for backwards            |
    |                 | compatibility.                                       |
    +-----------------+------------------------------------------------------+
    |compression_opts | (None, or special value) Setting for compression     |
    |                 | filter; legal values for each filter type are:       |
    |                 |                                                      |
    |                 | - *gzip* - (int) 0-9                                 |
    |                 | - *lzf* - None allowed                               |
    |                 | - *szip* - (tuple) 2-tuple ('ec'|'nn', even integer  |
    |                 |     0-32)                                            |
    |                 |                                                      |
    |                 | See the filters module for a detailed description of |
    |                 | each of these filters.                               |
    +-----------------+------------------------------------------------------+
    | chunks          | (None, True or shape tuple) Store the dataset in     |
    |                 | chunked format. Automatically selected if any of the |
    |                 | other keyword options are given. If you don't provide|
    |                 | a shape tuple, the library will guess one for you.   |
    +-----------------+------------------------------------------------------+
    | shuffle         | (True/False) Enable/disable data shuffling, which can|
    |                 | improve compression performance. Automatically       |
    |                 | enabled when compression is used.                    |
    +-----------------+------------------------------------------------------+
    | fletcher32      | (True/False) Enable Fletcher32 error detection; may  |
    |                 | be used with or without compression.                 |
    +-----------------+------------------------------------------------------+
    """
    
    # Option parsing
    option_defaults = {'compression':None,'compression_opts':None,
                       'chunks':None,'shuffle':False,'fletcher32':False}
    for (k,v) in option_defaults.iteritems():
        if options.has_key(k):
            exec("%s = options['%s']" % (k,k))
        else:
            exec('%s = v' % k)
    
    # File name
    filename = os.path.join(path,'%s%s.hdf' % 
                                (file_prefix,str(frame).zfill(4)))
    
    # Write out using h5py
    if use_h5py:
        f = h5py.File(filename,'w')
        
        # For each patch, write out attributes
        for state in solution.states:
            patch = state.patch
            # Create group for this patch
            subgroup = f.create_group('patch%s' % patch.patch_index)
            
            # General patch properties
            for attr in ['t','num_eqn','num_ghost','patch_index','level']:
                if hasattr(patch,attr):
                    if getattr(patch,attr) is not None:
                        subgroup.attrs[attr] = getattr(patch,attr)
                    
            # Add the dimension names as a attribute
            subgroup.attrs['dimensions'] = patch.get_dim_attribute('name')
            # Dimension properties
            for dim in patch.dimensions:
                for attr in ['n','lower','d','upper','bc_lower',
                             'bc_upper','units','num_cells']:
                    if hasattr(dim,attr):
                        if getattr(dim,attr) is not None:
                            attr_name = '%s.%s' % (dim.name,attr)
                            subgroup.attrs[attr_name] = getattr(dim,attr)
            
            # Write out q
            if write_p:
                q = state.p
            else:
                q = state.q
            subgroup.create_dataset('q',data=q,
                                        compression=compression,
                                        compression_opts=compression_opts,
                                        chunks=chunks,shuffle=shuffle,
                                        fletcher32=fletcher32)
            if write_aux and patch.num_aux > 0:
                subgroup.create_dataset('aux',data=patch.aux,
                                        compression=compression,
                                        compression_opts=compression_opts,
                                        chunks=chunks,shuffle=shuffle,
                                        fletcher32=fletcher32)
    
        # Flush and close the file
        f.close()
        
    # Write out using PyTables
    elif use_PyTables:
        # f = tables.openFile(filename, mode = "w", title = options['title'])
        logging.critical("PyTables has not been implemented yet.")
        raise IOError("PyTables has not been implemented yet.")
    else:
        err_msg = "No hdf5 python modules available."
        logging.critical(err_msg)
        raise Exception(err_msg)

def read(solution,frame,path='./',file_prefix='claw',read_aux=True,
                options={}):
    r"""
    Read in a HDF5 file into a Solution
    
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) Pyclaw object to be 
       output
     - *frame* - (int) Frame number
     - *path* - (string) Root path
     - *file_prefix* - (string) Prefix for the file name.  ``default = 'claw'``
     - *write_aux* - (bool) Boolean controlling whether the associated 
       auxiliary array should be written out.  ``default = False``     
     - *options* - (dict) Optional argument dictionary, unused for reading.
    """
    
    # Option parsing
    option_defaults = {}
    for (k,v) in option_defaults.iteritems():
        if options.has_key(k):
            exec("%s = options['%s']" % (k,k))
        else:
            exec('%s = v' % k)
    
    # File name
    filename = os.path.join(path,'%s%s.hdf' % 
                                (file_prefix,str(frame).zfill(4)))

    if use_h5py:
        f = h5py.File(filename,'r')
        
        for subgroup in f.iterobjects():

            # Construct each dimension
            dimensions = []
            dim_names = subgroup.attrs['dimensions']
            for dim_name in dim_names:
                # Create dimension
                dim = pyclaw.solution.Dimension(dim_name,
                                    subgroup.attrs["%s.lower" % dim_name],
                                    subgroup.attrs["%s.upper" % dim_name],
                                    subgroup.attrs["%s.n" % dim_name])                    
                # Optional attributes
                for attr in ['bc_lower','bc_upper','units']:
                    attr_name = "%s.%s" % (dim_name,attr)
                    if subgroup.attrs.get(attr_name, None):
                        setattr(dim,attr,subgroup.attrs["%s.%s" % (dim_name,attr)])
                dimensions.append(dim)
            
            # Create patch
            patch = pyclaw.solution.Patch(dimensions)
                
            # Fetch general patch properties
            for attr in ['t','num_eqn','patch_index','level']:
                setattr(patch,attr,subgroup.attrs[attr])
            
            # Read in q
            index_str = ','.join( [':' for i in xrange(len(subgroup['q'].shape))] )
            exec("patch.q = subgroup['q'][%s]" % index_str)
            
            # Read in aux if applicable
            if read_aux and subgroup.get('aux',None) is not None:
                index_str = ','.join( [':' for i in xrange(len(subgroup['aux'].shape))] )
                exec("patch.aux = subgroup['aux'][%s]" % index_str)
                
            solution.patchs.append(patch)
            
        # Flush and close the file
        f.close()
            
    elif use_PyTables:
        # f = tables.openFile(filename, mode = "r", title = options['title'])
        logging.critical("PyTables has not been implemented yet.")
        raise IOError("PyTables has not been implemented yet.")
    else:
        err_msg = "No hdf5 python modules available."
        logging.critical(err_msg)
        raise Exception(err_msg)
        

########NEW FILE########
__FILENAME__ = netcdf
#!/usr/bin/env python
# encoding: utf-8
r"""
Routines for reading and writing a NetCDF output file

Routines for reading and writing a NetCDF output file via either
    - netcdf4-python - http://code.google.com/p/netcdf4-python/
    - pupynere - http://pypi.python.org/pypi/pupynere/
    
These interfaces are very similar so if a different module needs to be used,
it can more than likely be inserted with a minimal of effort.

This module will first try to import the netcdf4-python module which is based
on the compiled libraries and failing that will attempt to import the pure
python interface pupynere which requires no libraries.

To install the netCDF 4 library, please see:
    http://www.unidata.ucar.edu/software/netcdf/
    
:Authors:
    Kyle T. Mandli (2009-02-17) Initial version
"""
# ============================================================================
#      Copyright (C) 2009 Kyle T. Mandli <mandli@amath.washington.edu>
#
#  Distributed under the terms of the Berkeley Software Distribution (BSD) 
#  license
#                     http://www.opensource.org/licenses/
# ============================================================================

import os,sys
import logging

import clawpack.pyclaw.solution

logger = logging.getLogger('pyclaw.io')

# Import appropriate netcdf package
use_netcdf4 = False
use_pupynere = False
try:
    import netCDF4
    use_netcdf4 = True
except:
    pass
if not use_netcdf4:
    try:
        import pupynere
        use_pupynere = True
    except:
        error_msg = ("Could not import netCDF4 or Pupynere, please install " +
            "one of the available modules for netcdf files.  Refer to this " +
            "modules doc_string for more information.")
        #raise Exception(error_msg)
        print error_msg

def write(solution,frame,path,file_prefix='claw',write_aux=False,
                    options={},write_p=False):
    r"""
    Write out a NetCDF data file representation of solution
    
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) Pyclaw object to be 
       output
     - *frame* - (int) Frame number
     - *path* - (string) Root path
     - *file_prefix* - (string) Prefix for the file name. ``default = 'claw'``
     - *write_aux* - (bool) Boolean controlling whether the associated 
       auxiliary array should be written out. ``default = False``     
     - *options* - (dict) Optional argument dictionary, see 
       `NetCDF Option Table`_
    
    .. _`NetCDF Option Table`:
    
    +-------------------------+----------------------------------------------+
    | Key                     | Value                                        |
    +=========================+==============================================+
    | description             | Dictionary of key/value pairs that will be   |
    |                         | attached to the root group as attributes,    |
    |                         | i.e. {'time':3}                              |
    +-------------------------+----------------------------------------------+
    | format                  | Can be one of the following netCDF flavors:  |
    |                         | NETCDF3_CLASSIC, NETCDF3_64BIT,              |
    |                         | NETCDF4_CLASSIC, and NETCDF4                 |
    |                         | ``default = NETCDF4``                        |
    +-------------------------+----------------------------------------------+
    | clobber                 | if True (Default), file will be overwritten, |
    |                         | if False an exception will be raised         |
    +-------------------------+----------------------------------------------+
    | zlib                    | if True, data assigned to the Variable       |
    |                         | instance is compressed on disk.              |
    |                         | ``default = False``                          |
    +-------------------------+----------------------------------------------+
    | complevel               | the level of zlib compression to use (1 is   |
    |                         | the fastest, but poorest compression, 9 is   |
    |                         | the slowest but best compression).  Ignored  |
    |                         | if zlib=False.  ``default = 6``              |
    +-------------------------+----------------------------------------------+
    | shuffle                 | if True, the HDF5 shuffle filter is applied  |
    |                         | to improve compression. Ignored if           |
    |                         | zlib=False. ``default = True``               |
    +-------------------------+----------------------------------------------+
    | fletcher32              | if True (default False), the Fletcher32      |
    |                         | checksum algorithm is used for error         |
    |                         | detection.                                   |
    +-------------------------+----------------------------------------------+
    | contiguous              | if True (default False), the variable data   |
    |                         | is stored contiguously on disk.  Setting to  |
    |                         | True for a variable with an unlimited        |
    |                         | dimension will trigger an error.             |
    |                         | ``default = False``                          |
    +-------------------------+----------------------------------------------+
    | chunksizes              | Can be used to specify the HDF5 chunksizes   |
    |                         | for each dimension of the variable. A        |
    |                         | detailed discussion of HDF chunking and I/O  |
    |                         | performance is available here. Basically,    |
    |                         | you want the chunk size for each dimension   |
    |                         | to match as closely as possible the size of  |
    |                         | the data block that users will read from the |
    |                         | file. chunksizes cannot be set if            |
    |                         | contiguous=True.                             |
    +-------------------------+----------------------------------------------+
    | least_significant_digit | If specified, variable data will be          |
    |                         | truncated (quantized). In conjunction with   |
    |                         | zlib=True this produces 'lossy', but         |
    |                         | significantly more efficient compression.    |
    |                         | For example, if least_significant_digit=1,   |
    |                         | data will be quantized using around          |
    |                         | (scale*data)/scale, where scale = 2**bits,   |
    |                         | and bits is determined so that a precision   |
    |                         | of 0.1 is retained (in this case bits=4).    |
    |                         | ``default = None``, or no quantization.      |
    +-------------------------+----------------------------------------------+
    | endian                  | Can be used to control whether the data is   |
    |                         | stored in little or big endian format on     | 
    |                         | disk. Possible values are little, big or     |
    |                         | native (default). The library will           |
    |                         | automatically handle endian conversions when |
    |                         | the data is read, but if the data is always  |
    |                         | going to be read on a computer with the      |
    |                         | opposite format as the one used to create    |
    |                         | the file, there may be some performance      |
    |                         | advantage to be gained by setting the        |
    |                         | endian-ness.                                 |
    +-------------------------+----------------------------------------------+
    | fill_value              | If specified, the default netCDF _FillValue  |
    |                         | (the value that the variable gets filled     |
    |                         | with before any data is written to it) is    |
    |                         | replaced with this value. If fill_value is   |
    |                         | set to False, then the variable is not       |
    |                         | pre-filled.                                  |
    +-------------------------+----------------------------------------------+
    
    .. note:: 
        The zlib, complevel, shuffle, fletcher32, contiguous, chunksizes and
        endian keywords are silently ignored for netCDF 3 files that do not 
        use HDF5.
        
    """
    
    # Option parsing
    option_defaults = {'format':'NETCDF4','zlib':False,'complevel':6,
                       'shuffle':True,'fletcher32':False,'contiguous':False,
                       'chunksizes':None,'endian':'native',
                       'least_significant_digit':None,'fill_value':None,
                       'clobber':True,'description':{}}
    for (k,v) in option_defaults.iteritems():
        if options.has_key(k):
            exec("%s = options['%s']" % (k,k))
        else:
            exec('%s = v' % k)
            
    # Filename
    filename = os.path.join(path,"%s%s.nc" % (file_prefix,str(frame).zfill(4)))
        
    if use_netcdf4:
        # Open new file
        f = netCDF4.Dataset(filename,'w',clobber=clobber,format=format)
        
        # Loop through description dictionary and add the attributes to the
        # root group
        for (k,v) in description.iteritems():
            exec('f.%s = %s' % (k,v))
        
        # For each patch, write out attributes
        for state in solution.states:
            patch = solution.patch
            # Create group for this patch
            subgroup = f.createGroup('patch%s' % patch.patch_index)
        
            # General patch properties
            for attr in ['t','num_eqn']:
                setattr(subgroup,attr,getattr(state,attr))
            for attr in ['patch_index','level']:
                setattr(subgroup,attr,getattr(patch,attr))
            
            # Write out dimension names
            setattr(subgroup,'dim_names',patch.name)
            
            # Create dimensions for q (and aux)
            for dim in patch.dimensions:
                subgroup.createDimension(dim.name,dim.num_cells)
                # Write other dimension attributes
                for attr in ['num_cells','lower','delta','upper','bc_lower',
                             'bc_upper','units']:
                    if hasattr(dim,attr):
                        if getattr(dim,attr) is not None:
                            attr_name = '%s.%s' % (dim.name,attr)
                            setattr(subgroup,attr_name,getattr(dim,attr))
            subgroup.createDimension('num_eqn',state.num_eqn)
            
            # Write q array
            from copy import copy
            dim_names = copy(patch.name)
            dim_names.append('num_eqn')
            index_str = ','.join( [':' for name in dim_names] )
            q = subgroup.createVariable('q','f8',dim_names,zlib,
                                            complevel,shuffle,fletcher32,
                                            contiguous,chunksizes,endian,
                                            least_significant_digit,fill_value)
            exec("q[%s] = state.q" % index_str)
            
            # Write out aux
            if state.num_aux > 0 and write_aux:
                dim_names[-1] = 'num_aux'
                subgroup.createDimension('num_aux',state.num_aux)
                aux = subgroup.createVariable('aux','f8',dim_names,
                                            zlib,complevel,shuffle,fletcher32,
                                            contiguous,chunksizes,endian,
                                            least_significant_digit,fill_value)
                exec("aux[%s] = state.aux" % index_str)
        
        f.close()
    elif use_pupynere:
        logging.critical("Pupynere support has not been implemented yet.")
        raise IOError("Pupynere support has not been implemented yet.")
    else:
        err_msg = "No netcdf python modules available."
        logging.critical(err_msg)
        raise Exception(err_msg)

    
def read(solution,frame,path='./',file_prefix='claw',read_aux=True,
                options={}):
    r"""
    Read in a NetCDF data files into solution
    
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) Pyclaw object to be 
       output
     - *frame* - (int) Frame number
     - *path* - (string) Root path
     - *file_prefix* - (string) Prefix for the file name.  ``default = 'claw'``
     - *write_aux* - (bool) Boolean controlling whether the associated 
       auxiliary array should be written out.  ``default = False``     
     - *options* - (dict) Optional argument dictionary, unused for reading.
    """
    
    # Option parsing
    option_defaults = {}
    for (k,v) in option_defaults.iteritems():
        if options.has_key(k):
            exec("%s = options['%s']" % (k,k))
        else:
            exec('%s = v' % k)
            
    # Filename
    filename = os.path.join(path,"%s%s.nc" % (file_prefix,str(frame).zfill(4)))
        
    if use_netcdf4:
        # Open file
        f = netCDF4.Dataset(filename,'r')
        
        # We only expect subgroups of patches, otherwise we need to put some
        # sort of conditional here
        for subgroup in f.groups.itervalues():
            # Construct each dimension
            dimensions = []
            
            # Read in dimension attribute to keep dimension order
            dim_names = getattr(subgroup,'dim_names')
            for dim_name in dim_names:
                dim = pyclaw.solution.Dimension(dim_name, 
                                      getattr(subgroup,'%s.lower' % dim_name),
                                      getattr(subgroup,'%s.upper' % dim_name),
                                      getattr(subgroup,'%s.n' % dim_name))
                 # Optional attributes
                for attr in ['bc_lower','bc_upper','units']:
                    attr_name = "%s.%s" % (dim_name,attr)
                    if hasattr(subgroup,attr_name):
                        setattr(dim,attr,getattr(subgroup, "%s.%s" % (dim_name,attr)))
                dimensions.append(dim)
            
            # Create patch
            patch = pyclaw.solution.Patch(dimensions)
            
            # General patch properties
            for attr in ['t','num_eqn','patch_index','level']:
                setattr(patch,attr,getattr(subgroup,attr))
                
            # Read in q
            index_str = ','.join( [':' for i in xrange(patch.num_dim+1)] )
            exec("patch.q = subgroup.variables['q'][%s]" % index_str)
            
            # Read in aux if applicable
            if read_aux and subgroup.dimensions.has_key('num_aux'):
                exec("patch.aux = subgroup.variables['aux'][%s]" % index_str)
        
            solution.patches.append(patch)
            
        f.close()
    elif use_pupynere:
        logging.critical("Pupynere support has not been implemented yet.")
        raise IOError("Pupynere support has not been implemented yet.")
    else:
        err_msg = "No netcdf python modules available."
        logging.critical(err_msg)
        raise Exception(err_msg)

########NEW FILE########
__FILENAME__ = recon
#Reconstruction functions for SharpClaw

def weno(k, q):
    import numpy as np

    if k != 5:
        raise ValueError, '%d order WENO reconstruction not supported' % k

    epweno=1.e-36

    dqiph = np.diff(q,1)

    LL=3
    UL=q.shape[1]-2
    qr=q.copy()
    ql=q.copy()

    for m1 in [1,2]:
        #m1=1: construct q^-_{i+1/2} (ql)
        #m1=2: construct q^+_{i+1/2} (qr)
        im=(-1)**(m1+1)
        ione=im
        inone=-im
        intwo=-2*im

        #Create references to DQ slices
        dq_intwo=dqiph[:,LL+intwo-1:UL+intwo-1]
        dq_ione =dqiph[:,LL+ione-1 :UL+ione-1 ]
        dq_inone=dqiph[:,LL+inone-1:UL+inone-1]
        dq      =dqiph[:,LL-1:UL-1            ]

        t1 = im*(dq_intwo-dq_inone)
        t2 = im*(dq_inone-dq)
        t3 = im*(dq      -dq_ione)

        tt1=13.*t1**2+3.*(   dq_intwo - 3.*dq_inone)**2
        tt2=13.*t2**2+3.*(   dq_inone +    dq      )**2
        tt3=13.*t3**2+3.*(3.*dq       -    dq_ione )**2

        tt1=(epweno+tt1)**2
        tt2=(epweno+tt2)**2
        tt3=(epweno+tt3)**2
        s1 = tt2*tt3
        s2 = 6.*tt1*tt3
        s3 = 3.*tt1*tt2
        t0 = 1./(s1+s2+s3)
        s1 *= t0
        s3 *= t0

        z=(s1*(t2-t1)+(0.5*s3-0.25)*(t3-t2))/3. \
                + (-q[:,LL-2:UL-2]+7.*(q[:,LL-1:UL-1]+q[:,LL:UL])-q[:,LL+1:UL+1])/12.
        if m1==1: qr[:,LL-1:UL-1] = z
        else: ql[:,LL:UL] = z

    return ql,qr

def weno5_wave(q,wave,s):

    import numpy as np

    epweno=1.e-36

    qr=q.copy()
    ql=q.copy()
    LL=2
    UL=q.shape[1]-3
    num_waves=wave.shape[1]
    num_eqn=wave.shape[0]
    for m1 in [1,2]:
        #m1=1: construct q^-_{i+1/2} (ql)
        #m1=2: construct q^+_{i+1/2} (qr)
        im=(-1)**(m1+1)
        ione=im
        inone=-im
        intwo=-2*im

        for mw in xrange(num_waves):
            wnorm2 = wave[0,mw,LL:UL]**2
            theta1 = wave[0,mw,LL+intwo:UL+intwo]*wave[0,mw,LL:UL]
            theta2 = wave[0,mw,LL+inone:UL+inone]*wave[0,mw,LL:UL]
            theta3 = wave[0,mw,LL+ione :UL+ione ]*wave[0,mw,LL:UL]
            for m in xrange(1,num_eqn):
                wnorm2 += wave[m,mw,LL:UL]**2
                theta1 += wave[m,mw,LL+intwo:UL+intwo]*wave[m,mw,LL:UL]
                theta2 += wave[m,mw,LL+inone:UL+inone]*wave[m,mw,LL:UL]
                theta3 += wave[m,mw,LL+ione :UL+ione ]*wave[m,mw,LL:UL]

            t1=im*(theta1-theta2)
            t2=im*(theta2-wnorm2)
            t3=im*(wnorm2-theta3)

            tt1=13.*t1**2+3.*(   theta1 - 3.*theta2)**2
            tt2=13.*t2**2+3.*(   theta2 +    wnorm2)**2
            tt3=13.*t3**2+3.*(3.*wnorm2 -    theta3)**2

            tt1=(epweno+tt1)**2
            tt2=(epweno+tt2)**2
            tt3=(epweno+tt3)**2
            s1 = tt2*tt3
            s2 = 6.*tt1*tt3
            s3 = 3.*tt1*tt2
            t0 = 1./(s1+s2+s3)
            s1 *= t0
            s3 *= t0

            z=(s1*(t2-t1)+(0.5*s3-0.25)*(t3-t2))/3. \
                    + im*(theta2+6.*wnorm2-theta3)/12.
            u=np.where(wnorm2>1.e-14,z,0.)
            wnorm2=np.where(wnorm2>1.e-14,1./wnorm2,1.)

            for m in xrange(num_eqn):
                if m1==1: qr[m,LL:UL] += u*wave[m,mw,LL:UL]*wnorm2
                else: ql[m,LL+1:UL+1] += u*wave[m,mw,LL:UL]*wnorm2

    return ql,qr

########NEW FILE########
__FILENAME__ = reconstruct
r"""(Py)WENO based reconstructor for hyperbolic PDEs.

The :py:mod:`weno.reconstruct` module needs to be built before this
module can be used.  See 'weno/codegen.py' for details.

To build a higher order reconstruction, *k* needs to be tweaked here
and in 'weno/codegen.py'.  Also, *num_ghost* needs to be tweaked in the
PyClaw solver.

"""

import weno.reconstruct as recon

def weno(k, q):
    r"""Return the *k* order WENO based reconstruction of *q*.

    The reconstruction is component based.
    """

    import numpy as np
    # XXX: this should really by a class so that the workspaces (sigma
    # and weights) can be pre-allocated and the 'getattr's can be done
    # once instead of every call

    if (k % 2) == 0:
        raise ValueError, 'even order WENO reconstructions are not supported'

    k = (k+1)/2
    sigma = np.zeros((q.shape[1], k))
    weights = np.zeros((q.shape[1], k))

    ql = np.zeros(q.shape)
    qr = np.zeros(q.shape)

    try:
        smoothness    = getattr(recon, 'smoothness_k' + str(k))
        weights_l     = getattr(recon, 'weights_left_k' + str(k))
        weights_r     = getattr(recon, 'weights_right_k' + str(k))
        reconstruct_l = getattr(recon, 'reconstruct_left_k' + str(k))
        reconstruct_r = getattr(recon, 'reconstruct_right_k' + str(k))
    except:
        raise ValueError, '%d order WENO reconstructions are not supported' % (2*k-1)


    for m in range(q.shape[0]):
        smoothness(q[m,:], sigma)

        weights_l(sigma, weights)
        reconstruct_l(q[m,:], weights, ql[m,:])

        weights_r(sigma, weights)
        reconstruct_r(q[m,:], weights, qr[m,:])


    # XXX: copy ghost-cells.  i'm not sure why this is necessary, but
    # it make the acoustics examples in the implicit time-stepping
    # branch work properly.

    ql[:,:k-1]  = ql[:,-2*k+2:-k+1]
    ql[:,-k+1:] = ql[:,k-1:2*k-2]

    qr[:,:k-1]  = qr[:,-2*k+2:-k+1]
    qr[:,-k+1:] = qr[:,k-1:2*k-2]

    return ql, qr

########NEW FILE########
__FILENAME__ = tvd
#!/usr/bin/env python
# encoding: utf-8
r"""
Library of limiter functions to be applied to waves

This module contains all of the standard limiters found in clawpack.  To
use any of the limiters, use the function limit to limit the appropriate
waves.  Refer to each limiter and the function limit's doc strings.

This is a list of the provided limiters and their corresponding method number,
note that some of the limiters actually correspond to a more general function
which can be controlled more directly.  Refer to the limiter function and its
corresponding documentation for details.

CFL Independent Limiters
''''''''''''''''''''''''
1. minmod - :func:`minmod_limiter`
2. superbee - :func:`superbee_limiter`
3. van leer - :math:`(r + |r|) / (1 + |r|)`
4. mc - :func:`mc_limiter`
5. Beam-warming - :math:`r`
6. Frommm - :math:`1/2 (1 + r)`
7. Albada 2 - :math:`(r^2 + r) / (1 + r^2)`
8. Albada 3 - :math:`1/2 (1+r) (1 - (|1-r|^3) / (1+|r|^3))`
9. van Leer with Klein sharpening, k=2 - 
   :func:`van_leer_klein_sharpening_limiter`

CFL Dependent Limiters
''''''''''''''''''''''
10. Roe's linear third order scheme - :math:`1 + (r-1) (1 + cfl) / 3`
11. Arora-Roe (= limited version of the linear third order scheme) - 
    :func:`arora_roe`
12. Theta Limiter, theta=0.95 (safety on nonlinear waves) - 
    :func:`theta_limiter`
13. Theta Limiter, theta=0.75 - :func:`theta_limiter`
14. Theta Limiter, theta=0.5 - :func:`theta_limiter`
15. CFL-Superbee (Roe's Ultrabee)  - :func:`cfl_superbee`
16. CFL-Superbee (Roe's Ultrabee) with theta=0.95 (nonlinear waves) - 
    :func:`cfl_superbee_theta`
17. beta=2/3 limiter - :func:`beta_limiter`
18. beta=2/3 limiter with theta=0.95 (nonlinear waves) - :func:`beta_limiter`
19. Hyperbee - :func:`hyperbee_limiter`
20. SuperPower - :func:`superpower_limiter`
21. Cada-Torrilhon modified - :func:`cada_torrilhon_limiter`
22. Cada-Torrilhon modified, version for nonlinear waves - 
    :func:`cada_torrilhon_limiter_nonlinear`
23. upper bound limiter (1st order) - :func:`upper_bound_limiter`
    
All limiters have the same function call signature:
    :Input:
     - *r* - (ndarray(:)) 
     - *cfl* - (ndarray(:)) Local CFL number
     
    :Output:
     - (ndarray(:)) - 

Newer limiters are based on work done by Friedemann Kemm [kemm_2009]_, paper 
in review.
    
:Authors:
    Kyle Mandli and Randy LeVeque (2008-08-21) Initial version
    
    Kyle Mandli (2009-07-05) Added CFL depdendent limiters
"""
# ============================================================================
#      Copyright (C) 2008 Kyle T. Mandli <mandli@amath.washington.edu>
#      Copyrigth (C) 2009 Randall J. LeVeque <rjl@amath.washington.edu>
#
#  Distributed under the terms of the Berkeley Software Distribution (BSD) 
#  license
#                     http://www.opensource.org/licenses/
# ============================================================================

minmod = 1
superbee = 2
vanleer = 3
MC = 4

import numpy as np

def limit(num_eqn,wave,s,limiter,dtdx):
    r"""
    Apply a limiter to the waves

    Function that limits the given waves using the methods contained
    in limiter.  This is the vectorized version of the function acting on a 
    row of waves at a time.
    
    :Input:
     - *wave* - (ndarray(:,num_eqn,num_waves)) The waves at each interface
     - *s* - (ndarray(:,num_waves)) Speeds for each wave
     - *limiter* - (``int`` list) Array of type ``int`` determining which 
         limiter to use
     - *dtdx* - (ndarray(:)) :math:`\Delta t / \Delta x` ratio, used for CFL 
        dependent limiters
        
    :Output:
     - (ndarray(:,num_eqn,num_waves)) - Returns the limited waves

    :Version: 1.1 (2009-07-05)
    """
    
    # wave_norm2 is the sum of the squares along the num_eqn axis,
    # so the norm of the cell i for wave number j is addressed 
    # as wave_norm2[i,j]
    wave_norm2 = np.sum(np.square(wave),axis=0)
    wave_zero_mask = np.array((wave_norm2 == 0), dtype=float)
    wave_nonzero_mask = (1.0-wave_zero_mask)

    # dotls contains the products of adjacent cell values summed
    # along the num_eqn axis.  For reference, dotls[0,:,:] is the dot
    # product of the 0 cell and the 1 cell.
    dotls = np.sum(wave[:,:,1:]*wave[:,:,:-1],axis=0)

    # array containing ones where s > 0, zeros elsewhere
    spos = np.array(s > 0.0, dtype=float)[:,1:-1]

    # Here we construct a masked array, then fill the empty values with 0,
    # this is done in case wave_norm2 is 0 or close to it
    # Take upwind dot product
    r = np.ma.array((spos*dotls[:,:-1] + (1-spos)*dotls[:,1:]))
    # Divide it by the norm**2
    r /= np.ma.array(wave_norm2[:,1:-1])
    # Fill the rest of the array
    r.fill_value = 0
    r = r.filled()
    
    for mw in xrange(wave.shape[1]):
        # skip waves that are marked as not needing a limiter
        limit_func = limiter_functions.get(limiter[mw])
        if limit_func is not None:
            for m in xrange(num_eqn):
                cfl = np.abs(s[mw,1:-1]*(dtdx[1:-2]*spos[mw,:] 
                                        + (1-spos[mw,:])*dtdx[2:-1]))
                wlimitr = limit_func(r[mw,:],cfl)
                wave[m,mw,1:-1] = wave[m,mw,1:-1]*wave_zero_mask[mw,1:-1] \
                    + wlimitr * wave[m,mw,1:-1] * wave_nonzero_mask[mw,1:-1]

    return wave

def minmod_limiter(r,cfl):
    r"""
    Minmod vectorized limiter
    """
    a = np.ones((2,len(r)))
    b = np.zeros((2,len(r)))
    
    a[1,:] = r
    
    b[1,:] = np.min(a,axis=0)
    
    return np.max(b,axis=0)
    

def superbee_limiter(r,cfl):
    r"""
    Superbee vectorized limiter
    """
    a = np.ones((2,len(r)))
    b = np.zeros((2,len(r)))
    c = np.zeros((3,len(r)))

    a[1,:] = 2.0*r
    
    b[1,:] = r

    c[1,:] = np.min(a,axis=0)
    c[2,:] = np.min(b,axis=0)

    return np.max(c,axis=0)
    
def mc_limiter(r,cfl):
    r"""
    MC vectorized limiter
    """
    a = np.empty((3,len(r)))
    b = np.zeros((2,len(r)))

    a[0,:] = (1.0 + r) / 2.0
    a[1,:] = 2
    a[2,:] = 2.0 * r
    
    b[1,:] = np.min(a,axis=0)

    return np.max(b,axis=0)
    
def van_leer_klein_sharpening_limiter(r,cfl):
    r"""
    van Leer with Klein sharpening, k=2
    """
    a = np.ones((2,len(r))) * 1.e-5
    a[0,:] = r
    
    rcorr = np.max(a,axis=0)
    a[1,:] = 1/rcorr
    sharg = np.min(a,axis=0)
    sharp = 1.0 + sharg * (1.0 - sharg) * (1.0 - sharg**2)
    
    return (r+np.abs(r)) / (1.0 + np.abs(r)) * sharp

def arora_roe(r,cfl):
    r"""
    Arora-Roe limiter, limited version of the linear third order scheme
    """
    caut = 0.99
    
    a = np.empty((3,len(r)))
    b = np.zeros((2,len(r)))
    
    s1 = (caut * 2.0 / cfl)
    s2 = (1.0 + cfl) / 3.0
    phimax = caut * 2.0 / (1.0 - cfl)
    
    a[0,:] = s1 * r
    a[1,:] = 1.0 + s2 * (r - 1.0)
    a[2,:] = phimax
    b[1,:] = np.min(a,axis=0)
    
    return np.max(b,axis=0)

def theta_limiter(r,cfl,theta=0.95):
    r"""
    Theta limiter
    
    Additional Input:
     - *theta* =
    """
    a = np.empty((2,len(r)))
    b = np.empty((3,len(r)))
    
    a[0,:] = 0.001
    a[1,:] = cfl
    cfmod1 = np.max(a,axis=0)
    a[0,:] = 0.999
    cfmod2 = np.min(a,axis=0)
    s1 = 2.0 / cfmod1
    s2 = (1.0 + cfl) / 3.0
    phimax = 2.0 / (1.0 - cfmod2)
    
    a[0,:] = (1.0 - theta) * s1
    a[1,:] = 1.0 + s2 * (r - 1.0)
    left = np.max(a,axis=0)
    a[0,:] = (1.0 - theta) * phimax * r
    a[1,:] = theta * s1 * r
    middle = np.max(a,axis=0)
    
    b[0,:] = left
    b[1,:] = middle
    b[2,:] = theta*phimax
    
    return np.min(b,axis=0)
    
def cfl_superbee(r,cfl):
    r"""
    CFL-Superbee (Roe's Ultrabee) without theta parameter
    """
    a = np.empty((2,len(r)))
    b = np.zeros((3,len(r)))
    
    a[0,:] = 0.001
    a[1,:] = cfl
    cfmod1 = np.max(a,axis=0)
    a[0,:] = 0.999
    cfmod2 = np.min(a,axis=0)
    
    a[0,:] = 1.0
    a[1,:] = 2.0 * r / cfmod1
    b[1,:] = np.min(a,axis=0)
    a[0,:] = 2.0/(1-cfmod2)
    a[1,:] = r
    b[2,:] = np.min(a,axis=0)
    
    return np.max(b,axis=0)

    
def cfl_superbee_theta(r,cfl,theta=0.95):
    r"""
    CFL-Superbee (Roe's Ultrabee) with theta parameter
    """
    a = np.empty((2,len(r)))
    b = np.zeros((2,len(r)))
    
    a[0,:] = 0.001
    a[1,:] = cfl
    cfmod1 = np.max(a,axis=0)
    a[0,:] = 0.999
    cfmod2 = np.min(a,axis=0)

    s1 = theta * 2.0 / cfmod1
    phimax = theta * 2.0 / (1.0 - cfmod2)

    a[0,:] = s1*r
    a[1,:] = phimax
    b[1,:] = np.min(a,axis=0)
    ultra = np.max(b,axis=0)
    
    a[0,:] = ultra
    b[0,:] = 1.0
    b[1,:] = r
    a[1,:] = np.max(b,axis=0)
    return np.min(a,axis=0)

def beta_limiter(r,cfl,theta=0.95,beta=0.66666666666666666):
    r"""
    Modification of CFL Superbee limiter with theta and beta parameters
    
    Additional Input:
     - *theta*
     - *beta*
    """
    a = np.empty((2,len(r)))
    b = np.zeros((2,len(r)))
    
    a[0,:] = 0.001
    a[1,:] = cfl
    cfmod1 = np.max(a,axis=0)
    a[0,:] = 0.999
    cfmod2 = np.min(a,axis=0)
    
    s1 = theta * 2.0 / cfmod1
    s2 = (1.0 + cfl) / 3.0
    phimax = theta * 2.0 / (1.0 - cfmod2)
    
    a[0,:] = s1*r
    a[1,:] = phimax
    b[1,:] = np.min(a)
    ultra = np.max(b)
    
    a[0,:] = 1.0 + (s2 - beta/2.0) * (r-1.0)
    a[1,:] = 1.0 + (s2 + beta/2.0) * (r-1.0)
    b[0,:] = ultra
    b[1,:] = np.max(a)
    a[0,:] = 0.0
    a[1,:] = np.min(b)
    
    return np.max(a)


def hyperbee_limiter(r,cfl):
    r"""Hyperbee"""
    a = np.empty((2,len(r)))
    
    a[0,:] = 0.001
    a[1,:] = cfl
    cfmod1 = np.max(a,axis=0)
    a[0,:] = 0.999
    cfmod2 = np.min(a,axis=0)
    
    index1 = r < 0.0
    index2 = np.abs(r-1.0) < 1.0e-6
    index3 = np.abs(index1 + index2 - 1)
    master_index = index1 * 0 + index2 * 1 + index3 * 2

    rmin = r-1.0
    rdur = r/rmin
    return np.choose(master_index,[0.0,1.0,
                                    2.0 * rdur * (cfl * rmin + 1.0 - r**cfl) 
                                    / (cfmod1 * (1.0 - cfmod2) * rmin)])
    
def superpower_limiter(r,cfl,caut=1.0):
    r"""
    SuperPower limiter
    
    Additional input:
     - *caut* = Limiter parameter
    """
    s2 = (1.0 + cfl) / 3.0
    s3 = 1.0 - s2
    
    pp = (((r<=1.0) * np.abs(2.0/cfl) * caut) * 2.0 * s3 
            + (r > 1.0) * (np.abs(2.0)/(1.0 - cfl) * caut) * 2.0 * s2)
            
    rabs = np.abs(r)
    rfrac = np.abs((1.0 - rabs) / (1.0 + rabs))
    signum = np.floor(0.5 * (1.0 + np.sign(r)))
    
    return signum * (s3 + s2 * r) * (1.0 - rfrac**pp)
    
def cada_torrilhon_limiter(r,cfl,epsilon=1.0e-3):
    r"""
    Cada-Torrilhon modified
    
    Additional Input:
     - *epsilon* = 
    """
    a = np.ones((2,len(r))) * 0.95
    b = np.empty((3,len(r)))

    a[0,:] = cfl
    cfl = np.min(a)
    a[1,:] = 0.05
    cfl = np.max(a)
    
    # Multiply all parts except b[0,:] by (1.0 - epsilon) as well
    b[0,:] = 1.0 + (1+cfl) / 3.0 * (r - 1)
    b[1,:] = 2.0 * np.abs(r) / (cfl + epsilon)
    b[2,:] = (8.0 - 2.0 * cfl) / (np.abs(r) * (cfl - 1.0 - epsilon)**2)
    b[1,::2] *= (1.0 - epsilon)
    a[0,:] = np.min(b)
    a[1,:] = (-2.0 * (cfl**2 - 3.0 * cfl + 8.0) * (1.0-epsilon)
                    / (np.abs(r) * (cfl**3 - cfl**2 - cfl + 1.0 + epsilon)))
    
    return np.max(a)
    
def cada_torrilhon_limiter_nonlinear(r,cfl):
    r"""
    Cada-Torrilhon modified, version for nonlinear waves
    """
    a = np.empty((3,len(r)))
    b = np.empty((2,len(r)))
    
    s2 = (1.0 + cfl) / 3.0
    a[0,:] = 1.0 + s2 * (r - 1.0)
    a[1,:] = 2.0 * np.abs(r) / (0.6 + np.abs(r))
    a[2,:] = 5.0 / np.abs(r)
    b[0,:] = np.min(a)
    b[1,:] = -3.0 / np.abs(r)
    
    return np.max(b)
    
def upper_bound_limiter(r,cfl,theta=1.0):
    r"""
    Upper bound limiter (1st order)
    
    Additional Input:
     - *theta* =
     """
    a = np.empty((2,len(r)))
    b = np.zeros((2,len(r)))
    
    a[0,:] = 0.001
    a[1,:] = cfl
    cfmod1 = np.max(a,axis=0)
    a[0,:] = 0.999
    cfmod2 = np.min(a,axis=0)
    
    s1 = theta * 2.0 / cfmod1
    phimax = theta * 2.0 / (1.0 - cfmod2)
    
    a[0,:] = s1*r
    a[1,:] = phimax
    b[1,:] = np.min(a)
    
    return np.max(b)


# ============================================================================
#  Limiter function dictionary
# ============================================================================
limiter_functions = {1:minmod_limiter,
                     2:superbee_limiter,
                     3:lambda r,cfl:(r + np.abs(r)) / (1.0 + np.abs(r)),
                     4:mc_limiter,
                     5:lambda r,cfl:r,
                     6:lambda r,cfl:0.5*(1.0 + r),
                     7:lambda r,cfl:(r**2 + r) / (1.0 + r**2),
                     8:lambda r,cfl:0.5*(1+r)*(1 - np.abs(1-(r))**3/(1+np.abs(r)**3)),
                     9:van_leer_klein_sharpening_limiter,
                     10:lambda r,cfl:1.0 + (1.0 + cfl) / 3.0*(r-1.0),
                     11:arora_roe,
                     12:theta_limiter,
                     13:lambda r,cfl:theta_limiter(r,cfl,0.75),
                     14:lambda r,cfl:theta_limiter(r,cfl,0.5),
                     15:cfl_superbee,
                     16:cfl_superbee_theta,
                     17:lambda r,cfl:beta_limiter(r,cfl,theta=0.0),
                     18:beta_limiter,
                     19:hyperbee_limiter,
                     20:superpower_limiter,
                     21:cada_torrilhon_limiter,
                     22:cada_torrilhon_limiter_nonlinear,
                     23:upper_bound_limiter}

########NEW FILE########
__FILENAME__ = codegen
r"""Generate C code to compute a 2k-1 order WENO reconstructions.

This generates a Python extension module (written in C) to perform
WENO reconstructions.

Usage:

$ python codegen.py
$ python setup.py build
$ cp build/lib*/reconstruct.so .

Note: the naming convection in PyWENO is cell based: 'left' means the
left edge of a cell, and 'right' means the right edge of a cell.
Matching this up with how PyClaw expects 'ql' and 'qr' to be indexed
is a bit tricky.

"""

import os

import pyweno.symbolic
import pyweno.c

# config

K = range(3, 10)                        # 2*k-1 order reconstructions
module = 'reconstruct'                  # py module name
output = module + '.c'

# open output and init

f = open(output, 'w')

c = pyweno.c.CCodeGenerator()
f.write(c.wrapper_head(module))

# smoothness
for k in K:

    print 'generating code for k = %d...' % k

    beta = pyweno.symbolic.jiang_shu_smoothness_coefficients(k)
    c.set_smoothness(beta)

    f.write(c.uniform_smoothness(function='smoothness_k'+str(k),
                                 wrapper=True))

    # left edge of cell (right side of boundary)

    (varpi, split) = pyweno.symbolic.optimal_weights(k, 'left')
    coeffs = pyweno.symbolic.reconstruction_coefficients(k, 'left')

    c.set_optimal_weights(varpi, split)
    c.set_reconstruction_coefficients(coeffs)

    f.write(c.uniform_weights(function='weights_left_k' + str(k),
                              wrapper=True))
    f.write(c.uniform_reconstruction(function='reconstruct_left_k' + str(k),
                                     wrapper=True))

    # right edge of cell (left side boundary, shifted)

    (varpi, split) = pyweno.symbolic.optimal_weights(k, 'right')
    coeffs = pyweno.symbolic.reconstruction_coefficients(k, 'right')

    c.set_optimal_weights(varpi, split)
    c.set_reconstruction_coefficients(coeffs)

    f.write(c.uniform_weights(function='weights_right_k' + str(k),
                              wrapper=True))
    f.write(c.uniform_reconstruction(function='reconstruct_right_k' + str(k),
                                     wrapper=True))


f.write(c.wrapper_foot())
f.close()

try:
    import os
    os.system('indent ' + output)
except:
    pass

########NEW FILE########
__FILENAME__ = plot
r"""Convenience routines for easily plotting with VisClaw."""

import os
import sys
import types

def plot(setplot=None, outdir="./_output", plotdir=None, htmlplot=False, 
         iplot=True, file_format='ascii', **plot_kargs):
    r"""setplot can be a function or a path to a file."""
    
    # Construct a plot directory if not provided
    if plotdir is None:
        try: 
            plotdir = os.path.join(os.path.split(outdir)[:-2],"_plots")
        except AttributeError:
            plotdir = os.path.join(os.getcwd(),"_plots")
    
    if htmlplot or iplot:
        # No setplot specified, try to use a local file
        if setplot is None:
            # Grab and import the setplot function
            local_setplot_path = os.path.join(os.getcwd(),'setplot.py')
            if os.path.exists(local_setplot_path):
                setplot = local_setplot_path

        # Fetch setplot function depending on type of setplot
        if isinstance(setplot, types.FunctionType):
            # setplot points to a function
            setplot_func = lambda plotdata:setplot(plotdata, **plot_kargs)

        elif isinstance(setplot, types.ModuleType):
            # setplot points to a module
            setplot_func = lambda plotdata:setplot.setplot(plotdata, **plot_kargs)
            
        elif isinstance(setplot, basestring):
            # setplot contains a path to a module
            path = os.path.abspath(os.path.expandvars(os.path.expanduser(setplot)))
            setplot_module_dir = os.path.dirname(path)
            setplot_module_name = os.path.splitext(os.path.basename(setplot))[0]
            sys.path.insert(0,setplot_module_dir)
            setplot_module = __import__(setplot_module_name)
            setplot_func = lambda plotdata:setplot_module.setplot(plotdata, **plot_kargs)
        
        if not isinstance(setplot_func, types.FunctionType):
            # Everything else has failed, use default setplot
            import clawpack.visclaw.setplot_default as setplot_module
            setplot_func = setplot_module.setplot

        # Interactive plotting
        if iplot:
            from clawpack.visclaw import Iplotclaw
        
            ip = Iplotclaw.Iplotclaw(setplot=setplot_func, outdir=outdir)
            ip.plotdata.format = file_format
        
            ip.plotloop()
            
        # Static HTML plotting
        if htmlplot:
            from clawpack.visclaw import plotclaw
            plotclaw.plotclaw(outdir, plotdir, format=file_format,
                                               setplot=setplot_func)
        

# These now just point to the above more generic function
def interactive_plot(outdir='./_output', file_format='ascii', setplot=None):
    """Convenience function for launching an interactive plotting session."""
    plot(setplot, outdir=outdir, file_format=file_format, iplot=True, 
                  htmlplot=False)


def html_plot(outdir='./_output', file_format='ascii', setplot=None):
    """Convenience function for creating html page with plots."""
    plot(setplot, outdir=outdir, file_format=file_format, htmlplot=True, 
                  iplot=False)

########NEW FILE########
__FILENAME__ = solver
r"""
Module containing SharpClaw solvers for PyClaw/PetClaw

#  File:        sharpclaw.py
#  Created:     2010-03-20
#  Author:      David Ketcheson
"""
# Solver superclass
from clawpack.pyclaw.solver import Solver, CFLError
from clawpack.pyclaw.util import add_parent_doc

# Reconstructor
try:
    # load c-based WENO reconstructor (PyWENO)
    from clawpack.pyclaw.limiters import reconstruct as recon
except ImportError:
    # load old WENO5 reconstructor
    from clawpack.pyclaw.limiters import recon

def before_step(solver,solution):
    r"""
    Dummy routine called before each step
    
    Replace this routine if you want to do something before each time step.
    """
    pass

class SharpClawSolver(Solver):
    r"""
    Superclass for all SharpClawND solvers.

    Implements Runge-Kutta time stepping and the basic form of a 
    semi-discrete step (the dq() function).  If another method-of-lines
    solver is implemented in the future, it should be based on this class,
    which then ought to be renamed to something like "MOLSolver".

    .. attribute:: before_step
    
        Function called before each time step is taken.
        The required signature for this function is:
        
        def before_step(solver,solution)

    .. attribute:: lim_type

        Limiter(s) to be used.
        0: No limiting.
        1: TVD reconstruction.
        2: WENO reconstruction.
        ``Default = 2``

    .. attribute:: weno_order

        Order of the WENO reconstruction. From 1st to 17th order (PyWENO)
        ``Default = 5``

    .. attribute:: time_integrator

        Time integrator to be used.
        Euler: forward Euler method.
        SSP33: 3-stages, 3rd-order SSP Runge-Kutta method.
        SSP104: 10-stages, 4th-order SSP Runge-Kutta method.
        ``Default = 'SSP104'``

    .. attribute:: char_decomp

        Type of WENO reconstruction.
        0: conservative variables WENO reconstruction (standard).
        1: Wave-slope reconstruction.
        2: characteristic-wise WENO reconstruction.
        3: transmission-based WENO reconstruction.
        ``Default = 0``

    .. attribute:: tfluct_solver

        Whether a total fluctuation solver have to be used. If True the function
        that calculates the total fluctuation must be provided.
        ``Default = False``

    .. attribute:: aux_time_dep

        Whether the auxiliary array is time dependent.
        ``Default = False``
    
    .. attribute:: kernel_language

        Specifies whether to use wrapped Fortran routines ('Fortran')
        or pure Python ('Python').  
        ``Default = 'Fortran'``.

    .. attribute:: num_ghost

        Number of ghost cells.
        ``Default = 3``

    .. attribute:: fwave
    
        Whether to split the flux jump (rather than the jump in Q) into waves; 
        requires that the Riemann solver performs the splitting.  
        ``Default = False``

    .. attribute:: cfl_desired

        Desired CFL number.
        ``Default = 2.45``

    .. attribute:: cfl_max

        Maximum CFL number.
        ``Default = 2.50``

    .. attribute:: dq_src

        Whether a source term is present. If it is present the function that 
        computes its contribution must be provided.
        ``Default = None``

    .. attribute:: call_before_step_each_stage

        Whether to call the method `self.before_step` before each RK stage.
        ``Default = False``

    """
    _sspcoeff = {
       'Euler' :    1.0,
       'SSP33':     1.0,
       'SSP104' :   6.0,
       'SSPMS32' :  0.5,
       'SSPMS43' :  1./3.,
       'RK':        None,
       'LMM':       None
       }

    _cfl_default = {
        'SSP104':   [2.45, 2.5],
        'SSPMS32':  [0.16, 0.2],
        'SSPMS43':  [0.14, 0.16]
        }

    # ========================================================================
    #   Initialization routines
    # ========================================================================
    def __init__(self,riemann_solver=None,claw_package=None):
        r"""
        Set default options for SharpClawSolvers and call the super's __init__().
        """
        self.limiters = [1]
        self.before_step = before_step
        self.lim_type = 2
        self.weno_order = 5
        self.time_integrator = 'SSP104'
        self.char_decomp = 0
        self.tfluct_solver = False
        self.aux_time_dep = False
        self.kernel_language = 'Fortran'
        self.num_ghost = 3
        self.fwave = False
        self.cfl_desired = None
        self.cfl_max = None
        self.dq_src = None
        self.call_before_step_each_stage = False
        self._mthlim = self.limiters
        self._method = None
        self._registers = None

        # Used only if time integrator is 'RK'
        self.a = None
        self.b = None
        self.c = None

        # Used only if time integrator is a multistep method
        self.step_index = 1
        self.alpha = None
        self.beta = None

        # Call general initialization function
        super(SharpClawSolver,self).__init__(riemann_solver,claw_package)
        
    def setup(self,solution):
        """
        Allocate RK stage arrays or previous step solutions and fortran routine work arrays.
        """
        if self.lim_type == 2:
            self.num_ghost = (self.weno_order+1)/2

        # This is a hack to deal with the fact that petsc4py
        # doesn't allow us to change the stencil_width (num_ghost)
        state = solution.state
        state.set_num_ghost(self.num_ghost)
        # End hack

        self._allocate_registers(solution)
        self._set_mthlim()
        try:
            if self.cfl_max is None:
                self.cfl_desired  = self._cfl_default[self.time_integrator][0]
                self.cfl_max  = self._cfl_default[self.time_integrator][1]
            if self.cfl_desired is None:
                self.cfl_desired = 0.9*self.cfl_max
        except KeyError:
            raise KeyError('Maximum CFL number is not provided.')

        state = solution.states[0]
 
        if self.kernel_language=='Fortran':
            if self.fmod is None:
                so_name = 'clawpack.pyclaw.sharpclaw.sharpclaw'+str(self.num_dim)
                self.fmod = __import__(so_name,fromlist=['clawpack.pyclaw.sharpclaw'])
            state.set_cparam(self.fmod)
            state.set_cparam(self.rp)
            self._set_fortran_parameters(state,self.fmod.clawparams,self.fmod.workspace,self.fmod.reconstruct)

        self._allocate_bc_arrays(state)

        super(SharpClawSolver,self).setup(solution)


    def __del__(self):
        r"""
        Deallocate F90 module arrays.
        Also delete Fortran objects, which otherwise tend to persist in Python sessions.
        """
        if self.kernel_language=='Fortran':
            self.fmod.clawparams.dealloc_clawparams()
            self.fmod.workspace.dealloc_workspace(self.char_decomp)
            self.fmod.reconstruct.dealloc_recon_workspace(self.fmod.clawparams.lim_type,self.fmod.clawparams.char_decomp)
            del self.fmod

        super(SharpClawSolver,self).__del__()


    # ========== Time stepping routines ======================================
    def step(self,solution):
        """Evolve q over one time step.

        Take on Runge-Kutta time step or multistep method using the method specified by
        self.time_integrator.  Currently implemented methods:

        'Euler'  : 1st-order Forward Euler integration
        'SSP33'  : 3rd-order strong stability preserving method of Shu & Osher
        'SSP104' : 4th-order strong stability preserving method Ketcheson
        'SSPMS32': 2nd-order strong stability preserving 3-step linear multistep method
        """
        state = solution.states[0]

        self.before_step(self,state)

        try:
            if self.time_integrator=='Euler':
                deltaq=self.dq(state)
                state.q+=deltaq

            elif self.time_integrator=='SSP33':
                deltaq=self.dq(state)
                self._registers[0].q=state.q+deltaq
                self._registers[0].t =state.t+self.dt

                if self.call_before_step_each_stage:
                    self.before_step(self,self._registers[0])
                deltaq=self.dq(self._registers[0])
                self._registers[0].q= 0.75*state.q + 0.25*(self._registers[0].q+deltaq)
                self._registers[0].t = state.t+0.5*self.dt

                if self.call_before_step_each_stage:
                    self.before_step(self,self._registers[0])
                deltaq=self.dq(self._registers[0])
                state.q = 1./3.*state.q + 2./3.*(self._registers[0].q+deltaq)


            elif self.time_integrator=='SSP104':
                state.q = self.ssp104(state)


            elif self.time_integrator=='RK':
                # General RK with specified coefficients
                # self._registers[i].q actually stores dt*f(y_i)
                num_stages = len(self.b)
                for i in range(num_stages):
                    self._registers[i].q = state.q.copy()
                    for j in range(i):
                        self._registers[i].q += self.a[i,j]*self._registers[j].q
                    self._registers[i].t = state.t + self.dt * self.c[i]
                    self._registers[i].q = self.dq(self._registers[i])

                for j in range(num_stages):
                    state.q += self.b[j]*self._registers[j].q


            elif self.time_integrator == 'SSPMS32':
                # Store initial solution
                if self.step_index == 1:
                    for i in range(2):
                        self._registers[-2+i].dt = self.dt
                    self._registers[-1].q = state.q.copy()

                if self.step_index < 3:
                    # Using Euler method for previous step values
                    deltaq = self.dq(state)
                    state.q += deltaq
                    self.step_index += 1
                
                else:
                    omega = (self._registers[-2].dt + self._registers[-1].dt)/self.dt
                    # ssp coefficient
                    r = (omega-1.)/omega
                    # method coefficients 
                    delta = 1./omega**2
                    beta = (omega+1.)/omega
                    deltaq = self.dq(state)
                    state.q = beta*(r*state.q + deltaq) + delta*self._registers[-3].q

                # Update stored solutions
                for i in range(2):
                    self._registers[-3+i].q = self._registers[-2+i].q.copy()
                    self._registers[-3+i].dt = self._registers[-2+i].dt
                self._registers[-1].q = state.q.copy()
                self._registers[-1].dt = self.dt


            elif self.time_integrator == 'SSPMS43':
                # Store initial solution
                if self.step_index == 1:
                    for i in range(3):
                        self._registers[-3+i].dt = self.dt
                    self._registers[-1].q = state.q.copy()

                if self.step_index < 4:
                    # Using SSP22 method for previous step values
                    import copy
                    s1 = copy.deepcopy(state)
                    s1.set_num_ghost(self.num_ghost)

                    deltaq=self.dq(state)
                    s1.q = state.q + deltaq
                    s1.t = state.t + self.dt
                    deltaq = self.dq(s1)
                    state.q = 0.5*(state.q + s1.q + deltaq)

                    self.step_index += 1
                
                else:
                    H = self._registers[-3].dt + self._registers[-2].dt + self._registers[-1].dt
                    omega3 = H/self.dt
                    omega4 = omega3 + 1.
                    # ssp coefficient
                    r = (omega3-2.)/omega3
                    # method coefficients
                    delta0 = (4*omega4 - omega3**2)/omega3**3
                    beta0 = omega4/omega3**2
                    beta3 = omega4**2/omega3**2
                    deltaq = self.dq(state)
                    deltaqm4 = self.dq(self._registers[-4]) 
                    state.q = beta3*(r*state.q + deltaq) + \
                            (r*beta0+delta0)*self._registers[-4].q + beta0*deltaqm4

                # Update stored solutions
                for i in range(3):
                    self._registers[-4+i].q = self._registers[-3+i].q.copy()
                    self._registers[-4+i].dt = self._registers[-3+i].dt
                self._registers[-1].q = state.q.copy()
                self._registers[-1].dt = self.dt


            elif self.time_integrator == 'LMM':
                num_steps = len(self.alpha)

                # Store initial solution
                if self.step_index == 1:
                    self._registers[-num_steps].q  = state.q.copy()
                    self._registers[-num_steps].dq = self.dq(state)

                if self.step_index < num_steps:
                    # Using SSP104 for previous step values
                    state.q = self.ssp104(state)
                    self._registers[-num_steps+self.step_index].q = state.q.copy()
                    self._registers[-num_steps+self.step_index].dq = self.dq(state)
                    self.step_index += 1
                else:
                    # Update solution: alpha[-1] and beta[-1] correspond to solution at the previous step
                    state.q = self.alpha[-1]*self._registers[-1].q + self.beta[-1]*self._registers[-1].dq
                    for i in range(-num_steps,-1):
                        state.q += self.alpha[i]*self._registers[i].q + self.beta[i]*self._registers[i].dq
                        self._registers[i].q = self._registers[i+1].q.copy()
                        self._registers[i].dq = self._registers[i+1].dq.copy()
                    # Store current solution and function evaluation
                    self._registers[-1].q = state.q.copy()
                    self._registers[-1].dq = self.dq(state)


            else:
                raise Exception('Unrecognized time integrator')
        except CFLError:
            return False


    def ssp104(self,state):
        if self.time_integrator == 'SSP104':
            s1=self._registers[0]
            s2=self._registers[1]
            s1.q = state.q.copy()
        elif self.time_integrator == 'LMM':
            import copy
            s1 = copy.deepcopy(state)
            s1.set_num_ghost(self.num_ghost)
            s2 = copy.deepcopy(s1)

        deltaq=self.dq(state)
        s1.q = state.q + deltaq/6.
        s1.t = state.t + self.dt/6.

        for i in xrange(4):
            if self.call_before_step_each_stage:
                self.before_step(self,s1)
            deltaq=self.dq(s1)
            s1.q=s1.q + deltaq/6.
            s1.t =s1.t + self.dt/6.

        s2.q = state.q/25. + 9./25 * s1.q
        s1.q = 15. * s2.q - 5. * s1.q
        s1.t = state.t + self.dt/3.

        for i in xrange(4):
            if self.call_before_step_each_stage:
                self.before_step(self,s1)
            deltaq=self.dq(s1)
            s1.q=s1.q + deltaq/6.
            s1.t =s1.t + self.dt/6.

        if self.call_before_step_each_stage:
            self.before_step(self,s1)
        deltaq = self.dq(s1)
 
        return s2.q + 0.6 * s1.q + 0.1 * deltaq


    def _set_mthlim(self):
        self._mthlim = self.limiters
        if not isinstance(self.limiters,list): self._mthlim=[self._mthlim]
        if len(self._mthlim)==1: self._mthlim = self._mthlim * self.num_waves
        if len(self._mthlim)!=self.num_waves:
            raise Exception('Length of solver.limiters is not equal to 1 or to solver.num_waves')

       
    def dq(self,state):
        """
        Evaluate dq/dt * (delta t)
        """

        deltaq = self.dq_hyperbolic(state)

        # Check here if we violated the CFL condition, if we did, return 
        # immediately to evolve_to_time and let it deal with picking a new
        # dt
        if self.cfl.get_cached_max() > self.cfl_max:
            raise CFLError('cfl_max exceeded')

        if self.dq_src is not None:
            deltaq+=self.dq_src(self,state,self.dt)

        return deltaq

    def dq_hyperbolic(self,state):
        raise NotImplementedError('You must subclass SharpClawSolver.')

         
    def dqdt(self,state):
        """
        Evaluate dq/dt.  This routine is used for implicit time stepping.
        """

        self.dt = 1
        deltaq = self.dq_hyperbolic(state)

        if self.dq_src is not None:
            deltaq+=self.dq_src(self,state,self.dt)

        return deltaq.flatten('f')


    def _set_fortran_parameters(self,state,clawparams,workspace,reconstruct):
        """
        Set parameters for Fortran modules used by SharpClaw.
        The modules should be imported and passed as arguments to this function.

        """
        grid = state.grid
        clawparams.num_dim       = grid.num_dim
        clawparams.lim_type      = self.lim_type
        clawparams.weno_order    = self.weno_order
        clawparams.char_decomp   = self.char_decomp
        clawparams.tfluct_solver = self.tfluct_solver
        clawparams.fwave         = self.fwave
        clawparams.index_capa         = state.index_capa+1

        clawparams.num_waves     = self.num_waves
        clawparams.alloc_clawparams()
        for idim in range(grid.num_dim):
            clawparams.xlower[idim]=grid.dimensions[idim].lower
            clawparams.xupper[idim]=grid.dimensions[idim].upper
        clawparams.dx       =grid.delta
        clawparams.mthlim   =self._mthlim

        maxnx = max(grid.num_cells)+2*self.num_ghost
        workspace.alloc_workspace(maxnx,self.num_ghost,state.num_eqn,self.num_waves,self.char_decomp)
        reconstruct.alloc_recon_workspace(maxnx,self.num_ghost,state.num_eqn,self.num_waves,
                                            clawparams.lim_type,clawparams.char_decomp)

    def _allocate_registers(self,solution):
        r"""
        Instantiate State objects for Runge--Kutta stages and Linear Multistep method steps.

        This routine is only used by method-of-lines solvers (SharpClaw),
        not by the Classic solvers.  It allocates additional State objects
        to store the intermediate stages used by Runge--Kutta and Multistep 
        time integrators.

        If we create a MethodOfLinesSolver subclass, this should be moved there.
        """
        # Generally the number of registers for the starting method should be at most 
        # equal to the number of registers of the LMM
        if self.time_integrator   == 'Euler':   nregisters=0
        elif self.time_integrator == 'SSP33':   nregisters=1
        elif self.time_integrator == 'SSP104':  nregisters=2
        elif self.time_integrator == 'RK':      nregisters=len(self.b)+1
        elif self.time_integrator == 'SSPMS32': nregisters=3
        elif self.time_integrator == 'SSPMS43': nregisters=4
        elif self.time_integrator == 'LMM':
            nregisters=len(self.alpha)
            self.dt_variable = False
        else:
            raise Exception('Unrecognized time intergrator')
        
        state = solution.states[0]
        # use the same class constructor as the solution for the Runge Kutta stages
        State = type(state)
        self._registers = []
        for i in xrange(nregisters):
            #Maybe should use State.copy() here?
            self._registers.append(State(state.patch,state.num_eqn,state.num_aux))
            self._registers[-1].problem_data                = state.problem_data
            self._registers[-1].set_num_ghost(self.num_ghost)
            self._registers[-1].t                           = state.t
            if state.num_aux > 0: self._registers[-1].aux   = state.aux


    def get_cfl_max(self):
        """
        Set maximum CFL number for current step depending on time integrator
        """
        if self.time_integrator[:-2] == 'SSPMS' and self.step_index >= len(self._registers):
            s = len(self._registers)-2
            H = self._registers[-2].dt
            for i in range(s):
                H += self._registers[-3-i].dt
            r = (H - s*self._registers[-1].dt)/H # ssp coefficient at the current step
            sigma = r/self._sspcoeff[self.time_integrator]
        else:
            sigma = 1.0

        return sigma * self.cfl_max

    def get_dt_new(self):
        """
        Set time-step for next step depending on time integrator
        """
        # desired time-step 
        dt_des = self.dt * self.cfl_desired / self.cfl.get_cached_max()

        if self.time_integrator[:-2] == 'SSPMS' and self.step_index >= len(self._registers):
            s = len(self._registers)-2
            H = self._registers[-1].dt
            for i in range(s):
                H += self._registers[-2-i].dt
            sigma = H / (self._sspcoeff[self.time_integrator]*H + s*dt_des)
        else:
            sigma = 1.0

        return sigma * dt_des



# ========================================================================
class SharpClawSolver1D(SharpClawSolver):
# ========================================================================
    """
    SharpClaw solver for one-dimensional problems.
    
    Used to solve 1D hyperbolic systems using the SharpClaw algorithms,
    which are based on WENO reconstruction and Runge-Kutta time stepping.
    """

    __doc__ += add_parent_doc(SharpClawSolver)
    
    def __init__(self,riemann_solver=None,claw_package=None):
        r"""
        See :class:`SharpClawSolver1D` for more info.
        """   
        self.num_dim = 1
        super(SharpClawSolver1D,self).__init__(riemann_solver,claw_package)


    def dq_hyperbolic(self,state):
        r"""
        Compute dq/dt * (delta t) for the hyperbolic hyperbolic system.

        Note that the capa array, if present, should be located in the aux
        variable.

        Indexing works like this (here num_ghost=2 as an example)::

         0     1     2     3     4     mx+num_ghost-2     mx+num_ghost      mx+num_ghost+2
                     |                        mx+num_ghost-1 |  mx+num_ghost+1
         |     |     |     |     |   ...   |     |     |     |     |
            0     1  |  2     3            mx+num_ghost-2    |mx+num_ghost       
                                                  mx+num_ghost-1   mx+num_ghost+1

        The top indices represent the values that are located on the grid
        cell boundaries such as waves, s and other Riemann problem values, 
        the bottom for the cell centered values such as q.  In particular
        the ith grid cell boundary has the following related information::

                          i-1         i         i+1
                           |          |          |
                           |   i-1    |     i    |
                           |          |          |

        Again, grid cell boundary quantities are at the top, cell centered
        values are in the cell.

        """
    
        import numpy as np

        self._apply_q_bcs(state)
        if state.num_aux > 0:
            self._apply_aux_bcs(state)
        q = self.qbc 

        grid = state.grid
        mx = grid.num_cells[0]

        ixy=1

        if self.kernel_language=='Fortran':
            rp1 = self.rp.rp1._cpointer
            dq,cfl=self.fmod.flux1(q,self.auxbc,self.dt,state.t,ixy,mx,self.num_ghost,mx,rp1)

        elif self.kernel_language=='Python':

            dtdx = np.zeros( (mx+2*self.num_ghost) ,order='F')
            dq   = np.zeros( (state.num_eqn,mx+2*self.num_ghost) ,order='F')

            # Find local value for dt/dx
            if state.index_capa>=0:
                dtdx = self.dt / (grid.delta[0] * state.aux[state.index_capa,:])
            else:
                dtdx += self.dt/grid.delta[0]
 
            aux=self.auxbc
            if aux.shape[0]>0:
                aux_l=aux[:,:-1]
                aux_r=aux[:,1: ]
            else:
                aux_l = None
                aux_r = None

            #Reconstruct (wave reconstruction uses a Riemann solve)
            if self.lim_type==-1: #1st-order Godunov
                ql=q; qr=q
            elif self.lim_type==0: #Unlimited reconstruction
                raise NotImplementedError('Unlimited reconstruction not implemented')
            elif self.lim_type==1: #TVD Reconstruction
                raise NotImplementedError('TVD reconstruction not implemented')
            elif self.lim_type==2: #WENO Reconstruction
                if self.char_decomp==0: #No characteristic decomposition
                    ql,qr=recon.weno(5,q)
                elif self.char_decomp==1: #Wave-based reconstruction
                    q_l=q[:,:-1]
                    q_r=q[:,1: ]
                    wave,s,amdq,apdq = self.rp(q_l,q_r,aux_l,aux_r,state.problem_data)
                    ql,qr=recon.weno5_wave(q,wave,s)
                elif self.char_decomp==2: #Characteristic-wise reconstruction
                    raise NotImplementedError

            # Solve Riemann problem at each interface
            q_l=qr[:,:-1]
            q_r=ql[:,1: ]
            wave,s,amdq,apdq = self.rp(q_l,q_r,aux_l,aux_r,state.problem_data)

            # Loop limits for local portion of grid
            # THIS WON'T WORK IN PARALLEL!
            LL = self.num_ghost - 1
            UL = grid.num_cells[0] + self.num_ghost + 1

            # Compute maximum wave speed
            cfl = 0.0
            for mw in xrange(self.num_waves):
                smax1 = np.max( dtdx[LL  :UL]  *s[mw,LL-1:UL-1])
                smax2 = np.max(-dtdx[LL-1:UL-1]*s[mw,LL-1:UL-1])
                cfl = max(cfl,smax1,smax2)

            #Find total fluctuation within each cell
            wave,s,amdq2,apdq2 = self.rp(ql,qr,aux,aux,state.problem_data)

            # Compute dq
            for m in xrange(state.num_eqn):
                dq[m,LL:UL] = -dtdx[LL:UL]*(amdq[m,LL:UL] + apdq[m,LL-1:UL-1] \
                                + apdq2[m,LL:UL] + amdq2[m,LL:UL])

        else: 
            raise Exception('Unrecognized value of solver.kernel_language.')

        self.cfl.update_global_max(cfl)
        return dq[:,self.num_ghost:-self.num_ghost]
    

# ========================================================================
class SharpClawSolver2D(SharpClawSolver):
# ========================================================================
    """ Two Dimensional SharpClawSolver
    """

    __doc__ += add_parent_doc(SharpClawSolver)

    def __init__(self,riemann_solver=None,claw_package=None):
        r"""
        Create 2D SharpClaw solver
        
        See :class:`SharpClawSolver2D` for more info.
        """   
        self.num_dim = 2

        super(SharpClawSolver2D,self).__init__(riemann_solver,claw_package)


    def dq_hyperbolic(self,state):
        """Compute dq/dt * (delta t) for the hyperbolic hyperbolic system

        Note that the capa array, if present, should be located in the aux
        variable.

        Indexing works like this (here num_ghost=2 as an example)::

         0     1     2     3     4     mx+num_ghost-2     mx+num_ghost      mx+num_ghost+2
                     |                        mx+num_ghost-1 |  mx+num_ghost+1
         |     |     |     |     |   ...   |     |     |     |     |
            0     1  |  2     3            mx+num_ghost-2    |mx+num_ghost       
                                                  mx+num_ghost-1   mx+num_ghost+1

        The top indices represent the values that are located on the grid
        cell boundaries such as waves, s and other Riemann problem values, 
        the bottom for the cell centered values such as q.  In particular
        the ith grid cell boundary has the following related information::

                          i-1         i         i+1
                           |          |          |
                           |   i-1    |     i    |
                           |          |          |

        Again, grid cell boundary quantities are at the top, cell centered
        values are in the cell.

        """
        self._apply_q_bcs(state)
        if state.num_aux > 0:    
            self._apply_aux_bcs(state)
        q = self.qbc 

        grid = state.grid

        num_ghost=self.num_ghost
        mx=grid.num_cells[0]
        my=grid.num_cells[1]
        maxm = max(mx,my)

        if self.kernel_language=='Fortran':
            rpn2 = self.rp.rpn2._cpointer
            dq,cfl=self.fmod.flux2(q,self.auxbc,self.dt,state.t,num_ghost,maxm,mx,my,rpn2)

        else: raise Exception('Only Fortran kernels are supported in 2D.')

        self.cfl.update_global_max(cfl)
        return dq[:,num_ghost:-num_ghost,num_ghost:-num_ghost]

# ========================================================================
class SharpClawSolver3D(SharpClawSolver):
# ========================================================================
    """ Three Dimensional SharpClawSolver
    """

    __doc__ += add_parent_doc(SharpClawSolver)

    def __init__(self,riemann_solver=None,claw_package=None):
        r"""
        Create 3D SharpClaw solver
        
        See :class:`SharpClawSolver3D` for more info.
        """   
        self.num_dim = 3

        super(SharpClawSolver3D,self).__init__(riemann_solver,claw_package)


    def teardown(self):
        r"""
        Deallocate F90 module arrays.
        Also delete Fortran objects, which otherwise tend to persist in Python sessions.
        """
        if self.kernel_language=='Fortran':
            self.fmod.workspace.dealloc_workspace(self.char_decomp)
            self.fmod.reconstruct.dealloc_recon_workspace(self.fmod.clawparams.lim_type,self.fmod.clawparams.char_decomp)
            self.fmod.clawparams.dealloc_clawparams()
            del self.fmod


    def dq_hyperbolic(self,state):
        """Compute dq/dt * (delta t) for the hyperbolic hyperbolic system

        Note that the capa array, if present, should be located in the aux
        variable.

        Indexing works like this (here num_ghost=2 as an example)::

         0     1     2     3     4     mx+num_ghost-2     mx+num_ghost      mx+num_ghost+2
                     |                        mx+num_ghost-1 |  mx+num_ghost+1
         |     |     |     |     |   ...   |     |     |     |     |
            0     1  |  2     3            mx+num_ghost-2    |mx+num_ghost       
                                                  mx+num_ghost-1   mx+num_ghost+1

        The top indices represent the values that are located on the grid
        cell boundaries such as waves, s and other Riemann problem values, 
        the bottom for the cell centered values such as q.  In particular
        the ith grid cell boundary has the following related information::

                          i-1         i         i+1
                           |          |          |
                           |   i-1    |     i    |
                           |          |          |

        Again, grid cell boundary quantities are at the top, cell centered
        values are in the cell.

        """
        self._apply_q_bcs(state)
        if state.num_aux > 0:    
            self._apply_aux_bcs(state)
        q = self.qbc 

        grid = state.grid

        num_ghost=self.num_ghost
        mx=grid.num_cells[0]
        my=grid.num_cells[1]
        mz=grid.num_cells[2]
        maxm = max(mx,my,mz)

        if self.kernel_language=='Fortran':
            rpn3 = self.rp.rpn3._cpointer
            dq,cfl=self.fmod.flux3(q,self.auxbc,self.dt,state.t,num_ghost,maxm,mx,my,mz,rpn3)

        else: raise Exception('Only Fortran kernels are supported in 3D.')

        self.cfl.update_global_max(cfl)
        return dq[:,num_ghost:-num_ghost,num_ghost:-num_ghost,num_ghost:-num_ghost]

########NEW FILE########
__FILENAME__ = weno
"""Generate Fortran WENO kernels with PyWENO."""

# Copyright (c) 2011, Matthew Emmett.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import pyweno.symbolic
import pyweno.kernels
import pyweno.functions

import numpy as np

wrapper = pyweno.functions.FunctionGenerator('fortran')

#### set fortran templatese to match clawpack

pyweno.functions.templates['fortran']['callable'] = '''
subroutine {function}(q, ql, qr, num_eqn, maxnx, num_ghost)

  implicit none

  integer,          intent(in)  :: num_eqn, maxnx, num_ghost
  double precision, intent(in)  :: q(num_eqn,maxnx+2*num_ghost)
  double precision, intent(out) :: ql(num_eqn,maxnx+2*num_ghost), qr(num_eqn,maxnx+2*num_ghost)

  integer :: i, m
  double precision :: {variables}

  do i = num_ghost, maxnx+num_ghost+1
    do m = 1, num_eqn
      {kernel}
    end do
  end do

end subroutine
'''
pyweno.kernels.global_names['fortran'] = 'q(m,i{r:+d})'


#### open weno.f90 and write header

out = open('weno.f90', 'w')
out.write('''! This file was generated by: python weno.py
module weno
contains
''')


#### generate and write reconstruction functions

for k in range(3, 10):
# for k in range(3, 5):

  print 'generating reconstruction for k: %02d' % k
  
  # set smoothness
  beta = pyweno.symbolic.jiang_shu_smoothness_coefficients(k)
  wrapper.set_smoothness(beta)

  # reconstructions: -1=left, 1=right
  (varpi, split) = pyweno.symbolic.optimal_weights(k, [ -1, 1 ])
  coeffs = pyweno.symbolic.reconstruction_coefficients(k, [ -1, 1 ])

  wrapper.set_optimal_weights(varpi, split)
  wrapper.set_reconstruction_coefficients(coeffs)

  # tweak reconstructed function (f_star) names to match subroutine
  # definition above
  wrapper.global_f_star[0] = 'ql(m,i)'
  wrapper.global_f_star[1] = 'qr(m,i)'
  
  # write function
  out.write(wrapper.generate(
    function='weno%d' % (2*k-1), normalise=False))


#### done

out.write('''end module weno''')
out.close()

########NEW FILE########
__FILENAME__ = solution
#!/usr/bin/env python
# encoding: utf-8
r"""
Module containing all Pyclaw solution objects
"""

import os
import logging

from .geometry import Patch, Dimension, Domain

# ============================================================================
#  Solution Class
# ============================================================================
class Solution(object):
    r"""
    Pyclaw patch container class
        
    :Input and Output:
    
        Input and output of solution objects is handle via the io package.
        Solution contains the generic methods :meth:`write`, :meth:`read` and
        :meth:`plot` which then figure out the correct method to call.  Please
        see the io package for the particulars of each format and method and 
        the methods in this class for general input and output information.
    
    :Properties:
    
        If there is only one state and patch belonging to this solution, 
        the solution will appear to have many of the attributes assigned to its
        one state and patch.  Some parameters that have in the past been
        parameters for all patch,s are also reachable although Solution does not
        check to see if these parameters are truly universal.

        Patch Attributes:
            'dimensions'
        State Attributes:
            't','num_eqn','q','aux','capa','problem_data'
            
            
    :Initialization:
        
        The initialization of a Solution can happen one of these ways
        
            1. `args` is empty and an empty Solution is created
            2. `args` is an integer (the number of components of q), a single
               State, or a list of States and is followed
               by the appropriate :ref:`geometry <pyclaw_geometry>` object
               which can be one of:
                
                 - (:class:`~pyclaw.geometry.Domain`)
                 - (:class:`~pyclaw.geometry.Patch`) - A domain is created
                   with the patch or list of patches provided.
                 - (:class:`~pyclaw.geometry.Dimension`) - A domain and 
                   patch is created with the dimensions or list of 
                   dimensions provided.
            3. `args` is a variable number of arguments that describes the 
               location of a file to be read in to initialize the object
    
    :Examples:

        >>> import clawpack.pyclaw as pyclaw
        >>> x = pyclaw.Dimension('x',0.,1.,100)
        >>> domain = pyclaw.Domain((x))
        >>> state = pyclaw.State(domain,3,2)
        >>> solution = pyclaw.Solution(state,domain)
    """
    def __getattr__(self, key):
        if key in ('t','num_eqn','mp','mF','q','p','F','aux','capa',
                   'problem_data','num_aux',
                   'num_dim', 'p_centers', 'p_edges', 'c_centers', 'c_edges',
                   'num_cells', 'lower', 'upper', 'delta', 'centers', 'edges',
                   'gauges', 'num_eqn', 'num_aux', 'grid', 'problem_data'):
            return self._get_base_state_attribute(key)
        else:
            raise AttributeError("'Solution' object has no attribute '"+key+"'")

    def __setattr__(self, key, value):
        if key in ('t','mp','mF'):
            self.set_all_states(key,value)
        else:
            self.__dict__[key] = value

    # ========== Attributes ==================================================
    
    # ========== Properties ==================================================
    @property
    def state(self):
        r"""(:class:`State`) - Base state is returned"""
        return self.states[0]
    @property
    def patch(self):
        r"""(:class:`Patch`) - Base state's patch is returned"""
        return self.domain.patch

    @property
    def start_frame(self):
        r"""(int) - : Solution start frame number in case the `Solution`
        object is initialized by loading frame from file"""
        return self._start_frame
    _start_frame = 0
       

    # ========== Class Methods ===============================================
    def __init__(self,*arg,**kargs):
        r"""Solution Initiatlization Routine
        
        See :class:`Solution` for more info.
        """

        # select package to build solver objects from, by default this will be
        # the package that contains the module implementing the derived class
        # for example, if Solution is implemented in 'clawpack.petclaw.solution', then 
        # the computed claw_package will be 'clawpack.petclaw'

        import sys
        if 'claw_package' in kargs.keys():
            claw_package = kargs['claw_package']
        else:
            claw_package = None

        if claw_package is not None and claw_package in sys.modules:
            self.claw_package = sys.modules[claw_package]
        else:
            def get_clawpack_dot_xxx(modname): return modname.rpartition('.')[0]
            claw_package_name = get_clawpack_dot_xxx(self.__module__)
            if claw_package_name in sys.modules:
                self.claw_package = sys.modules[claw_package_name]
            else:
                raise NotImplementedError("Unable to determine solver package, please provide one")

        State = self.claw_package.State

        self.states = []
        self.domain = None
        if len(arg) == 1:
            # Load frame
            frame = arg[0]
            if not isinstance(frame,int):
                raise Exception('Invalid pyclaw.Solution object initialization')
            if 'count_from_zero' in kargs.keys() and\
              kargs['count_from_zero'] == True:
                self._start_frame = 0
            else:
                self._start_frame = frame
            try:
                kargs.pop('count_from_zero')
            except KeyError:
                pass

            self.read(frame,**kargs)
        elif len(arg) == 2:
            #Set domain
            if isinstance(arg[1],Domain):
                self.domain = arg[1]
            else:
                if not isinstance(arg[1],(list,tuple)):
                    arg[1] = list(arg[1])
                if isinstance(arg[1][0],Dimension):
                    self.domain = Domain(Patch(arg[1]))
                elif isinstance(arg[1][0],Patch):
                    self.domain = Domain(arg[1])
                else:
                    raise Exception("Invalid argument list")

            #Set state
            if isinstance(arg[0],State):
                # Single State
                self.states.append(arg[0])
            elif isinstance(arg[0],(list,tuple)):
                if isinstance(arg[0][0],State):
                    # List of States
                    self.states = arg[0]
                elif isinstance(arg[0][0],int):
                    self.states = State(self.domain,arg[0][0],arg[0][1])
                else:
                    raise Exception("Invalid argument list")
            elif isinstance(arg[0],int):
                self.states.append(State(self.domain,arg[0]))
            if self.states == [] or self.domain is None:
                raise Exception("Invalid argument list")
                
                
    def is_valid(self):
        r"""
        Checks to see if this solution is valid
        
        The Solution checks to make sure it is valid by checking each of its
        states.  If an invalid state is found, a message is logged what
        specifically made this solution invalid.
       
        :Output:
         - (bool) - True if valid, false otherwise
        """
        return all([state.is_valid() for state in self.states])


    def __str__(self):
        output = "states:\n"
        # This is information about each of the states
        for state in self.states:
            output = output + str(state)
        return str(output)
    
    
    def set_all_states(self,attr,value,overwrite=True):
        r"""
        Sets all member states attribute 'attr' to value
        
        :Input:
         - *attr* - (string) Attribute name to be set
         - *value* - (id) Value for attribute
         - *overwrite* - (bool) Whether to overwrite the attribute if it 
           already exists.  ``default = True``
        """
        for state in self.states:
            if getattr(state,attr) is None or overwrite:
                setattr(state,attr,value) 
    
                    
    def _get_base_state_attribute(self, name):
        r"""
        Return base state attribute
        
        :Output:
         - (id) - Value of attribute from ``states[0]``
        """
        return getattr(self.states[0],name)
    
    
    def __copy__(self):
        return self.__class__(self)
    
    
    def __deepcopy__(self,memo={}):
        import copy
        # Create basic container
        result = self.__class__()
        result.__init__()
        
        # Populate the states
        for state in self.states:
            result.states.append(copy.deepcopy(state))
        result.domain = copy.deepcopy(self.domain)
        
        return result
    
    
    # ========== IO Functions ================================================
    def write(self,frame,path='./',file_format='ascii',file_prefix=None,
                write_aux=False,options={},write_p=False):
        r"""
        Write out a representation of the solution

        Writes out a suitable representation of this solution object based on
        the format requested.  The path is built from the optional path and
        file_prefix arguments.  Will raise an IOError if unsuccessful.

        :Input:
         - *frame* - (int) Frame number to append to the file output
         - *path* - (string) Root path, will try and create the path if it 
           does not already exist. ``default = './'``
         - *format* - (string or list of strings) a string or list of strings 
           containing the desired output formats. ``default = 'ascii'``
         - *file_prefix* - (string) Prefix for the file name.  Defaults to
           the particular io modules default.
         - *write_aux* - (book) Write the auxillary array out as well if 
           present. ``default = False``
         - *options* - (dict) Dictionary of optional arguments dependent on 
           which format is being used. ``default = {}``
        """
        # Determine if we need to create the path
        path = os.path.expandvars(os.path.expanduser(path))
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError:
                print "directory already exists, ignoring"  

        # Call the correct write function based on the output format
        if isinstance(file_format,str):
            format_list = [file_format]
        elif isinstance(file_format,list):
            format_list = file_format


        # Loop over list of formats requested
        for form in format_list:
            if 'petsc' in form:
                from clawpack.petclaw import io
                write_func = io.petsc.write
            else:
                from clawpack.pyclaw import io
                write_func = getattr(getattr(io,form),'write')


            if file_prefix is None:
                write_func(self,frame,path,write_aux=write_aux,
                            options=options,write_p=write_p)
            else:
                write_func(self,frame,path,file_prefix=file_prefix,
                                write_aux=write_aux,options=options,
                           write_p=write_p)
            msg = "Wrote out solution in format %s for time t=%s" % (form,self.t)
            logging.getLogger('pyclaw.io').info(msg)

        
    def read(self,frame,path='./_output',file_format='ascii',file_prefix=None,
                read_aux=True,options={}, **kargs):
        r"""
        Reads in a Solution object from a file
        
        Reads in and initializes this Solution with the data specified.  This 
        function will raise an IOError if it was unsuccessful.  

        Any format must conform to the following call signiture and return
        True if the file has been successfully read into the given solution or
        False otherwise.  Options is a dictionary of parameters that each
        format can specify.  See the ascii module for an example.::
        
            read_<format>(solution,path,frame,file_prefix,options={})
            
        ``<format>`` is the name of the format in question.
        
        :Input:
         - *frame* - (int) Frame number to be read in
         - *path* - (string) Base path to the files to be read. 
           ``default = './'``
         - *file_format* - (string) Format of the file, should match on of the 
           modules inside of the io package.  ``default = 'ascii'``
         - *file_prefix* - (string) Name prefix in front of all the files, 
           defaults to whatever the format defaults to, e.g. fort for ascii
         - *options* - (dict) Dictionary of optional arguments dependent on 
           the format being read in.  ``default = {}``
            
        :Output:
         - (bool) - True if read was successful, False otherwise
        """
        
        if file_format=='petsc':
            from clawpack.petclaw import io
            read_func = io.petsc.read
        elif file_format == 'binary':
            from clawpack.pyclaw import io 
            read_func = io.binary.read
        elif file_format=='ascii': 
            from clawpack.pyclaw import io
            read_func = io.ascii.read

        path = os.path.expandvars(os.path.expanduser(path))
        if file_prefix is None:
            read_func(self,frame,path,read_aux=read_aux,options=options)
        else:
            read_func(self,frame,path,file_prefix=file_prefix,
                                    read_aux=read_aux,options=options)
        logging.getLogger('pyclaw.io').info("Read in solution for time t=%s" % self.t)
        
        
    def plot(self):
        r"""
        Plot the solution
        """
        raise NotImplementedError("Direct solution plotting has not been " +
            "implemented as of yet, please refer to the plotting module for" +
            " how to plot solutions.")

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = solver
r"""
Module specifying the interface to every solver in PyClaw.
"""
import logging
import numpy as np

class CFLError(Exception):
    """Error raised when cfl_max is exceeded.  Is this a
       reasonable mechanism for handling that?"""
    def __init__(self,msg):
        super(CFLError,self).__init__(msg)

class BC():
    """Enumeration of boundary condition names."""
    # This could instead just be implemented as a static dictionary.
    custom     = 0
    extrap    = 1
    periodic   = 2
    wall = 3

#################### Dummy routines ######################
def default_compute_gauge_values(q,aux):
    r"""By default, record values of q at gauges.
    """
    return q

class Solver(object):
    r"""
    Pyclaw solver superclass.

    The pyclaw.Solver.solver class is an abstract class that should
    not be instantiated; rather, all Solver classes should inherit from it.

    Solver initialization takes one argument -- a Riemann solver:

        >>> from clawpack import pyclaw, riemann
        >>> solver = pyclaw.ClawSolver2D(riemann.rp2_euler_4wave)

    After which solver options may be set.
    It is necessary to set the boundary conditions (for q, and
    for aux if an aux array is used):

        >>> solver.bc_lower[0] = pyclaw.BC.extrap
        >>> solver.bc_upper[0] = pyclaw.BC.wall
    
    Many other options may be set
    for specific solvers; for instance the limiter to be used, whether to
    use a dimensionally-split algorithm, and so forth.

    Usually the solver is attached to a controller before being used::

        >>> claw = pyclaw.Controller()
        >>> claw.solver = solver

    .. attribute:: dt
        
        Current time step, ``default = 0.1``
        
    .. attribute:: cfl
        
        Current Courant-Freidrichs-Lewy number, ``default = 1.0``
    
    .. attribute:: status
        
        Dictionary of status values for the solver with the following keys:
         - ``cflmax`` = Maximum CFL number
         - ``dtmin`` = Minimum time step taken
         - ``dtmax`` = Maximum time step taken
         - ``numsteps`` = Total number of time steps that have been taken

        solver.status is returned by solver.evolve_to_time.
    
    .. attribute:: dt_variable
    
        Whether to allow the time step to vary, ``default = True``.
        If false, the initial time step size is used for all steps.
        
    .. attribute:: max_steps
    
        The maximum number of time steps allowd to reach the end time 
        requested, ``default = 10000``.  If exceeded, an exception is
        raised.
    
    .. attribute:: logger
    
        Default logger for all solvers.  Records information about the run
        and debugging messages (if requested).

    .. attribute:: bc_lower 
    
        (list of ints) Lower boundary condition types, listed in the
        same order as the Dimensions of the Patch.  See Solver.BC for
        an enumeration.

    .. attribute:: bc_upper 
    
        (list of ints) Upper boundary condition types, listed in the
        same order as the Dimensions of the Patch.  See Solver.BC for
        an enumeration.

    .. attribute:: user_bc_lower 
        
        (func) User defined lower boundary condition.
        Fills the values of qbc with the correct boundary values.
        The appropriate signature is:

        def user_bc_lower(patch,dim,t,qbc,num_ghost):

    .. attribute:: user_bc_upper 
    
        (func) User defined upper boundary condition.
        Fills the values of qbc with the correct boundary values.
        The appropriate signature is:

        def user_bc_upper(patch,dim,t,qbc,num_ghost):
 
        
    :Initialization:
    
    Output:
     - (:class:`Solver`) - Initialized Solver object
    """

            
    def __setattr__(self, key, value):
        if not hasattr(self, '_isinitialized'):
            self.__dict__['_isinitialized'] = False
        if self._isinitialized and not hasattr(self, key):
            raise TypeError("%s has no attribute %s" % (self.__class__,key))
        object.__setattr__(self,key,value)

    @property
    def all_bcs(self):
        return self.bc_lower, self.bc_upper
    @all_bcs.setter
    def all_bcs(self,all_bcs):
        for i in range(self.num_dim):
            self.bc_lower[i] = all_bcs
            self.bc_upper[i] = all_bcs


    #  ======================================================================
    #   Initialization routines
    #  ======================================================================
    def __init__(self,riemann_solver=None,claw_package=None):
        r"""
        Initialize a Solver object
        
        See :class:`Solver` for full documentation
        """ 
        # Setup solve logger
        self.logger = logging.getLogger('pyclaw.solver')

        self.dt_initial = 0.1
        self.dt_max = 1e99
        self.max_steps = 10000
        self.dt_variable = True
        self.num_waves = None #Must be set later to agree with Riemann solver
        self.qbc = None
        self.auxbc = None
        self.rp = None
        self.fmod = None
        self._is_set_up = False

        # select package to build solver objects from, by default this will be
        # the package that contains the module implementing the derived class
        # for example, if ClawSolver1D is implemented in 'clawpack.petclaw.solver', then 
        # the computed claw_package will be 'clawpack.petclaw'
        
        import sys
        if claw_package is not None and claw_package in sys.modules:
            self.claw_package = sys.modules[claw_package]
        else:
            def get_clawpack_dot_xxx(modname): return modname.rpartition('.')[0].rpartition('.')[0]
            claw_package_name = get_clawpack_dot_xxx(self.__module__)
            if claw_package_name in sys.modules:
                self.claw_package = sys.modules[claw_package_name]
            else:
                raise NotImplementedError("Unable to determine solver package, please provide one")

        # Initialize time stepper values
        self.dt = self.dt_initial
        self.cfl = self.claw_package.CFL(self.cfl_desired)
       
        # Status Dictionary
        self.status = {'cflmax': -np.inf,
                       'dtmin': np.inf,
                       'dtmax': -np.inf,
                       'numsteps': 0 }
        
        # No default BCs; user must set them
        self.bc_lower =    [None]*self.num_dim
        self.bc_upper =    [None]*self.num_dim
        self.aux_bc_lower = [None]*self.num_dim
        self.aux_bc_upper = [None]*self.num_dim
        
        self.user_bc_lower = None
        self.user_bc_upper = None

        self.user_aux_bc_lower = None
        self.user_aux_bc_upper = None

        self.num_eqn   = None
        self.num_waves = None

        self.compute_gauge_values = default_compute_gauge_values
        r"""(function) - Function that computes quantities to be recorded at gauges"""

        self.qbc          = None
        r""" Array to hold ghost cell values.  This is the one that gets passed
        to the Fortran code.  """

        if riemann_solver is not None:
            self.rp = riemann_solver
            rp_name = riemann_solver.__name__.split('.')[-1]
            from clawpack import riemann
            self.num_eqn   = riemann.static.num_eqn.get(rp_name,None)
            self.num_waves = riemann.static.num_waves.get(rp_name,None)

        self._isinitialized = True

        super(Solver,self).__init__()


    # ========================================================================
    #  Solver setup and validation routines
    # ========================================================================
    def is_valid(self):
        r"""
        Checks that all required solver attributes are set.
        
        Checks to make sure that all the required attributes for the solver 
        have been set correctly.  All required attributes that need to be set 
        are contained in the attributes list of the class.
        
        Will post debug level logging message of which required attributes 
        have not been set.
        
        :Output:
         - *valid* - (bool) True if the solver is valid, False otherwise
        
        """
        valid = True
        reason = None
        if any([bcmeth == BC.custom for bcmeth in self.bc_lower]):
            if self.user_bc_lower is None:
                valid = False
                reason = 'Lower custom BC function has not been set.'
        if any([bcmeth == BC.custom for bcmeth in self.bc_upper]):
            if self.user_bc_upper is None:
                valid = False
                reason = 'Upper custom BC function has not been set.'
        if self.num_waves is None:
            valid = False
            reason = 'solver.num_waves has not been set.'
        if self.num_eqn is None:
            valid = False
            reason = 'solver.num_eqn has not been set.'
        if (None in self.bc_lower) or (None in self.bc_upper):
            valid = False
            reason = 'One of the boundary conditions has not been set.'

        if reason is not None:
            self.logger.debug(reason)
        return valid, reason
        
    def setup(self,solution):
        r"""
        Stub for solver setup routines.
        
        This function is called before a set of time steps are taken in order 
        to reach tend.  A subclass should extend or override it if it needs to 
        perform some setup based on attributes that would be set after the 
        initialization routine.  Typically this is initialization that
        requires knowledge of the solution object.
        """

        self._is_set_up = True

    def __del__(self):
        r"""
        Stub for solver teardown routines.
        
        This function is called at the end of a simulation.
        A subclass should override it only if it needs to 
        perform some cleanup, such as deallocating arrays in a Fortran module.
        """
        self._is_set_up = False



    def __str__(self):
        output = "Solver Status:\n"
        for (k,v) in self.status.iteritems():
            output = "\n".join((output,"%s = %s" % (k.rjust(25),v)))
        return output


    # ========================================================================
    #  Boundary Conditions
    # ========================================================================    
    def _allocate_bc_arrays(self,state):
        r"""
        Create numpy arrays for q and aux with ghost cells attached.
        These arrays are referred to throughout the code as qbc and auxbc.

        This is typically called by solver.setup().
        """
        qbc_dim = [n+2*self.num_ghost for n in state.grid.num_cells]
        qbc_dim.insert(0,state.num_eqn)
        self.qbc = np.zeros(qbc_dim,order='F')

        auxbc_dim = [n+2*self.num_ghost for n in state.grid.num_cells]
        auxbc_dim.insert(0,state.num_aux)
        self.auxbc = np.empty(auxbc_dim,order='F')
        if state.num_aux>0:
            self._apply_aux_bcs(state)

    def _apply_q_bcs(self,state):
        r"""
        Fills in solver.qbc (the local vector), including ghost cell values.
    
        This function returns an array of dimension determined by the 
        :attr:`num_ghost` attribute.  The type of boundary condition set is 
        determined by :attr:`bc_lower` and :attr:`bc_upper` for the 
        approprate dimension.  Valid values for :attr:`bc_lower` and 
        :attr:`bc_upper` include:
        
        - 'custom'     or 0: A user defined boundary condition will be used, the appropriate 
            Dimension method user_bc_lower or user_bc_upper will be called.
        - 'extrap'    or 1: Zero-order extrapolation.
        - 'periodic'   or 2: Periodic boundary conditions.
        - 'wall' or 3: Wall boundary conditions. It is assumed that the second 
            component of q represents velocity or momentum.
    
        :Input:
         -  *grid* - (:class:`Patch`) The grid being operated on.
         -  *state* - The state being operated on; this may or may not be the
                      same as *grid*.  Generally it is the same as *grid* for
                      the classic algorithms and other one-level algorithms, 
                      but different for method-of-lines algorithms like SharpClaw.

        :Output:
         - (ndarray(num_eqn,...)) q array with boundary ghost cells added and set
         

        .. note:: 

            Note that for user-defined boundary conditions, the array sent to
            the boundary condition has not been rolled. 
        """
        
        import numpy as np
        
        self.qbc = state.get_qbc_from_q(self.num_ghost,self.qbc)
        grid = state.grid
       
        for idim,dim in enumerate(grid.dimensions):
            # First check if we are actually on the boundary
            # (in case of a parallel run)
            if state.grid.on_lower_boundary[idim]:
                # If a user defined boundary condition is being used, send it on,
                # otherwise roll the axis to front position and operate on it
                if self.bc_lower[idim] == BC.custom:
                    self._qbc_lower(state,dim,state.t,self.qbc,idim)
                elif self.bc_lower[idim] == BC.periodic:
                    if state.grid.on_upper_boundary[idim]:
                        # This process owns the whole domain
                        self._qbc_lower(state,dim,state.t,np.rollaxis(self.qbc,idim+1,1),idim)
                    else:
                        pass #Handled automatically by PETSc
                else:
                    self._qbc_lower(state,dim,state.t,np.rollaxis(self.qbc,idim+1,1),idim)

            if state.grid.on_upper_boundary[idim]:
                if self.bc_upper[idim] == BC.custom:
                    self._qbc_upper(state,dim,state.t,self.qbc,idim)
                elif self.bc_upper[idim] == BC.periodic:
                    if state.grid.on_lower_boundary[idim]: 
                        # This process owns the whole domain
                        self._qbc_upper(state,dim,state.t,np.rollaxis(self.qbc,idim+1,1),idim)
                    else:
                        pass #Handled automatically by PETSc
                else:
                    self._qbc_upper(state,dim,state.t,np.rollaxis(self.qbc,idim+1,1),idim)


    def _qbc_lower(self,state,dim,t,qbc,idim):
        r"""
        Apply lower boundary conditions to qbc
        
        Sets the lower coordinate's ghost cells of *qbc* depending on what 
        :attr:`bc_lower` is.  If :attr:`bc_lower` = 0 then the user 
        boundary condition specified by :attr:`user_bc_lower` is used.  Note 
        that in this case the function :attr:`user_bc_lower` belongs only to 
        this dimension but :attr:`user_bc_lower` could set all user boundary 
        conditions at once with the appropriate calling sequence.
        
        :Input:
         - *patch* - (:class:`Patch`) Patch that the dimension belongs to
         
        :Input/Ouput:
         - *qbc* - (ndarray(...,num_eqn)) Array with added ghost cells which will
           be set in this routines
        """
        if self.bc_lower[idim] == BC.custom: 
            self.user_bc_lower(state,dim,t,qbc,self.num_ghost)
        elif self.bc_lower[idim] == BC.extrap:
            for i in xrange(self.num_ghost):
                qbc[:,i,...] = qbc[:,self.num_ghost,...]
        elif self.bc_lower[idim] == BC.periodic:
            # This process owns the whole patch
            qbc[:,:self.num_ghost,...] = qbc[:,-2*self.num_ghost:-self.num_ghost,...]
        elif self.bc_lower[idim] == BC.wall:
            for i in xrange(self.num_ghost):
                qbc[:,i,...] = qbc[:,2*self.num_ghost-1-i,...]
                qbc[idim+1,i,...] = -qbc[idim+1,2*self.num_ghost-1-i,...] # Negate normal velocity
        else:
            raise NotImplementedError("Boundary condition %s not implemented" % self.bc_lower)


    def _qbc_upper(self,state,dim,t,qbc,idim):
        r"""
        Apply upper boundary conditions to qbc
        
        Sets the upper coordinate's ghost cells of *qbc* depending on what 
        :attr:`bc_upper` is.  If :attr:`bc_upper` = 0 then the user 
        boundary condition specified by :attr:`user_bc_upper` is used.  Note 
        that in this case the function :attr:`user_bc_upper` belongs only to 
        this dimension but :attr:`user_bc_upper` could set all user boundary 
        conditions at once with the appropriate calling sequence.
        
        :Input:
         - *patch* - (:class:`Patch`) Patch that the dimension belongs to
         
        :Input/Ouput:
         - *qbc* - (ndarray(...,num_eqn)) Array with added ghost cells which will
           be set in this routines
        """
 
        if self.bc_upper[idim] == BC.custom:
            self.user_bc_upper(state,dim,t,qbc,self.num_ghost)
        elif self.bc_upper[idim] == BC.extrap:
            for i in xrange(self.num_ghost):
                qbc[:,-i-1,...] = qbc[:,-self.num_ghost-1,...] 
        elif self.bc_upper[idim] == BC.periodic:
            # This process owns the whole patch
            qbc[:,-self.num_ghost:,...] = qbc[:,self.num_ghost:2*self.num_ghost,...]
        elif self.bc_upper[idim] == BC.wall:
            for i in xrange(self.num_ghost):
                qbc[:,-i-1,...] = qbc[:,-2*self.num_ghost+i,...]
                qbc[idim+1,-i-1,...] = -qbc[idim+1,-2*self.num_ghost+i,...] # Negate normal velocity
        else:
            raise NotImplementedError("Boundary condition %s not implemented" % self.bc_lower)



    def _apply_aux_bcs(self,state):
        r"""
        Appends boundary cells to aux and fills them with appropriate values.
    
        This function returns an array of dimension determined by the 
        :attr:`num_ghost` attribute.  The type of boundary condition set is 
        determined by :attr:`aux_bc_lower` and :attr:`aux_bc_upper` for the 
        approprate dimension.  Valid values for :attr:`aux_bc_lower` and 
        :attr:`aux_bc_upper` include:
        
        - 'custom'     or 0: A user defined boundary condition will be used, the appropriate 
            Dimension method user_aux_bc_lower or user_aux_bc_upper will be called.
        - 'extrap'    or 1: Zero-order extrapolation.
        - 'periodic'   or 2: Periodic boundary conditions.
        - 'wall' or 3: Wall boundary conditions. It is assumed that the second 
            component of q represents velocity or momentum.
    
        :Input:
         -  *patch* - (:class:`Patch`) The patch being operated on.
         -  *state* - The state being operated on; this may or may not be the
                      same as *patch*.  Generally it is the same as *patch* for
                      the classic algorithms and other one-level algorithms, 
                      but different for method-of-lines algorithms like SharpClaw.

        :Output:
         - (ndarray(num_aux,...)) q array with boundary ghost cells added and set
         

        .. note:: 

            Note that for user-defined boundary conditions, the array sent to
            the boundary condition has not been rolled. 
        """
        
        import numpy as np

        self.auxbc = state.get_auxbc_from_aux(self.num_ghost,self.auxbc)

        patch = state.patch
       
        for idim,dim in enumerate(patch.dimensions):
            # First check if we are actually on the boundary
            # (in case of a parallel run)
            if state.grid.on_lower_boundary[idim]:
                # If a user defined boundary condition is being used, send it on,
                # otherwise roll the axis to front position and operate on it
                if self.aux_bc_lower[idim] == BC.custom:
                    self._auxbc_lower(state,dim,state.t,self.auxbc,idim)
                elif self.aux_bc_lower[idim] == BC.periodic:
                    if state.grid.on_upper_boundary[idim]:
                        # This process owns the whole patch
                        self._auxbc_lower(state,dim,state.t,np.rollaxis(self.auxbc,idim+1,1),idim)
                    else:
                        pass #Handled automatically by PETSc
                else:
                    self._auxbc_lower(state,dim,state.t,np.rollaxis(self.auxbc,idim+1,1),idim)

            if state.grid.on_upper_boundary[idim]:
                if self.aux_bc_upper[idim] == BC.custom:
                    self._auxbc_upper(state,dim,state.t,self.auxbc,idim)
                elif self.aux_bc_upper[idim] == BC.periodic:
                    if state.grid.on_lower_boundary[idim]:
                        # This process owns the whole patch
                        self._auxbc_upper(state,dim,state.t,np.rollaxis(self.auxbc,idim+1,1),idim)
                    else:
                        pass #Handled automatically by PETSc
                else:
                    self._auxbc_upper(state,dim,state.t,np.rollaxis(self.auxbc,idim+1,1),idim)


    def _auxbc_lower(self,state,dim,t,auxbc,idim):
        r"""
        Apply lower boundary conditions to auxbc
        
        Sets the lower coordinate's ghost cells of *auxbc* depending on what 
        :attr:`aux_bc_lower` is.  If :attr:`aux_bc_lower` = 0 then the user 
        boundary condition specified by :attr:`user_aux_bc_lower` is used.  Note 
        that in this case the function :attr:`user_aux_bc_lower` belongs only to 
        this dimension but :attr:`user_aux_bc_lower` could set all user boundary 
        conditions at once with the appropriate calling sequence.
        
        :Input:
         - *patch* - (:class:`Patch`) Patch that the dimension belongs to
         
        :Input/Ouput:
         - *auxbc* - (ndarray(num_aux,...)) Array with added ghost cells which will
           be set in this routines
        """
        if self.aux_bc_lower[idim] == BC.custom: 
            self.user_aux_bc_lower(state,dim,t,auxbc,self.num_ghost)
        elif self.aux_bc_lower[idim] == BC.extrap:
            for i in xrange(self.num_ghost):
                auxbc[:,i,...] = auxbc[:,self.num_ghost,...]
        elif self.aux_bc_lower[idim] == BC.periodic:
            # This process owns the whole patch
            auxbc[:,:self.num_ghost,...] = auxbc[:,-2*self.num_ghost:-self.num_ghost,...]
        elif self.aux_bc_lower[idim] == BC.wall:
            for i in xrange(self.num_ghost):
                auxbc[:,i,...] = auxbc[:,2*self.num_ghost-1-i,...]
        elif self.aux_bc_lower[idim] is None:
            raise Exception("One or more of the aux boundary conditions aux_bc_upper has not been specified.")
        else:
            raise NotImplementedError("Boundary condition %s not implemented" % self.aux_bc_lower)


    def _auxbc_upper(self,state,dim,t,auxbc,idim):
        r"""
        Apply upper boundary conditions to auxbc
        
        Sets the upper coordinate's ghost cells of *auxbc* depending on what 
        :attr:`aux_bc_upper` is.  If :attr:`aux_bc_upper` = 0 then the user 
        boundary condition specified by :attr:`user_aux_bc_upper` is used.  Note 
        that in this case the function :attr:`user_aux_bc_upper` belongs only to 
        this dimension but :attr:`user_aux_bc_upper` could set all user boundary 
        conditions at once with the appropriate calling sequence.
        
        :Input:
         - *patch* - (:class:`Patch`) Patch that the dimension belongs to
         
        :Input/Ouput:
         - *auxbc* - (ndarray(num_aux,...)) Array with added ghost cells which will
           be set in this routines
        """
 
        if self.aux_bc_upper[idim] == BC.custom:
            self.user_aux_bc_upper(state,dim,t,auxbc,self.num_ghost)
        elif self.aux_bc_upper[idim] == BC.extrap:
            for i in xrange(self.num_ghost):
                auxbc[:,-i-1,...] = auxbc[:,-self.num_ghost-1,...] 
        elif self.aux_bc_upper[idim] == BC.periodic:
            # This process owns the whole patch
            auxbc[:,-self.num_ghost:,...] = auxbc[:,self.num_ghost:2*self.num_ghost,...]
        elif self.aux_bc_upper[idim] == BC.wall:
            for i in xrange(self.num_ghost):
                auxbc[:,-i-1,...] = auxbc[:,-2*self.num_ghost+i,...]
        elif self.aux_bc_lower[idim] is None:
            raise Exception("One or more of the aux boundary conditions aux_bc_lower has not been specified.")
        else:
            raise NotImplementedError("Boundary condition %s not implemented" % self.aux_bc_lower)


    # ========================================================================
    #  Evolution routines
    # ========================================================================
    def get_cfl_max(self):
        return self.cfl_max

    def get_dt_new(self):
        cfl = self.cfl.get_cached_max()
        return min(self.dt_max,self.dt * self.cfl_desired / cfl)

    def evolve_to_time(self,solution,tend=None):
        r"""
        Evolve solution from solution.t to tend.  If tend is not specified,
        take a single step.
        
        This method contains the machinery to evolve the solution object in
        ``solution`` to the requested end time tend if given, or one 
        step if not.          

        :Input:
         - *solution* - (:class:`Solution`) Solution to be evolved
         - *tend* - (float) The end time to evolve to, if not provided then 
           the method will take a single time step.
            
        :Output:
         - (dict) - Returns the status dictionary of the solver
        """

        if not self._is_set_up:
            self.setup(solution)
        
        if tend == None:
            take_one_step = True
        else:
            take_one_step = False
            
        # Parameters for time-stepping
        tstart = solution.t

        # Reset status dictionary
        num_steps = 0

        # Setup for the run
        if not self.dt_variable:
            if take_one_step:
                self.max_steps = 1
            else:
                self.max_steps = int((tend - tstart + 1e-10) / self.dt)
                if abs(self.max_steps*self.dt - (tend - tstart)) > 1e-5 * (tend-tstart):
                    raise Exception('dt does not divide (tend-tstart) and dt is fixed!')
        if self.dt_variable == 1 and self.cfl_desired > self.cfl_max:
            raise Exception('Variable time-stepping and desired CFL > maximum CFL')
        if tend <= tstart and not take_one_step:
            self.logger.info("Already at or beyond end time: no evolution required.")
            self.max_steps = 0
                
        # Main time-stepping loop
        for n in xrange(self.max_steps):
            
            state = solution.state
            
            # Adjust dt so that we hit tend exactly if we are near tend
            if not take_one_step:
                if solution.t + self.dt > tend and tstart < tend:
                    self.dt = tend - solution.t
                if tend - solution.t - self.dt < 1.e-14*solution.t:
                    self.dt = tend - solution.t

            # Keep a backup in case we need to retake a time step
            if self.dt_variable:
                q_backup = state.q.copy('F')
                told = solution.t
            
            self.step(solution)

            # Check to make sure that the Courant number was not too large
            cfl = self.cfl.get_cached_max()
            cfl_max = self.get_cfl_max()
            if cfl <= cfl_max:
                # Accept this step
                self.status['cflmax'] = max(cfl, self.status['cflmax'])
                if self.dt_variable==True:
                    solution.t += self.dt 
                else:
                    #Avoid roundoff error if dt_variable=False:
                    solution.t = tstart+(n+1)*self.dt

                # Verbose messaging
                self.logger.debug("Step %i  CFL = %f   dt = %f   t = %f"
                    % (n,cfl,self.dt,solution.t))
                    
                self.write_gauge_values(solution)
                # Increment number of time steps completed
                num_steps += 1
                self.status['numsteps'] += 1
            else:
                # Reject this step
                self.logger.debug("Rejecting time step, CFL number too large")
                if self.dt_variable:
                    state.q = q_backup
                    solution.t = told
                else:
                    # Give up, we cannot adapt, abort
                    self.status['cflmax'] = \
                        max(cfl, self.status['cflmax'])
                    raise Exception('CFL too large, giving up!')
                    
            # Choose new time step
            if self.dt_variable:
                if cfl > 0.0:
                    self.dt = self.get_dt_new()
                    self.status['dtmin'] = min(self.dt, self.status['dtmin'])
                    self.status['dtmax'] = max(self.dt, self.status['dtmax'])
                else:
                    self.dt = self.dt_max

            # See if we are finished yet
            if solution.t >= tend or take_one_step:
                break
      
        # End of main time-stepping loop -------------------------------------

        if self.dt_variable and solution.t < tend \
                and num_steps == self.max_steps:
            raise Exception("Maximum number of timesteps have been taken")

        return self.status

    def step(self,solution):
        r"""
        Take one step
        
        This method is only a stub and should be overridden by all solvers who
        would like to use the default time-stepping in evolve_to_time.
        """
        raise NotImplementedError("No stepping routine has been defined!")

    # ========================================================================
    #  Gauges
    # ========================================================================
    def write_gauge_values(self,solution):
        r"""Write solution (or derived quantity) values at each gauge coordinate
            to file.
        """
        import numpy as np
        if solution.num_aux == 0:
            aux = None
        for i,gauge in enumerate(solution.state.grid.gauges):
            if self.num_dim == 1:
                ix=gauge[0];
                if solution.num_aux > 0:
                    aux = solution.state.aux[:,ix]
                q=solution.state.q[:,ix]
            elif self.num_dim == 2:
                ix=gauge[0]; iy=gauge[1]
                if solution.num_aux > 0:
                    aux = solution.state.aux[:,ix,iy]
                q=solution.state.q[:,ix,iy]
            p=self.compute_gauge_values(q,aux)
            t=solution.t
            if solution.state.keep_gauges:
                gauge_data = solution.state.gauge_data
                if len(gauge_data) == len(solution.state.grid.gauges):
                    gauge_data[i]=np.vstack((gauge_data[i],np.append(t,p)))
                else:
                    gauge_data.append(np.append(t,p))
            
            try:
                solution.state.grid.gauge_files[i].write(str(t)+' '+' '.join(str(j) 
                                                         for j in p)+'\n')  
            except:
                raise Exception("Gauge files are not set up correctly. You should call \
                       \nthe method `setup_gauge_files` of the Grid class object \
                       \nbefore any call for `write_gauge_values` from the Solver class.")
                

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = state
#!/usr/bin/env python
# encoding: utf-8
r"""
Module containing all Pyclaw solution objects

:Authors:
    David I. Ketcheson -- Initial version (June 2011)
"""

import numpy as np

class State(object):
    r"""
    A PyClaw State object contains the current state on a particular patch,
    including the unkowns q, the time t, and the auxiliary coefficients aux.

    Both q and aux are initialized to None.  They cannot be accessed until
    num_eqn and num_aux (respectively) are set.

    :State Data:
    
        The arrays :attr:`q`, and :attr:`aux` have variable 
        extents based on the patch dimensions and the values of 
        :attr:`num_eqn` and :attr:`num_aux`.  Note that these are initialy set to 
        None and later set to appropriately sized empty numpy arrays when
        :attr:`num_eqn` and :attr:`num_aux` are set.
 
    To instantiate a State, we first need a patch:

        >>> from clawpack import pyclaw
        >>> x = pyclaw.Dimension('x',0.,1.,100)
        >>> patch = pyclaw.Patch((x))

    The arguments to the constructor are the patch, the number of equations,
    and the number of auxiliary fields:

        >>> state = pyclaw.State(patch,3,2)
        >>> state.q.shape
        (3, 100)
        >>> state.aux.shape
        (2, 100)
        >>> state.t
        0.0

    Note that state.q and state.aux are initialized as empty arrays (not zeroed).
    Additional parameters, such as scalar values that are used in the Riemann solver,
    can be set using the dictionary state.problem_data.
    """

    def __getattr__(self, key):
        if key in ('num_dim', 'p_centers', 'p_edges', 'c_centers', 'c_edges',
                   'num_cells', 'lower', 'upper', 'delta', 'centers', 'edges',
                   'gauges'):
            return self._get_grid_attribute(key)
        else:
            raise AttributeError("'State' object has no attribute '"+key+"'")

    def _get_grid_attribute(self, name):
        r"""
        Return grid attribute
        
        :Output:
         - (id) - Value of attribute from ``grid``
        """
        return getattr(self.grid,name)
 

    # ========== Property Definitions ========================================
    @property
    def num_eqn(self):
        r"""(int) - Number of unknowns (components of q)"""
        if self.q is None:
            raise Exception('state.num_eqn has not been set.')
        else: return self.q.shape[0]

    @property
    def num_aux(self):
        r"""(int) - Number of auxiliary fields"""
        if self.aux is not None: return self.aux.shape[0]
        else: return 0

    @property
    def mp(self):
        r"""(int) - Number of derived quantities"""
        if self.p is not None: return self.p.shape[0]
        else: return 0
    @mp.setter
    def mp(self,mp):
        if self.p is not None:
            raise Exception('Cannot change state.mp after aux is initialized.')
        else:
            self.p = self.new_array(mp)

    @property
    def grid(self):
        return self.patch.grid

    @property
    def mF(self):
        r"""(int) - Number of output functionals"""
        if self.F is not None: return self.F.shape[0]
        else: return 0
    @mF.setter
    def mF(self,mF):
        if self.F is not None:
            raise Exception('Cannot change state.mF after aux is initialized.')
        else:
            self.F = self.new_array(mF)

    # ========== Class Methods ===============================================
    def __init__(self,geom,num_eqn,num_aux=0):
        from clawpack.pyclaw import geometry
        if isinstance(geom,geometry.Patch):
            self.patch = geom
        elif isinstance(geom,geometry.Domain):
            self.patch = geom.patches[0]
        else:
            raise Exception("""A PyClaw State object must be initialized with
                             a PyClaw Patch object.""")

        # ========== Attribute Definitions ===================================
        r"""pyclaw.Patch.patch - The patch this state lives on"""
        self.p   = None
        r"""(ndarray(mp,...)) - Cell averages of derived quantities."""
        self.F   = None
        r"""(ndarray(mF,...)) - Cell averages of output functional densities."""
        self.problem_data = {}
        r"""(dict) - Dictionary of global values for this patch, 
            ``default = {}``"""
        self.t=0.
        r"""(float) - Current time represented on this patch, 
            ``default = 0.0``"""
        self.index_capa = -1
        self.keep_gauges = False
        r"""(bool) - Keep gauge values in memory for every time step, 
        ``default = False``"""
        self.gauge_data = []
        r"""(list) - List of numpy.ndarray objects. Each element of the list
        stores the values of the corresponding gauge if ``keep_gauges`` is set
        to ``True``"""
        

        self.q   = self.new_array(num_eqn)
        self.aux = self.new_array(num_aux)

    def __str__(self):
        output = "PyClaw State object\n"
        output += "Patch dimensions: %s\n" % str(self.patch.num_cells_global)
        output += "Time  t=%s\n" % (self.t)
        output += "Number of conserved quantities: %s\n" % str(self.q.shape[0])
        if self.aux is not None:
            output += "Number of auxiliary fields: %s\n" % str(self.aux.shape[0])
        if self.problem_data != {}:
            output += "problem_data: "+self.problem_data.__str__()
        return output

    def is_valid(self):
        r"""
        Checks to see if this state is valid
        
        The state is declared valid based on the following criteria:
            - :attr:`q` is not None
            - :attr:`num_eqn` > 0
            
        A debug logger message will be sent documenting exactly what was not 
        valid.
            
        :Output:
         - (bool) - True if valid, false otherwise.
        
        """
        import logging
        valid = True
        logger = logging.getLogger('pyclaw.solution')
        if not self.q.flags['F_CONTIGUOUS']:
            logger.debug('q array is not Fortran contiguous.')
            valid = False
        return valid
 
    def set_cparam(self,fortran_module):
        """
        Set the variables in fortran_module.cparam to the corresponding values in
        patch.problem_data.  This is the mechanism for passing scalar variables to the
        Fortran Riemann solvers; cparam must be defined as a common block in the
        Riemann solver.

        This function should be called from solver.setup().  This seems like a fragile
        interdependency between solver and state; perhaps problem_data should belong
        to solver instead of state.

        This function also checks that the set of variables defined in cparam 
        all appear in problem_data.
        """
        if hasattr(fortran_module,'cparam'):
            if not set(dir(fortran_module.cparam)) <= set(self.problem_data.keys()):
                raise Exception("""Some required value(s) in the cparam common 
                                   block in the Riemann solver have not been 
                                   set in problem_data.""")
            for global_var_name,global_var_value in self.problem_data.iteritems(): 
                setattr(fortran_module.cparam,global_var_name,global_var_value)

    def set_num_ghost(self,num_ghost):
        """
        Virtual routine (does nothing).  Overridden in the petclaw.state class.
        """
        pass


    def set_q_from_qbc(self,num_ghost,qbc):
        """
        Set the value of q using the array qbc.  This is called after
        qbc is updated by the solver.
        """
        
        patch = self.patch
        if patch.num_dim == 1:
            self.q = qbc[:,num_ghost:-num_ghost]
        elif patch.num_dim == 2:
            self.q = qbc[:,num_ghost:-num_ghost,num_ghost:-num_ghost]
        elif patch.num_dim == 3:
            self.q = qbc[:,num_ghost:-num_ghost,num_ghost:-num_ghost,num_ghost:-num_ghost]
        else:
            raise Exception("Assumption (1 <= num_dim <= 3) violated.")
            
    def set_aux_from_auxbc(self,num_ghost,auxbc):
        """
        Set the value of aux using the array auxbc. 
        """
        
        patch = self.patch
        if patch.num_dim == 1:
            self.aux = auxbc[:,num_ghost:-num_ghost]
        elif patch.num_dim == 2:
            self.aux = auxbc[:,num_ghost:-num_ghost,num_ghost:-num_ghost]
        elif patch.num_dim == 3:
            self.aux = auxbc[:,num_ghost:-num_ghost,num_ghost:-num_ghost,num_ghost:-num_ghost]
        else:
            raise Exception("Assumption (1 <= num_dim <= 3) violated.")


    def get_qbc_from_q(self,num_ghost,qbc):
        """
        Fills in the interior of qbc by copying q to it.
        """
        num_dim = self.patch.num_dim
        
        if num_dim == 1:
            qbc[:,num_ghost:-num_ghost] = self.q
        elif num_dim == 2:
            qbc[:,num_ghost:-num_ghost,num_ghost:-num_ghost] = self.q
        elif num_dim == 3:
            qbc[:,num_ghost:-num_ghost,num_ghost:-num_ghost,num_ghost:-num_ghost] = self.q
        else:
            raise Exception("Assumption (1 <= num_dim <= 3) violated.")

        return qbc
        
    def get_auxbc_from_aux(self,num_ghost,auxbc):
        """
        Fills in the interior of auxbc by copying aux to it.
        """
        num_dim = self.patch.num_dim
        
        if num_dim == 1:
            auxbc[:,num_ghost:-num_ghost] = self.aux
        elif num_dim == 2:
            auxbc[:,num_ghost:-num_ghost,num_ghost:-num_ghost] = self.aux
        elif num_dim == 3:
            auxbc[:,num_ghost:-num_ghost,num_ghost:-num_ghost,num_ghost:-num_ghost] = self.aux
        else:
            raise Exception("Assumption (1 <= num_dim <= 3) violated.")

        return auxbc
        

    # ========== Copy functionality ==========================================
    def __copy__(self):
        return self.__class__(self)
        
        
    def __deepcopy__(self,memo={}):
        import copy
        result = self.__class__(copy.deepcopy(self.patch),self.num_eqn,self.num_aux)
        result.__init__(copy.deepcopy(self.patch),self.num_eqn,self.num_aux)
        
        for attr in ('t'):
            setattr(result,attr,copy.deepcopy(getattr(self,attr)))
        
        if self.q is not None:
            result.q = copy.deepcopy(self.q)
        if self.aux is not None:
            result.aux = copy.deepcopy(self.aux)
        result.problem_data = copy.deepcopy(self.problem_data)
        
        return result

    def sum_F(self,i):
        return np.sum(np.abs(self.F[i,...]))

    def new_array(self,dof):
        if dof==0: return None
        shape = [dof]
        shape.extend(self.grid.num_cells)
        return np.empty(shape,order='F')

    def get_q_global(self):
        r"""
        Returns a copy of state.q.
        """
        return self.q.copy()

    def get_aux_global(self):
        r"""
        Returns a copy of state.aux.
        """
        return self.aux.copy()

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# encoding: utf-8
r"""
Pyclaw utility methods
"""

import time
import os
import sys
import subprocess
import logging
import tempfile
import inspect
import warnings

import numpy as np
import contextlib


LOGGING_LEVELS = {0:logging.CRITICAL,
                  1:logging.ERROR,
                  2:logging.WARNING,
                  3:logging.INFO,
                  4:logging.DEBUG}

def add_parent_doc(parent):
    """add parent documentation for a class""" 
    
    return """
    Parent Class Documentation
    ==========================
    """ + parent.__doc__

def run_serialized(fun):
    """ Decorates a function to only run serially, even if called in parallel.

    In a parallel communicator, the first process will run while the remaining processes
    block on a barrier.  In a serial run, the function will be called directly.

    This currently assumes the global communicator is PETSc.COMM_WORLD, but is easily
    generalized.
    """

    try:
        from petsc4py import PETSc
        is_parallel = True
    except ImportError:
        is_parallel = False

    if is_parallel:
        rank = PETSc.COMM_WORLD.getRank()
        if rank == 0:
            def serial_fun(*args, **kwargs):
                fun(*args, **kwargs)
                PETSc.COMM_WORLD.Barrier()
        else:
            def serial_fun(*args, **kwargs):
                PETSc.COMM_WORLD.Barrier()
    else:
        def serial_fun(*args, **kwargs):
            fun(*args, **kwargs)

    return serial_fun

@run_serialized
def inplace_build(working_dir, warn=True):
    """Build missing extension modules with an in-place build.  This is a convenience
    function for PyClaw applications that rely on custom extension modules.  In its default
    mode, this function emits warnings indicating its actions.

    This function is safe to execute in parallel, it will only run on the 0 zero process while
    the other processes block.
    """

    if warn:
        warnings.warn("missing extension modules")
        warnings.warn("running python setup.py build_ext -i in %s" % working_dir)

    subprocess.check_call('python setup.py build_ext -i', shell=True, cwd=working_dir)

    if warn:
        warnings.warn("successfully executed python setup.py build_ext -i in %s" % working_dir)

def run_app_from_main(application,setplot=None):
    r"""
    Runs an application from pyclaw/examples/, automatically parsing command line keyword
    arguments (key=value) as parameters to the application, with positional
    arguments being passed to PETSc (if it is enabled).

    Perhaps we should take the PETSc approach of having a database of PyClaw
    options that can be queried for options on specific objects within the
    PyClaw runtime instead of front-loading everything through the application
    main...
    """

    # Arguments to the PyClaw should be keyword based, positional arguments
    # will be passed to PETSc
    petsc_args, pyclaw_kwargs = _info_from_argv(sys.argv)

    if 'use_petsc' in pyclaw_kwargs and pyclaw_kwargs['use_petsc']:
        import petsc4py
        petsc_args = [arg.replace('--','-') for arg in sys.argv[1:] if '=' not in arg]
        petsc4py.init(petsc_args)
        from clawpack import petclaw as pyclaw
    else:
        from clawpack import pyclaw

    if sys.version_info >= (2, 7):
        app_kwargs = {key: value for key, value in pyclaw_kwargs.items() 
                      if not key in ('htmlplot','iplot')}
    else:
        # the above fails with Python < 2.7, so write it out...
        app_kwargs = {}
        for key,value in pyclaw_kwargs.items():
            if key not in ('htmlplot','iplot'):
                app_kwargs[key] = value

    claw=application(**app_kwargs)

    # Solve
    status = claw.run()

    # Plot results
    htmlplot = pyclaw_kwargs.get('htmlplot',False)
    iplot    = pyclaw_kwargs.get('iplot',False)
    outdir   = pyclaw_kwargs.get('outdir','./_output')
    if htmlplot:  
        if setplot is not None:
            pyclaw.plot.html_plot(outdir=outdir,setplot=setplot)
        else:
            pyclaw.plot.html_plot(outdir=outdir)
    if iplot:     
        if setplot is not None:
            pyclaw.plot.interactive_plot(outdir=outdir,setplot=setplot)
        else:
            pyclaw.plot.interactive_plot(outdir=outdir)

    return claw

class VerifyError(Exception):
    pass

def gen_variants(application, verifier, kernel_languages=('Fortran',), **kwargs):
    r"""
    Generator of runnable variants of a test application given a verifier

    Given an application, a script for verifying its output, and a
    list of kernel languages to try, generates all possible variants of the
    application to try by taking a product of the available kernel_languages and
    (petclaw/pyclaw).  For many applications, this will generate 4 variants:
    the product of the two main kernel languages ('Fortran' and 'Python'), against
    the the two parallel modes (petclaw and pyclaw).

    For more information on how the verifier function should be implemented,
    see util.test_app for a description, and util.check_diff for an example.

    All unrecognized keyword arguments are passed through to the application.
    """

    arg_dicts = build_variant_arg_dicts(kernel_languages)

    for test_kwargs in arg_dicts:
        test_kwargs.update(kwargs)
        try:
            test_name = application.__module__
        except:
            test_name = inspect.getmodule(application)
        if 'solver_type' in test_kwargs:
            solver_info = 'solver_type={solver_type!s}, '
        else:
            solver_info = ''
        test = lambda: test_app(application, verifiers, test_kwargs)
        test.description = ('{test_name!s}(kernel_language={kernel_language!s}, ' +
                            solver_info + 'use_petsc={use_petsc!s})').format(test_name=test_name, **test_kwargs)
        yield test
    return

def build_variant_arg_dicts(kernel_languages=('Fortran',)):
    import itertools

    # only test petsc4py if it is available
    try:
        import petsc4py
        use_petsc_opts=(True,False)
    except ImportError:
        use_petsc_opts = (False,)

    opt_names = 'use_petsc','kernel_language'
    opt_product = itertools.product(use_petsc_opts,kernel_languages)
    arg_dicts = [dict(zip(opt_names,argset)) for argset in opt_product]

    return arg_dicts

def test_app_variants(application, verifier, kernel_languages, **kwargs):

    arg_dicts = build_variant_arg_dicts(kernel_languages)

    for test_kwargs in arg_dicts:
        test_kwargs.update(kwargs)
        test_app(application, verifier, test_kwargs)
    return

def test_app(application, verifier, kwargs):
    r"""
    Test the output of a given application against its verifier method.

    This function performs the following two function calls::

        output = application(**kwargs)
        check_values = verifier(output)

    The verifier method should return None if the output is correct, otherwise
    it should return an indexed sequence of three items::

      0 - expected value
      1 - test value
      2 - string describing the tolerance type (abs/rel) and value.

    This information is used to present descriptive help if an error is detected.
    For an example verifier method, see util.check_diff

    """
    print kwargs

    if 'use_petsc' in kwargs and not kwargs['use_petsc']:
        try:
            # don't duplicate serial test runs
            from petsc4py import PETSc
            rank = PETSc.COMM_WORLD.getRank()
            if rank != 0:
                return
        except ImportError, e:
            pass

    claw = application(**kwargs)
    claw.run()
    check_values = verifier(claw)

    if check_values is not None:
        err = \
        """%s
********************************************************************************
verification function
%s
args                 : %s
norm of expected data: %s
norm of test data    : %s
test error           : %s
%s
********************************************************************************
""" % \
        (inspect.getsourcefile(application),
         inspect.getsource(verifier),
         kwargs,
         check_values[0],
         check_values[1],
         check_values[2],
         check_values[3])
        raise VerifyError(err)
    return

def check_diff(expected, test, **kwargs):
    r"""
    Checks the difference between expected and test values, return None if ok

    This function expects either the keyword argument 'abstol' or 'reltol'.
    """
    err_norm = np.linalg.norm(expected - test)
    expected_norm = np.linalg.norm(expected)
    test_norm = np.linalg.norm(test)
    if 'abstol' in kwargs:
        if err_norm < kwargs['abstol']: return None
        else: return (expected_norm, test_norm, err_norm,
                      'abstol  : %s' % kwargs['abstol'])
    elif 'reltol' in kwargs:
        if err_norm/expected_norm < kwargs['reltol']: return None
        else: return (expected_norm, test_norm, err_norm,
                      'reltol  : %s' % kwargs['reltol'])
    else:
        raise Exception('Incorrect use of check_diff verifier, specify tol!')



# ============================================================================
#  F2PY Utility Functions
# ============================================================================
def compile_library(source_list,module_name,interface_functions=[],
                        local_path='./',library_path='./',f2py_flags='',
                        FC=None,FFLAGS=None,recompile=False,clean=False):
    r"""
    Compiles and wraps fortran source into a callable module in python.

    This function uses f2py to create an interface from python to the fortran
    sources in source_list.  The source_list can either be a list of names
    of source files in which case compile_library will search for the file in
    local_path and then in library_path.  If a path is given, the file will be
    checked to see if it exists, if not it will look for the file in the above
    resolution order.  If any source file is not found, an IOException is
    raised.

    The list interface_functions allows the user to specify which fortran
    functions are actually available to python.  The interface functions are
    assumed to be in the file with their name, i.e. claw1 is located in
    'claw1.f95' or 'claw1.f'.

    The interface from fortran may be different than the original function
    call in fortran so the user should make sure to check the automatically
    created doc string for the fortran module for proper use.

    Source files will not be recompiled if they have not been changed.

    One set of options of note is for enabling OpenMP, it requires the usual
    fortran flags but the OpenMP library also must be compiled in, this is
    done with the flag -lgomp.  The call to compile_library would then be:

    compile_library(src,module_name,f2py_flags='-lgomp',FFLAGS='-fopenmp')

    For complete optimization use:

    FFLAGS='-O3 -fopenmp -funroll-loops -finline-functions -fdefault-real-8'

    :Input:
     - *source_list* - (list of strings) List of source files, if these are
       just names of the source files, i.e. 'bc1.f' then they will be searched
       for in the default source resolution order, if an explicit path is
       given, i.e. './bc1.f', then the function will use that source if it can
       find it.
     - *module_name* - (string) Name of the resulting module
     - *interface_functions* - (list of strings) List of function names to
       provide access to, if empty, all functions are accessible to python.
       Defaults to [].
     - *local_path* - (string) The base path for source resolution, defaults
       to './'.
     - *library_path* - (string) The library path for source resolution,
       defaults to './'.
     - *f2py_flags* - (string) f2py flags to be passed
     - *FC* - (string) Override the environment variable FC and use it to
       compile, note that this does not replace the compiler that f2py uses,
       only the object file compilation (functions that do not have
       interfaces)
     - *FFLAGS* - (string) Override the environment variable FFLAGS and pass
       them to the fortran compiler
     - *recompile* - (bool) Force recompilation of the library, defaults to
       False
     - *clean* - (bool) Force a clean build of all source files
    """

    # Setup logger
    logger = logging.getLogger('f2py')
    temp_file = tempfile.TemporaryFile()
    logger.info('Compiling %s' % module_name)

    # Force recompile if the clean flag is set
    if clean:
        recompile = True

    # Expand local_path and library_path
    local_path = os.path.expandvars(local_path)
    local_path = os.path.expanduser(local_path)
    library_path = os.path.expandvars(library_path)
    library_path = os.path.expanduser(library_path)

    # Fetch environment variables we need for compilation
    if FC is None:
        if os.environ.has_key('FC'):
            FC = os.environ['FC']
        else:
            FC = 'gfortran'

    if FFLAGS is None:
        if os.environ.has_key('FFLAGS'):
            FFLAGS = os.environ['FFLAGS']
        else:
            FFLAGS = ''

    # Create the list of paths to sources
    path_list = []
    for source in source_list:
        # Check to see if the source looks like a path, i.e. it contains the
        # os.path.sep character
        if source.find(os.path.sep) >= 0:
            source = os.path.expandvars(source)
            source = os.path.expanduser(source)
            # This is a path, check to see if it's valid
            if os.path.exists(source):
                path_list.append(source)
                continue
            # Otherwise, take the last part of the path and try searching for
            # it in the resolution order
            source = os.path.split(source)

        # Search for the source file in local_path and then library_path
        if os.path.exists(os.path.join(local_path,source)):
            path_list.append(os.path.join(local_path,source))
            continue
        elif os.path.exists(os.path.join(library_path,source)):
            path_list.append(os.path.join(library_path,source))
            continue
        else:
            raise IOError('Could not find source file %s' % source)

    # Compile each of the source files if the object files are not present or
    # if the modification date of the source file is newer than the object
    # file's creation date
    object_list = []
    src_list = []
    for path in path_list:
        object_path = os.path.join(os.path.split(path)[0],
            '.'.join((os.path.split(path)[1].split('.')[:-1][0],'o')))

        # Check to see if this path contains one of the interface functions
        if os.path.split(path)[1].split('.')[:-1][0] in interface_functions:
            src_list.append(path)
            continue
        # If there are no interface functions specified, then all source files
        # must be included in the f2py call
        elif len(interface_functions) == 0:
            src_list.append(path)
            continue

        if os.path.exists(object_path) and not clean:
            # Check to see if the modification date of the source file is
            # greater than the object file
            if os.path.getmtime(object_path) > os.path.getmtime(path):
                object_list.append(object_path)
                continue
        # Compile the source file into the object file
        command = '%s %s -c %s -o %s' % (FC,FFLAGS,path,object_path)
        logger.debug(command)
        subprocess.call(command,shell=True,stdout=temp_file)
        object_list.append(object_path)

    # Check to see if recompile is needed
    if not recompile:
        module_path = os.path.join('.','.'.join((module_name,'so')))
        if os.path.exists(module_path):
            for src in src_list:
                if os.path.getmtime(module_path) < os.path.getmtime(src):
                    recompile = True
                    break
            for obj in object_list:
                if os.path.getmtime(module_path) < os.path.getmtime(obj):
                    recompile = True
                    break
        else:
            recompile = True

    if recompile:
        # Wrap the object files into a python module
        f2py_command = "f2py -c"
        # Add standard compiler flags
        f2py_command = ' '.join((f2py_command,f2py_flags))
        f2py_command = ' '.join((f2py_command,"--f90flags='%s'" % FFLAGS))
        # Add module names
        f2py_command = ' '.join((f2py_command,'-m %s' % module_name))
        # Add source files
        f2py_command = ' '.join((f2py_command,' '.join(src_list)))
        # Add object files
        f2py_command = ' '.join((f2py_command,' '.join(object_list)))
        # Add interface functions
        if len(interface_functions) > 0:
            f2py_command = ' '.join( (f2py_command,'only:') )
            for interface in interface_functions:
                f2py_command = ' '.join( (f2py_command,interface) )
            f2py_command = ''.join( (f2py_command,' :') )
        logger.debug(f2py_command)
        status = subprocess.call(f2py_command,shell=True,stdout=temp_file)
        if status == 0:
            logger.info("Module %s compiled" % module_name)
        else:
            logger.info("Module %s failed to compile with code %s" % (module_name,status))
            sys.exit(13)
    else:
        logger.info("Module %s is up to date." % module_name)

    temp_file.seek(0)
    logger.debug(temp_file.read())
    temp_file.close()

def construct_function_handle(path,function_name=None):
    r"""
    Constructs a function handle from the file at path.

    This function will attempt to construct a function handle from the python
    file at path.

    :Input:
     - *path* - (string) Path to the file containing the function
     - *function_name* - (string) Name of the function defined in the file
       that the handle will point to.  Defaults to the same name as the file
       without the extension.

    :Output:
     - (func) Function handle to the constructed function, None if this has
       failed.
    """
    # Determine the resulting function_name
    if function_name is None:
        function_name = path.split('/')[-1].split('.')[0]

    full_path = os.path.abspath(path)
    if os.path.exists(full_path):
        suffix = path.split('.')[-1]
        # This is a python file and we just need to read it and map it
        if suffix in ['py']:
            execfile(full_path,globals())
            return eval('%s' % function_name)
        else:
            raise Exception("Invalid file type for function handle.")
    else:
        raise Exception("Invalid file path %s" % path)


#---------------------------------------------------------
def read_data_line(inputfile,num_entries=1,data_type=float):
#---------------------------------------------------------
    r"""
    Read data a single line from an input file

    Reads one line from an input file and returns an array of values

    inputfile: a file pointer to an open file object
    num_entries: number of entries that should be read, defaults to only 1
    type: Type of the values to be read in, they all must be the same type

    This function will return either a single value or an array of values
    depending on if num_entries > 1

    """
    l = []
    while  l==[]:  # skip over blank lines
        line = inputfile.readline()
        l = line.split()
    val = np.empty(num_entries,data_type)
    if num_entries > len(l):
        print 'Error in read_data_line: num_entries = ', num_entries
        print '  is larger than length of l = ',l
    if num_entries == 1:  # This is a convenience for calling functions
        return data_type(l[0])
    val = [data_type(entry) for entry in l[:num_entries]]
    return val

#----------------------------------------
def convert_fort_double_to_float(number):
#----------------------------------------
    r"""
    Converts a fortran format double to a float

    Converts a fortran format double to a python float.

    number: is a string representation of the double.  Number should
    be of the form "1.0d0"

    """
    a = number.split('d')
    return float(a[0])*10**float(a[1])

#-----------------------------
def current_time(addtz=False):
#-----------------------------
    # determine current time and reformat:
    time1 = time.asctime()
    year = time1[-5:]
    day = time1[:-14]
    hour = time1[-13:-5]
    current_time = day + year + ' at ' + hour
    if addtz:
        current_time = current_time + ' ' + time.tzname[time.daylight]
    return current_time


def _method_info_from_argv(argv=None):
    """Command-line -> method call arg processing.

    - positional args:
            a b -> method('a', 'b')
    - intifying args:
            a 123 -> method('a', 123)
    - json loading args:
            a '["pi", 3.14, null]' -> method('a', ['pi', 3.14, None])
    - keyword args:
            a foo=bar -> method('a', foo='bar')
    - using more of the above
            1234 'extras=["r2"]'  -> method(1234, extras=["r2"])

    @param argv {list} Command line arg list. Defaults to `sys.argv`.
    @returns (<method-name>, <args>, <kwargs>)
    """
    import json
    if argv is None:
        argv = sys.argv

    method_name, arg_strs = argv[1], argv[2:]
    args = []
    kwargs = {}
    for s in arg_strs:
        if s.count('=') == 1:
            key, value = s.split('=', 1)
        else:
            key, value = None, s
        try:
            value = json.loads(value)
        except ValueError:
            pass
        if value=='True': value=True
        if value.lower()=='false': value=False
        if key:
            kwargs[key] = value
        else:
            args.append(value)
    return method_name, args, kwargs

def _info_from_argv(argv=None):
    """Command-line -> method call arg processing.

    - positional args:
            a b -> method('a', 'b')
    - intifying args:
            a 123 -> method('a', 123)
    - json loading args:
            a '["pi", 3.14, null]' -> method('a', ['pi', 3.14, None])
    - keyword args:
            a foo=bar -> method('a', foo='bar')
    - using more of the above
            1234 'extras=["r2"]'  -> method(1234, extras=["r2"])

    @param argv {list} Command line arg list. Defaults to `sys.argv`.
    @returns (<method-name>, <args>, <kwargs>)
    """
    import json
    if argv is None:
        argv = sys.argv

    arg_strs = argv[1:]
    args = []
    kwargs = {}
    for s in arg_strs:
        if s.count('=') == 1:
            key, value = s.split('=', 1)
        else:
            key, value = None, s
        try:
            value = json.loads(value)
        except ValueError:
            pass
        if value=='True': value=True
        if value=='False': value=False
        if key:
            kwargs[key] = value
        else:
            args.append(value)
    return args, kwargs

def _arguments_str_from_dictionary(options):
    """
    Convert method options passed as a dictionary to a str object
    having the form of the method arguments
    """
    option_string = ""
    for k in options:
        if isinstance(options[k], str):
            option_string += k+"='"+str(options[k])+"',"
        else:
            option_string += k+"="+str(options[k])+","
    option_string = option_string.strip(',')

    return option_string
#-----------------------------
class FrameCounter:
#-----------------------------
    r"""
    Simple frame counter

    Simple frame counter to keep track of current frame number.  This can
    also be used to keep multiple runs frames seperated by having multiple
    counters at once.

    Initializes to 0
    """
    def __init__(self):
        self.__frame = 0

    def __repr__(self):
        return str(self.__frame)

    def increment(self):
        r"""
        Increment the counter by one
        """
        self.__frame += 1
    def set_counter(self,new_frame_num):
        r"""
        Set the counter to new_frame_num
        """
        self.__frame = new_frame_num
    def get_counter(self):
        r"""
        Get the current frame number
        """
        return self.__frame
    def reset_counter(self):
        r"""
        Reset the counter to 0
        """
        self.__frame = 0

########NEW FILE########
