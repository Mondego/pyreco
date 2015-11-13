__FILENAME__ = computesim
import numpy as np

from mrjob.job import MRJob
from itertools import combinations, permutations
from math import sqrt

from scipy.stats.stats import pearsonr

class RestaurantSimilarities(MRJob):

    def steps(self):
        thesteps = [
            self.mr(mapper=self.line_mapper, reducer=self.users_items_collector),
            self.mr(mapper=self.pair_items_mapper, reducer=self.calc_sim_collector)
        ]
        return thesteps

    def line_mapper(self,_,line):
        user_id,business_id,stars,business_avg,user_avg=line.split(',')
        yield user_id, (business_id,stars,business_avg,user_avg)

    def users_items_collector(self, user_id, values):
        ratings=[]
        for business_id,stars,business_avg,user_avg in values:
            ratings.append((business_id,(stars, user_avg)))
        yield user_id, ratings

    def pair_items_mapper(self, user_id, values):
        ratings = values
        for biz1tuple, biz2tuple in combinations(ratings, 2):
            biz1, biz1r=biz1tuple
            biz2, biz2r=biz2tuple
            if biz1 <= biz2 :
                yield (biz1, biz2), (biz1r, biz2r)
            else:
                yield (biz2, biz1), (biz2r, biz1r)

    def calc_sim_collector(self, key, values):
        (rest1, rest2), common_ratings = key, values
        diff1=[]
        diff2=[]
        n_common=0


        for rt1, rt2 in common_ratings:
            diff1.append(float(rt1[0])-float(rt1[1]))
            diff2.append(float(rt2[0])-float(rt2[1]))
            n_common=n_common+1
        if n_common==0:
            rho=0.
        else:
            rho=pearsonr(diff1, diff2)[0]
            if np.isnan(rho):
                rho=0.
        yield (rest1, rest2), (rho, n_common)


#Below MUST be there for things to work!
if __name__ == '__main__':
    RestaurantSimilarities.run()

########NEW FILE########
__FILENAME__ = computesim2
import numpy as np

from mrjob.job import MRJob
from itertools import combinations, permutations
from math import sqrt
import mrjob

from scipy.stats.stats import pearsonr

class RestaurantSimilarities(MRJob):

    def steps(self):
        thesteps = [
            self.mr(mapper=self.line_mapper, reducer=self.users_items_collector),
            self.mr(mapper=self.pair_items_mapper, reducer=self.calc_sim_collector),
            self.mr(mapper=self.ranking_mapper, reducer=self.top_similar_collector)
        ]
        return thesteps

    def line_mapper(self,_,line):
        user_id,business_id,stars,business_avg,user_avg=line.split(',')
        yield user_id, (business_id,stars,business_avg,user_avg)

    def users_items_collector(self, user_id, values):
        ratings=[]
        for business_id,stars,business_avg,user_avg in values:
            ratings.append((business_id,(stars, user_avg)))
        yield user_id, ratings

    def pair_items_mapper(self, user_id, values):
        ratings = values
        for biz1tuple, biz2tuple in combinations(ratings, 2):
            biz1, biz1r=biz1tuple
            biz2, biz2r=biz2tuple
            if biz1 <= biz2 :
                yield (biz1, biz2), (biz1r, biz2r)
            else:
                yield (biz2, biz1), (biz2r, biz1r)

    def calc_sim_collector(self, key, values):
        (rest1, rest2), common_ratings = key, values
        diff1=[]
        diff2=[]
        n_common=0


        for rt1, rt2 in common_ratings:
            diff1.append(float(rt1[0])-float(rt1[1]))
            diff2.append(float(rt2[0])-float(rt2[1]))
            n_common=n_common+1
        if n_common==0:
            rho=0.
        else:
            rho=pearsonr(diff1, diff2)[0]
            if np.isnan(rho):
                rho=0.
        yield (rest1, rest2), (rho, n_common)

    def ranking_mapper(self, restaurants, values):
        sim, n_common = values
        rest1, rest2 = restaurants
        if int(n_common) > 0:
            yield (rest1), (sim, rest2, n_common)

    def top_similar_collector(self, key, values):
        rest1 = key
        for sim, rest2, n_common in sorted(values, reverse=True):
            yield None, (rest1, rest2, sim, n_common)

#Below MUST be there for things to work!
if __name__ == '__main__':
    RestaurantSimilarities.run()

########NEW FILE########
__FILENAME__ = cs109style
from __future__ import print_function

from IPython.core.display import HTML
from matplotlib import rcParams

#colorbrewer2 Dark2 qualitative color table
dark2_colors = [(0.10588235294117647, 0.6196078431372549, 0.4666666666666667),
                (0.8509803921568627, 0.37254901960784315, 0.00784313725490196),
                (0.4588235294117647, 0.4392156862745098, 0.7019607843137254),
                (0.9058823529411765, 0.1607843137254902, 0.5411764705882353),
                (0.4, 0.6509803921568628, 0.11764705882352941),
                (0.9019607843137255, 0.6705882352941176, 0.00784313725490196),
                (0.6509803921568628, 0.4627450980392157, 0.11372549019607843),
                (0.4, 0.4, 0.4)]

def customize_mpl():
    """Tweak matplotlib visual style"""
    print("Setting custom matplotlib visual style")

    rcParams['figure.figsize'] = (10, 6)
    rcParams['figure.dpi'] = 150
    rcParams['axes.color_cycle'] = dark2_colors
    rcParams['lines.linewidth'] = 2
    rcParams['axes.grid'] = True
    rcParams['axes.facecolor'] = '#eeeeee'
    rcParams['font.size'] = 14
    rcParams['patch.edgecolor'] = 'none'


def customize_css():
    print("Setting custom CSS for the IPython Notebook")
    styles = open('custom.css', 'r').read()
    return HTML(styles)

########NEW FILE########
__FILENAME__ = query_bing_images
from bs4 import BeautifulSoup
import requests
import re
import urllib2
import os
import sys


def get_soup(url):
    return BeautifulSoup(requests.get(url).text)

query = sys.argv[1]
image_type = '_'.join(query.split())
print query, image_type
url = "http://www.bing.com/images/search?q=" + query + "&qft=+filterui:color2-bw+filterui:imagesize-large&FORM=R5IR3"

soup = get_soup(url)
images = [a['src'] for a in soup.find_all("img", {"src": re.compile("mm.bing.net")})]

for img in images:
    raw_img = urllib2.urlopen(img).read()
    cntr = len([i for i in os.listdir("images") if image_type in i]) + 1
    f = open("images/" + image_type + "_"+ str(cntr) + ".jpg", 'wb')
    f.write(raw_img)
    f.close()

########NEW FILE########
__FILENAME__ = _multivariate
#
# Author: Joris Vankerschaver 2013
#
from __future__ import division, print_function, absolute_import

from scipy.misc import doccer
from functools import wraps
import numpy as np
import scipy.linalg

__all__ = ['multivariate_normal']


_LOG_2PI = np.log(2 * np.pi)


def _process_parameters(dim, mean, cov):
    """
    Infer dimensionality from mean or covariance matrix, ensure that
    mean and covariance are full vector resp. matrix.

    """

    # Try to infer dimensionality
    if dim is None:
        if mean is None:
            if cov is None:
                dim = 1
            else:
                cov = np.asarray(cov, dtype=float)
                if cov.ndim < 2:
                    dim = 1
                else:
                    dim = cov.shape[0]
        else:
            mean = np.asarray(mean, dtype=float)
            dim = mean.size
    else:
        if not np.isscalar(dim):
            raise ValueError("Dimension of random variable must be a scalar.")

    # Check input sizes and return full arrays for mean and cov if necessary
    if mean is None:
        mean = np.zeros(dim)
    mean = np.asarray(mean, dtype=float)

    if cov is None:
        cov = 1.0
    cov = np.asarray(cov, dtype=float)

    if dim == 1:
        mean.shape = (1,)
        cov.shape = (1, 1)

    if mean.ndim != 1 or mean.shape[0] != dim:
        raise ValueError("Array 'mean' must be vector of length %d." % dim)
    if cov.ndim == 0:
        cov = cov * np.eye(dim)
    elif cov.ndim == 1:
        cov = np.diag(cov)
    else:
        if cov.shape != (dim, dim):
            raise ValueError("Array 'cov' must be at most two-dimensional,"
                                 " but cov.ndim = %d" % cov.ndim)

    return dim, mean, cov


def _process_quantiles(x, dim):
    """
    Adjust quantiles array so that last axis labels the components of
    each data point.

    """
    x = np.asarray(x, dtype=float)

    if x.ndim == 0:
        x = x[np.newaxis]
    elif x.ndim == 1:
        if dim == 1:
            x = x[:, np.newaxis]
        else:
            x = x[np.newaxis, :]

    return x


def _squeeze_output(out):
    """
    Remove single-dimensional entries from array and convert to scalar,
    if necessary.

    """
    out = out.squeeze()
    if out.ndim == 0:
        out = out[()]
    return out


def _pinv_1d(v, eps=1e-5):
    """
    A helper function for computing the pseudoinverse.

    Parameters
    ----------
    v : iterable of numbers
        This may be thought of as a vector of eigenvalues or singular values.
    eps : float
        Elements of v smaller than eps are considered negligible.

    Returns
    -------
    v_pinv : 1d float ndarray
        A vector of pseudo-inverted numbers.

    """
    return np.array([0 if abs(x) < eps else 1/x for x in v], dtype=float)


def _psd_pinv_decomposed_log_pdet(mat, cond=None, rcond=None,
                                  lower=True, check_finite=True):
    """
    Compute a decomposition of the pseudo-inverse and the logarithm of
    the pseudo-determinant of a symmetric positive semi-definite
    matrix.

    The pseudo-determinant of a matrix is defined as the product of
    the non-zero eigenvalues, and coincides with the usual determinant
    for a full matrix.

    Parameters
    ----------
    mat : array_like
        Input array of shape (`m`, `n`)
    cond, rcond : float or None
        Cutoff for 'small' singular values.
        Eigenvalues smaller than ``rcond*largest_eigenvalue``
        are considered zero.
        If None or -1, suitable machine precision is used.
    lower : bool, optional
        Whether the pertinent array data is taken from the lower or upper
        triangle of `mat`. (Default: lower)
    check_finite : boolean, optional
        Whether to check that the input matrix contains only finite numbers.
        Disabling may give a performance gain, but may result in problems
        (crashes, non-termination) if the inputs do contain infinities or NaNs.

    Returns
    -------
    M : array_like
        The pseudo-inverse of the input matrix is np.dot(M, M.T).
    log_pdet : float
        Logarithm of the pseudo-determinant of the matrix.

    """
    # Compute the symmetric eigendecomposition.
    # The input covariance matrix is required to be real symmetric
    # and positive semidefinite which implies that its eigenvalues
    # are all real and non-negative,
    # but clip them anyway to avoid numerical issues.

    # TODO: the code to set cond/rcond is identical to that in
    # scipy.linalg.{pinvh, pinv2} and if/when this function is subsumed
    # into scipy.linalg it should probably be shared between all of
    # these routines.

    # Note that eigh takes care of array conversion, chkfinite,
    # and assertion that the matrix is square.
    s, u = scipy.linalg.eigh(mat, lower=lower, check_finite=check_finite)

    if rcond is not None:
        cond = rcond
    if cond in [None, -1]:
        t = u.dtype.char.lower()
        factor = {'f': 1E3, 'd': 1E6}
        cond = factor[t] * np.finfo(t).eps
    eps = cond * np.max(abs(s))

    if np.min(s) < -eps:
        raise ValueError('the covariance matrix must be positive semidefinite')

    s_pinv = _pinv_1d(s, eps)
    U = np.multiply(u, np.sqrt(s_pinv))
    log_pdet = np.sum(np.log(s[s > eps]))

    return U, log_pdet


_doc_default_callparams = \
"""mean : array_like, optional
    Mean of the distribution (default zero)
cov : array_like, optional
    Covariance matrix of the distribution (default one)
"""

_doc_callparams_note = \
"""Setting the parameter `mean` to `None` is equivalent to having `mean`
be the zero-vector. The parameter `cov` can be a scalar, in which case
the covariance matrix is the identity times that value, a vector of
diagonal entries for the covariance matrix, or a two-dimensional
array_like.
"""

_doc_frozen_callparams = ""

_doc_frozen_callparams_note = \
"""See class definition for a detailed description of parameters."""

docdict_params = {
    '_doc_default_callparams': _doc_default_callparams,
    '_doc_callparams_note': _doc_callparams_note
}

docdict_noparams = {
    '_doc_default_callparams': _doc_frozen_callparams,
    '_doc_callparams_note': _doc_frozen_callparams_note
}


class multivariate_normal_gen(object):
    r"""
    A multivariate normal random variable.

    The `mean` keyword specifies the mean. The `cov` keyword specifies the
    covariance matrix.

    .. versionadded:: 0.14.0

    Methods
    -------
    pdf(x, mean=None, cov=1)
        Probability density function.
    logpdf(x, mean=None, cov=1)
        Log of the probability density function.
    rvs(mean=None, cov=1)
        Draw random samples from a multivariate normal distribution.
    entropy()
        Compute the differential entropy of the multivariate normal.

    Parameters
    ----------
    x : array_like
        Quantiles, with the last axis of `x` denoting the components.
    %(_doc_default_callparams)s

    Alternatively, the object may be called (as a function) to fix the mean
    and covariance parameters, returning a "frozen" multivariate normal
    random variable:

    rv = multivariate_normal(mean=None, scale=1)
        - Frozen  object with the same methods but holding the given
          mean and covariance fixed.

    Notes
    -----
    %(_doc_callparams_note)s

    The covariance matrix `cov` must be a (symmetric) positive
    semi-definite matrix. The determinant and inverse of `cov` are computed
    as the pseudo-determinant and pseudo-inverse, respectively, so
    that `cov` does not need to have full rank.

    The probability density function for `multivariate_normal` is

    .. math::

        f(x) = \frac{1}{\sqrt{(2 \pi)^k \det \Sigma}} \exp\left( -\frac{1}{2} (x - \mu)^T \Sigma^{-1} (x - \mu) \right),

    where :math:`\mu` is the mean, :math:`\Sigma` the covariance matrix,
    and :math:`k` is the dimension of the space where :math:`x` takes values.

    Examples
    --------
    >>> from scipy.stats import multivariate_normal
    >>> x = np.linspace(0, 5, 10, endpoint=False)
    >>> y = multivariate_normal.pdf(x, mean=2.5, cov=0.5); y
    array([ 0.00108914,  0.01033349,  0.05946514,  0.20755375,  0.43939129,
            0.56418958,  0.43939129,  0.20755375,  0.05946514,  0.01033349])
    >>> plt.plot(x, y)

    The input quantiles can be any shape of array, as long as the last
    axis labels the components.  This allows us for instance to
    display the frozen pdf for a non-isotropic random variable in 2D as
    follows:

    >>> x, y = np.mgrid[-1:1:.01, -1:1:.01]
    >>> pos = np.empty(x.shape + (2,))
    >>> pos[:, :, 0] = x; pos[:, :, 1] = y
    >>> rv = multivariate_normal([0.5, -0.2], [[2.0, 0.3], [0.3, 0.5]])
    >>> plt.contourf(x, y, rv.pdf(pos))

    """

    def __init__(self):
        self.__doc__ = doccer.docformat(self.__doc__, docdict_params)

    def __call__(self, mean=None, cov=1):
        """
        Create a frozen multivariate normal distribution.

        See `multivariate_normal_frozen` for more information.

        """
        return multivariate_normal_frozen(mean, cov)

    def _logpdf(self, x, mean, prec_U, log_det_cov):
        """
        Parameters
        ----------
        x : ndarray
            Points at which to evaluate the log of the probability
            density function
        mean : ndarray
            Mean of the distribution
        prec_U : ndarray
            A decomposition such that np.dot(prec_U, prec_U.T)
            is the precision matrix, i.e. inverse of the covariance matrix.
        log_det_cov : float
            Logarithm of the determinant of the covariance matrix

        Notes
        -----
        As this function does no argument checking, it should not be
        called directly; use 'logpdf' instead.

        """
        dim = x.shape[-1]
        dev = x - mean
        maha = np.sum(np.square(np.dot(dev, prec_U)), axis=-1)
        return -0.5 * (dim * _LOG_2PI + log_det_cov + maha)

    def logpdf(self, x, mean, cov):
        """
        Log of the multivariate normal probability density function.

        Parameters
        ----------
        x : array_like
            Quantiles, with the last axis of `x` denoting the components.
        %(_doc_default_callparams)s

        Notes
        -----
        %(_doc_callparams_note)s

        Returns
        -------
        pdf : ndarray
            Log of the probability density function evaluated at `x`

        """
        dim, mean, cov = _process_parameters(None, mean, cov)
        x = _process_quantiles(x, dim)
        prec_U, log_det_cov = _psd_pinv_decomposed_log_pdet(cov)
        out = self._logpdf(x, mean, prec_U, log_det_cov)
        return _squeeze_output(out)

    def pdf(self, x, mean, cov):
        """
        Multivariate normal probability density function.

        Parameters
        ----------
        x : array_like
            Quantiles, with the last axis of `x` denoting the components.
        %(_doc_default_callparams)s

        Notes
        -----
        %(_doc_callparams_note)s

        Returns
        -------
        pdf : ndarray
            Probability density function evaluated at `x`

        """
        dim, mean, cov = _process_parameters(None, mean, cov)
        x = _process_quantiles(x, dim)
        prec_U, log_det_cov = _psd_pinv_decomposed_log_pdet(cov)
        out = np.exp(self._logpdf(x, mean, prec_U, log_det_cov))
        return _squeeze_output(out)

    def rvs(self, mean=None, cov=1, size=1):
        """
        Draw random samples from a multivariate normal distribution.

        Parameters
        ----------
        %(_doc_default_callparams)s
        size : integer, optional
            Number of samples to draw (default 1).

        Notes
        -----
        %(_doc_callparams_note)s

        Returns
        -------
        rvs : ndarray or scalar
            Random variates of size (`size`, `N`), where `N` is the
            dimension of the random variable.

        """
        dim, mean, cov = _process_parameters(None, mean, cov)
        out = np.random.multivariate_normal(mean, cov, size)
        return _squeeze_output(out)

    def entropy(self, mean=None, cov=1):
        """
        Compute the differential entropy of the multivariate normal.

        Parameters
        ----------
        %(_doc_default_callparams)s

        Notes
        -----
        %(_doc_callparams_note)s

        Returns
        -------
        h : scalar
            Entropy of the multivariate normal distribution

        """
        dim, mean, cov = _process_parameters(None, mean, cov)
        return 1/2 * np.log(np.linalg.det(2 * np.pi * np.e * cov))

multivariate_normal = multivariate_normal_gen()


class multivariate_normal_frozen(object):
    def __init__(self, mean=None, cov=1):
        """
        Create a frozen multivariate normal distribution.

        Parameters
        ----------
        mean : array_like, optional
            Mean of the distribution (default zero)
        cov : array_like, optional
            Covariance matrix of the distribution (default one)

        Examples
        --------
        When called with the default parameters, this will create a 1D random
        variable with mean 0 and covariance 1:

        >>> from scipy.stats import multivariate_normal
        >>> r = multivariate_normal()
        >>> r.mean
        array([ 0.])
        >>> r.cov
        array([[1.]])

        """
        self.dim, self.mean, self.cov = _process_parameters(None, mean, cov)
        self.prec_U, self._log_det_cov = _psd_pinv_decomposed_log_pdet(self.cov)

        self._mnorm = multivariate_normal_gen()

    def logpdf(self, x):
        x = _process_quantiles(x, self.dim)
        out = self._mnorm._logpdf(x, self.mean, self.prec_U, self._log_det_cov)
        return _squeeze_output(out)

    def pdf(self, x):
        return np.exp(self.logpdf(x))

    def rvs(self, size=1):
        return self._mnorm.rvs(self.mean, self.cov, size)

    def entropy(self):
        """
        Computes the differential entropy of the multivariate normal.

        Returns
        -------
        h : scalar
            Entropy of the multivariate normal distribution

        """
        return 1/2 * (self.dim * (_LOG_2PI + 1) + self._log_det_cov)


# Set frozen generator docstrings from corresponding docstrings in
# multivariate_normal_gen and fill in default strings in class docstrings
for name in ['logpdf', 'pdf', 'rvs']:
    method = multivariate_normal_gen.__dict__[name]
    method_frozen = multivariate_normal_frozen.__dict__[name]
    method_frozen.__doc__ = doccer.docformat(method.__doc__, docdict_noparams)
    method.__doc__ = doccer.docformat(method.__doc__, docdict_params)

########NEW FILE########
__FILENAME__ = anagrams
from mrjob.job import MRJob

class MRAnagram(MRJob):

    def mapper(self, _, line):
        # Convert word into a list of characters, sort them, and convert
        # back to a string.
        letters = list(line)
        letters.sort()

        # Key is the sorted word, value is the regular word.
        yield letters, line

    def reducer(self, _, words):
        # Get the list of words containing these letters.
        anagrams = [w for w in words]

        # Only yield results if there are at least two words which are
        # anagrams of each other.
        if len(anagrams) > 1:
            yield len(anagrams), anagrams


if __name__ == "__main__":
    MRAnagram.run()

        

########NEW FILE########
__FILENAME__ = friend_affiliations
from mrjob.job import MRJob

class MRFriendAffiliations(MRJob):

    def mapper(self, _, line):
        # Tokenize line.
        tokens = line.split(',')
        tokens = [t.strip() for t in tokens]
        
        # First token is the person's name.
        # Second token is their favorite team.
        # Remaining tokens are their friends' names.
        name, team, friends = (tokens[0], tokens[1], tokens[2:])

        # Emit (key, value) pairs with friends names as the keys and 
        # (this_name, this_team) as the value (same value for all).
        for friend in friends:
            yield friend, (name, team)

        # Special case: emit a similar (key, value) pair for this person.
        yield name, (name, team)

    def reducer(self, name, friends):
        # Count the number of Red Sox and Cardinals fans who are friends
        # with this person.
        team = None
        red_sox_count = 0
        cardinals_count = 0
        for friend in friends:
            # Keep an eye out of the special case where the friends name 
            # and this persons name are the same -- that tells us which 
            # team this person cheers for.
            if friend[0] == name:
                this_team = friend[1]
            else:
                if friend[1] == "Red Sox":
                    red_sox_count += 1
                elif friend[1] == "Cardinals":
                    cardinals_count += 1
                else:
                    print "ERROR: Unknown team \"{0}\"".format(friend[1])

        # Yield results.
        yield name, (this_team, red_sox_count, cardinals_count)

if __name__ == '__main__':
    MRFriendAffiliations.run()


########NEW FILE########
__FILENAME__ = generate_friends
#!/usr/bin/python

"""
generate_friends.py

Generates data file "baseball_friends.csv" to be used for lab8 MapReduce
example.

Reads list of names from "names.txt", randomly assigns team alligiences,
then assigns friendships based on super simple algorithm, and finally 
writes out the file in the following csv format:

  name, team, friend1, friend2, friend3, ...

"""

import numpy as np
from numpy.random import binomial

# Read list of names from file.
names = [line.strip() for line in open("names.txt")]
names = np.unique(names)

# Randomly generate team affiliations for each person.
team = binomial(1, 0.5, len(names))

# Probability that two people who are fans of the same team are friends.
friendliness_same = 0.05
# Probability that two people who are fans of opposite teams are friends.
friendliness_diff = 0.03

# Create matrix to store friend relationships.
friends = np.zeros([len(names), len(names)])
for i1 in range(len(names)):
    for i2 in range(i1 + 1, len(names)):
        if team[i1] == team[i2]:
            flip = binomial(1, friendliness_same)
        else:
            flip = binomial(1, friendliness_diff)

        friends[i1, i2] = flip
        friends[i2, i1] = flip

# Write output file.
outfile = open("baseball_friends.csv", 'w')
for i in range(len(names)):
    # Get data for this row.
    this_name = names[i]
    this_team = "Red Sox" if team[i] else "Cardinals"
    friend_list = np.array(names)[friends[i,:] == 1]

    # Write to file.
    outstr = ", ".join((this_name, this_team) + tuple(friend_list))
    outfile.write(outstr + "\n")
outfile.close()


########NEW FILE########
__FILENAME__ = most_used_word
from mrjob.job import MRJob
import re

WORD_RE = re.compile(r"[\w']+")

class MRMostUsedWord(MRJob):

    def mapper_get_words(self, _, line):
        # yield each word in the line
        for word in WORD_RE.findall(line):
            yield (word.lower(), 1)

    def combiner_count_words(self, word, counts):
        # optimization: sum the words we've seen so far
        yield (word, sum(counts))

    def reducer_count_words(self, word, counts):
        # send all (num_occurrences, word) pairs to the same reducer.
        # num_occurrences is so we can easily use Python's max() function.
        yield None, (sum(counts), word)

    # discard the key, it is just None
    def reducer_find_max_word(self, _, word_count_pairs):
        # each item of word_count_pairs is (count, word),
        # so yielding one results in key=counts, value=word
        yield max(word_count_pairs)

    def steps(self):
        return [
            self.mr(mapper=self.mapper_get_words,
                    combiner=self.combiner_count_words,
                    reducer=self.reducer_count_words),
            self.mr(reducer=self.reducer_find_max_word)
            ]

if __name__ == '__main__':
    MRMostUsedWord.run()


########NEW FILE########
__FILENAME__ = word_count
from mrjob.job import MRJob

class MRWordFrequencyCount(MRJob):

    def mapper(self, _, line):
        yield "chars", len(line)
        yield "words", len(line.split())
        yield "lines", 1

    def reducer(self, key, values):
        yield key, sum(values)

if __name__ == '__main__':
    MRWordFrequencyCount.run()

########NEW FILE########
__FILENAME__ = skeleton
import numpy as np

from mrjob.job import MRJob
from itertools import combinations, permutations

from scipy.stats.stats import pearsonr


class RestaurantSimilarities(MRJob):

    def steps(self):
        "the steps in the map-reduce process"
        thesteps = [
            self.mr(mapper=self.line_mapper, reducer=self.users_items_collector),
            self.mr(mapper=self.pair_items_mapper, reducer=self.calc_sim_collector)
        ]
        return thesteps

    def line_mapper(self,_,line):
        "this is the complete implementation"
        user_id,business_id,stars,business_avg,user_avg=line.split(',')
        yield user_id, (business_id,stars,business_avg,user_avg)


    def users_items_collector(self, user_id, values):
        """
        #iterate over the list of tuples yielded in the previous mapper
        #and append them to an array of rating information
        """
        pass


    def pair_items_mapper(self, user_id, values):
        """
        ignoring the user_id key, take all combinations of business pairs
        and yield as key the pair id, and as value the pair rating information
        """
	   pass #your code here

    def calc_sim_collector(self, key, values):
        """
        Pick up the information from the previous yield as shown. Compute
        the pearson correlation and yield the final information as in the
        last line here.
        """
        (rest1, rest2), common_ratings = key, values
	    #your code here
        yield (rest1, rest2), (rho, n_common)


#Below MUST be there for things to work
if __name__ == '__main__':
    RestaurantSimilarities.run()

########NEW FILE########
