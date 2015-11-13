__FILENAME__ = fetch_data
import os
import urllib
import tarfile
import zipfile


TWENTY_URL = ("http://people.csail.mit.edu/jrennie/"
              "20Newsgroups/20news-bydate.tar.gz")
TWENTY_ARCHIVE_NAME = "20news-bydate.tar.gz"
TWENTY_CACHE_NAME = "20news-bydate.pkz"
TWENTY_TRAIN_FOLDER = "20news-bydate-train"
TWENTY_TEST_FOLDER = "20news-bydate-test"

SENTIMENT140_URL = ("http://cs.stanford.edu/people/alecmgo/"
                    "trainingandtestdata.zip")
SENTIMENT140_ARCHIVE_NAME = "trainingandtestdata.zip"


def get_datasets_folder():
    here = os.path.dirname(__file__)
    notebooks = os.path.join(here, 'notebooks')
    datasets_folder = os.path.abspath(os.path.join(notebooks, 'datasets'))
    datasets_archive = os.path.abspath(os.path.join(notebooks, 'datasets.zip'))

    if not os.path.exists(datasets_folder):
        if os.path.exists(datasets_archive):
            print("Extracting " + datasets_archive)
            zf = zipfile.ZipFile(datasets_archive)
            zf.extractall('.')
            assert os.path.exists(datasets_folder)
        else:
            print("Creating datasets folder: " + datasets_folder)
            os.makedirs(datasets_folder)
    else:
        print("Using existing dataset folder:" + datasets_folder)
    return datasets_folder


def check_twenty_newsgroups(datasets_folder):
    print("Checking availability of the 20 newsgroups dataset")

    archive_path = os.path.join(datasets_folder, TWENTY_ARCHIVE_NAME)
    train_path = os.path.join(datasets_folder, TWENTY_TRAIN_FOLDER)
    test_path = os.path.join(datasets_folder, TWENTY_TEST_FOLDER)

    if not os.path.exists(archive_path):
        print("Downloading dataset from %s (14 MB)" % TWENTY_URL)
        opener = urllib.urlopen(TWENTY_URL)
        open(archive_path, 'wb').write(opener.read())
    else:
        print("Found archive: " + archive_path)

    if not os.path.exists(train_path) or not os.path.exists(test_path):
        print("Decompressing %s" % archive_path)
        tarfile.open(archive_path, "r:gz").extractall(path=datasets_folder)

    print("Checking that the 20 newsgroups files exist...")
    assert os.path.exists(train_path)
    assert os.path.exists(test_path)
    print("=> Success!")


def check_sentiment140(datasets_folder):
    print("Checking availability of the sentiment 140 dataset")
    archive_path = os.path.join(datasets_folder, SENTIMENT140_ARCHIVE_NAME)
    sentiment140_path = os.path.join(datasets_folder, 'sentiment140')
    train_path = os.path.join(sentiment140_path,
                              'training.1600000.processed.noemoticon.csv')
    test_path = os.path.join(sentiment140_path,
                             'testdata.manual.2009.06.14.csv')

    if not os.path.exists(sentiment140_path):
        if not os.path.exists(archive_path):
            print("Downloading dataset from %s (77MB)" % SENTIMENT140_URL)
            opener = urllib.urlopen(SENTIMENT140_URL)
            open(archive_path, 'wb').write(opener.read())
        else:
            print("Found archive: " + archive_path)

        print("Extracting %s to %s" % (archive_path, sentiment140_path))
        zf = zipfile.ZipFile(archive_path)
        zf.extractall(sentiment140_path)
    print("Checking that the sentiment 140 CSV files exist...")
    assert os.path.exists(train_path)
    assert os.path.exists(test_path)
    print("=> Success!")


if __name__ == "__main__":
    datasets_folder = get_datasets_folder()
    check_twenty_newsgroups(datasets_folder)
    check_sentiment140(datasets_folder)

    print "Loading Labeled Faces Data (~200MB)"
    from sklearn.datasets import fetch_lfw_people
    fetch_lfw_people(min_faces_per_person=70, resize=0.4,
                     data_home=datasets_folder)
    print("=> Success!")

########NEW FILE########
__FILENAME__ = ipynbhelper
"""Utility script to be used to cleanup the notebooks before git commit

This a mix from @minrk's various gists.

"""

import sys
import os
import io
from Queue import Empty

from IPython.nbformat import current
try:
    from IPython.kernel import KernelManager
    assert KernelManager  # to silence pyflakes
except ImportError:
    # 0.13
    from IPython.zmq.blockingkernelmanager import BlockingKernelManager
    KernelManager = BlockingKernelManager


def remove_outputs(nb):
    """Remove the outputs from a notebook"""
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                cell.outputs = []
                if 'prompt_number' in cell:
                    del cell['prompt_number']


def run_cell(shell, iopub, cell, timeout=300):
    # print cell.input
    shell.execute(cell.input)
    # wait for finish, maximum 5min by default
    reply = shell.get_msg(timeout=timeout)['content']
    if reply['status'] == 'error':
        failed = True
        print "\nFAILURE:"
        print cell.input
        print '-----'
        print "raised:"
        print '\n'.join(reply['traceback'])
    else:
        failed = False

    # Collect the outputs of the cell execution
    outs = []
    while True:
        try:
            msg = iopub.get_msg(timeout=0.2)
        except Empty:
            break
        msg_type = msg['msg_type']
        if msg_type in ('status', 'pyin'):
            continue
        elif msg_type == 'clear_output':
            outs = []
            continue

        content = msg['content']
        # print msg_type, content
        out = current.NotebookNode(output_type=msg_type)

        if msg_type == 'stream':
            out.stream = content['name']
            out.text = content['data']
        elif msg_type in ('display_data', 'pyout'):
            for mime, data in content['data'].iteritems():
                attr = mime.split('/')[-1].lower()
                # this gets most right, but fix svg+html, plain
                attr = attr.replace('+xml', '').replace('plain', 'text')
                setattr(out, attr, data)
            if msg_type == 'pyout':
                out.prompt_number = content['execution_count']
        elif msg_type == 'pyerr':
            out.ename = content['ename']
            out.evalue = content['evalue']
            out.traceback = content['traceback']
        else:
            print "unhandled iopub msg:", msg_type

        outs.append(out)
    return outs, failed


def run_notebook(nb):
    km = KernelManager()
    km.start_kernel(stderr=open(os.devnull, 'w'))
    if hasattr(km, 'client'):
        kc = km.client()
        kc.start_channels()
        iopub = kc.iopub_channel
    else:
        # IPython 0.13 compat
        kc = km
        kc.start_channels()
        iopub = kc.sub_channel
    shell = kc.shell_channel

    # simple ping:
    shell.execute("pass")
    shell.get_msg()

    cells = 0
    failures = 0
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type != 'code':
                continue

            outputs, failed = run_cell(shell, iopub, cell)
            cell.outputs = outputs
            cell['prompt_number'] = cells
            failures += failed
            cells += 1
            sys.stdout.write('.')

    print
    print "ran notebook %s" % nb.metadata.name
    print "    ran %3i cells" % cells
    if failures:
        print "    %3i cells raised exceptions" % failures
    kc.stop_channels()
    km.shutdown_kernel()
    del km


def process_notebook_file(fname, action='clean', output_fname=None):
    print("Performing '{}' on: {}".format(action, fname))
    orig_wd = os.getcwd()
    with io.open(fname, 'rb') as f:
        nb = current.read(f, 'json')

    if action == 'check':
        os.chdir(os.path.dirname(fname))
        run_notebook(nb)
        remove_outputs(nb)
    elif action == 'render':
        os.chdir(os.path.dirname(fname))
        run_notebook(nb)
    else:
        # Clean by default
        remove_outputs(nb)

    os.chdir(orig_wd)
    if output_fname is None:
        output_fname = fname
    with io.open(output_fname, 'wb') as f:
        nb = current.write(nb, f, 'json')


if __name__ == '__main__':
    # TODO: use argparse instead
    args = sys.argv[1:]
    targets = [t for t in args if not t.startswith('--')]
    action = 'check' if '--check' in args else 'clean'
    action = 'render' if '--render' in args else action

    rendered_folder = os.path.join(os.path.dirname(__file__),
                                   'rendered_notebooks')
    if not os.path.exists(rendered_folder):
        os.makedirs(rendered_folder)
    if not targets:
        targets = [os.path.join(os.path.dirname(__file__), 'notebooks')]

    for target in targets:
        if os.path.isdir(target):
            fnames = [os.path.abspath(os.path.join(target, f))
                      for f in os.listdir(target)
                      if f.endswith('.ipynb')]
        else:
            fnames = [target]
        for fname in fnames:
            if action == 'render':
                output_fname = os.path.join(rendered_folder,
                                            os.path.basename(fname))
            else:
                output_fname = fname
            process_notebook_file(fname, action=action,
                                  output_fname=output_fname)

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
REFSPEC_URL = 'ftp://ftp.stsci.edu/cdbs/current_calspec/1732526_nic_002.ascii'
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
__FILENAME__ = helpers
"""
Small helpers for code that is not shown in the notebooks
"""

from sklearn import neighbors, datasets, linear_model
import pylab as pl
import numpy as np
from matplotlib.colors import ListedColormap

# Create color maps for 3-class classification problem, as with iris
cmap_light = ListedColormap(['#FFAAAA', '#AAFFAA', '#AAAAFF'])
cmap_bold = ListedColormap(['#FF0000', '#00FF00', '#0000FF'])

def plot_iris_knn():
    iris = datasets.load_iris()
    X = iris.data[:, :2]  # we only take the first two features. We could
                        # avoid this ugly slicing by using a two-dim dataset
    y = iris.target

    knn = neighbors.KNeighborsClassifier(n_neighbors=3)
    knn.fit(X, y)

    x_min, x_max = X[:, 0].min() - .1, X[:, 0].max() + .1
    y_min, y_max = X[:, 1].min() - .1, X[:, 1].max() + .1
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, 100),
                         np.linspace(y_min, y_max, 100))
    Z = knn.predict(np.c_[xx.ravel(), yy.ravel()])

    # Put the result into a color plot
    Z = Z.reshape(xx.shape)
    pl.figure()
    pl.pcolormesh(xx, yy, Z, cmap=cmap_light)

    # Plot also the training points
    pl.scatter(X[:, 0], X[:, 1], c=y, cmap=cmap_bold)
    pl.xlabel('sepal length (cm)')
    pl.ylabel('sepal width (cm)')
    pl.axis('tight')


def plot_polynomial_regression():
    rng = np.random.RandomState(0)
    x = 2*rng.rand(100) - 1

    f = lambda t: 1.2 * t**2 + .1 * t**3 - .4 * t **5 - .5 * t ** 9
    y = f(x) + .4 * rng.normal(size=100)

    x_test = np.linspace(-1, 1, 100)

    pl.figure()
    pl.scatter(x, y, s=4)

    X = np.array([x**i for i in range(5)]).T
    X_test = np.array([x_test**i for i in range(5)]).T
    regr = linear_model.LinearRegression()
    regr.fit(X, y)
    pl.plot(x_test, regr.predict(X_test), label='4th order')

    X = np.array([x**i for i in range(10)]).T
    X_test = np.array([x_test**i for i in range(10)]).T
    regr = linear_model.LinearRegression()
    regr.fit(X, y)
    pl.plot(x_test, regr.predict(X_test), label='9th order')

    pl.legend(loc='best')
    pl.axis('tight')
    pl.title('Fitting a 4th and a 9th order polynomial')

    pl.figure()
    pl.scatter(x, y, s=4)
    pl.plot(x_test, f(x_test), label="truth")
    pl.axis('tight')
    pl.title('Ground truth (9th order polynomial)')



########NEW FILE########
__FILENAME__ = 02A_faces_plot
faces = fetch_olivetti_faces()

# set up the figure
fig = plt.figure(figsize=(6, 6))  # figure size in inches
fig.subplots_adjust(left=0, right=1, bottom=0, top=1, hspace=0.05, wspace=0.05)

# plot the faces:
for i in range(64):
    ax = fig.add_subplot(8, 8, i + 1, xticks=[], yticks=[])
    ax.imshow(faces.images[i], cmap=plt.cm.bone, interpolation='nearest')

########NEW FILE########
__FILENAME__ = 04B_houses_regression
from sklearn.ensemble import GradientBoostingRegressor

clf = GradientBoostingRegressor()
clf.fit(X_train, y_train)

predicted = clf.predict(X_test)
expected = y_test

plt.scatter(expected, predicted)
plt.plot([0, 50], [0, 50], '--k')
plt.axis('tight')
plt.xlabel('True price ($1000s)')
plt.ylabel('Predicted price ($1000s)')
print "RMS:", np.sqrt(np.mean((predicted - expected) ** 2))

########NEW FILE########
__FILENAME__ = 04C_validation_exercise
# suppress warnings from older versions of KNeighbors
import warnings
warnings.filterwarnings('ignore', message='kneighbors*')

X = digits.data
y = digits.target
X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, y, test_size=0.25, random_state=0)

for Model in [LinearSVC, GaussianNB, KNeighborsClassifier]:
    clf = Model().fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    print Model.__name__, metrics.f1_score(y_test, y_pred)
    
print '------------------'

# test SVC loss
for loss in ['l1', 'l2']:
    clf = LinearSVC(loss=loss).fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    print "LinearSVC(loss='{0}')".format(loss), metrics.f1_score(y_test, y_pred)
    
print '-------------------'
    
# test K-neighbors
for n_neighbors in range(1, 11):
    clf = KNeighborsClassifier(n_neighbors=n_neighbors).fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    print "KNeighbors(n_neighbors={0})".format(n_neighbors), metrics.f1_score(y_test, y_pred)

########NEW FILE########
__FILENAME__ = 05B_strip_headers
def strip_headers(post):
    """Find the first blank line and drop the headers to keep the body"""
    if '\n\n' in post:
        headers, body = post.split('\n\n', 1)
        return body.lower()
    else:
        # Unexpected post inner-structure, be conservative
        # and keep everything
        return post.lower()

# Let's try it on the first post. Here is the original post content,
# including the headers:

original_text = all_twenty_train.data[0]
print("Oringinal text:")
print(original_text + "\n")

text_body = strip_headers(original_text)
print("Stripped text:")
print(text_body + "\n")

# Let's train a new classifier with the header stripping preprocessor

strip_vectorizer = TfidfVectorizer(preprocessor=strip_headers, min_df=2)
X_train_small_stripped = strip_vectorizer.fit_transform(
    twenty_train_small.data)

y_train_small_stripped = twenty_train_small.target

classifier = MultinomialNB(alpha=0.01).fit(
  X_train_small_stripped, y_train_small_stripped)

print("Training score: {0:.1f}%".format(
    classifier.score(X_train_small_stripped, y_train_small_stripped) * 100))

X_test_small_stripped = strip_vectorizer.transform(twenty_test_small.data)
y_test_small_stripped = twenty_test_small.target
print("Testing score: {0:.1f}%".format(
    classifier.score(X_test_small_stripped, y_test_small_stripped) * 100))
########NEW FILE########
__FILENAME__ = 06B_basic_grid_search
for Model in [Lasso, Ridge]:
    scores = [cross_val_score(Model(alpha), X, y, cv=3).mean()
              for alpha in alphas]
    plt.plot(alphas, scores, label=Model.__name__)
plt.legend(loc='lower left')

########NEW FILE########
__FILENAME__ = 06B_learning_curves
from sklearn.metrics import explained_variance_score, mean_squared_error
from sklearn.cross_validation import train_test_split

def plot_learning_curve(model, err_func=explained_variance_score, N=300, n_runs=10, n_sizes=50, ylim=None):
    sizes = np.linspace(5, N, n_sizes).astype(int)
    train_err = np.zeros((n_runs, n_sizes))
    validation_err = np.zeros((n_runs, n_sizes))
    for i in range(n_runs):
        for j, size in enumerate(sizes):
            xtrain, xtest, ytrain, ytest = train_test_split(
                X, y, train_size=size, random_state=i)
            # Train on only the first `size` points
            model.fit(xtrain, ytrain)
            validation_err[i, j] = err_func(ytest, model.predict(xtest))
            train_err[i, j] = err_func(ytrain, model.predict(xtrain))

    plt.plot(sizes, validation_err.mean(axis=0), lw=2, label='validation')
    plt.plot(sizes, train_err.mean(axis=0), lw=2, label='training')

    plt.xlabel('traning set size')
    plt.ylabel(err_func.__name__.replace('_', ' '))
    
    plt.grid(True)
    
    plt.legend(loc=0)
    
    plt.xlim(0, N-1)
    
    if ylim:
        plt.ylim(ylim)


plt.figure(figsize=(10, 8))
for i, model in enumerate([Lasso(0.01), Ridge(0.06)]):
    plt.subplot(221 + i)
    plot_learning_curve(model, ylim=(0, 1))
    plt.title(model.__class__.__name__)
    
    plt.subplot(223 + i)
    plot_learning_curve(model, err_func=mean_squared_error, ylim=(0, 8000))

########NEW FILE########
__FILENAME__ = 07B_grid_search
np.random.seed(42)
for model in [DecisionTreeRegressor(),
              GradientBoostingRegressor(),
              RandomForestRegressor()]:
    parameters = {'max_depth':[3, 5, 7, 9, 11]}

    # Warning: be sure your data is shuffled before using GridSearch!
    clf_grid = grid_search.GridSearchCV(model, parameters)
    clf_grid.fit(X, y_noisy)
    print '------------------------'
    print model.__class__.__name__
    print clf_grid.best_params_
    print clf_grid.best_score_

########NEW FILE########
__FILENAME__ = 08A_digits_projection
from sklearn.decomposition import PCA
from sklearn.manifold import Isomap, LocallyLinearEmbedding

plt.figure(figsize=(14, 4))
for i, est in enumerate([PCA(n_components=2, whiten=True),
                         Isomap(n_components=2, n_neighbors=10),
                         LocallyLinearEmbedding(n_components=2, n_neighbors=10, method='modified')]):
    plt.subplot(131 + i)
    projection = est.fit_transform(digits.data)
    plt.scatter(projection[:, 0], projection[:, 1], c=digits.target)
    plt.title(est.__class__.__name__)

########NEW FILE########
__FILENAME__ = 08B_digits_clustering
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=10)
clusters = kmeans.fit_predict(digits.data)

print kmeans.cluster_centers_.shape

#------------------------------------------------------------
# visualize the cluster centers
fig = plt.figure(figsize=(8, 3))
for i in range(10):
    ax = fig.add_subplot(2, 5, 1 + i)
    ax.imshow(kmeans.cluster_centers_[i].reshape((8, 8)),
              cmap=plt.cm.binary)
from sklearn.manifold import Isomap
X_iso = Isomap(n_neighbors=10).fit_transform(digits.data)

#------------------------------------------------------------
# visualize the projected data
fig, ax = plt.subplots(1, 2, figsize=(8, 4))

ax[0].scatter(X_iso[:, 0], X_iso[:, 1], c=clusters)
ax[1].scatter(X_iso[:, 0], X_iso[:, 1], c=digits.target)

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
from __future__ import division, print_function

print(__doc__)

# Author: Peter Prettenhoer <peter.prettenhofer@gmail.com>
#
# License: BSD 3 clause

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
from sklearn.externals.six.moves import xrange

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
        print("fit the model")
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
            print("Accuracy:", clf.score(X, y) * 100)
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

    def plot_kernels(self):
        self.ax.text(-50, -60, "Linear: $u^T v$")
        self.ax.text(-20, -60, "RBF: $\exp (-\gamma \| u-v \|^2)$")
        self.ax.text(10, -60, "Poly: $(\gamma \, u^T v + r)^d$")

    def onclick(self, event):
        if event.xdata and event.ydata:
            if event.button == 1:
                self.controller.add_example(event.xdata, event.ydata, 1)
            elif event.button == 3:
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
                                                  origin='lower', alpha=0.85))
            self.contours.append(self.ax.contour(X1, X2, Z, [0.0], colors='k',
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


def main(argv):
    op = get_parser()
    opts, args = op.parse_args(argv[1:])
    root = Tk.Tk()
    model = Model()
    controller = Controller(model)
    root.wm_title("Scikit-learn Libsvm GUI")
    view = View(root, controller)
    model.add_observer(view)
    Tk.mainloop()

    if opts.output:
        model.dump_svmlight_file(opts.output)

if __name__ == "__main__":
    main(sys.argv)

########NEW FILE########
