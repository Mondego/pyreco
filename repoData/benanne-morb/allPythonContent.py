__FILENAME__ = example_advparams
import morb
from morb import rbms, stats, updaters, trainers, monitors, units, parameters

import theano
import theano.tensor as T

import numpy as np

import gzip, cPickle

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context
import time

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# load data
print ">> Loading dataset..."

f = gzip.open('datasets/mnist.pkl.gz','rb')
train_set, valid_set, test_set = cPickle.load(f)
f.close()

train_set_x, train_set_y = train_set
valid_set_x, valid_set_y = train_set
test_set_x, test_set_y = train_set


# TODO DEBUG
train_set_x = train_set_x[:10000]
valid_set_x = valid_set_x[:1000]


n_visible = train_set_x.shape[1]
n_hidden = 100


print ">> Constructing RBM..."

class AdvRBM(morb.base.RBM):
    def __init__(self, n_visible, n_hidden):
        super(AdvRBM, self).__init__()
        # data shape
        self.n_visible = n_visible
        self.n_hidden = n_hidden
        # units
        self.v = units.BinaryUnits(self, name='v') # visibles
        self.h = units.BinaryUnits(self, name='h') # hiddens
        # parameters
        self.W = parameters.AdvancedProdParameters(self, [self.v, self.h], [1,1], theano.shared(value = self._initial_W(), name='W'), name='W') # weights
        self.bv = parameters.AdvancedBiasParameters(self, self.v, 1, theano.shared(value = self._initial_bv(), name='bv'), name='bv') # visible bias
        self.bh = parameters.AdvancedBiasParameters(self, self.h, 1, theano.shared(value = self._initial_bh(), name='bh'), name='bh') # hidden bias
        
    def _initial_W(self):
        return np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   high  =  4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   size  =  (self.n_visible, self.n_hidden)),
                   dtype =  theano.config.floatX)
        
    def _initial_bv(self):
        return np.zeros(self.n_visible, dtype = theano.config.floatX)
        
    def _initial_bh(self):
        return np.zeros(self.n_hidden, dtype = theano.config.floatX)
        







rbm = AdvRBM(n_visible, n_hidden)
# rbm = rbms.SigmoidBinaryRBM(n_visible, n_hidden)
initial_vmap = { rbm.v: T.matrix('v') }

# try to calculate weight updates using CD-1 stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=1, mean_field_for_gibbs=[rbm.v], mean_field_for_stats=[rbm.v])

umap = {}
for var in rbm.variables:
    pu =  var + 0.001 * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
m_data = s['data'][rbm.v]
m_model = s['model'][rbm.v]
e_data = rbm.energy(s['data']).mean()
e_model = rbm.energy(s['model']).mean()

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=100, monitors=[m, e_data, e_model], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=100, monitors=[m, m_data, m_model, e_data, e_model], name='evaluate', train=False, mode=mode)


def plot_data(d):
    plt.figure(5)
    plt.clf()
    plt.imshow(d.reshape((28,28)), interpolation='gaussian')
    plt.draw()


def sample_evolution(start, ns=100): # start = start data
    sample = t.compile_function(initial_vmap, mb_size=1, monitors=[m_model], name='evaluate', train=False, mode=mode)
    
    data = start
    plot_data(data)
    

    while True:
        for k in range(ns):
            for x in sample({ rbm.v: data }): # draw a new sample
                data = x[0]
            
        plot_data(data)
        









# TRAINING 

epochs = 200
print ">> Training for %d epochs..." % epochs

start_time = time.time()

mses_train_so_far = []
mses_valid_so_far = []
edata_train_so_far = []
emodel_train_so_far = []
edata_so_far = []
emodel_so_far = []

for epoch in range(epochs):
    monitoring_data_train = [(cost, energy_data, energy_model) for cost, energy_data, energy_model in train({ rbm.v: train_set_x })]
    mses_train, edata_train_list, emodel_train_list = zip(*monitoring_data_train)
    mse_train = np.mean(mses_train)
    edata_train = np.mean(edata_train_list)
    emodel_train = np.mean(emodel_train_list)
    
    monitoring_data = [(cost, data, model, energy_data, energy_model) for cost, data, model, energy_data, energy_model in evaluate({ rbm.v: valid_set_x })]
    mses_valid, vdata, vmodel, edata, emodel = zip(*monitoring_data)
    mse_valid = np.mean(mses_valid)
    edata_valid = np.mean(edata)
    emodel_valid = np.mean(emodel)
    
    # plotting
    mses_train_so_far.append(mse_train)
    mses_valid_so_far.append(mse_valid)
    edata_so_far.append(edata_valid)
    emodel_so_far.append(emodel_valid)
    edata_train_so_far.append(edata_train)
    emodel_train_so_far.append(emodel_train)
    
    plt.figure(1)
    plt.clf()
    plt.plot(mses_train_so_far, label='train')
    plt.plot(mses_valid_so_far, label='validation')
    plt.title("MSE")
    plt.legend()
    plt.draw()
    
    plt.figure(4)
    plt.clf()
    plt.plot(edata_so_far, label='validation / data')
    plt.plot(emodel_so_far, label='validation / model')
    plt.plot(edata_train_so_far, label='train / data')
    plt.plot(emodel_train_so_far, label='train / model')
    plt.title("energy")
    plt.legend()
    plt.draw()
    
    # plot some samples
    plt.figure(2)
    plt.clf()
    plt.imshow(vdata[0][0].reshape((28, 28)))
    plt.draw()
    plt.figure(3)
    plt.clf()
    plt.imshow(vmodel[0][0].reshape((28, 28)))
    plt.draw()

    
    print "Epoch %d" % epoch
    print "%.2f seconds" % (time.time() - start_time)
    print "training set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_train, edata_train, emodel_train)
    print "validation set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_valid, edata_valid, emodel_valid)





########NEW FILE########
__FILENAME__ = example_basic
import morb
from morb import rbms, stats, updaters, trainers, monitors

import theano
import theano.tensor as T

import numpy as np
import time

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context


# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None

# generate data
data = generate_data(200)

# use the predefined binary-binary RBM, which has visible units (rbm.v), hidden units (rbm.h),
# a weight matrix W connecting them (rbm.W), and visible and hidden biases (rbm.bv and rbm.bh).
n_visible = data.shape[1]
n_hidden = 100
rbm = rbms.BinaryBinaryRBM(n_visible, n_hidden)
initial_vmap = { rbm.v: T.matrix('v') }

# We use single-step contrastive divergence (CD-1) to train the RBM. For this, we can use
# the CDUpdater. This requires symbolic CD-1 statistics:
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=1, mean_field_for_gibbs=[rbm.v], mean_field_for_stats=[rbm.v, rbm.h])

# We create an updater for each parameter variable
umap = {}
for var in rbm.variables:
    pu = var + 0.001 * updaters.CDUpdater(rbm, var, s) # the learning rate is 0.001
    umap[var] = pu
 
# training
t = trainers.MinibatchTrainer(rbm, umap)
mse = monitors.reconstruction_mse(s, rbm.v)
train = t.compile_function(initial_vmap, mb_size=32, monitors=[mse], name='train', mode=mode)

epochs = 50

start_time = time.time()
for epoch in range(epochs):
    print "Epoch %d" % epoch
    costs = [m for m in train({ rbm.v: data })]
    print "MSE = %.4f" % np.mean(costs)

print "Took %.2f seconds" % (time.time() - start_time)

########NEW FILE########
__FILENAME__ = example_crbm
import morb
from morb import rbms, stats, updaters, trainers, monitors

import theano
import theano.tensor as T

import numpy as np

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# generate data
print ">> Generating dataset..."
data = generate_data(1000) # np.random.randint(2, size=(10000, n_visible))
data_context = get_context(data)

data_train = data[:-1000, :]
data_eval = data[-1000:, :]
data_context_train = data_context[:-1000, :]
data_context_eval = data_context[-1000:, :]

n_visible = data.shape[1]
n_context = data_context.shape[1]
n_hidden = 100


print ">> Constructing RBM..."
rbm = rbms.BinaryBinaryCRBM(n_visible, n_hidden, n_context)
initial_vmap = { rbm.v: T.matrix('v'), rbm.x: T.matrix('x') }

# try to calculate weight updates using CD-1 stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], context_units=[rbm.x], k=1)

umap = {}
for var in rbm.variables:
    pu = var + 0.0005 * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
mce = monitors.reconstruction_crossentropy(s, rbm.v)
free_energy = T.mean(rbm.free_energy([rbm.h], s['data'])) # take the mean over the minibatch.

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=32, monitors=[m, mce, free_energy], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=32, monitors=[m, mce, free_energy], train=False, name='evaluate', mode=mode)

epochs = 200
print ">> Training for %d epochs..." % epochs


for epoch in range(epochs):
    costs_train = [costs for costs in train({ rbm.v: data_train, rbm.x: data_context_train })]
    costs_eval = [costs for costs in evaluate({ rbm.v: data_eval, rbm.x: data_context_eval })]
    mses_train, ces_train, fes_train = zip(*costs_train)
    mses_eval, ces_eval, fes_eval = zip(*costs_eval)
    
    mse_train = np.mean(mses_train)
    ce_train = np.mean(ces_train)
    fe_train = np.mean(fes_train)
    mse_eval = np.mean(mses_eval)
    ce_eval = np.mean(ces_eval)
    fe_eval = np.mean(fes_eval)
    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, CE = %.6f, FE = %.2f" % (mse_train, ce_train, fe_train)
    print "validation set: MSE = %.6f, CE = %.6f, FE = %.2f" % (mse_eval, ce_eval, fe_eval)



########NEW FILE########
__FILENAME__ = example_factor
import morb
from morb import rbms, stats, updaters, trainers, monitors, units, parameters, factors

import theano
import theano.tensor as T

import numpy as np

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# generate data
print ">> Generating dataset..."
data = generate_data(1000) # np.random.randint(2, size=(10000, n_visible))
data_context = get_context(data, N=1) # keep the number of dimensions low

data_train = data[:-1000, :]
data_eval = data[-1000:, :]
data_context_train = data_context[:-1000, :]
data_context_eval = data_context[-1000:, :]

n_visible = data.shape[1]
n_context = data_context.shape[1]
n_hidden = 20
n_factors = 50

print ">> Constructing RBM..."
numpy_rng = np.random.RandomState(123)

def initial_W(n, f):
    return np.asarray(np.random.uniform(low=-4*np.sqrt(6./(n+f)), high=4*np.sqrt(6./(n+f)), size=(n, f)), dtype=theano.config.floatX)
initial_bv = np.zeros(n_visible, dtype = theano.config.floatX)
initial_bh = np.zeros(n_hidden, dtype = theano.config.floatX)



rbm = morb.base.RBM()
rbm.v = units.BinaryUnits(rbm, name='v') # visibles
rbm.h = units.BinaryUnits(rbm, name='h') # hiddens
rbm.x = units.Units(rbm, name='x') # context

Wv = theano.shared(value=initial_W(n_visible, n_factors), name='Wv')
Wh = theano.shared(value=initial_W(n_hidden, n_factors), name='Wh')
# Wx = theano.shared(value=initial_W(n_context, n_factors), name='Wx')
Wx = Wv # parameter tying

# rbm.W = parameters.ThirdOrderFactoredParameters(rbm, [rbm.v, rbm.h, rbm.x], [Wv, Wh, Wx], name='W') # weights
rbm.F = factors.Factor(rbm, name='F')
# IMPORTANT: the following parameters instances are associated with the FACTOR rbm.F, and not with the RBM itself.
rbm.Wv = parameters.ProdParameters(rbm.F, [rbm.v, rbm.F], Wv, name='Wv')
rbm.Wh = parameters.ProdParameters(rbm.F, [rbm.h, rbm.F], Wh, name='Wh')
rbm.Wx = parameters.ProdParameters(rbm.F, [rbm.x, rbm.F], Wx, name='Wx')

rbm.F.initialize() # done adding parameters to rbm.F

rbm.bv = parameters.BiasParameters(rbm, rbm.v, theano.shared(value = initial_bv, name='bv'), name='bv') # visible bias
rbm.bh = parameters.BiasParameters(rbm, rbm.h, theano.shared(value = initial_bh, name='bh'), name='bh') # hidden bias

initial_vmap = { rbm.v: T.matrix('v'), rbm.x: T.matrix('x') }

# try to calculate weight updates using CD-1 stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], context_units=[rbm.x], k=1, mean_field_for_gibbs=[rbm.v], mean_field_for_stats=[rbm.v])

umap = {}
for var in rbm.variables:
    pu = var + 0.0005 * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
mce = monitors.reconstruction_crossentropy(s, rbm.v)

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=32, monitors=[m, mce], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=32, monitors=[m, mce], train=False, name='evaluate', mode=mode)

epochs = 200
print ">> Training for %d epochs..." % epochs


for epoch in range(epochs):
    costs_train = [costs for costs in train({ rbm.v: data_train, rbm.x: data_context_train })]
    costs_eval = [costs for costs in evaluate({ rbm.v: data_eval, rbm.x: data_context_eval })]
    mses_train, ces_train = zip(*costs_train)
    mses_eval, ces_eval = zip(*costs_eval)
    
    mse_train = np.mean(mses_train)
    ce_train = np.mean(ces_train)
    mse_eval = np.mean(mses_eval)
    ce_eval = np.mean(ces_eval)
    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, CE = %.6f" % (mse_train, ce_train)
    print "validation set: MSE = %.6f, CE = %.6f" % (mse_eval, ce_eval)



########NEW FILE########
__FILENAME__ = example_fiotrbm
from morb import base, units, parameters, stats, param_updaters, trainers, monitors

# This example shows how the FIOTRBM model from "Facial Expression Transfer with
# Input-Output Temporal Restricted Boltzmann Machines" by Zeiler et al. (NIPS 
# 2011) can be recreated in Morb.

rbm = base.RBM()
rbm.v = units.GaussianUnits(rbm) # output (visibles)
rbm.h = units.BinaryUnits(rbm) # latent (hiddens)
rbm.s = units.Units(rbm) # input (context)
rbm.vp = units.Units(rbm) # output history (context)

initial_A = ...
initial_B = ...
initial_bv = ...
initial_bh = ...
initial_Wv = ...
initial_Wh = ...
initial_Ws = ...

parameters.FixedBiasParameters(rbm, rbm.v.precision_units) # add precision term to the energy function
rbm.A = parameters.ProdParameters(rbm, [rbm.vp, rbm.v], initial_A) # weights from past output to current output
rbm.B = parameters.ProdParameters(rbm, [rbm.vp, rbm.h], initial_B) # weights from past output to hiddens
rbm.bv = parameters.BiasParameters(rbm, rbm.v, initial_bv) # visible bias
rbm.bh = parameters.BiasParameters(rbm, rbm.h, initial_bh) # hidden bias
rbm.W = parameters.ThirdOrderFactoredParameters(rbm, [rbm.v, rbm.h, rbm.s], [initial_Wv, initial_Wh, initial_Ws]) # factored third order weights

########NEW FILE########
__FILENAME__ = example_free_energy
import morb
from morb import rbms, stats, updaters, trainers, monitors

import theano
import theano.tensor as T

import numpy as np
import time

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context


# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None

# generate data
data = generate_data(200)

# use the predefined binary-binary RBM, which has visible units (rbm.v), hidden units (rbm.h),
# a weight matrix W connecting them (rbm.W), and visible and hidden biases (rbm.bv and rbm.bh).
n_visible = data.shape[1]
n_hidden = 100
rbm = rbms.BinaryBinaryRBM(n_visible, n_hidden)
initial_vmap = { rbm.v: T.matrix('v') }

# We use single-step contrastive divergence (CD-1) to train the RBM. For this, we can use
# the CDParamUpdater. This requires symbolic CD-1 statistics:
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=1)

# We create an updater for each parameter variable
umap = {}
for var in rbm.variables:
    pu = var + 0.001 * updaters.CDUpdater(rbm, var, s) # the learning rate is 0.001
    umap[var] = pu
 
# training
t = trainers.MinibatchTrainer(rbm, umap)
mse = monitors.reconstruction_mse(s, rbm.v)
free_energy = T.mean(rbm.free_energy([rbm.h], s['data'])) # take the mean over the minibatch.
train = t.compile_function(initial_vmap, mb_size=32, monitors=[mse, free_energy], name='train', mode=mode)

epochs = 50

start_time = time.time()
for epoch in range(epochs):
    print "Epoch %d" % epoch
    costs = [(m, f) for m, f in train({ rbm.v: data })]
    mses, free_energies = zip(*costs)
    print "MSE = %.4f, avg free energy = %.2f" % (np.mean(mses), np.mean(free_energies))

print "Took %.2f seconds" % (time.time() - start_time)

########NEW FILE########
__FILENAME__ = example_gaussian
import morb
from morb import rbms, stats, updaters, trainers, monitors, units, parameters

import theano
import theano.tensor as T

import numpy as np
import time

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context


# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None

# generate data
data = generate_data(200)

# use the predefined binary-binary RBM, which has visible units (rbm.v), hidden units (rbm.h),
# a weight matrix W connecting them (rbm.W), and visible and hidden biases (rbm.bv and rbm.bh).
n_visible = data.shape[1]
n_hidden = 100

rbm = rbms.GaussianBinaryRBM(n_visible, n_hidden)

initial_vmap = { rbm.v: T.matrix('v') }

# We use single-step contrastive divergence (CD-1) to train the RBM. For this, we can use
# the CDParamUpdater. This requires symbolic CD-1 statistics:
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=1)

# We create an updater for each parameter variable
umap = {}
for var in rbm.variables:
    pu =  var + 0.001 * updaters.CDUpdater(rbm, var, s) # the learning rate is 0.001
    umap[var] = pu
 
# training
t = trainers.MinibatchTrainer(rbm, umap)
mse = monitors.reconstruction_mse(s, rbm.v)
train = t.compile_function(initial_vmap, mb_size=32, monitors=[mse], name='train', mode=mode)

epochs = 200

start_time = time.time()
for epoch in range(epochs):
    print "Epoch %d" % epoch
    costs = [m for m in train({ rbm.v: data })]
    print "MSE = %.4f" % np.mean(costs)

print "Took %.2f seconds" % (time.time() - start_time)

########NEW FILE########
__FILENAME__ = example_gaussian_learntprecision
import morb
from morb import rbms, stats, updaters, trainers, monitors

import theano
import theano.tensor as T

import numpy as np

import gzip, cPickle

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# load data
print ">> Loading dataset..."

f = gzip.open('datasets/mnist.pkl.gz','rb')
train_set, valid_set, test_set = cPickle.load(f)
f.close()

train_set_x, train_set_y = train_set
valid_set_x, valid_set_y = valid_set
test_set_x, test_set_y = test_set


# TODO DEBUG
train_set_x = train_set_x[:10000]
valid_set_x = valid_set_x[:1000]


n_visible = train_set_x.shape[1]
n_hidden = 100 # 500
# n_hidden_mean = 100
# n_hidden_precision = 100
mb_size = 20
k = 1 # 15
learning_rate = 0.01 # 0.1
epochs = 2000


print ">> Constructing RBM..."
rbm = rbms.LearntPrecisionGaussianBinaryRBM(n_visible, n_hidden)
# rbm = rbms.LearntPrecisionSeparateGaussianBinaryRBM(n_visible, n_hidden_mean, n_hidden_precision)
initial_vmap = { rbm.v: T.matrix('v') }

# try to calculate weight updates using CD stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=k)
# s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.hp, rbm.hm], k=k)

# We create an updater for each parameter variable.
# IMPORTANT: the precision parameters must be constrained to be negative.
variables = [rbm.Wm.var, rbm.bvm.var, rbm.bh.var, rbm.Wp.var, rbm.bvp.var]
# variables = [rbm.Wm.var, rbm.bvm.var, rbm.bhm.var, rbm.Wp.var, rbm.bvp.var, rbm.bhp.var]
precision_variables = [rbm.Wp.var, rbm.bvp.var]

umap = {}
for var in variables:
    pu = var + (learning_rate/mb_size) * updaters.CDUpdater(rbm, var, s) # the learning rate is 0.001
    if var in precision_variables:
        pu = updaters.BoundUpdater(pu, bound=0, type='upper')
    umap[var] = pu
    

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
m_data = s['data'][rbm.v]
m_model = s['model'][rbm.v]
e_data = rbm.energy(s['data']).mean()
e_model = rbm.energy(s['model']).mean()

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, e_data, e_model], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, m_data, m_model, e_data, e_model], name='evaluate', train=False, mode=mode)






def plot_data(d):
    plt.figure(5)
    plt.clf()
    plt.imshow(d.reshape((28,28)), interpolation='gaussian')
    plt.draw()


def sample_evolution(start, ns=100): # start = start data
    sample = t.compile_function(initial_vmap, mb_size=1, monitors=[m_model], name='evaluate', train=False, mode=mode)
    
    data = start
    plot_data(data)
    

    while True:
        for k in range(ns):
            for x in sample({ rbm.v: data }): # draw a new sample
                data = x[0]
            
        plot_data(data)
        









# TRAINING 

print ">> Training for %d epochs..." % epochs

mses_train_so_far = []
mses_valid_so_far = []
edata_train_so_far = []
emodel_train_so_far = []
edata_so_far = []
emodel_so_far = []

for epoch in range(epochs):
    monitoring_data_train = [(cost, energy_data, energy_model) for cost, energy_data, energy_model in train({ rbm.v: train_set_x })]
    mses_train, edata_train_list, emodel_train_list = zip(*monitoring_data_train)
    mse_train = np.mean(mses_train)
    edata_train = np.mean(edata_train_list)
    emodel_train = np.mean(emodel_train_list)
    
    monitoring_data = [(cost, data, model, energy_data, energy_model) for cost, data, model, energy_data, energy_model in evaluate({ rbm.v: valid_set_x })]
    mses_valid, vdata, vmodel, edata, emodel = zip(*monitoring_data)
    mse_valid = np.mean(mses_valid)
    edata_valid = np.mean(edata)
    emodel_valid = np.mean(emodel)
    
    # plotting
    mses_train_so_far.append(mse_train)
    mses_valid_so_far.append(mse_valid)
    edata_so_far.append(edata_valid)
    emodel_so_far.append(emodel_valid)
    edata_train_so_far.append(edata_train)
    emodel_train_so_far.append(emodel_train)
    
    plt.figure(1)
    plt.clf()
    plt.plot(mses_train_so_far, label='train')
    plt.plot(mses_valid_so_far, label='validation')
    plt.title("MSE")
    plt.legend()
    plt.draw()
    
    plt.figure(4)
    plt.clf()
    plt.plot(edata_so_far, label='validation / data')
    plt.plot(emodel_so_far, label='validation / model')
    plt.plot(edata_train_so_far, label='train / data')
    plt.plot(emodel_train_so_far, label='train / model')
    plt.title("energy")
    plt.legend()
    plt.draw()
    
    # plot some samples
    plt.figure(2)
    plt.clf()
    plt.imshow(vdata[0][0].reshape((28, 28)), vmin=0, vmax=1)
    plt.colorbar()
    plt.draw()
    plt.figure(3)
    plt.clf()
    plt.imshow(vmodel[0][0].reshape((28, 28)), vmin=0, vmax=1)
    plt.colorbar()
    plt.draw()

    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_train, edata_train, emodel_train)
    print "validation set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_valid, edata_valid, emodel_valid)





########NEW FILE########
__FILENAME__ = example_mnist
import morb
from morb import rbms, stats, updaters, trainers, monitors

import theano
import theano.tensor as T

import numpy as np

import gzip, cPickle

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# load data
print ">> Loading dataset..."

f = gzip.open('datasets/mnist.pkl.gz','rb')
train_set, valid_set, test_set = cPickle.load(f)
f.close()

train_set_x, train_set_y = train_set
valid_set_x, valid_set_y = valid_set
test_set_x, test_set_y = test_set


# TODO DEBUG
train_set_x = train_set_x[:10000]
valid_set_x = valid_set_x[:1000]


n_visible = train_set_x.shape[1]
n_hidden = 100 # 500
mb_size = 100
k = 1 # 15
learning_rate = 0.001 # 0.1
epochs = 1000


print ">> Constructing RBM..."
rbm = rbms.BinaryBinaryRBM(n_visible, n_hidden)
#rbm = rbms.TruncExpBinaryRBM(n_visible, n_hidden)
initial_vmap = { rbm.v: T.matrix('v') }

# try to calculate weight updates using CD stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=k, mean_field_for_stats=[rbm.v], mean_field_for_gibbs=[rbm.v])

umap = {}
for var in rbm.variables:
    pu = var + (learning_rate / float(mb_size)) * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
m_data = s['data'][rbm.v]
m_model = s['model'][rbm.v]
e_data = rbm.energy(s['data']).mean()
e_model = rbm.energy(s['model']).mean()

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, e_data, e_model], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, m_data, m_model, e_data, e_model], name='evaluate', train=False, mode=mode)






def plot_data(d):
    plt.figure(5)
    plt.clf()
    plt.imshow(d.reshape((28,28)), interpolation='gaussian')
    plt.draw()


def sample_evolution(start, ns=100): # start = start data
    sample = t.compile_function(initial_vmap, mb_size=1, monitors=[m_model], name='evaluate', train=False, mode=mode)
    
    data = start
    plot_data(data)
    

    while True:
        for k in range(ns):
            for x in sample({ rbm.v: data }): # draw a new sample
                data = x[0]
            
        plot_data(data)
        









# TRAINING 

print ">> Training for %d epochs..." % epochs

mses_train_so_far = []
mses_valid_so_far = []
edata_train_so_far = []
emodel_train_so_far = []
edata_so_far = []
emodel_so_far = []

for epoch in range(epochs):
    monitoring_data_train = [(cost, energy_data, energy_model) for cost, energy_data, energy_model in train({ rbm.v: train_set_x })]
    mses_train, edata_train_list, emodel_train_list = zip(*monitoring_data_train)
    mse_train = np.mean(mses_train)
    edata_train = np.mean(edata_train_list)
    emodel_train = np.mean(emodel_train_list)
    
    monitoring_data = [(cost, data, model, energy_data, energy_model) for cost, data, model, energy_data, energy_model in evaluate({ rbm.v: valid_set_x })]
    mses_valid, vdata, vmodel, edata, emodel = zip(*monitoring_data)
    mse_valid = np.mean(mses_valid)
    edata_valid = np.mean(edata)
    emodel_valid = np.mean(emodel)
    
    # plotting
    mses_train_so_far.append(mse_train)
    mses_valid_so_far.append(mse_valid)
    edata_so_far.append(edata_valid)
    emodel_so_far.append(emodel_valid)
    edata_train_so_far.append(edata_train)
    emodel_train_so_far.append(emodel_train)
    
    plt.figure(1)
    plt.clf()
    plt.plot(mses_train_so_far, label='train')
    plt.plot(mses_valid_so_far, label='validation')
    plt.title("MSE")
    plt.legend()
    plt.draw()
    
    plt.figure(4)
    plt.clf()
    plt.plot(edata_so_far, label='validation / data')
    plt.plot(emodel_so_far, label='validation / model')
    plt.plot(edata_train_so_far, label='train / data')
    plt.plot(emodel_train_so_far, label='train / model')
    plt.title("energy")
    plt.legend()
    plt.draw()
    
    # plot some samples
    plt.figure(2)
    plt.clf()
    plt.imshow(vdata[0][0].reshape((28, 28)))
    plt.draw()
    plt.figure(3)
    plt.clf()
    plt.imshow(vmodel[0][0].reshape((28, 28)))
    plt.draw()

    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_train, edata_train, emodel_train)
    print "validation set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_valid, edata_valid, emodel_valid)





########NEW FILE########
__FILENAME__ = example_mnist_autoenc
import morb
from morb import rbms, stats, updaters, trainers, monitors, objectives

import theano
import theano.tensor as T

import numpy as np

import gzip, cPickle

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context, visualise_filters

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# load data
print ">> Loading dataset..."

f = gzip.open('datasets/mnist.pkl.gz','rb')
train_set, valid_set, test_set = cPickle.load(f)
f.close()

train_set_x, train_set_y = train_set
valid_set_x, valid_set_y = valid_set
test_set_x, test_set_y = test_set


train_set_x = train_set_x[:10000]
valid_set_x = valid_set_x[:1000]


n_visible = train_set_x.shape[1]
n_hidden = 100 # 500
mb_size = 100
k = 1 # 15
learning_rate = 0.1 # 0.1 # 0.02 # 0.1
epochs = 500
corruption_level = 0.0 # 0.3
sparsity_penalty = 0.1 # 0.0
sparsity_target = 0.05


print ">> Constructing RBM..."
# rbm = rbms.GaussianBinaryRBM(n_visible, n_hidden)
rbm = rbms.BinaryBinaryRBM(n_visible, n_hidden)
# rbm = rbms.TruncExpBinaryRBM(n_visible, n_hidden)

v = T.matrix('v')
v_corrupted = objectives.corrupt_masking(v, corruption_level)
initial_vmap = { rbm.v: v }
initial_vmap_corrupted = { rbm.v: v_corrupted }

print ">> Constructing autoencoder updaters..."
autoencoder_objective = objectives.autoencoder(rbm, [rbm.v], [rbm.h], initial_vmap, initial_vmap_corrupted)
reconstruction = objectives.mean_reconstruction(rbm, [rbm.v], [rbm.h], initial_vmap_corrupted)

autoencoder_objective += sparsity_penalty * objectives.sparsity_penalty(rbm, [rbm.h], initial_vmap, sparsity_target)

umap = {}
for var in rbm.variables:
    pu = var + (learning_rate / float(mb_size)) * updaters.GradientUpdater(autoencoder_objective, var)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = T.mean((initial_vmap[rbm.v] - reconstruction[rbm.v]) ** 2)
c = T.mean(T.nnet.binary_crossentropy(reconstruction[rbm.v], initial_vmap[rbm.v]))

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[autoencoder_objective, m, c], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[autoencoder_objective, m, c], name='evaluate', train=False, mode=mode)






def plot_data(d, *args, **kwargs):
    plt.figure(5)
    plt.clf()
    plt.imshow(d.reshape((28,28)), interpolation='gaussian', *args, **kwargs)
    plt.draw()








# TRAINING 

print ">> Training for %d epochs..." % epochs

mses_train_so_far = []
mses_valid_so_far = []
objs_train_so_far = []
objs_valid_so_far = []
ces_train_so_far = []
ces_valid_so_far = []


for epoch in range(epochs):
    objs_train, mses_train, ces_train = zip(*train({ rbm.v: train_set_x }))
    mse_train = np.mean(mses_train)
    ce_train = np.mean(ces_train)
    obj_train = np.mean(objs_train)
    
    objs_valid, mses_valid, ces_valid = zip(*evaluate({ rbm.v: valid_set_x }))
    mse_valid = np.mean(mses_valid)
    ce_valid = np.mean(ces_valid)
    obj_valid = np.mean(objs_valid)
    
    # plotting
    mses_train_so_far.append(mse_train)
    mses_valid_so_far.append(mse_valid)
    objs_train_so_far.append(obj_train)
    objs_valid_so_far.append(obj_valid)
    ces_train_so_far.append(ce_train)
    ces_valid_so_far.append(ce_valid)
    
    plt.figure(1)
    plt.clf()
    plt.plot(mses_train_so_far, label='train')
    plt.plot(mses_valid_so_far, label='validation')
    plt.title("MSE")
    plt.legend()
    plt.draw()
    
    plt.figure(2)
    plt.clf()
    plt.plot(objs_train_so_far, label='train')
    plt.plot(objs_valid_so_far, label='validation')
    plt.title("objective")
    plt.legend()
    plt.draw()
    
    plt.figure(3)
    plt.clf()
    plt.plot(ces_train_so_far, label='train')
    plt.plot(ces_valid_so_far, label='validation')
    plt.title("cross-entropy")
    plt.legend()
    plt.draw()
    
    plt.figure(4)
    plt.clf()
    visualise_filters(rbm.W.var.get_value(), dim=28)
    plt.colorbar()
    plt.title("filters")
    plt.draw()
    
    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, CE = %.6f, objective = %.6f" % (mse_train, ce_train, obj_train)
    print "validation set: MSE = %.6f, CE = %.6f, objective = %.6f" % (mse_valid, ce_valid, obj_valid)





########NEW FILE########
__FILENAME__ = example_mnist_convolutional
import morb
from morb import rbms, stats, updaters, trainers, monitors, units, parameters

import theano
import theano.tensor as T

import numpy as np

import gzip, cPickle, time

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# load data
print ">> Loading dataset..."

f = gzip.open('datasets/mnist.pkl.gz','rb')
train_set, valid_set, test_set = cPickle.load(f)
f.close()

train_set_x, train_set_y = train_set
valid_set_x, valid_set_y = valid_set
test_set_x, test_set_y = test_set


# TODO DEBUG
train_set_x = train_set_x[:10000]
valid_set_x = valid_set_x[:1000]


# reshape data for convolutional RBM
train_set_x = train_set_x.reshape((train_set_x.shape[0], 1, 28, 28))
valid_set_x = valid_set_x.reshape((valid_set_x.shape[0], 1, 28, 28))
test_set_x = test_set_x.reshape((test_set_x.shape[0], 1, 28, 28))



visible_maps = 1
hidden_maps = 50 # 100 # 50
filter_height = 28 # 8
filter_width = 28 # 8
mb_size = 10 # 1



print ">> Constructing RBM..."
fan_in = visible_maps * filter_height * filter_width

"""
initial_W = numpy.asarray(
            self.numpy_rng.uniform(
                low = - numpy.sqrt(3./fan_in),
                high = numpy.sqrt(3./fan_in),
                size = self.filter_shape
            ), dtype=theano.config.floatX)
"""
numpy_rng = np.random.RandomState(123)
initial_W = np.asarray(
            numpy_rng.normal(
                0, 0.5 / np.sqrt(fan_in),
                size = (hidden_maps, visible_maps, filter_height, filter_width)
            ), dtype=theano.config.floatX)
initial_bv = np.zeros(visible_maps, dtype = theano.config.floatX)
initial_bh = np.zeros(hidden_maps, dtype = theano.config.floatX)



shape_info = {
  'hidden_maps': hidden_maps,
  'visible_maps': visible_maps,
  'filter_height': filter_height,
  'filter_width': filter_width,
  'visible_height': 28,
  'visible_width': 28,
  'mb_size': mb_size
}

# shape_info = None


# rbms.SigmoidBinaryRBM(n_visible, n_hidden)
rbm = morb.base.RBM()
rbm.v = units.BinaryUnits(rbm, name='v') # visibles
rbm.h = units.BinaryUnits(rbm, name='h') # hiddens
rbm.W = parameters.Convolutional2DParameters(rbm, [rbm.v, rbm.h], theano.shared(value=initial_W, name='W'), name='W', shape_info=shape_info)
# one bias per map (so shared across width and height):
rbm.bv = parameters.SharedBiasParameters(rbm, rbm.v, 3, 2, theano.shared(value=initial_bv, name='bv'), name='bv')
rbm.bh = parameters.SharedBiasParameters(rbm, rbm.h, 3, 2, theano.shared(value=initial_bh, name='bh'), name='bh')

initial_vmap = { rbm.v: T.tensor4('v') }

# try to calculate weight updates using CD-1 stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=1, mean_field_for_stats=[rbm.v], mean_field_for_gibbs=[rbm.v])

umap = {}
for var in rbm.variables:
    pu =  var + 0.001 * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
m_data = s['data'][rbm.v]
m_model = s['model'][rbm.v]
e_data = rbm.energy(s['data']).mean()
e_model = rbm.energy(s['model']).mean()


# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, e_data, e_model], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, m_data, m_model, e_data, e_model], name='evaluate', train=False, mode=mode)






def plot_data(d):
    plt.figure(5)
    plt.clf()
    plt.imshow(d.reshape((28,28)), interpolation='gaussian')
    plt.draw()


def sample_evolution(start, ns=100): # start = start data
    sample = t.compile_function(initial_vmap, mb_size=1, monitors=[m_model], name='evaluate', train=False, mode=mode)
    
    data = start
    plot_data(data)
    

    while True:
        for k in range(ns):
            for x in sample({ rbm.v: data }): # draw a new sample
                data = x[0]
            
        plot_data(data)
        









# TRAINING 

epochs = 200
print ">> Training for %d epochs..." % epochs

mses_train_so_far = []
mses_valid_so_far = []
edata_train_so_far = []
emodel_train_so_far = []
edata_so_far = []
emodel_so_far = []

start_time = time.time()

for epoch in range(epochs):
    monitoring_data_train = [(cost, energy_data, energy_model) for cost, energy_data, energy_model in train({ rbm.v: train_set_x })]
    mses_train, edata_train_list, emodel_train_list = zip(*monitoring_data_train)
    mse_train = np.mean(mses_train)
    edata_train = np.mean(edata_train_list)
    emodel_train = np.mean(emodel_train_list)
    
    monitoring_data = [(cost, data, model, energy_data, energy_model) for cost, data, model, energy_data, energy_model in evaluate({ rbm.v: valid_set_x })]
    mses_valid, vdata, vmodel, edata, emodel = zip(*monitoring_data)
    mse_valid = np.mean(mses_valid)
    edata_valid = np.mean(edata)
    emodel_valid = np.mean(emodel)
    
    # plotting
    mses_train_so_far.append(mse_train)
    mses_valid_so_far.append(mse_valid)
    edata_so_far.append(edata_valid)
    emodel_so_far.append(emodel_valid)
    edata_train_so_far.append(edata_train)
    emodel_train_so_far.append(emodel_train)
    
    plt.figure(1)
    plt.clf()
    plt.plot(mses_train_so_far, label='train')
    plt.plot(mses_valid_so_far, label='validation')
    plt.title("MSE")
    plt.legend()
    plt.draw()
    
    plt.figure(4)
    plt.clf()
    plt.plot(edata_so_far, label='validation / data')
    plt.plot(emodel_so_far, label='validation / model')
    plt.plot(edata_train_so_far, label='train / data')
    plt.plot(emodel_train_so_far, label='train / model')
    plt.title("energy")
    plt.legend()
    plt.draw()
    
    # plot some samples
    plt.figure(2)
    plt.clf()
    plt.imshow(vdata[0][0].reshape((28, 28)))
    plt.draw()
    plt.figure(3)
    plt.clf()
    plt.imshow(vmodel[0][0].reshape((28, 28)))
    plt.draw()

    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_train, edata_train, emodel_train)
    print "validation set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_valid, edata_valid, emodel_valid)
    print "Time: %.2f s" % (time.time() - start_time)





########NEW FILE########
__FILENAME__ = example_mnist_factor
import morb
from morb import base, units, parameters, stats, updaters, trainers, monitors, factors

import theano
import theano.tensor as T

import numpy as np

import gzip, cPickle

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context

# DEBUGGING

from theano import ProfileMode
mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
# mode = None


# load data
print ">> Loading dataset..."

f = gzip.open('datasets/mnist.pkl.gz','rb')
train_set, valid_set, test_set = cPickle.load(f)
f.close()

train_set_x, train_set_y = train_set
valid_set_x, valid_set_y = valid_set
test_set_x, test_set_y = test_set


# TODO DEBUG
train_set_x = train_set_x[:10000]
valid_set_x = valid_set_x[:1000]


n_visible = train_set_x.shape[1]
n_hidden = 100
n_factors = 500
mb_size = 20
k = 1 # 15
learning_rate = 0.02 # 0.1
epochs = 15


print ">> Constructing RBM..."
class FactoredBinaryBinaryRBM(base.RBM):
    def __init__(self, n_visible, n_hidden, n_factors):
        super(FactoredBinaryBinaryRBM, self).__init__()
        # data shape
        self.n_visible = n_visible
        self.n_hidden = n_hidden
        self.n_factors = n_factors
        # units
        self.v = units.BinaryUnits(self, name='v') # visibles
        self.h = units.BinaryUnits(self, name='h') # hiddens
        # parameters
        Wv = theano.shared(value = self._initial_W(self.n_visible, self.n_factors), name='Wv')
        Wh = theano.shared(value = self._initial_W(self.n_hidden, self.n_factors), name='Wh')
        self.F = factors.Factor(self, name='F') # factor
        self.Wv = parameters.ProdParameters(self.F, [self.v, self.F], Wv, name='Wv')
        self.Wh = parameters.ProdParameters(self.F, [self.h, self.F], Wh, name='Wh')
        self.F.initialize()
        
        self.bv = parameters.BiasParameters(self, self.v, theano.shared(value = self._initial_bv(), name='bv'), name='bv') # visible bias
        self.bh = parameters.BiasParameters(self, self.h, theano.shared(value = self._initial_bh(), name='bh'), name='bh') # hidden bias
        
    def _initial_W(self, d1, d2):
        return np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(d1+d2)),
                   high  =  4*np.sqrt(6./(d1+d2)),
                   size  =  (d1, d2)),
                   dtype =  theano.config.floatX)
        
    def _initial_bv(self):
        return np.zeros(self.n_visible, dtype = theano.config.floatX)
        
    def _initial_bh(self):
        return np.zeros(self.n_hidden, dtype = theano.config.floatX)


rbm = FactoredBinaryBinaryRBM(n_visible, n_hidden, n_factors)
initial_vmap = { rbm.v: T.matrix('v') }

# try to calculate weight updates using CD stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=k, mean_field_for_stats=[rbm.v], mean_field_for_gibbs=[rbm.v])

umap = {}
for var in rbm.variables:
    pu = var + (learning_rate / float(mb_size)) * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
m_data = s['data'][rbm.v]
m_model = s['model'][rbm.v]
e_data = rbm.energy(s['data']).mean()
e_model = rbm.energy(s['model']).mean()

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, e_data, e_model], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, m_data, m_model, e_data, e_model], name='evaluate', train=False, mode=mode)






def plot_data(d):
    plt.figure(5)
    plt.clf()
    plt.imshow(d.reshape((28,28)), interpolation='gaussian')
    plt.draw()


def sample_evolution(start, ns=100): # start = start data
    sample = t.compile_function(initial_vmap, mb_size=1, monitors=[m_model], name='evaluate', train=False, mode=mode)
    
    data = start
    plot_data(data)
    

    while True:
        for k in range(ns):
            for x in sample({ rbm.v: data }): # draw a new sample
                data = x[0]
            
        plot_data(data)
        









# TRAINING 

print ">> Training for %d epochs..." % epochs

mses_train_so_far = []
mses_valid_so_far = []
edata_train_so_far = []
emodel_train_so_far = []
edata_so_far = []
emodel_so_far = []

for epoch in range(epochs):
    monitoring_data_train = [(cost, energy_data, energy_model) for cost, energy_data, energy_model in train({ rbm.v: train_set_x })]
    mses_train, edata_train_list, emodel_train_list = zip(*monitoring_data_train)
    mse_train = np.mean(mses_train)
    edata_train = np.mean(edata_train_list)
    emodel_train = np.mean(emodel_train_list)
    
    monitoring_data = [(cost, data, model, energy_data, energy_model) for cost, data, model, energy_data, energy_model in evaluate({ rbm.v: valid_set_x })]
    mses_valid, vdata, vmodel, edata, emodel = zip(*monitoring_data)
    mse_valid = np.mean(mses_valid)
    edata_valid = np.mean(edata)
    emodel_valid = np.mean(emodel)
    
    # plotting
    mses_train_so_far.append(mse_train)
    mses_valid_so_far.append(mse_valid)
    edata_so_far.append(edata_valid)
    emodel_so_far.append(emodel_valid)
    edata_train_so_far.append(edata_train)
    emodel_train_so_far.append(emodel_train)
    
    plt.figure(1)
    plt.clf()
    plt.plot(mses_train_so_far, label='train')
    plt.plot(mses_valid_so_far, label='validation')
    plt.title("MSE")
    plt.legend()
    plt.draw()
    
    plt.figure(4)
    plt.clf()
    plt.plot(edata_so_far, label='validation / data')
    plt.plot(emodel_so_far, label='validation / model')
    plt.plot(edata_train_so_far, label='train / data')
    plt.plot(emodel_train_so_far, label='train / model')
    plt.title("energy")
    plt.legend()
    plt.draw()
    
    # plot some samples
    plt.figure(2)
    plt.clf()
    plt.imshow(vdata[0][0].reshape((28, 28)))
    plt.draw()
    plt.figure(3)
    plt.clf()
    plt.imshow(vmodel[0][0].reshape((28, 28)))
    plt.draw()

    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_train, edata_train, emodel_train)
    print "validation set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_valid, edata_valid, emodel_valid)





########NEW FILE########
__FILENAME__ = example_mnist_labeled
import morb
from morb import rbms, stats, updaters, trainers, monitors, units, parameters

import theano
import theano.tensor as T

import numpy as np

import gzip, cPickle

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context, one_hot

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# load data
print ">> Loading dataset..."

f = gzip.open('datasets/mnist.pkl.gz','rb')
train_set, valid_set, test_set = cPickle.load(f)
f.close()

train_set_x, train_set_y = train_set
valid_set_x, valid_set_y = valid_set
test_set_x, test_set_y = test_set

# convert labels to one hot representation
train_set_y_oh = one_hot(np.atleast_2d(train_set_y).T)
valid_set_y_oh = one_hot(np.atleast_2d(valid_set_y).T)
test_set_y_oh = one_hot(np.atleast_2d(test_set_y).T)

# dim 0 = minibatches, dim 1 = units, dim 2 = states
train_set_y_oh = train_set_y_oh.reshape((train_set_y_oh.shape[0], 1, train_set_y_oh.shape[1]))
valid_set_y_oh = valid_set_y_oh.reshape((valid_set_y_oh.shape[0], 1, valid_set_y_oh.shape[1]))
test_set_y_oh = test_set_y_oh.reshape((test_set_y_oh.shape[0], 1, test_set_y_oh.shape[1]))


# make the sets a bit smaller for testing purposes
train_set_x = train_set_x[:10000]
train_set_y_oh = train_set_y_oh[:10000]
valid_set_x = valid_set_x[:1000]
valid_set_y_oh = valid_set_y_oh[:1000]




n_visible = train_set_x.shape[1]
n_hidden = 100
n_states = train_set_y_oh.shape[2]


print ">> Constructing RBM..."
rbm = rbms.BinaryBinaryRBM(n_visible, n_hidden)

# add softmax unit for context
rbm.s = units.SoftmaxUnits(rbm, name='s')

# link context and hiddens
initial_Ws = np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(n_hidden+1+n_states)),
                   high  =  4*np.sqrt(6./(n_hidden+1+n_states)),
                   size  =  (1, n_states, n_hidden)),
                   dtype =  theano.config.floatX)
rbm.Ws = parameters.AdvancedProdParameters(rbm, [rbm.s, rbm.h], [2, 1], theano.shared(value = initial_Ws, name='Ws'), name='Ws')

initial_vmap = { rbm.v: T.matrix('v'), rbm.s: T.tensor3('s') }

# try to calculate weight updates using CD-1 stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], context_units=[rbm.s], k=1, mean_field_for_stats=[rbm.v], mean_field_for_gibbs=[rbm.v])
# s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v, rbm.s], hidden_units=[rbm.h], k=1, mean_field_for_stats=[rbm.v], mean_field_for_gibbs=[rbm.v])

umap = {}
for var in rbm.variables:
    pu = var + 0.001 * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
m_data = s['data'][rbm.v]
m_model = s['model'][rbm.v]
e_data = rbm.energy(s['data']).mean()
e_model = rbm.energy(s['model']).mean()

train = t.compile_function(initial_vmap, mb_size=100, monitors=[m, e_data, e_model], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=100, monitors=[m, m_data, m_model, e_data, e_model], name='evaluate', train=False, mode=mode)






def plot_data(d):
    plt.figure(5)
    plt.clf()
    plt.imshow(d.reshape((28,28)), interpolation='gaussian')
    plt.draw()


def sample_evolution(start, cls, ns=100): # start = start data
    sample = t.compile_function(initial_vmap, mb_size=1, monitors=[m_model], name='evaluate', train=False, mode=mode)
    
    data = start
    plot_data(data)
    
    label = one_hot(np.atleast_2d(cls), dim=10)
    label = label.reshape((label.shape[0], 1, label.shape[1]))
    

    while True:
        for k in range(ns):
            for x in sample({ rbm.v: data, rbm.s: label }): # draw a new sample
                data = x[0]
            
        plot_data(data)
        









# TRAINING 

epochs = 200
print ">> Training for %d epochs..." % epochs

mses_train_so_far = []
mses_valid_so_far = []
edata_train_so_far = []
emodel_train_so_far = []
edata_so_far = []
emodel_so_far = []

for epoch in range(epochs):
    monitoring_data_train = [(cost, energy_data, energy_model) for cost, energy_data, energy_model in train({ rbm.v: train_set_x, rbm.s: train_set_y_oh })]
    mses_train, edata_train_list, emodel_train_list = zip(*monitoring_data_train)
    mse_train = np.mean(mses_train)
    edata_train = np.mean(edata_train_list)
    emodel_train = np.mean(emodel_train_list)
    
    monitoring_data = [(cost, data, model, energy_data, energy_model) for cost, data, model, energy_data, energy_model in evaluate({ rbm.v: valid_set_x, rbm.s: valid_set_y_oh })]
    mses_valid, vdata, vmodel, edata, emodel = zip(*monitoring_data)
    mse_valid = np.mean(mses_valid)
    edata_valid = np.mean(edata)
    emodel_valid = np.mean(emodel)
    
    # plotting
    mses_train_so_far.append(mse_train)
    mses_valid_so_far.append(mse_valid)
    edata_so_far.append(edata_valid)
    emodel_so_far.append(emodel_valid)
    edata_train_so_far.append(edata_train)
    emodel_train_so_far.append(emodel_train)
    
    plt.figure(1)
    plt.clf()
    plt.plot(mses_train_so_far, label='train')
    plt.plot(mses_valid_so_far, label='validation')
    plt.title("MSE")
    plt.legend()
    plt.draw()
    
    plt.figure(4)
    plt.clf()
    plt.plot(edata_so_far, label='validation / data')
    plt.plot(emodel_so_far, label='validation / model')
    plt.plot(edata_train_so_far, label='train / data')
    plt.plot(emodel_train_so_far, label='train / model')
    plt.title("energy")
    plt.legend()
    plt.draw()
    
    # plot some samples
    plt.figure(2)
    plt.clf()
    plt.imshow(vdata[0][0].reshape((28, 28)))
    plt.draw()
    plt.figure(3)
    plt.clf()
    plt.imshow(vmodel[0][0].reshape((28, 28)))
    plt.draw()

    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_train, edata_train, emodel_train)
    print "validation set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_valid, edata_valid, emodel_valid)





########NEW FILE########
__FILENAME__ = example_mnist_persistent
import morb
from morb import rbms, stats, updaters, trainers, monitors

import theano
import theano.tensor as T

import numpy as np

import gzip, cPickle

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# load data
print ">> Loading dataset..."

f = gzip.open('datasets/mnist.pkl.gz','rb')
train_set, valid_set, test_set = cPickle.load(f)
f.close()

train_set_x, train_set_y = train_set
valid_set_x, valid_set_y = valid_set
test_set_x, test_set_y = test_set


# TODO DEBUG
# train_set_x = train_set_x[:10000]
valid_set_x = valid_set_x[:1000]


n_visible = train_set_x.shape[1]
n_hidden = 500
mb_size = 20
k = 15
learning_rate = 0.1
epochs = 15


print ">> Constructing RBM..."
rbm = rbms.BinaryBinaryRBM(n_visible, n_hidden)
initial_vmap = { rbm.v: T.matrix('v') }

persistent_vmap = { rbm.h: theano.shared(np.zeros((mb_size, n_hidden), dtype=theano.config.floatX)) }

# try to calculate weight updates using CD stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=k, persistent_vmap=persistent_vmap, mean_field_for_stats=[rbm.v], mean_field_for_gibbs=[rbm.v])

umap = {}
for var in rbm.variables:
    pu = var + (learning_rate / float(mb_size)) * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
m_data = s['data'][rbm.v]
m_model = s['model'][rbm.v]
e_data = rbm.energy(s['data']).mean()
e_model = rbm.energy(s['model']).mean()

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, e_data, e_model], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=mb_size, monitors=[m, m_data, m_model, e_data, e_model], name='evaluate', train=False, mode=mode)






def plot_data(d):
    plt.figure(5)
    plt.clf()
    plt.imshow(d.reshape((28,28)), interpolation='gaussian')
    plt.draw()


def sample_evolution(start, ns=100): # start = start data
    sample = t.compile_function(initial_vmap, mb_size=1, monitors=[m_model], name='evaluate', train=False, mode=mode)
    
    data = start
    plot_data(data)
    

    while True:
        for k in range(ns):
            for x in sample({ rbm.v: data }): # draw a new sample
                data = x[0]
            
        plot_data(data)
        









# TRAINING 

print ">> Training for %d epochs..." % epochs

mses_train_so_far = []
mses_valid_so_far = []
edata_train_so_far = []
emodel_train_so_far = []
edata_so_far = []
emodel_so_far = []

for epoch in range(epochs):
    monitoring_data_train = [(cost, energy_data, energy_model) for cost, energy_data, energy_model in train({ rbm.v: train_set_x })]
    mses_train, edata_train_list, emodel_train_list = zip(*monitoring_data_train)
    mse_train = np.mean(mses_train)
    edata_train = np.mean(edata_train_list)
    emodel_train = np.mean(emodel_train_list)
    
    monitoring_data = [(cost, data, model, energy_data, energy_model) for cost, data, model, energy_data, energy_model in evaluate({ rbm.v: valid_set_x })]
    mses_valid, vdata, vmodel, edata, emodel = zip(*monitoring_data)
    mse_valid = np.mean(mses_valid)
    edata_valid = np.mean(edata)
    emodel_valid = np.mean(emodel)
    
    # plotting
    mses_train_so_far.append(mse_train)
    mses_valid_so_far.append(mse_valid)
    edata_so_far.append(edata_valid)
    emodel_so_far.append(emodel_valid)
    edata_train_so_far.append(edata_train)
    emodel_train_so_far.append(emodel_train)
    
    plt.figure(1)
    plt.clf()
    plt.plot(mses_train_so_far, label='train')
    plt.plot(mses_valid_so_far, label='validation')
    plt.title("MSE")
    plt.legend()
    plt.draw()
    
    plt.figure(4)
    plt.clf()
    plt.plot(edata_so_far, label='validation / data')
    plt.plot(emodel_so_far, label='validation / model')
    plt.plot(edata_train_so_far, label='train / data')
    plt.plot(emodel_train_so_far, label='train / model')
    plt.title("energy")
    plt.legend()
    plt.draw()
    
    # plot some samples
    plt.figure(2)
    plt.clf()
    plt.imshow(vdata[0][0].reshape((28, 28)))
    plt.draw()
    plt.figure(3)
    plt.clf()
    plt.imshow(vmodel[0][0].reshape((28, 28)))
    plt.draw()

    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_train, edata_train, emodel_train)
    print "validation set: MSE = %.6f, data energy = %.2f, model energy = %.2f" % (mse_valid, edata_valid, emodel_valid)





########NEW FILE########
__FILENAME__ = example_momentum
import morb
from morb import rbms, stats, updaters, trainers, monitors

import theano
import theano.tensor as T

import numpy as np

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context


# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# generate data
data = generate_data(200) # np.random.randint(2, size=(10000, n_visible))

n_visible = data.shape[1]
n_hidden = 100


rbm = rbms.BinaryBinaryRBM(n_visible, n_hidden)
initial_vmap = { rbm.v: T.matrix('v') }

# try to calculate weight updates using CD-1 stats
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=1)

umap = {}

for var, shape in zip([rbm.W.var, rbm.bv.var, rbm.bh.var], [(rbm.n_visible, rbm.n_hidden), (rbm.n_visible,), (rbm.n_hidden,)]):
    # pu =  0.001 * (param_updaters.CDParamUpdater(params, sc) + 0.02 * param_updaters.DecayParamUpdater(params))
    pu = updaters.CDUpdater(rbm, var, s)
    pu = var + 0.0001 * updaters.MomentumUpdater(pu, 0.9, shape)
    umap[var] = pu
    

 
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)

epochs = 50

for epoch in range(epochs):
    print "Epoch %d" % epoch
    costs = [m for m in train({ rbm.v: data })]
    print "MSE = %.4f" % np.mean(costs)


########NEW FILE########
__FILENAME__ = example_sparsity
import morb
from morb import rbms, stats, updaters, trainers, monitors

import theano
import theano.tensor as T

import numpy as np

import gzip, cPickle

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context, plot_data

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# load data
print ">> Loading dataset..."

f = gzip.open('datasets/mnist.pkl.gz','rb')
train_set, valid_set, test_set = cPickle.load(f)
f.close()

train_set_x, train_set_y = train_set
valid_set_x, valid_set_y = valid_set
test_set_x, test_set_y = test_set


# TODO DEBUG
train_set_x = train_set_x[:1000]
valid_set_x = valid_set_x[:100]


n_visible = train_set_x.shape[1]
n_hidden = 100


print ">> Constructing RBM..."
rbm = rbms.BinaryBinaryRBM(n_visible, n_hidden)
initial_vmap = { rbm.v: T.matrix('v') }

# try to calculate weight updates using CD-1 stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=1, mean_field_for_stats=[rbm.v], mean_field_for_gibbs=[rbm.v])

sparsity_targets = { rbm.h: 0.1 }


eta = 0.001 # learning rate
sparsity_cost = 0.5

umap = {}

umap[rbm.W.var] = rbm.W.var + eta * updaters.CDUpdater(rbm, rbm.W.var, s) \
            + eta * sparsity_cost * updaters.SparsityUpdater(rbm, rbm.W.var, sparsity_targets, s)
umap[rbm.bh.var] = rbm.bh.var + eta * updaters.CDUpdater(rbm, rbm.bh.var, s) \
             + eta * sparsity_cost * updaters.SparsityUpdater(rbm, rbm.bh.var, sparsity_targets, s)
umap[rbm.bv.var] = rbm.bv.var + eta * updaters.CDUpdater(rbm, rbm.bv.var, s)



print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
m_model = s['model'][rbm.h]


# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=100, monitors=[m, m_model], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=100, monitors=[m, m_model], name='evaluate', train=False, mode=mode)




def sample_evolution(start, ns=100): # start = start data
    sample = t.compile_function(initial_vmap, mb_size=1, monitors=[m_model], name='evaluate', train=False, mode=mode)
    
    data = start
    plot_data(data)
    

    while True:
        for k in range(ns):
            for x in sample({ rbm.v: data }): # draw a new sample
                data = x[0]
            
        plot_data(data)
        







# TRAINING 

epochs = 200
print ">> Training for %d epochs..." % epochs

mses_train_so_far = []
mses_valid_so_far = []
mact_train_so_far = []
mact_valid_so_far = []

for epoch in range(epochs):
    monitoring_data_train = [(cost, m_model) for cost, m_model in train({ rbm.v: train_set_x })]
    mses_train, m_model_train_list = zip(*monitoring_data_train)
    mse_train = np.mean(mses_train)
    mean_activation_train = np.mean([np.mean(m) for m in m_model_train_list])
    
    monitoring_data = [(cost, m_model) for cost, m_model in evaluate({ rbm.v: valid_set_x })]
    mses_valid, m_model_valid_list = zip(*monitoring_data)
    mse_valid = np.mean(mses_valid)
    mean_activation_valid = np.mean([np.mean(m) for m in m_model_valid_list])
    
    # plotting
    mses_train_so_far.append(mse_train)
    mses_valid_so_far.append(mse_valid)
    mact_train_so_far.append(mean_activation_train)
    mact_valid_so_far.append(mean_activation_valid)
    
    plt.figure(1)
    plt.clf()
    plt.plot(mses_train_so_far, label='train')
    plt.plot(mses_valid_so_far, label='validation')
    plt.title("MSE")
    plt.legend()
    plt.draw()
    
    plt.figure(4)
    plt.clf()
    plt.plot(mact_train_so_far, label='train')
    plt.plot(mact_valid_so_far, label='validation')
    plt.title("Mean activation of hiddens")
    plt.legend()
    plt.draw()
    
    """
    # plot some samples
    plt.figure(2)
    plt.clf()
    plt.imshow(vdata[0][0].reshape((28, 28)))
    plt.draw()
    plt.figure(3)
    plt.clf()
    plt.imshow(vmodel[0][0].reshape((28, 28)))
    plt.draw()
    """

    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, mean hidden activation = %.6f" % (mse_train, mean_activation_train)
    print "validation set: MSE = %.6f, mean hidden activation = %.6f" % (mse_valid, mean_activation_valid)





########NEW FILE########
__FILENAME__ = example_texp
import morb
from morb import rbms, stats, updaters, trainers, monitors, units, parameters

import theano
import theano.tensor as T

import numpy as np
import time

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context


# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None

# generate data
data = generate_data(200)

n_visible = data.shape[1]
n_hidden = 100

class TexpBinaryRBM(morb.base.RBM):
    def __init__(self, n_visible, n_hidden):
        super(TexpBinaryRBM, self).__init__()
        # data shape
        self.n_visible = n_visible
        self.n_hidden = n_hidden
        # units
        self.v = units.TruncatedExponentialUnits(self, name='v') # visibles
        self.h = units.BinaryUnits(self, name='h') # hiddens
        # parameters
        self.W = parameters.ProdParameters(self, [self.v, self.h], theano.shared(value = self._initial_W(), name='W'), name='W') # weights
        self.bv = parameters.BiasParameters(self, self.v, theano.shared(value = self._initial_bv(), name='bv'), name='bv') # visible bias
        self.bh = parameters.BiasParameters(self, self.h, theano.shared(value = self._initial_bh(), name='bh'), name='bh') # hidden bias
        
    def _initial_W(self):
        return np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   high  =  4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   size  =  (self.n_visible, self.n_hidden)),
                   dtype =  theano.config.floatX)
        
    def _initial_bv(self):
        return np.zeros(self.n_visible, dtype = theano.config.floatX)
        
    def _initial_bh(self):
        return np.zeros(self.n_hidden, dtype = theano.config.floatX)


rbm = TexpBinaryRBM(n_visible, n_hidden)

initial_vmap = { rbm.v: T.matrix('v') }

# We use single-step contrastive divergence (CD-1) to train the RBM. For this, we can use
# the CDParamUpdater. This requires symbolic CD-1 statistics:
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], k=1)

# We create an updater for each parameter variable
umap = {}
for var in rbm.variables:
    pu = var + 0.001 * updaters.CDUpdater(rbm, var, s) # the learning rate is 0.001
    umap[var] = pu
 
# training
t = trainers.MinibatchTrainer(rbm, umap)
mse = monitors.reconstruction_mse(s, rbm.v)
train = t.compile_function(initial_vmap, mb_size=32, monitors=[mse], name='train', mode=mode)

epochs = 200

start_time = time.time()
for epoch in range(epochs):
    print "Epoch %d" % epoch
    costs = [m for m in train({ rbm.v: data })]
    print "MSE = %.4f" % np.mean(costs)

print "Took %.2f seconds" % (time.time() - start_time)

########NEW FILE########
__FILENAME__ = example_thirdorder
import morb
from morb import rbms, stats, updaters, trainers, monitors, units, parameters

import theano
import theano.tensor as T

import numpy as np

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# generate data
print ">> Generating dataset..."
data = generate_data(1000) # np.random.randint(2, size=(10000, n_visible))
data_context = get_context(data, N=1) # keep the number of dimensions low

data_train = data[:-1000, :]
data_eval = data[-1000:, :]
data_context_train = data_context[:-1000, :]
data_context_eval = data_context[-1000:, :]

n_visible = data.shape[1]
n_context = data_context.shape[1]
n_hidden = 20


print ">> Constructing RBM..."
numpy_rng = np.random.RandomState(123)
initial_W = np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(n_hidden+n_visible+n_context)),
                   high  =  4*np.sqrt(6./(n_hidden+n_visible+n_context)),
                   size  =  (n_visible, n_hidden, n_context)),
                   dtype =  theano.config.floatX)
initial_bv = np.zeros(n_visible, dtype = theano.config.floatX)
initial_bh = np.zeros(n_hidden, dtype = theano.config.floatX)



rbm = morb.base.RBM()
rbm.v = units.BinaryUnits(rbm, name='v') # visibles
rbm.h = units.BinaryUnits(rbm, name='h') # hiddens
rbm.x = units.Units(rbm, name='x') # context

rbm.W = parameters.ThirdOrderParameters(rbm, [rbm.v, rbm.h, rbm.x], theano.shared(value = initial_W, name='W'), name='W') # weights
rbm.bv = parameters.BiasParameters(rbm, rbm.v, theano.shared(value = initial_bv, name='bv'), name='bv') # visible bias
rbm.bh = parameters.BiasParameters(rbm, rbm.h, theano.shared(value = initial_bh, name='bh'), name='bh') # hidden bias

initial_vmap = { rbm.v: T.matrix('v'), rbm.x: T.matrix('x') }

# try to calculate weight updates using CD-1 stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], context_units=[rbm.x], k=1, mean_field_for_gibbs=[rbm.v], mean_field_for_stats=[rbm.v])

umap = {}
for var in rbm.variables:
    pu = var + 0.0005 * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
mce = monitors.reconstruction_crossentropy(s, rbm.v)

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=32, monitors=[m, mce], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=32, monitors=[m, mce], train=False, name='evaluate', mode=mode)

epochs = 200
print ">> Training for %d epochs..." % epochs


for epoch in range(epochs):
    costs_train = [costs for costs in train({ rbm.v: data_train, rbm.x: data_context_train })]
    costs_eval = [costs for costs in evaluate({ rbm.v: data_eval, rbm.x: data_context_eval })]
    mses_train, ces_train = zip(*costs_train)
    mses_eval, ces_eval = zip(*costs_eval)
    
    mse_train = np.mean(mses_train)
    ce_train = np.mean(ces_train)
    mse_eval = np.mean(mses_eval)
    ce_eval = np.mean(ces_eval)
    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, CE = %.6f" % (mse_train, ce_train)
    print "validation set: MSE = %.6f, CE = %.6f" % (mse_eval, ce_eval)



########NEW FILE########
__FILENAME__ = example_thirdorder_factored
import morb
from morb import rbms, stats, updaters, trainers, monitors, units, parameters

import theano
import theano.tensor as T

import numpy as np

import matplotlib.pyplot as plt
plt.ion()

from utils import generate_data, get_context

# DEBUGGING

from theano import ProfileMode
# mode = theano.ProfileMode(optimizer='fast_run', linker=theano.gof.OpWiseCLinker())
# mode = theano.compile.DebugMode(check_py_code=False, require_matching_strides=False)
mode = None


# generate data
print ">> Generating dataset..."
data = generate_data(1000) # np.random.randint(2, size=(10000, n_visible))
data_context = get_context(data, N=1) # keep the number of dimensions low

data_train = data[:-1000, :]
data_eval = data[-1000:, :]
data_context_train = data_context[:-1000, :]
data_context_eval = data_context[-1000:, :]

n_visible = data.shape[1]
n_context = data_context.shape[1]
n_hidden = 20
n_factors = 50

print ">> Constructing RBM..."
numpy_rng = np.random.RandomState(123)

def initial_W(n, f):
    return np.asarray(np.random.uniform(low=-4*np.sqrt(6./(n+f)), high=4*np.sqrt(6./(n+f)), size=(n, f)), dtype=theano.config.floatX)
initial_bv = np.zeros(n_visible, dtype = theano.config.floatX)
initial_bh = np.zeros(n_hidden, dtype = theano.config.floatX)



rbm = morb.base.RBM()
rbm.v = units.BinaryUnits(rbm, name='v') # visibles
rbm.h = units.BinaryUnits(rbm, name='h') # hiddens
rbm.x = units.Units(rbm, name='x') # context

Wv = theano.shared(value=initial_W(n_visible, n_factors), name='Wv')
Wh = theano.shared(value=initial_W(n_hidden, n_factors), name='Wh')
# Wx = theano.shared(value=initial_W(n_context, n_factors), name='Wx')
Wx = Wv # parameter tying

rbm.W = parameters.ThirdOrderFactoredParameters(rbm, [rbm.v, rbm.h, rbm.x], [Wv, Wh, Wx], name='W') # weights
rbm.bv = parameters.BiasParameters(rbm, rbm.v, theano.shared(value = initial_bv, name='bv'), name='bv') # visible bias
rbm.bh = parameters.BiasParameters(rbm, rbm.h, theano.shared(value = initial_bh, name='bh'), name='bh') # hidden bias

initial_vmap = { rbm.v: T.matrix('v'), rbm.x: T.matrix('x') }

# try to calculate weight updates using CD-1 stats
print ">> Constructing contrastive divergence updaters..."
s = stats.cd_stats(rbm, initial_vmap, visible_units=[rbm.v], hidden_units=[rbm.h], context_units=[rbm.x], k=1, mean_field_for_gibbs=[rbm.v], mean_field_for_stats=[rbm.v])

umap = {}
for var in rbm.variables:
    pu = var + 0.0005 * updaters.CDUpdater(rbm, var, s)
    umap[var] = pu

print ">> Compiling functions..."
t = trainers.MinibatchTrainer(rbm, umap)
m = monitors.reconstruction_mse(s, rbm.v)
mce = monitors.reconstruction_crossentropy(s, rbm.v)

# train = t.compile_function(initial_vmap, mb_size=32, monitors=[m], name='train', mode=mode)
train = t.compile_function(initial_vmap, mb_size=32, monitors=[m, mce], name='train', mode=mode)
evaluate = t.compile_function(initial_vmap, mb_size=32, monitors=[m, mce], train=False, name='evaluate', mode=mode)

epochs = 200
print ">> Training for %d epochs..." % epochs


for epoch in range(epochs):
    costs_train = [costs for costs in train({ rbm.v: data_train, rbm.x: data_context_train })]
    costs_eval = [costs for costs in evaluate({ rbm.v: data_eval, rbm.x: data_context_eval })]
    mses_train, ces_train = zip(*costs_train)
    mses_eval, ces_eval = zip(*costs_eval)
    
    mse_train = np.mean(mses_train)
    ce_train = np.mean(ces_train)
    mse_eval = np.mean(mses_eval)
    ce_eval = np.mean(ces_eval)
    
    print "Epoch %d" % epoch
    print "training set: MSE = %.6f, CE = %.6f" % (mse_train, ce_train)
    print "validation set: MSE = %.6f, CE = %.6f" % (mse_eval, ce_eval)



########NEW FILE########
__FILENAME__ = utils
import numpy as np
import matplotlib.pyplot as plt


def generate_data(N):
    """Creates a noisy dataset with some simple pattern in it."""
    T = N * 38
    u = np.mat(np.zeros((T, 20)))
    for i in range(1, T, 38):
        if i % 76 == 1:
            u[i - 1:i + 19, :] = np.eye(20)
            u[i + 18:i + 38, :] = np.eye(20)[np.arange(19, -1, -1)]
            u[i - 1:i + 19, :] += np.eye(20)[np.arange(19, -1, -1)] 
        else:
            u[i - 1:i + 19, 1] = 1
            u[i + 18:i + 38, 8] = 1
    return u

def get_context(u, N=4):
    T, D = u.shape
    x = np.zeros((T, D * N))
    for i in range(N - 1, T):
        dat = u[i - 1, :]
        for j in range(2, N + 1):
            dat = np.concatenate((dat, u[i - j, :]), 1)
        x[i, :] = dat
    return x




def plot_data(d):
    plt.figure(5)
    plt.clf()
    plt.imshow(d.reshape((28,28)), interpolation='gaussian')
    plt.draw()




def one_hot(vec, dim=None):
    """
    Convert a column vector with indices (normalised) to a one-hot representation.
    Each row is a one-hot vector corresponding to an element in the original vector.
    """
    length = len(vec)
    
    if dim is None: # default dimension is the maximal dimension needed to represent 'vec'
        dim = np.max(vec) + 1
        
    m = np.tile(np.arange(dim), (length, 1))
    return (vec == m)




def load_mnist():
    f = gzip.open('mnist.pkl.gz','rb')
    train_set, valid_set, test_set = cPickle.load(f)
    f.close()
    return train_set, valid_set, test_set
    
    

def most_square_shape(num_blocks, blockshape=(1,1)):
    x, y = blockshape
    num_x = np.ceil(np.sqrt(num_blocks * y / float(x)))
    num_y = np.ceil(num_blocks / num_x)
    return (num_x, num_y)  
    
    
    
def visualise_filters(data, dim=6, posneg=True):
    """
    input: a (dim*dim) x H matrix, which is reshaped into filters
    """
    num_x, num_y = most_square_shape(data.shape[1], (dim, dim))
    
    #pad with zeros so that the number of filters equals num_x * num_y
    padding = np.zeros((dim*dim, num_x*num_y - data.shape[1]))
    data_padded = np.hstack([data, padding])
    
    data_split = data_padded.reshape(dim, dim, num_x, num_y)
    
    data_with_border = np.zeros((dim+1, dim+1, num_x, num_y))
    data_with_border[:dim, :dim, :, :] = data_split
    
    filters = data_with_border.transpose(2,0,3,1).reshape(num_x*(dim+1), num_y*(dim+1))
    
    filters_with_left_border = np.zeros((num_x*(dim+1)+1, num_y*(dim+1)+1))
    filters_with_left_border[1:, 1:] = filters
    
    if posneg:
        m = np.abs(data).max()
        plt.imshow(filters_with_left_border, interpolation='nearest', cmap=plt.cm.RdBu, vmin=-m, vmax=m)
    else:
        plt.imshow(filters_with_left_border, interpolation='nearest', cmap=plt.cm.binary, vmin = data.min(), vmax=data.max())



########NEW FILE########
__FILENAME__ = activation_functions
import theano
import theano.tensor as T

## common activation functions

sigmoid = T.nnet.sigmoid

def softmax(x):
    # expected input dimensions:
    # 0 = minibatches
    # 1 = units
    # 2 = states 
    
    r = x.reshape((x.shape[0]*x.shape[1], x.shape[2]))
    # r 0 = minibatches * units
    # r 1 = states
    
    # this is the expected input for theano.nnet.softmax
    s = T.nnet.softmax(r)
    
    # reshape back to original shape
    return s.reshape(x.shape)

def softmax_with_zero(x):
    # expected input dimensions:
    # 0 = minibatches
    # 1 = units
    # 2 = states 
    
    r = x.reshape((x.shape[0]*x.shape[1], x.shape[2]))
    # r 0 = minibatches * units
    # r 1 = states
    r0 = T.concatenate([r, T.zeros_like(r)[:, 0:1]], axis=1) # add row of zeros for zero energy state
    
    # this is the expected input for theano.nnet.softmax
    p0 = T.nnet.softmax(r0)
    
    # reshape back to original shape, but with the added state
    return p0.reshape((x.shape[0], x.shape[1], x.shape[2] + 1))   



########NEW FILE########
__FILENAME__ = base
import theano
import theano.tensor as T

def _unique(l): # no idea why this function isn't available - the set() trick only works for hashable types!
    u = []
    for e in l:
        if e not in u:
            u.append(e)
    return u

### Base classes: sampling and modeling ###
    
class Units(object):    
    def __init__(self, rbm, name=None):
        self.rbm = rbm
        self.name = name
        self.proxy_units = [] # list of units that are proxies of this Units instance
        self.rbm.add_units(self)
        
    def activation(self, vmap):
        terms = [param.activation_term_for(self, vmap) for param in self.rbm.params_affecting(self)]
        # the linear activation is the sum of the activations for each of the parameters.
        return sum(terms, T.constant(0, theano.config.floatX))
        
    def sample_from_activation(self, vmap):
        raise NotImplementedError("Sampling not supported for this Units instance: %s" % repr(self))
        
    def mean_field_from_activation(self, vmap):
        raise NotImplementedError("Mean field not supported for this Units instance: %s" % repr(self))
        
    def free_energy_term_from_activation(self, vmap):
        raise NotImplementedError("Free energy calculation not supported for this Units instance: %s" % repr(self))
        
    def log_prob_from_activation(self, vmap, activation_vmap):
        raise NotImplementedError("Log-probability calculation not supported for this Units instance: %s" % repr(self))
        # note that this gives the log probability density for continuous units, but the log probability mass for discrete ones.
                
    def sample(self, vmap):
        return self.sample_from_activation({ self: self.activation(vmap) })
        
    def mean_field(self, vmap):
        return self.mean_field_from_activation({ self: self.activation(vmap) })
        
    def free_energy_term(self, vmap):
        return self.free_energy_term_from_activation({ self: self.activation(vmap) })
        
    def log_prob(self, vmap):
        activation_vmap = { self: self.activation(vmap) }
        return self.log_prob_from_activation(vmap, activation_vmap)
        
    def __repr__(self):
        return "<morb:Units '%s'>" % self.name


class ProxyUnits(Units):
    def __init__(self, rbm, units, func, name=None):
        super(ProxyUnits, self).__init__(rbm, name)
        self.units = units # the units this proxy is a function of
        self.func = func # the function to apply
        # simple proxy units do not support mean field, the class needs to be overridden for this.
        
    def sample(self, vmap):
        s = self.units.sample(vmap)
        return self.func(s)
        
    def sample_from_activation(self, vmap):
        s = self.units.sample_from_activation(vmap)
        return self.func(s)
        
    def mean_field(self, vmap):
        m = self.units.mean_field(vmap)
        return self.func(m)
        
    def mean_field_from_activation(self, vmap):
        m = self.units.mean_field_from_activation(vmap)
        return self.func(m)
        
        
class Parameters(object):
    def __init__(self, rbm, units_list, name=None):
        self.rbm = rbm
        self.units_list = units_list
        self.terms = {} # terms is a dict of FUNCTIONS that take a vmap.
        self.energy_gradients = {} # a dict of FUNCTIONS that take a vmap.
        self.energy_gradient_sums = {} # a dict of FUNCTIONS that take a vmap.
        self.name = name
        self.rbm.add_parameters(self)
        
    def activation_term_for(self, units, vmap):
        return self.terms[units](vmap)
        
    def energy_gradient_for(self, variable, vmap):
        """
        Returns the energy gradient for each example in the batch.
        """
        return self.energy_gradients[variable](vmap)
        
    def energy_gradient_sum_for(self, variable, vmap):
        """
        Returns the energy gradient, summed across the minibatch dimension.
        If a fast implementation for this is available in the energy_gradient_sums
        dictionary, this will be used. Else the energy gradient will be computed
        for each example in the batch (using the implementation from the
        energy_gradients dictionary) and then summed.
        
        Take a look at the ProdParameters implementation for an example of where
        this is useful: the gradient summed over the batch can be computed more
        efficiently with a dot product.
        """
        if variable in self.energy_gradient_sums:
            return self.energy_gradient_sums[variable](vmap)
        else:
            return T.sum(self.energy_gradients[variable](vmap), axis=0)
        
    def energy_term(self, vmap):
        raise NotImplementedError("Parameters base class")
        
    def affects(self, units):
        return (units in self.units_list)
        
    def __repr__(self):
        units_names = ", ".join(("'%s'" % u.name) for u in self.units_list)
        return "<morb:Parameters '%s' affecting %s>" % (self.name, units_names)


### Base classes: training (parameter updates) ###


class Updater(object):
    # An Updater object updates a single parameter variable. Multiple Updaters can compute updates for a single variable, which can then be aggregated by composite Updaters (like the SumUpdater)
    def __init__(self, variable, stats_list=[]):
        # variable is a single parameter variable, not a Parameters object or a list of variables.
        self.variable = variable
        self.stats_list = stats_list
        self.theano_updates = {} # some Updaters have state. Most don't, so then this is just
        # an empty dictionary. Those who do have state (like the MomentumUpdater) override
        # this variable.
                
    def get_update(self):
        raise NotImplementedError("Updater base class")
        
    def get_theano_updates(self):
        """
        gets own updates and the updates of all contained updaters (if applicable).
        """
        return self.theano_updates
        
    def _to_updater(self, e):
        """
        helper function that turns any expression into an updater
        """
        if not isinstance(e, Updater):
            eu = ExpressionUpdater(self.variable, e)
            return eu
        else:
            return e
        
    def __add__(self, p2):
        p2 = self._to_updater(p2)
        return SumUpdater([self, p2])
        
    def __sub__(self, p2):
        p2 = self._to_updater(p2)
        return self + (-p2)
        
    __radd__ = __add__
    __rsub__ = __sub__
        
    def __neg__(self):
        return ScaleUpdater(self, -1)
        
    def __mul__(self, a):
        return ScaleUpdater(self, a)
        # a is assumed to be a scalar!
        
    def __div__(self, a):
        return self * (1.0/a)
        
    __rmul__ = __mul__
    __rdiv__ = __div__
        

# this extension has to be here because it's used in the base class
class ExpressionUpdater(Updater):
    """
    An updater that returns a specified expression as its update.
    Mainly useful internally.
    """
    def __init__(self, variable, expression):
        super(ExpressionUpdater, self).__init__(variable)
        self.expression = expression
        
    def get_update(self):
        return self.expression

     
# this extension has to be here because it's used in the base class        
class ScaleUpdater(Updater):
    def __init__(self, pu, scaling_factor):
        super(ScaleUpdater, self).__init__(pu.variable, pu.stats_list)
        self.pu = pu
        self.scaling_factor = scaling_factor
        
    def get_update(self):
        return self.scaling_factor * self.pu.get_update()
        
    def get_theano_updates(self):
        u = {} # a scale updater has no state, so it has no theano updates of its own.
        u.update(self.pu.get_theano_updates())
        return u
        
# this extension has to be here because it's used in the base class
class SumUpdater(Updater):
    def __init__(self, updaters):
        # assert that all updaters affect the same variable, gather stats collectors
        self.updaters = updaters
        stats_list = []
        for pu in updaters:
            if pu.variable != updaters[0].variable:
                raise RuntimeError("Cannot add Updaters that affect a different variable together")        
            stats_list.extend(pu.stats_list)
        stats_list = _unique(stats_list) # we only need each Stats object once.
        
        super(SumUpdater, self).__init__(updaters[0].variable, stats_list)
        
    def get_update(self):
        return sum((pu.get_update() for pu in self.updaters), T.constant(0, theano.config.floatX))
        
    def get_theano_updates(self):
        u = {} # a sum updater has no state, so it has no theano updates of its own.
        for pu in self.updaters:
            u.update(pu.get_theano_updates())
        return u
        

class Stats(dict): # a stats object is just a dictionary of vmaps, but it also holds associated theano updates.
    def __init__(self, updates):
        self.theano_updates = updates
    
    def get_theano_updates(self):
        return self.theano_updates

class Trainer(object):
    def __init__(self, rbm, umap):
        self.rbm = rbm
        self.umap = umap

    def get_theano_updates(self, train=True):
        theano_updates = {}
        # collect stats
        stats_list = _unique([s for pu in self.umap.values() for s in pu.stats_list]) # cannot use set() here because dicts are not hashable.
        for s in stats_list:
            theano_updates.update(s.get_theano_updates())
        
        if train:
            variable_updates = {}
            for v, pu in self.umap.items():
                theano_updates.update(pu.get_theano_updates()) # Updater state updates
                theano_updates[v] = pu.get_update() # variable update
                
        return theano_updates
                

### Base classes: RBM container class ###

class RBM(object):
    def __init__(self):
        self.units_list = []
        self.params_list = []
        
    def add_units(self, units):
        self.units_list.append(units)
        
    def remove_units(self, units):
        self.units_list.remove(units)
        
    def add_parameters(self, params):
        self.params_list.append(params)
        
    def remove_parameters(self, params):
        self.params_list.remove(params)
        
    @property
    def variables(self):
        """
        property that returns a set of all parameter variables.
        """
        # This is a set, because if it were a regular list,
        #there would be duplicates when parameters are tied.
        return set(variable for params in self.params_list for variable in params.variables)
                
    def params_affecting(self, units):
        """
        return a list of all Parameters that contribute a term to the activation of Units units.
        """
        return [param for param in self.params_list if param.affects(units)]
        
    def dependent_units(self, given_units_list):
        """
        returns a list of all Units that are dependent on the given list of Units.
        this is useful for block Gibbs sampling (where given_units_list is the set of
        visible Units, and the set of hiddens is returned).
        
        Note that this method does not detect possible dependencies between the given Units
        themselves, or the returned Units themselves! This check should be performed before
        doing gibbs sampling. Alternatively, some back and forth sampling between these
        dependent Units can be used (what's the correct name for this again?)
        
        Also, context (i.e. units that should never be sampled) has to be handled separately.
        This method will include context as it only checks which units are linked to which
        other units, and these links are not directional.
        """
        # first, find all the parameters affecting the Units in the given_units_list
        # then, for each of these, add all the affected units
        dependent_units_list = []
        for u in given_units_list:
            params_list = self.params_affecting(u)
            for params in params_list:
                dependent_units_list.extend(params.units_list)
                
        # finally, remove the given units and return the others
        return set([u for u in dependent_units_list if u not in given_units_list])
        # note that there are no dependency checks here.
        
    def energy_gradient(self, variable, vmap):
        """
        sums the gradient contributions of all Parameters instances for the given variable.
        """
        return sum((p.energy_gradient_for(variable, vmap) for p in self.params_list if variable in p.variables), T.constant(0, theano.config.floatX))
        
    def energy_gradient_sum(self, variable, vmap):
        """
        sums the gradient contributions of all Parameters instances for the given variable,
        where the contributions are summed over the minibatch dimension.
        """
        return sum((p.energy_gradient_sum_for(variable, vmap) for p in self.params_list if variable in p.variables), T.constant(0, theano.config.floatX))
    
    def energy_terms(self, vmap):
        return [params.energy_term(vmap) for params in self.params_list]
        
    def energy(self, vmap):
        # the energy is the sum of the energy terms for each of the parameters.
        return sum(self.energy_terms(vmap), T.constant(0, theano.config.floatX))
        
    def complete_units_list_split(self, units_list):
        """
        Returns two lists: one with basic units and one with proxy units.
        For all basic units in the units_list, all proxies are added as well.
        For all proxy units in the units_list, all missing basic units are added
        as well.
        """
        proxy_units, basic_units = [], []        
        for u in units_list:
            if isinstance(u, ProxyUnits):
                if u not in proxy_units:
                    proxy_units.append(u)
                if u.units not in basic_units:
                    basic_units.append(u.units)
            else:
                if u not in basic_units:
                    basic_units.append(u)
                for p in u.proxy_units:
                    if p not in proxy_units:
                        proxy_units.append(p)
                        
        return basic_units, proxy_units
        
    def complete_units_list(self, units_list):
        b, pr = self.complete_units_list_split(units_list)
        return b + pr
        
    def complete_vmap(self, vmap):
        """
        Takes in a vmap and computes any missing proxy units values.
        """
        vmap = vmap.copy() # don't modify the original dict
        units_list = vmap.keys()
        missing_units_list = []
        for u in units_list:
            for p in u.proxy_units:
                if p not in units_list:
                    missing_units_list.append(p)
                    
        for p in missing_units_list:
            vmap[p] = p.func(vmap[p.units])
            
        return vmap
    
    def sample_from_activation(self, vmap):
        """
        This method allows to sample a given set of Units instances at the same time and enforces consistency.
        say v is a Units instance, and x is a ProxyUnits instance tied to v. Then the following:
        vs = v.sample_from_activation(a1)
        xs = x.sample_from_activation(a2)
        ...will yield inconsistent samples (i.e. xs != func(vs)). This is undesirable in CD, for example.
        To remedy this, only the 'basic' units are sampled, and the values of the proxy units are computed.
        The supplied activation_map is assumed to be complete.
        """
        # This code does not support proxies of proxies.
        # If this should be supported, this code should be rethought.
        
        # first, 'complete' units_list: if there are any proxies whose basic units
        # are not included, add them. If any of the included basic units have proxies
        # which are not, add them as well. Make two separate lists.
        # note that this completion comes at almost no extra cost: the expressions
        # are added to the resulting dictionary, but that doesn't mean they'll
        # necessarily be used (and thus, compiled).
        units_list = vmap.keys()
        basic_units, proxy_units = self.complete_units_list_split(units_list)
                
        # sample all basic units
        samples = {}
        for u in basic_units:
            samples[u] = u.sample_from_activation(vmap)
            
        # compute all proxy units
        for u in proxy_units:
            samples[u] = u.func(samples[u.units])
        
        return samples
    
    def sample(self, units_list, vmap):
        """
        This method allows to sample a given set of Units instances at the same time and enforces consistency.
        say v is a Units instance, and x is a ProxyUnits instance tied to v. Then the following:
        vs = v.sample(vmap)
        xs = x.sample(vmap)
        ...will yield inconsistent samples (i.e. xs != func(vs)). This is undesirable in CD, for example.
        To remedy this, only the 'basic' units are sampled, and the values of the proxy units are computed.
        All proxies are always included in the returned vmap.
        """
        activations_vmap = self.activations(units_list, vmap)
        return self.sample_from_activation(activations_vmap)
    
    def mean_field_from_activation(self, vmap):
        units_list = vmap.keys()
        units_list = self.complete_units_list(units_list)
        # no consistency need be enforced when using mean field.
        return dict((u, u.mean_field_from_activation(vmap)) for u in units_list)
    
    def mean_field(self, units_list, vmap):
        activations_vmap = self.activations(units_list, vmap)
        return self.mean_field_from_activation(activations_vmap)
        
    def free_energy_unchanged_terms(self, units_list, vmap):
        """
        The terms of the energy that don't involve any of the given units.
        These terms are unchanged when computing the free energy, where
        the given units are integrated out.
        """
        unchanged_terms = []
        for params in self.params_list:
            if not any(params.affects(u) for u in units_list):
                # if none of the given Units instances are affected by the current Parameters instance,
                # this term is unchanged (it's the same as in the energy function)
                unchanged_terms.append(params.energy_term(vmap))
        
        return unchanged_terms
        
    def free_energy_affected_terms_from_activation(self, vmap):
        """
        For each Units instance in the activation vmap, the corresponding free energy
        term is returned.
        """
        return dict((u, u.free_energy_term_from_activation(vmap)) for u in vmap)

    def free_energy_affected_terms(self, units_list, vmap):
        """
        The terms of the energy that involve the units given in units_list are
        of course affected when these units are integrated out. This method
        gives the 'integrated' terms.
        """
        return dict((u, u.free_energy_term(vmap)) for u in units_list)
            
    def free_energy(self, units_list, vmap):
        """
        Calculates the free energy, integrating out the units given in units_list.
        This has to be a list of Units instances that are independent of eachother
        given the other units, and each of them has to have a free_energy_term.
        """
        # first, get the terms of the energy that don't involve any of the given units. These terms are unchanged.
        unchanged_terms = self.free_energy_unchanged_terms(units_list, vmap)
        # all other terms are affected by the summing out of the units.        
        affected_terms = self.free_energy_affected_terms(units_list, vmap).values()  
        # note that this separation breaks down if there are dependencies between the Units instances given.
        return sum(unchanged_terms + affected_terms, T.constant(0, theano.config.floatX))
        
    def activations(self, units_list, vmap):
        units_list = self.complete_units_list(units_list)
        # no consistency need be enforced when computing activations.
        return dict((u, u.activation(vmap)) for u in units_list)

    def __repr__(self):
        units_names = ", ".join(("'%s'" % u.name) for u in self.units_list)
        params_names = ", ".join(("'%s'" % p.name) for p in self.params_list)
        return "<morb:%s with units %s and parameters %s>" % (self.__class__.__name__, units_names, params_names)
        


########NEW FILE########
__FILENAME__ = factors
import theano.tensor as T
from morb.base import Parameters

from operator import mul

# general 'Factor' implementation that can represent factored parameters by
# combining other types of parameters. This could be used to implement a
# factored convolutional RBM or something, or an n-way factored RBM with n >= 2.

# The idea is that the 'Factor' object acts as an RBM and Units proxy for the
# contained Parameters, and is used as a Parameters object within the RBM.

# The Parameters contained within the Factor MUST NOT be added to the RBM,
# because their joint energy term is not linear in each of the individual
# factored parameter sets (but rather multiplicative). Adding them to the
# RBM would cause them to contribute an energy term, which doesn't make sense.

# TODO: an uninitialised factor typically just results in bogus results, it doesn't
# raise any exceptions. This isn't very clean. Maybe find a way around this.

class Factor(Parameters):
    """
    A 'factor' can be used to construct factored parameters from other
    Parameters instances.
    """
    def __init__(self, rbm, name=None):
        super(Factor, self).__init__(rbm, [], name=name)
        # units_list is initially empty, but is expanded later by adding Parameters.
        self.variables = [] # same for variables
        self.params_list = []
        self.terms = {}
        self.energy_gradients = {} # careful, this is now a dict of LISTS to support parameter tying.
        self.energy_gradient_sums = {} # same here!
        self.initialized = False
        
    def check_initialized(self):
        if not self.initialized:
            raise RuntimeError("Factor '%s' has not been initialized." % self.name)
    
    def factor_product(self, params, vmap):
        """
        The factor product needed to compute the activation of the other units
        tied by Parameters params.
        """
        # get all Parameters except for the given instance
        fp_params_list = list(self.params_list) # make a copy
        fp_params_list.remove(params) # remove the given instance
        
        # compute activation terms of the factor
        activations = [fp_params.terms[self](vmap) for fp_params in fp_params_list]

        # multiply the activation terms
        return reduce(mul, activations)
    
    def update_terms(self, params):
        """
        Add activation terms for the units associated with Parameters instance params
        """
        ul = list(params.units_list) # copy
        ul.remove(self)
        for u in ul:
            def term(vmap):
                fp = self.factor_product(params, vmap) # compute factor values
                fvmap = vmap.copy()
                fvmap.update({ self: fp }) # insert them in a vmap copy
                return params.terms[u](fvmap) # pass the copy to the Parameters instance so it can compute its activation
            self.terms[u] = term

    def update_energy_gradients(self, params):
        """
        Add/update energy gradients for the variables associated with Parameters instance params
        """
        for var in params.variables:
            def grad(vmap):
                fp = self.factor_product(params, vmap) # compute factor values
                fvmap = vmap.copy()
                fvmap.update({ self: fp }) # insert them in a vmap copy
                return params.energy_gradient_for(var, fvmap)
                
            def grad_sum(vmap):
                fp = self.factor_product(params, vmap) # compute factor values
                fvmap = vmap.copy()
                fvmap.update({ self: fp }) # insert them in a vmap copy
                return params.energy_gradient_sum_for(var, fvmap)
           
            if var not in self.energy_gradients:
                self.energy_gradients[var] = []
                self.energy_gradient_sums[var] = []
            self.energy_gradients[var].append(grad)
            self.energy_gradient_sums[var].append(grad_sum)

    def activation_term_for(self, units, vmap):
        self.check_initialized()
        return self.terms[units](vmap)
        
    def energy_gradient_for(self, variable, vmap):
        self.check_initialized()
        return sum(f(vmap) for f in self.energy_gradients[variable]) # sum all contributions
        
    def energy_gradient_sum_for(self, variable, vmap):
        self.check_initialized()
        return sum(f(vmap) for f in self.energy_gradient_sums[variable]) # sum all contributions

    def energy_term(self, vmap):
        """
        The energy term of the factor, which is the product of all activation
        terms of the factor from the contained Parameters instances.
        """
        self.check_initialized()
        factor_activations = [params.terms[self](vmap) for params in self.params_list]
        return T.sum(reduce(mul, factor_activations))
    
    def initialize(self):
        """
        Extract Units instances and variables from each contained Parameters
        instance. Unfortunately there is no easy way to do this automatically
        when the Parameters instances are created, because the add_parameters
        method is called before they are fully initialised.
        """
        if self.initialized: # don't initialize multiple times
            return # TODO: maybe this should raise a warning?
            
        for params in self.params_list:
            self.variables.extend(params.variables)
            units_list = list(params.units_list)
            units_list.remove(self)
            self.units_list.extend(units_list)
            self.update_terms(params)
            self.update_energy_gradients(params)
            
        self.initialized = True
        
    def add_parameters(self, params):
        """
        This method is called by the Parameters constructor when the 'rbm'
        argument is substituted for a Factor instance.
        """
        self.params_list.append(params)

    def __repr__(self):
        units_names = ", ".join(("'%s'" % u.name) for u in self.units_list)
        return "<morb:Factor '%s' affecting %s>" % (self.name, units_names)


########NEW FILE########
__FILENAME__ = misc
# miscellaneous utility functions

import theano
from theano import tensor
import numpy
 
    
def tensordot(a, b, axes=2):
    """
    implementation of tensordot that reduces to a regular matrix product. This allows tensordot to be GPU accelerated,
    which isn't possible with the default Theano implementation (which is just a wrapper around numpy.tensordot).
    based on code from Tijmen Tieleman's gnumpy http://www.cs.toronto.edu/~tijmen/gnumpy.html
    """
    if numpy.isscalar(axes):
        # if 'axes' is a number of axes to multiply and sum over (trailing axes
        # of a, leading axes of b), we can just reshape and use dot.         
        outshape = tensor.concatenate([a.shape[:a.ndim - axes], b.shape[axes:]])
        outndim = a.ndim + b.ndim - 2*axes
        a_reshaped = a.reshape((tensor.prod(a.shape[:a.ndim - axes]), tensor.prod(a.shape[a.ndim - axes:])))
        b_reshaped = b.reshape((tensor.prod(b.shape[:axes]), tensor.prod(b.shape[axes:])))
        return tensor.dot(a_reshaped, b_reshaped).reshape(outshape, ndim=outndim)
    elif len(axes) == 2:
        # if 'axes' is a pair of axis lists, we first shuffle the axes of a and
        # b to reduce this to the first case (note the recursion).
        a_other, b_other = tuple(axes[0]), tuple(axes[1])
        num_axes = len(a_other)
        a_order = tuple(x for x in tuple(xrange(a.ndim)) if x not in a_other) + a_other
        b_order = b_other + tuple(x for x in tuple(xrange(b.ndim)) if x not in b_other)
        a_shuffled = a.dimshuffle(a_order)
        b_shuffled = b.dimshuffle(b_order)
        return tensordot(a_shuffled, b_shuffled, num_axes)
    else:
        raise ValueError("Axes should be scalar valued or a list/tuple of len 2.")

########NEW FILE########
__FILENAME__ = monitors
import theano
import theano.tensor as T


def reconstruction_mse(stats, u):
    data = stats['data'][u]
    reconstruction = stats['model'][u]
    return T.mean((data - reconstruction) ** 2)
    
def reconstruction_error_rate(stats, u):
    data = stats['data'][u]
    reconstruction = stats['model'][u]
    return T.mean(T.neq(data, reconstruction))

def reconstruction_crossentropy(stats, u):
    data = stats['data'][u]
    reconstruction_activation = stats['model_activation'][u]
    return T.mean(T.sum(data*T.log(T.nnet.sigmoid(reconstruction_activation)) +
                  (1 - data)*T.log(1 - T.nnet.sigmoid(reconstruction_activation)), axis=1))                          
    # without optimisation:
    # return T.mean(T.sum(data*T.log(reconstruction) + (1 - data)*T.log(reconstruction), axis=1))
    # see http://deeplearning.net/tutorial/rbm.html, below the gibbs_hvh and gibbs_vhv code for an explanation.



# TODO: pseudo likelihood? is that feasible?



########NEW FILE########
__FILENAME__ = objectives
import theano
import theano.tensor as T

import samplers


#def autoencoder(rbm, vmap, visible_units, hidden_units, context_units=[]):
#    """
#    Takes an RBM that consists only of units that implement mean field.
#    The means of these units will be treated as activations of an autoencoder.
#    
#    Note that this can only be used for autoencoders with tied weights.
#    
#    input
#    rbm: the RBM object
#    vmap: a vmap dictionary of input units instances of the RBM mapped to theano expressions.
#    visible_units: a list of input units, the autoencoder will attempt to reconstruct these
#    hidden_units: the hidden layer of the autoencoder
#    
#    context units should simply be added in the vmap, they need not be specified.
#    
#    output
#    a vmap dictionary giving the reconstructions.
#    """
#    
#    # complete units lists
#    visible_units = rbm.complete_units_list(visible_units)
#    hidden_units = rbm.complete_units_list(hidden_units)
#    
#    # complete the supplied vmap
#    vmap = rbm.complete_vmap(vmap)
#    
#    hidden_vmap = rbm.mean_field(hidden_units, vmap)
#    hidden_vmap.update(vmap) # we can just add the supplied vmap to the hidden vmap to
#    # ensure that any context units are also in the hidden vmap. We do not run the risk
#    # of 'overwriting' anything since the hiddens and the visibles are disjoint.
#    # note that the hidden vmap need not be completed, since the hidden_units list
#    # has already been completed.
#    reconstruction_vmap = rbm.mean_field(visible_units, hidden_vmap)
#    
#    return reconstruction_vmap
    


### autoencoder objective + utilities ###

def autoencoder(rbm, visible_units, hidden_units, v0_vmap, v0_vmap_source=None):
    """
    Implements the autoencoder objective: the log likelihood of the visibles given the hiddens,
    where the hidden values are obtained using mean field.

    The last argument, v0_vmap_source, allows for using inputs that are different than the targets.
    This is useful for implementing denoising regularisation.
    """
    if v0_vmap_source is None:
        v0_vmap_source = v0_vmap # default to using the same input as source and target

    full_vmap_source = rbm.complete_vmap(v0_vmap_source)
    full_vmap = rbm.complete_vmap(v0_vmap)
    # add the conditional means for the hidden units to the vmap
    for hu in hidden_units:
        full_vmap_source[hu] = hu.mean_field(v0_vmap_source)

    # add any missing proxies of the hiddens (unlikely, but you never know)
    full_vmap_source = rbm.complete_vmap(full_vmap_source)

    # get log probs of all the visibles
    log_prob_terms = []
    for vu in visible_units:
        activation_vmap_source = { vu: vu.activation(full_vmap_source) }
        lp = vu.log_prob_from_activation(full_vmap, activation_vmap_source)
        log_prob_terms.append(T.sum(T.mean(lp, 0))) # mean over the minibatch dimension

    total_log_prob = sum(log_prob_terms)
    
    return total_log_prob



def mean_reconstruction(rbm, visible_units, hidden_units, v0_vmap):   
    """
    Computes the mean reconstruction for a given RBM and a set of visibles and hiddens.
    E[v|h] with h = E[h|v].
    
    input
    rbm: the RBM object
    vmap: a vmap dictionary of input units instances of the RBM mapped to theano expressions.
    visible_units: a list of input units
    hidden_units: the hidden layer of the autoencoder
    
    context units should simply be added in the vmap, they need not be specified.
    
    output
    a vmap dictionary giving the reconstructions.

    NOTE: this vmap may contain more than just the requested values, because the 'visible_units'
    units list is completed with all proxies. So it's probably not a good idea to iterate over
    the output vmap.
    """
    
    # complete units lists
    visible_units = rbm.complete_units_list(visible_units)
    hidden_units = rbm.complete_units_list(hidden_units)
    
    # complete the supplied vmap
    v0_vmap = rbm.complete_vmap(v0_vmap)
    
    hidden_vmap = rbm.mean_field(hidden_units, v0_vmap)
    hidden_vmap.update(v0_vmap) # we can just add the supplied vmap to the hidden vmap to
    # ensure that any context units are also in the hidden vmap. We do not run the risk
    # of 'overwriting' anything since the hiddens and the visibles are disjoint.
    # note that the hidden vmap need not be completed, since the hidden_units list
    # has already been completed.
    reconstruction_vmap = rbm.mean_field(visible_units, hidden_vmap)
    
    return reconstruction_vmap



### regularisation ###

def sparsity_penalty(rbm, hidden_units, v0_vmap, target):
    """
    Implements a cross-entropy sparsity penalty. Note that this only really makes sense if the hidden units are binary.
    """
    # complete units lists
    hidden_units = rbm.complete_units_list(hidden_units)
    
    # complete the supplied vmap
    v0_vmap = rbm.complete_vmap(v0_vmap)
    
    hidden_vmap = rbm.mean_field(hidden_units, v0_vmap)

    penalty_terms = []
    for hu in hidden_units:
        mean_activation = T.mean(hidden_vmap[hu], 0) # mean over minibatch dimension
        penalty_terms.append(T.sum(T.nnet.binary_crossentropy(mean_activation, target))) # sum over the features

    total_penalty = sum(penalty_terms)
    return total_penalty


### input corruption ###

def corrupt_masking(v, corruption_level):
    return samplers.theano_rng.binomial(size=v.shape, n=1, p=1 - corruption_level, dtype=theano.config.floatX) * v

def corrupt_salt_and_pepper(v, corruption_level):
    mask = samplers.theano_rng.binomial(size=v.shape, n=1, p=1 - corruption_level, dtype=theano.config.floatX)
    rand = samplers.theano_rng.binomial(size=v.shape, n=1, p=0.5, dtype=theano.config.floatX)
    return mask * v + (1 - mask) * rand

def corrupt_gaussian(v, std):
    noise = samplers.theano_rng.normal(size=v.shape, avg=0.0, std=std, dtype=theano.config.floatX)
    return v + noise



### common error measures ###

def mse(units_list, vmap_targets, vmap_predictions):
    """
    Computes the mean square error between two vmaps representing data
    and reconstruction.
    
    units_list: list of input units instances
    vmap_targets: vmap dictionary containing targets
    vmap_predictions: vmap dictionary containing model predictions
    """
    return sum(T.mean((vmap_targets[u] - vmap_predictions[u]) ** 2) for u in units_list)


def cross_entropy(units_list, vmap_targets, vmap_predictions):
    """
    Computes the cross entropy error between two vmaps representing data
    and reconstruction.
    
    units_list: list of input units instances
    vmap_targets: vmap dictionary containing targets
    vmap_predictions: vmap dictionary containing model predictions
    """
    t, p = vmap_targets, vmap_predictions
    return sum((- t[u] * T.log(p[u]) - (1 - t[u]) * T.log(1 - p[u])) for u in units_list)

    

########NEW FILE########
__FILENAME__ = parameters
from morb.base import Parameters

import theano
import theano.tensor as T
from theano.tensor.nnet import conv

from morb.misc import tensordot # better tensordot implementation that can be GPU accelerated
# tensordot = T.tensordot # use theano implementation

class FixedBiasParameters(Parameters):
    # Bias fixed at -1, which is useful for some energy functions (like Gaussian with fixed variance, Beta)
    def __init__(self, rbm, units, name=None):
        super(FixedBiasParameters, self).__init__(rbm, [units], name=name)
        self.variables = []
        self.u = units
        
        self.terms[self.u] = lambda vmap: T.constant(-1, theano.config.floatX) # T.constant is necessary so scan doesn't choke on it
        
    def energy_term(self, vmap):
        s = vmap[self.u]
        return T.sum(s, axis=range(1, s.ndim)) # NO minus sign! bias is -1 so this is canceled.
        # sum over all but the minibatch dimension.
        
        
class ProdParameters(Parameters):
    def __init__(self, rbm, units_list, W, name=None):
        super(ProdParameters, self).__init__(rbm, units_list, name=name)
        assert len(units_list) == 2
        self.var = W
        self.variables = [self.var]
        self.vu = units_list[0]
        self.hu = units_list[1]
        
        self.terms[self.vu] = lambda vmap: T.dot(vmap[self.hu], W.T)
        self.terms[self.hu] = lambda vmap: T.dot(vmap[self.vu], W)
        
        self.energy_gradients[self.var] = lambda vmap: vmap[self.vu].dimshuffle(0, 1, 'x') * vmap[self.hu].dimshuffle(0, 'x', 1)
        self.energy_gradient_sums[self.var] = lambda vmap: T.dot(vmap[self.vu].T, vmap[self.hu])
                
    def energy_term(self, vmap):
        return - T.sum(self.terms[self.hu](vmap) * vmap[self.hu], axis=1)
        # return - T.sum(T.dot(vmap[self.vu], self.var) * vmap[self.hu])
        # T.sum sums over the hiddens dimension.
        
    
class BiasParameters(Parameters):
    def __init__(self, rbm, units, b, name=None):
        super(BiasParameters, self).__init__(rbm, [units], name=name)
        self.var = b
        self.variables = [self.var]
        self.u = units
        
        self.terms[self.u] = lambda vmap: self.var
        
        self.energy_gradients[self.var] = lambda vmap: vmap[self.u]
        
    def energy_term(self, vmap):
        return - T.dot(vmap[self.u], self.var)
        # bias is NOT TRANSPOSED because it's a vector, and apparently vectors are COLUMN vectors by default.


class AdvancedProdParameters(Parameters):
    def __init__(self, rbm, units_list, dimensions_list, W, name=None):
        super(AdvancedProdParameters, self).__init__(rbm, units_list, name=name)
        assert len(units_list) == 2
        self.var = W
        self.variables = [self.var]
        self.vu = units_list[0]
        self.hu = units_list[1]
        self.vd = dimensions_list[0]
        self.hd = dimensions_list[1]
        self.vard = self.vd + self.hd
        
        # there are vd visible dimensions and hd hidden dimensions, meaning that the weight matrix has
        # vd + hd = Wd dimensions.
        # the hiddens and visibles have hd+1 and vd+1 dimensions respectively, because the first dimension
        # is reserved for minibatches!
        self.terms[self.vu] = lambda vmap: tensordot(vmap[self.hu], W, axes=(range(1,self.hd+1),range(self.vd, self.vard)))
        self.terms[self.hu] = lambda vmap: tensordot(vmap[self.vu], W, axes=(range(1,self.vd+1),range(0, self.vd)))
        
        def gradient(vmap):
            v_indices = range(0, self.vd + 1) + (['x'] * self.hd)
            h_indices = [0] + (['x'] * self.vd) + range(1, self.hd + 1)
            v_reshaped = vmap[self.vu].dimshuffle(v_indices)
            h_reshaped = vmap[self.hu].dimshuffle(h_indices)
            return v_reshaped * h_reshaped
        
        self.energy_gradients[self.var] = gradient
        self.energy_gradient_sums[self.var] = lambda vmap: tensordot(vmap[self.vu], vmap[self.hu], axes=([0],[0]))
        # only sums out the minibatch dimension.
                
    def energy_term(self, vmap):
        # v_part = tensordot(vmap[self.vu], self.var, axes=(range(1, self.vd+1), range(0, self.vd)))
        v_part = self.terms[self.hu](vmap)
        neg_energy = tensordot(v_part, vmap[self.hu], axes=(range(1, self.hd+1), range(1, self.hd+1)))
        # we do not sum over the first dimension, which is reserved for minibatches!
        return - neg_energy # don't forget to flip the sign!


class AdvancedBiasParameters(Parameters):
    def __init__(self, rbm, units, dimensions, b, name=None):
        super(AdvancedBiasParameters, self).__init__(rbm, [units], name=name)
        self.var = b
        self.variables = [self.var]
        self.u = units
        self.ud = dimensions
        
        self.terms[self.u] = lambda vmap: self.var
        
        self.energy_gradients[self.var] = lambda vmap: vmap[self.u]
        
    def energy_term(self, vmap):
        return - tensordot(vmap[self.u], self.var, axes=(range(1, self.ud+1), range(0, self.ud)))
        

class SharedBiasParameters(Parameters):
    """
    like AdvancedBiasParameters, but a given number of trailing dimensions are 'shared'.
    """
    def __init__(self, rbm, units, dimensions, shared_dimensions, b, name=None):
        super(SharedBiasParameters, self).__init__(rbm, [units], name=name)
        self.var = b
        self.variables = [self.var]
        self.u = units
        self.ud = dimensions
        self.sd = shared_dimensions
        self.nd = self.ud - self.sd
        
        self.terms[self.u] = lambda vmap: T.shape_padright(self.var, self.sd)
        
        self.energy_gradients[self.var] = lambda vmap: T.mean(vmap[self.u], axis=self._shared_axes(vmap))
        
    def _shared_axes(self, vmap):
        d = vmap[self.u].ndim
        return range(d - self.sd, d)
            
    def energy_term(self, vmap):
        # b_padded = T.shape_padright(self.var, self.sd)
        # return - T.sum(tensordot(vmap[self.u], b_padded, axes=(range(1, self.ud+1), range(0, self.ud))), axis=0)
        # this does not work because tensordot cannot handle broadcastable dimensions.
        # instead, the dimensions of b_padded which are broadcastable should be summed out afterwards.
        # this comes down to the same thing. so:
        t = tensordot(vmap[self.u], self.var, axes=(range(1, self.nd+1), range(0, self.nd)))
        # now sum t over its trailing shared dimensions, which mimics broadcast + tensordot behaviour.
        axes = range(t.ndim - self.sd, t.ndim)
        return - T.sum(t, axis=axes)

               
class Convolutional2DParameters(Parameters):
    def __init__(self, rbm, units_list, W, shape_info=None, name=None):
        # use the shape_info parameter to provide a dict with keys:
        # hidden_maps, visible_maps, filter_height, filter_width, visible_height, visible_width, mb_size
        
        super(Convolutional2DParameters, self).__init__(rbm, units_list, name=name)
        assert len(units_list) == 2
        self.var = W # (hidden_maps, visible_maps, filter_height, filter_width)
        self.variables = [self.var]
        self.vu = units_list[0] # (mb_size, visible_maps, visible_height, visible_width)
        self.hu = units_list[1] # (mb_size, hidden_maps, hidden_height, hidden_width)
        self.shape_info = shape_info

        # conv input is (output_maps, input_maps, filter height [numrows], filter width [numcolumns])
        # conv input is (mb_size, input_maps, input height [numrows], input width [numcolumns])
        # conv output is (mb_size, output_maps, output height [numrows], output width [numcolumns])
        
        def term_vu(vmap):
            # input = hiddens, output = visibles so we need to swap dimensions
            W_shuffled = self.var.dimshuffle(1, 0, 2, 3)
            if self.filter_shape is not None:
                shuffled_filter_shape = [self.filter_shape[k] for k in (1, 0, 2, 3)]
            else:
                shuffled_filter_shape = None
            return conv.conv2d(vmap[self.hu], W_shuffled, border_mode='full', \
                               image_shape=self.hidden_shape, filter_shape=shuffled_filter_shape)
            
        def term_hu(vmap):
            # input = visibles, output = hiddens, flip filters
            W_flipped = self.var[:, :, ::-1, ::-1]
            return conv.conv2d(vmap[self.vu], W_flipped, border_mode='valid', \
                               image_shape=self.visible_shape, filter_shape=self.filter_shape)
        
        self.terms[self.vu] = term_vu
        self.terms[self.hu] = term_hu
        
        def gradient(vmap):
            raise NotImplementedError # TODO
        
        def gradient_sum(vmap):
            if self.visible_shape is not None:
                i_shape = [self.visible_shape[k] for k in [1, 0, 2, 3]]
            else:
                i_shape = None
        
            if self.hidden_shape is not None:
                f_shape = [self.hidden_shape[k] for k in [1, 0, 2, 3]]
            else:
                f_shape = None
            
            v_shuffled = vmap[self.vu].dimshuffle(1, 0, 2, 3)
            h_shuffled = vmap[self.hu].dimshuffle(1, 0, 2, 3)
            
            c = conv.conv2d(v_shuffled, h_shuffled, border_mode='valid', image_shape=i_shape, filter_shape=f_shape)   
            return c.dimshuffle(1, 0, 2, 3)
            
        self.energy_gradients[self.var] = gradient
        self.energy_gradient_sums[self.var] = gradient_sum
    
    @property    
    def filter_shape(self):
        keys = ['hidden_maps', 'visible_maps', 'filter_height', 'filter_width']
        if self.shape_info is not None and all(k in self.shape_info for k in keys):
            return tuple(self.shape_info[k] for k in keys)
        else:
            return None

    @property            
    def visible_shape(self):
        keys = ['mb_size', 'visible_maps', 'visible_height', 'visible_width']                
        if self.shape_info is not None and all(k in self.shape_info for k in keys):
            return tuple(self.shape_info[k] for k in keys)
        else:
            return None

    @property            
    def hidden_shape(self):
        keys = ['mb_size', 'hidden_maps', 'visible_height', 'visible_width']
        if self.shape_info is not None and all(k in self.shape_info for k in keys):
            hidden_height = self.shape_info['visible_height'] - self.shape_info['filter_height'] + 1
            hidden_width = self.shape_info['visible_width'] - self.shape_info['filter_width'] + 1
            return (self.shape_info['mb_size'], self.shape_info['hidden_maps'], hidden_height, hidden_width)
        else:
            return None
        
    def energy_term(self, vmap):
        return - T.sum(self.terms[self.hu](vmap) * vmap[self.hu], axis=[1,2,3])
        # sum over all but the minibatch axis
        
        
        
        
# TODO: 1D convolution + optimisation




class ThirdOrderParameters(Parameters):
    def __init__(self, rbm, units_list, W, name=None):
        super(ThirdOrderParameters, self).__init__(rbm, units_list, name=name)
        assert len(units_list) == 3
        self.var = W
        self.variables = [self.var]
        self.u0 = units_list[0]
        self.u1 = units_list[1]
        self.u2 = units_list[2]
        
        def term_u0(vmap):
            p = tensordot(vmap[self.u1], W, axes=([1],[1])) # (mb, u0, u2)
            return T.sum(p * vmap[self.u2].dimshuffle(0, 'x', 1), axis=2) # (mb, u0)
            # cannot use two tensordots here because of the minibatch dimension.
            
        def term_u1(vmap):
            p = tensordot(vmap[self.u0], W, axes=([1],[0])) # (mb, u1, u2)
            return T.sum(p * vmap[self.u2].dimshuffle(0, 'x', 1), axis=2) # (mb, u1)
            
        def term_u2(vmap):
            p = tensordot(vmap[self.u0], W, axes=([1],[0])) # (mb, u1, u2)
            return T.sum(p * vmap[self.u1].dimshuffle(0, 1, 'x'), axis=1) # (mb, u2)
            
        self.terms[self.u0] = term_u0
        self.terms[self.u1] = term_u1
        self.terms[self.u2] = term_u2
                
        def gradient(vmap):
            p = vmap[self.u0].dimshuffle(0, 1, 'x') * vmap[self.u1].dimshuffle(0, 'x', 1) # (mb, u0, u1)
            p2 = p.dimshuffle(0, 1, 2, 'x') * vmap[self.u2].dimshuffle(0, 'x', 'x', 1) # (mb, u0, u1, u2)
            return p2
            
        self.energy_gradients[self.var] = gradient
        
    def energy_term(self, vmap):
        return - T.sum(self.terms[self.u1](vmap) * vmap[self.u1], axis=1)
        # sum is over the u1 dimension, not the minibatch dimension!




class ThirdOrderFactoredParameters(Parameters):
    """
    Factored 3rd order parameters, connecting three Units instances. Each factored
    parameter matrix has dimensions (units_size, num_factors).
    """
    def __init__(self, rbm, units_list, variables, name=None):
        super(ThirdOrderFactoredParameters, self).__init__(rbm, units_list, name=name)
        assert len(units_list) == 3
        assert len(variables) == 3
        self.variables = variables
        self.var0 = variables[0]
        self.var1 = variables[1]
        self.var2 = variables[2]
        self.u0 = units_list[0]
        self.u1 = units_list[1]
        self.u2 = units_list[2]
        self.prod0 = lambda vmap: T.dot(vmap[self.u0], self.var0) # (mb, f)
        self.prod1 = lambda vmap: T.dot(vmap[self.u1], self.var1) # (mb, f)
        self.prod2 = lambda vmap: T.dot(vmap[self.u2], self.var2) # (mb, f)
        self.terms[self.u0] = lambda vmap: T.dot(self.prod1(vmap) * self.prod2(vmap), self.var0.T) # (mb, u0)
        self.terms[self.u1] = lambda vmap: T.dot(self.prod0(vmap) * self.prod2(vmap), self.var1.T) # (mb, u1)
        self.terms[self.u2] = lambda vmap: T.dot(self.prod0(vmap) * self.prod1(vmap), self.var2.T) # (mb, u2)
        
        # if the same parameter variable is used multiple times, the energy gradients should be added.
        # so we need a little bit of trickery here to make this work.
        energy_gradient_sums_list = [
            lambda vmap: T.dot(vmap[self.u0].T, self.prod1(vmap) * self.prod2(vmap)), # (u0, f)
            lambda vmap: T.dot(vmap[self.u1].T, self.prod0(vmap) * self.prod2(vmap)), # (u1, f)
            lambda vmap: T.dot(vmap[self.u2].T, self.prod0(vmap) * self.prod1(vmap)), # (u2, f)
        ] # the T.dot also sums out the minibatch dimension
        
        energy_gradient_sums_dict = {}
        for var, grad in zip(self.variables, energy_gradient_sums_list):
            if var not in energy_gradient_sums_dict:
                energy_gradient_sums_dict[var] = []
            energy_gradient_sums_dict[var].append(grad)
            
        for var, grad_list in energy_gradient_sums_dict.items():
            def tmp(): # create a closure, otherwise grad_list will always
                # refer to the one of the last iteration!
                # TODO: this is nasty, is there a cleaner way?
                g = grad_list
                self.energy_gradient_sums[var] = lambda vmap: sum(f(vmap) for f in g)
            tmp()
            
        # TODO: do the same for the gradient without summing!
    
    def energy_term(self, vmap):
        return - T.sum(self.terms[self.u1](vmap) * vmap[self.u1], axis=1)
        # sum is over the u1 dimension, not the minibatch dimension!
        



class TransformedParameters(Parameters):
    """
    Transform parameter variables, adapt gradients accordingly
    """
    def __init__(self, params, transforms, transform_gradients, name=None):
        """
        params: a Parameters instance for which variables should be transformed
        transforms: a dict mapping variables to their transforms
        gradients: a dict mapping variables to the gradient of their transforms
        
        IMPORTANT: the original Parameters instance should not be used afterwards
        as it will be removed from the RBM.
        
        ALSO IMPORTANT: because of the way the chain rule is applied, the old
        Parameters instance is expected to be linear in the variables.
        
        Example usage:
            rbm = RBM(...)
            h = Units(...)
            v = Units(...)
            var_W = theano.shared(...)
            W = ProdParameters(rbm, [u, v], var_W, name='W')
            W_tf = TransformedParameters(W, { var_W: T.exp(var_W) }, { var_W: T.exp(var_W) }, name='W_tf')
        """
        self.encapsulated_params = params
        self.transforms = transforms
        self.transform_gradients = transform_gradients

        # remove the old instance, this one will replace it
        params.rbm.remove_parameters(params)
        # TODO: it's a bit nasty that the old instance is first added to the RBM and then removed again.
        # maybe there is a way to prevent this? For example, giving the old parameters a 'dummy' RBM
        # like in the factor implementation. But then this dummy has to be initialised first...
        
        # initialise
        super(TransformedParameters, self).__init__(params.rbm, params.units_list, name)
        
        self.variables = params.variables
        for u, l in params.terms.items(): # in the terms, replace the vars by their transforms
            self.terms[u] = lambda vmap: theano.clone(l(vmap), transforms)
            
        for v, l in params.energy_gradients.items():
            self.energy_gradients[v] = lambda vmap: l(vmap) * transform_gradients[v] # chain rule
            
        for v, l in params.energy_gradient_sums.items():
            self.energy_gradient_sums[v] = lambda vmap: l(vmap) * transform_gradients[v] # chain rule
            
    def energy_term(self, vmap):
        old = self.encapsulated_params.energy_term(vmap)
        return theano.clone(old, self.transforms)
        
        

########NEW FILE########
__FILENAME__ = rbms
from morb.base import RBM
from morb import units, parameters

import theano
import theano.tensor as T

import numpy as np


### RBMS ###

class BinaryBinaryRBM(RBM): # the basic RBM, with binary visibles and binary hiddens
    def __init__(self, n_visible, n_hidden):
        super(BinaryBinaryRBM, self).__init__()
        # data shape
        self.n_visible = n_visible
        self.n_hidden = n_hidden
        # units
        self.v = units.BinaryUnits(self, name='v') # visibles
        self.h = units.BinaryUnits(self, name='h') # hiddens
        # parameters
        self.W = parameters.ProdParameters(self, [self.v, self.h], theano.shared(value = self._initial_W(), name='W'), name='W') # weights
        self.bv = parameters.BiasParameters(self, self.v, theano.shared(value = self._initial_bv(), name='bv'), name='bv') # visible bias
        self.bh = parameters.BiasParameters(self, self.h, theano.shared(value = self._initial_bh(), name='bh'), name='bh') # hidden bias
        
    def _initial_W(self):
        return np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   high  =  4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   size  =  (self.n_visible, self.n_hidden)),
                   dtype =  theano.config.floatX)
        
    def _initial_bv(self):
        return np.zeros(self.n_visible, dtype = theano.config.floatX)
        
    def _initial_bh(self):
        return np.zeros(self.n_hidden, dtype = theano.config.floatX)
              


class BinaryBinaryCRBM(BinaryBinaryRBM):
    def __init__(self, n_visible, n_hidden, n_context):
        super(BinaryBinaryCRBM, self).__init__(n_visible, n_hidden)
        # data shape
        self.n_context = n_context
        # units
        self.x = units.Units(self, name='x') # context
        # parameters
        self.A = parameters.ProdParameters(self, [self.x, self.v], theano.shared(value = self._initial_A(), name='A'), name='A') # context-to-visible weights
        self.B = parameters.ProdParameters(self, [self.x, self.h], theano.shared(value = self._initial_B(), name='B'), name='B') # context-to-hidden weights

    def _initial_A(self):
        return np.zeros((self.n_context, self.n_visible), dtype = theano.config.floatX)

    def _initial_B(self):
        return np.zeros((self.n_context, self.n_hidden), dtype = theano.config.floatX)



class GaussianBinaryRBM(RBM): # Gaussian visible units
    def __init__(self, n_visible, n_hidden):
        super(GaussianBinaryRBM, self).__init__()
        # data shape
        self.n_visible = n_visible
        self.n_hidden = n_hidden
        # units
        self.v = units.GaussianUnits(self, name='v') # visibles
        self.h = units.BinaryUnits(self, name='h') # hiddens
        # parameters
        parameters.FixedBiasParameters(self, self.v.precision_units)
        self.W = parameters.ProdParameters(self, [self.v, self.h], theano.shared(value = self._initial_W(), name='W'), name='W') # weights
        self.bv = parameters.BiasParameters(self, self.v, theano.shared(value = self._initial_bv(), name='bv'), name='bv') # visible bias
        self.bh = parameters.BiasParameters(self, self.h, theano.shared(value = self._initial_bh(), name='bh'), name='bh') # hidden bias
        
    def _initial_W(self):
        return np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   high  =  4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   size  =  (self.n_visible, self.n_hidden)),
                   dtype =  theano.config.floatX)
        
    def _initial_bv(self):
        return np.zeros(self.n_visible, dtype = theano.config.floatX)
        
    def _initial_bh(self):
        return np.zeros(self.n_hidden, dtype = theano.config.floatX)



class LearntPrecisionGaussianBinaryRBM(RBM):
    """
    Important: Wp and bvp should be constrained to be negative.
    """
    def __init__(self, n_visible, n_hidden):
        super(LearntPrecisionGaussianBinaryRBM, self).__init__()
        # data shape
        self.n_visible = n_visible
        self.n_hidden = n_hidden
        # units
        self.v = units.LearntPrecisionGaussianUnits(self, name='v') # visibles
        self.h = units.BinaryUnits(self, name='h') # hiddens
        # parameters
        self.Wm = parameters.ProdParameters(self, [self.v, self.h], theano.shared(value = self._initial_W(), name='Wm'), name='Wm') # weights
        self.Wp = parameters.ProdParameters(self, [self.v.precision_units, self.h], theano.shared(value = -np.abs(self._initial_W())/1000, name='Wp'), name='Wp') # weights
        self.bvm = parameters.BiasParameters(self, self.v, theano.shared(value = self._initial_bias(self.n_visible), name='bvm'), name='bvm') # visible bias
        self.bvp = parameters.BiasParameters(self, self.v.precision_units, theano.shared(value = self._initial_bias(self.n_visible), name='bvp'), name='bvp') # precision bias
        self.bh = parameters.BiasParameters(self, self.h, theano.shared(value = self._initial_bias(self.n_hidden), name='bh'), name='bh') # hidden bias
        
    def _initial_W(self):
        return np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   high  =  4*np.sqrt(6./(self.n_hidden+self.n_visible)),
                   size  =  (self.n_visible, self.n_hidden)),
                   dtype =  theano.config.floatX)
        
    def _initial_bias(self, n):
        return np.zeros(n, dtype = theano.config.floatX)


class LearntPrecisionSeparateGaussianBinaryRBM(RBM):
    """
    Important: Wp and bvp should be constrained to be negative.
    This RBM models mean and precision with separate hidden units.
    """
    def __init__(self, n_visible, n_hidden_mean, n_hidden_precision):
        super(LearntPrecisionSeparateGaussianBinaryRBM, self).__init__()
        # data shape
        self.n_visible = n_visible
        self.n_hidden_mean = n_hidden_mean
        self.n_hidden_precision = n_hidden_precision
        # units
        self.v = units.LearntPrecisionGaussianUnits(self, name='v') # visibles
        self.hm = units.BinaryUnits(self, name='hm') # hiddens for mean
        self.hp = units.BinaryUnits(self, name='hp') # hiddens for precision
        # parameters
        self.Wm = parameters.ProdParameters(self, [self.v, self.hm], theano.shared(value = self._initial_W(self.n_visible, self.n_hidden_mean), name='Wm'), name='Wm') # weights
        self.Wp = parameters.ProdParameters(self, [self.v.precision_units, self.hp], theano.shared(value = -np.abs(self._initial_W(self.n_visible, self.n_hidden_precision))/1000, name='Wp'), name='Wp') # weights
        self.bvm = parameters.BiasParameters(self, self.v, theano.shared(value = self._initial_bias(self.n_visible), name='bvm'), name='bvm') # visible bias
        self.bvp = parameters.BiasParameters(self, self.v.precision_units, theano.shared(value = self._initial_bias(self.n_visible), name='bvp'), name='bvp') # precision bias
        self.bhm = parameters.BiasParameters(self, self.hm, theano.shared(value = self._initial_bias(self.n_hidden_mean), name='bhm'), name='bhm') # hidden bias for mean
        self.bhp = parameters.BiasParameters(self, self.hp, theano.shared(value = self._initial_bias(self.n_hidden_precision)+1.0, name='bhp'), name='bhp') # hidden bias for precision
        
    def _initial_W(self, nv, nh):
        return np.asarray( np.random.uniform(
                   low   = -4*np.sqrt(6./(nv+nh)),
                   high  =  4*np.sqrt(6./(nv+nh)),
                   size  =  (nv, nh)),
                   dtype =  theano.config.floatX)
        
    def _initial_bias(self, n):
        return np.zeros(n, dtype = theano.config.floatX)



class TruncExpBinaryRBM(RBM): # RBM with truncated exponential visibles and binary hiddens
    def __init__(self, n_visible, n_hidden):
        super(TruncExpBinaryRBM, self).__init__()
        # data shape
        self.n_visible = n_visible
        self.n_hidden = n_hidden
        # units
        self.v = units.TruncatedExponentialUnits(self, name='v') # visibles
        self.h = units.BinaryUnits(self, name='h') # hiddens
        # parameters
        self.W = parameters.ProdParameters(self, [self.v, self.h], theano.shared(value = self._initial_W(), name='W'), name='W') # weights
        self.bv = parameters.BiasParameters(self, self.v, theano.shared(value = self._initial_bv(), name='bv'), name='bv') # visible bias
        self.bh = parameters.BiasParameters(self, self.h, theano.shared(value = self._initial_bh(), name='bh'), name='bh') # hidden bias
        
    def _initial_W(self):
#        return np.asarray( np.random.uniform(
#                   low   = -4*np.sqrt(6./(self.n_hidden+self.n_visible)),
#                   high  =  4*np.sqrt(6./(self.n_hidden+self.n_visible)),
#                   size  =  (self.n_visible, self.n_hidden)),
#                   dtype =  theano.config.floatX)

        return np.asarray( np.random.normal(0, 0.01,
                   size  =  (self.n_visible, self.n_hidden)),
                   dtype =  theano.config.floatX)
        
    def _initial_bv(self):
        return np.zeros(self.n_visible, dtype = theano.config.floatX)
        
    def _initial_bh(self):
        return np.zeros(self.n_hidden, dtype = theano.config.floatX)

########NEW FILE########
__FILENAME__ = samplers
import theano
import theano.tensor as T

# from theano.tensor.shared_randomstreams import RandomStreams
from theano.sandbox.rng_mrg import MRG_RandomStreams as RandomStreams # veel sneller
import numpy as np

numpy_rng = np.random.RandomState(123)
theano_rng = RandomStreams(numpy_rng.randint(2**30))

## samplers

def bernoulli(a):
    # a is the bernoulli parameter
    return theano_rng.binomial(size=a.shape, n=1, p=a, dtype=theano.config.floatX) 

def gaussian(a, var=1.0):
    # a is the mean, var is the variance (not std or precision!)
    std = T.sqrt(var)
    return theano_rng.normal(size=a.shape, avg=a, std=std, dtype=theano.config.floatX)

        

def multinomial(a):
    # 0 = minibatches
    # 1 = units
    # 2 = states
    p = a.reshape((a.shape[0]*a.shape[1], a.shape[2]))    
    # r 0 = minibatches * units
    # r 1 = states
    # this is the expected input for theano.nnet.softmax and theano_rng.multinomial
    s = theano_rng.multinomial(n=1, pvals=p, dtype=theano.config.floatX)    
    return s.reshape(a.shape) # reshape back to original shape
    

def exponential(a):
    uniform_samples = theano_rng.uniform(size=a.shape, dtype=theano.config.floatX)
    return (-1 / a) * T.log(1 - uniform_samples)


def truncated_exponential(a, maximum=1.0):
    uniform_samples = theano_rng.uniform(size=a.shape, dtype=theano.config.floatX)
    return (-1 / a) * T.log(1 - uniform_samples*(1 - T.exp(-a * maximum)))


def truncated_exponential_mean(a, maximum=1.0):
    # return (1 / a) + (maximum / (1 - T.exp(maximum*a))) # this is very unstable around a=0, even for a=0.001 it's already problematic.
    # here is a version that switches depending on the magnitude of the input
    m_real = (1 / a) + (maximum / (1 - T.exp(maximum*a)))
    m_approx = 0.5 - (1./12)*a + (1./720)*a**3 - (1./30240)*a**5 # + (1./1209600)*a**7 # this extra term is unnecessary, it's accurate enough
    return T.switch(T.abs_(a) > 0.5, m_real, m_approx)
 


def laplacian(b, mu=0.0):
    # laplacian distributition is only exponential family when mu=0!
    uniform_samples = theano_rng.uniform(size=b.shape, dtype=theano.config.floatX)
    return mu - b*T.sgn(uniform_samples-0.5) * T.log(1 - 2*T.abs_(uniform_samples-0.5))
    
    
    
## approximate gamma sampler
# Two approximations for the gamma function are defined.
# Windschitl is very fast, but problematic close to 0, and using the reflection formula
# causes discontinuities.
# Lanczos on the other hand is extremely accurate, but slower.
   
def _log_gamma_windschitl(z):
    """
    computes log(gamma(z)) using windschitl's approximation.
    """
    return 0.5 * (T.log(2*np.pi) - T.log(z)  + z * (2 * T.log(z) - 2 + T.log(z * T.sinh(1/z) + 1 / (810*(z**6)))))
    
def _log_gamma_ratio_windschitl(z, k):
    """
    computes log(gamma(z+k)/gamma(z)) using windschitl's approximation.
    """
    return _log_gamma_windschitl(z + k) - _log_gamma_windschitl(z)
    

def _log_gamma_lanczos(z):
    # optimised by nouiz. thanks!
    assert z.dtype.startswith("float")
    # reflection formula. Normally only used for negative arguments,
    # but here it's also used for 0 < z < 0.5 to improve accuracy in
    # this region.
    flip_z = 1 - z
    # because both paths are always executed (reflected and
    # non-reflected), the reflection formula causes trouble when the
    # input argument is larger than one.
    # Note that for any z > 1, flip_z < 0.
    # To prevent these problems, we simply set all flip_z < 0 to a
    # 'dummy' value. This is not a problem, since these computations
    # are useless anyway and are discarded by the T.switch at the end
    # of the function.
    flip_z = T.switch(flip_z < 0, 1, flip_z)
    log_pi = np.asarray(np.log(np.pi), dtype=z.dtype)
    small = log_pi - T.log(T.sin(np.pi * z)) - _log_gamma_lanczos_sub(flip_z)
    big = _log_gamma_lanczos_sub(z)
    return T.switch(z < 0.5, small, big)


def _log_gamma_lanczos_sub(z): # expanded version
    # optimised by nouiz. thanks!
    # Coefficients used by the GNU Scientific Library
    # note that vectorising this function and using .sum() turns out to be
    # really slow! possibly because the dimension across which is summed is
    # really small.
    g = 7
    p = np.array([0.99999999999980993, 676.5203681218851, -1259.1392167224028,
                  771.32342877765313, -176.61502916214059, 12.507343278686905,
                  -0.13857109526572012, 9.9843695780195716e-6,
                  1.5056327351493116e-7], dtype=z.dtype)
    z = z - 1
    x = p[0]
    for i in range(1, g + 2):
        x += p[i] / (z + i)
    t = z + g + 0.5
    pi = np.asarray(np.pi, dtype=z.dtype)
    log_sqrt_2pi = np.asarray(np.log(np.sqrt(2 * np.pi)), dtype=z.dtype)
    return log_sqrt_2pi + (z + 0.5) * T.log(t) - t + T.log(x)

    
def _log_gamma_ratio_lanczos(z, k):
    """
    computes log(gamma(z+k)/gamma(z)) using the lanczos approximation.
    """ 
    return _log_gamma_lanczos(z + k) - _log_gamma_lanczos(z)
    
 
def gamma_approx(k, theta=1):
    """
    Sample from a gamma distribution using the Wilson-Hilferty approximation.
    The gamma function itself is also approximated, so everything can be
    computed on the GPU (using the Lanczos approximation).
    """
    lmbda = 1/3.0 # according to Wilson and Hilferty
    mu = T.exp(_log_gamma_ratio_lanczos(k, lmbda))
    sigma = T.sqrt(T.exp(_log_gamma_ratio_lanczos(k, 2*lmbda)) - mu**2)
    normal_samples = theano_rng.normal(size=k.shape, avg=mu, std=sigma, dtype=theano.config.floatX)
    gamma_samples = theta * T.abs_(normal_samples ** 3)
    # The T.abs_ is technically incorrect. The problem is that, without it, this formula may yield
    # negative samples, which is impossible for the gamma distribution.
    # It was also noted that, for very small values of the shape parameter k, the distribution
    # of resulting samples is roughly symmetric around 0. By 'folding' the negative part
    # onto the positive part, we still get a decent approximation because of this.
    return gamma_samples
    
    
    
    


########NEW FILE########
__FILENAME__ = stats
from morb.base import Stats

import numpy as np

import theano


def gibbs_step(rbm, vmap, units_list, mean_field_for_stats=[], mean_field_for_gibbs=[]):
    # implements a single gibbs step, and makes sure mean field is only used where it should be.
    # returns two vmaps, one for stats and one for gibbs.
    # also enforces consistency between samples, between the gibbs vmap and the stats vmap.
    # the provided lists and vmaps are expected to be COMPLETE. Otherwise, the behaviour is unspecified.
    
    # first, find out which units we need to sample for the stats vmap, and which for the gibbs vmap.
    # Mean field will be used for the others.
    units_sample_stats = units_list[:] # make a copy
    units_mean_field_stats = []
    for u in mean_field_for_stats:
        if u in units_sample_stats:
            units_sample_stats.remove(u) # remove all mean field units from the sample list
            units_mean_field_stats.append(u) # add them to the mean field list instead

    units_sample_gibbs = units_list[:]
    units_mean_field_gibbs = []
    for u in mean_field_for_gibbs:
        if u in units_sample_gibbs:
            units_sample_gibbs.remove(u) # remove all mean field units from the sample list
            units_mean_field_gibbs.append(u) # add them to the mean field list instead

    # now we can compute the total list of units to sample.
    # By sampling them all in one go, we can enforce consistency.
    units_sample = list(set(units_sample_gibbs + units_sample_stats))
    sample_vmap = rbm.sample(units_sample, vmap)
    units_mean_field = list(set(units_mean_field_gibbs + units_mean_field_stats))
    mean_field_vmap = rbm.mean_field(units_mean_field, vmap)
    
    # now, construct the gibbs and stats vmaps
    stats_vmap = dict((u, sample_vmap[u]) for u in units_sample_stats)
    stats_vmap.update(dict((u, mean_field_vmap[u]) for u in units_mean_field_stats))
    gibbs_vmap = dict((u, sample_vmap[u]) for u in units_sample_gibbs)
    gibbs_vmap.update(dict((u, mean_field_vmap[u]) for u in units_mean_field_gibbs))
        
    return stats_vmap, gibbs_vmap


def cd_stats(rbm, v0_vmap, visible_units, hidden_units, context_units=[], k=1, mean_field_for_stats=[], mean_field_for_gibbs=[], persistent_vmap=None):
    # mean_field_for_gibbs is a list of units for which 'mean_field' should be used during gibbs sampling, rather than 'sample'.
    # mean_field_for_stats is a list of units for which 'mean_field' should be used to compute statistics, rather than 'sample'.

    # complete units lists
    visible_units = rbm.complete_units_list(visible_units)
    hidden_units = rbm.complete_units_list(hidden_units)
    context_units = rbm.complete_units_list(context_units)
    
    # complete the supplied vmap
    v0_vmap = rbm.complete_vmap(v0_vmap)
    
    # extract the context vmap, because we will need to merge it into all other vmaps
    context_vmap = dict((u, v0_vmap[u]) for u in context_units)

    h0_activation_vmap = dict((h, h.activation(v0_vmap)) for h in hidden_units)
    h0_stats_vmap, h0_gibbs_vmap = gibbs_step(rbm, v0_vmap, hidden_units, mean_field_for_stats, mean_field_for_gibbs)
            
    # add context
    h0_activation_vmap.update(context_vmap)
    h0_gibbs_vmap.update(context_vmap)
    h0_stats_vmap.update(context_vmap)
    
    exp_input = [v0_vmap[u] for u in visible_units]
    exp_context = [v0_vmap[u] for u in context_units]
    exp_latent = [h0_gibbs_vmap[u] for u in hidden_units]
    
    # scan requires a function that returns theano expressions, so we cannot pass vmaps in or out. annoying.
    def gibbs_hvh(*args):
        h0_gibbs_vmap = dict(zip(hidden_units, args))
        
        v1_in_vmap = h0_gibbs_vmap.copy()
        v1_in_vmap.update(context_vmap) # add context
        
        v1_activation_vmap = dict((v, v.activation(v1_in_vmap)) for v in visible_units)
        v1_stats_vmap, v1_gibbs_vmap = gibbs_step(rbm, v1_in_vmap, visible_units, mean_field_for_stats, mean_field_for_gibbs)

        h1_in_vmap = v1_gibbs_vmap.copy()
        h1_in_vmap.update(context_vmap) # add context

        h1_activation_vmap = dict((h, h.activation(h1_in_vmap)) for h in hidden_units)
        h1_stats_vmap, h1_gibbs_vmap = gibbs_step(rbm, h1_in_vmap, hidden_units, mean_field_for_stats, mean_field_for_gibbs)
            
        # get the v1 values in a fixed order
        v1_activation_values = [v1_activation_vmap[u] for u in visible_units]
        v1_gibbs_values = [v1_gibbs_vmap[u] for u in visible_units]
        v1_stats_values = [v1_stats_vmap[u] for u in visible_units]
        
        # same for the h1 values
        h1_activation_values = [h1_activation_vmap[u] for u in hidden_units]
        h1_gibbs_values = [h1_gibbs_vmap[u] for u in hidden_units]
        h1_stats_values = [h1_stats_vmap[u] for u in hidden_units]
        
        return v1_activation_values + v1_stats_values + v1_gibbs_values + \
               h1_activation_values + h1_stats_values + h1_gibbs_values
    
    
    # support for persistent CD
    if persistent_vmap is None:
        chain_start = exp_latent
    else:
        chain_start = [persistent_vmap[u] for u in hidden_units]
    
    
    # The 'outputs_info' keyword argument of scan configures how the function outputs are mapped to the inputs.
    # in this case, we want the h1_gibbs_vmap values to map onto the function arguments, so they become
    # h0_gibbs_vmap values in the next iteration. To this end, we construct outputs_info as follows:
    outputs_info = [None] * (len(exp_input)*3) + [None] * (len(exp_latent)*2) + list(chain_start)
    # 'None' indicates that this output is not used in the next iteration.
    
    exp_output_all_list, theano_updates = theano.scan(gibbs_hvh, outputs_info = outputs_info, n_steps = k)
    # we only need the final outcomes, not intermediary values
    exp_output_list = [out[-1] for out in exp_output_all_list]
            
    # reconstruct vmaps from the exp_output_list.
    n_input, n_latent = len(visible_units), len(hidden_units)
    vk_activation_vmap = dict(zip(visible_units, exp_output_list[0:1*n_input]))
    vk_stats_vmap = dict(zip(visible_units, exp_output_list[1*n_input:2*n_input]))
    vk_gibbs_vmap = dict(zip(visible_units, exp_output_list[2*n_input:3*n_input]))
    hk_activation_vmap = dict(zip(hidden_units, exp_output_list[3*n_input:3*n_input+1*n_latent]))
    hk_stats_vmap = dict(zip(hidden_units, exp_output_list[3*n_input+1*n_latent:3*n_input+2*n_latent]))
    hk_gibbs_vmap = dict(zip(hidden_units, exp_output_list[3*n_input+2*n_latent:3*n_input+3*n_latent]))
    
    # add the Theano updates for the persistent CD states:
    if persistent_vmap is not None:
        for u, v in persistent_vmap.items():
            theano_updates[v] = hk_gibbs_vmap[u] # this should be the gibbs vmap, and not the stats vmap!
    
    activation_data_vmap = v0_vmap.copy() # TODO: this doesn't really make sense to have in an activation vmap!
    activation_data_vmap.update(h0_activation_vmap)
    activation_model_vmap = vk_activation_vmap.copy()
    activation_model_vmap.update(context_vmap)
    activation_model_vmap.update(hk_activation_vmap)
    
    stats = Stats(theano_updates) # create a new stats object
    
    # store the computed stats in a dictionary of vmaps.
    stats_data_vmap = v0_vmap.copy()
    stats_data_vmap.update(h0_stats_vmap)
    stats_model_vmap = vk_stats_vmap.copy()
    stats_model_vmap.update(context_vmap)
    stats_model_vmap.update(hk_stats_vmap)
    stats.update({
      'data': stats_data_vmap,
      'model': stats_model_vmap,
    })
            
    stats['data_activation'] = activation_data_vmap
    stats['model_activation'] = activation_model_vmap
        
    return stats


########NEW FILE########
__FILENAME__ = trainers
from morb.base import Trainer

import theano
import theano.tensor as T

import numpy as np

class MinibatchTrainer(Trainer):
    # use self.rbm, self.umap, self.get_updates(vmap)
    def compile_function(self, initial_vmap, monitors=[], name='func', mb_size=32, train=True, mode=None):
        # setting train=False is useful when compiling a function for evaluation only, i.e. no training.
        # this is interesting when one wants to evaluate training progress on a validation set, for example.
        # then the variables will not be updated, but there might still be updates from scan operations
        # for example, so we still have to fetch them!
        updates = self.get_theano_updates(train) 
        
        # initialise data sets
        data_sets = {}
        for u, v in initial_vmap.items():
            shape = (1,) * v.ndim
            data_sets[u] = theano.shared(value = np.zeros(shape, dtype=theano.config.floatX),
                                          name="dataset for '%s'"  % u.name)
                                          
        index = T.lscalar() # index to a minibatch
        
        # construct givens for the compiled theano function - mapping variables to data
        givens = dict((initial_vmap[u], data_sets[u][index*mb_size:(index+1)*mb_size]) for u in initial_vmap)
            
        TF = theano.function([index], monitors,
            updates = updates, givens = givens, name = name, mode = mode)    
                
        def func(dmap):
            # dmap is a dict that maps unit types on their respective datasets (numeric).
            units_list = dmap.keys()
            data_sizes = [int(np.ceil(dmap[u].shape[0] / float(mb_size))) for u in units_list]
            
            if data_sizes.count(data_sizes[0]) != len(data_sizes): # check if all data sizes are equal
                raise RuntimeError("The sizes of the supplied datasets for the different input units are not equal.")

            data_cast = [dmap[u].astype(theano.config.floatX) for u in units_list]
            
            for i, u in enumerate(units_list):
                data_sets[u].set_value(data_cast[i], borrow=True)
                
            for batch_index in xrange(min(data_sizes)):
                yield TF(batch_index)
                
        return func
                        


########NEW FILE########
__FILENAME__ = units
from morb.base import Units, ProxyUnits
from morb import samplers, activation_functions
import theano.tensor as T
import numpy as np


class BinaryUnits(Units):
    def success_probability_from_activation(self, vmap):
        return activation_functions.sigmoid(vmap[self])
        
    def success_probability(self, vmap):
        return self.success_probability_from_activation({ self: self.activation(vmap) })

    def sample_from_activation(self, vmap):
        p = self.success_probability_from_activation(vmap)
        return samplers.bernoulli(p)
        
    def mean_field_from_activation(self, vmap):
        return activation_functions.sigmoid(vmap[self])

    def free_energy_term_from_activation(self, vmap):
        # softplus of unit activations, summed over # units
        s = - T.nnet.softplus(vmap[self])
        # sum over all but the minibatch dimension
        return T.sum(s, axis=range(1, s.ndim))
        
    def log_prob_from_activation(self, vmap, activation_vmap):
        # the log probability mass function is actually the  negative of the
        # cross entropy between the unit values and the activations
        p = self.success_probability_from_activation(activation_vmap)
        return vmap[self] * T.log(p) + (1 - vmap[self]) * T.log(1 - p)
  
class GaussianPrecisionProxyUnits(ProxyUnits):
    def __init__(self, rbm, units, name=None):
        func = lambda x: x**2 / 2.0
        super(GaussianPrecisionProxyUnits, self).__init__(rbm, units, func, name)
       
class GaussianUnits(Units):
    def __init__(self, rbm, name=None):
        super(GaussianUnits, self).__init__(rbm, name)
        proxy_name = (name + "_precision" if name is not None else None)
        self.precision_units = GaussianPrecisionProxyUnits(rbm, self, name=proxy_name)
        self.proxy_units = [self.precision_units]
        
    def mean_from_activation(self, vmap): # mean is the parameter
        return vmap[self]
        
    def mean(self, vmap):
        return self.mean_from_activation({ self: self.activation(vmap) })

    def sample_from_activation(self, vmap):
        mu = self.mean_from_activation(vmap)
        return samplers.gaussian(mu)
        
    def mean_field_from_activation(self, vmap):
        return vmap[self]

    def log_prob_from_activation(self, vmap, activation_vmap):
        return - np.log(np.sqrt(2*np.pi)) - ((vmap[self] - activation_vmap[self])**2 / 2.0)



class LearntPrecisionGaussianProxyUnits(ProxyUnits):
    def __init__(self, rbm, units, name=None):
        func = lambda x: x**2
        super(LearntPrecisionGaussianProxyUnits, self).__init__(rbm, units, func, name)
             
class LearntPrecisionGaussianUnits(Units):
    def __init__(self, rbm, name=None):
        super(LearntPrecisionGaussianUnits, self).__init__(rbm, name)
        proxy_name = (name + "_precision" if name is not None else None)
        self.precision_units = LearntPrecisionGaussianProxyUnits(rbm, self, name=proxy_name)
        self.proxy_units = [self.precision_units]
        
    def mean_from_activation(self, vmap):
        return vmap[self] / self.precision_from_activation(vmap)
    
    def mean(self, vmap):
        a1 = self.activation(vmap)
        a2 = self.precision_units.activation(vmap)
        return self.mean_from_activation({ self: a1, self.precision_units: a2 })
    
    def variance_from_activation(self, vmap):
        return 1 / self.precision_from_activation(vmap)
    
    def variance(self, vmap):
        a1 = self.activation(vmap)
        a2 = self.precision_units.activation(vmap)
        return self.variance_from_activation({ self: a1, self.precision_units: a2 })
    
    def precision_from_activation(self, vmap):
        return -2 * vmap[self.precision_units]
    
    def precision(self, vmap):
        a1 = self.activation(vmap)
        a2 = self.precision_units.activation(vmap)
        return self.precision_from_activation({ self: a1, self.precision_units: a2 })
        
    def sample_from_activation(self, vmap):
        mu = self.mean_from_activation(vmap)
        sigma2 = self.variance_from_activation(vmap)
        return samplers.gaussian(mu, sigma2)
        
    def sample(self, vmap):
        a1 = self.activation(vmap)
        a2 = self.precision_units.activation(vmap)
        return self.sample_from_activation({ self: a1, self.precision_units: a2 })
    
    def log_prob(self, vmap):
        a1 = self.activation(vmap)
        a2 = self.precision_units.activation(vmap)
        activation_vmap = { self: a1, self.precision_units: a2 }
        return self.log_prob_from_activation(vmap, activation_vmap)
        
    def log_prob_from_activation(self, vmap, activation_vmap):
        var = self.variance_from_activation(activation_vmap)
        mean = self.mean_from_activation(activation_vmap)
        return - np.log(np.sqrt(2 * np.pi * var)) - ((vmap[self] - mean)**2 / (2.0 * var))
        
        
       
# TODO later: gaussian units with custom fixed variance (maybe per-unit). This probably requires two proxies.

class SoftmaxUnits(Units):
    # 0 = minibatches
    # 1 = units
    # 2 = states
    def probabilities_from_activation(self, vmap):
        return activation_functions.softmax(vmap[self])
    
    def probabilities(self, vmap):
        return self.probabilities_from_activation({ self: self.activation(vmap) })
    
    def sample_from_activation(self, vmap):
        p = self.probabilities_from_activation(vmap)
        return samplers.multinomial(p)


class SoftmaxWithZeroUnits(Units):
    """
    Like SoftmaxUnits, but in this case a zero state is possible, yielding N+1 possible states in total.
    """
    def probabilities_from_activation(self, vmap):
        return activation_functions.softmax_with_zero(vmap[self])
        
    def probabilities(self, vmap):
        return self.probabilities_from_activation({ self: self.activation(vmap) })
    
    def sample_from_activation(self, vmap):
        p0 = self.probabilities_from_activation(vmap)
        s0 = samplers.multinomial(p0)
        s = s0[:, :, :-1] # chop off the last state (zero state)
        return s


class TruncatedExponentialUnits(Units):
    def rate_from_activation(self, vmap): # lambda
        return -vmap[self] # lambda = -activation!
        
    def rate(self, vmap):
        return self.rate_from_activation({ self: self.activation(vmap) })

    def sample_from_activation(self, vmap):
        rate = self.rate_from_activation(vmap)
        return samplers.truncated_exponential(rate)
        
    def mean_field_from_activation(self, vmap):
        rate = self.rate_from_activation(vmap)
        return samplers.truncated_exponential_mean(rate)
        
    def log_prob_from_activation(self, vmap, activation_vmap):
        rate = self.rate_from_activation(activation_vmap)
        return T.log(rate) - rate * vmap[self] - T.log(1 - T.exp(-rate))


class ExponentialUnits(Units):
    def rate_from_activation(self, vmap): # lambda
        return -vmap[self] # lambda = -activation!
        
    def rate(self, vmap):
        return self.rate_from_activation({ self: self.activation(vmap) })

    def sample_from_activation(self, vmap):
        rate = self.rate_from_activation(vmap)
        return samplers.exponential(rate) # lambda = -activation!
        
    def mean_field_from_activation(self, vmap):
        return 1.0 / self.rate_from_activation(vmap)
        
    def log_prob_from_activation(self, vmap, activation_vmap):
        rate = self.rate_from_activation(activation_vmap)
        return T.log(rate) - rate * vmap[self]
        
        

class NRELUnits(Units):
    """
    Noisy rectified linear units from 'Rectified Linear Units Improve Restricted Boltzmann Machines'
    by Nair & Hinton (ICML 2010)
    
    WARNING: computing the energy or free energy of a configuration does not have the same semantics
    as usual with NReLUs, because each ReLU is actually the sum of an infinite number of Bernoulli
    units with offset biases. The energy depends on the individual values of these Bernoulli units,
    whereas only the sum is ever sampled (approximately).
    
    See: http://metaoptimize.com/qa/questions/8524/energy-function-of-an-rbm-with-noisy-rectified-linear-units-nrelus
    """
    def sample_from_activation(self, vmap):
        s = vmap[self] + samplers.gaussian(0, T.nnet.sigmoid(vmap[self])) # approximation: linear + gaussian noise
        return T.max(0, s) # rectify
        
    def mean_field_from_activation(self, vmap):
        return T.max(0, vmap[self])
    
        
        
        
class GammaLogProxyUnits(ProxyUnits):
    def __init__(self, rbm, units, name=None):
        func = lambda x: T.log(x)
        super(GammaLogProxyUnits, self).__init__(rbm, units, func, name)
             
class GammaUnits(Units):
    """
    Two-parameter gamma distributed units, using an approximate sampling procedure for speed.
    The activations should satisfy some constraints:
    - the activation of the GammaUnits should be strictly negative.
    - the activation of the GammaLogProxyUnits should be strictly larger than -1.
    It is recommended to use a FixedBiasParameters instance for the GammaLogProxyUnits,
    so that the 'remaining' part of the activation should be strictly positive. This
    constraint is much easier to satisfy.
    """
    def __init__(self, rbm, name=None):
        super(GammaUnits, self).__init__(rbm, name)
        proxy_name = (name + "_log" if name is not None else None)
        self.log_units = GammaLogProxyUnits(rbm, self, name=proxy_name)
        self.proxy_units = [self.log_units]

    def sample_from_activation(self, vmap):
        a1 = vmap[self]
        a2 = vmap[self.log_units]
        return samplers.gamma_approx(a2 + 1, -1 / a1)
        
    def sample(self, vmap):
        a1 = self.activation(vmap)
        a2 = self.log_units.activation(vmap)
        return self.sample_from_activation({ self: a1, self.log_units: a2 })

    def k_from_activation(self, vmap):
        a2 = vmap[self.log_units]
        return a2 + 1

    def k(self, vmap):
        a1 = self.activation(vmap
)
        a2 = self.log_units.activation(vmap)
        return self.k_from_activation({ self: a1, self.log_units: a2 })        

    def theta_from_activation(self, vmap):
        a1 = vmap[self]
        return -1.0 / a1

    def theta(self, vmap):
        a1 = self.activation(vmap)
        a2 = self.log_units.activation(vmap)
        return self.theta_from_activation({ self: a1, self.log_units: a2 })     

    def mean_from_activation(self, vmap):
        k = self.k_from_activation(vmap)
        theta = self.theta_from_activation(vmap)
        return k * theta

    def mean(self, vmap):
        a1 = self.activation(vmap)
        a2 = self.log_units.activation(vmap)
        return self.mean_from_activation({ self: a1, self.log_units: a2 })     



class SymmetricBinaryProxyUnits(ProxyUnits):
    def __init__(self, rbm, units, name=None):
        func = lambda x: 1 - x # flip
        super(SymmetricBinaryProxyUnits, self).__init__(rbm, units, func, name)


class SymmetricBinaryUnits(Units):
    """
    Symmetric binary units can be used to include both x and (1 - x) in the energy
    function. This is useful in cases where parameters have to be constrained to
    yield valid conditional distributions. Making the energy function symmetric
    allows for these constraints to be much weaker. For more info, refer to
    http://metaoptimize.com/qa/questions/9628/symmetric-energy-functions-for-rbms
    and the paper referenced there.
    """
    def __init__(self, rbm, name=None):
        super(SymmetricBinaryUnits, self).__init__(rbm, name)
        proxy_name = (name + '_flipped' if name is not None else None)
        self.flipped_units = SymmetricBinaryProxyUnits(rbm, self, name=proxy_name)
        self.proxy_units = [self.flipped_units]
        
    def sample_from_activation(self, vmap):
        p = activation_functions.sigmoid(vmap[self] - vmap[self.flipped_units])
        return samplers.bernoulli(p)
        
    def mean_field_from_activation(self, vmap):
        return activation_functions.sigmoid(vmap[self] - vmap[self.flipped_units])

    def free_energy_term_from_activation(self, vmap):
        # softplus of unit activations, summed over # units
        s = - T.nnet.softplus(vmap[self] - vmap[self.flipped_units])
        # sum over all but the minibatch dimension
        return T.sum(s, axis=range(1, s.ndim))


########NEW FILE########
__FILENAME__ = updaters
from morb.base import Updater, SumUpdater, ScaleUpdater
import samplers

import theano
import theano.tensor as T
import numpy as np
        

class SelfUpdater(Updater):
    def get_update(self):
        return self.variable

DecayUpdater = SelfUpdater
# weight decay: the update == the parameter values themselves
# (decay constant is taken care of by ScaleUpdater)       

class MomentumUpdater(Updater):
    def __init__(self, pu, momentum, variable_shape):
        # IMPORTANT: since this Updater has state, it requires the shape of the parameter
        # variable to be supplied at initialisation.
        super(MomentumUpdater, self).__init__(pu.variable, pu.stats_list)
        self.pu = pu
        self.momentum = momentum
        self.variable_shape = variable_shape
        
        name = pu.variable.name + "_momentum"
        self.previous_update = theano.shared(value = np.zeros(self.variable_shape, dtype=theano.config.floatX), name=name)
        
        # Update calculation has to happen in __init__, because else if get_theano_updates
        # is called before get_update, the state update will not be included in the dict.
        # This is a bit nasty, and it probably applies for all updaters with state.
        # maybe this is a design flaw?
        self.update = self.pu.get_update() + self.momentum * self.previous_update
        self.theano_updates = { self.previous_update: self.update }
                    
    def get_update(self):
        return self.update
        
    def get_theano_updates(self):
        u = self.theano_updates.copy() # the MomentumUpdater's own state updates
        u.update(self.pu.get_theano_updates()) # the state updates of the contained Updater
        return u


class CDUpdater(Updater):
    def __init__(self, rbm, variable, stats):
        super(CDUpdater, self).__init__(variable, [stats])
        # this updater has only one stats object, so make it more conveniently accessible
        self.stats = stats
        self.rbm = rbm
        
    def get_update(self):
        positive_term = self.rbm.energy_gradient_sum(self.variable, self.stats['data'])
        negative_term = self.rbm.energy_gradient_sum(self.variable, self.stats['model'])
        
        return positive_term - negative_term
                
    
class SparsityUpdater(Updater):
    def __init__(self, rbm, variable, sparsity_targets, stats):
        # sparsity_targets is a dict mapping Units instances to their target activations
        super(SparsityUpdater, self).__init__(variable, [stats])
        self.stats = stats
        self.rbm = rbm
        self.sparsity_targets = sparsity_targets
        
    def get_update(self):        
        # modify vmap: subtract target values
        # this follows the formulation in 'Biasing RBMs to manipulate latent selectivity and sparsity' by Goh, Thome and Cord (2010), formulas (8) and (9).
        vmap = self.stats['data'].copy()
        for u, target in self.sparsity_targets.items():
            if u in vmap:
                vmap[u] -= target
        
        return - self.rbm.energy_gradient_sum(self.variable, vmap) # minus sign is important!
        

class BoundUpdater(Updater):
    """
    Forces the parameter to be larger than (default) or smaller than a given value.
    When type='lower', the bound is a lower bound. This is the default behaviour.
    When type='upper', the bound is an upper bound.
    The value of the bound is 0 by default, so if no extra arguments are supplied,
    this updater will force the parameter values to be positive.
    The bound is always inclusive.
    """
    def __init__(self, pu, bound=0, type='lower'):  
        super(BoundUpdater, self).__init__(pu.variable, pu.stats_list)
        self.pu = pu
        self.bound = bound
        self.type = type
                    
    def get_update(self):
        update = self.pu.get_update()
        if self.type == 'lower':
            condition = update >= self.bound
        else: # type is 'upper'
            condition = update <= self.bound
        # return T.switch(condition, update, T.ones_like(update) * self.bound)
        return T.switch(condition, update, self.variable)
      
    def get_theano_updates(self):
        # The BoundUpdater has no state, so the only updates that should be returned
        # are those of the encapsulated updater.
        return self.pu.get_theano_updates()
        
        
        
class GradientUpdater(Updater):
    """
    Takes any objective in the form of a scalar Theano expression and uses T.grad
    to compute the update with respect to the given parameter variable.
    
    This can be used to train/finetune a model supervisedly or as an auto-
    encoder, for example.
    """
    def __init__(self, objective, variable, theano_updates={}):
        """
        the theano_updates argument can be used to pass in updates if the objective
        contains a scan op or something.
        """
        super(GradientUpdater, self).__init__(variable)
        self.update = T.grad(objective, variable)
        self.theano_updates = theano_updates
        
    def get_update(self):
        return self.update
        
    def get_theano_updates(self):
        return self.theano_updates



# class DenoisingScoreMatchingUpdater(Updater):
#     """
#     implements the denoising version of the score matching objective, an alternative to
#     maximum likelihood that doesn't require an approximation of the partition function.

#     This version uses a Gaussian kernel. Furthermore, it adds the scale factor 1/sigma**2
#     to the free energy of the model, as described in "A connection between score matching
#     and denoising autoencoders" by Vincent et al., such that it yields the denoising
#     autoencoder objective for a Gaussian-Bernoulli RBM.
    
#     This approach is only valid if the domain of the input is the real numbers. That means it
#     won't work for binary input units, or other unit types that don't define a distribution
#     on the entire real line. In practice, this is used almost exclusively with Gaussian
#     visible units.

#     std: noise level
#     """
#     def __init__(self, rbm, visible_units, hidden_units, v0_vmap, std):
#         noise_map = {}
#         noisy_vmap = {}
#         for vu in visible_units:
#             noise_map[vu] = samplers.theano_rng.normal(size=v0_vmap[vu].shape, avg=0.0, std=std, dtype=theano.config.floatX)
#             noisy_vmap[vu] = v0_vmap[vu] + noise_map[vu]

#         free_energy = rbm.free_energy(hidden_units, noisy_vmap)
#         scores = [T.grad(free_energy, noisy_vmap[u]) for u in visible_units]
#         score_map = dict(zip(visible_units, scores))

#         terms = []
#         for vu in visible_units:
#             terms.append(T.sum(T.mean((score_map[vu] + noise_map[vu]) ** 2, 0))) # mean over minibatches

#         self.update = sum(terms)

#     def get_update(self):
#         return self.update



########NEW FILE########
