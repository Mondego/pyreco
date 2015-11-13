__FILENAME__ = analyze_webstats
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os
import scipy as sp
import matplotlib.pyplot as plt

from utils import DATA_DIR, CHART_DIR

data = sp.genfromtxt(os.path.join(DATA_DIR, "web_traffic.tsv"), delimiter="\t")
print(data[:10])

# all examples will have three classes in this file
colors = ['g', 'k', 'b', 'm', 'r']
linestyles = ['-', '-.', '--', ':', '-']

x = data[:, 0]
y = data[:, 1]
print("Number of invalid entries:", sp.sum(sp.isnan(y)))
x = x[~sp.isnan(y)]
y = y[~sp.isnan(y)]

# plot input data


def plot_models(x, y, models, fname, mx=None, ymax=None, xmin=None):
    plt.clf()
    plt.scatter(x, y, s=10)
    plt.title("Web traffic over the last month")
    plt.xlabel("Time")
    plt.ylabel("Hits/hour")
    plt.xticks(
        [w * 7 * 24 for w in range(10)], ['week %i' % w for w in range(10)])

    if models:
        if mx is None:
            mx = sp.linspace(0, x[-1], 1000)
        for model, style, color in zip(models, linestyles, colors):
            # print "Model:",model
            # print "Coeffs:",model.coeffs
            plt.plot(mx, model(mx), linestyle=style, linewidth=2, c=color)

        plt.legend(["d=%i" % m.order for m in models], loc="upper left")

    plt.autoscale(tight=True)
    plt.ylim(ymin=0)
    if ymax:
        plt.ylim(ymax=ymax)
    if xmin:
        plt.xlim(xmin=xmin)
    plt.grid(True, linestyle='-', color='0.75')
    plt.savefig(fname)

# first look at the data
plot_models(x, y, None, os.path.join(CHART_DIR, "1400_01_01.png"))

# create and plot models
fp1, res, rank, sv, rcond = sp.polyfit(x, y, 1, full=True)
print("Model parameters: %s" % fp1)
print("Error of the model:", res)
f1 = sp.poly1d(fp1)
f2 = sp.poly1d(sp.polyfit(x, y, 2))
f3 = sp.poly1d(sp.polyfit(x, y, 3))
f10 = sp.poly1d(sp.polyfit(x, y, 10))
f100 = sp.poly1d(sp.polyfit(x, y, 100))

plot_models(x, y, [f1], os.path.join(CHART_DIR, "1400_01_02.png"))
plot_models(x, y, [f1, f2], os.path.join(CHART_DIR, "1400_01_03.png"))
plot_models(
    x, y, [f1, f2, f3, f10, f100], os.path.join(CHART_DIR, "1400_01_04.png"))

# fit and plot a model using the knowledge about inflection point
inflection = 3.5 * 7 * 24
xa = x[:inflection]
ya = y[:inflection]
xb = x[inflection:]
yb = y[inflection:]

fa = sp.poly1d(sp.polyfit(xa, ya, 1))
fb = sp.poly1d(sp.polyfit(xb, yb, 1))

plot_models(x, y, [fa, fb], os.path.join(CHART_DIR, "1400_01_05.png"))


def error(f, x, y):
    return sp.sum((f(x) - y) ** 2)

print("Errors for the complete data set:")
for f in [f1, f2, f3, f10, f100]:
    print("Error d=%i: %f" % (f.order, error(f, x, y)))

print("Errors for only the time after inflection point")
for f in [f1, f2, f3, f10, f100]:
    print("Error d=%i: %f" % (f.order, error(f, xb, yb)))

print("Error inflection=%f" % (error(fa, xa, ya) + error(fb, xb, yb)))


# extrapolating into the future
plot_models(
    x, y, [f1, f2, f3, f10, f100], os.path.join(CHART_DIR, "1400_01_06.png"),
    mx=sp.linspace(0 * 7 * 24, 6 * 7 * 24, 100),
    ymax=10000, xmin=0 * 7 * 24)

print("Trained only on data after inflection point")
fb1 = fb
fb2 = sp.poly1d(sp.polyfit(xb, yb, 2))
fb3 = sp.poly1d(sp.polyfit(xb, yb, 3))
fb10 = sp.poly1d(sp.polyfit(xb, yb, 10))
fb100 = sp.poly1d(sp.polyfit(xb, yb, 100))

print("Errors for only the time after inflection point")
for f in [fb1, fb2, fb3, fb10, fb100]:
    print("Error d=%i: %f" % (f.order, error(f, xb, yb)))

plot_models(
    x, y, [fb1, fb2, fb3, fb10, fb100], os.path.join(CHART_DIR, "1400_01_07.png"),
    mx=sp.linspace(0 * 7 * 24, 6 * 7 * 24, 100),
    ymax=10000, xmin=0 * 7 * 24)

# separating training from testing data
frac = 0.3
split_idx = int(frac * len(xb))
shuffled = sp.random.permutation(list(range(len(xb))))
test = sorted(shuffled[:split_idx])
train = sorted(shuffled[split_idx:])
fbt1 = sp.poly1d(sp.polyfit(xb[train], yb[train], 1))
fbt2 = sp.poly1d(sp.polyfit(xb[train], yb[train], 2))
fbt3 = sp.poly1d(sp.polyfit(xb[train], yb[train], 3))
fbt10 = sp.poly1d(sp.polyfit(xb[train], yb[train], 10))
fbt100 = sp.poly1d(sp.polyfit(xb[train], yb[train], 100))

print("Test errors for only the time after inflection point")
for f in [fbt1, fbt2, fbt3, fbt10, fbt100]:
    print("Error d=%i: %f" % (f.order, error(f, xb[test], yb[test])))

plot_models(
    x, y, [fbt1, fbt2, fbt3, fbt10, fbt100], os.path.join(CHART_DIR,
                                                          "1400_01_08.png"),
    mx=sp.linspace(0 * 7 * 24, 6 * 7 * 24, 100),
    ymax=10000, xmin=0 * 7 * 24)

from scipy.optimize import fsolve
print(fbt2)
print(fbt2 - 100000)
reached_max = fsolve(fbt2 - 100000, 800) / (7 * 24)
print("100,000 hits/hour expected at week %f" % reached_max[0])

########NEW FILE########
__FILENAME__ = gen_webstats
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

# This script generates web traffic data for our hypothetical
# web startup "MLASS" in chapter 01

import os
import scipy as sp
from scipy.stats import gamma
import matplotlib.pyplot as plt

from utils import DATA_DIR, CHART_DIR

sp.random.seed(3)  # to reproduce the data later on

x = sp.arange(1, 31 * 24)
y = sp.array(200 * (sp.sin(2 * sp.pi * x / (7 * 24))), dtype=int)
y += gamma.rvs(15, loc=0, scale=100, size=len(x))
y += 2 * sp.exp(x / 100.0)
y = sp.ma.array(y, mask=[y < 0])
print(sum(y), sum(y < 0))

plt.scatter(x, y)
plt.title("Web traffic over the last month")
plt.xlabel("Time")
plt.ylabel("Hits/hour")
plt.xticks([w * 7 * 24 for w in [0, 1, 2, 3, 4]], ['week %i' % (w + 1) for w in [
           0, 1, 2, 3, 4]])

plt.autoscale(tight=True)
plt.grid()
plt.savefig(os.path.join(CHART_DIR, "1400_01_01.png"))

# sp.savetxt(os.path.join("..", "web_traffic.tsv"),
# zip(x[~y.mask],y[~y.mask]), delimiter="\t", fmt="%i")

sp.savetxt(os.path.join(
    DATA_DIR, "web_traffic.tsv"), list(zip(x, y)), delimiter="\t", fmt="%s")

########NEW FILE########
__FILENAME__ = performance_test
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License


import timeit

normal_py_sec = timeit.timeit('sum(x*x for x in xrange(1000))',
                              number=10000)
naive_np_sec = timeit.timeit('sum(na*na)',
                             setup="import numpy as np; na=np.arange(1000)",
                             number=10000)
good_np_sec = timeit.timeit('na.dot(na)',
                            setup="import numpy as np; na=np.arange(1000)",
                            number=10000)

print("Normal Python: %f sec" % normal_py_sec)
print("Naive NumPy: %f sec" % naive_np_sec)
print("Good NumPy: %f sec" % good_np_sec)

########NEW FILE########
__FILENAME__ = utils
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "data")

CHART_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "charts")

for d in [DATA_DIR, CHART_DIR]:
    if not os.path.exists(d):
        os.mkdir(d)


########NEW FILE########
__FILENAME__ = create_tsv
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import milksets.iris
import milksets.seeds


def save_as_tsv(fname, module):
    features, labels = module.load()
    nlabels = [module.label_names[ell] for ell in labels]
    with open(fname, 'w') as ofile:
        for f, n in zip(features, nlabels):
            print >>ofile, "\t".join(map(str, f) + [n])

save_as_tsv('iris.tsv', milksets.iris)
save_as_tsv('seeds.tsv', milksets.seeds)

########NEW FILE########
__FILENAME__ = figure1
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from sklearn.datasets import load_iris
from matplotlib import pyplot as plt

data = load_iris()
features = data['data']
feature_names = data['feature_names']
target = data['target']


pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
for i, (p0, p1) in enumerate(pairs):
    plt.subplot(2, 3, i + 1)
    for t, marker, c in zip(range(3), ">ox", "rgb"):
        plt.scatter(features[target == t, p0], features[
                    target == t, p1], marker=marker, c=c)
    plt.xlabel(feature_names[p0])
    plt.ylabel(feature_names[p1])
    plt.xticks([])
    plt.yticks([])
plt.savefig('figure1.png')

########NEW FILE########
__FILENAME__ = figure2
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

COLOUR_FIGURE = False

from matplotlib import pyplot as plt
from sklearn.datasets import load_iris
data = load_iris()
features = data['data']
feature_names = data['feature_names']
species = data['target_names'][data['target']]

setosa = (species == 'setosa')
features = features[~setosa]
species = species[~setosa]
virginica = species == 'virginica'

t = 1.75
p0, p1 = 3, 2

if COLOUR_FIGURE:
    area1c = (1., .8, .8)
    area2c = (.8, .8, 1.)
else:
    area1c = (1., 1, 1)
    area2c = (.7, .7, .7)

x0, x1 = [features[:, p0].min() * .9, features[:, p0].max() * 1.1]
y0, y1 = [features[:, p1].min() * .9, features[:, p1].max() * 1.1]

plt.fill_between([t, x1], [y0, y0], [y1, y1], color=area2c)
plt.fill_between([x0, t], [y0, y0], [y1, y1], color=area1c)
plt.plot([t, t], [y0, y1], 'k--', lw=2)
plt.plot([t - .1, t - .1], [y0, y1], 'k:', lw=2)
plt.scatter(features[virginica, p0],
            features[virginica, p1], c='b', marker='o')
plt.scatter(features[~virginica, p0],
            features[~virginica, p1], c='r', marker='x')
plt.ylim(y0, y1)
plt.xlim(x0, x1)
plt.xlabel(feature_names[p0])
plt.ylabel(feature_names[p1])
plt.savefig('figure2.png')

########NEW FILE########
__FILENAME__ = figure4_5
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

COLOUR_FIGURE = False

from matplotlib import pyplot as plt
from matplotlib.colors import ListedColormap
from load import load_dataset
import numpy as np
from knn import learn_model, apply_model, accuracy

feature_names = [
    'area',
    'perimeter',
    'compactness',
    'length of kernel',
    'width of kernel',
    'asymmetry coefficien',
    'length of kernel groove',
]


def train_plot(features, labels):
    y0, y1 = features[:, 2].min() * .9, features[:, 2].max() * 1.1
    x0, x1 = features[:, 0].min() * .9, features[:, 0].max() * 1.1
    X = np.linspace(x0, x1, 100)
    Y = np.linspace(y0, y1, 100)
    X, Y = np.meshgrid(X, Y)

    model = learn_model(1, features[:, (0, 2)], np.array(labels))
    C = apply_model(
        np.vstack([X.ravel(), Y.ravel()]).T, model).reshape(X.shape)
    if COLOUR_FIGURE:
        cmap = ListedColormap([(1., .6, .6), (.6, 1., .6), (.6, .6, 1.)])
    else:
        cmap = ListedColormap([(1., 1., 1.), (.2, .2, .2), (.6, .6, .6)])
    plt.xlim(x0, x1)
    plt.ylim(y0, y1)
    plt.xlabel(feature_names[0])
    plt.ylabel(feature_names[2])
    plt.pcolormesh(X, Y, C, cmap=cmap)
    if COLOUR_FIGURE:
        cmap = ListedColormap([(1., .0, .0), (.0, 1., .0), (.0, .0, 1.)])
        plt.scatter(features[:, 0], features[:, 2], c=labels, cmap=cmap)
    else:
        for lab, ma in zip(range(3), "Do^"):
            plt.plot(features[labels == lab, 0], features[
                     labels == lab, 2], ma, c=(1., 1., 1.))


features, labels = load_dataset('seeds')
names = sorted(set(labels))
labels = np.array([names.index(ell) for ell in labels])

train_plot(features, labels)
plt.savefig('figure4.png')

features -= features.mean(0)
features /= features.std(0)
train_plot(features, labels)
plt.savefig('figure5.png')

########NEW FILE########
__FILENAME__ = heldout
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

# This script demonstrates the difference between the training accuracy and
# testing (held-out) accuracy.

from matplotlib import pyplot as plt
import numpy as np
from sklearn.datasets import load_iris
from threshold import learn_model, apply_model, accuracy

data = load_iris()
features = data['data']
labels = data['target_names'][data['target']]

# We are going to remove the setosa examples as they are too easy:
setosa = (labels == 'setosa')
features = features[~setosa]
labels = labels[~setosa]

# Now we classify virginica vs non-virginica
virginica = (labels == 'virginica')

# Split the data in two: testing and training
testing = np.tile([True, False], 50) # testing = [True,False,True,False,True,False...]
training = ~testing

model = learn_model(features[training], virginica[training])
train_accuracy = accuracy(features[training], virginica[training], model)
test_accuracy = accuracy(features[testing], virginica[testing], model)

print('''\
Training accuracy was {0:.1%}.
Testing accuracy was {1:.1%} (N = {2}).
'''.format(train_accuracy, test_accuracy, testing.sum()))

########NEW FILE########
__FILENAME__ = knn
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np


def learn_model(k, features, labels):
    '''Learn a k-nn model'''
    # There is no model in k-nn, just a copy of the inputs
    return k, features.copy(), labels.copy()


def plurality(xs):
    '''Find the most common element in a collection'''
    from collections import defaultdict
    counts = defaultdict(int)
    for x in xs:
        counts[x] += 1
    maxv = max(counts.values())
    for k, v in counts.items():
        if v == maxv:
            return k


def apply_model(features, model):
    '''Apply k-nn model'''
    k, train_feats, labels = model
    results = []
    for f in features:
        label_dist = []
        # Compute all distances:
        for t, ell in zip(train_feats, labels):
            label_dist.append((np.linalg.norm(f - t), ell))
        label_dist.sort(key=lambda d_ell: d_ell[0])
        label_dist = label_dist[:k]
        results.append(plurality([ell for _, ell in label_dist]))
    return np.array(results)


def accuracy(features, labels, model):
    preds = apply_model(features, model)
    return np.mean(preds == labels)

########NEW FILE########
__FILENAME__ = load
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np


def load_dataset(dataset_name):
    '''
    data,labels = load_dataset(dataset_name)

    Load a given dataset

    Returns
    -------
    data : numpy ndarray
    labels : list of str
    '''
    data = []
    labels = []
    with open('./data/{0}.tsv'.format(dataset_name)) as ifile:
        for line in ifile:
            tokens = line.strip().split('\t')
            data.append([float(tk) for tk in tokens[:-1]])
            labels.append(tokens[-1])
    data = np.array(data)
    labels = np.array(labels)
    return data, labels

########NEW FILE########
__FILENAME__ = seeds_knn
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from load import load_dataset
import numpy as np
from knn import learn_model, apply_model, accuracy

features, labels = load_dataset('seeds')


def cross_validate(features, labels):
    '''Compute cross-validation errors'''
    error = 0.0
    for fold in range(10):
        training = np.ones(len(features), bool)
        training[fold::10] = 0
        testing = ~training
        model = learn_model(1, features[training], labels[training])
        test_error = accuracy(features[testing], labels[testing], model)
        error += test_error

    return error / 10.0

error = cross_validate(features, labels)
print('Ten fold cross-validated error was {0:.1%}.'.format(error))

# Z-score (whiten) the features
features -= features.mean(0)
features /= features.std(0)
error = cross_validate(features, labels)
print(
    'Ten fold cross-validated error after z-scoring was {0:.1%}.'.format(error))

########NEW FILE########
__FILENAME__ = seeds_threshold
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from load import load_dataset
import numpy as np
from threshold import learn_model, apply_model, accuracy

features, labels = load_dataset('seeds')

# Turn the labels into a binary array
labels = (labels == 'Canadian')

error = 0.0
for fold in range(10):
    training = np.ones(len(features), bool)

    # numpy magic to make an array with 10% of 0s starting at fold
    training[fold::10] = 0

    # whatever is not training is for testing
    testing = ~training

    model = learn_model(features[training], labels[training])
    test_error = accuracy(features[testing], labels[testing], model)
    error += test_error

error /= 10.0

print('Ten fold cross-validated error was {0:.1%}.'.format(error))

########NEW FILE########
__FILENAME__ = simple_threshold
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from sklearn.datasets import load_iris

data = load_iris()
features = data['data']
target = data['target']
target_names = data['target_names']
labels = target_names[target]

plength = features[:, 2]
is_setosa = (labels == 'setosa')
print('Maximum of setosa: {0}.'.format(plength[is_setosa].max()))
print('Minimum of others: {0}.'.format(plength[~is_setosa].min()))

########NEW FILE########
__FILENAME__ = stump
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from matplotlib import pyplot as plt
from sklearn.datasets import load_iris
data = load_iris()
features = data['data']
labels = data['target_names'][data['target']]


setosa = (labels == 'setosa')
features = features[~setosa]
labels = labels[~setosa]
virginica = (labels == 'virginica')


best_acc = -1.0
for fi in range(features.shape[1]):
    thresh = features[:, fi].copy()
    thresh.sort()
    for t in thresh:
        pred = (features[:, fi] > t)
        acc = (pred == virginica).mean()
        if acc > best_acc:
            best_acc = acc
            best_fi = fi
            best_t = t
print('Best cut is {0} on feature {1}, which achieves accuracy of {2:.1%}.'.format(
    best_t, best_fi, best_acc))

########NEW FILE########
__FILENAME__ = test_load
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from load import load_dataset


def test_iris():
    features, labels = load_dataset('iris')
    assert len(features[0]) == 4
    assert len(features)
    assert len(features) == len(labels)


def test_seeds():
    features, labels = load_dataset('seeds')
    assert len(features[0]) == 7
    assert len(features)
    assert len(features) == len(labels)

########NEW FILE########
__FILENAME__ = threshold
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np


def learn_model(features, labels):
    '''Learn a simple threshold model'''
    best_acc = -1.0
    # Loop over all the features:
    for fi in range(features.shape[1]):
        thresh = features[:, fi].copy()
        # test all feature values in order:
        thresh.sort()
        for t in thresh:
            pred = (features[:, fi] > t)

            # Measure the accuracy of this 
            acc = (pred == labels).mean()
            if acc > best_acc:
                best_acc = acc
                best_fi = fi
                best_t = t

    # A model is a threshold and an index
    return best_t, best_fi


def apply_model(features, model):
    '''Apply a learned model'''
    # A model is a pair as returned by learn_model
    t, fi = model
    return features[:, fi] > t

def accuracy(features, labels, model):
    '''Compute the accuracy of the model'''
    preds = apply_model(features, model)
    return np.mean(preds == labels)

########NEW FILE########
__FILENAME__ = plot_kmeans_example
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

# inspired by http://scikit-
# learn.org/dev/auto_examples/cluster/plot_kmeans_digits.html#example-
# cluster-plot-kmeans-digits-py

import os
import scipy as sp
from scipy.stats import norm
from matplotlib import pylab
from sklearn.cluster import KMeans

from utils import DATA_DIR, CHART_DIR

seed = 2
sp.random.seed(seed)  # to reproduce the data later on

num_clusters = 3


def plot_clustering(x, y, title, mx=None, ymax=None, xmin=None, km=None):
    pylab.figure(num=None, figsize=(8, 6))
    if km:
        pylab.scatter(x, y, s=50, c=km.predict(list(zip(x, y))))
    else:
        pylab.scatter(x, y, s=50)

    pylab.title(title)
    pylab.xlabel("Occurrence word 1")
    pylab.ylabel("Occurrence word 2")
    # pylab.xticks([w*7*24 for w in range(10)], ['week %i'%w for w in range(10)])

    pylab.autoscale(tight=True)
    pylab.ylim(ymin=0, ymax=1)
    pylab.xlim(xmin=0, xmax=1)
    pylab.grid(True, linestyle='-', color='0.75')

    return pylab


xw1 = norm(loc=0.3, scale=.15).rvs(20)
yw1 = norm(loc=0.3, scale=.15).rvs(20)

xw2 = norm(loc=0.7, scale=.15).rvs(20)
yw2 = norm(loc=0.7, scale=.15).rvs(20)

xw3 = norm(loc=0.2, scale=.15).rvs(20)
yw3 = norm(loc=0.8, scale=.15).rvs(20)

x = sp.append(sp.append(xw1, xw2), xw3)
y = sp.append(sp.append(yw1, yw2), yw3)

i = 1
plot_clustering(x, y, "Vectors")
pylab.savefig(os.path.join(CHART_DIR, "1400_03_0%i.png" % i))
pylab.clf()

i += 1

# 1 iteration ####################

mx, my = sp.meshgrid(sp.arange(0, 1, 0.001), sp.arange(0, 1, 0.001))

km = KMeans(init='random', n_clusters=num_clusters, verbose=1,
            n_init=1, max_iter=1,
            random_state=seed)
km.fit(sp.array(list(zip(x, y))))

Z = km.predict(sp.c_[mx.ravel(), my.ravel()]).reshape(mx.shape)

plot_clustering(x, y, "Clustering iteration 1", km=km)
pylab.imshow(Z, interpolation='nearest',
             extent=(mx.min(), mx.max(), my.min(), my.max()),
             cmap=pylab.cm.Blues,
             aspect='auto', origin='lower')

c1a, c1b, c1c = km.cluster_centers_
pylab.scatter(km.cluster_centers_[:, 0], km.cluster_centers_[:, 1],
              marker='x', linewidth=2, s=100, color='black')
pylab.savefig(os.path.join(CHART_DIR, "1400_03_0%i.png" % i))
pylab.clf()

i += 1

# 2 iterations ####################
km = KMeans(init='random', n_clusters=num_clusters, verbose=1,
            n_init=1, max_iter=2,
            random_state=seed)
km.fit(sp.array(list(zip(x, y))))

Z = km.predict(sp.c_[mx.ravel(), my.ravel()]).reshape(mx.shape)

plot_clustering(x, y, "Clustering iteration 2", km=km)
pylab.imshow(Z, interpolation='nearest',
             extent=(mx.min(), mx.max(), my.min(), my.max()),
             cmap=pylab.cm.Blues,
             aspect='auto', origin='lower')

c2a, c2b, c2c = km.cluster_centers_
pylab.scatter(km.cluster_centers_[:, 0], km.cluster_centers_[:, 1],
              marker='x', linewidth=2, s=100, color='black')

pylab.gca().add_patch(
    pylab.Arrow(c1a[0], c1a[1], c2a[0] - c1a[0], c2a[1] - c1a[1], width=0.1))
pylab.gca().add_patch(
    pylab.Arrow(c1b[0], c1b[1], c2b[0] - c1b[0], c2b[1] - c1b[1], width=0.1))
pylab.gca().add_patch(
    pylab.Arrow(c1c[0], c1c[1], c2c[0] - c1c[0], c2c[1] - c1c[1], width=0.1))

pylab.savefig(os.path.join(CHART_DIR, "1400_03_0%i.png" % i))
pylab.clf()

i += 1

# 3 iterations ####################
km = KMeans(init='random', n_clusters=num_clusters, verbose=1,
            n_init=1, max_iter=10,
            random_state=seed)
km.fit(sp.array(list(zip(x, y))))

Z = km.predict(sp.c_[mx.ravel(), my.ravel()]).reshape(mx.shape)

plot_clustering(x, y, "Clustering iteration 10", km=km)
pylab.imshow(Z, interpolation='nearest',
             extent=(mx.min(), mx.max(), my.min(), my.max()),
             cmap=pylab.cm.Blues,
             aspect='auto', origin='lower')

pylab.scatter(km.cluster_centers_[:, 0], km.cluster_centers_[:, 1],
              marker='x', linewidth=2, s=100, color='black')
pylab.savefig(os.path.join(CHART_DIR, "1400_03_0%i.png" % i))
pylab.clf()

i += 1

########NEW FILE########
__FILENAME__ = rel_post_01
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os
import sys

import scipy as sp

from sklearn.feature_extraction.text import CountVectorizer

from utils import DATA_DIR

TOY_DIR = os.path.join(DATA_DIR, "toy")
posts = [open(os.path.join(TOY_DIR, f)).read() for f in os.listdir(TOY_DIR)]

new_post = "imaging databases"

import nltk.stem
english_stemmer = nltk.stem.SnowballStemmer('english')


class StemmedCountVectorizer(CountVectorizer):

    def build_analyzer(self):
        analyzer = super(StemmedCountVectorizer, self).build_analyzer()
        return lambda doc: (english_stemmer.stem(w) for w in analyzer(doc))

# vectorizer = CountVectorizer(min_df=1, stop_words='english',
# preprocessor=stemmer)
vectorizer = StemmedCountVectorizer(min_df=1, stop_words='english')

from sklearn.feature_extraction.text import TfidfVectorizer


class StemmedTfidfVectorizer(TfidfVectorizer):

    def build_analyzer(self):
        analyzer = super(StemmedTfidfVectorizer, self).build_analyzer()
        return lambda doc: (english_stemmer.stem(w) for w in analyzer(doc))

vectorizer = StemmedTfidfVectorizer(
    min_df=1, stop_words='english', charset_error='ignore')
print(vectorizer)

X_train = vectorizer.fit_transform(posts)

num_samples, num_features = X_train.shape
print("#samples: %d, #features: %d" % (num_samples, num_features))

new_post_vec = vectorizer.transform([new_post])
print(new_post_vec, type(new_post_vec))
print(new_post_vec.toarray())
print(vectorizer.get_feature_names())


def dist_raw(v1, v2):
    delta = v1 - v2
    return sp.linalg.norm(delta.toarray())


def dist_norm(v1, v2):
    v1_normalized = v1 / sp.linalg.norm(v1.toarray())
    v2_normalized = v2 / sp.linalg.norm(v2.toarray())

    delta = v1_normalized - v2_normalized

    return sp.linalg.norm(delta.toarray())

dist = dist_norm

best_dist = sys.maxsize
best_i = None

for i in range(0, num_samples):
    post = posts[i]
    if post == new_post:
        continue
    post_vec = X_train.getrow(i)
    d = dist(post_vec, new_post_vec)

    print("=== Post %i with dist=%.2f: %s" % (i, d, post))

    if d < best_dist:
        best_dist = d
        best_i = i

print("Best post is %i with dist=%.2f" % (best_i, best_dist))

########NEW FILE########
__FILENAME__ = rel_post_mlcomp_01
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os
import sys
import sklearn.datasets
import scipy as sp

from utils import DATA_DIR

if not os.path.exists(DATA_DIR):
    print("""\
It seems that you have not yet downloaded the MLCOMP data set.
Please do so and place it into %s."""%DATA_DIR)
    sys.exit(1)

new_post = \
    """Disk drive problems. Hi, I have a problem with my hard disk.
After 1 year it is working only sporadically now.
I tried to format it, but now it doesn't boot any more.
Any ideas? Thanks.
"""

groups = [
    'comp.graphics', 'comp.os.ms-windows.misc', 'comp.sys.ibm.pc.hardware',
    'comp.sys.ma c.hardware', 'comp.windows.x', 'sci.space']
dataset = sklearn.datasets.load_mlcomp("20news-18828", "train",
                                       mlcomp_root=DATA_DIR,
                                       categories=groups)
print("Number of posts:", len(dataset.filenames))

labels = dataset.target
num_clusters = 50  # sp.unique(labels).shape[0]

import nltk.stem
english_stemmer = nltk.stem.SnowballStemmer('english')

from sklearn.feature_extraction.text import TfidfVectorizer


class StemmedTfidfVectorizer(TfidfVectorizer):

    def build_analyzer(self):
        analyzer = super(TfidfVectorizer, self).build_analyzer()
        return lambda doc: (english_stemmer.stem(w) for w in analyzer(doc))

vectorizer = StemmedTfidfVectorizer(min_df=10, max_df=0.5,
                                    # max_features=1000,
                                    stop_words='english', charset_error='ignore'
                                    )
vectorized = vectorizer.fit_transform(dataset.data)
num_samples, num_features = vectorized.shape
print("#samples: %d, #features: %d" % (num_samples, num_features))


from sklearn.cluster import KMeans

km = KMeans(n_clusters=num_clusters, init='k-means++', n_init=1,
            verbose=1)

clustered = km.fit(vectorized)

from sklearn import metrics
print("Homogeneity: %0.3f" % metrics.homogeneity_score(labels, km.labels_))
print("Completeness: %0.3f" % metrics.completeness_score(labels, km.labels_))
print("V-measure: %0.3f" % metrics.v_measure_score(labels, km.labels_))
print("Adjusted Rand Index: %0.3f" %
      metrics.adjusted_rand_score(labels, km.labels_))
print("Adjusted Mutual Information: %0.3f" %
      metrics.adjusted_mutual_info_score(labels, km.labels_))
print(("Silhouette Coefficient: %0.3f" %
       metrics.silhouette_score(vectorized, labels, sample_size=1000)))

new_post_vec = vectorizer.transform([new_post])
new_post_label = km.predict(new_post_vec)[0]

similar_indices = (km.labels_ == new_post_label).nonzero()[0]

similar = []
for i in similar_indices:
    dist = sp.linalg.norm((new_post_vec - vectorized[i]).toarray())
    similar.append((dist, dataset.data[i]))

similar = sorted(similar)

show_at_1 = similar[0]
show_at_2 = similar[len(similar) / 2]
show_at_3 = similar[-1]

print("=== #1 ===")
print(show_at_1)
print()

print("=== #2 ===")
print(show_at_2)
print()

print("=== #3 ===")
print(show_at_3)

########NEW FILE########
__FILENAME__ = tfidf
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import scipy as sp


def tfidf(t, d, D):
    tf = float(d.count(t)) / sum(d.count(w) for w in set(d))
    idf = sp.log(float(len(D)) / (len([doc for doc in D if t in doc])))
    return tf * idf


a, abb, abc = ["a"], ["a", "b", "b"], ["a", "b", "c"]
D = [a, abb, abc]

print(tfidf("a", a, D))
print(tfidf("b", abb, D))
print(tfidf("a", abc, D))
print(tfidf("b", abc, D))
print(tfidf("c", abc, D))

########NEW FILE########
__FILENAME__ = utils
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os
import sys

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "data")

if not os.path.exists(DATA_DIR):
    print("Uh, we were expecting a data directory, which contains the toy data")
    sys.exit(1)


########NEW FILE########
__FILENAME__ = blei_lda
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from __future__ import print_function
try:
    from gensim import corpora, models, similarities
except:
    print("import gensim failed.")
    print()
    print("Please install it")
    raise

try:
    from mpltools import style
    style.use('ggplot')
except:
    print("Could not import mpltools: plots will not be styled correctly")

import matplotlib.pyplot as plt
import numpy as np
from os import path

if not path.exists('./data/ap/ap.dat'):
    print('Error: Expected data to be present at data/ap/')
    print('Please cd into ./data & run ./download_ap.sh')

corpus = corpora.BleiCorpus('./data/ap/ap.dat', './data/ap/vocab.txt')
model = models.ldamodel.LdaModel(
    corpus, num_topics=100, id2word=corpus.id2word, alpha=None)

for ti in xrange(84):
    words = model.show_topic(ti, 64)
    tf = sum(f for f, w in words)
    print('\n'.join('{}:{}'.format(w, int(1000. * f / tf)) for f, w in words))
    print()
    print()
    print()

thetas = [model[c] for c in corpus]
plt.hist([len(t) for t in thetas], np.arange(42))
plt.ylabel('Nr of documents')
plt.xlabel('Nr of topics')
plt.savefig('../1400OS_04_01+.png')

model1 = models.ldamodel.LdaModel(
    corpus, num_topics=100, id2word=corpus.id2word, alpha=1.)
thetas1 = [model1[c] for c in corpus]

#model8 = models.ldamodel.LdaModel(corpus, num_topics=100, id2word=corpus.id2word, alpha=1.e-8)
#thetas8 = [model8[c] for c in corpus]
plt.clf()
plt.hist([[len(t) for t in thetas], [len(t) for t in thetas1]], np.arange(42))
plt.ylabel('Nr of documents')
plt.xlabel('Nr of topics')
plt.text(9, 223, r'default alpha')
plt.text(26, 156, 'alpha=1.0')
plt.savefig('../1400OS_04_02+.png')

########NEW FILE########
__FILENAME__ = build_lda
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License
from __future__ import print_function

try:
    import nltk.corpus
except ImportError:
    print("nltk not found")
    print("please install it")
    raise
from scipy.spatial import distance
import numpy as np
import string
from gensim import corpora, models, similarities
import sklearn.datasets
import nltk.stem
from collections import defaultdict

english_stemmer = nltk.stem.SnowballStemmer('english')
stopwords = set(nltk.corpus.stopwords.words('english'))
stopwords.update(['from:', 'subject:', 'writes:', 'writes'])


class DirectText(corpora.textcorpus.TextCorpus):

    def get_texts(self):
        return self.input

    def __len__(self):
        return len(self.input)
try:
    dataset = sklearn.datasets.load_mlcomp("20news-18828", "train",
                                       mlcomp_root='./data')
except:
    print("Newsgroup data not found.")
    print("Please download from http://mlcomp.org/datasets/379")
    print("And expand the zip into the subdirectory data/")
    print()
    print()
    raise

otexts = dataset.data
texts = dataset.data

texts = [t.decode('utf-8', 'ignore') for t in texts]
texts = [t.split() for t in texts]
texts = [map(lambda w: w.lower(), t) for t in texts]
texts = [filter(lambda s: not len(set("+-.?!()>@012345689") & set(s)), t)
         for t in texts]
texts = [filter(lambda s: (len(s) > 3) and (s not in stopwords), t)
         for t in texts]
texts = [map(english_stemmer.stem, t) for t in texts]
usage = defaultdict(int)
for t in texts:
    for w in set(t):
        usage[w] += 1
limit = len(texts) / 10
too_common = [w for w in usage if usage[w] > limit]
too_common = set(too_common)
texts = [filter(lambda s: s not in too_common, t) for t in texts]

corpus = DirectText(texts)
dictionary = corpus.dictionary
try:
    dictionary['computer']
except:
    pass

model = models.ldamodel.LdaModel(
    corpus, num_topics=100, id2word=dictionary.id2token)

thetas = np.zeros((len(texts), 100))
for i, c in enumerate(corpus):
    for ti, v in model[c]:
        thetas[i, ti] += v

distances = distance.squareform(distance.pdist(thetas))
large = distances.max() + 1
for i in xrange(len(distances)):
    distances[i, i] = large

print(otexts[1])
print()
print()
print()
print(otexts[distances[1].argmin()])

########NEW FILE########
__FILENAME__ = wikitopics
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from __future__ import print_function
import numpy as np
import logging
import gensim
logging.basicConfig(
    format='%(asctime)s : %(levelname)s : %(message)s',
    level=logging.INFO)
id2word = gensim.corpora.Dictionary.load_from_text(
    'data/wiki_en_output_wordids.txt')
mm = gensim.corpora.MmCorpus('data/wiki_en_output_tfidf.mm')
model = gensim.models.ldamodel.LdaModel(
    corpus=mm,
    id2word=id2word,
    num_topics=100,
    update_every=1,
    chunksize=10000,
    passes=1)
model.save('wiki_lda.pkl')
topics = [model[doc] for doc in mm]
lens = np.array([len(t) for t in topics])
print(np.mean(lens <= 10))
print(np.mean(lens))

counts = np.zeros(100)
for doc_top in topics:
    for ti, _ in doc_toc:
        counts[ti] += 1

for doc_top in topics:
    for ti, _ in doc_top:
        counts[ti] += 1

words = model.show_topic(counts.argmax(), 64)
print(words)
print()
print()
print()
words = model.show_topic(counts.argmin(), 64)
print(words)
print()
print()
print()

########NEW FILE########
__FILENAME__ = chose_instances
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os
try:
    import ujson as json  # UltraJSON if available
except:
    import json
import sys
from collections import defaultdict

try:
    import enchant
    speller = enchant.Dict("en_US")

except:
    print("""\
Enchant is not installed, which is not a problem since spell correction features
will not be used in the chapter. If, however, you want to experiment with them
(highly encouraged!), you can get the library from http://packages.python.org/pyenchant/.
""")
    class EnchantMock:
        def __init__(self):
            pass
        def check(self, word):
            return True
    speller = EnchantMock()

from data import chosen, chosen_meta, filtered, filtered_meta

filtered_meta = json.load(open(filtered_meta, "r"))



def misspelled_fraction(p):
    tokens = p.split()
    if not tokens:
        return 0.0
    return 1 - float(sum(speller.check(t) for t in tokens)) / len(tokens)


def data(filename, col=None):
    for line in open(filename, "r"):
        data = line.strip().split("\t")

        # check format
        Id, ParentId, IsAccepted, TimeToAnswer, Score, Text, NumTextTokens, NumCodeLines, LinkCount, NumImages = data

        if col:
            yield data[col]
        else:
            yield data

posts_to_keep = set()
found_questions = 0

num_qestion_sample = 1000

# keep the best and worst, but only if we have one with positive and one with negative score
# filter_method = "negative_positive"

# if true, only keep the lowest scoring answer per class in addition to the accepted one
# filter_method = "only_one_per_class "

# if not None, specifies the number of unaccepted per question
# filter_method = "sample_per_question"
filter_method = "negative_positive"  # warning: this does not retrieve many!
# filter_method = "only_one_per_class"
MaxAnswersPerQuestions = 10  # filter_method == "sample_per_question"

# filter_method = "all"

# equal share of questions that are unanswered and those that are answered
# filter_method = "half-half"

unaccepted_scores = {}

has_q_accepted_a = {}
num_q_with_accepted_a = 0
num_q_without_accepted_a = 0

for ParentId, posts in filtered_meta.items():
    assert ParentId != -1

    if len(posts) < 2:
        continue

    ParentId = int(ParentId)
    AllIds = set([ParentId])
    AcceptedId = None
    UnacceptedId = None
    UnacceptedIds = []
    UnacceptedScore = sys.maxsize

    NegativeScoreIds = []
    PositiveScoreIds = []

    if filter_method == "half-half":

        has_accepted_a = False
        for post in posts:
            Id, IsAccepted, TimeToAnswer, Score = post

            if IsAccepted:
                has_accepted_a = True
                break

        has_q_accepted_a[ParentId] = has_accepted_a

        if has_accepted_a:
            if num_q_with_accepted_a < num_qestion_sample / 2:
                num_q_with_accepted_a += 1
                posts_to_keep.add(ParentId)
        else:
            if num_q_without_accepted_a < num_qestion_sample / 2:
                num_q_without_accepted_a += 1
                posts_to_keep.add(ParentId)

        if num_q_without_accepted_a + num_q_with_accepted_a > num_qestion_sample:
            assert -1 not in posts_to_keep
            break

    else:

        for post in posts:
            Id, IsAccepted, TimeToAnswer, Score = post

            if filter_method == "all":
                AllIds.add(int(Id))

            elif filter_method == "only_one_per_class":
                if IsAccepted:
                    AcceptedId = Id
                elif Score < UnacceptedScore:
                    UnacceptedScore = Score
                    UnacceptedId = Id

            elif filter_method == "sample_per_question":
                if IsAccepted:
                    AcceptedId = Id
                else:
                    UnacceptedIds.append(Id)

            elif filter_method == "negative_positive":
                if Score < 0:
                    NegativeScoreIds.append((Score, Id))
                elif Score > 0:
                    PositiveScoreIds.append((Score, Id))

            else:
                raise ValueError(filter_method)

        added = False
        if filter_method == "all":
            posts_to_keep.update(AllIds)
            added = True
        elif filter_method == "only_one_per_class":
            if AcceptedId is not None and UnacceptedId is not None:
                posts_to_keep.add(ParentId)
                posts_to_keep.add(AcceptedId)
                posts_to_keep.add(UnacceptedId)
                added = True

        elif filter_method == "sample_per_question":
            if AcceptedId is not None and UnacceptedIds is not None:
                posts_to_keep.add(ParentId)
                posts_to_keep.add(AcceptedId)
                posts_to_keep.update(UnacceptedIds[:MaxAnswersPerQuestions])
                added = True

        elif filter_method == "negative_positive":
            if PositiveScoreIds and NegativeScoreIds:
                posts_to_keep.add(ParentId)

                posScore, posId = sorted(PositiveScoreIds)[-1]
                posts_to_keep.add(posId)

                negScore, negId = sorted(NegativeScoreIds)[0]
                posts_to_keep.add(negId)
                print("%i: %i/%i %i/%i" % (ParentId, posId,
                      posScore, negId, negScore))
                added = True

        if added:
            found_questions += 1

    if num_qestion_sample and found_questions >= num_qestion_sample:
        break

total = 0
kept = 0

already_written = set()
chosen_meta_dict = defaultdict(dict)

with open(chosen, "w") as f:
    for line in data(filtered):
        strId, ParentId, IsAccepted, TimeToAnswer, Score, Text, NumTextTokens, NumCodeLines, LinkCount, NumImages = line
        Text = Text.strip()

        total += 1

        Id = int(strId)
        if Id in posts_to_keep:
            if Id in already_written:
                print(Id, "is already written")
                continue

            if kept % 100 == 0:
                print(kept)

            # setting meta info
            post = chosen_meta_dict[Id]
            post['ParentId'] = int(ParentId)
            post['IsAccepted'] = int(IsAccepted)
            post['TimeToAnswer'] = int(TimeToAnswer)
            post['Score'] = int(Score)
            post['NumTextTokens'] = int(NumTextTokens)
            post['NumCodeLines'] = int(NumCodeLines)
            post['LinkCount'] = int(LinkCount)
            post['MisSpelledFraction'] = misspelled_fraction(Text)
            post['NumImages'] = int(NumImages)
            post['idx'] = kept  # index into the file

            if int(ParentId) == -1:
                q = chosen_meta_dict[Id]

                if not 'Answers' in q:
                    q['Answers'] = []

                if filter_method == "half-half":
                    q['HasAcceptedAnswer'] = has_q_accepted_a[Id]

            else:
                q = chosen_meta_dict[int(ParentId)]

                if int(IsAccepted) == 1:
                    assert 'HasAcceptedAnswer' not in q
                    q['HasAcceptedAnswer'] = True

                if 'Answers' not in q:
                    q['Answers'] = [Id]
                else:
                    q['Answers'].append(Id)

            f.writelines("%s\t%s\n" % (Id, Text))
            kept += 1

with open(chosen_meta, "w") as fm:
    json.dump(chosen_meta_dict, fm)

print("total=", total)
print("kept=", kept)

########NEW FILE########
__FILENAME__ = classify
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import time
start_time = time.time()

import numpy as np

from sklearn.metrics import classification_report
from sklearn.metrics import precision_recall_curve, roc_curve, auc
from sklearn.cross_validation import KFold
from sklearn import neighbors

from data import chosen, chosen_meta
from utils import plot_roc, plot_pr
from utils import plot_feat_importance
from utils import load_meta
from utils import fetch_posts
from utils import plot_feat_hist
from utils import plot_bias_variance
from utils import plot_k_complexity

# question Id -> {'features'->feature vector, 'answers'->[answer Ids]}, 'scores'->[scores]}
# scores will be added on-the-fly as the are not in meta
meta, id_to_idx, idx_to_id = load_meta(chosen_meta)

import nltk

# splitting questions into train (70%) and test(30%) and then take their
# answers
all_posts = list(meta.keys())
all_questions = [q for q, v in meta.items() if v['ParentId'] == -1]
all_answers = [q for q, v in meta.items() if v['ParentId'] != -1]  # [:500]

feature_names = np.array((
    'NumTextTokens',
    'NumCodeLines',
    'LinkCount',
    'AvgSentLen',
    'AvgWordLen',
    'NumAllCaps',
    'NumExclams',
    'NumImages'
))

# activate the following for reduced feature space
"""
feature_names = np.array((
    'NumTextTokens',
    'LinkCount',
))
"""


def prepare_sent_features():
    for pid, text in fetch_posts(chosen, with_index=True):
        if not text:
            meta[pid]['AvgSentLen'] = meta[pid]['AvgWordLen'] = 0
        else:
            sent_lens = [len(nltk.word_tokenize(
                sent)) for sent in nltk.sent_tokenize(text)]
            meta[pid]['AvgSentLen'] = np.mean(sent_lens)
            meta[pid]['AvgWordLen'] = np.mean(
                [len(w) for w in nltk.word_tokenize(text)])

        meta[pid]['NumAllCaps'] = np.sum(
            [word.isupper() for word in nltk.word_tokenize(text)])

        meta[pid]['NumExclams'] = text.count('!')


prepare_sent_features()


def get_features(aid):
    return tuple(meta[aid][fn] for fn in feature_names)

qa_X = np.asarray([get_features(aid) for aid in all_answers])
# Score > 0 tests => positive class is good answer
# Score <= 0 tests => positive class is poor answer
qa_Y = np.asarray([meta[aid]['Score'] > 0 for aid in all_answers])
classifying_answer = "good"

for idx, feat in enumerate(feature_names):
    plot_feat_hist([(qa_X[:, idx], feat)])
"""
plot_feat_hist([(qa_X[:, idx], feature_names[idx]) for idx in [1,0]], 'feat_hist_two.png')
plot_feat_hist([(qa_X[:, idx], feature_names[idx]) for idx in [3,4,5,6]], 'feat_hist_four.png')
"""
avg_scores_summary = []


def measure(clf_class, parameters, name, data_size=None, plot=False):
    start_time_clf = time.time()
    if data_size is None:
        X = qa_X
        Y = qa_Y
    else:
        X = qa_X[:data_size]
        Y = qa_Y[:data_size]

    cv = KFold(n=len(X), n_folds=10, indices=True)

    train_errors = []
    test_errors = []

    scores = []
    roc_scores = []
    fprs, tprs = [], []

    pr_scores = []
    precisions, recalls, thresholds = [], [], []

    for train, test in cv:
        X_train, y_train = X[train], Y[train]
        X_test, y_test = X[test], Y[test]

        clf = clf_class(**parameters)

        clf.fit(X_train, y_train)

        train_score = clf.score(X_train, y_train)
        test_score = clf.score(X_test, y_test)

        train_errors.append(1 - train_score)
        test_errors.append(1 - test_score)

        scores.append(test_score)
        proba = clf.predict_proba(X_test)

        label_idx = 1
        fpr, tpr, roc_thresholds = roc_curve(y_test, proba[:, label_idx])
        precision, recall, pr_thresholds = precision_recall_curve(
            y_test, proba[:, label_idx])

        roc_scores.append(auc(fpr, tpr))
        fprs.append(fpr)
        tprs.append(tpr)

        pr_scores.append(auc(recall, precision))
        precisions.append(precision)
        recalls.append(recall)
        thresholds.append(pr_thresholds)
        print(classification_report(y_test, proba[:, label_idx] >
              0.63, target_names=['not accepted', 'accepted']))

    # get medium clone
    scores_to_sort = pr_scores  # roc_scores
    medium = np.argsort(scores_to_sort)[len(scores_to_sort) / 2]

    if plot:
        #plot_roc(roc_scores[medium], name, fprs[medium], tprs[medium])
        plot_pr(pr_scores[medium], name, precisions[medium],
                recalls[medium], classifying_answer + " answers")

        if hasattr(clf, 'coef_'):
            plot_feat_importance(feature_names, clf, name)

    summary = (name,
               np.mean(scores), np.std(scores),
               np.mean(roc_scores), np.std(roc_scores),
               np.mean(pr_scores), np.std(pr_scores),
               time.time() - start_time_clf)
    print(summary)
    avg_scores_summary.append(summary)
    precisions = precisions[medium]
    recalls = recalls[medium]
    thresholds = np.hstack(([0], thresholds[medium]))
    idx80 = precisions >= 0.8
    print("P=%.2f R=%.2f thresh=%.2f" % (precisions[idx80][0], recalls[
          idx80][0], thresholds[idx80][0]))

    return np.mean(train_errors), np.mean(test_errors)


def bias_variance_analysis(clf_class, parameters, name):
    data_sizes = np.arange(60, 2000, 4)

    train_errors = []
    test_errors = []

    for data_size in data_sizes:
        train_error, test_error = measure(
            clf_class, parameters, name, data_size=data_size)
        train_errors.append(train_error)
        test_errors.append(test_error)

    plot_bias_variance(data_sizes, train_errors,
                       test_errors, name, "Bias-Variance for '%s'" % name)


def k_complexity_analysis(clf_class, parameters):
    ks = np.hstack((np.arange(1, 20), np.arange(21, 100, 5)))

    train_errors = []
    test_errors = []

    for k in ks:
        parameters['n_neighbors'] = k
        train_error, test_error = measure(
            clf_class, parameters, "%dNN" % k, data_size=2000)
        train_errors.append(train_error)
        test_errors.append(test_error)

    plot_k_complexity(ks, train_errors, test_errors)

for k in [5]:  # [5, 10, 40, 90]:
    bias_variance_analysis(neighbors.KNeighborsClassifier, {
                           'n_neighbors': k, 'warn_on_equidistant': False}, "%iNN" % k)
    k_complexity_analysis(neighbors.KNeighborsClassifier, {'n_neighbors': k,
                                                           'warn_on_equidistant': False})
    # measure(neighbors.KNeighborsClassifier, {'n_neighbors': k, 'p': 2,
            #'warn_on_equidistant': False}, "%iNN" % k)

from sklearn.linear_model import LogisticRegression
for C in [0.1]:  # [0.01, 0.1, 1.0, 10.0]:
    name = "LogReg C=%.2f" % C
    bias_variance_analysis(LogisticRegression, {'penalty': 'l2', 'C': C}, name)
    measure(LogisticRegression, {'penalty': 'l2', 'C': C}, name, plot=True)

print("=" * 50)
from operator import itemgetter
for s in reversed(sorted(avg_scores_summary, key=itemgetter(1))):
    print("%-20s\t%.5f\t%.5f\t%.5f\t%.5f\t%.5f\t%.5f\t%.5f" % s)

print("time spent:", time.time() - start_time)

########NEW FILE########
__FILENAME__ = data
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os

DATA_DIR = "data" # put your posts-2011-12.xml into this directory
CHART_DIR = "charts"

filtered = os.path.join(DATA_DIR, "filtered.tsv")
filtered_meta = os.path.join(DATA_DIR, "filtered-meta.json")

chosen = os.path.join(DATA_DIR, "chosen.tsv")
chosen_meta = os.path.join(DATA_DIR, "chosen-meta.json")

########NEW FILE########
__FILENAME__ = log_reg_example
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os
from data import CHART_DIR

import numpy as np
from scipy.stats import norm

from matplotlib import pyplot
np.random.seed(3)

num_per_class = 40
X = np.hstack((norm.rvs(2, size=num_per_class, scale=2),
              norm.rvs(8, size=num_per_class, scale=3)))
y = np.hstack((np.zeros(num_per_class),
               np.ones(num_per_class)))


def lr_model(clf, X):
    return 1.0 / (1.0 + np.exp(-(clf.intercept_ + clf.coef_ * X)))

from sklearn.linear_model import LogisticRegression
logclf = LogisticRegression()
print(logclf)
logclf.fit(X.reshape(num_per_class * 2, 1), y)
print(np.exp(logclf.intercept_), np.exp(logclf.coef_.ravel()))
print("P(x=-1)=%.2f\tP(x=7)=%.2f" %
      (lr_model(logclf, -1), lr_model(logclf, 7)))
X_test = np.arange(-5, 20, 0.1)
pyplot.figure(figsize=(10, 4))
pyplot.xlim((-5, 20))
pyplot.scatter(X, y, c=y)
pyplot.xlabel("feature value")
pyplot.ylabel("class")
pyplot.grid(True, linestyle='-', color='0.75')
pyplot.savefig(os.path.join(CHART_DIR, "log_reg_example_data.png"), bbox_inches="tight")


def lin_model(clf, X):
    return clf.intercept_ + clf.coef_ * X

from sklearn.linear_model import LinearRegression
clf = LinearRegression()
print(clf)
clf.fit(X.reshape(num_per_class * 2, 1), y)
X_odds = np.arange(0, 1, 0.001)
pyplot.figure(figsize=(10, 4))
pyplot.subplot(1, 2, 1)
pyplot.scatter(X, y, c=y)
pyplot.plot(X_test, lin_model(clf, X_test))
pyplot.xlabel("feature value")
pyplot.ylabel("class")
pyplot.title("linear fit on original data")
pyplot.grid(True, linestyle='-', color='0.75')

X_ext = np.hstack((X, norm.rvs(20, size=100, scale=5)))
y_ext = np.hstack((y, np.ones(100)))
clf = LinearRegression()
clf.fit(X_ext.reshape(num_per_class * 2 + 100, 1), y_ext)
pyplot.subplot(1, 2, 2)
pyplot.scatter(X_ext, y_ext, c=y_ext)
pyplot.plot(X_ext, lin_model(clf, X_ext))
pyplot.xlabel("feature value")
pyplot.ylabel("class")
pyplot.title("linear fit on additional data")
pyplot.grid(True, linestyle='-', color='0.75')
pyplot.savefig(os.path.join(CHART_DIR, "log_reg_log_linear_fit.png"), bbox_inches="tight")

pyplot.figure(figsize=(10, 4))
pyplot.xlim((-5, 20))
pyplot.scatter(X, y, c=y)
pyplot.plot(X_test, lr_model(logclf, X_test).ravel())
pyplot.plot(X_test, np.ones(X_test.shape[0]) * 0.5, "--")
pyplot.xlabel("feature value")
pyplot.ylabel("class")
pyplot.grid(True, linestyle='-', color='0.75')
pyplot.savefig(os.path.join(CHART_DIR, "log_reg_example_fitted.png"), bbox_inches="tight")

X = np.arange(0, 1, 0.001)
pyplot.figure(figsize=(10, 4))
pyplot.subplot(1, 2, 1)
pyplot.xlim((0, 1))
pyplot.ylim((0, 10))
pyplot.plot(X, X / (1 - X))
pyplot.xlabel("P")
pyplot.ylabel("odds = P / (1-P)")
pyplot.grid(True, linestyle='-', color='0.75')

pyplot.subplot(1, 2, 2)
pyplot.xlim((0, 1))
pyplot.plot(X, np.log(X / (1 - X)))
pyplot.xlabel("P")
pyplot.ylabel("log(odds) = log(P / (1-P))")
pyplot.grid(True, linestyle='-', color='0.75')
pyplot.savefig(os.path.join(CHART_DIR, "log_reg_log_odds.png"), bbox_inches="tight")

########NEW FILE########
__FILENAME__ = PosTagFreqVectorizer
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import re
from operator import itemgetter
from collections import Mapping

import scipy.sparse as sp

from sklearn.base import BaseEstimator
from sklearn.feature_extraction.text import strip_accents_ascii, strip_accents_unicode

import nltk

from collections import Counter

try:
    import ujson as json  # UltraJSON if available
except:
    import json

poscache_filename = "poscache.json"


class PosCounter(Counter):

    def __init__(self, iterable=(), normalize=True, poscache=None, **kwargs):
        self.n_sents = 0
        self.normalize = normalize

        self.poscache = poscache

        super(PosCounter, self).__init__(iterable, **kwargs)

    def update(self, other):
        """Adds counts for elements in other"""
        if isinstance(other, self.__class__):
            self.n_sents += other.n_sents
            for x, n in other.items():
                self[x] += n
        else:
            for sent in other:
                self.n_sents += 1

                if self.poscache is not None:
                    if sent in self.poscache:
                        tags = self.poscache[sent]
                    else:
                        self.poscache[sent] = tags = nltk.pos_tag(
                            nltk.word_tokenize(sent))
                else:
                    tags = nltk.pos_tag(nltk.word_tokenize(sent))

                for x in tags:
                    tok, tag = x
                    self[tag] += 1

            if self.normalize:
                for x, n in self.items():
                    self[x] /= float(self.n_sents)


class PosTagFreqVectorizer(BaseEstimator):

    """
    Convert a collection of raw documents to a matrix Pos tag frequencies
    """

    def __init__(self, input='content', charset='utf-8',
                 charset_error='strict', strip_accents=None,
                 vocabulary=None,
                 normalize=True,
                 dtype=float):

        self.input = input
        self.charset = charset
        self.charset_error = charset_error
        self.strip_accents = strip_accents
        if vocabulary is not None:
            self.fixed_vocabulary = True
            if not isinstance(vocabulary, Mapping):
                vocabulary = dict((t, i) for i, t in enumerate(vocabulary))
            self.vocabulary_ = vocabulary
        else:
            self.fixed_vocabulary = False

        try:
            self.poscache = json.load(open(poscache_filename, "r"))
        except IOError:
            self.poscache = {}

        self.normalize = normalize
        self.dtype = dtype

    def write_poscache(self):
        json.dump(self.poscache, open(poscache_filename, "w"))

    def decode(self, doc):
        """Decode the input into a string of unicode symbols

        The decoding strategy depends on the vectorizer parameters.
        """
        if self.input == 'filename':
            doc = open(doc, 'rb').read()

        elif self.input == 'file':
            doc = doc.read()

        if isinstance(doc, bytes):
            doc = doc.decode(self.charset, self.charset_error)
        return doc

    def build_preprocessor(self):
        """Return a function to preprocess the text before tokenization"""

        # unfortunately python functools package does not have an efficient
        # `compose` function that would have allowed us to chain a dynamic
        # number of functions. However the however of a lambda call is a few
        # hundreds of nanoseconds which is negligible when compared to the
        # cost of tokenizing a string of 1000 chars for instance.
        noop = lambda x: x

        # accent stripping
        if not self.strip_accents:
            strip_accents = noop
        elif hasattr(self.strip_accents, '__call__'):
            strip_accents = self.strip_accents
        elif self.strip_accents == 'ascii':
            strip_accents = strip_accents_ascii
        elif self.strip_accents == 'unicode':
            strip_accents = strip_accents_unicode
        else:
            raise ValueError('Invalid value for "strip_accents": %s' %
                             self.strip_accents)

        only_prose = lambda s: re.sub('<[^>]*>', '', s).replace("\n", " ")

        return lambda x: strip_accents(only_prose(x))

    def build_tokenizer(self):
        """Return a function that split a string in sequence of tokens"""
        return nltk.sent_tokenize

    def build_analyzer(self):
        """Return a callable that handles preprocessing and tokenization"""

        preprocess = self.build_preprocessor()

        tokenize = self.build_tokenizer()

        return lambda doc: tokenize(preprocess(self.decode(doc)))

    def _term_count_dicts_to_matrix(self, term_count_dicts):
        i_indices = []
        j_indices = []
        values = []
        vocabulary = self.vocabulary_

        for i, term_count_dict in enumerate(term_count_dicts):
            for term, count in term_count_dict.items():
                j = vocabulary.get(term)
                if j is not None:
                    i_indices.append(i)
                    j_indices.append(j)
                    values.append(count)
            # free memory as we go
            term_count_dict.clear()

        shape = (len(term_count_dicts), max(vocabulary.values()) + 1)
        spmatrix = sp.csr_matrix((values, (i_indices, j_indices)),
                                 shape=shape, dtype=self.dtype)
        return spmatrix

    def fit(self, raw_documents, y=None):
        """Learn a vocabulary dictionary of all tokens in the raw documents

        Parameters
        ----------
        raw_documents: iterable
            an iterable which yields either str, unicode or file objects

        Returns
        -------
        self
        """
        self.fit_transform(raw_documents)
        return self

    def fit_transform(self, raw_documents, y=None):
        """Learn the vocabulary dictionary and return the count vectors

        This is more efficient than calling fit followed by transform.

        Parameters
        ----------
        raw_documents: iterable
            an iterable which yields either str, unicode or file objects

        Returns
        -------
        vectors: array, [n_samples, n_features]
        """
        if self.fixed_vocabulary:
            # No need to fit anything, directly perform the transformation.
            # We intentionally don't call the transform method to make it
            # fit_transform overridable without unwanted side effects in
            # TfidfVectorizer
            analyze = self.build_analyzer()
            term_counts_per_doc = [PosCounter(analyze(doc), normalize=self.normalize, poscache=self.poscache)
                                   for doc in raw_documents]
            return self._term_count_dicts_to_matrix(term_counts_per_doc)

        self.vocabulary_ = {}
        # result of document conversion to term count dicts
        term_counts_per_doc = []
        term_counts = Counter()

        analyze = self.build_analyzer()

        for doc in raw_documents:
            term_count_current = PosCounter(
                analyze(doc), normalize=self.normalize, poscache=self.poscache)
            term_counts.update(term_count_current)

            term_counts_per_doc.append(term_count_current)

        self.write_poscache()

        terms = set(term_counts)

        # store map from term name to feature integer index: we sort the term
        # to have reproducible outcome for the vocabulary structure: otherwise
        # the mapping from feature name to indices might depend on the memory
        # layout of the machine. Furthermore sorted terms might make it
        # possible to perform binary search in the feature names array.
        self.vocabulary_ = dict(((t, i) for i, t in enumerate(sorted(terms))))

        return self._term_count_dicts_to_matrix(term_counts_per_doc)

    def transform(self, raw_documents):
        """Extract token counts out of raw text documents using the vocabulary
        fitted with fit or the one provided in the constructor.

        Parameters
        ----------
        raw_documents: iterable
            an iterable which yields either str, unicode or file objects

        Returns
        -------
        vectors: sparse matrix, [n_samples, n_features]
        """
        if not hasattr(self, 'vocabulary_') or len(self.vocabulary_) == 0:
            raise ValueError("Vocabulary wasn't fitted or is empty!")

        # raw_documents can be an iterable so we don't know its size in
        # advance

        # XXX @larsmans tried to parallelize the following loop with joblib.
        # The result was some 20% slower than the serial version.
        analyze = self.build_analyzer()
        term_counts_per_doc = [Counter(analyze(doc)) for doc in raw_documents]
        return self._term_count_dicts_to_matrix(term_counts_per_doc)

    def get_feature_names(self):
        """Array mapping from feature integer indices to feature name"""
        if not hasattr(self, 'vocabulary_') or len(self.vocabulary_) == 0:
            raise ValueError("Vocabulary wasn't fitted or is empty!")

        return [t for t, i in sorted(iter(self.vocabulary_.items()),
                                     key=itemgetter(1))]

########NEW FILE########
__FILENAME__ = so_xml_to_tsv
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

#
# This script filters the posts and keeps those posts that are or belong
# to a question that has been asked in 2011 or 2012.
#

import os
import re
try:
    import ujson as json  # UltraJSON if available
except:
    import json
from dateutil import parser as dateparser

from operator import itemgetter
from xml.etree import cElementTree as etree
from collections import defaultdict

from data import DATA_DIR

filename = os.path.join(DATA_DIR, "posts-2011-12.xml")
filename_filtered = os.path.join(DATA_DIR, "filtered.tsv")

q_creation = {}  # creation datetimes of questions
q_accepted = {}  # id of accepted answer

# question -> [(answer Id, IsAccepted, TimeToAnswer, Score), ...]
meta = defaultdict(list)

# regegx to find code snippets
code_match = re.compile('<pre>(.*?)</pre>', re.MULTILINE | re.DOTALL)
link_match = re.compile(
    '<a href="http://.*?".*?>(.*?)</a>', re.MULTILINE | re.DOTALL)
img_match = re.compile('<img(.*?)/>', re.MULTILINE | re.DOTALL)
tag_match = re.compile('<[^>]*>', re.MULTILINE | re.DOTALL)


def filter_html(s):
    num_code_lines = 0
    link_count_in_code = 0
    code_free_s = s

    num_images = len(img_match.findall(s))

    # remove source code and count how many lines
    for match_str in code_match.findall(s):
        num_code_lines += match_str.count('\n')
        code_free_s = code_match.sub("", code_free_s)

        # sometimes source code contain links, which we don't want to count
        link_count_in_code += len(link_match.findall(match_str))

    anchors = link_match.findall(s)
    link_count = len(anchors)

    link_count -= link_count_in_code

    html_free_s = re.sub(
        " +", " ", tag_match.sub('', code_free_s)).replace("\n", "")

    link_free_s = html_free_s
    for anchor in anchors:
        if anchor.lower().startswith("http://"):
            link_free_s = link_free_s.replace(anchor, '')

    num_text_tokens = html_free_s.count(" ")

    return link_free_s, num_text_tokens, num_code_lines, link_count, num_images

years = defaultdict(int)
num_questions = 0
num_answers = 0

from itertools import imap

def parsexml(filename):
    global num_questions, num_answers

    counter = 0

    it = imap(itemgetter(1),
             iter(etree.iterparse(filename, events=('start',))))

    root = next(it)  # get posts element

    for elem in it:
        if counter % 100000 == 0:
            print(counter)

        counter += 1

        if elem.tag == 'row':
            creation_date = dateparser.parse(elem.get('CreationDate'))

            Id = int(elem.get('Id'))
            PostTypeId = int(elem.get('PostTypeId'))
            Score = int(elem.get('Score'))

            if PostTypeId == 1:
                num_questions += 1
                years[creation_date.year] += 1

                ParentId = -1
                TimeToAnswer = 0
                q_creation[Id] = creation_date
                accepted = elem.get('AcceptedAnswerId')
                if accepted:
                    q_accepted[Id] = int(accepted)
                IsAccepted = 0

            elif PostTypeId == 2:
                num_answers += 1

                ParentId = int(elem.get('ParentId'))
                if not ParentId in q_creation:
                    # question was too far in the past
                    continue

                TimeToAnswer = (creation_date - q_creation[ParentId]).seconds

                if ParentId in q_accepted:
                    IsAccepted = int(q_accepted[ParentId] == Id)
                else:
                    IsAccepted = 0

                meta[ParentId].append((Id, IsAccepted, TimeToAnswer, Score))

            else:
                continue

            Text, NumTextTokens, NumCodeLines, LinkCount, NumImages = filter_html(
                elem.get('Body'))

            values = (Id, ParentId,
                      IsAccepted,
                      TimeToAnswer, Score,
                      Text.encode("utf-8"),
                      NumTextTokens, NumCodeLines, LinkCount, NumImages)

            yield values

            root.clear()  # preserve memory

with open(os.path.join(DATA_DIR, filename_filtered), "w") as f:
    for values in parsexml(filename):
        line = "\t".join(map(str, values))
        f.write(line + "\n")

with open(os.path.join(DATA_DIR, "filtered-meta.json"), "w") as f:
    json.dump(meta, f)

print("years:", years)
print("#qestions: %i" % num_questions)
print("#answers: %i" % num_answers)

########NEW FILE########
__FILENAME__ = utils
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os

try:
    import ujson as json  # UltraJSON if available
except:
    import json

from matplotlib import pylab
import numpy as np

from data import CHART_DIR


def fetch_data(filename, col=None, line_count=-1, only_questions=False):
    count = 0

    for line in open(filename, "r"):
        count += 1
        if line_count > 0 and count > line_count:
            break

        data = Id, ParentId, IsQuestion, IsAccepted, TimeToAnswer, Score, Text, NumTextTokens, NumCodeLines, LinkCount, MisSpelledFraction = line.split(
            "\t")

        IsQuestion = int(IsQuestion)

        if only_questions and not IsQuestion:
            continue

        if col:
            if col < 6:
                val = int(data[col])
            else:
                val = data[col]

            yield val

        else:
            Id = int(Id)
            assert Id >= 0, line

            ParentId = int(ParentId)

            IsAccepted = int(IsAccepted)

            assert not IsQuestion == IsAccepted == 1, "%i %i --- %s" % (
                IsQuestion, IsAccepted, line)
            assert (ParentId == -1 and IsQuestion) or (
                ParentId >= 0 and not IsQuestion), "%i %i --- %s" % (ParentId, IsQuestion, line)

            TimeToAnswer = int(TimeToAnswer)
            Score = int(Score)
            NumTextTokens = int(NumTextTokens)
            NumCodeLines = int(NumCodeLines)
            LinkCount = int(LinkCount)
            MisSpelledFraction = float(MisSpelledFraction)
            yield Id, ParentId, IsQuestion, IsAccepted, TimeToAnswer, Score, Text, NumTextTokens, NumCodeLines, LinkCount, MisSpelledFraction


def fetch_posts(filename, with_index=True, line_count=-1):
    count = 0

    for line in open(filename, "r"):
        count += 1
        if line_count > 0 and count > line_count:
            break

        Id, Text = line.split("\t")
        Text = Text.strip()

        if with_index:

            yield int(Id), Text

        else:

            yield Text


def load_meta(filename):
    meta = json.load(open(filename, "r"))
    keys = list(meta.keys())

    # JSON only allows string keys, changing that to int
    for key in keys:
        meta[int(key)] = meta[key]
        del meta[key]

    # post Id to index in vectorized
    id_to_idx = {}
    # and back
    idx_to_id = {}

    for PostId, Info in meta.items():
        id_to_idx[PostId] = idx = Info['idx']
        idx_to_id[idx] = PostId

    return meta, id_to_idx, idx_to_id


def plot_roc(auc_score, name, fpr, tpr):
    pylab.figure(num=None, figsize=(6, 5))
    pylab.plot([0, 1], [0, 1], 'k--')
    pylab.xlim([0.0, 1.0])
    pylab.ylim([0.0, 1.0])
    pylab.xlabel('False Positive Rate')
    pylab.ylabel('True Positive Rate')
    pylab.title('Receiver operating characteristic (AUC=%0.2f)\n%s' % (
        auc_score, name))
    pylab.legend(loc="lower right")
    pylab.grid(True, linestyle='-', color='0.75')
    pylab.fill_between(tpr, fpr, alpha=0.5)
    pylab.plot(fpr, tpr, lw=1)
    pylab.savefig(
        os.path.join(CHART_DIR, "roc_" + name.replace(" ", "_") + ".png"))


def plot_pr(auc_score, name, precision, recall, label=None):
    pylab.figure(num=None, figsize=(6, 5))
    pylab.xlim([0.0, 1.0])
    pylab.ylim([0.0, 1.0])
    pylab.xlabel('Recall')
    pylab.ylabel('Precision')
    pylab.title('P/R (AUC=%0.2f) / %s' % (auc_score, label))
    pylab.fill_between(recall, precision, alpha=0.5)
    pylab.grid(True, linestyle='-', color='0.75')
    pylab.plot(recall, precision, lw=1)
    filename = name.replace(" ", "_")
    pylab.savefig(os.path.join(CHART_DIR, "pr_" + filename + ".png"))


def show_most_informative_features(vectorizer, clf, n=20):
    c_f = sorted(zip(clf.coef_[0], vectorizer.get_feature_names()))
    top = list(zip(c_f[:n], c_f[:-(n + 1):-1]))
    for (c1, f1), (c2, f2) in top:
        print("\t%.4f\t%-15s\t\t%.4f\t%-15s" % (c1, f1, c2, f2))


def plot_feat_importance(feature_names, clf, name):
    pylab.figure(num=None, figsize=(6, 5))
    coef_ = clf.coef_
    important = np.argsort(np.absolute(coef_.ravel()))
    f_imp = feature_names[important]
    coef = coef_.ravel()[important]
    inds = np.argsort(coef)
    f_imp = f_imp[inds]
    coef = coef[inds]
    xpos = np.array(list(range(len(coef))))
    pylab.bar(xpos, coef, width=1)

    pylab.title('Feature importance for %s' % (name))
    ax = pylab.gca()
    ax.set_xticks(np.arange(len(coef)))
    labels = ax.set_xticklabels(f_imp)
    for label in labels:
        label.set_rotation(90)
    filename = name.replace(" ", "_")
    pylab.savefig(os.path.join(
        CHART_DIR, "feat_imp_%s.png" % filename), bbox_inches="tight")


def plot_feat_hist(data_name_list, filename=None):
    if len(data_name_list) > 1:
        assert filename is not None

    pylab.figure(num=None, figsize=(8, 6))
    num_rows = 1 + (len(data_name_list) - 1) / 2
    num_cols = 1 if len(data_name_list) == 1 else 2
    pylab.figure(figsize=(5 * num_cols, 4 * num_rows))

    for i in range(num_rows):
        for j in range(num_cols):
            pylab.subplot(num_rows, num_cols, 1 + i * num_cols + j)
            x, name = data_name_list[i * num_cols + j]
            pylab.title(name)
            pylab.xlabel('Value')
            pylab.ylabel('Fraction')
            # the histogram of the data
            max_val = np.max(x)
            if max_val <= 1.0:
                bins = 50
            elif max_val > 50:
                bins = 50
            else:
                bins = max_val
            n, bins, patches = pylab.hist(
                x, bins=bins, normed=1, facecolor='blue', alpha=0.75)

            pylab.grid(True)

    if not filename:
        filename = "feat_hist_%s.png" % name.replace(" ", "_")

    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


def plot_bias_variance(data_sizes, train_errors, test_errors, name, title):
    pylab.figure(num=None, figsize=(6, 5))
    pylab.ylim([0.0, 1.0])
    pylab.xlabel('Data set size')
    pylab.ylabel('Error')
    pylab.title("Bias-Variance for '%s'" % name)
    pylab.plot(
        data_sizes, test_errors, "--", data_sizes, train_errors, "b-", lw=1)
    pylab.legend(["train error", "test error"], loc="upper right")
    pylab.grid(True, linestyle='-', color='0.75')
    pylab.savefig(
        os.path.join(CHART_DIR, "bv_" + name.replace(" ", "_") + ".png"), bbox_inches="tight")


def plot_k_complexity(ks, train_errors, test_errors):
    pylab.figure(num=None, figsize=(6, 5))
    pylab.ylim([0.0, 1.0])
    pylab.xlabel('k')
    pylab.ylabel('Error')
    pylab.title('Errors for for different values of k')
    pylab.plot(
        ks, test_errors, "--", ks, train_errors, "-", lw=1)
    pylab.legend(["train error", "test error"], loc="upper right")
    pylab.grid(True, linestyle='-', color='0.75')
    pylab.savefig(
        os.path.join(CHART_DIR, "kcomplexity.png"), bbox_inches="tight")

########NEW FILE########
__FILENAME__ = 01_start
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

#
# This script trains multinomial Naive Bayes on the tweet corpus
# to find two different results:
# - How well can we distinguis positive from negative tweets?
# - How well can we detect whether a tweet contains sentiment at all?
#

import time
start_time = time.time()

import numpy as np

from sklearn.metrics import precision_recall_curve, roc_curve, auc
from sklearn.cross_validation import ShuffleSplit

from utils import plot_pr
from utils import load_sanders_data
from utils import tweak_labels

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

from sklearn.naive_bayes import MultinomialNB


def create_ngram_model():
    tfidf_ngrams = TfidfVectorizer(ngram_range=(1, 3),
                                   analyzer="word", binary=False)
    clf = MultinomialNB()
    pipeline = Pipeline([('vect', tfidf_ngrams), ('clf', clf)])
    return pipeline


def train_model(clf_factory, X, Y, name="NB ngram", plot=False):
    cv = ShuffleSplit(
        n=len(X), n_iter=10, test_size=0.3, indices=True, random_state=0)

    train_errors = []
    test_errors = []

    scores = []
    pr_scores = []
    precisions, recalls, thresholds = [], [], []

    for train, test in cv:
        X_train, y_train = X[train], Y[train]
        X_test, y_test = X[test], Y[test]

        clf = clf_factory()
        clf.fit(X_train, y_train)

        train_score = clf.score(X_train, y_train)
        test_score = clf.score(X_test, y_test)

        train_errors.append(1 - train_score)
        test_errors.append(1 - test_score)

        scores.append(test_score)
        proba = clf.predict_proba(X_test)

        fpr, tpr, roc_thresholds = roc_curve(y_test, proba[:, 1])
        precision, recall, pr_thresholds = precision_recall_curve(
            y_test, proba[:, 1])

        pr_scores.append(auc(recall, precision))
        precisions.append(precision)
        recalls.append(recall)
        thresholds.append(pr_thresholds)

    scores_to_sort = pr_scores
    median = np.argsort(scores_to_sort)[len(scores_to_sort) / 2]

    if plot:
        plot_pr(pr_scores[median], name, "01", precisions[median],
                recalls[median], label=name)

        summary = (np.mean(scores), np.std(scores),
                   np.mean(pr_scores), np.std(pr_scores))
        print "%.3f\t%.3f\t%.3f\t%.3f\t" % summary

    return np.mean(train_errors), np.mean(test_errors)


def print_incorrect(clf, X, Y):
    Y_hat = clf.predict(X)
    wrong_idx = Y_hat != Y
    X_wrong = X[wrong_idx]
    Y_wrong = Y[wrong_idx]
    Y_hat_wrong = Y_hat[wrong_idx]
    for idx in xrange(len(X_wrong)):
        print "clf.predict('%s')=%i instead of %i" %\
            (X_wrong[idx], Y_hat_wrong[idx], Y_wrong[idx])


if __name__ == "__main__":
    X_orig, Y_orig = load_sanders_data()
    classes = np.unique(Y_orig)
    for c in classes:
        print "#%s: %i" % (c, sum(Y_orig == c))

    print "== Pos vs. neg =="
    pos_neg = np.logical_or(Y_orig == "positive", Y_orig == "negative")
    X = X_orig[pos_neg]
    Y = Y_orig[pos_neg]
    Y = tweak_labels(Y, ["positive"])

    train_model(create_ngram_model, X, Y, name="pos vs neg", plot=True)

    print "== Pos/neg vs. irrelevant/neutral =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["positive", "negative"])
    train_model(create_ngram_model, X, Y, name="sent vs rest", plot=True)

    print "== Pos vs. rest =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["positive"])
    train_model(create_ngram_model, X, Y, name="pos vs rest", plot=True)

    print "== Neg vs. rest =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["negative"])
    train_model(create_ngram_model, X, Y, name="neg vs rest", plot=True)

    print "time spent:", time.time() - start_time

########NEW FILE########
__FILENAME__ = 02_tuning
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

#
# This script trains tries to tweak hyperparameters to improve P/R AUC
#

import time
start_time = time.time()

import numpy as np

from sklearn.metrics import precision_recall_curve, roc_curve, auc
from sklearn.cross_validation import ShuffleSplit

from utils import plot_pr
from utils import load_sanders_data
from utils import tweak_labels

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import f1_score

from sklearn.naive_bayes import MultinomialNB

phase = "02"


def create_ngram_model(params=None):
    tfidf_ngrams = TfidfVectorizer(ngram_range=(1, 3),
                                   analyzer="word", binary=False)
    clf = MultinomialNB()
    pipeline = Pipeline([('vect', tfidf_ngrams), ('clf', clf)])

    if params:
        pipeline.set_params(**params)

    return pipeline


def grid_search_model(clf_factory, X, Y):
    cv = ShuffleSplit(
        n=len(X), n_iter=10, test_size=0.3, indices=True, random_state=0)

    param_grid = dict(vect__ngram_range=[(1, 1), (1, 2), (1, 3)],
                      vect__min_df=[1, 2],
                      vect__stop_words=[None, "english"],
                      vect__smooth_idf=[False, True],
                      vect__use_idf=[False, True],
                      vect__sublinear_tf=[False, True],
                      vect__binary=[False, True],
                      clf__alpha=[0, 0.01, 0.05, 0.1, 0.5, 1],
                      )

    grid_search = GridSearchCV(clf_factory(),
                               param_grid=param_grid,
                               cv=cv,
                               score_func=f1_score,
                               verbose=10)
    grid_search.fit(X, Y)
    clf = grid_search.best_estimator_
    print clf

    return clf


def train_model(clf, X, Y, name="NB ngram", plot=False):
    # create it again for plotting
    cv = ShuffleSplit(
        n=len(X), n_iter=10, test_size=0.3, indices=True, random_state=0)

    train_errors = []
    test_errors = []

    scores = []
    pr_scores = []
    precisions, recalls, thresholds = [], [], []

    for train, test in cv:
        X_train, y_train = X[train], Y[train]
        X_test, y_test = X[test], Y[test]

        clf.fit(X_train, y_train)

        train_score = clf.score(X_train, y_train)
        test_score = clf.score(X_test, y_test)

        train_errors.append(1 - train_score)
        test_errors.append(1 - test_score)

        scores.append(test_score)
        proba = clf.predict_proba(X_test)

        fpr, tpr, roc_thresholds = roc_curve(y_test, proba[:, 1])
        precision, recall, pr_thresholds = precision_recall_curve(
            y_test, proba[:, 1])

        pr_scores.append(auc(recall, precision))
        precisions.append(precision)
        recalls.append(recall)
        thresholds.append(pr_thresholds)

    if plot:
        scores_to_sort = pr_scores
        median = np.argsort(scores_to_sort)[len(scores_to_sort) / 2]

        plot_pr(pr_scores[median], name, phase, precisions[median],
                recalls[median], label=name)

    summary = (np.mean(scores), np.std(scores),
               np.mean(pr_scores), np.std(pr_scores))
    print "%.3f\t%.3f\t%.3f\t%.3f\t" % summary

    return np.mean(train_errors), np.mean(test_errors)


def print_incorrect(clf, X, Y):
    Y_hat = clf.predict(X)
    wrong_idx = Y_hat != Y
    X_wrong = X[wrong_idx]
    Y_wrong = Y[wrong_idx]
    Y_hat_wrong = Y_hat[wrong_idx]
    for idx in xrange(len(X_wrong)):
        print "clf.predict('%s')=%i instead of %i" %\
            (X_wrong[idx], Y_hat_wrong[idx], Y_wrong[idx])


def get_best_model():
    best_params = dict(vect__ngram_range=(1, 2),
                       vect__min_df=1,
                       vect__stop_words=None,
                       vect__smooth_idf=False,
                       vect__use_idf=False,
                       vect__sublinear_tf=True,
                       vect__binary=False,
                       clf__alpha=0.01,
                       )

    best_clf = create_ngram_model(best_params)

    return best_clf

if __name__ == "__main__":
    X_orig, Y_orig = load_sanders_data()
    classes = np.unique(Y_orig)
    for c in classes:
        print "#%s: %i" % (c, sum(Y_orig == c))

    print "== Pos vs. neg =="
    pos_neg = np.logical_or(Y_orig == "positive", Y_orig == "negative")
    X = X_orig[pos_neg]
    Y = Y_orig[pos_neg]
    Y = tweak_labels(Y, ["positive"])
    train_model(get_best_model(), X, Y, name="pos vs neg", plot=True)

    print "== Pos/neg vs. irrelevant/neutral =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["positive", "negative"])

    # best_clf = grid_search_model(create_ngram_model, X, Y, name="sent vs
    # rest", plot=True)
    train_model(get_best_model(), X, Y, name="pos vs neg", plot=True)

    print "== Pos vs. rest =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["positive"])
    train_model(get_best_model(), X, Y, name="pos vs rest",
                plot=True)

    print "== Neg vs. rest =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["negative"])
    train_model(get_best_model(), X, Y, name="neg vs rest",
                plot=True)

    print "time spent:", time.time() - start_time

########NEW FILE########
__FILENAME__ = 03_clean
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

#
# This script tries to improve the classifier by cleaning the tweets a bit
#

import time
start_time = time.time()
import re

import numpy as np

from sklearn.metrics import precision_recall_curve, roc_curve, auc
from sklearn.cross_validation import ShuffleSplit
from sklearn.pipeline import Pipeline

from utils import plot_pr
from utils import load_sanders_data
from utils import tweak_labels
from utils import log_false_positives

from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.naive_bayes import MultinomialNB

from utils import load_sent_word_net

sent_word_net = load_sent_word_net()

phase = "03"

emo_repl = {
    # positive emoticons
    "&lt;3": " good ",
    ":d": " good ",  # :D in lower case
    ":dd": " good ",  # :DD in lower case
    "8)": " good ",
    ":-)": " good ",
    ":)": " good ",
    ";)": " good ",
    "(-:": " good ",
    "(:": " good ",

    # negative emoticons:
    ":/": " bad ",
    ":&gt;": " sad ",
    ":')": " sad ",
    ":-(": " bad ",
    ":(": " bad ",
    ":S": " bad ",
    ":-S": " bad ",
}

emo_repl_order = [k for (k_len, k) in reversed(
    sorted([(len(k), k) for k in emo_repl.keys()]))]

re_repl = {
    r"\br\b": "are",
    r"\bu\b": "you",
    r"\bhaha\b": "ha",
    r"\bhahaha\b": "ha",
    r"\bdon't\b": "do not",
    r"\bdoesn't\b": "does not",
    r"\bdidn't\b": "did not",
    r"\bhasn't\b": "has not",
    r"\bhaven't\b": "have not",
    r"\bhadn't\b": "had not",
    r"\bwon't\b": "will not",
    r"\bwouldn't\b": "would not",
    r"\bcan't\b": "can not",
    r"\bcannot\b": "can not",
}


def create_ngram_model(params=None):
    def preprocessor(tweet):
        global emoticons_replaced
        tweet = tweet.lower()

        for k in emo_repl_order:
            tweet = tweet.replace(k, emo_repl[k])
        for r, repl in re_repl.iteritems():
            tweet = re.sub(r, repl, tweet)

        return tweet

    tfidf_ngrams = TfidfVectorizer(preprocessor=preprocessor,
                                   analyzer="word")
    clf = MultinomialNB()
    pipeline = Pipeline([('tfidf', tfidf_ngrams), ('clf', clf)])

    if params:
        pipeline.set_params(**params)

    return pipeline


def train_model(clf, X, Y, name="NB ngram", plot=False):
    # create it again for plotting
    cv = ShuffleSplit(
        n=len(X), n_iter=10, test_size=0.3, indices=True, random_state=0)

    train_errors = []
    test_errors = []

    scores = []
    pr_scores = []
    precisions, recalls, thresholds = [], [], []

    clfs = []  # just to later get the median

    for train, test in cv:
        X_train, y_train = X[train], Y[train]
        X_test, y_test = X[test], Y[test]

        clf.fit(X_train, y_train)
        clfs.append(clf)

        train_score = clf.score(X_train, y_train)
        test_score = clf.score(X_test, y_test)

        train_errors.append(1 - train_score)
        test_errors.append(1 - test_score)

        scores.append(test_score)
        proba = clf.predict_proba(X_test)

        fpr, tpr, roc_thresholds = roc_curve(y_test, proba[:, 1])
        precision, recall, pr_thresholds = precision_recall_curve(
            y_test, proba[:, 1])

        pr_scores.append(auc(recall, precision))
        precisions.append(precision)
        recalls.append(recall)
        thresholds.append(pr_thresholds)

    if plot:
        scores_to_sort = pr_scores
        median = np.argsort(scores_to_sort)[len(scores_to_sort) / 2]

        plot_pr(pr_scores[median], name, phase, precisions[median],
                recalls[median], label=name)

        log_false_positives(clfs[median], X_test, y_test, name)

    summary = (np.mean(scores), np.std(scores),
               np.mean(pr_scores), np.std(pr_scores))
    print "%.3f\t%.3f\t%.3f\t%.3f\t" % summary

    return np.mean(train_errors), np.mean(test_errors)


def print_incorrect(clf, X, Y):
    Y_hat = clf.predict(X)
    wrong_idx = Y_hat != Y
    X_wrong = X[wrong_idx]
    Y_wrong = Y[wrong_idx]
    Y_hat_wrong = Y_hat[wrong_idx]
    for idx in xrange(len(X_wrong)):
        print "clf.predict('%s')=%i instead of %i" %\
            (X_wrong[idx], Y_hat_wrong[idx], Y_wrong[idx])


def get_best_model():
    best_params = dict(tfidf__ngram_range=(1, 2),
                       tfidf__min_df=1,
                       tfidf__stop_words=None,
                       tfidf__smooth_idf=False,
                       tfidf__use_idf=False,
                       tfidf__sublinear_tf=True,
                       tfidf__binary=False,
                       clf__alpha=0.01,
                       )

    best_clf = create_ngram_model(best_params)

    return best_clf

if __name__ == "__main__":
    X_orig, Y_orig = load_sanders_data()
    classes = np.unique(Y_orig)
    for c in classes:
        print "#%s: %i" % (c, sum(Y_orig == c))

    print "== Pos vs. neg =="
    pos_neg = np.logical_or(Y_orig == "positive", Y_orig == "negative")
    X = X_orig[pos_neg]
    Y = Y_orig[pos_neg]
    Y = tweak_labels(Y, ["positive"])
    train_model(get_best_model(), X, Y, name="pos vs neg", plot=True)

    print "== Pos/neg vs. irrelevant/neutral =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["positive", "negative"])

    # best_clf = grid_search_model(create_union_model, X, Y, name="sent vs
    # rest", plot=True)
    train_model(get_best_model(), X, Y, name="pos+neg vs rest", plot=True)

    print "== Pos vs. rest =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["positive"])
    train_model(get_best_model(), X, Y, name="pos vs rest",
                plot=True)

    print "== Neg vs. rest =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["negative"])
    train_model(get_best_model(), X, Y, name="neg vs rest",
                plot=True)

    print "time spent:", time.time() - start_time

########NEW FILE########
__FILENAME__ = 04_sent
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

#
# This script trains tries to tweak hyperparameters to improve P/R AUC
#

import time
start_time = time.time()
import re

import nltk

import numpy as np

from sklearn.metrics import precision_recall_curve, roc_curve, auc
from sklearn.cross_validation import ShuffleSplit

from utils import plot_pr
from utils import load_sanders_data
from utils import tweak_labels
from utils import log_false_positives

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import f1_score
from sklearn.base import BaseEstimator

from sklearn.naive_bayes import MultinomialNB

from utils import load_sent_word_net

sent_word_net = load_sent_word_net()

phase = "04"

import json

poscache_filename = "poscache.json"
try:
    poscache = json.load(open(poscache_filename, "r"))
except IOError:
    poscache = {}


class LinguisticVectorizer(BaseEstimator):

    def get_feature_names(self):
        return np.array(['sent_neut', 'sent_pos', 'sent_neg',
                         'nouns', 'adjectives', 'verbs', 'adverbs',
                         'allcaps', 'exclamation', 'question'])

    def fit(self, documents, y=None):
        return self

    def _get_sentiments(self, d):
        # http://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
        sent = tuple(nltk.word_tokenize(d))
        if poscache is not None:
            if d in poscache:
                tagged = poscache[d]
            else:
                poscache[d] = tagged = nltk.pos_tag(sent)
        else:
            tagged = nltk.pos_tag(sent)

        pos_vals = []
        neg_vals = []

        nouns = 0.
        adjectives = 0.
        verbs = 0.
        adverbs = 0.

        for w, t in tagged:
            p, n = 0, 0
            sent_pos_type = None
            if t.startswith("NN"):
                sent_pos_type = "n"
                nouns += 1
            elif t.startswith("JJ"):
                sent_pos_type = "a"
                adjectives += 1
            elif t.startswith("VB"):
                sent_pos_type = "v"
                verbs += 1
            elif t.startswith("RB"):
                sent_pos_type = "r"
                adverbs += 1

            if sent_pos_type is not None:
                sent_word = "%s/%s" % (sent_pos_type, w)

                if sent_word in sent_word_net:
                    p, n = sent_word_net[sent_word]

            pos_vals.append(p)
            neg_vals.append(n)

        l = len(sent)
        avg_pos_val = np.mean(pos_vals)
        avg_neg_val = np.mean(neg_vals)

        return [1 - avg_pos_val - avg_neg_val, avg_pos_val, avg_neg_val,
                nouns / l, adjectives / l, verbs / l, adverbs / l]

    def transform(self, documents):
        obj_val, pos_val, neg_val, nouns, adjectives, verbs, adverbs = np.array(
            [self._get_sentiments(d) for d in documents]).T

        allcaps = []
        exclamation = []
        question = []

        for d in documents:
            allcaps.append(
                np.sum([t.isupper() for t in d.split() if len(t) > 2]))

            exclamation.append(d.count("!"))
            question.append(d.count("?"))

        result = np.array(
            [obj_val, pos_val, neg_val, nouns, adjectives, verbs, adverbs, allcaps,
             exclamation, question]).T

        return result

emo_repl = {
    # positive emoticons
    "&lt;3": " good ",
    ":d": " good ",  # :D in lower case
    ":dd": " good ",  # :DD in lower case
    "8)": " good ",
    ":-)": " good ",
    ":)": " good ",
    ";)": " good ",
    "(-:": " good ",
    "(:": " good ",

    # negative emoticons:
    ":/": " bad ",
    ":&gt;": " sad ",
    ":')": " sad ",
    ":-(": " bad ",
    ":(": " bad ",
    ":S": " bad ",
    ":-S": " bad ",
}

emo_repl_order = [k for (k_len, k) in reversed(
    sorted([(len(k), k) for k in emo_repl.keys()]))]

re_repl = {
    r"\br\b": "are",
    r"\bu\b": "you",
    r"\bhaha\b": "ha",
    r"\bhahaha\b": "ha",
    r"\bdon't\b": "do not",
    r"\bdoesn't\b": "does not",
    r"\bdidn't\b": "did not",
    r"\bhasn't\b": "has not",
    r"\bhaven't\b": "have not",
    r"\bhadn't\b": "had not",
    r"\bwon't\b": "will not",
    r"\bwouldn't\b": "would not",
    r"\bcan't\b": "can not",
    r"\bcannot\b": "can not",
}


def create_union_model(params=None):
    def preprocessor(tweet):
        tweet = tweet.lower()

        for k in emo_repl_order:
            tweet = tweet.replace(k, emo_repl[k])
        for r, repl in re_repl.iteritems():
            tweet = re.sub(r, repl, tweet)

        return tweet.replace("-", " ").replace("_", " ")

    tfidf_ngrams = TfidfVectorizer(preprocessor=preprocessor,
                                   analyzer="word")
    ling_stats = LinguisticVectorizer()
    all_features = FeatureUnion(
        [('ling', ling_stats), ('tfidf', tfidf_ngrams)])
    #all_features = FeatureUnion([('tfidf', tfidf_ngrams)])
    #all_features = FeatureUnion([('ling', ling_stats)])
    clf = MultinomialNB()
    pipeline = Pipeline([('all', all_features), ('clf', clf)])

    if params:
        pipeline.set_params(**params)

    return pipeline


def __grid_search_model(clf_factory, X, Y):
    cv = ShuffleSplit(
        n=len(X), n_iter=10, test_size=0.3, indices=True, random_state=0)

    param_grid = dict(vect__ngram_range=[(1, 1), (1, 2), (1, 3)],
                      vect__min_df=[1, 2],
                      vect__smooth_idf=[False, True],
                      vect__use_idf=[False, True],
                      vect__sublinear_tf=[False, True],
                      vect__binary=[False, True],
                      clf__alpha=[0, 0.01, 0.05, 0.1, 0.5, 1],
                      )

    grid_search = GridSearchCV(clf_factory(),
                               param_grid=param_grid,
                               cv=cv,
                               score_func=f1_score,
                               verbose=10)
    grid_search.fit(X, Y)
    clf = grid_search.best_estimator_
    print clf

    return clf


def train_model(clf, X, Y, name="NB ngram", plot=False):
    # create it again for plotting
    cv = ShuffleSplit(
        n=len(X), n_iter=10, test_size=0.3, indices=True, random_state=0)

    train_errors = []
    test_errors = []

    scores = []
    pr_scores = []
    precisions, recalls, thresholds = [], [], []

    clfs = []  # just to later get the median

    for train, test in cv:
        X_train, y_train = X[train], Y[train]
        X_test, y_test = X[test], Y[test]

        clf.fit(X_train, y_train)
        clfs.append(clf)

        train_score = clf.score(X_train, y_train)
        test_score = clf.score(X_test, y_test)

        train_errors.append(1 - train_score)
        test_errors.append(1 - test_score)

        scores.append(test_score)
        proba = clf.predict_proba(X_test)

        fpr, tpr, roc_thresholds = roc_curve(y_test, proba[:, 1])
        precision, recall, pr_thresholds = precision_recall_curve(
            y_test, proba[:, 1])

        pr_scores.append(auc(recall, precision))
        precisions.append(precision)
        recalls.append(recall)
        thresholds.append(pr_thresholds)

    if plot:
        scores_to_sort = pr_scores
        median = np.argsort(scores_to_sort)[len(scores_to_sort) / 2]

        plot_pr(pr_scores[median], name, phase, precisions[median],
                recalls[median], label=name)

        log_false_positives(clfs[median], X_test, y_test, name)

    summary = (np.mean(scores), np.std(scores),
               np.mean(pr_scores), np.std(pr_scores))
    print "%.3f\t%.3f\t%.3f\t%.3f\t" % summary

    return np.mean(train_errors), np.mean(test_errors)


def print_incorrect(clf, X, Y):
    Y_hat = clf.predict(X)
    wrong_idx = Y_hat != Y
    X_wrong = X[wrong_idx]
    Y_wrong = Y[wrong_idx]
    Y_hat_wrong = Y_hat[wrong_idx]
    for idx in xrange(len(X_wrong)):
        print "clf.predict('%s')=%i instead of %i" %\
            (X_wrong[idx], Y_hat_wrong[idx], Y_wrong[idx])


def get_best_model():
    best_params = dict(all__tfidf__ngram_range=(1, 2),
                       all__tfidf__min_df=1,
                       all__tfidf__stop_words=None,
                       all__tfidf__smooth_idf=False,
                       all__tfidf__use_idf=False,
                       all__tfidf__sublinear_tf=True,
                       all__tfidf__binary=False,
                       clf__alpha=0.01,
                       )

    best_clf = create_union_model(best_params)

    return best_clf

if __name__ == "__main__":
    X_orig, Y_orig = load_sanders_data()
    #from sklearn.utils import shuffle
    # print "shuffle, sample"
    #X_orig, Y_orig = shuffle(X_orig, Y_orig)
    #X_orig = X_orig[:100,]
    #Y_orig = Y_orig[:100,]
    classes = np.unique(Y_orig)
    for c in classes:
        print "#%s: %i" % (c, sum(Y_orig == c))

    print "== Pos vs. neg =="
    pos_neg = np.logical_or(Y_orig == "positive", Y_orig == "negative")
    X = X_orig[pos_neg]
    Y = Y_orig[pos_neg]
    Y = tweak_labels(Y, ["positive"])
    train_model(get_best_model(), X, Y, name="pos vs neg", plot=True)

    print "== Pos/neg vs. irrelevant/neutral =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["positive", "negative"])

    # best_clf = grid_search_model(create_union_model, X, Y, name="sent vs
    # rest", plot=True)
    train_model(get_best_model(), X, Y, name="pos+neg vs rest", plot=True)

    print "== Pos vs. rest =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["positive"])
    train_model(get_best_model(), X, Y, name="pos vs rest",
                plot=True)

    print "== Neg vs. rest =="
    X = X_orig
    Y = tweak_labels(Y_orig, ["negative"])
    train_model(get_best_model(), X, Y, name="neg vs rest",
                plot=True)

    print "time spent:", time.time() - start_time

    json.dump(poscache, open(poscache_filename, "w"))

########NEW FILE########
__FILENAME__ = install
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

#
# Sanders-Twitter Sentiment Corpus Install Script
# Version 0.1
#
# Pulls tweet data from Twitter because ToS prevents distributing it directly.
#
# Right now we use unauthenticated requests, which are rate-limited to 150/hr.
# We use 125/hr to stay safe.
#
#
#   - Niek Sanders
#     njs@sananalytics.com
#     October 20, 2011
#
#
# Excuse the ugly code.  I threw this together as quickly as possible and I
# don't normally code in Python.
#

# In Sanders' original form, the code was using Twitter API 1.0.
# Now that Twitter moved to 1.1, we had to make a few changes.
# Cf. twitterauth.py for the details.

import sys
import csv
import json
import os
import time

try:
    import twitter
except ImportError:
    print("""\
You need to install python-twitter:
    pip install python-twitter
If pip is not found you might have to install it using easy_install.
If it does not work on your system, you might want to follow instructions
at https://github.com/bear/python-twitter, most likely:
  $ git clone https://github.com/bear/python-twitter
  $ cd python-twitter
  $ sudo python setup.py install
""")

    sys.exit(1)

from twitterauth import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET
api = twitter.Api(consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET,
                  access_token_key=ACCESS_TOKEN_KEY, access_token_secret=ACCESS_TOKEN_SECRET)


MAX_TWEETS_PER_HR = 350

DATA_PATH = "data"

# for some reasons TWeets disappear. In this file we collect those
MISSING_ID_FILE = os.path.join(DATA_PATH, "missing.tsv")
NOT_AUTHORIZED_ID_FILE = os.path.join(DATA_PATH, "not_authorized.tsv")


def get_user_params(DATA_PATH):

    user_params = {}

    # get user input params
    user_params['inList'] = os.path.join(DATA_PATH, 'corpus.csv')
    user_params['outList'] = os.path.join(DATA_PATH, 'full-corpus.csv')
    user_params['rawDir'] = os.path.join(DATA_PATH, 'rawdata/')

    # apply defaults
    if user_params['inList'] == '':
        user_params['inList'] = './corpus.csv'
    if user_params['outList'] == '':
        user_params['outList'] = './full-corpus.csv'
    if user_params['rawDir'] == '':
        user_params['rawDir'] = './rawdata/'

    return user_params


def dump_user_params(user_params):

    # dump user params for confirmation
    print 'Input:    ' + user_params['inList']
    print 'Output:   ' + user_params['outList']
    print 'Raw data: ' + user_params['rawDir']
    return


def read_total_list(in_filename):

    # read total fetch list csv
    fp = open(in_filename, 'rb')
    reader = csv.reader(fp, delimiter=',', quotechar='"')

    if os.path.exists(MISSING_ID_FILE):
        missing_ids = [line.strip()
                       for line in open(MISSING_ID_FILE, "r").readlines()]
    else:
        missing_ids = []

    if os.path.exists(NOT_AUTHORIZED_ID_FILE):
        not_authed_ids = [line.strip()
                          for line in open(NOT_AUTHORIZED_ID_FILE, "r").readlines()]
    else:
        not_authed_ids = []

    print "We will skip %i tweets that are not available/visible any more on twitter" % (len(missing_ids) + len(not_authed_ids))

    ignore_ids = set(missing_ids + not_authed_ids)
    total_list = []
    for row in reader:
        if row[2] not in ignore_ids:
            total_list.append(row)

    return total_list


def purge_already_fetched(fetch_list, raw_dir):

    # list of tweet ids that still need downloading
    rem_list = []
    count_done = 0

    # check each tweet to see if we have it
    for item in fetch_list:

        # check if json file exists
        tweet_file = os.path.join(raw_dir, item[2] + '.json')
        if os.path.exists(tweet_file):

            # attempt to parse json file
            try:
                parse_tweet_json(tweet_file)
                count_done += 1
            except RuntimeError:
                print "Error parsing", item
                rem_list.append(item)
        else:
            rem_list.append(item)

    print "We have already downloaded %i tweets." % count_done

    return rem_list


def download_tweets(fetch_list, raw_dir):

    # ensure raw data directory exists
    if not os.path.exists(raw_dir):
        os.mkdir(raw_dir)

    # stay within rate limits
    download_pause_sec = 3600 / MAX_TWEETS_PER_HR

    # download tweets
    for idx in range(0, len(fetch_list)):
        # stay in Twitter API rate limits
        print 'Pausing %d sec to obey Twitter API rate limits' % \
              (download_pause_sec)
        time.sleep(download_pause_sec)

        # current item
        item = fetch_list[idx]
        print item

        # print status
        print '--> downloading tweet #%s (%d of %d)' % \
              (item[2], idx + 1, len(fetch_list))

        # Old Twitter API 1.0
        # pull data
        # url = 'https://api.twitter.com/1/statuses/show.json?id=' + item[2]
        # print url
        # urllib.urlretrieve(url, raw_dir + item[2] + '.json')

        # New Twitter API 1.1
        try:
            sec = api.GetSleepTime('/statuses/show/:id')
            if sec > 0:
                print "Sleeping %i seconds to conform to Twitter's rate limiting" % sec
                time.sleep(sec)

            result = api.GetStatus(item[2])
            json_data = result.AsJsonString()

        except twitter.TwitterError, e:
            fatal = True
            for m in e.message:
                if m['code'] == 34:
                    print "Tweet missing: ", item
                    # [{u'message': u'Sorry, that page does not exist', u'code': 34}]
                    with open(MISSING_ID_FILE, "a") as f:
                        f.write(item[2] + "\n")

                    fatal = False
                    break
                elif m['code'] == 63:
                    print "User of tweet '%s' has been suspended." % item
                    # [{u'message': u'Sorry, that page does not exist', u'code': 34}]
                    with open(MISSING_ID_FILE, "a") as f:
                        f.write(item[2] + "\n")

                    fatal = False
                    break
                elif m['code'] == 88:
                    print "Rate limit exceeded. Please lower max_tweets_per_hr."
                    fatal = True
                    break
                elif m['code'] == 179:
                    print "Not authorized to view this tweet."
                    with open(NOT_AUTHORIZED_ID_FILE, "a") as f:
                        f.write(item[2] + "\n")
                    fatal = False
                    break

            if fatal:
                raise
            else:
                continue

        with open(raw_dir + item[2] + '.json', "w") as f:
            f.write(json_data + "\n")

    return


def parse_tweet_json(filename):

    # read tweet
    fp = open(filename, 'rb')

    # parse json
    try:
        tweet_json = json.load(fp)
    except ValueError:
        raise RuntimeError('error parsing json')

    # look for twitter api error msgs
    if 'error' in tweet_json or 'errors' in tweet_json:
        raise RuntimeError('error in downloaded tweet')

    # extract creation date and tweet text
    return [tweet_json['created_at'], tweet_json['text']]


def build_output_corpus(out_filename, raw_dir, total_list):

    # open csv output file
    fp = open(out_filename, 'wb')
    writer = csv.writer(fp, delimiter=',', quotechar='"', escapechar='\\',
                        quoting=csv.QUOTE_ALL)

    # write header row
    writer.writerow(
        ['Topic', 'Sentiment', 'TweetId', 'TweetDate', 'TweetText'])

    # parse all downloaded tweets
    missing_count = 0
    for item in total_list:

        # ensure tweet exists
        if os.path.exists(raw_dir + item[2] + '.json'):

            try:
                # parse tweet
                parsed_tweet = parse_tweet_json(raw_dir + item[2] + '.json')
                full_row = item + parsed_tweet

                # character encoding for output
                for i in range(0, len(full_row)):
                    full_row[i] = full_row[i].encode("utf-8")

                # write csv row
                writer.writerow(full_row)

            except RuntimeError:
                print '--> bad data in tweet #' + item[2]
                missing_count += 1

        else:
            print '--> missing tweet #' + item[2]
            missing_count += 1

    # indicate success
    if missing_count == 0:
        print '\nSuccessfully downloaded corpus!'
        print 'Output in: ' + out_filename + '\n'
    else:
        print '\nMissing %d of %d tweets!' % (missing_count, len(total_list))
        print 'Partial output in: ' + out_filename + '\n'

    return


def main():
    # get user parameters
    user_params = get_user_params(DATA_PATH)
    print user_params
    dump_user_params(user_params)

    # get fetch list
    total_list = read_total_list(user_params['inList'])

    # remove already fetched or missing tweets
    fetch_list = purge_already_fetched(total_list, user_params['rawDir'])
    print "Fetching %i tweets..." % len(fetch_list)

    if fetch_list:
        # start fetching data from twitter
        download_tweets(fetch_list, user_params['rawDir'])

        # second pass for any failed downloads
        fetch_list = purge_already_fetched(total_list, user_params['rawDir'])
        if fetch_list:
            print '\nStarting second pass to retry %i failed downloads...' % len(fetch_list)
            download_tweets(fetch_list, user_params['rawDir'])
    else:
        print "Nothing to fetch any more."

    # build output corpus
    build_output_corpus(user_params['outList'], user_params['rawDir'],
                        total_list)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = twitterauth
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import sys

CONSUMER_KEY = None
CONSUMER_SECRET = None

ACCESS_TOKEN_KEY = None
ACCESS_TOKEN_SECRET = None

if CONSUMER_KEY is None or CONSUMER_SECRET is None or ACCESS_TOKEN_KEY is None or ACCESS_TOKEN_SECRET is None:
    print("""\
When doing last code sanity checks for the book, Twitter
was using the API 1.0, which did not require authentication.
With its switch to version 1.1, this has now changed.

It seems that you don't have already created your personal Twitter
access keys and tokens. Please do so at
https://dev.twitter.com/docs/auth/tokens-devtwittercom
and paste the keys/secrets into twitterauth.py

Sorry for the inconvenience,
The authors.""")

    sys.exit(1)

########NEW FILE########
__FILENAME__ = utils
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os
import collections
import csv
import json

from matplotlib import pylab
import numpy as np


DATA_DIR = "data"
CHART_DIR = "charts"

if not os.path.exists(DATA_DIR):
    raise RuntimeError("Expecting directory 'data' in current path")

if not os.path.exists(CHART_DIR):
    os.mkdir(CHART_DIR)


def tweak_labels(Y, pos_sent_list):
    pos = Y == pos_sent_list[0]
    for sent_label in pos_sent_list[1:]:
        pos |= Y == sent_label

    Y = np.zeros(Y.shape[0])
    Y[pos] = 1
    Y = Y.astype(int)

    return Y


def load_sanders_data(dirname=".", line_count=-1):
    count = 0

    topics = []
    labels = []
    tweets = []

    with open(os.path.join(DATA_DIR, dirname, "corpus.csv"), "r") as csvfile:
        metareader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for line in metareader:
            count += 1
            if line_count > 0 and count > line_count:
                break

            topic, label, tweet_id = line

            tweet_fn = os.path.join(
                DATA_DIR, dirname, 'rawdata', '%s.json' % tweet_id)
            try:
                tweet = json.load(open(tweet_fn, "r"))
            except IOError:
                print("Tweet '%s' not found. Skip."%tweet_fn)
                continue

            if 'text' in tweet and tweet['user']['lang'] == "en":
                topics.append(topic)
                labels.append(label)
                tweets.append(tweet['text'])

    tweets = np.asarray(tweets)
    labels = np.asarray(labels)

    return tweets, labels


def plot_pr(auc_score, name, phase, precision, recall, label=None):
    pylab.clf()
    pylab.figure(num=None, figsize=(5, 4))
    pylab.grid(True)
    pylab.fill_between(recall, precision, alpha=0.5)
    pylab.plot(recall, precision, lw=1)
    pylab.xlim([0.0, 1.0])
    pylab.ylim([0.0, 1.0])
    pylab.xlabel('Recall')
    pylab.ylabel('Precision')
    pylab.title('P/R curve (AUC=%0.2f) / %s' % (auc_score, label))
    filename = name.replace(" ", "_")
    pylab.savefig(os.path.join(CHART_DIR, "pr_%s_%s.png" %
                  (filename, phase)), bbox_inches="tight")


def show_most_informative_features(vectorizer, clf, n=20):
    c_f = sorted(zip(clf.coef_[0], vectorizer.get_feature_names()))
    top = zip(c_f[:n], c_f[:-(n + 1):-1])
    for (c1, f1), (c2, f2) in top:
        print "\t%.4f\t%-15s\t\t%.4f\t%-15s" % (c1, f1, c2, f2)


def plot_log():
    pylab.clf()
    pylab.figure(num=None, figsize=(6, 5))

    x = np.arange(0.001, 1, 0.001)
    y = np.log(x)

    pylab.title('Relationship between probabilities and their logarithm')
    pylab.plot(x, y)
    pylab.grid(True)
    pylab.xlabel('P')
    pylab.ylabel('log(P)')
    filename = 'log_probs.png'
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


def plot_feat_importance(feature_names, clf, name):
    pylab.clf()
    coef_ = clf.coef_
    important = np.argsort(np.absolute(coef_.ravel()))
    f_imp = feature_names[important]
    coef = coef_.ravel()[important]
    inds = np.argsort(coef)
    f_imp = f_imp[inds]
    coef = coef[inds]
    xpos = np.array(range(len(coef)))
    pylab.bar(xpos, coef, width=1)

    pylab.title('Feature importance for %s' % (name))
    ax = pylab.gca()
    ax.set_xticks(np.arange(len(coef)))
    labels = ax.set_xticklabels(f_imp)
    for label in labels:
        label.set_rotation(90)
    filename = name.replace(" ", "_")
    pylab.savefig(os.path.join(
        CHART_DIR, "feat_imp_%s.png" % filename), bbox_inches="tight")


def plot_feat_hist(data_name_list, filename=None):
    pylab.clf()
    num_rows = 1 + (len(data_name_list) - 1) / 2
    num_cols = 1 if len(data_name_list) == 1 else 2
    pylab.figure(figsize=(5 * num_cols, 4 * num_rows))

    for i in range(num_rows):
        for j in range(num_cols):
            pylab.subplot(num_rows, num_cols, 1 + i * num_cols + j)
            x, name = data_name_list[i * num_cols + j]
            pylab.title(name)
            pylab.xlabel('Value')
            pylab.ylabel('Density')
            # the histogram of the data
            max_val = np.max(x)
            if max_val <= 1.0:
                bins = 50
            elif max_val > 50:
                bins = 50
            else:
                bins = max_val
            n, bins, patches = pylab.hist(
                x, bins=bins, normed=1, facecolor='green', alpha=0.75)

            pylab.grid(True)

    if not filename:
        filename = "feat_hist_%s.png" % name

    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


def plot_bias_variance(data_sizes, train_errors, test_errors, name):
    pylab.clf()
    pylab.ylim([0.0, 1.0])
    pylab.xlabel('Data set size')
    pylab.ylabel('Error')
    pylab.title("Bias-Variance for '%s'" % name)
    pylab.plot(
        data_sizes, train_errors, "-", data_sizes, test_errors, "--", lw=1)
    pylab.legend(["train error", "test error"], loc="upper right")
    pylab.grid()
    pylab.savefig(os.path.join(CHART_DIR, "bv_" + name + ".png"))


def load_sent_word_net():

    sent_scores = collections.defaultdict(list)

    with open(os.path.join(DATA_DIR, "SentiWordNet_3.0.0_20130122.txt"), "r") as csvfile:
        reader = csv.reader(csvfile, delimiter='\t', quotechar='"')
        for line in reader:
            if line[0].startswith("#"):
                continue
            if len(line) == 1:
                continue

            POS, ID, PosScore, NegScore, SynsetTerms, Gloss = line
            if len(POS) == 0 or len(ID) == 0:
                continue
            # print POS,PosScore,NegScore,SynsetTerms
            for term in SynsetTerms.split(" "):
                # drop #number at the end of every term
                term = term.split("#")[0]
                term = term.replace("-", " ").replace("_", " ")
                key = "%s/%s" % (POS, term.split("#")[0])
                sent_scores[key].append((float(PosScore), float(NegScore)))
    for key, value in sent_scores.iteritems():
        sent_scores[key] = np.mean(value, axis=0)

    return sent_scores


def log_false_positives(clf, X, y, name):
    with open("FP_" + name.replace(" ", "_") + ".tsv", "w") as f:
        false_positive = clf.predict(X) != y
        for tweet, false_class in zip(X[false_positive], y[false_positive]):
            f.write("%s\t%s\n" %
                    (false_class, tweet.encode("ascii", "ignore")))


if __name__ == '__main__':
    plot_log()

########NEW FILE########
__FILENAME__ = boston1
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

# This script shows an example of simple (ordinary) linear regression

import numpy as np
from sklearn.datasets import load_boston
import pylab as plt

boston = load_boston()
x = np.array([np.concatenate((v, [1])) for v in boston.data])
y = boston.target

# np.linal.lstsq implements least-squares linear regression
s, total_error, _, _ = np.linalg.lstsq(x, y)

rmse = np.sqrt(total_error[0] / len(x))
print('Residual: {}'.format(rmse))

# Plot the prediction versus real:
plt.plot(np.dot(x, s), boston.target, 'ro')

# Plot a diagonal (for reference):
plt.plot([0, 50], [0, 50], 'g-')
plt.xlabel('predicted')
plt.ylabel('real')
plt.show()

########NEW FILE########
__FILENAME__ = boston_cv10_penalized
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

# This script fits several forms of penalized regression

from __future__ import print_function
from sklearn.cross_validation import KFold
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.linear_model import ElasticNetCV, LassoCV, RidgeCV
import numpy as np
from sklearn.datasets import load_boston
boston = load_boston()
x = np.array([np.concatenate((v, [1])) for v in boston.data])
y = boston.target

for name, met in [
        ('elastic-net(.5)', ElasticNet(fit_intercept=True, alpha=0.5)),
        ('lasso(.5)', Lasso(fit_intercept=True, alpha=0.5)),
        ('ridge(.5)', Ridge(fit_intercept=True, alpha=0.5)),
]:
    # Fit on the whole data:
    met.fit(x, y)

    # Predict on the whole data:
    p = np.array([met.predict(xi) for xi in x])

    e = p - y
    # np.dot(e, e) == sum(ei**2 for ei in e) but faster
    total_error = np.dot(e, e)
    rmse_train = np.sqrt(total_error / len(p))

    # Now, we use 10 fold cross-validation to estimate generalization error
    kf = KFold(len(x), n_folds=10)
    err = 0
    for train, test in kf:
        met.fit(x[train], y[train])
        p = np.array([met.predict(xi) for xi in x[test]])
        e = p - y[test]
        err += np.dot(e, e)

    rmse_10cv = np.sqrt(err / len(x))
    print('Method: {}'.format(name))
    print('RMSE on training: {}'.format(rmse_train))
    print('RMSE on 10-fold CV: {}'.format(rmse_10cv))
    print()
    print()

########NEW FILE########
__FILENAME__ = cv10_lr
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from sklearn.cross_validation import KFold
from sklearn.linear_model import LinearRegression, ElasticNet
import numpy as np
from sklearn.datasets import load_boston
boston = load_boston()
x = np.array([np.concatenate((v, [1])) for v in boston.data])
y = boston.target
FIT_EN = False

if FIT_EN:
    model = ElasticNet(fit_intercept=True, alpha=0.5)
else:
    model = LinearRegression(fit_intercept=True)
model.fit(x, y)
p = np.array([model.predict(xi) for xi in x])
e = p - y
total_error = np.dot(e, e)
rmse_train = np.sqrt(total_error / len(p))

kf = KFold(len(x), n_folds=10)
err = 0
for train, test in kf:
    model.fit(x[train], y[train])
    p = np.array([model.predict(xi) for xi in x[test]])
    e = p - y[test]
    err += np.dot(e, e)

rmse_10cv = np.sqrt(err / len(x))
print('RMSE on training: {}'.format(rmse_train))
print('RMSE on 10-fold CV: {}'.format(rmse_10cv))

########NEW FILE########
__FILENAME__ = figure1
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from sklearn.datasets import load_boston
import pylab as plt
from mpltools import style
style.use('ggplot')

boston = load_boston()
plt.scatter(boston.data[:, 5], boston.target)
plt.xlabel("RM")
plt.ylabel("House Price")


x = boston.data[:, 5]
x = np.array([[v] for v in x])
y = boston.target

slope, res, _, _ = np.linalg.lstsq(x, y)
plt.plot([0, boston.data[:, 5].max() + 1],
         [0, slope * (boston.data[:, 5].max() + 1)], '-', lw=4)
plt.savefig('Figure1.png', dpi=150)

rmse = np.sqrt(res[0] / len(x))
print('Residual: {}'.format(rmse))

########NEW FILE########
__FILENAME__ = figure2
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from sklearn.datasets import load_boston
import pylab as plt
from mpltools import style
style.use('ggplot')

boston = load_boston()
plt.scatter(boston.data[:, 5], boston.target)
plt.xlabel("RM")
plt.ylabel("House Price")


x = boston.data[:, 5]
xmin = x.min()
xmax = x.max()
x = np.array([[v, 1] for v in x])
y = boston.target

(slope, bias), res, _, _ = np.linalg.lstsq(x, y)
plt.plot([xmin, xmax], [slope * xmin + bias, slope * xmax + bias], '-', lw=4)
plt.savefig('Figure2.png', dpi=150)

rmse = np.sqrt(res[0] / len(x))
print('Residual: {}'.format(rmse))

########NEW FILE########
__FILENAME__ = figure4
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from sklearn.linear_model import Lasso
import numpy as np
from sklearn.datasets import load_boston
import pylab as plt
from mpltools import style
style.use('ggplot')

boston = load_boston()
plt.scatter(boston.data[:, 5], boston.target)
plt.xlabel("RM")
plt.ylabel("House Price")


x = boston.data[:, 5]
xmin = x.min()
xmax = x.max()
x = np.array([[v, 1] for v in x])
y = boston.target

(slope, bias), res, _, _ = np.linalg.lstsq(x, y)
plt.plot([xmin, xmax], [slope * xmin + bias, slope * xmax + bias], ':', lw=4)

las = Lasso()
las.fit(x, y)
y0 = las.predict([xmin, 1])
y1 = las.predict([xmax, 1])
plt.plot([xmin, xmax], [y0, y1], '-', lw=4)
plt.savefig('Figure3.png', dpi=150)

########NEW FILE########
__FILENAME__ = lr10k
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from sklearn.datasets import load_svmlight_file
from sklearn.linear_model import ElasticNet, LinearRegression
data, target = load_svmlight_file('E2006.train')
lr = LinearRegression(fit_intercept=True)

from sklearn.cross_validation import KFold
kf = KFold(len(target), n_folds=10)
err = 0
for train, test in kf:
    lr.fit(data[train], target[train])
    p = map(lr.predict, data[test])
    p = np.array(p).ravel()
    e = p - target[test]
    err += np.dot(e, e)

rmse_10cv = np.sqrt(err / len(target))


lr.fit(data, target)
p = np.array(map(lr.predict, data))
p = p.ravel()
e = p - target
total_error = np.dot(e, e)
rmse_train = np.sqrt(total_error / len(p))


print('RMSE on training: {}'.format(rmse_train))
print('RMSE on 10-fold CV: {}'.format(rmse_10cv))

########NEW FILE########
__FILENAME__ = predict10k_en
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from sklearn.datasets import load_svmlight_file
from sklearn.cross_validation import KFold
from sklearn.linear_model import ElasticNet, LinearRegression

data, target = load_svmlight_file('data/E2006.train')

# Edit the lines below if you want to switch method:
# met = LinearRegression(fit_intercept=True)
met = ElasticNet(fit_intercept=True, alpha=.1)

kf = KFold(len(target), n_folds=10)
err = 0
for train, test in kf:
    met.fit(data[train], target[train])
    p = map(met.predict, data[test])
    p = np.array(p).ravel()
    e = p - target[test]
    err += np.dot(e, e)

rmse_10cv = np.sqrt(err / len(target))


met.fit(data, target)
p = np.array(map(met.predict, data))
p = p.ravel()
e = p - target
total_error = np.dot(e, e)
rmse_train = np.sqrt(total_error / len(p))


print('RMSE on training: {}'.format(rmse_train))
print('RMSE on 10-fold CV: {}'.format(rmse_10cv))

########NEW FILE########
__FILENAME__ = usermodel
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from scipy import sparse
from sklearn.linear_model import LassoCV, RidgeCV, ElasticNetCV
from sklearn.cross_validation import KFold

data = np.array([[int(tok) for tok in line.split('\t')[:3]]
                for line in open('data/ml-100k/u.data')])
ij = data[:, :2]
ij -= 1  # original data is in 1-based system
values = data[:, 2]
reviews = sparse.csc_matrix((values, ij.T)).astype(float)

reg = ElasticNetCV(fit_intercept=True, alphas=[
                   0.0125, 0.025, 0.05, .125, .25, .5, 1., 2., 4.])


def movie_norm(xc):
    '''Normalize per movie'''
    xc = xc.copy().toarray()
    # x1 is the mean of the positive items
    x1 = np.array([xi[xi > 0].mean() for xi in xc])
    x1 = np.nan_to_num(x1)

    for i in range(xc.shape[0]):
        xc[i] -= (xc[i] > 0) * x1[i]
    return xc, x1


def learn_for(i):
    u = reviews[i]
    us = np.delete(np.arange(reviews.shape[0]), i)
    ps, = np.where(u.toarray().ravel() > 0)
    x = reviews[us][:, ps].T
    y = u.data
    err = 0
    eb = 0
    kf = KFold(len(y), n_folds=4)
    for train, test in kf:
        xc, x1 = movie_norm(x[train])
        reg.fit(xc, y[train] - x1)

        xc, x1 = movie_norm(x[test])
        p = np.array([reg.predict(xi) for xi in xc]).ravel()
        e = (p + x1) - y[test]
        err += np.sum(e * e)
        eb += np.sum((y[train].mean() - y[test]) ** 2)
    return np.sqrt(err / float(len(y))), np.sqrt(eb / float(len(y)))

whole_data = []
for i in range(reviews.shape[0]):
    s = learn_for(i)
    print(s[0] < s[1])
    print(s)
    whole_data.append(s)

########NEW FILE########
__FILENAME__ = all_correlations
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np

# This is the version in the book:


def all_correlations(bait, target):
    '''
    corrs = all_correlations(bait, target)

    corrs[i] is the correlation between bait and target[i]
    '''
    return np.array(
        [np.corrcoef(bait, c)[0, 1]
         for c in target])

# This is a faster, but harder to read, implementation:


def all_correlations(y, X):
    '''
    Cs = all_correlations(y, X)

    Cs[i] = np.corrcoef(y, X[i])[0,1]
    '''
    X = np.asanyarray(X, float)
    y = np.asanyarray(y, float)
    xy = np.dot(X, y)
    y_ = y.mean()
    ys_ = y.std()
    x_ = X.mean(1)
    xs_ = X.std(1)
    n = float(len(y))
    ys_ += 1e-5  # Handle zeros in ys
    xs_ += 1e-5  # Handle zeros in x

    return (xy - x_ * y_ * n) / n / xs_ / ys_

########NEW FILE########
__FILENAME__ = apriori
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

def apriori(dataset, minsupport, maxsize):
    '''
    freqsets, baskets = apriori(dataset, minsupport, maxsize)

    Parameters
    ----------
    dataset : sequence of sequences
        input dataset
    minsupport : int
        Minimal support for frequent items
    maxsize : int
        Maximal size of frequent items to return

    Returns
    -------
    freqsets : sequence of sequences
    baskets : dictionary
    '''
    from collections import defaultdict

    baskets = defaultdict(list)
    pointers = defaultdict(list)
    for i, ds in enumerate(dataset):
        for ell in ds:
            pointers[ell].append(i)
            baskets[frozenset([ell])].append(i)
    pointers = dict([(k, frozenset(v)) for k, v in pointers.items()])
    baskets = dict([(k, frozenset(v)) for k, v in baskets.items()])

    valid = set(list(el)[0]
                for el, c in baskets.items() if (len(c) >= minsupport))
    dataset = [[el for el in ds if (el in valid)] for ds in dataset]
    dataset = [ds for ds in dataset if len(ds) > 1]
    dataset = map(frozenset, dataset)

    itemsets = [frozenset([v]) for v in valid]
    freqsets = []
    for i in range(maxsize - 1):
        print(len(itemsets))
        newsets = []
        for i, ell in enumerate(itemsets):
            ccounts = baskets[ell]
            for v_, pv in pointers.items():
                if v_ not in ell:
                    csup = (ccounts & pv)
                    if len(csup) >= minsupport:
                        new = frozenset(ell | set([v_]))
                        if new not in baskets:
                            newsets.append(new)
                            baskets[new] = csup
        freqsets.extend(itemsets)
        itemsets = newsets
    return freqsets, baskets


def association_rules(dataset, freqsets, baskets, minlift):
    '''
    for (antecendent, consequent, base, py_x, lift) in association_rules(dataset, freqsets, baskets, minlift):
        ...

    This function takes the returns from ``apriori``.

    Parameters
    ----------
    dataset : sequence of sequences
        input dataset
    freqsets : sequence of sequences
    baskets : dictionary
    minlift : int
        minimal lift of yielded rules
    '''
    nr_transactions = float(len(dataset))
    freqsets = [f for f in freqsets if len(f) > 1]
    for fset in freqsets:
        for f in fset:
            consequent = frozenset([f])
            antecendent = fset - consequent
            base = len(baskets[consequent]) / nr_transactions
            py_x = len(baskets[fset]) / float(len(baskets[antecendent]))
            lift = py_x / base
            if lift > minlift:
                yield (antecendent, consequent, base, py_x, lift)

########NEW FILE########
__FILENAME__ = apriori_example
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from apriori import apriori, association_rules
from gzip import GzipFile
dataset = [[int(tok) for tok in line.strip().split()]
           for line in GzipFile('retail.dat.gz')]
freqsets, baskets = apriori(dataset, 80, maxsize=5)
nr_transactions = float(len(dataset))
for ant, con, base, pyx, lift in association_rules(dataset, freqsets, baskets, 30):
    print('{} | {} | {} ({:%}) | {} | {} | {}'
          .format(ant, con, len(baskets[con]), len(baskets[con]) / nr_transactions, len(baskets[ant]), len(baskets[con | ant]), int(lift)))

########NEW FILE########
__FILENAME__ = apriori_naive
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from collections import defaultdict
from itertools import chain
from gzip import GzipFile
minsupport = 44

dataset = [[int(tok) for tok in line.strip().split()]
           for line in GzipFile('retail.dat.gz')]
dataset = dataset[::20]

counts = defaultdict(int)
for elem in chain(*dataset):
    counts[elem] += 1

valid = set(el for el, c in counts.items() if (c >= minsupport))
dataset = [[el for el in ds if (el in valid)] for ds in dataset]

dataset = [frozenset(ds) for ds in dataset if len(ds) > 1]

itemsets = [frozenset([v]) for v in valid]
allsets = [itemsets]
for i in range(16):
    print(len(itemsets))
    nextsets = []
    for i, ell in enumerate(itemsets):
        for v_ in valid:
            if v_ not in ell:
                c = (ell | set([v_]))
                if sum(1 for d in dataset if d.issuperset(c)) > minsupport:
                    nextsets.append(c)
    allsets.append(nextsets)
    itemsets = nextsets

########NEW FILE########
__FILENAME__ = histogram
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from collections import defaultdict
from itertools import chain
from gzip import GzipFile
dataset = [[int(tok) for tok in line.strip().split()]
           for line in GzipFile('retail.dat.gz')]
counts = defaultdict(int)
for elem in chain(*dataset):
    counts[elem] += 1
counts = np.array(list(counts.values()))
bins = [1, 2, 4, 8, 16, 32, 64, 128, 512]
print(' {0:11} | {1:12}'.format('Nr of baskets', 'Nr of products'))
print('--------------------------------')
for i in range(len(bins)):
    bot = bins[i]
    top = (bins[i + 1] if (i + 1) < len(bins) else 100000000000)
    print('  {0:4} - {1:3}   | {2:12}'.format(
        bot, (top if top < 1000 else ''), np.sum((counts >= bot) & (counts < top))))

########NEW FILE########
__FILENAME__ = corrneighbours
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from __future__ import print_function
from all_correlations import all_correlations
import numpy as np
from scipy import sparse
from load_ml100k import load
reviews = load()


def estimate_user(user, rest):
    bu = user > 0
    br = rest > 0
    ws = all_correlations(bu, br)
    selected = ws.argsort()[-100:]
    estimates = rest[selected].mean(0)
    estimates /= (.1 + br[selected].mean(0))
    return estimates


def train_test(user, rest):
    estimates = estimate_user(user, rest)
    bu = user > 0
    br = rest > 0
    err = estimates[bu] - user[bu]
    null = rest.mean(0)
    null /= (.1 + br.mean(0))
    nerr = null[bu] - user[bu]
    return np.dot(err, err), np.dot(nerr, nerr)


def cross_validate_all():
    err = []
    for i in xrange(reviews.shape[0]):
        err.append(
            train_test(reviews[i], np.delete(reviews, i, 0))
        )
    revs = (reviews > 0).sum(1)
    err = np.array(err)
    rmse = np.sqrt(err / revs[:, None])
    print(np.mean(rmse, 0))
    print(np.mean(rmse[revs > 60], 0))


def all_estimates(reviews):
    reviews = reviews.toarray()
    estimates = np.zeros_like(reviews)
    for i in xrange(reviews.shape[0]):
        estimates[i] = estimate_user(reviews[i], np.delete(reviews, i, 0))
    return estimates

########NEW FILE########
__FILENAME__ = figure3
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from load_ml100k import load
from matplotlib import pyplot as plt
data = load()
data = data.toarray()
plt.gray()
plt.imshow(data[:200, :200], interpolation='nearest')
plt.xlabel('User ID')
plt.ylabel('Film ID')
plt.savefig('../1400_08_03+.png')

########NEW FILE########
__FILENAME__ = load_ml100k
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from scipy import sparse


def load():
    data = np.array([[int(t) for t in line.split('\t')[:3]]
                    for line in open('data/ml-100k/u.data')])
    ij = data[:, :2]
    ij -= 1  # original data is in 1-based system
    values = data[:, 2]
    reviews = sparse.csc_matrix((values, ij.T)).astype(float)
    return reviews

########NEW FILE########
__FILENAME__ = similar_movie
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from __future__ import print_function
import numpy as np
from load_ml100k import load
from all_correlations import all_correlations


def nn_movie(ureviews, reviews, uid, mid, k=1):
    X = ureviews
    y = ureviews[mid].copy()
    y -= y.mean()
    y /= (y.std() + 1e-5)
    corrs = np.dot(X, y)
    likes = corrs.argsort()
    likes = likes[::-1]
    c = 0
    pred = 3.
    for ell in likes:
        if ell == mid:
            continue
        if reviews[uid, ell] > 0:
            pred = reviews[uid, ell]
            if c == k:
                return pred
            c += 1
    return pred


def all_estimates(reviews, k=1):
    reviews = reviews.astype(float)
    k -= 1
    nusers, nmovies = reviews.shape
    estimates = np.zeros_like(reviews)
    for u in range(nusers):
        ureviews = np.delete(reviews, u, 0)
        ureviews -= ureviews.mean(0)
        ureviews /= (ureviews.std(0) + 1e-4)
        ureviews = ureviews.T.copy()
        for m in np.where(reviews[u] > 0)[0]:
            estimates[u, m] = nn_movie(ureviews, reviews, u, m, k)
    return estimates

if __name__ == '__main__':
    reviews = load().toarray()
    estimates = all_estimates(reviews)
    error = (estimates - reviews)
    error **= 2
    error = error[reviews > 0]
    print(np.sqrt(error).mean())

########NEW FILE########
__FILENAME__ = stacked
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from __future__ import print_function
from sklearn.linear_model import LinearRegression
from load_ml100k import load
import numpy as np
import similar_movie
import usermodel
import corrneighbours

reviews = load()
reg = LinearRegression()
es = np.array([
    usermodel.all_estimates(reviews),
    corrneighbours.all_estimates(reviews),
    similar_movies.all_estimates(reviews),
])

reviews = reviews.toarray()


total_error = 0.0
coefficients = []
for u in xrange(reviews.shape[0]):
    es0 = np.delete(es, u, 1)
    r0 = np.delete(reviews, u, 0)
    X, Y = np.where(r0 > 0)
    X = es[:, X, Y]
    y = r0[r0 > 0]
    reg.fit(X.T, y)
    coefficients.append(reg.coef_)

    r0 = reviews[u]
    X = np.where(r0 > 0)
    p0 = reg.predict(es[:, u, X].squeeze().T)
    err0 = r0[r0 > 0] - p0
    total_error += np.dot(err0, err0)
    print(u)

########NEW FILE########
__FILENAME__ = stacked5
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from sklearn.linear_model import LinearRegression
from load_ml100k import load
import numpy as np
import similar_movie
import usermodel
import corrneighbours

sreviews = load()
reviews = sreviews.toarray()
reg = LinearRegression()
es = np.array([
    usermodel.all_estimates(sreviews),
    similar_movie.all_estimates(reviews, k=1),
    similar_movie.all_estimates(reviews, k=2),
    similar_movie.all_estimates(reviews, k=3),
    similar_movie.all_estimates(reviews, k=4),
    similar_movie.all_estimates(reviews, k=5),
])

total_error = 0.0
coefficients = []
for u in xrange(reviews.shape[0]):
    es0 = np.delete(es, u, 1)
    r0 = np.delete(reviews, u, 0)
    X, Y = np.where(r0 > 0)
    X = es[:, X, Y]
    y = r0[r0 > 0]
    reg.fit(X.T, y)
    coefficients.append(reg.coef_)

    r0 = reviews[u]
    X = np.where(r0 > 0)
    p0 = reg.predict(es[:, u, X].squeeze().T)
    err0 = r0[r0 > 0] - p0
    total_error += np.dot(err0, err0)
coefficients = np.array(coefficients)

########NEW FILE########
__FILENAME__ = usermodel
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from sklearn.linear_model import LassoCV, RidgeCV, ElasticNetCV
from sklearn.cross_validation import KFold
from load_ml100k import load


def learn_for(reviews, i):
    reg = ElasticNetCV(fit_intercept=True, alphas=[
                       0.0125, 0.025, 0.05, .125, .25, .5, 1., 2., 4.])
    u = reviews[i]
    us = range(reviews.shape[0])
    del us[i]
    ps, = np.where(u.toarray().ravel() > 0)
    x = reviews[us][:, ps].T
    y = u.data
    kf = KFold(len(y), n_folds=4)
    predictions = np.zeros(len(ps))
    for train, test in kf:
        xc = x[train].copy().toarray()
        x1 = np.array([xi[xi > 0].mean() for xi in xc])
        x1 = np.nan_to_num(x1)

        for i in xrange(xc.shape[0]):
            xc[i] -= (xc[i] > 0) * x1[i]

        reg.fit(xc, y[train] - x1)

        xc = x[test].copy().toarray()
        x1 = np.array([xi[xi > 0].mean() for xi in xc])
        x1 = np.nan_to_num(x1)

        for i in xrange(xc.shape[0]):
            xc[i] -= (xc[i] > 0) * x1[i]

        p = np.array(map(reg.predict, xc)).ravel()
        predictions[test] = p
    return predictions


def all_estimates(reviews):
    whole_data = []
    for i in xrange(reviews.shape[0]):
        s = learn_for(reviews, i)
        whole_data.append(s)
    return np.array(whole_data)

########NEW FILE########
__FILENAME__ = 01_fft_based_classifier
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from collections import defaultdict

from sklearn.metrics import precision_recall_curve, roc_curve
from sklearn.metrics import auc
from sklearn.cross_validation import ShuffleSplit

from sklearn.metrics import confusion_matrix

from utils import plot_pr, plot_roc, plot_confusion_matrix, GENRE_LIST, TEST_DIR

from fft import read_fft

genre_list = GENRE_LIST


def train_model(clf_factory, X, Y, name, plot=False):
    labels = np.unique(Y)

    cv = ShuffleSplit(
        n=len(X), n_iter=1, test_size=0.3, indices=True, random_state=0)

    train_errors = []
    test_errors = []

    scores = []
    pr_scores = defaultdict(list)
    precisions, recalls, thresholds = defaultdict(
        list), defaultdict(list), defaultdict(list)

    roc_scores = defaultdict(list)
    tprs = defaultdict(list)
    fprs = defaultdict(list)

    clfs = []  # just to later get the median

    cms = []

    for train, test in cv:
        X_train, y_train = X[train], Y[train]
        X_test, y_test = X[test], Y[test]

        clf = clf_factory()
        clf.fit(X_train, y_train)
        clfs.append(clf)

        train_score = clf.score(X_train, y_train)
        test_score = clf.score(X_test, y_test)
        scores.append(test_score)

        train_errors.append(1 - train_score)
        test_errors.append(1 - test_score)

        y_pred = clf.predict(X_test)
        cm = confusion_matrix(y_test, y_pred)
        cms.append(cm)

        for label in labels:
            y_label_test = np.asarray(y_test == label, dtype=int)
            proba = clf.predict_proba(X_test)
            proba_label = proba[:, label]

            precision, recall, pr_thresholds = precision_recall_curve(
                y_label_test, proba_label)
            pr_scores[label].append(auc(recall, precision))
            precisions[label].append(precision)
            recalls[label].append(recall)
            thresholds[label].append(pr_thresholds)

            fpr, tpr, roc_thresholds = roc_curve(y_label_test, proba_label)
            roc_scores[label].append(auc(fpr, tpr))
            tprs[label].append(tpr)
            fprs[label].append(fpr)

    if plot:
        for label in labels:
            print("Plotting %s"%genre_list[label])
            scores_to_sort = roc_scores[label]
            median = np.argsort(scores_to_sort)[len(scores_to_sort) / 2]

            desc = "%s %s" % (name, genre_list[label])
            plot_pr(pr_scores[label][median], desc, precisions[label][median],
                    recalls[label][median], label='%s vs rest' % genre_list[label])
            plot_roc(roc_scores[label][median], desc, tprs[label][median],
                     fprs[label][median], label='%s vs rest' % genre_list[label])

    all_pr_scores = np.asarray(pr_scores.values()).flatten()
    summary = (np.mean(scores), np.std(scores),
               np.mean(all_pr_scores), np.std(all_pr_scores))
    print("%.3f\t%.3f\t%.3f\t%.3f\t" % summary)

    return np.mean(train_errors), np.mean(test_errors), np.asarray(cms)


def create_model():
    from sklearn.linear_model.logistic import LogisticRegression
    clf = LogisticRegression()

    return clf


if __name__ == "__main__":
    X, y = read_fft(genre_list)

    train_avg, test_avg, cms = train_model(
        create_model, X, y, "Log Reg FFT", plot=True)

    cm_avg = np.mean(cms, axis=0)
    cm_norm = cm_avg / np.sum(cm_avg, axis=0)

    plot_confusion_matrix(cm_norm, genre_list, "fft",
                          "Confusion matrix of an FFT based classifier")

########NEW FILE########
__FILENAME__ = 02_ceps_based_classifier
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
from collections import defaultdict

from sklearn.metrics import precision_recall_curve, roc_curve
from sklearn.metrics import auc
from sklearn.cross_validation import ShuffleSplit

from sklearn.metrics import confusion_matrix

from utils import plot_roc, plot_confusion_matrix, GENRE_LIST, TEST_DIR

from ceps import read_ceps


genre_list = GENRE_LIST


def train_model(clf_factory, X, Y, name, plot=False):
    labels = np.unique(Y)

    cv = ShuffleSplit(
        n=len(X), n_iter=1, test_size=0.3, indices=True, random_state=0)

    train_errors = []
    test_errors = []

    scores = []
    pr_scores = defaultdict(list)
    precisions, recalls, thresholds = defaultdict(
        list), defaultdict(list), defaultdict(list)

    roc_scores = defaultdict(list)
    tprs = defaultdict(list)
    fprs = defaultdict(list)

    clfs = []  # just to later get the median

    cms = []

    for train, test in cv:
        X_train, y_train = X[train], Y[train]
        X_test, y_test = X[test], Y[test]

        clf = clf_factory()
        clf.fit(X_train, y_train)
        clfs.append(clf)

        train_score = clf.score(X_train, y_train)
        test_score = clf.score(X_test, y_test)
        scores.append(test_score)

        train_errors.append(1 - train_score)
        test_errors.append(1 - test_score)

        y_pred = clf.predict(X_test)
        cm = confusion_matrix(y_test, y_pred)
        cms.append(cm)

        for label in labels:
            y_label_test = np.asarray(y_test == label, dtype=int)
            proba = clf.predict_proba(X_test)
            proba_label = proba[:, label]

            precision, recall, pr_thresholds = precision_recall_curve(
                y_label_test, proba_label)
            pr_scores[label].append(auc(recall, precision))
            precisions[label].append(precision)
            recalls[label].append(recall)
            thresholds[label].append(pr_thresholds)

            fpr, tpr, roc_thresholds = roc_curve(y_label_test, proba_label)
            roc_scores[label].append(auc(fpr, tpr))
            tprs[label].append(tpr)
            fprs[label].append(fpr)

    if plot:
        for label in labels:
            print("Plotting %s"%genre_list[label])
            scores_to_sort = roc_scores[label]
            median = np.argsort(scores_to_sort)[len(scores_to_sort) / 2]

            desc = "%s %s" % (name, genre_list[label])
            plot_roc(roc_scores[label][median], desc, tprs[label][median],
                     fprs[label][median], label='%s vs rest' % genre_list[label])

    all_pr_scores = np.asarray(pr_scores.values()).flatten()
    summary = (np.mean(scores), np.std(scores),
               np.mean(all_pr_scores), np.std(all_pr_scores))
    print("%.3f\t%.3f\t%.3f\t%.3f\t" % summary)

    return np.mean(train_errors), np.mean(test_errors), np.asarray(cms)


def create_model():
    from sklearn.linear_model.logistic import LogisticRegression
    clf = LogisticRegression()

    return clf


if __name__ == "__main__":
    X, y = read_ceps(genre_list)

    train_avg, test_avg, cms = train_model(
        create_model, X, y, "Log Reg CEPS", plot=True)

    cm_avg = np.mean(cms, axis=0)
    cm_norm = cm_avg / np.sum(cm_avg, axis=0)

    plot_confusion_matrix(cm_norm, genre_list, "ceps",
                          "Confusion matrix of a CEPS based classifier")

########NEW FILE########
__FILENAME__ = ceps
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os
import glob
import sys

import numpy as np
import scipy
import scipy.io.wavfile
from scikits.talkbox.features import mfcc

from utils import GENRE_DIR


def write_ceps(ceps, fn):
    """
    Write the MFCC to separate files to speed up processing.
    """
    base_fn, ext = os.path.splitext(fn)
    data_fn = base_fn + ".ceps"
    np.save(data_fn, ceps)
    print "Written", data_fn


def create_ceps(fn):
    sample_rate, X = scipy.io.wavfile.read(fn)

    ceps, mspec, spec = mfcc(X)
    write_ceps(ceps, fn)


def read_ceps(genre_list, base_dir=GENRE_DIR):
    X = []
    y = []
    for label, genre in enumerate(genre_list):
        for fn in glob.glob(os.path.join(base_dir, genre, "*.ceps.npy")):
            ceps = np.load(fn)
            num_ceps = len(ceps)
            X.append(
                np.mean(ceps[int(num_ceps / 10):int(num_ceps * 9 / 10)], axis=0))
            y.append(label)

    return np.array(X), np.array(y)


if __name__ == "__main__":
    os.chdir(GENRE_DIR)
    glob_wav = os.path.join(sys.argv[1], "*.wav")
    print glob_wav
    for fn in glob.glob(glob_wav):
        create_ceps(fn)

########NEW FILE########
__FILENAME__ = fft
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import sys
import os
import glob

import numpy as np
import scipy
import scipy.io.wavfile

from utils import GENRE_DIR, CHART_DIR

import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter


def write_fft(fft_features, fn):
    """
    Write the FFT features to separate files to speed up processing.
    """
    base_fn, ext = os.path.splitext(fn)
    data_fn = base_fn + ".fft"

    np.save(data_fn, fft_features)
    print "Written", data_fn


def create_fft(fn):
    sample_rate, X = scipy.io.wavfile.read(fn)

    fft_features = abs(scipy.fft(X)[:1000])
    write_fft(fft_features, fn)


def read_fft(genre_list, base_dir=GENRE_DIR):
    X = []
    y = []
    for label, genre in enumerate(genre_list):
        genre_dir = os.path.join(base_dir, genre, "*.fft.npy")
        file_list = glob.glob(genre_dir)
        assert(file_list), genre_dir
        for fn in file_list:
            fft_features = np.load(fn)

            X.append(fft_features[:2000])
            y.append(label)

    return np.array(X), np.array(y)


def plot_wav_fft(wav_filename, desc=None):
    plt.clf()
    plt.figure(num=None, figsize=(6, 4))
    sample_rate, X = scipy.io.wavfile.read(wav_filename)
    spectrum = np.fft.fft(X)
    freq = np.fft.fftfreq(len(X), 1.0 / sample_rate)

    plt.subplot(211)
    num_samples = 200.0
    plt.xlim(0, num_samples / sample_rate)
    plt.xlabel("time [s]")
    plt.title(desc or wav_filename)
    plt.plot(np.arange(num_samples) / sample_rate, X[:num_samples])
    plt.grid(True)

    plt.subplot(212)
    plt.xlim(0, 5000)
    plt.xlabel("frequency [Hz]")
    plt.xticks(np.arange(5) * 1000)
    if desc:
        desc = desc.strip()
        fft_desc = desc[0].lower() + desc[1:]
    else:
        fft_desc = wav_filename
    plt.title("FFT of %s" % fft_desc)
    plt.plot(freq, abs(spectrum), linewidth=5)
    plt.grid(True)

    plt.tight_layout()

    rel_filename = os.path.split(wav_filename)[1]
    plt.savefig("%s_wav_fft.png" % os.path.splitext(rel_filename)[0],
                bbox_inches='tight')

    plt.show()


def plot_wav_fft_demo():
    plot_wav_fft("sine_a.wav", "400Hz sine wave")
    plot_wav_fft("sine_b.wav", "3,000Hz sine wave")
    plot_wav_fft("sine_mix.wav", "Mixed sine wave")


def plot_specgram(ax, fn):
    sample_rate, X = scipy.io.wavfile.read(fn)
    ax.specgram(X, Fs=sample_rate, xextent=(0, 30))


def plot_specgrams(base_dir=CHART_DIR):
    """
    Plot a bunch of spectrograms of wav files in different genres
    """
    plt.clf()
    genres = ["classical", "jazz", "country", "pop", "rock", "metal"]
    num_files = 3
    f, axes = plt.subplots(len(genres), num_files)

    for genre_idx, genre in enumerate(genres):
        for idx, fn in enumerate(glob.glob(os.path.join(GENRE_DIR, genre, "*.wav"))):
            if idx == num_files:
                break
            axis = axes[genre_idx, idx]
            axis.yaxis.set_major_formatter(EngFormatter())
            axis.set_title("%s song %i" % (genre, idx + 1))
            plot_specgram(axis, fn)

    specgram_file = os.path.join(base_dir, "Spectrogram_Genres.png")
    plt.savefig(specgram_file, bbox_inches="tight")

    plt.show()


if __name__ == "__main__":
    # for fn in glob.glob(os.path.join(sys.argv[1], "*.wav")):
    #    create_fft(fn)

    # plot_decomp()

    if len(sys.argv) > 1:
        plot_wav_fft(sys.argv[1], desc="some sample song")
    else:
        plot_wav_fft_demo()

    plot_specgrams()

########NEW FILE########
__FILENAME__ = utils
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os
import sys

from matplotlib import pylab
import numpy as np

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "data")

CHART_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "charts")

for d in [DATA_DIR, CHART_DIR]:
    if not os.path.exists(d):
        os.mkdir(d)

# Put your directory to the different music genres here
GENRE_DIR = None
GENRE_LIST = ["classical", "jazz", "country", "pop", "rock", "metal"]

# Put your directory to the test dir here
TEST_DIR = None

if GENRE_DIR is None or TEST_DIR is None:
    print("Please set GENRE_DIR and TEST_DIR in utils.py") 
    sys.exit(1)



def plot_confusion_matrix(cm, genre_list, name, title):
    pylab.clf()
    pylab.matshow(cm, fignum=False, cmap='Blues', vmin=0, vmax=1.0)
    ax = pylab.axes()
    ax.set_xticks(range(len(genre_list)))
    ax.set_xticklabels(genre_list)
    ax.xaxis.set_ticks_position("bottom")
    ax.set_yticks(range(len(genre_list)))
    ax.set_yticklabels(genre_list)
    pylab.title(title)
    pylab.colorbar()
    pylab.grid(False)
    pylab.show()
    pylab.xlabel('Predicted class')
    pylab.ylabel('True class')
    pylab.grid(False)
    pylab.savefig(
        os.path.join(CHART_DIR, "confusion_matrix_%s.png" % name), bbox_inches="tight")


def plot_pr(auc_score, name, precision, recall, label=None):
    pylab.clf()
    pylab.figure(num=None, figsize=(5, 4))
    pylab.grid(True)
    pylab.fill_between(recall, precision, alpha=0.5)
    pylab.plot(recall, precision, lw=1)
    pylab.xlim([0.0, 1.0])
    pylab.ylim([0.0, 1.0])
    pylab.xlabel('Recall')
    pylab.ylabel('Precision')
    pylab.title('P/R curve (AUC = %0.2f) / %s' % (auc_score, label))
    filename = name.replace(" ", "_")
    pylab.savefig(
        os.path.join(CHART_DIR, "pr_" + filename + ".png"), bbox_inches="tight")


def plot_roc(auc_score, name, tpr, fpr, label=None):
    pylab.clf()
    pylab.figure(num=None, figsize=(5, 4))
    pylab.grid(True)
    pylab.plot([0, 1], [0, 1], 'k--')
    pylab.plot(fpr, tpr)
    pylab.fill_between(fpr, tpr, alpha=0.5)
    pylab.xlim([0.0, 1.0])
    pylab.ylim([0.0, 1.0])
    pylab.xlabel('False Positive Rate')
    pylab.ylabel('True Positive Rate')
    pylab.title('ROC curve (AUC = %0.2f) / %s' %
                (auc_score, label), verticalalignment="bottom")
    pylab.legend(loc="lower right")
    filename = name.replace(" ", "_")
    pylab.savefig(
        os.path.join(CHART_DIR, "roc_" + filename + ".png"), bbox_inches="tight")


def show_most_informative_features(vectorizer, clf, n=20):
    c_f = sorted(zip(clf.coef_[0], vectorizer.get_feature_names()))
    top = zip(c_f[:n], c_f[:-(n + 1):-1])
    for (c1, f1), (c2, f2) in top:
        print "\t%.4f\t%-15s\t\t%.4f\t%-15s" % (c1, f1, c2, f2)


def plot_log():
    pylab.clf()

    x = np.arange(0.001, 1, 0.001)
    y = np.log(x)

    pylab.title('Relationship between probabilities and their logarithm')
    pylab.plot(x, y)
    pylab.grid(True)
    pylab.xlabel('P')
    pylab.ylabel('log(P)')
    filename = 'log_probs.png'
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


def plot_feat_importance(feature_names, clf, name):
    pylab.clf()
    coef_ = clf.coef_
    important = np.argsort(np.absolute(coef_.ravel()))
    f_imp = feature_names[important]
    coef = coef_.ravel()[important]
    inds = np.argsort(coef)
    f_imp = f_imp[inds]
    coef = coef[inds]
    xpos = np.array(range(len(coef)))
    pylab.bar(xpos, coef, width=1)

    pylab.title('Feature importance for %s' % (name))
    ax = pylab.gca()
    ax.set_xticks(np.arange(len(coef)))
    labels = ax.set_xticklabels(f_imp)
    for label in labels:
        label.set_rotation(90)
    filename = name.replace(" ", "_")
    pylab.savefig(os.path.join(
        CHART_DIR, "feat_imp_%s.png" % filename), bbox_inches="tight")


def plot_feat_hist(data_name_list, filename=None):
    pylab.clf()
    num_rows = 1 + (len(data_name_list) - 1) / 2
    num_cols = 1 if len(data_name_list) == 1 else 2
    pylab.figure(figsize=(5 * num_cols, 4 * num_rows))

    for i in range(num_rows):
        for j in range(num_cols):
            pylab.subplot(num_rows, num_cols, 1 + i * num_cols + j)
            x, name = data_name_list[i * num_cols + j]
            pylab.title(name)
            pylab.xlabel('Value')
            pylab.ylabel('Density')
            # the histogram of the data
            max_val = np.max(x)
            if max_val <= 1.0:
                bins = 50
            elif max_val > 50:
                bins = 50
            else:
                bins = max_val
            n, bins, patches = pylab.hist(
                x, bins=bins, normed=1, facecolor='green', alpha=0.75)

            pylab.grid(True)

    if not filename:
        filename = "feat_hist_%s.png" % name

    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


def plot_bias_variance(data_sizes, train_errors, test_errors, name):
    pylab.clf()
    pylab.ylim([0.0, 1.0])
    pylab.xlabel('Data set size')
    pylab.ylabel('Error')
    pylab.title("Bias-Variance for '%s'" % name)
    pylab.plot(
        data_sizes, train_errors, "-", data_sizes, test_errors, "--", lw=1)
    pylab.legend(["train error", "test error"], loc="upper right")
    pylab.grid(True)
    pylab.savefig(os.path.join(CHART_DIR, "bv_" + name + ".png"))

########NEW FILE########
__FILENAME__ = edginess
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
import mahotas as mh


def edginess_sobel(image):
    '''Measure the "edginess" of an image

    image should be a 2d numpy array (an image)

    Returns a floating point value which is higher the "edgier" the image is.

    '''
    edges = mh.sobel(image, just_filter=True)
    edges = edges.ravel()
    return np.sqrt(np.dot(edges, edges))

########NEW FILE########
__FILENAME__ = figure10
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
import mahotas as mh

# This little script just builds an image with two examples, side-by-side:

text = mh.imread("simple-dataset/text21.jpg")
scene = mh.imread("simple-dataset/scene00.jpg")
h, w, _ = text.shape
canvas = np.zeros((h, 2 * w + 128, 3), np.uint8)
canvas[:, -w:] = scene
canvas[:, :w] = text
canvas = canvas[::4, ::4]
mh.imsave('../1400OS_10_10+.jpg', canvas)

########NEW FILE########
__FILENAME__ = figure13
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import mahotas as mh
from mahotas.colors import rgb2grey
import numpy as np

# Adds a little salt-n-pepper noise to an image

im = mh.imread('lenna.jpg')
im = rgb2grey(im)

# Salt & pepper arrays
salt = np.random.random(im.shape) > .975
pepper = np.random.random(im.shape) > .975

# salt is 170 & pepper is 30
# Some playing around showed that setting these to more extreme values looks
# very artificial. These look nicer

im = np.maximum(salt * 170, mh.stretch(im))
im = np.minimum(pepper * 30 + im * (~pepper), im)

mh.imsave('../1400OS_10_13+.jpg', im.astype(np.uint8))

########NEW FILE########
__FILENAME__ = figure18
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import mahotas as mh
from sklearn import cross_validation
from sklearn.linear_model.logistic import LogisticRegression
from mpltools import style
from matplotlib import pyplot as plt
import numpy as np
from glob import glob

basedir = 'AnimTransDistr'


def features_for(images):
    fs = []
    for im in images:
        im = mh.imread(im, as_grey=True).astype(np.uint8)
        fs.append(mh.features.haralick(im).mean(0))
    return np.array(fs)


def features_labels(groups):
    labels = np.zeros(sum(map(len, groups)))
    st = 0
    for i, g in enumerate(groups):
        labels[st:st + len(g)] = i
        st += len(g)
    return np.vstack(groups), labels

classes = [
    'Anims',
    'Cars',
    'Distras',
    'Trans',
]

features = []
labels = []
for ci, cl in enumerate(classes):
    images = glob('{}/{}/*.jpg'.format(basedir, cl))
    features.extend(features_for(images))
    labels.extend([ci for _ in images])

features = np.array(features)
labels = np.array(labels)

scores0 = cross_validation.cross_val_score(
    LogisticRegression(), features, labels, cv=10)
print('Accuracy (5 fold x-val) with Logistic Regrssion [std features]: %s%%' % (
    0.1 * round(1000 * scores0.mean())))

tfeatures = features

from sklearn.cluster import KMeans
from mahotas.features import surf

images = []
labels = []

for ci, cl in enumerate(classes):
    curimages = glob('{}/{}/*.jpg'.format(basedir, cl))
    images.extend(curimages)
    labels.extend([ci for _ in curimages])
labels = np.array(labels)

alldescriptors = []
for im in images:
    im = mh.imread(im, as_grey=1)
    im = im.astype(np.uint8)

    #alldescriptors.append(surf.dense(im, spacing=max(im.shape)//32))
    alldescriptors.append(surf.surf(im, descriptor_only=True))

print('Descriptors done')
k = 256
km = KMeans(k)

concatenated = np.concatenate(alldescriptors)
concatenated = concatenated[::64]
print('k-meaning...')
km.fit(concatenated)
features = []
for d in alldescriptors:
    c = km.predict(d)
    features.append(
        np.array([np.sum(c == i) for i in xrange(k)])
    )
features = np.array(features)
print('predicting...')
scoreSURFlr = cross_validation.cross_val_score(
    LogisticRegression(), features, labels, cv=5).mean()
print('Accuracy (5 fold x-val) with Log. Reg [SURF features]: %s%%' % (
    0.1 * round(1000 * scoreSURFlr.mean())))

print('combined...')
allfeatures = np.hstack([features, tfeatures])
scoreSURFplr = cross_validation.cross_val_score(
    LogisticRegression(), allfeatures, labels, cv=5).mean()

print('Accuracy (5 fold x-val) with Log. Reg [All features]: %s%%' % (
    0.1 * round(1000 * scoreSURFplr.mean())))

style.use('ggplot')
plt.plot([0, 1, 2], 100 *
         np.array([scores0.mean(), scoreSURFlr, scoreSURFplr]), 'k-', lw=8)
plt.plot(
    [0, 1, 2], 100 * np.array([scores0.mean(), scoreSURFlr, scoreSURFplr]),
    'o', mec='#cccccc', mew=12, mfc='white')
plt.xlim(-.5, 2.5)
plt.ylim(scores0.mean() * 90., scoreSURFplr * 110)
plt.xticks([0, 1, 2], ["baseline", "SURF", "combined"])
plt.ylabel('Accuracy (%)')
plt.savefig('../1400OS_10_18+.png')

########NEW FILE########
__FILENAME__ = figure5_6
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from matplotlib import pyplot as plt
import numpy as np
import mahotas as mh
image = mh.imread('../1400OS_10_01.jpeg')
image = mh.colors.rgb2gray(image)
im8 = mh.gaussian_filter(image, 8)
im16 = mh.gaussian_filter(image, 16)
im32 = mh.gaussian_filter(image, 32)
h, w = im8.shape
canvas = np.ones((h, 3 * w + 256), np.uint8)
canvas *= 255
canvas[:, :w] = im8
canvas[:, w + 128:2 * w + 128] = im16
canvas[:, -w:] = im32
mh.imsave('../1400OS_10_05+.jpg', canvas[:, ::2])

im32 = mh.stretch(im32)
ot32 = mh.otsu(im32)
mh.imsave('../1400OS_10_06+.jpg', (im32 > ot32).astype(np.uint8) * 255)

########NEW FILE########
__FILENAME__ = figure9
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from matplotlib import pyplot as plt
import numpy as np
import mahotas as mh
image = mh.imread('../1400OS_10_01.jpeg')
image = mh.colors.rgb2gray(image, dtype=np.uint8)
image = image[::4, ::4]
thresh = mh.sobel(image)
filtered = mh.sobel(image, just_filter=True)

thresh = mh.dilate(thresh, np.ones((7, 7)))
filtered = mh.dilate(mh.stretch(filtered), np.ones((7, 7)))


h, w = thresh.shape
canvas = 255 * np.ones((h, w * 2 + 64), np.uint8)
canvas[:, :w] = thresh * 255
canvas[:, -w:] = filtered

mh.imsave('../1400OS_10_09+.jpg', canvas)

########NEW FILE########
__FILENAME__ = lenna-ring
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import mahotas as mh
import numpy as np

# Read in the image
im = mh.imread('lenna.jpg')

# This breaks up the image into RGB channels
r, g, b = im.transpose(2, 0, 1)
h, w = r.shape

# smooth the image per channel:
r12 = mh.gaussian_filter(r, 12.)
g12 = mh.gaussian_filter(g, 12.)
b12 = mh.gaussian_filter(b, 12.)

# build back the RGB image
im12 = mh.as_rgb(r12, g12, b12)

X, Y = np.mgrid[:h, :w]
X = X - h / 2.
Y = Y - w / 2.
X /= X.max()
Y /= Y.max()

# Array C will have the highest values in the center, fading out to the edges:

C = np.exp(-2. * (X ** 2 + Y ** 2))
C -= C.min()
C /= C.ptp()
C = C[:, :, None]

# The final result is sharp in the centre and smooths out to the borders:
ring = mh.stretch(im * C + (1 - C) * im12)
mh.imsave('lenna-ring.jpg', ring)

########NEW FILE########
__FILENAME__ = simple_classification
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import mahotas as mh
from sklearn import cross_validation
from sklearn.linear_model.logistic import LogisticRegression
import numpy as np
from glob import glob
from edginess import edginess_sobel

basedir = 'simple-dataset'


def features_for(im):
    im = mh.imread(im, as_grey=True).astype(np.uint8)
    return mh.features.haralick(im).mean(0)

features = []
sobels = []
labels = []
images = glob('{}/*.jpg'.format(basedir))
for im in images:
    features.append(features_for(im))
    sobels.append(edginess_sobel(mh.imread(im, as_grey=True)))
    labels.append(im[:-len('00.jpg')])

features = np.array(features)
labels = np.array(labels)

scores = cross_validation.cross_val_score(
    LogisticRegression(), features, labels, cv=5)
print('Accuracy (5 fold x-val) with Logistic Regrssion [std features]: {}%'.format(
    0.1 * round(1000 * scores.mean())))

scores = cross_validation.cross_val_score(
    LogisticRegression(), np.hstack([np.atleast_2d(sobels).T, features]), labels, cv=5).mean()
print('Accuracy (5 fold x-val) with Logistic Regrssion [std features + sobel]: {}%'.format(
    0.1 * round(1000 * scores.mean())))

########NEW FILE########
__FILENAME__ = threshold
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import numpy as np
import mahotas as mh
image = mh.imread('../1400OS_10_01.jpeg')
image = mh.colors.rgb2gray(image, dtype=np.uint8)
thresh = mh.thresholding.otsu(image)
print(thresh)
otsubin = (image > thresh)
mh.imsave('otsu-threshold.jpeg', otsubin.astype(np.uint8) * 255)
otsubin = ~ mh.close(~otsubin, np.ones((15, 15)))
mh.imsave('otsu-closed.jpeg', otsubin.astype(np.uint8) * 255)

thresh = mh.thresholding.rc(image)
print(thresh)
mh.imsave('rc-threshold.jpeg', (image > thresh).astype(np.uint8) * 255)

########NEW FILE########
__FILENAME__ = demo_corr
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os

from matplotlib import pylab
import numpy as np
import scipy
from scipy.stats import norm, pearsonr

from utils import CHART_DIR


def _plot_correlation_func(x, y):

    r, p = pearsonr(x, y)
    title = "Cor($X_1$, $X_2$) = %.3f" % r
    pylab.scatter(x, y)
    pylab.title(title)
    pylab.xlabel("$X_1$")
    pylab.ylabel("$X_2$")

    f1 = scipy.poly1d(scipy.polyfit(x, y, 1))
    pylab.plot(x, f1(x), "r--", linewidth=2)
    # pylab.xticks([w*7*24 for w in [0,1,2,3,4]], ['week %i'%(w+1) for w in
    # [0,1,2,3,4]])


def plot_correlation_demo():
    np.random.seed(0)  # to reproduce the data later on
    pylab.clf()
    pylab.figure(num=None, figsize=(8, 8))

    x = np.arange(0, 10, 0.2)

    pylab.subplot(221)
    y = 0.5 * x + norm.rvs(1, scale=.01, size=len(x))
    _plot_correlation_func(x, y)

    pylab.subplot(222)
    y = 0.5 * x + norm.rvs(1, scale=.1, size=len(x))
    _plot_correlation_func(x, y)

    pylab.subplot(223)
    y = 0.5 * x + norm.rvs(1, scale=1, size=len(x))
    _plot_correlation_func(x, y)

    pylab.subplot(224)
    y = norm.rvs(1, scale=10, size=len(x))
    _plot_correlation_func(x, y)

    pylab.autoscale(tight=True)
    pylab.grid(True)

    filename = "corr_demo_1.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")

    pylab.clf()
    pylab.figure(num=None, figsize=(8, 8))

    x = np.arange(-5, 5, 0.2)

    pylab.subplot(221)
    y = 0.5 * x ** 2 + norm.rvs(1, scale=.01, size=len(x))
    _plot_correlation_func(x, y)

    pylab.subplot(222)
    y = 0.5 * x ** 2 + norm.rvs(1, scale=.1, size=len(x))
    _plot_correlation_func(x, y)

    pylab.subplot(223)
    y = 0.5 * x ** 2 + norm.rvs(1, scale=1, size=len(x))
    _plot_correlation_func(x, y)

    pylab.subplot(224)
    y = 0.5 * x ** 2 + norm.rvs(1, scale=10, size=len(x))
    _plot_correlation_func(x, y)

    pylab.autoscale(tight=True)
    pylab.grid(True)

    filename = "corr_demo_2.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")

if __name__ == '__main__':
    plot_correlation_demo()

########NEW FILE########
__FILENAME__ = demo_mds
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os

import numpy as np
from matplotlib import pylab
from mpl_toolkits.mplot3d import Axes3D

from sklearn import linear_model, manifold, decomposition, datasets
logistic = linear_model.LogisticRegression()

from utils import CHART_DIR

np.random.seed(3)

# all examples will have three classes in this file
colors = ['r', 'g', 'b']
markers = ['o', 6, '*']


def plot_demo_1():
    X = np.c_[np.ones(5), 2 * np.ones(5), 10 * np.ones(5)].T
    y = np.array([0, 1, 2])

    fig = pylab.figure(figsize=(10, 4))

    ax = fig.add_subplot(121, projection='3d')
    ax.set_axis_bgcolor('white')

    mds = manifold.MDS(n_components=3)
    Xtrans = mds.fit_transform(X)

    for cl, color, marker in zip(np.unique(y), colors, markers):
        ax.scatter(
            Xtrans[y == cl][:, 0], Xtrans[y == cl][:, 1], Xtrans[y == cl][:, 2], c=color, marker=marker, edgecolor='black')
    pylab.title("MDS on example data set in 3 dimensions")
    ax.view_init(10, -15)

    mds = manifold.MDS(n_components=2)
    Xtrans = mds.fit_transform(X)

    ax = fig.add_subplot(122)
    for cl, color, marker in zip(np.unique(y), colors, markers):
        ax.scatter(
            Xtrans[y == cl][:, 0], Xtrans[y == cl][:, 1], c=color, marker=marker, edgecolor='black')
    pylab.title("MDS on example data set in 2 dimensions")

    filename = "mds_demo_1.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


def plot_iris_mds():

    iris = datasets.load_iris()
    X = iris.data
    y = iris.target

    # MDS

    fig = pylab.figure(figsize=(10, 4))

    ax = fig.add_subplot(121, projection='3d')
    ax.set_axis_bgcolor('white')

    mds = manifold.MDS(n_components=3)
    Xtrans = mds.fit_transform(X)

    for cl, color, marker in zip(np.unique(y), colors, markers):
        ax.scatter(
            Xtrans[y == cl][:, 0], Xtrans[y == cl][:, 1], Xtrans[y == cl][:, 2], c=color, marker=marker, edgecolor='black')
    pylab.title("MDS on Iris data set in 3 dimensions")
    ax.view_init(10, -15)

    mds = manifold.MDS(n_components=2)
    Xtrans = mds.fit_transform(X)

    ax = fig.add_subplot(122)
    for cl, color, marker in zip(np.unique(y), colors, markers):
        ax.scatter(
            Xtrans[y == cl][:, 0], Xtrans[y == cl][:, 1], c=color, marker=marker, edgecolor='black')
    pylab.title("MDS on Iris data set in 2 dimensions")

    filename = "mds_demo_iris.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")

    # PCA

    fig = pylab.figure(figsize=(10, 4))

    ax = fig.add_subplot(121, projection='3d')
    ax.set_axis_bgcolor('white')

    pca = decomposition.PCA(n_components=3)
    Xtrans = pca.fit(X).transform(X)

    for cl, color, marker in zip(np.unique(y), colors, markers):
        ax.scatter(
            Xtrans[y == cl][:, 0], Xtrans[y == cl][:, 1], Xtrans[y == cl][:, 2], c=color, marker=marker, edgecolor='black')
    pylab.title("PCA on Iris data set in 3 dimensions")
    ax.view_init(50, -35)

    pca = decomposition.PCA(n_components=2)
    Xtrans = pca.fit_transform(X)

    ax = fig.add_subplot(122)
    for cl, color, marker in zip(np.unique(y), colors, markers):
        ax.scatter(
            Xtrans[y == cl][:, 0], Xtrans[y == cl][:, 1], c=color, marker=marker, edgecolor='black')
    pylab.title("PCA on Iris data set in 2 dimensions")

    filename = "pca_demo_iris.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


if __name__ == '__main__':
    plot_demo_1()
    plot_iris_mds()

########NEW FILE########
__FILENAME__ = demo_mi
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os

from matplotlib import pylab
import numpy as np
from scipy.stats import norm, entropy

from utils import CHART_DIR


def mutual_info(x, y, bins=10):
    counts_xy, bins_x, bins_y = np.histogram2d(x, y, bins=(bins, bins))
    counts_x, bins = np.histogram(x, bins=bins)
    counts_y, bins = np.histogram(y, bins=bins)

    counts_xy += 1
    counts_x += 1
    counts_y += 1
    P_xy = counts_xy / np.sum(counts_xy, dtype=float)
    P_x = counts_x / np.sum(counts_x, dtype=float)
    P_y = counts_y / np.sum(counts_y, dtype=float)

    I_xy = np.sum(P_xy * np.log2(P_xy / (P_x.reshape(-1, 1) * P_y)))

    return I_xy / (entropy(counts_x) + entropy(counts_y))


def plot_entropy():
    pylab.clf()
    pylab.figure(num=None, figsize=(5, 4))

    title = "Entropy $H(X)$"
    pylab.title(title)
    pylab.xlabel("$P(X=$coin will show heads up$)$")
    pylab.ylabel("$H(X)$")

    pylab.xlim(xmin=0, xmax=1.1)
    x = np.arange(0.001, 1, 0.001)
    y = -x * np.log2(x) - (1 - x) * np.log2(1 - x)
    pylab.plot(x, y)
    # pylab.xticks([w*7*24 for w in [0,1,2,3,4]], ['week %i'%(w+1) for w in
    # [0,1,2,3,4]])

    pylab.autoscale(tight=True)
    pylab.grid(True)

    filename = "entropy_demo.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


def _plot_mi_func(x, y):

    mi = mutual_info(x, y)
    title = "NI($X_1$, $X_2$) = %.3f" % mi
    pylab.scatter(x, y)
    pylab.title(title)
    pylab.xlabel("$X_1$")
    pylab.ylabel("$X_2$")


def plot_mi_demo():
    np.random.seed(0)  # to reproduce the data later on
    pylab.clf()
    pylab.figure(num=None, figsize=(8, 8))

    x = np.arange(0, 10, 0.2)

    pylab.subplot(221)
    y = 0.5 * x + norm.rvs(1, scale=.01, size=len(x))
    _plot_mi_func(x, y)

    pylab.subplot(222)
    y = 0.5 * x + norm.rvs(1, scale=.1, size=len(x))
    _plot_mi_func(x, y)

    pylab.subplot(223)
    y = 0.5 * x + norm.rvs(1, scale=1, size=len(x))
    _plot_mi_func(x, y)

    pylab.subplot(224)
    y = norm.rvs(1, scale=10, size=len(x))
    _plot_mi_func(x, y)

    pylab.autoscale(tight=True)
    pylab.grid(True)

    filename = "mi_demo_1.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")

    pylab.clf()
    pylab.figure(num=None, figsize=(8, 8))

    x = np.arange(-5, 5, 0.2)

    pylab.subplot(221)
    y = 0.5 * x ** 2 + norm.rvs(1, scale=.01, size=len(x))
    _plot_mi_func(x, y)

    pylab.subplot(222)
    y = 0.5 * x ** 2 + norm.rvs(1, scale=.1, size=len(x))
    _plot_mi_func(x, y)

    pylab.subplot(223)
    y = 0.5 * x ** 2 + norm.rvs(1, scale=1, size=len(x))
    _plot_mi_func(x, y)

    pylab.subplot(224)
    y = 0.5 * x ** 2 + norm.rvs(1, scale=10, size=len(x))
    _plot_mi_func(x, y)

    pylab.autoscale(tight=True)
    pylab.grid(True)

    filename = "mi_demo_2.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")

if __name__ == '__main__':
    plot_entropy()
    plot_mi_demo()

########NEW FILE########
__FILENAME__ = demo_pca
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os

from matplotlib import pylab
import numpy as np

from sklearn import linear_model, decomposition
from sklearn import lda

logistic = linear_model.LogisticRegression()


from utils import CHART_DIR

np.random.seed(3)

x1 = np.arange(0, 10, .2)
x2 = x1 + np.random.normal(scale=1, size=len(x1))


def plot_simple_demo_1():
    pylab.clf()
    fig = pylab.figure(num=None, figsize=(10, 4))
    pylab.subplot(121)

    title = "Original feature space"
    pylab.title(title)
    pylab.xlabel("$X_1$")
    pylab.ylabel("$X_2$")

    x1 = np.arange(0, 10, .2)
    x2 = x1 + np.random.normal(scale=1, size=len(x1))

    good = (x1 > 5) | (x2 > 5)
    bad = ~good

    x1g = x1[good]
    x2g = x2[good]
    pylab.scatter(x1g, x2g, edgecolor="blue", facecolor="blue")

    x1b = x1[bad]
    x2b = x2[bad]
    pylab.scatter(x1b, x2b, edgecolor="red", facecolor="white")

    pylab.grid(True)

    pylab.subplot(122)

    X = np.c_[(x1, x2)]

    pca = decomposition.PCA(n_components=1)
    Xtrans = pca.fit_transform(X)

    Xg = Xtrans[good]
    Xb = Xtrans[bad]

    pylab.scatter(
        Xg[:, 0], np.zeros(len(Xg)), edgecolor="blue", facecolor="blue")
    pylab.scatter(
        Xb[:, 0], np.zeros(len(Xb)), edgecolor="red", facecolor="white")
    title = "Transformed feature space"
    pylab.title(title)
    pylab.xlabel("$X'$")
    fig.axes[1].get_yaxis().set_visible(False)

    print(pca.explained_variance_ratio_)

    pylab.grid(True)

    pylab.autoscale(tight=True)
    filename = "pca_demo_1.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


def plot_simple_demo_2():
    pylab.clf()
    fig = pylab.figure(num=None, figsize=(10, 4))
    pylab.subplot(121)

    title = "Original feature space"
    pylab.title(title)
    pylab.xlabel("$X_1$")
    pylab.ylabel("$X_2$")

    x1 = np.arange(0, 10, .2)
    x2 = x1 + np.random.normal(scale=1, size=len(x1))

    good = x1 > x2
    bad = ~good

    x1g = x1[good]
    x2g = x2[good]
    pylab.scatter(x1g, x2g, edgecolor="blue", facecolor="blue")

    x1b = x1[bad]
    x2b = x2[bad]
    pylab.scatter(x1b, x2b, edgecolor="red", facecolor="white")

    pylab.grid(True)

    pylab.subplot(122)

    X = np.c_[(x1, x2)]

    pca = decomposition.PCA(n_components=1)
    Xtrans = pca.fit_transform(X)

    Xg = Xtrans[good]
    Xb = Xtrans[bad]

    pylab.scatter(
        Xg[:, 0], np.zeros(len(Xg)), edgecolor="blue", facecolor="blue")
    pylab.scatter(
        Xb[:, 0], np.zeros(len(Xb)), edgecolor="red", facecolor="white")
    title = "Transformed feature space"
    pylab.title(title)
    pylab.xlabel("$X'$")
    fig.axes[1].get_yaxis().set_visible(False)

    print(pca.explained_variance_ratio_)

    pylab.grid(True)

    pylab.autoscale(tight=True)
    filename = "pca_demo_2.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")


def plot_simple_demo_lda():
    pylab.clf()
    fig = pylab.figure(num=None, figsize=(10, 4))
    pylab.subplot(121)

    title = "Original feature space"
    pylab.title(title)
    pylab.xlabel("$X_1$")
    pylab.ylabel("$X_2$")

    good = x1 > x2
    bad = ~good

    x1g = x1[good]
    x2g = x2[good]
    pylab.scatter(x1g, x2g, edgecolor="blue", facecolor="blue")

    x1b = x1[bad]
    x2b = x2[bad]
    pylab.scatter(x1b, x2b, edgecolor="red", facecolor="white")

    pylab.grid(True)

    pylab.subplot(122)

    X = np.c_[(x1, x2)]

    lda_inst = lda.LDA(n_components=1)
    Xtrans = lda_inst.fit_transform(X, good)

    Xg = Xtrans[good]
    Xb = Xtrans[bad]

    pylab.scatter(
        Xg[:, 0], np.zeros(len(Xg)), edgecolor="blue", facecolor="blue")
    pylab.scatter(
        Xb[:, 0], np.zeros(len(Xb)), edgecolor="red", facecolor="white")
    title = "Transformed feature space"
    pylab.title(title)
    pylab.xlabel("$X'$")
    fig.axes[1].get_yaxis().set_visible(False)

    pylab.grid(True)

    pylab.autoscale(tight=True)
    filename = "lda_demo.png"
    pylab.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")

if __name__ == '__main__':
    plot_simple_demo_1()
    plot_simple_demo_2()
    plot_simple_demo_lda()

########NEW FILE########
__FILENAME__ = demo_rfe
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from sklearn.feature_selection import RFE
from sklearn.linear_model import LogisticRegression

from sklearn.datasets import make_classification

X, y = make_classification(
    n_samples=100, n_features=10, n_informative=3, random_state=0)

clf = LogisticRegression()
clf.fit(X, y)

for i in range(1, 11):
    selector = RFE(clf, i)
    selector = selector.fit(X, y)
    print("%i\t%s\t%s" % (i, selector.support_, selector.ranking_))

########NEW FILE########
__FILENAME__ = utils
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

import os

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "data")

CHART_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "charts")

for d in [DATA_DIR, CHART_DIR]:
    if not os.path.exists(d):
        os.mkdir(d)


########NEW FILE########
__FILENAME__ = jugfile
# This code is supporting material for the book
# Building Machine Learning Systems with Python
# by Willi Richert and Luis Pedro Coelho
# published by PACKT Publishing
#
# It is made available under the MIT License

from jug import TaskGenerator
from time import sleep


@TaskGenerator
def double(x):
    sleep(4)
    return 2 * x


@TaskGenerator
def add(a, b):
    return a + b


@TaskGenerator
def print_final_result(oname, value):
    with open(oname, 'w') as output:
        print >>output, "Final result:", value

input = 2
y = double(input)
z = double(y)

y2 = double(7)
z2 = double(y2)
print_final_result('output.txt', add(z, z2))

########NEW FILE########
