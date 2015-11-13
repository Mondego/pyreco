__FILENAME__ = diagnostics
"""
Verbose debug output for the model.
"""

import logging
from common.stats import stats
from common.str import percent

import examples

import numpy
import random

def diagnostics(cnt, model):
    logging.info(stats())
    idxs = range(model.parameters.vocab_size)
    random.shuffle(idxs)
    idxs = idxs[:100]

    embeddings_debug(model.parameters.embeddings[idxs], cnt, "rand 100 words, model %s" % model.modelname)
    embeddings_debug(model.parameters.embeddings[:100], cnt, "top  100 words, model %s" % model.modelname)
    embeddings_debug(model.parameters.embeddings[model.parameters.vocab_size/2-50:model.parameters.vocab_size/2+50], cnt, "mid  100 words, model %s" % model.modelname)
    embeddings_debug(model.parameters.embeddings[-100:], cnt, "last 100 words, model %s" % model.modelname)
    weights_debug(model.parameters.hidden_weights.value, cnt, "hidden weights, model %s" % model.modelname)
    weights_debug(model.parameters.output_weights.value, cnt, "output weights, model %s" % model.modelname)
    logging.info(stats())

def visualizedebug(cnt, model, rundir, newkeystr, WORDCNT=500):
    idxs = range(model.parameters.vocab_size)
    random.shuffle(idxs)
    idxs = idxs[:WORDCNT]

    visualize(cnt, model, rundir, idxs, "randomized%s" % newkeystr)
    visualize(cnt, model, rundir, range(WORDCNT), "mostcommon%s" % newkeystr)
    visualize(cnt, model, rundir, range(-1, -WORDCNT*50, -1*50), "leastcommon%s" % newkeystr)
    visualize(cnt, model, rundir, range(model.parameters.vocab_size/2-WORDCNT*20/2,model.parameters.vocab_size/2+WORDCNT*20/2, 20), "midcommon%s" % newkeystr)

def visualize(cnt, model, rundir, idxs, str):
    """
    Visualize a set of examples using t-SNE.
    """
    from vocabulary import wordmap, wordform
    PERPLEXITY=30

    idxs = [id % model.parameters.embeddings.shape[0] for id in idxs]
    x = model.parameters.embeddings[idxs]
    print x.shape
    #titles = [`wordmap().str(id)` for id in idxs]
    titles = [wordform(id) for id in idxs]

    import os.path
    filename = os.path.join(rundir, "embeddings.model-%s.-%s-%d.png" % (model.modelname, str, cnt))
    try:
        from textSNE.calc_tsne import tsne
#       from textSNE.tsne import tsne
        out = tsne(x, perplexity=PERPLEXITY)
        from textSNE.render import render
        render([(title, point[0], point[1]) for title, point in zip(titles, out)], filename)
    except IOError:
        logging.info("ERROR visualizing", filename, ". Continuing...")

def embeddings_debug(w, cnt, str):
    """
    Output the l2norm mean and max of the embeddings, including in debug out the str and training cnt
    """
    totalcnt = numpy.sum(numpy.abs(w) >= 0)
    notsmallcnt = numpy.sum(numpy.abs(w) >= 0.1)
    logging.info("%d %s dimensions of %s have absolute value >= 0.1" % (cnt, percent(notsmallcnt, totalcnt), str))
    notsmallcnt = numpy.sum(numpy.abs(w) >= 0.01)
    logging.info("%d %s dimensions of %s have absolute value >= 0.01" % (cnt, percent(notsmallcnt, totalcnt), str))

    l2norm = numpy.sqrt(numpy.square(w).sum(axis=1))
    median = numpy.median(l2norm)
    mean = numpy.mean(l2norm)
    std = numpy.std(l2norm)
#    print("%d l2norm of top 100 words: mean = %f stddev=%f" % (cnt, numpy.mean(l2norm), numpy.std(l2norm),))
    l2norm = l2norm.tolist()
    l2norm.sort()
    l2norm.reverse()
    logging.info("%d l2norm of %s: median = %f mean = %f stddev=%f top3=%s" % (cnt, str, median, mean, std, `l2norm[:3]`))
#    print("top 5 = %s" % `l2norm[:5]`)

def weights_debug(w, cnt, str):
    """
    Output the abs median, mean, and max of the weights w, including in debug out the str and training cnt
    """
    w = numpy.abs(w)
    logging.info("%d abs of %s: median=%f mean=%f stddev=%f" % (cnt, str, numpy.median(w), numpy.mean(w), numpy.std(w),))
#    print("%d l2norm of top 100 words: mean = %f stddev=%f" % (cnt, numpy.mean(l2norm), numpy.std(l2norm),))
#    w = w.tolist()
#    w.sort()
#    w.reverse()
#    logging.info("\ttop 5 = %s" % `w[:5]`)
#    print("top 5 = %s" % `l2norm[:5]`)

########NEW FILE########
__FILENAME__ = dump-embeddings
#!/usr/bin/env python

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-m", "--modelfile", dest="modelfile")
(options, args) = parser.parse_args()
assert options.modelfile is not None

import cPickle
m = cPickle.load(open(options.modelfile))
#print m.parameters.embeddings.shape

from vocabulary import wordmap
for i in range(m.parameters.vocab_size):
    print wordmap.str(i),
    for v in m.parameters.embeddings[i]:
        print v,
    print

########NEW FILE########
__FILENAME__ = badrun
#!/usr/bin/python
#
#  For every filename in sys.stdin, add a file BAD to that run directory.
#  Read stdin until there is a blank line.
#
#   BUG: If the filename has a space in it, sorry you're out of luck.
#   BUG: We don't unescape quotes, we just strip them.
#

import sys, os.path, string
#assert len(sys.argv)>2

while 1:
#    for l in sys.stdin:
    l = sys.stdin.readline()
#    for l in sys.stdin:
    if string.strip(l) == "": break
    for f in string.split(l):
        f = f.replace('\"','').replace("\'",'')
        if not os.path.exists(f): continue
        d = os.path.dirname(os.path.realpath(f))
        newf = os.path.join(d, "BAD")
        print newf
        if os.path.exists(newf): continue
        cmd = "rm %s" % os.path.join(d, "*.dat")
        print >> sys.stderr, "Creating %s, %s" % (newf, cmd)
        open(newf, "wt").close()
        os.system("rm %s" % os.path.join(d, "*.dat"))

########NEW FILE########
__FILENAME__ = hyperparameters
"""
Module to update hyperparameters automatically.
"""

from os.path import join
import common.hyperparameters
HYPERPARAMETERS = common.hyperparameters.read("language-model")
HYPERPARAMETERS["DATA_DIR"] = HYPERPARAMETERS["locations"]["DATA_DIR"]
RUN_NAME = HYPERPARAMETERS["RUN_NAME"]
MONOLINGUAL_VOCABULARY_SIZE = HYPERPARAMETERS["MONOLINGUAL_VOCABULARY_SIZE"]
INCLUDE_UNKNOWN_WORD = HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"]
HYPERPARAMETERS["TRAIN_SENTENCES"] = join(HYPERPARAMETERS["DATA_DIR"], "%s.train.txt.gz" % RUN_NAME)
HYPERPARAMETERS["ORIGINAL VALIDATION_SENTENCES"] = join(HYPERPARAMETERS["DATA_DIR"], "%s.validation.txt.gz" % RUN_NAME)
HYPERPARAMETERS["VALIDATION_SENTENCES"] = join(HYPERPARAMETERS["DATA_DIR"], "%s.validation-%d.txt.gz" % (RUN_NAME, HYPERPARAMETERS["VALIDATION EXAMPLES"]))
HYPERPARAMETERS["MONOLINGUAL_VOCABULARY"] = join(HYPERPARAMETERS["DATA_DIR"], "vocabulary-%s-%d.txt.gz" % (RUN_NAME, MONOLINGUAL_VOCABULARY_SIZE))
HYPERPARAMETERS["MONOLINGUAL_VOCABULARY_IDMAP_FILE"] = join(HYPERPARAMETERS["DATA_DIR"], "idmap.%s-%d.include_unknown=%s.pkl.gz" % (RUN_NAME, MONOLINGUAL_VOCABULARY_SIZE, INCLUDE_UNKNOWN_WORD))
HYPERPARAMETERS["INITIAL_EMBEDDINGS"] = join(HYPERPARAMETERS["DATA_DIR"], "initial-embeddings.minfreq=%d.include_unknown=%s.pkl.gz" % (HYPERPARAMETERS["W2W MINIMUM WORD FREQUENCY"], HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"]))

########NEW FILE########
__FILENAME__ = lemmatizer
"""
Lemmatize English using the NLTK WordNetLemmatizer.
"""

from nltk.stem.wordnet import WordNetLemmatizer

_lmtzr = None
def lmtzr():
    global _lmtzr
    if _lmtzr is None: _lmtzr = WordNetLemmatizer()
    return _lmtzr

def lemmatize(language, wordform):
    assert language == "en"
    return lmtzr().lemmatize(wordform)

########NEW FILE########
__FILENAME__ = miscglobals
"""
Miscellaneous globals.

@todo: Most of these should be moved somewhere more specific.
"""

#: RNG seed
RANDOMSEED = 0

#LINKER      = 'c|py'
##LINKER      = 'py'
#OPTIMIZER   = 'merge'   # 'math' optimizer is broken with 'c|py' linker

########NEW FILE########
__FILENAME__ = graphcw
"""
Theano graph of Collobert & Weston language model.
"""

import theano
#import theano.sandbox.cuda
#theano.sandbox.cuda.use()

from theano.compile import pfunc, shared
from theano import config
floatX = config.floatX


from theano import tensor as t
from theano import scalar as s

from theano.tensor.basic import horizontal_stack
from theano.tensor import dot

from theano import gradient

import theano.compile
#from miscglobals import LINKER, OPTIMIZER
#mode = theano.compile.Mode(LINKER, OPTIMIZER)
#import theano.compile.debugmode
#COMPILE_MODE = theano.compile.debugmode.DebugMode(optimizer='fast_run', check_isfinite=False)
#import theano.compile.profilemode
#COMPILE_MODE = theano.compile.profilemode.ProfileMode()
COMPILE_MODE = theano.compile.Mode('c|py', 'fast_run')
#COMPILE_MODE = theano.compile.Mode('py', 'fast_compile')

import numpy

#hidden_weights = t.matrix()
#hidden_biases = t.matrix()

#if HYPERPARAMETERS["USE_SECOND_HIDDEN_LAYER"] == True:
#    hidden2_weights = t.matrix()
#    hidden2_biases = t.matrix()

#output_weights = t.matrix()
#output_biases = t.matrix()

# TODO: Include gradient steps in actual function, don't do them manually

def activation_function(r):
    from hyperparameters import HYPERPARAMETERS
    if HYPERPARAMETERS["ACTIVATION_FUNCTION"] == "sigmoid":
        return sigmoid(r)
    elif HYPERPARAMETERS["ACTIVATION_FUNCTION"] == "tanh":
        return t.tanh(r)
    elif HYPERPARAMETERS["ACTIVATION_FUNCTION"] == "softsign":
        from theano.sandbox.softsign import softsign
        return softsign(r)
    else:
        assert 0

def stack(x):
    """
    Horizontally stack a list of representations, and then compress them to
    one representation.
    """
    assert len(x) >= 2
    return horizontal_stack(*x)

def score(x):
    from hyperparameters import HYPERPARAMETERS
    prehidden = dot(x, hidden_weights) + hidden_biases
    hidden = activation_function(prehidden)
    if HYPERPARAMETERS["TWO_HIDDEN_LAYERS"] == True:
        prehidden2 = dot(hidden, hidden2_weights) + hidden2_biases
        hidden2 = activation_function(prehidden2)
        score = dot(hidden2, output_weights) + output_biases
    else:
        score = dot(hidden, output_weights) + output_biases
    return score, prehidden

cached_functions = {}
def functions(sequence_length):
    """
    Return two functions
     * The first function does prediction.
     * The second function does learning.
    """
    global cached_functions
    cachekey = (sequence_length)
    if len(cached_functions.keys()) > 1:
        # This is problematic because we use global variables for the model parameters.
        # Hence, we might be unsafe, if we are using the wrong model parameters globally.
        assert 0
    if cachekey not in cached_functions:
        print "Need to construct graph for sequence_length=%d..." % (sequence_length)
        # Create the sequence_length inputs.
        # Each is a t.matrix(), initial word embeddings (provided by
        # Jason + Ronan) to be transformed into an initial representation.
        # We could use a vector, but instead we use a matrix with one row.
        correct_inputs = [t.matrix() for i in range(sequence_length)]
        noise_inputs = [t.matrix() for i in range(sequence_length)]
        learning_rate = t.scalar()

        stacked_correct_inputs = stack(correct_inputs)
        stacked_noise_inputs = stack(noise_inputs)

        correct_score, correct_prehidden = score(stacked_correct_inputs)
        noise_score, noise_prehidden = score(stacked_noise_inputs)
        unpenalized_loss = t.clip(1 - correct_score + noise_score, 0, 1e999)

        from hyperparameters import HYPERPARAMETERS
        if HYPERPARAMETERS["CW_EMBEDDING_L1_PENALTY"] != 0:
            l1penalty = t.sum(t.abs_(stacked_correct_inputs) + t.abs_(stacked_noise_inputs), axis=1).T * HYPERPARAMETERS["CW_EMBEDDING_L1_PENALTY"]
        else:
            l1penalty = t.as_tensor_variable(numpy.asarray(0, dtype=floatX))
#            l1penalty = t.as_tensor_variable(numpy.asarray((0,), dtype=floatX))
        loss = (unpenalized_loss.T + l1penalty).T

#        import sys
#        print >> sys.stderr, "FIXME: MODEL_LEARNING_RATE = fixed at 0.001"
#        MODEL_LEARNING_RATE = t.as_tensor_variable(numpy.asarray(0.001, dtype=floatX))

        total_loss = t.sum(loss)

        if HYPERPARAMETERS["TWO_HIDDEN_LAYERS"] == True:
            (dhidden_weights, dhidden_biases, dhidden2_weights, dhidden2_biases, doutput_weights, doutput_biases) = t.grad(total_loss, [hidden_weights, hidden_biases, hidden2_weights, hidden2_biases, output_weights, output_biases])
        else:
            (dhidden_weights, dhidden_biases, doutput_weights, doutput_biases) = t.grad(total_loss, [hidden_weights, hidden_biases, output_weights, output_biases])
        if HYPERPARAMETERS["EMBEDDING_LEARNING_RATE"] != 0:
            dcorrect_inputs = t.grad(total_loss, correct_inputs)
            dnoise_inputs = t.grad(total_loss, noise_inputs)
        #print "REMOVEME", len(dcorrect_inputs)
        predict_inputs = correct_inputs
        train_inputs = correct_inputs + noise_inputs + [learning_rate]
        verbose_predict_inputs = predict_inputs
        predict_outputs = [correct_score]
        if HYPERPARAMETERS["EMBEDDING_LEARNING_RATE"] != 0:
            train_outputs = dcorrect_inputs + dnoise_inputs + [loss, unpenalized_loss, l1penalty, correct_score, noise_score]
        else:
            train_outputs = [loss, unpenalized_loss, l1penalty, correct_score, noise_score]
        verbose_predict_outputs = [correct_score, correct_prehidden]

        import theano.gof.graph

        nnodes = len(theano.gof.graph.ops(predict_inputs, predict_outputs))
        print "About to compile predict function over %d ops [nodes]..." % nnodes
        predict_function = pfunc(predict_inputs, predict_outputs, mode=COMPILE_MODE)
        print "...done constructing graph for sequence_length=%d" % (sequence_length)

        nnodes = len(theano.gof.graph.ops(verbose_predict_inputs, verbose_predict_outputs))
        print "About to compile predict function over %d ops [nodes]..." % nnodes
        verbose_predict_function = pfunc(verbose_predict_inputs, verbose_predict_outputs, mode=COMPILE_MODE)
        print "...done constructing graph for sequence_length=%d" % (sequence_length)

        nnodes = len(theano.gof.graph.ops(train_inputs, train_outputs))
        print "About to compile train function over %d ops [nodes]..." % nnodes
        if HYPERPARAMETERS["TWO_HIDDEN_LAYERS"] == True:
            train_function = pfunc(train_inputs, train_outputs, mode=COMPILE_MODE, updates=[(p, p-learning_rate*gp) for p, gp in zip((hidden_weights, hidden_biases, hidden2_weights, hidden2_biases, output_weights, output_biases), (dhidden_weights, dhidden_biases, dhidden2_weights, dhidden2_biases, doutput_weights, doutput_biases))])
        else:
            train_function = pfunc(train_inputs, train_outputs, mode=COMPILE_MODE, updates=[(p, p-learning_rate*gp) for p, gp in zip((hidden_weights, hidden_biases, output_weights, output_biases), (dhidden_weights, dhidden_biases, doutput_weights, doutput_biases))])
        print "...done constructing graph for sequence_length=%d" % (sequence_length)

        cached_functions[cachekey] = (predict_function, train_function, verbose_predict_function)
    return cached_functions[cachekey]

#def apply_function(fn, sequence, target_output, parameters):
#    assert len(sequence) == parameters.hidden_width
#    inputs = [numpy.asarray([token]) for token in sequence]
#    if target_output != None:
##        if HYPERPARAMETERS["USE_SECOND_HIDDEN_LAYER"]:
##            return fn(*(inputs + [numpy.asarray([target_output]), parameters.hidden_weights, parameters.hidden_biases, parameters.hidden2_weights, parameters.hidden2_biases, parameters.output_weights, parameters.output_biases]))
##        else:
#        return fn(*(inputs + [numpy.asarray([target_output]), parameters.hidden_weights, parameters.hidden_biases, parameters.output_weights, parameters.output_biases]))
#    else:
##        if HYPERPARAMETERS["USE_SECOND_HIDDEN_LAYER"]:
##            return fn(*(inputs + [parameters.hidden_weights, parameters.hidden_biases, parameters.hidden2_weights, parameters.hidden2_biases, parameters.output_weights, parameters.output_biases]))
##        else:
#        return fn(*(inputs + [parameters.hidden_weights, parameters.hidden_biases, parameters.output_weights, parameters.output_biases]))
#
def predict(correct_sequence):
    fn = functions(sequence_length=len(correct_sequence))[0]
#    print "REMOVEME", correct_sequence
    r = fn(*(correct_sequence))
    assert len(r) == 1
    r = r[0]
    assert r.shape == (1, 1)
    return r[0,0]
def verbose_predict(correct_sequence):
    fn = functions(sequence_length=len(correct_sequence))[2]
    r = fn(*(correct_sequence))
    assert len(r) == 2
    (score, prehidden) = r
    assert score.shape == (1, 1)
    return score[0,0], prehidden
def train(correct_sequence, noise_sequence, learning_rate):
    assert len(correct_sequence) == len(noise_sequence)
    fn = functions(sequence_length=len(correct_sequence))[1]
    r = fn(*(correct_sequence + noise_sequence + [learning_rate]))
    from hyperparameters import HYPERPARAMETERS
    if HYPERPARAMETERS["EMBEDDING_LEARNING_RATE"] != 0:
        dcorrect_inputs = r[:len(correct_sequence)]
        r = r[len(correct_sequence):]
        dnoise_inputs = r[:len(noise_sequence)]
        r = r[len(correct_sequence):]
#    print "REMOVEME", len(dcorrect_inputs), len(dnoise_inputs)
    (loss, unpenalized_loss, l1penalty, correct_score, noise_score) = r
#    if loss == 0:
#        for di in [dhidden_weights, dhidden_biases, doutput_weights, doutput_biases]:
#            assert (di == 0).all()

    if HYPERPARAMETERS["EMBEDDING_LEARNING_RATE"] != 0:
        return (dcorrect_inputs, dnoise_inputs, loss, unpenalized_loss, l1penalty, correct_score, noise_score)
    else:
        return (loss, unpenalized_loss, l1penalty, correct_score, noise_score)

########NEW FILE########
__FILENAME__ = graphlbl
"""
Theano graph of Mnih log bi-linear model.
"""

import theano
import theano.sandbox.cuda
theano.sandbox.cuda.use()

from theano import tensor as t
from theano import scalar as s

from theano.tensor.basic import horizontal_stack
from theano.tensor import dot

from theano import gradient

import theano.compile
#from miscglobals import LINKER, OPTIMIZER
#mode = theano.compile.Mode(LINKER, OPTIMIZER)
COMPILE_MODE = theano.compile.Mode('c|py', 'fast_run')
#COMPILE_MODE = theano.compile.Mode('py', 'fast_compile')

import numpy

from common.chopargs import chopargs

#output_weights = t.xmatrix()
#output_biases = t.xmatrix()

# TODO: Include gradient steps in actual function, don't do them manually

def activation_function(r):
    from hyperparameters import HYPERPARAMETERS
    if HYPERPARAMETERS["ACTIVATION_FUNCTION"] == "sigmoid":
        return sigmoid(r)
    elif HYPERPARAMETERS["ACTIVATION_FUNCTION"] == "tanh":
        return t.tanh(r)
    elif HYPERPARAMETERS["ACTIVATION_FUNCTION"] == "softsign":
        from theano.sandbox.softsign import softsign
        return softsign(r)
    else:
        assert 0

def stack(x):
    """
    Horizontally stack a list of representations, and then compress them to
    one representation.
    """
    assert len(x) >= 2
    return horizontal_stack(*x)

def score(targetrepr, predictrepr):
    # TODO: Is this the right scoring function?
    score = dot(targetrepr, predictrepr.T)
    return score

cached_functions = {}
def functions(sequence_length):
    """
    Return two functions
     * The first function does prediction.
     * The second function does learning.
    """
    global cached_functions
    p = (sequence_length)
    if len(cached_functions.keys()) > 1:
        # This is problematic because we use global variables for the model parameters.
        # Hence, we might be unsafe, if we are using the wrong model parameters globally.
        assert 0
    if p not in cached_functions:
        print "Need to construct graph for sequence_length=%d..." % (sequence_length)
        # Create the sequence_length inputs.
        # Each is a t.xmatrix(), initial word embeddings (provided by
        # Jason + Ronan) to be transformed into an initial representation.
        # We could use a vector, but instead we use a matrix with one row.
        sequence = [t.xmatrix() for i in range(sequence_length)]
        correct_repr = t.xmatrix()
        noise_repr = t.xmatrix()
#        correct_scorebias = t.xscalar()
#        noise_scorebias = t.xscalar()
        correct_scorebias = t.xvector()
        noise_scorebias = t.xvector()

        stackedsequence = stack(sequence)
        predictrepr = dot(stackedsequence, output_weights) + output_biases

        correct_score = score(correct_repr, predictrepr) + correct_scorebias
        noise_score = score(noise_repr, predictrepr) + noise_scorebias
        loss = t.clip(1 - correct_score + noise_score, 0, 1e999)

        (doutput_weights, doutput_biases) = t.grad(loss, [output_weights, output_biases])
        dsequence = t.grad(loss, sequence)
        (dcorrect_repr, dnoise_repr) = t.grad(loss, [correct_repr, noise_repr])
        (dcorrect_scorebias, dnoise_scorebias) = t.grad(loss, [correct_scorebias, noise_scorebias])
        #print "REMOVEME", len(dcorrect_inputs)
        predict_inputs = sequence + [correct_repr, correct_scorebias, output_weights, output_biases]
        train_inputs = sequence + [correct_repr, noise_repr, correct_scorebias, noise_scorebias, output_weights, output_biases]
        predict_outputs = [predictrepr, correct_score]
        train_outputs = [loss, predictrepr, correct_score, noise_score] + dsequence + [dcorrect_repr, dnoise_repr, doutput_weights, doutput_biases, dcorrect_scorebias, dnoise_scorebias]
#        train_outputs = [loss, correct_repr, correct_score, noise_repr, noise_score]

        import theano.gof.graph

        nnodes = len(theano.gof.graph.ops(predict_inputs, predict_outputs))
        print "About to compile predict function over %d ops [nodes]..." % nnodes
        predict_function = theano.function(predict_inputs, predict_outputs, mode=COMPILE_MODE)
        print "...done constructing graph for sequence_length=%d" % (sequence_length)

        nnodes = len(theano.gof.graph.ops(train_inputs, train_outputs))
        print "About to compile train function over %d ops [nodes]..." % nnodes
        train_function = theano.function(train_inputs, train_outputs, mode=COMPILE_MODE)
        print "...done constructing graph for sequence_length=%d" % (sequence_length)

        cached_functions[p] = (predict_function, train_function)
    return cached_functions[p]

#def apply_function(fn, sequence, target_output, parameters):
#    assert len(sequence) == parameters.hidden_width
#    inputs = [numpy.asarray([token]) for token in sequence]
#    if target_output != None:
##        if HYPERPARAMETERS["USE_SECOND_HIDDEN_LAYER"]:
##            return fn(*(inputs + [numpy.asarray([target_output]), parameters.hidden_weights, parameters.hidden_biases, parameters.hidden2_weights, parameters.hidden2_biases, parameters.output_weights, parameters.output_biases]))
##        else:
#        return fn(*(inputs + [numpy.asarray([target_output]), parameters.hidden_weights, parameters.hidden_biases, parameters.output_weights, parameters.output_biases]))
#    else:
##        if HYPERPARAMETERS["USE_SECOND_HIDDEN_LAYER"]:
##            return fn(*(inputs + [parameters.hidden_weights, parameters.hidden_biases, parameters.hidden2_weights, parameters.hidden2_biases, parameters.output_weights, parameters.output_biases]))
##        else:
#        return fn(*(inputs + [parameters.hidden_weights, parameters.hidden_biases, parameters.output_weights, parameters.output_biases]))
#

def predict(sequence, targetrepr, target_scorebias):
    fn = functions(sequence_length=len(sequence))[0]
    (predictrepr, score) = fn(*(sequence + [targetrepr, target_scorebias]))
    return predictrepr, score

def train(sequence, correct_repr, noise_repr, correct_scorebias, noise_scorebias, learning_rate):
    fn = functions(sequence_length=len(sequence))[1]
#    print "REMOVEME", correct_scorebias, noise_scorebias
#    print "REMOVEME", correct_scorebias[0], noise_scorebias[0]
    r = fn(*(sequence + [correct_repr, noise_repr, correct_scorebias, noise_scorebias]))

    (loss, predictrepr, correct_score, noise_score, dsequence, dcorrect_repr, dnoise_repr, doutput_weights, doutput_biases, dcorrect_scorebias, dnoise_scorebias) = chopargs(r, (0,0,0,0,len(sequence),0,0,0,0,0,0))
    if loss == 0:
        for di in [doutput_weights, doutput_biases]:
            # This tends to trigger if training diverges (NaN)
            assert (di == 0).all()

    parameters.output_weights   -= 1.0 * learning_rate * doutput_weights
    parameters.output_biases    -= 1.0 * learning_rate * doutput_biases

    # You also need to update score_biases here
    assert 0

    dsequence = list(dsequence)
    return (loss, predictrepr, correct_score, noise_score, dsequence, dcorrect_repr, dnoise_repr, dcorrect_scorebias, dnoise_scorebias)

########NEW FILE########
__FILENAME__ = model
from parameters import Parameters

from hyperparameters import HYPERPARAMETERS
LBL = HYPERPARAMETERS["LOG BILINEAR MODEL"]

if LBL:
    import graphlbl as graph
else:
    import graphcw as graph

import sys, pickle
import math
import logging

from common.file import myopen
from common.movingaverage import MovingAverage

from vocabulary import *

class Model:
    """
    A Model can:

    @type parameters: L{Parameters}
    @todo: Document
    """

    import hyperparameters
    import miscglobals
    import vocabulary
    def __init__(self, modelname="", window_size=HYPERPARAMETERS["WINDOW_SIZE"], vocab_size=vocabulary.wordmap().len, embedding_size=HYPERPARAMETERS["EMBEDDING_SIZE"], hidden_size=HYPERPARAMETERS["HIDDEN_SIZE"], seed=miscglobals.RANDOMSEED, initial_embeddings=None, two_hidden_layers=HYPERPARAMETERS["TWO_HIDDEN_LAYERS"]):
        self.modelname = modelname
        self.parameters = Parameters(window_size, vocab_size, embedding_size, hidden_size, seed, initial_embeddings, two_hidden_layers)
        if LBL:
            graph.output_weights = self.parameters.output_weights
            graph.output_biases = self.parameters.output_biases
            graph.score_biases = self.parameters.score_biases
        else:
            graph.hidden_weights = self.parameters.hidden_weights
            graph.hidden_biases = self.parameters.hidden_biases
            if self.parameters.two_hidden_layers:
                graph.hidden2_weights = self.parameters.hidden2_weights
                graph.hidden2_biases = self.parameters.hidden2_biases
            graph.output_weights = self.parameters.output_weights
            graph.output_biases = self.parameters.output_biases

#        (self.graph_train, self.graph_predict, self.graph_verbose_predict) = graph.functions(self.parameters)
        import sets
        self.train_loss = MovingAverage()
        self.train_err = MovingAverage()
        self.train_lossnonzero = MovingAverage()
        self.train_squashloss = MovingAverage()
        self.train_unpenalized_loss = MovingAverage()
        self.train_l1penalty = MovingAverage()
        self.train_unpenalized_lossnonzero = MovingAverage()
        self.train_correct_score = MovingAverage()
        self.train_noise_score = MovingAverage()
        self.train_cnt = 0

    def __getstate__(self):
        return (self.modelname, self.parameters, self.train_loss, self.train_err, self.train_lossnonzero, self.train_squashloss, self.train_unpenalized_loss, self.train_l1penalty, self.train_unpenalized_lossnonzero, self.train_correct_score, self.train_noise_score, self.train_cnt)

    def __setstate__(self, state):
        (self.modelname, self.parameters, self.train_loss, self.train_err, self.train_lossnonzero, self.train_squashloss, self.train_unpenalized_loss, self.train_l1penalty, self.train_unpenalized_lossnonzero, self.train_correct_score, self.train_noise_score, self.train_cnt) = state
        if LBL:
            graph.output_weights = self.parameters.output_weights
            graph.output_biases = self.parameters.output_biases
            graph.score_biases = self.parameters.score_biases
        else:
            graph.hidden_weights = self.parameters.hidden_weights
            graph.hidden_biases = self.parameters.hidden_biases
            if self.parameters.two_hidden_layers:
                graph.hidden2_weights = self.parameters.hidden2_weights
                graph.hidden2_biases = self.parameters.hidden2_biases
            graph.output_weights = self.parameters.output_weights
            graph.output_biases = self.parameters.output_biases

#    def load(self, filename):
#        sys.stderr.write("Loading model from: %s\n" % filename)
#        f = myopen(filename, "rb")
#        (self.parameters, self.train_loss, self.train_err, self.train_lossnonzero, self.train_squashloss, self.train_unpenalized_loss, self.train_l1penalty, self.train_unpenalized_lossnonzero, self.train_correct_score, self.train_noise_score, self.train_cnt) = pickle.load(f)
#        if LBL:
#            graph.output_weights = self.parameters.output_weights
#            graph.output_biases = self.parameters.output_biases
#            graph.score_biases = self.parameters.score_biases
#        else:
#            graph.hidden_weights = self.parameters.hidden_weights
#            graph.hidden_biases = self.parameters.hidden_biases
#            graph.output_weights = self.parameters.output_weights
#            graph.output_biases = self.parameters.output_biases
#
#    def save(self, filename):
#        sys.stderr.write("Saving model to: %s\n" % filename)
#        f = myopen(filename, "wb")
#        pickle.dump((self.parameters, self.train_loss, self.train_err, self.train_lossnonzero, self.train_squashloss, self.train_unpenalized_loss, self.train_l1penalty, self.train_unpenalized_lossnonzero, self.train_correct_score, self.train_noise_score, self.train_cnt), f)

    def embed(self, sequence):
        """
        Embed a sequence of vocabulary IDs
        """
        seq = [self.parameters.embeddings[s] for s in sequence]
        import numpy
        return [numpy.resize(s, (1, s.size)) for s in seq]
#        return [self.parameters.embeddings[s] for s in sequence]

    def embeds(self, sequences):
        """
        Embed sequences of vocabulary IDs.
        If we are given a list of MINIBATCH lists of SEQLEN items, return a list of SEQLEN matrices of shape (MINIBATCH, EMBSIZE)
        """
        embs = []
        for sequence in sequences:
            embs.append(self.embed(sequence))

        for emb in embs: assert len(emb) == len(embs[0])

        new_embs = []
        for i in range(len(embs[0])):
            colembs = [embs[j][i] for j in range(len(embs))]
            import numpy
            new_embs.append(numpy.vstack(colembs))
            assert new_embs[-1].shape == (len(sequences), self.parameters.embedding_size)
        assert len(new_embs) == len(sequences[0])
        return new_embs

    def train(self, correct_sequences, noise_sequences, weights):
        from hyperparameters import HYPERPARAMETERS
        learning_rate = HYPERPARAMETERS["LEARNING_RATE"]

        # All weights must be the same, because of how we use a scalar learning rate
        assert HYPERPARAMETERS["UNIFORM EXAMPLE WEIGHTS"]
        if HYPERPARAMETERS["UNIFORM EXAMPLE WEIGHTS"]:
            for w in weights: assert w == weights[0]

        if LBL:
            # REWRITE FOR MINIBATCH
            assert 0

#            noise_repr = noise_sequence[-1]
#            correct_repr = correct_sequence[-1]
            noise_repr = noise_sequence[-1:]
            correct_repr = correct_sequence[-1:]
            assert noise_repr != correct_repr
            assert noise_sequence[:-1] == correct_sequence[:-1]
            sequence = correct_sequence[:-1]
#            r = graph.train(self.embed(sequence), self.embed([correct_repr])[0], self.embed([noise_repr])[0], self.parameters.score_biases[correct_repr], self.parameters.score_biases[noise_repr])
            r = graph.train(self.embed(sequence), self.embed(correct_repr)[0], self.embed(noise_repr)[0], self.parameters.score_biases[correct_repr], self.parameters.score_biases[noise_repr], learning_rate * weight)
            assert len(noise_repr) == 1
            assert len(correct_repr) == 1
            noise_repr = noise_repr[0]
            correct_repr = correct_repr[0]
            (loss, predictrepr, correct_score, noise_score, dsequence, dcorrect_repr, dnoise_repr, dcorrect_scorebias, dnoise_scorebias) = r
#            print
#            print "loss = ", loss
#            print "predictrepr = ", predictrepr
#            print "correct_repr = ", correct_repr, self.embed(correct_repr)[0]
#            print "noise_repr = ", noise_repr, self.embed(noise_repr)[0]
#            print "correct_score = ", correct_score
#            print "noise_score = ", noise_score
        else:
            r = graph.train(self.embeds(correct_sequences), self.embeds(noise_sequences), learning_rate * weights[0])
            if HYPERPARAMETERS["EMBEDDING_LEARNING_RATE"] != 0:
                (dcorrect_inputss, dnoise_inputss, losss, unpenalized_losss, l1penaltys, correct_scores, noise_scores) = r
            else:
                (losss, unpenalized_losss, l1penaltys, correct_scores, noise_scores) = r
#            print [d.shape for d in dcorrect_inputss]
#            print [d.shape for d in dnoise_inputss]
#            print "losss", losss.shape, losss
#            print "unpenalized_losss", unpenalized_losss.shape, unpenalized_losss
#            print "l1penaltys", l1penaltys.shape, l1penaltys
#            print "correct_scores", correct_scores.shape, correct_scores
#            print "noise_scores", noise_scores.shape, noise_scores

        import sets
        to_normalize = sets.Set()
        for ecnt in range(len(correct_sequences)):
            (loss, unpenalized_loss, correct_score, noise_score) = \
                (losss[ecnt], unpenalized_losss[ecnt], correct_scores[ecnt], noise_scores[ecnt])
            if l1penaltys.shape == ():
                assert l1penaltys == 0
                l1penalty = 0
            else:
                l1penalty = l1penaltys[ecnt]
            correct_sequence = correct_sequences[ecnt]
            noise_sequence = noise_sequences[ecnt]

            if HYPERPARAMETERS["EMBEDDING_LEARNING_RATE"] != 0:
                dcorrect_inputs = [d[ecnt] for d in dcorrect_inputss]
                dnoise_inputs = [d[ecnt] for d in dnoise_inputss]

#            print [d.shape for d in dcorrect_inputs]
#            print [d.shape for d in dnoise_inputs]
#            print "loss", loss.shape, loss
#            print "unpenalized_loss", unpenalized_loss.shape, unpenalized_loss
#            print "l1penalty", l1penalty.shape, l1penalty
#            print "correct_score", correct_score.shape, correct_score
#            print "noise_score", noise_score.shape, noise_score


            self.train_loss.add(loss)
            self.train_err.add(correct_score <= noise_score)
            self.train_lossnonzero.add(loss > 0)
            squashloss = 1./(1.+math.exp(-loss))
            self.train_squashloss.add(squashloss)
            if not LBL:
                self.train_unpenalized_loss.add(unpenalized_loss)
                self.train_l1penalty.add(l1penalty)
                self.train_unpenalized_lossnonzero.add(unpenalized_loss > 0)
            self.train_correct_score.add(correct_score)
            self.train_noise_score.add(noise_score)
    
            self.train_cnt += 1
            if self.train_cnt % 10000 == 0:
    #        if self.train_cnt % 1000 == 0:
    #            print self.train_cnt
#                graph.COMPILE_MODE.print_summary()
                logging.info(("After %d updates, pre-update train loss %s" % (self.train_cnt, self.train_loss.verbose_string())))
                logging.info(("After %d updates, pre-update train error %s" % (self.train_cnt, self.train_err.verbose_string())))
                logging.info(("After %d updates, pre-update train Pr(loss != 0) %s" % (self.train_cnt, self.train_lossnonzero.verbose_string())))
                logging.info(("After %d updates, pre-update train squash(loss) %s" % (self.train_cnt, self.train_squashloss.verbose_string())))
                if not LBL:
                    logging.info(("After %d updates, pre-update train unpenalized loss %s" % (self.train_cnt, self.train_unpenalized_loss.verbose_string())))
                    logging.info(("After %d updates, pre-update train l1penalty %s" % (self.train_cnt, self.train_l1penalty.verbose_string())))
                    logging.info(("After %d updates, pre-update train Pr(unpenalized loss != 0) %s" % (self.train_cnt, self.train_unpenalized_lossnonzero.verbose_string())))
                logging.info(("After %d updates, pre-update train correct score %s" % (self.train_cnt, self.train_correct_score.verbose_string())))
                logging.info(("After %d updates, pre-update train noise score %s" % (self.train_cnt, self.train_noise_score.verbose_string())))

                self.debug_prehidden_values(correct_sequences)
    
                if LBL:
                    i = 1.
                    while i < wordmap.len:
                        inti = int(i)
                        str = "word %s, rank %d, score %f" % (wordmap.str(inti), inti, self.parameters.score_biases[inti])
                        logging.info("After %d updates, score biases: %s" % (self.train_cnt, str))
                        i *= 3.2
    
    #            print(("After %d updates, pre-update train loss %s" % (self.train_cnt, self.train_loss.verbose_string())))
    #            print(("After %d updates, pre-update train error %s" % (self.train_cnt, self.train_err.verbose_string())))
    

            # All weights must be the same, because of how we use a scalar learning rate
            assert HYPERPARAMETERS["UNIFORM EXAMPLE WEIGHTS"]
            if HYPERPARAMETERS["UNIFORM EXAMPLE WEIGHTS"]:
                for w in weights: assert w == weights[0]
            embedding_learning_rate = HYPERPARAMETERS["EMBEDDING_LEARNING_RATE"] * weights[0]
            if loss == 0:
                if LBL:
                    for di in dsequence + [dcorrect_repr, dnoise_repr]:
                        # This tends to trigger if training diverges (NaN)
                        assert (di == 0).all()
    #                if not (di == 0).all():
    #                    print "WARNING:", di
    #                    print "WARNING in ", dsequence + [dcorrect_repr, dnoise_repr]
    #                    print "loss = ", loss
    #                    print "predictrepr = ", predictrepr
    #                    print "correct_repr = ", correct_repr, self.embed(correct_repr)[0]
    #                    print "noise_repr = ", noise_repr, self.embed(noise_repr)[0]
    #                    print "correct_score = ", correct_score
    #                    print "noise_score = ", noise_score
                else:
                    if HYPERPARAMETERS["EMBEDDING_LEARNING_RATE"] != 0:
                        for di in dcorrect_inputs + dnoise_inputs:
                            assert (di == 0).all()
    
            if loss != 0:
                if LBL:
                    val = sequence + [correct_repr, noise_repr]
                    dval = dsequence + [dcorrect_repr, dnoise_repr]
    #                print val
                    for (i, di) in zip(val, dval):
    #                for (i, di) in zip(tuple(sequence + [correct_repr, noise_repr]), tuple(dsequence + [dcorrect_repr, dnoise_repr])):
                        assert di.shape[0] == 1
                        di.resize(di.size)
    #                    print i, di
                        self.parameters.embeddings[i] -= 1.0 * embedding_learning_rate * di
                        if HYPERPARAMETERS["NORMALIZE_EMBEDDINGS"]:
                            to_normalize.add(i)
    
                    for (i, di) in zip([correct_repr, noise_repr], [dcorrect_scorebias, dnoise_scorebias]):
                        self.parameters.score_biases[i] -= 1.0 * embedding_learning_rate * di
    #                    print "REMOVEME", i, self.parameters.score_biases[i]
                else:
                    if HYPERPARAMETERS["EMBEDDING_LEARNING_RATE"] != 0:
                        for (i, di) in zip(correct_sequence, dcorrect_inputs):
    #                        assert di.shape[0] == 1
    #                        di.resize(di.size)
        #                    print i, di
                            assert di.shape == (self.parameters.embedding_size,)
                            self.parameters.embeddings[i] -= 1.0 * embedding_learning_rate * di
                            if HYPERPARAMETERS["NORMALIZE_EMBEDDINGS"]:
                                to_normalize.add(i)
                        for (i, di) in zip(noise_sequence, dnoise_inputs):
    #                        assert di.shape[0] == 1
    #                        di.resize(di.size)
        #                    print i, di
                            assert di.shape == (self.parameters.embedding_size,)
                            self.parameters.embeddings[i] -= 1.0 * embedding_learning_rate * di
                            if HYPERPARAMETERS["NORMALIZE_EMBEDDINGS"]:
                                to_normalize.add(i)
        #                print to_normalize
    
        if len(to_normalize) > 0:
            to_normalize = [i for i in to_normalize]
#            print "NORMALIZING", to_normalize
            self.parameters.normalize(to_normalize)



    def predict(self, sequence):
        if LBL:
            targetrepr = sequence[-1:]
            sequence = sequence[:-1]
            (predictrepr, score) = graph.predict(self.embed(sequence), self.embed(targetrepr)[0], self.parameters.score_biases[targetrepr], self.parameters)
            return score
        else:
            (score) = graph.predict(self.embed(sequence), self.parameters)
            return score

    def verbose_predict(self, sequence):
        if LBL:
            assert 0
        else:
            (score, prehidden) = graph.verbose_predict(self.embed(sequence))
            return score, prehidden
    
    def debug_prehidden_values(self, sequences):
        """
        Give debug output on pre-squash hidden values.
        """
        import numpy
        for (i, ve) in enumerate(sequences):
            (score, prehidden) = self.verbose_predict(ve)
            abs_prehidden = numpy.abs(prehidden)
            med = numpy.median(abs_prehidden)
            abs_prehidden = abs_prehidden.tolist()
            assert len(abs_prehidden) == 1
            abs_prehidden = abs_prehidden[0]
            abs_prehidden.sort()
            abs_prehidden.reverse()

            logging.info("model %s, %s %s %s %s %s" % (self.modelname, self.train_cnt, "abs(pre-squash hidden) median =", med, "max =", abs_prehidden[:3]))
            if i+1 >= 3: break

    def validate(self, sequence):
        """
        Get the rank of this final word, as opposed to all other words in the vocabulary.
        """
        import random
        r = random.Random()
        r.seed(0)
        from hyperparameters import HYPERPARAMETERS

        import copy
        corrupt_sequence = copy.copy(sequence)
        rank = 1
        correct_score = self.predict(sequence)
#        print "CORRECT", correct_score, [wordmap.str(id) for id in sequence]
        for i in range(self.parameters.vocab_size):
            if r.random() > HYPERPARAMETERS["PERCENT OF NOISE EXAMPLES FOR VALIDATION LOGRANK"]: continue
            if i == sequence[-1]: continue
            corrupt_sequence[-1] = i
            corrupt_score = self.predict(corrupt_sequence)
            if correct_score <= corrupt_score:
#                print " CORRUPT", corrupt_score, [wordmap.str(id) for id in corrupt_sequence]
                rank += 1
        return rank

    def validate_errors(self, correct_sequences, noise_sequences):
        """
        Count the errors in this validation batch.
        """

#            r = graph.train(self.embeds(correct_sequences), self.embeds(noise_sequences), learning_rate * weights[0])
        correct_scores = graph.predict(self.embeds(correct_sequences))
        noise_scores = graph.predict(self.embeds(noise_sequences))

#        print correct_scores
#        print noise_scores
        return correct_scores > noise_scores
##        print "CORRECT", correct_score, [wordmap.str(id) for id in sequence]
#        for i in range(self.parameters.vocab_size):
#            if r.random() > HYPERPARAMETERS["PERCENT OF NOISE EXAMPLES FOR VALIDATION LOGRANK"]: continue
#            if i == sequence[-1]: continue
#            corrupt_sequence[-1] = i
#            corrupt_score = self.predict(corrupt_sequence)
#            if correct_score <= corrupt_score:
##                print " CORRUPT", corrupt_score, [wordmap.str(id) for id in corrupt_sequence]
#                rank += 1
#        return rank

########NEW FILE########
__FILENAME__ = parameters
"""
@todo: WRITEME
"""

from theano import config
from theano.compile.sandbox import shared

import copy

floatX = config.floatX

from hyperparameters import HYPERPARAMETERS
LBL = HYPERPARAMETERS["LOG BILINEAR MODEL"]

class Parameters:
    """
    Parameters used by the L{Model}.
    @todo: Document these
    """

    def __init__(self, window_size, vocab_size, embedding_size, hidden_size, seed, initial_embeddings, two_hidden_layers):
        """
        Initialize L{Model} parameters.
        """

        self.vocab_size     = vocab_size
        self.window_size    = window_size
        self.embedding_size = embedding_size
        self.two_hidden_layers = two_hidden_layers
        if LBL:
            self.hidden_size    = hidden_size
            self.output_size    = self.embedding_size
        else:
            self.hidden_size    = hidden_size
            self.output_size    = 1

        import numpy
        import hyperparameters

        from pylearn.algorithms.weights import random_weights
        numpy.random.seed(seed)
        if initial_embeddings is None:
            self.embeddings = numpy.asarray((numpy.random.rand(self.vocab_size, HYPERPARAMETERS["EMBEDDING_SIZE"]) - 0.5)*2 * HYPERPARAMETERS["INITIAL_EMBEDDING_RANGE"], dtype=floatX)
        else:
            assert initial_embeddings.shape == (self.vocab_size, HYPERPARAMETERS["EMBEDDING_SIZE"])
            self.embeddings = copy.copy(initial_embeddings)
        if HYPERPARAMETERS["NORMALIZE_EMBEDDINGS"]: self.normalize(range(self.vocab_size))
        if LBL:
            self.output_weights = shared(numpy.asarray(random_weights(self.input_size, self.output_size, scale_by=HYPERPARAMETERS["SCALE_INITIAL_WEIGHTS_BY"]), dtype=floatX))
            self.output_biases = shared(numpy.asarray(numpy.zeros((1, self.output_size)), dtype=floatX))
            self.score_biases = shared(numpy.asarray(numpy.zeros(self.vocab_size), dtype=floatX))
            assert not self.two_hidden_layers
        else:
            self.hidden_weights = shared(numpy.asarray(random_weights(self.input_size, self.hidden_size, scale_by=HYPERPARAMETERS["SCALE_INITIAL_WEIGHTS_BY"]), dtype=floatX))
            self.hidden_biases = shared(numpy.asarray(numpy.zeros((self.hidden_size,)), dtype=floatX))
            if self.two_hidden_layers:
                self.hidden2_weights = shared(numpy.asarray(random_weights(self.hidden_size, self.hidden_size, scale_by=HYPERPARAMETERS["SCALE_INITIAL_WEIGHTS_BY"]), dtype=floatX))
                self.hidden2_biases = shared(numpy.asarray(numpy.zeros((self.hidden_size,)), dtype=floatX))
            self.output_weights = shared(numpy.asarray(random_weights(self.hidden_size, self.output_size, scale_by=HYPERPARAMETERS["SCALE_INITIAL_WEIGHTS_BY"]), dtype=floatX))
            self.output_biases = shared(numpy.asarray(numpy.zeros((self.output_size,)), dtype=floatX))

    input_size = property(lambda self:
                                LBL*((self.window_size-1) * self.embedding_size) + (1-LBL)*(self.window_size * self.embedding_size))
    
    def normalize(self, indices):
        """
        Normalize such that the l2 norm of the embeddings indices passed in.
        @todo: l1 norm?
        @return: The normalized embeddings
        """
        import numpy
        l2norm = numpy.square(self.embeddings[indices]).sum(axis=1)
        l2norm = numpy.sqrt(l2norm.reshape((len(indices), 1)))

        self.embeddings[indices] /= l2norm
        import math
        self.embeddings[indices] *= math.sqrt(self.embeddings.shape[1])
    
        # TODO: Assert that norm is correct
    #    l2norm = (embeddings * embeddings).sum(axis=1)
    #    print l2norm.shape
    #    print (l2norm == numpy.ones((vocabsize)) * HYPERPARAMETERS["EMBEDDING_SIZE"])
    #    print (l2norm == numpy.ones((vocabsize)) * HYPERPARAMETERS["EMBEDDING_SIZE"]).all()

########NEW FILE########
__FILENAME__ = build-vocabulary
#!/usr/bin/env python

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    import vocabulary
    import common.idmap

    words = []

    import string
    for i, l in enumerate(common.file.myopen(HYPERPARAMETERS["MONOLINGUAL_VOCABULARY"])):
        if HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"] and i+1 >= HYPERPARAMETERS["MONOLINGUAL_VOCABULARY_SIZE"]:
            break
        if not HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"] and i >= HYPERPARAMETERS["MONOLINGUAL_VOCABULARY_SIZE"]:
            break
        (cnt, w) = string.split(l)
        words.append(w)

    v = common.idmap.IDmap(words, allow_unknown=HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"])
    assert v.len == HYPERPARAMETERS["MONOLINGUAL_VOCABULARY_SIZE"]
    vocabulary.write(v)

########NEW FILE########
__FILENAME__ = corrupt
"""
Methods for corrupting examples.
"""

def corrupt_example(model, e):
    """
    Return a corrupted version of example e, plus the weight of this example.
    """
    from hyperparameters import HYPERPARAMETERS
    import random
    import copy
    e = copy.copy(e)
    last = e[-1]
    cnt = 0
    while e[-1] == last:
        if HYPERPARAMETERS["NGRAM_FOR_TRAINING_NOISE"] == 0:
            e[-1] = random.randint(0, model.parameters.vocab_size-1)
            pr = 1./model.parameters.vocab_size
        elif HYPERPARAMETERS["NGRAM_FOR_TRAINING_NOISE"] == 1:
            import noise
            from common.myrandom import weighted_sample
            e[-1], pr = weighted_sample(noise.indexed_weights())
#            from vocabulary import wordmap
#            print wordmap.str(e[-1]), pr
        else:
            assert 0
        cnt += 1
        # Backoff to 0gram smoothing if we fail 10 times to get noise.
        if cnt > 10: e[-1] = random.randint(0, model.parameters.vocab_size-1)
    weight = 1./pr
    return e, weight

def corrupt_examples(model, correct_sequences):
    noise_sequences = []
    weights = []
    for e in correct_sequences:
        noise_sequence, weight = model.corrupt_example(e)
        noise_sequences.append(noise_sequence)
        weights.append(weight)
    return noise_sequences, weights

########NEW FILE########
__FILENAME__ = examples
"""
Methods for getting examples.
"""

from common.stats import stats
from common.file import myopen
import string

import common.hyperparameters
import sys

class TrainingExampleStream(object):
    def __init__(self):
        self.count = 0
        pass
    
    def __iter__(self):
        HYPERPARAMETERS = common.hyperparameters.read("language-model")
        from vocabulary import wordmap
        self.filename = HYPERPARAMETERS["TRAIN_SENTENCES"]
        self.count = 0
        for l in myopen(self.filename):
            prevwords = []
            for w in string.split(l):
                w = string.strip(w)
                id = None
                if wordmap.exists(w):
                    prevwords.append(wordmap.id(w))
                    if len(prevwords) >= HYPERPARAMETERS["WINDOW_SIZE"]:
                        self.count += 1
                        yield prevwords[-HYPERPARAMETERS["WINDOW_SIZE"]:]
                else:
                    # If we can learn an unknown word token, we should
                    # delexicalize the word, not discard the example!
                    if HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"]: assert 0
                    prevwords = []

    def __getstate__(self):
        return self.filename, self.count

    def __setstate__(self, state):
        """
        @warning: We ignore the filename.  If we wanted
        to be really fastidious, we would assume that
        HYPERPARAMETERS["TRAIN_SENTENCES"] might change.  The only
        problem is that if we change filesystems, the filename
        might change just because the base file is in a different
        path. So we issue a warning if the filename is different from
        """
        filename, count = state
        print >> sys.stderr, ("__setstate__(%s)..." % `state`)
        print >> sys.stderr, (stats())
        iter = self.__iter__()
        while count != self.count:
#            print count, self.count
            iter.next()
        if self.filename != filename:
            assert self.filename == HYPERPARAMETERS["TRAIN_SENTENCES"]
            print >> sys.stderr, ("self.filename %s != filename given to __setstate__ %s" % (self.filename, filename))
        print >> sys.stderr, ("...__setstate__(%s)" % `state`)
        print >> sys.stderr, (stats())

class TrainingMinibatchStream(object):
    def __init__(self):
        pass
    
    def __iter__(self):
        HYPERPARAMETERS = common.hyperparameters.read("language-model")
        minibatch = []
        self.get_train_example = TrainingExampleStream()
        for e in self.get_train_example:
#            print self.get_train_example.__getstate__()
            minibatch.append(e)
            if len(minibatch) >= HYPERPARAMETERS["MINIBATCH SIZE"]:
                assert len(minibatch) == HYPERPARAMETERS["MINIBATCH SIZE"]
                yield minibatch
                minibatch = []

    def __getstate__(self):
        return (self.get_train_example.__getstate__(),)

    def __setstate__(self, state):
        """
        @warning: We ignore the filename.
        """
        self.get_train_example = TrainingExampleStream()
        self.get_train_example.__setstate__(state[0])

def get_validation_example():
    HYPERPARAMETERS = common.hyperparameters.read("language-model")

    from vocabulary import wordmap
    for l in myopen(HYPERPARAMETERS["VALIDATION_SENTENCES"]):
        prevwords = []
        for w in string.split(l):
            w = string.strip(w)
            if wordmap.exists(w):
                prevwords.append(wordmap.id(w))
                if len(prevwords) >= HYPERPARAMETERS["WINDOW_SIZE"]:
                    yield prevwords[-HYPERPARAMETERS["WINDOW_SIZE"]:]
            else:
                # If we can learn an unknown word token, we should
                # delexicalize the word, not discard the example!
                if HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"]: assert 0
                prevwords = []

########NEW FILE########
__FILENAME__ = noise
"""
Sophisticated training noise.
"""

from vocabulary import wordmap

from common.myrandom import build
import sys

_indexed_weights = None
def indexed_weights():
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    global _indexed_weights
    if _indexed_weights is not None:
        return _indexed_weights
    print >> sys.stderr, wordmap.len, "=?=", HYPERPARAMETERS["MONOLINGUAL_VOCABULARY_SIZE"]
    assert wordmap.len == HYPERPARAMETERS["MONOLINGUAL_VOCABULARY_SIZE"]
    if HYPERPARAMETERS["NGRAM_FOR_TRAINING_NOISE"] == 0:
        _indexed_weights = [1 for id in range(wordmap.len)]
    elif HYPERPARAMETERS["NGRAM_FOR_TRAINING_NOISE"] == 1:
        from common.json import load
        from common.file import myopen
        ngrams_file = HYPERPARAMETERS["NGRAMS"][(HYPERPARAMETERS["NGRAM_FOR_TRAINING_NOISE"], HYPERPARAMETERS["MONOLINGUAL_VOCABULARY_SIZE"])]
        print >> sys.stderr, "Reading ngrams from", ngrams_file, "..."
        from collections import defaultdict
        ngramcnt = defaultdict(int)
        for (ngram, cnt) in load(myopen(ngrams_file)):
            assert len(ngram) == 1
            ngramcnt[ngram[0]] = cnt + HYPERPARAMETERS["TRAINING_NOISE_SMOOTHING_ADDITION"]
        _indexed_weights = [ngramcnt[wordmap.str(id)] for id in range(wordmap.len)]
        _indexed_weights = build(_indexed_weights)
    else: assert 0
    return _indexed_weights

########NEW FILE########
__FILENAME__ = state
"""
Save and load training state.
@todo: Training state variables (cnt, epoch, trainstate) should all be combined into one object.
"""

import logging
import os.path
import cPickle

from common.stats import stats
from common.file import myopen
import sys

_lastfilename = None
def save(model, cnt, epoch, trainstate, rundir, newkeystr):
    global _lastfilename

    filename = os.path.join(rundir, "model-%d%s.pkl" % (cnt, newkeystr))
    logging.info("Writing model to %s..." % filename)
    logging.info(stats())
    cPickle.dump(model, myopen(filename, "wb"), protocol=-1)
    logging.info("...done writing model to %s" % filename)
    logging.info(stats())

    if _lastfilename is not None:
        logging.info("Removing old model %s..." % _lastfilename)
        try:
            os.remove(_lastfilename)
            logging.info("...removed %s" % _lastfilename)
        except:
            logging.info("Could NOT remove %s" % _lastfilename)
    _lastfilename = filename

    filename = os.path.join(rundir, "trainstate.pkl")
    cPickle.dump((trainstate, cnt, epoch), myopen(filename, "wb"), protocol=-1)

    filename = os.path.join(rundir, "newkeystr.txt")
    myopen(filename, "wt").write(newkeystr)

def load(rundir, newkeystr):
    """
    Read the directory and load the model, the training count, the training epoch, and the training state.
    """
    global _lastfilename

    filename = os.path.join(rundir, "newkeystr.txt")
    assert newkeystr == myopen(filename).read()

    filename = os.path.join(rundir, "trainstate.pkl")
    (trainstate, cnt, epoch) = cPickle.load(myopen(filename))

    filename = os.path.join(rundir, "model-%d%s.pkl" % (cnt, newkeystr))
    print >> sys.stderr, ("Reading model from %s..." % filename)
    print >> sys.stderr, (stats())
    model = cPickle.load(myopen(filename))
    print >> sys.stderr, ("...done reading model from %s" % filename)
    print >> sys.stderr, (stats())
    _lastfilename = filename

    return (model, cnt, epoch, trainstate)

########NEW FILE########
__FILENAME__ = train
#!/usr/bin/env python

import sys
import string
import common.dump
from common.file import myopen
from common.stats import stats

import miscglobals
import logging

import examples
import diagnostics
import state

def validate(cnt):
    import math
    logranks = []
    logging.info("BEGINNING VALIDATION AT TRAINING STEP %d" % cnt)
    logging.info(stats())
    i = 0
    for (i, ve) in enumerate(examples.get_validation_example()):
#        logging.info([wordmap.str(id) for id in ve])
        logranks.append(math.log(m.validate(ve)))
        if (i+1) % 10 == 0:
            logging.info("Training step %d, validating example %d, mean(logrank) = %.2f, stddev(logrank) = %.2f" % (cnt, i+1, numpy.mean(numpy.array(logranks)), numpy.std(numpy.array(logranks))))
            logging.info(stats())
    logging.info("FINAL VALIDATION AT TRAINING STEP %d: mean(logrank) = %.2f, stddev(logrank) = %.2f, cnt = %d" % (cnt, numpy.mean(numpy.array(logranks)), numpy.std(numpy.array(logranks)), i+1))
    logging.info(stats())
#    print "FINAL VALIDATION AT TRAINING STEP %d: mean(logrank) = %.2f, stddev(logrank) = %.2f, cnt = %d" % (cnt, numpy.mean(numpy.array(logranks)), numpy.std(numpy.array(logranks)), i+1)
#    print stats()

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    from common import myyaml
    import sys
    print >> sys.stderr, myyaml.dump(common.dump.vars_seq([hyperparameters, miscglobals]))

    import noise
    indexed_weights = noise.indexed_weights()

    from rundir import rundir
    rundir = rundir()

    import os.path, os
    logfile = os.path.join(rundir, "log")
    if newkeystr != "":
        verboselogfile = os.path.join(rundir, "log%s" % newkeystr)
        print >> sys.stderr, "Logging to %s, and creating link %s" % (logfile, verboselogfile)
        os.system("ln -s log %s " % (verboselogfile))
    else:
        print >> sys.stderr, "Logging to %s, not creating any link because of default settings" % logfile

    import random, numpy
    random.seed(miscglobals.RANDOMSEED)
    numpy.random.seed(miscglobals.RANDOMSEED)

    import vocabulary
#    logging.info("Reading vocab")
#    vocabulary.read()
    
    import model
    try:
        print >> sys.stderr, ("Trying to read training state for %s %s..." % (newkeystr, rundir))
        (m, cnt, epoch, get_train_minibatch) = state.load(rundir, newkeystr)
        print >> sys.stderr, ("...success reading training state for %s %s" % (newkeystr, rundir))
        print >> sys.stderr, logfile
        logging.basicConfig(filename=logfile, level=logging.DEBUG)
#        logging.basicConfig(filename=logfile, filemode="w", level=logging.DEBUG)
        logging.info("CONTINUING FROM TRAINING STATE")
    except IOError:
        print >> sys.stderr, ("...FAILURE reading training state for %s %s" % (newkeystr, rundir))
        print >> sys.stderr, ("INITIALIZING")

        m = model.Model()
        cnt = 0
        epoch = 1
        get_train_minibatch = examples.TrainingMinibatchStream()
        logging.basicConfig(filename=logfile, filemode="w", level=logging.DEBUG)
        logging.info("INITIALIZING TRAINING STATE")

    logging.info(myyaml.dump(common.dump.vars_seq([hyperparameters, miscglobals])))

    #validate(0)
    diagnostics.diagnostics(cnt, m)
#    diagnostics.visualizedebug(cnt, m, rundir)
    while 1:
        logging.info("STARTING EPOCH #%d" % epoch)
        for ebatch in get_train_minibatch:
            cnt += len(ebatch)
        #    print [wordmap.str(id) for id in e]

            noise_sequences, weights = corrupt.corrupt_examples(m, ebatch)
            m.train(ebatch, noise_sequences, weights)

            #validate(cnt)
            if cnt % (int(1000./HYPERPARAMETERS["MINIBATCH SIZE"])*HYPERPARAMETERS["MINIBATCH SIZE"]) == 0:
                logging.info("Finished training step %d (epoch %d)" % (cnt, epoch))
#                print ("Finished training step %d (epoch %d)" % (cnt, epoch))
            if cnt % (int(100000./HYPERPARAMETERS["MINIBATCH SIZE"])*HYPERPARAMETERS["MINIBATCH SIZE"]) == 0:
                diagnostics.diagnostics(cnt, m)
                if os.path.exists(os.path.join(rundir, "BAD")):
                    logging.info("Detected file: %s\nSTOPPING" % os.path.join(rundir, "BAD"))
                    sys.stderr.write("Detected file: %s\nSTOPPING\n" % os.path.join(rundir, "BAD"))
                    sys.exit(0)
            if cnt % (int(HYPERPARAMETERS["VALIDATE_EVERY"]*1./HYPERPARAMETERS["MINIBATCH SIZE"])*HYPERPARAMETERS["MINIBATCH SIZE"]) == 0:
                state.save(m, cnt, epoch, get_train_minibatch, rundir, newkeystr)
                diagnostics.visualizedebug(cnt, m, rundir, newkeystr)
#                validate(cnt)
        get_train_minibatch = examples.TrainingMinibatchStream()
        epoch += 1

########NEW FILE########
__FILENAME__ = vocabulary
"""
Automatically load the wordmap, if available.
"""

import cPickle
from common.file import myopen
import sys

def _wordmap_filename(name):
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    return HYPERPARAMETERS["MONOLINGUAL_VOCABULARY_IDMAP_FILE"]

wordmap = None
try:
    wordmap = cPickle.load(myopen(_wordmap_filename()))
    wordmap.str = wordmap.key
except: pass

def write(wordmap, name=""):
    """
    Write the word ID map, passed as a parameter.
    """
    print >> sys.stderr, "Writing word map to %s..." % _wordmap_filename(name)
    cPickle.dump(wordmap, myopen(_wordmap_filename(name), "w"))

########NEW FILE########
__FILENAME__ = ngrams
#!/usr/bin/env python
"""
Dump n-gram counts over entire training data as YAML.
"""

import sys
from common.stats import stats

from collections import defaultdict
cnt = defaultdict(int)
if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    import vocabulary
    print >> sys.stderr, "Reading vocab"
    vocabulary.read()
    from vocabulary import wordmap

    import train
    for (i, e) in enumerate(train.get_train_example()):
        cnt[tuple([wordmap.str(t) for t in e])] += 1
        if i % 10000 == 0:
            print >> sys.stderr, "Read %d examples" % i
            print >> sys.stderr, stats()
        if i > 100000000:
            break
    cnt = [(t, cnt[t]) for t in cnt]
    import common.json
    common.json.dump(cnt, sys.stdout)

########NEW FILE########
__FILENAME__ = filter-sentences-by-lemma
#!/usr/bin/python
"""
For the N files given as command line arguments, filter the sentences
to be only those in which the first file contains a word that lemmatizes
to one of the W2W FOCUS LEMMAS.
We write files that are prefixed by "filtered-"
"""

from common.str import percent
import string
import sys

import common.hyperparameters, common.options
HYPERPARAMETERS = common.hyperparameters.read("language-model")
HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)

if HYPERPARAMETERS["W2W FOCUS LEMMAS"] is None or len (HYPERPARAMETERS["W2W FOCUS LEMMAS"]) == 0:
    print >> sys.stderr, "There are no focus lemmas, hence we have nothing to filter"
    sys.exit(0)

assert len(args) >= 1

from common.stats import stats
from lemmatizer import lemmatize

print >> sys.stderr, "Loaded Morphological analyizer"
print >> sys.stderr, stats()

from itertools import izip
import os.path, os

filenames = args
outfilenames = [os.path.join(os.path.dirname(f), "filtered-%s" % os.path.basename(f)) for f in filenames]

print >> sys.stderr, "Reading from %s" % `filenames`
print >> sys.stderr, "Writing to %s" % `outfilenames`

for f in filenames: assert os.path.exists(f)
for f in outfilenames:
    if os.path.exists(f):
        print >> sys.stderr, "Warning, going to overwrite %s" % f

#print "Sleeping for 10 seconds..."
#import time
#time.sleep(10)

inf = [open(f) for f in filenames]
outf = [open(f, "wt") for f in outfilenames]

tot = 0
cnt = 0
for lines in izip(*inf):
    tot += 1
    keep = False
    for w in string.split(lines[0]):
        if lemmatize("en", w) in HYPERPARAMETERS["W2W FOCUS LEMMAS"]:
            keep = True
            break
    if keep:
        cnt += 1
        for l, f in izip(lines, outf):
            f.write(l)
    if tot % 10000 == 0:
        print >> sys.stderr, "%s lines kept" % percent(cnt, tot)
        print >> sys.stderr, stats()

########NEW FILE########
__FILENAME__ = lemmatizer
../lemmatizer.py
########NEW FILE########
__FILENAME__ = random-validation-examples
#!/usr/bin/env python
#
#  Print out validation examples, disregarding vocabulary.
#
#  @TODO: Don't duplicate get_example code here and twice in train.py
#

from common.file import myopen
import string
import sys

def get_example(f):
    import common.hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    for l in myopen(f):
        prevwords = []
        for w in string.split(l):
            w = string.strip(w)
            prevwords.append(w)
            if len(prevwords) >= HYPERPARAMETERS["WINDOW_SIZE"]:
                yield prevwords[-HYPERPARAMETERS["WINDOW_SIZE"]:]

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    print >> sys.stderr, "Reading examples from %s" % HYPERPARAMETERS["ORIGINAL VALIDATION_SENTENCES"]
    ves = [e for e in get_example(HYPERPARAMETERS["ORIGINAL VALIDATION_SENTENCES"])]
    import random
    random.shuffle(ves)
    print >> sys.stderr, "Reading %d examples to %s" % (HYPERPARAMETERS["VALIDATION EXAMPLES"], HYPERPARAMETERS["VALIDATION_SENTENCES"])
    o = myopen(HYPERPARAMETERS["VALIDATION_SENTENCES"], "w")
    for e in ves[:HYPERPARAMETERS["VALIDATION EXAMPLES"]]:
        o.write(string.join(e) + "\n")

########NEW FILE########
__FILENAME__ = rundir
"""
Run directory
"""

import common.hyperparameters, common.options, common.dump

_rundir = None
def rundir():
    global _rundir
    if _rundir is None:
        HYPERPARAMETERS = common.hyperparameters.read("language-model")
        _rundir = common.dump.create_canonical_directory(HYPERPARAMETERS)
    return _rundir

########NEW FILE########
__FILENAME__ = build-example-cache
#!/usr/bin/env python
"""
Extract all training examples, and cache them.
"""

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    import logging
    logging.basicConfig(level=logging.INFO)

    import w2w.examples
    w2w.examples.all_training_examples_cached()

########NEW FILE########
__FILENAME__ = build-initial-embeddings
#!/usr/bin/env python
"""
Given embeddings in one language, initialize embeddings in all languages
using these monolingual embeddings.  We do this as a weighted average
of the translations of the target word in the embedding language.
(However, we only do the weighted average over words that have
embeddings. By comparison, we could do the weighted average and treat
words without embeddings as *UNKNOWN* in the embedding language, and
include these embeddings. But we don't.)
"""

def visualize(embeddings, idxs, name, PERPLEXITY=30):
    idxs = [w % embeddings.shape[0] for w in idxs]
    titles = [wordform(w) for w in idxs]
    import os.path
    filename = HYPERPARAMETERS["INITIAL_EMBEDDINGS"] + ".visualize-%s.png" % name
    try:
        from textSNE.calc_tsne import tsne
#       from textSNE.tsne import tsne
        out = tsne(embeddings[idxs], perplexity=PERPLEXITY)
        from textSNE.render import render
        render([(title, point[0], point[1]) for title, point in zip(titles, out)], filename)
    except IOError:
        logging.info("ERROR visualizing", filename, ". Continuing...")


if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    import sys
    from common.stats import stats
    from common.str import percent
    import common.file
    import numpy
    import string
    import copy
    import cPickle

    import logging
    logging.basicConfig(level=logging.DEBUG)

    from w2w.vocabulary import wordmap, language, wordform
    from w2w.targetvocabulary import targetmap

    # Read in the embeddings
    print >> sys.stderr, "Reading embeddings from %s..." % HYPERPARAMETERS["W2W INITIAL EMBEDDINGS"]
    print >> sys.stderr, stats()
    original_embeddings = {}
    tot = 0
    for l in common.file.myopen(HYPERPARAMETERS["W2W INITIAL EMBEDDINGS"]):
        vals = string.split(l)
        word = vals[0]
        if HYPERPARAMETERS["W2W LOWERCASE INITIAL EMBEDDINGS BEFORE INITIALIZATION"] and word != "*UNKNOWN*":
            if (word[0] == '*' and word[-1] == '*' and len(word) > 1):
                print >> sys.stderr, "WEIRD WORD: %s" % word
            word = string.lower(word)
        assert len(vals[1:]) == HYPERPARAMETERS["EMBEDDING_SIZE"]
        tot += 1
        if tot % 10000 == 0:
            print >> sys.stderr, "\tRead %d lines from %s" % (tot, HYPERPARAMETERS["W2W INITIAL EMBEDDINGS"])
        if word in original_embeddings:
#            print >> sys.stderr, "Skipping word %s (originally %s), we already have an embedding for it" % (word, vals[0])
            continue
        else:
            original_embeddings[word] = numpy.array([float(v) for v in vals[1:]])
    print >> sys.stderr, "...done reading embeddings from %s" % HYPERPARAMETERS["W2W INITIAL EMBEDDINGS"]
    print >> sys.stderr, "Skipped %s words for which we had duplicate embeddings" % percent(tot-len(original_embeddings), tot)
    print >> sys.stderr, stats()

    reversemap = targetmap(name="reverse")

    embeddings = numpy.zeros((wordmap().len, HYPERPARAMETERS["EMBEDDING_SIZE"]))
    assert embeddings.shape == (wordmap().len, HYPERPARAMETERS["EMBEDDING_SIZE"])

    ELANG = HYPERPARAMETERS["W2W INITIAL EMBEDDINGS LANGUAGE"]
    for w in range(wordmap().len):
        embedding = None
        # If this word is in a different language than the embeddings.
        if language(w) != HYPERPARAMETERS["W2W INITIAL EMBEDDINGS LANGUAGE"]:
            if w not in reversemap:
                print >> sys.stderr, "Word %s is not even in target map! Using *UNKNOWN*" % `wordmap().str(w)`
                embedding = original_embeddings["*UNKNOWN*"]
            elif ELANG not in reversemap[w]:
                print >> sys.stderr, "Have no %s translations for word %s, only have %s, using *UNKNOWN*" % (ELANG, wordmap().str(w), reversemap[w].keys())
                embedding = original_embeddings["*UNKNOWN*"]
            else:
                # Mix the target word embedding over the weighted translation into the source language

                mixcnt = {}
                for w2 in reversemap[w][ELANG]:
                    if language(w2) is None:
                        assert HYPERPARAMETERS["W2W SKIP TRANSLATIONS TO UNKNOWN WORD"]
                        continue
                    assert language(w2) == ELANG
                    if wordform(w2) not in original_embeddings:
                        print >> sys.stderr, "%s is NOT mixed by %s %d (no embedding)" % (wordmap().str(w), wordmap().str(w2), reversemap[w][ELANG][w2])
                        continue
                    mixcnt[w2] = reversemap[w][ELANG][w2]

                tot = 0
                for w2 in mixcnt: tot += mixcnt[w2]

                if tot == 0:
                    print >> sys.stderr, "Unable to mix ANY translations for %s, using *UNKNOWN*" % `wordmap().str(w)`
                    embedding = original_embeddings["*UNKNOWN*"]
                else:
                    embedding = numpy.zeros((HYPERPARAMETERS["EMBEDDING_SIZE"]))
                    for w2 in mixcnt:
                        embedding += 1. * mixcnt[w2] / tot * (original_embeddings[wordform(w2)])
#                       print >> sys.stderr, "%s is mixed %s by %s" % (wordmap().str(w), percent(mixcnt[w2], tot), wordmap().str(w2))
        else:
            if wordform(w) not in original_embeddings:
                print >> sys.stderr, "Word %s has no embedding, using *UNKNOWN*" % `wordmap().str(w)`
                embedding = original_embeddings["*UNKNOWN*"]
            else:
                embedding = original_embeddings[wordform(w)]
        embeddings[w] = copy.copy(embedding)

#        print wordform(w), language(w),
#        for v in embeddings[w]:
#            print v,
#        print

    print >> sys.stderr, "Dumping initial embeddings to %s" % HYPERPARAMETERS["INITIAL_EMBEDDINGS"]
    cPickle.dump(embeddings, common.file.myopen(HYPERPARAMETERS["INITIAL_EMBEDDINGS"], "w"))

    import random
    WORDCNT = 500
    idxs = range(wordmap().len)
    random.shuffle(idxs)
    idxs = idxs[:WORDCNT]

    visualize(embeddings, idxs, "randomized")
    visualize(embeddings, range(WORDCNT), "mostcommon")
    visualize(embeddings, range(-1, -WORDCNT*50, -50), "leastcommon")
    visualize(embeddings, range(wordmap().len/2-WORDCNT*20/2,wordmap().len/2+WORDCNT*20/2, 20), "midcommon")

########NEW FILE########
__FILENAME__ = build-target-vocabulary
#!/usr/bin/env python
"""
Read in the w2w corpora (bi + monolingual), and build the translation
vocabulary (for each source word, what target words it can translate to).
Note: Each corpus is weighted in proportion to its length. (i.e. all
words are equally weighted.)
"""

import sys

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    import logging
    logging.basicConfig(level=logging.DEBUG)

    import w2w.corpora
    from w2w.vocabulary import wordmap, language, wordform
    from collections import defaultdict
    from common.mydict import sort as dictsort

    cnt = {}
    reversecnt = {}
    for l1, l2, f1, f2, falign in w2w.corpora.bicorpora_filenames():
        for ws1, ws2, links in w2w.corpora.bicorpus_sentences_and_alignments(l1, l2, f1, f2, falign):
            for i1, i2 in links:
                if len(ws1) <= i1 or len(ws2) <= i2:
                    print >> sys.stderr, "This is going to break on link (%d, %d) because lens = (%d, %d)" % (i1,i2, len(ws1), len(ws2))
                    print >> sys.stderr, [wordform(w) for w in ws1]
                    print >> sys.stderr, [wordform(w) for w in ws2]
                    print >> sys.stderr, links
                w1 = ws1[i1]
                w2 = ws2[i2]
#                print wordmap.str(w1)[1], wordmap.str(w2)[1]

                l2new = language(w2)

                assert HYPERPARAMETERS["W2W SKIP TRANSLATIONS TO UNKNOWN WORD"]
                # Skip translations to unknown words
                if wordform(w2) == "*UNKNOWN*": continue

                assert l2new == l2


                # We don't filter here, otherwise we will get a reversemap that only maps to focus lemmas.
#                # If we are filtering examples by lemma
#                if not(HYPERPARAMETERS["W2W FOCUS LEMMAS"] is None or len (HYPERPARAMETERS["W2W FOCUS LEMMAS"]) == 0):
#                    assert language(w1) == "en"
#                    from lemmatizer import lemmatize
#                    if lemmatize(language(w1), wordform(w1)) not in HYPERPARAMETERS["W2W FOCUS LEMMAS"]:
##                        logging.debug("Focus word %s (lemma %s) not in our list of focus lemmas" % (`wordmap().str(w1)`, lemmatize(language(w1), wordform(w1))))
#                        continue

                if w1 not in cnt: cnt[w1] = {}
                if l2 not in cnt[w1]: cnt[w1][l2] = defaultdict(int)
                cnt[w1][l2][w2] += 1

                if w2 not in reversecnt: reversecnt[w2] = {}
                if l1 not in reversecnt[w2]: reversecnt[w2][l1] = defaultdict(int)
                reversecnt[w2][l1][w1] += 1

#    for w1 in cnt:
#        for l2 in cnt[w1]:
#            print wordmap().str(w1), l2, [(n, wordmap().str(w2)) for n, w2 in dictsort(cnt[w1][l2])]

#    words = {}
#    for (l, w) in wordfreq:
#        if l not in words: words[l] = []
#        if wordfreq[(l, w)] >= HYPERPARAMETERS["W2W MINIMUM WORD FREQUENCY"]:
#            words[l].append(w)

    import w2w.targetvocabulary
    w2w.targetvocabulary.write(cnt)
    w2w.targetvocabulary.write(reversecnt, name="reverse")

########NEW FILE########
__FILENAME__ = build-vocabulary
#!/usr/bin/env python
"""
Read in the w2w corpora (bi + monolingual), and build the vocabulary as
all words per language that occur at least HYPERPARAMETERS["W2W MINIMUM
WORD FREQUENCY"] times.
Each corpus is weighted in proportion to its length. (i.e. all words are equally weighted.)
"""

import sys
from common.stats import stats

def readwords(filename):
    print >> sys.stderr, "Processing %s" % filename
    i = 0
    for line in open(filename):
        i += 1
        if i % 100000 == 0:
            print >> sys.stderr, "Read line %d of %s..." % (i, filename)
            print >> sys.stderr, stats()
        for w in string.split(line):
            yield w

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    import logging
    logging.basicConfig(level=logging.DEBUG)

    import w2w.corpora
    import string

    from common.mydict import sort as dictsort

    from collections import defaultdict
    wordfreq = defaultdict(int)
    for l1, l2, f1, f2, falign in w2w.corpora.bicorpora_filenames():
        for w in readwords(f1): wordfreq[(l1,w)] += 1
        for w in readwords(f2): wordfreq[(l2,w)] += 1

    for l, f in w2w.corpora.monocorpora_filenames():
        assert 0

    for (l, w) in wordfreq.keys():
        if wordfreq[(l, w)] < HYPERPARAMETERS["W2W MINIMUM WORD FREQUENCY"]:
            del wordfreq[(l, w)]
        if w == "*UNKNOWN*":
            del wordfreq[(l, w)]

    import w2w.vocabulary
    import common.idmap

    wordfreqkeys = [key for cnt, key in dictsort(wordfreq)]

#    for k in wordfreq.keys():
#        print k
    v = common.idmap.IDmap([(None, "*LBOUNDARY*"), (None, "*RBOUNDARY*")] + wordfreqkeys, allow_unknown=HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"], unknown_key=(None, "*UNKNOWN*"))
    w2w.vocabulary.write(v)

########NEW FILE########
__FILENAME__ = corpora
"""
Methods for reading corpora.
"""

from os.path import join, isdir, exists
import sys
import os
import re
import itertools
import string
import logging

from common.stats import stats
from common.str import percent

def bicorpora_filenames():
    """
    For each bicorpora language pair in "W2W BICORPORA", traverse that
    language pair's subdirectory of DATA_DIR. Find all corpora files in
    that directory.
    Generator yields: tuples of type (l1, l2, f1, f2, falign), where l1 =
    source language, l2 = target language, f1 = source filename, f2 =
    target filename, falign = alignment file.
    """
    import common.hyperparameters, hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    
    for (l1, l2) in HYPERPARAMETERS["W2W BICORPORA"]:
        d = join(HYPERPARAMETERS["DATA_DIR"], "%s-%s" % (l1, l2))
        assert isdir(d)
        l1re = re.compile("%s$" % l1)
        alignre = re.compile("align.*-%s$" % l1)
        for f1 in os.listdir(d):
            f1 = join(d, f1)
            if not l1re.search(f1) or alignre.search(f1): continue
            f2 = l1re.sub(l2, f1)
            assert exists(f2)
            falign = l1re.sub("align.%s-%s" % (l1, l2), f1)
            assert exists(falign)
            yield l1, l2, f1, f2, falign

def monocorpora_filenames():
    import common.hyperparameters, hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    # Not yet implemented
    assert len(HYPERPARAMETERS["W2W MONOCORPORA"]) == 0
    return []

def bicorpus_sentences_and_alignments(l1, l2, f1, f2, falign):
    """
    Given languages l1 and l2 and their bicorpus filenames f1, f2, and falign,
    yield tuples of the former (ws1, ws2, links),
    where ws1 are the word ids in the sentence from f1,
    where ws2 are the word ids in the sentence from f2,
    and links is a list of (i1, i2) word indexes that are linked.
    """
    from w2w.vocabulary import wordmap

    i = 0
    emptycnt = 0
    logging.info("Reading %s,%s sentences and alignments from %s, %s, %s" % (l1, l2, f1, f2, falign))
    fil1, fil2, filalign = open(f1), open(f2), open(falign)
    for (s1, s2, salign) in itertools.izip(fil1, fil2, filalign):
   #     print s1, s2, salign,
        i += 1
        if i % 100000 == 0:
            logging.info("\tRead line %d of %s, %s, %s..." % (i, f1, f2, falign))
            logging.info("\tEmpty sentences are %s..." % (percent(emptycnt, i)))
            logging.info("\t%s" % stats())

        ws1 = [(l1, w1) for w1 in string.split(s1)]
        ws2 = [(l2, w2) for w2 in string.split(s2)]
        ws1 = [wordmap().id(tok) for tok in ws1]
        ws2 = [wordmap().id(tok) for tok in ws2]
   
        if len(ws1) == 0 or len(ws2) == 0:
            emptycnt += 1
            continue
   
   #     print ws2, [w2w.vocabulary.wordmap.str(w2) for w2 in ws2]
        links = [string.split(link, sep="-") for link in string.split(salign)]
        links = [(int(i1), int(i2)) for i1, i2 in links]

        yield ws1, ws2, links
   
    # Make sure all iterators are exhausted
    alldone = 0
    try: value = fil1.next()
    except StopIteration: alldone += 1
    try: value = fil2.next()
    except StopIteration: alldone += 1
    try: value = filalign.next()
    except StopIteration: alldone += 1
    assert alldone == 3
   
    logging.info("DONE. Read line %d of %s, %s, %s..." % (i, f1, f2, falign))
    logging.info("Empty sentences are %s..." % (percent(emptycnt, i)))
    logging.info(stats())

if __name__ == "__main__":
    for l1, l2, f1, f2, falign in bicorpora_filenames():
        print l1, l2, f1, f2, falign
    print monocorpora_filenames()

########NEW FILE########
__FILENAME__ = dump-example-cache
#!/usr/bin/env python
"""
Dump the w2w target vocabulary.
"""

import sys

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)

    import logging
    logging.basicConfig(level=logging.INFO)

    import w2w.examples
    for e in w2w.examples.get_all_training_examples_cached():
        print e

########NEW FILE########
__FILENAME__ = dump-target-vocabulary
#!/usr/bin/env python
"""
Dump the w2w target vocabulary.
"""

import sys

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    from common.mydict import sort as dictsort
    from common.str import percent

    from vocabulary import wordmap, wordform, language
    from targetvocabulary import targetmap

    for w1 in wordmap().all:
        w1 = wordmap().id(w1)
        # Actually, should assert W2W SKIP TRANSLATIONS FROM UNKNOWN WORD
        assert HYPERPARAMETERS["W2W SKIP TRANSLATIONS TO UNKNOWN WORD"]
        if language(w1) is None:
            print >> sys.stderr, "Skipping %s" % `wordmap().str(w1)`
            continue
        if w1 not in targetmap():
            print >> sys.stderr, "Skipping %s, not a source word in targetmap" % `wordmap().str(w1)`
            continue
        for l2 in targetmap()[w1]:
            totcnt = 0
            for cnt, w2 in dictsort(targetmap()[w1][l2]): totcnt += cnt
            print wordmap().str(w1), l2, [(percent(cnt, totcnt), wordform(w2)) for cnt, w2 in dictsort(targetmap()[w1][l2])]

    print >> sys.stderr, "REVERSE MAP NOW"

    for w1 in wordmap().all:
        w1 = wordmap().id(w1)
        # Actually, should assert W2W SKIP TRANSLATIONS FROM UNKNOWN WORD
        assert HYPERPARAMETERS["W2W SKIP TRANSLATIONS TO UNKNOWN WORD"]
        if language(w1) is None:
            print >> sys.stderr, "Skipping %s" % `wordmap().str(w1)`
            continue
        if w1 not in targetmap(name="reverse"):
            print >> sys.stderr, "Skipping %s, not a source word in targetmap" % `wordmap().str(w1)`
            continue
        for l2 in targetmap(name="reverse")[w1]:
            totcnt = 0
            for cnt, w2 in dictsort(targetmap(name="reverse")[w1][l2]): totcnt += cnt
            print wordmap().str(w1), l2, [(percent(cnt, totcnt), wordform(w2)) for cnt, w2 in dictsort(targetmap(name="reverse")[w1][l2])]

########NEW FILE########
__FILENAME__ = dump-vocabulary
#!/usr/bin/env python
"""
Dump the w2w vocaulary.
"""

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    from vocabulary import wordmap
    for w in wordmap().all:
        print w

########NEW FILE########
__FILENAME__ = examples
"""
Streaming examples.
"""

from w2w.corpora import bicorpora_filenames, monocorpora_filenames, bicorpus_sentences_and_alignments
from common.file import myopen
from common.stats import stats

from w2w.targetvocabulary import targetmap
from w2w.vocabulary import wordmap, language, wordform
import string
import logging

import random
from rundir import rundir
import os.path
import cPickle

import murmur

class MonolingualExample:
    def __init__(self, l1, l1seq, w1):
        """
        l1 = source language
        l1seq = sequence of word IDs in source language
        w1 = focus word ID in source language
        """
        self.l1 = l1
        self.l1seq = l1seq
        self.w1 = w1

        if wordform(self.w1) != "*UNKNOWN*":
            assert self.l1 == language(self.w1)

    def __str__(self):
        return "%s" % `(self.l1, wordform(self.w1), [wordmap().str(w)[1] for w in self.l1seq])`

class BilingualExample(MonolingualExample):
    def __init__(self, l1, l1seq, w1, w2):
        """
        l1 = source language
        l1seq = sequence of word IDs in source language
        w1 = focus word ID in source language
        w2 = focus word ID in target language
        """
        MonolingualExample.__init__(self, l1, l1seq, w1)
        self.w2 = w2

    @property
    def l2(self):
        return language(self.w2)

    @property
    def corrupt(self):
        """
        Return a (notw2, weight), a corrupt target word and its weight.
        Note: This will return a different random value every call.
        """
        from hyperparameters import HYPERPARAMETERS
        import random
        possible_targets = targetmap()[self.w1][self.l2]
        assert len(possible_targets) > 1
        assert self.w2 in possible_targets
        notw2 = self.w2
        cnt = 0
        while self.w2 == notw2:
            if HYPERPARAMETERS["NGRAM_FOR_TRAINING_NOISE"] == 0:
                notw2 = random.choice(possible_targets)
                pr = 1./len(possible_targets)
            elif HYPERPARAMETERS["NGRAM_FOR_TRAINING_NOISE"] == 1:
                assert 0
    #            import noise
    #            from common.myrandom import weighted_sample
    #            e[-1], pr = weighted_sample(noise.indexed_weights())
    ##            from vocabulary import wordmap
    ##            print wordmap.str(e[-1]), pr
            else:
                assert 0
            cnt += 1
            # Backoff to 0gram smoothing if we fail 10 times to get noise.
            if cnt > 10: notw2 = random.choice(possible_targets)

        if HYPERPARAMETERS["UNIFORM EXAMPLE WEIGHTS"]:
            weight = 1.
        else:
            weight = 1./pr
        return notw2, weight

    def __str__(self):
        return "%s" % `(wordmap().str(self.w2), self.l1, wordform(self.w1), [wordmap().str(w)[1] for w in self.l1seq])`

def get_training_biexample(l1, l2, f1, f2, falign):
    """
    Generator of bilingual training examples from this bicorpus.
    """
    import common.hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    WINDOW = HYPERPARAMETERS["WINDOW_SIZE"]

    for ws1, ws2, links in bicorpus_sentences_and_alignments(l1, l2, f1, f2, falign):
        for i1, i2 in links:
            w1 = ws1[i1]
            w2 = ws2[i2]

            l2new = language(w2)
            assert HYPERPARAMETERS["W2W SKIP TRANSLATIONS TO UNKNOWN WORD"]
            # Skip translations to unknown words
            if wordform(w2) == "*UNKNOWN*": continue
            assert l2new == l2

            # Skip translations from unknown words
            if wordform(w1) == "*UNKNOWN*": continue

            # If we are filtering examples by lemma
            if not(HYPERPARAMETERS["W2W FOCUS LEMMAS"] is None or len (HYPERPARAMETERS["W2W FOCUS LEMMAS"]) == 0):
#                print wordmap().str(w1), wordmap().str(w2)
                assert language(w1) == "en"
#                from lemmatizer import lemmatize
#                if lemmatize(language(w1), wordform(w1)) not in HYPERPARAMETERS["W2W FOCUS LEMMAS"]:
#                    logging.debug("Focus word %s (lemma %s) not in our list of focus lemmas" % (`wordmap().str(w1)`, lemmatize(language(w1), wordform(w1))))
                if wordform(w1) not in HYPERPARAMETERS["W2W FOCUS LEMMAS"]:
                    logging.debug("Focus word %s not in our list of focus lemmas" % (`wordmap().str(w1)`))
                    continue

            if w1 not in targetmap():
                logging.warning("No translations for word %s, skipping" % (`wordmap().str(w1)`))
                continue

            if l2new not in targetmap()[w1]:
                logging.warning("Word %s has no translations for language %s, skipping" % (`wordmap().str(w1)`, l2new))
                continue

            if w2 not in targetmap()[w1][l2new]:
                logging.error("Word %s cannot translate to word %s, skipping" % (`wordmap().str(w1)`, `wordmap().str(w2)`))
                continue

            if len(targetmap()[w1][l2new]) == 1:
                logging.debug("Word %s has only one translation in language %s, skipping" % (`wordmap().str(w1)`, l2new))
                continue

            # Extract the window of tokens around index i1. Pad with *LBOUNDARY* and *RBOUNDARY* as necessary.
            min = i1 - (WINDOW-1)/2
            max = i1 + (WINDOW-1)/2
            lpad = 0
            rpad = 0
            if min < 0:
                lpad = -min
                min = 0
            if max >= len(ws1):
                rpad = max - (len(ws1)-1)
                max = len(ws1)-1
            assert lpad + (max - min + 1) + rpad == WINDOW

#            print i1 - (WINDOW-1)/2, i1 + (WINDOW-1)/2
#            print "min=%d, max=%d, lpad=%d, rpad=%d" % (min, max, lpad, rpad)
            seq = [wordmap().id((None, "*LBOUNDARY*"))]*lpad + ws1[min:max+1] + [wordmap().id((None, "*RBOUNDARY*"))]*rpad
#            print [wordmap.str(w) for w in seq]
            assert len(seq) == WINDOW
#            print ws1[i1 - (WINDOW-1)/2:i1 + (WINDOW-1)/2]

            assert seq[(WINDOW-1)/2] == w1
            yield BilingualExample(l1, seq, w1, w2)

def is_validation_example(e):
    import common.hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    examples_per_validation = int(1/HYPERPARAMETERS["PERCENT_OF_TRAINING_EXAMPLES_FOR_VALIDATION"])
    return murmur.string_hash(`e`) % examples_per_validation == 0

def get_training_minibatch_online():
    """
    Warning: The approach has the weird property that if one language
    pair's corpus is way longer than others, it will be the only examples
    for a while after the other corpora are exhausted.
    """

    assert 0 # We need to filter validation examples

    import common.hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    MINIBATCH_SIZE = HYPERPARAMETERS["MINIBATCH SIZE"]

    generators = []
    for l1, l2, f1, f2, falign in bicorpora_filenames():
#        print l1, l2, f1, f2, falign
        generators.append(get_training_biexample(l1, l2, f1, f2, falign))
    for l, f in monocorpora_filenames(): assert 0

    # Cycles over generators.
    idx = 0
    last_minibatch = None
    while 1:
        minibatch = []
        for e in generators[idx]:
            minibatch.append(e)
            if len(minibatch) >= MINIBATCH_SIZE:
                break
        if len(minibatch) > 0:
            last_minibatch = idx
            yield minibatch
        elif last_minibatch == idx:
            # We haven't had any minibatch in the last cycle over the generators.
            # So we are done will all corpora.
            break

        # Go to the next corpus
        idx = (idx + 1) % len(generators)

def training_examples_cache_filename():
    import common.hyperparameters, hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    return os.path.join(HYPERPARAMETERS["DATA_DIR"], "examples-cache.minfreq=%d.include_unknown=%s.window-%d.pkl.gz" % (HYPERPARAMETERS["W2W MINIMUM WORD FREQUENCY"], HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"], HYPERPARAMETERS["WINDOW_SIZE"]))

_all_examples = None
def all_training_examples_cached():
    global _all_examples
    if _all_examples is None:
        try:
            _all_examples, cnt = cPickle.load(myopen(training_examples_cache_filename()))
            assert len(_all_examples) == cnt
            logging.info("Successfully read %d training examples from %s" % (cnt, training_examples_cache_filename()))
            logging.info(stats())
        except:
            logging.info("(Couldn't read training examples from %s, sorry)" % (training_examples_cache_filename()))
            logging.info("Caching all training examples...")
            logging.info(stats())
            _all_examples = []
            for l1, l2, f1, f2, falign in bicorpora_filenames():
                for e in get_training_biexample(l1, l2, f1, f2, falign):
                    _all_examples.append(e)
                    if len(_all_examples) % 10000 == 0:
                        logging.info("\tcurrently have read %d training examples" % len(_all_examples))
                        logging.info(stats())
            random.shuffle(_all_examples)
            logging.info("...done caching all %d training examples" % len(_all_examples))
            logging.info(stats())

            cnt = len(_all_examples)
            cPickle.dump((_all_examples, cnt), myopen(training_examples_cache_filename(), "wb"), protocol=-1)
            assert len(_all_examples) == cnt
            logging.info("Wrote %d training examples to %s" % (cnt, training_examples_cache_filename()))
            logging.info(stats())
    assert _all_examples is not None
    return _all_examples

def get_all_training_examples_cached():
    for e in all_training_examples_cached():
        if is_validation_example(e): continue
        yield e

def get_all_validation_examples_cached():
    for e in all_training_examples_cached():
        if not is_validation_example(e): continue
        yield e
    
def get_training_minibatch_cached():
    import common.hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    MINIBATCH_SIZE = HYPERPARAMETERS["MINIBATCH SIZE"]

    minibatch = []
    for e in get_all_training_examples_cached():
        minibatch.append(e)
        if len(minibatch) >= MINIBATCH_SIZE:
            yield minibatch
            minibatch = []
    if len(minibatch) > 0:
        yield minibatch
        minibatch = []

if __name__ == "__main__":
    for minibatch in get_training_minibatch_cached():
#        print len(minibatch)
        for e in minibatch:
            print e

########NEW FILE########
__FILENAME__ = state
"""
Save and load training state.
@todo: Training state variables (cnt, epoch) should all be combined into one object.
"""

import logging
import os.path
import cPickle

from common.stats import stats
from common.file import myopen
import common.json
import sys

_lastfilename = None
def save(translation_model, cnt, lastcnt, epoch, rundir, newkeystr):
    global _lastfilename

    filename = os.path.join(rundir, "translation_model-%d%s.pkl" % (cnt, newkeystr))
    logging.info("Writing translation_model to %s..." % filename)
    logging.info(stats())
    cPickle.dump(translation_model, myopen(filename, "wb"), protocol=-1)
    logging.info("...done writing translation_model to %s" % filename)
    logging.info(stats())

#    if _lastfilename is not None:
#        logging.info("Removing old translation_model %s..." % _lastfilename)
#        try:
#            os.remove(_lastfilename)
#            logging.info("...removed %s" % _lastfilename)
#        except:
#            logging.info("Could NOT remove %s" % _lastfilename)
    _lastfilename = filename

    common.json.dumpfile((cnt, lastcnt, epoch, filename), os.path.join(rundir, "trainstate.json"))

    filename = os.path.join(rundir, "newkeystr.txt")
    myopen(filename, "wt").write(newkeystr)

def load(rundir, newkeystr):
    """
    Read the directory and load the translation_model, the training count, the training epoch, and the training state.
    """
    global _lastfilename

    filename = os.path.join(rundir, "newkeystr.txt")
    assert newkeystr == myopen(filename).read()

    (cnt, lastcnt, epoch, filename) = common.json.loadfile(os.path.join(rundir, "trainstate.json"))

#    filename = os.path.join(rundir, "translation_model-%d%s.pkl" % (cnt, newkeystr))
    print >> sys.stderr, ("Reading translation_model from %s..." % filename)
    print >> sys.stderr, (stats())
    translation_model = cPickle.load(myopen(filename))
    print >> sys.stderr, ("...done reading translation_model from %s" % filename)
    print >> sys.stderr, (stats())
    _lastfilename = filename

    return (translation_model, cnt, lastcnt, epoch)

########NEW FILE########
__FILENAME__ = targetvocabulary
"""
targetmap[w1][l2][w2] = c means that source word ID w1 mapped to target
language l2 and target word ID w2 with count c.
"""

import cPickle
from common.file import myopen
from common.stats import stats
import sys
from os.path import join

def _targetmap_filename(name=""):
    import common.hyperparameters, common.options, hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    return join(HYPERPARAMETERS["DATA_DIR"], "%stargetmap.minfreq=%d.include_unknown=%s.pkl.gz" % (name, HYPERPARAMETERS["W2W MINIMUM WORD FREQUENCY"], HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"]))

_targetmap = {}
def targetmap(name=""):
    global _targetmap
    if name not in _targetmap:
        f = _targetmap_filename(name=name)
        print >> sys.stderr, "Reading target map from %s..." % f
        print >> sys.stderr, stats()
        _targetmap[name] = cPickle.load(myopen(f))
        print >> sys.stderr, "...done reading target map from %s" % f
        print >> sys.stderr, stats()
    return _targetmap[name]

def write(_targetmap_new, name=""):
    """
    Write the word ID map, passed as a parameter.
    """
    global _targetmap
    assert name not in _targetmap
    _targetmap[name] = _targetmap_new
    f = _targetmap_filename(name=name)
    print >> sys.stderr, "Writing target map to %s..." % f
    cPickle.dump(_targetmap[name], myopen(f, "w"))

########NEW FILE########
__FILENAME__ = train
#!/usr/bin/env python

import sys
import string
import common.dump
from common.file import myopen
from common.stats import stats
from common.str import percent

import miscglobals
import logging

import w2w.examples
import diagnostics
import state

import cPickle

def validate(translation_model, cnt):
    import math
#    logranks = []
#    logging.info("BEGINNING VALIDATION AT TRAINING STEP %d" % cnt)
#    logging.info(stats())
    i = 0
    tot = 0
    correct = 0
    for (i, ve) in enumerate(w2w.examples.get_all_validation_examples_cached()):
        correct_sequences, noise_sequences, weights = ebatch_to_sequences([ve])
        source_language = ve.l1
        is_correct = translation_model[source_language].validate_errors(correct_sequences, noise_sequences)
#        print r
        for w in weights: assert w == 1.0

        tot += 1
        if is_correct: correct += 1

        if i % 1000 == 0: logging.info("\tvalidating %d examples done..." % i)
#    logging.info("Validation of model %s at cnt %d: validation err %s" % (translation_model[source_language].modelname, cnt, percent(correct, tot)))
    logging.info("VALIDATION of model at cnt %d: validation accuracy %s" % (cnt, percent(correct, tot)))
##        logging.info([wordmap.str(id) for id in ve])
#        logranks.append(math.log(m.validate(ve)))
#        if (i+1) % 10 == 0:
#            logging.info("Training step %d, validating example %d, mean(logrank) = %.2f, stddev(logrank) = %.2f" % (cnt, i+1, numpy.mean(numpy.array(logranks)), numpy.std(numpy.array(logranks))))
#            logging.info(stats())
#    logging.info("FINAL VALIDATION AT TRAINING STEP %d: mean(logrank) = %.2f, stddev(logrank) = %.2f, cnt = %d" % (cnt, numpy.mean(numpy.array(logranks)), numpy.std(numpy.array(logranks)), i+1))
#    logging.info(stats())
##    print "FINAL VALIDATION AT TRAINING STEP %d: mean(logrank) = %.2f, stddev(logrank) = %.2f, cnt = %d" % (cnt, numpy.mean(numpy.array(logranks)), numpy.std(numpy.array(logranks)), i+1)
##    print stats()

def ebatch_to_sequences(ebatch):
    """
    Convert example batch to sequences.
    """
    correct_sequences = []
    noise_sequences = []
    weights = []
    for e in ebatch:
        notw2, weight = e.corrupt
        correct_sequences.append(e.l1seq + [e.w2])
        noise_sequences.append(e.l1seq + [notw2])
        weights.append(weight)
    assert len(ebatch) == len(correct_sequences)
    assert len(ebatch) == len(noise_sequences)
    assert len(ebatch) == len(weights)
    return correct_sequences, noise_sequences, weights

if __name__ == "__main__":
    import common.hyperparameters, common.options
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    HYPERPARAMETERS, options, args, newkeystr = common.options.reparse(HYPERPARAMETERS)
    import hyperparameters

    from common import myyaml
    import sys
    print >> sys.stderr, myyaml.dump(common.dump.vars_seq([hyperparameters, miscglobals]))

    # We do not allow sophisticated training noise
    assert HYPERPARAMETERS["NGRAM_FOR_TRAINING_NOISE"] == 0

    from rundir import rundir
    rundir = rundir()

    import os.path, os
    logfile = os.path.join(rundir, "log")
    if newkeystr != "":
        verboselogfile = os.path.join(rundir, "log%s" % newkeystr)
        print >> sys.stderr, "Logging to %s, and creating link %s" % (logfile, verboselogfile)
        os.system("ln -s log %s " % (verboselogfile))
    else:
        print >> sys.stderr, "Logging to %s, not creating any link because of default settings" % logfile

    import random, numpy
    random.seed(miscglobals.RANDOMSEED)
    numpy.random.seed(miscglobals.RANDOMSEED)

    # Random wait if we are a batch job
    import time
    if not HYPERPARAMETERS["console"]:
        wait = 100 * random.random()
        print >> sys.stderr, "Waiting %f seconds..." % wait
        time.sleep(wait)

#    import vocabulary
##    logging.info("Reading vocab")
##    vocabulary.read()
#    
    import model
    try:
        print >> sys.stderr, ("Trying to read training state for %s %s..." % (newkeystr, rundir))
        (translation_model, cnt, lastcnt, epoch) = state.load(rundir, newkeystr)
        print >> sys.stderr, ("...success reading training state for %s %s" % (newkeystr, rundir))
        print >> sys.stderr, logfile
        print >> sys.stderr, "CONTINUING FROM TRAINING STATE"
    except IOError:
        print >> sys.stderr, ("...FAILURE reading training state for %s %s" % (newkeystr, rundir))
        print >> sys.stderr, ("INITIALIZING")

        translation_model = {}
        print >> sys.stderr, "Loading initial embeddings from %s" % HYPERPARAMETERS["INITIAL_EMBEDDINGS"]
        # TODO: If we want more than one model, we should SHARE the embeddings parameters
        embeddings = cPickle.load(common.file.myopen(HYPERPARAMETERS["INITIAL_EMBEDDINGS"]))

        print >> sys.stderr, "INITIALIZING TRAINING STATE"

        all_l1 = {}
        for l1, l2 in HYPERPARAMETERS["W2W BICORPORA"]: all_l1[l1] = True
        for l1 in all_l1:
            translation_model[l1] = model.Model(modelname="translate-from-%s" % l1, window_size=HYPERPARAMETERS["WINDOW_SIZE"]+1, initial_embeddings=embeddings)
        # TODO: I'd like to free this memory, but translation_model doesn't make a copy.
#        embeddings = None
        cnt = 0
        lastcnt = 0
        epoch = 1
#        get_train_minibatch = examples.TrainingMinibatchStream()

    if HYPERPARAMETERS["console"]:
        print >> sys.stderr, "Console mode (not batch mode)."
        logging.basicConfig(level=logging.INFO)
    else:
        print >> sys.stderr, "YOU ARE RUNNING IN BATCH, NOT CONSOLE MODE. THIS WILL BE THE LAST MESSAGE TO STDERR."
        logging.basicConfig(filename=logfile, filemode="w", level=logging.INFO)

    assert len(translation_model) == 1
    for l1 in HYPERPARAMETERS["W2W MONOCORPORA"]:
        assert 0

#    get_train_minibatch = w2w.examples.get_training_minibatch_online()
    get_train_minibatch = w2w.examples.get_training_minibatch_cached()

    logging.info(myyaml.dump(common.dump.vars_seq([hyperparameters, miscglobals])))

    validate(translation_model, 0)
#    diagnostics.diagnostics(cnt, m)
##    diagnostics.visualizedebug(cnt, m, rundir)
#    state.save(translation_model, cnt, lastcnt, epoch, rundir, newkeystr)
    while 1:
        logging.info("STARTING EPOCH #%d" % epoch)
        for ebatch in get_train_minibatch:
            lastcnt = cnt
            cnt += len(ebatch)
#        #    print [wordmap.str(id) for id in e]

            source_language = ebatch[0].l1
            for e in ebatch:
                # Make sure all examples have the same source language
                assert e.l1 == source_language

            # The following is code for training on bilingual examples.
            # TODO: Monolingual examples?

            correct_sequences, noise_sequences, weights = ebatch_to_sequences(ebatch)
            translation_model[source_language].train(correct_sequences, noise_sequences, weights)

            #validate(translation_model, cnt)
            if int(cnt/1000) > int(lastcnt/1000):
                logging.info("Finished training step %d (epoch %d)" % (cnt, epoch))
#                print ("Finished training step %d (epoch %d)" % (cnt, epoch))
            if int(cnt/10000) > int(lastcnt/10000):
                for l1 in translation_model:
                    diagnostics.diagnostics(cnt, translation_model[l1])
                if os.path.exists(os.path.join(rundir, "BAD")):
                    logging.info("Detected file: %s\nSTOPPING" % os.path.join(rundir, "BAD"))
                    sys.stderr.write("Detected file: %s\nSTOPPING\n" % os.path.join(rundir, "BAD"))
                    sys.exit(0)
            if int(cnt/HYPERPARAMETERS["VALIDATE_EVERY"]) > int(lastcnt/HYPERPARAMETERS["VALIDATE_EVERY"]):
                validate(translation_model, cnt)
                pass
#                for l1 in translation_model:
#                    diagnostics.visualizedebug(cnt, translation_model[l1], rundir, newkeystr)

        validate(translation_model, cnt)
#        get_train_minibatch = w2w.examples.get_training_minibatch_online()
        get_train_minibatch = w2w.examples.get_training_minibatch_cached()
        epoch += 1

        state.save(translation_model, cnt, lastcnt, epoch, rundir, newkeystr)
#       validate(cnt)

########NEW FILE########
__FILENAME__ = vocabulary
"""
wordmap is a map from id to (language, wordform)
"""

import cPickle
from common.file import myopen
import sys
from os.path import join

def _wordmap_filename():
    import common.hyperparameters, common.options, hyperparameters
    HYPERPARAMETERS = common.hyperparameters.read("language-model")
    return join(HYPERPARAMETERS["DATA_DIR"], "idmap.minfreq=%d.include_unknown=%s.pkl.gz" % (HYPERPARAMETERS["W2W MINIMUM WORD FREQUENCY"], HYPERPARAMETERS["INCLUDE_UNKNOWN_WORD"]))

_wordmap = None
def wordmap():
    global _wordmap
    if _wordmap is None:
        _wordmap = cPickle.load(myopen(_wordmap_filename()))
        _wordmap.str = _wordmap.key
    return _wordmap

def language(id):
    """
    Get the language of this word id.
    """
    return wordmap().str(id)[0]

def wordform(id):
    """
    Get the word form of this word id.
    """
    return wordmap().str(id)[1]

def write(_wordmap_new):
    """
    Write the word ID map, passed as a parameter.
    """
    global _wordmap
    assert _wordmap is None
    _wordmap = _wordmap_new
    print >> sys.stderr, "Writing word map with %d words to %s..." % (_wordmap.len, _wordmap_filename())
    cPickle.dump(_wordmap, myopen(_wordmap_filename(), "w"))

########NEW FILE########
__FILENAME__ = weight-histogram
#!/usr/bin/env python
#
#  Plot a histogram of the absolute values of model embeddings
#
#

PERCENT = 0.01
import random

import sys
import matplotlib
matplotlib.use( 'Agg' ) # Use non-GUI backend
import pylab

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-m", "--modelfile", dest="modelfile")
(options, args) = parser.parse_args()
assert options.modelfile is not None

histfile = "%s.weight-histogram.png" % options.modelfile

import cPickle
m = cPickle.load(open(options.modelfile))
#print m.parameters.embeddings.shape

values = []

from vocabulary import wordmap
for i in range(m.parameters.vocab_size):
    for v in m.parameters.embeddings[i]:
        if random.random() < PERCENT:
            values.append(abs(v))
values.sort()

print >> sys.stderr, "%d values read (at %f percent) of %d embeddings, %d/%f/%d = %f" % (len(values), PERCENT, m.parameters.vocab_size, len(values), PERCENT, m.parameters.vocab_size, len(values)/PERCENT/m.parameters.vocab_size)

x = []
for i, v in enumerate(values):
    x.append(1./(len(values)-1) * i)

print >> sys.stderr, 'Writing weight histogram to %s' % histfile

pylab.ylim(ymin=0, ymax=1.)
pylab.plot(x, values)
pylab.ylim(ymin=0, ymax=1.)
pylab.savefig(histfile)
pylab.show()

########NEW FILE########
