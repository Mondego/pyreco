__FILENAME__ = mnist_average_darkness
"""
mnist_average_darkness
~~~~~~~~~~~~~~~~~~~~~~

A naive classifier for recognizing handwritten digits from the MNIST
data set.  The program classifies digits based on how dark they are
--- the idea is that digits like "1" tend to be less dark than digits
like "8", simply because the latter has a more complex shape.  When
shown an image the classifier returns whichever digit in the training
data had the closest average darkness.

The program works in two steps: first it trains the classifier, and
then it applies the classifier to the MNIST test data to see how many
digits are correctly classified.

Needless to say, this isn't a very good way of recognizing handwritten
digits!  Still, it's useful to show what sort of performance we get
from naive ideas."""

#### Libraries
# Standard library
from collections import defaultdict

# My libraries
import mnist_loader

def main():
    training_data, validation_data, test_data = mnist_loader.load_data()
    # training phase: compute the average darknesses for each digit,
    # based on the training data
    avgs = avg_darknesses(training_data)
    # testing phase: see how many of the test images are classified
    # correctly
    num_correct = sum(int(guess_digit(image, avgs) == digit)
                      for image, digit in zip(test_data[0], test_data[1]))
    print "Baseline classifier using average darkness of image."
    print "%s of %s values correct." % (num_correct, len(test_data[1]))

def avg_darknesses(training_data):
    """ Return a defaultdict whose keys are the digits 0 through 9.
    For each digit we compute a value which is the average darkness of
    training images containing that digit.  The darkness for any
    particular image is just the sum of the darknesses for each pixel."""
    digit_counts = defaultdict(int)
    darknesses = defaultdict(float)
    for image, digit in zip(training_data[0], training_data[1]):
        digit_counts[digit] += 1
        darknesses[digit] += sum(image)
    avgs = defaultdict(float)
    for digit, n in digit_counts.iteritems():
        avgs[digit] = darknesses[digit] / n
    return avgs

def guess_digit(image, avgs):
    """Return the digit whose average darkness in the training data is
    closest to the darkness of ``image``.  Note that ``avgs`` is
    assumed to be a defaultdict whose keys are 0...9, and whose values
    are the corresponding average darknesses across the training data."""
    darkness = sum(image)
    distances = {k: abs(v-darkness) for k, v in avgs.iteritems()}
    return min(distances, key=distances.get)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = mnist_loader
"""
mnist_loader
~~~~~~~~~~~~

A library to load the MNIST image data.  For details of the data
structures that are returned, see the doc strings for ``load_data``
and ``load_data_wrapper``.  In practice, ``load_data_wrapper`` is the
function usually called by our neural network code.
"""

#### Libraries
# Standard library
import cPickle
import gzip

# Third-party libraries
import numpy as np

def load_data():
    """Return the MNIST data as a tuple containing the training data,
    the validation data, and the test data.

    The ``training_data`` is returned as a tuple with two entries.
    The first entry contains the actual training images.  This is a
    numpy ndarray with 50,000 entries.  Each entry is, in turn, a
    numpy ndarray with 784 values, representing the 28 * 28 = 784
    pixels in a single MNIST image.

    The second entry in the ``training_data`` tuple is a numpy ndarray
    containing 50,000 entries.  Those entries are just the digit
    values (0...9) for the corresponding images contained in the first
    entry of the tuple.

    The ``validation_data`` and ``test_data`` are similar, except
    each contains only 10,000 images.

    This is a nice data format, but for use in neural networks it's
    helpful to modify the format of the ``training_data`` a little.
    That's done in the wrapper function ``load_data_wrapper()``, see
    below.
    """
    f = gzip.open('../data/mnist.pkl.gz', 'rb')
    training_data, validation_data, test_data = cPickle.load(f)
    f.close()
    return (training_data, validation_data, test_data)

def load_data_wrapper():
    """Return a tuple containing ``(training_data, validation_data,
    test_data)``. Based on ``load_data``, but the format is more
    convenient for use in our implementation of neural networks.

    In particular, ``training_data`` is a list containing 50,000
    2-tuples ``(x, y)``.  ``x`` is a 784-dimensional numpy.ndarray
    containing the input image.  ``y`` is a 10-dimensional
    numpy.ndarray representing the unit vector corresponding to the
    correct digit for ``x``.

    ``validation_data`` and ``test_data`` are lists containing 10,000
    2-tuples ``(x, y)``.  In each case, ``x`` is a 784-dimensional
    numpy.ndarry containing the input image, and ``y`` is the
    corresponding classification, i.e., the digit values (integers)
    corresponding to ``x``.

    Obviously, this means we're using slightly different formats for
    the training data and the validation / test data.  These formats
    turn out to be the most convenient for use in our neural network
    code."""
    tr_d, va_d, te_d = load_data()
    training_inputs = [np.reshape(x, (784, 1)) for x in tr_d[0]]
    training_results = [vectorized_result(y) for y in tr_d[1]]
    training_data = zip(training_inputs, training_results)
    validation_inputs = [np.reshape(x, (784, 1)) for x in va_d[0]]
    validation_data = zip(validation_inputs, va_d[1])
    test_inputs = [np.reshape(x, (784, 1)) for x in te_d[0]]
    test_data = zip(test_inputs, te_d[1])
    return (training_data, validation_data, test_data)

def vectorized_result(j):
    """Return a 10-dimensional unit vector with a 1.0 in the jth
    position and zeroes elsewhere.  This is used to convert a digit
    (0...9) into a corresponding desired output from the neural
    network."""
    e = np.zeros((10, 1))
    e[j] = 1.0
    return e

########NEW FILE########
__FILENAME__ = mnist_svm
"""
mnist_svm
~~~~~~~~~

A classifier program for recognizing handwritten digits from the MNIST
data set, using an SVM classifier."""

#### Libraries
# My libraries
import mnist_loader 

# Third-party libraries
from sklearn import svm

def svm_baseline():
    training_data, validation_data, test_data = mnist_loader.load_data()
    # train
    clf = svm.SVC()
    clf.fit(training_data[0], training_data[1])
    # test
    predictions = [int(a) for a in clf.predict(test_data[0])]
    num_correct = sum(int(a == y) for a, y in zip(predictions, test_data[1]))
    print "Baseline classifier using an SVM."
    print "%s of %s values correct." % (num_correct, len(test_data[1]))

if __name__ == "__main__":
    svm_baseline()
    

########NEW FILE########
__FILENAME__ = network
"""
network.py
~~~~~~~~~~

A module to implement the stochastic gradient descent learning
algorithm for a feedforward neural network.  Gradients are calculated
using backpropagation.  Note that I have focused on making the code
simple, easily readable, and easily modifiable.  It is not optimized,
and omits many desirable features.
"""

#### Libraries
# Standard library
import random

# Third-party libraries
import numpy as np

class Network():

    def __init__(self, sizes):
        """The list ``sizes`` contains the number of neurons in the
        respective layers of the network.  For example, if the list
        was [2, 3, 1] then it would be a three-layer network, with the
        first layer containing 2 neurons, the second layer 3 neurons,
        and the third layer 1 neuron.  The biases and weights for the
        network are initialized randomly, using a Gaussian
        distribution with mean 0, and variance 1.  Note that the first
        layer is assumed to be an input layer, and by convention we
        won't set any biases for those neurons, since biases are only
        ever used in computing the outputs from later layers."""
        self.num_layers = len(sizes)
        self.sizes = sizes
        self.biases = [np.random.randn(y, 1) for y in sizes[1:]]
        self.weights = [np.random.randn(y, x) 
                        for x, y in zip(sizes[:-1], sizes[1:])]

    def feedforward(self, a):
        """Return the output of the network if ``a`` is input."""
        for b, w in zip(self.biases, self.weights):
            a = sigmoid_vec(np.dot(w, a)+b)
        return a

    def SGD(self, training_data, epochs, mini_batch_size, eta,
            test_data=None):
        """Train the neural network using mini-batch stochastic
        gradient descent.  The ``training_data`` is a list of tuples
        ``(x, y)`` representing the training inputs and the desired
        outputs.  The other non-optional parameters are
        self-explanatory.  If ``test_data`` is provided then the
        network will be evaluated against the test data after each
        epoch, and partial progress printed out.  This is useful for
        tracking progress, but slows things down substantially."""
        if test_data: n_test = len(test_data)
        n = len(training_data)
        for j in xrange(epochs):
            random.shuffle(training_data)
            mini_batches = [
                training_data[k:k+mini_batch_size]
                for k in xrange(0, n, mini_batch_size)]
            for mini_batch in mini_batches:
                self.update_mini_batch(mini_batch, eta)
            if test_data:
                print "Epoch {}: {} / {}".format(
                    j, self.evaluate(test_data), n_test)
            else:
                print "Epoch %s complete" % j

    def update_mini_batch(self, mini_batch, eta):
        """Update the network's weights and biases by applying
        gradient descent using backpropagation to a single mini batch.
        The ``mini_batch`` is a list of tuples ``(x, y)``, and ``eta``
        is the learning rate."""
        nabla_b = [np.zeros(b.shape) for b in self.biases]
        nabla_w = [np.zeros(w.shape) for w in self.weights]
        for x, y in mini_batch:
            delta_nabla_b, delta_nabla_w = self.backprop(x, y)
            nabla_b = [nb+dnb for nb, dnb in zip(nabla_b, delta_nabla_b)]
            nabla_w = [nw+dnw for nw, dnw in zip(nabla_w, delta_nabla_w)]
        self.weights = [w-(eta/len(mini_batch))*nw 
                        for w, nw in zip(self.weights, nabla_w)]
        self.biases = [b-(eta/len(mini_batch))*nb 
                       for b, nb in zip(self.biases, nabla_b)]

    def backprop(self, x, y):
        """Return a tuple ``(nabla_b, nabla_w)`` representing the
        gradient for the cost function C_x.  ``nabla_b`` and
        ``nabla_w`` are layer-by-layer lists of numpy arrays, similar
        to ``self.biases`` and ``self.weights``."""
        nabla_b = [np.zeros(b.shape) for b in self.biases]
        nabla_w = [np.zeros(w.shape) for w in self.weights]
        # feedforward
        activation = x
        activations = [x] # list to store all the activations, layer by layer
        zs = [] # list to store all the z vectors, layer by layer
        for b, w in zip(self.biases, self.weights):
            z = np.dot(w, activation)+b
            zs.append(z)
            activation = sigmoid_vec(z)
            activations.append(activation)
        # backward pass
        delta = self.cost_derivative(activations[-1], y) * \
            sigmoid_prime_vec(zs[-1])
        nabla_b[-1] = delta
        nabla_w[-1] = np.dot(delta, activations[-2].transpose())
        # Note that the variable l in the loop below is used a little
        # differently to the notation in Chapter 2 of the book.  Here,
        # l = 1 means the last layer of neurons, l = 2 is the
        # second-last layer, and so on.  It's a renumbering of the
        # scheme in the book, used here to take advantage of the fact
        # that Python can use negative indices in lists.
        for l in xrange(2, self.num_layers):
            z = zs[-l]
            spv = sigmoid_prime_vec(z)
            delta = np.dot(self.weights[-l+1].transpose(), delta) * spv
            nabla_b[-l] = delta
            nabla_w[-l] = np.dot(delta, activations[-l-1].transpose())
        return (nabla_b, nabla_w)

    def evaluate(self, test_data):
        """Return the number of test inputs for which the neural
        network outputs the correct result. Note that the neural
        network's output is assumed to be the index of whichever
        neuron in the final layer has the highest activation."""
        test_results = [(np.argmax(self.feedforward(x)), y) 
                        for (x, y) in test_data]
        return sum(int(x == y) for (x, y) in test_results)
        
    def cost_derivative(self, output_activations, y):
        """Return the vector of partial derivatives \partial C_x /
        \partial a for the output activations."""
        return (output_activations-y) 

#### Miscellaneous functions
def sigmoid(z):
    """The sigmoid function."""
    return 1.0/(1.0+np.exp(-z))

sigmoid_vec = np.vectorize(sigmoid)

def sigmoid_prime(z):
    """Derivative of the sigmoid function."""
    return sigmoid(z)*(1-sigmoid(z))

sigmoid_prime_vec = np.vectorize(sigmoid_prime)

########NEW FILE########
__FILENAME__ = network2
"""network2.py
~~~~~~~~~~~~~~

An improved version of network.py, implementing the stochastic
gradient descent learning algorithm for a feedforward neural network.
Improvements include the addition of the cross-entropy cost function,
regularization, and better initialization of network weights.  Note
that I have focused on making the code simple, easily readable, and
easily modifiable.  It is not optimized, and omits many desirable
features.

"""

#### Libraries
# Standard library
import json
import random
import sys

# Third-party libraries
import numpy as np


#### Define the quadratic and cross-entropy cost functions

class QuadraticCost:

    @staticmethod
    def fn(a, y):
        """Return the cost associated with an output ``a`` and desired output
        ``y``.

        """
        return 0.5*np.linalg.norm(a-y)**2

    @staticmethod
    def delta(z, a, y):
        """Return the error delta from the output layer."""
        return (a-y) * sigmoid_prime_vec(z)


class CrossEntropyCost:

    @staticmethod
    def fn(a, y):
        """Return the cost associated with an output ``a`` and desired output
        ``y``.  Note that np.nan_to_num is used to ensure numerical
        stability.  In particular, if both ``a`` and ``y`` have a 1.0
        in the same slot, then the expression (1-y)*np.log(1-a)
        returns nan.  The np.nan_to_num ensures that that is converted
        to the correct value (0.0).

        """
        return np.nan_to_num(np.sum(-y*np.log(a)-(1-y)*np.log(1-a)))

    @staticmethod
    def delta(z, a, y):
        """Return the error delta from the output layer.  Note that the
        parameter ``z`` is not used by the method.  It is included in
        the method's parameters in order to make the interface
        consistent with the delta method for other cost classes.

        """
        return (a-y)


#### Main Network class
class Network():

    def __init__(self, sizes, cost=CrossEntropyCost):
        """The list ``sizes`` contains the number of neurons in the respective
        layers of the network.  For example, if the list was [2, 3, 1]
        then it would be a three-layer network, with the first layer
        containing 2 neurons, the second layer 3 neurons, and the
        third layer 1 neuron.  The biases and weights for the network
        are initialized randomly, using
        ``self.default_weight_initializer`` (see docstring for that
        method).

        """
        self.num_layers = len(sizes)
        self.sizes = sizes
        self.default_weight_initializer()
        self.cost=cost

    def default_weight_initializer(self):
        """Initialize each weight using a Gaussian distribution with mean 0
        and standard deviation 1 over the square root of the number of
        weights connecting to the same neuron.  Initialize the biases
        using a Gaussian distribution with mean 0 and standard
        deviation 1.

        Note that the first layer is assumed to be an input layer, and
        by convention we won't set any biases for those neurons, since
        biases are only ever used in computing the outputs from later
        layers.

        """
        self.biases = [np.random.randn(y, 1) for y in self.sizes[1:]]
        self.weights = [np.random.randn(y, x)/np.sqrt(x) 
                        for x, y in zip(self.sizes[:-1], self.sizes[1:])]

    def large_weight_initializer(self):
        """Initialize the weights using a Gaussian distribution with mean 0
        and standard deviation 1.  Initialize the biases using a
        Gaussian distribution with mean 0 and standard deviation 1.

        Note that the first layer is assumed to be an input layer, and
        by convention we won't set any biases for those neurons, since
        biases are only ever used in computing the outputs from later
        layers.

        This weight and bias initializer uses the same approach as in
        Chapter 1, and is included for purposes of comparison.  It
        will usually be better to use the default weight initializer
        instead.

        """
        self.biases = [np.random.randn(y, 1) for y in self.sizes[1:]]
        self.weights = [np.random.randn(y, x) 
                        for x, y in zip(self.sizes[:-1], self.sizes[1:])]

    def feedforward(self, a):
        """Return the output of the network if ``a`` is input."""
        for b, w in zip(self.biases, self.weights):
            a = sigmoid_vec(np.dot(w, a)+b)
        return a

    def SGD(self, training_data, epochs, mini_batch_size, eta, 
            lmbda = 0.0, 
            evaluation_data=None, 
            monitor_evaluation_cost=False,
            monitor_evaluation_accuracy=False,
            monitor_training_cost=False, 
            monitor_training_accuracy=False):
        """Train the neural network using mini-batch stochastic gradient
        descent.  The ``training_data`` is a list of tuples ``(x, y)``
        representing the training inputs and the desired outputs.  The
        other non-optional parameters are self-explanatory, as is the
        regularization parameter ``lmbda``.  The method also accepts
        ``evaluation_data``, usually either the validation or test
        data.  We can monitor the cost and accuracy on either the
        evaluation data or the training data, by setting the
        appropriate flags.  The method returns a tuple containing four
        lists: the (per-epoch) costs on the evaluation data, the
        accuracies on the evaluation data, the costs on the training
        data, and the accuracies on the training data.  All values are
        evaluated at the end of each training epoch.  So, for example,
        if we train for 30 epochs, then the first element of the tuple
        will be a 30-element list containing the cost on the
        evaluation data at the end of each epoch. Note that the lists
        are empty if the corresponding flag is not set.

        """
        if evaluation_data: n_data = len(evaluation_data)
        n = len(training_data)
        evaluation_cost, evaluation_accuracy = [], []
        training_cost, training_accuracy = [], []
        for j in xrange(epochs):
            random.shuffle(training_data)
            mini_batches = [
                training_data[k:k+mini_batch_size]
                for k in xrange(0, n, mini_batch_size)]
            for mini_batch in mini_batches:
                self.update_mini_batch(
                    mini_batch, eta, lmbda, len(training_data))
            print "Epoch %s training complete" % j
            if monitor_training_cost:
                cost = self.total_cost(training_data, lmbda)
                training_cost.append(cost)
                print "Cost on training data: {}".format(cost)
            if monitor_training_accuracy:
                accuracy = self.accuracy(training_data, convert=True)
                training_accuracy.append(accuracy)
                print "Accuracy on training data: {} / {}".format(
                    accuracy, n)
            if monitor_evaluation_cost:
                cost = self.total_cost(evaluation_data, lmbda, convert=True)
                evaluation_cost.append(cost)
                print "Cost on evaluation data: {}".format(cost)
            if monitor_evaluation_accuracy:
                accuracy = self.accuracy(evaluation_data)
                evaluation_accuracy.append(accuracy)
                print "Accuracy on evaluation data: {} / {}".format(
                    self.accuracy(evaluation_data), n_data)
            print
        return evaluation_cost, evaluation_accuracy, \
            training_cost, training_accuracy

    def update_mini_batch(self, mini_batch, eta, lmbda, n):
        """Update the network's weights and biases by applying gradient
        descent using backpropagation to a single mini batch.  The
        ``mini_batch`` is a list of tuples ``(x, y)``, ``eta`` is the
        learning rate, ``lmbda`` is the regularization parameter, and
        ``n`` is the total size of the training data set.

        """
        nabla_b = [np.zeros(b.shape) for b in self.biases]
        nabla_w = [np.zeros(w.shape) for w in self.weights]
        for x, y in mini_batch:
            delta_nabla_b, delta_nabla_w = self.backprop(x, y)
            nabla_b = [nb+dnb for nb, dnb in zip(nabla_b, delta_nabla_b)]
            nabla_w = [nw+dnw for nw, dnw in zip(nabla_w, delta_nabla_w)]
        self.weights = [(1-eta*(lmbda/n))*w-(eta/len(mini_batch))*nw 
                        for w, nw in zip(self.weights, nabla_w)]
        self.biases = [b-(eta/len(mini_batch))*nb 
                       for b, nb in zip(self.biases, nabla_b)]

    def backprop(self, x, y):
        """Return a tuple ``(nabla_b, nabla_w)`` representing the
        gradient for the cost function C_x.  ``nabla_b`` and
        ``nabla_w`` are layer-by-layer lists of numpy arrays, similar
        to ``self.biases`` and ``self.weights``."""
        nabla_b = [np.zeros(b.shape) for b in self.biases]
        nabla_w = [np.zeros(w.shape) for w in self.weights]
        # feedforward
        activation = x
        activations = [x] # list to store all the activations, layer by layer
        zs = [] # list to store all the z vectors, layer by layer
        for b, w in zip(self.biases, self.weights):
            z = np.dot(w, activation)+b
            zs.append(z)
            activation = sigmoid_vec(z)
            activations.append(activation)
        # backward pass
        delta = (self.cost).delta(zs[-1], activations[-1], y)
        nabla_b[-1] = delta
        nabla_w[-1] = np.dot(delta, activations[-2].transpose())
        # Note that the variable l in the loop below is used a little
        # differently to the notation in Chapter 2 of the book.  Here,
        # l = 1 means the last layer of neurons, l = 2 is the
        # second-last layer, and so on.  It's a renumbering of the
        # scheme in the book, used here to take advantage of the fact
        # that Python can use negative indices in lists.
        for l in xrange(2, self.num_layers):
            z = zs[-l]
            spv = sigmoid_prime_vec(z)
            delta = np.dot(self.weights[-l+1].transpose(), delta) * spv
            nabla_b[-l] = delta
            nabla_w[-l] = np.dot(delta, activations[-l-1].transpose())
        return (nabla_b, nabla_w)

    def accuracy(self, data, convert=False):
        """Return the number of inputs in ``data`` for which the neural
        network outputs the correct result. The neural network's
        output is assumed to be the index of whichever neuron in the
        final layer has the highest activation.  

        The flag ``convert`` should be set to False if the data set is
        validation or test data (the usual case), and to True if the
        data set is the training data. The need for this flag arises
        due to differences in the way the results ``y`` are
        represented in the different data sets.  In particular, it
        flags whether we need to convert between the different
        representations.  It may seem strange to use different
        representations for the different data sets.  Why not use the
        same representation for all three data sets?  It's done for
        efficiency reasons -- the program usually evaluates the cost
        on the training data and the accuracy on other data sets.
        These are different types of computations, and using different
        representations speeds things up.  More details on the
        representations can be found in
        mnist_loader.load_data_wrapper.

        """
        if convert:
            results = [(np.argmax(self.feedforward(x)), np.argmax(y)) 
                       for (x, y) in data]
        else:
            results = [(np.argmax(self.feedforward(x)), y)
                        for (x, y) in data]
        return sum(int(x == y) for (x, y) in results)

    def total_cost(self, data, lmbda, convert=False):
        """Return the total cost for the data set ``data``.  The flag
        ``convert`` should be set to False if the data set is the
        training data (the usual case), and to True if the data set is
        the validation or test data.  See comments on the similar (but
        reversed) convention for the ``accuracy`` method, above.
        """
        cost = 0.0
        for x, y in data:
            a = self.feedforward(x)
            if convert: y = vectorized_result(y)
            cost += self.cost.fn(a, y)/len(data)
        cost += 0.5*(lmbda/len(data))*sum(
            np.linalg.norm(w)**2 for w in self.weights)
        return cost

    def save(self, filename):
        """Save the neural network to the file ``filename``."""
        data = {"sizes": self.sizes,
                "weights": [w.tolist() for w in self.weights],
                "biases": [b.tolist() for b in self.biases],
                "cost": str(self.cost.__name__)}
        f = open(filename, "w")
        json.dump(data, f)
        f.close()

#### Loading a Network
def load(filename):
    """Load a neural network from the file ``filename``.  Returns an
    instance of Network.

    """
    f = open(filename, "r")
    data = json.load(f)
    f.close()
    cost = getattr(sys.modules[__name__], data["cost"])
    net = Network(data["sizes"], cost=cost)
    net.weights = [np.array(w) for w in data["weights"]]
    net.biases = [np.array(b) for b in data["biases"]]
    return net

#### Miscellaneous functions
def vectorized_result(j):
    """Return a 10-dimensional unit vector with a 1.0 in the j'th position
    and zeroes elsewhere.  This is used to convert a digit (0...9)
    into a corresponding desired output from the neural network.

    """
    e = np.zeros((10, 1))
    e[j] = 1.0
    return e

def sigmoid(z):
    """The sigmoid function."""
    return 1.0/(1.0+np.exp(-z))

sigmoid_vec = np.vectorize(sigmoid)

def sigmoid_prime(z):
    """Derivative of the sigmoid function."""
    return sigmoid(z)*(1-sigmoid(z))

sigmoid_prime_vec = np.vectorize(sigmoid_prime)

########NEW FILE########
__FILENAME__ = common_knowledge
"""
common_knowledge
~~~~~~~~~~~~~~~~

Try to determine whether or not it's possible to relate the
descriptions given by two different autoencoders.

"""

#### Libraries
# My libraries
from backprop2 import Network, sigmoid_vec
import mnist_loader

# Third-party libraries
import matplotlib
import matplotlib.pyplot as plt
import numpy as np


#### Parameters
# Size of the training sets.  May range from 1000 to 12,500.  Lower
# will be faster, higher will give more accuracy.
SIZE = 5000 
# Number of hidden units in the autoencoder
HIDDEN = 30

print "\nGenerating training data"
training_data, _, _ = mnist_loader.load_data_nn()
td_1 = [(x, x) for x, _ in training_data[0:SIZE]]
td_2 = [(x, x) for x, _ in training_data[12500:12500+SIZE]]
td_3 = [x for x, _ in training_data[25000:25000+SIZE]]
test = [x for x, _ in training_data[37500:37500+SIZE]]

print "\nFinding first autoencoder"
ae_1 = Network([784, HIDDEN, 784])
ae_1.SGD(td_1, 4, 10, 0.01, 0.05)

print "\nFinding second autoencoder"
ae_2 = Network([784, HIDDEN, 784])
ae_2.SGD(td_1, 4, 10, 0.01, 0.05)

print "\nGenerating encoded training data"
encoded_td_1 = [sigmoid_vec(np.dot(ae_1.weights[0], x)+ae_1.biases[0])
                for x in td_3]
encoded_td_2 = [sigmoid_vec(np.dot(ae_2.weights[0], x)+ae_2.biases[0])
                for x in td_3]
encoded_training_data = zip(encoded_td_1, encoded_td_2)

print "\nFinding mapping between theories"
net = Network([HIDDEN, HIDDEN])
net.SGD(encoded_training_data, 6, 10, 0.01, 0.05)

print """\nBaseline for comparison: decompress with the first autoencoder"""
print """and compress with the second autoencoder"""
encoded_test_1 = [sigmoid_vec(np.dot(ae_1.weights[0], x)+ae_1.biases[0])
                  for x in test]
encoded_test_2 = [sigmoid_vec(np.dot(ae_2.weights[0], x)+ae_2.biases[0])
                  for x in test]
test_data = zip(encoded_test_1, encoded_test_2)
net_baseline = Network([HIDDEN, 784, HIDDEN])
net_baseline.biases[0] = ae_1.biases[1]
net_baseline.weights[0] = ae_1.weights[1]
net_baseline.biases[1] = ae_2.biases[0]
net_baseline.weights[1] = ae_2.weights[0]
error_baseline = sum(np.linalg.norm(net_baseline.feedforward(x)-y, 1) 
                     for (x, y) in test_data)
print "Baseline average l1 error per training image: %s" % (error_baseline / SIZE,)

print "\nComparing theories with a simple interconversion"
print "Mean desired output activation: %s" % (
    sum(y.mean() for _, y in test_data) / SIZE,)
error = sum(np.linalg.norm(net.feedforward(x)-y, 1) for (x, y) in test_data)
print "Average l1 error per training image: %s" % (error / SIZE,)

print "\nComputing fiducial image inputs"
fiducial_images_1 = [
    ae_1.weights[0][j,:].reshape(28,28)/np.linalg.norm(net.weights[0][j,:])
    for j in range(HIDDEN)]
fiducial_images_2 = [
    ae_2.weights[0][j,:].reshape(28,28)/np.linalg.norm(net.weights[0][j,:])
    for j in range(HIDDEN)]
image = np.concatenate([np.concatenate(fiducial_images_1, axis=1), 
                        np.concatenate(fiducial_images_2, axis=1)])
fig = plt.figure()
ax = fig.add_subplot(111)
ax.matshow(image, cmap = matplotlib.cm.binary)
plt.xticks(np.array([]))
plt.yticks(np.array([]))
plt.show()

########NEW FILE########
__FILENAME__ = deep_autoencoder
"""
deep_autoencoder
~~~~~~~~~~~~~~~~

A module which implements deep autoencoders.  
"""

#### Libraries
# Standard library
import random

# My libraries
from backprop2 import Network, sigmoid_vec

# Third-party libraries
import numpy as np


def plot_helper(x):
    import matplotlib
    import matplotlib.pyplot as plt
    x = np.reshape(x, (-1, 28))
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.matshow(x, cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    plt.show()


class DeepAutoencoder(Network):

    def __init__(self, layers):
        """
        The list ``layers`` specifies the sizes of the nested
        autoencoders.  For example, if ``layers`` is [50, 20, 10] then
        the deep autoencoder will be a neural network with layers of
        size [50, 20, 10, 20, 50]."""
        self.layers = layers
        Network.__init__(self, layers+layers[-2::-1])

    def train(self, training_data, epochs, mini_batch_size, eta,
              lmbda):
        """
        Train the DeepAutoencoder.  The ``training_data`` is a list of
        training inputs, ``x``, ``mini_batch_size`` is a single
        positive integer, and ``epochs``, ``eta``, ``lmbda`` are lists
        of parameters, with the different list members corresponding
        to the different stages of training.  For example, ``eta[0]``
        is the learning rate used for the first nested autoencoder,
        ``eta[1]`` is the learning rate for the second nested
        autoencoder, and so on.  ``eta[-1]`` is the learning rate used
        for the final stage of fine-tuning.
        """
        print "\nTraining a %s deep autoencoder" % (
            "-".join([str(j) for j in self.sizes]),)
        training_data = double(training_data)
        cur_training_data = training_data[::]
        for j in range(len(self.layers)-1):
            print "\nTraining the %s-%s-%s nested autoencoder" % (
                self.layers[j], self.layers[j+1], self.layers[j])
            print "%s epochs, mini-batch size %s, eta = %s, lambda = %s" % (
                epochs[j], mini_batch_size, eta[j], lmbda[j])
            self.train_nested_autoencoder(
                j, cur_training_data, epochs[j], mini_batch_size, eta[j],
                lmbda[j])
            cur_training_data = [
                (sigmoid_vec(np.dot(net.weights[0], x)+net.biases[0]),)*2
                for (x, _) in cur_training_data]
        print "\nFine-tuning network weights with backpropagation"
        print "%s epochs, mini-batch size %s, eta = %s, lambda = %s" % (
                epochs[-1], mini_batch_size, eta[-1], lmbda[-1])
        self.SGD(training_data, epochs[-1], mini_batch_size, eta[-1],
                 lmbda[-1])

    def train_nested_autoencoder(
        self, j, encoded_training_data, epochs, mini_batch_size, eta, lmbda):
        """
        Train the nested autoencoder that starts at layer ``j`` in the
        deep autoencoder.  Note that ``encoded_training_data`` is a
        list with entries of the form ``(x, x)``, where the ``x`` are
        encoded training inputs for layer ``j``."""
        net = Network([self.layers[j], self.layers[j+1], self.layers[j]])
        net.biases[0] = self.biases[j]
        net.biases[1] = self.biases[-j-1]
        net.weights[0] = self.weights[j]
        net.weights[1] = self.weights[-j-1]
        net.SGD(encoded_training_data, epochs, mini_batch_size, eta, lmbda)
        self.biases[j] = net.biases[0]
        self.biases[-j-1] = net.biases[1]
        self.weights[j] = net.weights[0]
        self.weights[-j-1] = net.weights[1]

    def train_nested_autoencoder_repl(
        self, j, training_data, epochs, mini_batch_size, eta, lmbda):
        """
        This is a convenience method that can be used from the REPL to
        train the nested autoencoder that starts at level ``j`` in the
        deep autoencoder.  Note that ``training_data`` is the input
        data for the first layer of the network, and is a list of
        entries ``x``."""
        self.train_nested_autoencoder(
            j, 
            double(
                [self.feedforward(x, start=0, end=j) for x in training_data]),
            epochs, mini_batch_size, eta, lmbda)

    def feature(self, j, k):
        """
        Return the output if neuron number ``k`` in layer ``j`` is
        activated, and all others are not active.  """
        a = np.zeros((self.sizes[j], 1))
        a[k] = 1.0
        return self.feedforward(a, start=j, end=self.num_layers)

def double(l):
    return [(x, x) for x in l]


########NEW FILE########
__FILENAME__ = deep_learning
"""
deep_learning
~~~~~~~~~~~~~

Module to do deep learning.  Most of the functionality needed is
already in the ``backprop2`` and ``deep_autoencoder`` modules, but
this adds convenience functions to help in doing things like unrolling
deep autoencoders, and adding and training a classifier layer."""

# My Libraries
from backprop2 import Network
from deep_autoencoder import DeepAutoencoder

def unroll(deep_autoencoder):
    """
    Return a Network that contains the compression stage of the
    ``deep_autoencoder``."""
    net = Network(deep_autoencoder.layers)
    net.weights = deep_autoencoder.weights[:len(deep_autoencoder.layers)-1]
    net.biases = deep_autoencoder.biases[:len(deep_autoencoder.layers)-1]
    return net

def add_classifier_layer(net, num_outputs):
    """
    Return the Network ``net``, but with an extra layer containing
    ``num_outputs`` neurons appended."""
    net_classifier = Network(net.sizes+[num_outputs])
    net_classifier.weights[:-1] = net.weights
    net_classifier.biases[:-1] = net.biases
    return net_classifier

def SGD_final_layer(
    self, training_data, epochs, mini_batch_size, eta, lmbda):
    """
    Run SGD on the final layer of the Network ``self``.  Note that
    ``training_data`` is the input to the whole Network, not the
    encoded training data input to the final layer. 
    """
    encoded_training_data = [
        (self.feedforward(x, start=0, end=self.num_layers-2), y) 
        for x, y in training_data]
    net = Network(self.sizes[-2:])
    net.biases[0] = self.biases[-1]
    net.weights[0] = self.weights[-1]
    net.SGD(encoded_training_data, epochs, mini_batch_size, eta, lmbda)
    self.biases[-1] = net.biases[0]
    self.weights[-1] = net.weights[0]


# Add the SGD_final_layer method to the Network class
Network.SGD_final_layer = SGD_final_layer

########NEW FILE########
__FILENAME__ = gradient_descent_hack
"""
gradient_descent_hack
~~~~~~~~~~~~~~~~~~~~~

This program uses gradient descent to learn weights and biases for a
three-neuron network to compute the XOR function.  The program is a
quick-and-dirty hack meant to illustrate the basic ideas of gradient
descent, not a cleanly-designed and generalizable implementation."""

#### Libraries
# Third-party libraries
import matplotlib.pyplot as plt
import numpy as np

def sigmoid(z):
    return 1.0/(1.0+np.exp(-z))

def neuron(w, x):
    """ Return the output from the sigmoid neuron with weights ``w``
    and inputs ``x``.  Both are numpy arrays, with three and two
    elements, respectively.  The first input weight is the bias."""
    return sigmoid(w[0]+np.inner(w[1:], x))

def h(w, x):
    """ Return the output from the three-neuron network with weights
    ``w`` and inputs ``x``.  Note that ``w`` is a numpy array with
    nine elements, consisting of three weights for each neuron (the
    bias plus two input weights).  ``x`` is a numpy array with just
    two elements."""
    neuron1_out = neuron(w[0:3], x) # top left neuron
    neuron2_out = neuron(w[3:6], x) # bottom left neuron
    return neuron(w[6:9], np.array([neuron1_out, neuron2_out]))

# inputs and corresponding outputs for the function we're computing (XOR)
INPUTS = [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]] 
OUTPUTS = [0.0, 1.0, 1.0, 0.0]

def cost(w):
    """ Return the cost when the neural network has weights ``w``.
    The cost is computed with respect to the XOR function."""
    return 0.5 * sum((y-h(w, np.array(x)))**2 for x, y in zip(INPUTS, OUTPUTS))

def partial(f, k, w):
    """ Return the partial derivative of the function ``f`` with
    respect to the ``k``th variable, at location ``w``.  Note that
    ``f`` must take a numpy array as input, and the partial derivative
    is evaluated with respect to the ``k``th element in that array.
    Similarly, ``w`` is a numpy array which can be used as input to
    ``f``."""
    w_plus, w_minus = w.copy(), w.copy()
    w_plus[k] += 0.01 # using epsilon = 0.01
    w_minus[k] += -0.01
    return (f(w_plus)-f(w_minus))/0.02
    
def gradient_descent(cost, eta, n):
    """ Perform ``n`` iterations of the gradient descent algorithm to
    minimize the ``cost`` function, with a learning rate ``eta``.
    Return a tuple whose first entry is an array containing the final
    weights, and whose second entry is a list of the values the
    ``cost`` function took at different iterations."""
    w = np.random.uniform(-1, 1, 9) # initialize weights randomly
    costs = []
    for j in xrange(n):
        c = cost(w)
        print "Current cost: {0:.3f}".format(c)
        costs.append(c)
        gradient = [partial(cost, k, w) for k in xrange(9)]
        w = np.array([wt-eta*d for wt, d in zip(w, gradient)])
    return w, costs

def main():
    """ Perform gradient descent to find weights for a sigmoid neural
    network to compute XOR.  10,000 iterations are used.  Outputs the
    final value of the cost function, the final weights, and plots a
    graph of cost as a function of iteration."""
    w, costs = gradient_descent(cost, 0.1, 10000)
    print "\nFinal cost: {0:.3f}".format(cost(w))
    print "\nFinal weights: %s" % w
    plt.plot(np.array(costs))
    plt.xlabel('iteration')
    plt.ylabel('cost')
    plt.title('How cost decreases with the number of iterations')
    plt.show()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = mnist_autoencoder
"""
mnist_autoencoder
~~~~~~~~~~~~~~~~~

Implements an autoencoder for the MNIST data.  The program can do two
things: (1) plot the autoencoder's output for the first ten images in
the MNIST test set; and (2) use the autoencoder to build a classifier.
The program is a quick-and-dirty hack --- we'll do things in a more
systematic way in the module ``deep_autoencoder``.
"""

# My Libraries
from backprop2 import Network
import mnist_loader 

# Third-party libraries
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

def autoencoder_results(hidden_units):
    """
    Train an autoencoder using the MNIST training data and plot the
    results when the first ten MNIST test images are passed through
    the autoencoder.
    """
    training_data, test_inputs, actual_test_results = \
        mnist_loader.load_data_nn()
    net = train_autoencoder(hidden_units, training_data)
    plot_test_results(net, test_inputs)

def train_autoencoder(hidden_units, training_data):
    "Return a trained autoencoder."
    autoencoder_training_data = [(x, x) for x, _ in training_data]
    net = Network([784, hidden_units, 784])
    net.SGD(autoencoder_training_data, 6, 10, 0.01, 0.05)
    return net

def plot_test_results(net, test_inputs):
    """
    Plot the results after passing the first ten test MNIST digits through
    the autoencoder ``net``."""
    fig = plt.figure()
    ax = fig.add_subplot(111)
    images_in = [test_inputs[j].reshape(-1, 28) for j in range(10)]
    images_out = [net.feedforward(test_inputs[j]).reshape(-1, 28) 
                  for j in range(10)]
    image_in = np.concatenate(images_in, axis=1)
    image_out = np.concatenate(images_out, axis=1)
    image = np.concatenate([image_in, image_out])
    ax.matshow(image, cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    plt.show()

def classifier(hidden_units, n_unlabeled_inputs, n_labeled_inputs):
    """
    Train a semi-supervised classifier.  We begin with pretraining,
    creating an autoencoder which uses ``n_unlabeled_inputs`` from the
    MNIST training data.  This is then converted into a classifier
    which is fine-tuned using the ``n_labeled_inputs``.

    For comparison a classifier is also created which does not make
    use of the unlabeled data.
    """
    training_data, test_inputs, actual_test_results = \
        mnist_loader.load_data_nn()
    print "\nUsing pretraining and %s items of unlabeled data" %\
        n_unlabeled_inputs
    net_ae = train_autoencoder(hidden_units, training_data[:n_unlabeled_inputs])
    net_c = Network([784, hidden_units, 10])
    net_c.biases = net_ae.biases[:1]+[np.random.randn(10, 1)/np.sqrt(10)]
    net_c.weights = net_ae.weights[:1]+\
        [np.random.randn(10, hidden_units)/np.sqrt(10)]
    net_c.SGD(training_data[-n_labeled_inputs:], 300, 10, 0.01, 0.05)
    print "Result on test data: %s / %s" % (
        net_c.evaluate(test_inputs, actual_test_results), len(test_inputs))
    print "Training a network with %s items of training data" % n_labeled_inputs
    net = Network([784, hidden_units, 10])
    net.SGD(training_data[-n_labeled_inputs:], 300, 10, 0.01, 0.05)
    print "Result on test data: %s / %s" % (
        net.evaluate(test_inputs, actual_test_results), len(test_inputs))
    return net_c

########NEW FILE########
__FILENAME__ = mnist_pca
"""
mnist_pca
~~~~~~~~~

Use PCA to reconstruct some of the MNIST test digits.
"""

# My libraries
import mnist_loader

# Third-party libraries
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import RandomizedPCA


# Training
training_data, test_inputs, actual_test_results = mnist_loader.load_data_nn()
pca = RandomizedPCA(n_components=30)
nn_images = [x for (x, y) in training_data]
pca_images = np.concatenate(nn_images, axis=1).transpose()
pca_r = pca.fit(pca_images)

# Try PCA on first ten test images
test_images = np.array(test_inputs[:10]).reshape((10,784))
test_outputs = pca_r.inverse_transform(pca_r.transform(test_images))

# Plot the first ten test images and the corresponding outputs
fig = plt.figure()
ax = fig.add_subplot(111)
images_in = [test_inputs[j].reshape(-1, 28) for j in range(10)]
images_out = [test_outputs[j].reshape(-1, 28) for j in range(10)]
image_in = np.concatenate(images_in, axis=1)
image_out = np.concatenate(images_out, axis=1)
image = np.concatenate([image_in, image_out])
ax.matshow(image, cmap = matplotlib.cm.binary)
plt.xticks(np.array([]))
plt.yticks(np.array([]))
plt.show()

########NEW FILE########
__FILENAME__ = perceptron_learning
"""
perceptron_learning
~~~~~~~~~~~~~~~~~~~

Demonstrates how a perceptron can learn the NAND gate, using the
perceptron learning algorithm."""

#### Libraries
# Third-party library
import numpy as np

class Perceptron():
    """ A Perceptron instance can take a function and attempt to
    ``learn`` a bias and set of weights that compute that function,
    using the perceptron learning algorithm."""

    def __init__(self, num_inputs=2):
        """ Initialize the perceptron with the bias and all weights
        set to 0.0. ``num_inputs`` is the number of input bits to the
        perceptron."""
        self.num_inputs = num_inputs
        self.bias = 0.0
        self.weights = np.zeros(num_inputs)
        # self.inputs is a convenience attribute.  It's a list containing
        # all possible binary inputs to the perceptron.  E.g., for three
        # inputs it is: [np.array([0, 0, 0]), np.array([0, 0, 1]), ...]
        self.inputs = [np.array([int(y)
                        for y in bin(x).lstrip("0b").zfill(num_inputs)])
                       for x in xrange(2**num_inputs)]      

    def output(self, x):
        """ Return the output (0 or 1) from the perceptron, with input
        ``x``."""
        return 1 if np.inner(self.weights, x)+self.bias > 0 else 0

    def learn(self, f, eta=0.1):
        """ Find a bias and a set of weights for a perceptron that
        computes the function ``f``. ``eta`` is the learning rate, and
        should be a small positive number.  Does not terminate when
        the function cannot be computed using a perceptron."""        
        # initialize the bias and weights with random values
        self.bias = np.random.normal()
        self.weights = np.random.randn(self.num_inputs)
        number_of_errors = -1
        while number_of_errors != 0:         
            number_of_errors = 0
            print "Beginning iteration"
            print "Bias: {:.3f}".format(self.bias)
            print "Weights:", ", ".join(
                "{:.3f}".format(wt) for wt in self.weights)
            for x in self.inputs:
                error = f(x)-self.output(x)
                if error:
                    number_of_errors += 1
                    self.bias = self.bias+eta*error
                    self.weights = self.weights+eta*error*x
            print "Number of errors:", number_of_errors, "\n"

def f(x): 
    """ Target function for the perceptron learning algorithm.  I've
    chosen the NAND gate, but any function is okay, with the caveat
    that the algorithm won't terminate if ``f`` cannot be computed by
    a perceptron."""    
    return int(not (x[0] and x[1]))

if __name__ == "__main__":
    Perceptron(2).learn(f, 0.1)

########NEW FILE########
__FILENAME__ = backprop_magnitude_nabla
"""
backprop_magnitude_nabla
~~~~~~~~~~~~~~~~~~~~~~~~

Using backprop2 I constructed a 784-30-30-30-30-30-10 network to classify
MNIST data.  I ran ten mini-batches of size 100, with eta = 0.01 and
lambda = 0.05, using:

net.SGD(otd[:1000], 1, 100, 0.01, 0.05,

I obtained the following norms for the (unregularized) nabla_w for the
respective mini-batches:

[0.90845722175923671, 2.8852730656073566, 10.696793986223632, 37.75701921183488, 157.7365422527995, 304.43990075227839]
[0.22493835119537842, 0.6555126517964851, 2.6036801277234076, 11.408825365731225, 46.882319190445472, 70.499637502698221]
[0.11935180022357521, 0.19756069137133489, 0.8152794148335869, 3.4590802543293977, 15.470507965493903, 31.032396017142556]
[0.15130005837653659, 0.39687135985664701, 1.4810006139254532, 4.392519005642268, 16.831939776937311, 34.082104455938733]
[0.11594085276308999, 0.17177668061395848, 0.72204558746599512, 3.05062409378366, 14.133001132214286, 29.776204839994385]
[0.10790389807606221, 0.20707152756018626, 0.96348134037828603, 3.9043824079499561, 15.986873430586924, 39.195258080490895]
[0.088613291101645356, 0.129173436407863, 0.4242933114455002, 1.6154682713449411, 7.5451567587160069, 20.180545544006566]
[0.086175380639289575, 0.12571016850457151, 0.44231149185805047, 1.8435833504677326, 7.61973813981073, 19.474539356281781]
[0.095372080184163904, 0.15854489503205446, 0.70244235144444678, 2.6294803575724157, 10.427062019753425, 24.309420272033819]
[0.096453131000155692, 0.13574642196947601, 0.53551377709415471, 2.0247466793066895, 9.4503978546018068, 21.73772148470092]

Note that results are listed in order of layer.  They clearly show how
the magnitude of nabla_w decreases as we go back through layers.

In this program I take min-batches 7, 8, 9 as representative and plot
them.  I omit the results from the first and final layers since they
correspond to 784 input neurons and 10 output neurons, not 30 as in
the other layers, making it difficult to compare results.

Note that I haven't attempted to preserve the whole workflow here. It
involved some minor hacking around with backprop2, which messed up
that code.  That's why I've simply put the results in by hand below.
"""

# Third-party libraries
import matplotlib.pyplot as plt

nw1 = [0.129173436407863, 0.4242933114455002, 
       1.6154682713449411, 7.5451567587160069]
nw2 = [0.12571016850457151, 0.44231149185805047, 
       1.8435833504677326, 7.61973813981073]
nw3 = [0.15854489503205446, 0.70244235144444678, 
       2.6294803575724157, 10.427062019753425]
plt.plot(range(1, 5), nw1, "ro-", range(1, 5), nw2, "go-", 
         range(1, 5), nw3, "bo-")
plt.xlabel('Layer $l$')
plt.ylabel(r"$\Vert\nabla C^l_w\Vert$")
plt.xticks([1, 2, 3, 4])
plt.show()

########NEW FILE########
__FILENAME__ = false_minima
"""
false_minimum
~~~~~~~~~~~~~

Plots a function of two variables with many false minima."""

#### Libraries
# Third party libraries
from matplotlib.ticker import LinearLocator
# Note that axes3d is not explicitly used in the code, but is needed
# to register the 3d plot type correctly
from mpl_toolkits.mplot3d import axes3d 
import matplotlib.pyplot as plt
import numpy

fig = plt.figure()
ax = fig.gca(projection='3d')
X = numpy.arange(-5, 5, 0.1)
Y = numpy.arange(-5, 5, 0.1)
X, Y = numpy.meshgrid(X, Y)
Z = numpy.sin(X)*numpy.sin(Y)+0.2*X

colortuple = ('w', 'b')
colors = numpy.empty(X.shape, dtype=str)
for x in xrange(len(X)):
    for y in xrange(len(Y)):
        colors[x, y] = colortuple[(x + y) % 2]

surf = ax.plot_surface(X, Y, Z, rstride=1, cstride=1, facecolors=colors,
        linewidth=0)

ax.set_xlim3d(-5, 5)
ax.set_ylim3d(-5, 5)
ax.set_zlim3d(-2, 2)
ax.w_xaxis.set_major_locator(LinearLocator(3))
ax.w_yaxis.set_major_locator(LinearLocator(3))
ax.w_zaxis.set_major_locator(LinearLocator(3))

plt.show()


########NEW FILE########
__FILENAME__ = misleading_gradient
"""
misleading_gradient
~~~~~~~~~~~~~~~~~~~

Plots a function which misleads the gradient descent algorithm."""

#### Libraries
# Third party libraries
from matplotlib.ticker import LinearLocator
# Note that axes3d is not explicitly used in the code, but is needed
# to register the 3d plot type correctly
from mpl_toolkits.mplot3d import axes3d 
import matplotlib.pyplot as plt
import numpy

fig = plt.figure()
ax = fig.gca(projection='3d')
X = numpy.arange(-1, 1, 0.025)
Y = numpy.arange(-1, 1, 0.025)
X, Y = numpy.meshgrid(X, Y)
Z = X**2 + 10*Y**2

colortuple = ('w', 'b')
colors = numpy.empty(X.shape, dtype=str)
for x in xrange(len(X)):
    for y in xrange(len(Y)):
        colors[x, y] = colortuple[(x + y) % 2]

surf = ax.plot_surface(X, Y, Z, rstride=1, cstride=1, facecolors=colors,
        linewidth=0)

ax.set_xlim3d(-1, 1)
ax.set_ylim3d(-1, 1)
ax.set_zlim3d(0, 12)
ax.w_xaxis.set_major_locator(LinearLocator(3))
ax.w_yaxis.set_major_locator(LinearLocator(3))
ax.w_zaxis.set_major_locator(LinearLocator(3))
ax.text(0.05, -1.8, 0, "$w_1$", fontsize=20)
ax.text(1.5, -0.25, 0, "$w_2$", fontsize=20)
ax.text(1.79, 0, 9.62, "$C$", fontsize=20)

plt.show()


########NEW FILE########
__FILENAME__ = misleading_gradient_contours
"""
misleading_gradient_contours
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Plots the contours of the function from misleading_gradient.py"""

#### Libraries
# Third party libraries
import matplotlib.pyplot as plt
import numpy

X = numpy.arange(-1, 1, 0.02)
Y = numpy.arange(-1, 1, 0.02)
X, Y = numpy.meshgrid(X, Y)
Z = X**2 + 10*Y**2

plt.figure()
CS = plt.contour(X, Y, Z, levels=[0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
plt.xlabel("$w_1$", fontsize=16)
plt.ylabel("$w_2$", fontsize=16)
plt.show()

########NEW FILE########
__FILENAME__ = mnist
"""
mnist
~~~~~

Draws images based on the MNIST data."""

#### Libraries
# Standard library
import cPickle
import sys

# My library
sys.path.append('../code/')
import mnist_loader

# Third-party libraries
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

def main():
    training_set, validation_set, test_set = mnist_loader.load_data()
    images = get_images(training_set)
    plot_rotated_image(images[0])

#### Plotting
def plot_images_together(images):
    """ Plot a single image containing all six MNIST images, one after
    the other.  Note that we crop the sides of the images so that they
    appear reasonably close together."""
    fig = plt.figure()
    images = [image[:, 3:25] for image in images]
    image = np.concatenate(images, axis=1)
    ax = fig.add_subplot(1, 1, 1)
    ax.matshow(image, cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    plt.show()

def plot_10_by_10_images(images):
    """ Plot 100 MNIST images in a 10 by 10 table. Note that we crop
    the images so that they appear reasonably close together.  The
    image is post-processed to give the appearance of being continued."""
    fig = plt.figure()
    images = [image[3:25, 3:25] for image in images]
    #image = np.concatenate(images, axis=1)
    for x in range(10):
        for y in range(10):
            ax = fig.add_subplot(10, 10, 10*y+x)
            ax.matshow(images[10*y+x], cmap = matplotlib.cm.binary)
            plt.xticks(np.array([]))
            plt.yticks(np.array([]))
    plt.show()

def plot_images_separately(images):
    "Plot the six MNIST images separately."
    fig = plt.figure()
    for j in xrange(1, 7):
        ax = fig.add_subplot(1, 6, j)
        ax.matshow(images[j-1], cmap = matplotlib.cm.binary)
        plt.xticks(np.array([]))
        plt.yticks(np.array([]))
    plt.show()

def plot_mnist_digit(image):
    """ Plot a single MNIST image."""
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.matshow(image, cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    plt.show()

def plot_2_and_1(images):
    "Plot a 2 and a 1 image from the MNIST set."
    fig = plt.figure()
    ax = fig.add_subplot(1, 2, 1)
    ax.matshow(images[5], cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    ax = fig.add_subplot(1, 2, 2)
    ax.matshow(images[3], cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    plt.show()

def plot_top_left(image):
    "Plot the top left of ``image``."
    image[14:,:] = np.zeros((14,28))
    image[:,14:] = np.zeros((28,14))
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.matshow(image, cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    plt.show()

def plot_bad_images(images):
    """This takes a list of images misclassified by a pretty good
    neural network --- one achieving over 93 percent accuracy --- and
    turns them into a figure."""
    bad_image_indices = [8, 18, 33, 92, 119, 124, 149, 151, 193, 233, 241, 247, 259, 300, 313, 321, 324, 341, 349, 352, 359, 362, 381, 412, 435, 445, 449, 478, 479, 495, 502, 511, 528, 531, 547, 571, 578, 582, 597, 610, 619, 628, 629, 659, 667, 691, 707, 717, 726, 740, 791, 810, 844, 846, 898, 938, 939, 947, 956, 959, 965, 982, 1014, 1033, 1039, 1044, 1050, 1055, 1107, 1112, 1124, 1147, 1181, 1191, 1192, 1198, 1202, 1204, 1206, 1224, 1226, 1232, 1242, 1243, 1247, 1256, 1260, 1263, 1283, 1289, 1299, 1310, 1319, 1326, 1328, 1357, 1378, 1393, 1413, 1422, 1435, 1467, 1469, 1494, 1500, 1522, 1523, 1525, 1527, 1530, 1549, 1553, 1609, 1611, 1634, 1641, 1676, 1678, 1681, 1709, 1717, 1722, 1730, 1732, 1737, 1741, 1754, 1759, 1772, 1773, 1790, 1808, 1813, 1823, 1843, 1850, 1857, 1868, 1878, 1880, 1883, 1901, 1913, 1930, 1938, 1940, 1952, 1969, 1970, 1984, 2001, 2009, 2016, 2018, 2035, 2040, 2043, 2044, 2053, 2063, 2098, 2105, 2109, 2118, 2129, 2130, 2135, 2148, 2161, 2168, 2174, 2182, 2185, 2186, 2189, 2224, 2229, 2237, 2266, 2272, 2293, 2299, 2319, 2325, 2326, 2334, 2369, 2371, 2380, 2381, 2387, 2393, 2395, 2406, 2408, 2414, 2422, 2433, 2450, 2488, 2514, 2526, 2548, 2574, 2589, 2598, 2607, 2610, 2631, 2648, 2654, 2695, 2713, 2720, 2721, 2730, 2770, 2771, 2780, 2863, 2866, 2896, 2907, 2925, 2927, 2939, 2995, 3005, 3023, 3030, 3060, 3073, 3102, 3108, 3110, 3114, 3115, 3117, 3130, 3132, 3157, 3160, 3167, 3183, 3189, 3206, 3240, 3254, 3260, 3280, 3329, 3330, 3333, 3383, 3384, 3475, 3490, 3503, 3520, 3525, 3559, 3567, 3573, 3597, 3598, 3604, 3629, 3664, 3702, 3716, 3718, 3725, 3726, 3727, 3751, 3752, 3757, 3763, 3766, 3767, 3769, 3776, 3780, 3798, 3806, 3808, 3811, 3817, 3821, 3838, 3848, 3853, 3855, 3869, 3876, 3902, 3906, 3926, 3941, 3943, 3951, 3954, 3962, 3976, 3985, 3995, 4000, 4002, 4007, 4017, 4018, 4065, 4075, 4078, 4093, 4102, 4139, 4140, 4152, 4154, 4163, 4165, 4176, 4199, 4201, 4205, 4207, 4212, 4224, 4238, 4248, 4256, 4284, 4289, 4297, 4300, 4306, 4344, 4355, 4356, 4359, 4360, 4369, 4405, 4425, 4433, 4435, 4449, 4487, 4497, 4498, 4500, 4521, 4536, 4548, 4563, 4571, 4575, 4601, 4615, 4620, 4633, 4639, 4662, 4690, 4722, 4731, 4735, 4737, 4739, 4740, 4761, 4798, 4807, 4814, 4823, 4833, 4837, 4874, 4876, 4879, 4880, 4886, 4890, 4910, 4950, 4951, 4952, 4956, 4963, 4966, 4968, 4978, 4990, 5001, 5020, 5054, 5067, 5068, 5078, 5135, 5140, 5143, 5176, 5183, 5201, 5210, 5331, 5409, 5457, 5495, 5600, 5601, 5617, 5623, 5634, 5642, 5677, 5678, 5718, 5734, 5735, 5749, 5752, 5771, 5787, 5835, 5842, 5845, 5858, 5887, 5888, 5891, 5906, 5913, 5936, 5937, 5945, 5955, 5957, 5972, 5973, 5985, 5987, 5997, 6035, 6042, 6043, 6045, 6053, 6059, 6065, 6071, 6081, 6091, 6112, 6124, 6157, 6166, 6168, 6172, 6173, 6347, 6370, 6386, 6390, 6391, 6392, 6421, 6426, 6428, 6505, 6542, 6555, 6556, 6560, 6564, 6568, 6571, 6572, 6597, 6598, 6603, 6608, 6625, 6651, 6694, 6706, 6721, 6725, 6740, 6746, 6768, 6783, 6785, 6796, 6817, 6827, 6847, 6870, 6872, 6926, 6945, 7002, 7035, 7043, 7089, 7121, 7130, 7198, 7216, 7233, 7248, 7265, 7426, 7432, 7434, 7494, 7498, 7691, 7777, 7779, 7797, 7800, 7809, 7812, 7821, 7849, 7876, 7886, 7897, 7902, 7905, 7917, 7921, 7945, 7999, 8020, 8059, 8081, 8094, 8095, 8115, 8246, 8256, 8262, 8272, 8273, 8278, 8279, 8293, 8322, 8339, 8353, 8408, 8453, 8456, 8502, 8520, 8522, 8607, 9009, 9010, 9013, 9015, 9019, 9022, 9024, 9026, 9036, 9045, 9046, 9128, 9214, 9280, 9316, 9342, 9382, 9433, 9446, 9506, 9540, 9544, 9587, 9614, 9634, 9642, 9645, 9700, 9716, 9719, 9729, 9732, 9738, 9740, 9741, 9742, 9744, 9745, 9749, 9752, 9768, 9770, 9777, 9779, 9792, 9808, 9831, 9839, 9856, 9858, 9867, 9879, 9883, 9888, 9890, 9893, 9905, 9944, 9970, 9982]
    n = len(bad_image_indices)
    bad_images = [images[j] for j in bad_image_indices]
    fig = plt.figure(figsize=(10, 15))
    for j in xrange(1, n+1):
        ax = fig.add_subplot(25, 125, j)
        ax.matshow(bad_images[j-1], cmap = matplotlib.cm.binary)
        ax.set_title(str(bad_image_indices[j-1]))
        plt.xticks(np.array([]))
        plt.yticks(np.array([]))
    plt.subplots_adjust(hspace = 1.2)
    plt.show()

def plot_really_bad_images(images):
    """This takes a list of the worst images from plot_bad_images and
    turns them into a figure."""
    really_bad_image_indices = [
        324, 582, 659, 726, 846, 956, 1124, 1393,
        1773, 1868, 2018, 2109, 2654, 4199, 4201, 4620, 5457, 5642]
    n = len(really_bad_image_indices)
    really_bad_images = [images[j] for j in really_bad_image_indices]
    fig = plt.figure(figsize=(10, 2))
    for j in xrange(1, n+1):
        ax = fig.add_subplot(2, 9, j)
        ax.matshow(really_bad_images[j-1], cmap = matplotlib.cm.binary)
        #ax.set_title(str(really_bad_image_indices[j-1]))
        plt.xticks(np.array([]))
        plt.yticks(np.array([]))
    plt.show()

def plot_features(image):
    "Plot the top right, bottom left, and bottom right of ``image``."
    image_1, image_2, image_3 = np.copy(image), np.copy(image), np.copy(image)
    image_1[:,:14] = np.zeros((28,14))
    image_1[14:,:] = np.zeros((14,28))
    image_2[:,14:] = np.zeros((28,14))
    image_2[:14,:] = np.zeros((14,28))
    image_3[:14,:] = np.zeros((14,28))
    image_3[:,:14] = np.zeros((28,14))
    fig = plt.figure()
    ax = fig.add_subplot(1, 3, 1)
    ax.matshow(image_1, cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    ax = fig.add_subplot(1, 3, 2)
    ax.matshow(image_2, cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    ax = fig.add_subplot(1, 3, 3)
    ax.matshow(image_3, cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    plt.show()

def plot_rotated_image(image):
    """ Plot an MNIST digit and a version rotated by 10 degrees."""
    # Do the initial plot
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.matshow(image, cmap = matplotlib.cm.binary)
    plt.xticks(np.array([]))
    plt.yticks(np.array([]))
    plt.show()
    # Set up the rotated image.  There are fast matrix techniques
    # for doing this, but we'll do a pedestrian approach
    rot_image = np.zeros((28,28))
    theta = 15*np.pi/180 # 15 degrees
    def to_xy(j, k):
        # Converts from matrix indices to x, y co-ords, using the
        # 13, 14 matrix entry as the origin
        return (k-13, -j+14) # x range: -13..14, y range: -13..14
    def to_jk(x, y):
        # Converts from x, y co-ords to matrix indices
        return (-y+14, x+13)
    def image_value(image, x, y):
        # returns the value of the image at co-ordinate x, y
        # (Note that this would be better done as a closure, if Pythong
        # supported closures, so that image didn't need to be passed)
        j, k = to_jk(x, y)
        return image[j, k]
    # Element by element, figure out what should be in the rotated
    # image.  We simply take each matrix entry, figure out the
    # corresponding x, y co-ordinates, rotate backward, and then
    # average the nearby matrix elements.  It's not perfect, and it's
    # not fast, but it works okay.
    for j in range(28):
        for k in range(28):
            x, y = to_xy(j, k)
            # rotate by -theta
            x1 = np.cos(theta)*x + np.sin(theta)*y
            y1 = -np.sin(theta)*x + np.cos(theta)*y
            # Nearest integer x entries are x2 and x2+1. delta_x 
            # measures how to interpolate
            x2 = np.floor(x1)
            delta_x = x1-x2
            # Similarly for y
            y2 = np.floor(y1)
            delta_y = y1-y2
            # Check if we're out of bounds, and if so continue to next entry
            # This will miss a boundary row and layer, but that's okay,
            # MNIST digits usually don't go that near the boundary.
            if x2 < -13 or x2 > 13 or y2 < -13 or y2 > 13: continue
            # If we're in bounds, average the nearby entries.
            value \
                = (1-delta_x)*(1-delta_y)*image_value(image, x2, y2)+\
                (1-delta_x)*delta_y*image_value(image, x2, y2+1)+\
                delta_x*(1-delta_y)*image_value(image, x2+1, y2)+\
                delta_x*delta_y*image_value(image, x2+1, y2+1)
            # Rescale the value by a hand-set fudge factor.  This
            # seems to be necessary because the averaging doesn't
            # quite work right.  The fudge-factor should probably be
            # theta-dependent, but I've set it by hand.  
            rot_image[j, k] = 1.3*value
    plot_mnist_digit(rot_image)

#### Miscellanea
def load_data():
    """ Return the MNIST data as a tuple containing the training data,
    the validation data, and the test data."""
    f = open('../data/mnist.pkl', 'rb')
    training_set, validation_set, test_set = cPickle.load(f)
    f.close()
    return (training_set, validation_set, test_set)

def get_images(training_set):
    """ Return a list containing the images from the MNIST data
    set. Each image is represented as a 2-d numpy array."""
    flattened_images = training_set[0]
    return [np.reshape(f, (-1, 28)) for f in flattened_images]

#### Main
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = more_data
"""more_data
~~~~~~~~~~~~

Plot graphs to illustrate the performance of MNIST when different size
training sets are used.

"""

# Standard library
import json
import random
import sys

# My library
sys.path.append('../code/')
import mnist_loader
import network2

# Third-party libraries
import matplotlib.pyplot as plt
import numpy as np
from sklearn import svm

# The sizes to use for the different training sets
SIZES = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000] 

def main():
    run_networks()
    run_svms()
    make_plots()
                       
def run_networks():
    # Make results more easily reproducible
    random.seed(12345678)
    np.random.seed(12345678)
    training_data, validation_data, test_data = mnist_loader.load_data_wrapper()
    net = network2.Network([784, 30, 10], cost=network2.CrossEntropyCost())
    accuracies = []
    for size in SIZES:
        print "\n\nTraining network with data set size %s" % size
        net.large_weight_initializer()
        num_epochs = 1500000 / size 
        net.SGD(training_data[:size], num_epochs, 10, 0.5, lmbda = size*0.0001)
        accuracy = net.accuracy(validation_data) / 100.0
        print "Accuracy was %s percent" % accuracy
        accuracies.append(accuracy)
    f = open("more_data.json", "w")
    json.dump(accuracies, f)
    f.close()

def run_svms():
    svm_training_data, svm_validation_data, svm_test_data \
        = mnist_loader.load_data()
    accuracies = []
    for size in SIZES:
        print "\n\nTraining SVM with data set size %s" % size
        clf = svm.SVC()
        clf.fit(svm_training_data[0][:size], svm_training_data[1][:size])
        predictions = [int(a) for a in clf.predict(svm_validation_data[0])]
        accuracy = sum(int(a == y) for a, y in 
                       zip(predictions, svm_validation_data[1])) / 100.0
        print "Accuracy was %s percent" % accuracy
        accuracies.append(accuracy)
    f = open("more_data_svm.json", "w")
    json.dump(accuracies, f)
    f.close()

def make_plots():
    f = open("more_data.json", "r")
    accuracies = json.load(f)
    f.close()
    f = open("more_data_svm.json", "r")
    svm_accuracies = json.load(f)
    f.close()
    make_linear_plot(accuracies)
    make_log_plot(accuracies)
    make_combined_plot(accuracies, svm_accuracies)

def make_linear_plot(accuracies):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(SIZES, accuracies, color='#2A6EA6')
    ax.plot(SIZES, accuracies, "o", color='#FFA933')
    ax.set_xlim(0, 50000)
    ax.set_ylim(60, 100)
    ax.grid(True)
    ax.set_xlabel('Training set size')
    ax.set_title('Accuracy (%) on the validation data')
    plt.show()

def make_log_plot(accuracies):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(SIZES, accuracies, color='#2A6EA6')
    ax.plot(SIZES, accuracies, "o", color='#FFA933')
    ax.set_xlim(100, 50000)
    ax.set_ylim(60, 100)
    ax.set_xscale('log')
    ax.grid(True)
    ax.set_xlabel('Training set size')
    ax.set_title('Accuracy (%) on the validation data')
    plt.show()

def make_combined_plot(accuracies, svm_accuracies):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(SIZES, accuracies, color='#2A6EA6')
    ax.plot(SIZES, accuracies, "o", color='#2A6EA6', 
            label='Neural network accuracy (%)')
    ax.plot(SIZES, svm_accuracies, color='#FFA933')
    ax.plot(SIZES, svm_accuracies, "o", color='#FFA933',
            label='SVM accuracy (%)')
    ax.set_xlim(100, 50000)
    ax.set_ylim(25, 100)
    ax.set_xscale('log')
    ax.grid(True)
    ax.set_xlabel('Training set size')
    plt.legend(loc="lower right")
    plt.show()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = multiple_eta
"""multiple_eta
~~~~~~~~~~~~~~~

This program shows how different values for the learning rate affect
training.  In particular, we'll plot out how the cost changes using
three different values for eta.

"""

# Standard library
import json
import random
import sys

# My library
sys.path.append('../code/')
import mnist_loader
import network2

# Third-party libraries
import matplotlib.pyplot as plt
import numpy as np

# Constants
LEARNING_RATES = [0.025, 0.25, 2.5]
COLORS = ['#2A6EA6', '#FFCD33', '#FF7033']
NUM_EPOCHS = 30

def main():
    run_networks()
    make_plot()

def run_networks():
    """Train networks using three different values for the learning rate,
    and store the cost curves in the file ``multiple_eta.json``, where
    they can later be used by ``make_plot``.

    """
    # Make results more easily reproducible
    random.seed(12345678)
    np.random.seed(12345678)
    training_data, validation_data, test_data = mnist_loader.load_data_wrapper()
    results = []
    for eta in LEARNING_RATES:
        print "\nTrain a network using eta = "+str(eta)
        net = network2.Network([784, 30, 10])
        results.append(
            net.SGD(training_data, NUM_EPOCHS, 10, eta, lmbda=5.0,
                    evaluation_data=validation_data, 
                    monitor_training_cost=True))
    f = open("multiple_eta.json", "w")
    json.dump(results, f)
    f.close()

def make_plot():
    f = open("multiple_eta.json", "r")
    results = json.load(f)
    f.close()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    for eta, result, color in zip(LEARNING_RATES, results, COLORS):
        _, _, training_cost, _ = result
        ax.plot(np.arange(NUM_EPOCHS), training_cost, "o-",
                label="$\eta$ = "+str(eta),
                color=color)
    ax.set_xlim([0, NUM_EPOCHS])
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Cost')
    plt.legend(loc='upper right')
    plt.show()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = overfitting
"""
overfitting
~~~~~~~~~~~

Plot graphs to illustrate the problem of overfitting.  
"""

# Standard library
import json
import random
import sys

# My library
sys.path.append('../code/')
import mnist_loader
import network2

# Third-party libraries
import matplotlib.pyplot as plt
import numpy as np


def main(filename, num_epochs,
         training_cost_xmin=200, 
         test_accuracy_xmin=200, 
         test_cost_xmin=0, 
         training_accuracy_xmin=0,
         training_set_size=1000, 
         lmbda=0.0):
    """``filename`` is the name of the file where the results will be
    stored.  ``num_epochs`` is the number of epochs to train for.
    ``training_set_size`` is the number of images to train on.
    ``lmbda`` is the regularization parameter.  The other parameters
    set the epochs at which to start plotting on the x axis.
    """
    run_network(filename, num_epochs, training_set_size, lmbda)
    make_plots(filename, num_epochs, 
               test_accuracy_xmin,
               training_cost_xmin,
               test_accuracy_xmin, 
               training_accuracy_xmin,
               training_set_size)
                       
def run_network(filename, num_epochs, training_set_size=1000, lmbda=0.0):
    """Train the network for ``num_epochs`` on ``training_set_size``
    images, and store the results in ``filename``.  Those results can
    later be used by ``make_plots``.  Note that the results are stored
    to disk in large part because it's convenient not to have to
    ``run_network`` each time we want to make a plot (it's slow).

    """
    # Make results more easily reproducible
    random.seed(12345678)
    np.random.seed(12345678)
    training_data, validation_data, test_data = mnist_loader.load_data_wrapper()
    net = network2.Network([784, 30, 10], cost=network2.CrossEntropyCost())
    net.large_weight_initializer()
    test_cost, test_accuracy, training_cost, training_accuracy \
        = net.SGD(training_data[:training_set_size], num_epochs, 10, 0.5,
                  evaluation_data=test_data, lmbda = lmbda,
                  monitor_evaluation_cost=True, 
                  monitor_evaluation_accuracy=True, 
                  monitor_training_cost=True, 
                  monitor_training_accuracy=True)
    f = open(filename, "w")
    json.dump([test_cost, test_accuracy, training_cost, training_accuracy], f)
    f.close()

def make_plots(filename, num_epochs, 
               training_cost_xmin=200, 
               test_accuracy_xmin=200, 
               test_cost_xmin=0, 
               training_accuracy_xmin=0,
               training_set_size=1000):
    """Load the results from ``filename``, and generate the corresponding
    plots. """
    f = open(filename, "r")
    test_cost, test_accuracy, training_cost, training_accuracy \
        = json.load(f)
    f.close()
    plot_training_cost(training_cost, num_epochs, training_cost_xmin)
    plot_test_accuracy(test_accuracy, num_epochs, test_accuracy_xmin)
    plot_test_cost(test_cost, num_epochs, test_cost_xmin)
    plot_training_accuracy(training_accuracy, num_epochs, 
                           training_accuracy_xmin, training_set_size)
    plot_overlay(test_accuracy, training_accuracy, num_epochs,
                 min(test_accuracy_xmin, training_accuracy_xmin),
                 training_set_size)

def plot_training_cost(training_cost, num_epochs, training_cost_xmin):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(np.arange(training_cost_xmin, num_epochs), 
            training_cost[training_cost_xmin:num_epochs],
            color='#2A6EA6')
    ax.set_xlim([training_cost_xmin, num_epochs])
    ax.grid(True)
    ax.set_xlabel('Epoch')
    ax.set_title('Cost on the training data')
    plt.show()

def plot_test_accuracy(test_accuracy, num_epochs, test_accuracy_xmin):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(np.arange(test_accuracy_xmin, num_epochs), 
            [accuracy/100.0 
             for accuracy in test_accuracy[test_accuracy_xmin:num_epochs]],
            color='#2A6EA6')
    ax.set_xlim([test_accuracy_xmin, num_epochs])
    ax.grid(True)
    ax.set_xlabel('Epoch')
    ax.set_title('Accuracy (%) on the test data')
    plt.show()

def plot_test_cost(test_cost, num_epochs, test_cost_xmin):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(np.arange(test_cost_xmin, num_epochs), 
            test_cost[test_cost_xmin:num_epochs],
            color='#2A6EA6')
    ax.set_xlim([test_cost_xmin, num_epochs])
    ax.grid(True)
    ax.set_xlabel('Epoch')
    ax.set_title('Cost on the test data')
    plt.show()

def plot_training_accuracy(training_accuracy, num_epochs, 
                           training_accuracy_xmin, training_set_size):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(np.arange(training_accuracy_xmin, num_epochs), 
            [accuracy*100.0/training_set_size 
             for accuracy in training_accuracy[training_accuracy_xmin:num_epochs]],
            color='#2A6EA6')
    ax.set_xlim([training_accuracy_xmin, num_epochs])
    ax.grid(True)
    ax.set_xlabel('Epoch')
    ax.set_title('Accuracy (%) on the training data')
    plt.show()

def plot_overlay(test_accuracy, training_accuracy, num_epochs, xmin,
                 training_set_size):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(np.arange(xmin, num_epochs), 
            [accuracy/100.0 for accuracy in test_accuracy], 
            color='#2A6EA6',
            label="Accuracy on the test data")
    ax.plot(np.arange(xmin, num_epochs), 
            [accuracy*100.0/training_set_size 
             for accuracy in training_accuracy], 
            color='#FFA933',
            label="Accuracy on the training data")
    ax.grid(True)
    ax.set_xlim([xmin, num_epochs])
    ax.set_xlabel('Epoch')
    ax.set_ylim([90, 100])
    plt.legend(loc="lower right")
    plt.show()

if __name__ == "__main__":
    filename = raw_input("Enter a file name: ")
    num_epochs = int(raw_input(
        "Enter the number of epochs to run for: "))
    training_cost_xmin = int(raw_input(
        "training_cost_xmin (suggest 200): "))
    test_accuracy_xmin = int(raw_input(
        "test_accuracy_xmin (suggest 200): "))
    test_cost_xmin = int(raw_input(
        "test_cost_xmin (suggest 0): "))
    training_accuracy_xmin = int(raw_input(
        "training_accuracy_xmin (suggest 0): "))
    training_set_size = int(raw_input(
        "Training set size (suggest 1000): "))
    lmbda = float(raw_input(
        "Enter the regularization parameter, lambda (suggest: 5.0): "))
    main(filename, num_epochs, training_cost_xmin, 
         test_accuracy_xmin, test_cost_xmin, training_accuracy_xmin,
         training_set_size, lmbda)

########NEW FILE########
__FILENAME__ = pca_limitations
"""
pca_limitations
~~~~~~~~~~~~~~~

Plot graphs to illustrate the limitations of PCA.
"""

# Third-party libraries
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np

# Plot just the data
fig = plt.figure()
ax = fig.gca(projection='3d')
z = np.linspace(-2, 2, 20)
theta = np.linspace(-4 * np.pi, 4 * np.pi, 20)
x = np.sin(theta)+0.03*np.random.randn(20)
y = np.cos(theta)+0.03*np.random.randn(20)
ax.plot(x, y, z, 'ro')
plt.show()

# Plot the data and the helix together
fig = plt.figure()
ax = fig.gca(projection='3d')
z_helix = np.linspace(-2, 2, 100)
theta_helix = np.linspace(-4 * np.pi, 4 * np.pi, 100)
x_helix = np.sin(theta_helix)
y_helix = np.cos(theta_helix)
ax.plot(x, y, z, 'ro')
ax.plot(x_helix, y_helix, z_helix, '')
plt.show()

########NEW FILE########
__FILENAME__ = relu
"""
relu
~~~~

Plots a graph of the squashing function used by a rectified linear
unit."""

import numpy as np
import matplotlib.pyplot as plt

z = np.arange(-2, 2, .1)
zero = np.zeros(len(z))
y = np.max([zero, z], axis=0)

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(z, y)
ax.set_ylim([-2.0, 2.0])
ax.set_xlim([-2.0, 2.0])
ax.grid(True)
ax.set_xlabel('z')
ax.set_title('Rectified linear unit')

plt.show()

########NEW FILE########
__FILENAME__ = sigmoid
"""
sigmoid
~~~~~~~

Plots a graph of the sigmoid function."""

import numpy
import matplotlib.pyplot as plt

z = numpy.arange(-5, 5, .1)
sigma_fn = numpy.vectorize(lambda z: 1/(1+numpy.exp(-z)))
sigma = sigma_fn(z)

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(z, sigma)
ax.set_ylim([-0.5, 1.5])
ax.set_xlim([-5,5])
ax.grid(True)
ax.set_xlabel('z')
ax.set_title('sigmoid function')

plt.show()

########NEW FILE########
__FILENAME__ = step
"""
step
~~~~~~~

Plots a graph of a step function."""

import numpy
import matplotlib.pyplot as plt

z = numpy.arange(-5, 5, .02)
step_fn = numpy.vectorize(lambda z: 1.0 if z >= 0.0 else 0.0)
step = step_fn(z)

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(z, step)
ax.set_ylim([-0.5, 1.5])
ax.set_xlim([-5,5])
ax.grid(True)
ax.set_xlabel('z')
ax.set_title('step function')

plt.show()

########NEW FILE########
__FILENAME__ = tanh
"""
tanh
~~~~

Plots a graph of the tanh function."""

import numpy as np
import matplotlib.pyplot as plt

z = np.arange(-5, 5, .1)
t = np.tanh(z)

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(z, t)
ax.set_ylim([-1.0, 1.0])
ax.set_xlim([-5,5])
ax.grid(True)
ax.set_xlabel('z')
ax.set_title('tanh function')

plt.show()

########NEW FILE########
__FILENAME__ = valley
"""
valley
~~~~~~

Plots a function of two variables to minimize.  The function is a
fairly generic valley function."""

#### Libraries
# Third party libraries
from matplotlib.ticker import LinearLocator
# Note that axes3d is not explicitly used in the code, but is needed
# to register the 3d plot type correctly
from mpl_toolkits.mplot3d import axes3d 
import matplotlib.pyplot as plt
import numpy

fig = plt.figure()
ax = fig.gca(projection='3d')
X = numpy.arange(-1, 1, 0.1)
Y = numpy.arange(-1, 1, 0.1)
X, Y = numpy.meshgrid(X, Y)
Z = X**2 + Y**2

colortuple = ('w', 'b')
colors = numpy.empty(X.shape, dtype=str)
for x in xrange(len(X)):
    for y in xrange(len(Y)):
        colors[x, y] = colortuple[(x + y) % 2]

surf = ax.plot_surface(X, Y, Z, rstride=1, cstride=1, facecolors=colors,
        linewidth=0)

ax.set_xlim3d(-1, 1)
ax.set_ylim3d(-1, 1)
ax.set_zlim3d(0, 2)
ax.w_xaxis.set_major_locator(LinearLocator(3))
ax.w_yaxis.set_major_locator(LinearLocator(3))
ax.w_zaxis.set_major_locator(LinearLocator(3))
ax.text(1.79, 0, 1.62, "$C$", fontsize=20)
ax.text(0.05, -1.8, 0, "$v_1$", fontsize=20)
ax.text(1.5, -0.25, 0, "$v_2$", fontsize=20)

plt.show()

########NEW FILE########
__FILENAME__ = valley2
"""valley2.py
~~~~~~~~~~~~~

Plots a function of two variables to minimize.  The function is a
fairly generic valley function.

Note that this is a duplicate of valley.py, but omits labels on the
axis.  It's bad practice to duplicate in this way, but I had
considerable trouble getting matplotlib to update a graph in the way I
needed (adding or removing labels), so finally fell back on this as a
kludge solution.

"""

#### Libraries
# Third party libraries
from matplotlib.ticker import LinearLocator
# Note that axes3d is not explicitly used in the code, but is needed
# to register the 3d plot type correctly
from mpl_toolkits.mplot3d import axes3d 
import matplotlib.pyplot as plt
import numpy

fig = plt.figure()
ax = fig.gca(projection='3d')
X = numpy.arange(-1, 1, 0.1)
Y = numpy.arange(-1, 1, 0.1)
X, Y = numpy.meshgrid(X, Y)
Z = X**2 + Y**2

colortuple = ('w', 'b')
colors = numpy.empty(X.shape, dtype=str)
for x in xrange(len(X)):
    for y in xrange(len(Y)):
        colors[x, y] = colortuple[(x + y) % 2]

surf = ax.plot_surface(X, Y, Z, rstride=1, cstride=1, facecolors=colors,
        linewidth=0)

ax.set_xlim3d(-1, 1)
ax.set_ylim3d(-1, 1)
ax.set_zlim3d(0, 2)
ax.w_xaxis.set_major_locator(LinearLocator(3))
ax.w_yaxis.set_major_locator(LinearLocator(3))
ax.w_zaxis.set_major_locator(LinearLocator(3))
ax.text(1.79, 0, 1.62, "$C$", fontsize=20)

plt.show()

########NEW FILE########
__FILENAME__ = weight_initialization
"""weight_initialization 
~~~~~~~~~~~~~~~~~~~~~~~~

This program shows how weight initialization affects training.  In
particular, we'll plot out how the classification accuracies improve
using either large starting weights, whose standard deviation is 1, or
the default starting weights, whose standard deviation is 1 over the
square root of the number of input neurons.

"""

# Standard library
import json
import random
import sys

# My library
sys.path.append('../code/')
import mnist_loader
import network2

# Third-party libraries
import matplotlib.pyplot as plt
import numpy as np

def main(filename, n, eta):
    run_network(filename, n, eta)
    make_plot(filename)
                       
def run_network(filename, n, eta):
    """Train the network using both the default and the large starting
    weights.  Store the results in the file with name ``filename``,
    where they can later be used by ``make_plots``.

    """
    # Make results more easily reproducible
    random.seed(12345678)
    np.random.seed(12345678)
    training_data, validation_data, test_data = mnist_loader.load_data_wrapper()
    net = network2.Network([784, n, 10], cost=network2.CrossEntropyCost)
    print "Train the network using the default starting weights."
    default_vc, default_va, default_tc, default_ta \
        = net.SGD(training_data, 30, 10, eta, lmbda=5.0,
                  evaluation_data=validation_data, 
                  monitor_evaluation_accuracy=True)
    print "Train the network using the large starting weights."
    net.large_weight_initializer()
    large_vc, large_va, large_tc, large_ta \
        = net.SGD(training_data, 30, 10, eta, lmbda=5.0,
                  evaluation_data=validation_data, 
                  monitor_evaluation_accuracy=True)
    f = open(filename, "w")
    json.dump({"default_weight_initialization":
               [default_vc, default_va, default_tc, default_ta],
               "large_weight_initialization":
               [large_vc, large_va, large_tc, large_ta]}, 
              f)
    f.close()

def make_plot(filename):
    """Load the results from the file ``filename``, and generate the
    corresponding plot.

    """
    f = open(filename, "r")
    results = json.load(f)
    f.close()
    default_vc, default_va, default_tc, default_ta = results[
        "default_weight_initialization"]
    large_vc, large_va, large_tc, large_ta = results[
        "large_weight_initialization"]
    # Convert raw classification numbers to percentages, for plotting
    default_va = [x/100.0 for x in default_va]
    large_va = [x/100.0 for x in large_va]
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(np.arange(0, 30, 1), large_va, color='#2A6EA6',
            label="Old approach to weight initialization")
    ax.plot(np.arange(0, 30, 1), default_va, color='#FFA933', 
            label="New approach to weight initialization")
    ax.set_xlim([0, 30])
    ax.set_xlabel('Epoch')
    ax.set_ylim([85, 100])
    ax.set_title('Classification accuracy')
    plt.legend(loc="lower right")
    plt.show()

if __name__ == "__main__":
    main()

########NEW FILE########
