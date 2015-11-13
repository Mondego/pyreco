__FILENAME__ = cgp
try:
    PLOTTING='matplotlib'
    import matplotlib.pyplot as plt
except:
    import subprocess
    PLOTTING='external'

import circuits
import random
from copy import deepcopy
from time import strftime,time
import re
import pickle
from os.path import join as path_join
import os
import getch
import sys
import multiprocessing
import chromosomes
from optimization.diff_evolve import *
inf = 1e30

def multipliers(x):
    """Convert values with si multipliers to numbers"""
    try:
        return float(x)
    except:
        pass
    try:
        a = x[-1]
        y = float(x[:-1])
        endings = {'G':9,'Meg':6,'k':3,'m':-3,'u':-6,'n':-9,'p':-12,'s':0}
        return y*(10**endings[a])
    except:
        raise ValueError("I don't know what {} means".format(x))

class CGP:
    """
    Evolutionary circuits.

    pool_size: Amount of circuits in one generation
    nodes: maximum number of available nodes, nodes are named n0,n1,n2,.. and ground node is 0(not n0)
    parts_list: List of circuit elements available
    max_parts: Integer of maximum number of circuit elements in one circuit
    elitism: Integer of number of circuits to clone driectly to next generation
    mutation_rate: Mutation propability, float in range 0.0-1.0, but not exactly 1.0, because mutation can be applied many times.
    crossover_rate: Propability of crossover.
    fitnessfunction: List of functions to test circuits against
    fitness_weight: Scores from fitness functions are weighted with this weight
    spice_sim_commands: Commands for SPICE simulator
    log: Log file to save progress
    plot_titles: Titles for the plots of cricuits
    """
    def __init__(self,
    population,
    parts,
    max_parts,
    elitism,
    mutation_rate,
    crossover_rate,
    fitness_function,
    constraints,
    spice_commands,
    log_file,
    title='',
    common='',
    models='',
    fitness_weight=None,
    constraint_weight=None,
    nodes=None,
    resumed=False,
    extra_value=None,
    plot_titles=None,
    plot_yrange=None,
    selection_weight=1,
    max_mutations=3,
    **kwargs):

        if kwargs['chromosome'] == 'netlist':
            self.chromosome = chromosomes.netlist
        elif kwargs['chromosome'] == 'chain':
            self.chromosome = chromosomes.chain
        else:
            raise ValueError("Invalid chromosome")
        #Correct the types
        if hasattr(fitness_function, '__call__'):
            self.ff=[fitness_function]
        else:
            self.ff=fitness_function

        if hasattr(constraints, '__call__'):
            self.constraints=[constraints]
        else:
            self.constraints = constraints

        if hasattr(spice_commands, '__call__'):
            self.spice_commands=[spice_commands+common+models]
        else:
            self.spice_commands=[i+common+models for i in spice_commands]

        if fitness_weight==None:
            self.fitness_weight=[{}]
        else:
            self.fitness_weight = fitness_weight

        if self.constraints == None:
            self.constraints = [None for i in xrange(len(spice_commands))]

        if constraint_weight==None:
            self.constraint_weight=[100 for i in xrange(len(spice_commands))]
        else:
            self.constraint_weight = constraint_weight

        if len(self.spice_commands)>len(self.fitness_weight):
            raise Exception('Fitness function weight list length is incorrect')
        if len(self.spice_commands)>len(self.ff):
            raise Exception('Not enough fitness functions')
        if len(self.spice_commands)>len(self.constraints):
            raise Exception('Not enough constraints. Use None for no constraint')
        if len(self.spice_commands)>len(self.constraint_weight):
            raise Exception('Not enough constraint weights.')
        sim = map(self.parse_sim_options,self.spice_commands)

        print strftime("%Y-%m-%d %H:%M:%S")
        for e,i in enumerate(sim,1):
            print 'Simulation {0} - Type: {1}, Logarithmic plot: {2}'.format(e,i[0],str(i[1]))
            if i[3]:
                print 'Temperature specified in simulation'
                self.temperatures = True
                #TODO write the current temperature in the plot
        print

        self.timeout = kwargs['timeout']
        self.c_free_gens = kwargs['constraint_free_generations']
        self.rnd_circuits = kwargs['random_circuits']
        self.gradual_constraints = kwargs['gradual_constraints']
        self.constraint_ramp = kwargs['constraint_ramp']
        self.plot_all_gens = kwargs['plot_every_generation']

        self.def_scoring = kwargs['default_scoring']
        self.c_rank = kwargs['custom_scoring']

        if type(self.c_free_gens) not in (int,long,float):
            raise Exception('constraint_free_generations must be a number')
        if type(self.gradual_constraints) != bool:
            raise Exception('gradual_constraints must be of type "bool"')
        if type(self.constraint_ramp) not in (int,long,float):
            raise Exception('constraint_ramp must be a number')
        if type(self.plot_all_gens)!=bool:
            raise Exception('plot_every_generation must be of type "bool"')
        self.overflowed = 0

        self.sigma = kwargs['node_stddev']
        self.inputs = kwargs['inputs']
        self.outputs = kwargs['outputs']
        self.special_nodes = kwargs['special_nodes']
        self.special_node_prob = kwargs['special_node_prob']

        #sim_type is list of SPICE simulation types(ac,dc,tran...)
        self.sim_type = [sim[i][0] for i in xrange(len(sim))]
        #Boolean for each simulation for logarithm or linear plot
        self.log_plot = [sim[i][1] for i in xrange(len(sim))]
        #Maximum value of frequency or sweep
        self.frange   = [sim[i][2] for i in xrange(len(sim))]
        self.constraints_filled = False
        if nodes == None:
            self.nodes = max_parts
        else:
            self.nodes = nodes
        self.max_parts = max_parts
        self.extra_value = extra_value
        self.selection_weight = selection_weight

        #FIXME weight function plotting is currently disabled
        self.plot_weight=False
        #if all(i==None for i in self.fitness_weight):
        #    self.plot_weight=False
        #else:
        #    self.plot_weight=True

        if all(i==None for i in self.constraints):
            self.plot_constraints=False
        else:
            self.plot_constraints=True

        self.pool_size=population
        self.parts_list = parts
        self.generation=0
        self.elitism=elitism
        self.alltimebest=(float('inf'),float('inf'))
        self.mrate = mutation_rate
        self.crate = crossover_rate
        self.max_mutations = max_mutations
        self.logfile = log_file
        if not resumed:
            log_file.write("Spice simulation commands:\n"+'\n'.join(self.spice_commands)+'\n\n\n')

        self.plot_titles = plot_titles
        self.plot_yrange = plot_yrange

        #Directory to save files in
        self.directory = title

        #Generate seed circuits
        seed = kwargs['seed']
        self.seed_copies = kwargs['seed_copies']
        self.seed_circuits = []
        if seed!=None:
            if type(seed)==str:
                seed = [seed]
            for element in seed:
                self.seed_circuits.append(self.chromosome.parse_circuit(element, 
                    self.max_parts, self.parts_list, self.sigma, self.inputs, self.outputs,
                    self.special_nodes, self.special_node_prob, self.extra_value))



    def parse_sim_options(self,option):
        """Parses spice simulation commands for ac,dc,trans and temp words.
        If ac simulation is found plotting scale is made logarithmic"""
        m = re.search(r'\n(ac|AC) [a-zA-Z1-9]* [0-9\.]* [0-9\.]* [0-9\.]*[a-zA-Z]?[0-9\.]*',option)
        temp = ('.temp' in option) or ('.dtemp' in option)
        if m!=None:
            m = m.group(0).split()
            return m[0],False if m[1]=='lin' else True,multipliers(m[-1]),temp
        m = re.search(r'\n(dc|DC) [a-zA-Z1-9]* [0-9\.]* [0-9\.]*',option)
        if m!=None:
            m = m.group(0).split()
            return m[0],False,multipliers(m[-1]),temp
        m = re.search(r'\n(tran|TRAN) [0-9\.]*[a-zA-Z]? [0-9\.]*[a-zA-Z]?',option)
        if m!=None:
            m = m.group(0).split()
            return m[0],False,multipliers(m[-1]),temp
        else:
            return 0,False,0,temp

    def eval_single(self, ckt, options):
        """Used in plotting, when only 1 circuits needs to be simulated"""
        program = ckt.spice(options)
        thread = circuits.spice_thread(program)
        thread.start()
        thread.join(2*self.timeout)
        return thread.result

    def _optimize(self,pool):

        def g(self,ckt,x):
            ckt.set_values(x)
            return self.rank_pool([ckt])[0][0]

        for e,c in enumerate(pool):
            c = c[1]
            bounds = c.value_bounds()
            if len(bounds)==0:
                continue
            lbound = [b[0] for b in bounds]
            ubound = [b[1] for b in bounds]
            x0 = [c.get_values()]
            h = lambda x:g(self,c,x)
            try:
                d = DiffEvolver.frombounds(h,lbound,ubound, 30, x0=x0,strategy=('best',2,'bin'))
                gens = 2
                prev = pool[e][0]
                d.solve(2)
                while gens < 10:
                    gens += 2
                    d.solve(2)
                    if not d.best_value + gens - 4 < prev:
                        break
                    prev = d.best_value
                c.set_values(d.best_vector)
                #print d.best_val_history
                print e,gens,pool[e][0],d.best_value
                pool[e] = (d.best_value,c)
                del d
            except KeyboardInterrupt:
                return
        return pool

    def optimize_values(self, pool):
        best_score = pool[0][0]
        circuits = min(max(2*multiprocessing.cpu_count(),int(0.01*len(pool))),4*multiprocessing.cpu_count())
        i = 1
        #Already reached the best possible score
        if best_score == 0:
            return pool
        #Circuits to optimize
        op = [pool[0]]
        indices = [0]
        for score in xrange(1,len(pool)):
            if pool[score][0]>inf/2:
                break
        delta = (pool[score-1][0]-pool[0][0])/(score+1)
        while i < len(pool) and len(op)<circuits:
            if pool[i][0] > best_score*100:
                break
            if abs(pool[i][0]-best_score)> 0.01 and abs(1-pool[i][0]/best_score):
                #Make sure scores are different enough and score is
                #worth optimizing
                if all(abs(pool[i][0]-p[0])>delta for p in op):
                    op.append(pool[i])
                    indices.append(i)
            i += random.randint(1,min(2,score/circuits))

        print "Optimizing"

        try:
            l = len(op)
            cpool = multiprocessing.Pool()
            partitions = multiprocessing.cpu_count()
            op = [op[i*l/partitions:(i+1)*l/partitions] for i in xrange(partitions)]
            p = cpool.map(self._optimize,op)
            cpool.close()
        except KeyboardInterrupt:
            cpool.terminate()
            return
        op2 = []
        for thread in p:
            op2.extend(thread)
        for e,i in enumerate(indices):
            pool[i] = op2[e]
        return pool

    def rank_pool(self,pool):
        """Multithreaded version of self.rank, computes scores for whole pool"""
        try:
            scores  = [0]*len(pool)

            lasterror = None
            timeouts = 0
            for i in xrange(len(self.spice_commands)):
                errors = 0
                skipped = 0
                for t in xrange(len(pool)):
                    if scores[t]>=inf:
                        continue
                    thread = circuits.spice_thread(pool[t].spice(self.spice_commands[i]))
                    thread.start()
                    thread.join(self.timeout)
                    if thread.is_alive():
                        timeouts += 1
                        if self.generation==1:
                            if t<len(self.seed_circuits):
                                print "Seed circuit simulation timed out. Aborting."
                                print "Increase simulation timeout with 'timeout=?' command"
                                exit()
                        try:
                            thread.spice.terminate()
                        except OSError:#Thread died before we could kill it
                            pass

                    if thread==None:
                        #Something went wrong, just ignore it
                        scores[t]=inf
                        skipped+=1
                        continue
                    if thread.result==None:
                        #Error in simulation
                        errors+=1
                        lasterror = "Simulation timedout"
                        scores[t]=inf
                    elif thread.result[1]=={}:
                        #SPICE didn't return anything
                        errors+=1
                        lasterror = thread.result[0]
                        scores[t]=inf
                    else:
                        #Everything seems to be fine, calculate scores
                        if scores[t]<inf:
                            #Custom scoring function
                            if self.c_rank!=None:
                                scores[t]+=self.c_rank(thread.result[1],extra=pool[t].extra_value,circuit=pool[t])
                            #Default scoring function
                            if self.def_scoring:
                                for k in thread.result[1].keys():
                                    scores[t]+=self._rank(thread.result[1],i,k,extra=pool[t].extra_value,circuit=pool[t])
                        thread.result = None
                #Disable error reporting when size of pool is very low
                if errors + skipped == len(pool) and len(pool)>10:
                    #All simulations failed
                    raise SyntaxError("Simulation {} failed for every circuit.\nSpice returned {}".format(i,lasterror))
            #Don't increase timeout when there is only 1 circuit
            if len(pool) > 1:
                if timeouts != 0:
                    print '{} simulation(s) timed out'.format(timeouts)
                if timeouts > len(pool)/10:
                    if timeouts > len(pool)/2:
                        self.timeout *= 1.5
                        print "Increasing timeout length by 50%, to {}".format(self.timeout)
                    else:
                        self.timeout *= 1.25
                        print "Increasing timeout length by 25%, to {}".format(self.timeout)
            return [(scores[i],pool[i]) for i in xrange(len(pool))]
        except KeyboardInterrupt:
            return

    def _rank(self,x,i,k,extra=None,circuit=None):
        """Score of single circuit against single fitness function
        x is a dictionary of measurements, i is number of simulation, k is the measurement to score"""
        total=0.0
        func = self.ff[i]
        try:#fitness_weight might be None, or it might be list of None, or list of dictionary that contains None
            weight = self.fitness_weight[i][k]
        except (KeyError,TypeError,IndexError):
            weight = lambda x,**kwargs:1
        #If no weight function create function that returns one for all inputs
        if type(weight) in (int,long,float):
            c = weight
            weight = lambda x,**kwargs:float(c)#Make a constant anonymous function

        try:
            f = x[k][0]#Input
            v = x[k][1]#Output
            y = float(max(f))
        except:
            return inf
        #Sometimes spice doesn't simulate whole frequency range
        #I don't know why, so I just check if spice returned the whole range
        if y<0.99*self.frange[i]:
            return inf


        con_filled = True
        con_penalty=0
        for p in xrange(1,len(f)):
            try:
                total+=weight( f[p],extra=extra, generation=self.generation)*(f[p]-f[p-1])*( func(f[p],k,extra=extra, generation=self.generation) - v[p] )**2
            except TypeError as t:
                print 'Fitness function returned invalid value, while testing {} of simulation {}'.format(k,i)
                print t
                raise t
            except OverflowError:
                self.overflowed += 1
                total=inf
                pass
            except KeyboardInterrupt:
                return
            if self.constraints[i]!=None and self.c_free_gens<=self.generation :
                con=self.constraints[i]( f[p],v[p],k,extra=extra,generation=self.generation )
                if con==None:
                    print 'Constraint function {} return None, for input: ({},{},{},extra={},generation={})'.format(i,f[p],v[p],k,extra,self.generation)
                if con==False:
                    con_penalty+=1
                    con_filled=False

        total/=y
        if total<0:
            return inf
        #if self.generation>5 and self.generation%5:
        #    if circuit!=None and con_filled:
        #        total+=sum([element.cost if hasattr(element,'cost') else 0 for element in circuit.elements])
        #if con_penalty>1e5:
        #    con_penalty=1e5
        if self.c_free_gens>self.generation:
            return 1000*total+self.constraint_weight[i]*10
        if self.gradual_constraints:
            if self.generation>=self.constraint_ramp-self.c_free_gens:
                m = 1.0
            else:
                m = (self.generation-self.c_free_gens)/float(self.constraint_ramp)
            total+=m*con_penalty*self.constraint_weight[i]/float(len(f))
        else:
            total+=con_penalty*self.constraint_weight[i]/float(len(f))
        return total*1000+20000*(not con_filled)

    def printpool(self):
        """Prints all circuits and their scores in the pool"""
        for f,c in self.pool:
            print f,c
        print

    def save_plot(self,circuit,i,name='',**kwargs):
        v = circuit.evaluate(self.spice_commands[i],self.timeout)[1]
        #For every measurement in results
        for k in v.keys():
            score = self._rank(v,i,k,extra=circuit.extra_value)

            plt.figure()
            freq = v[k][0]
            gain = v[k][1]
            goal_val = [self.ff[i](f,k,extra=circuit.extra_value,generation=self.generation) for f in freq]
            #if self.plot_weight:
            #    weight_val = [self.fitness_weight[i](c,k) for c in freq]
            if self.constraints[i]!=None and self.plot_constraints:
                constraint_val = [(freq[c],gain[c])  for c in xrange(len(freq)) if not self.constraints[i](freq[c],gain[c],k,extra=circuit.extra_value,generation=self.generation)]

            if self.log_plot[i]==True:#Logarithmic plot
                plt.semilogx(freq,gain,'g',basex=10)
                plt.semilogx(freq,goal_val,'b',basex=10)
                #if self.plot_weight:
                #    plt.semilogx(freq,weight_val,'r--',basex=10)
                if self.plot_constraints:
                    plt.plot(*zip(*constraint_val), marker='.', color='r', ls='')
            else:
                plt.plot(freq,gain,'g')
                plt.plot(freq,goal_val,'b')
                #if self.plot_weight:
                #    plt.plot(freq,weight_val,'r--')
                if self.plot_constraints:
                    plt.plot(*zip(*constraint_val), marker='.', color='r', ls='')

            # update axis ranges
            ax = []
            ax[0:4] = plt.axis()
            # check if we were given a frequency range for the plot
            if k in self.plot_yrange.keys():
                plt.axis([min(freq),max(freq),self.plot_yrange[k][0],self.plot_yrange[k][1]])
            else:
                plt.axis([min(freq),max(freq),min(-0.5,-0.5+min(goal_val)),max(1.5,0.5+max(goal_val))])

            if self.sim_type[i]=='dc':
                plt.xlabel("Input (V)")
            if self.sim_type[i]=='ac':
                plt.xlabel("Input (Hz)")
            if self.sim_type[i]=='tran':
                plt.xlabel("Time (s)")

            try:
                plt.title(self.plot_titles[i][k])
            except:
                plt.title(k)

            plt.annotate('Generation '+str(self.generation),xy=(0.05,0.95),xycoords='figure fraction')
            if score!=None:
                plt.annotate('Score '+'{0:.2f}'.format(score),xy=(0.75,0.95),xycoords='figure fraction')
            plt.grid(True)
            # turn on the minor gridlines to give that awesome log-scaled look
            plt.grid(True,which='minor')
            if len(k)>=3 and k[1:3] == 'db':
                plt.ylabel("Output (dB)")
            elif k[0]=='v':
                plt.ylabel("Output (V)")
            elif k[0]=='i':
                plt.ylabel("Output (A)")

            plt.savefig(path_join(self.directory,strftime("%Y-%m-%d %H:%M:%S")+'-'+k+'-'+name+'.png'))

    def step(self):
        self.generation+=1

        def sf(pool,weight=1):
            #Select chromosomes from pool using weighted probablities
            r=random.random()**weight
            return random.choice(pool[:1+int(len(pool)*r)])[1]

        #Update best
        if self.generation==1:
            #Randomly generate some circuits
            newpool = [self.chromosome.random_circuit(self.parts_list, self.max_parts, self.sigma, self.inputs, self.outputs, self.special_nodes, self.special_node_prob, extra_value=self.extra_value) for i in xrange(self.pool_size)]
            #Generate seed circuits
            for i,circuit in enumerate(self.seed_circuits):
                newpool[i]=circuit
                #Set seed circuit extra values
                if self.extra_value!=None:
                    best_value = (inf,None)
                    for c,value in enumerate(self.extra_value):
                        #10 test values for one extra_value
                        for x in xrange(11):
                            ev = value[0]+(value[1]-value[0])*(x/10.0)
                            newpool[i].extra_value[c] = ev
                            score = 0
                            for command in xrange(len(self.spice_commands)):
                                v = self.eval_single(newpool[i],self.spice_commands[command])[1]
                                for k in v.keys():
                                    score += self._rank(v,command,k,extra=newpool[i].extra_value)
                            if 0 < score < best_value[0]:
                                #Better value found
                                best_value = (score,ev)
                        #Set the extra value to the best one found
                        print "Seed circuit {}, best found extra_value {}: {}".format(i,c,best_value[1])
                        newpool[i].extra_value[c] = best_value[1]
                #No extra values
                score = 0
                for command in xrange(len(self.spice_commands)):
                    v = self.eval_single(newpool[i],self.spice_commands[command])[1]
                    for k in v.keys():
                        score += self._rank(v,command,k,extra=newpool[i].extra_value)
                print "Seed circuit {}, score: {}".format(i,score)
                self.plotbest(newpool,0)
                for copy in xrange(self.seed_copies-1):
                    newpool[copy*len(self.seed_circuits)+i] = deepcopy(newpool[i])

        else:
            if self.elitism!=0:
                #Pick self.elitism amount of best performing circuits to the next generation
                newpool=[self.pool[i][1] for i in xrange(self.elitism)]
            else:
                newpool=[]

            #FIXME this should be enabled or disabled in the simulation settings
            #if (not self.constraints_filled) and (self.alltimebest[0]<10000):
            #    print 'Constraint filling solution found'
            #    print 'Optimizing for number of elements'
            #    self.constraints_filled = True
            self.best=self.pool[0]

            #We have already chosen "self.elitism" of circuits in the new pool
            newsize=self.elitism
            while newsize<(1.0-self.rnd_circuits)*self.pool_size:
                newsize+=1
                c=deepcopy(sf(self.pool,weight=self.selection_weight))   #selected chromosome
                if random.random()<=self.crate:#crossover
                    d=sf(self.pool,weight=self.selection_weight)
                    c.crossover(d)

                if random.random()<=self.mrate:#mutation
                    c.mutate()
                    tries=0
                    while random.random()<=self.mrate and tries<self.max_mutations:
                        tries+=1
                        c.mutate()
                newpool.append(c)
            while newsize<self.pool_size:
                #Generate new circuits randomly
                newpool.append(self.chromosome.random_circuit(self.parts_list, self.max_parts, self.sigma, self.inputs, self.outputs, self.special_nodes, self.special_node_prob, extra_value=self.extra_value))
                newsize+=1

        start = time()
        try:
            l = len(newpool)
            cpool = multiprocessing.Pool()
            #Partition the pool
            partitions = multiprocessing.cpu_count()
            newpool = [newpool[i*l/partitions:(i+1)*l/partitions] for i in xrange(partitions)]
            p = cpool.map(self.rank_pool,newpool)
            cpool.close()
        except (TypeError,KeyboardInterrupt):
            #Caught keyboardinterrupt. TypeError is raised when subprocess gets
            #keyboardinterrupt
            cpool.terminate()
            exit()
        self.pool = []
        for i in p:
            self.pool.extend(i)

        self.pool = sorted(self.pool)
        if (self.overflowed > self.pool_size/10):
            print "{0}\% of the circuits score overflowed, can't continue reliably. Try to decrease scoring weights.".format(100*float(self.overlflowed)/self.pool_size)
            exit()

        self.overflowed = 0

        #Optimize values
        if self.generation == 5 or self.generation % 10 == 0:
            self.pool = self.optimize_values(self.pool)
            self.pool = sorted(self.pool)

        print "Simulations per second: {}".format(round((len(self.spice_commands)*self.pool_size)/(time()-start),1))
        print "Time per generation: {} seconds".format(round(time()-start,1))
        if self.c_free_gens== self.generation:
            if self.constraints != None:
                print "Constraints enabled"
            self.alltimebest = (inf,None)

        if self.gradual_constraints and self.generation>self.c_free_gens:
            if self.generation-self.c_free_gens>self.constraint_ramp:
                self.gradual_constraints = False


        if self.plot_all_gens or self.pool[0][0]<self.alltimebest[0]:
                print strftime("%Y-%m-%d %H:%M:%S")
                if self.pool[0][1].extra_value != None:
                    print 'Extra values: '+str(self.pool[0][1].extra_value)
                print "Generation "+str(self.generation)+" New best -",self.pool[0][0],'\n',str(self.pool[0][1]),'\n'
                #print 'Cache size: %d/%d'%(self.cache_size,self.cache_max_size)+', Cache hits',self.cache_hits
                self.alltimebest=self.pool[0]
                self.plotbest()
                self.logfile.write(strftime("%Y-%m-%d %H:%M:%S")+' - Generation - '+str(self.generation) +' - '+str(self.alltimebest[0])+':\n'+str(self.alltimebest[1])+'\n\n')
                self.logfile.flush()#Flush changes to the logfile

        #Scale score for gradual constraint ramping
        if self.gradual_constraints and self.generation>self.c_free_gens:
            if self.generation-self.c_free_gens<self.constraint_ramp:
                self.alltimebest = (self.alltimebest[0]*(1-self.c_free_gens+self.generation)/float(self.generation-self.c_free_gens),
                        self.alltimebest[1])

    def averagefit(self):
        """Returns average score of the whole pool."""
        return sum(i[0] for i in self.pool)/float(self.pool_size)

    def plotbest(self,pool=None,nth=0):
        """Plot best circuit in the current pool.
        Alternatively plot nth circuit from the pool given in arguments."""
        if pool==None:
            pool = self.pool
        try:
                    circuit = pool[nth][1]
        except AttributeError:
                    #Not scored yet
                    circuit = pool[nth]
        try:
            if PLOTTING=='matplotlib':
                for c in xrange(len(self.spice_commands)):
                    self.save_plot(
                            circuit,
                            i=c,name=str(c))
            elif PLOTTING=='external':
                for i in xrange(len(self.spice_commands)):
                    v = self.eval_single(circuit,self.spice_commands[i])[1]
                    for k in v.keys():
                        freq = v[k][0]
                        gain = v[k][1]
                        score = self._rank(v,i,k,extra=circuit.extra_value)
                        goal_val = [self.ff[i](f,k,extra=circuit.extra_value,generation=self.generation) for f in freq]
                        if self.constraints[i]!=None and self.plot_constraints:
                            constraint_val = [(freq[c],gain[c])  for c in xrange(len(freq)) if not self.constraints[i](freq[c],gain[c],k,extra=circuit.extra_value,generation=self.generation)]
                        else:
                            constraint_val = None


                        command = os.path.join(os.path.dirname(os.path.abspath(__file__)),'plotting.py')
                        plt = subprocess.Popen(['python',command],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                        try:
                            title = self.plot_titles[i][k]
                        except (KeyError,TypeError):
                            title = None

                        if self.plot_yrange!=None and k in self.plot_yrange.keys():
                                yrange = self.plot_yrange[k]
                        else:
                            yrange = None
                        path = os.path.join(os.getcwd(),self.directory)
                        data = ((freq,gain),k,goal_val,self.sim_type[i],self.generation,score,path,title,yrange,self.log_plot[i],constraint_val,i)
                        output = plt.communicate(str(data))
                        if output != ('',''):
                            raise multiprocessing.ProcessError("Plotting failed")
        except multiprocessing.ProcessError:
            print "Plotting failed"
            print output[1]


    def run(self):
        try:
            while True:
                self.step()
                print "Saving progress"
                self.save_progress(path_join(self.directory,'.dump'))
        except KeyboardInterrupt:
            pass

    def save_progress(self,out):
        """Saves CGP pool,generation and log filename to file"""
        #pickle format: (generation,pool,logfile)
        out_temp=out+'.tmp'

        with open(out_temp,'w') as dump:
            data = (self.generation,self.pool,self.logfile.name)
            pickle.dump(data,dump)
            print "Saving done"
        try:
            os.remove(out)
        except OSError:
            pass#First time saving and file doesn't exist yet
        os.rename(out_temp,out)

def load_settings(filename):
    no_defaults= ['title','max_parts','spice_commands','parts','fitness_function','inputs','outputs']
            #newpool = [random_circuit(self.parts_list, self.max_parts, self.sigma, self.inputs, self.outputs, self.special_nodes, self.special_node_prob) for i in xrange(self.pool_size)]
    default_settings = {'common':'',
                        'models':'',
                        'constraints':None,
                        'population':1000,
                        'nodes':None,
                        'elitism':1,
                        'mutation_rate':0.75,
                        'crossover_rate':0.1,
                        'fitness_weight':None,
                        'extra_value':None,
                        'log_file':None,
                        'plot_titles':None,
                        'plot_yrange':None,
                        'selection_weight':1,
                        'constraint_weight':None,
                        'max_mutations':5,
                        'constraint_free_generations':1,
                        'gradual_constraints':True,
                        'constraint_ramp':20,
                        'random_circuits':0.01,
                        'plot_every_generation':False,
                        'default_scoring':True,
                        'custom_scoring':None,
                        'seed':None,
                        'seed_copies':1,
                        'timeout':1.0,
                        'special_nodes':[],
                        'special_node_prob':0.1,
                        'node_stddev':2,
                        'chromosome':'chain',
                        }
    settings = default_settings.copy()
    temp = {}
    execfile(filename,temp)
    for key in temp:
        if key[0]!='_':
            if key not in default_settings.keys()+no_defaults:
                print 'Ignoring unknown command:',key
                continue
            settings[key] = temp[key]
    for key in no_defaults:
        if key not in settings.keys():
            print '"{}" is required'.format(key)
            exit()
    print 'Settings loaded'
    return settings

def main(filename):
    settings = load_settings(filename)
    if not os.path.exists(settings['title']):
        os.makedirs(settings['title'])
    resume = False
    try:
        r_file = open(path_join(settings['title'],'.dump'),'r')
        print "Do you want to resume Y/n:"
        while True:
            r = getch._Getch()()
            if r=='':
                resume = True
                print "Resumed"
                break
            if r in ('y','Y','\n'):
                resume = True
                print "Resumed"
                break
            if r in ('n','N'):
                break
    except IOError:
        print 'No save file found'
        pass

    if resume:
        #Resuming from file
        resumed = pickle.load(r_file)
        outfile = open(resumed[2],'a')
    if settings['log_file']!=None:
        settings['log_file']=outfile
    else:
        if resume:
            settings['log_file']= open(resumed[2],'a')
        else:
            settings['log_file']= open(path_join(settings['title'],'sim'+strftime("%Y-%m-%d %H:%M:%S")+'.log'),'w')



    e = CGP(resume=resume,**settings)

    if resume:
        e.generation = resumed[0]
        e.pool = resumed[1]
    e.run()

if __name__ == '__main__':
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = chain
import random
import ast
from common import *

class Device:
    def __init__(self, name, value, kwvalues, model, cost):
        self.name = name
        self.value = value
        self.kwvalues = kwvalues
        self.model = model
        if cost!=None:
            self.cost = cost
        else:
            self.cost = 0

    def spice(self, nodes, device_number=None):
        kw = ''
        if self.kwvalues != None:
            for k in self.kwvalues.keys():
                kw += ' '+k+'='+str(self.kwvalues[k])
        if device_number==None:
            device_number = str(id(self))
        else:
            device_number = str(device_number)
        return self.name + device_number +' '+ ' '.join(map(str,nodes)) + ' '+ (str(self.value) if self.value!=None else '') +  (self.model if self.model!=None else '') + kw

    def __repr__(self):
        return self.spice('-',1)

    def mutatevalue(self, r):
        """Mutates device value. If r is 3-tuple third value is a random
        number distribution. Two first are lower and upper limits."""
        if len(r)==3:
            self.value = r[3](*r[:2])
        else:
            if r[0]>0:
                self.value = log_dist(*r)
            else:
                self.value = random.uniform(*r)

    def mutatekwvalue(self, r):
        """Mutates keyword values. Same logic as in value mutations."""
        kw = random.choice(self.kwvalues.keys())
        r = r[kw]
        if len(r)==3:
            self.kwvalues[kw] = r[3](*r[:2])
        else:
            if r[0]>0:
                self.kwvalues[kw] = log_dist(*r)
            else:
                self.kwvalues[kw] = random.uniform(*r)

def random_device(parts):
    """Generates a random device from parts list.
    "sigma" is the gaussian distribution standard deviation,
    which is used for generating connecting nodes."""
    name = random.choice(parts.keys())
    r = parts[name]
    kw,value,model = [None]*3
    cost = 0
    if 'kwvalues' in r.keys():
        kw = {i:value_dist(r['kwvalues'][i]) for i in r['kwvalues'].keys()}
    if 'value' in r.keys():
        value = value_dist(r['value'])
    if 'model' in r.keys():
        model = r['model'] if type(r['model'])==str else random.choice(r['model'])
    if 'cost' in r.keys():
        cost = r['cost']
    return Device(name, value, kw, model, cost)

def random_instruction(parts, sigma, special_nodes, special_node_prob, mu=0.5):
    """Generate random instruction with random device.
    "sigma" is the standard deviation of nodes."""
    d = random_device(parts)
    nodes = [int(round(random.gauss(mu,sigma))) for i in xrange(parts[d.name]['nodes'])]
    while same(nodes):
        nodes = [int(round(random.gauss(mu,sigma))) for i in xrange(parts[d.name]['nodes'])]
        #Sprinkle some special nodes
        if type(special_node_prob)==list:
            for i in xrange(len(nodes)):
                if random.random() < special_node_prob[i]:
                    nodes[i] = lst_random(special_nodes,special_node_prob)
        else:
            for i in xrange(len(nodes)):
                if random.random() < special_node_prob:
                    nodes[i] = random.choice(special_nodes)

    command = random.randint(0,1)
    return Instruction(command, d, sigma, nodes, special_nodes, special_node_prob)

class Instruction:
    def __init__(self, command, device, sigma, args, special_nodes, special_node_prob):
        self.commands = 2
        self.command = command
        self.device = device
        self.sigma = sigma
        self.args = args
        self.special_nodes = special_nodes
        self.special_node_prob = special_node_prob

    def __call__(self, current_node, device_number):
        #Transform relative nodes to absolute by adding current node
        nodes = [current_node + i if type(i)==int else i for i in self.args]
        #nodes = [i if i>=0 else 0 for i in nodes]
        if self.command == 0:
            #Connect
            return (self.device.spice(nodes,device_number),current_node)
        if self.command == 1:
            #Connect and move
            return (self.device.spice(nodes,device_number),current_node+1)
        #if self.command == 2:
        #    #Move to current_node + self.args
        #    return ('',current_node + self.args)
        raise Exception("Invalid instruction: {}".format(self.command))

    def __repr__(self):
        return self.__call__(0,1)[0]

    def mutate(self, parts):
        #Possible mutations
        m = [self.device.value!=None,self.device.kwvalues!=None,
                self.device.model!=None,True,self.command in (0,1)]
        m = [i for i,c in enumerate(m) if c==True]
        r = random.choice(m)
        if r == 0:
            #Change value
            self.device.mutatevalue(parts[self.device.name]['value'])
        elif r == 1:
            #Change kwvalue
            self.device.mutatekwvalue(parts[self.device.name]['kwvalues'])
        elif r == 2:
            #Change model
            models = parts[self.device.name]['model']
            if type(models)!=str and len(parts[self.device.name]['model'])>1:
                models = set(models)
                #Remove current model
                models.discard(self.device.model)
                self.device.model = random.choice(list(models))
        elif r == 3:
            #Change type of the instruction
            old = self.command
            new = set(range(self.commands))
            new.discard(old)
            self.command = random.choice(list(new))
        elif r == 4:
            #Change nodes
            self.args = [int(random.gauss(0,self.sigma)) for i in xrange(parts[self.device.name]['nodes'])]
            while same(self.args):
                self.args = [int(random.gauss(0,self.sigma)) for i in xrange(parts[self.device.name]['nodes'])]
                #Sprinkle some special nodes
                if type(self.special_node_prob)==list:
                    for i in xrange(len(self.args)):
                        if random.random() < self.special_node_prob[i]:
                            self.args[i] = lst_random(self.special_nodes,self.special_node_prob)
                else:
                    for i in xrange(len(self.args)):
                        if random.random() < self.special_node_prob:
                            self.args[i] = random.choice(self.special_nodes)


def random_circuit(parts, inst_limit, sigma, inputs, outputs, special_nodes, special_node_prob, extra_value=None):
    """Generates a random circuit.
    parts - dictionary of available devices.
    inst_limit - maximum number of instructions.
    sigma - standard deviation of nodes.
    inputs - input nodes.
    outputs - output nodes.
    special_nodes - power supplies and other useful but not necessary nodes.
    special_node_prob - Probability of having a special node in single instruction,
        can be a list or single number.
    """
    #Normalize probabilities and check that probabilities are valid
    special = special_nodes[:]
    if type(special_node_prob)==list:
        if not all(0<i<1 for i in special_node_prob):
            raise ValueError("Invalid probability in special node probabilities list. All probabilities need to be in the open interval (0,1).")
        if len(special_node_prob)!=len(special):
            raise ValueError("Special node lists are of different length.")
    else:
        if not 0<special_node_prob<1:
            raise ValueError("Invalid special node probability. Probability needs to be in the open interval (0,1).")
    #Add the ground
    if '0' not in special:
        special.append('0')
        if type(special_node_prob)==list:
            special_node_prob.append(0.1)
    if max(len(inputs),len(outputs)) > inst_limit:
        raise ValueError("Instruction limit is too small.")
    special = special + inputs + outputs
    if type(special_node_prob)==list:
        special_node_prob = special_node_prob + [0.1]*(len(inputs)+len(outputs))
    inst = [random_instruction(parts, sigma, special, special_node_prob) for i in xrange(random.randint(max(len(inputs),len(outputs)),inst_limit))]
    for e,i in enumerate(inputs):
        nodes = inst[e].args
        nodes[argmin(nodes)] = i
    for e,i in enumerate(outputs,1):
        nodes = inst[-e].args
        nodes[argmax(nodes)] = i
    return Circuit(inst, parts, inst_limit, (parts,sigma,special, special_node_prob), extra_value)

class Circuit:
    def __init__(self, inst, parts, inst_limit, inst_args, extra_value=None):
        #Everything necessary to make a new instruction
        self.inst_args = inst_args
        #List of instructions in the circuit
        self.instructions = inst
        #List of devices
        self.parts = parts
        #Max instructions
        self.inst_limit = inst_limit

        if extra_value!=None:
            self.extra_range = extra_value
            self.extra_value = [random.uniform(*i) for i in self.extra_range]
        else:
            self.extra_value = None

    def spice(self, commands):
        current_node = self.inst_limit
        program = ''
        for device_number,inst in enumerate(self.instructions,1):
            t = inst(current_node,device_number)
            program += t[0]+'\n'
            current_node = t[1]
        return commands+program

    def __repr__(self):
        return self.spice('')

    def mutate(self):
        #Available mutations
        m = [
                len(self.instructions)>0,
                len(self.instructions)>1,
                len(self.instructions)>1,
                len(self.instructions)<self.inst_limit,
                self.extra_value != None
            ]
        m = [i for i,c in enumerate(m) if c==True]
        r = random.choice(m)
        if r==0:
            #Single instruction mutation
            i = random.choice(self.instructions)
            i.mutate(self.parts)
        elif r==1:
            #Exchange two instructions
            i = random.randint(0,len(self.instructions)-1)
            c = random.randint(0,len(self.instructions)-1)
            self.instructions[i],self.instructions[c] = self.instructions[c],self.instructions[i]
        elif r==2:
            #Delete instruction
            i = random.randint(0,len(self.instructions)-1)
            del self.instructions[i]
        elif r==3:
            #Add instructions
            i = random_instruction(*self.inst_args)
            self.instructions.insert(random.randint(0,len(self.instructions)),i)
        elif r==4:
            #Change extra value
            self.extra_value = [random.uniform(*i) for i in self.extra_range]


    def crossover(self, other):
        #if len(self.instructions)<len(other.instructions):
        #    return other.crossover(self)
        r = random.randint(0,1)
        l = max(len(self.instructions),len(other.instructions))
        r1 = random.randint(0,l)
        r2 = random.randint(0,l)
        if r1>r2:
            r1,r2=r2,r1
        if r==0:
            #Two point crossover
            self.instructions = self.instructions[:r1]+other.instructions[r1:r2]+self.instructions[r2:]
            self.instructions = self.instructions[:self.inst_limit]
        else:
            #Single point crossover
            self.instructions = self.instructions[:r1]+other.instructions[r1:]
            self.instructions = self.instructions[:self.inst_limit]

    def value_bounds(self):
        """Return bounds of values for optimization."""
        bounds = []
        for ins in self.instructions:
            if ins.device.value != None:
                bounds.append(self.parts[ins.device.name]['value'])
            if ins.device.kwvalues != None:
                for kw in sorted(self.parts[ins.device.name]['kwvalues'].keys()):
                    bounds.append(self.parts[ins.device.name]['kwvalues'][kw])
        if self.extra_value != None:
            bounds.extend(self.extra_range)
        return bounds

    def get_values(self):
        values = []
        for ins in self.instructions:
            if ins.device.value != None:
                values.append(ins.device.value)
            if ins.device.kwvalues != None:
                for kw in sorted(self.parts[ins.device.name]['kwvalues'].keys()):
                    values.append(ins.device.kwvalues[kw])
        if self.extra_value != None:
            values.extend(self.extra_value)
        return values

    def set_values(self,values):
        i = 0
        for ins in self.instructions:
            if ins.device.value != None:
                ins.device.value = values[i]
                i += 1
            if ins.device.kwvalues != None:
                for kw in sorted(self.parts[ins.device.name]['kwvalues'].keys()):
                    ins.device.kwvalues[kw] = values[i]
                    i += 1
        if self.extra_value != None:
            self.extra_value = values[i:]
        return None

def parse_circuit(circuit, inst_limit, parts, sigma, inputs, outputs, special_nodes, special_node_prob, extra_value=None):
    """Converts netlist to chromosome format."""
    if '0' not in special_nodes:
        special_nodes.append('0')
    special = special_nodes + inputs + outputs
    #Devices starting with same substring are sorted longest
    #first to check longest possible device names first
    sorted_dev = sorted(parts.keys(),reverse=True)
    instructions = []
    #Table for converting circuit nodes to chromosome nodes
    nodes = {}
    len_nodes = 1
    current_node = 0
    for n,line in enumerate(circuit.splitlines()):
        if not line:
            #Ignores empty lines
            continue

        #Current device fields
        d_spice = []
        #Try all the devices
        for dev in sorted_dev:
            if line.startswith(dev):
                #Found matching device from parts list
                current_node += 1#Increase current node
                line = line.split()
                d_nodes = line[1:parts[dev]['nodes']+1]
                for node in d_nodes:
                    if node not in special and node not in nodes:
                        nodes[node] =len_nodes
                        len_nodes += 1

                d_spice = line[parts[dev]['nodes']+1:]
                for e in xrange(len(d_spice)):
                    #Correct types and change SPICE multipliers to bare numbers.
                    try:
                        d_spice[e] = multipliers(d_spice[e])
                    except:
                        #Not a number.
                        pass
                if 'value' in parts[dev]:
                    value = float(d_spice[0])
                    if not parts[dev]['value'][0]<=value<=parts[dev]['value'][1]:
                        raise ValueError("Value of component on line {} is out of bounds\n{}\nBounds defined in the parts dictionary are: {} to {}".format(n,' '.join(line),parts[dev]['value'][0],parts[dev]['value'][1]))
                    d_spice = d_spice[1:]
                else:
                    value = None
                if 'model' in parts[dev]:
                    model = d_spice[0]
                    d_spice = d_spice[1:]
                else:
                    model = None
                if 'kwvalues' in parts[dev]:
                    d_spice = ["'"+i[:i.index('=')]+"'"+i[i.index('='):] for i in d_spice]
                    kwvalues = ast.literal_eval('{'+', '.join(d_spice).replace('=',':')+'}')
                else:
                    kwvalues = None
                if 'cost' in parts[dev]:
                    cost = parts['cost']
                else:
                    cost = 0
                device = Device(dev, value, kwvalues, model, cost)
                node_temp = [nodes[node] - current_node + inst_limit if node in nodes else node for node in d_nodes]
                instructions.append(Instruction(1, device, sigma, node_temp, special, special_node_prob))
                break

        else:
            #Device not found
            print "Couldn't find device in line {}:{}\nIgnoring this line".format(n,line)
    if len(instructions) > inst_limit:
        raise ValueError("Maximum number of devices is too small for seed circuit.")
    return Circuit(instructions, parts, inst_limit, (parts, sigma, special, special_node_prob), extra_value)

#parts = { 'R':{'value':(1,1e6),'nodes':2}, 'C':{'value':(1e-12,1e-3),'nodes':2}, 'Q':{'model':('2N3904','2N3906'),'kwvalues':{'w':(1e-7,1e-5),'l':(1e-7,1e-5)},'nodes':3} }
#r = Device('R',100,None,None,0)
#c = Device('C',1e-5,None,None,0)
#q = Device('Q',None,{'w':1,'l':2},'2N3904',0)
#c = random_circuit(parts, 10, 2, ['in1','in2'],['out'], ['vc','vd'], [0.1,0.1])
#print c
#c.mutate()
#print c
#seed="""
#R1 n4 n3 1k
#R2 out n3 1k
#Q11 n5 n4 in1 2N3904
#Q12 n5 n4 in2 2N3904
#Q13 out n5 0 2N3904
#"""
#inputs = ['in1','in2']
#outputs = ['out']
#special = []
#print parse_circuit(seed, 10, parts, 2, inputs, outputs, special, 0.1)

########NEW FILE########
__FILENAME__ = common
import random
from math import log10

def value_dist(val):
    if len(val)==3:
        return val[3](*val[:2])
    else:
        if val[0]>0:
            return log_dist(*val)
        else:
            return random.uniform(*val)

def argmin(x):
    if len(x) < 2:
        return x[0]
    bestv,idx = x[0],0
    for e,i in enumerate(x[1:],1):
        if i<bestv:
            bestv = i
            idx = e
    return idx

def argmax(x):
    if len(x) < 2:
        return x[0]
    bestv,idx = x[0],0
    for e,i in enumerate(x[1:],1):
        if i>bestv:
            bestv = i
            idx = e
    return idx

def normalize_list(lst):
    """Return normalized list that sums to 1"""
    s = sum(lst)
    return [i/float(s) for i in lst]

def multipliers(x):
    """Convert values with si multipliers to numbers"""
    try:
        return float(x)
    except:
        pass
    try:
        a = x[-1]
        y = float(x[:-1])
        endings = {'G':9,'Meg':6,'k':3,'m':-3,'u':-6,'n':-9,'p':-12,'s':0}
        return y*(10**endings[a])
    except:
        raise ValueError("I don't know what {} means".format(x))

def log_dist(a,b):
    """Generates exponentially distributed random numbers.
    Gives better results for resistor, capacitor and inductor values
    than the uniform distribution."""
    if a <= 0 or a>b:
        raise ValueError("Value out of range. Valid range is (0,infinity).")
    return 10**(random.uniform(log10(a),log10(b)))

def same(x):
    #True if all elements are same
    return reduce(lambda x,y:x==y,x)

def lst_random(lst, probs):
    """Return element[i] with probability probs[i]."""
    s = sum(probs)
    r = random.uniform(0,s)
    t = 0
    for i in xrange(len(lst)):
        t += probs[i]
        if r <= t:
            return lst[i]
    return lst[-1]#Because of rounding errors or something?

########NEW FILE########
__FILENAME__ = netlist
from common import *

class Device:
    """Represents a single component"""
    def __init__(self,name,nodes,cost=0,*args):
        #Name of the component(eg. "R1")
        self.spice_name = name
        #N-tuple of values
        self.values = args
        self.nodes = nodes
        self.cost = cost
    def __repr__(self):
        return self.spice_name+str(id(self))+' '+' '.join(map(str,self.nodes))+' '+' '.join(map(str,*self.values))

def random_element(parts,node_list,fixed_node=None):
    #Return random circuit element from parts list
    name = random.choice(parts.keys())
    part = parts[name]
    spice_line = []
    if 'value' in part.keys():
        minval,maxval = part['value'][:2]
        spice_line.append(log_dist(minval,maxval))
    nodes = [random.choice(node_list) for i in xrange(part['nodes'])]
    while same(nodes):
        nodes = [random.choice(node_list) for i in xrange(part['nodes'])]
    if fixed_node!=None:
        nodes[0]=fixed_node
        random.shuffle(nodes)
    if 'model' in part:
        if type(part['model'])!=str:
            spice_line.append(random.choice(part['model']))
        else:
            spice_line.append(part['model'])
    if 'cost' in part:
        cost = part['cost']
    else:
        cost = 0
    return Device(name,nodes,cost,spice_line)

def mutate_value(element,parts,rel_amount=None):
    i = random.randint(0,len(element.values)-1)
    val = element.values[i]
    name = element.spice_name
    if rel_amount==None:
        try:
            val[i] = log_dist(parts[name]['value'][0],parts[name]['value'][1])
        except:
            return element
    else:
        try:
            temp = val[i]*(2*random.random-1)*rel_amount
            if parts[name]['value'][0]<=temp<=parts[name]['value'][1]:
                val[i] = temp
        except:
            return element
    try:
        cost = parts[element.spice_name]['cost']
    except KeyError:
        cost = 0
    return Device(element.spice_name,element.nodes,cost,val)

class Chromosome:
    """Class that contains one circuit and all of it's parameters"""
    def __init__(self,max_parts,parts_list,nodes,extra_value=None):
        #Maximum number of components in circuit
        self.max_parts = max_parts
        #List of nodes
        self.nodes = nodes
        self.parts_list = parts_list
        #Generates randomly a circuit
        self.elements = [random_element(self.parts_list,self.nodes) for i in xrange(random.randint(1,int(0.75*max_parts)))]
        self.extra_range = extra_value
        if extra_value!=None:
            self.extra_value = [random.uniform(*i) for i in self.extra_range]
        else:
            self.extra_value = None

    def __repr__(self):
        return '\n'.join(map(str,self.elements))

    def get_connected_node(self):
        """Randomly returns one connected node"""
        if len(self.elements)>0:
            device = random.choice(self.elements)
            return random.choice(device.nodes)
        else:
            return 'n1'

    def value_bounds(self):
        bounds = []
        for e in self.elements:
            if 'value' in self.parts_list[e.spice_name]:
                bounds.append(self.parts_list[e.spice_name]['value'][:2])
        if self.extra_value != None:
            bounds.extend(self.extra_range)
        return bounds

    def get_values(self):
        values = []
        for e in self.elements:
            if 'value' in self.parts_list[e.spice_name]:
                values.append(e.values[0][0])
        if self.extra_value != None:
            values.extend(self.extra_value)
        return values

    def set_values(self, values):
        i = 0
        for e in self.elements:
            if 'value' in self.parts_list[e.spice_name]:
                e.values = ([values[i]],)
                i += 1
        if self.extra_value != None:
            self.extra_value = values[i:]
        return None

    def crossover(self, other):
        #if len(self.instructions)<len(other.instructions):
        #    return other.crossover(self)
        r = random.randint(0,1)
        l = max(len(self.elements),len(other.elements))
        r1 = random.randint(0,l)
        r2 = random.randint(0,l)
        if r1>r2:
            r1,r2=r2,r1
        if r==0:
            #Two point crossover
            self.elements = self.elements[:r1]+other.elements[r1:r2]+self.elements[r2:]
            self.elements = self.elements[:self.max_parts]
        else:
            #Single point crossover
            self.elements = self.elements[:r1]+other.elements[r1:]
            self.elements = self.elements[:self.max_parts]

    def mutate(self):
        m = random.randint(0,7)
        i = random.randint(0,len(self.elements)-1)
        if m==0:
            #Change value of one component
            m = random.randint(0,1)
            if m==0:
                #New value
                self.elements[i] = mutate_value(self.elements[i],self.parts_list)
            else:
                #Slight change
                self.elements[i] = mutate_value(self.elements[i],self.parts_list,rel_amount=0.1)
        elif m==1:
            #Add one component if not already maximum number of components
            if len(self.elements)<self.max_parts:
                #self.elements.append(random_element(self.parts_list,self.nodes))
                self.elements.append(random_element(self.parts_list,self.nodes,fixed_node=self.get_connected_node()))
        elif m==2 and len(self.elements)>1:
            #Replace one component with open circuit
            del self.elements[i]
        elif m==3 and len(self.elements)>1:
            #Replace one component with open circuit
            nodes = self.elements[i].nodes
            random.shuffle(nodes)
            try:
                n1 = nodes[0]
                n2 = nodes[1]
            except IndexError:
                return None#Device doesn't have two nodes
            del self.elements[i]
            for element in self.elements:
                element.nodes = [(n1 if i==n2 else i) for i in element.nodes]
        elif m==4:
            #Replace one component keeping one node connected
            fixed_node = random.choice(self.elements[i].nodes)
            del self.elements[i]
            self.elements.append(random_element(self.parts_list,self.nodes,fixed_node=fixed_node))
        elif m==5:
            #Shuffle list of elements(better crossovers)
            random.shuffle(self.elements)
        elif m==6:
            #Change the extra_value
            if self.extra_range!=None:
                i = random.randint(0,len(self.extra_value)-1)
                self.extra_value[i] = random.uniform(*self.extra_range[i])
            else:
                self.mutate()
        elif m==7:
            #Relabel nodes
            l = len(self.elements)-1
            n1 = random.choice(self.elements[random.randint(0,l)].nodes)
            n2 = random.choice(self.elements[random.randint(0,l)].nodes)
            tries = 0
            while tries<10 or n1!=n2:
                n2 = random.choice(self.elements[random.randint(0,l)].nodes)
                tries+=1
            for element in self.elements:
                element.nodes = [(n1 if i==n2 else (n2 if i==n1 else i)) for i in element.nodes]


    def spice(self,options):
        """Generate the input to SPICE"""
        program = options+'\n'
        for i in self.elements:
            program+=str(i)+'\n'
        return program


def random_circuit(parts, inst_limit, sigma, inputs, outputs, special_nodes, special_node_prob, extra_value=None):
    """Generates a random circuit.
    parts - dictionary of available devices.
    inst_limit - maximum number of nodes
    sigma - standard deviation of nodes.
    inputs - input nodes.
    outputs - output nodes.
    special_nodes - power supplies and other useful but not necessary nodes.
    special_node_prob - Probability of having a special node in single instruction,
        can be a list or single number.
    """
    #Add the ground
    special = special_nodes[:]
    if '0' not in special:
        special.append('0')
    special.extend(range(1,inst_limit))
    if max(len(inputs),len(outputs)) > inst_limit:
        raise ValueError("Number of allowed nodes is too small.")
    special = special + inputs + outputs
    c = Chromosome(inst_limit,parts,special,extra_value=extra_value)

    #Check for input and outputs
    has_input = False
    has_output = False
    for e in c.elements:
        if any(i in e.nodes for i in inputs):
            has_input = True
        if any(o in e.nodes for o in outputs):
            has_output = True
    if not has_input:
        c.elements[0].nodes[0] = random.choice(inputs)
        random.shuffle(c.elements[0].nodes)
    if not has_output:
        c.elements[-1].nodes[0] = random.choice(outputs)
        random.shuffle(c.elements[-1].nodes)
    return c


def parse_circuit(circuit, inst_limit, parts, sigma, inputs, outputs, special_nodes, special_node_prob, extra_value=None):
    devices = []
    special = special_nodes[:]
    if '0' not in special:
        special.append('0')
    if max(len(inputs),len(outputs)) > inst_limit:
        raise ValueError("Number of allowed nodes is too small.")
    special = special + inputs + outputs
    #Devices starting with same substring are sorted longest
    #first to check longest possible device names first
    sorted_dev = sorted(parts.keys(),reverse=True)
    nodes = {}
    len_nodes = 1
    for n,line in enumerate(circuit.splitlines()):
        if not line:
            #Ignores empty lines
            continue

        #Current device fields
        d_spice = []
        #Try all the devices
        for dev in sorted_dev:
            if line.startswith(dev):
                #Found matching device from parts list
                line = line.split()
                d_nodes = line[1:parts[dev]['nodes']+1]
                for node in d_nodes:
                    if node not in special and node not in nodes:
                        nodes[node] =len_nodes
                        len_nodes += 1
                d_nodes = [nodes[node] if node in nodes else node for node in d_nodes]
                d_spice = line[parts[dev]['nodes']+1:]
                for e in xrange(len(d_spice)):
                    #Correct types and change SPICE multipliers to bare numbers.
                    try:
                        d_spice[e] = multipliers(d_spice[e])
                    except:
                        #Not a number.
                        pass
                devices.append(Device(dev,d_nodes,0,d_spice))
                break

        else:
            #Device not found
            print "Couldn't find device in line {}:{}\nIgnoring this line".format(n,line)
    #def __init__(self,max_parts,parts_list,nodes,extra_value=None):
    special.extend(map(str,range(1,inst_limit)))
    circuit = Chromosome(inst_limit, parts, special, extra_value)
    circuit.elements = devices
    return circuit

#parts = { 'R':{'value':(1,1e6),'nodes':2}, 'C':{'value':(1e-12,1e-3),'nodes':2}, 'Q':{'model':('2N3904','2N3906'),'kwvalues':{'w':(1e-7,1e-5),'l':(1e-7,1e-5)},'nodes':3} }
##r = Device('R',100,None,None,0)
##c = Device('C',1e-5,None,None,0)
##q = Device('Q',None,{'w':1,'l':2},'2N3904',0)
#c = random_circuit(parts, 10, 2, ['in1','in2'],['out'], ['vc','vd'], [0.1,0.1],extra_value=[(0,5)])
#print c
#c.mutate()
#print
#print c
#print c.value_bounds()
#d = c.get_values()
#print d
#c.set_values(d)
#print c
#print c.extra_value

########NEW FILE########
__FILENAME__ = circuits
import subprocess
import threading


class spice_thread(threading.Thread):
    def __init__(self, spice_in):
        threading.Thread.__init__(self)
        self.spice_in = spice_in
        self.result = None
        if self.spice_in!=None:
            self.spice = subprocess.Popen(['ngspice','-n'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def run(self):
        if self.spice_in!=None:
            output = self.spice.communicate(self.spice_in)
            self.result = (output[1],self.parse_output(output[0]))

    def parse_output(self,output):
        value={}
        output=output.split('\n')
        index=1
        current = ()
        for line in xrange(len(output)):
            temp=output[line].replace(',','').split()
            if len(temp)>0:
                if temp[0]=='Index':
                    if line+2<len(output):
                        temp2=output[line+2].replace(',','').split()
                        if float(temp2[0])<index:
                            current = temp[2]
                            value[temp[2]]=([],[])
                            index=0

            if len(temp)>2 and current!=():
                try:
                    float(temp[1]),float(temp[2])
                except:
                    continue
                index+=1
                value[current][0].append(float(temp[1]))
                value[current][1].append(float(temp[2]))
        return value

########NEW FILE########
__FILENAME__ = getch
class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()


########NEW FILE########
__FILENAME__ = diff_evolve
import random
#Differential evolution optimizer based on Scipy implementation:
#http://python-scipy.sourcearchive.com/documentation/0.6.0/classscipy_1_1sandbox_1_1rkern_1_1diffev_1_1DiffEvolver.html

def argmin(x):
    if len(x) < 2:
        return x[0]
    bestv,idx = x[0],0
    for e,i in enumerate(x[1:],1):
        if i<bestv:
            bestv = i
            idx = e
    return idx

class DiffEvolver(object):
    """Minimize a function using differential evolution.

    Constructors
    ------------
    DiffEvolver(func, pop0, args=(), crossover_rate=0.5, scale=None,
        strategy=('rand', 2, 'bin'), eps=1e-6)
      func -- function to minimize
      pop0 -- sequence of initial vectors
      args -- additional arguments to apply to func
      crossover_rate -- crossover probability [0..1] usually 0.5 or so
      scale -- scaling factor to apply to differences [0..1] usually > 0.5
        if None, then calculated from pop0 using a heuristic
      strategy -- tuple specifying the differencing/crossover strategy
        The first element is one of 'rand', 'best', 'rand-to-best' to specify
        how to obtain an initial trial vector.
        The second element is either 1 or 2 (or only 1 for 'rand-to-best') to
        specify the number of difference vectors to add to the initial trial.
        The third element is (currently) 'bin' to specify binomial crossover.
      eps -- if the maximum and minimum function values of a given generation are
        with eps of each other, convergence has been achieved.

    DiffEvolver.frombounds(func, lbound, ubound, npop, crossover_rate=0.5,
        scale=None, strategy=('rand', 2, 'bin'), eps=1e-6)
      Randomly initialize the population within given rectangular bounds.
      lbound -- lower bound vector
      ubound -- upper bound vector
      npop -- size of population

    Public Methods
    --------------
    solve(newgens=100)
      Run the minimizer for newgens more generations. Return the best parameter
      vector from the whole run.

    Public Members
    --------------
    best_value -- lowest function value in the history
    best_vector -- minimizing vector
    best_val_history -- list of best_value's for each generation
    best_vec_history -- list of best_vector's for each generation
    population -- current population
    pop_values -- respective function values for each of the current population
    generations -- number of generations already computed
    func, args, crossover_rate, scale, strategy, eps -- from constructor
    """

    def __init__(self, func, pop0, args=(), crossover_rate=0.5, scale=None,
            strategy=('rand', 2, 'bin'), eps=1e-6, lbound=None, ubound=None):
        self.func = func
        self.population = pop0
        self.npop, self.ndim = len(self.population),len(self.population[0])
        self.args = args
        self.crossover_rate = crossover_rate
        self.strategy = strategy
        self.eps = eps
        self.lbound = lbound
        self.ubound = ubound
        self.bounds = lbound!=None and ubound!=None

        self.pop_values = [self.func(m, *args) for m in self.population]
        bestidx = argmin(self.pop_values)
        self.best_vector = self.population[bestidx]
        self.best_value = self.pop_values[bestidx]

        if scale is None:
            self.scale = self.calculate_scale()
        else:
            self.scale = scale

        self.generations = 0
        self.best_val_history = []
        self.best_vec_history = []

        self.jump_table = {
            ('rand', 1, 'bin'): (self.choose_rand, self.diff1, self.bin_crossover),
            ('rand', 2, 'bin'): (self.choose_rand, self.diff2, self.bin_crossover),
            ('best', 1, 'bin'): (self.choose_best, self.diff1, self.bin_crossover),
            ('best', 2, 'bin'): (self.choose_best, self.diff2, self.bin_crossover),
            ('rand-to-best', 1, 'bin'):
                (self.choose_rand_to_best, self.diff1, self.bin_crossover),
            }

    def clear(self):
        self.best_val_history = []
        self.best_vec_history = []
        self.generations = 0
        self.pop_values = [self.func(m, *self.args) for m in self.population]

    def frombounds(cls, func, lbound, ubound, npop, crossover_rate=0.5,
            scale=None, x0=None, strategy=('rand', 2, 'bin'), eps=1e-6):
        if x0==None:
            pop0 = [[random.random()*(ubound[i]-lbound[i]) + lbound[i] for i in xrange(len(lbound))] for c in xrange(npop)]
        else:
            pop0 = [0]*npop
            for e,x in enumerate(x0):
                if len(x)!=len(lbound):
                    raise ValueError("Dimension of x0[{}] is incorrect".format(e))
                if any(not lbound[i]<=x[i]<=ubound[i] for i in xrange(len(lbound))):
                    raise ValueError("x0[{}] not inside the bounds.".format(e))
                for i in xrange(e,npop,len(x0)):
                    pop0[i] = x
            delta = 0.3
            pop0 = [[delta*(random.random()*(ubound[i]-lbound[i]) + lbound[i])+p[i] for i in xrange(len(lbound))] for p in pop0]
            pop0 = [[lbound[i] if p[i]<lbound[i] else (ubound[i] if p[i]>ubound[i] else p[i]) for i in xrange(len(lbound))] for p in pop0]
            #Make sure to include x0
            pop0[:len(x0)] = x0
        return cls(func, pop0, crossover_rate=crossover_rate, scale=scale,
            strategy=strategy, eps=eps, lbound=lbound, ubound=ubound)
    frombounds = classmethod(frombounds)

    def calculate_scale(self):
        rat = abs(max(self.pop_values)/self.best_value)
        rat = min(rat, 1./rat)
        return max(0.3, 1.-rat)

    def bin_crossover(self, oldgene, newgene):
        new = oldgene[:]
        for i in xrange(len(oldgene)):
            if random.random() < self.crossover_rate:
                new[i] = newgene[i]
        return new

    def select_samples(self, candidate, nsamples):
        possibilities = range(self.npop)
        possibilities.remove(candidate)
        random.shuffle(possibilities)
        return possibilities[:nsamples]

    def diff1(self, candidate):
        i1, i2 = self.select_samples(candidate, 2)
        y = [(self.population[i1][c] - self.population[i2][c]) for c in xrange(self.ndim)]
        y = [self.scale*i for i in y]
        return y

    def diff2(self, candidate):
        i1, i2, i3, i4 = self.select_samples(candidate, 4)
        y = ([(self.population[i1][c] - self.population[i2][c]+self.population[i3][c] - self.population[i4][c]) for c in xrange(self.ndim)])
        y = [self.scale*i for i in y]
        return y

    def choose_best(self, candidate):
        return self.best_vector

    def choose_rand(self, candidate):
        i = self.select_samples(candidate, 1)[0]
        return self.population[i]

    def choose_rand_to_best(self, candidate):
        return ((1-self.scale) * self.population[candidate] +
                self.scale * self.best_vector)

    def get_trial(self, candidate):
        chooser, differ, crosser = self.jump_table[self.strategy]
        chosen = chooser(candidate)
        diffed = differ(candidate)
        new = [chosen[i] + diffed[i] for i in xrange(self.ndim)]
        trial = crosser(self.population[candidate],new)
        if self.bounds:
            if random.random() < 0.2:
                trial = self.hug_bounds(trial)
            else:
                trial = self.mirror_bounds(trial)
        return trial

    def mirror_bounds(self,trial):
        """Mirrors values over bounds back to bounded area,
        or randomly generates a new coordinate if mirroring failed."""
        for i in xrange(self.ndim):
            if trial[i]<self.lbound[i]:
                trial[i] = 2*self.lbound[i]-trial[i]
                if trial[i]<self.lbound[i]:
                    trial[i] = random.random()*(self.ubound[i]-self.lbound[i]) + self.lbound[i]
            elif trial[i]>self.ubound[i]:
                trial[i] = 2*self.ubound[i]-trial[i]
                if trial[i]>self.ubound[i]:
                    trial[i] = random.random()*(self.ubound[i]-self.lbound[i]) + self.lbound[i]
        return trial

    def hug_bounds(self,trial):
        """Rounds values over bounds to bounds"""
        for i in xrange(self.ndim):
            if trial[i]<self.lbound[i]:
                trial[i] = self.lbound[i]
            elif trial[i]>self.ubound[i]:
                trial[i] = self.ubound[i]
        return trial

    def converged(self):
        return max(self.pop_values) - min(self.pop_values) <= self.eps

    def solve(self, newgens=100):
        """Run for newgens more generations.

        Return best parameter vector from the entire run.
        """
        for gen in xrange(self.generations+1, self.generations+newgens+1):
            for candidate in range(self.npop):
                trial = self.get_trial(candidate)
                trial_value = self.func(trial, *self.args)
                if trial_value < self.pop_values[candidate]:
                    self.population[candidate] = trial
                    self.pop_values[candidate] = trial_value
                    if trial_value < self.best_value:
                        self.best_vector = trial
                        self.best_value = trial_value
            self.best_val_history.append(self.best_value)
            self.best_vec_history.append(self.best_vector)
            if self.converged():
                break
        self.generations = gen
        return self.best_vector

########NEW FILE########
__FILENAME__ = plotting
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from os.path import join as path_join
from time import strftime

def save_plot(v,k,goal_val,sim_type,generation,score,output_path,plot_title=None,yrange=None,log_plot=False,constraints=None,name=''):
    #For every measurement in results
    plt.figure()
    freq = v[0]
    gain = v[1]
    if log_plot:#Logarithmic plot
        plt.semilogx(freq,gain,'g',basex=10)
        plt.semilogx(freq,goal_val,'b',basex=10)
        #if self.plot_weight:
        #    plt.semilogx(freq,weight_val,'r--',basex=10)
        if constraints!=None:
            plt.plot(*zip(*constraints), marker='.', color='r', ls='')
    else:
        plt.plot(freq,gain,'g')
        plt.plot(freq,goal_val,'b')
        #if self.plot_weight:
        #    plt.plot(freq,weight_val,'r--')
        if constraints!=None:
            plt.plot(*zip(*constraints), marker='.', color='r', ls='')

    # update axis ranges
    ax = []
    ax[0:4] = plt.axis()
    # check if we were given a frequency range for the plot
    if yrange!=None:
        plt.axis([min(freq),max(freq),yrange[0],yrange[1]])
    else:
        plt.axis([min(freq),max(freq),min(-0.5,-0.5+min(goal_val)),max(1.5,0.5+max(goal_val))])

    if sim_type=='dc':
        plt.xlabel("Input (V)")
    if sim_type=='ac':
        plt.xlabel("Input (Hz)")
    if sim_type=='tran':
        plt.xlabel("Time (s)")

    if plot_title!=None:
        plt.title(plot_title)
    else:
        plt.title(k)

    plt.annotate('Generation '+str(generation),xy=(0.05,0.95),xycoords='figure fraction')
    if score!=None:
        plt.annotate('Score '+'{0:.2f}'.format(score),xy=(0.75,0.95),xycoords='figure fraction')
    plt.grid(True)
    # turn on the minor gridlines to give that awesome log-scaled look
    plt.grid(True,which='minor')
    if len(k)>=3 and k[1:3] == 'db':
        plt.ylabel("Output (dB)")
    elif k[0]=='v':
        plt.ylabel("Output (V)")
    elif k[0]=='i':
        plt.ylabel("Output (A)")

    plt.savefig(path_join(output_path,strftime("%Y-%m-%d %H:%M:%S")+'-'+k+'-'+str(name)+'.png'))

data = input()
save_plot(*data)

########NEW FILE########
__FILENAME__ = inverter
title = 'Inverter'

#Put SPICE device models used in the simulations here.
models="""
.model 2N3906  PNP(Is=455.9E-18 Xti=3 Eg=1.11 Vaf=33.6 Bf=204 Ise=7.558f
+               Ne=1.536 Ikf=.3287 Nk=.9957 Xtb=1.5 Var=100 Br=3.72
+               Isc=529.3E-18 Nc=15.51 Ikr=11.1 Rc=.8508 Cjc=10.13p Mjc=.6993
+               Vjc=1.006 Fc=.5 Cje=10.39p Mje=.6931 Vje=.9937 Tr=10n Tf=181.2p
+               Itf=4.881m Xtf=.7939 Vtf=10 Rb=10, level=1)
.model 2N3904   NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.7 Ne=1.259
+               Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+               Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+               Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10, level=1)
"""

#This is for constructions common for every simulation
common="""
rin na in 10
vc vc 0 5
rload out 0 10k
cload out 0 100p
"""

#List of simulations
#Put SPICE simulation options between.control and .endc lines
spice_commands=[
"""
.control
dc Vin 0 5 0.05
print v(out)
print i(Vin)
print i(vc)
.endc
Vin na 0 0
""",
"""
.control
tran 2n 800n
print v(out)
print i(vin)
print i(vc)
.endc
Vin na 0 PULSE(0 5 10n 1n 1n 1 1)
""",
"""
.control
tran 2n 800n
print v(out)
print i(vin)
print i(vc)
.endc
Vin na 0 PULSE(5 0 10n 1n 1n 1 1)
"""
]

inputs = ['in']
outputs = ['out']
#Power supply node
special_nodes = ['vc']

#Dictionary of the availabe parts
parts = {'R':{'nodes':2,'value':(0.1,1e5)},#Resistors
         #'C':{'nodes':2,'value':1,'min':1e-13,'max':1e-9},#Capacitors
         #'L':{'nodes':2,'value':1,'min':1e-9,'max':1e-3},#No inductors allowed
         'Q':{'nodes':3,'model':('2N3904','2N3906')},#NPN transistors
         }

#Names starting with underscore are not loaded
def _goalinv(f,k,**kwargs):
    """k is the name of measurement. eq. v(out)"""
    #This is the DC transfer curve goal function
    if k=='v(out)':
        #kwargs['extra'][0] is the transition voltage
        return 5 if f<=kwargs['extra'][0] else 0
    elif k[0]=='i':
        #Goal for current use is 0
        return 0

def _transient_goal_inv(f,k,**kwargs):
    #Goal for first transient simulation
    n = 10**(-9)
    if k[0]=='v':
        if f<=10*n:
            return 5
        elif 20*n<f:
            return 0
    return 0#For current

def _transient_goal_inv2(f,k,**kwargs):
    #Second transient simulation
    n = 10**(-9)
    if k[0]=='v':
        if f<=10*n:
            return 0
        elif 20*n<f:
            return 5
    return 0

def _constraint0(f,x,k,**kwargs):
    #Constraint for static current consumption
    if k[0]=='v':
        if f<=kwargs['extra'][0]-0.2:
            return x>kwargs['extra'][0]+0.2
        elif f>=kwargs['extra'][0]+0.2:
            return x<kwargs['extra'][0]-0.2
    if k[0]=='i':
        #Limits current taken and going into the logic input to 2mA
        #Currents taken from the supply are negative and currents going into to
        #the supply are positive
        return abs(x)<5e-3+0.1/kwargs['generation']**0.5
    return True

def _constraint1(f,x,k,**kwargs):
    """f is input, x is output, k is measurement, extra is extra value of chromosome"""
    #Constraint for the first transient simulation
    if k[0]=='v' and f<9e-9:
        #Output should be 0.2V above the transition voltage at t=0
        return x>kwargs['extra'][0]+0.2
    if k[0]=='v' and f>350e-9:
        #And below it after the transition on the input
        return x<kwargs['extra'][0]-0.2
    if k[0]=='i':
        #Goal for current use
        return abs(x)<10e-3+0.1/kwargs['generation']**0.5
    return True

def _constraint2(f,x,k,**kwargs):
    """f is input, x is output, k is measurement, extra is extra value of chromosome"""
    #Same as last one, but with other way around
    if k[0]=='v' and f<9e-9:
        return x<kwargs['extra'][0]-0.2
    if k[0]=='v' and f>350e-9:
        return x>kwargs['extra'][0]+0.2
    if k[0]=='i':
        return abs(x)<10e-3+0.1/kwargs['generation']**0.5
    return True

population=500#Too small population might not converge, but is faster to simulate
max_parts=10#Maximum number of parts

mutation_rate=0.70
crossover_rate=0.10

#Because constraint functions change every generation score might
#increase even when better circuit is found
plot_every_generation = True
fitness_function=[_goalinv,_transient_goal_inv,_transient_goal_inv2]
constraints=[_constraint0,_constraint1,_constraint2]
constraint_weight=[1000,1000,1000]
constraint_free_generations = 1
gradual_constraints = True
constraint_ramp = 30
fitness_weight=[{'v(out)':lambda f,**kwargs: 15 if (f<0.5 or f>4.5) else 0.1,'i(vc)':lambda f,**kwargs:kwargs['generation']*100,'i(vin)':lambda f,**kwargs:kwargs['generation']*100},{'v(out)':2,'i(vc)':lambda f,**kwargs:kwargs['generation']*100,'i(vin)':1000},{'v(out)':2,'i(vc)':lambda f,**kwargs:kwargs['generation']*100,'i(vin)':1000}]

extra_value=[(0.5,4.5)]#This is used as transition value

plot_titles=[{'v(out)':"DC sweep",'i(vc)':"Current from power supply",'i(vin)':'Current from logic input'},{'v(out)':'Step response'},{'v(out)':'Step response'}]
plot_yrange={'v(out)':(-0.5,5.5),'i(vin)':(-0.05,0.01),'i(vc)':(-0.05,0.01)}

########NEW FILE########
__FILENAME__ = lowpass
from math import log

title = 'Low-pass filter'

#List of simulations
#Put SPICE simulation options between.control and .endc lines
#
spice_commands=[
"""
.control
ac dec 30 10 1e5
print vdb(out)
option rshunt = 1e12
.endc
Vin in 0 ac 1
Rload out 0 {aunif(10k,500)}
cload out 0 100p
"""
]

inputs = ['in']
outputs = ['out']

#Dictionary of the availabe parts
parts = {'R':{'nodes':2,'value':(0.1,1e6),},
         'C':{'nodes':2,'value':(1e-12,1e-5)},
         'L':{'nodes':2,'value':(1e-9,1e-3)},
         }

def _fitness_function1(f,k,**kwargs):
    """k is the name of measurement. eq. v(out)"""
    if k[0]=='v':
        #-100dB/decade
        return -43.43*log(f)+300 if f>=1000 else 0
    elif k[0]=='i':
        #Goal for current use is 0
        return 0

def _constraint1(f,x,k,**kwargs):
    if k[0]=='v':
        if f>8000:
            return x <= -20
        if f>1000:
            return x<=0.5
        elif f<100:
            return -5<x<3
        else:
            return -2<x<1
    return True

#This circuit will be added to the first generation
#Circuit below scores poorly, because it fails to fulfill the constraints
seed = """
R1 in out 1k
C1 out 0 150n
"""

population=3000#Too small population might not converge, or converges to local minimum, but is faster to simulate
max_parts=8#Maximum number of parts

#Enabling this makes the program ignore constraints for few first generations.
#Which makes the program try to fit right side first ignoring the pass-band.
gradual_constraints = False
mutation_rate=0.75
crossover_rate=0.10
#selection_weight=1.5
fitness_function=[_fitness_function1,_fitness_function1]
fitness_weight=[{'vdb(out)':lambda x,**kwargs:100 if x<3e3 else 0.1}]
constraints=[_constraint1]
constraint_weight=[10000]
plot_yrange={'vdb(out)':(-120,20),'i(vin)':(-0.2,0.2),'i(vc)':(-0.2,0.2),'i(ve)':(-0.2,0.2),'v(out)':(-2,2)}

########NEW FILE########
__FILENAME__ = nand
#TTL NAND-gate optimization
#Very slow simulation and usually takes somewhere close to 30-40 generations
#to find a working gate
title = 'nand'

#Put SPICE device models used in the simulations here.
models="""
.model 2N3906  PNP(Is=455.9E-18 Xti=3 Eg=1.11 Vaf=33.6 Bf=204 Ise=7.558f
+               Ne=1.536 Ikf=.3287 Nk=.9957 Xtb=1.5 Var=100 Br=3.72
+               Isc=529.3E-18 Nc=15.51 Ikr=11.1 Rc=.8508 Cjc=10.13p Mjc=.6993
+               Vjc=1.006 Fc=.5 Cje=10.39p Mje=.6931 Vje=.9937 Tr=10n Tf=181.2p
+               Itf=4.881m Xtf=.7939 Vtf=10 Rb=10, level=1)
.model 2N3904   NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.7 Ne=1.259
+               Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+               Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+               Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10, level=1)
"""

#5V power supply with series resistance of 10 ohms.
#Bypass capacitor with series resistance of 0.1 ohms.
#10k ohm and 100pF of load
common="""
Vc na 0 5
Rc na vc 10
cv na nb 10n
rcv nb vc 100m
rload out 0 10k
cload out 0 100p
"""

inputs = ['in1','in2']
outputs = ['out']
special_nodes = ['vc']

#List of simulations
#Put SPICE simulation options between.control and .endc lines
spice_commands=[
#Functionality
"""
.control
tran 5n 100u
print v(out)
print i(vc)
print i(Vpwl1)
print i(Vpwl2)
.endc
Vpwl1 in1 0 0 PWL(0 0 20u 0 20.05u 5 40u 5 40.05u 0 50u 0 50.05u 5 60u 5 60.05u 0 70u 0 70.05u 5)
Vpwl2 in2 0 0 PWL(0 0 10u 0 10.05u 5 20u 5 20.05u 0 30u 0 30.05u 5 40u 5 40.05u 0 60u 0 60.05u 5)
""",
#Input isolation test 1
"""
.control
tran 10u 20u
print v(in1)
.endc
Vin in2 0 0 PWL(0 0 5u 0 15u 5 20u 5)
rin in1 0 100k
"""
,
#Input isolation test 2
"""
.control
tran 10u 20u
print v(in2)
.endc
Vin in1 0 0 PWL(0 0 5u 0 15u 5 20u 5)
rin in2 0 100k
"""

]

#Dictionary of the availabe parts
parts = {'R':{'nodes':2,'value':(1,1e6)},#Resistors
         #'C':{'nodes':2,'value':(1e-12,1e-7)},#Capacitors
         #'L':{'nodes':2,'value':(1e-10,1e-5)},#Inductors
         'Q':{'nodes':3,'model':('2N3904','2N3906')},#NPN/PNP transistors
         }

def _goal(f,k,**kwargs):
    """k is the name of measurement. eq. v(out)"""
    #Functionality
    if k=='v(out)':
        if (30.05e-6<f<40e-6) or (f>70.05e-6):
            return 0
        return kwargs['extra'][0]
    #Current
    elif k[0]=='i':
        #Goal for current use is 0
        return 0
    #Input isolation
    elif k in ('v(in1)','v(in2)'):
        return 0

def _constraint0(f,x,k,**kwargs):
    if k[0] == 'v':
        if (32e-6<f<38e-6) or (f>72e-6):
            return x<1
        if f<20e-6 or (45e-6<f<59e-6) or (65e-6<f<69e-6) or (22e-6<f<29e-6):
            return kwargs['extra'][0]+0.1>x>kwargs['extra'][0]-0.1
    return True

def _weight(x,**kwargs):
    """Weighting function for scoring"""
    #Low weight when glitches are allowed
    if abs(x-20e-6)<8e-6:
        return 0.004
    if abs(x-60e-6)<8e-6:
        return 0.004
    #High weight on the edges
    if 0<x-40e-6<5e-6:
        return 5.0
    if 0<x-70e-6<5e-6:
        return 5.0
    return 0.07

##TTL npn NAND-gate seed circuit
#seed="""
#R1 n4 vc 1k
#R2 out vc 1k
#Q11 n5 n4 in1 2N3904
#Q12 n5 n4 in2 2N3904
#Q13 out n5 0 2N3904
#"""
#seed_copies = 300

#Default timeout is too low
timeout=2.5
population=2000#Too small population might not converge, but is faster to simulate
max_parts=10#Maximum number of parts
elitism=1#Best circuit is copied straight to next generation, default setting
constraints = [_constraint0,None,None]

mutation_rate=0.70
crossover_rate=0.10

plot_every_generation = True
fitness_function=[_goal]*3
fitness_weight=[{'v(out)':_weight,'i(vc)':3000,'i(vpwl1)':1000,'i(vpwl2)':1000},{'v(in1)':0.05},{'v(in2)':0.05}]
#On state output voltage
extra_value=[(4.5,5.0)]

plot_yrange={'v(out)':(-0.5,5.5),'i(vin)':(-0.1,0.01),'i(vc)':(-0.1,0.01),'v(in1)':(-0.5,5.5),'v(in2)':(-0.5,5.5)}

########NEW FILE########
