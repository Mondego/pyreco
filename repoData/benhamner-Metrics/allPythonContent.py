__FILENAME__ = auc

def tied_rank(x):
    """
    Computes the tied rank of elements in x.

    This function computes the tied rank of elements in x.

    Parameters
    ----------
    x : list of numbers, numpy array

    Returns
    -------
    score : list of numbers
            The tied rank f each element in x

    """
    sorted_x = sorted(zip(x,range(len(x))))
    r = [0 for k in x]
    cur_val = sorted_x[0][0]
    last_rank = 0
    for i in range(len(sorted_x)):
        if cur_val != sorted_x[i][0]:
            cur_val = sorted_x[i][0]
            for j in range(last_rank, i): 
                r[sorted_x[j][1]] = float(last_rank+1+i)/2.0
            last_rank = i
        if i==len(sorted_x)-1:
            for j in range(last_rank, i+1): 
                r[sorted_x[j][1]] = float(last_rank+i+2)/2.0
    return r

def auc(actual, posterior):
    """
    Computes the area under the receiver-operater characteristic (AUC)

    This function computes the AUC error metric for binary classification.

    Parameters
    ----------
    actual : list of binary numbers, numpy array
             The ground truth value
    posterior : same type as actual
                Defines a ranking on the binary numbers, from most likely to
                be positive to least likely to be positive.

    Returns
    -------
    score : double
            The mean squared error between actual and posterior

    """
    r = tied_rank(posterior)
    num_positive = len([0 for x in actual if x==1])
    num_negative = len(actual)-num_positive
    sum_positive = sum([r[i] for i in range(len(r)) if actual[i]==1])
    auc = ((sum_positive - num_positive*(num_positive+1)/2.0) /
           (num_negative*num_positive))
    return auc
########NEW FILE########
__FILENAME__ = average_precision
import numpy as np

def apk(actual, predicted, k=10):
    """
    Computes the average precision at k.

    This function computes the average prescision at k between two lists of
    items.

    Parameters
    ----------
    actual : list
             A list of elements that are to be predicted (order doesn't matter)
    predicted : list
                A list of predicted elements (order does matter)
    k : int, optional
        The maximum number of predicted elements

    Returns
    -------
    score : double
            The average precision at k over the input lists

    """
    if len(predicted)>k:
        predicted = predicted[:k]

    score = 0.0
    num_hits = 0.0

    for i,p in enumerate(predicted):
        if p in actual and p not in predicted[:i]:
            num_hits += 1.0
            score += num_hits / (i+1.0)

    if not actual:
        return 1.0

    return score / min(len(actual), k)

def mapk(actual, predicted, k=10):
    """
    Computes the mean average precision at k.

    This function computes the mean average prescision at k between two lists
    of lists of items.

    Parameters
    ----------
    actual : list
             A list of lists of elements that are to be predicted 
             (order doesn't matter in the lists)
    predicted : list
                A list of lists of predicted elements
                (order matters in the lists)
    k : int, optional
        The maximum number of predicted elements

    Returns
    -------
    score : double
            The mean average precision at k over the input lists

    """
    return np.mean([apk(a,p,k) for a,p in zip(actual, predicted)])

########NEW FILE########
__FILENAME__ = binomial_deviance
import numpy as np

def capped_log10_likelihood(actual, predicted):
    """
    Computes the capped log10 likelihood, predictions in (0.01, 0.99).

    This function computes the log likelihood between two numbers,
    or for element between a pair of lists or numpy arrays.

    Parameters
    ----------
    actual : int, float, list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double or list of doubles
            The log likelihood error between actual and predicted

    """
    actual = np.array(actual)
    predicted = np.array(predicted)
    predicted[predicted<0.01]=0.01
    predicted[predicted>0.99]=0.99

    score = -(actual*np.log10(predicted)+(1-actual)*np.log10(1-predicted))
    
    if type(score)==np.ndarray:
        score[np.isnan(score)] = 0
    else:
        if np.isnan(score):
            score = 0
    return score

def capped_binomial_deviance(actual, predicted):
    """
    Computes the capped binomial deviance.

    This function computes the log loss between two lists
    of numbers.

    Parameters
    ----------
    actual : list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double
            The log loss between actual and predicted

    """
    return np.mean(capped_log10_likelihood(actual, predicted))
########NEW FILE########
__FILENAME__ = kdd_average_precision
import numpy as np

def kdd_apk(actual, predicted, k=10):
    """
    Computes the average precision at k for Track 1 of the 2012 KDD Cup.

    This modified version uses the number of actual clicks as the denominator,
    regardless of k.

    This function computes the average prescision at k between two lists of
    items.

    Parameters
    ----------
    actual : list
             A list of elements that are to be predicted (order doesn't matter)
    predicted : list
                A list of predicted elements (order does matter)
    k : int, optional
        The maximum number of predicted elements

    Returns
    -------
    score : double
            The average precision at k over the input lists

    """
    if len(predicted)>k:
        predicted = predicted[:k]

    score = 0.0
    num_hits = 0.0

    for i,p in enumerate(predicted):
        if p in actual and p not in predicted[:i]:
            num_hits += 1.0
            score += num_hits / (i+1.0)

    if not actual:
        return 0.0

    return score / len(actual)

def kdd_mapk(actual, predicted, k=10):
    """
    Computes the mean average precision at k for Track 1 of the 2012 KDD Cup.

    This modified version uses the number of actual clicks as the denominator,
    regardless of k.

    This function computes the mean average prescision at k between two lists
    of lists of items.

    Parameters
    ----------
    actual : list
             A list of lists of elements that are to be predicted 
             (order doesn't matter in the lists)
    predicted : list
                A list of lists of predicted elements
                (order matters in the lists)
    k : int, optional
        The maximum number of predicted elements

    Returns
    -------
    score : double
            The mean average precision at k over the input lists

    """
    return np.mean([kdd_apk(a,p,k) for a,p in zip(actual, predicted)])

########NEW FILE########
__FILENAME__ = edit_distance
from __future__ import division

def levenshtein(s1, s2, normalize=False):
    """
    s1: String
    s2: String

    normalize: divide edit distance by maximum length if true
    """
    if len(s1) < len(s2):
        return levenshtein(s2, s1, normalize)
    if not s2:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i+1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j+1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    if normalize:
        return (current_row[-1] / len(s1))
    return current_row[-1]
########NEW FILE########
__FILENAME__ = elementwise
import numpy as np

def ae(actual, predicted):
    """
    Computes the absolute error.

    This function computes the absolute error between two numbers,
    or for element between a pair of lists or numpy arrays.

    Parameters
    ----------
    actual : int, float, list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double or list of doubles
            The absolute error between actual and predicted

    """
    return np.abs(np.array(actual)-np.array(predicted))

def ce(actual, predicted):
    """
    Computes the classification error.

    This function computes the classification error between two lists

    Parameters
    ----------
    actual : list
             A list of the true classes
    predicted : list
                A list of the predicted classes

    Returns
    -------
    score : double
            The classification error between actual and predicted

    """
    return (sum([1.0 for x,y in zip(actual,predicted) if x != y]) /
            len(actual))

def mae(actual, predicted):
    """
    Computes the mean absolute error.

    This function computes the mean absolute error between two lists
    of numbers.

    Parameters
    ----------
    actual : list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double
            The mean absolute error between actual and predicted

    """
    return np.mean(ae(actual, predicted))

def mse(actual, predicted):
    """
    Computes the mean squared error.

    This function computes the mean squared error between two lists
    of numbers.

    Parameters
    ----------
    actual : list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double
            The mean squared error between actual and predicted

    """
    return np.mean(se(actual, predicted))

def msle(actual, predicted):
    """
    Computes the mean squared log error.

    This function computes the mean squared log error between two lists
    of numbers.

    Parameters
    ----------
    actual : list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double
            The mean squared log error between actual and predicted

    """
    return np.mean(sle(actual, predicted))

def rmse(actual, predicted):
    """
    Computes the root mean squared error.

    This function computes the root mean squared error between two lists
    of numbers.

    Parameters
    ----------
    actual : list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double
            The root mean squared error between actual and predicted

    """
    return np.sqrt(mse(actual, predicted))

def rmsle(actual, predicted):
    """
    Computes the root mean squared log error.

    This function computes the root mean squared log error between two lists
    of numbers.

    Parameters
    ----------
    actual : list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double
            The root mean squared log error between actual and predicted

    """
    return np.sqrt(msle(actual, predicted))

def se(actual, predicted):
    """
    Computes the squared error.

    This function computes the squared error between two numbers,
    or for element between a pair of lists or numpy arrays.

    Parameters
    ----------
    actual : int, float, list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double or list of doubles
            The squared error between actual and predicted

    """
    return np.power(np.array(actual)-np.array(predicted), 2)

def sle(actual, predicted):
    """
    Computes the squared log error.

    This function computes the squared log error between two numbers,
    or for element between a pair of lists or numpy arrays.

    Parameters
    ----------
    actual : int, float, list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double or list of doubles
            The squared log error between actual and predicted

    """
    return (np.power(np.log(np.array(actual)+1) - 
            np.log(np.array(predicted)+1), 2))

def ll(actual, predicted):
    """
    Computes the log likelihood.

    This function computes the log likelihood between two numbers,
    or for element between a pair of lists or numpy arrays.

    Parameters
    ----------
    actual : int, float, list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double or list of doubles
            The log likelihood error between actual and predicted

    """
    actual = np.array(actual)
    predicted = np.array(predicted)
    err = np.seterr(all='ignore')
    score = -(actual*np.log(predicted)+(1-actual)*np.log(1-predicted))
    np.seterr(divide=err['divide'], over=err['over'],
              under=err['under'], invalid=err['invalid'])
    if type(score)==np.ndarray:
        score[np.isnan(score)] = 0
    else:
        if np.isnan(score):
            score = 0
    return score

def log_loss(actual, predicted):
    """
    Computes the log loss.

    This function computes the log loss between two lists
    of numbers.

    Parameters
    ----------
    actual : list of numbers, numpy array
             The ground truth value
    predicted : same type as actual
                The predicted value

    Returns
    -------
    score : double
            The log loss between actual and predicted

    """
    return np.mean(ll(actual, predicted))
########NEW FILE########
__FILENAME__ = quadratic_weighted_kappa
#! /usr/bin/env python2.7

import numpy as np


def confusion_matrix(rater_a, rater_b, min_rating=None, max_rating=None):
    """
    Returns the confusion matrix between rater's ratings
    """
    assert(len(rater_a) == len(rater_b))
    if min_rating is None:
        min_rating = min(rater_a + rater_b)
    if max_rating is None:
        max_rating = max(rater_a + rater_b)
    num_ratings = int(max_rating - min_rating + 1)
    conf_mat = [[0 for i in range(num_ratings)]
                for j in range(num_ratings)]
    for a, b in zip(rater_a, rater_b):
        conf_mat[a - min_rating][b - min_rating] += 1
    return conf_mat


def histogram(ratings, min_rating=None, max_rating=None):
    """
    Returns the counts of each type of rating that a rater made
    """
    if min_rating is None:
        min_rating = min(ratings)
    if max_rating is None:
        max_rating = max(ratings)
    num_ratings = int(max_rating - min_rating + 1)
    hist_ratings = [0 for x in range(num_ratings)]
    for r in ratings:
        hist_ratings[r - min_rating] += 1
    return hist_ratings


def quadratic_weighted_kappa(rater_a, rater_b, min_rating=None, max_rating=None):
    """
    Calculates the quadratic weighted kappa
    quadratic_weighted_kappa calculates the quadratic weighted kappa
    value, which is a measure of inter-rater agreement between two raters
    that provide discrete numeric ratings.  Potential values range from -1
    (representing complete disagreement) to 1 (representing complete
    agreement).  A kappa value of 0 is expected if all agreement is due to
    chance.

    quadratic_weighted_kappa(rater_a, rater_b), where rater_a and rater_b
    each correspond to a list of integer ratings.  These lists must have the
    same length.

    The ratings should be integers, and it is assumed that they contain
    the complete range of possible ratings.

    quadratic_weighted_kappa(X, min_rating, max_rating), where min_rating
    is the minimum possible rating, and max_rating is the maximum possible
    rating
    """
    rater_a = np.array(rater_a, dtype=int)
    rater_b = np.array(rater_b, dtype=int)
    assert(len(rater_a) == len(rater_b))
    if min_rating is None:
        min_rating = min(min(rater_a), min(rater_b))
    if max_rating is None:
        max_rating = max(max(rater_a), max(rater_b))
    conf_mat = confusion_matrix(rater_a, rater_b,
                                min_rating, max_rating)
    num_ratings = len(conf_mat)
    num_scored_items = float(len(rater_a))

    hist_rater_a = histogram(rater_a, min_rating, max_rating)
    hist_rater_b = histogram(rater_b, min_rating, max_rating)

    numerator = 0.0
    denominator = 0.0

    for i in range(num_ratings):
        for j in range(num_ratings):
            expected_count = (hist_rater_a[i] * hist_rater_b[j]
                              / num_scored_items)
            d = pow(i - j, 2.0) / pow(num_ratings - 1, 2.0)
            numerator += d * conf_mat[i][j] / num_scored_items
            denominator += d * expected_count / num_scored_items

    return 1.0 - numerator / denominator


def linear_weighted_kappa(rater_a, rater_b, min_rating=None, max_rating=None):
    """
    Calculates the linear weighted kappa
    linear_weighted_kappa calculates the linear weighted kappa
    value, which is a measure of inter-rater agreement between two raters
    that provide discrete numeric ratings.  Potential values range from -1
    (representing complete disagreement) to 1 (representing complete
    agreement).  A kappa value of 0 is expected if all agreement is due to
    chance.

    linear_weighted_kappa(rater_a, rater_b), where rater_a and rater_b
    each correspond to a list of integer ratings.  These lists must have the
    same length.

    The ratings should be integers, and it is assumed that they contain
    the complete range of possible ratings.

    linear_weighted_kappa(X, min_rating, max_rating), where min_rating
    is the minimum possible rating, and max_rating is the maximum possible
    rating
    """
    assert(len(rater_a) == len(rater_b))
    if min_rating is None:
        min_rating = min(rater_a + rater_b)
    if max_rating is None:
        max_rating = max(rater_a + rater_b)
    conf_mat = confusion_matrix(rater_a, rater_b,
                                min_rating, max_rating)
    num_ratings = len(conf_mat)
    num_scored_items = float(len(rater_a))

    hist_rater_a = histogram(rater_a, min_rating, max_rating)
    hist_rater_b = histogram(rater_b, min_rating, max_rating)

    numerator = 0.0
    denominator = 0.0

    for i in range(num_ratings):
        for j in range(num_ratings):
            expected_count = (hist_rater_a[i] * hist_rater_b[j]
                              / num_scored_items)
            d = abs(i - j) / float(num_ratings - 1)
            numerator += d * conf_mat[i][j] / num_scored_items
            denominator += d * expected_count / num_scored_items

    return 1.0 - numerator / denominator


def kappa(rater_a, rater_b, min_rating=None, max_rating=None):
    """
    Calculates the kappa
    kappa calculates the kappa
    value, which is a measure of inter-rater agreement between two raters
    that provide discrete numeric ratings.  Potential values range from -1
    (representing complete disagreement) to 1 (representing complete
    agreement).  A kappa value of 0 is expected if all agreement is due to
    chance.

    kappa(rater_a, rater_b), where rater_a and rater_b
    each correspond to a list of integer ratings.  These lists must have the
    same length.

    The ratings should be integers, and it is assumed that they contain
    the complete range of possible ratings.

    kappa(X, min_rating, max_rating), where min_rating
    is the minimum possible rating, and max_rating is the maximum possible
    rating
    """
    assert(len(rater_a) == len(rater_b))
    if min_rating is None:
        min_rating = min(rater_a + rater_b)
    if max_rating is None:
        max_rating = max(rater_a + rater_b)
    conf_mat = confusion_matrix(rater_a, rater_b,
                                min_rating, max_rating)
    num_ratings = len(conf_mat)
    num_scored_items = float(len(rater_a))

    hist_rater_a = histogram(rater_a, min_rating, max_rating)
    hist_rater_b = histogram(rater_b, min_rating, max_rating)

    numerator = 0.0
    denominator = 0.0

    for i in range(num_ratings):
        for j in range(num_ratings):
            expected_count = (hist_rater_a[i] * hist_rater_b[j]
                              / num_scored_items)
            if i == j:
                d = 0.0
            else:
                d = 1.0
            numerator += d * conf_mat[i][j] / num_scored_items
            denominator += d * expected_count / num_scored_items

    return 1.0 - numerator / denominator


def mean_quadratic_weighted_kappa(kappas, weights=None):
    """
    Calculates the mean of the quadratic
    weighted kappas after applying Fisher's r-to-z transform, which is
    approximately a variance-stabilizing transformation.  This
    transformation is undefined if one of the kappas is 1.0, so all kappa
    values are capped in the range (-0.999, 0.999).  The reverse
    transformation is then applied before returning the result.

    mean_quadratic_weighted_kappa(kappas), where kappas is a vector of
    kappa values

    mean_quadratic_weighted_kappa(kappas, weights), where weights is a vector
    of weights that is the same size as kappas.  Weights are applied in the
    z-space
    """
    kappas = np.array(kappas, dtype=float)
    if weights is None:
        weights = np.ones(np.shape(kappas))
    else:
        weights = weights / np.mean(weights)

    # ensure that kappas are in the range [-.999, .999]
    kappas = np.array([min(x, .999) for x in kappas])
    kappas = np.array([max(x, -.999) for x in kappas])

    z = 0.5 * np.log((1 + kappas) / (1 - kappas)) * weights
    z = np.mean(z)
    return (np.exp(2 * z) - 1) / (np.exp(2 * z) + 1)


def weighted_mean_quadratic_weighted_kappa(solution, submission):
    predicted_score = submission[submission.columns[-1]].copy()
    predicted_score.name = "predicted_score"
    if predicted_score.index[0] == 0:
        predicted_score = predicted_score[:len(solution)]
        predicted_score.index = solution.index
    combined = solution.join(predicted_score, how="left")
    groups = combined.groupby(by="essay_set")
    kappas = [quadratic_weighted_kappa(group[1]["essay_score"], group[1]["predicted_score"]) for group in groups]
    weights = [group[1]["essay_weight"].irow(0) for group in groups]
    return mean_quadratic_weighted_kappa(kappas, weights=weights)

########NEW FILE########
__FILENAME__ = test_auc
#! /usr/bin/env python2.7

import unittest
import ml_metrics as metrics
import numpy as np

class TestAuc(unittest.TestCase):

    def test_auc(self):
        self.assertAlmostEqual(metrics.auc([1,0,1,1], [.32,.52,.26,.86]), 1.0/3)
        self.assertAlmostEqual(metrics.auc([1,0,1,0,1], [.9,.1,.8,.1,.7]), 1)
        self.assertAlmostEqual(metrics.auc([0,1,1,0], [.2,.1,.3,.4]), 1.0/4)
        self.assertAlmostEqual(metrics.auc([1,1,1,1,0,0,0,0,0,0], 
                                           [1,1,1,1,1,1,1,1,1,1]), 1.0/2)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_average_precision
#! /usr/bin/env python2.7

import unittest
import ml_metrics as metrics
import numpy as np

class TestAveragePrecision(unittest.TestCase):

    def test_apk(self):
        self.assertAlmostEqual(metrics.apk(range(1,6),[6,4,7,1,2], 2), 0.25)
        self.assertAlmostEqual(metrics.apk(range(1,6),[1,1,1,1,1], 5), 0.2)
        predicted = range(1,21)
        predicted.extend(range(200,600))
        self.assertAlmostEqual(metrics.apk(range(1,100),predicted, 20), 1.0)

    def test_mapk(self):
        self.assertAlmostEqual(metrics.mapk([range(1,5)],[range(1,5)],3), 1.0)
        self.assertAlmostEqual(metrics.mapk([[1,3,4],[1,2,4],[1,3]],
            [range(1,6),range(1,6),range(1,6)], 3), 0.685185185185185)
        self.assertAlmostEqual(metrics.mapk([range(1,6),range(1,6)],
            [[6,4,7,1,2],[1,1,1,1,1]], 5), 0.26)
        self.assertAlmostEqual(metrics.mapk([[1,3],[1,2,3],[1,2,3]],
            [range(1,6),[1,1,1],[1,2,1]], 3), 11.0/18)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_edit_distance
#! /usr/bin/env python2.7

from __future__ import division
import unittest
import ml_metrics as metrics

class TestEditDistance(unittest.TestCase):

    def test_levenshtein(self):
        self.assertEqual(metrics.levenshtein("intention", "execution"), 5)
        self.assertEqual(metrics.levenshtein("sitting", "kitten"), 3)
        self.assertEqual(metrics.levenshtein("Saturday", "Sunday"), 3)
        self.assertEqual(metrics.levenshtein("sitting", ""), 7)
        self.assertEqual(metrics.levenshtein("", "Ben"), 3)
        self.assertEqual(metrics.levenshtein("cat", "cat"), 0)
        self.assertEqual(metrics.levenshtein("hat", "cat"), 1)
        self.assertEqual(metrics.levenshtein("at", "cat"), 1)
        self.assertEqual(metrics.levenshtein("", "a"), 1)
        self.assertEqual(metrics.levenshtein("a", ""), 1)
        self.assertEqual(metrics.levenshtein("", ""), 0)
        self.assertEqual(metrics.levenshtein("ant", "aunt"), 1)
        self.assertEqual(metrics.levenshtein("Samantha", "Sam"), 5)
        self.assertEqual(metrics.levenshtein("Flomax", "Volmax"), 3)
        self.assertEqual(metrics.levenshtein([1], [1]), 0)
        self.assertEqual(metrics.levenshtein([1], [1,2]), 1)
        self.assertEqual(metrics.levenshtein([1], [1,10]), 1)
        self.assertEqual(metrics.levenshtein([1,2], [10,20]), 2)
        self.assertEqual(metrics.levenshtein([1,2], [10,20,30]), 3)
        self.assertEqual(metrics.levenshtein([3,3,4], [4,1,4,3]), 3)

    def test_levenshtein_normalized(self):
        self.assertEqual(metrics.levenshtein("intention", "execution", True), 5/9)
        self.assertEqual(metrics.levenshtein("sitting", "kitten", normalize=True), 3/7)
        self.assertEqual(metrics.levenshtein("Saturday", "Sunday", True), 3/8)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_elementwise
#! /usr/bin/env python2.7

import unittest
import ml_metrics as metrics
import numpy as np

class TestElementwise(unittest.TestCase):

    def test_ae(self):
        self.assertAlmostEqual(metrics.ae(3.4, 3.4), 0)
        self.assertAlmostEqual(metrics.ae(3.4, 4.4), 1.0)
        self.assertAlmostEqual(metrics.ae(9, 11), 2)

    def test_ce(self):
        self.assertAlmostEqual(metrics.ce([1,1,1,0,0,0],
                                          [1,1,1,0,0,0]), 0)
        self.assertAlmostEqual(metrics.ce([1,1,1,0,0,0],
                                          [1,1,1,1,0,0]), 1.0/6)
        self.assertAlmostEqual(metrics.ce([1,2,3,4],
                                          [1,2,3,3]), 0.25)
        self.assertAlmostEqual(metrics.ce(["cat", "dog", "bird"],
                                          ["cat", "dog", "fish"]), 1.0/3)
        self.assertAlmostEqual(metrics.ce(["cat", "dog", "bird"],
                                          ["caat", "doog", "biird"]), 1)
    
    def test_ll(self):
        self.assertAlmostEqual(metrics.ll(1,1), 0)
        self.assertAlmostEqual(metrics.ll(1,0), np.inf)
        self.assertAlmostEqual(metrics.ll(0,1), np.inf)
        self.assertAlmostEqual(metrics.ll(1,0.5), -np.log(0.5))

    def test_logLoss(self):
        self.assertAlmostEqual(metrics.log_loss([1,1,0,0],[1,1,0,0]), 0)
        self.assertAlmostEqual(metrics.log_loss([1,1,0,0],[1,1,1,0]), np.inf)
        self.assertAlmostEqual(metrics.log_loss([1,1,1,0,0,0],[0.5,0.1,0.01,0.9,0.75,0.001]), 1.881797068998267)
        self.assertAlmostEqual(metrics.log_loss(1,0.5), -np.log(0.5))

    def test_mae(self):
        self.assertAlmostEqual(metrics.mae(range(0,11), range(1,12)), 1)
        self.assertAlmostEqual(metrics.mae([0,.5,1,1.5,2], [0,.5,1,1.5,2]), 0)
        self.assertAlmostEqual(metrics.mae(range(1,5), [1,2,3,5]), 0.25)

    def test_mse(self):
        self.assertAlmostEqual(metrics.mse(range(0,11), range(1,12)), 1)
        self.assertAlmostEqual(metrics.mse([0,.5,1,1.5,2], [0,.5,1,1.5,2]), 0)
        self.assertAlmostEqual(metrics.mse(range(1,5), [1,2,3,6]), 1.0)

    def test_msle(self):
        self.assertAlmostEqual(metrics.msle(np.exp(2)-1,np.exp(1)-1), 1)
        self.assertAlmostEqual(metrics.msle([0,.5,1,1.5,2], [0,.5,1,1.5,2]), 0)
        self.assertAlmostEqual(metrics.msle([1,2,3,np.exp(1)-1], [1,2,3,np.exp(2)-1]), 0.25)

    def test_rmse(self):
        self.assertAlmostEqual(metrics.rmse(range(0,11), range(1,12)), 1)
        self.assertAlmostEqual(metrics.rmse([0,.5,1,1.5,2], [0,.5,1,1.5,2]), 0)
        self.assertAlmostEqual(metrics.rmse(range(1,5), [1,2,3,5]), 0.5)

    def test_rmsle(self):
        self.assertAlmostEqual(metrics.rmsle(np.exp(2)-1,np.exp(1)-1), 1)
        self.assertAlmostEqual(metrics.rmsle([0,.5,1,1.5,2], [0,.5,1,1.5,2]), 0)
        self.assertAlmostEqual(metrics.rmsle([1,2,3,np.exp(1)-1], [1,2,3,np.exp(2)-1]), 0.5)

    def test_se(self):
        self.assertAlmostEqual(metrics.se(3.4, 3.4), 0)
        self.assertAlmostEqual(metrics.se(3.4, 4.4), 1.0)
        self.assertAlmostEqual(metrics.se(9, 11), 4)

    def test_sle(self):
        self.assertAlmostEqual(metrics.sle(3.4, 3.4), 0)
        self.assertAlmostEqual(metrics.sle(np.exp(2)-1, np.exp(1)-1), 1.0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_kappa
#! /usr/bin/env python2.7

import unittest
import ml_metrics as metrics

class Testquadratic_weighted_kappa(unittest.TestCase):

    def test_confusion_matrix(self):
        conf_mat = metrics.confusion_matrix([1,2],[1,2])
        self.assertEqual(conf_mat,[[1,0],[0,1]])
        
        conf_mat = metrics.confusion_matrix([1,2],[1,2],0,2)
        self.assertEqual(conf_mat,[[0,0,0],[0,1,0],[0,0,1]])
        
        conf_mat = metrics.confusion_matrix([1,1,2,2,4],[1,1,3,3,5])
        self.assertEqual(conf_mat,[[2,0,0,0,0],[0,0,2,0,0],[0,0,0,0,0],
                                   [0,0,0,0,1],[0,0,0,0,0]])
        
        conf_mat = metrics.confusion_matrix([1,2],[1,2],1,4)
        self.assertEqual(conf_mat,[[1,0,0,0],[0,1,0,0],[0,0,0,0],[0,0,0,0]])

    def test_quadratic_weighted_kappa(self):
        kappa = metrics.quadratic_weighted_kappa([1,2,3],[1,2,3])
        self.assertAlmostEqual(kappa, 1.0)

        kappa = metrics.quadratic_weighted_kappa([1,2,1],[1,2,2],1,2)
        self.assertAlmostEqual(kappa, 0.4)

        kappa = metrics.quadratic_weighted_kappa([1,2,3,1,2,2,3],[1,2,3,1,2,3,2])
        self.assertAlmostEqual(kappa, 0.75)
    
    # todo: test cases for linear_weighted_kappa

    def test_mean_quadratic_weighted_kappa(self):
        kappa = metrics.mean_quadratic_weighted_kappa([1, 1])
        self.assertAlmostEqual(kappa, 0.999)

        kappa = metrics.mean_quadratic_weighted_kappa([0.5, 0.8], [1,.5])
        self.assertAlmostEqual(kappa, 0.624536446425734)

        kappa = metrics.mean_quadratic_weighted_kappa([-1, 1])
        self.assertAlmostEqual(kappa, 0.0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
