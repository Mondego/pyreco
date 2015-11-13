__FILENAME__ = common
"""IPython.parallel helpers.

Author: Olivier Grisel <olivier@ogrisel.com>
Licensed: MIT
"""

from IPython.parallel import TaskAborted
from IPython.parallel import interactive


def is_aborted(task):
    return isinstance(getattr(task, '_exception', None), TaskAborted)


class TaskManager(object):
    """Base class for managing tasks and groups of tasks"""

    def all_tasks(self, skip_aborted=True):
        all_tasks = []
        all_tasks += getattr(self, 'tasks', [])

        task_groups = getattr(self, 'task_groups', [])
        all_tasks += [t for task_group in task_groups
                        for t in task_group]

        if skip_aborted:
            all_tasks = [t for t in all_tasks if not is_aborted(t)]

        return all_tasks

    def map_tasks(self, f, skip_aborted=True):
        return map(f, self.all_tasks(skip_aborted=skip_aborted))

    def abort(self):
        for task in self.all_tasks(skip_aborted=True):
            if not task.ready():
                try:
                    task.abort()
                except AssertionError:
                    pass
        return self

    def wait(self):
        self.map_tasks(lambda t: t.wait(), skip_aborted=True)
        return self

    def completed_tasks(self):
        return [t for t in self.all_tasks(skip_aborted=True) if t.ready()]

    def completed(self):
        return sum(self.map_tasks(lambda t: t.ready(), skip_aborted=True))

    def done(self):
        return all(self.map_tasks(lambda t: t.ready(), skip_aborted=True))

    def total(self):
        return sum(self.map_tasks(lambda t: 1, skip_aborted=False))

    def progress(self):
        c = self.completed()
        if c == 0:
            return 0.0
        else:
            return float(c) / self.total()

    def elapsed(self):
        all_tasks = self.all_tasks(skip_aborted=False)
        if not all_tasks:
            return 0.0
        return max([t.elapsed for t in all_tasks])


def get_host_view(client):
    """Return an IPython parallel direct view with one engine per host."""
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
    return client[one_engine_per_host.values()]

########NEW FILE########
__FILENAME__ = ensemble
"""Tools for build ensembles on distributed compute resources

Author: Olivier Grisel <olivier@ogrisel.com>
Licensed: MIT
"""

import uuid
import os
from random import Random
from copy import copy

from IPython.parallel import interactive

from sklearn.base import clone
from sklearn.externals import joblib
from pyrallel.common import TaskManager
from pyrallel.mmap_utils import host_dump


# Python 2 & 3 compat
try:
    basestring
except NameError:
    basestring = (str, bytes)


def combine(all_ensembles):
    """Combine the sub-estimators of a group of ensembles

        >>> from sklearn.datasets import load_iris
        >>> from sklearn.ensemble import ExtraTreesClassifier
        >>> iris = load_iris()
        >>> X, y = iris.data, iris.target

        >>> all_ensembles = [ExtraTreesClassifier(n_estimators=4).fit(X, y)
        ...                  for i in range(3)]
        >>> big = combine(all_ensembles)
        >>> len(big.estimators_)
        12
        >>> big.n_estimators
        12
        >>> big.score(X, y)
        1.0

        >>> big2 = combine(all_ensembles)
        >>> len(big2.estimators_)
        12

    """
    final_ensemble = copy(all_ensembles[0])
    final_ensemble.estimators_ = []

    for ensemble in all_ensembles:
        final_ensemble.estimators_ += ensemble.estimators_

    # Required in old versions of sklearn
    final_ensemble.n_estimators = len(final_ensemble.estimators_)

    return final_ensemble


def sub_ensemble(ensemble, n_estimators, seed=None):
    """Build a new ensemble with a random subset of the sub-estimators

        >>> from sklearn.datasets import load_iris
        >>> from sklearn.ensemble import ExtraTreesClassifier
        >>> iris = load_iris()
        >>> X, y = iris.data, iris.target

        >>> big = ExtraTreesClassifier(n_estimators=10).fit(X, y)
        >>> small = sub_ensemble(big, 3)
        >>> len(small.estimators_)
        3
        >>> small.n_estimators
        3
        >>> small.score(X, y)
        1.0

    """
    rng = Random(seed)
    final_ensemble = copy(ensemble)
    if n_estimators > len(ensemble.estimators_):
        raise ValueError(
            "Cannot sample %d estimators from ensemble of %d"
            % (n_estimators, len(ensemble.estimators_)))

    final_ensemble.estimators_ = rng.sample(
        ensemble.estimators_, n_estimators)

    # Required in old versions of sklearn
    final_ensemble.n_estimators = len(final_ensemble.estimators_)

    return final_ensemble


@interactive
def train_model(model, data_filename, model_filename=None,
                random_state=None):
    from sklearn.externals import joblib

    # Memory map the data
    X, y, sample_weight = joblib.load(data_filename, mmap_mode='r')

    # Train the model
    model.set_params(random_state=random_state)
    if sample_weight is not None:
        model.fit(X, y, sample_weight=sample_weight)
    else:
        model.fit(X, y)

    # Clean the random_state attributes to reduce the amount
    # of useless numpy arrays that will be created on the
    # filesystem (fixed upstream in sklearn 0.15-git)
    for estimator in model.estimators_:
        if (hasattr(estimator, 'tree_')
                and hasattr(estimator.tree_, 'random_state')):
            estimator.tree_.random_state = 0

    # Save the model back to the FS as it can be large
    if model_filename is not None:
        joblib.dump(model, model_filename)
        return model_filename

    # TODO: add support for cloud blob stores as an alternative to
    # filesystems.

    # Return the tree back to the caller if (useful if the drive)
    return model


class EnsembleGrower(TaskManager):
    """Distribute computation of sklearn ensembles

    This works for averaging ensembles like random forests
    or bagging ensembles.

    Does not work with sequential ensembles such as AdaBoost or
    GBRT.

    """

    def __init__(self, load_balanced_view, base_model):
        self.tasks = []
        self.base_model = base_model
        self.lb_view = load_balanced_view
        self._temp_files = []

    def reset(self):
        # Abort any other previously scheduled tasks
        self.abort()

        # Forget about the old tasks
        self.tasks[:] = []

        # Collect temporary files:
        for filename in self._temp_files:
            os.unlink(filename)
        del self._temp_files[:]

    def launch(self, X, y, sample_weight=None, n_estimators=1, pre_warm=True,
               folder=".", name=None, dump_models=False):
        self.reset()
        if name is None:
            name = uuid.uuid4().get_hex()

        if not os.path.exists(folder):
            os.makedirs(folder)

        data_filename = os.path.join(folder, name + '_data.pkl')
        data_filename = os.path.abspath(data_filename)

        # Dispatch the data files to all the nodes
        host_dump(self.lb_view.client, (X, y, sample_weight), data_filename,
                  pre_warm=pre_warm)

        # TODO: handle temporary files on all remote workers
        #self._temp_files.extend(dumped_filenames)

        for i in range(n_estimators):
            base_model = clone(self.base_model)
            if dump_models:
                model_filename = os.path.join(
                    folder, name + '_model_%03d.pkl' % i)
                model_filename = os.path.abspath(model_filename)
            else:
                model_filename = None
            self.tasks.append(self.lb_view.apply(
                train_model, base_model, data_filename, model_filename,
                random_state=i))
        # Make it possible to chain method calls
        return self

    def report(self, n_top=5):
        output = ("Progress: {0:02d}% ({1:03d}/{2:03d}),"
                  " elapsed: {3:0.3f}s\n").format(
            int(100 * self.progress()), self.completed(), self.total(),
            self.elapsed())
        return output

    def __repr__(self):
        return self.report()

    def aggregate_model(self, mmap_mode='r'):
        ready_models = []
        for task in self.completed_tasks():
            result = task.get()
            if isinstance(result, basestring):
                result = joblib.load(result, mmap_mode=mmap_mode)
            ready_models.append(result)

        if not ready_models:
            return None
        return combine(ready_models)

########NEW FILE########
__FILENAME__ = mmap_utils
"""Utilities for Memory Mapping cross validation folds

Author: Olivier Grisel <olivier@ogrisel.com>
Licensed: MIT
"""
import os
from IPython.parallel import interactive

from pyrallel.common import get_host_view


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
        # TODO: make it possible to ship the CV folds on each host for
        # non-NFS setups.
        cv_split_filenames.append(cv_split_filename)

    return cv_split_filenames


def warm_mmap(client, data_filenames, host_view=None):
    """Trigger a disk load on all the arrays data_filenames.

    Assume the files are shared on all the hosts using NFS or
    have been previously been dumped there with the host_dump function.
    """
    if host_view is None:
        host_view = get_host_view(client)

    # Second step: for each data file and host, mmap the arrays of the file
    # and trigger a sequential read of all the arrays' data
    @interactive
    def load_in_memory(filenames):
        from sklearn.externals import joblib
        for filename in filenames:
            arrays = joblib.load(filename, mmap_mode='r')
            for array in arrays:
                if hasattr(array, 'max'):
                    array.max()  # trigger the disk read

    data_filenames = [os.path.abspath(f) for f in data_filenames]
    host_view.apply_sync(load_in_memory, data_filenames)


# Backward compat
warm_mmap_on_cv_splits = warm_mmap


def _missing_file_engine_ids(view, filename):
    """Return the list of engine ids where filename does not exist"""

    @interactive
    def missing(filename):
        import os
        return not os.path.exists(filename)

    missing_ids = []
    for id_, is_missing in view.apply(missing, filename).get_dict().items():
        if is_missing:
            missing_ids.append(id_)
    return missing_ids


def host_dump(client, payload, target_filename, host_view=None, pre_warm=True):
    """Send payload to each host and dump it on the filesystem

    Nothing is done in case the file already exists.

    The payload is shipped only once per node in the cluster.

    """
    if host_view is None:
        host_view = get_host_view(client)

    client = host_view.client

    @interactive
    def dump_payload(payload, filename):
        from sklearn.externals import joblib
        import os
        folder = os.path.dirname(filename)
        if not os.path.exists(folder):
            os.makedirs(folder)
        return joblib.dump(payload, filename)

    missing_ids = _missing_file_engine_ids(host_view, target_filename)
    if missing_ids:
        first_id = missing_ids[0]

        # Do a first dispatch to the first node to avoid concurrent write in
        # case of shared filesystem
        client[first_id].apply_sync(dump_payload, payload, target_filename)

        # Refetch the list of engine ids where the file is missing
        missing_ids = _missing_file_engine_ids(host_view, target_filename)

        # Restrict the view to hosts where the target data file is still
        # missing for the final dispatch
        client[missing_ids].apply_sync(dump_payload, payload, target_filename)

    if pre_warm:
        warm_mmap(client, [target_filename], host_view=host_view)

########NEW FILE########
__FILENAME__ = model_selection
"""Utilities for Parallel Model Selection with IPython

Author: Olivier Grisel <olivier@ogrisel.com>
Licensed: MIT
"""
from time import sleep
from collections import namedtuple
import os

from IPython.parallel import interactive
from IPython.display import clear_output
from scipy.stats import sem
import numpy as np

from sklearn.utils import check_random_state
from sklearn.grid_search import ParameterGrid

from pyrallel.common import TaskManager
from pyrallel.common import is_aborted
from pyrallel.mmap_utils import warm_mmap_on_cv_splits
from pyrallel.mmap_utils import persist_cv_splits




@interactive
def compute_evaluation(model, cv_split_filename, params=None,
                       train_size=1.0, mmap_mode='r',
                       scoring=None, dump_model=False,
                       dump_predictions=False, dump_folder='.'):
    """Evaluate a model on a given CV split"""
    # All module imports should be executed in the worker namespace to make
    # possible to run an an engine node.
    from time import time
    from sklearn.externals import joblib

    X_train, y_train, X_test, y_test = joblib.load(
        cv_split_filename, mmap_mode=mmap_mode)

    # Slice a subset of the training set for plotting learning curves
    if train_size <= 1.0:
        # Assume that train_size is an relative fraction of the number of
        # samples
        n_samples_train = int(train_size * X_train.shape[0])
    else:
        # Assume that train_size is an absolute number of samples
        n_samples_train = int(train_size)
    X_train = X_train[:n_samples_train]
    y_train = y_train[:n_samples_train]

    # Configure the model
    if model is not None:
        model.set_params(**params)

    # Fit model and measure training time
    tick = time()
    model.fit(X_train, y_train)
    train_time = time() - tick

    # Compute score on training set
    train_score = model.score(X_train, y_train)

    # Compute score on test set
    test_score = model.score(X_test, y_test)

    # Wrap evaluation results in a simple tuple datastructure
    return (test_score, train_score, train_time,
            train_size, params)


# Named tuple to collect evaluation results
Evaluation = namedtuple('Evaluation', (
    'validation_score',
    'train_score',
    'train_time',
    'train_fraction',
    'parameters'))


class RandomizedGridSeach(TaskManager):
    """"Async Randomized Parameter search."""

    def __init__(self, load_balanced_view, random_state=0):
        self.task_groups = []
        self.lb_view = load_balanced_view
        self.random_state = random_state
        self._temp_files = []

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
                task = self.lb_view.apply(
                    compute_evaluation,
                    model, cv_split_filename, params=params)
                task_group.append(task)

            self.task_groups.append(task_group)

        # Make it possible to chain method calls
        return self

    def launch_for_arrays(self, model, parameter_grid, X, y, n_cv_iter=5,
                          train_size=None, test_size=0.25, pre_warm=True,
                          folder=".", name=None, random_state=None):
        cv_split_filenames = persist_cv_splits(
            X, y, n_cv_iter=n_cv_iter, train_size=train_size,
            test_size=test_size, name=name, folder=folder,
            random_state=random_state)
        return self.launch_for_splits(
            model, parameter_grid, cv_split_filenames, pre_warm=pre_warm,
            collect_files_on_reset=True)

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
        grid_items = self.parameter_grid.items()
        for i, (param_name, param_values) in enumerate(grid_items):
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
                pl.boxplot(
                    train_scores_per_value, widths=widths,
                    positions=positions - offset)

            pl.boxplot(
                val_scores_per_value, widths=widths,
                positions=positions + offset)

            pl.xticks(np.arange(len(param_values)) + 1, param_values)
            pl.xlabel(param_name)
            pl.ylabel("Val. Score")

    def monitor(self, plot=False):
        try:
            while not self.done():
                self.lb_view.spin()
                if plot:
                    import pylab as pl
                    pl.clf()
                    self.boxplot_parameters()
                clear_output()
                print(self.report())
                if plot:
                    pl.show()
                sleep(1)
        except KeyboardInterrupt:
            print("Monitoring interrupted.")

########NEW FILE########
