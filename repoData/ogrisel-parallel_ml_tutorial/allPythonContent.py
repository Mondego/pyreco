__FILENAME__ = fetch_data
import numpy as np
import os
try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen
import tarfile
import zipfile
import gzip
from sklearn.datasets import load_files
from sklearn.externals import joblib


TWENTY_URL = ("http://people.csail.mit.edu/jrennie/"
              "20Newsgroups/20news-bydate.tar.gz")
TWENTY_ARCHIVE_NAME = "20news-bydate.tar.gz"
TWENTY_CACHE_NAME = "20news-bydate.pkz"
TWENTY_TRAIN_FOLDER = "20news-bydate-train"
TWENTY_TEST_FOLDER = "20news-bydate-test"

SENTIMENT140_URL = ("http://cs.stanford.edu/people/alecmgo/"
                    "trainingandtestdata.zip")
SENTIMENT140_ARCHIVE_NAME = "trainingandtestdata.zip"


COVERTYPE_URL = ('http://archive.ics.uci.edu/ml/'
                 'machine-learning-databases/covtype/covtype.data.gz')

# Source: https://www.kaggle.com/c/titanic-gettingStarted/data
TITANIC_URL = ("https://dl.dropboxusercontent.com/"
               "u/5743203/data/titanic/titanic_train.csv")


def get_datasets_folder():
    here = os.path.dirname(__file__)
    datasets_folder = os.path.abspath(os.path.join(here, 'datasets'))
    datasets_archive = os.path.abspath(os.path.join(here, 'datasets.zip'))

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
        opener = urlopen(TWENTY_URL)
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

    if not os.path.exists(archive_path):
        print("Downloading dataset from %s (77MB)" % SENTIMENT140_URL)
        opener = urlopen(SENTIMENT140_URL)
        open(archive_path, 'wb').write(opener.read())
    else:
        print("Found archive: " + archive_path)

    if not os.path.exists(sentiment140_path):
        print("Extracting %s to %s" % (archive_path, sentiment140_path))
        zf = zipfile.ZipFile(archive_path)
        zf.extractall(sentiment140_path)
    print("Checking that the sentiment 140 CSV files exist...")
    assert os.path.exists(train_path)
    assert os.path.exists(test_path)
    print("=> Success!")


def check_covertype(datasets_folder):
    print("Checking availability of the covertype dataset")
    archive_path = os.path.join(datasets_folder, 'covtype.data.gz')
    covtype_dir = os.path.join(datasets_folder, "covertype")
    samples_path = os.path.join(covtype_dir, "samples.pkl")
    targets_path = os.path.join(covtype_dir, "targets.pkl")

    if not os.path.exists(covtype_dir):
        os.makedirs(covtype_dir)

    if not os.path.exists(archive_path):
        print("Downloading dataset from %s (10.7MB)" % COVERTYPE_URL)
        open(archive_path, 'wb').write(urlopen(COVERTYPE_URL).read())
    else:
        print("Found archive: " + archive_path)

    if not os.path.exists(samples_path) or not os.path.exists(targets_path):
        print("Parsing the data and splitting input and labels...")
        f = open(archive_path, 'rb')
        Xy = np.genfromtxt(gzip.GzipFile(fileobj=f), delimiter=',')

        X = Xy[:, :-1]
        y = Xy[:, -1].astype(np.int32)

        joblib.dump(X, samples_path)
        joblib.dump(y, targets_path )
    print("=> Success!")


def check_titanic(datasets_folder):
    print("Checking availability of the titanic dataset")
    csv_filename = os.path.join(datasets_folder, 'titanic_train.csv')
    if not os.path.exists(csv_filename):
        print("Downloading titanic data from %s" % TITANIC_URL)
        open(csv_filename, 'wb').write(urlopen(TITANIC_URL).read())
    print("=> Success!")


if __name__ == "__main__":
    import sys
    datasets_folder = get_datasets_folder()
    check_twenty_newsgroups(datasets_folder)
    check_titanic(datasets_folder)
    if 'sentiment140' in sys.argv:
        check_sentiment140(datasets_folder)
    if 'covertype' in sys.argv:
        check_covertype(datasets_folder)
########NEW FILE########
__FILENAME__ = housekeeping
"""Utility script to be used to cleanup the notebooks before git commit"""

import shutil
import sys
import os
import io
from IPython.nbformat import current


def remove_outputs(nb):
    """Remove the outputs from a notebook"""
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                cell.outputs = []
                if 'prompt_number' in cell:
                    del cell['prompt_number']


def remove_solutions(nb):
    """Generate a version of the notebook with stripped exercises solutions"""
    for ws in nb.worksheets:
        inside_solution = False
        cells_to_remove = []
        for i, cell in enumerate(ws.cells):
            if cell.cell_type == 'heading':
                inside_solution = False
            elif cell.cell_type == 'markdown':
                first_line = cell.source.split("\n")[0].strip()
                if first_line.lower() in ("**exercise:**", "**exercise**:"):
                    inside_solution = True
                    # Insert a new code cell to work on the exercise
                    ws.cells.insert(i + 1, current.new_code_cell())
                    continue
            if inside_solution:
                if cell.cell_type == 'code' and not hasattr(cell, 'input'):
                    # Leave blank code cells
                    continue
                cells_to_remove.append(cell)
        for cell in cells_to_remove:
            ws.cells.remove(cell)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'clean':
        target = sys.argv[2]
        if os.path.isdir(target):
            fnames = [os.path.join(target, f)
                      for f in os.listdir(target)
                      if f.endswith('.ipynb')]
        else:
            fnames = [target]
        for fname in fnames:
            print("Removing outputs for: " + fname)
            with open(fname, 'r') as f:
                nb = current.read(f, 'json')
            remove_outputs(nb)
            with open(fname, 'w') as f:
                nb = current.write(nb, f, 'json')
    elif cmd == 'exercises':
        # Copy the images from the solutions to the notebooks folder
        solutions_images = os.path.join('solutions', 'images')
        notebooks_images = os.path.join('notebooks', 'images')
        if os.path.exists(notebooks_images):
            shutil.rmtree(notebooks_images)
        shutil.copytree(solutions_images, notebooks_images)

        # Generate the notebooks without the exercises solutions
        fnames = [f for f in os.listdir('solutions')
                  if f.endswith('.ipynb')]
        for fname in fnames:
            solution = os.path.join('solutions', fname)
            notebook = os.path.join('notebooks', fname)
            print("Generating solution-free notebook: " + notebook)
            with open(solution, 'r') as f:
                nb = current.read(f, 'json')
            remove_solutions(nb)
            remove_outputs(nb)
            with open(notebook, 'w') as f:
                nb = current.write(nb, f, 'json')
    else:
        print("Unsupported command")
        sys.exit(1)

########NEW FILE########
__FILENAME__ = mmap_utils
import os
from IPython.parallel import interactive


@interactive
def persist_cv_splits(X, y, name=None, n_cv_iter=5, suffix="_cv_%03d.pkl",
                      train_size=None, test_size=0.25, random_state=None,
                      folder='.'):
    """Materialize randomized train test splits of a dataset."""
    from sklearn.externals import joblib
    from sklearn.cross_validation import ShuffleSplit
    import os
    import uuid

    if name is None:
        name = uuid.uuid4().get_hex()

    cv = ShuffleSplit(X.shape[0], n_iter=n_cv_iter,
        test_size=test_size, random_state=random_state)
    cv_split_filenames = []

    for i, (train, test) in enumerate(cv):
        cv_fold = (X[train], y[train], X[test], y[test])
        cv_split_filename = os.path.join(folder, name + suffix % i)
        cv_split_filename = os.path.abspath(cv_split_filename)
        joblib.dump(cv_fold, cv_split_filename)
        cv_split_filenames.append(cv_split_filename)

    return cv_split_filenames


def warm_mmap_on_cv_splits(client, cv_split_filenames):
    """Trigger a disk load on all the arrays of the CV splits

    Assume the files are shared on all the hosts using NFS.
    """
    # First step: query cluster to fetch one engine id per host
    all_engines = client[:]

    @interactive
    def hostname():
        import socket
        return socket.gethostname()

    hostnames = all_engines.apply(hostname).get_dict()
    one_engine_per_host = dict((hostname, engine_id)
                               for engine_id, hostname
                               in hostnames.items())
    hosts_view = client[one_engine_per_host.values()]

    # Second step: for each data file and host, mmap the arrays of the file
    # and trigger a sequential read of all the arrays' data
    @interactive
    def load_in_memory(filenames):
        from sklearn.externals import joblib
        for filename in filenames:
            arrays = joblib.load(filename, mmap_mode='r')
            for array in arrays:
                array.sum()  # trigger the disk read

    cv_split_filenames = [os.path.abspath(f) for f in cv_split_filenames]
    hosts_view.apply_sync(load_in_memory, cv_split_filenames)
########NEW FILE########
__FILENAME__ = model_selection
"""Utilities for Parallel Model Selection with IPython

Author: Olivier Grisel <olivier@ogrisel.com>
Licensed: Simplified BSD
"""
from collections import namedtuple
import os

from IPython.parallel import interactive
from IPython.parallel import TaskAborted
from scipy.stats import sem
import numpy as np

from sklearn.utils import check_random_state
try:
    # sklearn 0.14+
    from sklearn.grid_search import ParameterGrid
except ImportError:
    # sklearn 0.13
    from sklearn.grid_search import IterGrid as ParameterGrid

from mmap_utils import warm_mmap_on_cv_splits
from mmap_utils import persist_cv_splits


def is_aborted(task):
    return isinstance(getattr(task, '_exception', None), TaskAborted)


@interactive
def compute_evaluation(model, cv_split_filename, params=None,
    train_fraction=1.0, mmap_mode='r'):
    """Function executed on a worker to evaluate a model on a given CV split"""
    # All module imports should be executed in the worker namespace
    from time import time
    from sklearn.externals import joblib

    X_train, y_train, X_test, y_test = joblib.load(
        cv_split_filename, mmap_mode=mmap_mode)

    # Slice a subset of the training set for plotting learning curves
    n_samples_train = int(train_fraction * X_train.shape[0])
    X_train = X_train[:n_samples_train]
    y_train = y_train[:n_samples_train]

    # Configure the model
    if model is not None:
        model.set_params(**params)

    # Fit model and measure training time
    t0 = time()
    model.fit(X_train, y_train)
    train_time = time() - t0

    # Compute score on training set
    train_score = model.score(X_train, y_train)

    # Compute score on test set
    test_score = model.score(X_test, y_test)

    # Wrap evaluation results in a simple tuple datastructure
    return (test_score, train_score, train_time,
            train_fraction, params)


# Named tuple to collect evaluation results
Evaluation = namedtuple('Evaluation', (
    'validation_score',
    'train_score',
    'train_time',
    'train_fraction',
    'parameters'))


class RandomizedGridSeach(object):
    """"Async Randomized Parameter search."""

    def __init__(self, load_balanced_view, random_state=0):
        self.task_groups = []
        self.lb_view = load_balanced_view
        self.random_state = random_state
        self._temp_files = []

    def map_tasks(self, f, skip_aborted=True):
        if skip_aborted:
            return [f(task) for task_group in self.task_groups
                            for task in task_group
                            if not is_aborted(task)]
        else:
            return [f(task) for task_group in self.task_groups
                            for task in task_group]

    def abort(self):
        for task_group in self.task_groups:
            for task in task_group:
                if not task.ready() and not is_aborted(task):
                    try:
                        task.abort()
                    except AssertionError:
                        pass
        return self

    def wait(self):
        self.map_tasks(lambda t: t.wait(), skip_aborted=True)
        return self

    def completed(self):
        return sum(self.map_tasks(lambda t: t.ready(), skip_aborted=True))

    def total(self):
        return sum(self.map_tasks(lambda t: 1, skip_aborted=False))

    def progress(self):
        c = self.completed()
        if c == 0:
            return 0.0
        else:
            return float(c) / self.total()

    def reset(self):
        # Abort any other previously scheduled tasks
        self.abort()

        # Schedule a new batch of evalutation tasks
        self.task_groups, self.all_parameters = [], []

        # Collect temporary files:
        for filename in self._temp_files:
            os.unlink(filename)
        del self._temp_files[:]

    def launch_for_splits(self, model, parameter_grid, cv_split_filenames,
        pre_warm=True, collect_files_on_reset=False):
        """Launch a Grid Search on precomputed CV splits."""

        # Abort any existing processing and erase previous state
        self.reset()
        self.parameter_grid = parameter_grid

        # Mark the files for garbage collection
        if collect_files_on_reset:
            self._temp_files.extend(cv_split_filenames)

        # Warm the OS disk cache on each host with sequential reads instead
        # of having concurrent evaluation tasks compete for the the same host
        # disk resources later.
        if pre_warm:
            warm_mmap_on_cv_splits(self.lb_view.client, cv_split_filenames)

        # Randomize the grid order
        random_state = check_random_state(self.random_state)
        self.all_parameters = list(ParameterGrid(parameter_grid))
        random_state.shuffle(self.all_parameters)

        for params in self.all_parameters:
            task_group = []

            for cv_split_filename in cv_split_filenames:
                task = self.lb_view.apply(compute_evaluation,
                    model, cv_split_filename, params=params)
                task_group.append(task)

            self.task_groups.append(task_group)

        # Make it possible to chain method calls
        return self

    def launch_for_arrays(self, model, parameter_grid, X, y, n_cv_iter=5, train_size=None,
                          test_size=0.25, pre_warm=True, folder=".", name=None,
                          random_state=None):
        cv_split_filenames = persist_cv_splits(
            X, y, n_cv_iter=n_cv_iter, train_size=train_size, test_size=test_size,
            name=name, folder=folder, random_state=random_state)
        return self.launch_for_splits(model, parameter_grid,
            cv_split_filenames, pre_warm=pre_warm, collect_files_on_reset=True)

    def find_bests(self, n_top=5):
        """Compute the mean score of the completed tasks"""
        mean_scores = []

        for params, task_group in zip(self.all_parameters, self.task_groups):
            evaluations = [Evaluation(*t.get())
                           for t in task_group
                           if t.ready() and not is_aborted(t)]

            if len(evaluations) == 0:
                continue
            val_scores = [e.validation_score for e in evaluations]
            train_scores = [e.train_score for e in evaluations]
            mean_scores.append((np.mean(val_scores), sem(val_scores),
                                np.mean(train_scores), sem(train_scores),
                                params))

        return sorted(mean_scores, reverse=True)[:n_top]

    def report(self, n_top=5):
        bests = self.find_bests(n_top=n_top)
        output = "Progress: {0:02d}% ({1:03d}/{2:03d})\n".format(
            int(100 * self.progress()), self.completed(), self.total())
        for i, best in enumerate(bests):
            output += ("\nRank {0}: validation: {1:.5f} (+/-{2:.5f})"
                       " train: {3:.5f} (+/-{4:.5f}):\n {5}".format(
                       i + 1, *best))
        return output

    def __repr__(self):
        return self.report()

    def boxplot_parameters(self, display_train=False):
        """Plot boxplot for each parameters independently"""
        import pylab as pl
        results = [Evaluation(*task.get())
                   for task_group in self.task_groups
                   for task in task_group
                   if task.ready() and not is_aborted(task)]

        n_rows = len(self.parameter_grid)
        pl.figure()
        for i, (param_name, param_values) in enumerate(self.parameter_grid.items()):
            pl.subplot(n_rows, 1, i + 1)
            val_scores_per_value = []
            train_scores_per_value = []
            for param_value in param_values:
                train_scores = [r.train_score for r in results
                                if r.parameters[param_name] == param_value]
                train_scores_per_value.append(train_scores)

                val_scores = [r.validation_score for r in results
                              if r.parameters[param_name] == param_value]
                val_scores_per_value.append(val_scores)

            widths = 0.25
            positions = np.arange(len(param_values)) + 1
            offset = 0
            if display_train:
                offset = 0.175
                pl.boxplot(train_scores_per_value, widths=widths,
                    positions=positions - offset)

            pl.boxplot(val_scores_per_value, widths=widths,
                positions=positions + offset)

            pl.xticks(np.arange(len(param_values)) + 1, param_values)
            pl.xlabel(param_name)
            pl.ylabel("Val. Score")

########NEW FILE########
