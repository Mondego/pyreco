__FILENAME__ = cc_layers
"""
Layers using the cuda-convnet Theano wrappers that are part of pylearn2.
"""

import theano 
import theano.tensor as T
import numpy as np

import layers 

from theano.sandbox.cuda.basic_ops import gpu_contiguous
from pylearn2.sandbox.cuda_convnet.filter_acts import FilterActs
from pylearn2.sandbox.cuda_convnet.pool import MaxPool
from pylearn2.sandbox.cuda_convnet.stochastic_pool import StochasticMaxPool, WeightedMaxPool
from pylearn2.sandbox.cuda_convnet.response_norm import CrossMapNorm
from theano.sandbox.cuda import host_from_gpu


class CudaConvnetInput2DLayer(layers.Input2DLayer):
    """
    Like Input2DLayer, but the data is expected to be in c01b order instead of bc01.
    """
    def get_output_shape(self):
        return (self.n_features, self.width, self.height, self.mb_size) # c01b instead of bc01



class CudaConvnetConv2DLayer(object):
    def __init__(self, input_layer, n_filters, filter_size, weights_std, init_bias_value, stride=1, nonlinearity=layers.rectify, dropout=0., partial_sum=None, pad=0, untie_biases=False):
        """
        Only the valid border mode is supported.

        n_filters should be a multiple of 16
        """
        self.input_layer = input_layer
        self.n_filters = n_filters
        self.filter_size = filter_size
        self.weights_std = np.float32(weights_std)
        self.init_bias_value = np.float32(init_bias_value)
        self.stride = stride
        self.nonlinearity = nonlinearity
        self.dropout = dropout
        self.partial_sum = partial_sum
        self.pad = pad
        self.untie_biases = untie_biases
        # if untie_biases == True, each position in the output map has its own bias (as opposed to having the same bias everywhere for a given filter)
        self.mb_size = self.input_layer.mb_size

        self.input_shape = self.input_layer.get_output_shape()

        self.filter_shape = (self.input_shape[0], filter_size, filter_size, n_filters)

        self.W = layers.shared_single(4) # theano.shared(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)

        if self.untie_biases:
            self.b = layers.shared_single(3)
        else:
            self.b = layers.shared_single(1) # theano.shared(np.ones(n_filters).astype(np.float32) * self.init_bias_value)

        self.params = [self.W, self.b]
        self.bias_params = [self.b]
        self.reset_params()

        self.filter_acts_op = FilterActs(stride=self.stride, partial_sum=self.partial_sum, pad=self.pad)

    def reset_params(self):
        self.W.set_value(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)

        if self.untie_biases:
            self.b.set_value(np.ones(self.get_output_shape()[:3]).astype(np.float32) * self.init_bias_value)
        else:
            self.b.set_value(np.ones(self.n_filters).astype(np.float32) * self.init_bias_value)

    def get_output_shape(self):
        output_width = (self.input_shape[1] + 2 * self.pad - self.filter_size + self.stride) // self.stride
        output_height = (self.input_shape[2] + 2 * self.pad  - self.filter_size + self.stride) // self.stride        
        output_shape = (self.n_filters, output_width, output_height, self.mb_size)
        return output_shape

    def output(self, input=None, dropout_active=True, *args, **kwargs):
        if input == None:
            input = self.input_layer.output(dropout_active=dropout_active, *args, **kwargs)

        if dropout_active and (self.dropout > 0.):
            retain_prob = 1 - self.dropout
            mask = layers.srng.binomial(input.shape, p=retain_prob, dtype='int32').astype('float32')
                # apply the input mask and rescale the input accordingly. By doing this it's no longer necessary to rescale the weights at test time.
            input = input / retain_prob * mask

        contiguous_input = gpu_contiguous(input)
        contiguous_filters = gpu_contiguous(self.W)
        conved = self.filter_acts_op(contiguous_input, contiguous_filters)

        if self.untie_biases:
            conved += self.b.dimshuffle(0, 1, 2, 'x')
        else:
            conved += self.b.dimshuffle(0, 'x', 'x', 'x')

        return self.nonlinearity(conved)




class CudaConvnetPooling2DLayer(object):
    def __init__(self, input_layer, pool_size, stride=None): # pool_size is an INTEGER here!
        """
        pool_size is an INTEGER, not a tuple. We can only do square pooling windows.
        
        if the stride is none, it is taken to be the same as the pool size.

        borders are never ignored.
        """
        self.pool_size = pool_size
        self.stride = stride if stride is not None else pool_size
        self.input_layer = input_layer
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.pool_op = MaxPool(ds=self.pool_size, stride=self.stride)

    def get_output_shape(self):
        input_shape = self.input_layer.get_output_shape() # convert to list because we cannot assign to a tuple element
        w, h = input_shape[1], input_shape[2]

        new_w = int(np.ceil(float(w - self.pool_size + self.stride) / self.stride))
        new_h = int(np.ceil(float(h - self.pool_size + self.stride) / self.stride))

        return (input_shape[0], new_w, new_h, input_shape[3])

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)
        contiguous_input = gpu_contiguous(input)
        return self.pool_op(contiguous_input)




class CudaConvnetStochasticPooling2DLayer(object):
    def __init__(self, input_layer, pool_size, stride=None): # pool_size is an INTEGER here!
        """
        This implements stochastic pooling as in Zeiler et al. 2013 to replace max pooling.
        Pooling is stochastic by default. When dropout_active=True, weighted pooling is used
        instead. As a result it is not possible to enable/disable stochastic pooling and
        dropout separately within a network, but the use cases for that should be rare.
        Usually we want both on during training, and both off at test time.

        pool_size is an INTEGER, not a tuple. We can only do square pooling windows.
        
        if the stride is none, it is taken to be the same as the pool size.

        borders are never ignored.
        """
        self.pool_size = pool_size
        self.stride = stride if stride is not None else pool_size
        self.input_layer = input_layer
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.stochastic_pool_op = StochasticMaxPool(ds=self.pool_size, stride=self.stride)
        self.weighted_pool_op = WeightedMaxPool(ds=self.pool_size, stride=self.stride)

    def get_output_shape(self):
        input_shape = self.input_layer.get_output_shape() # convert to list because we cannot assign to a tuple element
        w, h = input_shape[1], input_shape[2]

        new_w = int(np.ceil(float(w - self.pool_size + self.stride) / self.stride))
        new_h = int(np.ceil(float(h - self.pool_size + self.stride) / self.stride))

        return (input_shape[0], new_w, new_h, input_shape[3])

    def output(self, dropout_active=True, *args, **kwargs):
        input = self.input_layer.output(dropout_active=dropout_active, *args, **kwargs)
        contiguous_input = gpu_contiguous(input)

        if dropout_active:
            return self.stochastic_pool_op(contiguous_input)
        else:
            return self.weighted_pool_op(contiguous_input)






class CudaConvnetCrossMapNormLayer(object):
    def __init__(self, input_layer, alpha=1e-4, beta=0.75, size_f=5, blocked=True):
        self.alpha = alpha
        self.beta = beta
        self.size_f = size_f
        self.blocked = blocked
        self.input_layer = input_layer
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.norm_op = CrossMapNorm(size_f=size_f, add_scale=alpha, pow_scale=beta, blocked=blocked)

    def get_output_shape(self):
        # output shape is the same as the input shape
        return self.input_layer.get_output_shape() 

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)
        contiguous_input = gpu_contiguous(input)
        return self.norm_op(contiguous_input)[0]




class ShuffleC01BToBC01Layer(object):
    """
    This layer dimshuffles 4D input for interoperability between C01B and BC01 ops.
    C01B (cuda convnet) -> BC01 (theano)
    """
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

    def get_output_shape(self):
        input_shape = self.input_layer.get_output_shape()
        return (input_shape[3], input_shape[0], input_shape[1], input_shape[2])

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)
        return input.dimshuffle(3, 0, 1, 2)


class ShuffleBC01ToC01BLayer(object):
    """
    This layer dimshuffles 4D input for interoperability between C01B and BC01 ops.
    BC01 (theano) -> C01B (cuda convnet)
    """
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

    def get_output_shape(self):
        input_shape = self.input_layer.get_output_shape()
        return (input_shape[1], input_shape[2], input_shape[3], input_shape[0])

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)
        return input.dimshuffle(1, 2, 3, 0)




class CudaConvnetCircularConv2DLayer(object):
    def __init__(self, input_layer, n_filters, filter_size, weights_std, init_bias_value, stride=1, nonlinearity=layers.rectify, dropout=0., partial_sum=None, untie_biases=False):
        """
        This is a convolution which is circular in the 0-direction, and valid in the 1-direction.

        n_filters should be a multiple of 16
        """
        self.input_layer = input_layer
        self.n_filters = n_filters
        self.filter_size = filter_size
        self.weights_std = np.float32(weights_std)
        self.init_bias_value = np.float32(init_bias_value)
        self.stride = stride
        self.nonlinearity = nonlinearity
        self.dropout = dropout
        self.partial_sum = partial_sum
        self.untie_biases = untie_biases
        # if untie_biases == True, each position in the output map has its own bias (as opposed to having the same bias everywhere for a given filter)
        self.mb_size = self.input_layer.mb_size

        self.input_shape = self.input_layer.get_output_shape()

        self.filter_shape = (self.input_shape[0], filter_size, filter_size, n_filters)

        self.W = layers.shared_single(4) # theano.shared(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)

        if self.untie_biases:
            self.b = layers.shared_single(3)
        else:
            self.b = layers.shared_single(1) # theano.shared(np.ones(n_filters).astype(np.float32) * self.init_bias_value)

        self.params = [self.W, self.b]
        self.bias_params = [self.b]
        self.reset_params()

        self.filter_acts_op = FilterActs(stride=self.stride, partial_sum=self.partial_sum)

    def reset_params(self):
        self.W.set_value(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)

        if self.untie_biases:
            self.b.set_value(np.ones(self.get_output_shape()[:3]).astype(np.float32) * self.init_bias_value)
        else:
            self.b.set_value(np.ones(self.n_filters).astype(np.float32) * self.init_bias_value)

    def get_output_shape(self):
        # output_width = (self.input_shape[1] - self.filter_size + self.stride) // self.stride
        output_width = self.input_shape[1] // self.stride # because it's a circular convolution, this dimension is just divided by the stride.
        output_height = (self.input_shape[2] - self.filter_size + self.stride) // self.stride # in this direction it's still valid though.       
        output_shape = (self.n_filters, output_width, output_height, self.mb_size)
        return output_shape

    def output(self, input=None, dropout_active=True, *args, **kwargs):
        if input == None:
            input = self.input_layer.output(dropout_active=dropout_active, *args, **kwargs)

        if dropout_active and (self.dropout > 0.):
            retain_prob = 1 - self.dropout
            mask = layers.srng.binomial(input.shape, p=retain_prob, dtype='int32').astype('float32')
                # apply the input mask and rescale the input accordingly. By doing this it's no longer necessary to rescale the weights at test time.
            input = input / retain_prob * mask

        # pad input so the valid convolution amounts to a circular one.
        # we need to copy (filter_size - stride) values from one side to the other
        input_padded = T.zeros((input.shape[0], input.shape[1] + self.filter_size - self.stride, input.shape[2], input.shape[3]))
        input_padded = T.set_subtensor(input_padded[:, :input.shape[1], :, :], input)
        input_padded = T.set_subtensor(input_padded[:, input.shape[1]:, :, :], input[:, :self.filter_size - self.stride, :, :])

        contiguous_input = gpu_contiguous(input_padded)
        contiguous_filters = gpu_contiguous(self.W)
        conved = self.filter_acts_op(contiguous_input, contiguous_filters)

        if self.untie_biases:
            conved += self.b.dimshuffle(0, 1, 2, 'x')
        else:
            conved += self.b.dimshuffle(0, 'x', 'x', 'x')

        return self.nonlinearity(conved)




def shuffle_pool_unshuffle(input_layer, *args, **kwargs):
    """
    The Krizhevskhy max pooling layer only supports square input. This function provides
    a workaround that uses Theano's own max pooling op, flanked by two shuffling operations:
    c01b to bc01 before pooling, and bc01 to c01b afterwards.
    """
    l_bc01 = ShuffleC01BToBC01Layer(input_layer)
    l_pool = layers.Pooling2DLayer(l_bc01, *args, **kwargs)
    l_c01b = ShuffleBC01ToC01BLayer(l_pool)

    return l_c01b




class StochasticPoolingC01BLayer(object):
    """
    Stochastic pooling implemented in Theano using reshapes, since the Pylearn2 class for it is
    way too slow.

    This only works for c01b, i.e. it assumes that the dimensions to pool over are (1, 2).
    It's also required that the dimensions are a multiple of the pool size (no incomplete pools).

    epsilon is used to prevent division by 0, it is added to all probabilities,
    so that when all activations are 0, the distribution is uniform.
    """
    def __init__(self, input_layer, pool_size, epsilon=1e-12):
        """
        pool_size: the number of inputs to be pooled together.
        """
        self.pool_size = pool_size
        self.epsilon = epsilon
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.mb_size = self.input_layer.mb_size

        self.params = []
        self.bias_params = []

    def get_output_shape(self):
        output_shape = list(self.input_shape) # make a mutable copy
        output_shape[1] = output_shape[1] // self.pool_size
        output_shape[2] = output_shape[2] // self.pool_size
        return tuple(output_shape)

    def output(self, dropout_active=True, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)

        output_shape = self.get_output_shape()
        pool_shape = (output_shape[0], output_shape[1], self.pool_size, output_shape[2], self.pool_size, output_shape[3])
        merged_shape = (output_shape[0], output_shape[1], output_shape[2], output_shape[3], self.pool_size**2)
        flat_shape = (output_shape[0] * output_shape[1] * output_shape[2] * output_shape[3], self.pool_size**2)
        input_reshaped = input.reshape(pool_shape).transpose(0, 1, 3, 5, 2, 4).reshape(flat_shape) #pools are now in axis 4

        input_reshaped += self.epsilon # add a small constant to prevent division by 0 in what follows.

        if dropout_active:
            probabilities = input_reshaped / input_reshaped.sum(axis=1, keepdims=True)
            samples = layers.srng.multinomial(pvals=probabilities, dtype=theano.config.floatX)
            output_flat = T.sum(input_reshaped * samples, axis=1)
            output = output_flat.reshape(output_shape)
        else:
            # no dropout, so compute the weighted average instead.
            # this amounts to the sum of squares normalised by the sum of the values.
            numerator = T.sum(input_reshaped**2, axis=1)
            denominator = T.sum(input_reshaped, axis=1)
            output_flat = numerator / denominator
            output = output_flat.reshape(output_shape)
            
        return output
########NEW FILE########
__FILENAME__ = check_label_constraints
"""
This file evaluates all constraints on the training labels as stipulated on the 'decision tree' page, and reports when they are violated.
It uses only the source CSV file for the sake of reproducibility.
"""

import numpy as np
import pandas as pd 

TOLERANCE = 0.00001 # 0.01 # only absolute errors greater than this are reported.

# TRAIN_LABELS_PATH = "data/raw/solutions_training.csv"
TRAIN_LABELS_PATH = "data/raw/training_solutions_rev1.csv"

d = pd.read_csv(TRAIN_LABELS_PATH)
targets = d.as_matrix()[:, 1:].astype('float32')
ids = d.as_matrix()[:, 0].astype('int32')


# separate out the questions for convenience
questions = [
    targets[:, 0:3], # 1.1 - 1.3,
    targets[:, 3:5], # 2.1 - 2.2
    targets[:, 5:7], # 3.1 - 3.2
    targets[:, 7:9], # 4.1 - 4.2
    targets[:, 9:13], # 5.1 - 5.4
    targets[:, 13:15], # 6.1 - 6.2
    targets[:, 15:18], # 7.1 - 7.3
    targets[:, 18:25], # 8.1 - 8.7
    targets[:, 25:28], # 9.1 - 9.3
    targets[:, 28:31], # 10.1 - 10.3
    targets[:, 31:37], # 11.1 - 11.6
]

# there is one constraint for each question.
# the sums of all answers for each of the questions should be equal to these numbers.
sums = [
    np.ones(targets.shape[0]), # 1, # Q1
    questions[0][:, 1], # Q2
    questions[1][:, 1], # Q3
    questions[1][:, 1], # Q4
    questions[1][:, 1], # Q5
    np.ones(targets.shape[0]), # 1, # Q6
    questions[0][:, 0], # Q7
    questions[5][:, 0], # Q8
    questions[1][:, 0], # Q9
    questions[3][:, 0], # Q10
    questions[3][:, 0], # Q11
]

num_total_violations = 0
affected_ids = set()

for k, desired_sums in enumerate(sums):
    print "QUESTION %d" % (k + 1)
    actual_sums = questions[k].sum(1)
    difference = abs(desired_sums - actual_sums)
    indices_violated = difference > TOLERANCE
    ids_violated = ids[indices_violated]
    num_violations = len(ids_violated)
    if num_violations > 0:
        print "%d constraint violations." % num_violations
        num_total_violations += num_violations
        for id_violated, d_s, a_s in zip(ids_violated, desired_sums[indices_violated], actual_sums[indices_violated]):
            print "violated by %d, sum should be %.6f but it is %.6f" % (id_violated, d_s, a_s)
            affected_ids.add(id_violated)
    else:
        print "No constraint violations."

    print

print
print "%d violations in total." % num_total_violations
print "%d data points violate constraints." % len(affected_ids)
########NEW FILE########
__FILENAME__ = consider_constant
import theano
import theano.tensor as T
from theano.tensor.opt import register_canonicalize

# TODO: implement w.r.t.?

class ConsiderConstant(theano.compile.ViewOp):
    def grad(self, args, g_outs):
        return [g_out.zeros_like(g_out) for g_out in g_outs]

consider_constant = ConsiderConstant()

register_canonicalize(theano.gof.OpRemove(consider_constant), name='remove_consider_constant_')


if __name__=='__main__':
    import theano.tensor as T
    import numpy as np


    x = T.matrix('x')
    x_c = consider_constant(x)

    g = T.grad((x * T.exp(x)).sum(), x)

    f = theano.function([x], g) # should always return 1

    g_c = T.grad((x * T.exp(x_c)).sum(), x)

    f_c = theano.function([x], g_c) # should always return 0

    a = np.random.normal(0, 1, (3,3)).astype("float32")

    print f(a)
    print f_c(a)
    print np.exp(a) * (a + 1)
    print np.exp(a)


    theano.printing.debugprint(f_c)



#########

# WITHOUT CANONICALIZATION
# DeepCopyOp [@A] ''   1
#  |ConsiderConstant [@B] ''   0
#    |x [@C]

# Elemwise{exp} [@A] ''   1
#  |ConsiderConstant [@B] ''   0
#    |x [@C]


# WITH CANONICALIZATION
# DeepCopyOp [@A] 'x'   0
#  |x [@B]

# Elemwise{exp} [@A] ''   0
#  |x [@B]






# class ConsiderConstant(ViewOp):
#     def grad(self, args, g_outs):
#         return [tensor.zeros_like(g_out) for g_out in g_outs]
# consider_constant_ = ConsiderConstant()


# # Although the op just returns its input, it should be removed from
# # the graph to make sure all possible optimizations can be applied.
# register_canonicalize(gof.OpRemove(consider_constant_),
#     name='remove_consider_constant')


# #I create a function only to have the doc show well.
# def consider_constant(x):
#     """ Consider an expression constant when computing gradients.

#     The expression itself is unaffected, but when its gradient is
#     computed, or the gradient of another expression that this
#     expression is a subexpression of, it will not be backpropagated
#     through. In other words, the gradient of the expression is
#     truncated to 0.

#     :param x: A Theano expression whose gradient should be truncated.

#     :return: The expression is returned unmodified, but its gradient
#         is now truncated to 0.

#     Support rectangular matrix and tensor with more than 2 dimensions
#     if the later have all dimensions are equals.

#     .. versionadded:: 0.6.1
#     """
#     return consider_constant_(x)
#     
########NEW FILE########
__FILENAME__ = convert_training_labels_to_npy
# TRAIN_LABELS_PATH = "data/raw/solutions_training.csv"
TRAIN_LABELS_PATH = "data/raw/training_solutions_rev1.csv"
TARGET_PATH = "data/solutions_train.npy"

import pandas as pd 
import numpy as np 




d = pd.read_csv(TRAIN_LABELS_PATH)
targets = d.as_matrix()[:, 1:].astype('float32')


print "Saving %s" % TARGET_PATH
np.save(TARGET_PATH, targets)


########NEW FILE########
__FILENAME__ = copy_data_to_shm
import os
import time

paths = ["data/raw/images_train_rev1", "data/raw/images_test_rev1"]

for path in paths:
    if os.path.exists(os.path.join("/dev/shm", os.path.basename(path))):
        print "%s exists in /dev/shm, skipping." % path
        continue

    print "Copying %s to /dev/shm..." % path
    start_time = time.time()
    os.system("cp -R %s /dev/shm/" % path)
    print "  took %.2f seconds." % (time.time() - start_time)

########NEW FILE########
__FILENAME__ = create_submission_from_npy
import sys 
import os
import csv
import load_data


if len(sys.argv) != 2:
    print "Creates a gzipped CSV submission file from a gzipped numpy file with testset predictions."
    print "Usage: create_submission_from_npy.py <input.npy.gz>"
    sys.exit()

src_path = sys.argv[1]
src_dir = os.path.dirname(src_path)
src_filename = os.path.basename(src_path)
tgt_filename = src_filename.replace(".npy.gz", ".csv")
tgt_path = os.path.join(src_dir, tgt_filename)


test_ids = load_data.test_ids


print "Loading %s" % src_path

data = load_data.load_gz(src_path)
assert data.shape[0] == load_data.num_test

print "Saving %s" % tgt_path

with open(tgt_path, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(load_data.num_test):
        row = [test_ids[k]] + data[k].tolist()
        writer.writerow(row)


print "Gzipping..."
os.system("gzip %s" % tgt_path)

print "Done!"
########NEW FILE########
__FILENAME__ = create_test_ids_file
TEST_IDS_PATH = "data/test_ids.npy"

import numpy as np
import glob
import os

filenames = glob.glob("data/raw/images_test_rev1/*.jpg")

test_ids = [int(os.path.basename(s).replace(".jpg", "")) for s in filenames]
test_ids.sort()
test_ids = np.array(test_ids)
print "Saving %s" % TEST_IDS_PATH
np.save(TEST_IDS_PATH, test_ids)
########NEW FILE########
__FILENAME__ = create_train_ids_file
TRAIN_IDS_PATH = "data/train_ids.npy"
# TRAIN_LABELS_PATH = "data/raw/solutions_training.csv"
TRAIN_LABELS_PATH = "data/raw/training_solutions_rev1.csv"

import numpy as np
import os
import csv

with open(TRAIN_LABELS_PATH, 'r') as f:
    reader = csv.reader(f, delimiter=",")
    train_ids = []
    for k, line in enumerate(reader):
        if k == 0: continue # skip header
        train_ids.append(int(line[0]))

train_ids = np.array(train_ids)
print "Saving %s" % TRAIN_IDS_PATH
np.save(TRAIN_IDS_PATH, train_ids)
########NEW FILE########
__FILENAME__ = custom
"""
Custom stuff that is specific to the galaxy contest
"""

import theano
import theano.tensor as T
import numpy as np
from consider_constant import consider_constant


def clip_01(x):
    # custom nonlinearity that is linear between [0,1] and clips to the boundaries outside of this interval.
    return T.clip(x, 0, 1)



def tc_exp(x, t):
    """
    A version of the exponential that returns 0 below a certain threshold.
    """
    return T.maximum(T.exp(x + np.log(1 + t)) - t, 0)


def tc_softmax(x, t):
    x_c = x - T.max(x, axis=1, keepdims=True)
    x_e = tc_exp(x_c, t)
    return x_e / T.sum(x_e, axis=1, keepdims=True)



class GalaxyOutputLayer(object):
    """
    This layer expects the layer before to have 37 linear outputs. These are grouped per question and then passed through a softmax each,
    to encode for the fact that the probabilities of all the answers to a question should sum to one.

    Then, these probabilities are re-weighted as described in the competition info, and the MSE of the re-weighted probabilities is the loss function.
    """
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.target_var = T.matrix() # variable for the labels


    def targets(self, *args, **kwargs):
        q1 = self.target_var[:, 0:3] # 1.1 - 1.3
        q2 = self.target_var[:, 3:5] # 2.1 - 2.2
        q3 = self.target_var[:, 5:7] # 3.1 - 3.2
        q4 = self.target_var[:, 7:9] # 4.1 - 4.2
        q5 = self.target_var[:, 9:13] # 5.1 - 5.4
        q6 = self.target_var[:, 13:15] # 6.1 - 6.2
        q7 = self.target_var[:, 15:18] # 7.1 - 7.3
        q8 = self.target_var[:, 18:25] # 8.1 - 8.7
        q9 = self.target_var[:, 25:28] # 9.1 - 9.3
        q10 = self.target_var[:, 28:31] # 10.1 - 10.3
        q11 = self.target_var[:, 31:37] # 11.1 - 11.6

        return q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11  


    def answer_probabilities(self, *args, **kwargs):
        """
        apply softmax functions to the answer groups for each question.
        """
        input = self.input_layer.output(*args, **kwargs)
        q1 = T.nnet.softmax(input[:, 0:3]) # 1.1 - 1.3
        q2 = T.nnet.softmax(input[:, 3:5]) # 2.1 - 2.2
        q3 = T.nnet.softmax(input[:, 5:7]) # 3.1 - 3.2
        q4 = T.nnet.softmax(input[:, 7:9]) # 4.1 - 4.2
        q5 = T.nnet.softmax(input[:, 9:13]) # 5.1 - 5.4
        q6 = T.nnet.softmax(input[:, 13:15]) # 6.1 - 6.2
        q7 = T.nnet.softmax(input[:, 15:18]) # 7.1 - 7.3
        q8 = T.nnet.softmax(input[:, 18:25]) # 8.1 - 8.7
        q9 = T.nnet.softmax(input[:, 25:28]) # 9.1 - 9.3
        q10 = T.nnet.softmax(input[:, 28:31]) # 10.1 - 10.3
        q11 = T.nnet.softmax(input[:, 31:37]) # 11.1 - 11.6

        return q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11

    def weighted_answer_probabilities(self, weight_with_targets=False, *args, **kwargs):
        answer_probabilities = self.answer_probabilities(*args, **kwargs)
        q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11 = answer_probabilities

        # weighting factors
        if weight_with_targets:
            t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11 = self.targets(*args, **kwargs)
            w1 = 1
            w2 = t1[:, 1]
            w3 = t2[:, 1]
            w4 = w3
            w7 = t1[:, 0]
            w9 = t2[:, 0]
            w10 = t4[:, 0]
            w11 = w10
            w5 = w4
            w6 = 1
            w8 = t6[:, 0]
        else:
            w1 = 1
            w2 = q1[:, 1] # question 1 answer 2
            w3 = q2[:, 1] * w2 # question 2 answer 2 * w2
            w4 = w3
            w7 = q1[:, 0] # question 1 answer 1
            w9 = q2[:, 0] * w2 # question 2 answer 1 * w2
            w10 = q4[:, 0] * w4 # question 4 answer 1 * w4
            w11 = w10
            w5 = w4 # THIS WAS WRONG BEFORE
            w6 = 1 # THIS SHOULD TECHNICALLY BE w5 + w7 + w9, but as explained on the forums, there was a mistake generating the dataset.
            # see http://www.kaggle.com/c/galaxy-zoo-the-galaxy-challenge/forums/t/6706/is-question-6-also-answered-for-stars-artifacts-answer-1-3 for more info
            w8 = q6[:, 0] * w6 # question 6 answer 1 * w6

        # weighted answers
        wq1 = q1 * w1
        wq2 = q2 * w2.dimshuffle(0, 'x')
        wq3 = q3 * w3.dimshuffle(0, 'x')
        wq4 = q4 * w4.dimshuffle(0, 'x')
        wq5 = q5 * w5.dimshuffle(0, 'x')
        wq6 = q6 * w6 # w6.dimshuffle(0, 'x')
        wq7 = q7 * w7.dimshuffle(0, 'x')
        wq8 = q8 * w8.dimshuffle(0, 'x')
        wq9 = q9 * w9.dimshuffle(0, 'x')
        wq10 = q10 * w10.dimshuffle(0, 'x')
        wq11 = q11 * w11.dimshuffle(0, 'x')

        return wq1, wq2, wq3, wq4, wq5, wq6, wq7, wq8, wq9, wq10, wq11

    def error(self, *args, **kwargs):
        predictions = self.predictions(*args, **kwargs)
        error = T.mean((predictions - self.target_var) ** 2)
        return error

    def predictions(self, *args, **kwargs):
        return T.concatenate(self.weighted_answer_probabilities(*args, **kwargs), axis=1) # concatenate all the columns together.
        # This might not be the best way to do this since we're summing everything afterwards.
        # Might be better to just write all of it as a sum straight away.






class ThresholdedGalaxyOutputLayer(object):
    """
    This layer expects the layer before to have 37 linear outputs. These are grouped per question and then passed through a softmax each,
    to encode for the fact that the probabilities of all the answers to a question should sum to one.

    The softmax function used is a special version with a threshold, such that it can return hard 0s and 1s for certain values.

    Then, these probabilities are re-weighted as described in the competition info, and the MSE of the re-weighted probabilities is the loss function.
    """
    def __init__(self, input_layer, threshold):
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.threshold = threshold
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.target_var = T.matrix() # variable for the labels

    def answer_probabilities(self, *args, **kwargs):
        """
        apply softmax functions to the answer groups for each question.
        """
        input = self.input_layer.output(*args, **kwargs)
        q1 = tc_softmax(input[:, 0:3], self.threshold) # 1.1 - 1.3
        q2 = tc_softmax(input[:, 3:5], self.threshold) # 2.1 - 2.2
        q3 = tc_softmax(input[:, 5:7], self.threshold) # 3.1 - 3.2
        q4 = tc_softmax(input[:, 7:9], self.threshold) # 4.1 - 4.2
        q5 = tc_softmax(input[:, 9:13], self.threshold) # 5.1 - 5.4
        q6 = tc_softmax(input[:, 13:15], self.threshold) # 6.1 - 6.2
        q7 = tc_softmax(input[:, 15:18], self.threshold) # 7.1 - 7.3
        q8 = tc_softmax(input[:, 18:25], self.threshold) # 8.1 - 8.7
        q9 = tc_softmax(input[:, 25:28], self.threshold) # 9.1 - 9.3
        q10 = tc_softmax(input[:, 28:31], self.threshold) # 10.1 - 10.3
        q11 = tc_softmax(input[:, 31:37], self.threshold) # 11.1 - 11.6

        return q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11

    def weighted_answer_probabilities(self, *args, **kwargs):
        answer_probabilities = self.answer_probabilities(*args, **kwargs)
        q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11 = answer_probabilities

        # weighting factors
        w1 = 1
        w2 = q1[:, 1] # question 1 answer 2
        w3 = q2[:, 1] * w2 # question 2 answer 2 * w2
        w4 = w3
        w7 = q1[:, 0] # question 1 answer 1
        w9 = q2[:, 0] * w2 # question 2 answer 1 * w2
        w10 = q4[:, 0] * w4 # question 4 answer 1 * w4
        w11 = w10
        w5 = w4 # THIS WAS WRONG BEFORE
        w6 = 1 # THIS SHOULD TECHNICALLY BE w5 + w7 + w9, but as explained on the forums, there was a mistake generating the dataset.
        # see http://www.kaggle.com/c/galaxy-zoo-the-galaxy-challenge/forums/t/6706/is-question-6-also-answered-for-stars-artifacts-answer-1-3 for more info
        w8 = q6[:, 0] * w6 # question 6 answer 1 * w6

        # weighted answers
        wq1 = q1 * w1
        wq2 = q2 * w2.dimshuffle(0, 'x')
        wq3 = q3 * w3.dimshuffle(0, 'x')
        wq4 = q4 * w4.dimshuffle(0, 'x')
        wq5 = q5 * w5.dimshuffle(0, 'x')
        wq6 = q6 * w6 # w6.dimshuffle(0, 'x')
        wq7 = q7 * w7.dimshuffle(0, 'x')
        wq8 = q8 * w8.dimshuffle(0, 'x')
        wq9 = q9 * w9.dimshuffle(0, 'x')
        wq10 = q10 * w10.dimshuffle(0, 'x')
        wq11 = q11 * w11.dimshuffle(0, 'x')

        return wq1, wq2, wq3, wq4, wq5, wq6, wq7, wq8, wq9, wq10, wq11

    def error(self, *args, **kwargs):
        predictions = self.predictions(*args, **kwargs)
        error = T.mean((predictions - self.target_var) ** 2)
        return error

    def predictions(self, *args, **kwargs):
        return T.concatenate(self.weighted_answer_probabilities(*args, **kwargs), axis=1) # concatenate all the columns together.
        # This might not be the best way to do this since we're summing everything afterwards.
        # Might be better to just write all of it as a sum straight away.









class DivisiveGalaxyOutputLayer(object):
    """
    This layer expects the layer before to have 37 linear outputs. These are grouped per question, clipped, and then normalised by dividing by the sum,
    to encode for the fact that the probabilities of all the answers to a question should sum to one.

    Then, these probabilities are re-weighted as described in the competition info, and the MSE of the re-weighted probabilities is the loss function.
    """
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.target_var = T.matrix() # variable for the labels

    def answer_probabilities(self, *args, **kwargs):
        """
        normalise the answer groups for each question.
        """
        input = self.input_layer.output(*args, **kwargs)
        input_clipped = T.maximum(input, 0) # T.clip(input, 0, 1) # T.maximum(input, 0)

        q1 = input_clipped[:, 0:3] # 1.1 - 1.3
        q2 = input_clipped[:, 3:5] # 2.1 - 2.2
        q3 = input_clipped[:, 5:7] # 3.1 - 3.2
        q4 = input_clipped[:, 7:9] # 4.1 - 4.2
        q5 = input_clipped[:, 9:13] # 5.1 - 5.4
        q6 = input_clipped[:, 13:15] # 6.1 - 6.2
        q7 = input_clipped[:, 15:18] # 7.1 - 7.3
        q8 = input_clipped[:, 18:25] # 8.1 - 8.7
        q9 = input_clipped[:, 25:28] # 9.1 - 9.3
        q10 = input_clipped[:, 28:31] # 10.1 - 10.3
        q11 = input_clipped[:, 31:37] # 11.1 - 11.6

        # what if the sums are 0?
        # adding a very small constant works, but then the probabilities don't sum to 1 anymore.
        # is there a better way?

        q1 = q1 / (q1.sum(1, keepdims=True) + 1e-12)
        q2 = q2 / (q2.sum(1, keepdims=True) + 1e-12)
        q3 = q3 / (q3.sum(1, keepdims=True) + 1e-12)
        q4 = q4 / (q4.sum(1, keepdims=True) + 1e-12)
        q5 = q5 / (q5.sum(1, keepdims=True) + 1e-12)
        q6 = q6 / (q6.sum(1, keepdims=True) + 1e-12)
        q7 = q7 / (q7.sum(1, keepdims=True) + 1e-12)
        q8 = q8 / (q8.sum(1, keepdims=True) + 1e-12)
        q9 = q9 / (q9.sum(1, keepdims=True) + 1e-12)
        q10 = q10 / (q10.sum(1, keepdims=True) + 1e-12)
        q11 = q11 / (q11.sum(1, keepdims=True) + 1e-12)

        return q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11

    def weighted_answer_probabilities(self, *args, **kwargs):
        answer_probabilities = self.answer_probabilities(*args, **kwargs)
        q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11 = answer_probabilities

        # weighting factors
        w1 = 1
        w2 = q1[:, 1] # question 1 answer 2
        w3 = q2[:, 1] * w2 # question 2 answer 2 * w2
        w4 = w3
        w7 = q1[:, 0] # question 1 answer 1
        w9 = q2[:, 0] * w2 # question 2 answer 1 * w2
        w10 = q4[:, 0] * w4 # question 4 answer 1 * w4
        w11 = w10
        w5 = w4 # THIS WAS WRONG BEFORE
        w6 = 1 # THIS SHOULD TECHNICALLY BE w5 + w7 + w9, but as explained on the forums, there was a mistake generating the dataset.
        # see http://www.kaggle.com/c/galaxy-zoo-the-galaxy-challenge/forums/t/6706/is-question-6-also-answered-for-stars-artifacts-answer-1-3 for more info
        w8 = q6[:, 0] * w6 # question 6 answer 1 * w6

        # weighted answers
        wq1 = q1 * w1
        wq2 = q2 * w2.dimshuffle(0, 'x')
        wq3 = q3 * w3.dimshuffle(0, 'x')
        wq4 = q4 * w4.dimshuffle(0, 'x')
        wq5 = q5 * w5.dimshuffle(0, 'x')
        wq6 = q6 * w6 # w6.dimshuffle(0, 'x')
        wq7 = q7 * w7.dimshuffle(0, 'x')
        wq8 = q8 * w8.dimshuffle(0, 'x')
        wq9 = q9 * w9.dimshuffle(0, 'x')
        wq10 = q10 * w10.dimshuffle(0, 'x')
        wq11 = q11 * w11.dimshuffle(0, 'x')

        return wq1, wq2, wq3, wq4, wq5, wq6, wq7, wq8, wq9, wq10, wq11

    def error(self, *args, **kwargs):
        predictions = self.predictions(*args, **kwargs)
        error = T.mean((predictions - self.target_var) ** 2)
        return error

    def predictions(self, *args, **kwargs):
        return T.concatenate(self.weighted_answer_probabilities(*args, **kwargs), axis=1) # concatenate all the columns together.
        # This might not be the best way to do this since we're summing everything afterwards.
        # Might be better to just write all of it as a sum straight away.




class SquaredGalaxyOutputLayer(object):
    """
    This layer expects the layer before to have 37 linear outputs. These are grouped per question, rectified, squared and then normalised by dividing by the sum,
    to encode for the fact that the probabilities of all the answers to a question should sum to one.

    Then, these probabilities are re-weighted as described in the competition info, and the MSE of the re-weighted probabilities is the loss function.
    """
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.target_var = T.matrix() # variable for the labels

    def answer_probabilities(self, *args, **kwargs):
        """
        normalise the answer groups for each question.
        """
        input = self.input_layer.output(*args, **kwargs)
        input_rectified = T.maximum(input, 0)
        input_squared = input_rectified ** 2

        q1 = input_squared[:, 0:3] # 1.1 - 1.3
        q2 = input_squared[:, 3:5] # 2.1 - 2.2
        q3 = input_squared[:, 5:7] # 3.1 - 3.2
        q4 = input_squared[:, 7:9] # 4.1 - 4.2
        q5 = input_squared[:, 9:13] # 5.1 - 5.4
        q6 = input_squared[:, 13:15] # 6.1 - 6.2
        q7 = input_squared[:, 15:18] # 7.1 - 7.3
        q8 = input_squared[:, 18:25] # 8.1 - 8.7
        q9 = input_squared[:, 25:28] # 9.1 - 9.3
        q10 = input_squared[:, 28:31] # 10.1 - 10.3
        q11 = input_squared[:, 31:37] # 11.1 - 11.6

        # what if the sums are 0?
        # adding a very small constant works, but then the probabilities don't sum to 1 anymore.
        # is there a better way?

        q1 = q1 / (q1.sum(1, keepdims=True) + 1e-12)
        q2 = q2 / (q2.sum(1, keepdims=True) + 1e-12)
        q3 = q3 / (q3.sum(1, keepdims=True) + 1e-12)
        q4 = q4 / (q4.sum(1, keepdims=True) + 1e-12)
        q5 = q5 / (q5.sum(1, keepdims=True) + 1e-12)
        q6 = q6 / (q6.sum(1, keepdims=True) + 1e-12)
        q7 = q7 / (q7.sum(1, keepdims=True) + 1e-12)
        q8 = q8 / (q8.sum(1, keepdims=True) + 1e-12)
        q9 = q9 / (q9.sum(1, keepdims=True) + 1e-12)
        q10 = q10 / (q10.sum(1, keepdims=True) + 1e-12)
        q11 = q11 / (q11.sum(1, keepdims=True) + 1e-12)

        return q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11

    def weighted_answer_probabilities(self, *args, **kwargs):
        answer_probabilities = self.answer_probabilities(*args, **kwargs)
        q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11 = answer_probabilities

        # weighting factors
        w1 = 1
        w2 = q1[:, 1] # question 1 answer 2
        w3 = q2[:, 1] * w2 # question 2 answer 2 * w2
        w4 = w3
        w7 = q1[:, 0] # question 1 answer 1
        w9 = q2[:, 0] * w2 # question 2 answer 1 * w2
        w10 = q4[:, 0] * w4 # question 4 answer 1 * w4
        w11 = w10
        w5 = w4 # THIS WAS WRONG BEFORE
        w6 = 1 # THIS SHOULD TECHNICALLY BE w5 + w7 + w9, but as explained on the forums, there was a mistake generating the dataset.
        # see http://www.kaggle.com/c/galaxy-zoo-the-galaxy-challenge/forums/t/6706/is-question-6-also-answered-for-stars-artifacts-answer-1-3 for more info
        w8 = q6[:, 0] * w6 # question 6 answer 1 * w6

        # weighted answers
        wq1 = q1 * w1
        wq2 = q2 * w2.dimshuffle(0, 'x')
        wq3 = q3 * w3.dimshuffle(0, 'x')
        wq4 = q4 * w4.dimshuffle(0, 'x')
        wq5 = q5 * w5.dimshuffle(0, 'x')
        wq6 = q6 * w6 # w6.dimshuffle(0, 'x')
        wq7 = q7 * w7.dimshuffle(0, 'x')
        wq8 = q8 * w8.dimshuffle(0, 'x')
        wq9 = q9 * w9.dimshuffle(0, 'x')
        wq10 = q10 * w10.dimshuffle(0, 'x')
        wq11 = q11 * w11.dimshuffle(0, 'x')

        return wq1, wq2, wq3, wq4, wq5, wq6, wq7, wq8, wq9, wq10, wq11

    def error(self, *args, **kwargs):
        predictions = self.predictions(*args, **kwargs)
        error = T.mean((predictions - self.target_var) ** 2)
        return error

    def predictions(self, *args, **kwargs):
        return T.concatenate(self.weighted_answer_probabilities(*args, **kwargs), axis=1) # concatenate all the columns together.
        # This might not be the best way to do this since we're summing everything afterwards.
        # Might be better to just write all of it as a sum straight away.





class ClippedGalaxyOutputLayer(object):
    """
    This layer expects the layer before to have 37 linear outputs. These are grouped per question, clipped, but NOT normalised, because it seems
    like this might be impeding the learning.

    Then, these probabilities are re-weighted as described in the competition info, and the MSE of the re-weighted probabilities is the loss function.
    """
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.target_var = T.matrix() # variable for the labels

    def answer_probabilities(self, *args, **kwargs):
        """
        normalise the answer groups for each question.
        """
        input = self.input_layer.output(*args, **kwargs)
        input_clipped = T.clip(input, 0, 1) # T.maximum(input, 0)

        q1 = input_clipped[:, 0:3] # 1.1 - 1.3
        q2 = input_clipped[:, 3:5] # 2.1 - 2.2
        q3 = input_clipped[:, 5:7] # 3.1 - 3.2
        q4 = input_clipped[:, 7:9] # 4.1 - 4.2
        q5 = input_clipped[:, 9:13] # 5.1 - 5.4
        q6 = input_clipped[:, 13:15] # 6.1 - 6.2
        q7 = input_clipped[:, 15:18] # 7.1 - 7.3
        q8 = input_clipped[:, 18:25] # 8.1 - 8.7
        q9 = input_clipped[:, 25:28] # 9.1 - 9.3
        q10 = input_clipped[:, 28:31] # 10.1 - 10.3
        q11 = input_clipped[:, 31:37] # 11.1 - 11.6

        return q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11

    def targets(self, *args, **kwargs):
        q1 = self.target_var[:, 0:3] # 1.1 - 1.3
        q2 = self.target_var[:, 3:5] # 2.1 - 2.2
        q3 = self.target_var[:, 5:7] # 3.1 - 3.2
        q4 = self.target_var[:, 7:9] # 4.1 - 4.2
        q5 = self.target_var[:, 9:13] # 5.1 - 5.4
        q6 = self.target_var[:, 13:15] # 6.1 - 6.2
        q7 = self.target_var[:, 15:18] # 7.1 - 7.3
        q8 = self.target_var[:, 18:25] # 8.1 - 8.7
        q9 = self.target_var[:, 25:28] # 9.1 - 9.3
        q10 = self.target_var[:, 28:31] # 10.1 - 10.3
        q11 = self.target_var[:, 31:37] # 11.1 - 11.6

        return q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11        

    def weighted_answer_probabilities(self, weight_with_targets=False, *args, **kwargs):
        answer_probabilities = self.answer_probabilities(*args, **kwargs)
        q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11 = answer_probabilities

        # weighting factors
        if weight_with_targets:
            w1, w2, w3, w4, w5, w6, w7, w8, w9, w10, w11 = self.question_weights(self.targets(*args, **kwargs))
        else:
            w1, w2, w3, w4, w5, w6, w7, w8, w9, w10, w11 = self.question_weights(answer_probabilities)

        # weighted answers
        wq1 = q1 * w1
        wq2 = q2 * w2.dimshuffle(0, 'x')
        wq3 = q3 * w3.dimshuffle(0, 'x')
        wq4 = q4 * w4.dimshuffle(0, 'x')
        wq5 = q5 * w5.dimshuffle(0, 'x')
        wq6 = q6 * w6 # w6.dimshuffle(0, 'x')
        wq7 = q7 * w7.dimshuffle(0, 'x')
        wq8 = q8 * w8.dimshuffle(0, 'x')
        wq9 = q9 * w9.dimshuffle(0, 'x')
        wq10 = q10 * w10.dimshuffle(0, 'x')
        wq11 = q11 * w11.dimshuffle(0, 'x')

        return wq1, wq2, wq3, wq4, wq5, wq6, wq7, wq8, wq9, wq10, wq11

    def error(self, *args, **kwargs):
        predictions = self.predictions(*args, **kwargs)
        error = T.mean((predictions - self.target_var) ** 2)
        return error

    def question_weights(self, q):
        """
        q is a list of matrices of length 11 (one for each question), like the output given by targets() and answer_probabilities()
        """
        q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11 = q # unpack
        w1 = 1
        w2 = q1[:, 1] # question 1 answer 2
        w3 = q2[:, 1] * w2 # question 2 answer 2 * w2
        w4 = w3
        w7 = q1[:, 0] # question 1 answer 1
        w9 = q2[:, 0] * w2 # question 2 answer 1 * w2
        w10 = q4[:, 0] * w4 # question 4 answer 1 * w4
        w11 = w10
        w5 = w4 # THIS WAS WRONG BEFORE
        w6 = 1 # THIS SHOULD TECHNICALLY BE w5 + w7 + w9, but as explained on the forums, there was a mistake generating the dataset.
        # see http://www.kaggle.com/c/galaxy-zoo-the-galaxy-challenge/forums/t/6706/is-question-6-also-answered-for-stars-artifacts-answer-1-3 for more info
        w8 = q6[:, 0] * w6 # question 6 answer 1 * w6

        return w1, w2, w3, w4, w5, w6, w7, w8, w9, w10, w11


    def normreg(self, direct_weighting=True, *args, **kwargs):
        """
        direct_weighting: if True, the weighting is applied directly to the constraints (before the barrier function).
        if False, all constraints are 'sum-to-1' and the weighting is applied after the barrier function.
        """
        answer_probabilities = self.answer_probabilities(*args, **kwargs)
        q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11 = answer_probabilities
        weights = self.question_weights(answer_probabilities)

        constraints = [q.sum(1, keepdims=True) - 1 for q in answer_probabilities]

        func = lambda x: x**2

        if direct_weighting: # scale the constraints with the weights
            terms = [func(weight * constraint) for weight, constraint in zip(weights, constraints)]
        else:
            terms = [weight * func(constraint) for weight, constraint in zip(weights, constraints)]

        return T.mean(T.concatenate(terms, axis=1))
        
        # means = [T.mean(term) for term in terms] # mean over the minibatch
        # return sum(means)


    def error_with_normreg(self, scale=1.0, *args, **kwargs):
        error_term = self.error(*args, **kwargs)
        normreg_term = self.normreg(*args, **kwargs)
        return error_term + scale * normreg_term

    def predictions(self, *args, **kwargs):
        return T.concatenate(self.weighted_answer_probabilities(*args, **kwargs), axis=1) # concatenate all the columns together.
        # This might not be the best way to do this since we're summing everything afterwards.
        # Might be better to just write all of it as a sum straight away.






class OptimisedDivGalaxyOutputLayer(object):
    """
    divisive normalisation, optimised for performance.
    """
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.target_var = T.matrix() # variable for the labels

        self.question_slices = [slice(0, 3), slice(3, 5), slice(5, 7), slice(7, 9), slice(9, 13), slice(13, 15),
                                slice(15, 18), slice(18, 25), slice(25, 28), slice(28, 31), slice(31, 37)]

        # self.scaling_factor_indices = [None, [1], [1, 4], [1, 4], [1, 4], None, [0], [13], [1, 3], [1, 4, 7], [1, 4, 7]]
        # indices of all the probabilities that scale each question.

        self.normalisation_mask = theano.shared(self.generate_normalisation_mask())
        # self.scaling_mask = theano.shared(self.generate_scaling_mask())

        # sequence of scaling steps to be undertaken.
        # First element is a slice indicating the values to be scaled. Second element is an index indicating the scale factor.
        # these have to happen IN ORDER else it doesn't work correctly.
        self.scaling_sequence = [
            (slice(3, 5), 1), # I: rescale Q2 by A1.2
            (slice(5, 13), 4), # II: rescale Q3, Q4, Q5 by A2.2
            (slice(15, 18), 0), # III: rescale Q7 by A1.1
            (slice(18, 25), 13), # IV: rescale Q8 by A6.1
            (slice(25, 28), 3), # V: rescale Q9 by A2.1
            (slice(28, 37), 7), # VI: rescale Q10, Q11 by A4.1
        ]


    def generate_normalisation_mask(self):
        """
        when the clipped input is multiplied by the normalisation mask, the normalisation denominators are generated.
        So then we can just divide the input by the normalisation constants (elementwise).
        """
        mask = np.zeros((37, 37), dtype='float32')
        for s in self.question_slices:
            mask[s, s] = 1.0
        return mask

    # def generate_scaling_mask(self):
    #     """
    #     This mask needs to be applied to the LOGARITHM of the probabilities. The appropriate log probs are then summed,
    #     which corresponds to multiplying the raw probabilities, which is what we want to achieve.
    #     """
    #     mask = np.zeros((37, 37), dtype='float32')
    #     for s, factor_indices in zip(self.question_slices, self.scaling_factor_indices):
    #         if factor_indices is not None:
    #             mask[factor_indices, s] = 1.0
    #     return mask

    def answer_probabilities(self, *args, **kwargs):
        """
        normalise the answer groups for each question.
        """
        input = self.input_layer.output(*args, **kwargs)
        input_clipped = T.maximum(input, 0) # T.clip(input, 0, 1) # T.maximum(input, 0)

        normalisation_denoms = T.dot(input_clipped, self.normalisation_mask) + 1e-12 # small constant to prevent division by 0
        input_normalised = input_clipped / normalisation_denoms

        return input_normalised
        # return [input_normalised[:, s] for s in self.question_slices]

    # def weighted_answer_probabilities(self, *args, **kwargs):
    #     answer_probabilities = self.answer_probabilities(*args, **kwargs)
        
    #     log_scale_factors = T.dot(T.log(answer_probabilities), self.scaling_mask)
    #     scale_factors = T.exp(T.switch(T.isnan(log_scale_factors), -np.inf, log_scale_factors)) # need NaN shielding here because 0 * -inf = NaN.

    #     return answer_probabilities * scale_factors

    def weighted_answer_probabilities(self, *args, **kwargs):
        probs = self.answer_probabilities(*args, **kwargs)

        # go through the rescaling sequence in order (6 steps)
        for probs_slice, scale_idx in self.scaling_sequence:
            probs = T.set_subtensor(probs[:, probs_slice], probs[:, probs_slice] * probs[:, scale_idx].dimshuffle(0, 'x'))

        return probs

    def predictions(self, normalisation=True, *args, **kwargs):
        return self.weighted_answer_probabilities(*args, **kwargs)

    def predictions_no_normalisation(self, *args, **kwargs):
        """
        Predict without normalisation. This can be used for the first few chunks to find good parameters.
        """
        input = self.input_layer.output(*args, **kwargs)
        input_clipped = T.clip(input, 0, 1) # clip on both sides here, any predictions over 1.0 are going to get normalised away anyway.
        return input_clipped

    def error(self, normalisation=True, *args, **kwargs):
        if normalisation:
            predictions = self.predictions(*args, **kwargs)
        else:
            predictions = self.predictions_no_normalisation(*args, **kwargs)
        error = T.mean((predictions - self.target_var) ** 2)
        return error







class ConstantWeightedDivGalaxyOutputLayer(object):
    """
    divisive normalisation, weights are considered constant when differentiating, optimised for performance.
    """
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

        self.target_var = T.matrix() # variable for the labels

        self.question_slices = [slice(0, 3), slice(3, 5), slice(5, 7), slice(7, 9), slice(9, 13), slice(13, 15),
                                slice(15, 18), slice(18, 25), slice(25, 28), slice(28, 31), slice(31, 37)]

        # self.scaling_factor_indices = [None, [1], [1, 4], [1, 4], [1, 4], None, [0], [13], [1, 3], [1, 4, 7], [1, 4, 7]]
        # indices of all the probabilities that scale each question.

        self.normalisation_mask = theano.shared(self.generate_normalisation_mask())
        # self.scaling_mask = theano.shared(self.generate_scaling_mask())

        # sequence of scaling steps to be undertaken.
        # First element is a slice indicating the values to be scaled. Second element is an index indicating the scale factor.
        # these have to happen IN ORDER else it doesn't work correctly.
        self.scaling_sequence = [
            (slice(3, 5), 1), # I: rescale Q2 by A1.2
            (slice(5, 13), 4), # II: rescale Q3, Q4, Q5 by A2.2
            (slice(15, 18), 0), # III: rescale Q7 by A1.1
            (slice(18, 25), 13), # IV: rescale Q8 by A6.1
            (slice(25, 28), 3), # V: rescale Q9 by A2.1
            (slice(28, 37), 7), # VI: rescale Q10, Q11 by A4.1
        ]


    def generate_normalisation_mask(self):
        """
        when the clipped input is multiplied by the normalisation mask, the normalisation denominators are generated.
        So then we can just divide the input by the normalisation constants (elementwise).
        """
        mask = np.zeros((37, 37), dtype='float32')
        for s in self.question_slices:
            mask[s, s] = 1.0
        return mask

    # def generate_scaling_mask(self):
    #     """
    #     This mask needs to be applied to the LOGARITHM of the probabilities. The appropriate log probs are then summed,
    #     which corresponds to multiplying the raw probabilities, which is what we want to achieve.
    #     """
    #     mask = np.zeros((37, 37), dtype='float32')
    #     for s, factor_indices in zip(self.question_slices, self.scaling_factor_indices):
    #         if factor_indices is not None:
    #             mask[factor_indices, s] = 1.0
    #     return mask

    def answer_probabilities(self, *args, **kwargs):
        """
        normalise the answer groups for each question.
        """
        input = self.input_layer.output(*args, **kwargs)
        input_clipped = T.maximum(input, 0) # T.clip(input, 0, 1) # T.maximum(input, 0)

        normalisation_denoms = T.dot(input_clipped, self.normalisation_mask) + 1e-12 # small constant to prevent division by 0
        input_normalised = input_clipped / normalisation_denoms

        return input_normalised
        # return [input_normalised[:, s] for s in self.question_slices]

    # def weighted_answer_probabilities(self, *args, **kwargs):
    #     answer_probabilities = self.answer_probabilities(*args, **kwargs)
        
    #     log_scale_factors = T.dot(T.log(answer_probabilities), self.scaling_mask)
    #     scale_factors = T.exp(T.switch(T.isnan(log_scale_factors), -np.inf, log_scale_factors)) # need NaN shielding here because 0 * -inf = NaN.

    #     return answer_probabilities * scale_factors

    def weighted_answer_probabilities(self, *args, **kwargs):
        probs = self.answer_probabilities(*args, **kwargs)

        # go through the rescaling sequence in order (6 steps)
        for probs_slice, scale_idx in self.scaling_sequence:
            probs = T.set_subtensor(probs[:, probs_slice], probs[:, probs_slice] * consider_constant(probs[:, scale_idx].dimshuffle(0, 'x')))

        return probs

    def predictions(self, normalisation=True, *args, **kwargs):
        return self.weighted_answer_probabilities(*args, **kwargs)

    def predictions_no_normalisation(self, *args, **kwargs):
        """
        Predict without normalisation. This can be used for the first few chunks to find good parameters.
        """
        input = self.input_layer.output(*args, **kwargs)
        input_clipped = T.clip(input, 0, 1) # clip on both sides here, any predictions over 1.0 are going to get normalised away anyway.
        return input_clipped

    def error(self, normalisation=True, *args, **kwargs):
        if normalisation:
            predictions = self.predictions(*args, **kwargs)
        else:
            predictions = self.predictions_no_normalisation(*args, **kwargs)
        error = T.mean((predictions - self.target_var) ** 2)
        return error










class SoftplusDivGalaxyOutputLayer(object):
    """
    divisive normalisation with softplus function, optimised for performance.
    """
    def __init__(self, input_layer, scale=10.0):
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size
        self.scale = scale

        self.target_var = T.matrix() # variable for the labels

        self.question_slices = [slice(0, 3), slice(3, 5), slice(5, 7), slice(7, 9), slice(9, 13), slice(13, 15),
                                slice(15, 18), slice(18, 25), slice(25, 28), slice(28, 31), slice(31, 37)]

        # self.scaling_factor_indices = [None, [1], [1, 4], [1, 4], [1, 4], None, [0], [13], [1, 3], [1, 4, 7], [1, 4, 7]]
        # indices of all the probabilities that scale each question.

        self.normalisation_mask = theano.shared(self.generate_normalisation_mask())
        # self.scaling_mask = theano.shared(self.generate_scaling_mask())

        # sequence of scaling steps to be undertaken.
        # First element is a slice indicating the values to be scaled. Second element is an index indicating the scale factor.
        # these have to happen IN ORDER else it doesn't work correctly.
        self.scaling_sequence = [
            (slice(3, 5), 1), # I: rescale Q2 by A1.2
            (slice(5, 13), 4), # II: rescale Q3, Q4, Q5 by A2.2
            (slice(15, 18), 0), # III: rescale Q7 by A1.1
            (slice(18, 25), 13), # IV: rescale Q8 by A6.1
            (slice(25, 28), 3), # V: rescale Q9 by A2.1
            (slice(28, 37), 7), # VI: rescale Q10, Q11 by A4.1
        ]


    def generate_normalisation_mask(self):
        """
        when the clipped input is multiplied by the normalisation mask, the normalisation denominators are generated.
        So then we can just divide the input by the normalisation constants (elementwise).
        """
        mask = np.zeros((37, 37), dtype='float32')
        for s in self.question_slices:
            mask[s, s] = 1.0
        return mask

    # def generate_scaling_mask(self):
    #     """
    #     This mask needs to be applied to the LOGARITHM of the probabilities. The appropriate log probs are then summed,
    #     which corresponds to multiplying the raw probabilities, which is what we want to achieve.
    #     """
    #     mask = np.zeros((37, 37), dtype='float32')
    #     for s, factor_indices in zip(self.question_slices, self.scaling_factor_indices):
    #         if factor_indices is not None:
    #             mask[factor_indices, s] = 1.0
    #     return mask

    def answer_probabilities(self, *args, **kwargs):
        """
        normalise the answer groups for each question.
        """
        input = self.input_layer.output(*args, **kwargs)
        input_clipped = T.nnet.softplus(input * self.scale) #  T.maximum(input, 0) # T.clip(input, 0, 1) # T.maximum(input, 0)

        normalisation_denoms = T.dot(input_clipped, self.normalisation_mask) + 1e-12 # small constant to prevent division by 0
        input_normalised = input_clipped / normalisation_denoms

        return input_normalised
        # return [input_normalised[:, s] for s in self.question_slices]

    # def weighted_answer_probabilities(self, *args, **kwargs):
    #     answer_probabilities = self.answer_probabilities(*args, **kwargs)
        
    #     log_scale_factors = T.dot(T.log(answer_probabilities), self.scaling_mask)
    #     scale_factors = T.exp(T.switch(T.isnan(log_scale_factors), -np.inf, log_scale_factors)) # need NaN shielding here because 0 * -inf = NaN.

    #     return answer_probabilities * scale_factors

    def weighted_answer_probabilities(self, *args, **kwargs):
        probs = self.answer_probabilities(*args, **kwargs)

        # go through the rescaling sequence in order (6 steps)
        for probs_slice, scale_idx in self.scaling_sequence:
            probs = T.set_subtensor(probs[:, probs_slice], probs[:, probs_slice] * probs[:, scale_idx].dimshuffle(0, 'x'))

        return probs

    def predictions(self, normalisation=True, *args, **kwargs):
        return self.weighted_answer_probabilities(*args, **kwargs)

    def predictions_no_normalisation(self, *args, **kwargs):
        """
        Predict without normalisation. This can be used for the first few chunks to find good parameters.
        """
        input = self.input_layer.output(*args, **kwargs)
        input_clipped = T.clip(input, 0, 1) # clip on both sides here, any predictions over 1.0 are going to get normalised away anyway.
        return input_clipped

    def error(self, normalisation=True, *args, **kwargs):
        if normalisation:
            predictions = self.predictions(*args, **kwargs)
        else:
            predictions = self.predictions_no_normalisation(*args, **kwargs)
        error = T.mean((predictions - self.target_var) ** 2)
        return error
########NEW FILE########
__FILENAME__ = ensembled_predictions_npy
"""
Given a set of predictions for the validation and testsets (as .npy.gz), this script computes
the optimal linear weights on the validation set, and then computes the weighted predictions on the testset.
"""

import sys
import os
import glob

import theano 
import theano.tensor as T

import numpy as np 

import scipy

import load_data


TARGET_PATH = "predictions/final/blended/blended_predictions.npy.gz"
TARGET_PATH_SEPARATE = "predictions/final/blended/blended_predictions_separate.npy.gz"
TARGET_PATH_UNIFORM = "predictions/final/blended/blended_predictions_uniform.npy.gz"

predictions_valid_dir = "predictions/final/augmented/valid"
predictions_test_dir = "predictions/final/augmented/test"


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



# paths of all the files to blend.
predictions_test_paths = glob.glob(os.path.join(predictions_test_dir, "*.npy.gz"))
predictions_valid_paths = [os.path.join(predictions_valid_dir, os.path.basename(path)) for path in predictions_test_paths]

print "Loading validation set predictions"
predictions_list = [load_data.load_gz(path) for path in predictions_valid_paths]
predictions_stack = np.array(predictions_list).astype(theano.config.floatX) # num_sources x num_datapoints x 37
del predictions_list
print

print "Compute individual prediction errors"
individual_prediction_errors = np.sqrt(((predictions_stack - y_valid[None])**2).reshape(predictions_stack.shape[0], -1).mean(1))
print

print "Compiling Theano functions"
X = theano.shared(predictions_stack) # source predictions
t = theano.shared(y_valid) # targets

W = T.vector('W')


# shared weights for all answers
s = T.nnet.softmax(W).reshape((W.shape[0], 1, 1))

weighted_avg_predictions = T.sum(X * s, axis=0) #  T.tensordot(X, s, [[0], [0]])

error = T.mean((weighted_avg_predictions - t) ** 2)
grad = T.grad(error, W)

f = theano.function([W], error)
g = theano.function([W], grad)


# separate weights for all answers
s2 = T.nnet.softmax(W.reshape((37, predictions_stack.shape[0]))).dimshuffle(1, 'x', 0) # (num_prediction_sets, 1, num_answers)

weighted_avg_predictions2 = T.sum(X * s2, axis=0) #  T.tensordot(X, s, [[0], [0]])

error2 = T.mean((weighted_avg_predictions2 - t) ** 2)
grad2 = T.grad(error2, W)

f2 = theano.function([W], error2)
g2 = theano.function([W], grad2)

print

print "Optimizing blending weights: shared"
w_init = np.random.randn(predictions_stack.shape[0]).astype(theano.config.floatX) * 0.01
w_zero = np.zeros(predictions_stack.shape[0], dtype=theano.config.floatX)
out, res, _ = scipy.optimize.fmin_l_bfgs_b(f, w_init, fprime=g, pgtol=1e-09, epsilon=1e-08, maxfun=10000)

rmse = np.sqrt(res)
out_s = np.exp(out)
out_s /= out_s.sum()
rmse_uniform = np.sqrt(f(w_zero))
print

print "Optimizing blending weights: separate"
w_init2 = np.random.randn(predictions_stack.shape[0] * 37).astype(theano.config.floatX) * 0.01
out2, res2, _ = scipy.optimize.fmin_l_bfgs_b(f2, w_init2, fprime=g2, pgtol=1e-09, epsilon=1e-08, maxfun=10000)

rmse2 = np.sqrt(res2)
out_s2 = np.exp(out2).reshape(37, predictions_stack.shape[0]).T
out_s2 /= out_s2.sum(0)[None, :]
print

print "Individual prediction errors:"
for path, error in zip(predictions_valid_paths, individual_prediction_errors):
    print "  %.6f\t%s" % (error, os.path.basename(path))

print
print "Resulting weights (shared):"
for path, weight in zip(predictions_valid_paths, out_s):
    print "  %.5f\t%s" % (weight, os.path.basename(path))

print
print "Resulting error (shared):\t\t%.6f" % rmse
print "Resulting error (separate):\t\t%.6f" % rmse2
print "Uniform weighting error:\t%.6f" % rmse_uniform

print
print "Blending testset predictions"
# we only load one testset predictions file at a time to save memory.

blended_predictions = None
blended_predictions_separate = None
blended_predictions_uniform = None

for path, weight, weights_separate in zip(predictions_test_paths, out_s, out_s2):
    # print "  %s" % os.path.basename(path)
    predictions = load_data.load_gz(path)
    predictions_uniform = predictions * (1.0 / len(predictions_test_paths))
    predictions_separate = predictions * weights_separate[None, :]
    predictions *= weight # inplace scaling

    if blended_predictions is None:
        blended_predictions = predictions
        blended_predictions_separate = predictions_separate
        blended_predictions_uniform = predictions_uniform
    else:
        blended_predictions += predictions
        blended_predictions_separate += predictions_separate
        blended_predictions_uniform += predictions_uniform


print
print "Storing blended predictions (shared) in %s" % TARGET_PATH
load_data.save_gz(TARGET_PATH, blended_predictions)

print
print "Storing blended predictions (separate) in %s" % TARGET_PATH_SEPARATE
load_data.save_gz(TARGET_PATH_SEPARATE, blended_predictions_separate)

print
print "Storing uniformly blended predictions in %s" % TARGET_PATH_UNIFORM
load_data.save_gz(TARGET_PATH_UNIFORM, blended_predictions_uniform)

    
print
print "Done!"
########NEW FILE########
__FILENAME__ = extract_pysex_params_extra
import load_data
import pysex

import numpy as np

import multiprocessing as mp
import cPickle as pickle


"""
Extract a bunch of extra info to get a better idea of the size of objects
"""


SUBSETS = ['train', 'test']
TARGET_PATTERN = "data/pysex_params_gen2_%s.npy.gz"
SIGMA2 = 5000 # 5000 # std of the centrality weighting (Gaussian)
DETECT_THRESH = 10.0 # detection threshold for sextractor
NUM_PROCESSES = 8


def estimate_params(img):
    img_green = img[..., 1] # supposedly using the green channel is a good idea. alternatively we could use luma.
    # this seems to work well enough.

    out = pysex.run(img_green, params=[
            'X_IMAGE', 'Y_IMAGE', # barycenter
            # 'XMIN_IMAGE', 'XMAX_IMAGE', 'YMIN_IMAGE', 'YMAX_IMAGE', # enclosing rectangle
            # 'XPEAK_IMAGE', 'YPEAK_IMAGE', # location of maximal intensity
            'A_IMAGE', 'B_IMAGE', 'THETA_IMAGE', # ellipse parameters
            # 'PETRO_RADIUS',
            'KRON_RADIUS', 'PETRO_RADIUS', 'FLUX_RADIUS', 'FWHM_IMAGE', # various radii
        ], conf_args={ 'DETECT_THRESH': DETECT_THRESH })

    # x and y are flipped for some reason.
    # theta should be 90 - theta.
    # we convert these here so we can plot stuff with matplotlib easily.
    try:
        ys = out['X_IMAGE'].tonumpy()
        xs = out['Y_IMAGE'].tonumpy()
        as_ = out['A_IMAGE'].tonumpy()
        bs = out['B_IMAGE'].tonumpy()
        thetas = 90 - out['THETA_IMAGE'].tonumpy()
        # kron_radii = out['KRON_RADIUS'].tonumpy()
        petro_radii = out['PETRO_RADIUS'].tonumpy()
        # flux_radii = out['FLUX_RADIUS'].tonumpy()
        # fwhms = out['FWHM_IMAGE'].tonumpy()

        # detect the most salient galaxy
        # take in account size and centrality
        surface_areas = np.pi * (as_ * bs)
        centralities = np.exp(-((xs - 211.5)**2 + (ys - 211.5)**2)/SIGMA2) # 211.5, 211.5 is the center of the image

        # salience is proportional to surface area, with a gaussian prior on the distance to the center.
        saliences = surface_areas * centralities
        most_salient_idx = np.argmax(saliences)

        x = xs[most_salient_idx]
        y = ys[most_salient_idx]
        a = as_[most_salient_idx]
        b = bs[most_salient_idx]
        theta = thetas[most_salient_idx]
        # kron_radius = kron_radii[most_salient_idx]
        petro_radius = petro_radii[most_salient_idx]
        # flux_radius = flux_radii[most_salient_idx]
        # fwhm = fwhms[most_salient_idx]

    except TypeError: # sometimes these are empty (no objects found), use defaults in that case
        x = 211.5
        y = 211.5
        a = np.nan # dunno what this has to be, deal with it later
        b = np.nan # same
        theta = np.nan # same
        # kron_radius = np.nan
        petro_radius = np.nan
        # flux_radius = np.nan
        # fwhm = np.nan


    # return (x, y, a, b, theta, flux_radius, kron_radius, petro_radius, fwhm)
    return (x, y, a, b, theta, petro_radius)



for subset in SUBSETS:
    print "SUBSET: %s" % subset
    print

    if subset == 'train':
        num_images = load_data.num_train
        ids = load_data.train_ids
    elif subset == 'test':
        num_images = load_data.num_test
        ids = load_data.test_ids
    

    def process(k):
        print "image %d/%d (%s)" % (k + 1, num_images, subset)
        img_id = ids[k]
        img = load_data.load_image(img_id, from_ram=True, subset=subset)
        return estimate_params(img)

    pool = mp.Pool(NUM_PROCESSES)

    estimated_params = pool.map(process, xrange(num_images), chunksize=100)
    pool.close()
    pool.join()

    # estimated_params = map(process, xrange(num_images)) # no mp for debugging

    params_array = np.array(estimated_params)

    target_path = TARGET_PATTERN % subset
    print "Saving to %s..." % target_path
    load_data.save_gz(target_path, params_array)

########NEW FILE########
__FILENAME__ = extract_pysex_params_gen2
import load_data
import pysex

import numpy as np

import multiprocessing as mp
import cPickle as pickle


"""
Extract a bunch of extra info to get a better idea of the size of objects
"""


SUBSETS = ['train', 'test']
TARGET_PATTERN = "data/pysex_params_gen2_%s.npy.gz"
SIGMA2 = 5000 # 5000 # std of the centrality weighting (Gaussian)
DETECT_THRESH = 2.0 # 10.0 # detection threshold for sextractor
NUM_PROCESSES = 8


def estimate_params(img):
    img_green = img[..., 1] # supposedly using the green channel is a good idea. alternatively we could use luma.
    # this seems to work well enough.

    out = pysex.run(img_green, params=[
            'X_IMAGE', 'Y_IMAGE', # barycenter
            # 'XMIN_IMAGE', 'XMAX_IMAGE', 'YMIN_IMAGE', 'YMAX_IMAGE', # enclosing rectangle
            # 'XPEAK_IMAGE', 'YPEAK_IMAGE', # location of maximal intensity
            'A_IMAGE', 'B_IMAGE', 'THETA_IMAGE', # ellipse parameters
            'PETRO_RADIUS',
            # 'KRON_RADIUS', 'PETRO_RADIUS', 'FLUX_RADIUS', 'FWHM_IMAGE', # various radii
        ], conf_args={ 'DETECT_THRESH': DETECT_THRESH })

    # x and y are flipped for some reason.
    # theta should be 90 - theta.
    # we convert these here so we can plot stuff with matplotlib easily.
    try:
        ys = out['X_IMAGE'].tonumpy()
        xs = out['Y_IMAGE'].tonumpy()
        as_ = out['A_IMAGE'].tonumpy()
        bs = out['B_IMAGE'].tonumpy()
        thetas = 90 - out['THETA_IMAGE'].tonumpy()
        # kron_radii = out['KRON_RADIUS'].tonumpy()
        petro_radii = out['PETRO_RADIUS'].tonumpy()
        # flux_radii = out['FLUX_RADIUS'].tonumpy()
        # fwhms = out['FWHM_IMAGE'].tonumpy()

        # detect the most salient galaxy
        # take in account size and centrality
        surface_areas = np.pi * (as_ * bs)
        centralities = np.exp(-((xs - 211.5)**2 + (ys - 211.5)**2)/SIGMA2) # 211.5, 211.5 is the center of the image

        # salience is proportional to surface area, with a gaussian prior on the distance to the center.
        saliences = surface_areas * centralities
        most_salient_idx = np.argmax(saliences)

        x = xs[most_salient_idx]
        y = ys[most_salient_idx]
        a = as_[most_salient_idx]
        b = bs[most_salient_idx]
        theta = thetas[most_salient_idx]
        # kron_radius = kron_radii[most_salient_idx]
        petro_radius = petro_radii[most_salient_idx]
        # flux_radius = flux_radii[most_salient_idx]
        # fwhm = fwhms[most_salient_idx]

    except TypeError: # sometimes these are empty (no objects found), use defaults in that case
        x = 211.5
        y = 211.5
        a = np.nan # dunno what this has to be, deal with it later
        b = np.nan # same
        theta = np.nan # same
        # kron_radius = np.nan
        petro_radius = np.nan
        # flux_radius = np.nan
        # fwhm = np.nan


    # return (x, y, a, b, theta, flux_radius, kron_radius, petro_radius, fwhm)
    return (x, y, a, b, theta, petro_radius)



for subset in SUBSETS:
    print "SUBSET: %s" % subset
    print

    if subset == 'train':
        num_images = load_data.num_train
        ids = load_data.train_ids
    elif subset == 'test':
        num_images = load_data.num_test
        ids = load_data.test_ids
    

    def process(k):
        print "image %d/%d (%s)" % (k + 1, num_images, subset)
        img_id = ids[k]
        img = load_data.load_image(img_id, from_ram=True, subset=subset)
        return estimate_params(img)

    pool = mp.Pool(NUM_PROCESSES)

    estimated_params = pool.map(process, xrange(num_images), chunksize=100)
    pool.close()
    pool.join()

    # estimated_params = map(process, xrange(num_images)) # no mp for debugging

    params_array = np.array(estimated_params)

    target_path = TARGET_PATTERN % subset
    print "Saving to %s..." % target_path
    load_data.save_gz(target_path, params_array)

########NEW FILE########
__FILENAME__ = layers
import numpy as np
import theano.tensor as T
import theano
from theano.tensor.signal.conv import conv2d as sconv2d
from theano.tensor.signal.downsample import max_pool_2d
from theano.tensor.nnet.conv import conv2d
from theano.sandbox.rng_mrg import MRG_RandomStreams as RandomStreams
import sys
import os
import cPickle as pickle


srng = RandomStreams()

# nonlinearities

sigmoid = T.nnet.sigmoid

tanh = T.tanh

def rectify(x):
    return T.maximum(x, 0.0)
    
def identity(x):
    # To create a linear layer.
    return x

def compress(x, C=10000.0):
    return T.log(1 + C * x ** 2) # no binning matrix here of course

def compress_abs(x, C=10000.0):
    return T.log(1 + C * abs(x))


def all_layers(layer):
    """
    Recursive function to gather all layers below the given layer (including the given layer)
    """
    if isinstance(layer, InputLayer) or isinstance(layer, Input2DLayer):
        return [layer]
    elif isinstance(layer, ConcatenateLayer):
        return sum([all_layers(i) for i in layer.input_layers], [layer])
    else:
        return [layer] + all_layers(layer.input_layer)

def all_parameters(layer):
    """
    Recursive function to gather all parameters, starting from the output layer
    """
    if isinstance(layer, InputLayer) or isinstance(layer, Input2DLayer):
        return []
    elif isinstance(layer, ConcatenateLayer):
        return sum([all_parameters(i) for i in layer.input_layers], [])
    else:
        return layer.params + all_parameters(layer.input_layer)

def all_bias_parameters(layer):
    """
    Recursive function to gather all bias parameters, starting from the output layer
    """    
    if isinstance(layer, InputLayer) or isinstance(layer, Input2DLayer):
        return []
    elif isinstance(layer, ConcatenateLayer):
        return sum([all_bias_parameters(i) for i in layer.input_layers], [])
    else:
        return layer.bias_params + all_bias_parameters(layer.input_layer)

def all_non_bias_parameters(layer):
    return [p for p in all_parameters(layer) if p not in all_bias_parameters(layer)]


def gather_rescaling_updates(layer, c):
    """
    Recursive function to gather weight rescaling updates when the constant is the same for all layers.
    """
    if isinstance(layer, InputLayer) or isinstance(layer, Input2DLayer):
        return []
    elif isinstance(layer, ConcatenateLayer):
        return sum([gather_rescaling_updates(i, c) for i in layer.input_layers], [])
    else:
        if hasattr(layer, 'rescaling_updates'):
            updates = layer.rescaling_updates(c)
        else:
            updates = []
        return updates + gather_rescaling_updates(layer.input_layer, c)



def get_param_values(layer):
    params = all_parameters(layer)
    return [p.get_value() for p in params]


def set_param_values(layer, param_values):
    params = all_parameters(layer)
    for p, pv in zip(params, param_values):
        p.set_value(pv)


def reset_all_params(layer):
    for l in all_layers(layer):
        if hasattr(l, 'reset_params'):
            l.reset_params()


    

def gen_updates_regular_momentum(loss, all_parameters, learning_rate, momentum, weight_decay):
    all_grads = [theano.grad(loss, param) for param in all_parameters]
    updates = []
    for param_i, grad_i in zip(all_parameters, all_grads):
        mparam_i = theano.shared(param_i.get_value()*0.)
        v = momentum * mparam_i - weight_decay * learning_rate * param_i  - learning_rate * grad_i
        updates.append((mparam_i, v))
        updates.append((param_i, param_i + v))
    return updates


# using the alternative formulation of nesterov momentum described at https://github.com/lisa-lab/pylearn2/pull/136
# such that the gradient can be evaluated at the current parameters.

def gen_updates_nesterov_momentum(loss, all_parameters, learning_rate, momentum, weight_decay):
    all_grads = [theano.grad(loss, param) for param in all_parameters]
    updates = []
    for param_i, grad_i in zip(all_parameters, all_grads):
        mparam_i = theano.shared(param_i.get_value()*0.)
        full_grad = grad_i + weight_decay * param_i
        v = momentum * mparam_i - learning_rate * full_grad # new momemtum
        w = param_i + momentum * v - learning_rate * full_grad # new parameter values
        updates.append((mparam_i, v))
        updates.append((param_i, w))
    return updates


def gen_updates_nesterov_momentum_no_bias_decay(loss, all_parameters, all_bias_parameters, learning_rate, momentum, weight_decay):
    """
    Nesterov momentum, but excluding the biases from the weight decay.
    """
    all_grads = [theano.grad(loss, param) for param in all_parameters]
    updates = []
    for param_i, grad_i in zip(all_parameters, all_grads):
        mparam_i = theano.shared(param_i.get_value()*0.)
        if param_i in all_bias_parameters:
            full_grad = grad_i
        else:
            full_grad = grad_i + weight_decay * param_i
        v = momentum * mparam_i - learning_rate * full_grad # new momemtum
        w = param_i + momentum * v - learning_rate * full_grad # new parameter values
        updates.append((mparam_i, v))
        updates.append((param_i, w))
    return updates


gen_updates = gen_updates_nesterov_momentum


def gen_updates_sgd(loss, all_parameters, learning_rate):
    all_grads = [theano.grad(loss, param) for param in all_parameters]
    updates = []
    for param_i, grad_i in zip(all_parameters, all_grads):
        updates.append((param_i, param_i - learning_rate * grad_i))
    return updates



def gen_updates_adagrad(loss, all_parameters, learning_rate=1.0, epsilon=1e-6):
    """
    epsilon is not included in the typical formula, 

    See "Notes on AdaGrad" by Chris Dyer for more info.
    """
    all_grads = [theano.grad(loss, param) for param in all_parameters]
    all_accumulators = [theano.shared(param.get_value()*0.) for param in all_parameters] # initialise to zeroes with the right shape

    updates = []
    for param_i, grad_i, acc_i in zip(all_parameters, all_grads, all_accumulators):
        acc_i_new = acc_i + grad_i**2
        updates.append((acc_i, acc_i_new))
        updates.append((param_i, param_i - learning_rate * grad_i / T.sqrt(acc_i_new + epsilon)))

    return updates


def gen_updates_rmsprop(loss, all_parameters, learning_rate=1.0, rho=0.9, epsilon=1e-6):
    """
    epsilon is not included in Hinton's video, but to prevent problems with relus repeatedly having 0 gradients, it is included here.

    Watch this video for more info: http://www.youtube.com/watch?v=O3sxAc4hxZU (formula at 5:20)

    also check http://climin.readthedocs.org/en/latest/rmsprop.html
    """
    all_grads = [theano.grad(loss, param) for param in all_parameters]
    all_accumulators = [theano.shared(param.get_value()*0.) for param in all_parameters] # initialise to zeroes with the right shape
    # all_accumulators = [theano.shared(param.get_value()*1.) for param in all_parameters] # initialise with 1s to damp initial gradients

    updates = []
    for param_i, grad_i, acc_i in zip(all_parameters, all_grads, all_accumulators):
        acc_i_new = rho * acc_i + (1 - rho) * grad_i**2
        updates.append((acc_i, acc_i_new))
        updates.append((param_i, param_i - learning_rate * grad_i / T.sqrt(acc_i_new + epsilon)))

    return updates


def gen_updates_adadelta(loss, all_parameters, learning_rate=1.0, rho=0.95, epsilon=1e-6):
    """
    in the paper, no learning rate is considered (so learning_rate=1.0). Probably best to keep it at this value.
    epsilon is important for the very first update (so the numerator does not become 0).

    rho = 0.95 and epsilon=1e-6 are suggested in the paper and reported to work for multiple datasets (MNIST, speech).

    see "Adadelta: an adaptive learning rate method" by Matthew Zeiler for more info.
    """
    all_grads = [theano.grad(loss, param) for param in all_parameters]
    all_accumulators = [theano.shared(param.get_value()*0.) for param in all_parameters] # initialise to zeroes with the right shape
    all_delta_accumulators = [theano.shared(param.get_value()*0.) for param in all_parameters]

    # all_accumulators: accumulate gradient magnitudes
    # all_delta_accumulators: accumulate update magnitudes (recursive!)

    updates = []
    for param_i, grad_i, acc_i, acc_delta_i in zip(all_parameters, all_grads, all_accumulators, all_delta_accumulators):
        acc_i_new = rho * acc_i + (1 - rho) * grad_i**2
        updates.append((acc_i, acc_i_new))

        update_i = grad_i * T.sqrt(acc_delta_i + epsilon) / T.sqrt(acc_i_new + epsilon) # use the 'old' acc_delta here
        updates.append((param_i, param_i - learning_rate * update_i))

        acc_delta_i_new = rho * acc_delta_i + (1 - rho) * update_i**2
        updates.append((acc_delta_i, acc_delta_i_new))

    return updates    



def shared_single(dim=2):
    """
    Shortcut to create an undefined single precision Theano shared variable.
    """
    shp = tuple([1] * dim)
    return theano.shared(np.zeros(shp, dtype='float32'))



class InputLayer(object):
    def __init__(self, mb_size, n_features, length):
        self.mb_size = mb_size
        self.n_features = n_features
        self.length = length
        self.input_var = T.tensor3('input')

    def get_output_shape(self):
        return (self.mb_size, self.n_features, self.length)

    def output(self, *args, **kwargs):
        """
        return theano variable
        """
        return self.input_var


class FlatInputLayer(InputLayer):
    def __init__(self, mb_size, n_features):
        self.mb_size = mb_size
        self.n_features = n_features
        self.input_var = T.matrix('input')

    def get_output_shape(self):
        return (self.mb_size, self.n_features)

    def output(self, *args, **kwargs):
        """
        return theano variable
        """
        return self.input_var


class Input2DLayer(object):
    def __init__(self, mb_size, n_features, width, height):
        self.mb_size = mb_size
        self.n_features = n_features
        self.width = width
        self.height = height
        self.input_var = T.tensor4('input')

    def get_output_shape(self):
        return (self.mb_size, self.n_features, self.width, self.height)

    def output(self, *args, **kwargs):
        return self.input_var




class PoolingLayer(object):
    def __init__(self, input_layer, ds_factor, ignore_border=False):
        self.ds_factor = ds_factor
        self.input_layer = input_layer
        self.ignore_border = ignore_border
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

    def get_output_shape(self):
        output_shape = list(self.input_layer.get_output_shape()) # convert to list because we cannot assign to a tuple element
        if self.ignore_border:
            output_shape[-1] = int(np.floor(float(output_shape[-1]) / self.ds_factor))
        else:
            output_shape[-1] = int(np.ceil(float(output_shape[-1]) / self.ds_factor))
        return tuple(output_shape)

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)
        return max_pool_2d(input, (1, self.ds_factor), self.ignore_border)



class Pooling2DLayer(object):
    def __init__(self, input_layer, pool_size, ignore_border=False): # pool_size is a tuple
        self.pool_size = pool_size # a tuple
        self.input_layer = input_layer
        self.ignore_border = ignore_border
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

    def get_output_shape(self):
        output_shape = list(self.input_layer.get_output_shape()) # convert to list because we cannot assign to a tuple element
        if self.ignore_border:
            output_shape[-2] = int(np.floor(float(output_shape[-2]) / self.pool_size[0]))
            output_shape[-1] = int(np.floor(float(output_shape[-1]) / self.pool_size[1]))
        else:
            output_shape[-2] = int(np.ceil(float(output_shape[-2]) / self.pool_size[0]))
            output_shape[-1] = int(np.ceil(float(output_shape[-1]) / self.pool_size[1]))
        return tuple(output_shape)

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)
        return max_pool_2d(input, self.pool_size, self.ignore_border)



class GlobalPooling2DLayer(object):
    """
    Global pooling across the entire feature map, useful in NINs.
    """
    def __init__(self, input_layer, pooling_function='mean'):
        self.input_layer = input_layer
        self.pooling_function = pooling_function
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

    def get_output_shape(self):
        return self.input_layer.get_output_shape()[:2] # this effectively removes the last 2 dimensions

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)
        if self.pooling_function == 'mean':
            out = input.mean([2, 3])
        elif self.pooling_function == 'max':
            out = input.max([2, 3])
        elif self.pooling_function == 'l2':
            out = T.sqrt((input ** 2).mean([2, 3]))

        return out



class DenseLayer(object):
    def __init__(self, input_layer, n_outputs, weights_std, init_bias_value, nonlinearity=rectify, dropout=0.):
        self.n_outputs = n_outputs
        self.input_layer = input_layer
        self.weights_std = np.float32(weights_std)
        self.init_bias_value = np.float32(init_bias_value)
        self.nonlinearity = nonlinearity
        self.dropout = dropout
        self.mb_size = self.input_layer.mb_size

        input_shape = self.input_layer.get_output_shape()
        self.n_inputs = int(np.prod(input_shape[1:]))
        self.flatinput_shape = (self.mb_size, self.n_inputs)

        self.W = shared_single(2) # theano.shared(np.random.randn(self.n_inputs, n_outputs).astype(np.float32) * weights_std)
        self.b = shared_single(1) # theano.shared(np.ones(n_outputs).astype(np.float32) * self.init_bias_value)
        self.params = [self.W, self.b]
        self.bias_params = [self.b]
        self.reset_params()

    def reset_params(self):
        self.W.set_value(np.random.randn(self.n_inputs, self.n_outputs).astype(np.float32) * self.weights_std)
        self.b.set_value(np.ones(self.n_outputs).astype(np.float32) * self.init_bias_value)

    def get_output_shape(self):
        return (self.mb_size, self.n_outputs)

    def output(self, input=None, dropout_active=True, *args, **kwargs): # use the 'dropout_active' keyword argument to disable it at test time. It is on by default.
        if input == None:
            input = self.input_layer.output(dropout_active=dropout_active, *args, **kwargs)
        if len(self.input_layer.get_output_shape()) > 2:
            input = input.reshape(self.flatinput_shape)

        if dropout_active and (self.dropout > 0.):
            retain_prob = 1 - self.dropout
            input = input / retain_prob * srng.binomial(input.shape, p=retain_prob, dtype='int32').astype('float32')
            # apply the input mask and rescale the input accordingly. By doing this it's no longer necessary to rescale the weights at test time.

        return self.nonlinearity(T.dot(input, self.W) + self.b.dimshuffle('x', 0))

    def rescaled_weights(self, c): # c is the maximal norm of the weight vector going into a single filter.
        norms = T.sqrt(T.sqr(self.W).mean(0, keepdims=True))
        scale_factors = T.minimum(c / norms, 1)
        return self.W * scale_factors

    def rescaling_updates(self, c):
        return [(self.W, self.rescaled_weights(c))]





class ConvLayer(object):
    def __init__(self, input_layer, n_filters, filter_length, weights_std, init_bias_value, nonlinearity=rectify, flip_conv_dims=False, dropout=0.):
        self.n_filters = n_filters
        self.filter_length = filter_length
        self.stride = 1
        self.input_layer = input_layer
        self.weights_std = np.float32(weights_std)
        self.init_bias_value = np.float32(init_bias_value)
        self.nonlinearity = nonlinearity
        self.flip_conv_dims = flip_conv_dims
        self.dropout = dropout
        self.mb_size = self.input_layer.mb_size

        self.input_shape = self.input_layer.get_output_shape()
        ' MB_size, N_filters, Filter_length '

#        if len(self.input_shape) == 2:
#            self.filter_shape = (n_filters, 1, filter_length)
#        elif len(self.input_shape) == 3:
#            self.filter_shape = (n_filters, self.input_shape[1], filter_length)
#        else:
#            raise

        self.filter_shape = (n_filters, self.input_shape[1], filter_length)

        self.W = shared_single(3) # theano.shared(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)
        self.b = shared_single(1) # theano.shared(np.ones(n_filters).astype(np.float32) * self.init_bias_value)
        self.params = [self.W, self.b]
        self.bias_params = [self.b]
        self.reset_params()

    def reset_params(self):
        self.W.set_value(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)
        self.b.set_value(np.ones(self.n_filters).astype(np.float32) * self.init_bias_value)

    def get_output_shape(self):
        output_length = (self.input_shape[2] - self.filter_length + self.stride) / self.stride # integer division
        output_shape = (self.input_shape[0], self.n_filters, output_length)
        return output_shape

    def output(self, input=None, *args, **kwargs):
        if input == None:
            input = self.input_layer.output(*args, **kwargs)

        if self.flip_conv_dims: # flip the conv dims to get a faster convolution when the filter_height is 1.
            flipped_input_shape = (self.input_shape[1], self.input_shape[0], self.input_shape[2])
            flipped_input = input.dimshuffle(1, 0, 2)
            conved = sconv2d(flipped_input, self.W, subsample=(1, self.stride), image_shape=flipped_input_shape, filter_shape=self.filter_shape)
            conved = T.addbroadcast(conved, 0) # else dimshuffle complains about dropping a non-broadcastable dimension
            conved = conved.dimshuffle(2, 1, 3)
        else:
            conved = sconv2d(input, self.W, subsample=(1, self.stride), image_shape=self.input_shape, filter_shape=self.filter_shape)
            conved = conved.dimshuffle(0, 1, 3) # gets rid of the obsolete filter height dimension

        return self.nonlinearity(conved + self.b.dimshuffle('x', 0, 'x'))

    # def dropoutput_train(self):
    #     p = self.dropout
    #     input = self.input_layer.dropoutput_train()
    #     if p > 0.:
    #         srng = RandomStreams()
    #         input = input * srng.binomial(self.input_layer.get_output_shape(), p=1 - p, dtype='int32').astype('float32')
    #     return self.output(input)

    # def dropoutput_predict(self):
    #     p = self.dropout
    #     input = self.input_layer.dropoutput_predict()
    #     if p > 0.:
    #         input = input * (1 - p)
    #     return self.output(input)




class StridedConvLayer(object):
    def __init__(self, input_layer, n_filters, filter_length, stride, weights_std, init_bias_value, nonlinearity=rectify, dropout=0.):
        if filter_length % stride != 0:
            print 'ERROR: the filter_length should be a multiple of the stride '
            raise
        if stride == 1:
            print 'ERROR: use the normal ConvLayer instead (stride=1) '
            raise

        self.n_filters = n_filters
        self.filter_length = filter_length
        self.stride = 1
        self.input_layer = input_layer
        self.stride = stride
        self.weights_std = np.float32(weights_std)
        self.init_bias_value = np.float32(init_bias_value)
        self.nonlinearity = nonlinearity
        self.dropout = dropout
        self.mb_size = self.input_layer.mb_size

        self.input_shape = self.input_layer.get_output_shape()
        ' MB_size, N_filters, Filter_length '


        self.filter_shape = (n_filters, self.input_shape[1], filter_length)

        self.W = shared_single(3) # theano.shared(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)
        self.b = shared_single(1) # theano.shared(np.ones(n_filters).astype(np.float32) * self.init_bias_value)
        self.params = [self.W, self.b]
        self.bias_params = [self.b]
        self.reset_params()

    def reset_params(self):
        self.W.set_value(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)
        self.b.set_value(np.ones(self.n_filters).astype(np.float32) * self.init_bias_value)

    def get_output_shape(self):
        output_length = (self.input_shape[2] - self.filter_length + self.stride) / self.stride # integer division
        output_shape = (self.input_shape[0], self.n_filters, output_length)
        return output_shape

    def output(self, input=None, *args, **kwargs):
        if input == None:
            input = self.input_layer.output(*args, **kwargs)
        input_shape = list(self.input_shape) # make a mutable copy

        # if the input is not a multiple of the stride, cut off the end
        if input_shape[2] % self.stride != 0:
            input_shape[2] = self.stride * (input_shape[2] / self.stride)
            input_truncated = input[:, :, :input_shape[2]] # integer division
        else:
            input_truncated = input

        r_input_shape = (input_shape[0], input_shape[1], input_shape[2] / self.stride, self.stride) # (mb size, #out, length/stride, stride)
        r_input = input_truncated.reshape(r_input_shape)

        if self.stride == self.filter_length:
            print " better use a tensordot"
            # r_input = r_input.dimshuffle(0, 2, 1, 3) # (mb size, length/stride, #out, stride)
            conved = T.tensordot(r_input, self.W, np.asarray([[1, 3], [1, 2]]))
            conved = conved.dimshuffle(0, 2, 1)
        elif self.stride == self.filter_length / 2:
            print " better use two tensordots"
            # define separate shapes for the even and odd parts, as they may differ depending on whether the sequence length
            # is an even or an odd multiple of the stride.
            length_even = input_shape[2] // self.filter_length
            length_odd = (input_shape[2] - self.stride) // self.filter_length

            r2_input_shape_even = (input_shape[0], input_shape[1], length_even, self.filter_length)
            r2_input_shape_odd = (input_shape[0], input_shape[1], length_odd, self.filter_length)

            r2_input_even = input[:, :, :length_even * self.filter_length].reshape(r2_input_shape_even)
            r2_input_odd = input[:, :, self.stride:length_odd * self.filter_length + self.stride].reshape(r2_input_shape_odd)

            conved_even = T.tensordot(r2_input_even, self.W, np.asarray([[1,3], [1, 2]]))
            conved_odd = T.tensordot(r2_input_odd, self.W, np.asarray([[1, 3], [1, 2]]))

            conved_even = conved_even.dimshuffle(0, 2, 1)
            conved_odd = conved_odd.dimshuffle(0, 2, 1)

            conved = T.zeros((conved_even.shape[0], conved_even.shape[1], conved_even.shape[2] + conved_odd.shape[2]))

            conved = T.set_subtensor(conved[:, :, ::2], conved_even)
            conved = T.set_subtensor(conved[:, :, 1::2], conved_odd)

        else:
            " use a convolution"
            r_filter_shape = (self.filter_shape[0], self.filter_shape[1], self.filter_shape[2] / self.stride, self.stride)

            r_W = self.W.reshape(r_filter_shape)

            conved = conv2d(r_input, r_W, image_shape=r_input_shape, filter_shape=r_filter_shape)
            conved = conved[:, :, :, 0] # get rid of the obsolete 'stride' dimension

        return self.nonlinearity(conved + self.b.dimshuffle('x', 0, 'x'))

    # def dropoutput_train(self):
    #     p = self.dropout
    #     input = self.input_layer.dropoutput_train()
    #     if p > 0.:
    #         srng = RandomStreams()
    #         input = input * srng.binomial(self.input_layer.get_output_shape(), p=1 - p, dtype='int32').astype('float32')
    #     return self.output(input)

    # def dropoutput_predict(self):
    #     p = self.dropout
    #     input = self.input_layer.dropoutput_predict()
    #     if p > 0.:
    #         input = input * (1 - p)
    #     return self.output(input)



class Conv2DLayer(object):
    def __init__(self, input_layer, n_filters, filter_width, filter_height, weights_std, init_bias_value, nonlinearity=rectify, dropout=0., dropout_tied=False, border_mode='valid'):
        self.n_filters = n_filters
        self.filter_width = filter_width
        self.filter_height = filter_height
        self.input_layer = input_layer
        self.weights_std = np.float32(weights_std)
        self.init_bias_value = np.float32(init_bias_value)
        self.nonlinearity = nonlinearity
        self.dropout = dropout
        self.dropout_tied = dropout_tied  # if this is on, the same dropout mask is applied across the entire input map
        self.border_mode = border_mode
        self.mb_size = self.input_layer.mb_size

        self.input_shape = self.input_layer.get_output_shape()
        ' mb_size, n_filters, filter_width, filter_height '

        self.filter_shape = (n_filters, self.input_shape[1], filter_width, filter_height)

        self.W = shared_single(4) # theano.shared(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)
        self.b = shared_single(1) # theano.shared(np.ones(n_filters).astype(np.float32) * self.init_bias_value)
        self.params = [self.W, self.b]
        self.bias_params = [self.b]
        self.reset_params()

    def reset_params(self):
        self.W.set_value(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)
        self.b.set_value(np.ones(self.n_filters).astype(np.float32) * self.init_bias_value)

    def get_output_shape(self):
        if self.border_mode == 'valid':
            output_width = self.input_shape[2] - self.filter_width + 1
            output_height = self.input_shape[3] - self.filter_height + 1
        elif self.border_mode == 'full':
            output_width = self.input_shape[2] + self.filter_width - 1
            output_height = self.input_shape[3] + self.filter_width - 1
        elif self.border_mode == 'same':
            output_width = self.input_shape[2]
            output_height = self.input_shape[3]
        else:
            raise RuntimeError("Invalid border mode: '%s'" % self.border_mode)

        output_shape = (self.input_shape[0], self.n_filters, output_width, output_height)
        return output_shape

    def output(self, input=None, dropout_active=True, *args, **kwargs):
        if input == None:
            input = self.input_layer.output(dropout_active=dropout_active, *args, **kwargs)

        if dropout_active and (self.dropout > 0.):
            retain_prob = 1 - self.dropout
            if self.dropout_tied:
                # tying of the dropout masks across the entire feature maps, so broadcast across the feature maps.
                mask = srng.binomial((input.shape[0], input.shape[1]), p=retain_prob, dtype='int32').astype('float32').dimshuffle(0, 1, 'x', 'x')
            else:
                mask = srng.binomial(input.shape, p=retain_prob, dtype='int32').astype('float32')
                # apply the input mask and rescale the input accordingly. By doing this it's no longer necessary to rescale the weights at test time.
            input = input / retain_prob * mask

        if self.border_mode in ['valid', 'full']:
            conved = conv2d(input, self.W, subsample=(1, 1), image_shape=self.input_shape, filter_shape=self.filter_shape, border_mode=self.border_mode)
        elif self.border_mode == 'same':
            conved = conv2d(input, self.W, subsample=(1, 1), image_shape=self.input_shape, filter_shape=self.filter_shape, border_mode='full')
            shift_x = (self.filter_width - 1) // 2
            shift_y = (self.filter_height - 1) // 2
            conved = conved[:, :, shift_x:self.input_shape[2] + shift_x, shift_y:self.input_shape[3] + shift_y]
        else:
            raise RuntimeError("Invalid border mode: '%s'" % self.border_mode)
        return self.nonlinearity(conved + self.b.dimshuffle('x', 0, 'x', 'x'))

    def rescaled_weights(self, c): # c is the maximal norm of the weight vector going into a single filter.
        weights_shape = self.W.shape
        W_flat = self.W.reshape((weights_shape[0], T.prod(weights_shape[1:])))
        norms = T.sqrt(T.sqr(W_flat).mean(1))
        scale_factors = T.minimum(c / norms, 1)
        return self.W * scale_factors.dimshuffle(0, 'x', 'x', 'x')

    def rescaling_updates(self, c):
        return [(self.W, self.rescaled_weights(c))]




class MaxoutLayer(object):
    def __init__(self, input_layer, n_filters_per_unit, dropout=0.):
        self.n_filters_per_unit = n_filters_per_unit
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.dropout = dropout
        self.mb_size = self.input_layer.mb_size

        self.params = []
        self.bias_params = []

    def get_output_shape(self):
        return (self.input_shape[0], self.input_shape[1] / self.n_filters_per_unit, self.input_shape[2])

    def output(self, input=None, dropout_active=True, *args, **kwargs):
        if input == None:
            input = self.input_layer.output(dropout_active=dropout_active, *args, **kwargs)

        if dropout_active and (self.dropout > 0.):
            retain_prob = 1 - self.dropout
            input = input / retain_prob * srng.binomial(input.shape, p=retain_prob, dtype='int32').astype('float32')
            # apply the input mask and rescale the input accordingly. By doing this it's no longer necessary to rescale the weights at test time.

        output = input.reshape((self.input_shape[0], self.input_shape[1] / self.n_filters_per_unit, self.n_filters_per_unit, self.input_shape[2]))
        output = T.max(output, 2)
        return output





class NIN2DLayer(object):
    def __init__(self, input_layer, n_outputs, weights_std, init_bias_value, nonlinearity=rectify, dropout=0., dropout_tied=False):
        self.n_outputs = n_outputs
        self.input_layer = input_layer
        self.weights_std = np.float32(weights_std)
        self.init_bias_value = np.float32(init_bias_value)
        self.nonlinearity = nonlinearity
        self.dropout = dropout
        self.dropout_tied = dropout_tied # if this is on, the same dropout mask is applied to all instances of the layer across the map.
        self.mb_size = self.input_layer.mb_size

        self.input_shape = self.input_layer.get_output_shape()
        self.n_inputs = self.input_shape[1]

        self.W = shared_single(2) # theano.shared(np.random.randn(self.n_inputs, n_outputs).astype(np.float32) * weights_std)
        self.b = shared_single(1) # theano.shared(np.ones(n_outputs).astype(np.float32) * self.init_bias_value)
        self.params = [self.W, self.b]
        self.bias_params = [self.b]
        self.reset_params()

    def reset_params(self):
        self.W.set_value(np.random.randn(self.n_inputs, self.n_outputs).astype(np.float32) * self.weights_std)
        self.b.set_value(np.ones(self.n_outputs).astype(np.float32) * self.init_bias_value)

    def get_output_shape(self):
        return (self.mb_size, self.n_outputs, self.input_shape[2], self.input_shape[3])

    def output(self, input=None, dropout_active=True, *args, **kwargs): # use the 'dropout_active' keyword argument to disable it at test time. It is on by default.
        if input == None:
            input = self.input_layer.output(dropout_active=dropout_active, *args, **kwargs)
        
        if dropout_active and (self.dropout > 0.):
            retain_prob = 1 - self.dropout
            if self.dropout_tied:
                # tying of the dropout masks across the entire feature maps, so broadcast across the feature maps.

                 mask = srng.binomial((input.shape[0], input.shape[1]), p=retain_prob, dtype='int32').astype('float32').dimshuffle(0, 1, 'x', 'x')
            else:
                mask = srng.binomial(input.shape, p=retain_prob, dtype='int32').astype('float32')
                # apply the input mask and rescale the input accordingly. By doing this it's no longer necessary to rescale the weights at test time.
            input = input / retain_prob * mask

        prod = T.tensordot(input, self.W, [[1], [0]]) # this has shape (batch_size, width, height, out_maps)
        prod = prod.dimshuffle(0, 3, 1, 2) # move the feature maps to the 1st axis, where they were in the input
        return self.nonlinearity(prod + self.b.dimshuffle('x', 0, 'x', 'x'))






class FilterPoolingLayer(object):
    """
    pools filter outputs from the previous layer. If the pooling function is 'max', the result is maxout.
    supported pooling function:
        - 'max': maxout (max pooling)
        - 'ss': sum of squares (L2 pooling)
        - 'rss': root of the sum of the squares (L2 pooling)
    """
    def __init__(self, input_layer, n_filters_per_unit, dropout=0., pooling_function='max'):
        self.n_filters_per_unit = n_filters_per_unit
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.dropout = dropout
        self.pooling_function = pooling_function
        self.mb_size = self.input_layer.mb_size

        self.params = []
        self.bias_params = []

    def get_output_shape(self):
        return (self.input_shape[0], self.input_shape[1] / self.n_filters_per_unit, self.input_shape[2])

    def output(self, input=None, dropout_active=True, *args, **kwargs):
        if input == None:
            input = self.input_layer.output(dropout_active=dropout_active, *args, **kwargs)

        if dropout_active and (self.dropout > 0.):
            retain_prob = 1 - self.dropout
            input = input / retain_prob * srng.binomial(input.shape, p=retain_prob, dtype='int32').astype('float32')
            # apply the input mask and rescale the input accordingly. By doing this it's no longer necessary to rescale the weights at test time.

        output = input.reshape((self.input_shape[0], self.input_shape[1] / self.n_filters_per_unit, self.n_filters_per_unit, self.input_shape[2]))

        if self.pooling_function == "max":
            output = T.max(output, 2)
        elif self.pooling_function == "ss":
            output = T.mean(output**2, 2)
        elif self.pooling_function == "rss":
            # a stabilising constant to prevent NaN in the gradient
            padding = 0.000001
            output = T.sqrt(T.mean(output**2, 2) + padding)
        else:
            raise "Unknown pooling function: %s" % self.pooling_function

        return output




class OutputLayer(object):
    def __init__(self, input_layer, error_measure='mse'):
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.params = []
        self.bias_params = []
        self.error_measure = error_measure
        self.mb_size = self.input_layer.mb_size

        self.target_var = T.matrix() # variable for the labels
        if error_measure == 'maha':
            self.target_cov_var = T.tensor3()

    def error(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)

        # never actually dropout anything on the output layer, just pass it along!

        if self.error_measure == 'mse':
            error = T.mean((input - self.target_var) ** 2)
        elif self.error_measure == 'ce': # cross entropy
            error = T.mean(T.nnet.binary_crossentropy(input, self.target_var))
        elif self.error_measure == 'nca':
            epsilon = 1e-8
            #dist_ij = - T.dot(input, input.T)
            # dist_ij = input
            dist_ij = T.sum((input.dimshuffle(0, 'x', 1) - input.dimshuffle('x', 0, 1)) ** 2, axis=2)
            p_ij_unnormalised = T.exp(-dist_ij) + epsilon
            p_ij_unnormalised = p_ij_unnormalised * (1 - T.eye(self.mb_size)) # set the diagonal to 0
            p_ij = p_ij_unnormalised / T.sum(p_ij_unnormalised, axis=1)
            return - T.mean(p_ij * self.target_var)

            # 
            # p_ij = p_ij_unnormalised / T.sum(p_ij_unnormalised, axis=1)
            # return np.mean(p_ij * self.target_var)
        elif self.error_measure == 'maha':
            # e = T.shape_padright(input - self.target_var)
            # e = (input - self.target_var).dimshuffle((0, 'x', 1))
            # error = T.sum(T.sum(self.target_cov_var * e, 2) ** 2) / self.mb_size

            e = (input - self.target_var)
            eTe = e.dimshuffle((0, 'x', 1)) * e.dimshuffle((0, 1, 'x'))
            error = T.sum(self.target_cov_var * eTe) / self.mb_size
        else:
            1 / 0

        return error

    def error_rate(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)
        error_rate = T.mean(T.neq(input > 0.5, self.target_var))
        return error_rate

    def predictions(self, *args, **kwargs):
        return self.input_layer.output(*args, **kwargs)




class FlattenLayer(object):
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size

    def get_output_shape(self):
        input_shape = self.input_layer.get_output_shape()
        size = int(np.prod(input_shape[1:]))
        return (self.mb_size, size)

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)
        return input.reshape(self.get_output_shape())




class ConcatenateLayer(object):
    def __init__(self, input_layers):
        self.input_layers = input_layers
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layers[0].mb_size

    def get_output_shape(self):
        sizes = [i.get_output_shape()[1] for i in self.input_layers] # this assumes the layers are already flat!
        return (self.mb_size, sum(sizes))

    def output(self, *args, **kwargs):
        inputs = [i.output(*args, **kwargs) for i in self.input_layers]
        return T.concatenate(inputs, axis=1)



class ResponseNormalisationLayer(object):
    def __init__(self, input_layer, n, k, alpha, beta):
        """
        n: window size
        k: bias
        alpha: scaling
        beta: power
        """
        self.input_layer = input_layer
        self.params = []
        self.bias_params = []
        self.n = n
        self.k = k
        self.alpha = alpha
        self.beta = beta
        self.mb_size = self.input_layer.mb_size

    def get_output_shape(self):
        return self.input_layer.get_output_shape()

    def output(self, *args, **kwargs):
        """
        Code is based on https://github.com/lisa-lab/pylearn2/blob/master/pylearn2/expr/normalize.py
        """
        input = self.input_layer.output(*args, **kwargs)

        half = self.n // 2
        sq = T.sqr(input)
        b, ch, r, c = input.shape
        extra_channels = T.alloc(0., b, ch + 2*half, r, c)
        sq = T.set_subtensor(extra_channels[:,half:half+ch,:,:], sq)
        scale = self.k

        for i in xrange(self.n):
            scale += self.alpha * sq[:,i:i+ch,:,:]

        scale = scale ** self.beta

        return input / scale




class StridedConv2DLayer(object):
    def __init__(self, input_layer, n_filters, filter_width, filter_height, stride_x, stride_y, weights_std, init_bias_value, nonlinearity=rectify, dropout=0., dropout_tied=False, implementation='convolution'):
        """
        implementation can be:
            - convolution: use conv2d with the subsample parameter
            - unstrided: use conv2d + reshaping so the result is a convolution with strides (1, 1)
            - single_dot: use a large tensor product
            - many_dots: use a bunch of tensor products
        """
        self.n_filters = n_filters
        self.filter_width = filter_width
        self.filter_height = filter_height
        self.stride_x = stride_x
        self.stride_y = stride_y
        self.input_layer = input_layer
        self.weights_std = np.float32(weights_std)
        self.init_bias_value = np.float32(init_bias_value)
        self.nonlinearity = nonlinearity
        self.dropout = dropout
        self.dropout_tied = dropout_tied  # if this is on, the same dropout mask is applied across the entire input map
        self.implementation = implementation # this controls whether the convolution is computed using theano's op,
        # as a bunch of tensor products, or a single stacked tensor product.
        self.mb_size = self.input_layer.mb_size

        self.input_shape = self.input_layer.get_output_shape()
        ' mb_size, n_filters, filter_width, filter_height '

        self.filter_shape = (n_filters, self.input_shape[1], filter_width, filter_height)

        if self.filter_width % self.stride_x != 0:
            raise RuntimeError("Filter width is not a multiple of the stride in the X direction")

        if self.filter_height % self.stride_y != 0:
            raise RuntimeError("Filter height is not a multiple of the stride in the Y direction")

        self.W = shared_single(4) # theano.shared(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)
        self.b = shared_single(1) # theano.shared(np.ones(n_filters).astype(np.float32) * self.init_bias_value)
        self.params = [self.W, self.b]
        self.bias_params = [self.b]
        self.reset_params()

    def reset_params(self):
        self.W.set_value(np.random.randn(*self.filter_shape).astype(np.float32) * self.weights_std)  
        self.b.set_value(np.ones(self.n_filters).astype(np.float32) * self.init_bias_value)      

    def get_output_shape(self):
        output_width = (self.input_shape[2] - self.filter_width + self.stride_x) // self.stride_x # integer division
        output_height = (self.input_shape[3] - self.filter_height + self.stride_y) // self.stride_y # integer division
        output_shape = (self.input_shape[0], self.n_filters, output_width, output_height)
        return output_shape

    def output(self, input=None, dropout_active=True, *args, **kwargs):
        if input == None:
            input = self.input_layer.output(dropout_active=dropout_active, *args, **kwargs)

        if dropout_active and (self.dropout > 0.):
            retain_prob = 1 - self.dropout
            if self.dropout_tied:
                # tying of the dropout masks across the entire feature maps, so broadcast across the feature maps.
                mask = srng.binomial((input.shape[0], input.shape[1]), p=retain_prob, dtype='int32').astype('float32').dimshuffle(0, 1, 'x', 'x')
            else:
                mask = srng.binomial(input.shape, p=retain_prob, dtype='int32').astype('float32')
                # apply the input mask and rescale the input accordingly. By doing this it's no longer necessary to rescale the weights at test time.
            input = input / retain_prob * mask

        output_shape = self.get_output_shape()
        W_flipped = self.W[:, :, ::-1, ::-1]

        # crazy convolution stuff!
        if self.implementation == 'single_dot':
            # one stacked product
            num_steps_x = self.filter_width // self.stride_x
            num_steps_y = self.filter_height // self.stride_y
            # print "DEBUG: %d x %d yields %d subtensors" % (num_steps_x, num_steps_y, num_steps_x * num_steps_y)

            # pad the input so all the shifted dot products fit inside. shape is (b, c, w, h)
            # padded_width =  int(np.ceil(self.input_shape[2] / float(self.filter_width))) * self.filter_width # INCORRECT
            # padded_height = int(np.ceil(self.input_shape[3] / float(self.filter_height))) * self.filter_height # INCORRECT

            padded_width =  (self.input_shape[2] // self.filter_width) * self.filter_width + (num_steps_x - 1) * self.stride_x
            padded_height = (self.input_shape[3] // self.filter_height) * self.filter_height + (num_steps_y - 1) * self.stride_y

            # print "DEBUG - PADDED WIDTH: %d" % padded_width
            # print "DEBUG - PADDED HEIGHT: %d" % padded_height

            # at this point, it is possible that the padded_width and height are SMALLER than the input size.
            # so then we have to truncate first.
            truncated_width = min(self.input_shape[2], padded_width)
            truncated_height = min(self.input_shape[3], padded_height)
            input_truncated = input[:, :, :truncated_width, :truncated_height]

            input_padded_shape = (self.input_shape[0], self.input_shape[1], padded_width, padded_height)
            input_padded = T.zeros(input_padded_shape)
            input_padded = T.set_subtensor(input_padded[:, :, :truncated_width, :truncated_height], input_truncated)


            inputs_x = []
            for num_x in xrange(num_steps_x):
                inputs_y = []
                for num_y in xrange(num_steps_y):
                    shift_x = num_x * self.stride_x # pixel shift in the x direction
                    shift_y = num_y * self.stride_y # pixel shift in the y direction

                    width = (input_padded_shape[2] - shift_x) // self.filter_width
                    height = (input_padded_shape[3] - shift_y) // self.filter_height

                    r_input_shape = (input_padded_shape[0], input_padded_shape[1], width, self.filter_width, height, self.filter_height)

                    r_input = input_padded[:, :, shift_x:width * self.filter_width + shift_x, shift_y:height * self.filter_height + shift_y]
                    r_input = r_input.reshape(r_input_shape)

                    inputs_y.append(r_input)

                inputs_x.append(T.stack(*inputs_y))

            inputs_stacked = T.stack(*inputs_x) # shape is (n_x, n_y, b, c, w_x, f_x, w_y, f_y)
            r_conved = T.tensordot(inputs_stacked, W_flipped, np.asarray([[3, 5, 7], [1, 2, 3]]))
            # resulting shape is (n_x, n_y, b, w_x, w_y, n_filters)
            # output needs to be (b, n_filters, w_x * n_x, w_y * n_y)
            r_conved = r_conved.dimshuffle(2, 5, 3, 0, 4, 1) # (b, n_filters, w_x, n_x, w_y, n_y)
            conved = r_conved.reshape((r_conved.shape[0], r_conved.shape[1], r_conved.shape[2] * r_conved.shape[3], r_conved.shape[4] * r_conved.shape[5]))
            # result is (b, n_f, w, h)

            # remove padding
            conved = conved[:, :, :output_shape[2], :output_shape[3]]

            # raise NotImplementedError("single stacked product not implemented yet")
        elif self.implementation == 'many_dots':
            # separate products
            num_steps_x = self.filter_width // self.stride_x
            num_steps_y = self.filter_height // self.stride_y
            # print "DEBUG: %d x %d yields %d subtensors" % (num_steps_x, num_steps_y, num_steps_x * num_steps_y)

            conved = T.zeros(output_shape)

            for num_x in xrange(num_steps_x):
                for num_y in xrange(num_steps_y):
                    shift_x = num_x * self.stride_x # pixel shift in the x direction
                    shift_y = num_y * self.stride_y # pixel shift in the y direction

                    width = (self.input_shape[2] - shift_x) // self.filter_width
                    height = (self.input_shape[3] - shift_y) // self.filter_height

                    if (width == 0) or (height == 0): # we can safely skip this product, it doesn't contribute to the final convolution.
                        # print "DEBUG: WARNING: skipping %d,%d" % (num_x, num_y)
                        continue

                    r_input_shape = (self.input_shape[0], self.input_shape[1], width, self.filter_width, height, self.filter_height)

                    r_input = input[:, :, shift_x:width * self.filter_width + shift_x, shift_y:height * self.filter_height + shift_y]
                    r_input = r_input.reshape(r_input_shape)

                    r_conved = T.tensordot(r_input, W_flipped, np.asarray([[1, 3, 5], [1, 2, 3]])) # shape (b,  w, h, n_filters)
                    r_conved = r_conved.dimshuffle(0, 3, 1, 2) # (b, n_filters, w, h)
                    conved = T.set_subtensor(conved[:, :, num_x::num_steps_x, num_y::num_steps_y], r_conved)

        elif self.implementation == 'unstrided':
            num_steps_x = self.filter_width // self.stride_x
            num_steps_y = self.filter_height // self.stride_y

            # input sizes need to be multiples of the strides, truncate to correct sizes.
            truncated_width =  (self.input_shape[2] // self.stride_x) * self.stride_x
            truncated_height = (self.input_shape[3] // self.stride_y) * self.stride_y
            input_truncated = input[:, :, :truncated_width, :truncated_height]

            r_input_shape = (self.input_shape[0], self.input_shape[1], truncated_width // self.stride_x, self.stride_x, truncated_height // self.stride_y, self.stride_y)
            r_input = input_truncated.reshape(r_input_shape)

            # fold strides into the feature maps dimension
            r_input_folded_shape = (self.input_shape[0], self.input_shape[1] * self.stride_x * self.stride_y, truncated_width // self.stride_x, truncated_height // self.stride_y)
            r_input_folded = r_input.transpose(0, 1, 3, 5, 2, 4).reshape(r_input_folded_shape)

            r_filter_shape = (self.filter_shape[0], self.filter_shape[1], num_steps_x, self.stride_x, num_steps_y, self.stride_y)
            r_W_flipped = W_flipped.reshape(r_filter_shape) # need to operate on the flipped W here, else things get hairy.

            # fold strides into the feature maps dimension
            r_filter_folded_shape = (self.filter_shape[0], self.filter_shape[1] * self.stride_x * self.stride_y, num_steps_x, num_steps_y)
            r_W_flipped_folded = r_W_flipped.transpose(0, 1, 3, 5, 2, 4).reshape(r_filter_folded_shape)
            r_W_folded = r_W_flipped_folded[:, :, ::-1, ::-1] # unflip

            conved = conv2d(r_input_folded, r_W_folded, subsample=(1, 1), image_shape=r_input_folded_shape, filter_shape=r_filter_folded_shape)
            # 'conved' should already have the right shape

        elif self.implementation == 'convolution':
            conved = conv2d(input, self.W, subsample=(self.stride_x, self.stride_y), image_shape=self.input_shape, filter_shape=self.filter_shape)
            # raise NotImplementedError("strided convolution using the theano op not implemented yet")
        else:
            raise RuntimeError("Invalid implementation string: '%s'" % self.implementation)

        return self.nonlinearity(conved + self.b.dimshuffle('x', 0, 'x', 'x'))


    def rescaled_weights(self, c): # c is the maximal norm of the weight vector going into a single filter.
        weights_shape = self.W.shape
        W_flat = self.W.reshape((weights_shape[0], T.prod(weights_shape[1:])))
        norms = T.sqrt(T.sqr(W_flat).mean(1))
        scale_factors = T.minimum(c / norms, 1)
        return self.W * scale_factors.dimshuffle(0, 'x', 'x', 'x')


    def rescaling_updates(self, c):
        return [(self.W, self.rescaled_weights(c))]




class Rot90SliceLayer(object):
    """
    This layer cuts 4 square-shaped parts of out of the input, rotates them 0, 90, 180 and 270 degrees respectively
    so they all have the same orientation, and then stacks them in the minibatch dimension.

    This allows for the same filters to be used in 4 directions.

    IMPORTANT: this increases the minibatch size for all subsequent layers!
    """
    def __init__(self, input_layer, part_size):
        self.input_layer = input_layer
        self.part_size = part_size
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size * 4 # 4 times bigger because of the stacking!

    def get_output_shape(self):
        input_shape = self.input_layer.get_output_shape()
        return (self.mb_size, input_shape[1], self.part_size, self.part_size)

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)

        ps = self.part_size # shortcut 
        part0 = input[:, :, :ps, :ps] # 0 degrees
        part1 = input[:, :, :ps, :-ps-1:-1].dimshuffle(0, 1, 3, 2) # 90 degrees
        part2 = input[:, :, :-ps-1:-1, :-ps-1:-1] # 180 degrees
        part3 = input[:, :, :-ps-1:-1, :ps].dimshuffle(0, 1, 3, 2) # 270 degrees

        return T.concatenate([part0, part1, part2, part3], axis=0)


class Rot90MergeLayer(FlattenLayer):
    """
    This layer merges featuremaps that were separated by the Rot90SliceLayer and flattens them in one go.
    """
    def __init__(self, input_layer):
        self.input_layer = input_layer
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size // 4 # divide by 4 again (it was multiplied by 4 by the Rot90SliceLayer)

    def get_output_shape(self):
        input_shape = self.input_layer.get_output_shape()
        size = int(np.prod(input_shape[1:])) * 4
        return (self.mb_size, size)

    def output(self, *args, **kwargs):
        input_shape = self.input_layer.get_output_shape()
        input = self.input_layer.output(*args, **kwargs)
        input_r = input.reshape((4, self.mb_size, input_shape[1] * input_shape[2] * input_shape[3])) # split out the 4* dimension
        return input_r.transpose(1, 0, 2).reshape(self.get_output_shape())




class MultiRotSliceLayer(ConcatenateLayer):
    """
    This layer cuts 4 square-shaped parts of out of the input, rotates them 0, 90, 180 and 270 degrees respectively
    so they all have the same orientation, and then stacks them in the minibatch dimension.

    It takes multiple input layers (expected to be multiple rotations of the same image) and stacks the results.
    All inputs should have the same shape!

    This allows for the same filters to be used in many different directions.

    IMPORTANT: this increases the minibatch size for all subsequent layers!

    enabling include_flip also includes flipped versions of all the parts. This doubles the number of views.
    """
    def __init__(self, input_layers, part_size, include_flip=False):
        self.input_layers = input_layers
        self.part_size = part_size
        self.include_flip = include_flip
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layers[0].mb_size * 4 * len(self.input_layers)
        # 4 * num_layers times bigger because of the stacking!
        
        if self.include_flip:
            self.mb_size *= 2 # include_flip doubles the number of views.
        

    def get_output_shape(self):
        input_shape = self.input_layers[0].get_output_shape()
        return (self.mb_size, input_shape[1], self.part_size, self.part_size)

    def output(self, *args, **kwargs):
        parts = []
        for input_layer in self.input_layers:
            input = input_layer.output(*args, **kwargs)
            ps = self.part_size # shortcut 

            if self.include_flip:
                input_representations = [input, input[:, :, :, ::-1]] # regular and flipped
            else:
                input_representations = [input] # just regular

            for input_rep in input_representations:
                part0 = input_rep[:, :, :ps, :ps] # 0 degrees
                part1 = input_rep[:, :, :ps, :-ps-1:-1].dimshuffle(0, 1, 3, 2) # 90 degrees
                part2 = input_rep[:, :, :-ps-1:-1, :-ps-1:-1] # 180 degrees
                part3 = input_rep[:, :, :-ps-1:-1, :ps].dimshuffle(0, 1, 3, 2) # 270 degrees
                parts.extend([part0, part1, part2, part3])

        return T.concatenate(parts, axis=0)


class MultiRotMergeLayer(FlattenLayer):
    """
    This layer merges featuremaps that were separated by the MultiRotSliceLayer and flattens them in one go.
    """
    def __init__(self, input_layer, num_views):
        """
        num_views is the number of different input representations that were merged.
        """
        self.input_layer = input_layer
        self.num_views = num_views
        self.params = []
        self.bias_params = []
        self.mb_size = self.input_layer.mb_size // (4 * self.num_views) # divide by total number of parts

    def get_output_shape(self):
        input_shape = self.input_layer.get_output_shape()
        size = int(np.prod(input_shape[1:])) * (4 * self.num_views)
        return (self.mb_size, size)

    def output(self, *args, **kwargs):
        input_shape = self.input_layer.get_output_shape()
        input = self.input_layer.output(*args, **kwargs)
        input_r = input.reshape((4 * self.num_views, self.mb_size, int(np.prod(input_shape[1:])))) # split out the 4* dimension
        return input_r.transpose(1, 0, 2).reshape(self.get_output_shape())




def sparse_initialisation(n_inputs, n_outputs, sparsity=0.05, std=0.01):
    """
    sparsity: fraction of the weights to each output unit that should be nonzero
    """
    weights = np.zeros((n_inputs, n_outputs), dtype='float32')
    size = int(sparsity * n_inputs)
    for k in xrange(n_outputs):
        indices = np.arange(n_inputs)
        np.random.shuffle(indices)
        indices = indices[:size]
        values = np.random.randn(size).astype(np.float32) * std
        weights[indices, k] = values

    return weights



class FeatureMaxPoolingLayer_old(object):
    """
    OLD implementation using T.maximum iteratively. This turns out to be very slow.

    Max pooling across feature maps. This can be used to implement maxout.
    This is similar to the FilterPoolingLayer, but this version uses a different
    implementation that supports input of any dimensionality and can do pooling 
    across any of the dimensions. It also supports overlapping pooling (the stride
    and downsample factor can be set separately).

    based on code from pylearn2's Maxout implementation.
    https://github.com/lisa-lab/pylearn2/blob/a2b616a384b9f39fa6f3e8d9e316b3af1274e687/pylearn2/models/maxout.py

    IMPORTANT: this layer requires that num_output_features = (feature_dim_size - pool_size + stride) / stride is INTEGER.
    if it isn't, it probably won't work properly.
    """
    def __init__(self, input_layer, pool_size, stride=None, feature_dim=1):
        """
        pool_size: the number of inputs to be pooled together.

        stride: the stride between pools, if not set it defaults to pool_size
        (no overlap)

        feature_dim: the dimension of the input to pool across. By default this is 1
        for both dense and convolutional layers (bc01).
        For c01b, this has to be set to 0.
        """
        self.pool_size = pool_size
        self.stride = stride if stride is not None else pool_size
        self.feature_dim = feature_dim
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.mb_size = self.input_layer.mb_size

        self.params = []
        self.bias_params = []

    def get_output_shape(self):
        feature_dim_size = self.input_shape[self.feature_dim]
        out_feature_dim_size = (feature_dim_size - self.pool_size + self.stride) // self.stride
        output_shape = list(self.input_shape) # make a mutable copy
        output_shape[self.feature_dim] = out_feature_dim_size
        return tuple(output_shape)

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)

        indices = [slice(None)] * input.ndim # select everything

        output = None
        for k in xrange(self.pool_size):
            indices[self.feature_dim] = slice(k, None, self.stride) # narrow down the selection for the feature dim
            m = input[tuple(indices)]
            if output is None:
                output = m
            else:
                output = T.maximum(output, m)

        return output



class FeatureMaxPoolingLayer(object):
    """
    Max pooling across feature maps. This can be used to implement maxout.
    This is similar to the FilterPoolingLayer, but this version uses a different
    implementation that supports input of any dimensionality and can do pooling 
    across any of the dimensions.

    IMPORTANT: this layer requires that feature_dim_size is a multiple of pool_size.
    """
    def __init__(self, input_layer, pool_size, feature_dim=1, implementation='max_pool'):
        """
        pool_size: the number of inputs to be pooled together.

        feature_dim: the dimension of the input to pool across. By default this is 1
        for both dense and convolutional layers (bc01).
        For c01b, this has to be set to 0.

        implementation:
            - 'max_pool': uses theano's max_pool_2d - doesn't work for input dimension > 1024!
            - 'reshape': reshapes the tensor to create a 'pool' dimension and then uses T.max.
        """
        self.pool_size = pool_size
        self.feature_dim = feature_dim
        self.implementation = implementation
        self.input_layer = input_layer
        self.input_shape = self.input_layer.get_output_shape()
        self.mb_size = self.input_layer.mb_size

        if self.input_shape[self.feature_dim] % self.pool_size != 0:
            raise "Feature dimension is not a multiple of the pool size. Doesn't work!"

        self.params = []
        self.bias_params = []

    def get_output_shape(self):
        feature_dim_size = self.input_shape[self.feature_dim]
        out_feature_dim_size = feature_dim_size // self.pool_size
        output_shape = list(self.input_shape) # make a mutable copy
        output_shape[self.feature_dim] = out_feature_dim_size
        return tuple(output_shape)

    def output(self, *args, **kwargs):
        input = self.input_layer.output(*args, **kwargs)

        if self.implementation == 'max_pool':
            # max_pool_2d operates on the last 2 dimensions of the input. So shift the feature dim to be last.
            shuffle_order = range(0, self.feature_dim) + range(self.feature_dim + 1, input.ndim) + [self.feature_dim]
            unshuffle_order = range(0, self.feature_dim) + [input.ndim - 1] + range(self.feature_dim, input.ndim - 1)

            input_shuffled = input.dimshuffle(*shuffle_order)
            output_shuffled = max_pool_2d(input_shuffled, (1, self.pool_size))
            output = output_shuffled.dimshuffle(*unshuffle_order)

        elif self.implementation == 'reshape':
            out_feature_dim_size = self.get_output_shape()[self.feature_dim]
            pool_shape = self.input_shape[:self.feature_dim] + (out_feature_dim_size, self.pool_size) + self.input_shape[self.feature_dim + 1:]
            
            input_reshaped = input.reshape(pool_shape)
            output = T.max(input_reshaped, axis=self.feature_dim + 1)
        else:
            raise "Uknown implementation string '%s'" % self.implementation

        return output





def dump_params(l, **kwargs):
    """
    dump parameters from layer l and down into a file.
    The dump file has the same name as the script, with _paramdump.pkl appended.

    This dump can be used to recover after a crash.

    additional metadata (i.e. chunk number) can be passed as keyword arguments.
    """
    param_values = get_param_values(l)
    kwargs['param_values'] = param_values
    fn = os.path.basename(sys.argv[0]).replace(".py", "_paramdump.pkl")
    dir = os.path.dirname(sys.argv[0])
    path = os.path.join(dir, fn)

    with open(path, 'w') as f:
        pickle.dump(kwargs, f, pickle.HIGHEST_PROTOCOL)
########NEW FILE########
__FILENAME__ = load_data
import numpy as np 
from scipy import ndimage
import glob
import itertools
import threading
import time
import skimage.transform
import skimage.io
import skimage.filter
import gzip
import os
import Queue
import multiprocessing as mp


num_train = 61578 # 70948
num_test = 79975 # 79971


train_ids = np.load("data/train_ids.npy")
test_ids = np.load("data/test_ids.npy")



def load_images_from_jpg(subset="train", downsample_factor=None, normalise=True, from_ram=False):
    if from_ram:
        pattern = "/dev/shm/images_%s_rev1/*.jpg"
    else:
        pattern = "data/raw/images_%s_rev1/*.jpg"
    paths = glob.glob(pattern % subset)
    paths.sort() # alphabetic ordering is used everywhere.
    for path in paths:
        # img = ndimage.imread(path)
        img = skimage.io.imread(path)
        if normalise:
            img = img.astype('float32') / 255.0 # normalise and convert to float

        if downsample_factor is None:
            yield img
        else:
            yield img[::downsample_factor, ::downsample_factor]


load_images = load_images_from_jpg



### data loading, chunking ###

def images_gen(id_gen, *args, **kwargs):
    for img_id in id_gen:
        yield load_image(img_id, *args, **kwargs)


def load_image(img_id, subset='train', normalise=True, from_ram=False):
        if from_ram:
            path = "/dev/shm/images_%s_rev1/%d.jpg" % (subset, img_id)
        else:
            path = "data/raw/images_%s_rev1/%d.jpg" % (subset, img_id)
        # print "loading %s" % path # TODO DEBUG
        img = skimage.io.imread(path)
        if normalise:
            img = img.astype('float32') / 255.0 # normalise and convert to float
        return img


def cycle(l, shuffle=True): # l should be a NUMPY ARRAY of ids
    l2 = list(l) # l.copy() # make a copy to avoid changing the input
    while True:
        if shuffle:
            np.random.shuffle(l2)
        for i in l2:
            yield i


def chunks_gen(images_gen, shape=(100, 424, 424, 3)):
    """
    specify images_gen(cycle(list(train_ids))) as the ids_gen to loop through the training set indefinitely in random order.

    The shape parameter is (chunk_size, imsize1, imsize2, ...)
    So the size of the resulting images needs to be known in advance for efficiency reasons.
    """
    chunk = np.zeros(shape)
    size = shape[0]

    k = 0
    for image in images_gen: 
        chunk[k] = image
        k += 1

        if k >= size:
            yield chunk, size # return the chunk as well as its size (this is useful because the final chunk may be smaller)
            chunk = np.zeros(shape)
            k = 0

    # last bit of chunk
    if k > 0: # there is leftover data
        yield chunk, k # the chunk is a fullsize array, but only the first k entries are valid.



### threaded generator with a buffer ###

def _generation_thread(source_gen, buffer, buffer_lock, buffer_size=2, sleep_time=1):
    while True:
        # print "DEBUG: loader: acquiring lock"-
        with buffer_lock:
            # print "DEBUG: loader: lock acquired, checking if buffer is full"
            buffer_is_full = (len(buffer) >= buffer_size)
            # print "DEBUG: loader: buffer length is %d" % len(buffer)
            
        if buffer_is_full:
            # buffer is full, wait.
            # this if-clause has to be outside the with-clause, else the lock is held for no reason!
            # print "DEBUG: loader: buffer is full, waiting"
            
            #print "buffer is full, exiting (DEBUG)"
            #break
            time.sleep(sleep_time)
        else:
            try:
                data = source_gen.next()
            except StopIteration:
                break # no more data. STAHP.
            # print "DEBUG: loader: loading %s" % current_path
     
            # stuff the data in the buffer as soon as it is free
            # print "DEBUG: loader: acquiring lock"
            with buffer_lock:
                # print "DEBUG: loader: lock acquired, adding data to buffer"
                buffer.append(data)
                # print "DEBUG: loader: buffer length went from %d to %d" % (len(buffer) - 1, len(buffer))

            
    
    
def threaded_gen(source_gen, buffer_size=2, sleep_time=1):
    """
    Generator that runs a slow source generator in a separate thread.
    buffer_size: the maximal number of items to pre-generate (length of the buffer)
    """
    buffer_lock = threading.Lock()
    buffer = []
    
    thread = threading.Thread(target=_generation_thread, args=(source_gen, buffer, buffer_lock, buffer_size, sleep_time))
    thread.setDaemon(True)
    thread.start()
    
    while True:
        # print "DEBUG: generator: acquiring lock"
        with buffer_lock:
            # print "DEBUG: generator: lock acquired, checking if buffer is empty"
            buffer_is_empty = (len(buffer) == 0)
            # print "DEBUG: generator: buffer length is %d" % len(buffer)
            
        if buffer_is_empty:
            # there's nothing in the buffer, so wait a bit.
            # this if-clause has to be outside the with-clause, else the lock is held for no reason!
            # print "DEBUG: generator: buffer is empty, waiting"

            if not thread.isAlive():
                print "buffer is empty and loading thread is finished, exiting"
                break

            print "buffer is empty, waiting!"
            time.sleep(sleep_time)
        else:
            # print "DEBUG: generator: acquiring lock"
            with buffer_lock:
                # print "DEBUG: generator: lock acquired, removing data from buffer, yielding"
                data = buffer.pop(0)
                # print "DEBUG: generator: buffer length went from %d to %d" % (len(buffer) + 1, len(buffer))
            yield data


### perturbation and preprocessing ###
# use these with imap to apply them to a generator and return a generator

def im_rotate(img, angle):
    return skimage.transform.rotate(img, angle, mode='reflect')


def im_flip(img, flip_h, flip_v):
    if flip_h:
        img = img[::-1]
    if flip_v:
        img = img[:, ::-1]
    return img


# this old version uses ndimage, which is a bit unreliable (lots of artifacts)
def im_rotate_old(img, angle):
    # downsampling afterwards is recommended
    return ndimage.rotate(img, angle, axes=(0,1), mode='reflect', reshape=False)


def im_translate(img, shift_x, shift_y):
    ## this could probably be a lot easier... meh.
    # downsampling afterwards is recommended
    translate_img = np.zeros_like(img, dtype=img.dtype)

    if shift_x >= 0:
        slice_x_src = slice(None, img.shape[0] - shift_x, None)
        slice_x_tgt = slice(shift_x, None, None)
    else:
        slice_x_src = slice(- shift_x, None, None)
        slice_x_tgt = slice(None, img.shape[0] + shift_x, None)

    if shift_y >= 0:
        slice_y_src = slice(None, img.shape[1] - shift_y, None)
        slice_y_tgt = slice(shift_y, None, None)
    else:
        slice_y_src = slice(- shift_y, None, None)
        slice_y_tgt = slice(None, img.shape[1] + shift_y, None)

    translate_img[slice_x_tgt, slice_y_tgt] = img[slice_x_src, slice_y_src]

    return translate_img


def im_rescale(img, scale_factor):
    zoomed_img = np.zeros_like(img, dtype=img.dtype)
    zoomed = skimage.transform.rescale(img, scale_factor)

    if scale_factor >= 1.0:
        shift_x = (zoomed.shape[0] - img.shape[0]) // 2
        shift_y = (zoomed.shape[1] - img.shape[1]) // 2
        zoomed_img[:,:] = zoomed[shift_x:shift_x+img.shape[0], shift_y:shift_y+img.shape[1]]
    else:
        shift_x = (img.shape[0] - zoomed.shape[0]) // 2
        shift_y = (img.shape[1] - zoomed.shape[1]) // 2
        zoomed_img[shift_x:shift_x+zoomed.shape[0], shift_y:shift_y+zoomed.shape[1]] = zoomed

    return zoomed_img


# this old version uses ndimage zoom which is unreliable
def im_rescale_old(img, scale_factor):
    zoomed_img = np.zeros_like(img, dtype=img.dtype)

    if img.ndim == 2:
        z = (scale_factor, scale_factor)
    elif img.ndim == 3:
        z = (scale_factor, scale_factor, 1)
    # else fail
    zoomed = ndimage.zoom(img, z)

    if scale_factor >= 1.0:
        shift_x = (zoomed.shape[0] - img.shape[0]) // 2
        shift_y = (zoomed.shape[1] - img.shape[1]) // 2
        zoomed_img[:,:] = zoomed[shift_x:shift_x+img.shape[0], shift_y:shift_y+img.shape[1]]
    else:
        shift_x = (img.shape[0] - zoomed.shape[0]) // 2
        shift_y = (img.shape[1] - zoomed.shape[1]) // 2
        zoomed_img[shift_x:shift_x+zoomed.shape[0], shift_y:shift_y+zoomed.shape[1]] = zoomed

    return zoomed_img


def im_downsample(img, ds_factor):
    return img[::ds_factor, ::ds_factor]

def im_downsample_smooth(img, ds_factor):
    return skimage.transform.rescale(img, 1.0/ds_factor)
    # ndimage is unreliable, don't use it
    # channels = [ndimage.zoom(img[:,:, k], 1.0/ds_factor) for k in range(3)]
    # return np.dstack(channels)


def im_crop(img, ds_factor):
    size_x = img.shape[0]
    size_y = img.shape[1]

    cropped_size_x = img.shape[0] // ds_factor
    cropped_size_y = img.shape[1] // ds_factor

    shift_x = (size_x - cropped_size_x) // 2
    shift_y = (size_y - cropped_size_y) // 2

    return img[shift_x:shift_x+cropped_size_x, shift_y:shift_y+cropped_size_y]


def im_lcn(img, sigma_mean, sigma_std):
    """
    based on matlab code by Guanglei Xiong, see http://www.mathworks.com/matlabcentral/fileexchange/8303-local-normalization
    """
    means = ndimage.gaussian_filter(img, sigma_mean)
    img_centered = img - means
    stds = np.sqrt(ndimage.gaussian_filter(img_centered**2, sigma_std))
    return img_centered / stds



rgb2yuv = np.array([[0.299, 0.587, 0.114],
                    [-0.147, -0.289, 0.436],
                    [0.615, -0.515, -0.100]])

yuv2rgb = np.linalg.inv(rgb2yuv)



def im_rgb_to_yuv(img):
    return np.tensordot(img, rgb2yuv, [[2], [0]])

def im_yuv_to_rgb(img):
    return np.tensordot(img, yuv2rgb, [[2], [0]])


def im_lcn_color(img, sigma_mean, sigma_std, std_bias):
    img_yuv = im_rgb_to_yuv(img)
    img_luma = img_yuv[:, :, 0]
    img_luma_filtered = im_lcn_bias(img_luma, sigma_mean, sigma_std, std_bias)
    img_yuv[:, :, 0] = img_luma_filtered
    return im_yuv_to_rgb(img_yuv)


def im_norm_01(img): # this is just for visualisation
    return (img - img.min()) / (img.max() - img.min())


def im_lcn_bias(img, sigma_mean, sigma_std, std_bias):
    """
    LCN with an std bias to avoid noise amplification
    """
    means = ndimage.gaussian_filter(img, sigma_mean)
    img_centered = img - means
    stds = np.sqrt(ndimage.gaussian_filter(img_centered**2, sigma_std) + std_bias)
    return img_centered / stds


def im_luma(img):
    return np.tensordot(img, np.array([0.299, 0.587, 0.114], dtype='float32'), [[2], [0]])


def chunk_luma(chunk): # faster than doing it per image, probably
    return np.tensordot(chunk, np.array([0.299, 0.587, 0.114], dtype='float32'), [[3], [0]])


def im_normhist(img, num_bins=256): # from http://www.janeriksolem.net/2009/06/histogram-equalization-with-python-and.html
    # this function only makes sense for grayscale images.
    img_flat = img.flatten()
    imhist, bins = np.histogram(img_flat, num_bins, normed=True)
    cdf = imhist.cumsum() #cumulative distribution function
    cdf = 255 * cdf / cdf[-1] #normalize

    #use linear interpolation of cdf to find new pixel values
    im2 = np.interp(img_flat, bins[:-1], cdf)

    return im2.reshape(img.shape)



def chunk_lcn(chunk, sigma_mean, sigma_std, std_bias=0.0, rescale=1.0):
    """
    based on matlab code by Guanglei Xiong, see http://www.mathworks.com/matlabcentral/fileexchange/8303-local-normalization
    assuming chunk.shape == (num_examples, x, y, channels)

    'rescale' is an additional rescaling constant to get the variance of the result in the 'right' range.
    """
    means = np.zeros(chunk.shape, dtype=chunk.dtype)
    for k in xrange(len(chunk)):
        means[k] = skimage.filter.gaussian_filter(chunk[k], sigma_mean, multichannel=True)

    chunk = chunk - means # centering
    del means # keep memory usage in check

    variances = np.zeros(chunk.shape, dtype=chunk.dtype)
    chunk_squared = chunk**2
    for k in xrange(len(chunk)):
        variances[k] = skimage.filter.gaussian_filter(chunk_squared[k], sigma_std, multichannel=True)

    chunk = chunk / np.sqrt(variances + std_bias)

    return chunk / rescale

    # TODO: make this 100x faster lol. otherwise it's not usable.



def chunk_gcn(chunk, rescale=1.0):
    means = chunk.reshape(chunk.shape[0], chunk.shape[1] * chunk.shape[2], chunk.shape[3]).mean(1).reshape(chunk.shape[0], 1, 1, chunk.shape[3])
    chunk -= means

    stds = chunk.reshape(chunk.shape[0], chunk.shape[1] * chunk.shape[2], chunk.shape[3]).std(1).reshape(chunk.shape[0], 1, 1, chunk.shape[3])
    chunk /= stds

    return chunk





def array_chunker_gen(data_list, chunk_size, loop=True, truncate=True, shuffle=True):
    while True:
        if shuffle:
            rs = np.random.get_state()
            for data in data_list:
                np.random.set_state(rs)
                np.random.shuffle(data)

        if truncate:
            num_chunks = data_list[0].shape[0] // chunk_size # integer division, we only want whole chunks
        else:
            num_chunks = int(np.ceil(data_list[0].shape[0] / float(chunk_size)))

        for k in xrange(num_chunks):
            idx_range = slice(k * chunk_size, (k+1) * chunk_size, None)
            chunks = []
            for data in data_list:
                c = data[idx_range]
                current_size = c.shape[0]
                if current_size < chunk_size: # incomplete chunk, pad zeros
                    cs = list(c.shape)
                    cs[0] = chunk_size
                    c_full = np.zeros(tuple(cs), dtype=c.dtype)
                    c_full[:current_size] = c
                else:
                    c_full = c
                chunks.append(c_full)
            yield tuple(chunks), current_size

        if not loop:
            break



def load_gz(path): # load a .npy.gz file
    if path.endswith(".gz"):
        f = gzip.open(path, 'rb')
        return np.load(f)
    else:
        return np.load(path)


def save_gz(path, arr): # save a .npy.gz file
    tmp_path = os.path.join("/tmp", os.path.basename(path) + ".tmp.npy")
    # tmp_path = path + ".tmp.npy" # temp file needs to end in .npy, else np.load adds it!
    np.save(tmp_path, arr)
    os.system("gzip -c %s > %s" % (tmp_path, path))
    os.remove(tmp_path)



def numpy_loader_gen(paths_gen, shuffle=True):
    for paths in paths_gen:
        # print "loading " + str(paths)
        data_list = [load_gz(p) for p in paths]

        if shuffle:
            rs = np.random.get_state()
            for data in data_list:
                np.random.set_state(rs)
                np.random.shuffle(data)

        yield data_list, data_list[0].shape[0] # 'chunk' length needs to be the last entry


def augmented_data_gen(path_patterns):
    paths = [sorted(glob.glob(pattern)) for pattern in path_patterns]
    assorted_paths = zip(*paths)
    paths_gen = cycle(assorted_paths, shuffle=True)
    return numpy_loader_gen(paths_gen)


def post_augmented_data_gen(path_patterns):
    paths = [sorted(glob.glob(pattern)) for pattern in path_patterns]
    assorted_paths = zip(*paths)
    paths_gen = cycle(assorted_paths, shuffle=True)
    for data_list, chunk_length in numpy_loader_gen(paths_gen):
        # print "DEBUG: post augmenting..."
        start_time = time.time()
        data_list = post_augment_chunk(data_list)
        # print "DEBUG: post augmenting done. took %.4f seconds." % (time.time() - start_time)
        yield data_list, chunk_length


def post_augment_chunk(data_list):
    """
    perform fast augmentation that can be applied directly to the chunks in realtime.
    """
    chunk_size = data_list[0].shape[0]

    rotations = np.random.randint(0, 4, chunk_size)
    flip_h = np.random.randint(0, 2, chunk_size).astype('bool')
    flip_v = np.random.randint(0, 2, chunk_size).astype('bool')

    for x in data_list:
        if x.ndim <= 3:
            continue # don't apply the transformations to anything that isn't an image

        for k in xrange(chunk_size):
            x_k = np.rot90(x[k], k=rotations[k])

            if flip_h[k]:
                x_k = x_k[::-1]

            if flip_v[k]:
                x_k = x_k[:, ::-1]

            x[k] = x_k

    return data_list



### better threaded/buffered generator using the Queue class ###

### threaded generator with a buffer ###

def buffered_gen(source_gen, buffer_size=2, sleep_time=1):
    """
    Generator that runs a slow source generator in a separate thread.
    buffer_size: the maximal number of items to pre-generate (length of the buffer)
    """
    buffer = Queue.Queue(maxsize=buffer_size)

    def _buffered_generation_thread(source_gen, buffer):
        while True:
            # we block here when the buffer is full. There's no point in generating more data
            # when the buffer is full, it only causes extra memory usage and effectively
            # increases the buffer size by one.
            while buffer.full():
                print "DEBUG: buffer is full, waiting to generate more data."
                time.sleep(sleep_time)

            try:
                data = source_gen.next()
            except StopIteration:
                break

            buffer.put(data)
    
    thread = threading.Thread(target=_buffered_generation_thread, args=(source_gen, buffer))
    thread.setDaemon(True)
    thread.start()
    
    while True:
        yield buffer.get()
        buffer.task_done()


### better version using multiprocessing, because the threading module acts weird,
# the background thread seems to slow down significantly. When the main thread is
# busy, i.e. computation time is not divided fairly.

def buffered_gen_mp(source_gen, buffer_size=2, sleep_time=1):
    """
    Generator that runs a slow source generator in a separate process.
    buffer_size: the maximal number of items to pre-generate (length of the buffer)
    """
    buffer = mp.Queue(maxsize=buffer_size)

    def _buffered_generation_process(source_gen, buffer):
        while True:
            # we block here when the buffer is full. There's no point in generating more data
            # when the buffer is full, it only causes extra memory usage and effectively
            # increases the buffer size by one.
            while buffer.full():
                # print "DEBUG: buffer is full, waiting to generate more data."
                time.sleep(sleep_time)

            try:
                data = source_gen.next()
            except StopIteration:
                # print "DEBUG: OUT OF DATA, CLOSING BUFFER"
                buffer.close() # signal that we're done putting data in the buffer
                break

            buffer.put(data)
    
    process = mp.Process(target=_buffered_generation_process, args=(source_gen, buffer))
    process.start()
    
    while True:
        try:
            # yield buffer.get()
            # just blocking on buffer.get() here creates a problem: when get() is called and the buffer
            # is empty, this blocks. Subsequently closing the buffer does NOT stop this block.
            # so the only solution is to periodically time out and try again. That way we'll pick up
            # on the 'close' signal.
            try:
                yield buffer.get(True, timeout=sleep_time)
            except Queue.Empty:
                if not process.is_alive():
                    break # no more data is going to come. This is a workaround because the buffer.close() signal does not seem to be reliable.

                # print "DEBUG: queue is empty, waiting..."
                pass # ignore this, just try again.

        except IOError: # if the buffer has been closed, calling get() on it will raise IOError.
            # this means that we're done iterating.
            # print "DEBUG: buffer closed, stopping."
            break




def hms(seconds):
    seconds = np.floor(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return "%02d:%02d:%02d" % (hours, minutes, seconds)

########NEW FILE########
__FILENAME__ = predict_augmented_npy_8433n_maxout2048
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=8, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=4, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

# l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_8433n_maxout2048_extradense
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_extradense.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=8, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=4, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_8433n_maxout2048_extradense_pysex
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_extradense_pysex.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=8, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=4, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_8433n_maxout2048_pysex
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_pysex.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=8, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=4, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

# l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_bigger
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_bigger.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=192, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

# l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
# l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_maxout2048
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

# l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_maxout2048_extradense
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_maxout2048_extradense_big256
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_big256.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=256, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_maxout2048_extradense_dup3
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_dup3.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_maxout2048_extradense_pysex
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysex.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_maxout2048_extradense_pysexgen1_dup
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysexgen1_dup.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_maxout2048_extradense_pysexgen1_dup2
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysexgen1_dup2.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_maxout2048_pysex
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_pysex.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

# l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_normconstraint
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_normconstraint.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_pysex
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_pysex.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

# l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
# l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms, processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_shareddense
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_shareddense.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)
l3f = layers.FlattenLayer(l3s)

l4a = layers.DenseLayer(l3f, n_outputs=512, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

j4 = layers.MultiRotMergeLayer(l4, num_views=4) # 2) # merge convolutional parts

l5a = layers.DenseLayer(j4, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l5 = layers.FeatureMaxPoolingLayer(l5a, pool_size=2, feature_dim=1, implementation='reshape')

l6a = layers.DenseLayer(l5, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l6a) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = predict_augmented_npy_shareddense512
"""
Load an analysis file and redo the predictions on the validation set / test set,
this time with augmented data and averaging. Store them as numpy files.
"""

import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle


BATCH_SIZE = 32 # 16
NUM_INPUT_FEATURES = 3

CHUNK_SIZE = 8000 # 10000 # this should be a multiple of the batch size

# ANALYSIS_PATH = "analysis/try_convnet_cc_multirot_3x69r45_untied_bias.pkl"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_shareddense512.pkl"

DO_VALID = True # disable this to not bother with the validation set evaluation
DO_TEST = True # disable this to not generate predictions on the testset



target_filename = os.path.basename(ANALYSIS_PATH).replace(".pkl", ".npy.gz")
target_path_valid = os.path.join("predictions/final/augmented/valid", target_filename)
target_path_test = os.path.join("predictions/final/augmented/test", target_filename)


print "Loading model data etc."
analysis = np.load(ANALYSIS_PATH)

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)]

num_input_representations = len(ds_transforms)

# split training data into training + a small validation set
num_train = load_data.num_train
num_valid = num_train // 10 # integer division
num_train -= num_valid
num_test = load_data.num_test

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]
test_ids = load_data.test_ids

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train+num_valid)
test_indices = np.arange(num_test)

y_valid = np.load("data/solutions_train.npy")[num_train:]


print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)
l3f = layers.FlattenLayer(l3s)

l4a = layers.DenseLayer(l3f, n_outputs=1024, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

j4 = layers.MultiRotMergeLayer(l4, num_views=4) # 2) # merge convolutional parts

l5a = layers.DenseLayer(j4, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l5 = layers.FeatureMaxPoolingLayer(l5a, pool_size=2, feature_dim=1, implementation='reshape')

l6a = layers.DenseLayer(l5, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l6a) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)



xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens)


print "Load model parameters"
layers.set_param_values(l6, analysis['param_values'])

print "Create generators"
# set here which transforms to use to make predictions
augmentation_transforms = []
for zoom in [1 / 1.2, 1.0, 1.2]:
    for angle in np.linspace(0, 360, 10, endpoint=False):
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=angle, zoom=zoom))
        augmentation_transforms.append(ra.build_augmentation_transform(rotation=(angle + 180), zoom=zoom, shear=180)) # flipped

print "  %d augmentation transforms." % len(augmentation_transforms)


augmented_data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
valid_gen = load_data.buffered_gen_mp(augmented_data_gen_valid, buffer_size=1)


augmented_data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test', augmentation_transforms=augmentation_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes, ds_transforms=ds_transforms)
test_gen = load_data.buffered_gen_mp(augmented_data_gen_test, buffer_size=1)


approx_num_chunks_valid = int(np.ceil(num_valid * len(augmentation_transforms) / float(CHUNK_SIZE)))
approx_num_chunks_test = int(np.ceil(num_test * len(augmentation_transforms) / float(CHUNK_SIZE)))

print "Approximately %d chunks for the validation set" % approx_num_chunks_valid
print "Approximately %d chunks for the test set" % approx_num_chunks_test


if DO_VALID:
    print
    print "VALIDATION SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(valid_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)


    all_predictions = np.vstack(predictions_list)

    print "Write predictions to %s" % target_path_valid
    load_data.save_gz(target_path_valid, all_predictions)

    print "Evaluate"
    rmse_valid = analysis['losses_valid'][-1]
    rmse_augmented = np.sqrt(np.mean((y_valid - all_predictions)**2))
    print "  MSE (last iteration):\t%.6f" % rmse_valid
    print "  MSE (augmented):\t%.6f" % rmse_augmented



if DO_TEST:
    print
    print "TEST SET"
    print "Compute predictions"
    predictions_list = []
    start_time = time.time()

    for e, (chunk_data, chunk_length) in enumerate(test_gen):
        print "Chunk %d" % (e + 1)
        xs_chunk = chunk_data

        # need to transpose the chunks to move the 'channels' dimension up
        xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

        print "  load data onto GPU"
        for x_shared, x_chunk in zip(xs_shared, xs_chunk):
            x_shared.set_value(x_chunk)
        num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))

        # make predictions, don't forget to cute off the zeros at the end
        predictions_chunk_list = []
        for b in xrange(num_batches_chunk):
            if b % 1000 == 0:
                print "  batch %d/%d" % (b + 1, num_batches_chunk)

            predictions = compute_output(b)
            predictions_chunk_list.append(predictions)

        predictions_chunk = np.vstack(predictions_chunk_list)
        predictions_chunk = predictions_chunk[:chunk_length] # cut off zeros / padding

        print "  compute average over transforms"
        predictions_chunk_avg = predictions_chunk.reshape(-1, len(augmentation_transforms), 37).mean(1)

        predictions_list.append(predictions_chunk_avg)

        time_since_start = time.time() - start_time
        print "  %s since start" % load_data.hms(time_since_start)

    all_predictions = np.vstack(predictions_list)


    print "Write predictions to %s" % target_path_test
    load_data.save_gz(target_path_test, all_predictions)

    print "Done!"

########NEW FILE########
__FILENAME__ = realtime_augmentation
"""
Generator that augments data in realtime
"""

import numpy as np
import skimage
import multiprocessing as mp
import time

import load_data


NUM_PROCESSES = 6
CHUNK_SIZE = 25000


IMAGE_WIDTH = 424
IMAGE_HEIGHT = 424
IMAGE_NUM_CHANNELS = 3


y_train = np.load("data/solutions_train.npy")

# split training data into training + a small validation set
num_train = y_train.shape[0]

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = load_data.train_ids[num_train:]
train_ids = load_data.train_ids[:num_train]



## UTILITIES ##

def select_indices(num, num_selected):
    selected_indices = np.arange(num)
    np.random.shuffle(selected_indices)
    selected_indices = selected_indices[:num_selected]
    return selected_indices


def fast_warp(img, tf, output_shape=(53,53), mode='reflect'):
    """
    This wrapper function is about five times faster than skimage.transform.warp, for our use case.
    """
    m = tf._matrix
    img_wf = np.empty((output_shape[0], output_shape[1], 3), dtype='float32')
    for k in xrange(3):
        img_wf[..., k] = skimage.transform._warps_cy._warp_fast(img[..., k], m, output_shape=output_shape, mode=mode)
    return img_wf




## TRANSFORMATIONS ##

center_shift = np.array((IMAGE_HEIGHT, IMAGE_WIDTH)) / 2. - 0.5
tform_center = skimage.transform.SimilarityTransform(translation=-center_shift)
tform_uncenter = skimage.transform.SimilarityTransform(translation=center_shift)

def build_augmentation_transform(zoom=1.0, rotation=0, shear=0, translation=(0, 0)):
    tform_augment = skimage.transform.AffineTransform(scale=(1/zoom, 1/zoom), rotation=np.deg2rad(rotation), shear=np.deg2rad(shear), translation=translation)
    tform = tform_center + tform_augment + tform_uncenter # shift to center, augment, shift back (for the rotation/shearing)
    return tform

def build_ds_transform_old(ds_factor=1.0, target_size=(53, 53)):
    tform_ds = skimage.transform.SimilarityTransform(scale=ds_factor)
    shift_x = IMAGE_WIDTH / (2.0 * ds_factor) - target_size[0] / 2.0
    shift_y = IMAGE_HEIGHT / (2.0 * ds_factor) - target_size[1] / 2.0
    tform_shift_ds = skimage.transform.SimilarityTransform(translation=(shift_x, shift_y))
    return tform_shift_ds + tform_ds


def build_ds_transform(ds_factor=1.0, orig_size=(424, 424), target_size=(53, 53), do_shift=True, subpixel_shift=False):
    """
    This version is a bit more 'correct', it mimics the skimage.transform.resize function.
    """
    rows, cols = orig_size
    trows, tcols = target_size
    col_scale = row_scale = ds_factor
    src_corners = np.array([[1, 1], [1, rows], [cols, rows]]) - 1
    dst_corners = np.zeros(src_corners.shape, dtype=np.double)
    # take into account that 0th pixel is at position (0.5, 0.5)
    dst_corners[:, 0] = col_scale * (src_corners[:, 0] + 0.5) - 0.5
    dst_corners[:, 1] = row_scale * (src_corners[:, 1] + 0.5) - 0.5

    tform_ds = skimage.transform.AffineTransform()
    tform_ds.estimate(src_corners, dst_corners)

    if do_shift:
        if subpixel_shift: 
            # if this is true, we add an additional 'arbitrary' subpixel shift, which 'aligns'
            # the grid of the target image with the original image in such a way that the interpolation
            # is 'cleaner', i.e. groups of <ds_factor> pixels in the original image will map to
            # individual pixels in the resulting image.
            #
            # without this additional shift, and when the downsampling factor does not divide the image
            # size (like in the case of 424 and 3.0 for example), the grids will not be aligned, resulting
            # in 'smoother' looking images that lose more high frequency information.
            #
            # technically this additional shift is not 'correct' (we're not looking at the very center
            # of the image anymore), but it's always less than a pixel so it's not a big deal.
            #
            # in practice, we implement the subpixel shift by rounding down the orig_size to the
            # nearest multiple of the ds_factor. Of course, this only makes sense if the ds_factor
            # is an integer.

            cols = (cols // int(ds_factor)) * int(ds_factor)
            rows = (rows // int(ds_factor)) * int(ds_factor)
            # print "NEW ROWS, COLS: (%d,%d)" % (rows, cols)


        shift_x = cols / (2 * ds_factor) - tcols / 2.0
        shift_y = rows / (2 * ds_factor) - trows / 2.0
        tform_shift_ds = skimage.transform.SimilarityTransform(translation=(shift_x, shift_y))
        return tform_shift_ds + tform_ds
    else:
        return tform_ds



def random_perturbation_transform(zoom_range, rotation_range, shear_range, translation_range, do_flip=False):
    # random shift [-4, 4] - shift no longer needs to be integer!
    shift_x = np.random.uniform(*translation_range)
    shift_y = np.random.uniform(*translation_range)
    translation = (shift_x, shift_y)

    # random rotation [0, 360]
    rotation = np.random.uniform(*rotation_range) # there is no post-augmentation, so full rotations here!

    # random shear [0, 5]
    shear = np.random.uniform(*shear_range)

    # # flip
    if do_flip and (np.random.randint(2) > 0): # flip half of the time
        shear += 180
        rotation += 180
        # shear by 180 degrees is equivalent to rotation by 180 degrees + flip.
        # So after that we rotate it another 180 degrees to get just the flip.

    # random zoom [0.9, 1.1]
    # zoom = np.random.uniform(*zoom_range)
    log_zoom_range = [np.log(z) for z in zoom_range]
    zoom = np.exp(np.random.uniform(*log_zoom_range)) # for a zoom factor this sampling approach makes more sense.
    # the range should be multiplicatively symmetric, so [1/1.1, 1.1] instead of [0.9, 1.1] makes more sense.

    return build_augmentation_transform(zoom, rotation, shear, translation)


def perturb_and_dscrop(img, ds_transforms, augmentation_params, target_sizes=None):
    if target_sizes is None: # default to (53,53) for backwards compatibility
        target_sizes = [(53, 53) for _ in xrange(len(ds_transforms))]

    tform_augment = random_perturbation_transform(**augmentation_params)
    # return [skimage.transform.warp(img, tform_ds + tform_augment, output_shape=target_size, mode='reflect').astype('float32') for tform_ds in ds_transforms]

    result = []
    for tform_ds, target_size in zip(ds_transforms, target_sizes):
        result.append(fast_warp(img, tform_ds + tform_augment, output_shape=target_size, mode='reflect').astype('float32'))

    return result




tform_ds_8x = build_ds_transform(8.0, target_size=(53, 53))
tform_ds_cropped33 = build_ds_transform(3.0, target_size=(53, 53))
tform_ds_cc = build_ds_transform(1.0, target_size=(53, 53))

tform_identity = skimage.transform.AffineTransform() # this is an identity transform by default


ds_transforms_default = [tform_ds_cropped33, tform_ds_8x]
ds_transforms_381 = [tform_ds_cropped33, tform_ds_8x, tform_ds_cc]

ds_transforms = ds_transforms_default # CHANGE THIS LINE to select downsampling transforms to be used

## REALTIME AUGMENTATION GENERATOR ##

def load_and_process_image(img_index, ds_transforms, augmentation_params, target_sizes=None):
    # start_time = time.time()
    img_id = load_data.train_ids[img_index]
    img = load_data.load_image(img_id, from_ram=True)
    # load_time = (time.time() - start_time) * 1000
    # start_time = time.time()
    img_a = perturb_and_dscrop(img, ds_transforms, augmentation_params, target_sizes)
    # augment_time = (time.time() - start_time) * 1000
    # print "load: %.2f ms\taugment: %.2f ms" % (load_time, augment_time)
    return img_a


class LoadAndProcess(object):
    """
    UGLY HACK:

    pool.imap does not allow for extra arguments to be passed to the called function.
    This is a problem because we want to pass in the augmentation parameters.
    As a workaround, we could use a lambda or a locally defined function, but that
    doesn't work, because it cannot be pickled properly.

    The solution is to use a callable object instead, which is picklable.
    """
    def __init__(self, ds_transforms, augmentation_params, target_sizes=None):
        self.ds_transforms = ds_transforms
        self.augmentation_params = augmentation_params
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image(img_index, self.ds_transforms, self.augmentation_params, self.target_sizes)


default_augmentation_params = {
    'zoom_range': (1.0, 1.1),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
}


def realtime_augmented_data_gen(num_chunks=None, chunk_size=CHUNK_SIZE, augmentation_params=default_augmentation_params,
                                ds_transforms=ds_transforms_default, target_sizes=None, processor_class=LoadAndProcess):
    """
    new version, using Pool.imap instead of Pool.map, to avoid the data structure conversion
    from lists to numpy arrays afterwards.
    """
    if target_sizes is None: # default to (53,53) for backwards compatibility
        target_sizes = [(53, 53) for _ in xrange(len(ds_transforms))]

    n = 0 # number of chunks yielded so far
    while True:
        if num_chunks is not None and n >= num_chunks:
            # print "DEBUG: DATA GENERATION COMPLETED"
            break

        # start_time = time.time()
        selected_indices = select_indices(num_train, chunk_size)
        labels = y_train[selected_indices]

        process_func = processor_class(ds_transforms, augmentation_params, target_sizes)

        target_arrays = [np.empty((chunk_size, size_x, size_y, 3), dtype='float32') for size_x, size_y in target_sizes]
        pool = mp.Pool(NUM_PROCESSES)
        gen = pool.imap(process_func, selected_indices, chunksize=100) # lower chunksize seems to help to keep memory usage in check

        for k, imgs in enumerate(gen):
            # print ">>> converting data: %d" % k
            for i, img in enumerate(imgs):
                target_arrays[i][k] = img

        pool.close()
        pool.join()

        # TODO: optionally do post-augmentation here

        target_arrays.append(labels)

        # duration = time.time() - start_time
        # print "chunk generation took %.2f seconds" % duration

        yield target_arrays, chunk_size

        n += 1





### Fixed test-time augmentation ####


def augment_fixed_and_dscrop(img, ds_transforms, augmentation_transforms, target_sizes=None):
    if target_sizes is None: # default to (53,53) for backwards compatibility
        target_sizes = [(53, 53) for _ in xrange(len(ds_transforms))]

    augmentations_list = []
    for tform_augment in augmentation_transforms:
        augmentation = [fast_warp(img, tform_ds + tform_augment, output_shape=target_size, mode='reflect').astype('float32') for tform_ds, target_size in zip(ds_transforms, target_sizes)]
        augmentations_list.append(augmentation)

    return augmentations_list


def load_and_process_image_fixed(img_index, subset, ds_transforms, augmentation_transforms, target_sizes=None):
    if subset == 'train':
        img_id = load_data.train_ids[img_index]
    elif subset == 'test':
        img_id = load_data.test_ids[img_index]

    img = load_data.load_image(img_id, from_ram=True, subset=subset)
    img_a = augment_fixed_and_dscrop(img, ds_transforms, augmentation_transforms, target_sizes)
    return img_a


class LoadAndProcessFixed(object):
    """
    Same ugly hack as before
    """
    def __init__(self, subset, ds_transforms, augmentation_transforms, target_sizes=None):
        self.subset = subset
        self.ds_transforms = ds_transforms
        self.augmentation_transforms = augmentation_transforms
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image_fixed(img_index, self.subset, self.ds_transforms, self.augmentation_transforms, self.target_sizes)




def realtime_fixed_augmented_data_gen(selected_indices, subset, ds_transforms=ds_transforms_default, augmentation_transforms=[tform_identity],
                                        chunk_size=CHUNK_SIZE, target_sizes=None, processor_class=LoadAndProcessFixed):
    """
    by default, only the identity transform is in the augmentation list, so no augmentation occurs (only ds_transforms are applied).
    """
    num_ids_per_chunk = (chunk_size // len(augmentation_transforms)) # number of datapoints per chunk - each datapoint is multiple entries!
    num_chunks = int(np.ceil(len(selected_indices) / float(num_ids_per_chunk)))

    if target_sizes is None: # default to (53,53) for backwards compatibility
        target_sizes = [(53, 53) for _ in xrange(len(ds_transforms))]

    process_func = processor_class(subset, ds_transforms, augmentation_transforms, target_sizes)

    for n in xrange(num_chunks):
        indices_n = selected_indices[n * num_ids_per_chunk:(n+1) * num_ids_per_chunk]
        current_chunk_size = len(indices_n) * len(augmentation_transforms) # last chunk will be shorter!

        target_arrays = [np.empty((chunk_size, size_x, size_y, 3), dtype='float32') for size_x, size_y in target_sizes]

        pool = mp.Pool(NUM_PROCESSES)
        gen = pool.imap(process_func, indices_n, chunksize=100) # lower chunksize seems to help to keep memory usage in check

        for k, imgs_aug in enumerate(gen):
            for j, imgs in enumerate(imgs_aug):
                for i, img in enumerate(imgs):
                    idx = k * len(augmentation_transforms) + j # put all augmented versions of the same datapoint after each other
                    target_arrays[i][idx] = img

        pool.close()
        pool.join()

        yield target_arrays, current_chunk_size


def post_augment_chunks(chunk_list, gamma_range=(1.0, 1.0)):
    """
    post augmentation MODIFIES THE CHUNKS IN CHUNK_LIST IN PLACE to save memory where possible!

    post_augmentation_params:
        - gamma_range: range of the gamma correction exponents
    """
    chunk_size = chunk_list[0].shape[0]

    if gamma_range != (1.0, 1.0):
        gamma_min, gamma_max = gamma_range
        lgamma_min = np.log(gamma_min)
        lgamma_max = np.log(gamma_max)
        gammas = np.exp(np.random.uniform(lgamma_min, lgamma_max, (chunk_size,)))
        gammas = gammas.astype('float32').reshape(-1, 1, 1, 1)

        for i in xrange(len(chunk_list)):
            chunk_list[i] **= gammas



def post_augment_gen(data_gen, post_augmentation_params):
    for target_arrays, chunk_size in data_gen:
        # start_time = time.time()
        post_augment_chunks(target_arrays[:-1], **post_augmentation_params)
        # print "post augmentation took %.4f seconds" % (time.time() - start_time)
        # target_arrays[:-1], don't augment the labels!
        yield target_arrays, chunk_size



colour_channel_weights = np.array([-0.0148366, -0.01253134, -0.01040762], dtype='float32')


def post_augment_brightness_gen(data_gen, std=0.5):
    for target_arrays, chunk_size in data_gen:
        labels = target_arrays.pop()
        
        stds = np.random.randn(chunk_size).astype('float32') * std
        noise = stds[:, None] * colour_channel_weights[None, :]

        target_arrays = [np.clip(t + noise[:, None, None, :], 0, 1) for t in target_arrays]
        target_arrays.append(labels)

        yield target_arrays, chunk_size



def post_augment_gaussian_noise_gen(data_gen, std=0.1):
    """
    Adds gaussian noise. Note that this is not entirely correct, the correct way would be to do it
    before downsampling, so the regular image and the rot45 image have the same noise pattern.
    But this is easier.
    """
    for target_arrays, chunk_size in data_gen:
        labels = target_arrays.pop()
        
        noise = np.random.randn(*target_arrays[0].shape).astype('float32') * std

        target_arrays = [np.clip(t + noise, 0, 1) for t in target_arrays]
        target_arrays.append(labels)

        yield target_arrays, chunk_size


def post_augment_gaussian_noise_gen_separate(data_gen, std=0.1):
    """
    Adds gaussian noise. Note that this is not entirely correct, the correct way would be to do it
    before downsampling, so the regular image and the rot45 image have the same noise pattern.
    But this is easier.

    This one generates separate noise for the different channels but is a lot slower
    """
    for target_arrays, chunk_size in data_gen:
        labels = target_arrays.pop()

        new_target_arrays = []

        for target_array in target_arrays:
            noise = np.random.randn(*target_array.shape).astype('float32') * std
            new_target_arrays.append(np.clip(target_array + noise, 0, 1))

        new_target_arrays.append(labels)

        yield new_target_arrays, chunk_size


### Alternative image loader and processor which does pysex centering

# pysex_params_train = load_data.load_gz("data/pysex_params_extra_train.npy.gz")
# pysex_params_test = load_data.load_gz("data/pysex_params_extra_test.npy.gz")


pysex_params_train = load_data.load_gz("data/pysex_params_gen2_train.npy.gz")
pysex_params_test = load_data.load_gz("data/pysex_params_gen2_test.npy.gz")

pysexgen1_params_train = load_data.load_gz("data/pysex_params_extra_train.npy.gz")
pysexgen1_params_test = load_data.load_gz("data/pysex_params_extra_test.npy.gz")


center_x, center_y = (IMAGE_WIDTH - 1) / 2.0, (IMAGE_HEIGHT - 1) / 2.0

# def build_pysex_center_transform(img_index, subset='train'):
#     if subset == 'train':
#         x, y, a, b, theta, flux_radius, kron_radius, petro_radius, fwhm = pysex_params_train[img_index]
#     elif subset == 'test':
#         x, y, a, b, theta, flux_radius, kron_radius, petro_radius, fwhm = pysex_params_test[img_index]

#     return build_augmentation_transform(translation=(x - center_x, y - center_y))  


# def build_pysex_center_rescale_transform(img_index, subset='train', target_radius=170.0): # target_radius=160.0):
#     if subset == 'train':
#         x, y, a, b, theta, flux_radius, kron_radius, petro_radius, fwhm = pysex_params_train[img_index]
#     elif subset == 'test':
#         x, y, a, b, theta, flux_radius, kron_radius, petro_radius, fwhm = pysex_params_test[img_index]
    
#     scale_factor_limit = 1.5 # scale up / down by this fraction at most

#     scale_factor = target_radius / (petro_radius * a) # magic constant, might need some tuning

#     if np.isnan(scale_factor):
#         scale_factor = 1.0 # no info
    
#     scale_factor = max(min(scale_factor, scale_factor_limit), 1.0 / scale_factor_limit) # truncate for edge cases

#     return build_augmentation_transform(translation=(x - center_x, y - center_y), zoom=scale_factor)  


def build_pysex_center_transform(img_index, subset='train'):
    if subset == 'train':
        x, y, a, b, theta, petro_radius = pysex_params_train[img_index]
    elif subset == 'test':
        x, y, a, b, theta, petro_radius = pysex_params_test[img_index]

    return build_augmentation_transform(translation=(x - center_x, y - center_y))  


def build_pysex_center_rescale_transform(img_index, subset='train', target_radius=160.0):
    if subset == 'train':
        x, y, a, b, theta, petro_radius = pysex_params_train[img_index]
    elif subset == 'test':
        x, y, a, b, theta, petro_radius = pysex_params_test[img_index]
    
    scale_factor_limit = 1.5 # scale up / down by this fraction at most

    scale_factor = target_radius / (petro_radius * a) # magic constant, might need some tuning

    if np.isnan(scale_factor):
        scale_factor = 1.0 # no info
    
    scale_factor = max(min(scale_factor, scale_factor_limit), 1.0 / scale_factor_limit) # truncate for edge cases

    return build_augmentation_transform(translation=(x - center_x, y - center_y), zoom=scale_factor)  



def build_pysexgen1_center_rescale_transform(img_index, subset='train', target_radius=160.0):
    if subset == 'train':
        x, y, a, b, theta, flux_radius, kron_radius, petro_radius, fwhm = pysexgen1_params_train[img_index]
    elif subset == 'test':
        x, y, a, b, theta, flux_radius, kron_radius, petro_radius, fwhm = pysexgen1_params_test[img_index]
    
    scale_factor_limit = 1.5 # scale up / down by this fraction at most

    scale_factor = target_radius / (petro_radius * a) # magic constant, might need some tuning

    if np.isnan(scale_factor):
        scale_factor = 1.0 # no info
    
    scale_factor = max(min(scale_factor, scale_factor_limit), 1.0 / scale_factor_limit) # truncate for edge cases

    return build_augmentation_transform(translation=(x - center_x, y - center_y), zoom=scale_factor)  




def perturb_and_dscrop_with_prepro(img, ds_transforms, augmentation_params, target_sizes=None, prepro_transform=tform_identity):
    """
    This version supports a preprocessing transform which is applied before anything else
    """
    if target_sizes is None: # default to (53,53) for backwards compatibility
        target_sizes = [(53, 53) for _ in xrange(len(ds_transforms))]

    tform_augment = random_perturbation_transform(**augmentation_params)
    # return [skimage.transform.warp(img, tform_ds + tform_augment, output_shape=target_size, mode='reflect').astype('float32') for tform_ds in ds_transforms]

    result = []
    for tform_ds, target_size in zip(ds_transforms, target_sizes):
        result.append(fast_warp(img, tform_ds + tform_augment + prepro_transform, output_shape=target_size, mode='reflect').astype('float32'))

    return result


def load_and_process_image_pysex_centering(img_index, ds_transforms, augmentation_params, target_sizes=None):
    # start_time = time.time()
    img_id = load_data.train_ids[img_index]
    img = load_data.load_image(img_id, from_ram=True)
    # load_time = (time.time() - start_time) * 1000
    # start_time = time.time()
    tf_center = build_pysex_center_transform(img_index)

    img_a = perturb_and_dscrop_with_prepro(img, ds_transforms, augmentation_params, target_sizes, prepro_transform=tf_center)
    # augment_time = (time.time() - start_time) * 1000
    # print "load: %.2f ms\taugment: %.2f ms" % (load_time, augment_time)
    return img_a


class LoadAndProcessPysexCentering(object):
    def __init__(self, ds_transforms, augmentation_params, target_sizes=None):
        self.ds_transforms = ds_transforms
        self.augmentation_params = augmentation_params
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image_pysex_centering(img_index, self.ds_transforms, self.augmentation_params, self.target_sizes)


def load_and_process_image_pysex_centering_rescaling(img_index, ds_transforms, augmentation_params, target_sizes=None):
    # start_time = time.time()
    img_id = load_data.train_ids[img_index]
    img = load_data.load_image(img_id, from_ram=True)
    # load_time = (time.time() - start_time) * 1000
    # start_time = time.time()
    tf_center_rescale = build_pysex_center_rescale_transform(img_index)

    img_a = perturb_and_dscrop_with_prepro(img, ds_transforms, augmentation_params, target_sizes, prepro_transform=tf_center_rescale)
    # augment_time = (time.time() - start_time) * 1000
    # print "load: %.2f ms\taugment: %.2f ms" % (load_time, augment_time)
    return img_a


class LoadAndProcessPysexCenteringRescaling(object):
    def __init__(self, ds_transforms, augmentation_params, target_sizes=None):
        self.ds_transforms = ds_transforms
        self.augmentation_params = augmentation_params
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image_pysex_centering_rescaling(img_index, self.ds_transforms, self.augmentation_params, self.target_sizes)


def load_and_process_image_pysexgen1_centering_rescaling(img_index, ds_transforms, augmentation_params, target_sizes=None):
    # start_time = time.time()
    img_id = load_data.train_ids[img_index]
    img = load_data.load_image(img_id, from_ram=True)
    # load_time = (time.time() - start_time) * 1000
    # start_time = time.time()
    tf_center_rescale = build_pysexgen1_center_rescale_transform(img_index)

    img_a = perturb_and_dscrop_with_prepro(img, ds_transforms, augmentation_params, target_sizes, prepro_transform=tf_center_rescale)
    # augment_time = (time.time() - start_time) * 1000
    # print "load: %.2f ms\taugment: %.2f ms" % (load_time, augment_time)
    return img_a


class LoadAndProcessPysexGen1CenteringRescaling(object):
    def __init__(self, ds_transforms, augmentation_params, target_sizes=None):
        self.ds_transforms = ds_transforms
        self.augmentation_params = augmentation_params
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image_pysexgen1_centering_rescaling(img_index, self.ds_transforms, self.augmentation_params, self.target_sizes)







def augment_fixed_and_dscrop_with_prepro(img, ds_transforms, augmentation_transforms, target_sizes=None, prepro_transform=tform_identity):
    if target_sizes is None: # default to (53,53) for backwards compatibility
        target_sizes = [(53, 53) for _ in xrange(len(ds_transforms))]

    augmentations_list = []
    for tform_augment in augmentation_transforms:
        augmentation = [fast_warp(img, tform_ds + tform_augment + prepro_transform, output_shape=target_size, mode='reflect').astype('float32') for tform_ds, target_size in zip(ds_transforms, target_sizes)]
        augmentations_list.append(augmentation)

    return augmentations_list


def load_and_process_image_fixed_pysex_centering(img_index, subset, ds_transforms, augmentation_transforms, target_sizes=None):
    if subset == 'train':
        img_id = load_data.train_ids[img_index]
    elif subset == 'test':
        img_id = load_data.test_ids[img_index]

    tf_center = build_pysex_center_transform(img_index, subset)
    
    img = load_data.load_image(img_id, from_ram=True, subset=subset)
    img_a = augment_fixed_and_dscrop_with_prepro(img, ds_transforms, augmentation_transforms, target_sizes, prepro_transform=tf_center)
    return img_a


class LoadAndProcessFixedPysexCentering(object):
    """
    Same ugly hack as before
    """
    def __init__(self, subset, ds_transforms, augmentation_transforms, target_sizes=None):
        self.subset = subset
        self.ds_transforms = ds_transforms
        self.augmentation_transforms = augmentation_transforms
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image_fixed_pysex_centering(img_index, self.subset, self.ds_transforms, self.augmentation_transforms, self.target_sizes)



def load_and_process_image_fixed_pysex_centering_rescaling(img_index, subset, ds_transforms, augmentation_transforms, target_sizes=None):
    if subset == 'train':
        img_id = load_data.train_ids[img_index]
    elif subset == 'test':
        img_id = load_data.test_ids[img_index]

    tf_center_rescale = build_pysex_center_rescale_transform(img_index, subset)
    
    img = load_data.load_image(img_id, from_ram=True, subset=subset)
    img_a = augment_fixed_and_dscrop_with_prepro(img, ds_transforms, augmentation_transforms, target_sizes, prepro_transform=tf_center_rescale)
    return img_a


class LoadAndProcessFixedPysexCenteringRescaling(object):
    """
    Same ugly hack as before
    """
    def __init__(self, subset, ds_transforms, augmentation_transforms, target_sizes=None):
        self.subset = subset
        self.ds_transforms = ds_transforms
        self.augmentation_transforms = augmentation_transforms
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image_fixed_pysex_centering_rescaling(img_index, self.subset, self.ds_transforms, self.augmentation_transforms, self.target_sizes)



def load_and_process_image_fixed_pysexgen1_centering_rescaling(img_index, subset, ds_transforms, augmentation_transforms, target_sizes=None):
    if subset == 'train':
        img_id = load_data.train_ids[img_index]
    elif subset == 'test':
        img_id = load_data.test_ids[img_index]

    tf_center_rescale = build_pysexgen1_center_rescale_transform(img_index, subset)
    
    img = load_data.load_image(img_id, from_ram=True, subset=subset)
    img_a = augment_fixed_and_dscrop_with_prepro(img, ds_transforms, augmentation_transforms, target_sizes, prepro_transform=tf_center_rescale)
    return img_a


class LoadAndProcessFixedPysexGen1CenteringRescaling(object):
    """
    Same ugly hack as before
    """
    def __init__(self, subset, ds_transforms, augmentation_transforms, target_sizes=None):
        self.subset = subset
        self.ds_transforms = ds_transforms
        self.augmentation_transforms = augmentation_transforms
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image_fixed_pysexgen1_centering_rescaling(img_index, self.subset, self.ds_transforms, self.augmentation_transforms, self.target_sizes)






### Processor classes for brightness normalisation ###

def load_and_process_image_brightness_norm(img_index, ds_transforms, augmentation_params, target_sizes=None):
    img_id = load_data.train_ids[img_index]
    img = load_data.load_image(img_id, from_ram=True)
    img = img / img.max() # normalise
    img_a = perturb_and_dscrop(img, ds_transforms, augmentation_params, target_sizes)
    return img_a


class LoadAndProcessBrightnessNorm(object):
    def __init__(self, ds_transforms, augmentation_params, target_sizes=None):
        self.ds_transforms = ds_transforms
        self.augmentation_params = augmentation_params
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image_brightness_norm(img_index, self.ds_transforms, self.augmentation_params, self.target_sizes)


def load_and_process_image_fixed_brightness_norm(img_index, subset, ds_transforms, augmentation_transforms, target_sizes=None):
    if subset == 'train':
        img_id = load_data.train_ids[img_index]
    elif subset == 'test':
        img_id = load_data.test_ids[img_index]

    img = load_data.load_image(img_id, from_ram=True, subset=subset)
    img = img / img.max() # normalise
    img_a = augment_fixed_and_dscrop(img, ds_transforms, augmentation_transforms, target_sizes)
    return img_a


class LoadAndProcessFixedBrightnessNorm(object):
    """
    Same ugly hack as before
    """
    def __init__(self, subset, ds_transforms, augmentation_transforms, target_sizes=None):
        self.subset = subset
        self.ds_transforms = ds_transforms
        self.augmentation_transforms = augmentation_transforms
        self.target_sizes = target_sizes

    def __call__(self, img_index):
        return load_and_process_image_fixed_brightness_norm(img_index, self.subset, self.ds_transforms, self.augmentation_transforms, self.target_sizes)





class CallableObj(object):
    """
    UGLY HACK:

    pool.imap does not allow for extra arguments to be passed to the called function.
    This is a problem because we want to pass in the augmentation parameters.
    As a workaround, we could use a lambda or a locally defined function, but that
    doesn't work, because it cannot be pickled properly.

    The solution is to use a callable object instead, which is picklable.
    """
    def __init__(self, func, *args, **kwargs):
        self.func = func # the function to call
        self.args = args # additional arguments
        self.kwargs = kwargs # additional keyword arguments

    def __call__(self, index):
        return self.func(index, *self.args, **self.kwargs)
        


########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=8, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=4, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

# l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_extradense
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_extradense.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_extradense.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=8, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=4, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_extradense_pysex
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_extradense_pysex.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_extradense_pysex.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes, processor_class=ra.LoadAndProcessPysexCenteringRescaling)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=8, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=4, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_pysex
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_pysex.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_8433n_maxout2048_pysex.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes, processor_class=ra.LoadAndProcessPysexCenteringRescaling)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=8, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=4, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

# l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_bigger
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_bigger.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_bigger.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=192, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

# l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
# l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_maxout2048
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_maxout2048.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

# l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_big256
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_big256.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_big256.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=256, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

        layers.dump_params(l6, e=e)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_dup3
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_dup3.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_dup3.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

        layers.dump_params(l6, e=e)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysex
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysex.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysex.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes, processor_class=ra.LoadAndProcessPysexCenteringRescaling)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

        layers.dump_params(l6, e=e)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysexgen1_dup
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysexgen1_dup.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysexgen1_dup.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes, processor_class=ra.LoadAndProcessPysexGen1CenteringRescaling)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

        layers.dump_params(l6, e=e)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysexgen1_dup2
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysexgen1_dup2.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_extradense_pysexgen1_dup2.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes, processor_class=ra.LoadAndProcessPysexGen1CenteringRescaling)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexGen1CenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

        layers.dump_params(l6, e=e)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_maxout2048_pysex
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_pysex.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_maxout2048_pysex.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes, processor_class=ra.LoadAndProcessPysexCenteringRescaling)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

# l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_normconstraint
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_normconstraint.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_normconstraint.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts


l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4b = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')
l4c = layers.DenseLayer(l4b, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4c, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


# norm constraint stuff
rescaling_updates = l4a.rescaling_updates(0.4) + l4c.rescaling_updates(0.23) # constants were determined by looking at histograms.
rescale_weights = theano.function([], [], updates=rescaling_updates) # updating only, not computing anything
rescale_every = 10 # rescale the weights only every N updates to save time


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)

        # weight rescaling (norm constraints)
        if (b + 1) % rescale_every == 0:
            rescale_weights()


    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_pysex
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_pysex.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_pysex.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes, processor_class=ra.LoadAndProcessPysexCenteringRescaling)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes,
        processor_class=ra.LoadAndProcessFixedPysexCenteringRescaling)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)

j3 = layers.MultiRotMergeLayer(l3s, num_views=4) # 2) # merge convolutional parts

l4 = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5)

# l4a = layers.DenseLayer(j3, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
# l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

# l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.0, dropout=0.5, nonlinearity=custom.clip_01) #  nonlinearity=layers.identity)
l5 = layers.DenseLayer(l4, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l5) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_shareddense
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_shareddense.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_shareddense.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)
l3f = layers.FlattenLayer(l3s)

l4a = layers.DenseLayer(l3f, n_outputs=512, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

j4 = layers.MultiRotMergeLayer(l4, num_views=4) # 2) # merge convolutional parts

l5a = layers.DenseLayer(j4, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l5 = layers.FeatureMaxPoolingLayer(l5a, pool_size=2, feature_dim=1, implementation='reshape')

l6a = layers.DenseLayer(l5, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l6a) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

        layers.dump_params(l6, e=e)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
__FILENAME__ = try_convnet_cc_multirotflip_3x69r45_shareddense512
import numpy as np
# import pandas as pd
import theano
import theano.tensor as T
import layers
import cc_layers
import custom
import load_data
import realtime_augmentation as ra
import time
import csv
import os
import cPickle as pickle
from datetime import datetime, timedelta

# import matplotlib.pyplot as plt 
# plt.ion()
# import utils

BATCH_SIZE = 16
NUM_INPUT_FEATURES = 3

LEARNING_RATE_SCHEDULE = {
    0: 0.04,
    1800: 0.004,
    2300: 0.0004,
}
MOMENTUM = 0.9
WEIGHT_DECAY = 0.0
CHUNK_SIZE = 10000 # 30000 # this should be a multiple of the batch size, ideally.
NUM_CHUNKS = 2500 # 3000 # 1500 # 600 # 600 # 600 # 500 
VALIDATE_EVERY = 20 # 12 # 6 # 6 # 6 # 5 # validate only every 5 chunks. MUST BE A DIVISOR OF NUM_CHUNKS!!!
# else computing the analysis data does not work correctly, since it assumes that the validation set is still loaded.

NUM_CHUNKS_NONORM = 1 # train without normalisation for this many chunks, to get the weights in the right 'zone'.
# this should be only a few, just 1 hopefully suffices.

GEN_BUFFER_SIZE = 1


# # need to load the full training data anyway to extract the validation set from it. 
# # alternatively we could create separate validation set files.
# DATA_TRAIN_PATH = "data/images_train_color_cropped33_singletf.npy.gz"
# DATA2_TRAIN_PATH = "data/images_train_color_8x_singletf.npy.gz"
# DATA_VALIDONLY_PATH = "data/images_validonly_color_cropped33_singletf.npy.gz"
# DATA2_VALIDONLY_PATH = "data/images_validonly_color_8x_singletf.npy.gz"
# DATA_TEST_PATH = "data/images_test_color_cropped33_singletf.npy.gz"
# DATA2_TEST_PATH = "data/images_test_color_8x_singletf.npy.gz"

TARGET_PATH = "predictions/final/try_convnet_cc_multirotflip_3x69r45_shareddense512.csv"
ANALYSIS_PATH = "analysis/final/try_convnet_cc_multirotflip_3x69r45_shareddense512.pkl"
# FEATURES_PATTERN = "features/try_convnet_chunked_ra_b3sched.%s.npy"

print "Set up data loading"
# TODO: adapt this so it loads the validation data from JPEGs and does the processing realtime

input_sizes = [(69, 69), (69, 69)]

ds_transforms = [
    ra.build_ds_transform(3.0, target_size=input_sizes[0]),
    ra.build_ds_transform(3.0, target_size=input_sizes[1]) + ra.build_augmentation_transform(rotation=45)
    ]

num_input_representations = len(ds_transforms)

augmentation_params = {
    'zoom_range': (1.0 / 1.3, 1.3),
    'rotation_range': (0, 360),
    'shear_range': (0, 0),
    'translation_range': (-4, 4),
    'do_flip': True,
}

augmented_data_gen = ra.realtime_augmented_data_gen(num_chunks=NUM_CHUNKS, chunk_size=CHUNK_SIZE,
                                                    augmentation_params=augmentation_params, ds_transforms=ds_transforms,
                                                    target_sizes=input_sizes)

post_augmented_data_gen = ra.post_augment_brightness_gen(augmented_data_gen, std=0.5)

train_gen = load_data.buffered_gen_mp(post_augmented_data_gen, buffer_size=GEN_BUFFER_SIZE)


y_train = np.load("data/solutions_train.npy")
train_ids = load_data.train_ids
test_ids = load_data.test_ids

# split training data into training + a small validation set
num_train = len(train_ids)
num_test = len(test_ids)

num_valid = num_train // 10 # integer division
num_train -= num_valid

y_valid = y_train[num_train:]
y_train = y_train[:num_train]

valid_ids = train_ids[num_train:]
train_ids = train_ids[:num_train]

train_indices = np.arange(num_train)
valid_indices = np.arange(num_train, num_train + num_valid)
test_indices = np.arange(num_test)



def create_train_gen():
    """
    this generates the training data in order, for postprocessing. Do not use this for actual training.
    """
    data_gen_train = ra.realtime_fixed_augmented_data_gen(train_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_train, buffer_size=GEN_BUFFER_SIZE)


def create_valid_gen():
    data_gen_valid = ra.realtime_fixed_augmented_data_gen(valid_indices, 'train',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_valid, buffer_size=GEN_BUFFER_SIZE)


def create_test_gen():
    data_gen_test = ra.realtime_fixed_augmented_data_gen(test_indices, 'test',
        ds_transforms=ds_transforms, chunk_size=CHUNK_SIZE, target_sizes=input_sizes)
    return load_data.buffered_gen_mp(data_gen_test, buffer_size=GEN_BUFFER_SIZE)


print "Preprocess validation data upfront"
start_time = time.time()
xs_valid = [[] for _ in xrange(num_input_representations)]

for data, length in create_valid_gen():
    for x_valid_list, x_chunk in zip(xs_valid, data):
        x_valid_list.append(x_chunk[:length])

xs_valid = [np.vstack(x_valid) for x_valid in xs_valid]
xs_valid = [x_valid.transpose(0, 3, 1, 2) for x_valid in xs_valid] # move the colour dimension up


print "  took %.2f seconds" % (time.time() - start_time)



print "Build model"
l0 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[0][0], input_sizes[0][1])
l0_45 = layers.Input2DLayer(BATCH_SIZE, NUM_INPUT_FEATURES, input_sizes[1][0], input_sizes[1][1])

l0r = layers.MultiRotSliceLayer([l0, l0_45], part_size=45, include_flip=True)

l0s = cc_layers.ShuffleBC01ToC01BLayer(l0r) 

l1a = cc_layers.CudaConvnetConv2DLayer(l0s, n_filters=32, filter_size=6, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l1 = cc_layers.CudaConvnetPooling2DLayer(l1a, pool_size=2)

l2a = cc_layers.CudaConvnetConv2DLayer(l1, n_filters=64, filter_size=5, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l2 = cc_layers.CudaConvnetPooling2DLayer(l2a, pool_size=2)

l3a = cc_layers.CudaConvnetConv2DLayer(l2, n_filters=128, filter_size=3, weights_std=0.01, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3b = cc_layers.CudaConvnetConv2DLayer(l3a, n_filters=128, filter_size=3, pad=0, weights_std=0.1, init_bias_value=0.1, dropout=0.0, partial_sum=1, untie_biases=True)
l3 = cc_layers.CudaConvnetPooling2DLayer(l3b, pool_size=2)

l3s = cc_layers.ShuffleC01BToBC01Layer(l3)
l3f = layers.FlattenLayer(l3s)

l4a = layers.DenseLayer(l3f, n_outputs=1024, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)
l4 = layers.FeatureMaxPoolingLayer(l4a, pool_size=2, feature_dim=1, implementation='reshape')

j4 = layers.MultiRotMergeLayer(l4, num_views=4) # 2) # merge convolutional parts

l5a = layers.DenseLayer(j4, n_outputs=4096, weights_std=0.001, init_bias_value=0.01, dropout=0.5, nonlinearity=layers.identity)
l5 = layers.FeatureMaxPoolingLayer(l5a, pool_size=2, feature_dim=1, implementation='reshape')

l6a = layers.DenseLayer(l5, n_outputs=37, weights_std=0.01, init_bias_value=0.1, dropout=0.5, nonlinearity=layers.identity)

# l6 = layers.OutputLayer(l5, error_measure='mse')
l6 = custom.OptimisedDivGalaxyOutputLayer(l6a) # this incorporates the constraints on the output (probabilities sum to one, weighting, etc.)

train_loss_nonorm = l6.error(normalisation=False)
train_loss = l6.error() # but compute and print this!
valid_loss = l6.error(dropout_active=False)
all_parameters = layers.all_parameters(l6)
all_bias_parameters = layers.all_bias_parameters(l6)

xs_shared = [theano.shared(np.zeros((1,1,1,1), dtype=theano.config.floatX)) for _ in xrange(num_input_representations)]
y_shared = theano.shared(np.zeros((1,1), dtype=theano.config.floatX))

learning_rate = theano.shared(np.array(LEARNING_RATE_SCHEDULE[0], dtype=theano.config.floatX))

idx = T.lscalar('idx')

givens = {
    l0.input_var: xs_shared[0][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l0_45.input_var: xs_shared[1][idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
    l6.target_var: y_shared[idx*BATCH_SIZE:(idx+1)*BATCH_SIZE],
}

# updates = layers.gen_updates(train_loss, all_parameters, learning_rate=LEARNING_RATE, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates_nonorm = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss_nonorm, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)
updates = layers.gen_updates_nesterov_momentum_no_bias_decay(train_loss, all_parameters, all_bias_parameters, learning_rate=learning_rate, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY)

train_nonorm = theano.function([idx], train_loss_nonorm, givens=givens, updates=updates_nonorm)
train_norm = theano.function([idx], train_loss, givens=givens, updates=updates)
compute_loss = theano.function([idx], valid_loss, givens=givens) # dropout_active=False
compute_output = theano.function([idx], l6.predictions(dropout_active=False), givens=givens, on_unused_input='ignore') # not using the labels, so theano complains
compute_features = theano.function([idx], l4.output(dropout_active=False), givens=givens, on_unused_input='ignore')


print "Train model"
start_time = time.time()
prev_time = start_time

num_batches_valid = x_valid.shape[0] // BATCH_SIZE
losses_train = []
losses_valid = []

param_stds = []

for e in xrange(NUM_CHUNKS):
    print "Chunk %d/%d" % (e + 1, NUM_CHUNKS)
    chunk_data, chunk_length = train_gen.next()
    y_chunk = chunk_data.pop() # last element is labels.
    xs_chunk = chunk_data

    # need to transpose the chunks to move the 'channels' dimension up
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk]

    if e in LEARNING_RATE_SCHEDULE:
        current_lr = LEARNING_RATE_SCHEDULE[e]
        learning_rate.set_value(LEARNING_RATE_SCHEDULE[e])
        print "  setting learning rate to %.6f" % current_lr

    # train without normalisation for the first # chunks.
    if e >= NUM_CHUNKS_NONORM:
        train = train_norm
    else:
        train = train_nonorm

    print "  load training data onto GPU"
    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)
    y_shared.set_value(y_chunk)
    num_batches_chunk = x_chunk.shape[0] // BATCH_SIZE

    # import pdb; pdb.set_trace()

    print "  batch SGD"
    losses = []
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        loss = train(b)
        losses.append(loss)
        # print "  loss: %.6f" % loss

    mean_train_loss = np.sqrt(np.mean(losses))
    print "  mean training loss (RMSE):\t\t%.6f" % mean_train_loss
    losses_train.append(mean_train_loss)

    # store param stds during training
    param_stds.append([p.std() for p in layers.get_param_values(l6)])

    if ((e + 1) % VALIDATE_EVERY) == 0:
        print
        print "VALIDATING"
        print "  load validation data onto GPU"
        for x_shared, x_valid in zip(xs_shared, xs_valid):
            x_shared.set_value(x_valid)
        y_shared.set_value(y_valid)

        print "  compute losses"
        losses = []
        for b in xrange(num_batches_valid):
            # if b % 1000 == 0:
            #     print "  batch %d/%d" % (b + 1, num_batches_valid)
            loss = compute_loss(b)
            losses.append(loss)

        mean_valid_loss = np.sqrt(np.mean(losses))
        print "  mean validation loss (RMSE):\t\t%.6f" % mean_valid_loss
        losses_valid.append(mean_valid_loss)

        layers.dump_params(l6, e=e)

    now = time.time()
    time_since_start = now - start_time
    time_since_prev = now - prev_time
    prev_time = now
    est_time_left = time_since_start * (float(NUM_CHUNKS - (e + 1)) / float(e + 1))
    eta = datetime.now() + timedelta(seconds=est_time_left)
    eta_str = eta.strftime("%c")
    print "  %s since start (%.2f s)" % (load_data.hms(time_since_start), time_since_prev)
    print "  estimated %s to go (ETA: %s)" % (load_data.hms(est_time_left), eta_str)
    print


del chunk_data, xs_chunk, x_chunk, y_chunk, xs_valid, x_valid # memory cleanup


print "Compute predictions on validation set for analysis in batches"
predictions_list = []
for b in xrange(num_batches_valid):
    # if b % 1000 == 0:
    #     print "  batch %d/%d" % (b + 1, num_batches_valid)

    predictions = compute_output(b)
    predictions_list.append(predictions)

all_predictions = np.vstack(predictions_list)

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0

print "Write validation set predictions to %s" % ANALYSIS_PATH
with open(ANALYSIS_PATH, 'w') as f:
    pickle.dump({
        'ids': valid_ids[:num_batches_valid * BATCH_SIZE], # note that we need to truncate the ids to a multiple of the batch size.
        'predictions': all_predictions,
        'targets': y_valid,
        'mean_train_loss': mean_train_loss,
        'mean_valid_loss': mean_valid_loss,
        'time_since_start': time_since_start,
        'losses_train': losses_train,
        'losses_valid': losses_valid,
        'param_values': layers.get_param_values(l6),
        'param_stds': param_stds,
    }, f, pickle.HIGHEST_PROTOCOL)


del predictions_list, all_predictions # memory cleanup


# print "Loading test data"
# x_test = load_data.load_gz(DATA_TEST_PATH)
# x2_test = load_data.load_gz(DATA2_TEST_PATH)
# test_ids = np.load("data/test_ids.npy")
# num_test = x_test.shape[0]
# x_test = x_test.transpose(0, 3, 1, 2) # move the colour dimension up.
# x2_test = x2_test.transpose(0, 3, 1, 2)
# create_test_gen = lambda: load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


print "Computing predictions on test data"
predictions_list = []
for e, (xs_chunk, chunk_length) in enumerate(create_test_gen()):
    print "Chunk %d" % (e + 1)
    xs_chunk = [x_chunk.transpose(0, 3, 1, 2) for x_chunk in xs_chunk] # move the colour dimension up.

    for x_shared, x_chunk in zip(xs_shared, xs_chunk):
        x_shared.set_value(x_chunk)

    num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

    # make predictions for testset, don't forget to cute off the zeros at the end
    for b in xrange(num_batches_chunk):
        # if b % 1000 == 0:
        #     print "  batch %d/%d" % (b + 1, num_batches_chunk)

        predictions = compute_output(b)
        predictions_list.append(predictions)


all_predictions = np.vstack(predictions_list)
all_predictions = all_predictions[:num_test] # truncate back to the correct length

# postprocessing: clip all predictions to 0-1
all_predictions[all_predictions > 1] = 1.0
all_predictions[all_predictions < 0] = 0.0


print "Write predictions to %s" % TARGET_PATH
# test_ids = np.load("data/test_ids.npy")

with open(TARGET_PATH, 'wb') as csvfile:
    writer = csv.writer(csvfile) # , delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['GalaxyID', 'Class1.1', 'Class1.2', 'Class1.3', 'Class2.1', 'Class2.2', 'Class3.1', 'Class3.2', 'Class4.1', 'Class4.2', 'Class5.1', 'Class5.2', 'Class5.3', 'Class5.4', 'Class6.1', 'Class6.2', 'Class7.1', 'Class7.2', 'Class7.3', 'Class8.1', 'Class8.2', 'Class8.3', 'Class8.4', 'Class8.5', 'Class8.6', 'Class8.7', 'Class9.1', 'Class9.2', 'Class9.3', 'Class10.1', 'Class10.2', 'Class10.3', 'Class11.1', 'Class11.2', 'Class11.3', 'Class11.4', 'Class11.5', 'Class11.6'])

    # write data
    for k in xrange(test_ids.shape[0]):
        row = [test_ids[k]] + all_predictions[k].tolist()
        writer.writerow(row)

print "Gzipping..."
os.system("gzip -c %s > %s.gz" % (TARGET_PATH, TARGET_PATH))


del all_predictions, predictions_list, xs_chunk, x_chunk # memory cleanup


# # need to reload training data because it has been split and shuffled.
# # don't need to reload test data
# x_train = load_data.load_gz(DATA_TRAIN_PATH)
# x2_train = load_data.load_gz(DATA2_TRAIN_PATH)
# x_train = x_train.transpose(0, 3, 1, 2) # move the colour dimension up
# x2_train = x2_train.transpose(0, 3, 1, 2)
# train_gen_features = load_data.array_chunker_gen([x_train, x2_train], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)
# test_gen_features = load_data.array_chunker_gen([x_test, x2_test], chunk_size=CHUNK_SIZE, loop=False, truncate=False, shuffle=False)


# for name, gen, num in zip(['train', 'test'], [train_gen_features, test_gen_features], [x_train.shape[0], x_test.shape[0]]):
#     print "Extracting feature representations for all galaxies: %s" % name
#     features_list = []
#     for e, (xs_chunk, chunk_length) in enumerate(gen):
#         print "Chunk %d" % (e + 1)
#         x_chunk, x2_chunk = xs_chunk
#         x_shared.set_value(x_chunk)
#         x2_shared.set_value(x2_chunk)

#         num_batches_chunk = int(np.ceil(chunk_length / float(BATCH_SIZE)))  # need to round UP this time to account for all data

#         # compute features for set, don't forget to cute off the zeros at the end
#         for b in xrange(num_batches_chunk):
#             if b % 1000 == 0:
#                 print "  batch %d/%d" % (b + 1, num_batches_chunk)

#             features = compute_features(b)
#             features_list.append(features)

#     all_features = np.vstack(features_list)
#     all_features = all_features[:num] # truncate back to the correct length

#     features_path = FEATURES_PATTERN % name 
#     print "  write features to %s" % features_path
#     np.save(features_path, all_features)


print "Done!"

########NEW FILE########
