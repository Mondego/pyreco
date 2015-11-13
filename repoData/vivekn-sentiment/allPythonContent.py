__FILENAME__ = info
from __future__ import division
from math import log, exp
from operator import mul
from collections import Counter
import os
import pylab
import cPickle


class MyDict(dict):
    def __getitem__(self, key):
        if key in self:
            return self.get(key)
        return 0

pos = MyDict()
neg = MyDict()
features = set()
totals = [0, 0]
delchars = ''.join(c for c in map(chr, range(128)) if not c.isalnum())

CDATA_FILE = "countdata.pickle"
FDATA_FILE = "reduceddata.pickle"


def negate_sequence(text):
    """
    Detects negations and transforms negated words into "not_" form.
    """
    negation = False
    delims = "?.,!:;"
    result = []
    words = text.split()
    prev = None
    pprev = None
    for word in words:
        # stripped = word.strip(delchars)
        stripped = word.strip(delims).lower()
        negated = "not_" + stripped if negation else stripped
        result.append(negated)
        if prev:
            bigram = prev + " " + negated
            result.append(bigram)
            if pprev:
                trigram = pprev + " " + bigram
                result.append(trigram)
            pprev = prev
        prev = negated

        if any(neg in word for neg in ["not", "n't", "no"]):
            negation = not negation

        if any(c in word for c in delims):
            negation = False

    return result


def train():
    global pos, neg, totals
    retrain = False
    
    # Load counts if they already exist.
    if not retrain and os.path.isfile(CDATA_FILE):
        pos, neg, totals = cPickle.load(open(CDATA_FILE))
        return

    limit = 12500
    for file in os.listdir("./aclImdb/train/pos")[:limit]:
        for word in set(negate_sequence(open("./aclImdb/train/pos/" + file).read())):
            pos[word] += 1
            neg['not_' + word] += 1
    for file in os.listdir("./aclImdb/train/neg")[:limit]:
        for word in set(negate_sequence(open("./aclImdb/train/neg/" + file).read())):
            neg[word] += 1
            pos['not_' + word] += 1
    
    prune_features()

    totals[0] = sum(pos.values())
    totals[1] = sum(neg.values())
    
    countdata = (pos, neg, totals)
    cPickle.dump(countdata, open(CDATA_FILE, 'w'))

def classify(text):
    words = set(word for word in negate_sequence(text) if word in features)
    if (len(words) == 0): return True
    # Probability that word occurs in pos documents
    pos_prob = sum(log((pos[word] + 1) / (2 * totals[0])) for word in words)
    neg_prob = sum(log((neg[word] + 1) / (2 * totals[1])) for word in words)
    return pos_prob > neg_prob

def classify2(text):
    """
    For classification from pretrained data
    """
    words = set(word for word in negate_sequence(text) if word in pos or word in neg)
    if (len(words) == 0): return True
    # Probability that word occurs in pos documents
    pos_prob = sum(log((pos[word] + 1) / (2 * totals[0])) for word in words)
    neg_prob = sum(log((neg[word] + 1) / (2 * totals[1])) for word in words)
    return pos_prob > neg_prob

def classify_demo(text):
    words = set(word for word in negate_sequence(text) if word in pos or word in neg)
    if (len(words) == 0): 
        print "No features to compare on"
        return True

    pprob, nprob = 0, 0
    for word in words:
        pp = log((pos[word] + 1) / (2 * totals[0]))
        np = log((neg[word] + 1) / (2 * totals[1]))
        print "%15s %.9f %.9f" % (word, exp(pp), exp(np))
        pprob += pp
        nprob += np

    print ("Positive" if pprob > nprob else "Negative"), "log-diff = %.9f" % abs(pprob - nprob)

def MI(word):
    """
    Compute the weighted mutual information of a term.
    """
    T = totals[0] + totals[1]
    W = pos[word] + neg[word]
    I = 0
    if W==0:
        return 0
    if neg[word] > 0:
        # doesn't occur in -ve
        I += (totals[1] - neg[word]) / T * log ((totals[1] - neg[word]) * T / (T - W) / totals[1])
        # occurs in -ve
        I += neg[word] / T * log (neg[word] * T / W / totals[1])
    if pos[word] > 0:
        # doesn't occur in +ve
        I += (totals[0] - pos[word]) / T * log ((totals[0] - pos[word]) * T / (T - W) / totals[0])
        # occurs in +ve
        I += pos[word] / T * log (pos[word] * T / W / totals[0])
    return I

def get_relevant_features():
    pos_dump = MyDict({k: pos[k] for k in pos if k in features})
    neg_dump = MyDict({k: neg[k] for k in neg if k in features})
    totals_dump = [sum(pos_dump.values()), sum(neg_dump.values())]
    return (pos_dump, neg_dump, totals_dump)

def prune_features():
    """
    Remove features that appear only once.
    """
    global pos, neg
    for k in pos.keys():
        if pos[k] <= 1 and neg[k] <= 1:
            del pos[k]

    for k in neg.keys():
        if neg[k] <= 1 and pos[k] <= 1:
            del neg[k]

def feature_selection_trials():
    """
    Select top k features. Vary k and plot data
    """
    global pos, neg, totals, features
    retrain = True

    if not retrain and os.path.isfile(FDATA_FILE):
        pos, neg, totals = cPickle.load(open(FDATA_FILE))
        return

    words = list(set(pos.keys() + neg.keys()))
    print "Total no of features:", len(words)
    words.sort(key=lambda w: -MI(w))
    num_features, accuracy = [], []
    bestk = 0
    limit = 500
    path = "./aclImdb/test/"
    step = 500
    start = 20000
    best_accuracy = 0.0
    for w in words[:start]:
        features.add(w)
    for k in xrange(start, 40000, step):
        for w in words[k:k+step]:
            features.add(w)
        correct = 0
        size = 0

        for file in os.listdir(path + "pos")[:limit]:
            correct += classify(open(path + "pos/" + file).read()) == True
            size += 1

        for file in os.listdir(path + "neg")[:limit]:
            correct += classify(open(path + "neg/" + file).read()) == False
            size += 1

        num_features.append(k+step)
        accuracy.append(correct / size)
        if (correct / size) > best_accuracy:
            bestk = k
        print k+step, correct / size

    features = set(words[:bestk])
    cPickle.dump(get_relevant_features(), open(FDATA_FILE, 'w'))

    pylab.plot(num_features, accuracy)
    pylab.show()

def test_pang_lee():
    """
    Tests the Pang Lee dataset
    """
    total, correct = 0, 0
    for fname in os.listdir("txt_sentoken/pos"):
        correct += int(classify2(open("txt_sentoken/pos/" + fname).read()) == True)
        total += 1
    for fname in os.listdir("txt_sentoken/neg"):
        correct += int(classify2(open("txt_sentoken/neg/" + fname).read()) == False)
        total += 1
    print "accuracy: %f" % (correct / total)

if __name__ == '__main__':
    train()
    feature_selection_trials()
    # test_pang_lee()
    # classify_demo(open("pos_example").read())
    # classify_demo(open("neg_example").read())

########NEW FILE########
__FILENAME__ = metric
"""
F-Score metrics for testing classifier, also includes functions for data extraction.
Author: Vivek Narayanan
"""
import os

def get_paths():
    """
    Returns supervised paths annotated with their actual labels.
    """
    posfiles = [("./aclImdb/test/pos/" + f, True) for f in os.listdir("./aclImdb/test/pos/")]
    negfiles = [("./aclImdb/test/neg/" + f, False) for f in os.listdir("./aclImdb/test/neg/")]
    return posfiles + negfiles


def fscore(classifier, file_paths):
    tpos, fpos, fneg, tneg = 0, 0, 0, 0
    for path, label in file_paths:
        result = classifier(open(path).read())
        if label and result:
            tpos += 1
        elif label and (not result):
            fneg += 1
        elif (not label) and result:
            fpos += 1
        else:
            tneg += 1
    prec = 1.0 * tpos / (tpos + fpos)
    recall = 1.0 * tpos / (tpos + fneg)
    f1 = 2 * prec * recall / (prec + recall)
    accu = 100.0 * (tpos + tneg) / (tpos+tneg+fpos+fneg)
    # print "True Positives: %d\nFalse Positives: %d\nFalse Negatives: %d\n" % (tpos, fpos, fneg)
    print "Precision: %lf\nRecall: %lf\nAccuracy: %lf" % (prec, recall, accu)

def main():
    from altbayes import classify, train 
    train()
    fscore(classify, get_paths())

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = prepare_svm
from pretrained import *
from collections import Counter
import os

tmap = dict(zip(positive.keys() + negative.keys(), xrange(len(positive) + len(negative))))

POSITIVE_PATH = "./aclImdb/train/pos/"
NEGATIVE_PATH = "./aclImdb/train/neg/"

POSITIVE_TEST_PATH = "./aclImdb/test/pos/"
NEGATIVE_TEST_PATH = "./aclImdb/test/neg/"
 
def transform(path, cls):
	words = Counter(negate_sequence(open(path).read()))
	return "%s %s\n" % (cls, ' '.join('%d:%f' % (tmap[k], words[k]) for k in words if k in tmap))

def write_file(ofile, pospath, negpath):
	f = open(ofile, "w")
	for fil in os.listdir(pospath):
		f.write(transform(pospath + fil, "+1"))
	for fil in os.listdir(negpath):
		f.write(transform(negpath + fil, "-1"))

if __name__ == '__main__':
	write_file('train.svmdata', POSITIVE_PATH, NEGATIVE_PATH)
	write_file('test.svmdata', POSITIVE_TEST_PATH, NEGATIVE_TEST_PATH)
########NEW FILE########
__FILENAME__ = pretrained
"""
Train a naive Bayes classifier from the IMDb reviews data set
"""
from __future__ import division
from collections import defaultdict
from math import log, exp
from functools import partial
import re
import os
import random
import pickle
import pylab


handle = open("trained", "rb")
sums, positive, negative = pickle.load(handle)

def tokenize(text):
    return re.findall("\w+", text)

def negate_sequence(text):
    """
    Detects negations and transforms negated words into "not_" form.
    """
    negation = False
    delims = "?.,!:;"
    result = []
    words = text.split()
    for word in words:
        stripped = word.strip(delims).lower()
        result.append("not_" + stripped if negation else stripped)

        if any(neg in word for neg in frozenset(["not", "n't", "no"])):
            negation = not negation

        if any(c in word for c in delims):
            negation = False
    return result

def get_positive_prob(word):
    return 1.0 * (positive[word] + 1) / (2 * sums['pos'])

def get_negative_prob(word):
    return 1.0 * (negative[word] + 1) / (2 * sums['neg'])

def classify(text, pneg = 0.5, preprocessor=negate_sequence):
    words = preprocessor(text)
    pscore, nscore = 0, 0

    for word in words:
        pscore += log(get_positive_prob(word))
        nscore += log(get_negative_prob(word))

    return pscore > nscore

def classify_demo(text):
    words = negate_sequence(text)
    pscore, nscore = 0, 0

    for word in words:
        pdelta = log(get_positive_prob(word))
        ndelta = log(get_negative_prob(word))
        pscore += pdelta
        nscore += ndelta
        print "%25s, pos=(%10lf, %10d) \t\t neg=(%10lf, %10d)" % (word, pdelta, positive[word], ndelta, negative[word]) 

    print "\nPositive" if pscore > nscore else "Negative"
    print "Confidence: %lf" % exp(abs(pscore - nscore))
    return pscore > nscore, pscore, nscore

def test():
    strings = [
    open("pos_example").read(), 
    open("neg_example").read(),
    "This book was quite good.",
    "I think this product is horrible."
    ]
    print map(classify, strings)

def mutual_info(word):
    """
    Finds the mutual information of a word with the training set.
    """
    cnt_p, cnt_n = sums['pos'], sums['neg']
    total = cnt_n + cnt_p
    cnt_x = positive[word] + negative[word]
    if (cnt_x == 0): 
        return 0
    cnt_x_p, cnt_x_n = positive[word], negative[word]
    I = [[0]*2]*2
    I[0][0] = (cnt_n - cnt_x_n) * log ((cnt_n - cnt_x_n) * total / cnt_x / cnt_n) / total 
    I[0][1] = cnt_x_n * log ((cnt_x_n) * total / (cnt_x * cnt_n)) / total if cnt_x_n > 0 else 0
    I[1][0] = (cnt_p - cnt_x_p) * log ((cnt_p - cnt_x_p) * total / cnt_x / cnt_p) / total 
    I[1][1] = cnt_x_p * log ((cnt_x_p) * total / (cnt_x * cnt_p)) / total if cnt_x_p > 0 else 0

    return sum(map(sum, I))

def reduce_features(features, stream):
    return [word for word in negate_sequence(stream) if word in features]

def feature_selection_experiment(test_set):
    """
    Select top k features. Vary k from 1000 to 50000 and plot data
    """
    keys = positive.keys() + negative.keys()
    sorted_keys = sorted(keys, cmp=lambda x, y: mutual_info(x) > mutual_info(y)) # Sort descending by mutual info
    features = set()
    num_features, accuracy = [], []
    print sorted_keys[-100:]

    for k in xrange(0, 50000, 1000):
        features |= set(sorted_keys[k:k+1000])
        preprocessor = partial(reduce_features, features)
        correct = 0
        for text, label in test_set:
            correct += classify(text) == label
        num_features.append(k+1000)
        accuracy.append(correct / len(test_set))
    print negate_sequence("Is this a good idea")
    print reduce_features(features, "Is this a good idea")

    pylab.plot(num_features, accuracy)
    pylab.show()

def get_paths():
    """
    Returns supervised paths annotated with their actual labels.
    """
    posfiles = [("./aclImdb/test/pos/" + f, True) for f in os.listdir("./aclImdb/test/pos/")[:500]]
    negfiles = [("./aclImdb/test/neg/" + f, False) for f in os.listdir("./aclImdb/test/neg/")[:500]]
    return posfiles + negfiles

if __name__ == '__main__':
    print mutual_info('good')
    print mutual_info('bad')
    print mutual_info('incredible')
    print mutual_info('jaskdhkasjdhkjincredible')
    feature_selection_experiment(get_paths())


########NEW FILE########
