__FILENAME__ = mmms
#!/usr/bin/env python
# encode: utf-8

# Active Learning for 20 newsgroups : MCMI[min] with margin sampling
#    MCMI[min] refers to (Guo+ IJCAI-07)
#    Yuhong Guo and Russ Greiner, Optimistic Active Learning using Mutual Information, IJCAI-07

# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import optparse
import numpy
import scipy.sparse
import sklearn.datasets
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

def activelearn(data, test, train, pool, classifier_factory, max_train, seed):
    numpy.random.seed(seed)

    # copy initial indexes of training and pool
    train = list(train)
    pool = list(pool)

    accuracies = []
    Z = len(test.target)
    K = data.target.max() + 1
    while len(train) < max_train:
        if len(accuracies) > 0:
            predict = classifier.predict_proba(data.data[pool,:])
            predict.sort(axis=1)
            margin = predict[:,-1] - predict[:,-2]
            candidate = margin.argsort()[:30]

            i_star = y_i_star = None
            f_i_star = 1e300
            print "i\ty_i\t(actual)\tf_i\tmargin"
            for i in candidate:
                x = pool[i]
                L_x_i = data.data[train + [x], :]
                L_y = data.target[train]
                entropies = numpy.zeros(K)
                for y in xrange(K):
                    l = list(L_y)
                    l.append(y)
                    phi_i = classifier_factory().fit(L_x_i, l)

                    p = phi_i.predict_proba(data.data[pool])
                    entropies[y] = -(numpy.nan_to_num(numpy.log(p)) * p).sum()
                y_i = entropies.argmin()
                f_i = entropies[y_i]
                print "%d\t%d\t%d\t%f\t%f" % (x, y_i, data.target[x], f_i, margin[i])
                if f_i < f_i_star:
                    i_star = i
                    y_i_star = y_i
                    f_i_star = f_i

            x = pool[i_star]
            print "select : %d (MM=%f, predict=%d, actual=%d)" % (x, f_i_star, y_i_star, data.target[x])
            train.append(x)
            del pool[i_star]

        classifier = classifier_factory().fit(data.data[train,:], data.target[train])
        accuracy = classifier.score(test.data, test.target)
        print "%d : %f" % (len(train), accuracy)
        accuracies.append((len(train), accuracy))

    return accuracies

def main():
    parser = optparse.OptionParser()
    parser.add_option("--nb", dest="naive_bayes", type="float", help="use naive bayes classifier", default=None)
    parser.add_option("--lr1", dest="logistic_l1", type="float", help="use logistic regression with l1-regularity", default=None)
    parser.add_option("--lr2", dest="logistic_l2", type="float", help="use logistic regression with l2-regularity", default=None)

    parser.add_option("-K", dest="class_size", type="int", help="number of class", default=4)
    parser.add_option("-n", dest="max_train", type="int", help="max size of training", default=100)
    parser.add_option("-t", dest="training", help="specify indexes of training", default=None)
    parser.add_option("-N", dest="trying", type="int", help="number of trying", default=100)

    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    (opt, args) = parser.parse_args()

    data = sklearn.datasets.fetch_20newsgroups_vectorized()
    print "(train size, voca size) : (%d, %d)" % data.data.shape

    if opt.class_size:
        index = data.target < opt.class_size
        a = data.data.toarray()[index, :]
        data.data = scipy.sparse.csr_matrix(a)
        data.target = data.target[index]
        print "(shrinked train size, voca size) : (%d, %d)" % data.data.shape


    N_CLASS = data.target.max() + 1
    if opt.training:
        train = [int(x) for x in opt.training.split(",")]
    else:
        train = [numpy.random.choice((data.target==k).nonzero()[0]) for k in xrange(N_CLASS)]
    print "indexes of training set : ", ",".join("%d" % x for x in train)

    pool = range(data.data.shape[0])
    for x in train: pool.remove(x)

    classifier_factory = None
    if opt.logistic_l1:
        print "Logistic Regression with L1-regularity : C = %f" % opt.logistic_l1
        classifier_factory = lambda: LogisticRegression(penalty='l1', C=opt.logistic_l1)
    elif opt.logistic_l2:
        print "Logistic Regression with L2-regularity : C = %f" % opt.logistic_l2
        classifier_factory = lambda: LogisticRegression(C=opt.logistic_l2)
    elif opt.naive_bayes:
        print "Naive Bayes Classifier : alpha = %f" % opt.naive_bayes
        classifier_factory = lambda: MultinomialNB(alpha=opt.naive_bayes)

    if classifier_factory:
        test = sklearn.datasets.fetch_20newsgroups_vectorized(subset='test')
        print "(test size, voca size) : (%d, %d)" % test.data.shape
        if opt.class_size:
            index = test.target < opt.class_size
            a = test.data.toarray()[index, :]
            test.data = scipy.sparse.csr_matrix(a)
            test.target = test.target[index]
            print "(shrinked test size, voca size) : (%d, %d)" % test.data.shape

        print "score for all data: %f" % classifier_factory().fit(data.data, data.target).score(test.data, test.target)

        for n in xrange(opt.trying):
            print "trying.. %d" % n
            train = [numpy.random.choice((data.target==k).nonzero()[0]) for k in xrange(N_CLASS)]
            pool = range(data.data.shape[0])
            for x in train: pool.remove(x)
            results = activelearn(data, test, train, pool, classifier_factory, opt.max_train, opt.seed)

            with open("output_mmms_%d_%d.txt" % (opt.class_size, opt.max_train), "ab") as f:
                f.write("\t".join("%f" % x[1] for x in results))
                f.write("\n")

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = mmpm
#!/usr/bin/env python
# encode: utf-8

# Active Learning for 20 newsgroups with MM+M (Guo+ IJCAI-07)
#    Yuhong Guo and Russ Greiner, Optimistic Active Learning using Mutual Information, IJCAI-07

# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import optparse
import numpy
import scipy.sparse
import sklearn.datasets
from sklearn.linear_model import LogisticRegression

def activelearn(data, test, train, pool, classifier_factory, max_train, seed):
    numpy.random.seed(seed)

    # copy initial indexes of training and pool
    train = list(train)
    pool = list(pool)

    accuracies = []
    Z = len(test.target)
    K = data.target.max() + 1
    while len(train) < max_train:
        if len(accuracies) > 0:
            predict = classifier.predict_proba(data.data[pool,:])
            entbase = -numpy.nan_to_num(predict * numpy.log(predict)).sum(axis=1)
            predict.sort(axis=1)
            margin = predict[:,-1] - predict[:,-2]
            uncertain = predict[:,-1]

            i_star = y_i_star = None
            f_i_star = 1e300
            print "i\ty_i\tf_i\tuncertain\tmargin\tent"
            for i, x in enumerate(pool):
                L_x_i = data.data[train + [x], :]
                L_y = data.target[train]
                entropies = numpy.zeros(K)
                for y in xrange(K):
                    l = list(L_y)
                    l.append(y)
                    phi_i = classifier_factory().fit(L_x_i, l)

                    p = phi_i.predict_proba(data.data[pool])
                    entropies[y] = -(numpy.nan_to_num(numpy.log(p)) * p).sum()
                y_i = entropies.argmin()
                f_i = entropies[y_i]
                print "%d\t%d\t%f\t%f\t%f\t%f" % (x, y_i, f_i, uncertain[i], margin[i], entbase[i])
                if f_i < f_i_star:
                    i_star = i
                    y_i_star = y_i
                    f_i_star = f_i

            x = pool[i_star]
            print "select : %d (MM=%f, predict=%d, actual=%d)" % (x, f_i_star, y_i_star, data.target[x])
            train.append(x)
            del pool[i_star]

            if data.target[x] != y_i_star:
                phi = classifier_factory().fit(data.data[train, :], data.target[train])
                p = phi_i.predict_proba(data.data[pool])
                i_star = (numpy.nan_to_num(numpy.log(p)) * p).sum(axis=1).argmin()

                x = pool[i_star]
                print "select : %d (actual=%d)" % (x, data.target[x])
                train.append(x)
                del pool[i_star]

        classifier = classifier_factory().fit(data.data[train,:], data.target[train])
        accuracy = classifier.score(test.data, test.target)
        print "%d : %f" % (len(train), accuracy)
        accuracies.append((len(train), accuracy))

    return accuracies

def main():
    parser = optparse.OptionParser()
    parser.add_option("--nb", dest="naive_bayes", type="float", help="use naive bayes classifier", default=None)
    parser.add_option("--lr1", dest="logistic_l1", type="float", help="use logistic regression with l1-regularity", default=None)
    parser.add_option("--lr2", dest="logistic_l2", type="float", help="use logistic regression with l2-regularity", default=None)

    parser.add_option("-K", dest="class_size", type="int", help="number of class", default=None)
    parser.add_option("-n", dest="max_train", type="int", help="max size of training", default=30)
    parser.add_option("-t", dest="training", help="specify indexes of training", default=None)

    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    (opt, args) = parser.parse_args()

    data = sklearn.datasets.fetch_20newsgroups_vectorized()
    print "(train size, voca size) : (%d, %d)" % data.data.shape

    if opt.class_size:
        index = data.target < opt.class_size
        a = data.data.toarray()[index, :]
        data.data = scipy.sparse.csr_matrix(a)
        data.target = data.target[index]
        print "(shrinked train size, voca size) : (%d, %d)" % data.data.shape


    N_CLASS = data.target.max() + 1
    if opt.training:
        train = [int(x) for x in opt.training.split(",")]
    else:
        train = [numpy.random.choice((data.target==k).nonzero()[0]) for k in xrange(N_CLASS)]
    print "indexes of training set : ", ",".join("%d" % x for x in train)

    pool = range(data.data.shape[0])
    for x in train: pool.remove(x)

    classifier_factory = None
    if opt.logistic_l1:
        print "Logistic Regression with L1-regularity : C = %f" % opt.logistic_l1
        classifier_factory = lambda: LogisticRegression(penalty='l1', C=opt.logistic_l1)
    elif opt.logistic_l2:
        print "Logistic Regression with L2-regularity : C = %f" % opt.logistic_l2
        classifier_factory = lambda: LogisticRegression(C=opt.logistic_l2)
    else:
        pass

    if classifier_factory:
        test = sklearn.datasets.fetch_20newsgroups_vectorized(subset='test')
        print "(test size, voca size) : (%d, %d)" % test.data.shape
        if opt.class_size:
            index = test.target < opt.class_size
            a = test.data.toarray()[index, :]
            test.data = scipy.sparse.csr_matrix(a)
            test.target = test.target[index]
            print "(shrinked test size, voca size) : (%d, %d)" % test.data.shape

        print "score for all data: %f" % classifier_factory().fit(data.data, data.target).score(test.data, test.target)

        results = activelearn(data, test, train, pool, classifier_factory, opt.max_train, opt.seed)

        for x in results:
            print "%d\t%f" % x

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = oracle
#!/usr/bin/env python
# encode: utf-8

# Active Learning for 20 newsgroups with Oracle and testset

# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import optparse
import numpy
import scipy.sparse
import sklearn.datasets
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

def activelearn(data, test, train, pool, classifier_factory, max_train, n_candidate, seed):
    numpy.random.seed(seed)

    # copy initial indexes of training and pool
    train = list(train)
    pool = list(pool)

    accuracies = []
    Z = len(test.target)
    K = data.target.max() + 1
    while len(train) < max_train:
        if len(accuracies) > 0:
            i_star = None
            max_score = 0.0
            candidate = pool
            if 0 < n_candidate < len(pool):
                numpy.random.shuffle(pool)
                candidate = pool[:n_candidate]
            for i, x in enumerate(candidate):
                t = train + [x]
                s = classifier_factory().fit(data.data[t, :], data.target[t]).score(test.data, test.target)
                if max_score < s:
                    print "%d\t%f" % (x, s)
                    max_score = s
                    i_star = i
            train.append(pool[i_star])
            del pool[i_star]

        classifier = classifier_factory().fit(data.data[train,:], data.target[train])
        accuracy = classifier.score(test.data, test.target)
        print "%d : %f" % (len(train), accuracy)
        accuracies.append((len(train), accuracy))

    return accuracies

def main():
    parser = optparse.OptionParser()
    parser.add_option("--nb", dest="naive_bayes", type="float", help="use naive bayes classifier", default=None)
    parser.add_option("--lr1", dest="logistic_l1", type="float", help="use logistic regression with l1-regularity", default=None)
    parser.add_option("--lr2", dest="logistic_l2", type="float", help="use logistic regression with l2-regularity", default=None)

    parser.add_option("-K", dest="class_size", type="int", help="number of class", default=None)
    parser.add_option("-n", dest="max_train", type="int", help="max size of training", default=30)
    parser.add_option("-t", dest="training", help="specify indexes of training", default=None)
    parser.add_option("-T", dest="candidate", type="int", help="candidate size", default=-1)

    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    (opt, args) = parser.parse_args()

    data = sklearn.datasets.fetch_20newsgroups_vectorized()
    print "(train size, voca size) : (%d, %d)" % data.data.shape

    if opt.class_size:
        index = data.target < opt.class_size
        a = data.data.toarray()[index, :]
        data.data = scipy.sparse.csr_matrix(a)
        data.target = data.target[index]
        print "(shrinked train size, voca size) : (%d, %d)" % data.data.shape


    N_CLASS = data.target.max() + 1
    if opt.training:
        train = [int(x) for x in opt.training.split(",")]
    else:
        train = [numpy.random.choice((data.target==k).nonzero()[0]) for k in xrange(N_CLASS)]
    print "indexes of training set : ", ",".join("%d" % x for x in train)

    pool = range(data.data.shape[0])
    for x in train: pool.remove(x)

    classifier_factory = None
    if opt.logistic_l1:
        print "Logistic Regression with L1-regularity : C = %f" % opt.logistic_l1
        classifier_factory = lambda: LogisticRegression(penalty='l1', C=opt.logistic_l1)
    elif opt.logistic_l2:
        print "Logistic Regression with L2-regularity : C = %f" % opt.logistic_l2
        classifier_factory = lambda: LogisticRegression(C=opt.logistic_l2)
    elif opt.naive_bayes:
        print "Naive Bayes Classifier : alpha = %f" % opt.naive_bayes
        classifier_factory = lambda: MultinomialNB(alpha=opt.naive_bayes)

    if classifier_factory:
        test = sklearn.datasets.fetch_20newsgroups_vectorized(subset='test')
        print "(test size, voca size) : (%d, %d)" % test.data.shape
        if opt.class_size:
            index = test.target < opt.class_size
            a = test.data.toarray()[index, :]
            test.data = scipy.sparse.csr_matrix(a)
            test.target = test.target[index]
            print "(shrinked test size, voca size) : (%d, %d)" % test.data.shape

        print "score for all data: %f" % classifier_factory().fit(data.data, data.target).score(test.data, test.target)

        results = activelearn(data, test, train, pool, classifier_factory, opt.max_train, opt.candidate, opt.seed)

        for x in results:
            print "%d\t%f" % x

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = qbc4
#!/usr/bin/env python
# encode: utf-8

# Active Learning (Query-By-Committee) for 20 newsgroups
# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import optparse
import numpy
import sklearn.datasets
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

def activelearn(results, data, test, strategy, train, pool, classifier_factories, max_train, densities):
    print strategy

    # copy initial indexes of training and pool
    train = list(train)
    pool = list(pool)

    accuracies = []
    Z = len(test.target)
    while len(train) < max_train:
        if len(accuracies) > 0:
            if strategy == "random":
                x = numpy.random.randint(len(pool))
            else:
                if strategy == "vote entropy":
                    p = numpy.array([c.predict(data.data[pool,:]) for c in classifiers])
                    # This is equivalent to Vote Entropy when # of classifiers = 3
                    x = ((p[:,0:2]==p[:,1:3]).sum(axis=1) + (p[:,0]==p[:,2]))
                elif strategy == "average KL":
                    p = numpy.array([c.predict_proba(data.data[pool,:]) for c in classifiers]) # 3 * N * K
                    pc = p.mean(axis=0) # N * K
                    x = numpy.nan_to_num(p * numpy.log(pc / p)).sum(axis=2).sum(axis=0)
                elif strategy == "qbc+margin sampling":
                    p = numpy.array([c.predict_proba(data.data[pool,:]) for c in classifiers]) # 3 * N * K
                    pc = p.mean(axis=0) # N * K
                    pc.sort(axis=1)
                    x = pc[:,-1] - pc[:,-2]
                if densities != None: x *= densities[pool]
                x = x.argmin()
            train.append(pool[x])
            del pool[x]

        classifiers = [f().fit(data.data[train,:], data.target[train]) for f in classifier_factories]

        predict = sum(c.predict_proba(test.data) for c in classifiers)
        correct = (predict.argmax(axis=1) == test.target).sum()
        accuracy = float(correct) / Z
        print "%s %d : %d / %d = %f" % (strategy, len(train), correct, Z, accuracy)
        accuracies.append(accuracy)

    results.append((strategy, accuracies))

def main():
    parser = optparse.OptionParser()
    parser.add_option("--nb", dest="naive_bayes", type="float", help="use naive bayes classifier", default=None)
    parser.add_option("--lr1", dest="logistic_l1", type="float", help="use logistic regression with l1-regularity", default=None)
    parser.add_option("--lr2", dest="logistic_l2", type="float", help="use logistic regression with l2-regularity", default=None)

    parser.add_option("-n", dest="max_train", type="int", help="max size of training", default=300)
    parser.add_option("-t", dest="training", help="specify indexes of training", default=None)

    parser.add_option("-b", dest="beta", type="float", help="density importance", default=0)

    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    (opt, args) = parser.parse_args()
    numpy.random.seed(opt.seed)

    data = sklearn.datasets.fetch_20newsgroups_vectorized()
    print "(train size, voca size) : (%d, %d)" % data.data.shape

    N_CLASS = data.target.max() + 1
    if opt.training:
        train = [int(x) for x in opt.training.split(",")]
    else:
        train = [numpy.random.choice((data.target==k).nonzero()[0]) for k in xrange(N_CLASS)]
    print "indexes of training set : ", ",".join("%d" % x for x in train)

    pool = range(data.data.shape[0])
    for x in train: pool.remove(x)

    classifier_factories = []
    if opt.logistic_l1:
        print "Logistic Regression with L1-regularity : C = %f" % opt.logistic_l1
        classifier_factories.append(lambda: LogisticRegression(penalty='l1', C=opt.logistic_l1))
    if opt.logistic_l2:
        print "Logistic Regression with L2-regularity : C = %f" % opt.logistic_l2
        classifier_factories.append(lambda: LogisticRegression(C=opt.logistic_l2))
    if opt.naive_bayes:
        print "Naive Bayes Classifier : alpha = %f" % opt.naive_bayes
        classifier_factories.append(lambda: MultinomialNB(alpha=opt.naive_bayes))

    if len(classifier_factories) >= 2:
        test = sklearn.datasets.fetch_20newsgroups_vectorized(subset='test')
        print "(test size, voca size) : (%d, %d)" % test.data.shape

        densities = None
        if opt.beta > 0:
            densities = (data.data * data.data.T).mean(axis=0).A[0] ** opt.beta

        methods = ["random", "vote entropy", "average KL", "qbc+margin sampling", ]
        results = []
        for x in methods:
            activelearn(results, data, test, x, train, pool, classifier_factories, opt.max_train, densities)

        print "\t%s" % "\t".join(x[0] for x in results)
        d = len(train)
        for i in xrange(len(results[0][1])):
            print "%d\t%s" % (i+d, "\t".join("%f" % x[1][i] for x in results))

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = qbc_dist
#!/usr/bin/env python
# encode: utf-8

# Active Learning (Query-By-Committee) for 20 newsgroups
# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import optparse
import numpy
import sklearn.datasets
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

def activelearn(data, test, strategy, train, pool, classifier_factories, max_train, densities):
    # copy initial indexes of training and pool
    train = list(train)
    pool = list(pool)

    accuracies = []
    Z = len(test.target)
    while len(train) < max_train:
        if len(accuracies) > 0:
            if strategy == "random":
                x = numpy.random.randint(len(pool))
            else:
                if strategy == "vote entropy":
                    p = numpy.array([c.predict(data.data[pool,:]) for c in classifiers])
                    # This is equivalent to Vote Entropy when # of classifiers = 3
                    x = ((p[:,0:2]==p[:,1:3]).sum(axis=1) + (p[:,0]==p[:,2]))
                elif strategy == "average KL":
                    p = numpy.array([c.predict_proba(data.data[pool,:]) for c in classifiers]) # 3 * N * K
                    pc = p.mean(axis=0) # N * K
                    x = numpy.nan_to_num(p * numpy.log(pc / p)).sum(axis=2).sum(axis=0)
                elif strategy == "qbc+margin sampling":
                    p = numpy.array([c.predict_proba(data.data[pool,:]) for c in classifiers]) # 3 * N * K
                    pc = p.mean(axis=0) # N * K
                    pc.sort(axis=1)
                    x = pc[:,-1] - pc[:,-2]
                if densities != None: x *= densities[pool]
                x = x.argmin()
            train.append(pool[x])
            del pool[x]

        classifiers = [f().fit(data.data[train,:], data.target[train]) for f in classifier_factories]

        predict = sum(c.predict_proba(test.data) for c in classifiers)
        correct = (predict.argmax(axis=1) == test.target).sum()
        accuracy = float(correct) / Z
        print "%d : %d / %d = %f" % (len(train), correct, Z, accuracy)
        accuracies.append(accuracy)
    return accuracies

def main():
    parser = optparse.OptionParser()
    parser.add_option("--nb", dest="naive_bayes", type="float", help="use naive bayes classifier", default=None)
    parser.add_option("--lr1", dest="logistic_l1", type="float", help="use logistic regression with l1-regularity", default=None)
    parser.add_option("--lr2", dest="logistic_l2", type="float", help="use logistic regression with l2-regularity", default=None)

    parser.add_option("-n", dest="max_train", type="int", help="max size of training", default=300)
    parser.add_option("-N", dest="trying", type="int", help="number of trying", default=100)

    parser.add_option("-b", dest="beta", type="float", help="density importance", default=0)

    (opt, args) = parser.parse_args()

    data = sklearn.datasets.fetch_20newsgroups_vectorized()
    print "(train size, voca size) : (%d, %d)" % data.data.shape

    N_CLASS = data.target.max() + 1

    classifier_factories = []
    if opt.logistic_l1:
        print "Logistic Regression with L1-regularity : C = %f" % opt.logistic_l1
        classifier_factories.append(lambda: LogisticRegression(penalty='l1', C=opt.logistic_l1))
    if opt.logistic_l2:
        print "Logistic Regression with L2-regularity : C = %f" % opt.logistic_l2
        classifier_factories.append(lambda: LogisticRegression(C=opt.logistic_l2))
    if opt.naive_bayes:
        print "Naive Bayes Classifier : alpha = %f" % opt.naive_bayes
        classifier_factories.append(lambda: MultinomialNB(alpha=opt.naive_bayes))

    if len(classifier_factories) >= 2:
        test = sklearn.datasets.fetch_20newsgroups_vectorized(subset='test')
        print "(test size, voca size) : (%d, %d)" % test.data.shape

        densities = None
        if opt.beta > 0:
            densities = (data.data * data.data.T).mean(axis=0).A[0] ** opt.beta

        methods = ["random", "vote entropy", "average KL", "qbc+margin sampling", ]
        results = []
        for n in xrange(opt.trying):
            for method in methods:
                print "%s : %d" % (method, n)
                train = [numpy.random.choice((data.target==k).nonzero()[0]) for k in xrange(N_CLASS)]
                pool = range(data.data.shape[0])
                for x in train: pool.remove(x)

                results = activelearn(data, test, method, train, pool, classifier_factories, opt.max_train, densities)

                d = len(train)
                with open("output_qbc_%d.txt" % opt.max_train, "ab") as f:
                    f.write("%s\t%s\n" % (method, "\t".join("%f" % x for x in results)))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = uncertain
#!/usr/bin/env python
# encode: utf-8

# Active Learning (Uncertainly Sampling)
# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import sys, numpy
from sklearn.linear_model import LogisticRegression
from sklearn import cross_validation

import optparse
parser = optparse.OptionParser()
#parser.add_option("-c", dest="corpus", help="corpus module name under nltk.corpus (e.g. brown, reuters)", default='brown')
#parser.add_option("-r", dest="testrate", type="float", help="rate of test dataset in corpus", default=0.1)
parser.add_option("--seed", dest="seed", type="int", help="random seed")
(opt, args) = parser.parse_args()
numpy.random.seed(opt.seed)

output = False

def activelearn(data, label, strategy):
    #print strategy

    N, D = data.shape
    train = list(range(D))
    pool = range(D,N)
    predict = None

    for i in xrange(30-D):
        if predict != None:
            if strategy == "random":
                x = numpy.random.randint(len(pool))
            elif strategy == "least confident":
                x = predict.max(axis=1).argmin()
            elif strategy == "margin sampling":
                predict.sort(axis=1)
                x = (numpy.exp(predict[:,-1])-numpy.exp(predict[:,-2])).argmin()
            elif strategy == "entropy-based":
                x = numpy.nan_to_num(numpy.exp(predict)*predict).sum(axis=1).argmin()
            train.append(pool[x])
            del pool[x]

        cl = LogisticRegression()
        #cl = LogisticRegression(C=0.1, penalty="l1")
        cl.fit(data[train,:], label[train])
        predict = cl.predict_log_proba(data[pool,:])
        log_likelihood = 0
        correct = 0
        for n, logprob in zip(pool,predict):
            c = label[n]
            log_likelihood += logprob[c]
            if c == logprob.argmax(): correct += 1

        Z = len(pool)
        precision = float(correct) / Z
        perplexity = numpy.exp(-log_likelihood / Z)
        if output:
            print "%d : %d / %d = %f, %f" % (len(train), correct, Z, precision, perplexity)

    #print data[train,:], label[train]

    if D==2:
        import matplotlib.pyplot as plt
        plt.plot(data[pool,0], data[pool,1], 'x', color="red")
        plt.plot(data[train,0], data[train,1], 'o', color="red")
        plt.title(strategy)
        plt.show()

    return precision, perplexity


D=10
N=1000
presicions = []
perplexities = []
for i in xrange(100):
    data = numpy.random.randn(N,D)
    label = numpy.zeros(N, dtype=int)
    for n in xrange(N):
        c = n % D
        data[n, c] += 2
        label[n] = c

    result = []
    result.append(activelearn(data, label, "random"))
    result.append(activelearn(data, label, "least confident"))
    result.append(activelearn(data, label, "margin sampling"))
    result.append(activelearn(data, label, "entropy-based"))

    x = numpy.array(result)
    presicions.append(x[:,0])
    perplexities.append(x[:,1])

print numpy.mean(presicions, axis=0)


########NEW FILE########
__FILENAME__ = uncertain2
#!/usr/bin/env python
# encode: utf-8

# Active Learning (Uncertainly Sampling)
# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import re, collections, numpy
from nltk.corpus import movie_reviews
from nltk.stem import WordNetLemmatizer

voca = dict()
vocalist = []
doclist = []
labels = []
realphabet = re.compile('^[a-z]+$')
wnl = WordNetLemmatizer()
for id in movie_reviews.fileids():
    doc = collections.defaultdict(int)
    for w in movie_reviews.words(id):
        if realphabet.match(w):
            w = wnl.lemmatize(w)
            if w not in voca:
                voca[w] = len(vocalist)
                vocalist.append(w)
            doc[voca[w]] += 1
    if len(doc) > 0: doclist.append(doc)
    cat = movie_reviews.categories(id)[0]
    labels.append(1 if cat == "pos" else 0)
print len(voca)

labels = numpy.array(labels)
data = numpy.zeros((len(doclist), len(voca)))
for j, doc in enumerate(doclist):
    for i, c in doc.iteritems():
        data[j, i] = c


from sklearn.feature_extraction.text import TfidfTransformer
transformer = TfidfTransformer(norm=None)
data = transformer.fit_transform(data)


from sklearn import cross_validation

from sklearn.linear_model import LogisticRegression
cl = LogisticRegression()

from sklearn.naive_bayes import MultinomialNB
#cl = MultinomialNB()

from sklearn.naive_bayes import BernoulliNB
#cl = BernoulliNB()

from sklearn.svm import SVC
#cl = SVC()

from sklearn.ensemble import RandomForestClassifier
#cl = RandomForestClassifier()


print cross_validation.cross_val_score(cl, data, labels, cv=10)



"""
import sys, numpy
from sklearn.linear_model import LogisticRegression
from sklearn import cross_validation

import optparse
parser = optparse.OptionParser()
#parser.add_option("-c", dest="corpus", help="corpus module name under nltk.corpus (e.g. brown, reuters)", default='brown')
#parser.add_option("-r", dest="testrate", type="float", help="rate of test dataset in corpus", default=0.1)
parser.add_option("--seed", dest="seed", type="int", help="random seed")
(opt, args) = parser.parse_args()
numpy.random.seed(opt.seed)

output = False

def activelearn(data, label, strategy):
    #print strategy

    N, D = data.shape
    train = list(range(D))
    pool = range(D,N)
    predict = None

    for i in xrange(30-D):
        if predict != None:
            if strategy == "random":
                x = numpy.random.randint(len(pool))
            elif strategy == "least confident":
                x = predict.max(axis=1).argmin()
            elif strategy == "margin sampling":
                predict.sort(axis=1)
                x = (numpy.exp(predict[:,-1])-numpy.exp(predict[:,-2])).argmin()
            elif strategy == "entropy-based":
                x = numpy.nan_to_num(numpy.exp(predict)*predict).sum(axis=1).argmin()
            train.append(pool[x])
            del pool[x]

        cl = LogisticRegression()
        #cl = LogisticRegression(C=0.1, penalty="l1")
        cl.fit(data[train,:], label[train])
        predict = cl.predict_log_proba(data[pool,:])
        log_likelihood = 0
        correct = 0
        for n, logprob in zip(pool,predict):
            c = label[n]
            log_likelihood += logprob[c]
            if c == logprob.argmax(): correct += 1

        Z = len(pool)
        precision = float(correct) / Z
        perplexity = numpy.exp(-log_likelihood / Z)
        if output:
            print "%d : %d / %d = %f, %f" % (len(train), correct, Z, precision, perplexity)

    #print data[train,:], label[train]

    if D==2:
        import matplotlib.pyplot as plt
        plt.plot(data[pool,0], data[pool,1], 'x', color="red")
        plt.plot(data[train,0], data[train,1], 'o', color="red")
        plt.title(strategy)
        plt.show()

    return precision, perplexity


D=10
N=1000
presicions = []
perplexities = []
for i in xrange(100):
    data = numpy.random.randn(N,D)
    label = numpy.zeros(N, dtype=int)
    for n in xrange(N):
        c = n % D
        data[n, c] += 2
        label[n] = c

    result = []
    result.append(activelearn(data, label, "random"))
    result.append(activelearn(data, label, "least confident"))
    result.append(activelearn(data, label, "margin sampling"))
    result.append(activelearn(data, label, "entropy-based"))

    x = numpy.array(result)
    presicions.append(x[:,0])
    perplexities.append(x[:,1])

print numpy.mean(presicions, axis=0)

"""

########NEW FILE########
__FILENAME__ = uncertain3
#!/usr/bin/env python
# encode: utf-8

# Active Learning (Uncertainly Sampling)
# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import numpy
import dataset
from sklearn.linear_model import LogisticRegression

categories = ['crude', 'money-fx', 'trade', 'interest', 'ship', 'wheat', 'corn']
doclist, labels, voca, vocalist = dataset.load(categories)
print "document size : %d" % len(doclist)
print "vocaburary size : %d" % len(voca)

data = numpy.zeros((len(doclist), len(voca)))
for j, doc in enumerate(doclist):
    for i, c in doc.iteritems():
        data[j, i] = c

def activelearn(data, label, strategy, train):
    print strategy

    N, D = data.shape
    train = list(train) # copy initial indexes of training
    pool = range(N)
    for x in train: pool.remove(x)

    predict = None
    precisions = []
    while len(train) < 300:
        if predict != None:
            if strategy == "random":
                x = numpy.random.randint(len(pool))
            elif strategy == "least confident":
                x = predict.max(axis=1).argmin()
            elif strategy == "margin sampling":
                predict.sort(axis=1)
                x = (numpy.exp(predict[:,-1])-numpy.exp(predict[:,-2])).argmin()
            elif strategy == "entropy-based":
                x = numpy.nan_to_num(numpy.exp(predict)*predict).sum(axis=1).argmin()
            train.append(pool[x])
            del pool[x]

        cl = LogisticRegression()
        cl.fit(data[train,:], label[train])
        predict = cl.predict_log_proba(data[pool,:])
        log_likelihood = 0
        correct = 0
        for n, logprob in zip(pool,predict):
            c = label[n]
            log_likelihood += logprob[c]
            if c == logprob.argmax(): correct += 1

        Z = len(pool)
        precision = float(correct) / Z
        perplexity = numpy.exp(-log_likelihood / Z)
        print "%d : %d / %d = %f, %f" % (len(train), correct, Z, precision, perplexity)

        precisions.append(precision)

    return precisions

N_CLASS = labels.max() + 1
train = [numpy.random.choice((labels==k).nonzero()[0]) for k in xrange(N_CLASS)]

methods = ["random", "least confident", "margin sampling", "entropy-based"]
results = []
for x in methods:
    results.append(activelearn(data, labels, x, train))
print "\t%s" % "\t".join(methods)
d = len(categories)
for i in xrange(len(results[0])):
    print "%d\t%s" % (i+d, "\t".join("%f" % x[i] for x in results))

########NEW FILE########
__FILENAME__ = uncertain4
#!/usr/bin/env python
# encode: utf-8

# Active Learning (Uncertainly Sampling and Information Density) for 20 newsgroups
# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import optparse
import numpy
import scipy.sparse
import sklearn.datasets
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

def activelearn(results, data, test, strategy, train, pool, classifier_factory, max_train, densities):
    print strategy

    # copy initial indexes of training and pool
    train = list(train)
    pool = list(pool)

    accuracies = []
    while len(train) < max_train:
        if len(accuracies) > 0:
            if strategy == "random":
                x = numpy.random.randint(len(pool))
            else:
                predict = cl.predict_proba(data.data[pool,:])
                if strategy == "least confident":
                    x = predict.max(axis=1)-1
                elif strategy == "margin sampling":
                    predict.sort(axis=1)
                    x = (predict[:,-1] - predict[:,-2])
                elif strategy == "entropy-based":
                    x = numpy.nan_to_num(predict * numpy.log(predict)).sum(axis=1)
                if densities != None: x *= densities[pool]
                x = x.argmin()
            train.append(pool[x])
            del pool[x]

        cl = classifier_factory()
        cl.fit(data.data[train,:], data.target[train])
        accuracy = cl.score(test.data, test.target)
        print "%s %d : %f" % (strategy, len(train), accuracy)
        accuracies.append(accuracy)

    results.append((strategy, accuracies))


def main():
    parser = optparse.OptionParser()
    parser.add_option("-r", dest="method_random", action="store_true", help="use random sampling", default=False)
    parser.add_option("-l", dest="method_least", action="store_true", help="use least confident", default=False)
    parser.add_option("-m", dest="method_margin", action="store_true", help="use margin sampling", default=False)
    parser.add_option("-e", dest="method_entropy", action="store_true", help="use entropy-based method", default=False)
    parser.add_option("-a", dest="method_all", action="store_true", help="use all methods", default=False)

    parser.add_option("--nb", dest="naive_bayes", type="float", help="use naive bayes classifier", default=None)
    parser.add_option("--lr1", dest="logistic_l1", type="float", help="use logistic regression with l1-regularity", default=None)
    parser.add_option("--lr2", dest="logistic_l2", type="float", help="use logistic regression with l2-regularity", default=None)

    parser.add_option("-K", dest="class_size", type="int", help="number of class", default=None)
    parser.add_option("-n", dest="max_train", type="int", help="max size of training", default=300)
    parser.add_option("-t", dest="training", help="specify indexes of training", default=None)

    parser.add_option("-b", dest="beta", type="float", help="density importance", default=0)

    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    (opt, args) = parser.parse_args()
    numpy.random.seed(opt.seed)

    data = sklearn.datasets.fetch_20newsgroups_vectorized()
    print "(train size, voca size) : (%d, %d)" % data.data.shape

    N_CLASS = data.target.max() + 1
    if opt.training:
        train = [int(x) for x in opt.training.split(",")]
    else:
        train = [numpy.random.choice((data.target==k).nonzero()[0]) for k in xrange(N_CLASS)]
    print "indexes of training set : ", ",".join("%d" % x for x in train)
    if opt.class_size:
        index = data.target < opt.class_size
        a = data.data.toarray()[index, :]
        data.data = scipy.sparse.csr_matrix(a)
        data.target = data.target[index]
        print "(shrinked train size, voca size) : (%d, %d)" % data.data.shape

    pool = range(data.data.shape[0])
    for x in train: pool.remove(x)

    methods = []
    if opt.method_all:
        methods = ["random", "least confident", "margin sampling", "entropy-based"]
    else:
        if opt.method_random: methods.append("random")
        if opt.method_least: methods.append("least confident")
        if opt.method_margin: methods.append("margin sampling")
        if opt.method_entropy: methods.append("entropy-based")

    if len(methods) > 0:
        test = sklearn.datasets.fetch_20newsgroups_vectorized(subset='test')
        print "(test size, voca size) : (%d, %d)" % test.data.shape
        if opt.class_size:
            index = test.target < opt.class_size
            a = test.data.toarray()[index, :]
            test.data = scipy.sparse.csr_matrix(a)
            test.target = test.target[index]
            print "(shrinked test size, voca size) : (%d, %d)" % test.data.shape

        densities = None
        if opt.beta > 0:
            densities = (data.data * data.data.T).mean(axis=0).A[0] ** opt.beta

        if opt.logistic_l1:
            print "Logistic Regression with L1-regularity : C = %f" % opt.logistic_l1
            classifier_factory = lambda: LogisticRegression(penalty='l1', C=opt.logistic_l1)
        elif opt.logistic_l2:
            print "Logistic Regression with L2-regularity : C = %f" % opt.logistic_l2
            classifier_factory = lambda: LogisticRegression(C=opt.logistic_l2)
        else:
            a = opt.naive_bayes or 0.01
            print "Naive Bayes Classifier : alpha = %f" % a
            classifier_factory = lambda: MultinomialNB(alpha=a)

        results = []
        for x in methods:
            activelearn(results, data, test, x, train, pool, classifier_factory, opt.max_train, densities)

        print "\t%s" % "\t".join(x[0] for x in results)
        d = len(train)
        for i in xrange(len(results[0][1])):
            print "%d\t%s" % (i+d, "\t".join("%f" % x[1][i] for x in results))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = uncert_dist
#!/usr/bin/env python
# encode: utf-8

# Active Learning (Uncertainly Sampling and Information Density) for 20 newsgroups
# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import optparse
import numpy
import scipy.sparse
import sklearn.datasets
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

def activelearn(results, data, test, strategy, train, pool, classifier_factory, max_train, densities):
    # copy initial indexes of training and pool
    train = list(train)
    pool = list(pool)

    accuracies = []
    while len(train) < max_train:
        if len(accuracies) > 0:
            if strategy == "random":
                x = numpy.random.randint(len(pool))
            else:
                predict = cl.predict_proba(data.data[pool,:])
                if strategy == "least confident":
                    x = predict.max(axis=1)-1
                elif strategy == "margin sampling":
                    predict.sort(axis=1)
                    x = (predict[:,-1] - predict[:,-2])
                elif strategy == "entropy-based":
                    x = numpy.nan_to_num(predict * numpy.log(predict)).sum(axis=1)
                if densities != None: x *= densities[pool]
                x = x.argmin()
            train.append(pool[x])
            del pool[x]

        cl = classifier_factory()
        cl.fit(data.data[train,:], data.target[train])
        accuracy = cl.score(test.data, test.target)
        print "%d : %f" % (len(train), accuracy)
        accuracies.append(accuracy)

    results.append((strategy, accuracies))


def main():
    parser = optparse.OptionParser()
    parser.add_option("--nb", dest="naive_bayes", type="float", help="use naive bayes classifier", default=None)
    parser.add_option("--lr1", dest="logistic_l1", type="float", help="use logistic regression with l1-regularity", default=None)
    parser.add_option("--lr2", dest="logistic_l2", type="float", help="use logistic regression with l2-regularity", default=None)

    parser.add_option("-K", dest="class_size", type="int", help="number of class", default=None)
    parser.add_option("-n", dest="max_train", type="int", help="max size of training", default=100)
    parser.add_option("-N", dest="trying", type="int", help="number of trying", default=100)

    parser.add_option("-b", dest="beta", type="float", help="density importance", default=0)
    (opt, args) = parser.parse_args()

    data = sklearn.datasets.fetch_20newsgroups_vectorized()
    print "(train size, voca size) : (%d, %d)" % data.data.shape

    if opt.class_size:
        index = data.target < opt.class_size
        a = data.data.toarray()[index, :]
        data.data = scipy.sparse.csr_matrix(a)
        data.target = data.target[index]
        print "(shrinked train size, voca size) : (%d, %d)" % data.data.shape

    classifier_factory = clz = None
    if opt.logistic_l1:
        print "Logistic Regression with L1-regularity : C = %f" % opt.logistic_l1
        classifier_factory = lambda: LogisticRegression(penalty='l1', C=opt.logistic_l1)
        clz = "lrl1"
    elif opt.logistic_l2:
        print "Logistic Regression with L2-regularity : C = %f" % opt.logistic_l2
        classifier_factory = lambda: LogisticRegression(C=opt.logistic_l2)
        clz = "lrl2"
    elif opt.naive_bayes:
        print "Naive Bayes Classifier : alpha = %f" % opt.naive_bayes
        classifier_factory = lambda: MultinomialNB(alpha=opt.naive_bayes)
        clz = "nb"

    if classifier_factory:
        test = sklearn.datasets.fetch_20newsgroups_vectorized(subset='test')
        print "(test size, voca size) : (%d, %d)" % test.data.shape
        if opt.class_size:
            index = test.target < opt.class_size
            a = test.data.toarray()[index, :]
            test.data = scipy.sparse.csr_matrix(a)
            test.target = test.target[index]
            print "(shrinked test size, voca size) : (%d, %d)" % test.data.shape

        densities = None
        if opt.beta > 0:
            densities = (data.data * data.data.T).mean(axis=0).A[0] ** opt.beta

        N_CLASS = data.target.max() + 1
        for method in ["random", "least confident", "margin sampling", "entropy-based"]:
            results = []
            for n in xrange(opt.trying):
                print "%s : %d" % (method, n)
                train = [numpy.random.choice((data.target==k).nonzero()[0]) for k in xrange(N_CLASS)]
                pool = range(data.data.shape[0])
                for x in train: pool.remove(x)

                activelearn(results, data, test, method, train, pool, classifier_factory, opt.max_train, densities)

            d = len(train)
            with open("output_%s_%s.txt" % (method, clz), "wb") as f:
                f.write(method)
                f.write("\n")
                for i in xrange(len(results[0][1])):
                    f.write("%d\t%s\n" % (i+d, "\t".join("%f" % x[1][i] for x in results)))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Extract Web Content - Test
# (c)2010 Nakatani Shuyo, Cybozu Labs Inc.

import sys, os, re
from optparse import OptionParser
sys.path.append("../hmm")
from hmm import HMM

def load_data(directory):
    import glob
    htmllist = glob.glob(os.path.join(directory, "*.html"))
    features = []
    for filename in htmllist:
        taglist = []
        f = open(filename, 'r')
        for line in f:
            tags = re.findall(r'<(\w+)',line)
            if len(tags)>0: taglist.extend([x.lower() for x in tags])
        f.close()
        features.append(taglist)
    return features

def main():
    parser = OptionParser()
    parser.add_option("-t", dest="test", help="test data directory")
    parser.add_option("-m", dest="model", help="model data filename to save")
    (options, args) = parser.parse_args()
    if not options.model: parser.error("need model data filename(-m)")

    hmm = HMM()
    hmm.load(options.model)

    if options.test:
        tests = load_data(options.test)
        for x in tests:
            print zip(x, hmm.Viterbi(hmm.words2id(x)))

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = train
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Extract Web Content with HMM
# (c)2010 Nakatani Shuyo, Cybozu Labs Inc.

import sys, os, re
from optparse import OptionParser
sys.path.append("../hmm")
from hmm import HMM
#import numpy
#from numpy.random import dirichlet, randn

def load_data(directory):
    import glob
    htmllist = glob.glob(os.path.join(directory, "*.html"))
    features = []
    for filename in htmllist:
        taglist = []
        f = open(filename, 'r')
        for line in f:
            tags = re.findall(r'<(\w+)',line)
            if len(tags)>0: taglist.extend([x.lower() for x in tags])
        f.close()
        features.append(taglist)
    return features

def main():
    parser = OptionParser()
    parser.add_option("-d", dest="training", help="training data directory")
    parser.add_option("-k", dest="K", type="int", help="number of latent states", default=6)
    parser.add_option("-a", dest="a", type="float", help="Dirichlet parameter", default=1.0)
    parser.add_option("-i", dest="I", type="int", help="iteration count", default=10)
    parser.add_option("-m", dest="model", help="model data filename to save")
    (options, args) = parser.parse_args()
    if not options.training: parser.error("need training data directory(-d)")

    features = load_data(options.training)

    hmm = HMM()
    hmm.set_corpus(features)
    hmm.init_inference(options.K, options.a)
    pre_L = -1e10
    for i in range(options.I):
        log_likelihood = hmm.inference()
        print i, ":", log_likelihood
        if pre_L > log_likelihood: break
        pre_L = log_likelihood
    if options.model:
        hmm.save(options.model)
    else:
        hmm.dump()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = webextract
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Web Content Extractor with CRF
# (c)2010 Nakatani Shuyo, Cybozu Labs Inc.

import sys, os, re, glob, pickle
from optparse import OptionParser
sys.path.append("../sequence")
from crf import CRF, Features, FeatureVector, flatten


def load_dir(dir):
    '''load training/test data directory'''

    labels = []
    texts = []
    for filename in glob.glob(os.path.join(dir, '*.htm*')):
        text, label = load_file(filename)
        texts.append(text)
        labels.append(label)
    return (texts, labels)

def load_file(filename):
    '''load html file'''

    f = open(filename, 'r')
    html = f.read()
    f.close()

    html = re.sub(r'(?is)<(no)?script[^>]*>.*?</(no)?script>', '', html)
    html = re.sub(r'(?is)<style[^>]*>.*?</style>', '', html)
    slices = re.split(r'(?i)(<\/(?:head|div|td|table|p|ul|li|d[dlt]|h[1-6]|form)>|<br(?:\s*\/)?>|<!-- extractcontent_(?:\w+) -->)', html)

    current_label = "head"
    blocks = [slices[0]]
    labels = [current_label]
    for i in range(1,len(slices),2):
        mt = re.match(r'<!-- extractcontent_(\w+) -->', slices[i])
        if mt:
            current_label = mt.group(1)
        else:
            blocks[-1] += slices[i]
            if len(slices[i+1].strip())<15:
                blocks[-1] += slices[i+1]
                continue
        blocks.append(slices[i+1])
        labels.append(current_label)

    print "<<", filename, len(blocks), "blocks, labels=",unique(labels), ">>"
    return ([BlockInfo(b) for b in blocks], labels)

def eliminate_tags(x):
    return re.sub(r'\s', '', re.sub(r'(?s)<[^>]+>', '', x))

class BlockInfo(object):
    def __init__(self, block):
        tags = re.findall(r'<(\w+)', block)
        self.map = dict()
        for t in tags:
            t = t.lower()
            if t in self.map:
                self.map[t] += 1
            else:
                self.map[t] = 1

        self.has_word = dict()
        self.org_text = block
        self.plain_text = eliminate_tags(block)
        notlinked_text = eliminate_tags(re.sub(r'(?is)<a\s[^>]+>.+?<\/a>', '', block))

        self.len_text = len(self.plain_text)
        self.linked_rate = 1 - float(len(notlinked_text)) / self.len_text if self.len_text > 0 else 0
        self.n_ten = len(re.findall(r'、|，', self.plain_text))
        self.n_maru = len(re.findall(r'。', self.plain_text))
        self.has_date = re.search(r'20[01][0-9]\s?[\-\/]\s?[0-9]{1,2}\s?[\-\/]\s?[0-9]{1,2}', self.plain_text) or re.search(r'20[01][0-9]年[0-9]{1,2}月[0-9]{1,2}日', self.plain_text)
        self.affi_link = re.search(r'amazon[\w\d\.\/\-\?&]+-22', block)
    def __getitem__(self, key):
        if key not in self.map: return 0 #raise IndexError, key
        return self.map[key]
    def has(self, word):
        if word in self.has_word: return self.has_word[word]
        self.has_word[word] = True if re.search(word, self.plain_text, re.I) else False
        return self.has_word[word]


def unique(x):
    a = []
    b = dict()
    for y in x:
        if y not in b:
            a.append(y)
            b[y] = 1
    return a

def wce_features(LABELS):
    '''CRF features for Web Content Extractor'''
    features = Features(LABELS)
    for label in LABELS:
        # keywords
        for word in "Copyright|All Rights Reserved|広告掲載|会社概要|無断転載|プライバシーポリシー|利用規約|お問い合わせ|トラックバック|ニュースリリース|新着|無料|確認メール|コメントする|アソシエイト|プロフィール|カレンダー|カテゴリー|ログイン|検索|トップ|個人情報|".split('|'):
            features.add_feature( lambda x, y, w=word, l=label: 1 if x.has(w) and y == l else 0 )
            #features.add_feature( lambda x, y, w=word, l=label: 1 if re.search(w, x.org_text, re.I) and y == l else 0 )

        # html tags
        for tag in "a|p|div|span|ul|ol|li|br|dl|dt|dd|table|tr|td|h1|h2|h3|h4|h5|h6|b|i|center|strong|big|small|meta|form|input|select|option|object|img|iframe|noscript".split('|'):
            features.add_feature( lambda x, y, t=tag, l=label: 1 if y == l and x[t] > 0 else 0 )
            features.add_feature( lambda x, y, t=tag, l=label: 1 if y == l and x[t] < 3 else 0 )
            features.add_feature( lambda x, y, t=tag, l=label: 1 if y == l and x[t] > 5 else 0 )

        # date & affiliate link
        features.add_feature( lambda x, y, l=label: 1 if x.has_date and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.affi_link and y == l else 0 )

        # punctuation
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten==0 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten>0 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten>1 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten>3 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten>5 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_maru==0 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_maru>0 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_maru>1 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_maru>3 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_maru>5 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten+x.n_maru==0 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten+x.n_maru>0 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten+x.n_maru>1 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten+x.n_maru>3 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_ten+x.n_maru>5 and y == l else 0 )

        # text length
        features.add_feature( lambda x, y, l=label: 1 if x.len_text==0 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.len_text>10 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.len_text>20 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.len_text>50 and y == l else 0 )

        # linked rate
        features.add_feature( lambda x, y, l=label: 1 if x.linked_rate>0.8 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.linked_rate<0.2 and y == l else 0 )

    # label bigram
    for label1 in features.labels:
        features.add_feature( lambda x, y, l=label1: 1 if y == l else 0 )
        features.add_feature_edge( lambda y_, y, l=label1: 1 if y_ == l else 0 )
        for label2 in features.labels:
            features.add_feature_edge( lambda y_, y, l1=label1, l2=label2: 1 if y_ == l1 and y == l2 else 0 )

    return features

class CountDict(dict):
    def __getitem__(self, key):
        return super(CountDict,self).get(key, 0)

def wce_output_tagging(text, label, prob, tagged_label):
    '''tagging & output'''

    if all(x=="head" for x in label):
        print "log_prob:", prob

        cur_text = [] # texts with current label
        cur_label = None
        for x in zip(tagged_label, text):
            if cur_label != x[0]:
                wce_output(cur_label, cur_text)
                cur_text = []
                cur_label = x[0]
            cur_text.append(x[1].org_text[0:64].replace("\n", " "))
        wce_output(cur_label, cur_text)
    else:
        compare = zip(label, tagged_label, text)
        print "log_prob:", prob, " rate:", len(filter(lambda x:x[0]==x[1], compare)), "/", len(compare)
        for x in compare:
            if x[0] != x[1]:
                print "----------", x[0], "=>", x[1]
                print x[2].org_text[0:400].strip()

def wce_output(label, text):
    if len(text)==0: return
    if len(text)<=7:
        for t in text: print "[%s] %s" % (label, t)
    else:
        for t in text[:3]: print "[%s] %s" % (label, t)
        print ": (", len(text)-6, "paragraphs)"
        for t in text[-3:]: print "[%s] %s" % (label, t)


def main():
    parser = OptionParser()
    parser.add_option("-d", dest="training_dir", help="training data directory")
    parser.add_option("-t", dest="test_dir", help="test data directory")
    parser.add_option("-f", dest="test_file", help="test data file")
    parser.add_option("-m", dest="model", help="model file")
    parser.add_option("-b", dest="body", action="store_true", help="output body")
    parser.add_option("-l", dest="regularity", type="int", help="regularity. 0=none, 1=L1, 2=L2 [2]", default=2)
    parser.add_option("--l1", dest="fobos_l1", action="store_true", help="FOBOS L1", default=False)
    (options, args) = parser.parse_args()
    if not options.training_dir and not options.model:
        parser.error("need training data directory(-d) or model file(-m)")

    theta = LABELS = None
    if options.model and os.path.isfile(options.model):
        with open(options.model, 'r') as f:
            LABELS, theta = pickle.loads(f.read())
    if options.training_dir:
        texts, labels = load_dir(options.training_dir)
        if LABELS == None:
            LABELS = unique(flatten(labels))

    features = wce_features(LABELS)
    crf = CRF(features, options.regularity)

    if options.training_dir:
        fvs = [FeatureVector(features, x, y) for x, y in zip(texts, labels)]

        # initial parameter (pick up max in 10 random parameters)
        if theta == None:
            theta = sorted([crf.random_param() for i in range(10)], key=lambda t:crf.likelihood(fvs, t))[-1]

        # inference
        print "features:", features.size()
        print "labels:", len(features.labels), features.labels
        print "log likelihood (before inference):", crf.likelihood(fvs, theta)
        if options.fobos_l1:
            eta = 0.000001
            for i in range(0):
                for fv in fvs:
                    theta += eta * crf.gradient_likelihood([fv], theta)
                    print i, "log likelihood:", crf.likelihood(fvs, theta)
                eta *= 0.98
            lmd = 1
            while lmd < 200:
                for i in range(50):
                    theta += eta * crf.gradient_likelihood(fvs, theta)
                    lmd_eta = lmd * eta
                    theta = (theta > lmd_eta) * (theta - lmd_eta) + (theta < -lmd_eta) * (theta + lmd_eta)
                    if i % 10 == 5: print i, "log likelihood:", crf.likelihood(fvs, theta)
                    #eta *= 0.95
                import numpy
                print "%d : relevant features = %d / %d" % (lmd, (numpy.abs(theta) > 0.00001).sum(), theta.size)
                with open(options.model + str(lmd), 'w') as f:
                    f.write(pickle.dumps((LABELS, theta)))
                lmd += 1
        else:
            theta = crf.inference(fvs, theta)
        print "log likelihood (after inference):", crf.likelihood(fvs, theta)
        if options.model:
            with open(options.model, 'w') as f:
                f.write(pickle.dumps((LABELS, theta)))
    elif features.size() != len(theta):
        raise ValueError, "model's length not equal feature's length."

    if options.test_dir:
        test_files = glob.glob(options.test_dir + '/*.htm*')
    elif options.test_file:
        test_files = [options.test_file]
    else:
        test_files = []

    for x in sorted(theta):
        print x,
    print

    corrects = blocks = 0
    for i, filename in enumerate(test_files):
        if not options.body: print "========== test = ", i
        text, label = load_file(filename)
        fv = FeatureVector(features, text)
        prob, ys = crf.tagging(fv, theta)
        tagged_label = features.id2label(ys)

        cor, blo = len(filter(lambda x:x[0]==x[1], zip(label, tagged_label))), len(label)
        corrects += cor
        blocks += blo
        print "log_likely = %.3f, rate = %d / %d" % (prob, cor, blo)

        if options.body:
            for x, l in zip(text, tagged_label):
                if l == "body": print re.sub(r'\s+', ' ', re.sub(r'(?s)<[^>]+>', '', x.org_text)).strip()
        else:
            #wce_output_tagging(text, label, prob, tagged_label)
            map = CountDict()
            for x in zip(label, tagged_label):
                map[x] += 1
            for x in sorted(map):
                print x[0], " => ", x[1], " : ", map[x]
    if blocks > 0:
        print "total : %d / %d = %.3f%%" % (corrects, blocks, 100.0 * corrects / blocks)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = hdplda
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Hierarchical Dirichlet Process - Latent Dirichlet Allocation
# This code is available under the MIT License.
# (c)2010-2011 Nakatani Shuyo / Cybozu Labs Inc.
# (refer to "Hierarchical Dirichlet Processes"(Teh et.al, 2005))

import numpy

class HDPLDA:
    def __init__(self, alpha, gamma, base, docs, V):
        self.alpha = alpha
        self.base = base
        self.gamma = gamma
        self.V = V

        self.x_ji = docs # vocabulary for each document and term
        self.t_ji = [numpy.zeros(len(x_i), dtype=int) - 1 for x_i in docs] # table for each document and term (without assignment)
        self.k_jt = [[] for x_i in docs] # topic for each document and table
        self.n_jt = [numpy.ndarray(0,dtype=int) for x_i in docs] # number of terms for each document and table

        self.tables = [[] for x_i in docs] # available id of tables for each document
        self.n_tables = 0

        self.m_k = numpy.ndarray(0,dtype=int)  # number of tables for each topic
        self.n_k = numpy.ndarray(0,dtype=int)  # number of terms for each topic
        self.n_kv = numpy.ndarray((0, V),dtype=int) # number of terms for each topic and vocabulary

        self.topics = [] # available id of topics

        # memoization
        self.updated_n_tables()
        self.Vbase = V * base
        self.gamma_f_k_new_x_ji = gamma / V
        self.cur_log_base_cache = [0]
        self.cur_log_V_base_cache = [0]


    def inference(self):
        for j, x_i in enumerate(self.x_ji):
            for i in range(len(x_i)):
                self.sampling_table(j, i)
            for t in self.tables[j]:
                self.sampling_k(j, t)

    def worddist(self):
        return [(self.n_kv[k] + self.base) / (self.n_k[k] + self.Vbase) for k in self.topics]

    def perplexity(self):
        phi = self.worddist()
        phi.append(numpy.zeros(self.V) + 1.0 / self.V)
        log_per = 0
        N = 0
        gamma_over_T_gamma = self.gamma / (self.n_tables + self.gamma)
        for j, x_i in enumerate(self.x_ji):
            p_k = numpy.zeros(self.m_k.size)    # topic dist for document 
            for t in self.tables[j]:
                k = self.k_jt[j][t]
                p_k[k] += self.n_jt[j][t]       # n_jk
            len_x_alpha = len(x_i) + self.alpha
            p_k /= len_x_alpha
            
            p_k_parent = self.alpha / len_x_alpha
            p_k += p_k_parent * (self.m_k / (self.n_tables + self.gamma))
            
            theta = [p_k[k] for k in self.topics]
            theta.append(p_k_parent * gamma_over_T_gamma)

            for v in x_i:
                log_per -= numpy.log(numpy.inner([p[v] for p in phi], theta))
            N += len(x_i)
        return numpy.exp(log_per / N)

    def dump(self, disp_x=False):
        if disp_x: print "x_ji:", self.x_ji
        print "t_ji:", self.t_ji
        print "k_jt:", self.k_jt
        print "n_kv:", self.n_kv
        print "n_jt:", self.n_jt
        print "n_k:", self.n_k
        print "m_k:", self.m_k
        print "tables:", self.tables
        print "topics:", self.topics


    # internal methods from here

    # cache for faster calcuration
    def updated_n_tables(self):
        self.alpha_over_T_gamma = self.alpha / (self.n_tables + self.gamma)

    def cur_log_base(self, n):
        """cache of \sum_{i=0}^{n-1} numpy.log(i + self.base)"""
        N = len(self.cur_log_base_cache)
        if n < N: return self.cur_log_base_cache[n]
        s = self.cur_log_base_cache[-1]
        while N <= n:
            s += numpy.log(N + self.base - 1)
            self.cur_log_base_cache.append(s)
            N += 1
        return s

    def cur_log_V_base(self, n):
        """cache of \sum_{i=0}^{n-1} numpy.log(i + self.base * self.V)"""
        N = len(self.cur_log_V_base_cache)
        if n < N: return self.cur_log_V_base_cache[n]
        s = self.cur_log_V_base_cache[-1]
        while N <= n:
            s += numpy.log(N + self.Vbase - 1)
            self.cur_log_V_base_cache.append(s)
            N += 1
        return s

    def log_f_k_new_x_jt(self, n_jt, n_tv, n_kv = None, n_k = 0):
        p = self.cur_log_V_base(n_k) - self.cur_log_V_base(n_k + n_jt)
        for (v_l, n_l) in n_tv:
            n0 = n_kv[v_l] if n_kv != None else 0
            p += self.cur_log_base(n0 + n_l) - self.cur_log_base(n0)
        return p

    def count_n_jtv(self, j, t, k_old):
        """count n_jtv and decrease n_kv for k_old"""
        x_i = self.x_ji[j]
        t_i = self.t_ji[j]
        n_jtv = dict()
        for i, t1 in enumerate(t_i):
            if t1 == t:
                v = x_i[i]
                self.n_kv[k_old, v] -= 1
                if v in n_jtv:
                    n_jtv[v] += 1
                else:
                    n_jtv[v] = 1
        return n_jtv.items()


    # sampling t (table) from posterior
    def sampling_table(self, j, i):
        v = self.x_ji[j][i]
        tables = self.tables[j]
        t_old = self.t_ji[j][i]
        if t_old >=0:
            k_old = self.k_jt[j][t_old]

            # decrease counters
            self.n_kv[k_old, v] -= 1
            self.n_k[k_old] -= 1
            self.n_jt[j][t_old] -= 1

            if self.n_jt[j][t_old]==0:
                # table that all guests are gone
                tables.remove(t_old)
                self.m_k[k_old] -= 1
                self.n_tables -= 1
                self.updated_n_tables()

                if self.m_k[k_old] == 0:
                    # topic (dish) that all guests are gone
                    self.topics.remove(k_old)

        # sampling from posterior p(t_ji=t)
        t_new = self.sampling_t(j, i, v, tables)

        # increase counters
        self.t_ji[j][i] = t_new
        self.n_jt[j][t_new] += 1

        k_new = self.k_jt[j][t_new]
        self.n_k[k_new] += 1
        self.n_kv[k_new, v] += 1

    def sampling_t(self, j, i, v, tables):
        f_k = (self.n_kv[:, v] + self.base) / (self.n_k + self.Vbase)
        p_t = [self.n_jt[j][t] * f_k[self.k_jt[j][t]] for t in tables]
        p_x_ji = numpy.inner(self.m_k, f_k) + self.gamma_f_k_new_x_ji
        p_t.append(p_x_ji * self.alpha_over_T_gamma)

        p_t = numpy.array(p_t, copy=False)
        p_t /= p_t.sum()
        drawing = numpy.random.multinomial(1, p_t).argmax()
        if drawing < len(tables):
            return tables[drawing]
        else:
            return self.new_table(j, i, f_k)

    # Assign guest x_ji to a new table and draw topic (dish) of the table
    def new_table(self, j, i, f_k):
        # search a spare table ID
        T_j = self.n_jt[j].size
        for t_new in range(T_j):
            if t_new not in self.tables[j]: break
        else:
            # new table ID (no spare)
            t_new = T_j
            self.n_jt[j].resize(t_new+1)
            self.n_jt[j][t_new] = 0
            self.k_jt[j].append(0)
        self.tables[j].append(t_new)
        self.n_tables += 1
        self.updated_n_tables()

        # sampling of k for new topic(= dish of new table)
        p_k = [self.m_k[k] * f_k[k] for k in self.topics]
        p_k.append(self.gamma_f_k_new_x_ji)
        k_new = self.sampling_topic(numpy.array(p_k, copy=False))

        self.k_jt[j][t_new] = k_new
        self.m_k[k_new] += 1

        return t_new

    # sampling topic
    # In the case of new topic, allocate resource for parameters
    def sampling_topic(self, p_k):
        drawing = numpy.random.multinomial(1, p_k / p_k.sum()).argmax()
        if drawing < len(self.topics):
            # existing topic
            k_new = self.topics[drawing]
        else:
            # new topic
            K = self.m_k.size
            for k_new in range(K):
                # recycle table ID, if a spare ID exists
                if k_new not in self.topics: break
            else:
                # new table ID, if otherwise
                k_new = K
                self.n_k = numpy.resize(self.n_k, k_new + 1)
                self.n_k[k_new] = 0
                self.m_k = numpy.resize(self.m_k, k_new + 1)
                self.m_k[k_new] = 0
                self.n_kv = numpy.resize(self.n_kv, (k_new+1, self.V))
                self.n_kv[k_new, :] = numpy.zeros(self.V, dtype=int)
            self.topics.append(k_new)
        return k_new

    def sampling_k(self, j, t):
        """sampling k (dish=topic) from posterior"""
        k_old = self.k_jt[j][t]
        n_jt = self.n_jt[j][t]
        self.m_k[k_old] -= 1
        self.n_k[k_old] -= n_jt
        if self.m_k[k_old] == 0:
            self.topics.remove(k_old)

        # sampling of k
        n_jtv = self.count_n_jtv(j, t, k_old) # decrement n_kv also in this method
        K = len(self.topics)
        log_p_k = numpy.zeros(K+1)
        for i, k in enumerate(self.topics):
            log_p_k[i] = self.log_f_k_new_x_jt(n_jt, n_jtv, self.n_kv[k, :], self.n_k[k]) + numpy.log(self.m_k[k])
        log_p_k[K] = self.log_f_k_new_x_jt(n_jt, n_jtv) + numpy.log(self.gamma)
        k_new = self.sampling_topic(numpy.exp(log_p_k - log_p_k.max())) # for too small

        # update counters
        self.k_jt[j][t] = k_new
        self.m_k[k_new] += 1
        self.n_k[k_new] += self.n_jt[j][t]
        for v, t1 in zip(self.x_ji[j], self.t_ji[j]):
            if t1 != t: continue
            self.n_kv[k_new, v] += 1


def hdplda_learning(hdplda, iteration):
    for i in range(iteration):
        hdplda.inference()
        print "-%d K=%d p=%f" % (i + 1, len(hdplda.topics), hdplda.perplexity())
    return hdplda

def main():
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-f", dest="filename", help="corpus filename")
    parser.add_option("-c", dest="corpus", help="using range of Brown corpus' files(start:end)")
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=numpy.random.gamma(1, 1))
    parser.add_option("--gamma", dest="gamma", type="float", help="parameter gamma", default=numpy.random.gamma(1, 1))
    parser.add_option("--beta", dest="base", type="float", help="parameter of beta measure H", default=0.5)
    parser.add_option("-k", dest="K", type="int", help="initial number of topics", default=1)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=10)
    parser.add_option("-s", dest="stopwords", type="int", help="0=exclude stop words, 1=include stop words", default=1)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    parser.add_option("--df", dest="df", type="int", help="threshold of document freaquency to cut words", default=0)
    (options, args) = parser.parse_args()
    if not (options.filename or options.corpus): parser.error("need corpus filename(-f) or corpus range(-c)")
    if options.seed != None:
        numpy.random.seed(options.seed)

    import vocabulary
    if options.filename:
        corpus = vocabulary.load_file(options.filename)
    else:
        corpus = vocabulary.load_corpus(options.corpus)
        if not corpus: parser.error("corpus range(-c) forms 'start:end'")

    voca = vocabulary.Vocabulary(options.stopwords==0)
    docs = [voca.doc_to_ids(doc) for doc in corpus]
    if options.df > 0: docs = voca.cut_low_freq(docs, options.df)

    hdplda = HDPLDA(options.alpha, options.gamma, options.base, docs, voca.size())
    print "corpus=%d words=%d alpha=%.3f gamma=%.3f base=%.3f stopwords=%d" % (len(corpus), len(voca.vocas), options.alpha, options.gamma, options.base, options.stopwords)
    #hdplda.dump()

    #import cProfile
    #cProfile.runctx('hdplda_learning(hdplda, options.iteration)', globals(), locals(), 'hdplda.profile')
    hdplda_learning(hdplda, options.iteration)

    """
    phi = hdplda.worddist()
    for k, phi_k in enumerate(phi):
        print "\n-- topic: %d" % k
        for w in numpy.argsort(-phi_k)[:20]:
            print "%s: %f" % (voca[w], phi_k[w])
    """

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = hdplda2
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Hierarchical Dirichlet Process - Latent Dirichlet Allocation
# This code is available under the MIT License.
# (c)2010-2011 Nakatani Shuyo / Cybozu Labs Inc.
# (refer to "Hierarchical Dirichlet Processes"(Teh et.al, 2005))

import numpy
from scipy.special import gammaln

class DefaultDict(dict):
    def __init__(self, v):
        self.v = v
        dict.__init__(self)
    def __getitem__(self, k):
        return dict.__getitem__(self, k) if k in self else self.v
    def update(self, d):
        dict.update(self, d)
        return self

class HDPLDA:
    def __init__(self, alpha, beta, gamma, docs, V):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.V = V
        self.M = len(docs)

        # t : table index for document j
        #     t=0 means to draw a new table
        self.using_t = [[0] for j in xrange(self.M)]

        # k : dish(topic) index
        #     k=0 means to draw a new dish
        self.using_k = [0]

        self.x_ji = docs # vocabulary for each document and term
        self.k_jt = [numpy.zeros(1 ,dtype=int) for j in xrange(self.M)]   # topics of document and table
        self.n_jt = [numpy.zeros(1 ,dtype=int) for j in xrange(self.M)]   # number of terms for each table of document
        self.n_jtv = [[None] for j in xrange(self.M)]

        self.m = 0
        self.m_k = numpy.ones(1 ,dtype=int)  # number of tables for each topic
        self.n_k = numpy.array([self.beta * self.V]) # number of terms for each topic ( + beta * V )
        self.n_kv = [DefaultDict(0)]            # number of terms for each topic and vocabulary ( + beta )

        # table for each document and term (-1 means not-assigned)
        self.t_ji = [numpy.zeros(len(x_i), dtype=int) - 1 for x_i in docs]

    def inference(self):
        for j, x_i in enumerate(self.x_ji):
            for i in xrange(len(x_i)):
                self.sampling_t(j, i)
        for j in xrange(self.M):
            for t in self.using_t[j]:
                if t != 0: self.sampling_k(j, t)

    def worddist(self):
        """return topic-word distribution without new topic"""
        return [DefaultDict(self.beta / self.n_k[k]).update(
            (v, n_kv / self.n_k[k]) for v, n_kv in self.n_kv[k].iteritems())
                for k in self.using_k if k != 0]

    def docdist(self):
        """return document-topic distribution with new topic"""

        # am_k = effect from table-dish assignment
        am_k = numpy.array(self.m_k, dtype=float)
        am_k[0] = self.gamma
        am_k *= self.alpha / am_k[self.using_k].sum()

        theta = []
        for j, n_jt in enumerate(self.n_jt):
            p_jk = am_k.copy()
            for t in self.using_t[j]:
                if t == 0: continue
                k = self.k_jt[j][t]
                p_jk[k] += n_jt[t]
            p_jk = p_jk[self.using_k]
            theta.append(p_jk / p_jk.sum())

        return numpy.array(theta)

    def perplexity(self):
        phi = [DefaultDict(1.0/self.V)] + self.worddist()
        theta = self.docdist()
        log_likelihood = 0
        N = 0
        for x_ji, p_jk in zip(self.x_ji, theta):
            for v in x_ji:
                word_prob = sum(p * p_kv[v] for p, p_kv in zip(p_jk, phi))
                log_likelihood -= numpy.log(word_prob)
            N += len(x_ji)
        return numpy.exp(log_likelihood / N)



    def dump(self, disp_x=False):
        if disp_x: print "x_ji:", self.x_ji
        print "using_t:", self.using_t
        print "t_ji:", self.t_ji
        print "using_k:", self.using_k
        print "k_jt:", self.k_jt
        print "----"
        print "n_jt:", self.n_jt
        print "n_jtv:", self.n_jtv
        print "n_k:", self.n_k
        print "n_kv:", self.n_kv
        print "m:", self.m
        print "m_k:", self.m_k
        print


    def sampling_t(self, j, i):
        """sampling t (table) from posterior"""
        self.leave_from_table(j, i)

        v = self.x_ji[j][i]
        f_k = self.calc_f_k(v)
        assert f_k[0] == 0 # f_k[0] is a dummy and will be erased

        # sampling from posterior p(t_ji=t)
        p_t = self.calc_table_posterior(j, f_k)
        if len(p_t) > 1 and p_t[1] < 0: self.dump()
        t_new = self.using_t[j][numpy.random.multinomial(1, p_t).argmax()]
        if t_new == 0:
            p_k = self.calc_dish_posterior_w(f_k)
            k_new = self.using_k[numpy.random.multinomial(1, p_k).argmax()]
            if k_new == 0:
                k_new = self.add_new_dish()
            t_new = self.add_new_table(j, k_new)

        # increase counters
        self.seat_at_table(j, i, t_new)

    def leave_from_table(self, j, i):
        t = self.t_ji[j][i]
        if t  > 0:
            k = self.k_jt[j][t]
            assert k > 0

            # decrease counters
            v = self.x_ji[j][i]
            self.n_kv[k][v] -= 1
            self.n_k[k] -= 1
            self.n_jt[j][t] -= 1
            self.n_jtv[j][t][v] -= 1

            if self.n_jt[j][t] == 0:
                self.remove_table(j, t)

    def remove_table(self, j, t):
        """remove the table where all guests are gone"""
        k = self.k_jt[j][t]
        self.using_t[j].remove(t)
        self.m_k[k] -= 1
        self.m -= 1
        assert self.m_k[k] >= 0
        if self.m_k[k] == 0:
            # remove topic (dish) where all tables are gone
            self.using_k.remove(k)

    def calc_f_k(self, v):
        return [n_kv[v] for n_kv in self.n_kv] / self.n_k

    def calc_table_posterior(self, j, f_k):
        using_t = self.using_t[j]
        p_t = self.n_jt[j][using_t] * f_k[self.k_jt[j][using_t]]
        p_x_ji = numpy.inner(self.m_k, f_k) + self.gamma / self.V
        p_t[0] = p_x_ji * self.alpha / (self.gamma + self.m)
        #print "un-normalized p_t = ", p_t
        return p_t / p_t.sum()

    def seat_at_table(self, j, i, t_new):
        assert t_new in self.using_t[j]
        self.t_ji[j][i] = t_new
        self.n_jt[j][t_new] += 1

        k_new = self.k_jt[j][t_new]
        self.n_k[k_new] += 1

        v = self.x_ji[j][i]
        self.n_kv[k_new][v] += 1
        self.n_jtv[j][t_new][v] += 1

    # Assign guest x_ji to a new table and draw topic (dish) of the table
    def add_new_table(self, j, k_new):
        assert k_new in self.using_k
        for t_new, t in enumerate(self.using_t[j]):
            if t_new != t: break
        else:
            t_new = len(self.using_t[j])
            self.n_jt[j].resize(t_new+1)
            self.k_jt[j].resize(t_new+1)
            self.n_jtv[j].append(None)

        self.using_t[j].insert(t_new, t_new)
        self.n_jt[j][t_new] = 0  # to make sure
        self.n_jtv[j][t_new] = DefaultDict(0)

        self.k_jt[j][t_new] = k_new
        self.m_k[k_new] += 1
        self.m += 1

        return t_new

    def calc_dish_posterior_w(self, f_k):
        "calculate dish(topic) posterior when one word is removed"
        p_k = (self.m_k * f_k)[self.using_k]
        p_k[0] = self.gamma / self.V
        return p_k / p_k.sum()



    def sampling_k(self, j, t):
        """sampling k (dish=topic) from posterior"""
        self.leave_from_dish(j, t)

        # sampling of k
        p_k = self.calc_dish_posterior_t(j, t)
        k_new = self.using_k[numpy.random.multinomial(1, p_k).argmax()]
        if k_new == 0:
            k_new = self.add_new_dish()

        self.seat_at_dish(j, t, k_new)

    def leave_from_dish(self, j, t):
        """
        This makes the table leave from its dish and only the table counter decrease.
        The word counters (n_k and n_kv) stay.
        """
        k = self.k_jt[j][t]
        assert k > 0
        assert self.m_k[k] > 0
        self.m_k[k] -= 1
        self.m -= 1
        if self.m_k[k] == 0:
            self.using_k.remove(k)
            self.k_jt[j][t] = 0

    def calc_dish_posterior_t(self, j, t):
        "calculate dish(topic) posterior when one table is removed"
        k_old = self.k_jt[j][t]     # it may be zero (means a removed dish)
        #print "V=", self.V, "beta=", self.beta, "n_k=", self.n_k
        Vbeta = self.V * self.beta
        n_k = self.n_k.copy()
        n_jt = self.n_jt[j][t]
        n_k[k_old] -= n_jt
        n_k = n_k[self.using_k]
        log_p_k = numpy.log(self.m_k[self.using_k]) + gammaln(n_k) - gammaln(n_k + n_jt)
        log_p_k_new = numpy.log(self.gamma) + gammaln(Vbeta) - gammaln(Vbeta + n_jt)
        #print "log_p_k_new+=gammaln(",Vbeta,") - gammaln(",Vbeta + n_jt,")"

        gammaln_beta = gammaln(self.beta)
        for w, n_jtw in self.n_jtv[j][t].iteritems():
            assert n_jtw >= 0
            if n_jtw == 0: continue
            n_kw = numpy.array([n.get(w, self.beta) for n in self.n_kv])
            n_kw[k_old] -= n_jtw
            n_kw = n_kw[self.using_k]
            n_kw[0] = 1 # dummy for logarithm's warning
            if numpy.any(n_kw <= 0): print n_kw # for debug
            log_p_k += gammaln(n_kw + n_jtw) - gammaln(n_kw)
            log_p_k_new += gammaln(self.beta + n_jtw) - gammaln_beta
            #print "log_p_k_new+=gammaln(",self.beta + n_jtw,") - gammaln(",self.beta,"), w=",w
        log_p_k[0] = log_p_k_new
        #print "un-normalized p_k = ", numpy.exp(log_p_k)
        p_k = numpy.exp(log_p_k - log_p_k.max())
        return p_k / p_k.sum()

    def seat_at_dish(self, j, t, k_new):
        self.m += 1
        self.m_k[k_new] += 1

        k_old = self.k_jt[j][t]     # it may be zero (means a removed dish)
        if k_new != k_old:
            self.k_jt[j][t] = k_new

            n_jt = self.n_jt[j][t]
            if k_old != 0: self.n_k[k_old] -= n_jt
            self.n_k[k_new] += n_jt
            for v, n in self.n_jtv[j][t].iteritems():
                if k_old != 0: self.n_kv[k_old][v] -= n
                self.n_kv[k_new][v] += n


    def add_new_dish(self):
        "This is commonly used by sampling_t and sampling_k."
        for k_new, k in enumerate(self.using_k):
            if k_new != k: break
        else:
            k_new = len(self.using_k)
            if k_new >= len(self.n_kv):
                self.n_k = numpy.resize(self.n_k, k_new + 1)
                self.m_k = numpy.resize(self.m_k, k_new + 1)
                self.n_kv.append(None)
            assert k_new == self.using_k[-1] + 1
            assert k_new < len(self.n_kv)

        self.using_k.insert(k_new, k_new)
        self.n_k[k_new] = self.beta * self.V
        self.m_k[k_new] = 0
        self.n_kv[k_new] = DefaultDict(self.beta)
        return k_new



def hdplda_learning(hdplda, iteration):
    for i in range(iteration):
        hdplda.inference()
        print "-%d K=%d p=%f" % (i + 1, len(hdplda.using_k)-1, hdplda.perplexity())
    return hdplda

def output_summary(hdplda, voca, fp=None):
    if fp==None:
        import sys
        fp = sys.stdout
    K = len(hdplda.using_k) - 1
    kmap = dict((k,i-1) for i, k in enumerate(hdplda.using_k))
    dishcount = numpy.zeros(K, dtype=int)
    wordcount = [DefaultDict(0) for k in xrange(K)]
    for j, x_ji in enumerate(hdplda.x_ji):
        for v, t in zip(x_ji, hdplda.t_ji[j]):
            k = kmap[hdplda.k_jt[j][t]]
            dishcount[k] += 1
            wordcount[k][v] += 1

    phi = hdplda.worddist()
    for k, phi_k in enumerate(phi):
        fp.write("\n-- topic: %d (%d words)\n" % (hdplda.using_k[k+1], dishcount[k]))
        for w in sorted(phi_k, key=lambda w:-phi_k[w])[:20]:
            fp.write("%s: %f (%d)\n" % (voca[w], phi_k[w], wordcount[k][w]))

    fp.write("--- document-topic distribution\n")
    theta = hdplda.docdist()
    for j, theta_j in enumerate(theta):
        fp.write("%d\t%s\n" % (j, "\t".join("%.3f" % p for p in theta_j[1:])))

    fp.write("--- dishes for document\n")
    for j, using_t in enumerate(hdplda.using_t):
        fp.write("%d\t%s\n" % (j, "\t".join(str(hdplda.k_jt[j][t]) for t in using_t if t>0)))


def main():
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-f", dest="filename", help="corpus filename")
    parser.add_option("-c", dest="corpus", help="using range of Brown corpus' files(start:end)")
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=numpy.random.gamma(1, 1))
    parser.add_option("--gamma", dest="gamma", type="float", help="parameter gamma", default=numpy.random.gamma(1, 1))
    parser.add_option("--beta", dest="beta", type="float", help="parameter of beta measure H", default=0.5)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=10)
    parser.add_option("-s", dest="stopwords", type="int", help="0=exclude stop words, 1=include stop words", default=1)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    parser.add_option("--df", dest="df", type="int", help="threshold of document freaquency to cut words", default=0)
    (options, args) = parser.parse_args()
    if not (options.filename or options.corpus): parser.error("need corpus filename(-f) or corpus range(-c)")
    if options.seed != None:
        numpy.random.seed(options.seed)

    import vocabulary
    if options.filename:
        corpus = vocabulary.load_file(options.filename)
    else:
        corpus = vocabulary.load_corpus(options.corpus)
        if not corpus: parser.error("corpus range(-c) forms 'start:end'")

    voca = vocabulary.Vocabulary(options.stopwords==0)
    docs = [voca.doc_to_ids(doc) for doc in corpus]
    if options.df > 0: docs = voca.cut_low_freq(docs, options.df)

    hdplda = HDPLDA(options.alpha, options.gamma, options.beta, docs, voca.size())
    print "corpus=%d words=%d alpha=%.3f gamma=%.3f beta=%.3f stopwords=%d" % (len(corpus), len(voca.vocas), options.alpha, options.gamma, options.beta, options.stopwords)
    #hdplda.dump()

    #import cProfile
    #cProfile.runctx('hdplda_learning(hdplda, options.iteration)', globals(), locals(), 'hdplda.profile')
    hdplda_learning(hdplda, options.iteration)
    output_summary(hdplda, voca)



if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = hdp_online
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Online VB Inference for HDP [Wang+ AISTATS2011]
# This code is available under the MIT License.
# (c)2012 Nakatani Shuyo / Cybozu Labs Inc.

import numpy
from scipy.special import digamma

def golden_section_search(func, min, max):
    x1, x3 = min, max
    x2 = (x3 - x1) / (3 + math.sqrt(5)) * 2 + x1
    f1, f2, f3 = func(x1), func(x2), func(x3)
    while (x3 - x1) > 0.0001 * (max - min):
        x4 = x1 + x3 - x2
        f4 = func(x4)
        if f4 < f2:
            if x2 < x4:
                x1, x2 = x2, x4
                f1, f2 = f2, f4
            else:
                x2, x3 = x4, x2
                f2, f3 = f4, f2
        else:
            if x4 > x2:
                x3, f3 = x4, f4
            else:
                x1, f1 = x4, f4
    return x2, f2

class OnlineHDP:
    def __init__(self, K, T, alpha, beta, gamma, docs, V, kappa=0.6, tau=64):
        self.K = K
        self.T = T
        self.alpha = alpha
        self.eta = beta
        self.gamma = gamma

        self.w_jn = docs
        self.D = len(docs)
        self.V = V

        #self.lambda_kw = numpy.ones((self.K, self.V)) / self.K
        self.lambda_kw = numpy.random.gamma(0.1, 0.1, (self.K, self.V))
        self.u_k = numpy.random.gamma(1.0, 1.0, self.K - 1)
        self.v_k = numpy.random.gamma(1.0, 1.0, self.K - 1)

        self.zeta_jtn = [numpy.ones((self.T, len(w_n))) / self.T for w_n in self.w_jn]

        self.tau_t0 = tau + 1
        self.minus_kappa = -kappa

    def inference(self):
        jlist = range(self.D)
        self.phi_jkt = numpy.zeros((self.D, self.K, self.T))
        numpy.random.shuffle(jlist)
        for j in jlist:
            w_n = self.w_jn[j]

            sum_zeta = self.zeta_jtn[j].sum(axis=1)
            a_t = 1 + sum_zeta
            cum_zeta = sum_zeta.cumsum()
            # (z_1+..+z_{T-1},..,Z_{T-2}+Z_{T-1},Z_{T-1},0)
            b_t = self.alpha + cum_zeta[-1] - cum_zeta

            digamma_uk_vk = digamma(self.u_k + self.v_k)
            E_log_1_minus_beta_prime = digamma(self.v_k) - digamma_uk_vk
            E_log_beta = digamma(self.u_k) - digamma_uk_vk
            E_log_beta[1:] += E_log_1_minus_beta_prime.cumsum()[:-1]
            E_log_beta.resize(self.K) # E_log_beta[K-1] = 0

            digamma_sum_lambda = digamma(self.lambda_kw.sum(axis=1))
            E_log_p_nk = [digamma(self.lambda_kw[:,w]) - digamma_sum_lambda for w in w_n]
            log_phi_tk = numpy.dot(self.zeta_jtn[j], E_log_p_nk) + E_log_beta
            phi_kt = numpy.exp(log_phi_tk.T - log_phi_tk.max(axis=1))
            phi_kt /= phi_kt.sum(axis=0)
            self.phi_jkt[j] = phi_kt

            digamma_at_bt = digamma(a_t + b_t)
            E_log_1_minus_pi_prime = digamma(b_t) - digamma_at_bt
            E_log_pi = digamma(a_t) - digamma_at_bt
            E_log_pi[1:] += E_log_1_minus_pi_prime.cumsum()[:-1]
            E_log_pi.resize(self.T) # E_log_pi[T-1] = 0

            log_zeta_nt = numpy.dot(E_log_p_nk, phi_kt) + E_log_pi
            zeta_tn = numpy.exp(log_zeta_nt.T - log_zeta_nt.max(axis=1))
            zeta_tn /= zeta_tn.sum(axis=0)
            self.zeta_jtn[j] = zeta_tn

            rho = self.tau_t0 ** self.minus_kappa
            self.tau_t0 += 1

            partial_lambda_kw = - self.lambda_kw + self.eta
            for n, w in enumerate(w_n):
                partial_lambda_kw[:,w] += self.D * numpy.dot(phi_kt, zeta_tn[:,n])
            self.lambda_kw += rho * partial_lambda_kw

            phi_k = phi_kt.sum(axis=1)
            partial_u_k = - self.u_k + 1 + self.D * phi_k[:-1]
            self.u_k += rho * partial_u_k

            cum_phi_k = phi_k.cumsum()
            partial_v_k = - self.v_k + self.gamma + self.D * (cum_phi_k[-1] - cum_phi_k)[:-1]
            self.v_k += rho * partial_v_k

    def worddist(self):
        return self.lambda_kw / self.lambda_kw.sum(axis=1)[:, None]

    def docdist(self):
        return numpy.array([self.eachdocdist(j) for j in xrange(self.D)])

    def eachdocdist(self, j):
        theta_k = numpy.dot(self.phi_jkt[j], self.zeta_jtn[j].sum(axis=1))
        return theta_k / theta_k.sum()

    def perplexity(self, docs=None):
        if docs == None: docs = self.w_jn
        phi = self.worddist()
        log_per = 0
        N = 0
        for j, doc in enumerate(docs):
            theta = self.eachdocdist(j)
            for w in doc:
                log_per -= numpy.log(numpy.inner(phi[:,w], theta))
            N += len(doc)
        return numpy.exp(log_per / N)

def lda_learning(lda, iteration, voca):
    for i in range(iteration):
        lda.inference()
        perp = lda.perplexity()
        print "-%d p=%f" % (i + 1, perp)
    output_word_topic_dist(lda, voca)

def output_word_topic_dist(lda, voca):
    zweight = numpy.zeros(lda.K)
    wordweight = numpy.zeros((voca.size(), lda.K))
    for j, wlist in enumerate(lda.w_jn):
        phi_kn = numpy.dot(lda.phi_jkt[j], lda.zeta_jtn[j])
        zweight += phi_kn.sum(axis=1)
        for n, w in enumerate(wlist):
            wordweight[w] += phi_kn[:,n]

    phi = lda.worddist()
    for k in xrange(lda.K):
        print "\n-- topic: %d (%.2f)" % (k, zweight[k])
        for w in numpy.argsort(-phi[k])[:20]:
            print "%s: %f (%.2f)" % (voca[w], phi[k,w], wordweight[w, k])

def main():
    import optparse
    import vocabulary
    parser = optparse.OptionParser()
    parser.add_option("-f", dest="filename", help="corpus filename")
    parser.add_option("-c", dest="corpus", help="using range of Brown corpus' files(start:end)")
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=0.5)
    parser.add_option("--beta", dest="beta", type="float", help="parameter beta", default=0.5)
    parser.add_option("--gamma", dest="gamma", type="float", help="parameter gamma", default=0.5)
    parser.add_option("-k", dest="K", type="int", help="number of topics", default=20)
    parser.add_option("-t", dest="T", type="int", help="number of tables for each document", default=5)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=100)
    parser.add_option("--stopwords", dest="stopwords", help="exclude stop words", action="store_true", default=False)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    parser.add_option("--df", dest="df", type="int", help="threshold of document freaquency to cut words", default=0)
    (options, args) = parser.parse_args()
    if not (options.filename or options.corpus): parser.error("need corpus filename(-f) or corpus range(-c)")

    if options.filename:
        corpus = vocabulary.load_file(options.filename)
    else:
        corpus = vocabulary.load_corpus(options.corpus)
        if not corpus: parser.error("corpus range(-c) forms 'start:end'")
    if options.seed != None:
        numpy.random.seed(options.seed)

    voca = vocabulary.Vocabulary(options.stopwords)
    docs = [voca.doc_to_ids(doc) for doc in corpus]
    if options.df > 0: docs = voca.cut_low_freq(docs, options.df)

    lda = OnlineHDP(options.K, options.T, options.alpha, options.beta, options.gamma, docs, voca.size())
    print "corpus=%d, words=%d, K=%d, T=%d, a=%.3f, b=%.3f, g=%.3f" % (len(corpus), len(voca.vocas), options.K, options.T, options.alpha, options.beta, options.gamma)

    #import cProfile
    #cProfile.runctx('lda_learning(lda, options.iteration, voca)', globals(), locals(), 'lda.profile')
    lda_learning(lda, options.iteration, voca)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = itm
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# [Hu, Boyd-Graber and Satinoff ACL2011] Interactive Topic Modeling
# This code is available under the MIT License.
# (c)2011 Nakatani Shuyo / Cybozu Labs Inc.

import numpy

class ITM:
    def __init__(self, K, alpha, beta, eta, docs, V, smartinit=True):
        self.K = K
        self.alpha = alpha # parameter of topics prior
        self.beta  = beta  # first parameter of words prior
        self.eta   = eta   # second parameter of words prior
        self.docs  = docs
        self.V = V

        self.n_d_k = numpy.zeros((len(docs), K)) + alpha     # word count of each document and topic
        self.n_k_w = numpy.zeros((K, V), dtype=int)
        self.n_j_k = []
        self.n_k = numpy.zeros(K) + V * beta    # word count of each topic
        self.c_j = []

        self.w_to_j = dict()

        self.z_d_n = [] # topics of words of documents
        for doc in docs:
            self.z_d_n.append( numpy.zeros(len(doc), dtype=int) - 1 )

    def get_constraint(self, words):
        if len(words) < 2:
            raise "need more than 2 words for constraint"

        constraint_id = -1
        diff_c_j = 0
        for w in words:
            if w in self.w_to_j:
                if constraint_id < 0:
                    constraint_id = self.w_to_j[w]
                elif constraint_id != self.w_to_j[w]:
                    raise "specified words have belonged into more than 2 constraints"
            else:
                diff_c_j += 1
        if diff_c_j == 0:
            raise "all specified words belonged the same constraint already"

        if constraint_id < 0:
            constraint_id = len(self.c_j)
            self.c_j.append(diff_c_j)
            self.n_j_k.append(numpy.zeros(self.K, dtype=int))
        else:
            self.c_j[constraint_id] += diff_c_j

        for w in words:
            self.w_to_j[w] = constraint_id

        return constraint_id

    def add_constraint_all(self, words):
        constraint_id = self.get_constraint(words)

        for z_d_n in self.z_d_n: z_d_n.fill(-1)
        self.n_d_k.fill(self.alpha)
        self.n_k_w.fill(0)
        for n_j_k in self.n_j_k: n_j_k.fill(0)
        self.n_k.fill(self.V * self.beta)

    def add_constraint_doc(self, words):
        constraint_id = self.get_constraint(words)

        unassigned = []
        for d, doc in enumerate(self.docs):
            if any(self.w_to_j.get(w, -1) == constraint_id for w in doc):
                for n, w in enumerate(doc):
                    k = self.z_d_n[d][n]
                    self.n_k_w[k, w] -= 1
                    self.n_k[k] -= 1
                    j = self.w_to_j.get(w, -1)
                    if j >= 0:
                        self.n_j_k[j][k] -= 1

                self.n_d_k[d].fill(self.alpha)
                self.z_d_n[d].fill(-1)
                unassigned.append(d)
        self.n_j_k[constraint_id].fill(0)
        print "unassigned all words in document [%s]" % ",".join(unassigned)

    def add_constraint_term(self, words):
        constraint_id = self.get_constraint(words)

        self.n_j_k[constraint_id].fill(0)
        for d, doc in enumerate(self.docs):
            for n, w in enumerate(doc):
                if self.w_to_j.get(w, -1) == constraint_id:
                    k = self.z_d_n[d][n]
                    self.n_d_k[d][k] -= 1
                    self.n_k_w[k, w] -= 1
                    self.n_k[k] -= 1
                    self.z_d_n[d][n] = -1

    def add_constraint_none(self, words):
        constraint_id = self.get_constraint(words)

        n_j_k = self.n_j_k[constraint_id]
        n_j_k.fill(0)
        for w in words:
            n_j_k += self.n_k_w[:, w]

    def verify_topic(self):
        n_k_w = numpy.zeros((self.K, self.V), dtype=int)
        n_j_k = numpy.zeros((len(self.c_j), self.K), dtype=int)
        for doc, z_n in zip(self.docs, self.z_d_n):
            for w, k in zip(doc, z_n):
                if k >=0:
                    n_k_w[k, w] += 1
                    j = self.w_to_j.get(w, -1)
                    if j >= 0:
                        n_j_k[j, k] += 1

        c_j = numpy.zeros(len(self.c_j), dtype=int)
        for w in self.w_to_j:
            c_j[self.w_to_j[w]] += 1

        if numpy.abs(self.n_k - self.n_k_w.sum(1) - self.V * self.beta).max() > 0.001:
            raise "there are conflicts between n_k and n_k_w"
        if numpy.abs(self.n_d_k.sum(0) - self.n_k + (self.V * self.beta - len(self.docs) * self.alpha)).max() > 0.001:

            print self.n_d_k.sum(0) - len(self.docs) * self.alpha
            print self.n_k - self.V * self.beta
            raise "there are conflicts between n_d_k and n_k"
        if numpy.any(c_j != self.c_j):
            print c_j
            print self.c_j
            raise "there are conflicts between w_to_j and c_j"
        if numpy.any(n_k_w != self.n_k_w):
            raise "there are conflicts between z_d_n and n_k_w"
        if numpy.any(n_j_k != self.n_j_k):
            raise "there are conflicts between z_d_n/w_to_j and n_j_k"

    def inference(self):
        beta = self.beta
        eta = self.eta
        for d, doc in enumerate(self.docs):
            z_n = self.z_d_n[d]
            n_d_k = self.n_d_k[d]
            for n, w in enumerate(doc):
                k = z_n[n]
                j = self.w_to_j.get(w, -1)
                if k >= 0:
                    n_d_k[k] -= 1
                    self.n_k_w[k, w] -= 1
                    self.n_k[k] -= 1
                    if j >= 0:
                        self.n_j_k[j][k] -= 1

                # sampling topic new_z for t
                if j >= 0:
                    c_j = self.c_j[j]
                    n_j_k = self.n_j_k[j]
                    p_z = n_d_k * (self.n_k_w[:, w] + eta)  * (n_j_k + c_j * beta) / ((n_j_k + c_j * eta) * self.n_k)
                else:
                    p_z = n_d_k * (self.n_k_w[:, w] + beta) / self.n_k
                new_k = z_n[n] = numpy.random.multinomial(1, p_z / p_z.sum()).argmax()

                # set z the new topic and increment counters
                n_d_k[new_k] += 1
                self.n_k_w[new_k, w] += 1
                self.n_k[new_k] += 1
                if j >= 0:
                    self.n_j_k[j][new_k] += 1

    def worddist(self):
        """get topic-word distribution"""
        dist = (self.n_k_w + self.beta) / self.n_k[:, numpy.newaxis]
        beta = self.beta
        eta = self.eta
        for w in self.w_to_j:
            j = self.w_to_j[w]
            c_j = self.c_j[j]
            n_j_k = self.n_j_k[j]
            dist[:, w] = (self.n_k_w[:, w] + eta) * (n_j_k + c_j * beta) / ((n_j_k + c_j * eta) * self.n_k)
        return dist

    def perplexity(self, docs=None):
        if docs == None: docs = self.docs
        phi = self.worddist()
        log_per = 0
        N = 0
        Kalpha = self.K * self.alpha
        for d, doc in enumerate(docs):
            theta = self.n_d_k[d] / (len(self.docs[d]) + Kalpha)
            for w in doc:
                log_per -= numpy.log(numpy.inner(phi[:,w], theta))
            N += len(doc)
        return numpy.exp(log_per / N)

def lda_learning(lda, iteration, voca):
    print "\n== perplexity for each inference =="
    for i in range(iteration):
        lda.inference()
        print "-%d p=%f" % (i + 1, lda.perplexity())

    print "\n== topic-word distribution =="
    output_topic_word_dist(lda, voca)

    if len(lda.w_to_j) > 0:
        print "\n== constraints =="
        for j, w in sorted((j, w) for w, j in lda.w_to_j.items()):
            print "%d: %s [%s]" % (lda.w_to_j[w], voca.vocas[w], ",".join(str(x) for x in lda.n_k_w[:,w]))

def output_topic_word_dist(lda, voca):
    phi = lda.worddist()
    for k in range(lda.K):
        print "\n-- topic: %d" % k
        for w in numpy.argsort(-phi[k])[:30]:
            print "%s: %f" % (voca[w], phi[k,w])


def main():
    import os
    import pickle
    import optparse

    parser = optparse.OptionParser()
    parser.add_option("-m", dest="model", help="model filename")
    parser.add_option("-f", dest="filename", help="corpus filename")
    parser.add_option("-b", dest="corpus", help="using range of Brown corpus' files(start:end)")
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=0.1)
    parser.add_option("--beta", dest="beta", type="float", help="parameter beta", default=0.01)
    parser.add_option("--eta", dest="eta", type="float", help="parameter eta", default=100)
    parser.add_option("-k", dest="K", type="int", help="number of topics", default=20)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=10)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    parser.add_option("--df", dest="df", type="int", help="threshold of document freaquency to cut words", default=0)
    parser.add_option("-c", dest="constraint", help="add constraint (wordlist which should belong to the same topic)")
    parser.add_option("-u", "--unassign", dest="unassign", help="unassign method (all/doc/term/none)", default="none")
    (options, args) = parser.parse_args()

    numpy.random.seed(options.seed)

    if options.model and os.path.exists(options.model):
        with open(options.model, "rb") as f:
            lda, voca = pickle.load(f)
    elif not (options.filename or options.corpus):
        parser.error("need corpus filename(-f) or corpus range(-b) or model(-m)")
    else:
        import vocabulary
        if options.filename:
            corpus = vocabulary.load_file(options.filename)
        else:
            corpus = vocabulary.load_corpus(options.corpus)
            if not corpus: parser.error("corpus range(-c) forms 'start:end'")
        voca = vocabulary.Vocabulary()
        docs = [voca.doc_to_ids(doc) for doc in corpus]
        if options.df > 0: docs = voca.cut_low_freq(docs, options.df)
        lda = ITM(options.K, options.alpha, options.beta, options.eta, docs, voca.size())
    param = (len(lda.docs), len(voca.vocas), options.K, options.alpha, options.beta, options.eta)
    print "corpus=%d, words=%d, K=%d, a=%f, b=%f, eta=%f" % param

    if options.constraint:
        if options.unassign == "all":
            add_constraint = lda.add_constraint_all
        elif options.unassign == "doc":
            add_constraint = lda.add_constraint_doc
        elif options.unassign == "term":
            add_constraint = lda.add_constraint_term
        elif options.unassign == "none":
            add_constraint = lda.add_constraint_none
        else:
            parser.error("unassign method(-u) must be all/doc/term/none")

        wordlist = options.constraint.split(',')
        idlist = [voca.vocas_id[w] for w in wordlist]

        print "\n== add constraint =="
        for w, v in zip(idlist, wordlist):
            print "%s [%s]" % (v, ",".join(str(x) for x in lda.n_k_w[:,w]))

        add_constraint(idlist)

        lda.verify_topic()


    #import cProfile
    #cProfile.runctx('lda_learning(lda, options.iteration, voca)', globals(), locals(), 'lda.profile')
    lda_learning(lda, options.iteration, voca)

    with open(options.model, "wb") as f:
        pickle.dump((lda, voca), f)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = lda
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Latent Dirichlet Allocation + collapsed Gibbs sampling
# This code is available under the MIT License.
# (c)2010-2011 Nakatani Shuyo / Cybozu Labs Inc.

import numpy

class LDA:
    def __init__(self, K, alpha, beta, docs, V, smartinit=True):
        self.K = K
        self.alpha = alpha # parameter of topics prior
        self.beta = beta   # parameter of words prior
        self.docs = docs
        self.V = V

        self.z_m_n = [] # topics of words of documents
        self.n_m_z = numpy.zeros((len(self.docs), K)) + alpha     # word count of each document and topic
        self.n_z_t = numpy.zeros((K, V)) + beta # word count of each topic and vocabulary
        self.n_z = numpy.zeros(K) + V * beta    # word count of each topic

        self.N = 0
        for m, doc in enumerate(docs):
            self.N += len(doc)
            z_n = []
            for t in doc:
                if smartinit:
                    p_z = self.n_z_t[:, t] * self.n_m_z[m] / self.n_z
                    z = numpy.random.multinomial(1, p_z / p_z.sum()).argmax()
                else:
                    z = numpy.random.randint(0, K)
                z_n.append(z)
                self.n_m_z[m, z] += 1
                self.n_z_t[z, t] += 1
                self.n_z[z] += 1
            self.z_m_n.append(numpy.array(z_n))

    def inference(self):
        """learning once iteration"""
        for m, doc in enumerate(self.docs):
            z_n = self.z_m_n[m]
            n_m_z = self.n_m_z[m]
            for n, t in enumerate(doc):
                # discount for n-th word t with topic z
                z = z_n[n]
                n_m_z[z] -= 1
                self.n_z_t[z, t] -= 1
                self.n_z[z] -= 1

                # sampling topic new_z for t
                p_z = self.n_z_t[:, t] * n_m_z / self.n_z
                new_z = numpy.random.multinomial(1, p_z / p_z.sum()).argmax()

                # set z the new topic and increment counters
                z_n[n] = new_z
                n_m_z[new_z] += 1
                self.n_z_t[new_z, t] += 1
                self.n_z[new_z] += 1

    def worddist(self):
        """get topic-word distribution"""
        return self.n_z_t / self.n_z[:, numpy.newaxis]

    def perplexity(self, docs=None):
        if docs == None: docs = self.docs
        phi = self.worddist()
        log_per = 0
        N = 0
        Kalpha = self.K * self.alpha
        for m, doc in enumerate(docs):
            theta = self.n_m_z[m] / (len(self.docs[m]) + Kalpha)
            for w in doc:
                log_per -= numpy.log(numpy.inner(phi[:,w], theta))
            N += len(doc)
        return numpy.exp(log_per / N)

def lda_learning(lda, iteration, voca):
    pre_perp = lda.perplexity()
    print "initial perplexity=%f" % pre_perp
    for i in range(iteration):
        lda.inference()
        perp = lda.perplexity()
        print "-%d p=%f" % (i + 1, perp)
        if pre_perp:
            if pre_perp < perp:
                output_word_topic_dist(lda, voca)
                pre_perp = None
            else:
                pre_perp = perp
    output_word_topic_dist(lda, voca)

def output_word_topic_dist(lda, voca):
    zcount = numpy.zeros(lda.K, dtype=int)
    wordcount = [dict() for k in xrange(lda.K)]
    for xlist, zlist in zip(lda.docs, lda.z_m_n):
        for x, z in zip(xlist, zlist):
            zcount[z] += 1
            if x in wordcount[z]:
                wordcount[z][x] += 1
            else:
                wordcount[z][x] = 1

    phi = lda.worddist()
    for k in xrange(lda.K):
        print "\n-- topic: %d (%d words)" % (k, zcount[k])
        for w in numpy.argsort(-phi[k])[:20]:
            print "%s: %f (%d)" % (voca[w], phi[k,w], wordcount[k].get(w,0))

def main():
    import optparse
    import vocabulary
    parser = optparse.OptionParser()
    parser.add_option("-f", dest="filename", help="corpus filename")
    parser.add_option("-c", dest="corpus", help="using range of Brown corpus' files(start:end)")
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=0.5)
    parser.add_option("--beta", dest="beta", type="float", help="parameter beta", default=0.5)
    parser.add_option("-k", dest="K", type="int", help="number of topics", default=20)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=100)
    parser.add_option("-s", dest="smartinit", action="store_true", help="smart initialize of parameters", default=False)
    parser.add_option("--stopwords", dest="stopwords", help="exclude stop words", action="store_true", default=False)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    parser.add_option("--df", dest="df", type="int", help="threshold of document freaquency to cut words", default=0)
    (options, args) = parser.parse_args()
    if not (options.filename or options.corpus): parser.error("need corpus filename(-f) or corpus range(-c)")

    if options.filename:
        corpus = vocabulary.load_file(options.filename)
    else:
        corpus = vocabulary.load_corpus(options.corpus)
        if not corpus: parser.error("corpus range(-c) forms 'start:end'")
    if options.seed != None:
        numpy.random.seed(options.seed)

    voca = vocabulary.Vocabulary(options.stopwords)
    docs = [voca.doc_to_ids(doc) for doc in corpus]
    if options.df > 0: docs = voca.cut_low_freq(docs, options.df)

    lda = LDA(options.K, options.alpha, options.beta, docs, voca.size(), options.smartinit)
    print "corpus=%d, words=%d, K=%d, a=%f, b=%f" % (len(corpus), len(voca.vocas), options.K, options.alpha, options.beta)

    #import cProfile
    #cProfile.runctx('lda_learning(lda, options.iteration, voca)', globals(), locals(), 'lda.profile')
    lda_learning(lda, options.iteration, voca)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = lda_cvb0
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Latent Dirichlet Allocation + Collapsed Variational Bayesian
# This code is available under the MIT License.
# (c)2010-2011 Nakatani Shuyo / Cybozu Labs Inc.

import numpy

class LDA_CVB0:
    def __init__(self, K, alpha, beta, docs, V, smartinit=True):
        self.K = K
        self.alpha = alpha
        self.beta = beta
        self.V = V

        self.docs = []
        self.gamma_jik = []
        self.n_wk = numpy.zeros((V, K)) + beta
        self.n_jk = numpy.zeros((len(docs), K)) + alpha
        self.n_k = numpy.zeros(K) + V * beta
        self.N = 0
        for j, doc in enumerate(docs):
            self.N += len(doc)
            term_freq = dict()
            term_gamma = dict()
            for i, w in enumerate(doc):
                if smartinit:
                    p_k = self.n_wk[w] * self.n_jk[j] / self.n_k
                    gamma_k = numpy.random.mtrand.dirichlet(p_k / p_k.sum() * alpha)
                else:
                    gamma_k = [float("nan")]
                if not numpy.isfinite(gamma_k[0]): # maybe NaN or Inf
                    gamma_k = numpy.random.mtrand.dirichlet([alpha] * K)
                if w in term_freq:
                    term_freq[w] += 1
                    term_gamma[w] += gamma_k
                else:
                    term_freq[w] = 1
                    term_gamma[w] = gamma_k
                self.n_wk[w] += gamma_k
                self.n_jk[j] += gamma_k
                self.n_k += gamma_k
            term_freq = term_freq.items()
            self.docs.append(term_freq)
            self.gamma_jik.append([term_gamma[w] / freq for w, freq in term_freq])

    def inference(self):
        """learning once iteration"""
        new_n_wk = numpy.zeros((self.V, self.K)) + self.beta
        new_n_jk = numpy.zeros((len(self.docs), self.K)) + self.alpha
        n_k = self.n_k
        for j, doc in enumerate(self.docs):
            gamma_ik = self.gamma_jik[j]
            n_jk = self.n_jk[j]
            new_n_jk_j = new_n_jk[j]
            for i, gamma_k in enumerate(gamma_ik):
                w, freq = doc[i]
                new_gamma_k = (self.n_wk[w] - gamma_k) * (n_jk - gamma_k) / (n_k - gamma_k)
                new_gamma_k /= new_gamma_k.sum()

                gamma_ik[i] = new_gamma_k
                gamma_freq = new_gamma_k * freq
                new_n_wk[w] += gamma_freq
                new_n_jk_j += gamma_freq

        self.n_wk = new_n_wk
        self.n_jk = new_n_jk
        self.n_k  = new_n_wk.sum(axis=0)

    def worddist(self):
        """get topic-word distribution"""
        return numpy.transpose(self.n_wk / self.n_k)

    def perplexity(self, docs=None):
        if docs == None: docs = self.docs
        phi = self.worddist()
        log_per = 0
        N = 0
        for j, doc in enumerate(docs):
            theta = self.n_jk[j]
            theta = theta / theta.sum()
            for w, freq in doc:
                log_per -= numpy.log(numpy.inner(phi[:,w], theta)) * freq
                N += freq
        return numpy.exp(log_per / N)

def lda_learning(lda, iteration, voca):
    pre_perp = lda.perplexity()
    print "initial perplexity=%f" % pre_perp
    for i in range(iteration):
        lda.inference()
        perp = lda.perplexity()
        print "-%d p=%f" % (i + 1, perp)
        if pre_perp:
            if pre_perp < perp:
                output_word_topic_dist(lda, voca)
                pre_perp = None
            else:
                pre_perp = perp
    output_word_topic_dist(lda, voca)

def output_word_topic_dist(lda, voca):
    phi = lda.worddist()
    for k in range(lda.K):
        print "\n-- topic: %d" % k
        for w in numpy.argsort(-phi[k])[:20]:
            print "%s: %f" % (voca[w], phi[k,w])

def main():
    import optparse
    import vocabulary
    parser = optparse.OptionParser()
    parser.add_option("-f", dest="filename", help="corpus filename")
    parser.add_option("-c", dest="corpus", help="using range of Brown corpus' files(start:end)")
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=0.5)
    parser.add_option("--beta", dest="beta", type="float", help="parameter beta", default=0.5)
    parser.add_option("-k", dest="K", type="int", help="number of topics", default=20)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=100)
    parser.add_option("-s", dest="smartinit", action="store_true", help="smart initialize of parameters", default=False)
    parser.add_option("--stopwords", dest="stopwords", help="exclude stop words", action="store_true", default=False)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    parser.add_option("--df", dest="df", type="int", help="threshold of document freaquency to cut words", default=0)
    (options, args) = parser.parse_args()
    if not (options.filename or options.corpus): parser.error("need corpus filename(-f) or corpus range(-c)")

    if options.filename:
        corpus = vocabulary.load_file(options.filename)
    else:
        corpus = vocabulary.load_corpus(options.corpus)
        if not corpus: parser.error("corpus range(-c) forms 'start:end'")
    if options.seed != None:
        numpy.random.seed(options.seed)

    voca = vocabulary.Vocabulary(options.stopwords)
    docs = [voca.doc_to_ids(doc) for doc in corpus]
    if options.df > 0: docs = voca.cut_low_freq(docs, options.df)

    lda = LDA_CVB0(options.K, options.alpha, options.beta, docs, voca.size(), options.smartinit)
    print "corpus=%d, words=%d, voca=%d, K=%d, a=%f, b=%f" % (len(corpus), lda.N, len(voca.vocas), options.K, options.alpha, options.beta)

    #import cProfile
    #cProfile.runctx('lda_learning(lda, options.iteration, voca)', globals(), locals(), 'lda.profile')
    lda_learning(lda, options.iteration, voca)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = lda_test
#!/usr/bin/python

# This code is available under the MIT License.
# (c)2010-2011 Nakatani Shuyo / Cybozu Labs Inc.

import numpy

class FileOutput:
    def __init__(self, file):
        import datetime
        self.file = file + datetime.datetime.now().strftime('_%m%d_%H%M%S.txt')
    def out(self, st):
        with open(self.file, 'a') as f:
            print >>f,  st

def lda_learning(f, LDA, smartinit, options, docs, voca, plimit=1):
    import time
    t0 = time.time()

    if options.seed != None: numpy.random.seed(options.seed)
    lda = LDA(options.K, options.alpha, options.beta, docs, voca.size(), smartinit)

    pre_perp = lda.perplexity()
    f.out("alg=%s smart_init=%s initial perplexity=%f" % (LDA.__name__, smartinit, pre_perp))

    pc = 0
    for i in range(options.iteration):
        if i % 10==0: output_word_topic_dist(f, lda, voca)
        lda.inference()
        perp = lda.perplexity()
        f.out("-%d p=%f" % (i + 1, perp))
        if pre_perp is not None:
            if pre_perp < perp:
                pc += 1
                if pc >= plimit:
                    output_word_topic_dist(f, lda, voca)
                    pre_perp = None
            else:
                pc = 0
                pre_perp = perp
    output_word_topic_dist(f, lda, voca)

    t1 = time.time()
    f.out("time = %f\n" % (t1 - t0))

def output_word_topic_dist(f, lda, voca):
    phi = lda.worddist()
    for k in range(lda.K):
        f.out("\n-- topic: %d" % k)
        for w in numpy.argsort(-phi[k])[:20]:
            f.out("%s: %f" % (voca[w], phi[k,w]))

def main():
    import optparse
    import vocabulary
    import lda
    import lda_cvb0
    parser = optparse.OptionParser()
    parser.add_option("-c", dest="corpus", help="using range of Brown corpus' files(start:end)", default="1:100")
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=0.5)
    parser.add_option("--beta", dest="beta", type="float", help="parameter beta", default=0.5)
    parser.add_option("-k", dest="K", type="int", help="number of topics", default=20)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=100)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    parser.add_option("--stopwords", dest="stopwords", help="exclude stop words", action="store_true", default=False)
    parser.add_option("--df", dest="df", type="int", help="threshold of document freaquency to cut words", default=1)
    (options, args) = parser.parse_args()

    corpus = vocabulary.load_corpus(options.corpus)
    voca = vocabulary.Vocabulary(options.stopwords)
    docs = [voca.doc_to_ids(doc) for doc in corpus]
    if options.df > 0: docs = voca.cut_low_freq(docs, options.df)

    f = FileOutput("lda_test")
    f.out("corpus=%d, words=%d, K=%d, a=%f, b=%f" % (len(docs), len(voca.vocas), options.K, options.alpha, options.beta))

    lda_learning(f, lda_cvb0.LDA_CVB0, False, options, docs, voca)
    lda_learning(f, lda_cvb0.LDA_CVB0, True, options, docs, voca)
    lda_learning(f, lda.LDA, False, options, docs, voca, 2)
    lda_learning(f, lda.LDA, True, options, docs, voca, 2)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = lda_test2
#!/usr/bin/python

# This code is available under the MIT License.
# (c)2010-2011 Nakatani Shuyo / Cybozu Labs Inc.

import numpy

class FileOutput:
    def __init__(self, file):
        import datetime
        self.file = file + datetime.datetime.now().strftime('_%m%d_%H%M%S.txt')
    def out(self, st):
        with open(self.file, 'a') as f:
            print >>f,  st

def lda_learning(f, LDA, smartinit, options, docs, test_docs, voca, plimit=1):
    import time
    t0 = time.time()

    if options.seed != None: numpy.random.seed(options.seed)
    lda = LDA(options.K, options.alpha, options.beta, docs, voca.size(), smartinit)

    pre_perp = lda.perplexity(test_docs)
    f.out("alg=%s smart_init=%s initial perplexity=%f" % (LDA.__name__, smartinit, pre_perp))

    pc = 0
    for i in range(options.iteration):
        if i % 10==0: output_word_topic_dist(f, lda, voca)
        lda.inference()
        perp = lda.perplexity(test_docs)
        f.out("-%d p=%f" % (i + 1, perp))
        if pre_perp is not None:
            if pre_perp < perp:
                pc += 1
                if pc >= plimit:
                    output_word_topic_dist(f, lda, voca)
                    pre_perp = None
            else:
                pc = 0
                pre_perp = perp
    output_word_topic_dist(f, lda, voca)

    t1 = time.time()
    f.out("time = %f\n" % (t1 - t0))

def output_word_topic_dist(f, lda, voca):
    phi = lda.worddist()
    for k in range(lda.K):
        f.out("\n-- topic: %d" % k)
        for w in numpy.argsort(-phi[k])[:20]:
            f.out("%s: %f" % (voca[w], phi[k,w]))

def conv_word_freq(docs):
    result = []
    for doc in docs:
        term_freq = dict()
        for w in doc:
            if w in term_freq:
                term_freq[w] += 1
            else:
                term_freq[w] = 1
        result.append(term_freq.items())
    return result

def main():
    import optparse
    import vocabulary
    import lda
    import lda_cvb0
    parser = optparse.OptionParser()
    parser.add_option("-c", dest="corpus", help="using range of Brown corpus' files(start:end)", default="0:100")
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=0.5)
    parser.add_option("--beta", dest="beta", type="float", help="parameter beta", default=0.5)
    parser.add_option("-k", dest="K", type="int", help="number of topics", default=20)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=100)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    parser.add_option("--stopwords", dest="stopwords", help="exclude stop words", action="store_true", default=False)
    parser.add_option("--df", dest="df", type="int", help="threshold of document freaquency to cut words", default=10)
    (options, args) = parser.parse_args()

    corpus = vocabulary.load_corpus(options.corpus)
    voca = vocabulary.Vocabulary(options.stopwords)
    docs = [voca.doc_to_ids(doc) for doc in corpus]
    if options.df > 0: docs = voca.cut_low_freq(docs, options.df)
    train_docs = [[x for i, x in enumerate(doc) if i % 10 != 0] for doc in docs]
    test_docs = [[x for i, x in enumerate(doc) if i % 10 == 0] for doc in docs]
    test_docs_wf = conv_word_freq(test_docs)

    f = FileOutput("lda_test2")
    f.out("corpus=%d, words=%d, K=%d, a=%f, b=%f" % (len(docs), len(voca.vocas), options.K, options.alpha, options.beta))

    lda_learning(f, lda_cvb0.LDA_CVB0, False, options, train_docs, test_docs_wf, voca)
    lda_learning(f, lda_cvb0.LDA_CVB0, True, options, train_docs, test_docs_wf, voca)
    lda_learning(f, lda.LDA, False, options, train_docs, test_docs, voca, 2)
    lda_learning(f, lda.LDA, True, options, train_docs, test_docs, voca, 2)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = llda
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Labeled Latent Dirichlet Allocation
# This code is available under the MIT License.
# (c)2010 Nakatani Shuyo / Cybozu Labs Inc.
# refer to Ramage+, Labeled LDA: A supervised topic model for credit attribution in multi-labeled corpora(EMNLP2009)

from optparse import OptionParser
import sys, re, numpy

def load_corpus(filename):
    corpus = []
    labels = []
    labelmap = dict()
    f = open(filename, 'r')
    for line in f:
        mt = re.match(r'\[(.+?)\](.+)', line)
        if mt:
            label = mt.group(1).split(',')
            for x in label: labelmap[x] = 1
            line = mt.group(2)
        else:
            label = None
        doc = re.findall(r'\w+(?:\'\w+)?',line.lower())
        if len(doc)>0:
            corpus.append(doc)
            labels.append(label)
    f.close()
    return labelmap.keys(), corpus, labels

class LLDA:
    def __init__(self, K, alpha, beta):
        #self.K = K
        self.alpha = alpha
        self.beta = beta

    def term_to_id(self, term):
        if term not in self.vocas_id:
            voca_id = len(self.vocas)
            self.vocas_id[term] = voca_id
            self.vocas.append(term)
        else:
            voca_id = self.vocas_id[term]
        return voca_id

    def complement_label(self, label):
        if not label: return numpy.ones(len(self.labelmap))
        vec = numpy.zeros(len(self.labelmap))
        vec[0] = 1.0
        for x in label: vec[self.labelmap[x]] = 1.0
        return vec

    def set_corpus(self, labelset, corpus, labels):
        labelset.insert(0, "common")
        self.labelmap = dict(zip(labelset, range(len(labelset))))
        self.K = len(self.labelmap)

        self.vocas = []
        self.vocas_id = dict()
        self.labels = numpy.array([self.complement_label(label) for label in labels])
        self.docs = [[self.term_to_id(term) for term in doc] for doc in corpus]

        M = len(corpus)
        V = len(self.vocas)

        self.z_m_n = []
        self.n_m_z = numpy.zeros((M, self.K), dtype=int)
        self.n_z_t = numpy.zeros((self.K, V), dtype=int)
        self.n_z = numpy.zeros(self.K, dtype=int)

        for m, doc, label in zip(range(M), self.docs, self.labels):
            N_m = len(doc)
            #z_n = [label[x] for x in numpy.random.randint(len(label), size=N_m)]
            z_n = [numpy.random.multinomial(1, label / label.sum()).argmax() for x in range(N_m)]
            self.z_m_n.append(z_n)
            for t, z in zip(doc, z_n):
                self.n_m_z[m, z] += 1
                self.n_z_t[z, t] += 1
                self.n_z[z] += 1

    def inference(self):
        V = len(self.vocas)
        for m, doc, label in zip(range(len(self.docs)), self.docs, self.labels):
            for n in range(len(doc)):
                t = doc[n]
                z = self.z_m_n[m][n]
                self.n_m_z[m, z] -= 1
                self.n_z_t[z, t] -= 1
                self.n_z[z] -= 1

                denom_a = self.n_m_z[m].sum() + self.K * self.alpha
                denom_b = self.n_z_t.sum(axis=1) + V * self.beta
                p_z = label * (self.n_z_t[:, t] + self.beta) / denom_b * (self.n_m_z[m] + self.alpha) / denom_a
                new_z = numpy.random.multinomial(1, p_z / p_z.sum()).argmax()

                self.z_m_n[m][n] = new_z
                self.n_m_z[m, new_z] += 1
                self.n_z_t[new_z, t] += 1
                self.n_z[new_z] += 1

    def phi(self):
        V = len(self.vocas)
        return (self.n_z_t + self.beta) / (self.n_z[:, numpy.newaxis] + V * self.beta)

    def theta(self):
        """document-topic distribution"""
        n_alpha = self.n_m_z + self.labels * self.alpha
        return n_alpha / n_alpha.sum(axis=1)[:, numpy.newaxis]

    def perplexity(self, docs=None):
        if docs == None: docs = self.docs
        phi = self.phi()
        thetas = self.theta()

        log_per = N = 0
        for doc, theta in zip(docs, thetas):
            for w in doc:
                log_per -= numpy.log(numpy.inner(phi[:,w], theta))
            N += len(doc)
        return numpy.exp(log_per / N)

def main():
    parser = OptionParser()
    parser.add_option("-f", dest="filename", help="corpus filename")
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=0.001)
    parser.add_option("--beta", dest="beta", type="float", help="parameter beta", default=0.001)
    parser.add_option("-k", dest="K", type="int", help="number of topics", default=20)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=100)
    (options, args) = parser.parse_args()
    if not options.filename: parser.error("need corpus filename(-f)")

    labelset, corpus, labels = load_corpus(options.filename)

    llda = LLDA(options.K, options.alpha, options.beta)
    llda.set_corpus(labelset, corpus, labels)

    for i in range(options.iteration):
        sys.stderr.write("-- %d " % (i + 1))
        llda.inference()
    #print llda.z_m_n

    phi = llda.phi()
    for v, voca in enumerate(llda.vocas):
        #print ','.join([voca]+[str(x) for x in llda.n_z_t[:,v]])
        print ','.join([voca]+[str(x) for x in phi[:,v]])

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = llda_nltk
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Labeled LDA using nltk.corpus.reuters as dataset
# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import sys, string, random, numpy
from nltk.corpus import reuters
from llda import LLDA
from optparse import OptionParser

parser = OptionParser()
parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=0.001)
parser.add_option("--beta", dest="beta", type="float", help="parameter beta", default=0.001)
parser.add_option("-k", dest="K", type="int", help="number of topics", default=50)
parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=100)
parser.add_option("-s", dest="seed", type="int", help="random seed", default=None)
parser.add_option("-n", dest="samplesize", type="int", help="dataset sample size", default=100)
(options, args) = parser.parse_args()
random.seed(options.seed)
numpy.random.seed(options.seed)

idlist = random.sample(reuters.fileids(), options.samplesize)

labels = []
corpus = []
for id in idlist:
    labels.append(reuters.categories(id))
    corpus.append([x.lower() for x in reuters.words(id) if x[0] in string.ascii_letters])
    reuters.words(id).close()
labelset = list(set(reduce(list.__add__, labels)))


llda = LLDA(options.K, options.alpha, options.beta)
llda.set_corpus(labelset, corpus, labels)

print "M=%d, V=%d, L=%d, K=%d" % (len(corpus), len(llda.vocas), len(labelset), options.K)

for i in range(options.iteration):
    sys.stderr.write("-- %d : %.4f\n" % (i, llda.perplexity()))
    llda.inference()
print "perplexity : %.4f" % llda.perplexity()

phi = llda.phi()
for k, label in enumerate(labelset):
    print "\n-- label %d : %s" % (k, label)
    for w in numpy.argsort(-phi[k])[:20]:
        print "%s: %.4f" % (llda.vocas[w], phi[k,w])


########NEW FILE########
__FILENAME__ = test_hdplda2
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import numpy
import hdplda2

class TestHDPLDA(unittest.TestCase):
    def test1(self):
        self.sequence1(0.1, 0.1, 0.1)

    def test2(self):
        self.sequence1(0.2, 0.01, 0.5)

    def test4(self):
        self.sequence3(0.2, 0.01, 0.5)
        pass

    def test5(self):
        self.sequence4(0.2, 0.01, 0.5)
        pass

    def test7(self):
        self.sequence2(0.01, 0.001, 10)

    def test8(self):
        self.sequence2(0.01, 0.001, 0.05)


    def test_random_sequences(self):
        self.sequence_random(0.2, 0.01, 0.5, 0)
        self.sequence_random(0.2, 0.01, 0.01, 6)
        self.sequence_random(0.2, 0.01, 0.5, 2)
        self.sequence_random(0.01, 0.001, 0.05, 13)
        pass


    def sequence_random(self, alpha, beta, gamma, seed):
        print (alpha, beta, gamma)
        numpy.random.seed(seed)
        docs = [[0,1,2,3], [0,1,4,5], [0,1,5,6]]
        V = 7
        model = hdplda2.HDPLDA(alpha, beta, gamma, docs, V)
        print model.perplexity()
        for i in xrange(10):
            model.inference()
            print model.perplexity()

    def sequence4(self, alpha, beta, gamma):
        docs = [[0,1,2,3], [0,1,4,5], [0,1,5,6]]
        V = 7
        model = hdplda2.HDPLDA(alpha, beta, gamma, docs, V)
        Vbeta = V * beta

        k1 = model.add_new_dish()
        k2 = model.add_new_dish()

        j = 0
        t1 = model.add_new_table(j, k1)
        t2 = model.add_new_table(j, k2)
        model.seat_at_table(j, 0, t1)
        model.seat_at_table(j, 1, t2)
        model.seat_at_table(j, 2, t2)
        model.seat_at_table(j, 3, t2)

        j = 1
        t1 = model.add_new_table(j, k1)
        t2 = model.add_new_table(j, k2)
        model.seat_at_table(j, 0, t2)
        model.seat_at_table(j, 1, t2)
        model.seat_at_table(j, 2, t1)
        model.seat_at_table(j, 3, t2)

        j = 2
        t1 = model.add_new_table(j, k1)
        t2 = model.add_new_table(j, k2)
        model.seat_at_table(j, 0, t1)
        model.seat_at_table(j, 1, t2)
        model.seat_at_table(j, 2, t2)
        model.seat_at_table(j, 3, t2)


        model.leave_from_dish(2, 1)
        model.seat_at_dish(2, 1, 2)


        model.leave_from_table(2, 0)
        model.seat_at_table(2, 0, 2)


        model.leave_from_dish(0, 1)
        model.seat_at_dish(0, 1, 2)
        self.assertEqual(model.m, 5)
        self.assertEqual(model.m_k[1], 1)
        self.assertEqual(model.m_k[2], 4)

        model.leave_from_dish(1, 1)
        model.seat_at_dish(1, 1, 2)

        model.leave_from_table(2, 3)
        k_new = model.add_new_dish()
        self.assertEqual(k_new, 1)
        t_new = model.add_new_table(j, k_new)
        self.assertEqual(t_new, 1)
        model.seat_at_table(2, 3, 1)

        #model.dump()
        #using_t: [[0, 1, 2], [0, 1, 2], [0, 1, 2]]
        #t_ji: [[1, 2, 2, 2], [2, 2, 1, 2], [2, 2, 2, 1]]
        #using_k: [0, 1, 2]
        #k_jt: [[0, 2, 2], [0, 2, 2], [0, 1, 2]]

        j = 0
        t = 1
        model.leave_from_dish(j, t)

        #print "n_jt=", model.n_jt[j][t]

        p_k = model.calc_dish_posterior_t(j, t)
        #print "p_k=", p_k
        p0 = gamma / V
        p1 = 1 * beta / (V * beta + 1)
        p2 = 4 * (beta + 2) / (Vbeta + 10)
        #print "[p0, p1, p2]=", [p0, p1, p2]
        self.assertAlmostEqual(p_k[0], p0 / (p0 + p1 + p2))
        self.assertAlmostEqual(p_k[1], p1 / (p0 + p1 + p2))
        self.assertAlmostEqual(p_k[2], p2 / (p0 + p1 + p2))

        #k_new = self.add_new_dish()
        model.seat_at_dish(j, t, 1)

        t = 2
        model.leave_from_dish(j, t)

        #print "n_jt=", model.n_jt[j][t]

        p_k = model.calc_dish_posterior_t(j, t)
        #print "p_k=", p_k

        p0 = gamma * beta * beta * beta / (Vbeta * (Vbeta + 1) * (Vbeta + 2))
        p1 = 2 * (beta + 0) * beta * beta / ((Vbeta + 2) * (Vbeta + 3) * (Vbeta + 4))
        p2 = 3 * (beta + 2) * beta * beta / ((Vbeta + 7) * (Vbeta + 8) * (Vbeta + 9))
        #print "[p0, p1, p2]=", [p0, p1, p2]
        self.assertAlmostEqual(p_k[0], p0 / (p0 + p1 + p2))
        self.assertAlmostEqual(p_k[1], p1 / (p0 + p1 + p2))
        self.assertAlmostEqual(p_k[2], p2 / (p0 + p1 + p2))

        #k_new = self.add_new_dish()
        model.seat_at_dish(j, t, 1)



    def sequence3(self, alpha, beta, gamma):
        docs = [[0,1,2,3], [0,1,4,5], [0,1,5,6]]
        V = 7
        model = hdplda2.HDPLDA(alpha, beta, gamma, docs, V)

        k1 = model.add_new_dish()
        k2 = model.add_new_dish()

        j = 0
        t1 = model.add_new_table(j, k1)
        t2 = model.add_new_table(j, k2)
        model.seat_at_table(j, 0, t1)
        model.seat_at_table(j, 1, t2)
        model.seat_at_table(j, 2, t1)
        model.seat_at_table(j, 3, t1)

        j = 1
        t1 = model.add_new_table(j, k1)
        t2 = model.add_new_table(j, k2)
        model.seat_at_table(j, 0, t1)
        model.seat_at_table(j, 1, t2)
        model.seat_at_table(j, 2, t2)
        model.seat_at_table(j, 3, t2)

        j = 2
        t1 = model.add_new_table(j, k1)
        t2 = model.add_new_table(j, k2)
        model.seat_at_table(j, 0, t1)
        model.seat_at_table(j, 1, t2)
        model.seat_at_table(j, 2, t2)
        model.seat_at_table(j, 3, t2)

        #model.dump()

        # test for topic-word distribution
        phi = model.worddist()
        self.assertEqual(len(phi), 2)
        self.assertAlmostEqual(phi[0][0], (beta+3)/(V*beta+5))
        self.assertAlmostEqual(phi[0][2], (beta+1)/(V*beta+5))
        self.assertAlmostEqual(phi[0][3], (beta+1)/(V*beta+5))
        for v in [1,4,5,6]:
            self.assertAlmostEqual(phi[0][v], (beta+0)/(V*beta+5))
        self.assertAlmostEqual(phi[1][1], (beta+3)/(V*beta+7))
        self.assertAlmostEqual(phi[1][4], (beta+1)/(V*beta+7))
        self.assertAlmostEqual(phi[1][5], (beta+2)/(V*beta+7))
        self.assertAlmostEqual(phi[1][6], (beta+1)/(V*beta+7))
        for v in [0,2,3]:
            self.assertAlmostEqual(phi[1][v], (beta+0)/(V*beta+7))


        # test for document-topic distribution
        theta = model.docdist()
        self.assertEqual(theta.shape, (3, 3))
        self.assertAlmostEqual(theta[0][0], (  alpha*gamma/(6+gamma))/(4+alpha))
        self.assertAlmostEqual(theta[0][1], (3+alpha*  3  /(6+gamma))/(4+alpha))
        self.assertAlmostEqual(theta[0][2], (1+alpha*  3  /(6+gamma))/(4+alpha))
        self.assertAlmostEqual(theta[1][0], (  alpha*gamma/(6+gamma))/(4+alpha))
        self.assertAlmostEqual(theta[1][1], (1+alpha*  3  /(6+gamma))/(4+alpha))
        self.assertAlmostEqual(theta[1][2], (3+alpha*  3  /(6+gamma))/(4+alpha))
        self.assertAlmostEqual(theta[2][0], (  alpha*gamma/(6+gamma))/(4+alpha))
        self.assertAlmostEqual(theta[2][1], (1+alpha*  3  /(6+gamma))/(4+alpha))
        self.assertAlmostEqual(theta[2][2], (3+alpha*  3  /(6+gamma))/(4+alpha))

        j = 0
        i = 0
        v = docs[j][i]

        model.leave_from_table(j, i)

        f_k = model.calc_f_k(v)
        self.assertEqual(len(f_k), 3)
        self.assertAlmostEqual(f_k[1], (beta+2)/(V*beta+4))
        self.assertAlmostEqual(f_k[2], (beta+0)/(V*beta+7))

        p_t = model.calc_table_posterior(j, f_k)
        self.assertEqual(len(p_t), 3)
        p1 = 2 * f_k[1]
        p2 = 1 * f_k[2]
        p0 = alpha / (6+gamma) * (3*f_k[1] + 3*f_k[2] + gamma/V)
        self.assertAlmostEqual(p_t[0], p0 / (p0+p1+p2))
        self.assertAlmostEqual(p_t[1], p1 / (p0+p1+p2))
        self.assertAlmostEqual(p_t[2], p2 / (p0+p1+p2))

        model.seat_at_table(j, i, 1)

        j = 0
        i = 1
        v = docs[j][i]

        model.leave_from_table(j, i)
        self.assertEqual(len(model.using_t[j]), 2)
        self.assertEqual(model.using_t[j][0], 0)
        self.assertEqual(model.using_t[j][1], 1)

        f_k = model.calc_f_k(v)
        self.assertEqual(len(f_k), 3)
        self.assertAlmostEqual(f_k[1], (beta+0)/(V*beta+5))
        self.assertAlmostEqual(f_k[2], (beta+2)/(V*beta+6))

        p_t = model.calc_table_posterior(j, f_k)
        self.assertEqual(len(p_t), 2)
        p1 = 3 * f_k[1]
        p0 = alpha / (5+gamma) * (3*f_k[1] + 2*f_k[2] + gamma/V)
        self.assertAlmostEqual(p_t[0], p0 / (p0+p1))
        self.assertAlmostEqual(p_t[1], p1 / (p0+p1))

        model.seat_at_table(j, i, 1)




    def sequence2(self, alpha, beta, gamma):
        docs = [[0,1,2,3], [0,1,4,5], [0,1,5,6]]
        V = 7
        model = hdplda2.HDPLDA(alpha, beta, gamma, docs, V)

        # assign all words to table 1 and all tables to dish 1
        k_new = model.add_new_dish()
        self.assertEqual(k_new, 1)
        for j in xrange(3):
            t_new = model.add_new_table(j, k_new)
            self.assertEqual(t_new, 1)
            for i in xrange(4):
                model.seat_at_table(j, i, t_new)

        self.assertAlmostEqual(model.n_k[0], beta * V)
        self.assertAlmostEqual(model.n_k[1], beta * V + 12)
        self.assertAlmostEqual(model.n_kv[1][0], beta + 3)
        self.assertAlmostEqual(model.n_kv[1][1], beta + 3)
        self.assertAlmostEqual(model.n_kv[1][2], beta + 1)
        self.assertAlmostEqual(model.n_kv[1][3], beta + 1)
        self.assertAlmostEqual(model.n_kv[1][4], beta + 1)
        self.assertAlmostEqual(model.n_kv[1][5], beta + 2)
        self.assertAlmostEqual(model.n_kv[1][6], beta + 1)
        self.assertEqual(model.m_k[0], 1) # dummy
        self.assertEqual(model.m_k[1], 3)

        #model.sampling_k(0, 1)
        model.leave_from_dish(0, 1) # decrease m and m_k only
        self.assertEqual(model.m, 2)
        self.assertEqual(model.m_k[1], 2)

        model.seat_at_dish(0, 1, 1)
        self.assertEqual(model.m, 3)
        self.assertEqual(model.m_k[1], 3)

        for i in xrange(1):
            for j in xrange(3):
                model.sampling_k(j, 1)
                #model.dump()


    def sequence1(self, alpha, beta, gamma):
        docs = [[0,1,2,3], [0,1,4,5], [0,1,5,6]]
        V = 7
        model = hdplda2.HDPLDA(alpha, beta, gamma, docs, V)

        j = 0
        i = 0
        v = docs[j][i]
        self.assertEqual(v, 0)

        f_k = model.calc_f_k(v)
        #self.assertSequenceEqual(f_k, [0.])
        p_t = model.calc_table_posterior(j, f_k)
        self.assertSequenceEqual(p_t, [1.])

        p_k = model.calc_dish_posterior_w(f_k)
        self.assertEqual(len(p_k), 1)
        self.assertAlmostEqual(p_k[0], 1)

        k_new = model.add_new_dish()
        self.assertEqual(k_new, 1)
        t_new = model.add_new_table(j, k_new)
        self.assertEqual(t_new, 1)
        self.assertEqual(model.k_jt[j][t_new], 1)

        self.assertListEqual(model.using_t[j], [0, 1])
        self.assertListEqual(model.using_k, [0, 1])
        self.assertEqual(model.n_jt[j][t_new], 0) # まだ 0

        model.seat_at_table(j, i, t_new)
        self.assertEqual(model.t_ji[j][i], 1)
        self.assertEqual(model.n_jt[j][t_new], 1) # ふえた
        self.assertEqual(model.n_kv[k_new][v], beta + 1)


        i = 1 # the existed table
        v = docs[j][i]
        self.assertEqual(v, 1)

        f_k = model.calc_f_k(v)
        self.assertEqual(len(f_k), 2)
        #self.assertAlmostEqual(f_k[0], 0)
        self.assertAlmostEqual(f_k[1], (beta+0)/(V*beta+1))
        p_t = model.calc_table_posterior(j, f_k)
        self.assertEqual(len(p_t), 2)
        p0 = alpha / (1 + gamma) * (beta / (V * beta + 1) + gamma / V)
        p1 = 1 * beta / (V * beta + 1)
        self.assertAlmostEqual(p_t[0], p0 / (p0 + p1))  # 0.10151692
        self.assertAlmostEqual(p_t[1], p1 / (p0 + p1))  # 0.89848308

        t_new = 1
        model.seat_at_table(j, i, t_new)
        self.assertEqual(model.t_ji[j][i], t_new)
        self.assertEqual(model.n_jt[j][t_new], 2) # ふえた
        self.assertEqual(model.n_kv[k_new][v], beta + 1)


        i = 2
        v = docs[j][i]
        self.assertEqual(v, 2)

        f_k = model.calc_f_k(v)
        self.assertEqual(len(f_k), 2)
        self.assertAlmostEqual(f_k[0], 0)
        self.assertAlmostEqual(f_k[1], (beta+0)/(V*beta+2))
        p_t = model.calc_table_posterior(j, f_k)
        self.assertEqual(len(p_t), 2)
        p0 = alpha / (1 + gamma) * (beta / (V * beta + 2) + gamma / V)
        p1 = 2 * beta / (V * beta + 2)
        self.assertAlmostEqual(p_t[0], p0 / (p0 + p1))  # 0.05925473
        self.assertAlmostEqual(p_t[1], p1 / (p0 + p1))  # 0.94074527

        p_k = model.calc_dish_posterior_w(f_k)
        self.assertEqual(len(p_k), 2)
        p0 = gamma / V
        p1 = 1 * f_k[1]
        self.assertAlmostEqual(p_k[0], p0 / (p0 + p1))  # 0.27835052
        self.assertAlmostEqual(p_k[1], p1 / (p0 + p1))  # 0.72164948

        k_new = 1 # TODO : calculate posterior of k

        t_new = model.add_new_table(j, k_new)
        self.assertEqual(t_new, 2)
        self.assertEqual(k_new, model.k_jt[j][t_new])

        self.assertListEqual(model.using_t[j], [0, 1, 2])
        self.assertListEqual(model.using_k, [0, 1])

        model.seat_at_table(j, i, t_new)
        self.assertEqual(model.t_ji[j][i], t_new)
        self.assertEqual(model.n_jt[j][t_new], 1)
        self.assertEqual(model.n_kv[k_new][v], beta + 1)


        i = 3
        v = docs[j][i]
        self.assertEqual(v, 3)

        f_k = model.calc_f_k(v)
        self.assertEqual(len(f_k), 2)
        self.assertAlmostEqual(f_k[0], 0)
        self.assertAlmostEqual(f_k[1], (beta+0)/(V*beta+3))
        p_t = model.calc_table_posterior(j, f_k)
        self.assertEqual(len(p_t), 3)
        p0 = alpha / (2 + gamma) * (2 * beta / (V * beta + 3) + gamma / V)
        p1 = 2 * beta / (V * beta + 3)
        p2 = 1 * beta / (V * beta + 3)
        self.assertAlmostEqual(p_t[0], p0 / (p0 + p1 + p2))  # 0.03858731
        self.assertAlmostEqual(p_t[1], p1 / (p0 + p1 + p2))  # 0.64094179
        self.assertAlmostEqual(p_t[2], p2 / (p0 + p1 + p2))  # 0.3204709

        t_new = 1
        model.seat_at_table(j, i, t_new)
        self.assertEqual(model.t_ji[j][i], t_new)
        self.assertEqual(model.n_jt[j][t_new], 3)
        self.assertEqual(model.n_kv[k_new][v], beta + 1)


        j = 1
        i = 0
        v = docs[j][i]
        self.assertEqual(v, 0)

        f_k = model.calc_f_k(v)
        self.assertEqual(len(f_k), 2)
        self.assertAlmostEqual(f_k[0], 0)
        self.assertAlmostEqual(f_k[1], (beta+1)/(V*beta+4)) # 0.23404255

        p_t = model.calc_table_posterior(j, f_k)
        self.assertEqual(len(p_t), 1)
        self.assertAlmostEqual(p_t[0], 1)

        # add x_10 into a new table with dish 1
        k_new = 1
        t_new = model.add_new_table(j, k_new)
        self.assertEqual(t_new, 1)

        self.assertListEqual(model.using_t[j], [0, 1])
        self.assertListEqual(model.using_k, [0, 1])
        self.assertEqual(model.n_jt[j][t_new], 0) # まだ 0

        model.seat_at_table(j, i, t_new)
        self.assertEqual(model.t_ji[j][i], 1)
        self.assertEqual(model.n_jt[j][t_new], 1) # ふえた
        self.assertAlmostEqual(model.n_kv[k_new][v], beta + 2)


unittest.main()


########NEW FILE########
__FILENAME__ = twentygroups
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 20 Groups Loader
#   - load data at http://kdd.ics.uci.edu/databases/20newsgroups/20newsgroups.html
# This code is available under the MIT License.
# (c)2012 Nakatani Shuyo / Cybozu Labs Inc.

import os, codecs, re

STOPWORDS = """
a b c d e f g h i j k l m n o p q r s t u v w x y z
the of in and have to it was or were this that with is some on for so
how you if would com be your my one not never then take for an can no
but aaa when as out just from does they back up she those who another
her do by must what there at very are am much way all any other me he
something someone doesn his also its has into us him than about their
may too will had been we them why did being over without these could
out which only should even well more where after while anyone our now
such under two ten else always going either each however non let done
ever between anything before every same since because quite sure here
nothing new don off still down yes around few many own
go get know think like make say see look use said
"""

def readTerms(target):
    with codecs.open(target, 'rb', 'latin1') as f:
        text = re.sub(r'^(.+\n)*\n', '', f.read())
    return [w.group(0).lower() for w in re.finditer(r'[A-Za-z]+', text)]

class Loader:
    def __init__(self, dirpath, freq_threshold=1, docs_threshold_each_label=100, includes_stopwords=False):
        if includes_stopwords:
            stopwords = set(re.split(r'\s', STOPWORDS))
        else:
            stopwords = []

        self.resourcenames = []
        self.labels = []
        self.label2id = dict()
        self.doclabelids = []
        vocacount = dict()
        tempdocs = []

        dirlist = os.listdir(dirpath)
        for label in dirlist:
            path = os.path.join(dirpath, label)
            if os.path.isdir(path):
                label_id = len(self.labels)
                self.label2id[label] = label_id
                self.labels.append(label)

                filelist = os.listdir(path)
                for i, s in enumerate(filelist):
                    if i >= docs_threshold_each_label: break

                    self.resourcenames.append(os.path.join(label, s))
                    self.doclabelids.append(label_id)

                    wordlist = readTerms(os.path.join(path, s))
                    tempdocs.append(wordlist)

                    for w in wordlist:
                        if w in vocacount:
                            vocacount[w] += 1
                        else:
                            vocacount[w] = 1

        self.vocabulary = []
        self.vocabulary2id = dict()
        for w in vocacount:
            if w not in stopwords and vocacount[w] >= freq_threshold:
                self.vocabulary2id[w] = len(self.vocabulary)
                self.vocabulary.append(w)

        self.docs = []
        for doc in tempdocs:
            self.docs.append([self.vocabulary2id[w] for w in doc if w in self.vocabulary2id])

def main():
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("--alpha", dest="alpha", type="float", help="parameter alpha", default=0.1)
    parser.add_option("--beta", dest="beta", type="float", help="parameter beta", default=0.001)
    parser.add_option("-k", dest="K", type="int", help="number of topics", default=10)
    parser.add_option("-i", dest="iteration", type="int", help="iteration count", default=20)
    parser.add_option("--word_freq_threshold", dest="word_freq_threshold", type="int", default=3)
    parser.add_option("--docs_threshold_each_label", dest="docs_threshold_each_label", type="int", default=100)
    parser.add_option("-d", dest="dir", help="directory of 20-newsgroups dataset", default="./20groups/mini_newsgroups/")
    (options, args) = parser.parse_args()

    corpus = Loader(options.dir, options.word_freq_threshold, options.docs_threshold_each_label, True)
    V = len(corpus.vocabulary)

    import lda
    model = lda.LDA(options.K, options.alpha, options.beta, corpus.docs, V, True)
    print "corpus=%d, words=%d, K=%d, a=%f, b=%f" % (len(corpus.docs), V, options.K, options.alpha, options.beta)

    pre_perp = model.perplexity()
    print "initial perplexity=%f" % pre_perp
    for i in xrange(options.iteration):
        model.inference()
        perp = model.perplexity()
        print "-%d p=%f" % (i + 1, perp)
    lda.output_word_topic_dist(model, corpus.vocabulary)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = vocabulary
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This code is available under the MIT License.
# (c)2010-2011 Nakatani Shuyo / Cybozu Labs Inc.

import nltk, re

def load_corpus(range):
    m = re.match(r'(\d+):(\d+)$', range)
    if m:
        start = int(m.group(1))
        end = int(m.group(2))
        from nltk.corpus import brown as corpus
        return [corpus.words(fileid) for fileid in corpus.fileids()[start:end]]

def load_file(filename):
    corpus = []
    f = open(filename, 'r')
    for line in f:
        doc = re.findall(r'\w+(?:\'\w+)?',line)
        if len(doc)>0:
            corpus.append(doc)
    f.close()
    return corpus

#stopwords_list = nltk.corpus.stopwords.words('english')
stopwords_list = "a,s,able,about,above,according,accordingly,across,actually,after,afterwards,again,against,ain,t,all,allow,allows,almost,alone,along,already,also,although,always,am,among,amongst,an,and,another,any,anybody,anyhow,anyone,anything,anyway,anyways,anywhere,apart,appear,appreciate,appropriate,are,aren,t,around,as,aside,ask,asking,associated,at,available,away,awfully,be,became,because,become,becomes,becoming,been,before,beforehand,behind,being,believe,below,beside,besides,best,better,between,beyond,both,brief,but,by,c,mon,c,s,came,can,can,t,cannot,cant,cause,causes,certain,certainly,changes,clearly,co,com,come,comes,concerning,consequently,consider,considering,contain,containing,contains,corresponding,could,couldn,t,course,currently,definitely,described,despite,did,didn,t,different,do,does,doesn,t,doing,don,t,done,down,downwards,during,each,edu,eg,eight,either,else,elsewhere,enough,entirely,especially,et,etc,even,ever,every,everybody,everyone,everything,everywhere,ex,exactly,example,except,far,few,fifth,first,five,followed,following,follows,for,former,formerly,forth,four,from,further,furthermore,get,gets,getting,given,gives,go,goes,going,gone,got,gotten,greetings,had,hadn,t,happens,hardly,has,hasn,t,have,haven,t,having,he,he,s,hello,help,hence,her,here,here,s,hereafter,hereby,herein,hereupon,hers,herself,hi,him,himself,his,hither,hopefully,how,howbeit,however,i,d,i,ll,i,m,i,ve,ie,if,ignored,immediate,in,inasmuch,inc,indeed,indicate,indicated,indicates,inner,insofar,instead,into,inward,is,isn,t,it,it,d,it,ll,it,s,its,itself,just,keep,keeps,kept,know,knows,known,last,lately,later,latter,latterly,least,less,lest,let,let,s,like,liked,likely,little,look,looking,looks,ltd,mainly,many,may,maybe,me,mean,meanwhile,merely,might,more,moreover,most,mostly,much,must,my,myself,name,namely,nd,near,nearly,necessary,need,needs,neither,never,nevertheless,new,next,nine,no,nobody,non,none,noone,nor,normally,not,nothing,novel,now,nowhere,obviously,of,off,often,oh,ok,okay,old,on,once,one,ones,only,onto,or,other,others,otherwise,ought,our,ours,ourselves,out,outside,over,overall,own,particular,particularly,per,perhaps,placed,please,plus,possible,presumably,probably,provides,que,quite,qv,rather,rd,re,really,reasonably,regarding,regardless,regards,relatively,respectively,right,said,same,saw,say,saying,says,second,secondly,see,seeing,seem,seemed,seeming,seems,seen,self,selves,sensible,sent,serious,seriously,seven,several,shall,she,should,shouldn,t,since,six,so,some,somebody,somehow,someone,something,sometime,sometimes,somewhat,somewhere,soon,sorry,specified,specify,specifying,still,sub,such,sup,sure,t,s,take,taken,tell,tends,th,than,thank,thanks,thanx,that,that,s,thats,the,their,theirs,them,themselves,then,thence,there,there,s,thereafter,thereby,therefore,therein,theres,thereupon,these,they,they,d,they,ll,they,re,they,ve,think,third,this,thorough,thoroughly,those,though,three,through,throughout,thru,thus,to,together,too,took,toward,towards,tried,tries,truly,try,trying,twice,two,un,under,unfortunately,unless,unlikely,until,unto,up,upon,us,use,used,useful,uses,using,usually,value,various,very,via,viz,vs,want,wants,was,wasn,t,way,we,we,d,we,ll,we,re,we,ve,welcome,well,went,were,weren,t,what,what,s,whatever,when,whence,whenever,where,where,s,whereafter,whereas,whereby,wherein,whereupon,wherever,whether,which,while,whither,who,who,s,whoever,whole,whom,whose,why,will,willing,wish,with,within,without,won,t,wonder,would,would,wouldn,t,yes,yet,you,you,d,you,ll,you,re,you,ve,your,yours,yourself,yourselves,zero".split(',')
recover_list = {"wa":"was", "ha":"has"}
wl = nltk.WordNetLemmatizer()

def is_stopword(w):
    return w in stopwords_list
def lemmatize(w0):
    w = wl.lemmatize(w0.lower())
    #if w=='de': print w0, w
    if w in recover_list: return recover_list[w]
    return w

class Vocabulary:
    def __init__(self, excluds_stopwords=False):
        self.vocas = []        # id to word
        self.vocas_id = dict() # word to id
        self.docfreq = []      # id to document frequency
        self.excluds_stopwords = excluds_stopwords

    def term_to_id(self, term0):
        term = lemmatize(term0)
        if not re.match(r'[a-z]+$', term): return None
        if self.excluds_stopwords and is_stopword(term): return None
        if term not in self.vocas_id:
            voca_id = len(self.vocas)
            self.vocas_id[term] = voca_id
            self.vocas.append(term)
            self.docfreq.append(0)
        else:
            voca_id = self.vocas_id[term]
        return voca_id

    def doc_to_ids(self, doc):
        #print ' '.join(doc)
        list = []
        words = dict()
        for term in doc:
            id = self.term_to_id(term)
            if id != None:
                list.append(id)
                if not words.has_key(id):
                    words[id] = 1
                    self.docfreq[id] += 1
        if "close" in dir(doc): doc.close()
        return list

    def cut_low_freq(self, corpus, threshold=1):
        new_vocas = []
        new_docfreq = []
        self.vocas_id = dict()
        conv_map = dict()
        for id, term in enumerate(self.vocas):
            freq = self.docfreq[id]
            if freq > threshold:
                new_id = len(new_vocas)
                self.vocas_id[term] = new_id
                new_vocas.append(term)
                new_docfreq.append(freq)
                conv_map[id] = new_id
        self.vocas = new_vocas
        self.docfreq = new_docfreq

        def conv(doc):
            new_doc = []
            for id in doc:
                if id in conv_map: new_doc.append(conv_map[id])
            return new_doc
        return [conv(doc) for doc in corpus]

    def __getitem__(self, v):
        return self.vocas[v]

    def size(self):
        return len(self.vocas)

    def is_stopword_id(self, id):
        return self.vocas[id] in stopwords_list


########NEW FILE########
__FILENAME__ = knlm
#!/usr/bin/env python
# encode: utf-8

# n-Gram Language Model with Knerser-Ney Smoother
# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.

import sys, codecs, re, numpy

class NGram(dict):
    def __init__(self, N, depth=1):
        self.freq = 0
        self.N = N
        self.depth = depth
    def inc(self, v):
        if self.depth <= self.N:
            if v not in self:
                self[v] = NGram(self.N, self.depth + 1)
            self[v].freq += 1
            return self[v]
    def dump(self):
        if self.depth <= self.N:
            return "%d:{%s}" % (self.freq, ",".join("'%s':%s" % (k,d.dump()) for k,d in self.iteritems()))
        return "%d" % self.freq

    def probKN(self, D, given=""):
        assert D >= 0.0 and D <= 1.0
        if given == "":
            voca = self.keys()
            n = float(self.freq)
            return voca, [self[v].freq / n for v in voca]
        else:
            if len(given) >= self.N:
                given = given[-(self.N-1):]
            voca, low_prob = self.probKN(D, given[1:])
            cur_ngram = self
            for v in given:
                if v not in cur_ngram: return voca, low_prob
                cur_ngram = cur_ngram[v]
            g = 0.0 # for normalization
            freq = []
            for v in voca:
                c = cur_ngram[v].freq if v in cur_ngram else 0
                if c > D:
                    g += D
                    c -= D
                freq.append(c)
            n = float(cur_ngram.freq)
            return voca, [(c + g * lp) / n for c, lp in zip(freq, low_prob)]

class Generator(object):
    def __init__(self, ngram):
        self.ngram = ngram
        self.start()
    def start(self):
        self.pointers = []
    def inc(self, v):
        pointers = self.pointers + [self.ngram]
        self.pointers = [d.inc(v) for d in pointers if d != None]
        self.ngram.freq += 1

def main():
    import optparse

    parser = optparse.OptionParser()
    parser.add_option("-n", dest="ngram", type="int", help="n-gram", default=7)
    parser.add_option("-d", dest="discount", type="float", help="discount parameter of Knerser-Ney", default=0.5)
    parser.add_option("-i", dest="numgen", type="int", help="number of texts to generate", default=100)
    parser.add_option("-e", dest="encode", help="character code of input file(s)", default='utf-8')
    parser.add_option("-o", dest="output", help="output filename", default="generated.txt")
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    (opt, args) = parser.parse_args()

    numpy.random.seed(opt.seed)

    START = u"\u0001"
    END = u"\u0002"

    ngram = NGram(opt.ngram)
    gen = Generator(ngram)
    for filename in args:
        with codecs.open(filename, "rb", opt.encode) as f:
            for s in f:
                s = s.strip()
                if len(s) == 0: continue
                s = START + s + END
                gen.start()
                for c in s:
                    gen.inc(c)

    D = opt.discount
    with codecs.open(opt.output, "wb", "utf-8") as f:
        for n in xrange(opt.numgen):
            st = START
            for i in xrange(1000):
                voca, prob = ngram.probKN(D, st)
                i = numpy.random.multinomial(1, prob).argmax()
                v = voca[i]
                if v == END: break
                st += v
            f.write(st[1:])
            f.write("\n")

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = knsmooth
#!/usr/bin/env python
# encode: utf-8

# Knerser-Ney Smoother
# This code is available under the MIT License.
# (c)2012 Nakatani Shuyo / Cybozu Labs Inc.

import sys, codecs, math, re, collections

re_word = re.compile(u'[a-z\u00c0-\u024f]+')

class Distribution(dict):
    def __init__(self, arg=None):
        if arg == None:
            dict.__init__(self)
        else:
            dict.__init__(self, arg)
        self.n = self.n1 = self.n2 = self.n3 = self.n4 = 0
        self.N1 = collections.defaultdict(int)
        self.N1plus = collections.defaultdict(int)
        self.N2 = collections.defaultdict(int)
        self.N3plus = collections.defaultdict(int)
    def __setitem__(self, w, v):
        dict.__setitem__(self, w, v)
        self.n += v
        k = w[:-1]
        self.N1plus[k] += 1
        if v == 1:
            self.n1 += 1
            self.N1[k] += 1
        if v == 2:
            self.n2 += 1
            self.N2[k] += 1
        if v == 3: self.n3 += 1
        if v == 4: self.n4 += 1
        if v >= 3: self.N3plus[k] += 1
    def __getitem__(self, k):
        return dict.__getitem__(self, k) if k in self else 0

def loaddist(filename, threshold=0):
    dist = Distribution()
    with codecs.open(filename, "rb", "utf-8") as f:
        for s in f:
            w, c = s.split("\t")
            c = int(c)
            if c > threshold: dist[tuple(w.split(" "))] = c
    return dist

def maxlikelifood(gram1, gram2, gram3, text):
    w2 = w1 = ""
    for m in re_word.finditer(text):
        w = m.group(0)
        print "\np(%s) = %d / %d = %.5f" % (w, gram1[(w,)], gram1.n, float(gram1[(w,)]) / gram1.n)
        if gram1[(w1,)]>0:
            print "p(%s | %s) = %d / %d = %.5f" % (w, w1, gram2[(w1, w)], gram1[(w1,)], float(gram2[(w1, w)]) / gram1[(w1,)])
        if gram2[(w2, w1)]>0:
            print "p(%s | %s %s) = %d / %d = %.5f" % (w, w2, w1, gram3[(w2, w1, w)], gram2[(w2, w1)], float(gram3[(w2, w1, w)]) / gram2[(w2, w1)])
        w2, w1 = w1, w

def golden_section_search(func, min, max):
    x1, x3 = min, max
    x2 = (x3 - x1) / (3 + math.sqrt(5)) * 2 + x1
    f1, f2, f3 = func(x1), func(x2), func(x3)
    while (x3 - x1) > 0.0001 * (max - min):
        x4 = x1 + x3 - x2
        f4 = func(x4)
        if f4 < f2:
            if x2 < x4:
                x1, x2 = x2, x4
                f1, f2 = f2, f4
            else:
                x2, x3 = x4, x2
                f2, f3 = f4, f2
        else:
            if x4 > x2:
                x3, f3 = x4, f4
            else:
                x1, f1 = x4, f4
    return x2, f2

def unigram_perplexity(gram1, test, V, alpha):
    ppl = 0.0
    N = 0
    denom = gram1.n + V * alpha
    for s in test:
        for w in s:
            p = (gram1[(w,)] + alpha) / denom
            ppl -= math.log(p)
            N += 1
    return math.exp(ppl / N)

def bigram_perplexity(gram1, gram2, test, V, alpha1, alpha2):
    ppl = 0.0
    N = 0
    for s in test:
        w1 = ""
        for w in s:
            if w1 == "":
                p = (gram1[(w,)] + alpha1) / (gram1.n + V * alpha1)
            else:
                p = (gram2[(w1, w)] + alpha2) / (gram1[(w1,)] + V * alpha2)
            ppl -= math.log(p)
            w1 = w
            N += 1
    return math.exp(ppl / N)

def trigram_perplexity(gram1, gram2, gram3, test, V, alpha1, alpha2, alpha3):
    ppl = 0.0
    N = 0
    for s in test:
        w1 = w2 = ""
        for w in s:
            if w1 == "":
                p = (gram1[(w,)] + alpha1) / (gram1.n + V * alpha1)
            elif w2 == "":
                p = (gram2[(w1, w)] + alpha2) / (gram1[(w1,)] + V * alpha2)
            else:
                p = (gram3[(w2, w1, w)] + alpha3) / (gram2[(w2, w1)] + V * alpha3)
            ppl -= math.log(p)
            w2, w1 = w1, w
            N += 1
    return math.exp(ppl / N)

def kn1_perplexity(gram1, test, V, D=None):
    if D == None:
        D = gram1.n1 / float(gram1.n1 + 2 * gram1.n2)

    ppl = 0.0
    N = 0
    for s in test:
        for w in s:
            p = (max(gram1[(w,)] - D, 0) + D * gram1.N1plus[()] / V ) / gram1.n
            ppl -= math.log(p)
            N += 1
    return math.exp(ppl / N)

def mkn_heuristic_D(gram):
    Y = gram.n1 / float(gram.n1 + 2 * gram.n2)
    D1 = 1 - 2 * Y * gram.n2 / gram.n1
    D2 = 2 - 3 * Y * gram.n3 / gram.n2
    D3 = 3 - 4 * Y * gram.n4 / gram.n3
    return (D1, D2, D3)

def mkn1_perplexity(gram1, test, V):
    D1, D2, D3 = mkn_heuristic_D(gram1)
    gamma = D1 * gram1.n1 + D2 * gram1.n2 + D3 * gram1.N3plus[()]

    ppl = 0.0
    N = 0
    for s in test:
        for w in s:
            c = gram1[(w,)]
            D = 0  if c == 0 else D1 if c == 1 else D2 if c == 2 else D3
            p = (c - D + gamma / V ) / gram1.n
            ppl -= math.log(p)
            N += 1
    return math.exp(ppl / N)

def kn2_perplexity(gram1, gram2, test, V, D1=None, D2=None):
    if D1 == None:
        D1 = gram1.n1 / float(gram1.n1 + 2 * gram1.n2)
    if D2 == None:
        D2 = gram2.n1 / float(gram2.n1 + 2 * gram2.n2)

    ppl = 0.0
    N = 0
    for s in test:
        w1 = ''
        for w in s:
            c1 = gram1[(w,)]
            p = (max(c1 - D1, 0) + D1 * gram1.N1plus[()] / V ) / gram1.n
            if (w1,) in gram1:
                c2 = gram2[(w1, w)]
                p = (max(c2 - D2, 0) + D2 * gram2.N1plus[(w1,)] * p ) / gram1[(w1,)]
            ppl -= math.log(p)
            N += 1
            w1 = w
    return math.exp(ppl / N)

def mkn2_perplexity(gram1, gram2, test, V):
    D11, D12, D13 = mkn_heuristic_D(gram1)
    D21, D22, D23 = mkn_heuristic_D(gram2)
    gamma1 = D11 * gram1.n1 + D12 * gram1.n2 + D13 * gram1.N3plus[()]

    ppl = 0.0
    N = 0
    for s in test:
        w1 = ''
        for w in s:
            c1 = gram1[(w,)]
            D = 0 if c1 == 0 else D11 if c1 == 1 else D12 if c1 == 2 else D13
            p = (c1 - D + gamma1 / V ) / gram1.n
            if (w1,) in gram1:
                c2 = gram2[(w1, w)]
                D = 0 if c2 == 0 else D21 if c2 == 1 else D22 if c2 == 2 else D23
                gamma = D21 * gram2.N1[(w1,)] + D22 * gram2.N2[(w1,)] + D23 * gram2.N3plus[(w1,)]
                p = (c2 - D + gamma * p ) / gram1[(w1,)]
            ppl -= math.log(p)
            N += 1
            w1 = w
    return math.exp(ppl / N)

def kn3_perplexity(gram1, gram2, gram3, test, V, D1=None, D2=None, D3=None):
    if D1 == None:
        D1 = gram1.n1 / float(gram1.n1 + 2 * gram1.n2)
    if D2 == None:
        D2 = gram2.n1 / float(gram2.n1 + 2 * gram2.n2)
    if D3 == None:
        D3 = gram3.n1 / float(gram3.n1 + 2 * gram3.n2)

    ppl = 0.0
    N = 0
    for s in test:
        w1 = w2 = ''
        for w in s:
            c1 = gram1[(w,)]
            p = (max(c1 - D1, 0) + D1 * gram1.N1plus[()] / V ) / gram1.n
            if (w1,) in gram1:
                c2 = gram2[(w1, w)]
                p = (max(c2 - D2, 0) + D2 * gram2.N1plus[(w1,)] * p ) / gram1[(w1,)]
                if (w2, w1) in gram2:
                    c3 = gram3[(w2, w1, w)]
                    p = (max(c3 - D3, 0) + D3 * gram3.N1plus[(w2, w1,)] * p ) / gram2[(w2, w1)]
            ppl -= math.log(p)
            N += 1
            w2, w1 = w1, w
    return math.exp(ppl / N)

def mkn3_perplexity(gram1, gram2, gram3, test, V):
    D11, D12, D13 = mkn_heuristic_D(gram1)
    D21, D22, D23 = mkn_heuristic_D(gram2)
    D31, D32, D33 = mkn_heuristic_D(gram3)
    gamma1 = D11 * gram1.n1 + D12 * gram1.n2 + D13 * gram1.N3plus[()]

    ppl = 0.0
    N = 0
    for s in test:
        w2 = w1 = ''
        for w in s:
            c1 = gram1[(w,)]
            D = 0 if c1 == 0 else D11 if c1 == 1 else D12 if c1 == 2 else D13
            p = (c1 - D + gamma1 / V ) / gram1.n
            if (w1,) in gram1:
                c2 = gram2[(w1, w)]
                D = 0 if c2 == 0 else D21 if c2 == 1 else D22 if c2 == 2 else D23
                gamma = D21 * gram2.N1[(w1,)] + D22 * gram2.N2[(w1,)] + D23 * gram2.N3plus[(w1,)]
                p = (c2 - D + gamma * p ) / gram1[(w1,)]
                if (w2, w1) in gram2:
                    c3 = gram3[(w2, w1, w)]
                    D = 0 if c3 == 0 else D31 if c3 == 1 else D32 if c3 == 2 else D33
                    gamma = D31 * gram3.N1[(w2,w1)] + D32 * gram3.N2[(w2,w1)] + D33 * gram3.N3plus[(w2,w1)]
                    p = (c3 - D + gamma * p ) / gram2[(w2, w1)]
            ppl -= math.log(p)
            N += 1
            w2, w1 = w1, w
    return math.exp(ppl / N)

def main():
    import optparse, random, nltk

    parser = optparse.OptionParser()
    parser.add_option("-c", dest="corpus", help="corpus module name under nltk.corpus (e.g. brown, reuters)", default='brown')
    parser.add_option("-r", dest="testrate", type="float", help="rate of test dataset in corpus", default=0.1)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    (opt, args) = parser.parse_args()

    random.seed(opt.seed)

    m = __import__('nltk.corpus', globals(), locals(), [opt.corpus], -1)
    corpus = getattr(m, opt.corpus)
    ids = corpus.fileids()
    D = len(ids)
    print "found corpus : %s (D=%d)" % (opt.corpus, D)

    testids = set(random.sample(ids, int(D * opt.testrate)))
    trainids = [id for id in ids if id not in testids]
    trainwords = [w.lower() for w in corpus.words(trainids)]

    freq1 = nltk.FreqDist(trainwords)
    gram1 = Distribution()
    for w, c in freq1.iteritems():
        gram1[(w,)] = c
    print "# of terms=%d, vocabulary size=%d" % (gram1.n, len(gram1))

    gram2 = Distribution()
    for w, c in nltk.FreqDist(nltk.bigrams(trainwords)).iteritems():
        gram2[w] = c
    gram3 = Distribution()
    for w, c in nltk.FreqDist(nltk.trigrams(trainwords)).iteritems():
        gram3[w] = c

    #maxlikelifood(gram1, gram2, gram3, "this is a pen")
    #maxlikelifood(gram1, gram2, gram3, "the associated press microsoft looking at making its own smartphone?")

    testset = []
    voca = set(freq1.iterkeys())
    for id in testids:
        f = corpus.words(id)
        doc = [w.lower() for w in f]
        f.close()

        testset.append(doc)
        for w in doc:
            voca.add(w)
    V = len(voca)

    D1 = gram1.n1 / float(gram1.n1 + 2 * gram1.n2)
    D2 = gram2.n1 / float(gram2.n1 + 2 * gram2.n2)
    D3 = gram3.n1 / float(gram3.n1 + 2 * gram3.n2)

    print "\nUNIGRAM:"
    alpha1, minppl = golden_section_search(lambda a:unigram_perplexity(gram1, testset, V, a), 0.0001, 1.0)
    print "additive smoother: alpha1=%.4f, perplexity=%.3f" % (alpha1, minppl)
    print "Kneser-Ney: heuristic D=%.3f, perplexity=%.3f" % (D1, kn1_perplexity(gram1, testset, V, D1))
    D1min, minppl = golden_section_search(lambda d:kn1_perplexity(gram1, testset, V, d), 0.0001, 0.9999)
    print "Kneser-Ney: minimum D=%.3f, perplexity=%.3f" % (D1min, minppl)
    print "modified Kneser-Ney: perplexity=%.3f" % mkn1_perplexity(gram1, testset, V)

    print "\nBIGRAM:"
    alpha2, minppl = golden_section_search(lambda a:bigram_perplexity(gram1, gram2, testset, V, alpha1, a), 0.0001, 1.0)
    print "additive smoother: alpha2=%.4f, perplexity=%.3f" % (alpha2, minppl)
    print "Kneser-Ney: heuristic D=%.3f, perplexity=%.3f" % (D2, kn2_perplexity(gram1, gram2, testset, V, D1, D2))
    D2min, minppl = golden_section_search(lambda a:kn2_perplexity(gram1, gram2, testset, V, D1, a), 0.0001, 0.9999)
    print "Kneser-Ney: minimum D=%.3f, perplexity=%.3f" % (D2min, minppl)
    print "modified Kneser-Ney: perplexity=%.3f" % mkn2_perplexity(gram1, gram2, testset, V)

    print "\nTRIGRAM:"
    alpha3, minppl = golden_section_search(lambda a:trigram_perplexity(gram1, gram2, gram3, testset, V, alpha1, alpha2, a), 0.0001, 1.0)
    print "additive smoother: alpha3=%.4f, perplexity=%.3f" % (alpha3, minppl)
    print "Kneser-Ney: heuristic D=%.3f, perplexity=%.3f" % (D3, kn3_perplexity(gram1, gram2, gram3, testset, V, D1, D2, D3))
    D3min, minppl = golden_section_search(lambda a:kn3_perplexity(gram1, gram2, gram3, testset, V, D1, D2, a), 0.0001, 0.9999)
    print "Kneser-Ney: minimum D=%.3f, perplexity=%.3f" % (D3min, minppl)
    print "modified Kneser-Ney: perplexity=%.3f" % mkn3_perplexity(gram1, gram2, gram3, testset, V)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = rnnlm
#!/usr/bin/env python
# encode: utf-8

# Recurrent Neural Network Language Model
# This code is available under the MIT License.
# (c)2014 Nakatani Shuyo / Cybozu Labs Inc.

import numpy, nltk, codecs, re
import optparse

class RNNLM:
    def __init__(self, V, K=10):
        self.K = K
        self.v = V
        self.U = numpy.random.randn(K, V) / 3
        self.W = numpy.random.randn(K, K) / 3
        self.V = numpy.random.randn(V, K) / 3

    def learn(self, docs, alpha=0.1):
        index = numpy.arange(len(docs))
        numpy.random.shuffle(index)
        for i in index:
            doc = docs[i]
            pre_s = numpy.zeros(self.K)
            pre_w = 0 # <s>
            for w in doc:
                s = 1 / (numpy.exp(- numpy.dot(self.W, pre_s) - self.U[:, pre_w]) + 1)
                z = numpy.dot(self.V, s)
                y = numpy.exp(z - z.max())
                y = y / y.sum()
                y[w] -= 1  # -e0
                eha = numpy.dot(y, self.V) * s * (s - 1) * alpha # eh * alpha
                self.V -= numpy.outer(y, s * alpha)
                self.U[:, pre_w] += eha
                self.W += numpy.outer(pre_s, eha)
                pre_w = w
                pre_s = s

    def perplexity(self, docs):
        log_like = 0
        N = 0
        for doc in docs:
            s = numpy.zeros(self.K)
            pre_w = 0 # <s>
            for w in doc:
                s = 1 / (numpy.exp(- numpy.dot(self.W, s) - self.U[:, pre_w]) + 1)
                z = numpy.dot(self.V, s)
                y = numpy.exp(z - z.max())
                y = y / y.sum()
                log_like -= numpy.log(y[w])
                pre_w = w
            N += len(doc)
        return log_like / N

    def dist(self, w):
        if w==0:
            self.s = numpy.zeros(self.K)
        else:
            self.s = 1 / (numpy.exp(- numpy.dot(self.W, self.s) - self.U[:, w]) + 1)
            z = numpy.dot(self.V, self.s)
            y = numpy.exp(z - z.max())
            return y / y.sum()

class RNNLM_BPTT(RNNLM):
    """RNNLM with BackPropagation Through Time"""
    def learn(self, docs, alpha=0.1, tau=3):
        index = numpy.arange(len(docs))
        numpy.random.shuffle(index)
        for i in index:
            doc = docs[i]
            pre_s = [numpy.zeros(self.K)]
            pre_w = [0] # <s>
            for w in doc:
                s = 1 / (numpy.exp(- numpy.dot(self.W, pre_s[-1]) - self.U[:, pre_w[-1]]) + 1)
                z = numpy.dot(self.V, s)
                y = numpy.exp(z - z.max())
                y = y / y.sum()

                # calculate errors
                y[w] -= 1  # -e0
                eh = [numpy.dot(y, self.V) * s * (s - 1)] # eh[t]
                for t in xrange(min(tau, len(pre_s)-1)):
                    st = pre_s[-1-t]
                    eh.append(numpy.dot(eh[-1], self.W) * st * (1 - st))

                # update parameters
                pre_w.append(w)
                pre_s.append(s)
                self.V -= numpy.outer(y, s * alpha)
                for t in xrange(len(eh)):
                    self.U[:, pre_w[-1-t]] += eh[t] * alpha
                    self.W += numpy.outer(pre_s[-2-t], eh[t]) * alpha

class BIGRAM:
    def __init__(self, V, alpha=0.01):
        self.V = V
        self.alpha = alpha
        self.count = dict()
        self.amount = numpy.zeros(V, dtype=int)
    def learn(self, docs):
        for doc in docs:
            pre_w = 0 # <s>
            for w in doc:
                if pre_w not in self.count:
                    self.count[pre_w] = {w:1}
                elif w not in self.count[pre_w]:
                    self.count[pre_w][w] = 1
                else:
                    self.count[pre_w][w] += 1
                self.amount[pre_w] += 1
                pre_w = w

    def perplexity(self, docs):
        log_like = 0
        N = 0
        va = self.V * self.alpha
        for doc in docs:
            pre_w = 0 # <s>
            for w in doc:
                c = 0
                if pre_w in self.count and w in self.count[pre_w]:
                    c = self.count[pre_w][w]
                log_like -= numpy.log((c + self.alpha) / (self.amount[pre_w] + va))
                pre_w = w
            N += len(doc)
        return log_like / N

def CorpusWrapper(corpus):
    for id in corpus.fileids():
        yield corpus.words(id)

def main():
    parser = optparse.OptionParser()
    parser.add_option("-c", dest="corpus", help="corpus module name under nltk.corpus (e.g. brown, reuters)")
    parser.add_option("-f", dest="filename", help="corpus filename name (each line is regarded as a document)")
    parser.add_option("-a", dest="alpha", type="float", help="additive smoothing parameter of bigram", default=0.001)
    parser.add_option("-k", dest="K", type="int", help="size of hidden layer", default=10)
    parser.add_option("-i", dest="I", type="int", help="learning interval", default=10)
    parser.add_option("-o", dest="output", help="output filename of rnnlm model")
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    (opt, args) = parser.parse_args()

    numpy.random.seed(opt.seed)

    if opt.corpus:
        m = __import__('nltk.corpus', globals(), locals(), [opt.corpus], -1)
        corpus = CorpusWrapper(getattr(m, opt.corpus))
    elif opt.filename:
        corpus = []
        with codecs.open(opt.filename, "rb", "utf-8") as f:
            for s in f:
                s = re.sub(r'(["\.,!\?:;])', r' \1 ', s).strip()
                d = re.split(r'\s+', s)
                if len(d) > 0: corpus.append(d)
    else:
        raise "need -f or -c"

    voca = {"<s>":0, "</s>":1}
    vocalist = ["<s>", "</s>"]
    docs = []
    N = 0
    for words in corpus:
        doc = []
        for w in words:
            w = w.lower()
            if w not in voca:
                voca[w] = len(vocalist)
                vocalist.append(w)
            doc.append(voca[w])
        if len(doc) > 0:
            N += len(doc)
            doc.append(1) # </s>
            docs.append(doc)

    D = len(docs)
    V = len(vocalist)
    print "corpus : %s (D=%d)" % (opt.corpus or opt.filename, D)
    print "vocabulary : %d / %d" % (V, N)

    print ">> RNNLM(K=%d)" % opt.K
    model = RNNLM_BPTT(V, opt.K)
    a = 1.0
    for i in xrange(opt.I):
        print i, model.perplexity(docs)
        model.learn(docs, a)
        a = a * 0.95 + 0.01
    print opt.I, model.perplexity(docs)

    if opt.output:
        import cPickle
        with open(opt.output, 'wb') as f:
            cPickle.dump([model, voca, vocalist], f)

    print ">> BIGRAM(alpha=%f)" % opt.alpha
    model = BIGRAM(V, opt.alpha)
    model.learn(docs)
    print model.perplexity(docs)


"""
    testids = set(random.sample(ids, int(D * opt.testrate)))
    trainids = [id for id in ids if id not in testids]
    trainwords = [w.lower() for w in corpus.words(trainids)]

    testset = []
    voca = set(freq1.iterkeys())
    for id in testids:
        f = corpus.words(id)
        doc = [w.lower() for w in f]
        f.close()

        testset.append(doc)
        for w in doc:
            voca.add(w)
"""
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = wordcount
#!/usr/bin/env python


import re, sys

class NaiveCounting:
    def __init__(self):
        self.map = dict()
    def add(self, word):
        if word in self.map:
            self.map[word] += 1
        else:
            self.map[word] = 1

class SpaceSaving:
    def __init__(self, k):
        self.k = k
        self.map = dict()
    def add(self, word):
        if word in self.map:
            self.map[word] += 1
        elif len(self.map) < self.k:
            self.map[word] = 1
        else:
            j = min(self.map, key=lambda x:self.map[x])
            cj = self.map.pop(j)
            self.map[word] = cj + 1


text = ""
for filename in sys.argv:
    with open(filename, "rb") as f:
        text += f.read()

c1 = NaiveCounting()
c2 = SpaceSaving(1000)
c3 = SpaceSaving(100)

n = 0
for m in re.finditer(r'[A-Za-z]+', text):
    word = m.group(0).lower()
    c1.add(word)
    c2.add(word)
    c3.add(word)
    n += 1

print "total words = %d" % n

words = c1.map.items()
words.sort(key=lambda x:(-x[1], x[0]))
m2 = c2.map
m3 = c3.map
for i, x in enumerate(words):
    print "%d\t%s\t%d\t%d\t%d" % (i+1, x[0], x[1], m2.get(x[0],0), m3.get(x[0],0))



########NEW FILE########
__FILENAME__ = ssnb
#!/usr/bin/env python
# encode: utf-8

# Semi-Supervised Naive Bayes Classifier with EM-Algorithm
#    [K. Nigam, A. McCallum, S. Thrun, and T. Mitchell 2000] Text Classifcation from Labeled and Unlabeled Documents using EM. Machine Learning

# This code is available under the MIT License.
# (c)2013 Nakatani Shuyo / Cybozu Labs Inc.


import optparse
import numpy, scipy
import sklearn.datasets
from sklearn.feature_extraction.text import CountVectorizer

def performance(i, test, phi, theta):
    z = test.data * numpy.log(phi) + numpy.log(theta) # M * K
    z -= z.max(axis=1)[:, None]
    z = numpy.exp(z)
    z /= z.sum(axis=1)[:, None]
    predict = z.argmax(axis=1)
    correct = (test.target == predict).sum()
    T = test.data.shape[0]
    accuracy = float(correct) / T
    log_likelihood = numpy.log(numpy.choose(test.target, z.T) + 1e-14).sum() / T

    print "%d : %d / %d = %.3f, average of log likelihood = %.3f" % (i, correct, T, accuracy, log_likelihood)
    return accuracy

def estimate(data, test, alpha, beta, n, K=None):
    M, V = data.data.shape
    if not K:
        K = data.target.max() + 1
    #if opt.training:
    #    train = [int(x) for x in opt.training.split(",")]
    #else:
    train = []
    for k in xrange(K):
        train.extend(numpy.random.choice((data.target==k).nonzero()[0], n))

    theta = numpy.ones(K) / K
    phi0 = numpy.zeros((V, K)) + beta
    for n in train:
        phi0[:, data.target[n]] += data.data[n, :].toarray().flatten()
    phi = phi0 / phi0.sum(axis=0)
    accuracy0 = performance(0, test, phi, theta)

    for i in xrange(20):
        # E-step
        z = data.data * numpy.log(phi) + numpy.log(theta) # M * K
        z -= z.max(axis=1)[:, None]
        z = numpy.exp(z)
        z /= z.sum(axis=1)[:, None]

        # M-step
        theta = z.sum(axis=0) + alpha
        theta /= theta.sum()
        phi = phi0 + data.data.T * z
        phi = phi / phi.sum(axis=0)

        accuracy = performance(i+1, test, phi, theta)

    return len(train), accuracy0, accuracy

def main():
    parser = optparse.OptionParser()

    parser.add_option("-K", dest="class_size", type="int", help="number of class")
    parser.add_option("-a", dest="alpha", type="float", help="parameter alpha", default=0.05)
    parser.add_option("-b", dest="beta", type="float", help="parameter beta", default=0.001)
    #parser.add_option("-n", dest="n", type="int", help="training size for each label", default=1)
    #parser.add_option("-t", dest="training", help="specify indexes of training", default=None)
    parser.add_option("--seed", dest="seed", type="int", help="random seed")
    (opt, args) = parser.parse_args()
    numpy.random.seed(opt.seed)

    data = sklearn.datasets.fetch_20newsgroups()
    test = sklearn.datasets.fetch_20newsgroups(subset='test')

    vec = CountVectorizer()
    data.data = vec.fit_transform(data.data).tocsr()
    test.data = vec.transform(test.data).tocsr() # use the same vocaburary of training data

    print "(data size, voca size) : (%d, %d)" % data.data.shape
    print "(test size, voca size) : (%d, %d)" % test.data.shape

    if opt.class_size:
        """
        index = data.target < opt.class_size
        a = data.data.toarray()[index, :]
        data.data = scipy.sparse.csr_matrix(a)
        data.target = data.target[index]
        print "(shrinked data size, voca size) : (%d, %d)" % data.data.shape
        """

        index = test.target < opt.class_size
        a = test.data.toarray()[index, :]
        test.data = scipy.sparse.csr_matrix(a)
        test.target = test.target[index]
        print "(shrinked test size, voca size) : (%d, %d)" % test.data.shape


    result = []
    for n in xrange(50):
        result.append(estimate(data, test, opt.alpha, opt.beta, n+1, 2))
    for x in result:
        print x

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = crf
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Conditional Random Field
# This code is available under the MIT License.
# (c)2010-2011 Nakatani Shuyo / Cybozu Labs Inc.

import numpy
from scipy import maxentropy

def logdotexp_vec_mat(loga, logM):
    return numpy.array([maxentropy.logsumexp(loga + x) for x in logM.T], copy=False)

def logdotexp_mat_vec(logM, logb):
    return numpy.array([maxentropy.logsumexp(x + logb) for x in logM], copy=False)

def flatten(x):
    a = []
    for y in x: a.extend(flatten(y) if isinstance(y, list) else [y])
    return a

class FeatureVector(object):
    def __init__(self, features, xlist, ylist=None):
        '''intermediates of features (sufficient statistics like)'''
        flist = features.features_edge
        glist = features.features
        self.K = len(features.labels)

        # expectation of features under empirical distribution (if ylist is specified)
        if ylist:
            self.Fss = numpy.zeros(features.size(), dtype=int)
            for y1, y2 in zip(["start"] + ylist, ylist + ["end"]):
                self.Fss[:len(flist)] += [f(y1, y2) for f in flist]
            for y1, x1 in zip(ylist, xlist):
                self.Fss[len(flist):] += [g(x1, y1) for g in glist]

        # index list of ON values of edge features
        self.Fon = [] # (n, #f, indexes)

        # for calculation of M_i
        self.Fmat = [] # (n, K, #f, K)-matrix
        self.Gmat = [] # (n, #g, K)-matrix
        for x in xlist:
            mt = numpy.zeros((len(glist), self.K), dtype=int)
            for j, g in enumerate(glist):
                mt[j] = [g(x, y) for y in features.labels]  # sparse
            self.Gmat.append(mt)
            #self._calc_fmlist(flist, x) # when fmlist depends on x_i (if necessary)

        # when fmlist doesn't depend on x_i
        self._calc_fmlist(features)


    def _calc_fmlist(self, features):
        flist = features.features_edge
        fmlist = []
        f_on = [[] for f in flist]
        for k1, y1 in enumerate(features.labels):
            mt = numpy.zeros((len(flist), self.K), dtype=int)
            for j, f in enumerate(flist):
                mt[j] = [f(y1, y2) for y2 in features.labels]  # sparse
                f_on[j].extend([k1 * self.K + k2 for k2, v in enumerate(mt[j]) if v == 1])
            fmlist.append(mt)
        self.Fmat.append(fmlist)
        self.Fon.append(f_on)

    def cost(self, theta):
        return numpy.dot(theta, self.Fss)

    def logMlist(self, theta_f, theta_g):
        '''for independent fmlists on x_i'''
        fv = numpy.zeros((self.K, self.K))
        for j, fm in enumerate(self.Fmat[0]):
            fv[j] = numpy.dot(theta_f, fm)
        return [fv + numpy.dot(theta_g, gm) for gm in self.Gmat] + [fv]

class Features(object):
    def __init__(self, labels):
        self.features = []
        self.features_edge = []
        self.labels = ["start","stop"] + flatten(labels)

    def start_label_index(self):
        return 0
    def stop_label_index(self):
        return 1
    def size(self):
        return len(self.features) + len(self.features_edge)
    def size_edge(self):
        return len(self.features_edge)
    def id2label(self, list):
        return [self.labels[id] for id in list]

    def add_feature(self, f):
        self.features.append(f)
    def add_feature_edge(self, f):
        self.features_edge.append(f)

class CRF(object):
    def __init__(self, features, regularity, sigma=1):
        self.features = features
        if regularity == 0:
            self.regularity = lambda w:0
            self.regularity_deriv = lambda w:0
        elif regularity == 1:
            self.regularity = lambda w:numpy.sum(numpy.abs(w)) / sigma
            self.regularity_deriv = lambda w:numpy.sign(w) / sigma
        else:
            v = sigma ** 2
            v2 = v * 2
            self.regularity = lambda w:numpy.sum(w ** 2) / v2
            self.regularity_deriv = lambda w:numpy.sum(w) / v

    def random_param(self):
        return numpy.random.randn(self.features.size())

    def logalphas(self, Mlist):
        logalpha = Mlist[0][self.features.start_label_index()] # alpha(1)
        logalphas = [logalpha]
        for logM in Mlist[1:]:
            logalpha = logdotexp_vec_mat(logalpha, logM)
            logalphas.append(logalpha)
        return logalphas

    def logbetas(self, Mlist):
        logbeta = Mlist[-1][:, self.features.stop_label_index()]
        logbetas = [logbeta]
        for logM in Mlist[-2::-1]:
            logbeta = logdotexp_mat_vec(logM, logbeta)
            logbetas.append(logbeta)
        return logbetas[::-1]

    def likelihood(self, fvs, theta):
        '''conditional log likelihood log p(Y|X)'''
        n_fe = self.features.size_edge() # number of features on edge
        t1, t2 = theta[:n_fe], theta[n_fe:]
        stop_index = self.features.stop_label_index()

        likelihood = 0
        for fv in fvs:
            logMlist = fv.logMlist(t1, t2)
            logZ = self.logalphas(logMlist)[-1][stop_index]
            likelihood += fv.cost(theta) - logZ
        return likelihood - self.regularity(theta)

    def gradient_likelihood(self, fvs, theta):
        n_fe = self.features.size_edge() # number of features on edge
        t1, t2 = theta[:n_fe], theta[n_fe:]
        stop_index = self.features.stop_label_index()
        start_index = self.features.start_label_index()

        grad = numpy.zeros(self.features.size())
        for fv in fvs:
            logMlist = fv.logMlist(t1, t2)
            logalphas = self.logalphas(logMlist)
            logbetas = self.logbetas(logMlist)
            logZ = logalphas[-1][stop_index]

            grad += numpy.array(fv.Fss, dtype=float) # empirical expectation

            expect = numpy.zeros_like(logMlist[0])
            for i in range(len(logMlist)):
                if i == 0:
                    expect[start_index] += numpy.exp(logalphas[i] + logbetas[i+1] - logZ)
                elif i < len(logbetas) - 1:
                    a = logalphas[i-1][:, numpy.newaxis]
                    expect += numpy.exp(logMlist[i] + a + logbetas[i+1] - logZ)
                else:
                    expect[:, stop_index] += numpy.exp(logalphas[i-1] + logbetas[i] - logZ)
            for k, indexes in enumerate(fv.Fon[0]):
                grad[k] -= numpy.sum(expect.take(indexes))

            for i, gm in enumerate(fv.Gmat):
                p_yi = numpy.exp(logalphas[i] + logbetas[i+1] - logZ)
                grad[n_fe:] -= numpy.sum(gm * numpy.exp(logalphas[i] + logbetas[i+1] - logZ), axis=1)

        return grad - self.regularity_deriv(theta)

    def inference(self, fvs, theta):
        from scipy import optimize
        likelihood = lambda x:-self.likelihood(fvs, x)
        likelihood_deriv = lambda x:-self.gradient_likelihood(fvs, x)
        return optimize.fmin_bfgs(likelihood, theta, fprime=likelihood_deriv)

    def tagging(self, fv, theta):
        n_fe = self.features.size_edge() # number of features on edge
        logMlist = fv.logMlist(theta[:n_fe], theta[n_fe:])

        logalphas = self.logalphas(logMlist)
        logZ = logalphas[-1][self.features.stop_label_index()]

        delta = logMlist[0][self.features.start_label_index()]
        argmax_y = []
        for logM in logMlist[1:]:
            h = logM + delta[:, numpy.newaxis]
            argmax_y.append(h.argmax(0))
            delta = h.max(0)
        Y = [delta.argmax()]
        for a in reversed(argmax_y):
            Y.append(a[Y[-1]])

        return Y[0] - logZ, Y[::-1]

    def tagging_verify(self, fv, theta):
        '''verification of tagging'''
        n_fe = self.features.size_edge() # number of features on edge
        logMlist = fv.logMlist(theta[:n_fe], theta[n_fe:])
        N = len(logMlist) - 1
        K = logMlist[0][0].size

        ylist = [0] * N
        max_p = -1e9
        argmax_p = None
        while True:
            logp = logMlist[0][self.features.start_label_index(), ylist[0]]
            for i in range(len(ylist)-1):
                logp += logMlist[i+1][ylist[i], ylist[i+1]]
            logp += logMlist[N][ylist[N-1], self.features.stop_label_index()]
            print ylist, logp
            if max_p < logp:
                max_p = logp
                argmax_p = ylist[:]

            for k in range(N-1,-1,-1):
                if ylist[k] < K-1:
                    ylist[k] += 1
                    break
                ylist[k] = 0
            else:
                break
        return max_p, argmax_p



def main():
    def load_data(data):
        texts = []
        labels = []
        text = []
        data = "\n" + data + "\n"
        for line in data.split("\n"):
            line = line.strip()
            if len(line) == 0:
                if len(text)>0:
                    texts.append(text)
                    labels.append(label)
                text = []
                label = []
            else:
                token, info, chunk = line.split()
                text.append((token, info))
                label.append(chunk)
        return (texts, labels)

    texts, labels = load_data("""
    This DT B-NP
    temblor-prone JJ I-NP
    city NN I-NP
    dispatched VBD B-VP
    inspectors NNS B-NP
    , , O
    firefighters NNS B-NP
    and CC O
    other JJ B-NP
    earthquake-trained JJ I-NP
    personnel NNS I-NP
    to TO B-VP
    aid VB I-VP
    San NNP B-NP
    Francisco NNP I-NP
    . . O

    He PRP B-NP
    reckons VBZ B-VP
    the DT B-NP
    current JJ I-NP
    account NN I-NP
    deficit NN I-NP
    will MD B-VP
    narrow VB I-VP
    to TO B-PP
    only RB B-NP
    # # I-NP
    1.8 CD I-NP
    billion CD I-NP
    in IN B-PP
    September NNP B-NP
    . . O

    Meanwhile RB B-ADVP
    , , O
    overall JJ B-NP
    evidence NN I-NP
    on IN B-PP
    the DT B-NP
    economy NN I-NP
    remains VBZ B-VP
    fairly RB B-ADJP
    clouded VBN I-ADJP
    . . O

    But CC O
    consumer NN B-NP
    expenditure NN I-NP
    data NNS I-NP
    released VBD B-VP
    Friday NNP B-NP
    do VBP B-VP
    n't RB I-VP
    suggest VB I-VP
    that IN B-SBAR
    the DT B-NP
    U.K. NNP I-NP
    economy NN I-NP
    is VBZ B-VP
    slowing VBG I-VP
    that DT B-ADVP
    quickly RB I-ADVP
    . . O
    """)

    test_texts, test_labels = load_data("""
    Rockwell NNP B-NP
    said VBD B-VP
    the DT B-NP
    agreement NN I-NP
    calls VBZ B-VP
    for IN B-SBAR
    it PRP B-NP
    to TO B-VP
    supply VB I-VP
    200 CD B-NP
    additional JJ I-NP
    so-called JJ I-NP
    shipsets NNS I-NP
    for IN B-PP
    the DT B-NP
    planes NNS I-NP
    . . O
    """)

    features = Features(labels)
    tokens = dict([(i[0],1) for x in texts for i in x]).keys()
    infos = dict([(i[1],1) for x in texts for i in x]).keys()

    for label in features.labels:
        for token in tokens:
            features.add_feature( lambda x, y, l=label, t=token: 1 if y==l and x[0]==t else 0 )
        for info in infos:
            features.add_feature( lambda x, y, l=label, i=info: 1 if y==l and x[1]==i else 0 )
    features.add_feature_edge( lambda y_, y: 0 )

    fvs = [FeatureVector(features, x, y) for x, y in zip(texts, labels)]
    fv = fvs[0]
    text_fv = FeatureVector(features, test_texts[0]) # text sequence without labels


    crf = CRF(features, 2)
    theta = crf.random_param()

    print "features:", features.size()
    print "labels:", len(features.labels)

    #print "theta:", theta
    print "log likelihood:", crf.likelihood(fvs, theta)
    prob, ys = crf.tagging(text_fv, theta)
    print "tagging:", prob, features.id2label(ys)

    theta = crf.inference(fvs, theta)

    #print "theta:", theta
    print "log likelihood:", crf.likelihood(fvs, theta)
    prob, ys = crf.tagging(text_fv, theta)
    print "tagging:", prob, zip(test_texts[0], test_labels[0], features.id2label(ys))

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = hmm
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Hidden Markov Model

import sys, os, re, pickle
from optparse import OptionParser
#import scipy.stats
import numpy
from numpy.random import dirichlet, randn


def load_corpus(filename):
    corpus = []
    f = open(filename, 'r')
    for line in f:
        doc = re.findall(r'\w+(?:-\w+)?(?:\'\w+)?',line)
        if len(doc)>0: corpus.append([x.lower() for x in doc])
    f.close()
    return corpus

class HMM(object):
    def set_corpus(self, corpus, end_of_sentense=False):
        self.x_ji = [] # vocabulary for each document and term
        self.vocas = []
        self.vocas_id = dict()
        if end_of_sentense: self.vocas.append("(END)") # END OF SENTENCE

        for doc in corpus:
            x_i = []
            for term in doc:
                if term not in self.vocas_id:
                    voca_id = len(self.vocas)
                    self.vocas_id[term] = voca_id
                    self.vocas.append(term)
                else:
                    voca_id = self.vocas_id[term]
                x_i.append(voca_id)
            if end_of_sentense: x_i.append(0) # END OF SENTENCE
            self.x_ji.append(x_i)
        self.V = len(self.vocas)

    def init_inference(self, K, a, triangle=False):
        self.K = K

        # transition
        self.pi = dirichlet([a] * self.K) # numpy.ones(self.K) / self.K
        if triangle:
            self.A = numpy.zeros((self.K, self.K))
            for i in range(self.K):
                self.A[i, i:self.K] = dirichlet([a] * (self.K - i))
        else:
            self.A = dirichlet([a] * self.K, self.K)

        # emission
        self.B = numpy.ones((self.V, self.K)) / self.V  # numpy.tile(1.0 / self.V, (self.V, self.K))

    def save(self, file):
        numpy.savez(file + ".npz",
            x_ji = pickle.dumps(self.x_ji),
            vocas = self.vocas,
            vocas_id = pickle.dumps(self.vocas_id),
            K = self.K,
            pi = self.pi,
            A = self.A,
            B = self.B
        )

    def load(self, file):
        if not os.path.exists(file): file += ".npz"
        x = numpy.load(file)
        self.x_ji = pickle.loads(x['x_ji'])
        self.vocas = x['vocas']
        self.vocas_id = pickle.loads(x['vocas_id'])
        self.K = x['K']
        self.pi = x['pi']
        self.A = x['A']
        self.B = x['B']
        self.V = len(self.vocas)
        print self.vocas_id["html"]

    def id2words(self, x):
        return [self.vocas[v] for v in x]

    def words2id(self, x):
        return [self.vocas_id[v] for v in x]

    def dump(self):
        print "V:", self.V
        print "pi:", self.pi
        print "A:"
        for i, x in enumerate(self.A):
            print i, ":", ', '.join(["%.4f" % y for y in x])
        print "B:"
        for i, x in enumerate(self.B):
            print i, ":", ', '.join(["%.4f" % y for y in x])

    def Estep(self, x):
        N = len(x)

        alpha = numpy.zeros((N, self.K))
        c = numpy.ones(N)   # c[0] = 1
        a = self.pi * self.B[x[0]]
        alpha[0] = a / a.sum()
        for n in xrange(1, N):
            a = self.B[x[n]] * numpy.dot(alpha[n-1], self.A)
            c[n] = z = a.sum()
            alpha[n] = a / z

        beta = numpy.zeros((N, self.K))
        beta[N-1] = 1
        for n in xrange(N-1, 0, -1):
            beta[n-1] = numpy.dot(self.A, beta[n] * self.B[x[n]]) / c[n]

        likelihood = numpy.log(c).sum()
        gamma = alpha * beta

        xi_sum = numpy.outer(alpha[0], self.B[x[1]] * beta[1]) / c[1]
        for n in range(2, N):
            xi_sum += numpy.outer(alpha[n-1], self.B[x[n]] * beta[n]) / c[n]
        xi_sum *= self.A

        return (gamma, xi_sum, likelihood)

    def inference(self):
        """
        @brief one step of EM algorithm
        @return log likelihood
        """
        pi_new = numpy.zeros(self.K)
        A_new = numpy.zeros((self.K, self.K))
        B_new = numpy.zeros((self.V, self.K))
        log_likelihood = 0
        for x in self.x_ji:
            gamma, xi_sum, likelihood = self.Estep(x)
            log_likelihood += likelihood

            # M-step
            pi_new += gamma[0]
            A_new += xi_sum
            for v, g_n in zip(x, gamma):
                B_new[v] += g_n

        self.pi = pi_new / pi_new.sum()
        self.A = A_new / (A_new.sum(1)[:, numpy.newaxis])
        self.B = B_new / B_new.sum(0)

        return log_likelihood

    def sampling(self):
        z = numpy.random.multinomial(1, self.pi).argmax()
        x_n = []
        while 1:
            v = numpy.random.multinomial(1, self.B[:,z]).argmax()
            if v==0: break
            x_n.append(self.vocas[v])
            z = numpy.random.multinomial(1, self.A[z]).argmax()
        return x_n

    def Viterbi(self, x):
        N = len(x)
        w = numpy.log(self.pi) + numpy.log(self.B[x[0]])
        argmax_z_n = []
        for n in range(1, N):
            mes = numpy.log(self.A) + w[:, numpy.newaxis] # max_{z_n}( ln p(z_{n+1}|z_n) + w(z_n) )
            argmax_z_n.append(mes.argmax(0))
            w = numpy.log(self.B[x[n]]) + mes.max(0)
        z = [0] * N
        z[N-1] = w.argmax()
        for n in range(N-1, 0, -1):
            z[n-1] = argmax_z_n[n-1][z[n]]
        return z

def main():
    parser = OptionParser()
    parser.add_option("-f", dest="filename", help="corpus filename")
    parser.add_option("-k", dest="K", type="int", help="number of latent states", default=6)
    parser.add_option("-a", dest="a", type="float", help="Dirichlet parameter", default=1.0)
    parser.add_option("-i", dest="I", type="int", help="iteration count", default=10)
    parser.add_option("-t", dest="triangle", action="store_true", help="triangle")
    (options, args) = parser.parse_args()
    if not options.filename: parser.error("need corpus filename(-f)")

    corpus = load_corpus(options.filename)

    hmm = HMM()
    hmm.set_corpus(corpus, end_of_sentense=True)
    hmm.init_inference(options.K, options.a, options.triangle)
    pre_L = -1e10
    for i in range(options.I):
        log_likelihood = hmm.inference()
        print i, ":", log_likelihood
        if pre_L > log_likelihood: break
        pre_L = log_likelihood
    hmm.dump()

    for i in range(10):
        print " ".join(hmm.sampling())

    for x in corpus:
        print zip(x, hmm.Viterbi(hmm.words2id(x)))


if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = pg
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Project Gutenberg Content Extractor with CRF

import re, glob
import pickle
from optparse import OptionParser
from crf import CRF, Features, FeatureVector


def load_dir(dir):
    '''load training/test data directory'''

    labels = []
    texts = []
    for filename in glob.glob(dir + '/*'):
        text, label = load_file(filename)
        texts.append(text)
        labels.append(label)
    return (texts, labels)

def load_file(filename):
    '''load one file of Project Gutenberg'''

    text = []
    label = []
    current_label = "H"
    f = open(filename, 'r')
    paragraph = ""
    for line in f:
        line = line.rstrip()
        if len(line)==0:
            if len(paragraph)==0:
                text[-1] += "\n"
                continue
            text.append(paragraph)
            label.append(current_label)
            paragraph = ""
            continue
        mt = re.match(r'##([A-Z]{1,3})$', line) # right tag (for training data)
        if mt:
            current_label = mt.group(1)
            continue
        paragraph += line + "\n"
    f.close()
    print filename, len(text), "paras."
    return ([Paragraph(p) for p in text], label)

def max_length(text, pattern, flags=re.M):
    list = [len(x) for x in re.findall(pattern, text, flags)]
    if len(list)==0: return 0
    return max(list)

class Paragraph(object):
    def __init__(self, text):
        self.has_word = dict()
        self.text = text
        self.all_upper = (text.upper() == text)
        self.linehead = {' ': max_length(text, '^ +'), '*': max_length(text, r'^\*+')}
        self.linetail = {'*': max_length(text, '\*+$')}
        self.n_lines = len(text.split("\n"))
    def has(self, word):
        if word in self.has_word: return self.has_word[word]
        self.has_word[word] = True if re.search(word, self.text, re.I) else False
        return self.has_word[word]


def pg_features(LABELS):
    '''CRF features for Project Gutenberg Content Extractor'''

    features = Features(LABELS)
    for label in LABELS:
        # keywords
        for word in "project/gutenberg/e-?text/ebook/copyright/chapter/scanner/David Reed/encoding/contents/file/zip/web/http/email/newsletter/public domain/donation/archive/ascii/produced/end of (the)? project gutenberg/PREFACE/INTRODUCTION/Language:/Release Date:/Character set/refund/LIMITED RIGHT".split('/'):
            features.add_feature( lambda x, y, w=word, l=label: 1 if x.has(w) and y == l else 0 )

        # type case
        features.add_feature( lambda x, y, l=label: 1 if x.all_upper and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'[A-Z]{3}') and y == l else 0 )

        # numeric
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'[0-9]') and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'[0-9]{2}') and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'[0-9]{3}') and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'[0-9]{4}') and y == l else 0 )

        # line head
        features.add_feature( lambda x, y, l=label: 1 if x.linehead[' ']>=2 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.linehead[' ']>=4 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.linehead['*']>=1 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.linehead['*']>=2 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.linehead['*']>=3 and y == l else 0 )

        # line tail
        features.add_feature( lambda x, y, l=label: 1 if x.linetail['*']>=1 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.linetail['*']>=2 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.linetail['*']>=3 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'\n\n$') and y == l else 0 )

        # symbols
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'@') and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'#') and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'\?') and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.has(r'\[') and y == l else 0 )

        # line number
        features.add_feature( lambda x, y, l=label: 1 if x.n_lines==1 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_lines==2 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_lines==3 and y == l else 0 )
        features.add_feature( lambda x, y, l=label: 1 if x.n_lines>3 and y == l else 0 )

    # labels
    for label1 in features.labels:
        features.add_feature( lambda x, y, l=label1: 1 if y == l else 0 )
        features.add_feature_edge( lambda y_, y, l=label1: 1 if y_ == l else 0 )
        for label2 in features.labels:
            features.add_feature_edge( lambda y_, y, l1=label1, l2=label2: 1 if y_ == l1 and y == l2 else 0 )

    return features

def pg_tagging(fv, text, label, crf, features, theta):
    '''tagging & output'''

    prob, ys = crf.tagging(fv, theta)
    if all(x=="H" for x in label):
        print "log_prob:", prob

        cur_text = [] # texts with current label
        cur_label = None
        for x in zip(features.id2label(ys), text):
            if cur_label != x[0]:
                pgt_output(cur_label, cur_text)
                cur_text = []
                cur_label = x[0]
            cur_text.append(x[1].text[0:64].replace("\n", " "))
        pgt_output(cur_label, cur_text)
    else:
        compare = zip(label, features.id2label(ys), text)
        print "log_prob:", prob, " rate:", len(filter(lambda x:x[0]==x[1], compare)), "/", len(compare)
        for x in compare:
            if x[0] != x[1]:
                print "----------", x[0], "=>", x[1]
                print x[2].text[0:400]

def pgt_output(label, text):
    if len(text)==0: return
    if len(text)<=7:
        for t in text: print label, t
    else:
        for t in text[:3]: print label, t
        print ": (", len(text)-6, "paragraphs)"
        for t in text[-3:]: print label, t


def main():
    parser = OptionParser()
    parser.add_option("-d", dest="training_dir", help="training data directory")
    parser.add_option("-t", dest="test_dir", help="test data directory")
    parser.add_option("-f", dest="test_file", help="test data file")
    parser.add_option("-m", dest="model", help="model file")
    parser.add_option("-l", dest="regularity", type="int", help="regularity. 0=none, 1=L1, 2=L2 [2]", default=2)
    (options, args) = parser.parse_args()
    if not options.training_dir and not options.model:
        parser.error("need training data directory(-d) or model file(-m)")

    features = pg_features(["H", "B", "F"])
    crf = CRF(features, options.regularity)
    print "features:", features.size()
    print "labels:", len(features.labels)

    if options.training_dir:
        texts, labels = load_dir(options.training_dir)
        fvs = [FeatureVector(features, x, y) for x, y in zip(texts, labels)]

        # initial parameter (pick up max in 10 random parameters)
        theta = sorted([crf.random_param() for i in range(10)], key=lambda t:crf.likelihood(fvs, t))[-1]

        # inference
        print "log likelihood (before inference):", crf.likelihood(fvs, theta)
        theta = crf.inference(fvs, theta)
        if options.model:
            f = open(options.model, 'w')
            f.write(pickle.dumps(theta))
            f.close()
    else:
        f = open(options.model, 'r')
        theta = pickle.loads(f.read())
        f.close()
        if features.size() != len(theta):
            raise ValueError, "model's length not equal feature's length."

    if options.test_dir:
        test_files = glob.glob(options.test_dir + '/*')
    elif options.test_file:
        test_files = [options.test_file]
    else:
        test_files = []

    i = 0
    for filename in test_files:
        print "========== test = ", i
        text, label = load_file(filename)
        pg_tagging(FeatureVector(features, text), text, label, crf, features, theta)
        i += 1

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = testcrf
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Project Gutenberg Content Extractor with CRF

import numpy
import time
from optparse import OptionParser
from crf import CRF, Features, FeatureVector


def main():
    def load_data(data):
        texts = []
        labels = []
        text = []
        data = "\n" + data + "\n"
        for line in data.split("\n"):
            line = line.strip()
            if len(line) == 0:
                if len(text)>0:
                    texts.append(text)
                    labels.append(label)
                text = []
                label = []
            else:
                token, info, chunk = line.split()
                text.append((token, info))
                label.append(chunk)
        return (texts, labels)

    texts, labels = load_data("""
    This DT B-NP
    temblor-prone JJ I-NP
    city NN I-NP
    dispatched VBD B-VP
    inspectors NNS B-NP
    , , O

    firefighters NNS B-NP
    and CC O
    other JJ B-NP
    earthquake-trained JJ I-NP
    personnel NNS I-NP
    to TO B-VP
    aid VB I-VP
    San NNP B-NP
    Francisco NNP I-NP
    . . O
    """)

    print texts, labels

    test_texts, test_labels = load_data("""
    Rockwell NNP B-NP
    said VBD B-VP
    the DT B-NP
    agreement NN I-NP
    calls VBZ B-VP
    for IN B-SBAR
    it PRP B-NP
    to TO B-VP
    supply VB I-VP
    200 CD B-NP
    additional JJ I-NP
    so-called JJ I-NP
    shipsets NNS I-NP
    for IN B-PP
    the DT B-NP
    planes NNS I-NP
    . . O
    """)

    features = Features(labels)
    tokens = dict([(i[0],1) for x in texts for i in x]).keys()
    infos = dict([(i[1],1) for x in texts for i in x]).keys()

    for label in features.labels:
        for token in tokens:
            features.add_feature( lambda x, y, l=label, t=token: 1 if y==l and x[0]==t else 0 )
        for info in infos:
            features.add_feature( lambda x, y, l=label, i=info: 1 if y==l and x[1]==i else 0 )
    features.add_feature_edge( lambda y_, y: 0 )

    fvs = [FeatureVector(features, x, y) for x, y in zip(texts, labels)]
    fv = fvs[0]
    text_fv = FeatureVector(features, test_texts[0]) # text sequence without labels


    crf = CRF(features, 0)
    theta0 = crf.random_param()
    print "initial log likelihood:", crf.likelihood(fvs, theta0)


    print ">> Steepest Descent"
    theta = theta0.copy()
    eta = 0.5
    t = time.time()
    for i in range(20):
        theta += eta * crf.gradient_likelihood(fvs, theta)
        print i, "log likelihood:", crf.likelihood(fvs, theta)
        eta *= 0.95
    print "time = %.3f, relevant features = %d / %d" % (time.time() - t, (numpy.abs(theta) > 0.00001).sum(), theta.size)

    print ">> SGD"
    theta = theta0.copy()
    eta = 0.5
    t = time.time()
    for i in range(20):
        for fv in fvs:
            theta += eta * crf.gradient_likelihood([fv], theta)
        print i, "log likelihood:", crf.likelihood(fvs, theta)
        eta *= 0.95
    print "time = %.3f, relevant features = %d / %d" % (time.time() - t, (numpy.abs(theta) > 0.00001).sum(), theta.size)

    print ">> SGD + FOBOS L1"
    theta = theta0.copy()
    eta = 0.5
    lmd = 0.01
    t = time.time()
    for i in range(20):
        lmd_eta = lmd * eta
        for fv in fvs:
            theta += eta * crf.gradient_likelihood([fv], theta)
            theta = (theta > lmd_eta) * (theta - lmd_eta) + (theta < -lmd_eta) * (theta + lmd_eta)
        print i, "log likelihood:", crf.likelihood(fvs, theta)
        eta *= 0.95
    print "time = %.3f, relevant features = %d / %d" % (time.time() - t, (numpy.abs(theta) > 0.00001).sum(), theta.size)

    print ">> Steepest Descent + FOBOS L1"
    theta = theta0.copy()
    eta = 0.2
    lmd = 0.5
    t = time.time()
    for i in range(20):
        theta += eta * crf.gradient_likelihood(fvs, theta)
        lmd_eta = lmd * eta
        theta = (theta > lmd_eta) * (theta - lmd_eta) + (theta < -lmd_eta) * (theta + lmd_eta)
        print i, "log likelihood:", crf.likelihood(fvs, theta)
        eta *= 0.9
    print "time = %.3f, relevant features = %d / %d" % (time.time() - t, (numpy.abs(theta) > 0.00001).sum(), theta.size)
    #print theta

    print ">> BFGS"
    t = time.time()
    theta = crf.inference(fvs, theta0)
    print "log likelihood:", crf.likelihood(fvs, theta)
    print "time = %.3f, relevant features = %d / %d" % (time.time() - t, (numpy.abs(theta) > 0.00001).sum(), theta.size)


if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = da
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import numpy

# Double Array for static ordered data
# This code is available under the MIT License.
# (c)2011 Nakatani Shuyo / Cybozu Labs Inc.

class DoubleArray(object):
    def __init__(self, verbose=False):
        self.verbose = verbose

    def validate_list(self, list):
        pre = ""
        for i, line in enumerate(list):
            if pre >= line:
                raise Exception, "list has not ascent order at %d" % (i+1)
            pre = line

    def initialize(self, list):
        self.validate_list(list)

        self.N = 1
        self.base  = [-1]
        self.check = [-1]
        self.value = [-1]

        max_index = 0
        queue = collections.deque([(0, 0, len(list), 0)])
        while len(queue) > 0:
            index, left, right, depth = queue.popleft()
            if depth >= len(list[left]):
                self.value[index] = left
                left += 1
                if left >= right: continue

            # get branches of current node
            stack = collections.deque([(right, -1)])
            cur, c1 = (left, ord(list[left][depth]))
            result = []
            while len(stack) >= 1:
                while c1 == stack[-1][1]:
                    cur, c1 = stack.pop()
                mid = (cur + stack[-1][0]) / 2
                if cur == mid:
                    result.append((cur + 1, c1))
                    cur, c1 = stack.pop()
                else:
                    c2 = ord(list[mid][depth])
                    if c1 != c2:
                        stack.append((mid, c2))
                    else:
                        cur = mid

            # search empty index for current node
            v0 = result[0][1]
            j = - self.check[0] - v0
            while any(j + v < self.N and self.check[j + v] >= 0 for right, v in result):
                j = - self.check[j + v0] - v0
            tail_index = j + result[-1][1]
            if max_index < tail_index:
                max_index = tail_index
                self.extend_array(tail_index + 2)

            # insert current node into DA
            self.base[index] = j
            depth += 1
            for right, v in result:
                child = j + v
                self.check[self.base[child]] = self.check[child]
                self.base[-self.check[child]] = self.base[child]
                self.check[child] = index
                queue.append((child, left, right, depth))
                left = right

        self.shrink_array(max_index)

    def extend_array(self, max_cand):
        if self.N < max_cand:
            new_N = 2 ** int(numpy.ceil(numpy.log2(max_cand)))
            self.log("extend DA : %d => (%d) => %d", (self.N, max_cand, new_N))
            self.base.extend(    n - 1 for n in xrange(self.N, new_N))
            self.check.extend( - n - 1 for n in xrange(self.N, new_N))
            self.value.extend(     - 1 for n in xrange(self.N, new_N))
            self.N = new_N

    def shrink_array(self, max_index):
        self.log("shrink DA : %d => %d", (self.N, max_index + 1))
        self.N = max_index + 1
        self.check = numpy.array(self.check[:self.N])
        self.base = numpy.array(self.base[:self.N])
        self.value = numpy.array(self.value[:self.N])

        not_used = self.check < 0
        self.check[not_used] = -1
        not_used[0] = False
        self.base[not_used] = self.N

    def log(self, format, param):
        if self.verbose:
            import time
            print "-- %s, %s" % (time.strftime("%Y/%m/%d %H:%M:%S"), format % param)

    def save(self, filename):
        numpy.savez(filename, base=self.base, check=self.check, value=self.value)

    def load(self, filename):
        loaded = numpy.load(filename)
        self.base = loaded['base']
        self.check = loaded['check']
        self.value = loaded['value']
        self.N = self.base.size

    def add_element(self, s, v):
        pass

    def get_subtree(self, s):
        cur = 0
        for c in iter(s):
            v = ord(c)
            next = self.base[cur] + v
            if next >= self.N or self.check[next] != cur:
                return None
            cur = next
        return cur

    def get_child(self, c, subtree):
        v = ord(c)
        next = self.base[subtree] + v
        if next >= self.N or self.check[next] != subtree:
            return None
        return next

    def get(self, s):
        cur = self.get_subtree(s)
        if cur >= 0:
            value = self.value[cur]
            if value >= 0: return value
        return None

    def get_value(self, subtree):
        return self.value[subtree]

    def extract_features(self, st):
        events = dict()
        pointers = []
        for c in iter(st):
            pointers.append(0)
            new_pointers = []
            for pointer in pointers:
                p = self.get_child(c, pointer)
                if p is not None:
                    new_pointers.append(p)
                    id = self.value[p]
                    if id >= 0:
                        events[id] = events.get(id, 0) + 1
            pointers = new_pointers
        return events




########NEW FILE########
__FILENAME__ = test_da
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import da

class TestDoubleArray(unittest.TestCase):
    def test1(self):
        trie = da.DoubleArray(verbose=False)
        trie.initialize(["cat"])
        self.assertEqual(trie.N, 4)
        self.assert_(trie.get("ca") is None)
        self.assert_(trie.get("xxx") is None)
        self.assertEqual(trie.get("cat"), 0)

    def test2(self):
        trie = da.DoubleArray()
        trie.initialize(["cat", "dog"])
        self.assertEqual(trie.N, 7)
        self.assert_(trie.get("ca") is None)
        self.assert_(trie.get("xxx") is None)
        self.assertEqual(trie.get("cat"), 0)
        self.assertEqual(trie.get("dog"), 1)

    def test3(self):
        trie = da.DoubleArray(verbose=False)
        trie.initialize(["ca", "cat", "deer", "dog", "fox", "rat"])
        print trie.base
        print trie.check
        print trie.value
        self.assertEqual(trie.N, 17)
        self.assert_(trie.get("c") is None)
        self.assertEqual(trie.get("ca"), 0)
        self.assertEqual(trie.get("cat"), 1)
        self.assertEqual(trie.get("deer"), 2)
        self.assertEqual(trie.get("dog"), 3)
        self.assert_(trie.get("xxx") is None)

    def test4(self):
        trie = da.DoubleArray()
        self.assertRaises(Exception, trie.initialize, ["cat", "ant"])

unittest.main()


########NEW FILE########
__FILENAME__ = trie
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Naive Trie
# This code is available under the MIT License.
# (c)2011 Nakatani Shuyo / Cybozu Labs Inc.

class Trie(object):
    def initialize(self):
        self.root = dict()
    def add_element(self, s, v):
        x = self.root
        for c in s:
            if c not in x: x[c] = dict()
            x = x[c]
        x[""] = v
    def get_subtree(self, s):
        x = self.root
        for c in iter(st):
            if c not in x: return None
            x = x[c]
        return x
    def get_child(self, c, subtree):
        if c not in x: return None
        return subtree[c]
    def get(self, s):
        return self.get_value(self.get_subtree(s))
    def get_value(self, subtree):
        return subtree[""]


########NEW FILE########
