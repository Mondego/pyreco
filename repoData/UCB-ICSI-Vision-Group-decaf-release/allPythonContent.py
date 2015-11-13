__FILENAME__ = base
"""base.py implements the basic data types.
"""

import cPickle as pickle
from collections import defaultdict
import logging
import networkx as nx
import numpy as np

from decaf._blob import Blob
from decaf.puff import Puff

class DecafError(Exception):
    """NOOOOOOO! I need caffeine!
    
    Yes, this is the basic error type under decaf.
    """
    pass


class InvalidLayerError(DecafError):
    """The error when an invalid spec is passed to a layer."""
    pass


class InvalidNetError(DecafError):
    """The error raised when the network does not pass validation."""
    pass


class Filler(object):
    """This is the class that implements util functions to fill a blob.
    
    A filler implements the fill() function that takes a blob as the input,
    and fills the blob's data() field.
    """

    def __init__(self, **kwargs):
        """simply get the spec."""
        self.spec = kwargs

    def fill(self, mat):
        raise NotImplementedError


class Layer(object):
    """A Layer is the most basic component in decal. It takes multiple blobs
    as its input, and produces its outputs as multiple blobs. The parameter
    to be learned in the layers are 
    
    When designing layers, always make sure that your code deals with minibatches.
    """

    def __init__(self, **kwargs):
        """Creates a Layer.

        Necessary argument:
            name: the name of the layer.
        """
        self.spec = kwargs
        self.name = self.spec['name']
        self.freeze = self.spec.get('freeze', False)
        self._param = []

    def forward(self, bottom, top):
        """Computes the forward pass.
        
        Input:
            bottom: the data at the bottom.
            top: the top-layer output.
        """
        raise NotImplementedError

    def predict(self, bottom, top):
        """A wrapper function to do prediction. If a layer has different
        behaviors during training and testing, one can write a predict()
        function which is called during testing time.
        
        In default, the predict() function will simply call forward.
        """
        return self.forward(bottom, top)


    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass.
        Input:
            bottom: the data at the bottom.
            top: the data at the top.
            propagate_down: if set False, the gradient w.r.t. the bottom
                blobs does not need to be computed.
        Output:
            loss: the loss being generated in this layer. Note that if your
                layer does not generate any loss, you should still return 0.
        """
        raise NotImplementedError
    
    def update(self):
        """Updates my parameters, based on the diff value given in the param
        blob.
        """
        raise NotImplementedError

    def param(self):
        """Returns the parameters in this layer. It should be a list of
        Blob objects.
        
        In our layer, either collect all your parameters into the self._param
        list, or implement your own param() function.
        """
        return self._param


# pylint: disable=R0921
class DataLayer(Layer):
    """A Layer that generates data.
    """
    
    def forward(self, bottom, top):
        """Generates the data.
        
        Your data layer should override this function.
        """
        raise NotImplementedError

    def backward(self, bottom, top, propagate_down):
        """No gradient needs to be computed for data.
        
        You should not override this function.
        """
        raise DecafError('You should not reach this.')

    def update(self):
        """The data layer has no parameter, and the update() function
        should not be called.
        """
        pass


# pylint: disable=R0921
class LossLayer(Layer):
    """A Layer that implements loss. Usually, the forward pass of the loss
    does the actual computation of both the loss and the gradients, and the
    backward pass will simply return the loss value. The loss layer should not
    accept any blobs on its top.
    
    The loss layer takes a keyword argument 'weight' (defaults to 1) that
    allows one to adjust the balance between multiple losses.
    """

    def __init__(self, **kwargs):
        Layer.__init__(self, **kwargs)
        self._loss = 0
        self.spec['weight'] = self.spec.get('weight', 1.)

    def forward(self, bottom, top):
        """The forward pass. In your loss layer, you need to compute the loss
        and store it at self._loss.
        """
        raise NotImplementedError

    def backward(self, bottom, top, propagate_down):
        return self._loss

    def update(self):
        pass


class SplitLayer(Layer):
    """A layer that splits a blob to multiple blobs."""

    def __init__(self, **kwargs):
        """Initializes a Split layer.
        """
        Layer.__init__(self, **kwargs)
    
    def forward(self, bottom, top):
        """Computes the forward pass.

        The output will simply mirror the input data.
        """
        if len(bottom) != 1:
            raise ValueError(
                'SplitLayer only accepts one input as its bottom.')
        for output in top:
            output.mirror(bottom[0])

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if propagate_down:
            diff = bottom[0].init_diff()
            for single_top in top:
                diff[:] += single_top.diff()
        return 0.

    def update(self):
        """Split has nothing to update."""
        pass


class Solver(object):
    """This is the very basic form of the solver."""
    def __init__(self, **kwargs):
        self.spec = kwargs

    def solve(self, net, previous_net=None):
        """The solve function takes a net as an input, and optimizes its
        parameters.
        
        Input:
            net: the decaf network to run optimization on.
            previous_net: the previous network that produces input to the net.
                This net should be pre-trained.
        """
        raise NotImplementedError


class Regularizer(object):
    """This is the class that implements the regularization terms.
    
    A regularizer takes in a blob and a scale term, and adds the gradient
    imposed by the regularization term to the blob's diff() field. It then
    returns the 
    """

    def __init__(self, **kwargs):
        """Initializes a regularizer. A regularizer needs a necessary keyword
        'weight'.
        """
        self.spec = kwargs
        self._weight = self.spec['weight']

    def reg(self, blob):
        """Compute the regularization term from the blob's data field, and
        add the regularization term to its diff directly.

        Input:
            blob: the blob to work on.
        """
        raise NotImplementedError


DECAF_PREFIX = '_decaf'


class Net(object):
    """A Net is a directed graph with layer names and layer instances."""

    def __init__(self, name=None):
        """Initialize a net.
        Input:
            name: (optional) a string to help remember what the net does.
        """
        if name is None:
            name = 'decaf_net'
        self.name = name
        self.graph = nx.DiGraph()
        self.blobs = {}
        # layers is a dictionary that maps layer names to actual layers.
        self.layers = {}
        # needs is a dictionary that maps layer names to a list of blob names
        # that it needs.
        self.needs = {}
        # provides is a dictionary that maps layer names to a list of blob
        # names that it provides.
        self.provides = {}
        # The parameters below will be automaticall inferred 
        # The counts for blobs
        self._need_count = defaultdict(int)
        # The topological order to execute the layer.
        self._forward_order = None
        self._backward_order = None
        # input_blobs are all blobs that have no layer producing them - they
        # have to be provided by the user. We only store the blob names.
        self._input_blobs = None
        # output_blibs are all blobs that no layer uses - they will be emitted
        # by the predict() function. We only store the blob names.
        self._output_blobs = None
        self._params = None
        self._finished = False

    def save(self, filename, store_full=False):
        """Saving the necessary 
        
        When pickling, we will simply store the network structure, but not
        any of the inferred knowledge or intermediate blobs.
        
        data layers and loss layers. If store_full is False, the data and loss
        layers are stripped and not stored - this will enable one to just keep
        necessary layers for future use.
        """
        output = [self.name, {}]
        for name, layer in self.layers.iteritems():
            if (not store_full and
                (isinstance(layer, DataLayer) or 
                 isinstance(layer, LossLayer) or
                 name.startswith(DECAF_PREFIX))):
                # We do not need to store these layers.
                continue
            else:
                output[1][name] = (layer, self.needs[name], self.provides[name])
        # finally, pickle the content.
        file = open(filename, 'wb')
        pickle.dump(output, file, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(filename):
        """Loads a network from file."""
        self = Net()
        file = open(filename, 'rb')
        contents = pickle.load(file)
        self.name = contents[0]
        for layer, needs, provides in contents[1].values():
            self.add_layer(layer, needs=needs, provides=provides)
        self.finish()
        return self

    def load_from(self, filename):
        """Load the parameters from an existing network.

        Unlike load, this function should be called on an already constructed
        network. What it does is to look into the file, and if there is any
        layer in the file that has the same name as a layer name defined in
        the current network, replace the current network's corresponding layer
        with the layer in the file.
        """
        file = open(filename, 'rb')
        contents = pickle.load(file)
        for name in contents[1]:
            if name in self.layers:
                self.layers[name] = contents[1][name][0]
        # after loading, we need to re-parse the layer to fix all reference
        # issues.
        self.finish()

    def add_layer(self, layer, needs=None, provides=None):
        """Add a layer to the current network.

        Args:
            layer: a decaf.base.Layer instance.
            needs: a tuple of strings, indicating the blobs that the layer
                needs as its input.
            provides: similar to needs, but the layer's output instead.
        """
        self._finished = False
        # validate input
        if needs is None:
            needs = []
        if provides is None:
            provides = []
        if type(needs) is str:
            needs = [needs]
        if type(provides) is str:
            provides = [provides]
        self._finished = False
        # Add the layer
        if layer.name in self.layers or layer.name in self.blobs:
            raise InvalidNetError('A name already exists: %s' % layer.name)
        self.layers[layer.name] = layer
        # Add the blobs
        # TODO: the current check may be slow, consider rewriting.
        already_provided = sum(self.provides.values(), [])
        for blobname in provides:
            if blobname in already_provided:
                raise InvalidNetError(
                    'Blob %s already provided by another layer.' % blobname)
        for blobname in needs + provides:
            if blobname in self.layers:
                raise InvalidNetError(
                    'Blob name found as a layer name: %s' % blobname)
            elif blobname not in self.blobs:
                self.blobs[blobname] = Blob()
        for name in needs: 
            self._need_count[name] += 1
        self.needs[layer.name] = list(needs)
        self.provides[layer.name] = list(provides)
        self._actual_needs = None

    @staticmethod
    def _make_output_name(layer):
        """Make an output name for a layer, assuming that it has only one
        output.
        """
        return '%s_%s_out' % (DECAF_PREFIX, layer.name)

    def add_layers(self, layers, needs=None, provides=None):
        """A wrapper that adds multiple layers as a chain to the graph. Each
        layer in the layers list should have only one blob as its input
        (except the first layer, whose input is given by needs), and only one
        blob as its output (except the last layer, likewise).
        """
        self._finished = False
        if isinstance(layers, Layer):
            # We are just given one simple layer
            self.add_layer(layers, needs, provides)
        elif len(layers) == 1:
            self.add_layer(layers[0], needs, provides)
        else:
            # add the first layer
            self.add_layer(layers[0], needs=needs,
                           provides=Net._make_output_name(layers[0]))
            for i in range(1, len(layers) - 1):
                self.add_layer(layers[i],
                               needs=Net._make_output_name(layers[i-1]),
                               provides=Net._make_output_name(layers[i]))
            self.add_layer(layers[-1], needs=Net._make_output_name(layers[-2]),
                           provides=provides)

    def finish(self):
        """Call this function when you finish the network construction."""
        # validate and generate the graph
        self._generate_graph()
        try:
            topological_order = nx.topological_sort(self.graph)
        except nx.NetworkXUnfeasible as error:
            raise DecafError(error)
        # For efficiency reasons, we will see for each layer, whether the
        # backward operation needs to be carried out.
        # This is stored in two parameters:
        #   need_backward: whether the backward pass needs to be carried out.
        #   propagate_down: whether the gradient w.r.t. to the bottom layer
        #       needs to be carried out.
        for name in topological_order:
            # whether the predecessor needs backward operation.
            pred_need_backward = any(self.graph.node[p]['need_backward']
                                     for p in self.graph.predecessors(name))
            if name in self.layers:
                # see if a layer needs backward operation. A layer needs
                # backward operation if (1) it has parameters and isn't frozen
                # or (2) any of its predecessors needs backward operation.
                layer = self.layers[name]
                if (pred_need_backward or
                    (len(layer.param()) and not layer.freeze)):
                    self.graph.node[name]['need_backward'] = True
                else:
                    self.graph.node[name]['need_backward'] = False
                # see if a layer needs to compute its bottom diff. A layer
                # needs to compute its bottom diff if any of its predecessors
                # needs backward operation.
                if pred_need_backward:
                    self.graph.node[name]['propagate_down'] = True
                else:
                    self.graph.node[name]['propagate_down'] = False
            else:
                # see if a blob needs backward operation.
                # This is only used so we can verify further layers.
                self.graph.node[name]['need_backward'] = pred_need_backward
        # create the order to run forward and backward passes
        layerorder = [name for name in topological_order
                      if name in self.layers]
        logging.debug('Layer order: %s', str(layerorder))
        self._forward_order = []
        for n in layerorder:
            self._forward_order.append(
                (n, self.layers[n],
                 [self.blobs[name] for name in self._actual_needs[n]],
                 [self.blobs[name] for name in self.provides[n]]))
        # logging.debug('Forward order details: %s', str(self._forward_order))
        self._backward_order = []
        for n in layerorder[::-1]:
            if self.graph.node[n]['need_backward']:
                self._backward_order.append(
                    (n, self.layers[n],
                     [self.blobs[name] for name in self._actual_needs[n]],
                     [self.blobs[name] for name in self.provides[n]],
                     self.graph.node[n]['propagate_down']))
        # logging.debug('Backward order details: %s', str(self._backward_order))
        # store all the parameters
        self._params = []
        for name in layerorder:
            self._params.extend(self.layers[name].param())
        # Note: Any further finishing code should be inserted here.
        self._finished = True
    
    def params(self):
        """Return a list of parameters used in the network."""
        return self._params

    def _generate_graph(self):
        """Validates if a network is executable, and generates the networkx 
        graph that reflects the execution order.
        """
        # first, get input and output blobs.
        provided_blobs = set(sum(self.provides.values(), []))
        self._input_blobs = [name for name in self.blobs
                             if name not in provided_blobs]
        if len(self._input_blobs):
            logging.info('This network needs input blobs: %s',
                         str(self._input_blobs))
        self._output_blobs = [name for name in self.blobs
                              if name not in self._need_count]
        if len(self._output_blobs):
            logging.info('This network produces output blobs: %s',
                         str(self._output_blobs))
        # For any blob that is needed by multiple layers, we will insert a split
        # layer to avoid gradient overwriting.
        for blobname, count in self._need_count.iteritems():
            if count > 1:
                split_provides = ['_'.join([DECAF_PREFIX, blobname, str(i)])
                                  for i in range(count)]
                self.add_layer(
                    SplitLayer(name='_'.join([DECAF_PREFIX, blobname, 'split'])),
                    needs=[blobname], provides=split_provides)
                logging.debug('Insert SplitLayer from [%s] to %s', blobname, str(split_provides))
        # compute actual_needed
        temp_need_idx = defaultdict(int)
        self._actual_needs = {}
        for layername, blobnames in self.needs.iteritems():
            actual_needs = []
            for blobname in blobnames:
                if (self._need_count[blobname] > 1 and 
                    not layername.startswith(DECAF_PREFIX)):
                    # instead of connecting it to the original blob, we connect
                    # it to the new splitted blob.
                    actual_needs.append(
                        '_'.join([DECAF_PREFIX, blobname,
                                  str(temp_need_idx[blobname])]))
                    temp_need_idx[blobname] += 1
                else:
                    actual_needs.append(blobname)
            self._actual_needs[layername] = list(actual_needs)
            logging.debug('Layer %s, needs %s, actual needs %s', layername, str(blobnames), str(actual_needs))
        # Now, create the graph
        self.graph = nx.DiGraph()
        for layername, blobnames in self._actual_needs.iteritems():
            logging.debug('Adding edges from %s to %s (needs)', str(blobnames), layername)
            for blobname in blobnames:
                self.graph.add_edge(blobname, layername)
        for layername, blobnames in self.provides.iteritems():
            logging.debug('Adding edges from %s to %s (provides)', layername, str(blobnames))
            for blobname in blobnames:
                self.graph.add_edge(layername, blobname)
        # Done creating graph!
        return        
                        
    def forward_backward(self, previous_net = None):
        """Runs the forward and backward passes of the net.
        """
        # the forward pass. We will also accumulate the loss function.
        if not self._finished:
            raise DecafError('Call finish() before you use the network.')
        if len(self._output_blobs):
            # If the network has output blobs, it usually shouldn't be used
            # to run forward-backward: such blobs won't be used and cause waste
            # of computation. Maybe the user is missing a few loss layers? We
            # will print the warning but still carry on.
            logging.warning('Have multiple unused blobs in the net. Do you'
                            ' actually mean running a forward backward pass?')
        loss = 0.
        # If there is a previous_net, we will run that first
        if isinstance(previous_net, Net):
            previous_blobs = previous_net.predict()
            try:
                for name in self._input_blobs:
                    self.blobs[name].mirror(previous_blobs[name])
            except KeyError as err:
                raise DecafError('Cannot run forward_backward on a network'
                                 ' with unspecified input blobs.', err)
        elif isinstance(previous_net, dict):
            # If previous net is a dict, simply mirror all the data.
            for key, arr in previous_net.iteritems():
                self.blobs[key].mirror(arr)
        for _, layer, bottom, top in self._forward_order:
            layer.forward(bottom, top)
        # the backward pass
        for name, layer, bottom, top, propagate_down in self._backward_order:
            layer_loss = layer.backward(bottom, top, propagate_down)
            loss += layer_loss
        return loss

    def predict(self, output_blobs = None, **kwargs):
        """Use the network to perform prediction. Note that your network
        should have at least one output blob. All input blobs need to be
        provided using the kwargs.
        
        Input:
            output_blobs: a list of output blobs to return. If None, all the 
                blobs that do not have layers following them are considered
                output and are returned.
            kwargs: any input data that the network needs. All the blobs in
                the network that do not have a layer generating them should
                be provided.
        Output:
            result: a dictionary where the keys are the output blob names, and
                the values are the numpy arrays storing the blob content.
        """
        if not self._finished:
            raise DecafError('Call finish() before you use the network.')
        for name in self._input_blobs:
            self.blobs[name].mirror(kwargs[name])
        for _, layer, bottom, top in self._forward_order:
            layer.predict(bottom, top)
        if not output_blobs:
            output_blobs = self._output_blobs
        return dict([(name, self.blobs[name].data())
                     for name in output_blobs])
    
    def feature(self, blob_name):
        """Returns the data in a specific blob name as the intermediate
        feature for the last run of either forward() or predict(). Note that
        if the network has not been run with any data, you should not call
        this function as the returned value will be invalid.
        
        Optionally, use predict() and provide a set of output blob names to
        obtain multiple features directly.
        
        Input:
            blob_name: the blob name to return.
        """
        return self.blobs[blob_name].data()

    def update(self):
        """Update the parameters using the diff values provided in the
        parameters blob."""
        for _, layer in self.layers.iteritems():
            layer.update()

########NEW FILE########
__FILENAME__ = test_convolution
from decaf import base
from decaf.layers import convolution
import numpy as np
import time

from theano.tensor.nnet import conv
import theano
import theano.tensor as T

def theano_convolution(input_size, dtype, num_kernels, ksize, mode, iternum):
    rng = np.random.RandomState(23455)
    # instantiate 4D tensor for input
    if dtype == np.float32:
        input = T.tensor4(name='input', dtype='float32')
    else:
        input = T.tensor4(name='input', dtype='float64')
    # initialize shared variable for weights.
    w_shp = (num_kernels, input_size[-1], ksize, ksize)
    w_bound = np.sqrt(input_size[-1] * ksize * ksize)
    W = theano.shared( np.asarray(
                rng.uniform(
                    low=-1.0 / w_bound,
                    high=1.0 / w_bound,
                    size=w_shp),
                dtype=dtype), name ='W')
    conv_out = conv.conv2d(input, W, border_mode=mode)
    # create theano function to compute filtered images
    f = theano.function([input], conv_out)
    img = np.random.random_sample(input_size).astype(dtype)
    # put image in 4D tensor of shape (1, 3, height, width)
    img_ = img.swapaxes(0, 2).swapaxes(1, 2).reshape(1, input_size[-1], input_size[0], input_size[1])
    img_ = np.ascontiguousarray(img_)
    # just in case theano want to initialize something, we will run the function once first.
    filtered_img = f(img_)
    start = time.time()
    for i in range(iternum):
        filtered_img = f(img_)
    print 'theano time:', (time.time() - start) / iternum

def decaf_convolution(input_size, dtype, num_kernels, ksize, stride, mode, iternum):
    bottom = base.Blob((1,) + input_size, dtype=dtype)
    layer = convolution.ConvolutionLayer(
        name='conv', num_kernels=num_kernels, ksize=ksize,
        stride=stride, mode=mode)
    top = base.Blob()
    # run a forward pass first to initialize everything.
    layer.forward([bottom], [top])
    top.init_diff()
    top.diff().flat = 1.
    print '*****'
    print 'input shape:', bottom.data().shape[1:]
    start = time.time()
    for i in range(iternum):
        layer.forward([bottom], [top])
    print 'forward runtime:', (time.time() - start) / iternum
    print 'output shape:', top.data().shape[1:]
    start = time.time()
    for i in range(iternum):
        layer.backward([bottom], [top], True)
    print 'backward runtime:', (time.time() - start) / iternum
    print '*****'

if __name__ == '__main__':
    print 'test float32'
    theano_convolution((256,256,3), np.float32, 16, 11,    'full', 50)
    decaf_convolution((256,256,3), np.float32, 16, 11, 1, 'full', 50)
    theano_convolution((256,256,3), np.float32, 16, 11,    'valid', 50)
    decaf_convolution((256,256,3), np.float32, 16, 11, 1, 'valid', 50)
    print 'test thick convolution'
    theano_convolution((55,55,96), np.float32, 256, 3,    'full', 50)
    decaf_convolution((55,55,96), np.float32, 256, 3, 1, 'full', 50)
    theano_convolution((55,55,96), np.float32, 256, 3,    'valid', 50)
    decaf_convolution((55,55,96), np.float32, 256, 3, 1, 'valid', 50)


########NEW FILE########
__FILENAME__ = test_lena_prediction_pipeline
"""A bunch of test scripts to check the performance of decafnet.
Recommended running command:
    srun -p vision -c 8 --nodelist=orange6 python test_lena_prediction_pipeline.py
"""
from decaf.scripts import decafnet
from decaf import util
from decaf.util import smalldata
import numpy as np
import cProfile as profile

# We will use a larger figure size since many figures are fairly big.
data_root='/u/vis/common/deeplearning/models/'
net = imagenet.DecafNet(data_root+'imagenet.decafnet.epoch90', data_root+'imagenet.decafnet.meta')
lena = smalldata.lena()
timer = util.Timer()

print 'Testing single classification with 10-part voting (10 runs)...'
# run a pass to initialize data
scores = net.classify(lena)
timer.reset()
for i in range(10):
    scores = net.classify(lena)
print 'Elapsed %s' % timer.total()

print 'Testing single classification with center_only (10 runs)...'
# run a pass to initialize data
scores = net.classify(lena, center_only=True)
timer.reset()
for i in range(10):
    scores = net.classify(lena, center_only=True)
print 'Elapsed %s' % timer.total()

lena_ready = lena[np.newaxis, :227,:227].astype(np.float32)
print 'Testing direct classification (10 runs)...'
# run a pass to initialize data
scores = net.classify_direct(lena_ready)
timer.reset()
for i in range(10):
    scores = net.classify_direct(lena_ready)
print 'Elapsed %s' % timer.total()

print 'Dumping computation time for layers:'
decaf_net = net._net
timer.reset()
for name, layer, bottom, top in decaf_net._forward_order:
    for i in range(100):
        layer.predict(bottom, top)
    print '%15s elapsed %f ms' % (name, timer.lap(False) * 10)

print 'Testing direct classification with batches (10 runs)...'
for batch in [1,2,5,10,20,100]:
    lena_batch = np.tile(lena_ready, [batch, 1, 1, 1,]).copy()
    # run a pass to initialize data
    scores = net.classify_direct(lena_batch)
    timer.reset()
    for i in range(10):
        scores = net.classify_direct(lena_batch)
    print 'Batch size %3d, equivalent time %s' % (batch, timer.total(False) / batch)

print 'Profiling batch 1 (100 runs)...'
pr = profile.Profile()
lena_batch = lena_ready.copy()
# run a pass to initialize data
scores = net.classify_direct(lena_batch)
pr.enable()
for i in range(100):
    scores = net.classify_direct(lena_batch)
pr.disable()
pr.dump_stats('lena_profile_batch1.pstats')
print 'Profiling done.'

print 'Profiling batch 10 (10 runs)...'
lena_batch = np.tile(lena_ready, [10, 1, 1, 1,]).copy()
# run a pass to initialize data
scores = net.classify_direct(lena_batch)
pr = profile.Profile()
pr.enable()
for i in range(10):
    scores = net.classify_direct(lena_batch)
pr.disable()
pr.dump_stats('lena_profile_batch10.pstats')
print 'Profiling done.'

########NEW FILE########
__FILENAME__ = demo_convolution
"""This demo will show how we do simple convolution on the lena image with
a 15*15 average filter.
"""

from decaf import base
from decaf.util import smalldata
from decaf.layers import convolution, fillers
import numpy as np
from skimage import io

"""The main demo code."""
img = np.asarray(smalldata.lena())
img = img.reshape((1,) + img.shape).astype(np.float64)
# wrap the img in a blob
input_blob = base.Blob()
input_blob.mirror(img)

# create a convolutional layer
layer = convolution.ConvolutionLayer(
    name='convolution',
    num_kernels=1,
    ksize=15,
    stride=1,
    mode='same',
    filler=fillers.ConstantFiller(value=1./15/15/3))

# run the layer
output_blob = base.Blob()
layer.forward([input_blob], [output_blob])

out = output_blob.data()[0, :, :, 0].astype(np.uint8)
io.imsave('out.png', out)
print('Convolution result written to out.png')

########NEW FILE########
__FILENAME__ = demo_mnist_two_layer_classifier
"""A code to perform logistic regression."""
import cPickle as pickle
from decaf import base
from decaf.layers import core_layers
from decaf.layers import regularization
from decaf.layers import fillers
from decaf.layers.data import mnist
from decaf.opt import core_solvers
from decaf.util import visualize
import logging
import numpy as np
import sys

# You may want to change these parameters when running the code.
ROOT_FOLDER='/u/vis/x1/common/mnist'
MINIBATCH=4096
NUM_NEURONS = 100
NUM_CLASS = 10
METHOD = 'sgd'

def main():
    logging.getLogger().setLevel(logging.INFO)
    ######################################
    # First, let's create the decaf layer.
    ######################################
    logging.info('Loading data and creating the network...')
    decaf_net = base.Net()
    # add data layer
    dataset = mnist.MNISTDataLayer(
        name='mnist', rootfolder=ROOT_FOLDER, is_training=True)
    decaf_net.add_layer(dataset,
                        provides=['image-all', 'label-all'])
    # add minibatch layer for stochastic optimization
    minibatch_layer = core_layers.BasicMinibatchLayer(
        name='batch', minibatch=MINIBATCH)
    decaf_net.add_layer(minibatch_layer,
                        needs=['image-all', 'label-all'],
                        provides=['image', 'label'])
    # add the two_layer network
    decaf_net.add_layers([
        core_layers.FlattenLayer(name='flatten'),
        core_layers.InnerProductLayer(
            name='ip1', num_output=NUM_NEURONS,
            filler=fillers.GaussianRandFiller(std=0.1),
            bias_filler=fillers.ConstantFiller(value=0.1)),
        core_layers.ReLULayer(name='relu1'),
        core_layers.InnerProductLayer(
            name='ip2', num_output=NUM_CLASS,
            filler=fillers.GaussianRandFiller(std=0.3))
        ], needs='image', provides='prediction')
    # add loss layer
    loss_layer = core_layers.MultinomialLogisticLossLayer(
        name='loss')
    decaf_net.add_layer(loss_layer,
                        needs=['prediction', 'label'])
    # finish.
    decaf_net.finish()
    ####################################
    # Decaf layer finished construction!
    ####################################
    
    # now, try to solve it
    if METHOD == 'adagrad':
        # The Adagrad Solver
        solver = core_solvers.AdagradSolver(base_lr=0.02, base_accum=1.e-6,
                                            max_iter=1000)
    elif METHOD == 'sgd':
        solver = core_solvers.SGDSolver(base_lr=0.1, lr_policy='inv',
                                        gamma=0.001, power=0.75, momentum=0.9,
                                        max_iter=1000)
    solver.solve(decaf_net)
    visualize.draw_net_to_file(decaf_net, 'mnist.png')
    decaf_net.save('mnist_2layers.decafnet')

    ##############################################
    # Now, let's load the net and run predictions 
    ##############################################
    prediction_net = base.Net.load('mnist_2layers.decafnet')
    visualize.draw_net_to_file(prediction_net, 'mnist_test.png')
    # obtain the test data.
    dataset_test = mnist.MNISTDataLayer(
        name='mnist', rootfolder=ROOT_FOLDER, is_training=False)
    test_image = base.Blob()
    test_label = base.Blob()
    dataset_test.forward([], [test_image, test_label])
    # Run the net.
    pred = prediction_net.predict(image=test_image)['prediction']
    accuracy = (pred.argmax(1) == test_label.data()).sum() / float(test_label.data().size)
    print 'Testing accuracy:', accuracy
    print 'Done.'

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = demo_sparse_autoencoder
"""This demo will show how we train a sparse autoencoder as described in more
detail at:
    http://deeplearning.stanford.edu/wiki/index.php/Exercise:Sparse_Autoencoder

To run this demo, simply do python demo_sparse_autoencoders.py. 

You will need to have X connection if you are ssh into your server. The
program will output the network structure to sparse-autoencoder-structure.png,
and display the learned filters. The trained network (less the input and loss
layers) is saved at sparse-autoencoder.decaf_net.
"""

from decaf import base
from decaf.util import smalldata, visualize
from decaf.layers import core_layers, fillers, regularization
from decaf.opt import core_solvers
import logging
from matplotlib import pyplot
import numpy as np

################################################
# Setting up the parameters for the autoencoder.
################################################

NUM_PATCHES = 10000
PSIZE = 8
NUM_HIDDEN = 25
INIT_SCALE = np.sqrt(6. / (NUM_HIDDEN + PSIZE * PSIZE + 1))
MAXFUN = 500
np.random.seed(1701)

################################################
# Generating training data.
################################################

logging.getLogger().setLevel(logging.INFO)
logging.info('*** Get patches ***')
images = smalldata.whitened_images()
patch_extractor = core_layers.RandomPatchLayer(
    name='extractor', psize=PSIZE, factor=NUM_PATCHES / 10)
patches = base.Blob()
patch_extractor.forward([images], [patches])
logging.info('*** Patch stats: %s', str(patches.data().shape))
logging.info('*** Normalize patches ***')
patches_data = patches.data()
# subtract mean
patches_data -= patches_data.mean(axis=0)
std = patches_data.std()
np.clip(patches_data, - std * 3, std * 3, out=patches_data)
# We shrink the patch range a little, to [0.1, 0.9]
patches_data *= 0.4 / std / 3.
patches_data += 0.5
logging.info('*** Finished Patch Preparation ***')

#############################################
# Creating the decaf net for the autoencoder.
#############################################

logging.info('*** Constructing the network ***')
decaf_net = base.Net()
# The data layer
decaf_net.add_layer(
    core_layers.NdarrayDataLayer(name='data-layer', sources=[patches]),
    provides='patches-origin')
# We will flatten the patches to a flat vector
decaf_net.add_layer(
    core_layers.FlattenLayer(name='flatten'),
    needs='patches-origin',
    provides='patches-flatten')
# The first inner product layer
decaf_net.add_layer(
    core_layers.InnerProductLayer(
            name='ip',
            num_output=NUM_HIDDEN,
            filler=fillers.RandFiller(min=-INIT_SCALE, max=INIT_SCALE),
            reg=regularization.L2Regularizer(weight=0.00005)),
    needs='patches-flatten',
    provides='ip-out')
# The first sigmoid layer
decaf_net.add_layer(
    core_layers.SigmoidLayer(name='sigmoid'),
    needs='ip-out',
    provides='sigmoid-out')
# The sparsity term imposed on the sigmoid output
decaf_net.add_layer(
    core_layers.AutoencoderLossLayer(
            name='sigmoid-reg',
            weight=3.,
            ratio=0.01),
    needs='sigmoid-out')
# The second inner product layer
decaf_net.add_layer(
    core_layers.InnerProductLayer(
            name='ip2',
            num_output=PSIZE * PSIZE,
            filler=fillers.RandFiller(min=-INIT_SCALE, max=INIT_SCALE),
            reg=regularization.L2Regularizer(weight=0.00005)),
    needs='sigmoid-out',
    provides='ip2-out')
# The second sigmoid layer
decaf_net.add_layer(
    core_layers.SigmoidLayer(name='sigmoid2'),
    needs='ip2-out',
    provides='sigmoid2-out')
# The reconstruction loss function
decaf_net.add_layer(
    core_layers.SquaredLossLayer(name='loss'),
    needs=['sigmoid2-out', 'patches-flatten'])
# Finished running decaf_net.
decaf_net.finish()

# let's do a proof-of-concept run, and draw the graph network to file.
decaf_net.forward_backward()
visualize.draw_net_to_file(decaf_net, 'sparse-autoencoder-structure.png')

#############################################
# The optimization.
#############################################
logging.info('*** Calling LBFGS solver ***')
solver = core_solvers.LBFGSSolver(
    lbfgs_args={'maxfun': MAXFUN, 'disp': 1})
solver.solve(decaf_net)
# let's get the weight matrix and show it.
weight = decaf_net.layers['ip'].param()[0].data()
#visualize.show_multiple(weight.T)
decaf_net.save('sparse-autoencoder.decafnet')
#pyplot.show()


########NEW FILE########
__FILENAME__ = flask_main
"""The main routine that starts a imagenet demo."""
from decaf.scripts import imagenet
import datetime
import flask
from flask import Flask, url_for, request
import gflags
import logging
import numpy as np
import os
from PIL import Image as PILImage
from skimage import io
import cStringIO as StringIO
import sys
import time
import urllib
from werkzeug import secure_filename

# tornado
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

UPLOAD_FOLDER = '/tscratch/tmp/jiayq/decaf'
ALLOWED_IMAGE_EXTENSIONS = set(['png', 'bmp', 'jpg', 'jpe', 'jpeg', 'gif'])

gflags.DEFINE_string('net_file', '', 'The network file learned from cudaconv')
gflags.DEFINE_string('meta_file', '', 'The meta file for imagenet.')
gflags.DEFINE_string('upload_folder', UPLOAD_FOLDER, 'The folder to store the uploaded images.')
FLAGS = gflags.FLAGS

# Obtain the flask app object
app = Flask(__name__)

@app.route('/')
def index():
    return flask.render_template('index.html',
                                 has_result=False)

@app.route('/classify_url', methods=['GET'])
def classify_url():
    # classify image using the URL
    imageurl = request.args.get('imageurl', '')
    try:
        string_buffer = StringIO.StringIO(
            urllib.urlopen(imageurl).read())
        image = io.imread(string_buffer)
    except Exception as err:
        # For any exception we encounter in reading the image, we will just
        # not continue.
        logging.info('URL Image open error: %s', err)
        return flask.render_template('index.html',
                                     has_result=True,
                                     result=(False, 'Cannot open image from URL.'))
    logging.info('Image: %s', imageurl)
    result = classify_image(image)
    return flask.render_template('index.html',
                                 has_result=True,
                                 result=result,
                                 imagesrc=imageurl)

@app.route('/classify_upload', methods=['POST'])                                     
def classify_upload():
    # classify image using the image name
    try:
        # We will save the file to disk for possible data collection.
        imagefile = request.files['imagefile']
        filename = os.path.join(FLAGS.upload_folder,
                                str(datetime.datetime.now()).replace(' ', '_') + \
                                secure_filename(imagefile.filename))
        imagefile.save(filename)
        logging.info('Saving to %s.', filename)
        image = imagenet.DecafNet.extract(io.imread(filename)).astype(np.uint8)
    except Exception as err:
        logging.info('Uploaded mage open error: %s', err)
        return flask.render_template('index.html',
                                     has_result=True,
                                     result=(False, 'Cannot open uploaded image.'))
    result = classify_image(image)
    return flask.render_template('index.html',
                                 has_result=True,
                                 result=result,
                                 imagesrc=embed_image_html(image))

def embed_image_html(image):
    """Creates an image embedded in HTML base64 format."""
    image_pil = PILImage.fromarray(image)
    string_buf = StringIO.StringIO()
    image_pil.save(string_buf, format='png')
    data = string_buf.getvalue().encode('base64').replace('\n', '')
    return 'data:image/png;base64,' + data

@app.route('/about')
def about():
    return flask.render_template('about.html')

def allowed_file(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1] in ALLOWED_IMAGE_EXTENSIONS)

def classify_image(image):
    # let's classify the image.
    try:
        starttime = time.time()
        scores = app.net.classify(image)
        indices, predictions = app.net.top_k_prediction(scores, 5)
        # In addition to the prediction text, we will also produce the length
        # for the progress bar visualization.
        max_score = scores[indices[0]]
        meta = [(p, '%.5f' % scores[i]) for i, p in zip(indices, predictions)]
        logging.info('result: %s', str(meta))
    except Exception as err:
        logging.info('Classification error: %s', err)
        return (False, 'Oops, something wrong happened wieh classifying the'
                       ' image. Maybe try another one?')
    # If everything is successful, return the results
    endtime = time.time()
    return (True, meta, '%.3f' % (endtime-starttime))

if __name__ == '__main__':
    gflags.FLAGS(sys.argv)
    # try to make the upload directory.
    try:
        os.makedirs(UPLOAD_FOLDER)
    except Exception as err:
        pass
    logging.getLogger().setLevel(logging.INFO)
    app.net = imagenet.DecafNet(net_file=FLAGS.net_file,
                              meta_file=FLAGS.meta_file)
    #app.run(host='0.0.0.0')
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(5001)
    IOLoop.instance().start()


########NEW FILE########
__FILENAME__ = flask_service_is_down
"""A simple interface to show when the flask server is down for debugging."""
import flask
from flask import Flask, url_for, request

# Obtain the flask app object
app = Flask(__name__)

@app.route('/')
def index():
    return "Decaf is down for debugging. Please check back in a few minutes."

if __name__ == '__main__':
    app.run(host='0.0.0.0')

########NEW FILE########
__FILENAME__ = convolution
"""Implements the convolution layer."""

from decaf import base
from decaf.layers.cpp import wrapper
from decaf.util import blasdot
import numpy as np

class ConvolutionLayer(base.Layer):
    """A layer that implements the convolution function."""

    def __init__(self, **kwargs):
        """Initializes the convolution layer. Strictly, this is a correlation
        layer since the kernels are not reversed spatially as in a classical
        convolution operation.

        kwargs:
            name: the name of the layer.
            num_kernels: the number of kernels.
            ksize: the kernel size. Kernels will be square shaped and have the
                same number of channels as the data.
            stride: the kernel stride.
            mode: 'valid', 'same', or 'full'.
            pad: if set, this value will overwrite the mode and we will use 
                the given pad size. Default None.
            reg: the regularizer to be used to add regularization terms.
                should be a decaf.base.Regularizer instance. Default None. 
            filler: a filler to initialize the weights. Should be a
                decaf.base.Filler instance. Default None.
            has_bias: specifying if the convolutional network should have a
                bias term. Note that the same bias is going to be applied
                regardless of the location. Default True.
            bias_filler: a filler to unitialize the bias. Should be a
                decaf.base.Filler instance. Default None.
            large_mem: if set True, the layer will consume a lot of memory by
                storing all the intermediate im2col results, but will increase
                the backward operation time. Default False.
        When computing convolutions, we will always start from the top left
        corner, and any rows/columns on the right and bottom sides that do not
        fit the stride will be discarded. To enforce the 'same' mode to return
        results of the same size as the data, we require the 'same' mode to be
        paired with an odd number as the kernel size.
        """
        base.Layer.__init__(self, **kwargs)
        self._num_kernels = self.spec['num_kernels']
        self._ksize = self.spec['ksize']
        self._stride = self.spec['stride']
        self._large_mem = self.spec.get('large_mem', False)
        self._reg = self.spec.get('reg', None)
        self._has_bias = self.spec.get('has_bias', True)
        if self._ksize <= 1:
            raise ValueError('Invalid kernel size. Kernel size should > 1.')
        # since the im2col operation often creates large intermediate matrices,
        # we will process them in batches.
        self._padded = base.Blob()
        self._col = base.Blob()
        # set up the parameter
        self._kernels = base.Blob(filler=self.spec.get('filler', None))
        if self._has_bias:
            self._bias = base.Blob(filler=self.spec.get('bias_filler', None))
            self._param = [self._kernels, self._bias]
        else:
            self._param = [self._kernels]
        self._pad_size = self.spec.get('pad', None)
        if self._pad_size is None:
            self._mode = self.spec['mode']
            if self._mode == 'same' and self._ksize % 2 == 0:
                raise ValueError(
                    'The "same" mode should have an odd kernel size.')
            if self._mode == 'valid':
                self._pad_size = 0
            elif self._mode == 'full':
                self._pad_size = self._ksize - 1
            elif self._mode == 'same':
                self._pad_size = int(self._ksize / 2)
            else:
                raise ValueError('Unknown mode: %s' % self._mode)
    
    def forward(self, bottom, top):
        """Runs the forward pass."""
        bottom_data = bottom[0].data()
        if bottom_data.ndim != 4:
            raise ValueError('Bottom data should be a 4-dim tensor.')
        if not self._kernels.has_data():
            # initialize the kernels
            self._kernels.init_data(
                (self._ksize * self._ksize * bottom_data.shape[-1],
                 self._num_kernels),
                bottom_data.dtype)
            if self._has_bias:
                self._bias.init_data((self._num_kernels,), bottom_data.dtype)
        # pad the data
        if self._pad_size == 0:
            padded_data = self._padded.mirror(bottom_data)
        else:
            padded_data = self._padded.init_data(
                    (bottom_data.shape[0],
                     bottom_data.shape[1] + self._pad_size * 2,
                     bottom_data.shape[2] + self._pad_size * 2,
                     bottom_data.shape[3]),
                    bottom_data.dtype)
            padded_data[:, self._pad_size:-self._pad_size,
                        self._pad_size:-self._pad_size] = bottom_data
        # initialize self._col
        if self._large_mem:
            col_data_num = bottom_data.shape[0]
        else:
            col_data_num = 1
        col_data = self._col.init_data(
            (col_data_num,
             (padded_data.shape[1] - self._ksize) / self._stride + 1,
             (padded_data.shape[2] - self._ksize) / self._stride + 1,
             padded_data.shape[3] * self._ksize * self._ksize),
            padded_data.dtype, setdata=False)
        # initialize top data
        top_data = top[0].init_data(
            (bottom_data.shape[0], col_data.shape[1], col_data.shape[2],
             self._num_kernels), dtype=bottom_data.dtype, setdata=False)
        # process data individually
        if self._large_mem:
            wrapper.im2col_forward(padded_data, col_data,
                                   self._ksize, self._stride)
            blasdot.dot_lastdim(col_data, self._kernels.data(), out=top_data)
        else:
            for i in range(bottom_data.shape[0]):
                # call im2col individually
                wrapper.im2col_forward(padded_data[i:i+1], col_data,
                                       self._ksize, self._stride)
                blasdot.dot_lastdim(col_data, self._kernels.data(),
                                    out=top_data[i])
        if self._has_bias:
            top_data += self._bias.data()
        return

    def backward(self, bottom, top, propagate_down):
        """Runs the backward pass."""
        top_diff = top[0].diff()
        padded_data = self._padded.data()
        col_data = self._col.data()
        bottom_data = bottom[0].data()
        if bottom_data.ndim != 4:
            raise ValueError('Bottom data should be a 4-dim tensor.')
        kernel_diff = self._kernels.init_diff()
        if self._has_bias:
            bias_diff = self._bias.init_diff()
            # bias diff is fairly easy to compute: just sum over all other
            # dimensions
            np.sum(top_diff.reshape(top_diff.size / top_diff.shape[-1],
                                    top_diff.shape[-1]),
                   axis=0, out=bias_diff)
        if propagate_down:
            bottom_diff = bottom[0].init_diff(setzero=False)
            col_diff = self._col.init_diff()
            if self._pad_size == 0:
                padded_diff = self._padded.mirror_diff(bottom_diff)
            else:
                padded_diff = self._padded.init_diff(setzero=False)
        if self._large_mem:
            # we have the col_data all pre-stored, making things more efficient.
            blasdot.dot_firstdims(col_data, top_diff, out=kernel_diff)
            if propagate_down:
                blasdot.dot_lastdim(top_diff, self._kernels.data().T,
                                    out=col_diff)
                wrapper.im2col_backward(padded_diff, col_diff,
                                    self._ksize, self._stride)
        else:
            kernel_diff_buffer = np.zeros_like(kernel_diff)
            for i in range(bottom_data.shape[0]):
                # although it is a backward layer, we still need to compute
                # the intermediate results using forward calls.
                wrapper.im2col_forward(padded_data[i:i+1], col_data,
                                       self._ksize, self._stride)
                blasdot.dot_firstdims(col_data, top_diff[i],
                                     out=kernel_diff_buffer)
                kernel_diff += kernel_diff_buffer
                if propagate_down:
                    blasdot.dot_lastdim(top_diff[i], self._kernels.data().T,
                                        out=col_diff)
                    # im2col backward
                    wrapper.im2col_backward(padded_diff[i:i+1], col_diff,
                                            self._ksize, self._stride)
        # finally, copy results to the bottom diff.
        if propagate_down:
            if self._pad_size != 0:
                bottom_diff[:] = padded_diff[:,
                                             self._pad_size:-self._pad_size,
                                             self._pad_size:-self._pad_size]
        # finally, add the regularization term
        if self._reg is not None:
            return self._reg.reg(self._kernels, bottom_data.shape[0])
        else:
            return 0.

    def __getstate__(self):
        """When pickling, we will remove the intermediate data."""
        self._padded = base.Blob()
        self._col = base.Blob()
        return self.__dict__

    def update(self):
        """updates the parameters."""
        # Only the inner product layer needs to be updated.
        self._kernels.update()
        if self._has_bias:
            self._bias.update()


########NEW FILE########
__FILENAME__ = core_layers
# pylint: disable=W0611
"""Imports commonly used layers."""

# Utility layers
from decaf.base import SplitLayer

# Data Layers
from decaf.layers.data.ndarraydata import NdarrayDataLayer
from decaf.layers.data.cifar import CIFARDataLayer
from decaf.layers.data.mnist import MNISTDataLayer
from decaf.layers.sampler import (BasicMinibatchLayer,
                                  RandomPatchLayer)
from decaf.layers.puffsampler import PuffSamplerLayer

# Computation Layers
from decaf.layers.convolution import ConvolutionLayer
from decaf.layers.group_convolution import GroupConvolutionLayer
from decaf.layers.deconvolution import DeconvolutionLayer
from decaf.layers.dropout import DropoutLayer
from decaf.layers.flatten import FlattenLayer
from decaf.layers.identity import IdentityLayer
from decaf.layers.im2col import Im2colLayer
from decaf.layers.innerproduct import InnerProductLayer
from decaf.layers.loss import (SquaredLossLayer,
                               LogisticLossLayer,
                               MultinomialLogisticLossLayer,
                               KLDivergenceLossLayer,
                               AutoencoderLossLayer)
from decaf.layers.normalize import (MeanNormalizeLayer,
                                    ResponseNormalizeLayer,
                                    LocalResponseNormalizeLayer)
from decaf.layers.padding import PaddingLayer
from decaf.layers.pooling import PoolingLayer
from decaf.layers.relu import ReLULayer
from decaf.layers.sigmoid import SigmoidLayer
from decaf.layers.softmax import SoftmaxLayer

########NEW FILE########
__FILENAME__ = wrapper
# pylint: disable=C0103
"""This folder contains some c++ implementations that either make code run
faster or handles some numpy tricky issues.
"""
import ctypes as ct
import numpy as np
import os

# first, let's import the library
try:
    _DLL = np.ctypeslib.load_library('libcpputil.so',
            os.path.join(os.path.dirname(__file__)))
except Exception as error:
    raise error
try:
    _OMP_NUM_THREADS=int(os.environ['OMP_NUM_THREADS'])
except KeyError:
    try:
        import multiprocessing
        _OMP_NUM_THREADS=multiprocessing.cpu_count()
    except ImportError:
        _OMP_NUM_THREADS=1

################################################################################
# im2col operation
################################################################################
_DLL.im2col_forward.restype = _DLL.im2col_backward.restype = None

def im2col_forward(im, col, psize, stride):
    num, height, width, channels = im.shape
    _DLL.im2col_forward(ct.c_int(im.itemsize),
                im.ctypes.data_as(ct.c_void_p),
                col.ctypes.data_as(ct.c_void_p),
                ct.c_int(num),
                ct.c_int(height),
                ct.c_int(width),
                ct.c_int(channels),
                ct.c_int(psize),
                ct.c_int(stride))

def im2col_backward(im, col, psize, stride):
    num, height, width, channels = im.shape
    _DLL.im2col_backward(ct.c_int(im.itemsize),
                im.ctypes.data_as(ct.c_void_p),
                col.ctypes.data_as(ct.c_void_p),
                ct.c_int(num),
                ct.c_int(height),
                ct.c_int(width),
                ct.c_int(channels),
                ct.c_int(psize),
                ct.c_int(stride))

################################################################################
# pooling operation
################################################################################
_DLL.maxpooling_forward.restype = \
_DLL.maxpooling_backward.restype = \
_DLL.avepooling_forward.restype = \
_DLL.avepooling_backward.restype = None

def maxpooling_forward(image, pooled, psize, stride):
    num, height, width, channels = image.shape
    _DLL.maxpooling_forward(ct.c_int(image.itemsize),
                            image.ctypes.data_as(ct.c_void_p),
                            pooled.ctypes.data_as(ct.c_void_p),
                            ct.c_int(num),
                            ct.c_int(height),
                            ct.c_int(width),
                            ct.c_int(channels),
                            ct.c_int(psize),
                            ct.c_int(stride))

def avepooling_forward(image, pooled, psize, stride):
    num, height, width, channels = image.shape
    _DLL.avepooling_forward(ct.c_int(image.itemsize),
                            image.ctypes.data_as(ct.c_void_p),
                            pooled.ctypes.data_as(ct.c_void_p),
                            ct.c_int(num),
                            ct.c_int(height),
                            ct.c_int(width),
                            ct.c_int(channels),
                            ct.c_int(psize),
                            ct.c_int(stride))

def maxpooling_backward(image, pooled, image_diff, pooled_diff, psize,
                        stride):
    num, height, width, channels = image.shape
    _DLL.maxpooling_backward(ct.c_int(image.itemsize),
                             image.ctypes.data_as(ct.c_void_p),
                             pooled.ctypes.data_as(ct.c_void_p),
                             image_diff.ctypes.data_as(ct.c_void_p),
                             pooled_diff.ctypes.data_as(ct.c_void_p),
                             ct.c_int(num),
                             ct.c_int(height),
                             ct.c_int(width),
                             ct.c_int(channels),
                             ct.c_int(psize),
                             ct.c_int(stride))

def avepooling_backward(image_diff, pooled_diff, psize, stride):
    num, height, width, channels = image_diff.shape
    _DLL.avepooling_backward(ct.c_int(image_diff.itemsize),
                             image_diff.ctypes.data_as(ct.c_void_p),
                             pooled_diff.ctypes.data_as(ct.c_void_p),
                             ct.c_int(num),
                             ct.c_int(height),
                             ct.c_int(width),
                             ct.c_int(channels),
                             ct.c_int(psize),
                             ct.c_int(stride))



################################################################################
# local contrast normalization operation
################################################################################
_DLL.lrn_forward.restype = \
_DLL.lrn_backward.restype = None

def lrn_forward(bottom, top, scale, size, k, alpha, beta):
    _DLL.lrn_forward(ct.c_int(bottom.itemsize),
                     bottom.ctypes.data_as(ct.c_void_p),
                     top.ctypes.data_as(ct.c_void_p),
                     scale.ctypes.data_as(ct.c_void_p),
                     ct.c_int(bottom.size / bottom.shape[-1]),
                     ct.c_int(bottom.shape[-1]),
                     ct.c_int(size),
                     ct.c_double(k),
                     ct.c_double(alpha),
                     ct.c_double(beta),
                     ct.c_int(_OMP_NUM_THREADS))


def lrn_backward(bottom, top, bottom_diff, top_diff, scale, size, k, alpha,
                 beta):
    _DLL.lrn_backward(ct.c_int(bottom.itemsize),
                     bottom.ctypes.data_as(ct.c_void_p),
                     top.ctypes.data_as(ct.c_void_p),
                     bottom_diff.ctypes.data_as(ct.c_void_p),
                     top_diff.ctypes.data_as(ct.c_void_p),
                     scale.ctypes.data_as(ct.c_void_p),
                     ct.c_int(bottom.size / bottom.shape[-1]),
                     ct.c_int(bottom.shape[-1]),
                     ct.c_int(size),
                     ct.c_double(k),
                     ct.c_double(alpha),
                     ct.c_double(beta),
                     ct.c_int(_OMP_NUM_THREADS))

################################################################################
# local contrast normalization operation
################################################################################
_DLL.relu_forward.restype = None

def relu_forward(bottom, top):
    _DLL.relu_forward(ct.c_int(bottom.itemsize),
                      bottom.ctypes.data_as(ct.c_void_p),
                      top.ctypes.data_as(ct.c_void_p),
                      ct.c_int(bottom.size))

########NEW FILE########
__FILENAME__ = cifar
'''The Cifar dataset 
'''
import cPickle as pickle
from decaf.layers.data import ndarraydata
import numpy as np
import os


class CIFARDataLayer(ndarraydata.NdarrayDataLayer):
    """The CIFAR dataset
    """
    # some cifar constants
    __num_train = 50000
    __num_batches = 5 # for cifar 10
    __batchsize = 10000 # for cifar 10
    __num_test = 10000
    __image_dim = (32, 32, 3)
    __num_channels = 3
    __image_size = 1024
    __flat_dim = 3072
    
    def __init__(self, **kwargs):
        """Initializes the cifar layer.

        kwargs:
            is_training: whether to load the training data. Default True.
            is_gray: whether to load gray image. Default False.
            rootfolder: the folder that stores the mnist data.
            dtype: the data type. Default numpy.float64.
        """
        # get keywords
        is_training = kwargs.get('is_training', True)
        is_gray = kwargs.get('is_gray', False)
        rootfolder = kwargs['rootfolder']
        dtype = kwargs.get('dtype', np.float64)
        self._data = None
        self._label = None
        self._coarselabel = None
        # we will automatically determine if the data is cifar-10 or cifar-100
        if os.path.exists(os.path.join(rootfolder, 'batches.meta')):
            self.load_cifar10(rootfolder, is_training, dtype)
        elif os.path.exists(os.path.join(rootfolder, 'meta')):
            self.load_cifar100(rootfolder, is_training, dtype)
        else:
            raise IOError, 'Cannot understand the dataset format.'
        if is_gray:
            self._data = self._data.mean(axis=-1)
        # Normalize data to [0, 1)
        self._data /= 255.
        # Initialize as an NdarrayDataLayer
        ndarraydata.NdarrayDataLayer.__init__(
            self, sources=[self._data, self._label], **kwargs)
        
    @staticmethod
    def _get_images_from_matrix(mat, dtype):
        """Converts the order of the loaded matrix so each pixel is stored
        contiguously
        """
        mat = mat.reshape((mat.shape[0],
                           CIFARDataLayer.__num_channels,
                           CIFARDataLayer.__image_size))
        images = mat.swapaxes(1, 2).reshape(
            (mat.shape[0],) + CIFARDataLayer.__image_dim)
        return np.ascontiguousarray(images.astype(dtype))
    
    def load_cifar100(self, rootfolder, is_training, dtype):
        """loads the cifar-100 dataset
        """
        if is_training:
            filename = 'train'
        else:
            filename = 'test'
        with open(rootfolder + os.sep + filename) as fid:
            batch = pickle.load(fid)
        self._data = CIFARDataLayer._get_images_from_matrix(
            batch['data'], dtype)
        self._coarselabel = np.array(batch['coarse_labels']).astype(np.int)
        self._label = np.array(batch['fine_labels']).astype(np.int)
    
    def load_cifar10(self, rootfolder, is_training, dtype):
        """loads the cifar-10 dataset
        """
        if is_training:
            self._data = np.empty(
                (CIFARDataLayer.__num_train,) + CIFARDataLayer.__image_dim,
                dtype=dtype)
            self._label = np.empty(CIFARDataLayer.__num_train, dtype=np.int)
            # training batches
            for i in range(CIFARDataLayer.__num_batches):
                with open(os.path.join(rootfolder,
                        'data_batch_{0}'.format(i+1)),'r') as fid:
                    batch = pickle.load(fid)
                start_idx = CIFARDataLayer.__batchsize * i
                end_idx = CIFARDataLayer.__batchsize * (i+1)
                self._data[start_idx:end_idx] = \
                    CIFARDataLayer._get_images_from_matrix(batch['data'], dtype)
                self._label[start_idx:end_idx] = np.array(batch['labels'])
        else:
            with open(os.path.join(rootfolder, 'test_batch'), 'r') as fid:
                batch = pickle.load(fid)
            self._data = CIFARDataLayer._get_images_from_matrix(
                batch['data'], dtype)
            self._label = np.array(batch['labels']).astype(np.int)


########NEW FILE########
__FILENAME__ = cub
"""The Caltech-UCSD bird dataset
"""

from decaf.layers.data import ndarraydata
import numpy as np
import os
from scipy import misc
from skimage import io


class CUBDataLayer(ndarraydata.NdarrayDataLayer):
    """ The Caltech-UCSD bird dataset
    """
    def __init__(self, **kwargs):
        """Load the dataset.
        kwargs:
            root: the root folder of the CUB_200_2011 dataset.
            is_training: if true, load the training data. Otherwise, load the
                testing data.
            crop: if None, does not crop the bounding box. If a real value,
                crop is the ratio of the bounding box that gets cropped.
                e.g., if crop = 1.5, the resulting image will be 1.5 * the
                bounding box area.
            target_size: all images are resized to the size specified. Should
                be a tuple of two integers, like [256, 256].
            version: either '2011' or '2010'.
        Note that we will use the python indexing (labels start from 0).
        """
        root = kwargs['root']
        is_training = kwargs.get('is_training', True)
        crop = kwargs.get('crop', None)
        target_size = kwargs['target_size']
        version = kwargs.get('version', '2011')
        if version == '2011':
            images = [line.split()[1] for line in
                        open(os.path.join(root, 'images.txt'), 'r')]
            boxes = [line.split()[1:] for line in
                        open(os.path.join(root, 'bounding_boxes.txt'),'r')]
            labels = [int(line.split()[1]) - 1 for line in 
                        open(os.path.join(root, 'image_class_labels.txt'), 'r')]
            birdnames = [line.split()[1] for line in
                          open(os.path.join(root, 'classes.txt'), 'r')]
            name_to_id = dict(zip(birdnames, range(len(birdnames))))
            split = [int(line.split()[1]) for line in
                        open(os.path.join(root, 'train_test_split.txt'),'r')]
        elif version == '2010':
            # we are using version 2010. We load the data to mimic the 2011
            # version data format
            images = [line.strip() for line in
                        open(os.path.join(root, 'lists', 'files.txt'), 'r')]
            boxes = []
            # unfortunately, we need to load the boxes from matlab annotations
            for filename in images:
                matfile = io.loadmat(os.path.join(root, 'annotations-mat',
                                                  filename[:-3]+'mat'))
                left, top, right, bottom = \
                        [matfile['bbox'][0][0][i][0][0] for i in range(4)]
                boxes.append([left, top, right-left, bottom-top])
            # get the training and testing split.
            train_images = [line.strip() for line in
                        open(os.path.join(root, 'lists', 'train.txt'), 'r')]
            labels = [int(line[:line.find('.')]) - 1 for line in images]
            birdnames = [line.strip() for line in
                        open(os.path.join(root, 'lists', 'classes.txt'),'r')]
            name_to_id = dict(zip(birdnames, range(len(birdnames))))
            split = [int(line in train_images) for line in images]
        else:
            raise ValueError, "Unrecognized version: %s" % version
        # now, do training testing split
        if is_training:
            target = 1
        else:
            target = 0
        images = [image for image, val in zip(images, split) if val == target]
        boxes = [box for box, val in zip(boxes, split) if val == target]
        label = [label for label, val in zip(labels, split) if val == target]
        # for the boxes, we store them as a numpy array
        boxes = np.array(boxes, dtype=np.float32)
        boxes -= 1
        # load the data
        self._data = None
        self._load_data(root, images, boxes, crop, target_size)
        self._label = np.asarray(label, dtype=np.int)
        ndarraydata.NdarrayDataLayer.__init__(
            self, sources=[self._data, self._label], **kwargs)

    def _load_data(self, root, images, boxes, crop, target_size):
        num_imgs = len(images)
        self._data = np.empty((num_imgs, target_size[0], target_size[1], 3),
                              dtype=np.uint8)
        for i in range(num_imgs):
            image = io.imread(os.path.join(root, 'images', images[i]))
            if image.ndim == 2:
                image = np.tile(image[:,:,np.newaxis], (1, 1, 3))
            if image.shape[2] == 4:
                image = image[:, :, :3]
            if crop:
                image = self._crop_image(image, crop, boxes[i])
            self._data[i] = misc.imresize(image, target_size)
        return

    def _crop_image(self, image, crop, box):
        imheight, imwidth = image.shape[:2]
        x, y, width, height = box
        centerx = x + width / 2.
        centery = y + height / 2.
        xoffset = width * crop / 2.
        yoffset = height * crop / 2.
        xmin = max(int(centerx - xoffset + 0.5), 0)
        ymin = max(int(centery - yoffset + 0.5), 0)
        xmax = min(int(centerx + xoffset + 0.5), imwidth - 1)
        ymax = min(int(centery + yoffset + 0.5), imheight - 1)
        if xmax - xmin <= 0 or ymax - ymin <= 0:
            raise ValueError("The cropped bounding box has size 0.")
        return image[ymin:ymax, xmin:xmax]

########NEW FILE########
__FILENAME__ = mnist
'''The MNIST dataset 
'''
from decaf.layers.data import ndarraydata
import numpy as np
import os

class MNISTDataLayer(ndarraydata.NdarrayDataLayer):
    NUM_TRAIN = 60000
    NUM_TEST = 10000
    IMAGE_DIM = (28,28)
    
    def __init__(self, **kwargs):
        """Initialize the mnist dataset.
        
        kwargs:
            is_training: whether to load the training data. Default True.
            rootfolder: the folder that stores the mnist data.
            dtype: the data type. Default numpy.float64.
        """
        is_training = kwargs.get('is_training', True)
        rootfolder = kwargs['rootfolder']
        dtype = kwargs.get('dtype', np.float64)
        self._load_mnist(rootfolder, is_training, dtype)
        # normalize data.
        self._data /= 255.
        ndarraydata.NdarrayDataLayer.__init__(
            self, sources=[self._data, self._label], **kwargs)

    def _load_mnist(self, rootfolder, is_training, dtype):
        if is_training:
            self._data = self._read_byte_data(
                    os.path.join(rootfolder,'train-images-idx3-ubyte'), 
                    16, (MNISTDataLayer.NUM_TRAIN,) + \
                            MNISTDataLayer.IMAGE_DIM).astype(dtype)
            self._label = self._read_byte_data(
                    os.path.join(rootfolder,'train-labels-idx1-ubyte'),
                    8, [MNISTDataLayer.NUM_TRAIN]).astype(np.int)
        else:
            self._data = self._read_byte_data(
                    os.path.join(rootfolder,'t10k-images-idx3-ubyte'),
                    16, (MNISTDataLayer.NUM_TEST,) + \
                            MNISTDataLayer.IMAGE_DIM).astype(dtype)
            self._label = self._read_byte_data(
                    os.path.join(rootfolder,'t10k-labels-idx1-ubyte'),
                    8, [MNISTDataLayer.NUM_TEST]).astype(np.int)
        # In the end, we will make the data 4-dimensional (num * 28 * 28 * 1)
        self._data.resize(self._data.shape + (1,))

    def _read_byte_data(self, filename, skipbytes, shape):
        fid = open(filename, 'rb')
        fid.seek(skipbytes)
        nbytes = np.prod(shape)
        data = np.fromfile(fid, dtype=np.uint8, count=nbytes)
        data.resize(shape)
        return data

########NEW FILE########
__FILENAME__ = ndarraydata
"""A simple ndarray data layer that wraps around numpy arrays."""

from decaf import base

class NdarrayDataLayer(base.DataLayer):
    """This layer takes a bunch of data as a dictionary, and then emits
    them as Blobs.
    """
    
    def __init__(self, **kwargs):
        """Initialize the data layer. The input matrices will be provided
        by keyword 'sources' as a list of Ndarrays, like
            sources = [array_1, array_2].
        The number of arrays should be identical to the number of output
        blobs.
        """
        base.DataLayer.__init__(self, **kwargs)
        self._sources = self.spec['sources']

    def forward(self, bottom, top):
        """Generates the data."""
        if len(top) != len(self._sources):
            raise ValueError('The number of sources and '
                             'output blobs should be the same.')
        for top_blob, source in zip(top, self._sources):
            top_blob.mirror(source)


########NEW FILE########
__FILENAME__ = deconvolution
"""Implements the convolution layer."""

from decaf import base
from decaf.layers.cpp import wrapper
from decaf.util import blasdot
import numpy as np

# pylint: disable=R0902
class DeconvolutionLayer(base.Layer):
    """A layer that implements the deconvolution function: it is the inverse
    as the convolution operation.
    """

    def __init__(self, **kwargs):
        """Initializes the deconvolution layer. Strictly, this is a correlation
        layer since the kernels are not reversed spatially as in a classical
        convolution operation.

        kwargs:
            name: the name of the layer.
            num_channels: the number of output channels.
            ksize: the kernel size. Kernels will be square shaped and have the
                same number of channels as the data.
            stride: the kernel stride.
            mode: 'valid', 'same', or 'full'. The modes represent the corres-
                ponding convolution operation.
            reg: the regularizer to be used to add regularization terms.
                should be a decaf.base.Regularizer instance. Default None. 
            filler: a filler to initialize the weights. Should be a
                decaf.base.Filler instance. Default None.
        """
        base.Layer.__init__(self, **kwargs)
        self._num_channels = self.spec['num_channels']
        self._ksize = self.spec['ksize']
        self._stride = self.spec['stride']
        self._mode = self.spec['mode']
        self._reg = self.spec.get('reg', None)
        self._filler = self.spec.get('filler', None)
        self._memory = self.spec.get('memory', 1e7)
        if self._ksize <= 1:
            raise ValueError('Invalid kernel size. Kernel size should > 1.')
        if self._mode == 'same' and self._ksize % 2 == 0:
            raise ValueError('The "same" mode should have an odd kernel size.')
        # since the im2col operation often creates large intermediate matrices,
        # we will have intermediate blobs to store them.
        self._padded = base.Blob()
        self._col = base.Blob()
        # set up the parameter
        self._kernels = base.Blob(filler=self._filler)
        self._param = [self._kernels]
        # compute the border.
        if self._mode == 'valid':
            self._border = 0
        elif self._mode == 'same':
            self._border = self._ksize / 2
        elif self._mode == 'full':
            self._border = self._ksize - 1

    def forward(self, bottom, top):
        """Runs the forward pass."""
        bottom_data = bottom[0].data()
        if bottom_data.ndim != 4:
            raise ValueError('Bottom data should be a 4-dim tensor.')
        if not self._kernels.has_data():
            # initialize the kernels
            self._kernels.init_data(
                (bottom_data.shape[-1],
                 self._ksize * self._ksize * self._num_channels),
                bottom_data.dtype)
        # initialize the buffers.
        self._col.init_data((1, bottom_data.shape[1], bottom_data.shape[2],
                             self._kernels.data().shape[1]),
                            dtype = bottom_data.dtype)
        pad_height = self._ksize + (bottom_data.shape[1] - 1) \
                * self._stride
        pad_width = self._ksize + (bottom_data.shape[2] - 1) \
                * self._stride
        if self._mode != 'valid':
            padded_data = self._padded.init_data(
                (1, pad_height, pad_width, self._num_channels),
                dtype = bottom_data.dtype)
        top_data = top[0].init_data(
            (bottom_data.shape[0], pad_height - self._border * 2,
             pad_width - self._border * 2, self._num_channels),
            dtype=bottom_data.dtype)
        # process data individually
        for i in range(bottom_data.shape[0]):
            # first, compute the convolution as a gemm operation
            blasdot.dot_lastdim(bottom_data[i:i+1], self._kernels.data(),
                                out=self._col.data())
            if self._mode != 'valid':
            # do col2im
                wrapper.im2col_backward(padded_data, self._col.data(),
                               self._ksize, self._stride)
                top_data[i] = padded_data[0, self._border:-self._border,
                                          self._border:-self._border]
            else:
                wrapper.im2col_backward(top_data[i:i+1], self._col.data(),
                                        self._ksize, self._stride)
        return

    def backward(self, bottom, top, propagate_down):
        """Runs the backward pass."""
        top_diff = top[0].diff()
        bottom_data = bottom[0].data()
        kernel_diff = self._kernels.init_diff()
        kernel_diff_buffer = np.zeros_like(kernel_diff)
        col_diff = self._col.init_diff()
        if propagate_down:
            bottom_diff = bottom[0].init_diff()
        if self._mode != 'valid':
            pad_diff = self._padded.init_diff()
        for i in range(bottom_data.shape[0]):
            if self._mode != 'valid':
                # do padding
                pad_diff[0, self._border:-self._border,
                         self._border:-self._border] = top_diff[i]
            else:
                pad_diff = top_diff[i:i+1].view()
            # run im2col
            wrapper.im2col_forward(pad_diff, col_diff, self._ksize,
                                   self._stride)
            blasdot.dot_firstdims(bottom_data[i], col_diff,
                                 out=kernel_diff_buffer)
            kernel_diff += kernel_diff_buffer
            if propagate_down:
                # compute final gradient
                blasdot.dot_lastdim(col_diff, self._kernels.data().T,
                                    out=bottom_diff[i])
        # finally, add the regularization term
        if self._reg is not None:
            return self._reg.reg(self._kernels, bottom_data.shape[0])
        else:
            return 0.

    def __getstate__(self):
        """When pickling, we will remove the intermediate data."""
        self._padded = base.Blob()
        self._col = base.Blob()
        return self.__dict__

    def update(self):
        """updates the parameters."""
        # Only the inner product layer needs to be updated.
        self._kernels.update()


########NEW FILE########
__FILENAME__ = dropout
"""Implements the dropout layer."""

from decaf import base
from decaf.layers import fillers
import numpy as np

class DropoutLayer(base.Layer):
    """A layer that implements the dropout.
    
    To increase test time efficiency, what we do in dropout is slightly
    different from the original version: instead of scaling during testing
    time, we scale up at training time so testing time is simply a mirroring
    operation.
    """

    def __init__(self, **kwargs):
        """Initializes a Dropout layer.

        kwargs:
            name: the layer name.
            ratio: the ratio to carry out dropout.
            debug_freeze: a debug flag. If set True, the mask will only
                be generated once when running. You should not use it other
                than purposes like gradient check.
        """
        base.Layer.__init__(self, **kwargs)
        filler = fillers.DropoutFiller(ratio=self.spec['ratio'])
        self._mask = base.Blob(filler=filler)

    def forward(self, bottom, top):
        """Computes the forward pass."""
        # Get features and output
        features = bottom[0].data()
        output = top[0].init_data(features.shape, features.dtype, setdata=False)
        if not self._mask.has_data():
            mask = self._mask.init_data(features.shape, np.bool)
        elif self.spec.get('debug_freeze', False):
            mask = self._mask.data()
        else:
            mask = self._mask.init_data(features.shape, np.bool)
        upscale = 1. / self.spec['ratio']
        output[:] = features * mask
        output *= upscale

    def predict(self, bottom, top):
        """The dropout predict pass. Under our definition, it is simply a
        mirror operation.
        """
        top[0].mirror(bottom[0])

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if not propagate_down:
            return 0.
        top_diff = top[0].diff()
        bottom_diff = bottom[0].init_diff(setzero=False)
        mask = self._mask.data()
        upscale = 1. / self.spec['ratio']
        bottom_diff[:] = top_diff * mask
        bottom_diff *= upscale
        return 0.

    def update(self):
        """Dropout has nothing to update."""
        pass

########NEW FILE########
__FILENAME__ = fillers
"""Implements basic fillers."""

from decaf import base
import numpy as np


# pylint: disable=R0903
class ConstantFiller(base.Filler):
    """Fills the values with a constant value.
    
    kwargs:
        value: the constant value to fill.
    """
    def fill(self, mat):
        """The fill function."""
        mat[:] = self.spec['value']


# pylint: disable=R0903
class RandFiller(base.Filler):
    """Fills the values with random numbers in [min, max).
    
    kwargs:
        min: the min value (default 0).
        max: the max value (default 1).
    """
    def fill(self, mat):
        """The fill function."""
        minval = self.spec.get('min', 0)
        maxval = self.spec.get('max', 1)
        mat[:] = np.random.random_sample(mat.shape)
        mat *= maxval - minval
        mat += minval

# pylint: disable=R0903
class RandIntFiller(base.Filler):
    """Fills the values with random numbers in [min, max).
    
    kwargs:
        low: the min value (default 0).
        high: the max value. Must be given.
    """
    def fill(self, mat):
        """The fill function."""
        lowval = self.spec.get('low', 0)
        highval = self.spec['high']
        mat[:] = np.random.randint(low=lowval, high=highval, size=mat.shape)

# pylint: disable=R0903
class GaussianRandFiller(base.Filler):
    """Fills the values with random gaussian.
    
    kwargs:
        mean: the mean value (default 0).
        std: the standard deviation (default 1).
    """
    def fill(self, mat):
        """The fill function."""
        mean = self.spec.get('mean', 0.)
        std = self.spec.get('std', 1.)
        mat[:] = np.random.standard_normal(mat.shape)
        mat *= std
        mat += mean

# pylint: disable=R0903
class DropoutFiller(base.Filler):
    """Fills the values with boolean.

    kwargs:
        ratio: the ratio of 1 values when generating random binaries.
    """
    def fill(self, mat):
        """The fill function."""
        ratio = self.spec['ratio']
        mat[:] = np.random.random_sample(mat.shape) < ratio


# pylint: disable=R0903
class XavierFiller(base.Filler):
    """A filler based on the paper [Bengio and Glorot 2010]: Understanding
    the difficulty of training deep feedforward neuralnetworks, but does not
    use the fan_out value.

    It fills the incoming matrix by randomly sampling uniform data from
    [-scale, scale] where scale = sqrt(3 / fan_in) where fan_in is the number
    of input nodes respectively. The code finds out fan_in as
        mat.size / mat.shape[-1]
    and you should make sure the matrix is at least 2-dimensional.
    """
    def fill(self, mat):
        """The fill function."""
        scale = np.sqrt(3. / float(mat.size / mat.shape[-1]))
        mat[:] = np.random.random_sample(mat.shape)
        mat *= scale * 2.
        mat -= scale


# pylint: disable=R0903
class XavierGaussianFiller(base.Filler):
    """A filler that is similar to XavierFiller, but uses a Gaussian
    distribution that has the same standard deviation as the XavierFiller
    has for the uniform distribution.
    """
    def fill(self, mat):
        """The fill function."""
        std = np.sqrt(1. / float(mat.size / mat.shape[-1]))
        mat[:] = np.random.standard_normal(mat.shape)
        mat *= std


# pylint: disable=R0903
class InverseStdFiller(base.Filler):
    """A filler that initializes the weights using standard deviation 
        1 / fan_in 
    where fan_in is computed as mat.size / mat.shape[-1].
    """
    def fill(self, mat):
        """The fill function."""
        std = 1. / float(mat.size / mat.shape[-1])
        mat[:] = np.random.standard_normal(mat.shape)
        mat *= std

########NEW FILE########
__FILENAME__ = flatten
"""Implements the flatten layer."""

from decaf import base
import numpy as np

class FlattenLayer(base.Layer):
    """A layer that flattens the data to a 1-dim vector (the resulting
    minibatch would be a 2-dim matrix."""

    def forward(self, bottom, top):
        """Computes the forward pass."""
        for blob_b, blob_t in zip(bottom, top):
            shape = blob_b.data().shape
            newshape = (shape[0], np.prod(shape[1:]))
            blob_t.mirror(blob_b, shape=newshape)

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if propagate_down:
            for blob_b, blob_t in zip(bottom, top):
                blob_b.mirror_diff(blob_t, shape=blob_b.data().shape)
        return 0.

    def update(self):
        """FlattenLayer has nothing to update."""
        pass

########NEW FILE########
__FILENAME__ = group_convolution
"""Implements the convolution layer."""

from decaf import base
from decaf.layers import convolution

class GroupConvolutionLayer(base.Layer):
    """A layer that implements the block group convolution function."""

    def __init__(self, **kwargs):
        """Initializes the convolution layer. Strictly, this is a correlation
        layer since the kernels are not reversed spatially as in a classical
        convolution operation.

        kwargs:
            name: the name of the layer.
            group: the number of groups that should be carried out for the
                block group convolution. Note that the number of channels of
                the incoming block should be divisible by the number of groups,
                otherwise we will have an error produced.
            num_kernels: the number of kernels PER GROUP. As a result, the
                output would have (num_kernels * group) channels.
        Also the layer should be provided all the appropriate parameters for
        the underlying convolutional layer.
        """
        base.Layer.__init__(self, **kwargs)
        self._group = self.spec['group']
        self._conv_args = dict(self.spec)
        self._conv_args['name'] = self.spec['name'] + '_sub'
        del self._conv_args['group']
        self._bottom_sub = [base.Blob() for _ in range(self._group)]
        self._top_sub = [base.Blob() for _ in range(self._group)]
        self._conv_layers = None
        self._blocksize = 0
        self._num_kernels = self.spec['num_kernels']
        # create the convolution layers
        self._conv_layers = [
            convolution.ConvolutionLayer(**self._conv_args)
            for i in range(self._group)]
        self._param = sum((layer.param() for layer in self._conv_layers), [])
        return

    def forward(self, bottom, top):
        """Runs the forward pass."""
        bottom_data = bottom[0].data()
        if bottom_data.ndim != 4:
            raise ValueError('Bottom data should be a 4-dim tensor.')
        if bottom_data.shape[-1] % self._group:
            raise RuntimeError('The number of input channels (%d) should be'
                               ' divisible by the number of groups (%d).' %
                               (bottom_data.shape[-1], self._group))
        self._blocksize = bottom_data.shape[-1] / self._group
        for i in range(self._group):
            in_start = i * self._blocksize
            in_end = in_start + self._blocksize
            out_start = i * self._num_kernels
            out_end = out_start + self._num_kernels
            # Now, create intermediate blobs, and compute forward by group
            bottom_sub_data = self._bottom_sub[i].init_data(
                bottom_data.shape[:-1] + (self._blocksize,),
                bottom_data.dtype, setdata=False)
            bottom_sub_data[:] = bottom_data[:, :, :, in_start:in_end]
            self._conv_layers[i].forward([self._bottom_sub[i]],
                                         [self._top_sub[i]])
            top_sub_data = self._top_sub[i].data()
            if i == 0:
                top_data = top[0].init_data(
                    top_sub_data.shape[:-1] + \
                    (top_sub_data.shape[-1] * self._group,),
                    top_sub_data.dtype, setdata=False)
            top_data[:, :, :, out_start:out_end] = top_sub_data
        return

    def backward(self, bottom, top, propagate_down):
        """Runs the backward pass."""
        loss = 0.
        top_diff = top[0].diff()
        bottom_data = bottom[0].data()
        # initialize the sub diff
        if propagate_down:
            bottom_diff = bottom[0].init_diff(setzero=False)
        for i in range(self._group):
            top_sub_diff = self._top_sub[i].init_diff(setzero=False)
            bottom_sub_data = self._bottom_sub[i].data()
            in_start = i * self._blocksize
            in_end = in_start + self._blocksize
            out_start = i * self._num_kernels
            out_end = out_start + self._num_kernels
            # Since the convolutional layers will need the input data,
            # we will need to provide them.
            bottom_sub_data[:] = bottom_data[:, :, :, in_start:in_end]
            top_sub_diff[:] = top_diff[:, :, :, out_start:out_end]
            loss += self._conv_layers[i].backward(
                [self._bottom_sub[i]], [self._top_sub[i]], propagate_down)
            if propagate_down:
                bottom_sub_diff = self._bottom_sub[i].init_diff(setzero=False)
                bottom_diff[:, :, :, in_start:in_end] = bottom_sub_diff
        return loss

    def __getstate__(self):
        """When pickling, we will remove the intermediate data."""
        self._bottom_sub = [base.Blob() for _ in range(self._group)]
        self._top_sub = [base.Blob() for _ in range(self._group)]
        return self.__dict__
    
    def update(self):
        """updates the parameters."""
        for layer in self._conv_layers:
            layer.update()

########NEW FILE########
__FILENAME__ = identity
"""Implements a dummy identity layer."""

from decaf import base

class IdentityLayer(base.Layer):
    """A layer that does nothing but mirroring things."""

    def __init__(self, **kwargs):
        """Initializes an identity layer.

        kwargs:
            name: the layer name.
        """
        base.Layer.__init__(self, **kwargs)

    def forward(self, bottom, top):
        """Computes the forward pass."""
        for top_blob, bottom_blob in zip(top, bottom):
            top_blob.mirror(bottom_blob)

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if not propagate_down:
            return 0.
        for top_blob, bottom_blob in zip(top, bottom):
            bottom_blob.mirror_diff(top_blob)
        return 0.

    def update(self):
        """Identity Layer has nothing to update."""
        pass

########NEW FILE########
__FILENAME__ = im2col
"""Implements the im2col layer."""

from decaf import base
from decaf.layers.cpp import wrapper

class Im2colLayer(base.Layer):
    """A layer that implements the im2col function."""

    def __init__(self, **kwargs):
        """Initializes an im2col layer.

        kwargs:
            name: the name of the layer.
            psize: the patch size (patch will be a square).
            stride: the patch stride.

        If the input image has shape [height, width, nchannels], the output
        will have shape [(height-psize)/stride+1, (width-psize)/stride+1,
        nchannels * psize * psize].
        """
        base.Layer.__init__(self, **kwargs)
        self._psize = self.spec['psize']
        self._stride = self.spec['stride']
        if self._psize <= 1:
            raise ValueError('Padding should be larger than 1.')
        if self._stride < 1:
            raise ValueError('Stride should be larger than 0.')

    def _get_new_shape(self, features):
        """Gets the new shape of the im2col operation."""
        if features.ndim != 4:
            raise ValueError('Input features should be 4-dimensional.')
        num, height, width, channels = features.shape
        return (num,
                (height - self._psize) / self._stride + 1,
                (width - self._psize) / self._stride + 1,
                channels * self._psize * self._psize)

    def forward(self, bottom, top):
        """Computes the forward pass."""
        # Get features and output
        features = bottom[0].data()
        output = top[0].init_data(self._get_new_shape(features),
                                  features.dtype, setdata=False)
        wrapper.im2col_forward(features, output, self._psize, self._stride)

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if not propagate_down:
            return 0.
        top_diff = top[0].diff()
        bottom_diff = bottom[0].init_diff(setzero=False)
        wrapper.im2col_backward(bottom_diff, top_diff, self._psize,
                                self._stride)
        return 0.

    def update(self):
        """Im2col has nothing to update."""
        pass

########NEW FILE########
__FILENAME__ = innerproduct
"""Implements the inner product layer."""

from decaf import base
from decaf.util import blasdot
import numpy as np

class InnerProductLayer(base.Layer):
    """A layer that implements the inner product."""

    def __init__(self, **kwargs):
        """Initializes an inner product layer. 
        
        kwargs:
            num_output: the number of outputs.
            reg: the regularizer to be used to add regularization terms.
                should be a decaf.base.Regularizer instance. Default None. 
            filler: a filler to initialize the weights. Should be a
                decaf.base.Filler instance. Default None.
            bias_filler: a filler to initialize the bias.
            bias: if True, the inner product will contain a bias term.
                Default True.
        """
        base.Layer.__init__(self, **kwargs)
        self._num_output = self.spec.get('num_output', 0)
        if self._num_output <= 0:
            raise base.InvalidLayerError(
                'Incorrect or unspecified num_output for %s' % self.name)
        self._reg = self.spec.get('reg', None)
        self._filler = self.spec.get('filler', None)
        self._weight = base.Blob(filler=self._filler)
        self._has_bias = self.spec.get('bias', True)
        if self._has_bias:
            self._bias_filler = self.spec.get('bias_filler', None)
            self._bias = base.Blob(filler=self._bias_filler)
            self._param = [self._weight, self._bias]
        else:
            self._param = [self._weight]
    
    def forward(self, bottom, top):
        """Computes the forward pass."""
        # Get features and output
        features = bottom[0].data()
        output = top[0].init_data(
            features.shape[:-1] + (self._num_output,), features.dtype,
            setdata=False)
        # initialize weights
        if not self._weight.has_data():
            self._weight.init_data(
                (features.shape[-1], self._num_output), features.dtype)
        if self._has_bias and not self._bias.has_data():
            self._bias.init_data((self._num_output), features.dtype)
        # computation
        weight = self._weight.data()
        blasdot.dot_lastdim(features, weight, out=output)
        if self._has_bias:
            output += self._bias.data()

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        # get diff
        top_diff = top[0].diff()
        features = bottom[0].data()
        # compute the gradient
        weight_diff = self._weight.init_diff(setzero=False)
        blasdot.dot_firstdims(features, top_diff, out=weight_diff)
        if self._has_bias:
            bias_diff = self._bias.init_diff(setzero=False)
            bias_diff[:] = top_diff.reshape(
                np.prod(top_diff.shape[:-1]), top_diff.shape[-1]).sum(0)
        # If necessary, compute the bottom Blob gradient.
        if propagate_down:
            bottom_diff = bottom[0].init_diff(setzero=False)
            blasdot.dot_lastdim(top_diff, self._weight.data().T,
                                out=bottom_diff)
        if self._reg is not None:
            return self._reg.reg(self._weight)
        else:
            return 0.

    def update(self):
        """Updates the parameters."""
        self._weight.update()
        if self._has_bias:
            self._bias.update()


########NEW FILE########
__FILENAME__ = loss
"""Implements common loss functions.
"""

from decaf import base
from decaf.util import logexp
import numpy as np
import numexpr

class SquaredLossLayer(base.LossLayer):
    """The squared loss. Following conventions, we actually compute
    the one-half of the squared loss.
    """
    def forward(self, bottom, top):
        """Forward emits the loss, and computes the gradient as well."""
        diff = bottom[0].init_diff(setzero=False)
        diff[:] = bottom[0].data()
        diff -= bottom[1].data()
        self._loss = np.dot(diff.flat, diff.flat) / 2. / diff.shape[0] \
                * self.spec['weight']
        diff *= self.spec['weight'] / diff.shape[0]


class LogisticLossLayer(base.LossLayer):
    """The logistic loss layer. The input will be the scores BEFORE softmax
    normalization.

    The inpub should be two blobs: the first blob stores a N*1 dimensional
    matrix where N is the number of data points. The second blob stores the
    labels as a N-dimensional 0-1 vector.
    """
    def forward(self, bottom, top):
        pred = bottom[0].data()
        label = bottom[1].data()[:, np.newaxis]
        prob = logexp.exp(pred)
        numexpr.evaluate("prob / (1. + prob)", out=prob)
        diff = bottom[0].init_diff(setzero=False)
        numexpr.evaluate("label - prob", out=diff)
        self._loss = np.dot(label.flat, logexp.log(prob).flat) + \
                     np.dot((1. - label).flat, logexp.log(1. - prob).flat)
        # finally, scale down by the number of data points
        # Also, since we we computing the Loss (minimizing), we change the
        # sign of the loss value.
        diff *= - self.spec['weight'] / diff.shape[0]
        self._loss *= - self.spec['weight'] / diff.shape[0]


class MultinomialLogisticLossLayer(base.LossLayer):
    """The multinomial logistic loss layer. The input will be the scores
    BEFORE softmax normalization.
    
    The input should be two blobs: the first blob stores a 2-dimensional
    matrix where each row is the prediction for one class. The second blob
    stores the labels as a matrix of the same size in 0-1 format, or as a
    vector of the same length as the minibatch size.
    """
    def __init__(self, **kwargs):
        base.LossLayer.__init__(self, **kwargs)
        self._prob = base.Blob()

    def __getstate__(self, **kwargs):
        self._prob.clear()
        return self.__dict__

    def forward(self, bottom, top):
        pred = bottom[0].data()
        prob = self._prob.init_data(
            pred.shape, pred.dtype, setdata=False)
        prob[:] = pred
        prob -= prob.max(axis=1)[:, np.newaxis]
        logexp.exp(prob, out=prob)
        prob /= prob.sum(axis=1)[:, np.newaxis]
        diff = bottom[0].init_diff(setzero=False)
        diff[:] = prob
        logexp.log(prob, out=prob)
        label = bottom[1].data()
        if label.ndim == 1:
            # The labels are given as a sparse vector.
            diff[np.arange(diff.shape[0]), label] -= 1.
            self._loss = -prob[np.arange(diff.shape[0]), label].sum()
        else:
            # The labels are given as a dense matrix.
            diff -= label
            self._loss = -np.dot(prob.flat, label.flat)
        # finally, scale down by the number of data points
        diff *= self.spec['weight'] / diff.shape[0]
        self._loss *= self.spec['weight'] / diff.shape[0]


class KLDivergenceLossLayer(base.LossLayer):
    """This layer is similar to the MultinomialLogisticLossLayer, with the
    difference that this layer's input is AFTER the softmax function. If you
    would like to train a multinomial logistic regression, you should prefer
    using the MultinomialLogisticLossLayer since the gradient computation
    would be more efficient.
    """
    def forward(self, bottom, top):
        prob = bottom[0].data()
        label = bottom[1].data()
        diff = bottom[0].init_diff()
        if label.ndim == 1:
            # The labels are given as a sparse vector.
            indices = np.arange(diff.shape[0])
            prob_sub = np.ascontiguousarray(prob[indices, label])
            diff[indices, label] = 1. / prob_sub
            self._loss = logexp.log(prob_sub).sum()
        else:
            numexpr.evaluate('label / prob', out=diff)
            self._loss = np.dot(label.flat, logexp.log(prob).flat)
        # finally, scale down by the number of data points
        diff *= - self.spec['weight'] / diff.shape[0]
        self._loss *= - self.spec['weight'] / diff.shape[0]


class AutoencoderLossLayer(base.LossLayer):
    """The sparse autoencoder loss term.
    
    kwargs:
        ratio: the target ratio that the activations should follow.
    """
    def forward(self, bottom, top):
        """The reg function."""
        data = bottom[0].data()
        diff = bottom[0].init_diff()
        data_mean = data.mean(axis=0)
        # we clip it to avoid overflow
        np.clip(data_mean, np.finfo(data_mean.dtype).eps,
                1. - np.finfo(data_mean.dtype).eps,
                out=data_mean)
        neg_data_mean = 1. - data_mean
        ratio = self.spec['ratio']
        loss = (ratio * np.log(ratio / data_mean).sum() + 
                (1. - ratio) * np.log((1. - ratio) / neg_data_mean).sum())
        data_diff = (1. - ratio) / neg_data_mean - ratio / data_mean
        data_diff *= self.spec['weight'] / data.shape[0]
        diff += data_diff
        self._loss = loss * self.spec['weight']


########NEW FILE########
__FILENAME__ = normalize
"""Implements the Mean and variance normalization layer."""

from decaf import base
from decaf.layers.cpp import wrapper
import numpy as np
from numpy.core.umath_tests import inner1d


class MeanNormalizeLayer(base.Layer):
    """ A Layer that removes the mean along the mast dimension.
    """
    def __init__(self, **kwargs):
        base.Layer.__init__(self, **kwargs)

    def forward(self, bottom, top):
        """Computes the backward pass."""
        features = bottom[0].data()
        output = top[0].init_data(features.shape, features.dtype, setdata=False)
        # Create 2-dimenisonal views of the features and outputs.
        features.shape = (features.size / features.shape[-1], features.shape[-1])
        output.shape = features.shape
        output[:] = features
        output -= features.mean(axis=1)[:, np.newaxis]

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if propagate_down:
            top_diff = top[0].diff()
            bottom_diff = bottom[0].init_diff(setzero=False)
            top_diff.shape = (top_diff.size / top_diff.shape[-1], top_diff.shape[-1])
            bottom_diff.shape = top_diff.shape
            bottom_diff[:] = top_diff
            bottom_diff -= (top_diff.sum(1) / top_diff.shape[-1])[:, np.newaxis]
        return 0.
        
    def update(self):
        """Has nothing to update."""
        pass


class ResponseNormalizeLayer(base.Layer):
    """A layer that normalizes the last dimension. For a vector x, it is 
    normalized as
        y_i = x_i / sqrt(smooth + 1/N \sum_j x_j^2),
    where N is the length of the vector.

    If you would like to subtract the mean and then normalize by standard
    deviation, stack a mean and response normalize layer.
    """
    def __init__(self, **kwargs):
        """Initalizes the layer. 
        
        kwargs:
            smooth: the smoothness term added to the norm.
        """
        base.Layer.__init__(self, **kwargs)
        self._scale = None

    def forward(self, bottom, top):
        """Computes the forward pass."""
        # Get features and output
        features = bottom[0].data()
        output = top[0].init_data(features.shape, features.dtype, setdata=False)
        # Create 2-dimenisonal views of the features and outputs.
        features.shape = (features.size / features.shape[-1], features.shape[-1])
        output.shape = features.shape
        self._scale = inner1d(features, features)
        self._scale /= features.shape[-1]
        self._scale += self.spec.get('smooth', np.finfo(self._scale.dtype).eps)
        np.sqrt(self._scale, out=self._scale)
        output[:] = features
        output /= self._scale[:, np.newaxis]
    
    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if propagate_down:
            features = bottom[0].data()
            output = top[0].data()
            top_diff = top[0].diff()
            bottom_diff = bottom[0].init_diff(setzero=False)
            scale = self._scale
            # Create 2-dimenisonal views of the features and outputs.
            features.shape = (features.size / features.shape[-1],
                              features.shape[-1])
            output.shape = features.shape
            top_diff.shape = features.shape
            bottom_diff.shape = features.shape
            # Compute gradients
            # TODO(Yangqing) any more efficient representations?
            bottom_diff[:] = top_diff / scale[:, np.newaxis] - output * \
                    (inner1d(top_diff, output) / scale / features.shape[-1])\
                    [:, np.newaxis]
        return 0.

    def update(self):
        """Has nothing to update."""
        pass


class LocalResponseNormalizeLayer(base.Layer):
    """A layer that locally normalizes the last dimension. For a vector x, it is 
    normalized as
        y_i = x_i / (k + alpha/size \sum_j x_j^2)^beta,
    where the range of j is
        [max(0, i - floor((size-1)/2)), min(dim, i - floor((size-1)/2) + size)].
    """
    def __init__(self, **kwargs):
        """Initalizes the layer. 
        
        kwargs:

            k, alpha, beta: as defined in the equation.
            size: the local range.
        """
        base.Layer.__init__(self, **kwargs)
        self._k = self.spec['k']
        self._alpha = self.spec['alpha']
        self._beta = self.spec['beta']
        self._size = self.spec['size']
        self._scale = base.Blob()

    def forward(self, bottom, top):
        """Computes the forward pass."""
        features = bottom[0].data()
        output = top[0].init_data(features.shape, features.dtype)
        scale = self._scale.init_data(features.shape, features.dtype)
        if self._size > features.shape[-1]:
            raise base.DecafError('Incorrect size: should be smaller than '
                                  'the number of input channels.')
        wrapper.lrn_forward(features, output, scale,
                            self._size, self._k, self._alpha, self._beta)
    
    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if propagate_down:
            features = bottom[0].data()
            output = top[0].data()
            top_diff = top[0].diff()
            bottom_diff = bottom[0].init_diff()
            scale = self._scale.data()
            wrapper.lrn_backward(
                features, output, bottom_diff, top_diff, scale,
                self._size, self._k, self._alpha, self._beta)
        return 0.

    def __getstate__(self):
        """When pickling, we will remove the intermediate data."""
        self._scale = base.Blob()
        return self.__dict__
    
    def update(self):
        """Has nothing to update."""
        pass

#    def _backward_python_implementation(self, bottom, top, propagate_down):
#        # This is a sample python implementation of the backward operation.
#        features = bottom[0].data()
#        output = top[0].data()
#        top_diff = top[0].diff()
#        bottom_diff = bottom[0].init_diff()
#        scale = self._scale.data()
#        features.shape = (features.size / features.shape[-1],
#                          features.shape[-1])
#        output.shape = top_diff.shape = bottom_diff.shape = scale.shape \
#                = features.shape
#        # elementwise gradient computation
#        for n in range(features.shape[0]):
#            for c in range(features.shape[1]):
#                local_end = c + (self._size + 1) / 2
#                local_start = local_end - self._size
#                local_start = max(local_start, 0)
#                local_end = min(local_end, features.shape[1])
#                bottom_diff[n, c] = \
#                    top_diff[n, c] / (scale[n, c] ** self._beta) - \
#                    2. * self._alpha * self._beta / self._size * \
#                    features[n, c] * \
#                    (output[n, local_start:local_end] * \
#                     top_diff[n, local_start:local_end] / \
#                     scale[n, local_start:local_end]).sum()
#        return 0


########NEW FILE########
__FILENAME__ = padding
"""Implements the padding layer."""

from decaf import base

class PaddingLayer(base.Layer):
    """A layer that pads a matrix."""

    def __init__(self, **kwargs):
        """Initializes a padding layer.
        kwargs:
            'pad': the number of pixels to pad. Should be nonnegative.
                If pad is 0, the layer will simply mirror the input.
            'value': the value inserted to the padded area. Default 0.
        """
        base.Layer.__init__(self, **kwargs)
        self._pad = self.spec['pad']
        self._value = self.spec.get('value', 0)
        if self._pad < 0:
            raise ValueError('Padding should be nonnegative.')

    def forward(self, bottom, top):
        """Computes the forward pass."""
        if self._pad == 0:
            top[0].mirror(bottom[0])
            return
        # Get features and output
        features = bottom[0].data()
        if features.ndim != 4:
            raise ValueError('Bottom data should be a 4-dim tensor.')
        pad = self._pad
        newshape = (features.shape[0],
                    features.shape[1] + pad * 2,
                    features.shape[2] + pad * 2,
                    features.shape[3])
        output = top[0].init_data(newshape,
                                  features.dtype, setdata=False)
        output[:] = self._value
        output[:, pad:-pad, pad:-pad] = features

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if not propagate_down:
            return 0.
        if self._pad == 0:
            bottom[0].mirror_diff(top[0].diff())
        else:
            pad = self._pad
            top_diff = top[0].diff()
            bottom_diff = bottom[0].init_diff(setzero=False)
            bottom_diff[:] = top_diff[:, pad:-pad, pad:-pad]
        return 0.

    def update(self):
        """Padding has nothing to update."""
        pass

########NEW FILE########
__FILENAME__ = pooling
"""Implements the pooling layer."""

from decaf import base
from decaf.layers.cpp import wrapper
import math

class PoolingLayer(base.Layer):
    """A layer that implements the pooling function."""

    def __init__(self, **kwargs):
        """Initializes the pooling layer.

        kwargs:
            name: the name of the layer.
            psize: the pooling size. Pooling regions will be square shaped.
            stride: the pooling stride. If not given, it will be the same as
                the psize.
            mode: 'max' or 'ave'.
        """
        base.Layer.__init__(self, **kwargs)
        self._psize = self.spec['psize']
        self._stride = self.spec.get('stride', self._psize)
        self._mode = self.spec['mode']
        if self._stride > self._psize:
            raise ValueError(
                    'Currently, we do not support stride > psize case.')
        if self._psize <= 1:
            raise ValueError('Invalid pool size. Pool size should > 1.')
        if self._stride <= 0:
            raise ValueError('Invalid stride size. Stride size should > 0.')
    
    def forward(self, bottom, top):
        """Runs the forward pass."""
        bottom_data = bottom[0].data()
        num, height, width, nchannels = bottom_data.shape
        pooled_height = int(math.ceil(
            float(height - self._psize) / self._stride)) + 1
        pooled_width = int(math.ceil(
            float(width - self._psize) / self._stride)) + 1
        top_data = top[0].init_data(
            (num, pooled_height, pooled_width, nchannels),
            dtype=bottom_data.dtype)
        if self._mode == 'max':
            wrapper.maxpooling_forward(bottom_data, top_data,
                                       self._psize, self._stride)
        elif self._mode == 'ave':
            wrapper.avepooling_forward(bottom_data, top_data,
                                       self._psize, self._stride)
        else:
            raise ValueError('Unknown mode: %s.' % self._mode)
        return

    def backward(self, bottom, top, propagate_down):
        """Runs the backward pass."""
        if propagate_down:
            bottom_data = bottom[0].data()
            top_data = top[0].data()
            bottom_diff = bottom[0].init_diff()
            top_diff = top[0].diff()
            if self._mode == 'max':
                wrapper.maxpooling_backward(
                        bottom_data, top_data, bottom_diff,
                        top_diff, self._psize, self._stride)
            elif self._mode == 'ave':
                wrapper.avepooling_backward(
                        bottom_diff, top_diff, self._psize,
                        self._stride)
            else:
                raise ValueError('Unknown mode: %s.' % self._mode)
        return 0.

    def update(self):
        pass

########NEW FILE########
__FILENAME__ = puffsampler
"""Implements the minibatch sampling methods for data stored in puff format.
"""

from decaf import base
from decaf.util import mpi
import numpy as np


class PuffSamplerLayer(base.DataLayer):
    """A layer that loads data from a set of puff files."""
    def __init__(self, **kwargs):
        """Initializes the Puff sampling layer.

        kwargs:
            minibatch: the minibatch size.
            puff: a list of puff files to be read. These files should have the
                same number of data points, and the sampler will return data
                points from different points with the same index.
            use_mpi: if set True, when the code is run with mpirun, each mpi
                node will only deal with the part of file that has index range
                [N * RANK / SIZE, N * (RANK+1) / SIZE). Note that in this
                case, one need to make sure that the minibatch size is smaller
                than the number of data points in the local range on every mpi
                node. Default True.
        """
        base.DataLayer.__init__(self, **kwargs)
        self._filenames = self.spec['puff']
        self._use_mpi = self.spec.get('use_mpi', True)
        self._minibatch = self.spec['minibatch']
        self._puffs = [base.Puff(filename) for filename in self._filenames]
        num_data = [puff.num_data() for puff in self._puffs]
        if len(set(num_data)) == 1:
            raise ValueError('The puff files have different number of data.')
        if self._use_mpi:
            local_start = int(num_data[0] * mpi.RANK / mpi.SIZE)
            local_end = int(num_data[0] * (mpi.RANK + 1) / mpi.SIZE)
            if mpi.mpi_any(local_end - local_start < self._minibatch):
                raise ValueError('Local range smaller than minibatch.')
            for puff in self._puffs:
                puff.set_range(local_start, local_end)
        return

    def forward(self, bottom, top):
        """The forward pass."""
        for puff, top_blob in zip(self._puffs, top):
            top_blob.mirror(puff.read(self._minibatch))
        return


########NEW FILE########
__FILENAME__ = regularization
"""Implements basic regularizers."""

from decaf import base
import numpy as np
from decaf.util import logexp


class RegularizationAsLossLayer(base.LossLayer):
    """This is a class that wraps around a specific regularizer class to
    create a loss layer. Different from the normal regularizer, which modifies
    a blob in-place and does not take into account the number of data points
    (which is desired in imposing regularization terms for parameters), the 
    wrapped layer divides the regularization output by the number of data
    points passed to the layer.

    kwargs:
        reg: the regularizer class.
        weight: the weight of the loss function.
        (You can add other parameters which your regularizer may need.)
    """
    def __init__(self, **kwargs):
        base.LossLayer.__init__(self, **kwargs)
        self._reg_kwargs = dict(self.spec)
        del self._reg_kwargs['reg']
        del self._reg_kwargs['weight']
        self._num_data = -1
        self._regularizer = None
    
    def _init_reg(self, num_data):
        if self._num_data != num_data:
            self._regularizer = self.spec['reg'](
                    weight=self.spec['weight'] / num_data, **self._reg_kwargs)
            self._num_data = num_data
    
    def forward(self, bottom, top):
        """Forward emits the loss, and computes the gradient as well."""
        num_data = bottom[0].data().shape[0]
        self._init_reg(num_data)
        diff = bottom[0].init_diff()
        self._loss = self._regularizer.reg(bottom[0])


def make_loss_layer_class(cls):
    def _make_layer(**kwargs):
        return RegularizationAsLossLayer(reg=cls, **kwargs)
    return _make_layer


# pylint: disable=R0903
class L2Regularizer(base.Regularizer):
    """The L2 regularization."""
    def reg(self, blob):
        """The reg function."""
        data = blob.data()
        #pylint: disable=W0612
        diff = blob.diff()
        diff += self._weight * 2. * data
        return np.dot(data.flat, data.flat) * self._weight

L2RegularizerLossLayer = make_loss_layer_class(L2Regularizer)


# pylint: disable=R0903
class L1Regularizer(base.Regularizer):
    """The L1 regularization."""
    def reg(self, blob):
        """The reg function."""
        data = blob.data()
        #pylint: disable=W0612
        diff = blob.diff()
        diff += self._weight * np.sign(data)
        return np.abs(data).sum() * self._weight


L1RegularizerLossLayer = make_loss_layer_class(L1Regularizer)

########NEW FILE########
__FILENAME__ = relu
"""Implements the ReLU layer."""

from decaf import base
from decaf.layers.cpp import wrapper

class ReLULayer(base.Layer):
    """A layer that implements the Regularized Linear Unit (ReLU) operation
    that converts x to max(x, 0).
    """

    def __init__(self, **kwargs):
        """Initializes a ReLU layer.
        """
        base.Layer.__init__(self, **kwargs)
    
    def forward(self, bottom, top):
        """Computes the forward pass."""
        # Get features and output
        features = bottom[0].data()
        output = top[0].init_data(features.shape, features.dtype)
        wrapper.relu_forward(features, output)
        #output[:] = features
        #output *= (features > 0)

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if not propagate_down:
            return 0.
        top_diff = top[0].diff()
        features = bottom[0].data()
        bottom_diff = bottom[0].init_diff()
        bottom_diff[:] = top_diff
        bottom_diff *= (features > 0)
        return 0.

    def update(self):
        """ReLU has nothing to update."""
        pass

########NEW FILE########
__FILENAME__ = sampler
"""Implements the minibatch sampling layer."""

from decaf import base
import numpy as np

class BasicMinibatchLayer(base.DataLayer):
    """A layer that extracts minibatches from bottom blobs.
    
    We will not randomly generate minibatches, but will instead produce them
    sequentially. Every forward() call will change the minibatch, so if you
    want a fixed minibatch, do NOT run forward multiple times.
    """

    def __init__(self, **kwargs):
        """Initializes the layer.

        kwargs:
            minibatch: the minibatch size.
        """
        base.DataLayer.__init__(self, **kwargs)
        self._minibatch = self.spec['minibatch']
        self._index = 0

    def forward(self, bottom, top):
        """Computes the forward pass."""
        size = bottom[0].data().shape[0]
        end_id = self._index + self._minibatch
        for bottom_blob, top_blob in zip(bottom, top):
            bottom_data = bottom_blob.data()
            if bottom_data.shape[0] != size:
                raise RuntimeError(
                    'Inputs do not have identical number of data points!')
            top_data = top_blob.init_data(
                (self._minibatch,) + bottom_data.shape[1:], bottom_data.dtype)
            # copy data
            if end_id <= size:
                top_data[:] = bottom_data[self._index:end_id]
            else:
                top_data[:(size - self._index)] = bottom_data[self._index:]
                top_data[-(end_id - size):] = bottom_data[:(end_id - size)]
        # finally, compute the new index.
        self._index = end_id % size
        

class RandomPatchLayer(base.DataLayer):
    """A layer that randomly extracts patches from bottom blobs.
    """

    def __init__(self, **kwargs):
        """Initialize the layer.

        kwargs:
            psize: the patch size.
            factor: the number of patches per bottom layer's image.
        """
        base.DataLayer.__init__(self, **kwargs)

    def forward(self, bottom, top):
        """Computes the forward pass."""
        factor = self.spec['factor']
        psize = self.spec['psize']
        bottom_data = bottom[0].data()
        num_img, height, width, num_channels = bottom_data.shape
        top_data = top[0].init_data(
            (num_img * factor, psize, psize, num_channels),
            dtype=bottom_data.dtype)
        h_indices = np.random.randint(height - psize, size=num_img * factor)
        w_indices = np.random.randint(width - psize, size=num_img * factor)
        for i in range(num_img):
            for j in range(factor):
                current = i * factor + j
                h_index, w_index = h_indices[current], w_indices[current]
                top_data[current] = bottom_data[i,
                                                h_index:h_index + psize,
                                                w_index:w_index + psize]
        return


########NEW FILE########
__FILENAME__ = sigmoid
"""Implements the sigmoid layer."""

from decaf import base
from decaf.util import logexp
import numexpr

class SigmoidLayer(base.Layer):
    """A layer that implements the sigmoid operation."""

    def __init__(self, **kwargs):
        """Initializes a ReLU layer.
        """
        base.Layer.__init__(self, **kwargs)
    
    def forward(self, bottom, top):
        """Computes the forward pass."""
        # Get features and top_data
        bottom_data = bottom[0].data()
        top_data = top[0].init_data(bottom_data.shape, bottom_data.dtype)
        numexpr.evaluate('1. / (exp(-bottom_data) + 1.)', out=top_data)

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if propagate_down:
            top_data = top[0].data()
            top_diff = top[0].diff()
            bottom_diff = bottom[0].init_diff()
            numexpr.evaluate('top_data * top_diff * (1. - top_data)', out=bottom_diff)
        return 0

    def update(self):
        """ReLU has nothing to update."""
        pass

########NEW FILE########
__FILENAME__ = softmax
"""Implements the softmax function.
"""

from decaf import base
from decaf.util import logexp
import numpy as np
from numpy.core.umath_tests import inner1d

class SoftmaxLayer(base.Layer):
    """A layer that implements the softmax function."""

    def __init__(self, **kwargs):
        """Initializes a softmax layer.

        kwargs:
            name: the layer name.
        """
        base.Layer.__init__(self, **kwargs)

    def forward(self, bottom, top):
        """Computes the forward pass."""
        # Get features and output
        pred = bottom[0].data()
        prob = top[0].init_data(pred.shape, pred.dtype, setdata=False)
        prob[:] = pred
        # normalize by subtracting the max to suppress numerical issues
        prob -= prob.max(axis=1)[:, np.newaxis]
        logexp.exp(prob, out=prob)
        prob /= prob.sum(axis=1)[:, np.newaxis]

    def backward(self, bottom, top, propagate_down):
        """Computes the backward pass."""
        if not propagate_down:
            return 0.
        top_diff = top[0].diff()
        prob = top[0].data()
        bottom_diff = bottom[0].init_diff(setzero=False)
        bottom_diff[:] = top_diff
        cross_term = inner1d(top_diff, prob)
        bottom_diff -= cross_term[:, np.newaxis]
        bottom_diff *= prob
        return 0.

    def update(self):
        """Softmax has nothing to update."""
        pass

########NEW FILE########
__FILENAME__ = core_solvers
# pylint: disable=W0611
"""Imports commonly used solvers."""

from decaf.opt.lbfgs_solver import LBFGSSolver
from decaf.opt.stochastic_solver import SGDSolver, AdagradSolver

########NEW FILE########
__FILENAME__ = lbfgs_solver
"""Implements the LBFGS solver."""

from decaf import base
from decaf.util import mpi
import logging
from scipy import optimize

_FMIN = optimize.fmin_l_bfgs_b

class LBFGSSolver(base.Solver):
    """The LBFGS solver.
    
    This solver heavily relies on scipy's optimize toolbox (specifically,
    fmin_l_bfgs_b) so we write it differently from the other solvers. When
    faced with very large-scale problems, the additional memory overhead of
    LBFGS may make the method inapplicable, in which you may want to use the
    stochastic solvers. Also, although LBFGS solver supports mpi based
    optimizations, due to the network communication overhead you may still be
    better off using stochastic solvers with large-scale problems..
    """
    
    def __init__(self, **kwargs):
        """The LBFGS solver. Necessary args is:
            lbfgs_args: a dictionary containg the parameters to be passed
                to lbfgs.
        """
        base.Solver.__init__(self, **kwargs)
        self._lbfgs_args = self.spec.get('lbfgs_args', {})
        self._param = None
        self._decaf_net = None
        self._previous_net = None

    def _collect_params(self, realloc=False):
        """Collect the network parameters into a long vector.
        """
        params_list = self._decaf_net.params()
        if self._param is None or realloc:
            total_size = sum(p.data().size for p in params_list)
            dtype = max(p.data().dtype for p in params_list)
            self._param = base.Blob(shape=total_size, dtype=dtype)
            self._param.init_diff()
        current = 0
        collected_param = self._param.data()
        collected_diff = self._param.diff()
        for param in params_list:
            size = param.data().size
            collected_param[current:current+size] = param.data().flat
            # If we are computing mpi, we will need to reduce the diff.
            diff = param.diff()
            if mpi.SIZE > 1:
                part = collected_diff[current:current+size]
                part.shape = diff.shape
                mpi.COMM.Allreduce(diff, part)
            else:
                collected_diff[current:current+size] = diff.flat
            current += size

    def _distribute_params(self):
        """Distribute the parameter to the net.
        """
        params_list = self._decaf_net.params()
        current = 0
        for param in params_list:
            size = param.data().size
            param.data().flat = self._param.data()[current:current+size]
            current += size

    def obj(self, variable):
        """The objective function that wraps around the net."""
        self._param.data()[:] = variable
        self._distribute_params()
        loss = self._decaf_net.forward_backward(self._previous_net)
        if mpi.SIZE > 1:
            loss = mpi.COMM.allreduce(loss)
        self._collect_params()
        return loss, self._param.diff()

    def solve(self, decaf_net, previous_net=None):
        """Solves the net."""
        # first, run an execute pass to initialize all the parameters.
        self._decaf_net = decaf_net
        self._previous_net = previous_net
        initial_loss = self._decaf_net.forward_backward(self._previous_net)
        logging.info('Initial loss: %f.', initial_loss)
        logging.info('(Under mpirun, the given loss will just be an estimate'
                     ' on the root node.)')
        if mpi.SIZE > 1:
            params = self._decaf_net.params()
            for param in params:
                mpi.COMM.Bcast(param.data())
        self._collect_params(True)
        # now, run LBFGS
        # pylint: disable=W0108
        result = _FMIN(lambda x: self.obj(x), self._param.data(), 
                       **self._lbfgs_args)
        # put the optimized result to the net.
        self._param.data()[:] = result[0]
        self._distribute_params()
        logging.info('Final function value: %f.', result[1])


########NEW FILE########
__FILENAME__ = stochastic_solver
"""Implements the stochastic solvers."""
import cPickle as pickle
from decaf import base
from decaf.util import mpi
from decaf.util.timer import Timer
import logging
import numpy as np
import os

class StochasticSolver(base.Solver):
    """The Basic stochastic solver."""
    
    def __init__(self, **kwargs):
        """Initializes the Stochastic solver.
        
        kwargs:
            base_lr: the base learning rate.
            disp: if 0, no information is displayed. If a positive number, the
                optimization status will be printed out every few iterations,
                with the interval given by disp.
            max_iter: the maximum number of iterations. Default 1000.
            snapshot_interval: the snapshot interval. Default 0.
            folder: the snapshot folder. Should be provided
                if snapshot_interval is not zero.
        """
        base.Solver.__init__(self, **kwargs)
        self._max_iter = self.spec.get('max_iter', 1000)
        self._snapshot_interval = self.spec.get('snapshot_interval', 0)
        if self._snapshot_interval > 0 and 'folder' not in self.spec:
            raise ValueError('You should provide a folder to write result to.')
        self._decaf_net = None
        self._previous_net = None
        self._iter_idx = None

    def initialize_status(self):
        """A function that specific stochastic solvers can override
        to perform necessary initialization, after the net is run for the
        first time to allocate all the intermediate variables and gives an
        initial loss. The default initialization will make all the parameters
        the same by broadcasting the parameters from root.
        """
        if mpi.SIZE > 1:
            params = self._decaf_net.params()
            for param in params:
                mpi.COMM.Bcast(param.data())
        return

    def compute_update_value(self):
        """An abstract function that specific stochastic solvers have to
        implement to determine the update value. The gradients can be obtained
        as [param.diff() for param in decaf_net.params()], and the algorithm
        should write the update values into the param.diff() fields. Note that
        the diff values are already the averaged version over the mpi nodes
        by the solver, so you don't need to rebroadcast them again.

        Input:
            decaf_net: the network.
            loss: the computed loss. A specific solver may not actually need
                the loss value, but we provide it here for logging purpose.
        """
        raise NotImplementedError
    
    def snapshot(self, is_final=False):
        """A function that specific stochastic solvers can override to provide
        snapshots of the current net as well as necessary other bookkeeping
        stuff. The folder will be the place that the snapshot should be written
        to, and the function should create a subfolder named as the iter_idx,
        and write any necessary information there.
        
        In default, the snapshot function will store the network using the 
        network's save function.
        """
        folder = self.spec['folder']
        if is_final:
            subfolder = os.path.join(folder, 'final')
        else:
            subfolder = os.path.join(folder, str(self._iter_idx))
        try:
            os.makedirs(subfolder)
        except OSError:
            pass
        self._decaf_net.save(
            os.path.join(subfolder, self._decaf_net.name + '.net'))
        # return the subfolder name that we will use for further processing.
        return subfolder

    def iter_callback(self, loss):
        """Iteration callback. Override this function if anything should be
        carried out after each iteration.
        """
        pass

    def solve(self, decaf_net, previous_net=None):
        """Solves the net."""
        # first, run a pass to initialize all the parameters.
        logging.info('StochasticSolver: precomputing.')
        self._iter_idx = 0
        self._decaf_net = decaf_net
        self._previous_net = previous_net
        initial_loss = decaf_net.forward_backward(self._previous_net)
        logging.info('StochasticSolver: initial loss: %f.', initial_loss)
        logging.info('(Under mpirun, the given loss will just be an estimate'
                     ' on the root node.)')
        self.initialize_status()
        # the main iteration
        timer = Timer()
        logging.info('StochasticSolver: started.')
        for _ in range(self._max_iter):
            if mpi.SIZE > 1:
                loss = mpi.COMM.allreduce(
                    decaf_net.forward_backward(self._previous_net)) / mpi.SIZE
                # we need to broadcast and average the parameters
                params = decaf_net.params()
                for param in params:
                    diff = param.diff()
                    diff_cache = diff.copy()
                    mpi.COMM.Allreduce(diff_cache, diff)
                    diff /= mpi.SIZE
            else:
                loss = decaf_net.forward_backward(self._previous_net)
            self.compute_update_value()
            decaf_net.update()
            if (mpi.is_root() and 
                self._snapshot_interval > 0 and self._iter_idx > 0 and
                self._iter_idx % self._snapshot_interval == 0):
                # perform snapshot.
                self.snapshot()
            if (self.spec.get('disp', 0) and 
                self._iter_idx % self.spec['disp']):
                logging.info('Iter %d, loss %f, elapsed %s', self._iter_idx,
                             loss, timer.lap())
            self.iter_callback(loss)
            self._iter_idx += 1
        # perform last snapshot.
        if mpi.is_root() and 'folder' in self.spec:
            self.snapshot(True)
        mpi.barrier()
        logging.info('StochasticSolver: finished. Total time %s.',
                     timer.total())


class SGDSolver(StochasticSolver):
    """The SGD solver.
    """
    
    def __init__(self, **kwargs):
        """Initializes the SGD solver.

        kwargs:
            base_lr: the base learning rate.
            max_iter: the maximum number of iterations. Default 1000.
            lr_policy: the learning rate policy. could be:
                'fixed': rate will always be base_lr.
                'exp': exponent decay - rate will be
                    base_lr * (gamma ^ t)
                'inv': rate will be base_lr / (1 + gamma * t)^power
                where t in the above equations are the epoch, starting from 0.
            min_lr: the minimun learning rate. Default 0. If weight decay
                results in a learning rate smaller than min_lr, it is set to
                min_lr.
            max_lr: the maximum learning rate. Default Inf.
            gamma: the gamma parameter, see lr_policy.
            power: the power parameter, see lr_policy. Default 1.
            momentum: the momentum value. Should be in the range [0,1).
                Default 0.
            asgd: if True, use average sgd (Polyak 1992).
            asgd_skip: the number of iterations to skip before averaging.
                Default 1 (http://leon.bottou.org/projects/sgd/).
        """
        StochasticSolver.__init__(self, **kwargs)
        self.spec['momentum'] = self.spec.get('momentum', 0)
        self.spec['asgd'] = self.spec.get('asgd', False)
        self.spec['asgd_skip'] = self.spec.get('asgd_skip', 1)
        self.spec['power'] = self.spec.get('power', 1)
        self.spec['max_lr'] = self.spec.get('max_lr', float('inf'))
        self.spec['min_lr'] = self.spec.get('min_lr', 0.)
        self._momentum = None
        self._asgd = None

    def _get_learningrate(self):
        """get the learning rate."""
        policy = self.spec['lr_policy']
        base_lr = self.spec['base_lr']
        if policy == 'fixed':
            learningrate = base_lr
        elif policy == 'exp':
            learningrate = base_lr * (self.spec['gamma'] ** self._iter_idx)
        elif policy == 'inv':
            learningrate = base_lr / ((1 + self.spec['gamma'] * self._iter_idx)
                                      ** self.spec['power'])
        return min(max(learningrate, self.spec['min_lr']), self.spec['max_lr'])
    
    def initialize_status(self):
        """Initializes the status."""
        StochasticSolver.initialize_status(self)
        if self.spec['momentum']:
            # we need to maintain the momentum history
            params = self._decaf_net.params()
            self._momentum = [np.zeros_like(p.data())
                              for p in params]
        if self.spec['asgd']:
            # we need to maintain the asgd param values
            params = self._decaf_net.params()
            self._asgd = [np.zeros_like(p.data())
                          for p in params]
        
    def compute_update_value(self):
        """Computes the update value by multiplying the gradient with the
        learning rate.
        """
        learningrate = self._get_learningrate()
        logging.debug('learning rate %f', learningrate)
        if self.spec['momentum'] > 0:
            # we need to add momentum terms and keep track of them.
            for momentum, param in zip(self._momentum,
                                       self._decaf_net.params()):
                momentum *= self.spec['momentum']
                diff = param.diff()
                diff *= learningrate
                diff += momentum
                momentum[:] = diff
        else:
            for param in self._decaf_net.params():
                diff = param.diff()
                diff *= learningrate
        return

    def iter_callback(self, loss):
        """Iteration callback."""
        if self.spec['asgd'] and self._iter_idx >= self.spec['asgd_skip']:
            # we need to maintain the asgd values.
            # pylint: disable=W0612
            for asgd, param in zip(self._asgd, self._decaf_net.params()):
                # we will simply do addition. Note that when you try to get
                # the final net, you need to divide the asgd_data by the
                # number of iterations minus asgd_skip. 
                asgd += param.data()
    
    def snapshot(self, is_final = False):
        """perform snapshot."""
        subfolder = StochasticSolver.snapshot(
            self, is_final=is_final)
        if self.spec['momentum'] > 0:
            # we need to store momentum as well
            with open(os.path.join(subfolder, 'momentum'), 'wb') as fid:
                pickle.dump(self._momentum, fid,
                            protocol=pickle.HIGHEST_PROTOCOL)
        if self.spec['asgd']:
            # let's store the accumulated asgd values.
            with open(os.path.join(subfolder, 'asgd'), 'wb') as fid:
                pickle.dump(self._asgd, fid, protocol=pickle.HIGHEST_PROTOCOL)


class AdagradSolver(StochasticSolver):
    """The Adagrad Solver."""
    def __init__(self, **kwargs):
        """Initializes the SGD solver.

        kwargs:
            base_lr: the base learning rate.
            max_iter: the maximum number of iterations. Default 1000.
            base_accum: the base value to initialize the accumulated gradient
                diagonal. Default 1e-8.
        """
        StochasticSolver.__init__(self, **kwargs) 
        self.spec['base_accum'] = self.spec.get('base_accum', 1e-8)
        self._accum = None

    def initialize_status(self):
        """Initializes the status."""
        # we need to maintain the momentum history
        params = self._decaf_net.params()
        self._accum = [base.Blob(p.data().shape, p.data().dtype)
                       for p in params]
        for accum in self._accum:
            accum_data = accum.data()
            accum_data[:] = self.spec['base_accum']
            # we initialize the diff as a buffer when computing things later.
            accum.init_diff()
        
    def compute_update_value(self):
        """Computes the update value by multiplying the gradient with the
        learning rate.
        """
        for param, accum in zip(self._decaf_net.params(), self._accum):
            diff = param.diff()
            # add the current gradient to the accumulation
            accum_data = accum.data()
            accum_buffer = accum.diff()
            accum_buffer[:] = diff
            accum_buffer *= diff
            accum_data += accum_buffer
            # compute the sqrt, and update diff
            np.sqrt(accum_data, out=accum_buffer)
            diff /= accum_buffer
            diff *= self.spec['base_lr']
        return

    def snapshot(self, is_final = False):
        """perform snapshot."""
        subfolder = StochasticSolver.snapshot(self, is_final=is_final)
        with open(os.path.join(subfolder, 'adagrad_accum'), 'wb') as fid:
            pickle.dump(self._accum, fid, protocol=pickle.HIGHEST_PROTOCOL)
        return subfolder


########NEW FILE########
__FILENAME__ = puff
"""Puff defines a purely unformatted file format accompanying decaf for easier
and faster access of numpy arrays.
"""
import bisect
import cPickle as pickle
import glob
import logging
import numpy as np
from operator import mul
import os


class Puff(object):
    """The puff class. It defines a simple interface that stores numpy arrays in
    its raw form.
    """
    def __init__(self, names, start = None, end = None):
        """Initializes the puff object.

        Input:
            names: the wildcard names matching multiple puff files.
            start: (optional) the local range start.
            end: (optional) the local range end.
        """
        if not names.endswith('.puff'):
            names = names + '.puff'
        # convert names to a list of files
        files = glob.glob(names)
        if not len(files):
            raise ValueError('No file found for the given wildcard: %s.' % names)
        files.sort()
        # shape is the shape of a single data point.
        self._shape = None
        # step is an internal variable that indicates how many bytes we need
        # to jump over per data point
        self._step = None
        # num_data is the total number of data in the file
        self._num_data = None
        # the following variables are used to slice a puff
        self._start = None
        self._end = None
        # the current index of the data.
        self._curr = None
        self._curr_fid = None
        # the number of local data
        self._num_local_data = None
        # dtype is the data type of the data
        self._dtype = None
        # iter_count is used to record the iteration status 
        self._iter_count = 0
        # the fids for the opened file. We will assume that there are not too
        # many files so we will keep them open all the time.
        self._fids = []
        self._fid_starts = []
        self.open(files)
        self.set_range(start, end)

    def set_range(self, start, end):
        """sets the range that we will read data from."""
        if start is not None:
            if start > self._num_data:
                raise ValueError('Invalid start index.')
            else:
                self._start = start
                self.seek(self._start)
                self._curr = self._start
        if end is not None:
            if end > start and end <= self._num_data:
                self._end = end
            else:
                raise ValueError('Invalid end index.')
        self._num_local_data = self._end - self._start

    def reset(self):
        """Reset the puff pointer to the start of the local range."""
        self.seek(self._start)

    def __iter__(self):
        """A simple iterator to go through the data."""
        self.seek(self._start)
        self._iter_count = 0
        return self

    def next(self):
        """The next function."""
        if self._curr == self._start and self._iter_count:
            raise StopIteration
        else:
            self._iter_count += 1
            return self.read(1)[0]

    def num_data(self):
        """Return the number of data."""
        return self._num_data
    
    def shape(self):
        """Return the shape of a single data point."""
        return self._shape

    def dtype(self):
        """Return the dtype of the data."""
        return self._dtype

    def num_local_data(self):
        """Returns the number of local data."""
        return self._num_local_data

    def open(self, names):
        """Opens a puff data: it is composed of two files, name.puff and
        name.icing. The open function will set the range to all the data
        points - use set_range() to specify a custom range to read from.
        """
        self._fids = []
        self._fid_starts = []
        count = 0
        for name in names:
            logging.debug('opening %s', name)
            icing = pickle.load(open(name[:-5] + '.icing'))
            if not self._dtype:
                # The first file. Will record the meta information
                self._shape = icing['shape']
                self._dtype = icing['dtype']
                self._step = reduce(mul, self._shape, 1)
            else:
                if (self._shape != icing['shape'] or
                    self._dtype != icing['dtype']):
                    raise ValueError('Shards do not have the same data shape or dtype!')
            self._fids.append(open(name, 'rb'))
            self._fid_starts.append(count)
            count += icing['num']
        # add a closing fid location
        self._fid_starts.append(count)
        # set all the pointers.
        self._num_data = count
        self._start = 0
        self._end = self._num_data
        self._num_local_data = self._num_data
        self._curr = 0
        self._curr_fid = 0

    def seek(self, offset):
        """Seek to the beginning of the offset-th data point."""
        if offset < self._start or offset >= self._end:
            raise ValueError('Offset (%d) should lie in the data range'
                             ' [%d, %d).' % (offset, self._start, self._end))
        # we need to find out which file we are at
        index = bisect.bisect_right(self._fid_starts, offset) - 1
        self._curr_fid = index
        self._fids[self._curr_fid].seek(
            (offset - self._fid_starts[index]) * self._step \
            * self._dtype.itemsize)
        self._curr = offset

    def read(self, count):
        """Read the specified number of data and return as a numpy array."""
        if count > self._num_local_data:
            raise ValueError('Not enough data points to read: count %d, limit'
                             ' %d.' % (count, self._num_local_data))
        fid = self._fids[self._curr_fid]
        fid_end = self._fid_starts[self._curr_fid + 1]
        if self._curr + count > self._end:
            # first, if the range goes over the local end, we will need to
            # read it in two (or more nested) batches.
            part = self._end - self._curr
            if self._shape:
                data = np.vstack((self.read(part), self.read(count - part)))
            else:
                data = np.hstack((self.read(part), self.read(count - part)))
        elif self._curr + count > fid_end:
            # second, if the current batch goes over the current fid, we will
            # need to read it in two or more batches.
            part = fid_end - self._curr
            if self._shape:
                data = np.vstack((self.read(part), self.read(count - part)))
            else:
                data = np.hstack((self.read(part), self.read(count - part)))
        else:
            # if nothing happens, we will simply read a single chunk.
            data = np.fromfile(fid, self._dtype, count * self._step)
            self._curr += count
            # If depleted, we will seek to the next file.
            if self._curr == fid_end or self._curr == self._end:
                self.seek(max(self._curr % self._end, self._start))
        return data.reshape((count,) + self._shape)

    def read_all(self):
        """Reads all the data from the file."""
        self.seek(self._start)
        return self.read(self._num_local_data)


class PuffStreamedWriter(object):
    """A streamed writer to write a large puff incrementally."""
    def __init__(self, name):
        self._shape = None
        self._num_data = 0
        self._dtype = None
        self._fid = open(name + '.puff', 'wb')
        self._name = name
    
    def check_validity(self, arr):
        """Checks if the data is valid."""
        if self._shape is None:
            self._shape = arr.shape
            self._dtype = arr.dtype
        else:
            if self._shape != arr.shape or self._dtype != arr.dtype:
                raise TypeError('Array invalid with previous inputs! '
                                'Previous: %s, %s, current: %s %s' %
                                (str(self._shape), str(self._dtype),
                                 str(arr.shape), str(arr.dtype)))

    def write_single(self, arr):
        """Write a single data point."""
        self.check_validity(arr)
        arr.tofile(self._fid)
        self._num_data += 1

    def write_batch(self, arr):
        """Write a bunch of data points to file."""
        self.check_validity(arr[0])
        arr.tofile(self._fid)
        self._num_data += arr.shape[0]

    def finish(self):
        """Finishes a Puff write."""
        if self._num_data == 0:
            raise ValueError('Nothing is written!')
        self._fid.close()
        logging.debug('Output shape: %s, dtype: %s, num: %s',
                      self._shape, self._dtype, self._num_data)
        with open(self._name + '.icing', 'w') as fid:
            pickle.dump({'shape': self._shape,
                         'dtype': self._dtype,
                         'num': self._num_data}, fid)


def write_puff(arr, name):
    """Write a single numpy array to puff format."""
    writer = PuffStreamedWriter(name)
    writer.write_batch(arr)
    writer.finish()


def merge_puff(names, output_name, batch_size=None, delete=None):
    """Merges a set of puff files, sorted according to their name.
    Input:
        names: a set of file names to be merged. The order does not matter,
            but note that we will sort the names internally.
        output_name: the output file name.
        batch_size: if None, read the whole file and write it in a single
            batch. Otherwise, read and write the given size at a time.
        delete: if True, delete the individual files after merging. Default
            False.
    Note that you usually do not need to merge puffs, since puff naturally
    supports sharding.
    """
    names.sort()
    writer = PuffStreamedWriter(output_name)
    if batch_size is None:
        for name in names:
            logging.debug('writing %s', name)
            writer.write_batch(Puff(name).read_all())
    else:
        for name in names:
            logging.debug('writing %s', name)
            puff = Puff(name)
            num = puff.num_data()
            for curr in range(0, num, batch_size):
                writer.write_batch(puff.read(batch_size))
            # write the last batch
            writer.write_batch(puff.read(num - curr))
    if delete:
        for name in names:
            if name.endswith('.puff'):
                shortname = name[:-5]
            else:
                shortname = name
            os.remove(shortname + '.puff')
            os.remove(shortname + '.icing')
    # Finally, finish the write.
    writer.finish()


def puffmap(func, puff, output_name, write_batch=None):
    """A function similar to map() that runs the func on each item of the puff
    and writes the result to output_name.
    Input:
        func: a function that takes in a puff entry and returns a numpy array.
        puff: the puff file. May be locally sliced.
        output_name: the output puff file name.
        write_batch: if True, we will use write_batch() instead of
            write_single(). This may be useful when each input puff element
            leads to multiple output elements. Default False.
    """
    writer = PuffStreamedWriter(output_name)
    if write_batch:
        for elem in puff:
            writer.write_batch(func(elem))
    else:
        for elem in puff:
            writer.write_single(func(elem))
    writer.finish()

########NEW FILE########
__FILENAME__ = imagenet
"""imagenet implements a wrapper over the imagenet classifier trained by Jeff
Donahue using the cuda convnet code.
"""
import cPickle as pickle
from decaf.util import translator, transform
import logging
import numpy as np
import os

_JEFFNET_FILE = os.path.join(os.path.dirname(__file__),
                             'imagenet.decafnet.epoch90')
_META_FILE = os.path.join(os.path.dirname(__file__), 'imagenet.decafnet.meta')

# This is a legacy flag specifying if the network is trained with vertically
# flipped images, which does not hurt performance but requires us to flip
# the input image first.
_JEFFNET_FLIP = True

# Due to implementational differences between the CPU and GPU codes, our net
# takes in 227x227 images - which supports convolution with 11x11 patches and
# stride 4 to a 55x55 output without any missing pixels. As a note, the GPU
# code takes 224 * 224 images, and does convolution with the same setting and
# no padding. As a result, the last image location is only convolved with 8x8
# image regions.
INPUT_DIM = 227

class DecafNet(object):
    """A wrapper that returns the decafnet interface to classify images."""
    def __init__(self, net_file=None, meta_file=None):
        """Initializes DecafNet.

        Input:
            net_file: the trained network file.
            meta_file: the meta information for images.
        """
        logging.info('Initializing decafnet...')
        try:
            if not net_file:
                # use the internal decafnet file.
                net_file = _JEFFNET_FILE
            if not meta_file:
                # use the internal meta file.
                meta_file = _META_FILE
            cuda_decafnet = pickle.load(open(net_file))
            meta = pickle.load(open(meta_file))
        except IOError:
            raise RuntimeError('Cannot find DecafNet files.')
        # First, translate the network
        self._net = translator.translate_cuda_network(
            cuda_decafnet, {'data': (INPUT_DIM, INPUT_DIM, 3)})
        # Then, get the labels and image means.
        self.label_names = meta['label_names']
        self._data_mean = translator.img_cudaconv_to_decaf(
            meta['data_mean'], 256, 3)
        logging.info('Jeffnet initialized.')
        return

    def classify_direct(self, images):
        """Performs the classification directly, assuming that the input
        images are already of the right form.

        Input:
            images: a numpy array of size (num x 227 x 227 x 3), dtype
                float32, c_contiguous, and has the mean subtracted and the
                image flipped if necessary.
        Output:
            scores: a numpy array of size (num x 1000) containing the
                predicted scores for the 1000 classes.
        """
        return self._net.predict(data=images)['probs_cudanet_out']

    @staticmethod
    def oversample(image, center_only=False):
        """Oversamples an image. Currently the indices are hard coded to the
        4 corners and the center of the image, as well as their flipped ones,
        a total of 10 images.

        Input:
            image: an image of size (256 x 256 x 3) and has data type uint8.
            center_only: if True, only return the center image.
        Output:
            images: the output of size (10 x 227 x 227 x 3)
        """
        indices = [0, 256 - INPUT_DIM]
        center = int(indices[1] / 2)
        if center_only:
            return np.ascontiguousarray(
                image[np.newaxis, center:center + INPUT_DIM,
                      center:center + INPUT_DIM], dtype=np.float32)
        else:
            images = np.empty((10, INPUT_DIM, INPUT_DIM, 3),
                              dtype=np.float32)
            curr = 0
            for i in indices:
                for j in indices:
                    images[curr] = image[i:i + INPUT_DIM,
                                         j:j + INPUT_DIM]
                    curr += 1
            images[4] = image[center:center + INPUT_DIM,
                              center:center + INPUT_DIM]
            # flipped version
            images[5:] = images[:5, ::-1]
            return images
    
    def classify(self, image, center_only=False):
        """Classifies an input image.
        
        Input:
            image: an image of 3 channels and has data type uint8. Only the
                center region will be used for classification.
        Output:
            scores: a numpy vector of size 1000 containing the
                predicted scores for the 1000 classes.
        """
        # first, extract the 256x256 center.
        image = transform.scale_and_extract(transform.as_rgb(image), 256)
        # convert to [0,255] float32
        image = image.astype(np.float32) * 255.
        if _JEFFNET_FLIP:
            # Flip the image if necessary, maintaining the c_contiguous order
            image = image[::-1, :].copy()
        # subtract the mean
        image -= self._data_mean
        # oversample the images
        images = DecafNet.oversample(image, center_only)
        predictions = self.classify_direct(images)
        return predictions.mean(0)

    def top_k_prediction(self, scores, k):
        """Returns the top k predictions as well as their names as strings.
        
        Input:
            scores: a numpy vector of size 1000 containing the
                predicted scores for the 1000 classes.
        Output:
            indices: the top k prediction indices.
            names: the top k prediction names.
        """
        indices = scores.argsort()
        return (indices[:-(k+1):-1],
                [self.label_names[i] for i in indices[:-(k+1):-1]])

    def feature(self, blob_name):
        """Returns the feature of a specific blob.
        Input:
            blob_name: the name of the blob requested.
        Output:
            array: the numpy array storing the feature.
        """
        # We will copy the feature matrix in case further calls overwrite
        # it.
        return self._net.feature(blob_name).copy()


def main():
    """A simple demo showing how to run decafnet."""
    from decaf.util import smalldata, visualize
    logging.getLogger().setLevel(logging.INFO)
    net = DecafNet()
    lena = smalldata.lena()
    scores = net.classify(lena)
    print 'prediction:', net.top_k_prediction(scores, 5)
    visualize.draw_net_to_file(net._net, 'decafnet.png')
    print 'Network structure written to decafnet.png'


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mpi4py
"""This mpi4py dummy code here is to trigger an exception
so we can check the code under the no mpi case
"""
raise ImportError, "Entering dummy mpi"

if __name__ == "__main__":
    pass

########NEW FILE########
__FILENAME__ = unittest_base
import cPickle as pickle
from decaf import base
import logging
import numpy as np
import numpy.testing as npt
import tempfile
import unittest


class TestBlob(unittest.TestCase):
    def setUp(self):
        pass

    def testBlobInit(self):
        """testBlobInit checks if blobs can be successfully initialized."""
        blob = base.Blob()
        self.assertFalse(blob.has_data())
        self.assertFalse(blob.has_diff())
        blob = base.Blob((1,1))
        self.assertTrue(blob.has_data())
        self.assertFalse(blob.has_diff())
        self.assertEqual(blob.data().shape, (1,1))
    
    def testBlobUpdate(self):
        """testBlobUpdate checks if blob update() succeeds."""
        blob = base.Blob((4,3))
        diff = blob.init_diff()
        diff[:] = 1.
        blob.update()
        npt.assert_array_almost_equal(blob.data(), - blob.diff())

    def testBlobPickle(self):
        blob = base.Blob((4,3))
        blob.data()[:] = np.random.random_sample(blob.data().shape)
        s = pickle.dumps(blob)
        blob_recover = pickle.loads(s)
        npt.assert_array_almost_equal(blob.data(), blob_recover.data())
        # Test pickling an empty blob
        blob = base.Blob()
        s = pickle.dumps(blob)
        blob_recover = pickle.loads(s)
        self.assertFalse(blob_recover.has_data())
        self.assertFalse(blob_recover.has_diff())

    def testBlobSwap(self):
        blob_a = base.Blob((4,3))
        blob_b = base.Blob((4,3))
        blob_a.data().flat = 1.
        blob_b.data().flat = 2.
        blob_a.swap_data(blob_b)
        npt.assert_array_almost_equal(blob_a.data(), 2.)
        npt.assert_array_almost_equal(blob_b.data(), 1.)

    def testUseBlob(self):
        """testUseBlob checks if simple blob usages work."""
        blob_a = base.Blob((4,3))
        blob_b = base.Blob((3,4))
        output = np.dot(blob_a.data(), blob_b.data())
        self.assertEqual(output.shape, (4,4))
        blob_c = base.Blob((4,4))
        output = np.dot(blob_a.data().T, blob_c.data())
        self.assertEqual(output.shape, (3,4))


class TestNet(unittest.TestCase):
    def setUp(self):
        self.decaf_net = base.Net()
        self.decaf_net.add_layer(base.Layer(name='a'), provides='data')
        self.decaf_net.add_layer(base.Layer(name='b'), needs='data')
        self.decaf_net.add_layer(base.Layer(name='c'), needs='data')
        self.decaf_net.finish()

    def testSplit(self):
        """testSplit tests if a net is able to insert split layers correctly.
        """
        self.assertEqual(len(self.decaf_net.layers), 4)
        self.assertEqual(len(self.decaf_net.blobs), 3)
        self.assertTrue(any(isinstance(layer, base.SplitLayer)
                             for layer in self.decaf_net.layers.values()))
    
    def testVisualize(self):
        from decaf.util import visualize
        try:
            import pydot
            visualize.draw_net_to_file(self.decaf_net, tempfile.mktemp('.png'))
        except (ImportError, pydot.InvocationException):
            raise unittest.SkipTest(
                'pydot not configured correctly. Skipping test.')
        self.assertTrue(True)

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_blasdot
from decaf.util import blasdot
import numpy as np
import unittest

class TestBlasdot(unittest.TestCase):
    """Test the blasdot module
    """
    def setUp(self, dtype=None):
        self.test_matrices = [
            (np.random.rand(1,1),
             np.random.rand(1,1)),
            (np.random.rand(1,5),
             np.random.rand(5,1)),
            (np.random.rand(5,1),
             np.random.rand(1,5)),
            (np.random.rand(5,5), 
             np.random.rand(5,5)),
            (np.random.rand(4,5),
             np.random.rand(5,4)),
            (np.random.rand(5,4),
             np.random.rand(4,5))]
        if dtype:
            self.test_matrices = [(m[0].astype(dtype), m[1].astype(dtype))
                                  for m in self.test_matrices]
        # Add the order-f case
        self.test_matrices += \
            [(a.copy(order='F'), b) for a, b in self.test_matrices] + \
            [(a, b.copy(order='F')) for a, b in self.test_matrices] + \
            [(a.copy(order='F'), b.copy(order='F'))
             for a, b in self.test_matrices]
        # Add explicit transpose
        self.test_matrices += [(b.T, a.T) for a,b in self.test_matrices]

    def testdot(self):
        for A, B in self.test_matrices:
            result = blasdot.dot(A, B)
            result_ref = np.dot(A,B)
            self.assertTrue(result.flags.c_contiguous)
            np.testing.assert_array_almost_equal(result, result_ref)
    
    def testdot_with_out(self):
        for A, B in self.test_matrices:
            result_ref = np.dot(A,B)
            # c order
            result = np.empty(result_ref.shape, dtype = A.dtype)
            blasdot.dot(A, B, out = result)
            self.assertTrue(result.flags.c_contiguous)
            np.testing.assert_array_almost_equal(result, result_ref)
            # f order
            result = np.empty(result_ref.shape, dtype = A.dtype, order='f')
            blasdot.dot(A, B, out = result)
            self.assertTrue(result.flags.f_contiguous)
            np.testing.assert_array_almost_equal(result, result_ref)


@unittest.skipIf(not blasdot._HAS_GPU, 
                 'No cuda gpu found.')
class TestBlasdotGPU(TestBlasdot):
    def setUp(self):
        blasdot.switch_backend('gpu')
        TestBlasdot.setUp(self, dtype=np.float32)
        
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = unittest_dropout
from decaf import base
from decaf.layers import dropout
from decaf.layers import fillers
import numpy as np
import unittest

class TestDropout(unittest.TestCase):
    def testdropoutlayer(self):
        layer = dropout.DropoutLayer(name='dropout', ratio=0.5)
        np.random.seed(1701)
        filler = fillers.RandFiller(min=1, max=2)
        bottom = base.Blob((100,4), filler=filler)
        top = base.Blob()
        # run the dropout layer
        layer.forward([bottom], [top])
        # simulate a diff
        fillers.RandFiller().fill(top.init_diff())
        layer.backward([bottom], [top], True)
        np.testing.assert_array_equal(top.data()[top.data()!=0] * 0.5,
                                      bottom.data()[top.data()!=0])
        np.testing.assert_array_equal(bottom.diff()[top.data() == 0],
                                      0)
        np.testing.assert_array_equal(bottom.diff()[top.data() != 0],
                                      top.diff()[top.data() != 0] * 2.)
        # test if debug_freeze works
        layer = dropout.DropoutLayer(name='dropout', ratio=0.5,
                                     debug_freeze=True)
        layer.forward([bottom], [top])
        snapshot = top.data().copy()
        layer.forward([bottom], [top])
        np.testing.assert_array_equal(snapshot, top.data())


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_fillers
from decaf import base
from decaf.layers import fillers
import numpy as np
import unittest

class TestFillers(unittest.TestCase):
    def testXavierFiller(self):
        np.random.seed(1701)
        filler = fillers.XavierFiller()
        mat = np.empty((100, 10))
        filler.fill(mat)
        scale = np.sqrt(3. / 100.)
        self.assertGreaterEqual(mat.min(), -scale)
        self.assertLessEqual(mat.max(), scale)
        self.assertLessEqual(mat.min(), -scale * 0.9)
        self.assertGreaterEqual(mat.max(), scale * 0.9)
        mat = np.empty((20, 5, 10))
        filler.fill(mat)
        self.assertGreaterEqual(mat.min(), -scale)
        self.assertLessEqual(mat.max(), scale)
        self.assertLessEqual(mat.min(), -scale * 0.9)
        self.assertGreaterEqual(mat.max(), scale * 0.9)

    def testXavierGaussianFiller(self):
        np.random.seed(1701)
        mat = np.empty((100, 1000))
        mat_ref = np.empty((100,1000))
        fillers.XavierGaussianFiller().fill(mat)
        fillers.XavierFiller().fill(mat_ref)
        self.assertAlmostEqual(mat.std(), mat_ref.std(), places=3)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_convolution
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestConvolutionGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testConvolutionGrad(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-4)
        shapes = [(1,5,5,1), (1,5,5,3)]
        num_kernels = 2
        params = [(3,1,'valid'), (3,1,'same'), (3,1,'full'), (2,1,'valid'), (2,1,'full'),
                  (3,2,'valid'), (3,2,'same'), (3,2,'full')]
        for shape in shapes:
            for ksize, stride, mode in params:
                print(ksize, stride, mode, shape)
                input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
                layer = core_layers.ConvolutionLayer(
                    name='conv', ksize=ksize, stride=stride, mode=mode,
                    num_kernels=num_kernels,
                    filler=fillers.GaussianRandFiller())
                result = checker.check(layer, [input_blob], [output_blob])
                print(result)
                self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_deconvolution
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestDeconvolutionGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testDeconvolutionGrad(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-4)
        shapes = [(1,3,3,1), (1,3,3,2)]
        params = [(3,1,'valid'), (3,1,'same'), (3,1,'full'), (2,1,'valid'), (2,1,'full'),
                  (3,2,'valid'), (3,2,'same'), (3,2,'full')]
        for shape in shapes:
            for num_channels in range(1, 3):
                for ksize, stride, mode in params:
                    print(num_channels, ksize, stride, mode, shape)
                    input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
                    layer = core_layers.DeconvolutionLayer(
                        name='deconv', ksize=ksize, stride=stride, mode=mode,
                        num_channels=num_channels,
                        filler=fillers.GaussianRandFiller())
                    result = checker.check(layer, [input_blob], [output_blob])
                    print(result)
                    self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_dropout
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestDropoutGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testDropoutGrad(self):
        np.random.seed(1701)
        input_blob = base.Blob((4,3), filler=fillers.GaussianRandFiller())
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-5)
        
        layer = core_layers.DropoutLayer(name='dropout', ratio=0.5,
                                         debug_freeze=True)
        result = checker.check(layer, [input_blob], [output_blob])
        print(result)
        self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_group_convolution
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestGroupConvolutionGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testGroupConvolutionGrad(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-3)
        shapes = [(1,5,5,4)]
        num_kernels = 1
        group = 2
        params = [(3,1,'valid'), (3,1,'same'), (3,1,'full'), (2,1,'valid'), (2,1,'full'),
                  (3,2,'valid'), (3,2,'same'), (3,2,'full')]
        for shape in shapes:
            for ksize, stride, mode in params:
                print(ksize, stride, mode, shape)
                input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
                layer = core_layers.GroupConvolutionLayer(
                    name='gconv', ksize=ksize, stride=stride, mode=mode,
                    num_kernels=num_kernels, group=group,
                    filler=fillers.GaussianRandFiller())
                result = checker.check(layer, [input_blob], [output_blob])
                self.assertEqual(output_blob.data().shape[-1], num_kernels * group)
                print(result)
                self.assertTrue(result[0])
        # check if we will be able to produce an exception
        input_blob = base.Blob((1,5,5,3), filler=fillers.GaussianRandFiller())
        self.assertRaises(RuntimeError, checker.check,
                          layer, [input_blob], [output_blob])
        

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_im2col
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestIm2colGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testIm2colGrad(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-4)
        shapes = [(1,5,5,1), (1,5,5,3), (1,4,3,1), (1,4,3,3)]
        params = [(2,1), (2,2), (3,1), (3,2)] 
        for psize, stride in params:
            for shape in shapes:
                input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
                layer = core_layers.Im2colLayer(name='im2col', psize=psize, stride=stride)
                result = checker.check(layer, [input_blob], [output_blob])
                print(result)
                self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_innerproduct
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestInnerproductGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testInnerproductGrad(self):
        np.random.seed(1701)
        input_blob = base.Blob((4,3), filler=fillers.GaussianRandFiller())
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-5)
        
        ip_layer = core_layers.InnerProductLayer(
            name='ip', num_output=5, bias=True,
            filler=fillers.GaussianRandFiller(),
            bias_filler=fillers.GaussianRandFiller(),
            reg=None)
        result = checker.check(ip_layer, [input_blob], [output_blob])
        print(result)
        self.assertTrue(result[0])
        
        ip_layer = core_layers.InnerProductLayer(
            name='ip', num_output=5, bias=False,
            filler=fillers.GaussianRandFiller(),
            reg=None)
        result = checker.check(ip_layer, [input_blob], [output_blob])
        print(result)
        self.assertTrue(result[0])

        ip_layer = core_layers.InnerProductLayer(
            name='ip', num_output=5, bias=True,
            filler=fillers.GaussianRandFiller(),
            bias_filler=fillers.GaussianRandFiller(),
            reg=regularization.L2Regularizer(weight=0.1))
        result = checker.check(ip_layer, [input_blob], [output_blob])
        print(result)
        self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_loss
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestLossGrad(unittest.TestCase):
    def setUp(self):
        pass

    def _testWeight(self, layer, input_blobs):
        layer.forward(input_blobs, [])
        loss = layer.backward(input_blobs, [], True)
        layer.spec['weight'] = layer.spec['weight'] / 2
        layer.forward(input_blobs, [])
        self.assertAlmostEqual(
            layer.backward(input_blobs, [], True),
            loss / 2.)
        layer.spec['weight'] = layer.spec['weight'] * 2


    def testSquaredLossGrad(self):
        np.random.seed(1701)
        shapes = [(4,3), (1,10), (4,3,2)]
        layer = core_layers.SquaredLossLayer(name='squared')
        checker = gradcheck.GradChecker(1e-6)
        for shape in shapes:
            input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
            target_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
            result = checker.check(layer, [input_blob,target_blob], [],
                                   check_indices = [0])
            print(result)
            self.assertTrue(result[0])
            # also, check if weight works.
            self._testWeight(layer, [input_blob, target_blob])

    def testLogisticLossGrad(self):
        np.random.seed(1701)
        layer = core_layers.LogisticLossLayer(name='logistic')
        checker = gradcheck.GradChecker(1e-6)
        input_blob = base.Blob((10,1), filler=fillers.GaussianRandFiller())
        target_blob = base.Blob((10,), dtype=np.int,
                                filler=fillers.RandIntFiller(high=2))
        result = checker.check(layer, [input_blob,target_blob], [],
                               check_indices = [0])
        print(result)
        self.assertTrue(result[0])
        # also, check if weight works.
        self._testWeight(layer, [input_blob, target_blob])
    
    def testAutoencoderLossGrad(self):
        np.random.seed(1701)
        shapes = [(4,3), (1,10), (4,3,2)]
        layer = core_layers.AutoencoderLossLayer(name='loss', ratio=0.5)
        checker = gradcheck.GradChecker(1e-5)
        for shape in shapes:
            input_blob = base.Blob(shape, filler=fillers.RandFiller(min=0.05, max=0.95))
            result = checker.check(layer, [input_blob], [])
            print(result)
            self.assertTrue(result[0])
            # also, check if weight works.
            self._testWeight(layer, [input_blob])

    def testMultinomialLogisticLossGrad(self):
        np.random.seed(1701)
        layer = core_layers.MultinomialLogisticLossLayer(name='loss')
        checker = gradcheck.GradChecker(1e-6)
        shape = (10,5)
        # check index input
        input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
        target_blob = base.Blob(shape[:1], dtype=np.int,
                                filler=fillers.RandIntFiller(high=shape[1]))
        result = checker.check(layer, [input_blob, target_blob], [],
                               check_indices = [0])
        print(result)
        self.assertTrue(result[0])
        # also, check if weight works.
        self._testWeight(layer, [input_blob, target_blob])
        
        # check full input
        target_blob = base.Blob(shape, filler=fillers.RandFiller())
        # normalize target
        target_data = target_blob.data()
        target_data /= target_data.sum(1)[:, np.newaxis]
        result = checker.check(layer, [input_blob, target_blob], [],
                               check_indices = [0])
        print(result)
        self.assertTrue(result[0])
        # also, check if weight works.
        self._testWeight(layer, [input_blob, target_blob])

    def testKLDivergenceLossGrad(self):
        np.random.seed(1701)
        layer = core_layers.KLDivergenceLossLayer(name='loss')
        checker = gradcheck.GradChecker(1e-6)
        shape = (4,5)
        # For the input, we make sure it is not too close to 0 (which would
        # create numerical issues).
        input_blob = base.Blob(shape,
                               filler=fillers.RandFiller(min=0.1, max=0.9))
        # normalize input blob
        input_data = input_blob.data()
        input_data /= input_data.sum(1)[:, np.newaxis]
        # check index input
        target_blob = base.Blob(shape[:1], dtype=np.int,
                                filler=fillers.RandIntFiller(high=shape[1]))
        result = checker.check(layer, [input_blob, target_blob], [],
                               check_indices = [0])
        print(result)
        self.assertTrue(result[0])
        # also, check if weight works.
        self._testWeight(layer, [input_blob, target_blob])
        
        # check full input
        target_blob = base.Blob(shape, filler=fillers.RandFiller())
        # normalize target
        target_data = target_blob.data()
        target_data /= target_data.sum(1)[:, np.newaxis]
        result = checker.check(layer, [input_blob, target_blob], [],
                               check_indices = [0])
        print(result)
        self.assertTrue(result[0])
        # also, check if weight works.
        self._testWeight(layer, [input_blob, target_blob])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_normalizer
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest
import os
import sys

class TestNormalizer(unittest.TestCase):
    def setUp(self):
        pass

    def testMeanNormalizeLayer(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-5)
        shapes = [(1,5,5,1), (1,5,5,3), (5,5), (1,5)]
        for shape in shapes:
            input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
            layer = core_layers.MeanNormalizeLayer(
                name='normalize')
            result = checker.check(layer, [input_blob], [output_blob])
            print(result)
            self.assertTrue(result[0])
    
    def testResponseNormalizeLayer(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-5)
        shapes = [(1,5,5,1), (1,5,5,3), (5,5), (1,5)]
        for shape in shapes:
            input_blob = base.Blob(shape,
                                   filler=fillers.RandFiller(min=0.1, max=1.))
            layer = core_layers.ResponseNormalizeLayer(
                name='normalize')
            result = checker.check(layer, [input_blob], [output_blob])
            print(result)
            self.assertTrue(result[0])

    # The following test is known to fail on my macbook when multiple OMP
    # threads are being used, so I will simply skip it.
    @unittest.skipIf(sys.platform.startswith('darwin') and 
                     ('OMP_NUM_THREADS' not in os.environ or
                      os.environ['OMP_NUM_THREADS'] != '1'),
                     "Known to not work on macs.")

    def testLocalResponseNormalizeLayer(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-6)
        shapes = [(1,10), (5,10)]
        alphas = [1.0, 2.0]
        betas = [0.75, 1.0]
        for shape in shapes:
            for alpha in alphas:
                for beta in betas:
                    input_blob = base.Blob(shape, filler=fillers.RandFiller())
                    # odd size
                    layer = core_layers.LocalResponseNormalizeLayer(
                        name='normalize', k = 1., alpha=alpha, beta=beta, size=5)
                    result = checker.check(layer, [input_blob], [output_blob])
                    print(result)
                    self.assertTrue(result[0])
                    layer = core_layers.LocalResponseNormalizeLayer(
                        name='normalize', k = 2., alpha=alpha, beta=beta, size=5)
                    result = checker.check(layer, [input_blob], [output_blob])
                    print(result)
                    self.assertTrue(result[0])
                    # even size
                    layer = core_layers.LocalResponseNormalizeLayer(
                        name='normalize', k = 1., alpha=alpha, beta=beta, size=6)
                    result = checker.check(layer, [input_blob], [output_blob])
                    print(result)
                    self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_padding
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestPaddingGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testPaddingGrad(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-5)
        shapes = [(1,5,5,1), (1,5,5,3), (1,4,3,1), (1,4,3,3)]
        pads = [1,2,3]
        for pad in pads:
            for shape in shapes:
                input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
                layer = core_layers.PaddingLayer(name='padding', pad=pad)
                result = checker.check(layer, [input_blob], [output_blob])
                print(result)
                self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_pooling
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestPoolingGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testPoolingGrad(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        checker = gradcheck.GradChecker(1e-4)
        shapes = [(1,7,7,1), (2,7,7,1), (1,7,7,3), (1,8,8,3), (1,13,13,1), (1,13,13,2)]
        params = [(3,2,'max'), (3,2,'ave'),(3,3,'max'), (3,3,'ave'),
                  (5,3,'max'), (5,3,'ave'),(5,5,'max'), (5,5,'ave')]
        for shape in shapes:
            for psize, stride, mode in params:
                print(psize, stride, mode, shape)
                input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
                layer = core_layers.PoolingLayer(
                    name='pool', psize=psize, stride=stride, mode=mode)
                result = checker.check(layer, [input_blob], [output_blob])
                print(result)
                self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_relu
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestReLUGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testReLUGrad(self):
        np.random.seed(1701)
        shapes = [(4,3), (1,10), (2,5,5,1), (2,5,5,3)]
        output_blob = base.Blob()
        layer = core_layers.ReLULayer(name='relu')
        checker = gradcheck.GradChecker(1e-5)
        for shape in shapes:
            input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
            result = checker.check(layer, [input_blob], [output_blob])
            print(result)
            self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_sigmoid
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestSigmoidGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testSigmoidGrad(self):
        np.random.seed(1701)
        shapes = [(4,3), (1,10), (2,5,5,1), (2,5,5,3)]
        output_blob = base.Blob()
        layer = core_layers.SigmoidLayer(name='sigmoid')
        checker = gradcheck.GradChecker(1e-5)
        for shape in shapes:
            input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
            # let's check the forward results by the way
            layer.forward([input_blob], [output_blob])
            np.testing.assert_array_almost_equal(
                output_blob.data(), 1. / (1. + np.exp(-input_blob.data())))
            result = checker.check(layer, [input_blob], [output_blob])
            print(result)
            self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_softmax
from decaf import base
from decaf.layers import core_layers, fillers
from decaf.util import gradcheck
import numpy as np
import unittest


class TestSoftmaxGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testSoftmaxGrad(self):
        np.random.seed(1701)
        input_blob = base.Blob((10,5), filler=fillers.GaussianRandFiller())
        output_blob = base.Blob()
        layer = core_layers.SoftmaxLayer(name='softmax')
        checker = gradcheck.GradChecker(1e-5)
        result = checker.check(layer, [input_blob], [output_blob])
        print(result)
        self.assertTrue(result[0])
        # Also, let's check the result
        pred = input_blob.data()
        prob = np.exp(pred) / np.exp(pred).sum(1)[:, np.newaxis]
        np.testing.assert_array_almost_equal(
            output_blob.data(), prob)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_gradcheck_split
from decaf import base
from decaf.layers import fillers
from decaf.util import gradcheck
import numpy as np
import unittest


class TestSplitGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testSplitGrad(self):
        np.random.seed(1701)
        output_blobs = [base.Blob(), base.Blob()]
        checker = gradcheck.GradChecker(1e-5)
        shapes = [(5,4), (5,1), (1,5), (1,5,5), (1,5,5,3), (1,5,5,1)]
        for shape in shapes:
            input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
            layer = base.SplitLayer(name='split')
            result = checker.check(layer, [input_blob], output_blobs)
            print(result)
            self.assertTrue(result[0])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_identity
from decaf import base
from decaf.layers import identity, fillers
import numpy as np
import unittest

class TestIdentity(unittest.TestCase):
    def testIdentityLayer(self):
        layer = identity.IdentityLayer(name='identity')
        np.random.seed(1701)
        filler = fillers.RandFiller()
        bottom = base.Blob((100,4), filler=filler)
        top = base.Blob()
        # run the dropout layer
        layer.forward([bottom], [top])
        # simulate a diff
        fillers.RandFiller().fill(top.init_diff())
        layer.backward([bottom], [top], True)
        np.testing.assert_array_equal(top.data(), bottom.data())
        np.testing.assert_array_equal(top.diff(), bottom.diff())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_im2col
from decaf import base
from decaf.layers import core_layers, fillers, regularization
import numpy as np
import unittest


class TestIm2col(unittest.TestCase):
    def setUp(self):
        pass

    def testIm2col(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        shapes = [(1,5,5,1), (1,5,5,3), (1,4,3,1), (1,4,3,3),
                  (3,5,5,1), (3,5,5,3), (3,4,3,1), (3,4,3,3)]
        params = [(2,1), (2,2), (3,1), (3,2)] 
        for psize, stride in params:
            for shape in shapes:
                input_blob = base.Blob(shape, filler=fillers.GaussianRandFiller())
                layer = core_layers.Im2colLayer(name='im2col',
                                                psize=psize, stride=stride)
                layer.forward([input_blob], [output_blob])
                # compare against naive implementation
                for i in range(0, shape[1] - psize - 1, stride):
                    for j in range(0, shape[2] - psize - 1, stride):
                        np.testing.assert_array_almost_equal(
                            output_blob.data()[:, i, j].flatten(),
                            input_blob.data()[:,
                                              i*stride:i*stride+psize,
                                              j*stride:j*stride+psize,
                                              :].flatten())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_imagenet_pipeline
"""A code to perform logistic regression."""
import cPickle as pickle
from decaf import base
from decaf.layers import core_layers
from decaf.layers import regularization
from decaf.layers import fillers
import logging
import numpy as np
import os
import sys
import unittest

def imagenet_layers():
    return [
        core_layers.ConvolutionLayer(
            name='conv-220-3-to-55-96', num_kernels=96, ksize=11,
            stride=4, mode='same', filler=fillers.XavierFiller()),
        core_layers.ReLULayer(name='relu-55-96'),
        core_layers.LocalResponseNormalizeLayer(
            name='lrn-55-96', k=2., alpha=0.0001, beta=0.75, size=5),
        core_layers.PoolingLayer(
            name='pool-55-to-27', psize=3, stride=2, mode='max'),
        core_layers.GroupConvolutionLayer(
            name='conv-27-256', num_kernels=128, group=2, ksize=5,
            stride=1, mode='same', filler=fillers.XavierFiller()),
        core_layers.ReLULayer(name='relu-27-256'),
        core_layers.LocalResponseNormalizeLayer(
            name='lrn-27-256', k=2., alpha=0.0001, beta=0.75, size=5),
        core_layers.PoolingLayer(
            name='pool-27-to-13', psize=3, stride=2, mode='max'),
        core_layers.ConvolutionLayer(
            name='conv-13-384', num_kernels=384, ksize=3,
            stride=1, mode='same', filler=fillers.XavierFiller()),
        core_layers.ReLULayer(name='relu-13-384'),
        core_layers.GroupConvolutionLayer(
            name='conv-13-384-second', num_kernels=192, group=2, ksize=3,
            stride=1, mode='same', filler=fillers.XavierFiller()),
        core_layers.ReLULayer(name='relu-13-384-second'),
        core_layers.GroupConvolutionLayer(
            name='conv-13-256', num_kernels=128, group=2, ksize=3,
            stride=1, mode='same', filler=fillers.XavierFiller()),
        core_layers.ReLULayer(name='relu-13-256'),
        core_layers.PoolingLayer(
            name='pool-13-to-6', psize=3, stride=2, mode='max'),
        core_layers.FlattenLayer(name='flatten'),
        core_layers.InnerProductLayer(
            name='fully-1', num_output=4096,
            filler=fillers.XavierFiller()),
        core_layers.ReLULayer(name='relu-full1'),
        core_layers.InnerProductLayer(
            name='fully-2', num_output=4096,
            filler=fillers.XavierFiller()),
        core_layers.ReLULayer(name='relu-full2'),
        core_layers.InnerProductLayer(
            name='predict', num_output=1000,
            filler=fillers.XavierFiller()),
    ]

def imagenet_data():
    """We will create a dummy imagenet data of one single image."""
    data = np.random.rand(1, 220, 220, 3).astype(np.float32)
    label = np.random.randint(1000, size=1)
    dataset = core_layers.NdarrayDataLayer(name='data', sources=[data, label])
    return dataset

class TestImagenet(unittest.TestCase):
    def setUp(self):
        np.random.seed(1701)
    
    def testPredict(self):
        # testPredict tests performing prediction without loss layer.
        decaf_net = base.Net()
        # add data layer
        decaf_net.add_layers(imagenet_data(),
                             provides=['image', 'label'])
        decaf_net.add_layers(imagenet_layers(),
                             needs='image',
                             provides='prediction')
        decaf_net.finish()
        result = decaf_net.predict()
        self.assertTrue('label' in result)
        self.assertTrue('prediction' in result)
        self.assertEqual(result['prediction'].shape[-1], 1000)


    def testForwardBackward(self):
        # testForwardBackward tests the full f-b path.
        decaf_net = base.Net()
        # add data layer
        decaf_net.add_layers(imagenet_data(),
                             provides=['image', 'label'])
        decaf_net.add_layers(imagenet_layers(),
                             needs='image',
                             provides='prediction')
        loss_layer = core_layers.MultinomialLogisticLossLayer(
            name='loss')
        decaf_net.add_layer(loss_layer,
                            needs=['prediction', 'label'])
        decaf_net.finish()
        loss = decaf_net.forward_backward()
        self.assertGreater(loss, 0.)
        self.assertLess(loss, 10.)
    
    def testForwardBackwardWithPrevLayer(self):
        decaf_net = base.Net()
        prev_net = base.Net()
        # add data layer
        prev_net.add_layers(imagenet_data(),
                             provides=['image', 'label'])
        decaf_net.add_layers(imagenet_layers(),
                             needs='image',
                             provides='prediction')
        loss_layer = core_layers.MultinomialLogisticLossLayer(
            name='loss')
        decaf_net.add_layer(loss_layer,
                            needs=['prediction', 'label'])
        prev_net.finish()
        decaf_net.finish()
        loss = decaf_net.forward_backward(previous_net=prev_net)
        self.assertGreater(loss, 0.)
        self.assertLess(loss, 10.)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_layers_innerproduct
from decaf import base
from decaf.layers import innerproduct
import numpy as np
import unittest

class TestInnerProduct(unittest.TestCase):
    """Test the blasdot module
    """
    def setUp(self):
        self.test_sizes = [(10,5), (1,1), (10,1), (1,5)]
        self.test_output_sizes = [1, 5, 10]
        self.test_blobs = [base.Blob(size, np.float32)
                           for size in self.test_sizes]
        self.test_blobs += [base.Blob(size, np.float64)
                            for size in self.test_sizes]

    def testForwardBackwardSize(self):
        for blob in self.test_blobs:
            for num_output in self.test_output_sizes:
                top_blob = base.Blob()
                decaf_layer = innerproduct.InnerProductLayer(
                    name='ip', num_output=num_output)
                decaf_layer.forward([blob], [top_blob])
                self.assertTrue(top_blob.has_data())
                self.assertEqual(top_blob.data().shape[0], blob.data().shape[0])
                self.assertEqual(top_blob.data().shape[1], num_output)
                # test backward
                top_diff = top_blob.init_diff()
                top_diff[:] = 1.
                decaf_layer.backward([blob], [top_blob], propagate_down=True)
                self.assertTrue(blob.has_diff())
                self.assertEqual(blob.diff().shape, blob.data().shape)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_local_response_normalization
from decaf.layers.cpp import wrapper
import logging
import numpy as np
import numpy.testing as npt
import unittest


class TestLRN(unittest.TestCase):
    def setUp(self):
        pass
    
    def reference_forward_implementation(self, features, size, k, alpha, beta):
        """A reference implementation of the local response normalization."""
        num_data = features.shape[0]
        channels = features.shape[1]
        output = np.zeros_like(features)
        scale = np.zeros_like(features)
        for n in range(num_data):
            for c in range(channels):
                local_start = c - (size - 1) / 2
                local_end = local_start + size
                local_start = max(local_start, 0)
                local_end = min(local_end, channels)
                scale[n, c] = k + \
                    (features[n, local_start:local_end]**2).sum() * \
                    alpha / size
                output[n, c] = features[n, c] / (scale[n, c] ** beta)
        return output, scale

    def testLocalResponseNormalizationForward(self):
        np.random.seed(1701)
        dtypes = [np.float32, np.float64]
        for dtype in dtypes:
            features = np.random.rand(5, 10).astype(dtype)
            output = np.random.rand(5, 10).astype(dtype)
            scale = np.random.rand(5, 10).astype(dtype)
            # odd size, k = 1
            wrapper.lrn_forward(features, output, scale, 5, 1., 1.5, 0.75)
            output_ref, scale_ref = self.reference_forward_implementation(
                features, 5, 1., 1.5, 0.75)
            np.testing.assert_array_almost_equal(output, output_ref)
            np.testing.assert_array_almost_equal(scale, scale_ref)
            # odd size, k = 2
            wrapper.lrn_forward(features, output, scale, 5, 2., 1.5, 0.75)
            output_ref, scale_ref = self.reference_forward_implementation(
                features, 5, 2., 1.5, 0.75)
            np.testing.assert_array_almost_equal(output, output_ref)
            np.testing.assert_array_almost_equal(scale, scale_ref)
            # even size
            wrapper.lrn_forward(features, output, scale, 6, 1., 1.5, 0.75)
            output_ref, scale_ref = self.reference_forward_implementation(
                features, 6, 1., 1.5, 0.75)
            np.testing.assert_array_almost_equal(output, output_ref)
            np.testing.assert_array_almost_equal(scale, scale_ref)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_opt
from decaf import base
from decaf.layers import core_layers
from decaf.layers import fillers
from decaf.opt import core_solvers
from decaf.util import mpi
import numpy as np
import unittest

class TestLBFGS(unittest.TestCase):
    """Test the blasdot module
    """

    def _testSolver(self, solver):
        # We are going to test if the solver correctly deals with the mpi case
        # where multiple nodes host different data. To this end we will
        # create a dummy regression problem which, when run under mpi with
        # >1 nodes, will create a different result from a single-node run.
        np.random.seed(1701)
        X = base.Blob((10, 1),
                      filler=fillers.GaussianRandFiller(
                          mean=mpi.RANK, std=0.01))
        Y = base.Blob((10, 1),
                      filler=fillers.ConstantFiller(value=mpi.RANK + 1.))
        decaf_net = base.Net()
        decaf_net.add_layer(core_layers.InnerProductLayer(name='ip',
                                                          num_output=1),
                            needs='X', provides='pred')
        decaf_net.add_layer(core_layers.SquaredLossLayer(name='loss'),
                            needs=['pred','Y'])
        decaf_net.finish()
        solver.solve(decaf_net, previous_net = {'X': X, 'Y': Y})
        w, b = decaf_net.layers['ip'].param()
        print w.data(), b.data()
        if mpi.SIZE == 1:
            # If size is 1, we are fitting y = 0 * x + 1
            np.testing.assert_array_almost_equal(w.data(), 0., 2)
            np.testing.assert_array_almost_equal(b.data(), 1., 2)
        else:
            # if size is not 1, we are fitting y = x + 1
            np.testing.assert_array_almost_equal(w.data(), 1., 2)
            np.testing.assert_array_almost_equal(b.data(), 1., 2)
        self.assertTrue(True)

    def testLBFGS(self):
        # create solver
        solver = core_solvers.LBFGSSolver(
            lbfgs_args={'disp': 0, 'pgtol': 1e-8})
        self._testSolver(solver)

    def testSGD(self):
        # create solver
        solver = core_solvers.SGDSolver(
            base_lr=1., max_iter=1000, lr_policy='inv',
            gamma=0.1, momentum=0.5)
        self._testSolver(solver)

    def testAdagrad(self):
        # create solver
        solver = core_solvers.AdagradSolver(
            base_lr=1., max_iter=1000, base_accum=1.e-8)
        self._testSolver(solver)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_pooling
from decaf import base
from decaf.layers import core_layers, fillers, regularization
from decaf.util import gradcheck
import numpy as np
import unittest


class TestPoolingGrad(unittest.TestCase):
    def setUp(self):
        pass

    def testPoolingGrad(self):
        np.random.seed(1701)
        output_blob = base.Blob()
        input_blob = base.Blob((1,8,8,3), filler=fillers.GaussianRandFiller())
        psize = 3
        stride = 2
        mode = 'max'
        layer = core_layers.PoolingLayer(
            name='pool', psize=psize, stride=stride, mode=mode)
        layer.forward([input_blob], [output_blob])
        img = input_blob.data()[0]
        output = output_blob.data()[0]
        print img.shape, output.shape
        for i in range(output.shape[0]):
            for j in range(output.shape[1]):
                for c in range(output.shape[2]):
                    self.assertAlmostEqual(
                        output[i,j,c],
                        img[i*stride:i*stride+psize,
                            j*stride:j*stride+psize,
                            c].max())
        mode = 'ave'
        layer = core_layers.PoolingLayer(
            name='pool', psize=psize, stride=stride, mode=mode)
        layer.forward([input_blob], [output_blob])
        img = input_blob.data()[0]
        output = output_blob.data()[0]
        print img.shape, output.shape
        for i in range(output.shape[0]):
            for j in range(output.shape[1]):
                for c in range(output.shape[2]):
                    self.assertAlmostEqual(
                        output[i,j,c],
                        img[i*stride:i*stride+psize,
                            j*stride:j*stride+psize,
                            c].mean())


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_puff
import cPickle as pickle
from decaf import puff
import logging
import numpy as np
import numpy.testing as npt
import tempfile
import unittest


class TestPuff(unittest.TestCase):
    def setUp(self):
        pass

    def testPuffVectorForm(self):
        fname = tempfile.mktemp()
        data = np.random.rand(4)
        puff.write_puff(data, fname)
        # Now, let's read it
        puff_recovered = puff.Puff(fname)
        npt.assert_array_almost_equal(puff_recovered.read_all(), data)
        self.assertTrue(puff_recovered.read_all().shape, (4,))
        puff_recovered.seek(0)
        npt.assert_array_almost_equal(puff_recovered.read(2), data[:2])
        self.assertTrue(puff_recovered.read(2).shape, (2,))

    def testPuffShardedVectorForm(self):
        fname = tempfile.mktemp()
        data = np.random.rand(4)
        for i in range(3):
            puff.write_puff(data, fname + '-%d-of-3' % i)
        puff_recovered = puff.Puff(fname + '-*-of-3')
        npt.assert_array_almost_equal(puff_recovered.read_all(),
                                      np.hstack([data] * 3))
        self.assertTrue(puff_recovered.read_all().shape, (12,))
        puff_recovered.seek(0)
        npt.assert_array_almost_equal(puff_recovered.read(2), data[:2])
        self.assertTrue(puff_recovered.read(2).shape, (2,))

    def testPuffSingleWrite(self):
        fname = tempfile.mktemp()
        data = np.random.rand(4,3)
        puff.write_puff(data, fname)
        # Now, let's read it
        puff_recovered = puff.Puff(fname)
        npt.assert_array_almost_equal(puff_recovered.read_all(), data)

    def testPuffMultipleWrites(self):
        fname = tempfile.mktemp()
        data = np.random.rand(4,3)
        writer = puff.PuffStreamedWriter(fname)
        writer.write_batch(data)
        writer.write_batch(data)
        writer.write_single(data[0])
        writer.finish()
        # Now, let's read it
        puff_recovered = puff.Puff(fname)
        data_recovered = puff_recovered.read_all()
        npt.assert_array_almost_equal(data_recovered[:4], data)
        npt.assert_array_almost_equal(data_recovered[4:8], data)
        npt.assert_array_almost_equal(data_recovered[8], data[0])

    def testPuffMultipleWriteException(self):
        fname = tempfile.mktemp()
        data = np.random.rand(4,3)
        writer = puff.PuffStreamedWriter(fname)
        writer.write_batch(data)
        self.assertRaises(
            TypeError, writer.write_batch, data.astype(np.float32))
        self.assertRaises(
            TypeError, writer.write_batch, np.random.rand(4,2))

    def testPuffIteration(self):
        fname = tempfile.mktemp()
        data = np.random.rand(10,3)
        puff.write_puff(data, fname)
        puff_recovered = puff.Puff(fname)
        count = 0
        for elem in puff_recovered:
            count += 1
        self.assertEqual(count, 10)
        for i, elem in zip(range(10), puff_recovered):
            npt.assert_array_almost_equal(data[i], elem)
        # test local slicing
        puff_recovered.set_range(3,7)
        count = 0
        for elem in puff_recovered:
            count += 1
        self.assertEqual(count, 4)
        for i, elem in zip(range(4), puff_recovered):
            npt.assert_array_almost_equal(data[i+3], elem)

    def testPuffShardedIteration(self):
        fname = tempfile.mktemp()
        data = np.random.rand(30,3)
        for i in range(3):
            puff.write_puff(data[i*10:(i+1)*10], fname + '-%d-of-3' % i)
        puff_recovered = puff.Puff(fname + '-*-of-3')
        count = 0
        for elem in puff_recovered:
            count += 1
        self.assertEqual(count, 30)
        for i, elem in zip(range(30), puff_recovered):
            npt.assert_array_almost_equal(data[i], elem)
        # test local slicing
        puff_recovered.set_range(3,17)
        count = 0
        for elem in puff_recovered:
            count += 1
        self.assertEqual(count, 14)
        for i, elem in zip(range(14), puff_recovered):
            npt.assert_array_almost_equal(data[i+3], elem)

    def testPuffReadBoundary(self):
        fname = tempfile.mktemp()
        data = np.random.rand(4,3)
        puff.write_puff(data, fname)
        # Now, let's read it
        puff_recovered = puff.Puff(fname)
        npt.assert_array_almost_equal(puff_recovered.read(3), data[:3])
        npt.assert_array_almost_equal(puff_recovered.read(3),
                                      data[np.array([3,0,1], dtype=int)])
        # test seeking
        puff_recovered.seek(1)
        npt.assert_array_almost_equal(puff_recovered.read(2), data[1:3])

    def testPuffReadSlice(self):
        fname = tempfile.mktemp()
        data = np.random.rand(10,3)
        puff.write_puff(data, fname)
        # Now, let's read it as a slice
        data = data[5:9]
        puff_recovered = puff.Puff(fname, start=5, end=9)
        npt.assert_array_almost_equal(puff_recovered.read(3), data[:3])
        npt.assert_array_almost_equal(puff_recovered.read(3),
                                      data[np.array([3,0,1], dtype=int)])
        # test incorrect seeking
        self.assertRaises(ValueError, puff_recovered.seek, 0)

    def testPuffShardedReadSlice(self):
        fname = tempfile.mktemp()
        data = np.random.rand(30,3)
        for i in range(3):
            puff.write_puff(data[i*10:(i+1)*10], fname + '-%d-of-3' % i)
        data = data[5:27]
        puff_recovered = puff.Puff(fname + '-*-of-3', start=5, end=27)
        npt.assert_array_almost_equal(puff_recovered.read(3), data[:3])
        npt.assert_array_almost_equal(puff_recovered.read_all(), data)
        self.assertRaises(ValueError, puff_recovered.seek, 0)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_util_mpi
from decaf import base
from decaf.util import mpi
import numpy as np
import os
import unittest

_MPI_TEST_DIR = '/tmp/mpi_test_dir'
_MPI_DUMP_TEST_FILE = '/tmp/iceberk.test.unittest_mpi.dump.npy'

class TestMPI(unittest.TestCase):
    """Test the mpi module
    """
    def setUp(self):
        pass

    def testBasic(self):
        self.assertIsNotNone(mpi.COMM)
        self.assertLess(mpi.RANK, mpi.SIZE)
        self.assertIsInstance(mpi.HOST, str)
        
    def testMkdir(self):
        mpi.mkdir(_MPI_TEST_DIR)
        self.assertTrue(os.path.exists(_MPI_TEST_DIR))
        
    def testAnyAll(self):
        self.assertTrue(mpi.mpi_all(True))
        self.assertFalse(mpi.mpi_all(False))
        self.assertEqual(mpi.mpi_all(mpi.RANK == 0), mpi.SIZE == 1)
        self.assertTrue(mpi.mpi_any(True))
        self.assertFalse(mpi.mpi_any(False))
        self.assertTrue(mpi.mpi_any(mpi.RANK == 0))
    
    def testRootDecide(self):
        self.assertTrue(mpi.root_decide(True))
        self.assertFalse(mpi.root_decide(False))
        self.assertTrue(mpi.root_decide(mpi.RANK == 0))
        self.assertFalse(mpi.root_decide(mpi.RANK != 0))

    def testElect(self):
        result = mpi.elect()
        self.assertLess(result, mpi.SIZE)
        all_results = mpi.COMM.allgather(result)
        self.assertEqual(len(set(all_results)), 1)
        num_presidents = mpi.COMM.allreduce(mpi.is_president())
        self.assertEqual(num_presidents, 1)
    
    def testIsRoot(self):
        if mpi.RANK == 0:
            self.assertTrue(mpi.is_root())
        else:
            self.assertFalse(mpi.is_root())
    
    def testBarrier(self):
        import time
        # sleep for a while, and resume
        time.sleep(mpi.RANK)
        mpi.barrier()
        self.assertTrue(True)

    def testBroadcastBlob(self):
        blob = base.Blob((3,4))
        blob.data()[:] = mpi.RANK
        np.testing.assert_array_almost_equal(blob.data(), mpi.RANK)
        mpi.COMM.Bcast(blob.data())
        np.testing.assert_array_almost_equal(blob.data(), 0)
    
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = unittest_util_translator
import cPickle as pickle
from decaf import base
from decaf.util import translator
from decaf.util import visualize
from matplotlib import pyplot
import numpy as np
import os
import unittest

_TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'convnet_data')
_HAS_TEST_DATA = os.path.exists(os.path.join(_TEST_DATA_DIR, 'layers.pickle'))
_BATCH_SIZE = 32


@unittest.skipIf(not _HAS_TEST_DATA, 
                 'No cuda convnet test data found. Run'
                 ' convnet_data/get_decaf_testdata.sh to get the test data.')
class TestCudaConv(unittest.TestCase):
    """Test the mpi module
    """
    def setUp(self):
        self._layers = pickle.load(open(os.path.join(_TEST_DATA_DIR,
                                                     'layers.pickle')))
        self._data = pickle.load(open(os.path.join(_TEST_DATA_DIR,
                                                   'data',
                                                   'data_batch_5')))
        self._decaf_data = translator.imgs_cudaconv_to_decaf(
            self._data['data'][:_BATCH_SIZE], 32, 3)
        #self._decaf_labels = self._data['labels'].flatten()[:_BATCH_SIZE]
        #self._decaf_labels = self._decaf_labels.astype(np.int)
        self._output_shapes = {'data': (32, 32, 3), 'labels': -1}
        self._net = translator.translate_cuda_network(
            self._layers, self._output_shapes)
        self._net.predict(data=self._decaf_data)
        #visualize.draw_net_to_file(self._net, 'test.png')

    def _testSingleLayer(self, decaf_name, cuda_name, reshape_size=0,
                         reshape_channels=0, decimal=6):
        output = self._net.feature(self._net.provides[decaf_name][0])
        self.assertEqual(output.shape[1:], self._output_shapes[decaf_name])
        ref_data = pickle.load(open(
            os.path.join(_TEST_DATA_DIR, cuda_name, 'data_batch_5')))
        ref_data = ref_data['data'][:_BATCH_SIZE]
        if reshape_size:
            ref_data = translator.imgs_cudaconv_to_decaf(
                ref_data, reshape_size, reshape_channels)
        # We rescale the data so that the decimal specified would also count
        # the original scale of the data.
        maxval = ref_data.max()
        ref_data /= maxval
        output /= maxval
        #print 'data range: [%f, %f], max diff: %f' % (
        #    ref_data.min(), ref_data.max(), np.abs(ref_data - output).max())
        np.testing.assert_array_almost_equal(ref_data, output, decimal)

    def testConv1(self):
        self._testSingleLayer('conv1', 'conv1', 32, 32)

    def testPool1(self):
        self._testSingleLayer('pool1', 'pool1', 16, 32)

    def testPool1Neuron(self):
        self._testSingleLayer('pool1_neuron', 'pool1_neuron', 16, 32)

    def testRnorm1(self):
        self._testSingleLayer('rnorm1', 'rnorm1', 16, 32)

    def testConv2(self):
        self._testSingleLayer('conv2_neuron', 'conv2_neuron', 16, 64)

    def testPool2(self):
        self._testSingleLayer('pool2', 'pool2', 8, 64)

    def testConv3(self):
        self._testSingleLayer('conv3_neuron', 'conv3_neuron', 8, 64, decimal=5)

    def testPool3(self):
        self._testSingleLayer('pool3', 'pool3', 4, 64)

    def testFc64(self):
        self._testSingleLayer('fc64_neuron', 'fc64_neuron')

    def testFc10(self):
        self._testSingleLayer('fc10', 'fc10')

    def testProbs(self):
        self._testSingleLayer('probs', 'probs')

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = dummydata
from decaf import base

class DummyDataLayer(base.Layer):
    """A layer that produces dummy data.
    kwargs:
        shape: the shape to produce.
        dtype: the dtype
    """
    def forward(self, bottom, top):
        data = top[0].init_data(self.spec['shape'], self.spec['dtype'])
        return

########NEW FILE########
__FILENAME__ = sleeplayer
from decaf import base

class SleepLayer(base.Layer):
    """A sleep layer that does nothing other than mapping the blobs,
    and sleeps for a few seconds.
    kwargs:
        sleep: the seconds to sleep.
    """
    def forward(self, bottom, top):
        for bottom_b, bottom_t in zip(bottom, top):
            bottom_t.mirror(bottom_b)
        time.sleep(self.spec['sleep'])
        return

    def backward(self, bottom, up, propagate_down):
        for bottom_b, bottom_t in zip(bottom, top):
            bottom_b.mirror_diff(bottom_t)
        time.sleep(self.spec['sleep'])
        return


########NEW FILE########
__FILENAME__ = blasdot
# pylint: disable=C0103
"""Efficient dot functions by calling the basic blas functions from scipy."""

import numpy as np

# import submodules that implements the blas functions
import _numpy_blasdot

# The default backend would be the numpy blasdot.
_gemm_f_contiguous = _numpy_blasdot._gemm_f_contiguous
_gemm_c_contiguous = _numpy_blasdot._gemm_c_contiguous


def dot(A, B, out=None):
    '''
    a simple wrapper that mimics np.dot (if A and B are both matrices!)
    This function solves the problem that np.dot copies matrices when
    working on transposed matrices.
    Input:
        A, B: two matrices. should be either c-contiguous or f-contiguous
        out: (optional) the output matrix. If it is passed, the matrix should
            have the right shape and should be C_CONTIGUOUS.
    Output:
        out: the output matrix
    Raises:
        TypeError, if the type of matrices is wrong.
    '''
    if out == None:
        out = np.empty((A.shape[0], B.shape[1]), A.dtype, B.dtype)
    # Numpy seems to have bugs dealing with the flags of 1x1 matrices. Thus,
    # if we encounter 1x1 matrices, we manually deal with the calculation.
    if out.size == 1:
        out[:] = np.dot(A.flat, B.flat)
    elif out.flags.f_contiguous:
        out = _gemm_f_contiguous(1.0, A, B, out=out)
    else:
        out = _gemm_c_contiguous(1.0, A, B, out=out)
    return out

def dot_lastdim(A, B, out=None):
    """Performs dot for multi-dimensional matrices A and B, where
    A.shape[-1] = B.shape[0]. The returned matrix should have shape
    A.shape[:-1] + B.shape[1:].

    A and B should both be c-contiguous, otherwise the code will report
    an error.
    """
    if out == None:
        out = np.empty(A.shape[:-1] + B.shape[1:], A.dtype)
    lda = A.size / A.shape[-1]
    dim = A.shape[-1]
    ldb = B.size / B.shape[0]
    # using views
    Aview = A.view()
    Bview = B.view()
    outview = out.view()
    Aview.shape = (lda, dim)
    Bview.shape = (dim, ldb)
    outview.shape = (lda, ldb)
    dot(Aview, Bview, outview)
    return out

def dot_firstdims(A, B, out=None):
    """Performs dot for multi-dimensional matrices A and B, where
    prod(A.shape[:-1]) = prod(B.shape[:-1]), and the result would be
    dot(A.T, B) where A and B are treated as 2-dimensional matrices with shape
    (prod(shape[:-1]), shape[-1]). The returned matrix should have shape
    (A.shape[-1], B.shape[-1]). The code is often encountered in computing the
    gradient in e.g. convolutions.
    
    A and B should both be c-contiguous, otherwise the code will report
    an error.
    """
    if out == None:
        out = np.empty((A.shape[-1], B.shape[-1]), A.dtype)
    lda = A.shape[-1]
    dim = A.size / A.shape[-1]
    ldb = B.shape[-1]
    Aview = A.view()
    Bview = B.view()
    Aview.shape = (dim, lda)
    Bview.shape = (dim, ldb)
    dot(Aview.T, Bview, out)
    return out



########NEW FILE########
__FILENAME__ = gradcheck
"""Utility to perform gradient check using scipy's check_grad method. 
"""

import numpy as np
from scipy import optimize
import unittest


def blobs_to_vec(blobs):
    """Collect the network parameters into a long vector.

    This method is not memory efficient - do NOT use in codes that require
    speed and memory.
    """
    if len(blobs) == 0:
        return np.array(())
    return np.hstack([blob.data().flatten() for blob in blobs])

def blobs_diff_to_vec(blobs):
    """Similar to blobs_to_vec, but copying diff."""
    if len(blobs) == 0:
        return np.array(())
    return np.hstack([blob.diff().flatten() for blob in blobs])

def vec_to_blobs(vec, blobs):
    """Distribute the values in the vec to the blobs.
    """
    current = 0
    for blob in blobs:
        size = blob.data().size
        blob.data().flat = vec[current:current+size]
        current += size

def vec_to_blobs_diff(vec, blobs):
    """Distribute the values in the vec to the blobs' diff part.
    """
    current = 0
    for blob in blobs:
        size = blob.diff().size
        blob.diff().flat = vec[current:current+size]
        current += size


class GradChecker(unittest.TestCase):
    """A gradient checker that utilizes scipy.optimize.check_grad to perform
    the gradient check.

    The gradient checker checks the gradient with respect to both the params
    and the bottom blobs if they exist. It checks 2 types of object functions:
        (1) the squared sum of all the outputs.
        (2) each of the output value.
    The total number of functions to be tested is (num of outputs + 1).

    The check is carried out by the check() function, which checks all the
    cases above. If any error exceeds the threshold, the check function will
    return a tuple: (False, index, err), where index is the index where error
    exceeds threshold, and err is the error value. index=-1 means the squared
    sum case. If all errors are under threshold, the check function will
    return (True, max_err) where max_err is the maximum error encountered.
    """

    def __init__(self, threshold):
        """Initializes the checker.

        Input:
            threshold: the threshold to reject the gradient value.
        """
        self._threshold = threshold
    
    @staticmethod
    def _func_net(x_init, decaf_net):
        """function wrapper for a net."""
        vec_to_blobs(x_init, decaf_net.params())
        return decaf_net.forward_backward()

    @staticmethod
    def _grad_net(x_init, decaf_net):
        """gradient wrapper for a net."""
        vec_to_blobs(x_init, decaf_net.params())
        decaf_net.forward_backward()
        return blobs_diff_to_vec(decaf_net.params())

    # pylint: disable=R0913
    @staticmethod
    def _func(x_init, layer, input_blobs, output_blobs, check_data, idx,
             checked_blobs):
        """The function. It returns the output at index idx, or if idx is
        negative, computes an overall loss by taking the squared sum of all
        output values.
        
        Input:
            x_init: the feature values.
            layer: the layer to be checked.
            input_blobs: the input blobs.
            output_blobs: the output blobs.
            check_data: if True, check the gradient with respect to the input
                data.
            idx: how we compute the loss function. If negative, the loss is
                the squared sum of all output. Note that the regularization
                term of the layer is always added to the loss.
            checked_blobs: when check_data is True, checked_blobs is a sublist
                of the input blobs whose gradients we need to check. Any input
                blob not in the checked_blobs would not be checked.
        """
        if check_data:
            vec_to_blobs(x_init, checked_blobs)
        else:
            vec_to_blobs(x_init, layer.param())
        layer.forward(input_blobs, output_blobs)
        if len(output_blobs) > 0:
            output = blobs_to_vec(output_blobs)
        else:
            # a dummy output
            output = np.array([0])
        for blob in output_blobs:
            blob.init_diff()
        # The layer may have reg terms, so we run a dummy backward
        additional_loss = layer.backward(input_blobs, output_blobs, True)
        if idx < 0:
            return np.dot(output, output) + additional_loss
        else:
            return output[idx] + additional_loss

    #pylint: disable=R0913
    @staticmethod
    def _grad(x_init, layer, input_blobs, output_blobs, check_data, idx,
              checked_blobs):
        """The coarse gradient. See _func for documentation."""
        if check_data:
            vec_to_blobs(x_init, checked_blobs)
        else:
            vec_to_blobs(x_init, layer.param())
        layer.forward(input_blobs, output_blobs)
        # initialize the diff
        for blob in output_blobs:
            blob.init_diff()
        if len(output_blobs) > 0:
            output = blobs_to_vec(output_blobs)
            if idx < 0:
                output *= 2.
            else:
                output[:] = 0
                output[idx] = 1.
            vec_to_blobs_diff(output, output_blobs)
        # Now, get the diff
        if check_data:
            layer.backward(input_blobs, output_blobs, True)
            return blobs_diff_to_vec(checked_blobs)
        else:
            layer.backward(input_blobs, output_blobs, False)
            return blobs_diff_to_vec(layer.param())

    def check_network(self, decaf_net):
        """Checks a whole decaf network. Your network should not contain any
        stochastic components: multiple forward backward passes should produce
        the same value for the same parameters.
        """
        # Run a round to initialize the params.
        decaf_net.forward_backward()
        param_backup = blobs_to_vec(decaf_net.params())
        x_init = param_backup.copy()
        # pylint: disable=E1101
        err = optimize.check_grad(GradChecker._func_net, GradChecker._grad_net,
                                  x_init, decaf_net)
        self.assertLessEqual(err, self._threshold)
        if err > self._threshold:
            return (False, err)
        else:
            return (True, err)

    def check(self, layer, input_blobs, output_blobs, check_indices = None):
        """Checks a layer with given input blobs and output blobs.
        """
        # pre-run to get the input and output shapes.
        if check_indices is None:
            checked_blobs = input_blobs
        else:
            checked_blobs = [input_blobs[i] for i in check_indices]
        layer.forward(input_blobs, output_blobs)
        input_backup = blobs_to_vec(checked_blobs)
        param_backup = blobs_to_vec(layer.param())
        num_output = blobs_to_vec(output_blobs).size
        max_err = 0
        # first, check grad w.r.t. param
        x_init = blobs_to_vec(layer.param())
        if len(x_init) > 0:
            for i in range(-1, num_output):
                # pylint: disable=E1101
                err = optimize.check_grad(
                    GradChecker._func, GradChecker._grad, x_init,
                    layer, input_blobs, output_blobs, False, i, checked_blobs)
                max_err = max(err, max_err)
                self.assertLessEqual(err, self._threshold)
                if err > self._threshold:
                    return (False, i, err, 'param')
            # restore param
            vec_to_blobs(param_backup, layer.param())
        # second, check grad w.r.t. input
        x_init = blobs_to_vec(checked_blobs)
        if len(x_init) > 0:
            for i in range(-1, num_output):
                # pylint: disable=E1101
                err = optimize.check_grad(
                    GradChecker._func, GradChecker._grad, x_init,
                    layer, input_blobs, output_blobs, True, i, checked_blobs)
                max_err = max(err, max_err)
                self.assertLessEqual(err, self._threshold)
                if err > self._threshold:
                    return (False, i, err, 'input')
            # restore input
            vec_to_blobs(input_backup, checked_blobs)
        return (True, max_err)

########NEW FILE########
__FILENAME__ = logexp
"""Safe log and exp computation."""

from decaf.util import pyvml
import numpy as np


def exp(mat, out=None):
    """ A (hacky) safe exp that avoids overflowing
    Input:
        mat: the input ndarray
        out: (optional) the output ndarray. Could be in-place.
    Output:
        out: the output ndarray
    """
    if out is None:
        out = np.empty_like(mat)
    np.clip(mat, -np.inf, 100, out=out)
    pyvml.Exp(out, out)
    return out


def log(mat, out=None):
    """ A (hacky) safe log that avoids nans
    
    Note that if there are negative values in the input, this function does not
    throw an error. Handle these cases with care.
    """
    if out is None:
        out = np.empty_like(mat)
    # pylint: disable=E1101
    np.clip(mat, np.finfo(mat.dtype).tiny, np.inf, out=out)
    pyvml.Ln(out, out)
    return out


########NEW FILE########
__FILENAME__ = mpi
''' mpi implements common util functions based on mpi4py.
'''

import logging
import numpy as np
import os
import random
import socket
import time

# MPI
try:
    from mpi4py import MPI
    COMM = MPI.COMM_WORLD
    _IS_DUMMY = False
except ImportError as error:
    logging.warning(
        "Warning: I cannot import mpi4py. Using a dummpy single noded "
        "implementation instead. The program will run in single node mode "
        "even if you executed me with mpirun or mpiexec.\n"
        "\n"
        "We STRONGLY recommend you to try to install mpi and "
        "mpi4py.\n")
    logging.warning("mpi4py exception message is: %s", error)
    from decaf.util._mpi_dummy import COMM
    _IS_DUMMY = True

RANK = COMM.Get_rank()
SIZE = COMM.Get_size()
HOST = socket.gethostname()

_MPI_PRINT_MESSAGE_TAG = 560710
_MPI_BUFFER_LIMIT = 2 ** 30

# we need to set the random seed different for each mpi instance
logging.info('blop.util.mpi: seting different random seeds for each node.')
random.seed(time.time() * (RANK+1))

def is_dummy():
    '''Returns True if this is a dummy version of MPI.'''
    return _IS_DUMMY

def mkdir(dirname):
    '''make a directory safely.
    
    This function avoids race conditions when writing to a common location.
    '''
    try:
        os.makedirs(dirname)
    except OSError as error:
        if not os.path.exists(dirname):
            raise error


def mpi_any(decision):
    """the logical any() over all instances
    """
    return any(COMM.allgather(decision))


def mpi_all(decision):
    """the logical all() over all instances
    """
    return all(COMM.allgather(decision))


def root_decide(decision):
    """Returns the root decision."""
    return COMM.bcast(decision)


def elect():
    '''elect() randomly chooses a node from all the nodes as the president.
    
    Input:
        None
    Output:
        the rank of the president
    '''
    president = COMM.bcast(np.random.randint(SIZE))
    return president


def is_president():
    ''' Returns true if I am the president, otherwise return false
    '''
    return (RANK == elect())


def is_root():
    '''returns if the current node is root
    '''
    return RANK == 0


def barrier(tag=0, sleep=0.01):
    ''' A better mpi barrier
    
    The original MPI.comm.barrier() may cause idle processes to still occupy
    the CPU, while this barrier waits.
    '''
    if SIZE == 1: 
        return 
    mask = 1 
    while mask < SIZE: 
        dst = (RANK + mask) % SIZE 
        src = (RANK - mask + SIZE) % SIZE 
        req = COMM.isend(None, dst, tag) 
        while not COMM.Iprobe(src, tag): 
            time.sleep(sleep) 
        COMM.recv(None, src, tag) 
        req.Wait() 
        mask <<= 1


def root_log_level(level, name = None):
    """set the log level on root. 
    Input:
        level: the logging level, such as logging.DEBUG
        name: (optional) the logger name
    """
    if is_root():
        log_level(level, name)


def log_level(level, name = None):
    """set the log level on all nodes. 
    Input:
        level: the logging level, such as logging.DEBUG
        name: (optional) the logger name
    """
    logging.getLogger(name).setLevel(level)


if __name__ == "__main__":
    pass

########NEW FILE########
__FILENAME__ = pyvml
"""A module to wrap over vml functions. Requires mkl runtime."""

import ctypes as ct
import logging
import numpy as np

_VML_2VECS = ['Sqr', 'Mul', 'Abs', 'Inv', 'Sqrt', 'InvSqrt', 'Cbrt', 'InvCbrt',
             'Pow2o3', 'Pow3o2', 'Exp', 'Expm1', 'Ln', 'Log10', 'Log1p', 'Cos',
             'Sin', 'Tan', 'Acos', 'Asin', 'Atan', 'Cosh', 'Sinh', 'Tanh',
             'Acosh', 'Asinh', 'Atanh', 'Erf', 'Erfc', 'CdfNorm', 'ErfInv',
             'ErfcInv', 'CdfNormInv']
_VML_3VECS = ['Add', 'Sub', 'Div', 'Pow', 'Hypot', 'Atan2']


def vml_dtype_wrapper(func_name):
    """For a function that has two input types, this function creates a
    wrapper that directs to the correct function.
    """
    float_func = getattr(_DLL, 'vs' + func_name)
    double_func = getattr(_DLL, 'vd' + func_name)
    def _wrapped_func(*args):
        """A function that calls vml functions with checked dtypes."""
        dtype = args[0].dtype
        size = args[0].size
        if not all(arg.dtype == dtype for arg in args):
            raise ValueError('Args should have the same dtype.')
        if not all(arg.size == size for arg in args):
            raise ValueError('Args should have the same size.')
        if not (all(arg.flags.c_contiguous for arg in args) or
                all(arg.flags.f_contiguous for arg in args)):
            raise ValueError('Args should be contiguous in the same way.')
        if args[0].dtype == np.float32:
            return float_func(size, *args)
        elif args[0].dtype == np.float64:
            return double_func(size, *args)
        else:
            raise TypeError('Unsupported type: ' + str(dtype))
    return _wrapped_func


def _set_dll_funcs():
    """Set the restypes and argtypes of the functions."""
    for func_name in _VML_2VECS + _VML_3VECS:
        getattr(_DLL, 'vs' + func_name).restype = None
        getattr(_DLL, 'vd' + func_name).restype = None
    for func_name in _VML_2VECS:
        getattr(_DLL, 'vs' + func_name).argtypes = [
            ct.c_int,
            np.ctypeslib.ndpointer(dtype=np.float32),
            np.ctypeslib.ndpointer(dtype=np.float32)]
        getattr(_DLL, 'vd' + func_name).argtypes = [
            ct.c_int,
            np.ctypeslib.ndpointer(dtype=np.float64),
            np.ctypeslib.ndpointer(dtype=np.float64)]
    for func_name in _VML_3VECS:
        getattr(_DLL, 'vs' + func_name).argtypes = [
            ct.c_int,
            np.ctypeslib.ndpointer(dtype=np.float32),
            np.ctypeslib.ndpointer(dtype=np.float32),
            np.ctypeslib.ndpointer(dtype=np.float32)]
        getattr(_DLL, 'vd' + func_name).argtypes = [
            ct.c_int,
            np.ctypeslib.ndpointer(dtype=np.float64),
            np.ctypeslib.ndpointer(dtype=np.float64),
            np.ctypeslib.ndpointer(dtype=np.float64)]

#################################################
# The main pyvml routine.
#################################################
try:
    # Try to load the mkl dynamic library. This does not support windows yet.
    try:
        _DLL = ct.CDLL('libmkl_rt.so')
    except OSError:
        _DLL = ct.CDLL('libmkl_rt.dylib')
except OSError:
    logging.warning('decaf.util.pyvml: unable to load the mkl library. '
                    'Using fallback options.')
    # implement necessary fallback options.
    # Yangqing's note: I am not writing all the fallbacks, only the necessary
    # ones are provided.
    # pylint: disable=C0103
    Exp = lambda x, y: np.exp(x, out=y)
    Ln = lambda x, y: np.log(x, out=y)
else:
    _set_dll_funcs()
    for name in _VML_2VECS + _VML_3VECS:
        globals()[name] = vml_dtype_wrapper(name)

########NEW FILE########
__FILENAME__ = smalldata
"""Simple utility functions to load small data for demo purpose."""

from decaf import base
import os
from skimage import io
import numpy as np

_DATA_PATH = os.path.join(os.path.dirname(__file__), '_data')

def lena():
    """A simple function to return the lena image."""
    filename = os.path.join(_DATA_PATH, 'lena.png')
    return io.imread(filename)

def whitened_images(dtype=np.float64):
    """Returns the whitened images provided in the Sparsenet website:
        http://redwood.berkeley.edu/bruno/sparsenet/
    The returned data will be in the shape (10,512,512,1) to fit
    the blob convension.
    """
    npzdata = np.load(os.path.join(_DATA_PATH, 'whitened_images.npz'))
    blob = base.Blob(npzdata['images'].shape, dtype)
    blob.data().flat = npzdata['images'].flat
    return blob

########NEW FILE########
__FILENAME__ = timer
"""Implement a timer that can be used to easily record time."""

import time

class Timer(object):
    """Timer implements some sugar functions that works like a stopwatch.
    
    timer.reset() resets the watch
    timer.lap()   returns the time elapsed since the last lap() call
    timer.total() returns the total time elapsed since the last reset
    """

    def __init__(self, template = '{0}h{1}m{2:.2f}s'):
        """Initializes a timer.
        
        Input: 
            template: (optional) a template string that can be used to format
                the timer. Inside the string, use {0} to denote the hour, {1}
                to denote the minute, and {2} to denote the seconds. Default
                '{0}h{1}m{2:.2f}s'
        """
        self._total = time.time()
        self._lap = time.time()
        if template:
            self._template = template
    
    def _format(self, timeval):
        """format the time value according to the template
        """
        hour = int(timeval / 3600.0)
        timeval = timeval % 3600.0
        minute = int (timeval / 60)
        timeval = timeval % 60
        return self._template.format(hour, minute, timeval)

    def reset(self):
        """Press the reset button on the timer
        """
        self._total = time.time()
        self._lap = time.time()
        
    def lap(self, use_template = True):
        """Report the elapsed time of the current lap, and start counting the
        next lap.
        Input:
            use_template: (optional) if True, returns the time as a formatted
                string. Otherwise, return the real-valued time. Default True.
        """
        diff = time.time() - self._lap
        self._lap = time.time()
        if use_template:
            return self._format(diff)
        else:
            return diff
    
    def total(self, use_template = True):
        """Report the total elapsed time of the timer.
        Input:
            use_template: (optional) if True, returns the time as a formatted
                string. Otherwise, return the real-valued time. Default True.
        """
        if use_template:
            return self._format(time.time() - self._total)
        else:
            return time.time() - self._total

########NEW FILE########
__FILENAME__ = transform
"""transform implements a few common functions that are often used in multiple
applications.
"""

import numpy as np
from skimage import transform

def scale_and_extract(image, height, width=None):
    """This function scales the image and then extracts the center part of the
    image with the given height and width.

    Input:
        image: an ndarray or a skimage Image.
        height: the target height of the image.
        width: the target width of the image. If not provided, we will use
            width = height.
    output:
        image_out: an ndarray of (height * width), and of dtype float64.
    """
    if not width:
        width = height
    ratio = max(height / float(image.shape[0]), width / float(image.shape[1]))
    # we add 0.5 to the converted result to avoid numerical problems.
    image_reshape = transform.resize(
        image, (int(image.shape[0] * ratio + 0.5), int(image.shape[1] * ratio + 0.5)))
    h_offset = (image_reshape.shape[0] - height) / 2
    w_offset = (image_reshape.shape[1] - width) / 2
    return image_reshape[h_offset:h_offset+height, w_offset:w_offset+width]


def as_rgb(image):
    """Converts an image that could possibly be a grayscale or RGBA image to
    RGB.
    """
    if image.ndim == 2:
        return np.tile(image[:, :, np.newaxis], (1, 1, 3))
    elif image.shape[2] == 4:
        # An RGBA image. We will only use the first 3 channels.
        return image[:, :, :3]
    else:
        return image

########NEW FILE########
__FILENAME__ = conversions
"""Conversions converts data from the cuda convnet convention to the decaf
convention."""
import numpy as np



def imgs_cudaconv_to_decaf(imgs, size, channels, out=None):
    """Converting a set of images from the cudaconv order (channels first) to
    our order (channels last).
    
    Input:
        imgs: the input image. Should be in the shape
            (num, channels, size, size), but the last 3 dims could be
            flattened as long as the channels come first.
        size: the image size. Input images should be square.
        channels: the number of channels.
        out: (optional) the output matrix.
    """
    if out is None:
        out = np.empty((imgs.shape[0], size, size, channels), imgs.dtype)
    img_view = imgs.view()
    img_view.shape = (imgs.shape[0], channels, size, size)
    for i in range(channels):
        out[:, :, :, i] = img_view[:, i, :, :]
    return out

def img_cudaconv_to_decaf(img, size, channels, out=None):
    """See imgs_cudaconv_to_decaf for details. The only difference is that
    this function deals with a single image of shape (channels, size, size).
    """
    if out is None:
        out = np.empty((size, size, channels), img.dtype)
    return imgs_cudaconv_to_decaf(img[np.newaxis, :], size, channels,
                                  out=out[np.newaxis, :])[0]

########NEW FILE########
__FILENAME__ = registerer
"""registerer is a simple module that allows one to register a custom
translator for a specific cuda layer.

== How to write a custom translator ==
Write your translate function in the format defined under translate_layer
below, and then register it with the type name of the corresponding cuda
convnet. Also, you need to import your module before the translation takes
place so your function actually gets registered.
"""

from decaf import base
from decaf.layers import core_layers
import logging

# OUTPUT_AFFIX is the affix we add to the layer name as the output blob name
# for the corresponding decaf layer.
OUTPUT_AFFIX = '_cudanet_out'
# DATA_TYPENAME is the typename for the data layers at cuda convnet.
DATA_TYPENAME = 'data'
# likewise, cost typename
COST_TYPENAME = 'cost'
# _TRANSLATORS is a dictionary mapping layer names to functions that does the
# actual translations.
_TRANSLATORS = {}


def register_translator(name, translator):
    """Registers a translator."""
    _TRANSLATORS[name] = translator


def default_translator(cuda_layer, output_shapes):
    """A default translator if nothing fits: it will print a warning and then
    return a dummy base.Layer that does nothing.
    """
    input_shape = output_shapes[cuda_layer['inputLayers'][0]['name']]
    output_shapes[cuda_layer['name']] = input_shape
    return core_layers.IdentityLayer(name=cuda_layer['name'])
    

def translate_layer(cuda_layer, output_shapes):
    """Translates a cuda layer to a decaf layer. The function will return
    False if the input layer is a data layer, in which no decaf layer needs to
    be inserted.

    Input:
        cuda_layer: a cuda layer as a dictionary, produced by the cuda convnet
            code.
        output_shapes: a dictionary keeping the output shapes of all the 
            layers.
    Output:
        decaf_layer: the corresponding decaf layer, or False if the input is a
            data layer.
    """
    layertype = cuda_layer['type']
    if layertype == DATA_TYPENAME or layertype.startswith(COST_TYPENAME):
        # if the layer type is data, it is simply a data layer.
        logging.info('Ignoring layer %s (type %s)', cuda_layer['name'],
                     cuda_layer['type'])
        return False
    elif layertype in _TRANSLATORS:
        logging.info('Translating layer %s (type %s)', cuda_layer['name'],
                     cuda_layer['type'])
        return _TRANSLATORS[layertype](cuda_layer, output_shapes)
    else:
        logging.error('No registered translator for %s (type %s),'
                      ' Will return a dummy layer.',
                      cuda_layer['name'], cuda_layer['type'])
        return default_translator(cuda_layer, output_shapes)


def translate_cuda_network(cuda_layers, output_shapes):
    """Translates a list of cuda layers to a decaf net.

    Input:
        cuda_layers: a list of layers from the cuda convnet training.
        output_shapes: a dictionary that contains the specification on the
            input shapes. This dictionary will be modified in-place to add
            the output shapes for the intermediate layers, but you need to
            provide the shapes for all the data layers. For data that are
            going to be scalar, use -1. The shapes should be following the
            decaf convention, not the cuda convnet convention.
    """
    decaf_net = base.Net()
    for cuda_layer in cuda_layers:
        decaf_layer = translate_layer(cuda_layer, output_shapes)
        if not decaf_layer:
            # This layer should be ignored.
            continue
        # Now, let's figure out the parent of the layer
        needs = []
        for idx in cuda_layer['inputs']:
            if cuda_layers[idx]['type'] == DATA_TYPENAME:
                needs.append(cuda_layers[idx]['name'])
            else:
                needs.append(cuda_layers[idx]['name'] + OUTPUT_AFFIX)
        provide = cuda_layer['name'] + OUTPUT_AFFIX
        decaf_net.add_layers(decaf_layer, needs=needs, provides=provide)
    decaf_net.finish()
    return decaf_net


########NEW FILE########
__FILENAME__ = translator_cmrnorm
"""Translates the cmrnorm layer."""
from decaf.util.translator import registerer
from decaf.layers import core_layers


def translator_cmrnorm(cuda_layer, output_shapes):
    """Translates the cmrnorm layer.
    Note: we hard-code the constant in the local response normalization
    layer to be 1. This may be different from Krizhevsky's NIPS paper but
    matches the actual cuda convnet code.
    """
    input_shape = output_shapes[cuda_layer['inputLayers'][0]['name']]
    output_shapes[cuda_layer['name']] = input_shape
    return core_layers.LocalResponseNormalizeLayer(
        name=cuda_layer['name'],
        size=cuda_layer['size'],
        k=1,
        alpha = cuda_layer['scale'] * cuda_layer['size'],
        beta = cuda_layer['pow'])

registerer.register_translator('cmrnorm', translator_cmrnorm)


########NEW FILE########
__FILENAME__ = translator_conv
"""Translates the convolution and group convolution layers."""
from decaf.util.translator import registerer
from decaf.layers import core_layers
import numpy as np

#pylint: disable=R0914
def translator_conv(cuda_layer, output_shapes):
    """Translates the convolution and group convolution layers."""
    group = cuda_layer['groups'][0]
    num_kernels = cuda_layer['filters']
    if num_kernels % group:
        raise ValueError('Incorrect num_kernels and group combination.')
    ksize = cuda_layer['filterSize'][0]
    if not cuda_layer['sharedBiases']:
        raise ValueError('Unshared bias layers not supported yet.')
    stride = cuda_layer['stride'][0]
    pad = -cuda_layer['padding'][0]
    # figure out the output shape
    input_shape = output_shapes[cuda_layer['inputLayers'][0]['name']]
    padded_shape = (input_shape[0] + pad * 2,
                    input_shape[1] + pad * 2,
                    input_shape[2])
    output_shape = ((padded_shape[0] - ksize) / stride + 1,
                    (padded_shape[1] - ksize) / stride + 1,
                    num_kernels)
    output_shapes[cuda_layer['name']] = output_shape
    weight = cuda_layer['weights'][0]
    input_channels = cuda_layer['channels'][0] / group
    weight.resize((input_channels, ksize, ksize, num_kernels))
    converted_weight = np.empty((ksize, ksize, input_channels, num_kernels),
                                weight.dtype)
    for i in range(input_channels):
        converted_weight[:, :, i, :] = weight[i, :, :, :]
    converted_weight.resize(ksize * ksize * input_channels, num_kernels)

    bias = cuda_layer['biases'].flatten().copy()
    if group == 1:
        # We should return a simple convolution layer
        decaf_layer = core_layers.ConvolutionLayer(
            name=cuda_layer['name'],
            num_kernels=num_kernels,
            ksize=ksize,
            stride=stride,
            pad=pad)
        param = decaf_layer.param()
        param[0].mirror(converted_weight)
        param[1].mirror(bias)
    else:
        # We should return a grouped convolution layer
        num_divided_kernels = num_kernels / group
        decaf_layer = core_layers.GroupConvolutionLayer(
            name=cuda_layer['name'],
            num_kernels=num_divided_kernels,
            ksize=ksize,
            stride=stride,
            pad=pad,
            group=group)
        param = decaf_layer.param()
        curr = 0
        for i in range(0, group * 2, 2):
            param[i].mirror(
                converted_weight[:, curr:curr+num_divided_kernels].copy())
            param[i+1].mirror(bias[curr:curr+num_divided_kernels])
            curr += num_divided_kernels
    return decaf_layer

registerer.register_translator('conv', translator_conv)

########NEW FILE########
__FILENAME__ = translator_fc
"""translator_fc translates a fully connected layer to a decaf
InnerProductLayer.
"""
from decaf.util.translator import registerer
from decaf.layers import core_layers
import numpy as np
from operator import mul

def translator_fc(cuda_layer, output_shapes):
    """The translator for the fc layer."""
    input_shape = output_shapes[cuda_layer['inputLayers'][0]['name']]
    input_size = reduce(mul, input_shape)
    num_output = cuda_layer['outputs']
    output_shapes[cuda_layer['name']] = (num_output,)
    decaf_layer = core_layers.InnerProductLayer(
        name=cuda_layer['name'],
        num_output=num_output)
    # put the parameters
    params = decaf_layer.param()
    # weight
    weight = cuda_layer['weights'][0]
    if weight.shape[0] != input_size or weight.shape[1] != num_output:
        raise ValueError('Incorrect shapes: weight shape %s, input shape %s,'
                         ' num_output %d' %
                         (weight.shape, input_shape, num_output))
    if len(input_shape) == 3:
        # The original input is an image, so we will need to reshape it
        weight = weight.reshape(
            (input_shape[2], input_shape[0], input_shape[1], num_output))
        converted_weight = np.empty(input_shape + (num_output,),
                                    weight.dtype)
        for i in range(input_shape[2]):
            converted_weight[:, :, i, :] = weight[i, :, :, :]
        converted_weight.resize(input_size, num_output)
    else:
        converted_weight = weight
    params[0].mirror(converted_weight)
    bias = cuda_layer['biases'][0]
    params[1].mirror(bias)
    if len(input_shape) == 1:
        return decaf_layer
    else:
        # If the input is not a vector, we need to have a flatten layer first.
        return [core_layers.FlattenLayer(name=cuda_layer['name'] + '_flatten'),
                decaf_layer]

registerer.register_translator('fc', translator_fc)

########NEW FILE########
__FILENAME__ = translator_neuron
"""Translates the neuron layers."""
from decaf.util.translator import registerer
from decaf.layers import core_layers
import logging


def translator_neuron(cuda_layer, output_shapes):
    """Translates the neuron layers.
    Note: not all neuron layers are supported. We only implemented those that
    are needed for imagenet.
    """
    output_shapes[cuda_layer['name']] = \
        output_shapes[cuda_layer['inputLayers'][0]['name']]
    neurontype = cuda_layer['neuron']['type']
    if neurontype == 'relu':
        return core_layers.ReLULayer(
            name=cuda_layer['name'])
    elif neurontype == 'dropout':
        return core_layers.DropoutLayer(
            name=cuda_layer['name'], ratio=cuda_layer['neuron']['params']['d'])
    else:
        raise NotImplementedError('Neuron type %s not implemented yet.'
                                  % neurontype)

registerer.register_translator('neuron', translator_neuron)

########NEW FILE########
__FILENAME__ = translator_pool
"""Translates the pooling layers."""
from decaf.util.translator import registerer
from decaf.layers import core_layers
import math

def translator_pool(cuda_layer, output_shapes):
    """Translates the pooling layers."""
    method = cuda_layer['pool']
    if method == 'max':
        pass
    elif method == 'avg':
        # We have a slightly different name
        method = 'ave'
    else:
        raise NotImplementedError('Unrecognized pooling method: %s' % method)
    if cuda_layer['start'] != 0:
        raise NotImplementedError('Unsupported layer with a non-zero start.')
    # Check the outputsX size.
    output_size = math.ceil(
        float(cuda_layer['imgSize'] - cuda_layer['sizeX']) / 
        cuda_layer['stride']) + 1
    if cuda_layer['outputsX'] != output_size:
        raise NotImplementedError('Unsupported layer with custon output size.')
    # If all checks passed, we will return our pooling layer
    psize = cuda_layer['sizeX']
    stride = cuda_layer['stride']
    input_shape = output_shapes[cuda_layer['inputLayers'][0]['name']]
    output_shape = (
        int(math.ceil(float(input_shape[0] - psize) / stride)) + 1,
        int(math.ceil(float(input_shape[1] - psize) / stride)) + 1,
        input_shape[2])
    output_shapes[cuda_layer['name']] = output_shape
    return core_layers.PoolingLayer(
        name=cuda_layer['name'],
        psize=psize,
        stride=stride,
        mode=method)
    

registerer.register_translator('pool', translator_pool)

########NEW FILE########
__FILENAME__ = translator_softmax
"""Translates the softmax layers."""
from decaf.util.translator import registerer
from decaf.layers import core_layers


def translator_softmax(cuda_layer, output_shapes):
    """Translates the softmax layers."""
    input_shape = output_shapes[cuda_layer['inputLayers'][0]['name']]
    output_shapes[cuda_layer['name']] = input_shape
    return core_layers.SoftmaxLayer(
        name=cuda_layer['name'])

registerer.register_translator('softmax', translator_softmax)

########NEW FILE########
__FILENAME__ = visualize
"""Functions that could be used to visualize patches."""

from decaf import base
from matplotlib import cm, pyplot
import numpy as np
import os
import pydot

LAYER_STYLE = {'shape': 'record', 'fillcolor': '#DFECF3',
               'style': 'filled,bold'}
BLOB_STYLE = {'shape': 'record', 'fillcolor': '#FEF9E3',
              'style': 'rounded,filled'}

def draw_net(decaf_net, ext='png'):
    """Draws a decaf net and returns the image string encoded using the given
    extension.
    
    Input:
        decaf_net: a decaf net.
        ext: the image extension. Default 'png'.
    """
    pydot_graph = pydot.Dot(graph_type='digraph')
    pydot_nodes = {}
    for name, layer in decaf_net.layers.iteritems():
        pydot_nodes[name] = pydot.Node(
            '{%s|%s}' % (name, layer.__class__.__name__), **LAYER_STYLE)
    for name, blob in decaf_net.blobs.iteritems():
        if blob.has_data():
            shapestr = 'x'.join(str(v) for v in blob.data().shape[1:])
            if blob.data().ndim == 1:
                shapestr = 'scalar'
            dtypestr = str(blob.data().dtype)
        else:
            shapestr = 'unknown shape'
            dtypestr = 'unknown dtype'
        pydot_nodes[name] = pydot.Node(
            '{%s|%s|%s}' % (name, shapestr, dtypestr), **BLOB_STYLE)
    for name in pydot_nodes:
        pydot_graph.add_node(pydot_nodes[name])
    # only write explicit edges
    for layername, blobnames in decaf_net.provides.iteritems():
        if layername.startswith(base.DECAF_PREFIX):
            continue
        for blobname in blobnames:
            pydot_graph.add_edge(
                pydot.Edge(pydot_nodes[layername], pydot_nodes[blobname]))
    for layername, blobnames in decaf_net.needs.iteritems():
        if layername.startswith(base.DECAF_PREFIX):
            continue
        for blobname in blobnames:
            pydot_graph.add_edge(
                pydot.Edge(pydot_nodes[blobname], pydot_nodes[layername]))
    return pydot_graph.create(format=ext)

def draw_net_to_file(decaf_net, filename):
    """Draws a decaf net, and saves it to file using the format given as the
    file extension.
    """
    ext = os.path.splitext(filename)[-1][1:]
    with open(filename, 'w') as fid:
        fid.write(draw_net(decaf_net, ext))


class PatchVisualizer(object):
    '''PatchVisualizer visualizes patches.
    '''
    def __init__(self, gap = 1):
        self.gap = gap
    
    def show_single(self, patch):
        """Visualizes one single patch. The input patch could be a vector (in
        which case we try to infer the shape of the patch), a 2-D matrix, or a
        3-D matrix whose 3rd dimension has 3 channels.
        """
        if len(patch.shape) == 1:
            patch = patch.reshape(self.get_patch_shape(patch))
        elif len(patch.shape) > 2 and patch.shape[2] != 3:
            raise ValueError('The input patch shape is incorrect.')
        # determine color
        if len(patch.shape) == 2:
            pyplot.imshow(patch, cmap = cm.gray)
        else:
            pyplot.imshow(patch)
        return patch
    
    def show_multiple(self, patches, ncols = None, bg_func = np.min):
        """Visualize multiple patches. In the passed in patches matrix, each row
        is a patch, in the shape of either n*n or n*n*3, either in a flattened
        format (so patches would be an 2-D array), or a multi-dimensional tensor
        (so patches will be higher dimensional). We will try our best to figure
        out automatically the patch size.
        """
        num_patches = patches.shape[0]
        if ncols is None:
            ncols = int(np.ceil(np.sqrt(num_patches)))
        nrows = int(np.ceil(num_patches / float(ncols)))
        if len(patches.shape) == 2:
            patches = patches.reshape((patches.shape[0],) + 
                                  self.get_patch_shape(patches[0]))
        patch_size_expand = np.array(patches.shape[1:3]) + self.gap
        image_size = patch_size_expand * np.array([nrows, ncols]) - self.gap
        if len(patches.shape) == 4:
            if patches.shape[3] != 3:
                raise ValueError('The input patch shape is incorrect.')
            # color patches
            image_shape = tuple(image_size) + (3,)
            cmap = None
        else:
            image_shape = tuple(image_size)
            cmap = cm.gray
        image = np.ones(image_shape) * bg_func(patches)
        for pid in range(num_patches):
            row = pid / ncols * patch_size_expand[0]
            col = pid % ncols * patch_size_expand[1]
            image[row:row+patches.shape[1], col:col+patches.shape[2]] = \
                    patches[pid]
        # normalize the patches for better viewing results
        image -= np.min(image)
        image /= np.max(image) + np.finfo(np.float64).eps
        pyplot.imshow(image, cmap = cmap, interpolation='nearest')
        pyplot.axis('off')
        return image
    
    def show_channels(self, patch, bg_func = np.min):
        """ This function shows the channels of a patch. The incoming patch
        should have shape [height, width, num_channels], and each channel will
        be visualized as a separate gray patch.
        """
        if len(patch.shape) != 3:
            raise ValueError("The input patch shape %s isn't correct."
                             % str(patch.shape))
        patch_reordered = np.swapaxes(patch.T, 1, 2)
        return self.show_multiple(patch_reordered, bg_func = bg_func)

    def show_blob(self, blob):
        """This function shows a blob by trying really hard to figure out what
        type of blob it is, and what is the best way to visualize it.
        """
        if isinstance(blob, base.Blob):
            data = blob.data()
        else:
            data = blob
        # TODO: figure out how to find the best function of the bg function.
        bg_func = np.max
        if data.ndim == 4:
            # We will first see if the first dim has shape 1, in which case we
            # will just call the 3-dim version.
            if data.shape[0] == 1:
                return self.show_blobs(data[0], bg_func=bg_func)
            elif data.shape[-1] == 3:
                # see if it could be visualized as color images
                return self.show_multiple(data, bg_func=bg_func)
            elif data.shape[-1] == 1:
                # see if it could be visualized as grayscale images
                return self.show_multiple(data[:,:,:,0], bg_func=bg_func)
            else:
                # We will show the blob organized as a two-dimensional tiling of
                # blocks, where the rows are data points and cols are channels.
                num, height, width, channels = data.shape
                data = data.swapaxes(2,3).swapaxes(1,2)
                data = data.reshape(num*channels, height, width)
                return self.show_multiple(data, ncols=channels, bg_func=bg_func)
        elif data.ndim == 3:
            # We will first see if the last dim has shape 1 or 3.
            if data.shape[-1] == 1:
                return self.show_single(data[:,:,0])
            elif data.shape[-1] == 3:
                return self.show_single(data)
            else:
                # If not, we will show the data channel by channel.
                return self.show_channels(data, bg_func=bg_func)
        elif data.ndim == 2:
            # When the data dimension is 2, we do nothing but simply showing
            # the image.
            return self.show_single(data)

    
    def get_patch_shape(self, patch):
        """Gets the patch shape of a single patch. Basically it tries to
        interprete the patch as a square, and also check if it is in color (3
        channels)
        """
        edge_len = np.sqrt(patch.size)
        if edge_len != np.floor(edge_len):
            # we are given color patches
            edge_len = np.sqrt(patch.size / 3.)
            if edge_len != np.floor(edge_len):
                raise ValueError('Cannot determine patch shape from %d.'
                                 % patch.size)
            return (int(edge_len), int(edge_len), 3)
        else:
            edge_len = int(edge_len)
            return (edge_len, edge_len)

_DEFAULT_VISUALIZER = PatchVisualizer()


# Wrappers to utility functions that directly points to functions in the
# default visualizer.

def show_single(*args, **kwargs):
    """Wrapper of PatchVisualizer.show_single()"""
    return _DEFAULT_VISUALIZER.show_single(*args, **kwargs)

def show_multiple(*args, **kwargs):
    """Wrapper of PatchVisualizer.show_multiple()"""
    return _DEFAULT_VISUALIZER.show_multiple(*args, **kwargs)

def show_channels(*args, **kwargs):
    """Wrapper of PatchVisualizer.show_channels()"""
    return _DEFAULT_VISUALIZER.show_channels(*args, **kwargs)

def show_blob(*args, **kwargs):
    """Wrapper of PatchVisualizer.show_blob()"""
    return _DEFAULT_VISUALIZER.show_blob(*args, **kwargs)

########NEW FILE########
__FILENAME__ = _mpi_dummy
# pylint: disable=C0103, C0111, W0613
"""This implements some dummy functions that mimics the MPI behavior when the
size is 1. It is here solely to provide (probably limited) ability to run single
noded tasks when one cannot install mpi or mpi4py.
"""

import copy

class COMM(object):
    """The dummy mpi common world.
    """
    def __init__(self):
        raise RuntimeError, "COMM should not be instantiated."
    
    @staticmethod
    def Get_rank():
        return 0
    
    @staticmethod
    def Get_size():
        return 1
    
    @staticmethod
    def allgather(sendobj):
        return [copy.copy(sendobj)]
    
    @staticmethod
    def Allreduce(sendbuf, recvbuf, op = None):
        recvbuf[:] = sendbuf[:]
    
    @staticmethod
    def allreduce(sendobj, op = None):
        return copy.copy(sendobj)
    
    @staticmethod
    def bcast(sendobj, root = 0):
        return copy.copy(sendobj)
    
    @staticmethod
    def Bcast(buf, root = 0):
        pass
    
    @staticmethod
    def gather(sendobj, root = 0):
        return [copy.copy(sendobj)]
    
    @staticmethod
    def Reduce(sendbuf, recvbuf, op = None, root = 0):
        recvbuf[:] = sendbuf[:]

########NEW FILE########
__FILENAME__ = _numpy_blasdot
# pylint: disable=C0103
"""Efficient dot functions by calling the basic blas functions from scipy."""

import numpy as np
from scipy.linalg.blas import fblas

# pylint: disable=R0912
def _gemm_f_contiguous(alpha, A, B, out):
    '''A gemm function that uses scipy fblas functions, avoiding matrix copy
    when the input is transposed.
    
    The returned matrix is designed to be F_CONTIGUOUS.
    '''
    if out.shape != (A.shape[0], B.shape[1]):
        raise ValueError("Incorrect output shape.")
    if out.dtype != A.dtype:
        raise ValueError("Incorrect output dtype.")
    if not out.flags.f_contiguous:
        raise ValueError("Output is not f-contiguous.")
    if A.dtype != B.dtype:
        raise TypeError('The data type of the matrices should be the same.')
    if A.dtype == np.float32:
        gemm = fblas.sgemm
    elif A.dtype == np.float64:
        gemm = fblas.dgemm
    else:
        raise TypeError('Unfit data type.')
    if A.shape[1] != B.shape[0]:
        raise ValueError("Matrices are not aligned")
    if A.flags.c_contiguous:
        A = A.T
        trans_a = True
    elif A.flags.f_contiguous:
        trans_a = False
    else:
        raise ValueError('Incorrect matrix flags for A.')
    if B.flags.c_contiguous:
        B = B.T
        trans_b = True
    elif B.flags.f_contiguous:
        trans_b = False
    else:
        raise ValueError('Incorrect matrix flags for B.')
    gemm(alpha, a=A, b=B, trans_a=trans_a, trans_b=trans_b, c=out,
         overwrite_c=True)
    return out

def _gemm_c_contiguous(alpha, A, B, out):
    """A wrapper that computes C_CONTIGUOUS gemm results."""
    _gemm_f_contiguous(alpha, B.T, A.T, out=out.T)
    return out

########NEW FILE########
__FILENAME__ = _blob
"""The module that implements Blob, the basic component that contains a piece
of matrix in addition to its gradients.
"""

import cPickle as pickle
import numpy as np


# pylint: disable=R0903
class Blob(object):
    """Blob is the data structure that holds a piece of numpy array as well as
    its gradient so that we can accumulate and pass around data more easily.

    We define two numpy matrices: one is data, which stores the data in the
    current blob; the other is diff (short for difference): when a network
    runs its forward and backward pass, diff will store the gradient value;
    when a solver goes through the blobs, diff will then be replaced with the
    value to update.

    The diff matrix will not be created unless you explicitly run init_diff,
    as many Blobs do not need the gradients to be computed.
    """
    def __init__(self, shape=None, dtype=None, filler=None):
        self._data = None
        self._diff = None
        self._filler = filler
        if shape is not None:
            self.init_data(shape, dtype)

    @staticmethod
    def blob_like(source_blob):
        """Create a blob that is similar to the source blob (same shape, same
        dtype, and same filler).
        """
        return Blob(source_blob._data.shape, source_blob._data.dtype,
                    source_blob._filler)

    def clear(self):
        """Clears a blob data."""
        self._data = None
        self._diff = None

    def mirror(self, input_array, shape=None):
        """Create the data as a view of the input array. This is useful to
        save space and avoid duplication for data layers.
        """
        if isinstance(input_array, Blob):
            income_data = input_array.data()
        else:
            income_data = input_array.view()
        # check if the shape or dtype changed, in which case we need to
        # reset the diff
        if (self.has_data() and (self._data.shape != income_data.shape
                                 or self._data.dtype != income_data.dtype)):
            self._diff = None
        self._data = income_data
        if shape is not None:
            self._data.shape = shape
        return self.data()
   
    def mirror_diff(self, input_array, shape=None):
        """Create the diff as a view of the input array's diff. This is useful
        to save space and avoid duplication for data layers.
        """
        if isinstance(input_array, Blob):
            self._diff = input_array.diff()
        else:
            self._diff = input_array.view()
        if shape is not None:
            self._diff.shape = shape
        return self.diff()

    def has_data(self):
        """Checks if the blob has data."""
        return self._data is not None
    
    def data(self):
        """Returns a view of the data."""
        if self.has_data():
            return self._data.view()

    def has_diff(self):
        """Checks if the blob has diff."""
        return self._diff is not None

    def diff(self):
        """Returns a view of the diff."""
        if self.has_diff():
            return self._diff.view()

    def update(self):
        """Update the data field by SUBTRACTING diff to it.
        
        Note that diff is often used to store the gradients, and most often
        we will perform MINIMIZATION. This is why we always do subtraction
        here.
        """
        self._data -= self._diff

    def init_data(self, shape, dtype, setdata=True):
        """Initializes the data if necessary. The filler will be always
        called even if no reallocation of data takes place.
        """
        if not(self.has_data() and self._data.shape == shape and \
           self._data.dtype == dtype):
            self._data = np.empty(shape, dtype)
            # Since we changed the data, the old diff has to be discarded.
            self._diff = None
        if setdata:
            if self._filler is not None:
                self._filler.fill(self._data)
            else:
                self._data[:] = 0
        return self.data()

    def init_diff(self, setzero=True):
        """Initialize the diff in the same format as data.
        
        Returns diff for easy access.
        """
        if not self.has_data():
            raise ValueError('The data should be initialized first!')
        if self.has_diff():
            if setzero:
                self._diff[:] = 0
        else:
            self._diff = np.zeros_like(self._data)
        return self.diff()

    def swap_data(self, other_blob):
        """swaps the data between two blobs."""
        if not(self.has_data() and other_blob.has_data() and
               self._data.dtype == other_blob._data.dtype and
               self._data.shape == other_blob._data.shape):
            raise ValueError('Attempting to swap incompatible blobs.')
        self._data, other_blob._data = other_blob._data, self._data
    
    def __getstate__(self):
        """When pickling, we will simply store the data field and the
        filler of this blob. We do NOT store the diff, since it is often
        binded to a specific run and does not bear much value.
        """
        return self.data(), self._filler
    
    def __setstate__(self, state):
        """Recovers the state."""
        if state[0] is None:
            Blob.__init__(self, filler=state[1])
        else:
            Blob.__init__(self, state[0].shape, state[0].dtype, state[1])
            self._data[:] = state[0]


########NEW FILE########
