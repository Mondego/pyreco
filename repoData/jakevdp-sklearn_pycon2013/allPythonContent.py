__FILENAME__ = download_data
"""
Run this script to make sure data is cached in the appropriate
place on your computer.

The data are only a few megabytes, but conference wireless is
often not very reliable...
"""
import os
import sys
from sklearn import datasets

#------------------------------------------------------------
# Faces data: this will be stored in the scikit_learn_data
#             sub-directory of your home folder
faces = datasets.fetch_olivetti_faces()
print "Successfully fetched olivetti faces data"

#------------------------------------------------------------
# SDSS galaxy data: this will be stored in notebooks/datasets/data
sys.path.append(os.path.abspath('notebooks'))
from datasets import fetch_sdss_galaxy_mags
colors = fetch_sdss_galaxy_mags()
print "Successfully fetched SDSS galaxy data"


#------------------------------------------------------------
# SDSS filters & vega spectrum: stored in notebooks/figures/downloads
from figures.sdss_filters import fetch_filter, fetch_vega_spectrum
spectrum = fetch_vega_spectrum()
print "Successfully fetched vega spectrum"

filters = [fetch_filter(f) for f in 'ugriz']
print "Successfully fetched SDSS filters"

########NEW FILE########
__FILENAME__ = galaxy_mags
# This download script comes from astroML: http://astroml.github.com
import os
import urllib
import numpy as np

#----------------------------------------------------------------------
# Tools for querying the SDSS database using SQL
PUBLIC_URL = 'http://cas.sdss.org/public/en/tools/search/x_sql.asp'
DEFAULT_FMT = 'csv'


def remove_sql_comments(sql):
    """Strip SQL comments starting with --"""
    return ' \n'.join(map(lambda x: x.split('--')[0], sql.split('\n')))


def sql_query(sql_str, url=PUBLIC_URL, format='csv'):
    """Execute query

    Parameters
    ----------
    sql_str : string
        valid sql query

    url: string (optional)
        query url.  Default is http://cas.sdss.org query script

    format: string (default='csv')
        query output format

    Returns
    -------
    F: file object
        results of the query
    """
    sql_str = remove_sql_comments(sql_str)
    params = urllib.urlencode(dict(cmd=sql_str, format=format))
    return urllib.urlopen(url + '?%s' % params)


SPECCLASS = ['UNKNOWN', 'STAR', 'GALAXY', 'QSO',
             'HIZ_QSO', 'SKY', 'STAR_LATE', 'GAL_EM']

NOBJECTS = 50000

GAL_MAGS_DTYPE = [('u', float),
                  ('g', float),
                  ('r', float),
                  ('i', float),
                  ('z', float),
                  ('specClass', int),
                  ('redshift', float),
                  ('redshift_err', float)]

ARCHIVE_FILE = 'sdss_galaxy_mags.npy'

DATA_HOME = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'data')

def fetch_sdss_galaxy_mags(data_home=DATA_HOME, download_if_missing=True):
    """Loader for SDSS galaxy magnitudes.

    This function directly queries the sdss SQL database at
    http://cas.sdss.org/

    Parameters
    ----------
    data_home : optional, default=None
        Specify another download and cache folder for the datasets. By default
        all scikit learn data is stored in '~/astroML_data' subfolders.

    download_if_missing : optional, default=True
        If False, raise a IOError if the data is not locally available
        instead of trying to download the data from the source site.

    Returns
    -------
    data : recarray, shape = (10000,)
        record array containing magnitudes and redshift for each galaxy
    """
    if not os.path.exists(data_home):
        os.makedirs(data_home)

    archive_file = os.path.join(data_home, ARCHIVE_FILE)

    query_text = ('\n'.join(
            ("SELECT TOP %i" % NOBJECTS,
             "   p.u, p.g, p.r, p.i, p.z, s.specClass, s.z, s.zerr",
             "FROM PhotoObj AS p",
             "   JOIN SpecObj AS s ON s.bestobjid = p.objid",
             "WHERE ",
             "   p.u BETWEEN 0 AND 19.6",
             "   AND p.g BETWEEN 0 AND 20",
             "   AND s.specClass > 1 -- not UNKNOWN or STAR",
             "   AND s.specClass <> 5 -- not SKY",
             "   AND s.specClass <> 6 -- not STAR_LATE")))

    if not os.path.exists(archive_file):
        if not download_if_missing:
            raise IOError('data not present on disk. '
                          'set download_if_missing=True to download')

        print "querying for %i objects" % NOBJECTS
        print query_text
        output = sql_query(query_text)
        print "finished."

        data = np.loadtxt(output, delimiter=',',
                          skiprows=1, dtype=GAL_MAGS_DTYPE)
        np.save(archive_file, data)

    else:
        data = np.load(archive_file)

    return data

########NEW FILE########
__FILENAME__ = bias_variance
import numpy as np
import matplotlib.pyplot as plt


def test_func(x, err=0.5):
    return np.random.normal(10 - 1. / (x + 0.1), err)


def compute_error(x, y, p):
    yfit = np.polyval(p, x)
    return np.sqrt(np.mean((y - yfit) ** 2))


def plot_bias_variance(N=8, random_seed=42, err=0.5):
    np.random.seed(random_seed)
    x = 10 ** np.linspace(-2, 0, N)
    y = test_func(x)

    xfit = np.linspace(-0.2, 1.2, 1000)

    titles = ['d = 1 (under-fit; high bias)',
              'd = 2',
              'd = 6 (over-fit; high variance)']
    degrees = [1, 2, 6]

    fig = plt.figure(figsize = (9, 3.5))
    fig.subplots_adjust(left = 0.06, right=0.98,
                        bottom=0.15, top=0.85,
                        wspace=0.05)
    for i, d in enumerate(degrees):
        ax = fig.add_subplot(131 + i, xticks=[], yticks=[])
        ax.scatter(x, y, marker='x', c='k', s=50)

        p = np.polyfit(x, y, d)
        yfit = np.polyval(p, xfit)
        ax.plot(xfit, yfit, '-b')

        ax.set_xlim(-0.2, 1.2)
        ax.set_ylim(0, 12)
        ax.set_xlabel('house size')
        if i == 0:
            ax.set_ylabel('price')

        ax.set_title(titles[i])

if __name__ == '__main__':
    plot_bias_variance()
    plt.show()

########NEW FILE########
__FILENAME__ = linear_regression
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression


def plot_linear_regression():
    a = 0.5
    b = 1.0

    # x from 0 to 10
    x = 30 * np.random.random(20)

    # y = a*x + b with noise
    y = a * x + b + np.random.normal(size=x.shape)

    # create a linear regression classifier
    clf = LinearRegression()
    clf.fit(x[:, None], y)

    # predict y from the data
    x_new = np.linspace(0, 30, 100)
    y_new = clf.predict(x_new[:, None])

    # plot the results
    ax = plt.axes()
    ax.scatter(x, y)
    ax.plot(x_new, y_new)

    ax.set_xlabel('x')
    ax.set_ylabel('y')

    ax.axis('tight')


if __name__ == '__main__':
    plot_linear_regression()
    plt.show()

########NEW FILE########
__FILENAME__ = ML_flow_chart
"""
Tutorial Diagrams
-----------------

This script plots the flow-charts used in the scikit-learn tutorials.
"""

import numpy as np
import pylab as pl
from matplotlib.patches import Circle, Rectangle, Polygon, Arrow, FancyArrow

def create_base(box_bg = '#CCCCCC',
                arrow1 = '#88CCFF',
                arrow2 = '#88FF88',
                supervised=True):
    fig = pl.figure(figsize=(9, 6), facecolor='w')
    ax = pl.axes((0, 0, 1, 1),
                 xticks=[], yticks=[], frameon=False)
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 6)

    patches = [Rectangle((0.3, 3.6), 1.5, 1.8, zorder=1, fc=box_bg),
               Rectangle((0.5, 3.8), 1.5, 1.8, zorder=2, fc=box_bg),
               Rectangle((0.7, 4.0), 1.5, 1.8, zorder=3, fc=box_bg),
               
               Rectangle((2.9, 3.6), 0.2, 1.8, fc=box_bg),
               Rectangle((3.1, 3.8), 0.2, 1.8, fc=box_bg),
               Rectangle((3.3, 4.0), 0.2, 1.8, fc=box_bg),
               
               Rectangle((0.3, 0.2), 1.5, 1.8, fc=box_bg),
               
               Rectangle((2.9, 0.2), 0.2, 1.8, fc=box_bg),
               
               Circle((5.5, 3.5), 1.0, fc=box_bg),
               
               Polygon([[5.5, 1.7],
                        [6.1, 1.1],
                        [5.5, 0.5],
                        [4.9, 1.1]], fc=box_bg),
               
               FancyArrow(2.3, 4.6, 0.35, 0, fc=arrow1,
                          width=0.25, head_width=0.5, head_length=0.2),
               
               FancyArrow(3.75, 4.2, 0.5, -0.2, fc=arrow1,
                          width=0.25, head_width=0.5, head_length=0.2),
               
               FancyArrow(5.5, 2.4, 0, -0.4, fc=arrow1,
                          width=0.25, head_width=0.5, head_length=0.2),
               
               FancyArrow(2.0, 1.1, 0.5, 0, fc=arrow2,
                          width=0.25, head_width=0.5, head_length=0.2),
               
               FancyArrow(3.3, 1.1, 1.3, 0, fc=arrow2,
                          width=0.25, head_width=0.5, head_length=0.2),
               
               FancyArrow(6.2, 1.1, 0.8, 0, fc=arrow2,
                          width=0.25, head_width=0.5, head_length=0.2)]

    if supervised:
        patches += [Rectangle((0.3, 2.4), 1.5, 0.5, zorder=1, fc=box_bg),
                    Rectangle((0.5, 2.6), 1.5, 0.5, zorder=2, fc=box_bg),
                    Rectangle((0.7, 2.8), 1.5, 0.5, zorder=3, fc=box_bg),
                    FancyArrow(2.3, 2.9, 2.0, 0, fc=arrow1,
                               width=0.25, head_width=0.5, head_length=0.2),
                    Rectangle((7.3, 0.85), 1.5, 0.5, fc=box_bg)]
    else:
        patches += [Rectangle((7.3, 0.2), 1.5, 1.8, fc=box_bg)]
    
    for p in patches:
        ax.add_patch(p)
        
    pl.text(1.45, 4.9, "Training\nText,\nDocuments,\nImages,\netc.",
            ha='center', va='center', fontsize=14)
    
    pl.text(3.6, 4.9, "Feature\nVectors", 
            ha='left', va='center', fontsize=14)
    
    pl.text(5.5, 3.5, "Machine\nLearning\nAlgorithm",
            ha='center', va='center', fontsize=14)
    
    pl.text(1.05, 1.1, "New Text,\nDocument,\nImage,\netc.",
            ha='center', va='center', fontsize=14)
    
    pl.text(3.3, 1.7, "Feature\nVector", 
            ha='left', va='center', fontsize=14)
    
    pl.text(5.5, 1.1, "Predictive\nModel", 
            ha='center', va='center', fontsize=12)

    if supervised:
        pl.text(1.45, 3.05, "Labels",
                ha='center', va='center', fontsize=14)
    
        pl.text(8.05, 1.1, "Expected\nLabel",
                ha='center', va='center', fontsize=14)
        pl.text(8.8, 5.8, "Supervised Learning Model",
                ha='right', va='top', fontsize=18)

    else:
        pl.text(8.05, 1.1,
                "Likelihood\nor Cluster ID\nor Better\nRepresentation",
                ha='center', va='center', fontsize=12)
        pl.text(8.8, 5.8, "Unsupervised Learning Model",
                ha='right', va='top', fontsize=18)
        
        

def plot_supervised_chart(annotate=False):
    create_base(supervised=True)
    if annotate:
        fontdict = dict(color='r', weight='bold', size=14)
        pl.text(1.9, 4.55, 'X = vec.fit_transform(input)',
                fontdict=fontdict,
                rotation=20, ha='left', va='bottom')
        pl.text(3.7, 3.2, 'clf.fit(X, y)',
                fontdict=fontdict,
                rotation=20, ha='left', va='bottom')
        pl.text(1.7, 1.5, 'X_new = vec.transform(input)',
                fontdict=fontdict,
                rotation=20, ha='left', va='bottom')
        pl.text(6.1, 1.5, 'y_new = clf.predict(X_new)',
                fontdict=fontdict,
                rotation=20, ha='left', va='bottom')

def plot_unsupervised_chart():
    create_base(supervised=False)


if __name__ == '__main__':
    plot_supervised_chart(False)
    plot_supervised_chart(True)
    plot_unsupervised_chart()
    pl.show()



########NEW FILE########
__FILENAME__ = sdss_filters
"""
SDSS Filters
------------

This example downloads and plots the filters from the Sloan Digital Sky
Survey, along with a reference spectrum.
"""
import os
import urllib2

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Arrow

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'downloads')
REFSPEC_URL = 'ftp://ftp.stsci.edu/cdbs/current_calspec/ascii_files/1732526_nic_002.ascii'
FILTER_URL = 'http://www.sdss.org/dr7/instruments/imager/filters/%s.dat'

def fetch_filter(filt):
    assert filt in 'ugriz'
    url = FILTER_URL % filt
    
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    loc = os.path.join(DOWNLOAD_DIR, '%s.dat' % filt)
    if not os.path.exists(loc):
        print "downloading from %s" % url
        F = urllib2.urlopen(url)
        open(loc, 'w').write(F.read())

    F = open(loc)
        
    data = np.loadtxt(F)
    return data


def fetch_vega_spectrum():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    refspec_file = os.path.join(DOWNLOAD_DIR, REFSPEC_URL.split('/')[-1])

    if  not os.path.exists(refspec_file):
        print "downloading from %s" % REFSPEC_URL
        F = urllib2.urlopen(REFSPEC_URL)
        open(refspec_file, 'w').write(F.read())

    F = open(refspec_file)

    data = np.loadtxt(F)
    return data


def plot_sdss_filters():
    Xref = fetch_vega_spectrum()
    Xref[:, 1] /= 2.1 * Xref[:, 1].max()

    #----------------------------------------------------------------------
    # Plot filters in color with a single spectrum
    fig, ax = plt.subplots()
    ax.plot(Xref[:, 0], Xref[:, 1], '-k', lw=2)

    for f,c in zip('ugriz', 'bgrmk'):
        X = fetch_filter(f)
        ax.fill(X[:, 0], X[:, 1], ec=c, fc=c, alpha=0.4)

    kwargs = dict(fontsize=20, ha='center', va='center', alpha=0.5)
    ax.text(3500, 0.02, 'u', color='b', **kwargs)
    ax.text(4600, 0.02, 'g', color='g', **kwargs)
    ax.text(6100, 0.02, 'r', color='r', **kwargs)
    ax.text(7500, 0.02, 'i', color='m', **kwargs)
    ax.text(8800, 0.02, 'z', color='k', **kwargs)

    ax.set_xlim(3000, 11000)

    ax.set_title('SDSS Filters and Reference Spectrum')
    ax.set_xlabel('Wavelength (Angstroms)')
    ax.set_ylabel('normalized flux / filter transmission')


def plot_redshifts():
    Xref = fetch_vega_spectrum()
    Xref[:, 1] /= 2.1 * Xref[:, 1].max()

    #----------------------------------------------------------------------
    # Plot filters in gray with several redshifted spectra
    fig, ax = plt.subplots()

    redshifts = [0.0, 0.4, 0.8]
    colors = 'bgr'

    for z, c in zip(redshifts, colors):
        plt.plot((1. + z) * Xref[:, 0], Xref[:, 1], color=c)

    ax.add_patch(Arrow(4200, 0.47, 1300, 0, lw=0, width=0.05, color='r'))
    ax.add_patch(Arrow(5800, 0.47, 1250, 0, lw=0, width=0.05, color='r'))

    ax.text(3800, 0.49, 'z = 0.0', fontsize=14, color=colors[0])
    ax.text(5500, 0.49, 'z = 0.4', fontsize=14, color=colors[1])
    ax.text(7300, 0.49, 'z = 0.8', fontsize=14, color=colors[2])

    for f in 'ugriz':
        X = fetch_filter(f)
        ax.fill(X[:, 0], X[:, 1], ec='k', fc='k', alpha=0.2)

    kwargs = dict(fontsize=20, color='gray', ha='center', va='center')
    ax.text(3500, 0.02, 'u', **kwargs)
    ax.text(4600, 0.02, 'g', **kwargs)
    ax.text(6100, 0.02, 'r', **kwargs)
    ax.text(7500, 0.02, 'i', **kwargs)
    ax.text(8800, 0.02, 'z', **kwargs)

    ax.set_xlim(3000, 11000)
    ax.set_ylim(0, 0.55)

    ax.set_title('Redshifting of a Spectrum')
    ax.set_xlabel('Observed Wavelength (Angstroms)')
    ax.set_ylabel('normalized flux / filter transmission')


if __name__ == '__main__':
    plot_sdss_filters()
    plot_redshifts()
    plt.show()

########NEW FILE########
__FILENAME__ = sgd_separator
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import SGDClassifier
from sklearn.datasets.samples_generator import make_blobs

def plot_sgd_separator():
    # we create 50 separable points
    X, Y = make_blobs(n_samples=50, centers=2,
                      random_state=0, cluster_std=0.60)

    # fit the model
    clf = SGDClassifier(loss="hinge", alpha=0.01,
                        n_iter=200, fit_intercept=True)
    clf.fit(X, Y)

    # plot the line, the points, and the nearest vectors to the plane
    xx = np.linspace(-1, 5, 10)
    yy = np.linspace(-1, 5, 10)

    X1, X2 = np.meshgrid(xx, yy)
    Z = np.empty(X1.shape)
    for (i, j), val in np.ndenumerate(X1):
        x1 = val
        x2 = X2[i, j]
        p = clf.decision_function([x1, x2])
        Z[i, j] = p[0]
    levels = [-1.0, 0.0, 1.0]
    linestyles = ['dashed', 'solid', 'dashed']
    colors = 'k'

    ax = plt.axes()
    ax.contour(X1, X2, Z, levels, colors=colors, linestyles=linestyles)
    ax.scatter(X[:, 0], X[:, 1], c=Y, cmap=plt.cm.Paired)

    ax.axis('tight')


if __name__ == '__main__':
    plot_sgd_separator()
    plt.show()

########NEW FILE########
__FILENAME__ = svm_gui_frames
"""
Linear Model Example
--------------------

This is an example plot from the tutorial which accompanies an explanation
of the support vector machine GUI.
"""

import numpy as np
import pylab as pl
import matplotlib

from sklearn import svm


def linear_model(rseed=42, Npts=30):
    np.random.seed(rseed)


    data = np.random.normal(0, 10, (Npts, 2))
    data[:Npts / 2] -= 15
    data[Npts / 2:] += 15

    labels = np.ones(Npts)
    labels[:Npts / 2] = -1

    return data, labels


def nonlinear_model(rseed=42, Npts=30):
    radius = 40 * np.random.random(Npts)
    far_pts = radius > 20
    radius[far_pts] *= 1.2
    radius[~far_pts] *= 1.1

    theta = np.random.random(Npts) * np.pi * 2

    data = np.empty((Npts, 2))
    data[:, 0] = radius * np.cos(theta)
    data[:, 1] = radius * np.sin(theta)

    labels = np.ones(Npts)
    labels[far_pts] = -1

    return data, labels


def plot_linear_model():
    X, y = linear_model()
    clf = svm.SVC(kernel='linear',
                  gamma=0.01, coef0=0, degree=3)
    clf.fit(X, y)

    fig = pl.figure()
    ax = pl.subplot(111, xticks=[], yticks=[])
    ax.scatter(X[:, 0], X[:, 1], c=y, cmap=pl.cm.bone)

    ax.scatter(clf.support_vectors_[:, 0],
               clf.support_vectors_[:, 1],
               s=80, edgecolors="k", facecolors="none")

    delta = 1
    y_min, y_max = -50, 50
    x_min, x_max = -50, 50
    x = np.arange(x_min, x_max + delta, delta)
    y = np.arange(y_min, y_max + delta, delta)
    X1, X2 = np.meshgrid(x, y)
    Z = clf.decision_function(np.c_[X1.ravel(), X2.ravel()])
    Z = Z.reshape(X1.shape)

    levels = [-1.0, 0.0, 1.0]
    linestyles = ['dashed', 'solid', 'dashed']
    colors = 'k'
    ax.contour(X1, X2, Z, levels,
               colors=colors,
               linestyles=linestyles)


def plot_rbf_model():
    X, y = nonlinear_model()
    clf = svm.SVC(kernel='rbf',
                  gamma=0.001, coef0=0, degree=3)
    clf.fit(X, y)

    fig = pl.figure()
    ax = pl.subplot(111, xticks=[], yticks=[])
    ax.scatter(X[:, 0], X[:, 1], c=y, cmap=pl.cm.bone, zorder=2)

    ax.scatter(clf.support_vectors_[:, 0],
               clf.support_vectors_[:, 1],
               s=80, edgecolors="k", facecolors="none")

    delta = 1
    y_min, y_max = -50, 50
    x_min, x_max = -50, 50
    x = np.arange(x_min, x_max + delta, delta)
    y = np.arange(y_min, y_max + delta, delta)
    X1, X2 = np.meshgrid(x, y)
    Z = clf.decision_function(np.c_[X1.ravel(), X2.ravel()])
    Z = Z.reshape(X1.shape)

    levels = [-1.0, 0.0, 1.0]
    linestyles = ['dashed', 'solid', 'dashed']
    colors = 'k'

    ax.contourf(X1, X2, Z, 10,
                cmap=matplotlib.cm.bone,
                origin='lower',
                alpha=0.85, zorder=1)
    ax.contour(X1, X2, Z, [0.0],
               colors='k',
               linestyles=['solid'], zorder=1)


if __name__ == '__main__':
    plot_linear_model()
    plot_rbf_model()
    pl.show()
    

########NEW FILE########
__FILENAME__ = generate_v2
"""Simple utility script for semi-gracefully downgrading v3 notebooks to v2"""

import io
import os

from IPython.nbformat import current

def heading_to_md(cell):
    """turn heading cell into corresponding markdown"""
    cell.cell_type = "markdown"
    level = cell.pop('level', 1)
    cell.source = '#'*level + ' ' + cell.source

def raw_to_md(cell):
    """let raw passthrough as markdown"""
    cell.cell_type = "markdown"

def downgrade(nb):
    """downgrade a v3 notebook to v2"""
    if nb.nbformat != 3:
        return nb
    nb.nbformat = 2
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'heading':
                heading_to_md(cell)
            elif cell.cell_type == 'raw':
                raw_to_md(cell)
    return nb

def downgrade_ipynb(fname):
    base, ext = os.path.splitext(fname)
    newname = base+'.v2'+ext
    print "downgrading %s -> %s" % (fname, newname)
    with io.open(fname, 'r', encoding='utf8') as f:
        nb = current.read(f, 'json')
    nb = downgrade(nb)
    with open(newname, 'w') as f:
        current.write(nb, f, 'json')

if __name__ == '__main__':
    map(downgrade_ipynb, [f for f in os.listdir('.')
                          if f.endswith('.ipynb') and 'v2' not in f]) 

########NEW FILE########
__FILENAME__ = boston_decision_tree
clf = DecisionTreeRegressor()
clf.fit(data.data, data.target)

predicted = clf.predict(data.data)

plt.scatter(data.target, predicted)
plt.plot([0, 50], [0, 50], '--k')
plt.axis('tight')
plt.xlabel('True price ($1000s)')
plt.ylabel('Predicted price ($1000s)')

########NEW FILE########
__FILENAME__ = iris_kmeans
kmeans = KMeans(n_clusters=3, random_state=rng).fit(X)

plot_2D(X_pca, kmeans.labels_, ["c0", "c1", "c2"])
plt.title('K-Means labels')

plot_2D(X_pca, iris.target, iris.target_names)
plt.title('True labels')

########NEW FILE########
__FILENAME__ = iris_rpca
from sklearn.decomposition import RandomizedPCA

X_rpca = RandomizedPCA(n_components=2).fit_transform(X)

plot_PCA_2D(X_rpca, iris.target, iris.target_names)
plt.title('Randomized PCA')

plot_PCA_2D(X_pca, iris.target, iris.target_names)
plt.title('PCA')

########NEW FILE########
__FILENAME__ = show_faces
from sklearn.datasets import fetch_olivetti_faces
import numpy as np
import matplotlib.pyplot as plt

faces = fetch_olivetti_faces()

# set up the figure
fig = plt.figure(figsize=(6, 6))  # figure size in inches
fig.subplots_adjust(left=0, right=1, bottom=0, top=1, hspace=0.05, wspace=0.05)

# plot the faces: each image is 64x64 pixels
for i in range(64):
    ax = fig.add_subplot(8, 8, i + 1, xticks=[], yticks=[])
    ax.imshow(faces.images[i], cmap=plt.cm.bone)

########NEW FILE########
__FILENAME__ = svm_gui
"""
==========
Libsvm GUI
==========

A simple graphical frontend for Libsvm mainly intended for didactic
purposes. You can create data points by point and click and visualize
the decision region induced by different kernels and parameter settings.

To create positive examples click the left mouse button; to create
negative examples click the right button.

If all examples are from the same class, it uses a one-class SVM.

"""
from __future__ import division

# Author: Peter Prettenhoer <peter.prettenhofer@gmail.com>
#
# License: BSD Style.

import matplotlib
matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg
from matplotlib.figure import Figure
from matplotlib.contour import ContourSet

import Tkinter as Tk
import sys
import numpy as np

from sklearn import svm
from sklearn.datasets import dump_svmlight_file

y_min, y_max = -50, 50
x_min, x_max = -50, 50


class Model(object):
    """The Model which hold the data. It implements the
    observable in the observer pattern and notifies the
    registered observers on change event.
    """

    def __init__(self):
        self.observers = []
        self.surface = None
        self.data = []
        self.cls = None
        self.surface_type = 0

    def changed(self, event):
        """Notify the observers. """
        for observer in self.observers:
            observer.update(event, self)

    def add_observer(self, observer):
        """Register an observer. """
        self.observers.append(observer)

    def set_surface(self, surface):
        self.surface = surface

    def dump_svmlight_file(self, file):
        data = np.array(self.data)
        X = data[:, 0:2]
        y = data[:, 2]
        dump_svmlight_file(X, y, file)


class Controller(object):
    def __init__(self, model):
        self.model = model
        self.kernel = Tk.IntVar()
        self.surface_type = Tk.IntVar()
        # Whether or not a model has been fitted
        self.fitted = False

    def fit(self):
        print "fit the model"
        train = np.array(self.model.data)
        X = train[:, 0:2]
        y = train[:, 2]

        C = float(self.complexity.get())
        gamma = float(self.gamma.get())
        coef0 = float(self.coef0.get())
        degree = int(self.degree.get())
        kernel_map = {0: "linear", 1: "rbf", 2: "poly"}
        if len(np.unique(y)) == 1:
            clf = svm.OneClassSVM(kernel=kernel_map[self.kernel.get()],
                      gamma=gamma, coef0=coef0, degree=degree)
            clf.fit(X)
        else:
            clf = svm.SVC(kernel=kernel_map[self.kernel.get()], C=C,
                          gamma=gamma, coef0=coef0, degree=degree)
            clf.fit(X, y)
        if hasattr(clf, 'score'):
            print "Accuracy:", clf.score(X, y) * 100
        X1, X2, Z = self.decision_surface(clf)
        self.model.clf = clf
        self.model.set_surface((X1, X2, Z))
        self.model.surface_type = self.surface_type.get()
        self.fitted = True
        self.model.changed("surface")

    def decision_surface(self, cls):
        delta = 1
        x = np.arange(x_min, x_max + delta, delta)
        y = np.arange(y_min, y_max + delta, delta)
        X1, X2 = np.meshgrid(x, y)
        Z = cls.decision_function(np.c_[X1.ravel(), X2.ravel()])
        Z = Z.reshape(X1.shape)
        return X1, X2, Z

    def clear_data(self):
        self.model.data = []
        self.fitted = False
        self.model.changed("clear")

    def add_example(self, x, y, label):
        self.model.data.append((x, y, label))
        self.model.changed("example_added")

        # update decision surface if already fitted.
        self.refit()

    def refit(self):
        """Refit the model if already fitted. """
        if self.fitted:
            self.fit()


class View(object):
    """Test docstring. """
    def __init__(self, root, controller):
        f = Figure()
        ax = f.add_subplot(111)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlim((x_min, x_max))
        ax.set_ylim((y_min, y_max))
        canvas = FigureCanvasTkAgg(f, master=root)
        canvas.show()
        canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
        canvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
        canvas.mpl_connect('button_press_event', self.onclick)
        canvas.mpl_connect('key_press_event', self.keypress)
        canvas.mpl_connect('key_release_event', self.keyrelease)
        toolbar = NavigationToolbar2TkAgg(canvas, root)
        toolbar.update()
        self.controllbar = ControllBar(root, controller)
        self.f = f
        self.ax = ax
        self.canvas = canvas
        self.controller = controller
        self.contours = []
        self.c_labels = None
        self.plot_kernels()

        self.control_key = False

    def plot_kernels(self):
        self.ax.text(-50, -60, "Linear: $u^T v$")
        self.ax.text(-20, -60, "RBF: $\exp (-\gamma \| u-v \|^2)$")
        self.ax.text(10, -60, "Poly: $(\gamma \, u^T v + r)^d$")

    def keypress(self, event):
        if event.key == 'control':
            self.control_key = True

    def keyrelease(self, event):
        if event.key == 'control':
            self.control_key = False
        
    def onclick(self, event):
        if event.xdata and event.ydata:
            if event.button == 1:
                if self.control_key:
                    self.controller.add_example(event.xdata, event.ydata, -1)
                else:
                    self.controller.add_example(event.xdata, event.ydata, 1)
            elif event.button in (2, 3):
                self.controller.add_example(event.xdata, event.ydata, -1)

    def update_example(self, model, idx):
        x, y, l = model.data[idx]
        if l == 1:
            color = 'w'
        elif l == -1:
            color = 'k'
        self.ax.plot([x], [y], "%so" % color, scalex=0.0, scaley=0.0)

    def update(self, event, model):
        if event == "examples_loaded":
            for i in xrange(len(model.data)):
                self.update_example(model, i)

        if event == "example_added":
            self.update_example(model, -1)

        if event == "clear":
            self.ax.clear()
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            self.contours = []
            self.c_labels = None
            self.plot_kernels()

        if event == "surface":
            self.remove_surface()
            self.plot_support_vectors(model.clf.support_vectors_)
            self.plot_decision_surface(model.surface, model.surface_type)

        self.canvas.draw()

    def remove_surface(self):
        """Remove old decision surface."""
        if len(self.contours) > 0:
            for contour in self.contours:
                if isinstance(contour, ContourSet):
                    for lineset in contour.collections:
                        lineset.remove()
                else:
                    contour.remove()
            self.contours = []

    def plot_support_vectors(self, support_vectors):
        """Plot the support vectors by placing circles over the
        corresponding data points and adds the circle collection
        to the contours list."""
        cs = self.ax.scatter(support_vectors[:, 0], support_vectors[:, 1],
                             s=80, edgecolors="k", facecolors="none")
        self.contours.append(cs)

    def plot_decision_surface(self, surface, type):
        X1, X2, Z = surface
        if type == 0:
            levels = [-1.0, 0.0, 1.0]
            linestyles = ['dashed', 'solid', 'dashed']
            colors = 'k'
            self.contours.append(self.ax.contour(X1, X2, Z, levels,
                                                 colors=colors,
                                                 linestyles=linestyles))
        elif type == 1:
            self.contours.append(self.ax.contourf(X1, X2, Z, 10,
                                             cmap=matplotlib.cm.bone,
                                             origin='lower',
                                             alpha=0.85))
            self.contours.append(self.ax.contour(X1, X2, Z, [0.0],
                                                 colors='k',
                                                 linestyles=['solid']))
        else:
            raise ValueError("surface type unknown")


class ControllBar(object):
    def __init__(self, root, controller):
        fm = Tk.Frame(root)
        kernel_group = Tk.Frame(fm)
        Tk.Radiobutton(kernel_group, text="Linear", variable=controller.kernel,
                       value=0, command=controller.refit).pack(anchor=Tk.W)
        Tk.Radiobutton(kernel_group, text="RBF", variable=controller.kernel,
                       value=1, command=controller.refit).pack(anchor=Tk.W)
        Tk.Radiobutton(kernel_group, text="Poly", variable=controller.kernel,
                       value=2, command=controller.refit).pack(anchor=Tk.W)
        kernel_group.pack(side=Tk.LEFT)

        valbox = Tk.Frame(fm)
        controller.complexity = Tk.StringVar()
        controller.complexity.set("1.0")
        c = Tk.Frame(valbox)
        Tk.Label(c, text="C:", anchor="e", width=7).pack(side=Tk.LEFT)
        Tk.Entry(c, width=6, textvariable=controller.complexity).pack(
            side=Tk.LEFT)
        c.pack()

        controller.gamma = Tk.StringVar()
        controller.gamma.set("0.01")
        g = Tk.Frame(valbox)
        Tk.Label(g, text="gamma:", anchor="e", width=7).pack(side=Tk.LEFT)
        Tk.Entry(g, width=6, textvariable=controller.gamma).pack(side=Tk.LEFT)
        g.pack()

        controller.degree = Tk.StringVar()
        controller.degree.set("3")
        d = Tk.Frame(valbox)
        Tk.Label(d, text="degree:", anchor="e", width=7).pack(side=Tk.LEFT)
        Tk.Entry(d, width=6, textvariable=controller.degree).pack(side=Tk.LEFT)
        d.pack()

        controller.coef0 = Tk.StringVar()
        controller.coef0.set("0")
        r = Tk.Frame(valbox)
        Tk.Label(r, text="coef0:", anchor="e", width=7).pack(side=Tk.LEFT)
        Tk.Entry(r, width=6, textvariable=controller.coef0).pack(side=Tk.LEFT)
        r.pack()
        valbox.pack(side=Tk.LEFT)

        cmap_group = Tk.Frame(fm)
        Tk.Radiobutton(cmap_group, text="Hyperplanes",
                       variable=controller.surface_type, value=0,
                       command=controller.refit).pack(anchor=Tk.W)
        Tk.Radiobutton(cmap_group, text="Surface",
                       variable=controller.surface_type, value=1,
                       command=controller.refit).pack(anchor=Tk.W)

        cmap_group.pack(side=Tk.LEFT)

        train_button = Tk.Button(fm, text='Fit', width=5,
                                 command=controller.fit)
        train_button.pack()
        fm.pack(side=Tk.LEFT)
        Tk.Button(fm, text='Clear', width=5,
                  command=controller.clear_data).pack(side=Tk.LEFT)


def get_parser():
    from optparse import OptionParser
    op = OptionParser()
    op.add_option("--output",
              action="store", type="str", dest="output",
              help="Path where to dump data.")
    return op


def run_gui():
    root = Tk.Tk()
    model = Model()
    controller = Controller(model)
    root.wm_title("Scikit-learn Libsvm GUI")
    view = View(root, controller)
    model.add_observer(view)
    Tk.mainloop()


def main(argv):
    op = get_parser()
    opts, args = op.parse_args(argv[1:])

    run_gui()

    if opts.output:
        model.dump_svmlight_file(opts.output)

if __name__ == "__main__":
    main(sys.argv)

########NEW FILE########
