__FILENAME__ = base
#-*- coding:utf-8 -*-

"""
Base Recommender Models.
"""

# Authors: Marcel Caraciolo <marcel@caraciolo.com.br>
# Based on scikit-learn's base.py, written by Gael Varoquaux.
# License: BSD Style.

import inspect
import warnings
from .utils.format import _pprint


class BaseRecommender(object):
    """Base Class for Recommenders that suggest items for users.

    Should not be used directly, use derived classes instead

    Notes
    -----
    All estimators should specify all the parameters that can be set
    at the class level in their __init__ as explicit keyword
    arguments (no *args, **kwargs).
    """

    @classmethod
    def _get_param_names(cls):
        """Get parameter names for the estimator"""
        try:
            # fetch the constructor or the original constructor before
            # deprecation wrapping if any
            init = getattr(cls.__init__, 'deprecated_original', cls.__init__)

            # introspect the constructor arguments to find the model parameters
            # to represent
            args, varargs, kw, default = inspect.getargspec(init)
            if not varargs is None:
                raise RuntimeError('crab recommenders should always '
                                   'specify their parameters in the signature'
                                   ' of their init (no varargs).')
            # Remove 'self'
            # XXX: This is going to fail if the init is a staticmethod, but
            # who would do this?
            args.pop(0)
        except TypeError:
            # No explicit __init__
            args = []
        args.sort()
        return args

    def get_params(self, deep=True):
        """Get parameters for the recommender

        Parameters
        ----------
        deep: boolean, optional
            If True, will return the parameters for this reccommender and
            contained subobjects that are recommenders.

        Returns
        -------
        params : mapping of string to any
            Parameter names mapped to their values.
        """
        out = dict()
        for key in self._get_param_names():
            # catch deprecation warnings
            with warnings.catch_warnings(record=True) as w:
                value = getattr(self, key, None)
            if len(w) and w[0].category == DeprecationWarning:
                # if the parameter is deprecated, don't show it
                continue

            # XXX: should we rather test if instance of recommender?
            if deep and hasattr(value, 'get_params'):
                deep_items = value.get_params().items()
                out.update((key + '__' + k, val) for k, val in deep_items)
            out[key] = value
        return out

    def set_params(self, **params):
        """Set the parameters of the recommenders.

        The method works on simple reccommenders as well as on nested objects
        (such as pipelines). The former have parameters of the form
        ``<component>__<parameter>`` so that it's possible to update each
        component of a nested object.

        Returns
        -------
        self
        """
        if not params:
            # Simple optimisation to gain speed (inspect is slow)
            return self
        valid_params = self.get_params(deep=True)
        for key, value in params.iteritems():
            split = key.split('__', 1)
            if len(split) > 1:
                # nested objects case
                name, sub_name = split
                if not name in valid_params:
                    raise ValueError('Invalid param %s for reccommender %s' %
                                     (name, self))
                sub_object = valid_params[name]
                sub_object.set_params(**{sub_name: value})
            else:
                # simple objects case
                if not key in valid_params:
                    raise ValueError('Invalid param %s ' 'for reccommender %s'
                                     % (key, self.__class__.__name__))
                setattr(self, key, value)
        return self

    def __repr__(self):
        class_name = self.__class__.__name__
        return '%s(%s)' % (class_name, _pprint(self.get_params(deep=False),
                                               offset=len(class_name),),)

    def __str__(self):
        class_name = self.__class__.__name__
        return '%s(%s)' % (class_name,
                           _pprint(self.get_params(deep=True),
                                   offset=len(class_name), printer=str,),)

########NEW FILE########
__FILENAME__ = pairwise
#-*- coding:utf-8 -*-

"""Utilities to evaluate pairwise distances or metrics between 2
sets of points.

Distance metrics are a function d(a, b) such that d(a, b) < d(a, c) if objects
a and b are considered "more similar" to objects a and c. Two objects exactly
alike would have a distance of zero.
One of the most popular examples is Euclidean distance.
To be a 'true' metric, it must obey the following four conditions::

    1. d(a, b) >= 0, for all a and b
    2. d(a, b) == 0, if and only if a = b, positive definiteness
    3. d(a, b) == d(b, a), symmetry
    4. d(a, c) <= d(a, b) + d(b, c), the triangle inequality

"""

# Authors: Marcel Caraciolo <caraciol@gmail.com>
# Based on scikit-learn's metrics.pairwise, written by
#   Alexandre Gramfort <alexandre.gramfort@inria.fr>
#   Mathieu Blondel <mathieu@mblondel.org>
#   Robert Layton <robertlayton@gmail.com>
#   Andreas Mueller <amueller@ais.uni-bonn.de>
#   Lars Buitinck <larsmans@gmail.com>

# License: BSD Style.

import numpy as np
import scipy.spatial.distance as ssd
from scipy.stats import spearmanr as spearman
from scipy.sparse import issparse
from scipy.sparse import csr_matrix

from ..utils import safe_asarray, atleast2d_or_csr
from ..utils.extmath import safe_sparse_dot


# Utility Functions
def check_pairwise_arrays(X, Y):
    """ Set X and Y appropriately and checks inputs

    If Y is None, it is set as a pointer to X (i.e. not a copy).
    If Y is given, this does not happen.
    All distance metrics should use this function first to assert that the
    given parameters are correct and safe to use.

    Specifically, this function first ensures that both X and Y are arrays,
    then checks that they are at least two dimensional. Finally, the function
    checks that the size of the second dimension of the two arrays is equal.

    Parameters
    ----------
    X : {array-like, sparse matrix}, shape = [n_samples_a, n_features]

    Y : {array-like, sparse matrix}, shape = [n_samples_b, n_features]

    Returns
    -------
    safe_X : {array-like, sparse matrix}, shape = [n_samples_a, n_features]
        An array equal to X, guaranteed to be a numpy array.

    safe_Y : {array-like, sparse matrix}, shape = [n_samples_b, n_features]
        An array equal to Y if Y was not None, guaranteed to be a numpy array.
        If Y was None, safe_Y will be a pointer to X.

    """
    if Y is X or Y is None:
        X = safe_asarray(X)
        X = Y = atleast2d_or_csr(X, dtype=np.float)
    else:
        X = safe_asarray(X)
        Y = safe_asarray(Y)
        X = atleast2d_or_csr(X, dtype=np.float)
        Y = atleast2d_or_csr(Y, dtype=np.float)
    if len(X.shape) < 2:
        raise ValueError("X is required to be at least two dimensional.")
    if len(Y.shape) < 2:
        raise ValueError("Y is required to be at least two dimensional.")
    if X.shape[1] != Y.shape[1]:
        raise ValueError("Incompatible dimension for X and Y matrices: "
                         "X.shape[1] == %d while Y.shape[1] == %d" % (
                             X.shape[1], Y.shape[1]))
    return X, Y


# Distances
def euclidean_distances(X, Y=None, Y_norm_squared=None, squared=False,
                        inverse=False):
    """
    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors.

    For efficiency reasons, the euclidean distance between a pair of row
    vector x and y is computed as::

        dist(x, y) = sqrt(dot(x, x) - 2 * dot(x, y) + dot(y, y))

    This formulation has two main advantages. First, it is computationally
    efficient when dealing with sparse data. Second, if x varies but y
    remains unchanged, then the right-most dot-product `dot(y, y)` can be
    pre-computed.


    An implementation of a "similarity" based on the Euclidean "distance"
    between two users X and Y. Thinking of items as dimensions and
    preferences as points along those dimensions, a distance is computed
    using all items (dimensions) where both users have expressed a preference
    for that item. This is simply the square root of the sum of the squares
    of differences in position (preference) along each dimension.

    The similarity could be computed as 1 / (1 + distance), so the resulting
    values are in the range (0,1].

    Parameters
    ----------
    X : {array-like, sparse matrix}, shape = [n_samples_1, n_features]

    Y : {array-like, sparse matrix}, shape = [n_samples_2, n_features]

    Y_norm_squared : array-like, shape = [n_samples_2], optional
        Pre-computed dot-products of vectors in Y (e.g.,
        ``(Y**2).sum(axis=1)``)

    squared : boolean, optional
        This routine will return squared Euclidean distances instead.

    inverse: boolean, optional
        This routine will return the inverse Euclidean distances instead.


    Returns
    -------
    distances : {array, sparse matrix}, shape = [n_samples_1, n_samples_2]

    Examples
    --------
    >>> from crab.metrics.pairwise import euclidean_distances
    >>> X = [[0, 1], [1, 1]]
    >>> # distance between rows of X
    >>> euclidean_distances(X, X)
    array([[ 0.,  1.],
           [ 1.,  0.]])
    >>> # get distance to origin
    >>> X = [[1.0, 0.0],[1.0,1.0]]
    >>> euclidean_distances(X, [[0.0, 0.0]])
    array([[ 1.      ],
          [ 1.41421356]])

    """
    # should not need X_norm_squared because if you could precompute that as
    # well as Y, then you should just pre-compute the output and not even
    # call this function.
    X, Y = check_pairwise_arrays(X, Y)

    if issparse(X):
        XX = X.multiply(X).sum(axis=1)
    else:
        XX = np.sum(X * X, axis=1)[:, np.newaxis]

    if X is Y:  # shortcut in the common case euclidean_distances(X, X)
        YY = XX.T
    elif Y_norm_squared is None:
        if issparse(Y):
            # scipy.sparse matrices don't have element-wise scalar
            # exponentiation, and tocsr has a copy kwarg only on CSR matrices.
            YY = Y.copy() if isinstance(Y, csr_matrix) else Y.tocsr()
            YY.data **= 2
            YY = np.asarray(YY.sum(axis=1)).T
        else:
            YY = np.sum(Y ** 2, axis=1)[np.newaxis, :]
    else:
        YY = atleast2d_or_csr(Y_norm_squared)
        if YY.shape != (1, Y.shape[0]):
            raise ValueError(
                "Incompatible dimensions for Y and Y_norm_squared")

    # TODO: a faster Cython implementation would do the clipping of negative
    # values in a single pass over the output matrix.
    distances = safe_sparse_dot(X, Y.T, dense_output=True)
    distances *= -2
    distances += XX
    distances += YY
    np.maximum(distances, 0, distances)

    if X is Y:
        # Ensure that distances between vectors and themselves are set to 0.0.
        # This may not be the case due to floating point rounding errors.
        distances.flat[::distances.shape[0] + 1] = 0.0

    distances = np.divide(1.0, (1.0 + distances)) if inverse else distances

    return distances if squared else np.sqrt(distances)


euclidian_distances = euclidean_distances  # both spelling for backward compatibility


def manhattan_distances(X, Y):
    """
    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors.

    This distance implementation is the distance between two points in a grid
    based on a strictly horizontal and/or vertical path (that is, along the
    grid lines as opposed to the diagonal or "as the crow flies" distance.
    The Manhattan distance is the simple sum of the horizontal and vertical
    components, whereas the diagonal distance might be computed by applying the
    Pythagorean theorem.

    The resulting unbounded distance is then mapped between 0 and 1.

    Parameters
    ----------
    X: array of shape (n_samples_1, n_features)

    Y: array of shape (n_samples_2, n_features)

    Returns
    -------
    distances: array of shape (n_samples_1, n_samples_2)

    Examples
    --------
    >>> from crab.metrics.pairwise  import manhattan_distances
    >>> X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    >>> # distance between rows of X
    >>> manhattan_distances(X, X)
    array([[ 1.,  1.],
           [ 1.,  1.]])
    >>> manhattan_distances(X, [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]])
    array([[ 0.25],
          [ 0.25]])
    """

    if issparse(X) or issparse(Y):
        raise ValueError("manhattan_distance does"
                         "not support sparse matrices.")
    X, Y = check_pairwise_arrays(X, Y)
    n_samples_X, n_features_X = X.shape
    n_samples_Y, n_features_Y = Y.shape
    if n_features_X != n_features_Y:
        raise Exception("X and Y should have the same number of features!")
    D = np.abs(X[:, np.newaxis, :] - Y[np.newaxis, :, :])
    D = np.sum(D, axis=2)

    return 1.0 - (D / float(n_features_X))


def pearson_correlation(X, Y):
    """
    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors.

    This correlation implementation is equivalent to the cosine similarity
    since the data it receives is assumed to be centered -- mean is 0. The
    correlation may be interpreted as the cosine of the angle between the two
    vectors defined by the users preference values.

    Parameters
    ----------
    X : {array-like, sparse matrix}, shape = [n_samples_1, n_features]

    Y : {array-like, sparse matrix}, shape = [n_samples_2, n_features]

    Returns
    -------
    distances : {array, sparse matrix}, shape = [n_samples_1, n_samples_2]

    Examples
    --------
    >>> from crab.metrics.pairwise import pearson_correlation
    >>> X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0],[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    >>> # distance between rows of X
    >>> pearson_correlation(X, X)
    array([[ 1., 1.],
           [ 1., 1.]])
    >>> pearson_correlation(X, [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]])
    array([[ 0.39605902],
               [ 0.39605902]])
    """

    X, Y = check_pairwise_arrays(X, Y)

    # should not need X_norm_squared because if you could precompute that as
    # well as Y, then you should just pre-compute the output and not even
    # call this function.

    #TODO: Fix to work with sparse matrices.
    if issparse(X) or issparse(Y):
        raise ValueError('Pearson does not yet support sparse matrices.')

    if X is Y:
        X = Y = np.asanyarray(X)
    else:
        X = np.asanyarray(X)
        Y = np.asanyarray(Y)

    if X.shape[1] != Y.shape[1]:
        raise ValueError("Incompatible dimension for X and Y matrices")

    XY = ssd.cdist(X, Y, 'correlation')

    return 1 - XY


def adjusted_cosine(X, Y, E):
    """
    For item based recommender systems, the basic cosine measure and Pearson correlation measure does not take the
    differences in the average rating behavior of the users into account. Some users tend to be too harsh while others
    tend to do be too soft. This behaviour, known as "grade inflation", is solved by using the adjusted cosine measure,
    which subtracts the user average from the item vector of ratings. The values for the adjusted cosine
    measure correspondingly range from −1 to +1, as in the Pearson measure. The adjusted cosine distance is obtained
    adding 1 to the measure value.

    This formula is from a seminal article in collaborative filtering: "Item-based collaborative filtering
    recommendation algorithms" by Badrul Sarwar, George Karypis, Joseph Konstan, and John Reidl
    (http://www.grouplens.org/papers/pdf/www10_sarwar.pdf)

    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors after normalize or adjust
    the vector using the EFV vector. EFV vector contains expected value for
    each feature from vectors X and Y, i.e., the mean of the values
    of each feature vector from X and Y.

    Parameters
    ----------
    X : {array-like, sparse matrix}, shape = [n_samples_1, n_features]

    Y : {array-like, sparse matrix}, shape = [n_samples_2, n_features]

    E: {array-like, sparse matrix}, shape = [n_samples_3, n_features]

    Returns
    -------
    distances : {array, sparse matrix}, shape = [n_samples_1, n_samples_2]

    Examples
    --------
    >>> from crab.metrics.pairwise import adjusted_cosine
    >>> # This example comes from the book "A programmer's Guide To Data Mining" by Ron Zacharski, chapter 3, pag 17.
    >>> # Copy online at: http://guidetodatamining.com/guide/ch3/DataMining-ch3.pdf
    >>> X = [[1.0, 5.0, 4.0]]
    >>> Y = [[2.0, 5.0, 5.0]]
    >>> # Vector of expected values of the features (user ratings in item based context)
    >>> E = [[3.0, 3.5, 4.0]]
    >>> # distance between rows of X adjusted by the rows of E
    >>> adjusted_cosine(X, X, E)
    array([[ 1.]])
    >>> # distance between rows of X and Y adjusted by the rows of E
    >>> adjusted_cosine(X, Y, E)
    array([[ 0.82462113]])
    """

    X, Y = check_pairwise_arrays(X, Y)
    #TODO: fix next line
    E, _ = check_pairwise_arrays(E, None)

    # should not need X_norm_squared because if you could precompute that as
    # well as Y, then you should just pre-compute the output and not even
    # call this function.

    #TODO: Fix to work with sparse matrices.
    if issparse(X) or issparse(Y) or issparse(E):
        raise ValueError('Adjusted cosine does not yet support sparse matrices.')

    if X is Y:
        X = Y = np.asanyarray(X)
    else:
        X = np.asanyarray(X)
        Y = np.asanyarray(Y)

    if X.shape[1] != Y.shape[1] != E.shape[1]:
        raise ValueError("Incompatible dimension for X, Y and EFV matrices")

    X = X - E
    Y = Y - E

    XY = 1 - ssd.cdist(X, Y, 'cosine')

    return XY


def jaccard_coefficient(X, Y):
    """
    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors.

    This correlation implementation is a statistic used for comparing the
    similarity and diversity of sample sets.
    The Jaccard coefficient measures similarity between sample sets,
    and is defined as the size of the intersection divided by the size of the
    union of the sample sets.

    Parameters
    ----------
    X: array of shape (n_samples_1, n_features)

    Y: array of shape (n_samples_2, n_features)

    Returns
    -------
    distances: array of shape (n_samples_1, n_samples_2)

    Examples
    --------
    >>> from crab.metrics.pairwise import jaccard_coefficient
    >>> X = [['a', 'b', 'c', 'd'],['e', 'f','g']]
    >>> # distance between rows of X
    >>> jaccard_coefficient(X, X)
    array([[ 1.,  0.],
           [ 0.,  1.]])

    >>> jaccard_coefficient(X, [['a', 'b', 'c', 'k']])
    array([[ 0.6],
           [ 0. ]])
    """

    X = safe_asarray(X)
    Y = safe_asarray(Y)

    #TODO: Fix to work with sparse matrices.
    if issparse(X) or issparse(Y):
        raise ValueError('Jaccard does not yet support sparse matrices.')

    #TODO: Check if it is possible to optimize this function
    sX = X.shape[0]
    sY = Y.shape[0]
    dm = np.zeros((sX, sY))
    for i in xrange(0, sX):
        for j in xrange(0, sY):
            sx = set(X[i])
            sy = set(Y[j])
            n_XY = len(sx & sy)
            d_XY = len(sx | sy)
            dm[i, j] = n_XY / float(d_XY)
    return dm


def tanimoto_coefficient(X, Y):
    """
    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors.

    An implementation of a "similarity" based on the Tanimoto coefficient,
    or extended Jaccard coefficient.

    This is intended for "binary" data sets where a user either expresses a
    generic "yes" preference for an item or has no preference. The actual
    preference values do not matter here, only their presence or absence.

    Parameters
    ----------
    X: array of shape n_samples_1

    Y: array of shape n_samples_2

    Returns
    -------
    distances: array of shape (n_samples_1, n_samples_2)

    Examples
    --------
    >>> from crab.metrics.pairwise  import tanimoto_coefficient
    >>> X =  [['a', 'b', 'c', 'd'],['e', 'f','g']]
    >>> # distance between rows of X
    >>> tanimoto_coefficient(X, X)
    array([[ 1.,  0.],
           [ 0.,  1.]])
    >>> tanimoto_coefficient(X, [['a', 'b', 'c', 'k']])
    array([[ 0.6],
           [ 0. ]])

    """
    return jaccard_coefficient(X, Y)


def cosine_distances(X, Y):
    """
    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors.

     An implementation of the cosine similarity. The result is the cosine of
     the angle formed between the two preference vectors.
     Note that this similarity does not "center" its data, shifts the user's
     preference values so that each of their means is 0. For this behavior,
     use Pearson Coefficient, which actually is mathematically
     equivalent for centered data.

    Parameters
    ----------
    X: array of shape (n_samples_1, n_features)

    Y: array of shape (n_samples_2, n_features)

    Returns
    -------
    distances: array of shape (n_samples_1, n_samples_2)

    Examples
    --------
    >>> from crab.metrics.pairwise  import cosine_distances
    >>> X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0],[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    >>> # distance between rows of X
    >>> cosine_distances(X, X)
    array([[ 1.,  1.],
          [ 1.,  1.]])
    >>> cosine_distances(X, [[3.0, 3.5, 1.5, 5.0, 3.5,3.0]])
    array([[ 0.9606463],
           [ 0.9606463]])

    """
    X, Y = check_pairwise_arrays(X, Y)

    #TODO: Fix to work with sparse matrices.
    if issparse(X) or issparse(Y):
        raise ValueError('Cosine does not yet support sparse matrices.')

    return 1. - ssd.cdist(X, Y, 'cosine')


def sorensen_coefficient(X, Y):
    """
    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors.

    The Sørensen index, also known as Sørensen’s similarity coefficient,
    is a statistic used for comparing the similarity of two samples.
    It was developed by the botanist Thorvald Sørensen and published in 1948.
    [1]
    See the link:http://en.wikipedia.org/wiki/S%C3%B8rensen_similarity_index

    This is intended for "binary" data sets where a user either expresses a
    generic "yes" preference for an item or has no preference. The actual
    preference values do not matter here, only their presence or absence.

    Parameters
    ----------
    X: array of shape (n_samples_1, n_features)

    Y: array of shape (n_samples_2, n_features)

    Returns
    -------
    distances: array of shape (n_samples_1, n_samples_2)

    Examples
    --------
    >>> from crab.metrics.pairwise import sorensen_coefficient
    >>> X = [['a', 'b', 'c', 'd'],['e', 'f','g']]
    >>> # distance between rows of X
    >>> sorensen_coefficient(X, X)
    array([[ 1.,  0.],
          [ 0.,  1.]])
    >>> sorensen_coefficient(X, [['a', 'b', 'c', 'k']])
    array([[ 0.75], [ 0.  ]])

    """
    # should not need X_norm_squared because if you could precompute that as
    # well as Y, then you should just pre-compute the output and not even
    # call this function.
    if X is Y:
        X = Y = np.asanyarray(X)
    else:
        X = np.asanyarray(X)
        Y = np.asanyarray(Y)

    sX = X.shape[0]
    sY = Y.shape[0]
    dm = np.zeros((sX, sY))

    #TODO: Check if it is possible to optimize this function
    for i in xrange(0, sX):
        for j in xrange(0, sY):
            sx = set(X[i])
            sy = set(Y[j])
            n_XY = len(sx & sy)
            dm[i, j] = (2.0 * n_XY) / (len(X[i]) + len(Y[j]))

    return dm


def _spearman_r(X, Y):
    """
    Calculates a Spearman rank-order correlation coefficient
    and the p-value to test for non-correlation.
    """
    rho, p_value = spearman(X, Y)
    return rho


def spearman_coefficient(X, Y):
    """
    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors.

    Like  Pearson Coefficient , but compares relative ranking of preference
    values instead of preference values themselves. That is, each user's
    preferences are sorted and then assign a rank as their preference value,
    with 1 being assigned to the least preferred item.

    Parameters
    ----------
    X: array of shape (n_samples_1, n_features)

    Y: array of shape (n_samples_2, n_features)

    Returns
    -------
    distances: array of shape (n_samples_1, n_samples_2)

    Examples
    --------
    >>> from crab.metrics.pairwise  import spearman_coefficient
    >>> X = [[('a',2.5),('b', 3.5), ('c',3.0), ('d',3.5)], \
            [('e', 2.5),('f', 3.0), ('g', 2.5), ('h', 4.0)] ]
    >>> # distance between rows of X
    >>> spearman_coefficient(X, X)
    array([[ 1.,  0.],
           [ 0.,  1.]])
    >>> spearman_coefficient(X, [[('a',2.5),('b', 3.5), ('c',3.0), ('k',3.5)]])
    array([[ 1.],
           [ 0.]])
    """
    # should not need X_norm_squared because if you could precompute that as
    # well as Y, then you should just pre-compute the output and not even
    # call this function.
    if X is Y:
        X = Y = np.asanyarray(X, dtype=[('x', 'S30'), ('y', float)])
    else:
        X = np.asanyarray(X, dtype=[('x', 'S30'), ('y', float)])
        Y = np.asanyarray(Y, dtype=[('x', 'S30'), ('y', float)])

    if X.shape[1] != Y.shape[1]:
        raise ValueError("Incompatible dimension for X and Y matrices")

    X.sort(order='y')
    Y.sort(order='y')

    result = []

    #TODO: Check if it is possible to optimize this function
    i = 0
    for arrayX in X:
        result.append([])
        for arrayY in Y:
            Y_keys = [key for key, value in arrayY]

            XY = [(key, value) for key, value in arrayX if key in Y_keys]

            sumDiffSq = 0.0
            for index, tup in enumerate(XY):
                sumDiffSq += pow((index + 1) - (Y_keys.index(tup[0]) + 1), 2.0)

            n = len(XY)
            if n == 0:
                result[i].append(0.0)
            else:
                result[i].append(1.0 - ((6.0 * sumDiffSq) / (n * (n * n - 1))))
        result[i] = np.asanyarray(result[i])
        i += 1

    return np.asanyarray(result)


def loglikehood_coefficient(n_items, X, Y):
    """
    Considering the rows of X (and Y=X) as vectors, compute the
    distance matrix between each pair of vectors.

    Parameters
    ----------
    n_items: int
        Number of items in the model.

    X: array of shape (n_samples_1, n_features)

    Y: array of shape (n_samples_2, n_features)

    Returns
    -------
    distances: array of shape (n_samples_1, n_samples_2)

    Examples
    --------
    >>> from crab.metrics.pairwise import loglikehood_coefficient
    >>> X = [['a', 'b', 'c', 'd'],  ['e', 'f','g', 'h']]
    >>> # distance between rows of X
    >>> n_items = 7
    >>> loglikehood_coefficient(n_items,X, X)
    array([[ 1.,  0.],
          [ 0.,  1.]])
    >>> n_items = 8
    >>> loglikehood_coefficient(n_items, X, [['a', 'b', 'c', 'k']])
    array([[ 0.67668852],
          [ 0.        ]])


    References
    ----------
    See http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.14.5962 and
    http://tdunning.blogspot.com/2008/03/surprise-and-coincidence.html.
    """
    # should not need X_norm_squared because if you could precompute that as
    # well as Y, then you should just pre-compute the output and not even
    # call this function.

    def safeLog(d):
        if d <= 0.0:
            return 0.0
        else:
            return np.log(d)

    def logL(p, k, n):
        return k * safeLog(p) + (n - k) * safeLog(1.0 - p)

    def twoLogLambda(k1, k2, n1, n2):
        p = (k1 + k2) / (n1 + n2)
        return 2.0 * (logL(k1 / n1, k1, n1) + logL(k2 / n2, k2, n2)
                      - logL(p, k1, n1) - logL(p, k2, n2))

    if X is Y:
        X = Y = np.asanyarray(X)
    else:
        X = np.asanyarray(X)
        Y = np.asanyarray(Y)

    result = []

    # TODO: Check if it is possible to optimize this function

    i = 0
    for arrayX in X:
        result.append([])
        for arrayY in Y:
            XY = np.intersect1d(arrayX, arrayY)

            if XY.size == 0:
                result[i].append(0.0)
            else:
                nX = arrayX.size
                nY = arrayY.size
                if (nX - XY.size == 0) or (n_items - nY) == 0:
                    result[i].append(1.0)
                else:
                    logLikelihood = twoLogLambda(float(XY.size),
                                                 float(nX - XY.size),
                                                 float(nY),
                                                 float(n_items - nY))

                    result[i].append(1.0 - 1.0 / (1.0 + float(logLikelihood)))
        result[i] = np.asanyarray(result[i])
        i += 1

    return np.asanyarray(result)

########NEW FILE########
__FILENAME__ = test_pairwise
import numpy as np
from ..pairwise import check_pairwise_arrays
from nose.tools import assert_true
from numpy.testing import assert_equal
from numpy.testing import assert_array_almost_equal
from nose.tools import assert_raises
from scipy.sparse import csr_matrix

from ..pairwise import euclidean_distances, manhattan_distances
from ..pairwise import pearson_correlation, jaccard_coefficient
from ..pairwise import tanimoto_coefficient, cosine_distances
from ..pairwise import loglikehood_coefficient, sorensen_coefficient
from ..pairwise import spearman_coefficient, adjusted_cosine


def test_check_dense_matrices():
    """ Ensure that pairwise array check works for dense matrices."""
    # Check that if XB is None, XB is returned as reference to XA
    XA = np.resize(np.arange(40), (5, 8))
    XA_checked, XB_checked = check_pairwise_arrays(XA, None)
    assert_true(XA_checked is XB_checked)
    assert_equal(XA, XA_checked)


def test_check_XB_returned():
    """ Ensure that if XA and XB are given correctly, they return as equal."""
    # Check that if XB is not None, it is returned equal.
    # Note that the second dimension of XB is the same as XA.
    XA = np.resize(np.arange(40), (5, 8))
    XB = np.resize(np.arange(32), (4, 8))
    XA_checked, XB_checked = check_pairwise_arrays(XA, XB)
    assert_equal(XA, XA_checked)
    assert_equal(XB, XB_checked)


def test_check_different_dimensions():
    """ Ensure an error is raised if the dimensions are different. """
    XA = np.resize(np.arange(45), (5, 9))
    XB = np.resize(np.arange(32), (4, 8))
    assert_raises(ValueError, check_pairwise_arrays, XA, XB)


def test_check_invalid_dimensions():
    """ Ensure an error is raised on 1D input arrays. """
    XA = np.arange(45)
    XB = np.resize(np.arange(32), (4, 8))
    assert_raises(ValueError, check_pairwise_arrays, XA, XB)
    XA = np.resize(np.arange(45), (5, 9))
    XB = np.arange(32)
    assert_raises(ValueError, check_pairwise_arrays, XA, XB)


def test_check_sparse_arrays():
    """ Ensures that checks return valid sparse matrices. """
    rng = np.random.RandomState(0)
    XA = rng.random_sample((5, 4))
    XA_sparse = csr_matrix(XA)
    XB = rng.random_sample((5, 4))
    XB_sparse = csr_matrix(XB)
    XA_checked, XB_checked = check_pairwise_arrays(XA_sparse, XB_sparse)
    assert_equal(XA_sparse, XA_checked)
    assert_equal(XB_sparse, XB_checked)


def tuplify(X):
    """ Turns a numpy matrix (any n-dimensional array) into tuples."""
    s = X.shape
    if len(s) > 1:
        # Tuplify each sub-array in the input.
        return tuple(tuplify(row) for row in X)
    else:
        # Single dimension input, just return tuple of contents.
        return tuple(r for r in X)


def test_check_tuple_input():
    """ Ensures that checks return valid tuples. """
    rng = np.random.RandomState(0)
    XA = rng.random_sample((5, 4))
    XA_tuples = tuplify(XA)
    XB = rng.random_sample((5, 4))
    XB_tuples = tuplify(XB)
    XA_checked, XB_checked = check_pairwise_arrays(XA_tuples, XB_tuples)
    assert_equal(XA_tuples, XA_checked)
    assert_equal(XB_tuples, XB_checked)


def test_euclidean_distances():
    """Check that the pairwise euclidian distances computation"""
    #Idepontent Test
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = euclidean_distances(X, X)
    assert_array_almost_equal(D, [[0.]])

    X = [[3.0, -2.0]]
    D = euclidean_distances(X, X, inverse=True)
    assert_array_almost_equal(D, [[1.]])

    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = euclidean_distances(X, X, inverse=False)
    assert_array_almost_equal(D, [[0.]])

    #Inverse Test
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = euclidean_distances(X, X, inverse=True)
    assert_array_almost_equal(D, [[1.]])

    #Vector x Non Vector
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[]]
    assert_raises(ValueError, euclidean_distances, X, Y)

    #Vector A x Vector B
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = euclidean_distances(X, Y)
    assert_array_almost_equal(D, [[2.39791576]])

    #Inverse vector (mahout check)
    X = [[3.0, -2.0]]
    Y = [[-3.0, 2.0]]
    D = euclidean_distances(X, Y, inverse=True)
    assert_array_almost_equal(D, [[0.13736056]])

    #Inverse vector (oreilly check)
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = euclidean_distances(X, Y, inverse=True, squared=True)
    assert_array_almost_equal(D, [[0.14814815]])

    #Vector N x 1
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = euclidean_distances(X, Y)
    assert_array_almost_equal(D, [[2.39791576], [2.39791576]])

    #N-Dimmensional Vectors
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = euclidean_distances(X, Y)
    assert_array_almost_equal(D, [[2.39791576, 0.], [2.39791576, 0.]])

    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = euclidean_distances(X, X)
    assert_array_almost_equal(D, [[0., 2.39791576], [2.39791576, 0.]])

    X = [[1.0, 0.0], [1.0, 1.0]]
    Y = [[0.0, 0.0]]
    D = euclidean_distances(X, Y)
    assert_array_almost_equal(D, [[1.], [1.41421356]])

    #Test Sparse Matrices
    X = csr_matrix(X)
    Y = csr_matrix(Y)
    D = euclidean_distances(X, Y)
    assert_array_almost_equal(D, [[1.], [1.41421356]])


def test_manhattan_distances():
    """ Check that the pairwise Manhattan distances computation"""
    #Idepontent Test
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = manhattan_distances(X, X)
    assert_array_almost_equal(D, [[1.]])

    #Vector x Non Vector
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[]]
    assert_raises(ValueError, manhattan_distances, X, Y)

    #Vector A x Vector B
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = manhattan_distances(X, Y)
    assert_array_almost_equal(D, [[0.25]])

    #BUG FIX: How to fix for multi-dimm arrays

    #Vector N x 1
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = manhattan_distances(X, Y)
    assert_array_almost_equal(D, [[0.25], [0.25]])

    #N-Dimmensional Vectors
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = manhattan_distances(X, Y)
    assert_array_almost_equal(D, [[1., 1.], [1., 1.]])

    X = [[0, 1], [1, 1]]
    D = manhattan_distances(X, X)
    assert_array_almost_equal(D, [[1., 0.5], [0.5, 1.]])

    X = [[0, 1], [1, 1]]
    Y = [[0, 0]]
    D = manhattan_distances(X, Y)
    assert_array_almost_equal(D, [[0.5], [0.]])

    #Test Sparse Matrices
    X = csr_matrix(X)
    Y = csr_matrix(Y)
    assert_raises(ValueError, manhattan_distances, X, Y)


def test_pearson_correlation():
    """ Check that the pairwise Pearson distances computation"""
    #Idepontent Test
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = pearson_correlation(X, X)
    assert_array_almost_equal(D, [[1.]])

    #Vector x Non Vector
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[]]
    assert_raises(ValueError, pearson_correlation, X, Y)

    #Vector A x Vector B
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = pearson_correlation(X, Y)
    assert_array_almost_equal(D, [[0.3960590]])

    #Vector N x 1
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = pearson_correlation(X, Y)
    assert_array_almost_equal(D, [[0.3960590], [0.3960590]])

    #N-Dimmensional Vectors
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = pearson_correlation(X, Y)
    assert_array_almost_equal(D, [[0.3960590, 1.], [0.3960590, 1.]])

    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = pearson_correlation(X, X)
    assert_array_almost_equal(D, [[1., 0.39605902], [0.39605902, 1.]])

    X = [[1.0, 0.0], [1.0, 1.0]]
    Y = [[0.0, 0.0]]
    D = pearson_correlation(X, Y)
    assert_array_almost_equal(D, [[np.nan], [np.nan]])

    #Test Sparse Matrices
    X = csr_matrix(X)
    Y = csr_matrix(Y)
    assert_raises(ValueError, pearson_correlation, X, Y)


def test_adjusted_cosine():
    """ Check that the pairwise Pearson distances computation"""
    #Idepontent Test
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    EFV = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
    D = adjusted_cosine(X, X, EFV)
    assert_array_almost_equal(D, [[1.]])

    #Vector x Non Vector
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[]]
    EFV = [[]]
    assert_raises(ValueError, adjusted_cosine, X, Y, EFV)

    #Vector A x Vector B
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    EFV = [[2.0, 2.0, 2.0, 2.0, 2.0, 2.0]]
    D = adjusted_cosine(X, Y, EFV)
    assert_array_almost_equal(D, [[0.80952381]])

    #Vector N x 1
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    EFV = [[2.0, 2.0, 2.0, 2.0, 2.0, 2.0]]
    D = adjusted_cosine(X, Y, EFV)
    assert_array_almost_equal(D, [[0.80952381], [0.80952381]])

    #N-Dimmensional Vectors
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    EFV = [[2.0, 2.0, 2.0, 2.0, 2.0, 2.0]]
    D = adjusted_cosine(X, Y, EFV)
    assert_array_almost_equal(D, [[0.80952381, 1.], [0.80952381, 1.]])

    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    EFV = [[2.0, 2.0, 2.0, 2.0, 2.0, 2.0]]
    D = adjusted_cosine(X, X, EFV)
    assert_array_almost_equal(D, [[1., 0.80952381], [0.80952381, 1.]])

    X = [[1.0, 0.0], [1.0, 1.0]]
    Y = [[0.0, 0.0]]
    EFV = [[0.0, 0.0]]
    D = adjusted_cosine(X, Y, EFV)
    assert_array_almost_equal(D, [[np.nan], [np.nan]])

    #Test Sparse Matrices
    X = csr_matrix(X)
    Y = csr_matrix(Y)
    EFV = csr_matrix(EFV)
    assert_raises(ValueError, adjusted_cosine, X, Y, EFV)


def test_jaccard_distances():
    """ Check that the pairwise Jaccard distances computation"""
    #Idepontent Test
    X = [['a', 'b', 'c']]
    D = jaccard_coefficient(X, X)
    assert_array_almost_equal(D, [[1.]])

    #Vector x Non Vector
    X = [['a', 'b', 'c']]
    Y = [[]]
    D = jaccard_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.]])

    #Vector A x Vector B
    X = [[1, 2, 3, 4]]
    Y = [[2, 3]]
    D = jaccard_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.5]])

    #BUG FIX: How to fix for multi-dimm arrays

    #Vector N x 1
    X = [['a', 'b', 'c', 'd'], ['e', 'f', 'g']]
    Y = [['a', 'b', 'c', 'k']]
    D = jaccard_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.6], [0.]])

    #N-Dimmensional Vectors
    X = [['a', 'b', 'c', 'd'], ['e', 'f', 'g']]
    Y = [['a', 'b', 'c', 'd'], ['e', 'f', 'g']]
    D = jaccard_coefficient(X, Y)
    assert_array_almost_equal(D, [[1., 0.], [0., 1.]])

    X = [[0, 1], [1, 2]]
    D = jaccard_coefficient(X, X)
    assert_array_almost_equal(D, [[1., 0.33333333], [0.33333333, 1.]])

    X = [[0, 1], [1, 2]]
    Y = [[0, 3]]
    D = jaccard_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.33333333], [0.]])

    #Test Sparse Matrices
    X = csr_matrix(X)
    Y = csr_matrix(Y)
    assert_raises(ValueError, jaccard_coefficient, X, Y)


def test_tanimoto_distances():
    """ Check that the pairwise Tanimoto distances computation"""
    #Idepontent Test
    X = [['a', 'b', 'c']]
    D = tanimoto_coefficient(X, X)
    assert_array_almost_equal(D, [[1.]])

    #Vector x Non Vector
    X = [['a', 'b', 'c']]
    Y = [[]]
    D = tanimoto_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.]])

    #Vector A x Vector B
    X = [[1, 2, 3, 4]]
    Y = [[2, 3]]
    D = tanimoto_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.5]])

    #BUG FIX: How to fix for multi-dimm arrays

    #Vector N x 1
    X = [['a', 'b', 'c', 'd'], ['e', 'f', 'g']]
    Y = [['a', 'b', 'c', 'k']]
    D = tanimoto_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.6], [0.]])

    #N-Dimmensional Vectors
    X = [['a', 'b', 'c', 'd'], ['e', 'f', 'g']]
    Y = [['a', 'b', 'c', 'd'], ['e', 'f', 'g']]
    D = tanimoto_coefficient(X, Y)
    assert_array_almost_equal(D, [[1., 0.], [0., 1.]])

    X = [[0, 1], [1, 2]]
    D = tanimoto_coefficient(X, X)
    assert_array_almost_equal(D, [[1., 0.33333333], [0.33333333, 1.]])

    X = [[0, 1], [1, 2]]
    Y = [[0, 3]]
    D = tanimoto_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.3333333], [0.]])

    #Test Sparse Matrices
    X = csr_matrix(X)
    Y = csr_matrix(Y)
    assert_raises(ValueError, tanimoto_coefficient, X, Y)


def test_cosine_distances():
    """ Check that the pairwise Cosine distances computation"""
    #Idepontent Test
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = cosine_distances(X, X)
    assert_array_almost_equal(D, [[1.]])
    #Vector x Non Vector
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[]]
    assert_raises(ValueError, cosine_distances, X, Y)
    #Vector A x Vector B
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = cosine_distances(X, Y)
    assert_array_almost_equal(D, [[0.960646301]])
    #Vector N x 1
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0]]
    D = cosine_distances(X, Y)
    assert_array_almost_equal(D, [[0.960646301], [0.960646301]])

    #N-Dimmensional Vectors
    X = [[2.5, 3.5, 3.0, 3.5, 2.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    Y = [[3.0, 3.5, 1.5, 5.0, 3.5, 3.0], [2.5, 3.5, 3.0, 3.5, 2.5, 3.0]]
    D = cosine_distances(X, Y)
    assert_array_almost_equal(D, [[0.960646301, 1.], [0.960646301, 1.]])

    X = [[0, 1], [1, 1]]
    D = cosine_distances(X, X)
    assert_array_almost_equal(D, [[1., 0.70710678], [0.70710678, 1.]])

    X = [[0, 1], [1, 1]]
    Y = [[0, 0]]
    D = cosine_distances(X, Y)
    assert_array_almost_equal(D, [[np.nan], [np.nan]])

    #Test Sparse Matrices
    X = csr_matrix(X)
    Y = csr_matrix(Y)
    assert_raises(ValueError, cosine_distances, X, Y)


def test_loglikehood_distances():
    """ Check that the pairwise LogLikehood distances computation"""
    #Idepontent Test
    X = [['a', 'b', 'c']]
    n_items = 3
    D = loglikehood_coefficient(n_items, X, X)
    assert_array_almost_equal(D, [[1.]])

    #Vector x Non Vector
    X = [['a', 'b', 'c']]
    Y = [[]]
    n_items = 3
    D = loglikehood_coefficient(n_items, X, Y)
    assert_array_almost_equal(D, [[0.]])

    #Vector A x Vector B
    X = [[1, 2, 3, 4]]
    Y = [[2, 3]]
    n_items = 4
    D = loglikehood_coefficient(n_items, X, Y)
    assert_array_almost_equal(D, [[0.]])

    #BUG FIX: How to fix for multi-dimm arrays

    #Vector N x 1
    X = [['a', 'b', 'c', 'd'], ['e', 'f', 'g', 'h']]
    Y = [['a', 'b', 'c', 'k']]
    n_items = 8
    D = loglikehood_coefficient(n_items, X, Y)
    assert_array_almost_equal(D, [[0.67668852], [0.]])

    #N-Dimmensional Vectors
    X = [['a', 'b', 'c', 'd'], ['e', 'f', 'g', 'h']]
    Y = [['a', 'b', 'c', 'd'], ['e', 'f', 'g', 'h']]
    n_items = 7
    D = loglikehood_coefficient(n_items, X, Y)
    assert_array_almost_equal(D, [[1., 0.], [0., 1.]])


def test_sorensen_distances():
    """ Check that the pairwise Sorensen distances computation"""
    #Idepontent Test
    X = [['a', 'b', 'c']]
    D = sorensen_coefficient(X, X)
    assert_array_almost_equal(D, [[1.]])

    #Vector x Non Vector
    X = [['a', 'b', 'c']]
    Y = [[]]
    D = sorensen_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.]])

    #Vector A x Vector B
    X = [[1, 2, 3, 4]]
    Y = [[2, 3]]
    D = sorensen_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.666666]])

    #BUG FIX: How to fix for multi-dimm arrays

    #Vector N x 1
    X = [['a', 'b', 'c', 'd'], ['e', 'f', 'g']]
    Y = [['a', 'b', 'c', 'k']]
    D = sorensen_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.75], [0.]])

    #N-Dimmensional Vectors
    X = [['a', 'b', 'c', 'd'], ['e', 'f', 'g']]
    Y = [['a', 'b', 'c', 'd'], ['e', 'f', 'g']]
    D = sorensen_coefficient(X, Y)
    assert_array_almost_equal(D, [[1., 0.], [0., 1.]])

    X = [[0, 1], [1, 2]]
    D = sorensen_coefficient(X, X)
    assert_array_almost_equal(D, [[1., 0.5], [0.5, 1.]])

    X = [[0, 1], [1, 2]]
    Y = [[0, 0]]
    D = sorensen_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.5], [0.]])


def test_spearman_distances():
    """ Check that the pairwise Spearman distances computation"""
    #Idepontent Test
    X = [[('a', 2.5), ('b', 3.5), ('c', 3.0), ('d', 3.5),
          ('e', 2.5), ('f', 3.0)]]
    D = spearman_coefficient(X, X)
    assert_array_almost_equal(D, [[1.]])

    #Vector x Non Vector
    X = [[('a', 2.5), ('b', 3.5), ('c', 3.0), ('d', 3.5),
          ('e', 2.5), ('f', 3.0)]]
    Y = [[]]
    assert_raises(ValueError, spearman_coefficient, X, Y)

    #Vector A x Vector B
    X = [[('a', 2.5), ('b', 3.5), ('c', 3.0), ('d', 3.5),
          ('e', 2.5), ('f', 3.0)]]
    Y = [[('a', 3.0), ('b', 3.5), ('c', 1.5), ('d', 5.0),
          ('e', 3.5), ('f', 3.0)]]
    D = spearman_coefficient(X, Y)
    assert_array_almost_equal(D, [[0.5428571428]])

    #Vector N x 1
    X = [[('a', 2.5), ('b', 3.5), ('c', 3.0), ('d', 3.5)],
         [('e', 2.5), ('f', 3.0), ('g', 2.5), ('h', 4.0)]]
    Y = [[('a', 2.5), ('b', 3.5), ('c', 3.0), ('k', 3.5)]]
    D = spearman_coefficient(X, Y)
    assert_array_almost_equal(D, [[1.], [0.]])

    #N-Dimmensional Vectors
    X = [[('a', 2.5), ('b', 3.5), ('c', 3.0), ('d', 3.5)],
         [('e', 2.5), ('f', 3.0), ('g', 2.5), ('h', 4.0)]]
    Y = [[('a', 2.5), ('b', 3.5), ('c', 3.0), ('d', 3.5)],
         [('e', 2.5), ('f', 3.0), ('g', 2.5), ('h', 4.0)]]
    D = spearman_coefficient(X, Y)
    assert_array_almost_equal(D, [[1., 0.], [0., 1.]])

########NEW FILE########
__FILENAME__ = test_base

# Author: Marcel Caraciolo
# License: BSD

from numpy.testing import assert_equal
from nose.tools import assert_true
from nose.tools import assert_raises

from crab.base import BaseRecommender


#############################################################################
# A few test classes
class MyRecommender(BaseRecommender):

    def __init__(self, model=None, with_preference=False):
        self.model = model
        self.with_preference = with_preference


class KRecommender(BaseRecommender):
    def __init__(self, c=None, d=None):
        self.c = c
        self.d = d


class TRecommender(BaseRecommender):
    def __init__(self, a=None, b=None):
        self.a = a
        self.b = b


class BuggyRecommender(BaseRecommender):
    " A buggy recommender that does not set its parameters right. "

    def __init__(self, a=None):
        self.a = 1


class NoRecommender(object):
    def __init__(self):
        pass

    def estimate_preference(self, user_id, item_id, **params):
        return self

    def recommend(self, user_id, how_many, **params):
        return None


class VargRecommender(BaseRecommender):
    """Crab recommenders shouldn't have vargs."""
    def __init__(self, *vargs):
        pass


def test_repr():
    """Smoke test the repr of the base estimator."""
    my_recommender = MyRecommender()
    repr(my_recommender)
    test = TRecommender(KRecommender(), KRecommender())
    assert_equal(
        repr(test),
        "TRecommender(a=KRecommender(c=None, d=None), " +
         "b=KRecommender(c=None, d=None))"
    )

    some_est = TRecommender(a=["long_params"] * 1000)
    assert_equal(len(repr(some_est)), 432)


def test_str():
    """Smoke test the str of the base estimator"""
    my_estimator = MyRecommender()
    str(my_estimator)


def test_get_params():
    test = TRecommender(KRecommender(), KRecommender())

    assert_true('a__d' in test.get_params(deep=True))
    assert_true('a__d' not in test.get_params(deep=False))

    test.set_params(a__d=2)
    assert_true(test.a.d == 2)
    assert_raises(ValueError, test.set_params, a__a=2)

########NEW FILE########
__FILENAME__ = extmath
"""
Extended math utilities.
"""
# Authors: Marcel Caraciolo
# License: BSD

import numpy as np


def safe_sparse_dot(a, b, dense_output=False):
    """Dot product that handle the sparse matrix case correctly"""
    from scipy import sparse
    if sparse.issparse(a) or sparse.issparse(b):
        ret = a * b
        if dense_output and hasattr(ret, "toarray"):
            ret = ret.toarray()
        return ret
    else:
        return np.dot(a, b)

########NEW FILE########
__FILENAME__ = fixes
"""Compatibility fixes for older version of python, numpy and scipy

If you add content to this file, please give the version of the package
at which the fix is no longer needed.
"""
# Authors: Marcel Caraciolo <marcel@pingmind.com>
# License: BSD

import numpy as np
import inspect

# little danse to see if np.copy has an 'order' keyword argument
if 'order' in inspect.getargspec(np.copy)[0]:
    def safe_copy(X):
        # Copy, but keep the order
        return np.copy(X, order='K')
else:
    # Before an 'order' argument was introduced, numpy wouldn't muck with
    # the ordering
    safe_copy = np.copy

########NEW FILE########
__FILENAME__ = format
"""
Formatter utils.
"""
# Authors: Marcel Caraciolo
# License: BSD

import numpy as np


def _pprint(params, offset=0, printer=repr):
    """Pretty print the dictionary 'params'

    Parameters
    ----------
    params: dict
        The dictionary to pretty print

    offset: int
        The offset in characters to add at the begin of each line.

    printer:
        The function to convert entries to strings, typically
        the builtin str or repr

    """
    # Do a multi-line justified repr:
    options = np.get_printoptions()
    np.set_printoptions(precision=5, threshold=64, edgeitems=2)
    params_list = list()
    this_line_length = offset
    line_sep = ',\n' + (1 + offset // 2) * ' '
    for i, (k, v) in enumerate(sorted((params.iteritems()))):
        if type(v) is float:
            # use str for representing floating point numbers
            # this way we get consistent representation across
            # architectures and versions.
            this_repr = '%s=%s' % (k, str(v))
        else:
            # use repr of the rest
            this_repr = '%s=%s' % (k, printer(v))
        if len(this_repr) > 500:
            this_repr = this_repr[:300] + '...' + this_repr[-100:]
        if i > 0:
            if (this_line_length + len(this_repr) >= 75 or '\n' in this_repr):
                params_list.append(line_sep)
                this_line_length = len(line_sep)
            else:
                params_list.append(', ')
                this_line_length += 2
        params_list.append(this_repr)
        this_line_length += len(this_repr)

    np.set_printoptions(**options)
    lines = ''.join(params_list)
    # Strip trailing space to avoid nightmare in doctests
    lines = '\n'.join(l.rstrip(' ') for l in lines.split('\n'))
    return lines


########NEW FILE########
__FILENAME__ = test_validation
"""Tests for input validation functions"""
import numpy as np
from nose.tools import assert_false, assert_true
import scipy.sparse as sp

from crab.utils import atleast2d_or_csr, atleast2d_or_csc, safe_asarray


def test_np_matrix():
    """Confirm that input validation code does not return np.matrix"""
    X = np.arange(12).reshape(3, 4)

    assert_false(isinstance(atleast2d_or_csr(X), np.matrix))
    assert_false(isinstance(atleast2d_or_csr(np.matrix(X)), np.matrix))
    assert_false(isinstance(atleast2d_or_csr(sp.csc_matrix(X)), np.matrix))

    assert_false(isinstance(atleast2d_or_csc(X), np.matrix))
    assert_false(isinstance(atleast2d_or_csc(np.matrix(X)), np.matrix))
    assert_false(isinstance(atleast2d_or_csc(sp.csr_matrix(X)), np.matrix))

    assert_false(isinstance(safe_asarray(X), np.matrix))
    assert_false(isinstance(safe_asarray(np.matrix(X)), np.matrix))
    assert_false(isinstance(safe_asarray(sp.lil_matrix(X)), np.matrix))

    assert_true(atleast2d_or_csr(X, copy=False) is X)
    assert_false(atleast2d_or_csr(X, copy=True) is X)
    assert_true(atleast2d_or_csc(X, copy=False) is X)
    assert_false(atleast2d_or_csc(X, copy=True) is X)

########NEW FILE########
__FILENAME__ = validation
"""Utilities for input validation"""

# Taken from scikit-learn.
# Authors: Olivier Grisel
#          Gael Varoquaux
#          Andreas Mueller
#          Lars Buitinck


from scipy import sparse
import numpy as np
from .fixes import safe_copy


def _assert_all_finite(X):
    """Like assert_all_finite, but only for ndarray."""
    if X.dtype.char in np.typecodes['AllFloat'] and not np.isfinite(X.sum()) and not np.isfinite(X).all():
        raise ValueError("Array contains NaN or infinity.")


def assert_all_finite(X):
    """Throw a ValueError if X contains NaN or infinity.

    Input MUST be an np.ndarray instance or a scipy.sparse matrix."""

    # First try an O(n) time, O(1) space solution for the common case that
    # there everything is finite; fall back to O(n) space np.isfinite to
    # prevent false positives from overflow in sum method.
    _assert_all_finite(X.data if sparse.issparse(X) else X)


def safe_asarray(X, dtype=None, order=None):
    """Convert X to an array or sparse matrix.

    Prevents copying X when possible; sparse matrices are passed through."""
    if sparse.issparse(X):
        assert_all_finite(X.data)
    else:
        X = np.asarray(X, dtype, order)
        assert_all_finite(X)
    return X


def array2d(X, dtype=None, order=None, copy=False):
    """Returns at least 2-d array with data from X"""
    if sparse.issparse(X):
        raise TypeError('A sparse matrix was passed, but dense data '
                        'is required. Use X.toarray() to convert to dense.')
    X_2d = np.asarray(np.atleast_2d(X), dtype=dtype, order=order)
    _assert_all_finite(X_2d)
    if X is X_2d and copy:
        X_2d = safe_copy(X_2d)
    return X_2d


def _atleast2d_or_sparse(X, dtype, order, copy, sparse_class, convmethod):
    if sparse.issparse(X):
        # Note: order is ignored because CSR matrices hold data in 1-d arrays
        if dtype is None or X.dtype == dtype:
            X = getattr(X, convmethod)()
        else:
            X = sparse_class(X, dtype=dtype)
        _assert_all_finite(X.data)
    else:
        X = array2d(X, dtype=dtype, order=order, copy=copy)
        _assert_all_finite(X)
    return X


def atleast2d_or_csc(X, dtype=None, order=None, copy=False):
    """Like numpy.atleast_2d, but converts sparse matrices to CSC format.

    Also, converts np.matrix to np.ndarray.
    """
    return _atleast2d_or_sparse(X, dtype, order, copy, sparse.csc_matrix,
                                "tocsc")


def atleast2d_or_csr(X, dtype=None, order=None, copy=False):
    """Like numpy.atleast_2d, but converts sparse matrices to CSR format

    Also, converts np.matrix to np.ndarray.
    """
    return _atleast2d_or_sparse(X, dtype, order, copy, sparse.csr_matrix,
                                "tocsr")

########NEW FILE########
