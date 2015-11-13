__FILENAME__ = dataset
from __future__ import division
import copper
import pandas as pd


class Dataset(dict):
    """ Wrapper around pandas.DataFrame introducing metadata to the different
    variables/columns making easier to interate in manual machine learning
    feature learning. Also provides access to basic data transformation such as
    string to numbers.
    Finally provides a convinient interface to the copper.ModelComparison
    utilities.

    Parameters
    ----------
    data : pandas.DataFrame

    Examples
    --------
    >>> df = pandas.read_cvs('a_csv_file.csv')
    >>> ds = copper.Dataset(df)

    >>> df = pd.DataFrame(np.random.rand(3, 3))
    >>> ds = copper.Dataset(df)
    >>> ds.frame
             0    1    2
        0  0.9  0.1  0.6
        1  0.7  0.6  0.8
        2  0.4  0.4  0.6
    >>> ds.metadata
                 Role      Type    dtype
        Columns
        0        Input    Number  float64
        1        Input    Number  float64
        2        Input    Number  float64
    """

    IGNORE = 'Ignore'
    INPUT = 'Input'
    TARGET = 'Target'
    NUMBER = 'Number'
    CATEGORY = 'Category'

    def __init__(self, data=None):
        self.role = pd.Series()
        self.type = pd.Series()
        self._frame = pd.DataFrame()
        if data is not None:
            self.frame = data

# -----------------------------------------------------------------------------
#                               Properties

    def get_frame(self):
        """ Return the pandas.DataFrame

        Examples
        --------
        >>> ds.frame
                 0    1    2    3    4    5
            0  0.9  0.1  0.6  0.9  0.4  0.8
            1  0.7  0.6  0.8  0.1  0.1  0.0
            2  0.4  0.4  0.6  0.8  0.2  0.7
            3  0.7  0.2  0.9  0.9  0.8  0.6
            4  0.5  0.7  0.6  0.0  0.2  0.0
        """
        return self._frame

    def set_frame(self, frame):
        """ Set the data of the dataset.

        When used recreates the metadata.

        Examples
        --------
        >>> ds.frame = pd.DataFrame(...)
        """
        assert type(frame) is pd.DataFrame, 'should be a pandas.DataFrame'

        recreate = True
        if len(self._frame.columns) > 0:
            if len(frame.columns) == len(self._frame.columns):
                if (frame.columns == self._frame.columns).all():
                    recreate = False
        if recreate:
            columns = frame.columns
            self.role = pd.Series(name='Role', index=columns, dtype=object)
            self.type = pd.Series(name='Type', index=columns, dtype=object)
            if not frame.empty:
                self.role[:] = self.INPUT
                self.type[:] = self.NUMBER
                self.type[frame.dtypes == object] = self.CATEGORY

        self._frame = frame

    def get_metadata(self):
        """ Return the pandas.DataFrame

        Returns
        -------
        pandas.DataFrame

        Examples
        --------
        >>> ds.metadata
                      Role      Type    dtype
            Columns
            0        Input  Category   object
            1        Input    Number  float64
            2        Input    Number  float64
            3        Input  Category   object
            4        Input    Number  float64
            5        Input    Number  float64
        """
        metadata = pd.DataFrame(index=self._frame.columns)
        metadata.index.name = 'Columns'
        metadata['Role'] = self.role
        metadata['Type'] = self.type
        metadata['dtype'] = [] if len(metadata) == 0 else self._frame.dtypes.values
        return metadata

    def set_metadata(self, metadata):
        """ Sets metadata

        Notes
        -----
        The new metadata index needs to match previous metadata index
        (columns of the DataFrame) in order to work

        See Also
        --------
        copper.Dataset.match
        """
        assert type(metadata) is pd.DataFrame, 'should be a pandas.DataFrame'
        assert len(self.metadata) == len(metadata), \
            'Length is not consistent, try Dataset.copy_metadata instead'
        assert (self.metadata.index.values == metadata.index.values).all(), \
            'Index is not consistent, try Dataset.copy_metadata instead'
        self.role = metadata['Role']
        self.type = metadata['Type']

    def copy_metadata(self, metadata, ignoreMissing=True):
        """ Copies the metadata from another dataset or dataframe

        Parameters
        ----------
        ignoreMissing: boolean
            If True (deafult) is going to ignore (do not modify)
            the variables that are not on the new metadata.
            if False is going to make role of variables not present on the
            new metadata "IGNORE"

        Returns
        -------

        """
        if isinstance(metadata, Dataset):
            metadata = metadata.metadata  # Brain damage

        if not ignoreMissing:
            self.role[:] = self.IGNORE
        for col in self.columns:
            if col in metadata.index:
                self.role[col] = metadata['Role'][col]
                self.type[col] = metadata['Type'][col]

    def get_columns(self):
        """ Returns the columns of the frame

        Examples
        --------
        >>> ds.columns == df.frame.columns
            True
        """
        return self._frame.columns

    def get_index(self):
        """ Returns the index of the frame

        Examples
        --------
        >>> ds.index == df.frame.index
            True
        """
        return self._frame.index

    frame = property(get_frame, set_frame, None, 'pandas.DataFrame')
    metadata = property(get_metadata, set_metadata, None, 'pandas.DataFrame')
    columns = property(get_columns, None, None)
    index = property(get_index, None, None)

    def __getitem__(self, name):
        return self._frame[name]

    def __setitem__(self, name, value):
        self._frame[name] = value

    def __len__(self):
        return len(self._frame)

    def __str__(self):
        return self.metadata.__str__()

    def __unicode__(self):
        return self.metadata.__unicode__()

# -----------------------------------------------------------------------------
#                            Functions

    def update(self):
        """ Updates the DataFrame based on the metadata.
        Transforms strings to numbers using regular expression.
        """
        for col in self._frame.columns:
            if self.type[col] == self.NUMBER and self._frame[col].dtype == object:
                self._frame[col] = self._frame[col].apply(copper.t.to_float)

    def filter_cols(self, role=None, type=None):
        """ Returns a list of the columns that matches the criterias.

        Parameters
        ----------
        role : list or string
        type : list or string

        Returns
        -------
        list with the columns names

        Examples
        --------
        >>> ds.filter_cols(role=ds.INPUT)
            ... list ...
        >>> ds.filter_cols(role=ds.INPUT, type=ds.CATEGORY)
            ... list ...
        """
        def _type(obj):
            return obj.__class__

        if role is None:
            role = [self.INPUT, self.TARGET, self.IGNORE]
        elif _type(role) == str:
            role = [role]
        if type is None:
            type = [self.NUMBER, self.CATEGORY]
        elif _type(type) == str:
            type = [type]

        return [col for col in self._frame.columns.tolist()
                if self.role[col] in role and self.type[col] in type]

    def filter(self, role=None, type=None):
        """ Returns a pandas.DataFrame with the variables that match the
        criterias.

        Parameters
        ----------
        role : list or string
        type : list or string

        Returns
        -------
        pandas.DataFrame

        Examples
        --------
        >>> ds.filter() == ds.frame
            True
        >>> ds.filter(role=ds.INPUT)
            ... pd.DataFrame ...
        >>> ds.filter(role=ds.INPUT, type=ds.CATEGORY)
            ... pd.DataFrame ...
        """
        return self._frame[self.filter_cols(role, type)]

# -----------------------------------------------------------------------------
#                               Pandas API

    def head(self, *args, **kwargs):
        return self._frame.head(*args, **kwargs)

    def tail(self, *args, **kwargs):
        return self._frame.tail(*args, **kwargs)

'''
import math
import random
import copper
import numpy as np
import pandas as pd

from nose.tools import raises
from copper.tests.utils import eq_




if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)
'''

########NEW FILE########
__FILENAME__ = compare
import copper
import numpy as np
import pandas as pd
from sklearn import cross_validation

# Metrics
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score
from sklearn.metrics import auc_score
from sklearn.metrics import average_precision_score
from sklearn.metrics import f1_score
from sklearn.metrics import fbeta_score
from sklearn.metrics import hinge_loss
from sklearn.metrics import matthews_corrcoef
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import zero_one_loss


class ModelComparison(dict):
    """ Utility for easy model(algorithm) comparison.
    Can use only numpy arrays or copper.Dataset to generate the training and
    testing datasets.

    Note: Designed to work with sklearn algorithms (extending BaseEstimator)
    but not necesary if the algorithm matches the basic sklearn API:
    algo.fit, algo.predict, algo.predict_proba

    Parameters
    ----------

    Examples
    --------
    >>> train = copper.Dataset(...)
    >>> test = copper.Dataset(...)
    >>> mc = copper.ModelComparison(...)
    >>> from sklearn.linear_model import LogisticRegression
    >>> mc['LR'] = LogisticRegression()
    >>> mc['LR with p=l1'] = LogisticRegression(penalty='l1')
    >>> mc.fit()
    >>> mc.predict()
    np.array([[...]])
    """

    def __init__(self):
        self.algorithms = {}
        self.X_train = None
        self.y_train = None
        self.X_test = None
        self.y_test = None
        self.le = None

# -----------------------------------------------------------------------------
#                               Properties

    def get_train(self):
        return self.X_train, self.y_train

    def set_train(self, dataset):
        assert type(dataset) is copper.Dataset, "Should be a copper.Dataset"
        self.X_train = copper.t.ml_inputs(dataset)
        self.le, self.y_train = copper.t.ml_target(dataset)

    def get_test(self):
        return self.X_test, self.y_test

    def set_test(self, dataset):
        assert type(dataset) is copper.Dataset, "Should be a copper.Dataset"
        self.X_test = copper.t.ml_inputs(dataset)
        _, self.y_test = copper.t.ml_target(dataset)

    train = property(get_train, set_train, None)
    test = property(get_test, set_test, None)

    def train_test_split(self, dataset, **args):
        """ Random split of a copper.Datasetinto a training and testing
        datasets

        Arguments are the same as: sklearn.cross_validation.train_test_split
        only test_size is necessary.

        Parameters
        ----------
        test_size: float percentage of the dataset used for testing
            between 0 and 1.
        """
        assert type(dataset) is copper.Dataset, "Should be a copper.Dataset"
        inputs = copper.t.ml_inputs(dataset)
        self.le, target = copper.t.ml_target(dataset)
        self.X_train, self.X_test, self.y_train, self.y_test = \
            cross_validation.train_test_split(inputs, target, **args)

    def __getitem__(self, name):
        return self.algorithms[name]

    def __setitem__(self, name, value):
        self.algorithms[name] = value

    def __delitem__(self, name):
        del self.algorithms[name]

    def __len__(self):
        return len(self.algorithms)

# -----------------------------------------------------------------------------

    def parse_entries(self, X_test=None, y_test=None):
        """ DRY: Small utility used inside of the class.
        """
        if X_test is None and y_test is None:
            X_test = self.X_test
            y_test = self.y_test
        elif isinstance(X_test, copper.Dataset):
            X_test = copper.transforms.ml_inputs(X_test)
            _, y_test = copper.transforms.ml_target(X_test)
        assert X_test is not None, 'Nothing to predict'
        return X_test, y_test

# -----------------------------------------------------------------------------
#                              Sklearn API

    def fit(self):
        for algorithm in self.algorithms:
            self.algorithms[algorithm].fit(self.X_train, self.y_train)

    def predict(self, X_test=None):
        X_test, _ = self.parse_entries(X_test, None)

        ans = pd.DataFrame(index=range(len(X_test)))
        for alg_name in self.algorithms:
            algo = self.algorithms[alg_name]
            scores = algo.predict(X_test)
            new = pd.Series(scores, index=ans.index, name=alg_name, dtype=int)
            ans = ans.join(new)
        return ans

    def predict_proba(self, X_test=None):
        X_test, _ = self.parse_entries(X_test, None)

        ans = pd.DataFrame(index=range(len(X_test)))
        for alg_name in self.algorithms:
            algo = self.algorithms[alg_name]
            probas = algo.predict_proba(X_test)
            for val in range(probas.shape[1]):
                new = pd.Series(probas[:, val], index=ans.index)
                new.name = '%s [%d]' % (alg_name, val)
                ans = ans.join(new)
        return ans

# -----------------------------------------------------------------------------
#                             Sklearn metrics

    def metric(self, func, X_test=None, y_test=None, name='', ascending=False, **args):
        X_test, y_test = self.parse_entries(X_test, y_test)

        ans_index = []
        ans_value = []
        for alg_name in self.algorithms:
            algo = self.algorithms[alg_name]
            y_pred = algo.predict(X_test)
            scores = func(y_test, y_pred, **args)

            if isinstance(scores, np.ndarray):
                for i, score in enumerate(scores):
                    lbl = str(i) if self.le is None else self.le.inverse_transform(i)
                    ans_index.append('%s (%s)' % (alg_name, lbl))
                    ans_value.append(score)
            else:
                ans_index.append(alg_name)
                ans_value.append(scores)
        return pd.Series(ans_value, index=ans_index).order(ascending=ascending)

    def accuracy_score(self, **args):
        return self.metric(accuracy_score, name='Accuracy', **args)

    def auc_score(self, **args):
        return self.metric(auc_score, name='AUC', **args)

    def average_precision_score(self, **args):
        return self.metric(average_precision_score, name='Avg Precision', **args)

    def f1_score(self, **args):
        return self.metric(f1_score, name='F1', **args)

    def fbeta_score(self, beta=1, **args):
        return self.metric(fbeta_score, name='Fbeta', beta=beta, **args)

    def hinge_loss(self, **args):
        return self.metric(hinge_loss, name='Hinge loss', **args)

    def matthews_corrcoef(self, **args):
        return self.metric(matthews_corrcoef, name='Matthews Coef', **args)

    def precision_score(self, **args):
        return self.metric(precision_score, name='Precision', **args)

    def recall_score(self, **args):
        return self.metric(recall_score, name='Recall', **args)

    def zero_one_loss(self, **args):
        return self.metric(zero_one_loss, name='Zero one loss', ascending=True, **args)

# -----------------------------------------------------------------------------
#                              Confusion matrix

    def _cm(self, X_test=None, y_test=None):
        '''
        Calculates the confusion matrixes of the classifiers

        Parameters
        ----------
            clfs: list or str, of the classifiers to calculate the cm

        Returns
        -------
            python dictionary
        '''
        X_test, y_test = self.parse_entries(X_test, y_test)

        ans = {}
        for alg_name in self.algorithms:
            algo = self.algorithms[alg_name]
            y_pred = algo.predict(self.X_test)
            ans[alg_name] = confusion_matrix(y_test, y_pred)
        return ans

    def cm(self, clf, X_test=None, y_test=None):
        '''
        Return a pandas.DataFrame version of a confusion matrix

        Parameters
        ----------
            clf: str, classifier identifier
        '''
        cm = self._cm(X_test, y_test)[clf]
        values = self.le.inverse_transform(np.unique(self.y_test))
        return pd.DataFrame(cm, index=values, columns=values)

'''
import math
import random
import copper
import numpy as np
import pandas as pd
from sklearn import cross_validation
from sklearn.linear_model import LogisticRegression

from nose.tools import raises, ok_
from copper.tests.utils import eq_


def get_iris():
    from sklearn import datasets
    iris = datasets.load_iris()

    X = iris.data
    Y = iris.target
    return X, Y

def get_iris_ds():
    X, Y = get_iris()
    df = pd.DataFrame(X)
    df['Target'] = pd.Series(Y, name='Target')

    ds = copper.Dataset(df)
    ds.role['Target'] = ds.TARGET
    return ds

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)
'''

########NEW FILE########
__FILENAME__ = dbn
from __future__ import division
import math
import json
import numpy as np
from sklearn.base import BaseEstimator

from rbm import RBM
from layers import SigmoidLayer
from copper.utils import opti as MBOpti
from utils import sigmoid
from sklearn.neural_network import BernoulliRBM

from copper.utils.progress import ProgressBar  # import last


def cost(weights, X, y, layers, num_labels):
    output = layers[0].output(X)
    for layer in layers[1:]:
        output = layer.output(output)

    Y = np.eye(num_labels)[y]
    h = output
    costPositive = -Y * np.log(h)
    costNegative = (1 - Y) * np.log(1 - h)
    return np.sum(costPositive - costNegative) / X.shape[0]


def cost_prime(weights, X, y, layers, num_labels):
    Y = np.eye(num_labels)[y]
    Deltas = [np.zeros((l.n_in + 1, l.n_out)) for l in layers]

    for i, row in enumerate(X):
        # Forward
        output = row
        activations = (output, )
        for layer in layers:
            output = layer.output(output)
            activations = activations + (output, )

        # Backprop
        prev_delta = activations[-1] - Y[i, :].T
        deltas = (prev_delta, )

        for act, layer in zip(reversed(activations[1:-1]), reversed(layers)):
            delta = np.dot(layer.W, prev_delta) * (act * (1 - act)).T
            deltas = (delta, ) + deltas
            prev_delta = delta

        # Accumulate errors
        for delta, act, i in zip(deltas, activations[:-1], range(len(Deltas))):
            act = np.append(1, act)  # Bias unit = 1
            Deltas[i] = Deltas[i] + np.dot(delta[np.newaxis].T, act[np.newaxis]).T

    for i in range(len(Deltas)):
        Deltas[i] = Deltas[i] / X.shape[0]

    return np.concatenate(tuple([D.reshape(-1) for D in Deltas]))


class DBN(BaseEstimator):

    def __init__(self, hidden_layers, coef0=None, random_state=None,
                 progress_bars=False,
                 pretrain_batch_size=100,
                 pretrain_epochs=0, pretrain_batches_per_epoch=-1,
                 pretrain_callback=None,
                 finetune_method='GD', finetune_batch_size=50,
                 finetune_epochs=1, finetune_batches_per_epoch=-1,
                 finetune_options=None, finetune_callback=None):
        self.hidden_layers = hidden_layers
        self.coef_ = None if coef0 is None else np.copy(coef0)

        if random_state is None:
            self.rnd = np.random.RandomState()
        elif isinstance(random_state, int):
            self.rnd = np.random.RandomState(random_state)
        else:
            self.rnd = random_state

        self.progress_bars = progress_bars

        self.pretrain_batch_size = pretrain_batch_size
        self.pretrain_epochs = pretrain_epochs
        self.pretrain_batches_per_epoch = pretrain_batches_per_epoch
        self.pretrain_callback = pretrain_callback
        self.finetune_method = finetune_method
        self.finetune_batch_size = finetune_batch_size
        self.finetune_epochs = finetune_epochs
        self.finetune_batches_per_epoch = finetune_batches_per_epoch

        self.finetune_options = {} if finetune_options is None else finetune_options
        self.finetune_callback = finetune_callback

    def build_net(self, n_in, n_out):
        layers = [n_in]
        layers.extend(self.hidden_layers)
        layers.append(n_out)
        self.weights_info = [(layers[i], layers[i + 1]) for i in range(len(layers) - 1)]

        self.layers = list()
        for w_info in self.weights_info:
            n_in = w_info[0]
            n_out = w_info[1]
            self.layers.append(SigmoidLayer(n_in=n_in, n_out=n_out, random_state=self.rnd))

    def assign_weights(self):
        start_pos = 0
        for layer in self.layers:
            n_in = layer.W.shape[0]
            n_out = layer.W.shape[1]

            end_pos = start_pos + n_out
            layer.b = self.coef_[start_pos:end_pos]

            start_pos = end_pos
            end_pos = start_pos + n_in * n_out
            layer.W = self.coef_[start_pos:end_pos].reshape((n_in, n_out))
            start_pos = end_pos

    def save(self, filepath):
        info = {}
        info['metadata'] = self.weights_info
        info['weights'] = self.coef_.tolist()
        with open(filepath, 'w') as outfile:
            json.dump(info, outfile)

    def load(self, filepath):
        with open(filepath, 'r') as infile:
            info = json.load(infile)
            weight_info = info['metadata']
            n_in = weight_info[0][0]
            n_out = weight_info[-1][1]
            self.build_net(n_in, n_out)
            self.coef_ = np.array(info['weights'])
            self.assign_weights()

    def fit(self, X, y):
        self.build_net(X.shape[1], len(np.unique(y)))

        # Assign weights of layers as views of the big weights
        if self.coef_ is None:
            ws = list()
            for layer in self.layers:
                ws.append(layer.b.reshape(-1))
                ws.append(layer.W.reshape(-1))
            self.coef_ = np.concatenate(tuple(ws))
            self.assign_weights()

        # Pretrain
        if self.pretrain_epochs > 0:
            if self.progress_bars:
                if self.pretrain_batches_per_epoch == -1:
                    batches_per_epoch = int(X.shape[0] / self.pretrain_batch_size)
                else:
                    batches_per_epoch = self.pretrain_batches_per_epoch

                maxiters = self.pretrain_epochs * batches_per_epoch * len(self.layers)
                pt_bar = ProgressBar(max=maxiters, desc='Pretrain')

            if self.pretrain_batch_size == -1:
                # Use full-batch
                self.pretrain_batch_size = X.shape[0]

            # Create RBM layers using the same weights
            self.rbm_layers = []
            for i, layer in enumerate(self.layers):
                n_hid = layer.W.shape[1]
                new = RBM(layer)
                self.rbm_layers.append(new)

            # Actual pretrain
            for i, rbm_layer in enumerate(self.rbm_layers):
                for epoch in range(self.pretrain_epochs):
                    mb = MBOpti.minibatches(X, batch_size=self.pretrain_batch_size,
                                 batches=self.pretrain_batches_per_epoch,
                                 random_state=self.rnd)

                    for j, batch in enumerate(mb):
                        if i == 0:
                            input = batch
                        else:
                            # input = self.layers[i - 1].output(batcn)
                            try:
                                input = self.layers[i - 1].sample_h_given_v(input)
                            except:
                                print input.shape, self.layers[i-1].W.shape
                                raise Exception('1')

                        rbm_layer.contrastive_divergence(input)
                        if self.progress_bars:
                            pt_bar.next()
                        if self.pretrain_callback is not None:
                            stop = self.pretrain_callback(self, layer, epoch + 1, j + 1)
                            if stop == True:
                                break

            if self.progress_bars:
                pt_bar.complete()

        # Finetune
        if self.finetune_epochs > 0:
            if self.progress_bars:
                if self.finetune_batches_per_epoch == -1:
                    batches_per_epoch = int(X.shape[0] / self.finetune_batch_size)
                else:
                    batches_per_epoch = self.finetune_batches_per_epoch

                maxiters = self.finetune_epochs * batches_per_epoch
                ft_bar = ProgressBar(max=maxiters, desc='Finetune')
            def _callback(epoch, i):
                if self.progress_bars:
                    ft_bar.next()
                if self.finetune_callback is not None:
                    return self.finetune_callback(self, epoch, i)

            self.finetune_options = self.finetune_options.copy()
            args = (self.layers, len(np.unique(y)))
            MBOpti.minimize(self.coef_, X, y, fun=cost, grad=cost_prime, weights=self.coef_,
                            method=self.finetune_method,
                            epochs=self.finetune_epochs, batch_size=self.finetune_batch_size,
                            batches_per_epoch=self.finetune_batches_per_epoch,
                            options=self.finetune_options, args=args, callback=_callback,
                            random_state=self.rnd)

            if self.progress_bars:
                ft_bar.complete()

    def predict_proba(self, X):
        output = self.layers[0].output(X)
        for layer in self.layers[1:]:
            output = layer.output(output)
        return output

    def predict(self, X):
        return self.predict_proba(X).argmax(1)

########NEW FILE########
__FILENAME__ = layers
# -*- coding: utf-8 -*-
import numpy as np
from utils import softmax, sigmoid


class Layer(object):
    def __init__(self, n_in=None, n_out=None, W=None, b=None, random_state=None, activation=None):
        if random_state is None:
            self.rnd = np.random.RandomState()
        elif isinstance(random_state, int):
            self.rnd = np.random.RandomState(random_state)
        else:
            self.rnd = random_state

        if W is None and b is None:
            if n_in is not None and n_out is not None:
                gap = 4 * np.sqrt(6. / (n_in + n_out))
                self.b = np.zeros(n_out)
                self.W = self.rnd.uniform(low=-gap, high=gap, size=(n_in, n_out))
                self.n_in = self.W.shape[0]
                self.n_out = self.W.shape[1]
        else:
            self.W = W
            self.b = b
            self.n_in = self.W.shape[0]
            self.n_out = self.W.shape[1]

        self.activation = activation

    def output(self, input):
        linear_output = np.dot(input, self.W) + self.b
        return self.activation(linear_output)

    def sample_h_given_v(self, input):
        v_mean = self.output(input)
        h_sample = self.rnd.binomial(size=v_mean.shape, n=1, p=v_mean)
        return h_sample


class LogisticLayer(Layer):
    def __init__(self, *args, **kwargs):
        Layer.__init__(self, *args, activation=softmax, **kwargs)


class SigmoidLayer(Layer):
    def __init__(self, *args, **kwargs):
        Layer.__init__(self, *args, activation=sigmoid, **kwargs)

########NEW FILE########
__FILENAME__ = rbm
# -*- coding: utf-8 -*-
from __future__ import division
import numpy as np


class RBM(object):
    '''
    Note: this class was taken from yusugomori RBM
    https://github.com/yusugomori/DeepLearning/blob/master/python/RBM.py
    I modified the class to match my requirements but basicly is the same thing.
    '''
    def __init__(self, input_layer, learning_rate=0.1, random_state=None):
        self.input_layer = input_layer
        self.learning_rate = learning_rate
        self.activation = input_layer.activation

        if random_state is None:
            self.np_rng = np.random.RandomState()
        else:
            self.np_rng = random_state

        self.n_visible = input_layer.W.shape[0]
        self.n_hidden = input_layer.W.shape[1]
        self.W = input_layer.W

        self.hbias = input_layer.b
        self.vbias = np.zeros(self.n_visible)

    def contrastive_divergence(self, input, lr=0.3, k=1):
        ph_mean, ph_sample = self.sample_h_given_v(input)

        for step in xrange(k):
            if step == 0:
                nv_means, nv_samples, nh_means, nh_samples = self.gibbs_hvh(ph_sample)
            else:
                nv_means, nv_samples, nh_means, nh_samples = self.gibbs_hvh(nh_samples)


        self.W += lr * (np.dot(input.T, ph_sample) -
                        np.dot(nv_samples.T, nh_means)) / input.shape[0]
        self.vbias += lr * np.mean(input - nv_samples, axis=0)
        self.hbias += lr * np.mean(ph_sample - nh_means, axis=0)


    def sample_h_given_v(self, v0_sample):
        h1_mean = self.propup(v0_sample)
        h1_sample = self.np_rng.binomial(size=h1_mean.shape, n=1, p=h1_mean)
        return [h1_mean, h1_sample]


    def sample_v_given_h(self, h0_sample):
        v1_mean = self.propdown(h0_sample)
        v1_sample = self.np_rng.binomial(size=v1_mean.shape, n=1, p=v1_mean)
        return [v1_mean, v1_sample]

    def propup(self, v):
        pre_activation = np.dot(v, self.W) + self.hbias
        return self.activation(pre_activation)

    def propdown(self, h):
        pre_sigmoid_activation = np.dot(h, self.W.T) + self.vbias
        return self.activation(pre_sigmoid_activation)

    def gibbs_hvh(self, h0_sample):
        v1_mean, v1_sample = self.sample_v_given_h(h0_sample)
        h1_mean, h1_sample = self.sample_h_given_v(v1_sample)
        return v1_mean, v1_sample, h1_mean, h1_sample


    def get_reconstruction_cross_entropy(self, input):
        pre_activation_h = np.dot(input, self.W) + self.hbias
        sigmoid_activation_h = self.activation(pre_activation_h)

        pre_sigmoid_activation_v = np.dot(sigmoid_activation_h, self.W.T) + self.vbias
        sigmoid_activation_v = self.activation(pre_sigmoid_activation_v)

        return - np.mean(np.sum(input * np.log(sigmoid_activation_v) +
                         (1 - input) * np.log(1 - sigmoid_activation_v),
                                  axis=1))

    def reconstruct(self, v):
        h = sigmoid(np.dot(v, self.W) + self.hbias)
        reconstructed_v = sigmoid(np.dot(h, self.W.T) + self.vbias)
        return reconstructed_v

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import division
import numpy as np


def softmax(x):
    e = np.exp(x - np.max(x))  # prevent overflow
    if e.ndim == 1:
        return e / np.sum(e, axis=0)
    else:
        return e / np.array([np.sum(e, axis=1)]).T  # ndim = 2


def sigmoid(x):
    return 1. / (1 + np.exp(-x))

########NEW FILE########
__FILENAME__ = activationFunctions
"""
 Copyright (c) 2011,2012 George Dahl

 Permission is hereby granted, free of charge, to any person  obtaining
 a copy of this software and associated documentation  files (the
 "Software"), to deal in the Software without  restriction, including
 without limitation the rights to use,  copy, modify, merge, publish,
 distribute, sublicense, and/or sell  copies of the Software, and to
 permit persons to whom the  Software is furnished to do so, subject
 to the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.  THE
 SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT  HOLDERS
 BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,  WHETHER IN AN
 ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING  FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR  OTHER DEALINGS IN THE
 SOFTWARE.
"""


import numpy as num
import gnumpy as gnp

#NOTATION:
#we use y_l for the output of layer l
#y_0 is input
#
#we use x_l for the net input so, using * as matrix multiply and h_l
#for the elementwise activation function of layer l,
#x_l = y_{l-1} * W_l + b_l
#y_l = h_l(x_l)
#
#A neural net with L layers implements the function f(y_0, W) = y_L where
#y_0 is the input to the network and W represents all of the weights
#and biases of the network.
#We train neural nets to minimize some error function
# error(y, t) for fixed targets t.
#So given training inputs y_0 and targets t we minimize the function
#Error(W) = error( f(y_0, W), t)
#
#An activation function suitable for use as a hidden layer
#nonlinearity defines the following methods:
# 1A. activation(netInput)
# 2A. dEdNetInput(acts)
#
#An activation function suitable for use as the output layer
#nonlinearity defines the following methods in addiction to 1A:
# 1B. error(targets, netInput, acts = None)
# 2B. dErrordNetInput(targets, netInput, acts = None)
# 3.  HProd(vect, acts)
#
# 1B takes as an argument the net input to the output units because
# sometimes having that quantity allows the loss to be computed in a
# more numerically stable way. Optionally, 1B also takes the output
# unit activations, since sometimes that allows a more efficient
# computation of the loss.
#
# For "matching" error functions and output activation functions 2B
# should be just acts-targets.
# The difference between 2B and 2A (above) is that 2B incorporates the
# training criterion error(y,t) instead of just the error *at the
# output of this layer* the way 2A does.
#
# HProd gives the product of the H_{L,M} Hessian (Notation from "Fast
# Curvature Matrix-Vector Products for Second-Order Gradient Descent
# by N. Schraudolph) with a vector.

#If gnumpy gets replaced and a logOnePlusExp is needed, be sure to make it numerically stable.
#def logOnePlusExp(x):
#    # log(1+exp(x)) when x < 0 and
#    # x + log(1+exp(-x)) when x > 0


class Sigmoid(object):
    def activation(self, netInput):
        return netInput.sigmoid()
    def dEdNetInput(self, acts):
        return acts*(1-acts)
    def error(self, targets, netInput, acts = None):
        #return (targets*logOnePlusExp(-netInput) + (1-targets)*logOnePlusExp(netInput)).sum()
        #return (logOnePlusExp(netInput)-targets*netInput).sum()
        return (netInput.log_1_plus_exp()-targets*netInput).sum()
    def HProd(self, vect, acts):
        return vect*acts*(1-acts)
    def dErrordNetInput(self, targets, netInput, acts = None):
        if acts == None:
            acts = self.activation(netInput)
        return acts - targets

#You can write tanh in terms of sigmoid.
#def tanh(ar):
#    return 2*(2*ar).sigmoid()-1
# There might be a "better" tanh to use based on Yann LeCun's
# efficient backprop paper, but I forget what the constants A and B
# are in A * tanh ( B * x).
class Tanh(object):
    def activation(self, netInput):
        return gnp.tanh(netInput)
    def dEdNetInput(self, acts):
        return 1-acts*acts

class ReLU(object):
    def activation(self, netInput):
        return netInput*(netInput > 0)
    def dEdNetInput(self, acts):
        return acts > 0

class Linear(object):
    def activation(self, netInput):
        return netInput
    def dEdNetInput(self, acts):
        return 1 #perhaps returning ones(acts.shape) is more appropriate?
    def error(self, targets, netInput, acts = None):
        diff = targets-netInput
        return 0.5*(diff*diff).sum()
    def HProd(self, vect, acts):
        return vect
    def dErrordNetInput(self, targets, netInput, acts = None):
        if acts == None:
            acts = self.activation(netInput)
        return acts - targets

class Softmax(object):
    def activation(self, netInput):
        Zshape = (netInput.shape[0],1)
        acts = netInput - netInput.max(axis=1).reshape(*Zshape)
        acts = acts.exp()
        return acts/acts.sum(axis=1).reshape(*Zshape)
    def HProd(self, vect, acts):
        return acts*(vect-(acts*vect).sum(1).reshape(-1,1))
    def dErrordNetInput(self, targets, netInput, acts = None):
        if acts == None:
            acts = self.activation(netInput)
        return acts - targets
    def error(self, targets, netInput, acts = None):
        ntInpt = netInput - netInput.max(axis=1).reshape(netInput.shape[0],1)
        logZs = ntInpt.exp().sum(axis=1).log().reshape(-1,1)
        err = targets*(ntInpt - logZs)
        return -err.sum()







########NEW FILE########
__FILENAME__ = core
"""
 Copyright (c) 2011,2012 George Dahl

 Permission is hereby granted, free of charge, to any person  obtaining
 a copy of this software and associated documentation  files (the
 "Software"), to deal in the Software without  restriction, including
 without limitation the rights to use,  copy, modify, merge, publish,
 distribute, sublicense, and/or sell  copies of the Software, and to
 permit persons to whom the  Software is furnished to do so, subject
 to the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.  THE
 SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT  HOLDERS
 BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,  WHETHER IN AN
 ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING  FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR  OTHER DEALINGS IN THE
 SOFTWARE.
"""

import numpy as num
import gnumpy as gnp
import itertools
from activationFunctions import *
from pretrain import CD1
from pretrain import Binary as RBMBinary
from pretrain import Gaussian as RBMGaussian
from pretrain import ReLU as RBMReLU
from counter import Progress

class DummyProgBar(object):
    def __init__(self, *args): pass
    def tick(self): pass
    def done(self): pass

def initWeightMatrix(shape, scale, maxNonZeroPerColumn = None, uniform = False):
    #number of nonzero incoming connections to a hidden unit
    fanIn = shape[0] if maxNonZeroPerColumn==None else min(maxNonZeroPerColumn, shape[0])
    if uniform:
        W = scale*(2*num.random.rand(*shape)-1)
    else:
        W = scale*num.random.randn(*shape)
    for j in range(shape[1]):
        perm = num.random.permutation(shape[0])
        W[perm[fanIn:],j] *= 0
    return W

def validShapes(weights, biases):
    if len(weights) + 1 == len(biases):
        t1 = all(b.shape[0] == 1 for b in biases)
        t2 = all(wA.shape[1] == wB.shape[0] for wA, wB in zip(weights[:-1], weights[1:]))
        t3 = all(w.shape[1] == hb.shape[1] for w, hb in zip(weights, biases[1:]))
        t4 = all(w.shape[0] == vb.shape[1] for w, vb in zip(weights, biases[:-1]))
        return t1 and t2 and t3 and t4
    return False

def garrayify(arrays):
    return [ar if isinstance(ar, gnp.garray) else gnp.garray(ar) for ar in arrays]

def numpyify(arrays):
    return [ar if isinstance(ar, num.ndarray) else ar.as_numpy_array(dtype=num.float32) for ar in arrays]

def loadDBN(path, outputActFunct, realValuedVis = False, useReLU = False):
    fd = open(path, 'rb')
    d = num.load(fd)
    weights = garrayify(d['weights'].flatten())
    biases = garrayify(d['biases'].flatten())
    genBiases = []
    if 'genBiases' in d:
        genBiases = garrayify(d['genBiases'].flatten())
    fd.close()
    return DBN(weights, biases, genBiases, outputActFunct, realValuedVis, useReLU)

def buildDBN(layerSizes, scales, fanOuts, outputActFunct, realValuedVis, useReLU = False, uniforms = None):
    shapes = [(layerSizes[i-1],layerSizes[i]) for i in range(1, len(layerSizes))]
    assert(len(scales) == len(shapes) == len(fanOuts))
    if uniforms == None:
        uniforms = [False for s in shapes]
    assert(len(scales) == len(uniforms))

    initialBiases = [gnp.garray(0*num.random.rand(1, layerSizes[i])) for i in range(1, len(layerSizes))]
    initialGenBiases = [gnp.garray(0*num.random.rand(1, layerSizes[i])) for i in range(len(layerSizes) - 1)]
    initialWeights = [gnp.garray(initWeightMatrix(shapes[i], scales[i], fanOuts[i], uniforms[i])) \
                      for i in range(len(shapes))]

    net = DBN(initialWeights, initialBiases, initialGenBiases, outputActFunct, realValuedVis, useReLU)
    return net

def columnRMS(W):
    return gnp.sqrt(gnp.mean(W*W,axis=0))

def limitColumnRMS(W, rmsLim):
    """
    All columns of W with rms entry above the limit are scaled to equal the limit.
    The limit can either be a row vector or a scalar.
    """
    rmsScale = rmsLim/columnRMS(W)
    return W*(1 + (rmsScale < 1)*(rmsScale-1))

class DBN(object):
    def __init__(self, initialWeights, initialBiases, initialGenBiases, outputActFunct, realValuedVis = False, useReLU = False):
        self.realValuedVis = realValuedVis
        self.learnRates = [0.05 for i in range(len(initialWeights))]
        self.momentum = 0.9
        self.L2Costs = [0.0001 for i in range(len(initialWeights))]
        self.dropouts = [0 for i in range(len(initialWeights))]
        self.nesterov = False
        self.nestCompare = False
        self.rmsLims = [None for i in range(len(initialWeights))]

        if self.realValuedVis:
            self.learnRates[0] = 0.005

        self.weights = initialWeights
        self.biases = initialBiases
        self.genBiases = initialGenBiases

        if useReLU:
            self.RBMHidUnitType = RBMReLU()
            self.hidActFuncts = [ReLU() for i in range(len(self.weights) - 1)]
        else:
            self.RBMHidUnitType = RBMBinary()
            self.hidActFuncts = [Sigmoid() for i in range(len(self.weights) - 1)]
        self.outputActFunct = outputActFunct

        #state variables modified in bprop
        self.WGrads = [gnp.zeros(self.weights[i].shape) for i in range(len(self.weights))]
        self.biasGrads = [gnp.zeros(self.biases[i].shape) for i in range(len(self.biases))]

    def weightsDict(self):
        d = {}
        if len(self.weights) == 1:
            d['weights'] = num.empty((1,), dtype=num.object)
            d['weights'][0] = numpyify(self.weights)[0]
            d['biases'] = num.empty((1,), dtype=num.object)
            d['biases'][0] = numpyify(self.biases)[0]
        else:
            d['weights'] = num.array(numpyify(self.weights)).flatten()
            d['biases'] = num.array(numpyify(self.biases)).flatten()
            if len(self.genBiases) == 1:
                d['genBiases'] = num.empty((1,), dtype=num.object)
                d['genBiases'][0] = numpyify(self.genBiases)[0]
            else:
                d['genBiases'] = num.array(numpyify(self.genBiases)).flatten()
        return d

    def scaleDerivs(self, scale):
        for i in range(len(self.weights)):
            self.WGrads[i] *= scale
            self.biasGrads[i] *= scale

    def loadWeights(self, path, layersToLoad = None):
        fd = open(path, 'rb')
        d = num.load(fd)
        if layersToLoad != None:
            self.weights[:layersToLoad] = garrayify(d['weights'].flatten())[:layersToLoad]
            self.biases[:layersToLoad] = garrayify(d['biases'].flatten())[:layersToLoad]
            self.genBiases[:layersToLoad] = garrayify(d['genBiases'].flatten())[:layersToLoad] #this might not be quite right
        else:
            self.weights = garrayify(d['weights'].flatten())
            self.biases = garrayify(d['biases'].flatten())
            if 'genBiases' in d:
                self.genBiases = garrayify(d['genBiases'].flatten())
            else:
                self.genBiases = []
        fd.close()

    def saveWeights(self, path):
        num.savez(path, **self.weightsDict())

    def preTrainIth(self, i, minibatchStream, epochs, mbPerEpoch):
        #initialize CD gradient variables
        self.dW = gnp.zeros(self.weights[i].shape)
        self.dvb = gnp.zeros(self.genBiases[i].shape)
        self.dhb = gnp.zeros(self.biases[i].shape)

        for ep in range(epochs):
            recErr = 0
            totalCases = 0
            for j in range(mbPerEpoch):
                inpMB = minibatchStream.next()
                curRecErr = self.CDStep(inpMB, i, self.learnRates[i], self.momentum, self.L2Costs[i])
                recErr += curRecErr
                totalCases += inpMB.shape[0]
            yield recErr/float(totalCases)

    def fineTune(self, minibatchStream, epochs, mbPerEpoch, loss = None, progressBar = True, useDropout = False):
        for ep in range(epochs):
            totalCases = 0
            sumErr = 0
            sumLoss = 0
            if self.nesterov:
                step = self.stepNesterov
            else:
                step = self.step
            prog = Progress(mbPerEpoch) if progressBar else DummyProgBar()
            for i in range(mbPerEpoch):
                inpMB, targMB = minibatchStream.next()
                err, outMB = step(inpMB, targMB, self.learnRates, self.momentum, self.L2Costs, useDropout)
                sumErr += err
                if loss != None:
                    sumLoss += loss(targMB, outMB)
                totalCases += inpMB.shape[0]
                prog.tick()
            prog.done()
            yield sumErr/float(totalCases), sumLoss/float(totalCases)

    def totalLoss(self, minibatchStream, lossFuncts):
        totalCases = 0
        sumLosses = num.zeros((1+len(lossFuncts),))
        for inpMB, targMB in minibatchStream:
            inputBatch = inpMB if isinstance(inpMB, gnp.garray) else gnp.garray(inpMB)
            targetBatch = targMB if isinstance(targMB, gnp.garray) else gnp.garray(targMB)

            outputActs = self.fprop(inputBatch)
            sumLosses[0] += self.outputActFunct.error(targetBatch, self.state[-1], outputActs)
            for j,f in enumerate(lossFuncts):
                sumLosses[j+1] += f(targetBatch, outputActs)
            totalCases += inpMB.shape[0]
        return sumLosses / float(totalCases)

    def predictions(self, minibatchStream, asNumpy = False):
        for inpMB in minibatchStream:
            inputBatch = inpMB if isinstance(inpMB, gnp.garray) else gnp.garray(inpMB)
            outputActs = self.fprop(inputBatch)
            yield outputActs.as_numpy_array() if asNumpy else outputActs

    def CDStep(self, inputBatch, layer, learnRate, momentum, L2Cost = 0):
        """
        layer=0 will train the first RBM directly on the input
        """
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        mbsz = inputBatch.shape[0]
        vis = self.fprop(inputBatch, layer)
        GRBMFlag = layer==0 and self.realValuedVis
        visType = RBMGaussian() if GRBMFlag else self.RBMHidUnitType
        visHidStats, hidBiasStats, visBiasStats, negVis = \
                     CD1(vis, self.weights[layer], self.genBiases[layer], self.biases[layer], visType, self.RBMHidUnitType)
        factor = 1-momentum if not self.nestCompare else 1
        self.dW = momentum*self.dW + factor*visHidStats
        self.dvb = momentum*self.dvb + factor*visBiasStats
        self.dhb = momentum*self.dhb + factor*hidBiasStats

        if L2Cost > 0:
            self.weights[layer] *= 1-L2Cost*learnRate*factor

        self.weights[layer] += (learnRate/mbsz) * self.dW
        self.genBiases[layer] += (learnRate/mbsz) * self.dvb
        self.biases[layer] += (learnRate/mbsz) * self.dhb

        #we compute squared error even for binary visible unit RBMs because who cares
        return gnp.sum((vis-negVis)**2)

    def fpropBprop(self, inputBatch, targetBatch, useDropout):
        if useDropout:
            outputActs = self.fpropDropout(inputBatch)
        else:
            outputActs = self.fprop(inputBatch)
        outputErrSignal = -self.outputActFunct.dErrordNetInput(targetBatch, self.state[-1], outputActs)
        error = self.outputActFunct.error(targetBatch, self.state[-1], outputActs)
        errSignals = self.bprop(outputErrSignal)
        return errSignals, outputActs, error

    def constrainWeights(self):
        for i in range(len(self.rmsLims)):
            if self.rmsLims[i] != None:
                self.weights[i] = limitColumnRMS(self.weights[i], self.rmsLims[i])

    def step(self, inputBatch, targetBatch, learnRates, momentum, L2Costs, useDropout = False):
        mbsz = inputBatch.shape[0]
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        targetBatch = targetBatch if isinstance(targetBatch, gnp.garray) else gnp.garray(targetBatch)

        errSignals, outputActs, error = self.fpropBprop(inputBatch, targetBatch, useDropout)

        factor = 1-momentum if not self.nestCompare else 1.0
        self.scaleDerivs(momentum)
        for i, (WGrad, biasGrad) in enumerate(self.gradients(self.state, errSignals)):
            self.WGrads[i] += learnRates[i]*factor*(WGrad/mbsz - L2Costs[i]*self.weights[i])
            self.biasGrads[i] += (learnRates[i]*factor/mbsz)*biasGrad
        self.applyUpdates(self.weights, self.biases, self.weights, self.biases, self.WGrads, self.biasGrads)
        self.constrainWeights()
        return error, outputActs

    def applyUpdates(self, destWeights, destBiases, curWeights, curBiases, WGrads, biasGrads):
        for i in range(len(destWeights)):
            destWeights[i] = curWeights[i] + WGrads[i]
            destBiases[i] = curBiases[i] + biasGrads[i]

    def stepNesterov(self, inputBatch, targetBatch, learnRates, momentum, L2Costs, useDropout = False):
        mbsz = inputBatch.shape[0]
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        targetBatch = targetBatch if isinstance(targetBatch, gnp.garray) else gnp.garray(targetBatch)

        curWeights = [w.copy() for w in self.weights]
        curBiases = [b.copy() for b in self.biases]
        self.scaleDerivs(momentum)
        self.applyUpdates(self.weights, self.biases, curWeights, curBiases, self.WGrads, self.biasGrads)

        errSignals, outputActs, error = self.fpropBprop(inputBatch, targetBatch, useDropout)

        #self.scaleDerivs(momentum)
        for i, (WGrad, biasGrad) in enumerate(self.gradients(self.state, errSignals)):
            self.WGrads[i] += learnRates[i]*(WGrad/mbsz - L2Costs[i]*self.weights[i])
            self.biasGrads[i] += (learnRates[i]/mbsz)*biasGrad

        self.applyUpdates(self.weights, self.biases, curWeights, curBiases, self.WGrads, self.biasGrads)
        self.constrainWeights()
        return error, outputActs

    def gradDebug(self, inputBatch, targetBatch):
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        targetBatch = targetBatch if isinstance(targetBatch, gnp.garray) else gnp.garray(targetBatch)

        # mbsz = inputBatch.shape[0]
        outputActs = self.fprop(inputBatch)
        outputErrSignal = -self.outputActFunct.dErrordNetInput(targetBatch, self.state[-1], outputActs)
        #error = self.outputActFunct.error(targetBatch, self.state[-1], outputActs)
        errSignals = self.bprop(outputErrSignal)
        for i, (WGrad, biasGrad) in enumerate(self.gradients(self.state, errSignals)):
            #update the weight increments
            self.WGrads[i] = WGrad
            self.biasGrads[i] = biasGrad
        allWeightGrads = itertools.chain(self.WGrads, self.biasGrads)
        return gnp.as_numpy_array(gnp.concatenate([dw.ravel() for dw in allWeightGrads]))

    def fprop(self, inputBatch, weightsToStopBefore = None ):
        """
        Perform a (possibly partial) forward pass through the
        network. Updates self.state which, on a full forward pass,
        holds the input followed by each hidden layer's activation and
        finally the net input incident on the output layer. For a full
        forward pass, we return the actual output unit activations. In
        a partial forward pass we return None.
        """
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        if weightsToStopBefore == None:
            weightsToStopBefore = len(self.weights)
        #self.state holds everything before the output nonlinearity, including the net input to the output units
        self.state = [inputBatch]
        for i in range(min(len(self.weights) - 1, weightsToStopBefore)):
            curActs = self.hidActFuncts[i].activation(gnp.dot(self.state[-1], self.weights[i]) + self.biases[i])
            self.state.append(curActs)
        if weightsToStopBefore >= len(self.weights):
            self.state.append(gnp.dot(self.state[-1], self.weights[-1]) + self.biases[-1])
            self.acts = self.outputActFunct.activation(self.state[-1])
            return self.acts
        #we didn't reach the output units
        # To return the first set of hidden activations, we would set
        # weightsToStopBefore to 1.
        return self.state[weightsToStopBefore]

    def fpropDropout(self, inputBatch, weightsToStopBefore = None ):
        """
        Perform a (possibly partial) forward pass through the
        network. Updates self.state which, on a full forward pass,
        holds the input followed by each hidden layer's activation and
        finally the net input incident on the output layer. For a full
        forward pass, we return the actual output unit activations. In
        a partial forward pass we return None.
        """
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        if weightsToStopBefore == None:
            weightsToStopBefore = len(self.weights)
        #self.state holds everything before the output nonlinearity, including the net input to the output units
        self.state = [inputBatch * (gnp.rand(*inputBatch.shape) > self.dropouts[0])]
        for i in range(min(len(self.weights) - 1, weightsToStopBefore)):
            dropoutMultiplier = 1.0/(1.0-self.dropouts[i])
            curActs = self.hidActFuncts[i].activation(gnp.dot(dropoutMultiplier*self.state[-1], self.weights[i]) + self.biases[i])
            self.state.append(curActs * (gnp.rand(*curActs.shape) > self.dropouts[i+1]) )
        if weightsToStopBefore >= len(self.weights):
            dropoutMultiplier = 1.0/(1.0-self.dropouts[-1])
            self.state.append(gnp.dot(dropoutMultiplier*self.state[-1], self.weights[-1]) + self.biases[-1])
            self.acts = self.outputActFunct.activation(self.state[-1])
            return self.acts
        #we didn't reach the output units
        # To return the first set of hidden activations, we would set
        # weightsToStopBefore to 1.
        return self.state[weightsToStopBefore]

    def bprop(self, outputErrSignal, fpropState = None):
        """
        Perform a backward pass through the network. fpropState
        defaults to self.state (set during fprop) and outputErrSignal
        should be self.outputActFunct.dErrordNetInput(...).
        """
        #if len(errSignals)==len(self.weights)==len(self.biases)==h+1 then
        # len(fpropState) == h+2 because it includes the input and the net input to the output layer and thus
        #fpropState[-2] is the activation of the penultimate hidden layer (or the input if there are no hidden layers)
        if fpropState == None:
            fpropState = self.state
        assert(len(fpropState) == len(self.weights) + 1)

        errSignals = [None for i in range(len(self.weights))]
        errSignals[-1] = outputErrSignal
        for i in reversed(range(len(self.weights) - 1)):
            errSignals[i] = gnp.dot(errSignals[i+1], self.weights[i+1].T)*self.hidActFuncts[i].dEdNetInput(fpropState[i+1])
        return errSignals

    def gradients(self, fpropState, errSignals):
        """
        Lazily generate (negative) gradients for the weights and biases given
        the result of fprop (fpropState) and the result of bprop
        (errSignals).
        """
        assert(len(fpropState) == len(self.weights)+1)
        assert(len(errSignals) == len(self.weights) == len(self.biases))
        for i in range(len(self.weights)):
            yield gnp.dot(fpropState[i].T, errSignals[i]), errSignals[i].sum(axis=0)




########NEW FILE########
__FILENAME__ = counter
"""
 Copyright (c) 2011,2012 George Dahl

 Permission is hereby granted, free of charge, to any person  obtaining
 a copy of this software and associated documentation  files (the
 "Software"), to deal in the Software without  restriction, including
 without limitation the rights to use,  copy, modify, merge, publish,
 distribute, sublicense, and/or sell  copies of the Software, and to
 permit persons to whom the  Software is furnished to do so, subject
 to the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.  THE
 SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT  HOLDERS
 BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,  WHETHER IN AN
 ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING  FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR  OTHER DEALINGS IN THE
 SOFTWARE.
"""

from sys import stderr

class Counter(object):
    def __init__(self, step=10):
        self.cur = 0
        self.step = step

    def tick(self):
        self.cur += 1
        if self.cur % self.step == 0:
            stderr.write( str(self.cur ) )
            stderr.write( "\r" )
            stderr.flush()
        
    def done(self):
        stderr.write( str(self.cur ) )
        stderr.write( "\n" )
        stderr.flush()

class Progress(object):
    def __init__(self, numSteps):
        self.total = numSteps
        self.cur = 0
        self.curPercent = 0
    def tick(self):
        self.cur += 1
        newPercent = (100*self.cur)/self.total
        if newPercent > self.curPercent:
            self.curPercent = newPercent
            stderr.write( str(self.curPercent)+"%" )
            stderr.write( "\r" )
            stderr.flush()
    def done(self):
        stderr.write( '100%' )
        stderr.write( "\n" )
        stderr.flush()

def ProgressLine(line):
    stderr.write(line)
    stderr.write( "\r" )
    stderr.flush()
    
def main():
    from time import sleep
    for i in range(500):
        s = str(2.379*i)
        ProgressLine(s)
        sleep(0.02)
    c = Counter(5)
    for i in range(500):
        c.tick()
        sleep(.005)
    c.done()
    p = Progress(5000)
    for i in range(5000):
        p.tick()
        sleep(.0005)
    p.done()


if __name__ == "__main__":
    main()
    

########NEW FILE########
__FILENAME__ = gdbn
from time import time
from datetime import timedelta

import gnumpy
import numpy as np

import activationFunctions
from core import buildDBN
from sklearn.base import BaseEstimator


class DBN(BaseEstimator):
    """A scikit-learn estimator based on George Dahl's DBN
    implementation `gdbn`.
    
    NOTE: this module was taken from the nolearn library, is just here to make
    my personal benchmarks easier. Please follow nolearn for updates.
    https://github.com/dnouri/nolearn
    """
    def __init__(
        self,
        layer_sizes=None,
        scales=0.05,
        fan_outs=None,
        output_act_funct=None,
        real_valued_vis=True,
        use_re_lu=False,
        uniforms=False,

        learn_rates=0.1,
        learn_rate_decays=1.0,
        learn_rate_minimums=0.0,
        momentum=0.9,
        l2_costs=0.0001,
        dropouts=0,
        nesterov=False,
        nest_compare=True,
        rms_lims=None,

        learn_rates_pretrain=None,
        momentum_pretrain=None,
        l2_costs_pretrain=None,
        nest_compare_pretrain=None,

        epochs=10,
        epochs_pretrain=0,
        loss_funct=None,
        minibatch_size=64,
        minibatches_per_epoch=None,

        pretrain_callback=None,
        fine_tune_callback=None,
        verbose=0,
        ):
        """
        Many parameters such as `learn_rates`, `dropouts` etc. will
        also accept a single value, in which case that value will be
        used for all layers.  To control the value per layer, pass a
        list of values instead; see examples below.

        Parameters ending with `_pretrain` may be provided to override
        the given parameter for pretraining.  Consider an example
        where you want the pre-training to use a lower learning rate
        than the fine tuning (the backprop), then you'd maybe pass
        something like::

          DBN([783, 300, 10], learn_rates=0.1, learn_rates_pretrain=0.005)

        If you don't pass the `learn_rates_pretrain` parameter, the
        value of `learn_rates` will be used for both pre-training and
        fine tuning.  (Which seems to not work very well.)

        :param layer_sizes: A list of integers of the form
                            ``[n_vis_units, n_hid_units1,
                            n_hid_units2, ..., n_out_units]``.

                            An example: ``[784, 300, 10]``

                            The number of units in the input layer and
                            the output layer will be set automatically
                            if you set them to -1.  Thus, the above
                            example is equivalent to ``[-1, 300, -1]``
                            if you pass an ``X`` with 784 features,
                            and a ``y`` with 10 classes.

        :param scales: A list of scales for the random initialization
                       of weights.  Defaults to `0.5`.

        :param fan_outs: Number of nonzero incoming connections to a
                         hidden unit.  Defaults to `None`, which means
                         that all connections have non-zero weights.

        :param output_act_funct: Output activation function.  Instance
                                 of type
                                 :class:`~gdbn.activationFunctions.Sigmoid`,
                                 :class:`~.gdbn.activationFunctions.Linear`,
                                 :class:`~.gdbn.activationFunctions.Softmax`
                                 from the
                                 :mod:`gdbn.activationFunctions`
                                 module.  Defaults to
                                 :class:`~.gdbn.activationFunctions.Softmax`.

        :param real_valued_vis: Set `True` (the default) if visible
                                units are real-valued.

        :param use_re_lu: Set `True` to use rectified linear units.
                          Defaults to `False`.

        :param uniforms: Not documented at this time.

        :param learn_rates: A list of learning rates, one entry per
                            weight layer.

                            An example: ``[0.1, 0.1]``

        :param learn_rate_decays: The number with which the
                                  `learn_rate` is multiplied after
                                  each epoch of fine-tuning.

        :param learn_rate_minimums: The minimum `learn_rates`; after
                                    the learn rate reaches the minimum
                                    learn rate, the
                                    `learn_rate_decays` no longer has
                                    any effect.

        :param momentum: Momentum

        :param l2_costs: L2 costs per weight layer.

        :param dropouts: Dropouts per weight layer.

        :param nesterov: Not documented at this time.

        :param nest_compare: Not documented at this time.

        :param rms_lims: Not documented at this time.

        :param learn_rates_pretrain: A list of learning rates similar
                                     to `learn_rates_pretrain`, but
                                     used for pretraining.  Defaults
                                     to value of `learn_rates` parameter.

        :param momentum_pretrain: Momentum for pre-training.  Defaults
                                  to value of `momentum` parameter.

        :param l2_costs_pretrain: L2 costs per weight layer, for
                                  pre-training.  Defaults to the value
                                  of `l2_costs` parameter.

        :param nest_compare_pretrain: Not documented at this time.

        :param epochs: Number of epochs to train (with backprop).

        :param epochs_pretrain: Number of epochs to pre-train (with CDN).

        :param loss_funct: A function that calculates the loss.  Used
                           for displaying learning progress and for
                           :meth:`score`.

        :param minibatch_size: Size of a minibatch.

        :param minibatches_per_epoch: Number of minibatches per epoch.
                                      The default is to use as many as
                                      fit into our training set.

        :param pretrain_callback: An optional function that takes as
                                  arguments the :class:`DBN` instance,
                                  the epoch and the layer index as its
                                  argument, and is called for each
                                  epoch of pretraining.

        :param fine_tune_callback: An optional function that takes as
                                   arguments the :class:`DBN` instance
                                   and the epoch, and is called for
                                   each epoch of fine tuning.

        :param verbose: Debugging output.
        """

        if layer_sizes is None:
            layer_sizes = [-1, -1]

        if output_act_funct is None:
            output_act_funct = activationFunctions.Softmax()
        elif isinstance(output_act_funct, str):
            output_act_funct = getattr(activationFunctions, output_act_funct)()

        self.layer_sizes = layer_sizes
        self.scales = scales
        self.fan_outs = fan_outs
        self.output_act_funct = output_act_funct
        self.real_valued_vis = real_valued_vis
        self.use_re_lu = use_re_lu
        self.uniforms = uniforms

        self.learn_rates = learn_rates
        self.learn_rate_decays = learn_rate_decays
        self.learn_rate_minimums = learn_rate_minimums
        self.momentum = momentum
        self.l2_costs = l2_costs
        self.dropouts = dropouts
        self.nesterov = nesterov
        self.nest_compare = nest_compare
        self.rms_lims = rms_lims

        self.learn_rates_pretrain = learn_rates_pretrain
        self.momentum_pretrain = momentum_pretrain
        self.l2_costs_pretrain = l2_costs_pretrain
        self.nest_compare_pretrain = nest_compare_pretrain

        self.epochs = epochs
        self.epochs_pretrain = epochs_pretrain
        self.loss_funct = loss_funct
        self.use_dropout = True if dropouts else False
        self.minibatch_size = minibatch_size
        self.minibatches_per_epoch = minibatches_per_epoch

        self.pretrain_callback = pretrain_callback
        self.fine_tune_callback = fine_tune_callback
        self.verbose = verbose

    def _fill_missing_layer_sizes(self, X, y):
        layer_sizes = self.layer_sizes
        if layer_sizes[0] == -1:  # n_feat
            layer_sizes[0] = X.shape[1]
        if layer_sizes[-1] == -1 and y is not None:  # n_classes
            layer_sizes[-1] = y.shape[1]

    def _vp(self, value):
        num_weights = len(self.layer_sizes) - 1
        if not hasattr(value, '__iter__'):
            value = [value] * num_weights
        return list(value)

    def _build_net(self, X, y=None):
        v = self._vp

        self._fill_missing_layer_sizes(X, y)
        if self.verbose:  # pragma: no cover
            print "[DBN] layers {}".format(self.layer_sizes)

        net = buildDBN(
            self.layer_sizes,
            v(self.scales),
            v(self.fan_outs),
            self.output_act_funct,
            self.real_valued_vis,
            self.use_re_lu,
            v(self.uniforms),
            )

        return net

    def _configure_net_pretrain(self, net):
        v = self._vp

        self._configure_net_finetune(net)

        learn_rates = self.learn_rates_pretrain
        momentum = self.momentum_pretrain
        l2_costs = self.l2_costs_pretrain
        nest_compare = self.nest_compare_pretrain

        if learn_rates is None:
            learn_rates = self.learn_rates
        if momentum is None:
            momentum = self.momentum
        if l2_costs is None:
            l2_costs = self.l2_costs
        if nest_compare is None:
            nest_compare = self.nest_compare

        net.learnRates = v(learn_rates)
        net.momentum = momentum
        net.L2Costs = v(l2_costs)
        net.nestCompare = nest_compare

        return net

    def _configure_net_finetune(self, net):
        v = self._vp

        net.learnRates = v(self.learn_rates)
        net.momentum = self.momentum
        net.L2Costs = v(self.l2_costs)
        net.dropouts = v(self.dropouts)
        net.nesterov = self.nesterov
        net.nestCompare = self.nest_compare
        net.rmsLims = v(self.rms_lims)

        return net

    def _minibatches(self, X, y=None):
        while True:
            idx = np.random.randint(X.shape[0], size=(self.minibatch_size,))

            X_batch = X[idx]
            if hasattr(X_batch, 'todense'):
                X_batch = X_batch.todense()

            if y is not None:
                yield (X_batch, y[idx])
            else:
                yield X_batch

    def _onehot(self, y):
        if len(y.shape) == 1:
            num_classes = y.max() + 1
            y_new = np.zeros(
                (y.shape[0], num_classes), dtype=np.int)
            for index, label in enumerate(y):
                y_new[index][label] = 1
                y = y_new
        return y

    def _num_mistakes(self, targets, outputs):
        if hasattr(targets, 'as_numpy_array'):  # pragma: no cover
            targets = targets.as_numpy_array()
        if hasattr(outputs, 'as_numpy_array'):
            outputs = outputs.as_numpy_array()
        return np.sum(outputs.argmax(1) != targets.argmax(1))

    def _learn_rate_adjust(self):
        if self.learn_rate_decays == 1.0:
            return

        learn_rate_decays = self._vp(self.learn_rate_decays)
        learn_rate_minimums = self._vp(self.learn_rate_minimums)

        for index, decay in enumerate(learn_rate_decays):
            new_learn_rate = self.net_.learnRates[index] * decay
            if new_learn_rate >= learn_rate_minimums[index]:
                self.net_.learnRates[index] = new_learn_rate

        if self.verbose >= 2:
            print "Learn rates: {}".format(self.net_.learnRates)

    def fit(self, X, y):
        y = self._onehot(y)

        self.net_ = self._build_net(X, y)

        minibatches_per_epoch = self.minibatches_per_epoch
        if minibatches_per_epoch is None:
            minibatches_per_epoch = X.shape[0] / self.minibatch_size

        loss_funct = self.loss_funct
        if loss_funct is None:
            loss_funct = self._num_mistakes

        errors_pretrain = self.errors_pretrain_ = []
        losses_fine_tune = self.losses_fine_tune_ = []
        errors_fine_tune = self.errors_fine_tune_ = []

        if self.epochs_pretrain:
            self.epochs_pretrain = self._vp(self.epochs_pretrain)
            self._configure_net_pretrain(self.net_)
            for layer_index in range(len(self.layer_sizes) - 1):
                errors_pretrain.append([])
                if self.verbose:  # pragma: no cover
                    print "[DBN] Pre-train layer {}...".format(layer_index + 1)
                time0 = time()
                for epoch, err in enumerate(
                    self.net_.preTrainIth(
                        layer_index,
                        self._minibatches(X),
                        self.epochs_pretrain[layer_index],
                        minibatches_per_epoch,
                        )):
                    errors_pretrain[-1].append(err)
                    if self.verbose:  # pragma: no cover
                        print "  Epoch {}: err {}".format(epoch + 1, err)
                        elapsed = str(timedelta(seconds=time() - time0))
                        print "  ({})".format(elapsed.split('.')[0])
                        time0 = time()
                    if self.pretrain_callback is not None:
                        self.pretrain_callback(self, epoch, layer_index)

        self._configure_net_finetune(self.net_)
        if self.verbose:  # pragma: no cover
            print "[DBN] Fine-tune..."
        time0 = time()
        for epoch, (loss, err) in enumerate(
            self.net_.fineTune(
                self._minibatches(X, y),
                self.epochs,
                minibatches_per_epoch,
                loss_funct,
                self.verbose,
                self.use_dropout,
                )):
            losses_fine_tune.append(loss)
            errors_fine_tune.append(err)
            self._learn_rate_adjust()
            if self.verbose:  # pragma: no cover
                print "Epoch {}:".format(epoch + 1)
                print "  loss {}".format(loss)
                print "  err  {}".format(err)
                elapsed = str(timedelta(seconds=time() - time0))
                print "  ({})".format(elapsed.split('.')[0])
                time0 = time()
            if self.fine_tune_callback is not None:
                self.fine_tune_callback(self, epoch)

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)

    def predict_proba(self, X):
        if hasattr(X, 'todense'):
            return self._predict_proba_sparse(X)
        res = np.zeros((X.shape[0], self.layer_sizes[-1]))
        for i, el in enumerate(self.net_.predictions(X, asNumpy=True)):
            res[i] = el
        return res

    def _predict_proba_sparse(self, X):
        batch_size = self.minibatch_size
        res = []
        for i in xrange(0, X.shape[0], batch_size):
            X_batch = X[i:min(i + batch_size, X.shape[0])].todense()
            res.extend(self.net_.predictions(X_batch))
        return np.array(res).reshape(X.shape[0], -1)

    def score(self, X, y):
        loss_funct = self.loss_funct
        if loss_funct is None:
            loss_funct = self._num_mistakes

        outputs = self.predict_proba(X)
        targets = self._onehot(y)
        mistakes = loss_funct(outputs, targets)
        return - float(mistakes) / len(y) + 1

########NEW FILE########
__FILENAME__ = gnumpy
"""Documentation can be found at http://www.cs.toronto.edu/~tijmen/gnumpy.html"""

"""

Copyright (c) 2010-2012 Tijmen Tieleman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

If you use Gnumpy for scientific work that gets published, you should include
in that publication a citation of the technical report that describes Gnumpy.
That report can be found at http://www.cs.toronto.edu/~tijmen/gnumpyTr.pdf

"""





"""
This file is not intended to be read by anyone other than gnumpy developers. It's long, it's weakly documented (much of the internal documentation is elsewhere), and many lines are unnaturally long & illegible because I did a lot of inlining.

If you really want to know how gnumpy works internally, or if you want to extend it, you can ask me for the original, which doesn't have the inlining, and the internal documentation.
"""




# ------------------------------------------------------------------------------- module init & shutdown

import numpy, operator, sys as _sys, types as types, time as _time, os as _os, __builtin__, collections as _collections, pdb as _pdb, gc as _gc, ctypes as _ctypes, weakref as _weakref

_useGpu = _os.environ.get('GNUMPY_USE_GPU', 'auto')
assert _useGpu in ('auto', 'yes', 'no'), "environment variable GNUMPY_USE_GPU, if present, should be one of 'auto', 'yes', 'no'."
if _useGpu == 'auto':
 try: import cudamat as _cudamat; _useGpu = 'yes'
 except: print 'gnumpy: failed to import cudamat. Using npmat instead. No GPU will be used.'; _useGpu = 'no'
if _useGpu == 'yes':
 import cudamat as _cudamat
elif _useGpu == 'no':
 import npmat as _cudamat
 _precision = _os.environ.get('GNUMPY_CPU_PRECISION', '32')
 assert _precision in ('32', '64', '128'), 'environment variable GNUMPY_CPU_PRECISION, if present, should have value 32, 64, or 128.'
 _cudamat.__DTYPE__ = eval('numpy.float'+_precision)

_cmType = _cudamat.CUDAMatrix
_isTijmen = False
if hasattr(_cudamat, 'ct'): _ctInt = _cudamat.ct.c_int

def board_id_to_use():
 try:
  import gpu_lock
  return gpu_lock.obtain_lock_id()
 except:
  print 'gnumpy: failed to use gpu_lock. Using board #0 without knowing whether it is in use or not.'
  return 0

class GnumpyGpuUnavailableException(Exception): pass

_boardId = None
def _init_gpu():
 """ picks a board and claims it (if using cudamat aot npmat). exception if there is no board. """
 if '__gpu_inited' in globals(): return
 global _boardId
 if _useGpu=='yes':
  _boardId = ( board_id_to_use() if callable(board_id_to_use) else board_id_to_use)
  if _boardId==-1: raise GnumpyGpuUnavailableException('No gpu board is available. gnumpy will not function. Consider telling it to run on the CPU by setting environment variable GNUMPY_USE_GPU to "no".')
  _cudamat.cuda_set_device(_boardId)
  _cudamat.cublas_init()
 _cudamat.CUDAMatrix.init_random(0)
 globals()['__gpu_inited'] = None

def usingGpu():
 assert _useGpu in ('yes', 'no'), 'first initialize gnumpy'
 return _useGpu=='yes'

expensive_check_probability = 1
acceptable_number_types = 'anything goes' # alternatives: 'no nans'; 'no nans or infs'; or a number indicating the max allowed abs
dont__check_number_types_in_non_garrays = True
class GnumpyNumberTypeException(Exception): pass

_checking_number_type_now = False
def _check_number_types(x):
 """ does some checks, and then returns x. """
 if acceptable_number_types == 'anything goes': return x # this is the typical case, and in this case I just want to leave this checking function asap.

 global _checking_number_type_now
 if dont__check_number_types_in_non_garrays and not isinstance(x, garray): return x
 if _checking_number_type_now: return x # to prevent checks upon checks upon checks (infinite recursion)
 try:
  _checking_number_type_now = True
  if acceptable_number_types == 'no nans': raise NotImplementedError
  elif acceptable_number_types == 'no nans or infs':
   if not garray(x, copy=False).all_real(): raise GnumpyNumberTypeException('Found values that violate the rule set by gnumpy.acceptable_number_types: "%s"' % acceptable_number_types)
  elif type(acceptable_number_types) in _numberTypes:
   if (abs(garray(x, copy=False)) > acceptable_number_types).any2(): raise GnumpyNumberTypeException('Found values that violate the rule set by gnumpy.acceptable_number_types: "%s"' % acceptable_number_types)
  else: assert False, 'gnumpy: the value of variable "acceptable_number_types" must be one of "anything goes", "no nans", "no nans or infs".'
 finally:
  _checking_number_type_now = False
 return x



# ------------------------------------------------------------------------------- helpers copied from other files

def _isFullSlice(x): return type(x) == types.SliceType and x == slice(None) # the first check is necessary to avoid returning a broadcast array of False's if x is an array
def _isSequence(x): return type(x) == list or type(x) == tuple or type(x)==xrange
def _insertT(tup, index, tupleToInsert): return tuple(tup[:index]) + tuple(tupleToInsert) + tuple(tup[index:])
def _modifyT(tup, index, newValue): return tuple(tup[:index]) + (newValue,) + tuple(tup[index+1:])
def _deleteT(tup, start, end): return tup[:start] + tup[end:]
def _prodT(x): return reduce(operator.mul, x, 1)
def _findIndex3(tupOrGenerator): return ( i for i, x in enumerate(tuple(tupOrGenerator)) if x).next()
def _isNumber(x): return type(x) in _numberTypes
def _nonSeqAsS(x): return ( x if _isSequence(x) else (x,))
_t0=()
def reduceAdd(x): return reduce(operator.add, x)

def _deleteT2(tup, index):
 index %= len(tup)
 return tup[:index] + tup[index+1:]

_intTypes = set((types.IntType, types.LongType, numpy.int16, numpy.int32, numpy.int8, numpy.int64))
_floatTypes = set((types.FloatType, numpy.float64, numpy.float32, getattr(numpy, 'float128', numpy.float64), getattr(numpy, 'float96', numpy.float64))) # considering numpy.float64 a number is debatable. it really is a numpy object, and behaves that way, too: it has a __mul__ which prevents garray.__rmul__ from getting the task. However, for most purposes it's a number.
_numberTypes = _intTypes | _floatTypes

def _allTheSame(tup):
 tup = tuple(tup)
 if len(tup)<=1: return True
 for elt in tup[1:]:
  if elt != tup[0]: return False
 return True





# ------------------------------------------------------------------------------- gnumpy specific helpers

def _all2_(t, pred): return reduce(operator.and_, map(pred, t), True)
def _any2_(t, pred): return reduce(operator.or_, map(pred, t), False)

def _doExpensiveCheck(): return numpy.random.rand() < expensive_check_probability

def as_garray(x): return ( x if isinstance(x, garray) else garray(x))
def as_garray_or_scalar(x): return ( x if type(x) in _numberTypes or isinstance(x, garray) else garray(x))
def as_numpy_array(x): return ( x.as_numpy_array() if isinstance(x, garray) else numpy.array(x))

def _cm_reshape(cm, newShape):
 if _prodT(newShape)==0: return cm
 else: return cm.reshape(tuple(reversed(newShape)))

def _cm_col_slice_write(cm, start, end, sourceCm):
 cm.set_row_slice(start, end, sourceCm)

def _cm_col_slice_read(cm, start, end, target):
 cm.get_row_slice(start, end, target)
 return target

def _cm_row_slice_read(cm, start, end):
 if start==end: return _new_cm((0, cm.shape[0])) # cudamat special case workaround
 if cm.shape[1]==1 and start==0 and end==1: return cm # cudamat special case workaround
 ret = cm.get_col_slice(start, end)
 return ret

def _read_single_index(index, axisLen):
 index = int(index)
 if index>=axisLen or index<-axisLen: raise IndexError('index out of bounds. index %d requested on an axis of length %d' % (index, axisLen))
 return index % axisLen

def _short_slice(i): return slice(i, i+1)

def _read_simple_slice(sl, axisLen):
 assert sl.step in (None, 1), 'simple slice not understood'
 sFrom, sTo = slice(( None if sl.start==None else int(sl.start)), ( None if sl.stop==None else int(sl.stop))).indices(axisLen)[:2]
 if sFrom>sTo: sTo = sFrom
 return (sFrom, sTo, sTo-sFrom)

def _extend_shape(shape, nAxes): return (1,) * (nAxes-len(shape)) + shape

def cudamatHas(name):
 if not hasattr(_cudamat, '_cudamat'): return False
 return hasattr(_cudamat._cudamat, name)


# ------------------------------------------------------------------------------- memory management

max_memory_usage = numpy.inf # public

_cmsForReuse = _collections.defaultdict(list) # dict from size to list of reusable (abandoned) cms
__memoryInUse = 0
_memoryUsers = _collections.defaultdict(lambda: (0, 0))
track_memory_usage = False
tracked_arrays = _weakref.WeakValueDictionary() # dict of id() to array. The key is never used. This remains empty if track_memory_usage remains False.

def _new_cm(sizeOrShape):
 """
 Internal.
 Returns a new CUDAMatrix object of the given size.
 This is the only proc that allocs gpu mem.
 """
 global __memoryInUse
 if type(sizeOrShape) == tuple:
  if _prodT(sizeOrShape)==0: return _new_cm(1) # cudamat workaround: cudamat can't handle size 0 arrays
  else: return _new_cm(sizeOrShape[0]*sizeOrShape[1]).reshape((sizeOrShape[1], sizeOrShape[0]))
 size = sizeOrShape
 if size==0: return _cudamat.empty((1, 1)) # cudamat workaround
 if len(_cmsForReuse[size])!=0:
  return _cm_reshape(_cmsForReuse[size].pop(), (1, size)) # re-use an abandoned cm
 _init_gpu()
 if __memoryInUse+size*4*5 > max_memory_usage: free_reuse_cache(False) # if we're somewhat close to the limit, then free what's easy to free, and hope that there are contiguous blocks available.
 if __memoryInUse+size*4 > max_memory_usage: # if we're (still) OVER the limit, then do whatever can be done to make more mem available
  free_reuse_cache(True) # gc.collect can take quite some time
  if __memoryInUse+size*4 > max_memory_usage:
   raise MemoryError('Gnumpy ran out of memory. Currently in use are %s; the maximum allowed is %s; so the present request for %s is refused. Free some memory and try again.' % (_n_bytes_str(__memoryInUse), _n_bytes_str(max_memory_usage), _n_bytes_str(size*4)))
 try:
  ret = _cudamat.empty((size, 1))
  __memoryInUse += size*4 # do this only if the malloc succeeded
  return ret
 except _cudamat.CUDAMatException, e: # this means that malloc failed
  raise MemoryError('The GPU failed to allocate the requested %d bytes of memory. This doesn\'t mean that your program is using too much memory. It does, however, mean that you should reduce the value of gnumpy.max_memory_usage (currently %s), to always have some memory unused (which is necessary to find contiguous large blocks of memory to allocate). Failing to allocate enough memory makes the GPU feel very unwell, so you are advised to restart Python now, or expect to see incoherent error messages and risk causing more serious damage.' % (size*4, str(max_memory_usage)))

def free_reuse_cache(completely=True):
 """
 This frees all GPU memory that is not in use but is kept allocated for re-use.
 If <completely> is set to False, this works quicker but less thoroughly.
 """
 if completely: _gc.collect() # this has to happen before the loop, because this may add more entries in _cmsForReuse which then have to be freed by the loop
 global __memoryInUse
 for size in _cmsForReuse:
  while _cmsForReuse[size]:
   _cmsForReuse[size].pop()
   __memoryInUse -= size*4
 del _gc.garbage[:] # this shouldn't be necessary at all, but for some reason perfectly referenced AND perfectly deletable cms get put there

def _n_bytes_str(n):
 def _base(s): return ( _base(s[:-3]) + ',' + s[-3:] if len(s)>=4 else s)
 return _base(str(n)) + ' bytes'

def memory_in_use(in_megabytes=False):
 """ returns the number of bytes (or megabytes if you asked for that) of GPU memory that are in use. """
 return __memoryInUse // ( 2**20 if in_megabytes else 1)

def memory_available(free_reuse_cache_first):
 if free_reuse_cache_first: free_reuse_cache()
 return max_memory_usage - memory_in_use()

def _calling_line():
 """ Internal. Inspects the current python call stack and returns a nice string description of the line of code that called gnumpy. """
 stack = _pdb.traceback.extract_stack()[::-1] # newest first
 stack = stack[( i for i, x in enumerate(stack) if x[0] != stack[0][0]).next():] # skip any gnumpy procs on the stack
 def stackFrameToString(frame): return 'File "%s", line %d, in function %s:    %s' % (frame[0], frame[1], frame[2], ( '<command unknown>' if frame[3]==None else frame[3]))
 ret = stackFrameToString(stack[0])
 for frame in stack[1:]:
  if 'File "<ipython console>",' in ret: break
  if 'File "<stdin>",' in ret: break
  ret += '\n  Called by: ' + stackFrameToString(frame)
 return ret

def memory_allocators(minimum_n_bytes=1, new_style=False):
 """ Prints a list of lines in your code that allocated GPU memory that's still in use. """
 if not track_memory_usage:
  print 'The variable gnumpy.track_memory_usage must be set to True, to enable memory data collection (which can slow down your program a lot).'
  return
 if new_style:
  sigs = _collections.defaultdict(int) # dict of t2(line; n bytes) to total n bytes
  for a in tuple(tracked_arrays.values()): # I want to be totally sure that this is a loop over something that doesn't change in the process
   k = (a.allocating_line, a.nbytes)
   sigs[k] += a.nbytes
  for (line, nb_each), nb_total in sorted(sigs.items(), key = lambda x: x[1])[::-1]:
   if nb_total < minimum_n_bytes: continue
   print '%d objects of %s (total %s), that are still in use, were allocated by: \n%s\n' % (nb_total/nb_each, _n_bytes_str(nb_each), _n_bytes_str(nb_total), line)
 else:
  for line, (n,amt) in sorted(_memoryUsers.items(), key=lambda x:x[1][1]) [::-1] : # this is the version that doesn't explicitly track arrays
   if amt >= minimum_n_bytes:
    print '%d objects, totalling %s, that are still in use, were allocated by: %s' % (n, _n_bytes_str(amt), line)
    print



# ------------------------------------------------------------------------------- external procs

def status():
 if not usingGpu(): print 'gnumpy is running on the CPU, i.e. in simulation mode. The data type is float%s.' % _precision
 if usingGpu():
  if _boardId==None: print 'gnumpy is planning to run on a GPU, but hasn\'t yet chosen & initialized a board.'
  else: print 'gnumpy is running on GPU board #%d.' % _boardId
 print '%s of gpu memory are in use, of which at least %s can be freed immediately by gnumpy.free_reuse_cache().' % (_n_bytes_str(__memoryInUse), _n_bytes_str(__builtin__.sum( size*len(cms)*4 for size, cms in _cmsForReuse.items())))



def _rand__base(shapeInfo, distribution, zero_d_means_scalar):
 if len(shapeInfo)==1 and _isSequence(shapeInfo[0]): zero_d_means_scalar = False; shapeInfo = shapeInfo[0]
 ret = empty(shapeInfo)
 {'uniform': _cmType.fill_with_rand, 'normal': _cmType.fill_with_randn}[distribution](ret._base)
 if ret.size!=0 and _doExpensiveCheck(): assert ret.sum() < 100 + 2*ret.size, 'numerical gpu error: rand() gave a result>100'
 if len(shapeInfo) == 0 and zero_d_means_scalar: return ret.item()
 else: return ret

def tile(a, reps):
 if type(reps) in _numberTypes: reps = (reps,)
 reps = tuple(reps) # for generator expressions
 if type(a) in _numberTypes:
  ret = empty(reps)
  ret._base.assign(a)
  return ret
 a = as_garray(a)
 if len(reps) > a.ndim: a = a._add_axes(len(reps))
 if len(reps) < a.ndim: reps = _extend_shape(reps, a.ndim) # now len(reps)==a.ndim
 retShape = tuple([ a.shape[i] * reps[i] for i in tuple(xrange(len(reps)))])
 if _prodT(retShape)==0: return zeros(retShape)
 if _prodT(reps)==1: return a
 for i in range(a.ndim-1): # merge replication requests on adjacent axes, for efficiency.
  if reps[i]!=1 and reps[i+1]!=1 and a.shape[i]==1: return a.reshape(_deleteT2(a.shape, i)).tile(reps[:i]+(_prodT(reps[i:i+2]),)+reps[i+2:]).reshape(map(operator.mul, a.shape, reps))
 def dataIDone(nextA, i): return nextA.reshape(_modifyT(a.shape, i, a.shape[i]*reps[i])).tile(_modifyT(reps, i, 1))
 if reps[0]!=1: # replicating rows is easy and efficient: just repeat the data a number of times.
  temp = empty((reps[0], a.size)) # shape doesn't matter because dataIDone changes it
  tempCm = temp._base_shaped(1)
  if reps[0]>=1:
   _cm_row_slice_read(tempCm, 0, 1).assign(a._base_as_row())
   nCopiesDone = 1
   while nCopiesDone < reps[0]:
    nNow = __builtin__.min(nCopiesDone, reps[0]-nCopiesDone)
    _cm_row_slice_read(tempCm, nCopiesDone, nCopiesDone + nNow).assign(_cm_row_slice_read(tempCm, 0, nNow))
    nCopiesDone += nNow
  return dataIDone(temp, 0)
 # the general case is repeating a subset (aot the whole array) n times, before moving on to the next subset
 # using a transpose with the right shape, the subsets can become columns. those can be lengthened because that is replicating rows; a second transpose makes them now-lengthened subsets again
 axis = __builtin__.min( i for i in range(a.ndim) if reps[i]!=1)
 return dataIDone(a.reshape_2d(axis).T.tile((reps[axis], 1)).T, axis)

def is_garray(x): return isinstance(x, garray)
def is_array(x): return isinstance(x, garray) or type(x) == numpy.ndarray

def rand(*shapeInfo):
 """ the desired array shape can be entered either as integers or as a tuple of integers. If you enter a tuple you always get an array; if you enter nothing you get a scalar. """
 return _rand__base(shapeInfo, 'uniform', True)

def randn(*shapeInfo):
 """ the desired array shape can be entered either as integers or as a tuple of integers. If you enter a tuple you always get an array; if you enter nothing you get a scalar. """
 return _rand__base(shapeInfo, 'normal', True)

def empty(shape):
 if _isSequence(shape) or type(shape) == types.GeneratorType: shape = tuple(shape)
 else: shape = (shape,)
 return garray(_new_cm(_prodT(shape)), shape, None)

def zeros (shape): return tile(0, shape)
def ones (shape): return tile(1, shape)

def seed_rand(seed=None):
 _init_gpu()
 if seed==None: seed = int(_time.time())
 _cudamat.CUDAMatrix.init_random(seed)

def dot(a1, a2):
 # internally: for matrix-matrix multiplies only; vectors are treated like special cases.
 a1 = as_garray(a1); a2 = as_garray(a2)
 if a1.ndim==0 or a2.ndim==0: return a1*a2
 if a1.ndim==a2.ndim==1:
  if a1 is a2: return sum(a1**2)
  else: return dot(a1.reshape(1, a1.size), a2.reshape(a2.size, 1)).item()
 if a1.ndim==2 and a2.ndim==1: return dot(a1, a2.reshape(a2.size, 1)).ravel() # treat a2 like a column vector
 if a1.ndim==1 and a2.ndim==2: return dot(a1._add_axes(2), a2)[0]   # treat a1 like a row vector
 if a1.shape[-1] != a2.shape[-2]: raise ValueError('arrays not aligned for dot product. a dot product was requested of arrays with shapes %s and %s' % (a1.shape, a2.shape))
 if a1.ndim==a2.ndim==2:
  retShape = (a1.shape[0], a2.shape[1])
  if a1.shape[1]==0: return zeros(retShape) # cudamat bug workaround
  ret = empty(retShape)
  if ret.size!=0: _cudamat.dot(a2._base_as_2d(), a1._base_as_2d(), ret._base_as_2d())
  return ret
 if a1.ndim >= 2 and a2.ndim >= 2:
  # this is not necessarily fast, because if a2.ndim>=3 then it involves a transpose
  a12 = ( a1.reshape_2d(-1) if a1.ndim!=2 else a1)
  a22 = ( a2.transpose((a2.ndim-2,) + tuple(xrange(a2.ndim-2)) + (a2.ndim-1,)).reshape_2d(1)
          if a2.ndim!=2 else
          a2)
  retShape = _deleteT2(a1.shape, -1) + _deleteT2(a2.shape, -2)
  return dot(a12, a22).reshape(retShape)
 raise NotImplementedError('dot with arguments of shapes %s and %s' % (a1.shape, a2.shape))

def outer(vec1, vec2): return dot(vec1.ravel()[:, newaxis], vec2.ravel()[newaxis, :])

def concatenate(arrays, axis=0):
 arrays = tuple(map(as_garray, arrays))
 if axis<0: axis += arrays[0].ndim
 if not _isSequence(arrays) or not type(axis) in _numberTypes: raise ValueError('wrong argument types to gnumpy.concatenate: expected <arrays> to be a sequence and <axis> to be a number, but got types %s and %s.' % (type(arrays), type(axis)))
 if axis not in range(arrays[0].ndim): raise ValueError('bad axis number (%d) specified (the first array has %d axes)' % (axis, arrays[0].ndim))
 if not _allTheSame( _deleteT2(a.shape, axis) for a in arrays): raise ValueError('array dimensions must agree except possibly for axis #%d. The given array shapes are: %s' % (axis, tuple( a.shape for a in arrays)))
 finalShape = _modifyT(arrays[0].shape, axis, __builtin__.sum( a.shape[axis] for a in arrays))
 if axis==0:
  ret = empty(finalShape)
  nextI = 0
  for a in arrays:
   _cm_row_slice_read(ret._base_shaped(ret.ndim), nextI, nextI+a.size).assign(a._base_shaped(a.ndim))
   nextI += a.size
  return ret
 else:
  return concatenate(tuple([ a.reshape_2d(axis).T for a in arrays]), 0).T.reshape(finalShape)

def where(a, *vararg):
 """
 Note: if only one argument is provided, the returned value will be a tuple of *numpy* arrays of integer indices (gpu arrays can only contain floats).
 """
 if vararg==_t0: return numpy.where(as_numpy_array(a))
 assert len(vararg)==2, 'wrong number of arguments to gnumpy.where()'
 return garray(numpy.where(as_numpy_array(a), as_numpy_array(vararg[0]), as_numpy_array(vararg[1])))

def nonzero(a):
 """ See notes for where(). """
 return where(a)

newaxis = None

def eye(n): return diagflat(ones(n))

def diagflat(a, k=0):
 if isinstance(a, garray): return a.diagflat(k)
 else: return numpy.diagflat(a,k)

def tensordot(a, b, axes=2):
 if type(axes) in _numberTypes: return dot(a.reshape_2d(a.ndim-axes), b.reshape_2d(axes)).reshape(a.shape[:a.ndim-axes] + b.shape[axes:])
 assert len(axes)==2 and len(axes[0])==len(axes[1]), 'the axes parameter to gnumpy.tensordot looks bad'
 aRemove, bRemove = (tuple(axes[0]), tuple(axes[1]))
 return tensordot(a.transpose(filter(lambda x: x not in aRemove, tuple(xrange(a.ndim))) + aRemove),
                  b.transpose(bRemove + filter(lambda x: x not in bRemove, tuple(xrange(b.ndim)))),
                  len(aRemove))



# ------------------------------------------------------------------------------- reductors

def _reductor__base(x, axis, gpuOp, npOp):
 if _isTijmen: numTimeIncurred(x.size, '%s onDim0=%s' % (npOp.__name__, axis in (0, None)))
 if type(x) == numpy.ndarray: return npOp(x, axis)
 if not isinstance(x, garray): x = garray(x)
 if gpuOp==None: return garray(npOp(x.as_numpy_array(), axis))
 else: return gpuOp(x, axis)

def all(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.all, numpy.all)

def any(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.any, numpy.any)

def sum(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.sum, numpy.sum)

def mean(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.mean, numpy.mean)

def max(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.max, numpy.max)

def min(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.min, numpy.min)

def prod(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, None, numpy.prod)

def std(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, None, numpy.std)



# ------------------------------------------------------------------------------- elementwise operations

def _elementwise__base(x, opGpu, opNp):
 if type(x) in _numberTypes: return _check_number_types(float(opNp(x)))
 if opGpu==None or type(x) == numpy.ndarray: # else, time admin happens in the method
  if _isTijmen: numTimeIncurred(x.size, opNp.__name__)
 if isinstance(x, garray):
  if opGpu==None: return _check_number_types(garray(opNp(x.as_numpy_array())))
  else: return _check_number_types(opGpu(x))
 if type(x) == numpy.ndarray:
  if x.ndim==0: return _check_number_types(numpy.array(opNp(x)))
  else: return _check_number_types(opNp(x))
 raise TypeError('value %s of unexpected type %s provided to %s()' % (x, type(x), str(opNp).split("'")[1]))

def abs(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.abs, numpy.abs)

def exp(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.exp, numpy.exp)

def isinf(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.isinf, numpy.isinf)

def isnan(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.isnan, numpy.isnan)

def log(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.log, numpy.log)

def log_1_plus_exp(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.log_1_plus_exp, lambda x: log(1.+exp(x)))

def logistic(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.logistic, lambda x: 1./(1. + exp(-x)))

def negative(x):
 """
 Like -x, except that a zero dimensional numpy array input results in a numpy array return value.
 This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats).
 """
 return _elementwise__base(x, operator.neg, operator.neg)

def sign(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.sign, numpy.sign)

def sqrt(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.sqrt, numpy.sqrt)

def tanh(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.tanh, numpy.tanh)

def log10(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, None, numpy.log10)

def log2(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, None, numpy.log2)

def cos(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, None, numpy.cos)

def sin(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, None, numpy.sin)





class garray(object):
 """
 A class designed to interface like numpy arrays, and internally do its work on a GPU.
 Documentation can be found at http://www.cs.toronto.edu/~tijmen/gnumpy.html
 """

 # ------------------------------------------------------------------------------- internal aux

 def _set_shape_info(self, shape): # setting these as attributes rather than properties saves exec time
  self.shape = shape
  self.size = _prodT(shape)
  self.ndim = len(shape)

 @property
 def nbytes(self): return self.size * 4
 @property
 def nMBytes(self): return self.nbytes / 2**20

 def _base_shaped(self, nDimsAsRows): return _cm_reshape(self._base, (_prodT(self.shape[:nDimsAsRows]), _prodT(self.shape[nDimsAsRows:])))
 def _base_as_row(self): return _cm_reshape(self._base, (1, self.size))
 def _base_as_2d(self): return self._base.reshape((self.shape[1], self.shape[0])) # optimized from self._base_shaped(1) by inlining

 def _new_cm(self, nDimsAsRows=0): return _new_cm((_prodT(self.shape[:nDimsAsRows]), _prodT(self.shape[nDimsAsRows:]))) # same size as self, with given shape

 def _new(self, cm): return garray(cm, self.shape, None) # short notation for the result of elementwise ops

 def _tile_to_broadcast(self, otherShape, indicesToBroadcast='all'):
  """ self.shape and otherShape must already be of the same length. otherShape is relevant only where self.shape is 1. """
  if otherShape == self.shape: return self
  assert self.ndim == len(otherShape), 'dimensionality mismatch in _tile_to_broadcast'
  if indicesToBroadcast=='all': indicesToBroadcast = tuple( i for i in range(self.ndim) if self.shape[i]==1 and otherShape[i]!=1)
  return self.tile( ( 1 if i not in indicesToBroadcast else otherShape[i] ) for i in range(self.ndim))

 def _broadcastable_op(self, other, operatorName):
  """
  accepted ops: "add", "multiply", "less than", "greater than", "pow".
  other must be either scalar or garray.
  """
  basicHandler = {'add': _cmType.add, 'multiply': _cmType.mult, 'less than': _cmType.less_than, 'greater than': _cmType.greater_than, 'pow': _cudamat.pow}[operatorName]
  if (type(other) in _numberTypes or (other.size==1 and other.ndim <= self.ndim)): # having other be a scalar is faster than doing a broadcast
   if _isTijmen: numTimeIncurred(self.size, 'AS eltwise')
   return self._new(basicHandler(self._base_as_row(), ( other.item() if isinstance(other, garray) else other), self._new_cm()))
  if operatorName=='pow': raise NotImplementedError('a**b where b is anything other than a scalar')
  other = as_garray(other)
  if self.ndim > other.ndim: other = other._add_axes(self.ndim)
  if self.ndim < other.ndim: return self._add_axes(other.ndim)._broadcastable_op(other, operatorName)
  if operatorName in ('less than', 'greater than'):
   self2 = self._tile_to_broadcast(other.shape)
   if _isTijmen: numTimeIncurred(self.size, 'eltwise binary, no bc')
   return self2._new(basicHandler(self2._base_as_row(), other._tile_to_broadcast(self2.shape)._base_as_row(), self2._new_cm()))
  if self.ndim < other.ndim: return other._broadcastable_op(self, operatorName) # now self.ndim == other.ndim
  selfToBroadcast =  tuple( self.shape[i]==1 and other.shape[i]!=1 for i in range(self.ndim))
  otherToBroadcast = tuple( other.shape[i]==1 and self.shape[i]!=1 for i in range(self.ndim))
  bc = otherToBroadcast; bci = tuple( i for i in tuple(xrange(len(bc))) if bc[i])
  if reduce(operator.or_, selfToBroadcast, False) and reduce(operator.or_, otherToBroadcast, False): return self._broadcastable_op(other._tile_to_broadcast(self.shape, bci), operatorName)
  if reduce(operator.or_, selfToBroadcast, False): return other._broadcastable_op(self, operatorName) # now only other may have dims that need to be broadcast
  if reduce(operator.or_, ( other.shape[i] not in (1, self.shape[i]) for i in range(self.ndim)), False): raise ValueError('shape mismatch: objects cannot be broadcast to a single shape')
  if not reduce(operator.or_, otherToBroadcast, False): # handle case: nothing to bc
   if _isTijmen: numTimeIncurred(self.size, 'eltwise binary, no bc')
   return self._new(( _cmType.add if operatorName=='add' else _cmType.mult)(self._base_as_row(), other._base_as_row(), self._new_cm()))
  if self.size==0: return self
  if bci == tuple(xrange(len(bci))): # handle case: only the first dims need broadcasting
   if operatorName in ('multiply', 'add') and _isTijmen and usingGpu(): # using optimized cuda code
    ret = empty(self.shape)
    axis0len = _prodT(self.shape[:len(bci)])
    axis1len = _prodT(self.shape[len(bci):])
    nThreadsPerBlock = 512
    nBlocks = axis1len//nThreadsPerBlock+1
    cudaFn = getattr(_cudamat._cudamat, '%sBcAxis0' % operatorName)
    cudaFn.restype = _ctypes.c_int
    assert 0==cudaFn(_ctInt(nBlocks), _ctInt(nThreadsPerBlock), self._base.p_mat, other._base.p_mat, ret._base.p_mat, _ctInt(axis0len), _ctInt(axis1len))
    if _isTijmen: numTimeIncurred(self.size, 'eltwise bc axis 0')
    return ret
   #return self._new(( _cmType.add_col_vec if operatorName=='add' else _cmType.mult_by_col)(self._base_shaped(len(bci)), other._base_as_row(), self._new_cm(len(bci))))
  if bci == tuple(xrange(self.ndim-len(bci), self.ndim)): # handle case: only the last dims need broadcasting
   if _isTijmen: numTimeIncurred(self.size, 'eltwise bc axis -1')
   return self._new(( _cmType.add_row_vec if operatorName=='add' else _cmType.mult_by_row)(self._base_shaped(self.ndim-len(bci)), other._base_shaped(self.ndim-len(bci)), self._new_cm(self.ndim-len(bci))))
  # remaining case: broadcasting neither just the first dims nor just the last dims. this can be done very intelligently, but for now I won't bother
  if operatorName=='multiply' and len(bci)==1 and cudamatHas('multiplyBcAxis1'): # special case: using optimized multiplyBcAxis1 (my cuda code)
   ret = empty(self.shape)
   axisI = bci[0]
   axis0len = _prodT(self.shape[:bci[0]])
   axis1len = self.shape[bci[0]]
   axis2len = _prodT(self.shape[bci[0]+1:])
   _cudamat._cudamat.multiplyBcAxis1.restype = _ctypes.c_int
   assert 0==_cudamat._cudamat.multiplyBcAxis1(_ctInt(__builtin__.min(512, axis2len)),
                                          self._base.p_mat,
                                          other._base.p_mat,
                                          ret._base.p_mat,
                                          _ctInt(axis0len),
                                          _ctInt(axis1len),
                                          _ctInt(axis2len),
                                          )
   if _isTijmen: numTimeIncurred(self.size, 'eltwise bc axis 1')
   return ret
  return self._broadcastable_op(other._tile_to_broadcast(self.shape, bci[:1]), operatorName)

 def _elementwise_unary(self, handler):
  if _isTijmen: numTimeIncurred(self.size, handler.__name__)
  return _check_number_types(self._new(handler(self._base_as_row(), self._new_cm())))

 def _reduction__base(self, operatorName, axis):
  if axis==None: return self.ravel()._reduction__base(operatorName, 0).item()
  if not type(axis) in _numberTypes: raise TypeError('the value %s is not appropriate for the "axis" parameter.' % str(axis))
  if axis < -self.ndim or axis>=self.ndim: raise ValueError('axis (%d) out of bounds for an array with %d axes.' % (axis, self.ndim))
  axis = int(axis) % self.ndim
  if self.size==0:
   retShape = _deleteT2(self.shape, axis)
   if operatorName=='sum': return zeros(retShape)
   elif operatorName=='max': return tile(-inf, retShape)
   else: assert False
  if operatorName=='max' and axis==0 and cudamatHas('maxAxis0'): # my own fast implementation
   ret = empty(self.shape[1:])
   _ctInt = _cudamat.ct.c_int
   nThreadsPerBlock = 32
   gridX, gridY = ((ret.size+nThreadsPerBlock-1)//nThreadsPerBlock), 1
   while gridX>65535: gridY*=2; gridX = (gridX+1)//2;
   _cudamat._cudamat.maxAxis0.restype = _ctypes.c_int
   assert 0==_cudamat._cudamat.maxAxis0(_ctInt(gridX), _ctInt(gridY), _ctInt(nThreadsPerBlock), self._base.p_mat, ret._base.p_mat, _ctInt(self.shape[0]), _ctInt(ret.size))
   return ret
  if axis==0 and operatorName=='max': # max over rows is not yet supported in cudamat
   return self.reshape_2d(1).T.max(1).reshape(self.shape[1:])
  if axis==0 and self.ndim==1 and self.size>5000 and operatorName=='sum': # optimization. apparently, cudamat is not maximally efficient.
   n = int(numpy.sqrt(self.size-1))
   return self[:n*n].reshape((n, n))._reduction__base(operatorName, 0)._reduction__base(operatorName, 0) + self[n*n:]._reduction__base(operatorName, 0)
  if operatorName=='sum':
   chunkSize = 1024*256 # sum over longer dimensions fails in cudamat
   nChunks = (self.shape[axis] + chunkSize-1) // chunkSize
   if nChunks>1:
    return reduceAdd( self[(slice(None),) * axis + (slice(chunkI*chunkSize, __builtin__.min(self.shape[axis], (chunkI+1)*chunkSize)),)]._reduction__base(operatorName, axis)
                      for chunkI in range(nChunks))
  if operatorName=='max' and self.isnan().any2(): # cudamat bug workaround
   return garray(self.asarray().max(axis))
  operatorInCm = {'sum': _cmType.sum, 'max': _cmType.max}[operatorName]
  if axis==0: return _check_number_types(garray(operatorInCm(self._base_shaped(1), 1, _new_cm(_prodT(self.shape[1:]))), self.shape[1:], None))
  if axis==self.ndim-1:
   if self.ndim!=2: return self.reshape_2d(-1)._reduction__base(operatorName, 1).reshape(self.shape[:-1])
   if self.ndim==2:
    chunkSize = 2**16-1
    nChunks = (len(self) + chunkSize-1) // chunkSize
    if nChunks>1: # cudamat chokes on big arrays, so break it in pieces for cudamat
     chunks = tuple([ self[chunkI*chunkSize : __builtin__.min((chunkI+1)*chunkSize, len(self))]
                      for chunkI in range(nChunks)])
     return concatenate([ chunk._reduction__base(operatorName, 1) for chunk in chunks])
    else: # small array
     return _check_number_types(garray(operatorInCm(self._base_shaped(1), 0, _new_cm((len(self), 1))), (len(self),), None))
  return self.transpose_simple(axis)._reduction__base(operatorName, 0).transpose_simple(-axis)



 # ------------------------------------------------------------------------------- external misc non-numerical

 def __init__(self, data, copy=True, ndmin=0):
  """ the parameters mean the same as in numpy.array() """
  if type(data)!=_cmType: assert copy in (True, False) and type(ndmin) in _numberTypes, 'garray() parameters copy=%s, ndmin=%s are not of the right type' % (str(copy), str(ndmin))
  if type(data)==_cmType: # internal use only. the 3 arguments are, unlike their names suggest, the ._base, .shape, ._is_alias_of
   self._base = data
   self._set_shape_info(copy)
   self._is_alias_of = ndmin
   if self._is_alias_of==None and track_memory_usage:
    self.allocating_line = _calling_line()
    tracked_arrays[id(self)] = self
    _memoryUsers[self.allocating_line] = (_memoryUsers[self.allocating_line][0]+1, _memoryUsers[self.allocating_line][1]+self.size*4)
  elif isinstance(data, garray):
   if ndmin>0: data = data._add_axes(ndmin)
   garray.__init__(self,
    ( _new_cm(data.size).assign(data._base_as_row()) if copy else data._base),
    data.shape,
    ( None if copy else data))
  elif type(data) == types.GeneratorType: garray.__init__(self, tuple(data), ndmin=ndmin)
  elif _isSequence(data):
   if len(data)==0 or not _any2_(data, is_garray): garray.__init__(self, numpy.array(data, ndmin=ndmin), copy=False)
   else: garray.__init__(self, concatenate( as_garray(element)[None] for element in data), ndmin=ndmin) # no need to copy, because concat copies.
  else: # remaining cases. essentially init from numpy array.
   npa = numpy.array(data, copy=False) # in case data was a number
   if str(npa.dtype) in ('object', '|S3'): raise TypeError('Cannot convert "%s" to a garray.' % data)
   # we're not using the cudamat constructor, because that always allocs gpu mem, and this way the mem may come from re-use.
   cm = _new_cm(npa.size)
   if not hasattr(cm, 'numpy_array'):
    #cm.copy_to_host() # if cm was created using cudamat.empty, this is needed to associate cm with a numpy array
    # follows an inlined version of the relevant portion of cm.copy_to_host(). This is quicker because it doesn't actually copy.
    cm.numpy_array = numpy.empty((cm.mat.size[0], cm.mat.size[1]), dtype=numpy.float32, order='F')
    cm.mat.data_host = cm.numpy_array.ctypes.data_as(_ctypes.POINTER(_ctypes.c_float))
    cm.mat.on_host = 1
   if npa.size!=0: cm.numpy_array[:] = npa.reshape((-1, 1), order='C') # no cudamat.reformat is needed, because that's only dtype and order change, which are handled by the assignment anyway
   cm.copy_to_device()
   garray.__init__(self, cm, _extend_shape(npa.shape, ndmin), None)

 def __new__(cls, *args, **kwarg): return object.__new__(cls)

 def as_numpy_array(self, dtype=numpy.float64):
  if self.size==0: return numpy.zeros(self.shape, dtype)
  return numpy.array(self._base_as_row().asarray(), copy=True, order='C', dtype=dtype).reshape(self.shape)

 asarray = as_numpy_array # the cudamat name

 def astype(self, type): return self.asarray().astype(type)

 tile = tile

 def ravel(self): return self.reshape(-1)

 def item(self): return self.as_numpy_array().item()

 def _add_axes(self, finalNdim): return self.reshape(_extend_shape(self.shape, finalNdim))

 def sort(self, axis=-1, kind='quicksort', order=None):
  """ like numpy.sort, this sorts in place and returns None. """
  temp = self.as_numpy_array()
  temp.sort(axis, kind, order)
  self[:] = temp

 def reshape(self, *newShape):
  if len(newShape)==1 and not type(newShape[0]) in _numberTypes: newShape = tuple(newShape[0])
  if not _all2_(newShape, _isNumber): raise TypeError('the parameters to reshape don\'t look like a valid shape')
  if -1 in newShape:
   if _prodT(newShape)==0: raise ValueError("-1 as a parameter to reshape is not allowed if one of the other parameters is zero.")
   newShape = _modifyT(newShape, operator.indexOf(newShape, -1), self.size//-_prodT(newShape))
  if _prodT(newShape) != self.size: raise ValueError('the total number of items cannot be changed in a reshape')
  return garray(self._base, newShape, self)

 def reshape_2d(self, n_dimensions_as_rows):
  """ reshapes to 2 axes. The first <n_dimensions_as_rows> axes of the array become the first axis of the returned value. The remaining ones form the second axis. """
  if n_dimensions_as_rows<0: n_dimensions_as_rows += self.ndim
  return self.reshape((_prodT(self.shape[:n_dimensions_as_rows]), _prodT(self.shape[n_dimensions_as_rows:])))

 @property
 def T(self):
  if self.ndim==2: # _base case
   if self.size==0: return self.reshape(tuple(reversed(self.shape))) # cudamat bug workaround
   if self.shape[1]>1e6: # cudamat bug workaround. with 2m columns it fails
    return concatenate([ self[:, i*10**6 : (i+1)*10**6].T for i in range((self.shape[1]+10**6-1)//10**6)])
   if self.shape[0]>1e6: # cudamat bug workaround. using concat is not an option, because that uses transpose.
    ret = empty(tuple(reversed(self.shape)))
    for i in range((self.shape[0]+10**6-1)//10**6):
     ret[:, i*10**6 : (i+1)*10**6] = self[i*10**6 : (i+1)*10**6].T
    return ret
   return garray(self._base_as_2d().transpose(_new_cm(tuple(reversed(self.shape)))), tuple(reversed(self.shape)), None)
  else: return self.transpose()

 def transpose_simple(self, nDimsToGroup):
  """ shifts the first <nDimsToGroup> axes to the end, and the remaining ones to the start. This returns a new array, not an alias. """
  if nDimsToGroup<0: nDimsToGroup += self.ndim
  return self.reshape_2d(nDimsToGroup).T.reshape(self.shape[nDimsToGroup:] + self.shape[:nDimsToGroup])

 def transpose(self, *axes):
  """ like numpy.transpose, except that this doesn't return an alias, but rather a new array. """
  # This is not really supported by cudamat, so it takes creativity. I handle a variety of cases differently.
  if len(axes)==1 and not type(axes[0]) in _numberTypes: axes = tuple(axes[0])
  if axes==_t0: axes = tuple(reversed(tuple(xrange(self.ndim))))
  if axes == tuple(xrange(self.ndim)): return self.copy()
  if tuple(sorted(axes)) != tuple(xrange(self.ndim)): raise ValueError("%s is not a valid argument to transpose() of an array of %d axes" % (axes, self.ndim))
  for i in range(self.ndim-1):
   if axes[i+1]==axes[i]+1: return (self. # see if the task can be simplified by collapsing some axes that are kept adjacent
    reshape(self.shape[:axes[i]] + (_prodT(self.shape[axes[i]:axes[i]+2]),) + self.shape[axes[i]+2:]).
    transpose((originalAxisI-(originalAxisI>axes[i])) for originalAxisI in _deleteT2(axes, i+1)).
    reshape(self.shape[axisI] for axisI in axes))
  if self.ndim==3 and hasattr(_cudamat, '_cudamat') and cudamatHas('transpose3') and self.size!=0:
   reorderingI = {(0, 2, 1): 0, (1, 0, 2): 1, (2, 1, 0): 2}[axes]
   ret = empty(tuple( self.shape[axisI] for axisI in axes))
   gridX, gridY = (self.size+511)//512, 1
   while gridX>65535: gridY*=2; gridX = (gridX+1)//2;
   _cudamat._cudamat.transpose3.restype = _ctypes.c_int
   assert 0==_cudamat._cudamat.transpose3(_ctInt(gridX), _ctInt(gridY), self._base.p_mat, ret._base.p_mat, _ctInt(self.shape[0]), _ctInt(self.shape[1]), _ctInt(self.shape[2]), _ctInt(reorderingI))
   return ret
  def shiftAxesRight(shiftN): return self.transpose_simple(-shiftN).transpose( (axisI+shiftN)%self.ndim for axisI in axes)
  for i in range(self.ndim-1): # see if the task can be simplified by rotating axes right by 1. if so, the loop before this one can simplify further
   if axes[i:i+2] == (self.ndim-1, 0): return shiftAxesRight(1)
  # no further simplifications can be done. we need to proceed with a loop over the first axis. First rotate the intended axis to position 0.
  if axes[0]!=0: return shiftAxesRight(-axes[0])
  ret = empty( self.shape[axisI] for axisI in axes)
  for i in range(self.shape[0]): ret[i] = self[i].transpose( x-1 for x in axes[1:])
  return ret

 def copy(self): return garray(self, copy=True)

 def diagflat(self, k=0):
  if self.ndim!=1: return self.ravel().diagflat(k)
  if k!=0: raise NotImplementedError('k!=0 for garray.diagflat')
  selfSize = self.size
  ret = zeros((selfSize, selfSize))
  ret.ravel()[:-1].reshape((selfSize-1, selfSize+1))[:, 0] = self[:-1]
  if selfSize!=0: ret.ravel()[-1] = self[-1]
  return ret

 def diagonal(self):
  if self.ndim==1: return self.diagflat()
  if self.ndim==2:
   if self.shape[0] > self.shape[1]: return self[:self.shape[1]].diagonal()
   if self.shape[1] > self.shape[0]: return self[:, :self.shape[0]].diagonal()
   return self.ravel()[::self.shape[0]+1]
  raise NotImplementedError('garray.diagonal for arrays with ndim other than 1 or 2.')
 def diag(self): return self.diagonal()



 # ------------------------------------------------------------------------------- elementwise type checking

 def all_real(self):
  """ returns True iff all array elements are regular floats, as opposed to inf's, -inf's, and NaN's.  """
  return (self*0).sum()==0

 def isinf(self):
  """ elementwise, checking for inf or -inf. """
  return 1 - self.isreal() - self.isnan()

 def isreal(self):
  """ elementwise, checking for real numbers. See also .all_real() """
  return (self<numpy.inf) * (self>-numpy.inf)

 def isnan(self):
  """ elementwise, checking for NaN's. """
  return (self>0) + (self<1) < .5

 def isnumber(self):
  """ elementwise, checking for anything other than NaN's """
  return (self>0) + (self<1) > .5



 # ------------------------------------------------------------------------------- external misc numerical

 def __abs__(self): return self._elementwise_unary(_cudamat.abs)
 def abs(self): return __builtin__.abs(self)
 def as_bool(self): return self!=0
 def exp(self): return self._elementwise_unary(_cudamat.exp)
 def log(self): return self._elementwise_unary(_cudamat.log)
 def log_1_plus_exp(self): return self._elementwise_unary(_cudamat.log_1_plus_exp)
 def logistic(self): return self._elementwise_unary(_cudamat.sigmoid)
 sigmoid = logistic
 def sign(self): return self._elementwise_unary(_cmType.sign)
 def sqrt(self): return self._elementwise_unary(_cudamat.sqrt)
 def tanh(self): return self._elementwise_unary(_cudamat.tanh)


 def sum(self, axis=None): return self._reduction__base('sum', axis)
 def max(self, axis=None): return self._reduction__base('max', axis)
 def mean(self, axis=None): return self.sum(axis) / ( self.size if axis==None else self.shape[axis])
 def argmax(self, axis=None): return numpy.argmax(self.asarray(), axis)
 def argmin(self, axis=None): return numpy.argmin(self.asarray(), axis)
 def min(self, axis=None): return -(-self).max(axis)
 def all(self, axis=None): return ( True if self.size==0 else (self.as_bool()).min())
 def any(self, axis=None): return ( False if self.size==0 else (self.as_bool()).max())

 def all2(self, axis=None): return 1-(1-self).any2(axis)  # optimized for when I'm sure that the content is boolean
 def any2(self, axis=None): return self.sum(axis) > 0  # optimized for when I'm sure that the content is boolean

 def rand(self, distribution = 'uniform'):
  """
  returns a new garray, of the same shape as self, filled with random numbers.
  <distribution> can be either 'uniform' or 'normal'.
  """
  return _rand__base(self.shape, distribution, False)

 def euclid_norm(self): return self._base.euclid_norm()

 dot = dot
 where = where
 nonzero = nonzero

 def __nonzero__(self): return self.size==1 and self.item()!=0


 # ------------------------------------------------------------------------------- operator overloads, numerical

 def __add__(self, other): return _check_number_types(self._broadcastable_op(as_garray_or_scalar(other), 'add'))
 def __mul__(self, other): return _check_number_types(self._broadcastable_op(as_garray_or_scalar(other), 'multiply'))
 def __or__(self, other): return (self.as_bool() + other.as_bool()).as_bool()
 def __and__(self, other): return self.as_bool() * other.as_bool()

 def __pow__(self, other, modulo=None):
  if modulo!=None: raise NotImplementedError('power with modulo')
  if type(other) in _numberTypes and other==2: return self*self # faster
  return self._broadcastable_op(as_garray_or_scalar(other), 'pow')


 # the following would be a lot simpler if I wouldn't have to deal with nans

 def __lt__(self, other): return _check_number_types(self._broadcastable_op(as_garray_or_scalar(other), 'less than'))

 def __gt__(self, other): return _check_number_types(self._broadcastable_op(as_garray_or_scalar(other), 'greater than'))

 def __le__(self, other): return self.isnumber() * as_garray(other).isnumber() * (1-(self>other))

 def __ge__(self, other): return self.isnumber() * as_garray(other).isnumber() * (1-(self<other))

 def __ne__(self, other): return ( 1-(self==other) if type(other) in _castableTypes else True)

 def __eq__(self, other): return ( (self<=other) * (self>=other) if type(other) in _castableTypes else False)

 def eq2(self, other):
  """
  Returns a boolean: True if self and other are the same (arrays with the same shape and contents); False otherwise.
  This is what == does on most Python objects (on arrays it's been strangely overloaded though).
  garrays compare equal to numpy arrays with the same contents, even if the data types differ.
  """
  if self is other: return True
  if not is_array(other): return False
  if self.shape != other.shape: return False
  return all(self==other)==1

 def __sub__(self, other):
  if isinstance(other, garray) and other.shape==self.shape: # use specialized method
   return self._new(self._base_as_row().subtract(other._base_as_row(), self._new_cm()))
  else: return self + -as_garray(other) # if i need to broadcast, making use of the row add and col add methods is probably faster

 def __div__(self, other):
  if type(other) in _numberTypes: return self * (1./other)
  other = as_garray(other)
  return self * other._new(other._base_as_row().reciprocal(other._new_cm()))

 def __rmul__(self, other): return self*other
 def __radd__(self, other): return self+other
 def __rsub__(self, other): return other + -self
 def __rdiv__(self, other): return as_garray(other) / self
 def __rpow__(self, other): raise NotImplementedError('a**b where only b is a garray')

 def __pos__(self): return self
 def __neg__(self): return self*-1

 def __iadd__(self, other): self[_t0] = self+other; return self # not as direct as it might have been, but the effect is the same. "self[:]" doesn't work for 0das.
 def __imul__(self, other): self[_t0] = self*other; return self
 def __isub__(self, other): self[_t0] = self-other; return self
 def __idiv__(self, other): self[_t0] = self/other; return self
 def __imod__(self, other): self[_t0] = self%other; return self
 def __ipow__(self, other, modulo=None): self[_t0] = self.__pow__(other, modulo); return self



 # ------------------------------------------------------------------------------- operator overloads, non-numerical

 def __len__(self):
  if self.ndim==0: raise TypeError('len() of unsized object')
  return self.shape[0]

 def __getitem__(self, selectors):
  selectors = _nonSeqAsS(selectors)
  for i,sel in enumerate(selectors): # deal with newaxis and ellipsis
   if sel is Ellipsis: return self[selectors[:i] + (slice(None),)* (self.ndim - (__builtin__.sum( x != None for x in selectors)-1)) + selectors[i+1:]] # sel==Ellipsis is bad when sel is an array
   if sel is newaxis: return self.reshape(_insertT(self.shape, i, (1,)))[_modifyT(selectors, i, slice(None))]
  if len(selectors) > self.ndim: raise IndexError('more indices than axes')
  if _all2_(selectors, _isFullSlice): return self
  if reduce(operator.and_, ( _isSequence(sel) or is_array(sel) for sel in selectors), True) and len(selectors)>=2:
   selectors = tuple(map(as_garray, selectors))
   if reduce(operator.or_, ( (sel < 0).sum() > 0 for sel in selectors), False): raise NotImplementedError('negative indices in index arrays, combined with having multiple indices arrays')
   # ravel the first two dimensions into one, and translate the corresponding indices arrays into one accordingly
   return self.reshape((self.shape[0]*self.shape[1],) + self.shape[2:])[(selectors[0]*self.shape[1]+selectors[1],) + selectors[2:]]
  if __builtin__.sum( _isSequence(sel) or is_array(sel) for sel in selectors)>1:
   raise NotImplementedError('slicing with more than one sequence/array among the indices, with also other kinds of values among the indices')
  # handle the operations on different axes one by one; earlier axes are handled earlier
  axisI = ( i for i, x in enumerate(selectors) if not _isFullSlice(x)).next()
  axisLen = self.shape[axisI]
  axisSelector = selectors[axisI]
  if not _all2_(selectors[axisI+1:], _isFullSlice): return self[selectors[:axisI+1]][(slice(None),)*(axisI+(not type(axisSelector) in _numberTypes)) + selectors[axisI+1:]] # first select on axisI only; then do the further axes.
  # from here, axisI is the only axis on which we don't take a full slice
  if type(axisSelector) == types.SliceType and axisSelector.step not in (1, None): axisSelector = numpy.arange(axisLen)[axisSelector]
  if type(axisSelector) in _numberTypes: # selecting a single location on axisI, and thus reducing the dimensionality by 1
   ret = self[selectors[:axisI] + (_short_slice(_read_single_index(axisSelector, axisLen)),)]  .reshape(_deleteT2(self.shape, axisI))
   return ( ret.item() if ret.shape==_t0 else ret) # exception, to have the same behavior as numpy
  if _isSequence(axisSelector) or type(axisSelector) == numpy.ndarray: axisSelector = garray(axisSelector)
  if isinstance(axisSelector, garray):
   # a 1d index means re-arranging this axis. I.e. a number of length 1 selections on this axis, concatenated on this axis.
   # other dimensionality means using the raveled version, and then reshaping to reflect the selector dimensionality
   if hasattr(_cmType, 'select_columns'):
    if axisI==0:
     if _doExpensiveCheck() and (axisSelector> len(self)-.01).sum() !=0: raise IndexError('index %d (found in an indices array) is too large, for an axis of length %d' % (max(axisSelector), len(self)))
     if _doExpensiveCheck() and (axisSelector<-len(self)-.5).sum() !=0: raise IndexError('index %d (found in an indices array) is too small, for an axis of length %d' % (min(axisSelector), len(self)))
     return garray(self._base_shaped(1).select_columns(axisSelector._base_shaped(axisSelector.ndim), _new_cm((axisSelector.size, self.size/self.shape[0]))), axisSelector.shape + self.shape[1:], None)
    else: return self.transpose_simple(axisI)[axisSelector].transpose_simple(-axisI)
   else: return (concatenate(tuple( self[_modifyT(selectors, axisI, slice(choiceOnThisAxis, choiceOnThisAxis+1))] for choiceOnThisAxis in axisSelector.ravel()), axisI)
                 .reshape(self.shape[:axisI] + axisSelector.shape + self.shape[axisI+1:]))
  if not type(axisSelector) == types.SliceType: raise ValueError('index not understood: %s' % axisSelector)
  # from here, selector is a simple slice
  sFrom, sTo, sLen = _read_simple_slice(axisSelector, axisLen)
  retShape = _modifyT(self.shape, axisI, sLen)
  if _prodT(retShape)==0: return zeros(retShape)
  if axisI==0: return garray(_cm_row_slice_read(self._base_shaped(1), sFrom, sTo), retShape, self) # slice on axis 0 is free, using _cm_row_slice_read
  if axisI!=1: return self.reshape((_prodT(self.shape[:axisI]),) + self.shape[axisI:])[:, sFrom:sTo].reshape(retShape) # redirect: collapse earlier axes into one
  if self.ndim != 2: return self.reshape_2d(1)[:, sFrom * _prodT(self.shape[axisI+1:]) : sTo * _prodT(self.shape[axisI+1:])].reshape(retShape) # redirect: use long elements
  chunkSize = int(2e6)
  nChunks = (len(self) + chunkSize - 1) // chunkSize
  if nChunks>1: return concatenate( tuple(self[chunkI*chunkSize : (chunkI+1)*chunkSize, sFrom:sTo] for chunkI in range(nChunks)), 0) # redirect in batches, bc cudamat chokes on big jobs, i.e. jobs with many rows
  if self.shape[0]==1: # then redo as row slice. This also avoids a cudamat limitation (on slicing many columns), sometimes.
   return self.ravel()[sFrom:sTo][newaxis].copy()
  # _base case for column slice
  retCm = _new_cm(retShape)
  _cm_col_slice_read(self._base_shaped(1), sFrom, sTo, retCm)
  return garray(retCm, retShape, None)

 def __iter__(self):
  for i in tuple(xrange(len(self))): yield self[i]

 def __setitem__(self, selectors, other):
  # this is different from getitem. There, I can handle the axes one at a time. Here, it's more integrated.
  selectors = _nonSeqAsS(selectors)
  for i,sel in enumerate(selectors): # deal with ellipsis
   if sel is Ellipsis: return self.__setitem__(selectors[:i] + (slice(None),)* (self.ndim - (len(selectors)-1)) + selectors[i+1:], other) # sel==Ellipsis is bad when sel is an array
  if len(selectors) > self.ndim: raise IndexError('more indices than axes')
  if reduce(operator.and_, ( is_array(sel) or _isSequence(sel) for sel in selectors), True) and selectors!=_t0:
   if len(selectors)==1:
    if not hasattr(_cmType, 'set_selected_columns'):
     raise NotImplementedError("slice assign with a sequence/array as index. Get the newest version of cudamat (or npmat if you're running on the cpu).")
    sel = as_garray(selectors[0])
    if len(sel) != len(other): raise ValueError('number of rows to set != number of provided rows')
    if other.shape[1:] != self.shape[1:]: raise ValueError('shape mismatch in assignment')
    if sel.ndim!=1: raise NotImplementedError('assignment with as index an array of ndim!=1')
    if sel.size==0: return # the current implementation of set_selected_columns doesn't handle that well
    self._base_shaped(1).set_selected_columns(sel._base_shaped(1), other._base_shaped(1))
   else: # >1 selectors, all arrays/sequences. ravel the first dimension of self, and correspondingly unify the first two selectors
    self.reshape((_prodT(self.shape[:2]),) + self.shape[2:])[(as_garray(selectors[0])*self.shape[1]+as_garray(selectors[1]),) + selectors[2:]] = as_garray(other)
   return
  if reduce(operator.or_, ( _isSequence(axisSel) or is_array(axisSel) for axisSel in selectors), False): raise NotImplementedError('slice assign with a sequence/array as index, as well as other indexing objects')
  if reduce(operator.or_, ( type(axisSel) == types.SliceType and axisSel.step not in (1, None) for axisSel in selectors), False): raise NotImplementedError('slice assign with stride != 1')
  if not reduce(operator.and_, ( type(axisSel) in _numberTypes or type(axisSel) == types.SliceType for axisSel in selectors), True): raise ValueError('index not understood, in slice assignment.')
  selectors = selectors + (slice(None),)*(self.ndim-len(selectors))
  # now len(selectors) == ndim, and all selectors are single indices or simple slices
  # task: broadcast other, and do shape check.
  other = as_garray_or_scalar(other)
  assignedShape = tuple( _read_simple_slice(axisSel, self.shape[axisI])[2] for axisI, axisSel in enumerate(selectors) if not type(axisSel) in _numberTypes)
  if isinstance(other, garray):
   if other.ndim < len(assignedShape): other = other._add_axes(len(assignedShape))
   if other.ndim > len(assignedShape):
    if _prodT(other.shape[: other.ndim-len(assignedShape)]) != 1: raise ValueError('Incompatible shapes in slice assign: the assigned area has shape %s, and the incoming values have shape %s.' % (assignedShape, other.shape))
    other = other.reshape(other.shape[-len(assignedShape):])
   # now other.ndim == len(assignedShape)
   if not reduce(operator.and_, ( other.shape[axisNr] in (1, assignedShape[axisNr]) for axisNr in tuple(xrange(len(assignedShape)))), True):
    raise ValueError('Incompatible shapes in slice assign: the incoming values have shape %s, but the assigned area has shape %s.' % (other.shape, assignedShape))
   other = other._tile_to_broadcast(assignedShape)
  # the only time I can use scalar assign is when I don't need cudamat's column assign at all. that only happens when all selectors other than optionally the first are full slices.
  if _all2_(selectors[1:], _isFullSlice):
   ( _cm_row_slice_read(self._base_shaped(1), _read_single_index(selectors[0], self.shape[0]), _read_single_index(selectors[0], self.shape[0])+1)
     if self.ndim==1 and type(selectors[0]) in _numberTypes else
     self[selectors[:1]]._base_as_row() # I want this to work even when selectors = _t0
     ).assign( other if type(other) in _numberTypes else other._base_as_row())
   return
  if type(other) in _numberTypes: other = garray(other)._add_axes(len(assignedShape))._tile_to_broadcast(assignedShape)
  # now other is a garray of exactly the expected shape, and there are things other than complete slices beyond axis #0 so I'm going to need a col assign.
  # task: get rid of single indices in selectors
  for i in range(self.ndim):
   if type(selectors[i]) in _numberTypes:
    selectors = _modifyT(selectors, i, _short_slice(_read_single_index(selectors[i], self.shape[i])))
    other = other.reshape(_insertT(other.shape, i, (1,)))
  if not _isFullSlice(selectors[0]): return self[selectors[0]].__setitem__((slice(None),) + selectors[1:], other)
  # now all selectors are either full or simple slices; axis 0 is a full slice; and at least one other axis is a simple slice.
  axisI = ( i for i, x in enumerate(tuple( not _isFullSlice(sel) for sel in selectors)) if x).next()
  if _all2_(selectors[axisI+1:], _isFullSlice): # then do a column slice assign directly using cudamat.
   sFrom, sTo = _read_simple_slice(selectors[axisI], self.shape[axisI])[:2]
   elementWidth = _prodT(self.shape[axisI+1:])
   if other.size!=0: # cudamat chokes on that
    _cm_col_slice_write(self._base_shaped(axisI), sFrom*elementWidth, sTo*elementWidth, other._base_shaped(axisI))
   return
  # remaining case: there are multiple non-full slices, and the slice on axis 0 is full. strategy: transpose to bring one of those non-full slices to the front.
  selfT = self.transpose_simple(axisI)
  selfT[selectors[axisI:] + selectors[:axisI]] = other.transpose_simple(axisI)
  self._base_as_row().assign(selfT.transpose_simple(self.ndim-axisI)._base_as_row())



 # ------------------------------------------------------------------------------- external, but not for user to see

 def __getstate__(self):
  return (self.shape, self._base_as_row().asarray())

 def __setstate__(self, state):
  garray.__init__(self, state[1])
  self._set_shape_info(state[0])

 def __array__(self, *dtype):
  _envInstruction = _os.environ.get('GNUMPY_IMPLICIT_CONVERSION', 'refuse')
  assert _envInstruction in ('allow', 'warn', 'refuse'), "environment variable GNUMPY_IMPLICIT_CONVERSION, if present, should be one of 'allow', 'warn', 'refuse'."
  if _envInstruction=='refuse': raise TypeError("garray objects cannot be quietly converted to numpy arrays, because the environment variable GNUMPY_IMPLICIT_CONVERSION is set to 'refuse', or is not set at all (the default is 'refuse'). Set that variable to 'allow' or 'warn' if you wish to allow quiet conversion. garray's can always be explicitly converted using the .as_numpy_array() method.")
  if _envInstruction=='warn': print "gnumpy: warning: a garray object is being quietly converted to a numpy array, and the environment variable GNUMPY_IMPLICIT_CONVERSION is set to 'warn'. garray objects can be explicitly converted using the .as_numpy_array() method."
  return self.as_numpy_array().__array__(*dtype)

 def __repr__(self): return self.as_numpy_array().__repr__().replace('array(', 'garray(').replace('\n', '\n ').replace(', dtype=float32', '').replace(', dtype=float64', '') # 64 happens for empty arrays

 def __del__(self):
  if not hasattr(self, '_is_alias_of'):
   if _isTijmen: print 'gnumpy cleaning up an unfinished garray. mem counting may be off now.'
   return # this object was never finished, because an exception (error or interrupt) occurred in the constructor. This check avoids error messages.
  if self._is_alias_of is None:
   # this is not true in one case: if a reference to self._base is stored somewhere explicitly (somewhere outside self but not in another garray). This happens internally sometimes. I saw it happening on the last line of setitem: a transpose is created (transposes own their mem, are not aliases), and then it's dropped but _base (obtained by _base_as_row) is still in use for a cm assign call. assert _sys.getrefcount(self._base)==2, _sys.getrefcount(self._base)
   _cmsForReuse[self.size].append(self._base)
   if track_memory_usage: _memoryUsers[self.allocating_line] = (_memoryUsers[self.allocating_line][0]-1, _memoryUsers[self.allocating_line][1]-self.size*4)
  else:
   assert type(self._is_alias_of).__name__ == 'garray', '_is_alias_of is of unexpected type, of which the str() is: "%s"' % str(type(self._is_alias_of))
   # del self._base # this is only to make the refcount assert not fail




_castableTypes = _numberTypes | set([tuple, list, numpy.array, garray])


########NEW FILE########
__FILENAME__ = npmat


import os, pdb, time, warnings
import numpy as np

__DTYPE__ = np.float64


def dummy():
    return CUDAMatrix(np.zeros((1, 1)))

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used."""

    def newFunc(*args, **kwargs):
        warnings.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning)
        return func(*args, **kwargs)
    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

#from cudamat import CUDAMatException
class CUDAMatException(Exception):
    pass



IncompatibleDimensionsException = CUDAMatException("Incompatible matrix dimensions.")

InvalidConfig = CUDAMatException("Invalid Configuration Error (i.e., a dim of the array must be smaller than 2**16.")
## TODO: Figure out which functions produce an invalid config error. These are those who allocate a thread per col/row/elem.
## Those who allocate a bunch of rows per thread, like mult, add, sub, etc, should be immune to the invalid
## configuration error. PS: this error occurs on the real cudamat, which is why it happens.
## Sum/Max/Cumsum
MAX_DIM = 2**16


class CUDAMatrix(object):
    """
    A CUDAMatrix object represents a matrix of single precision floating point
    numbers on a GPU.
    """

    def __init__(self, array, ref=True):
        if ref:
            self.numpy_array = reformat(array)
        else:
            self.numpy_array = array
        assert self.numpy_array.ndim == 2
        self.trans = False

    def __del__(self):
        pass

    @staticmethod
    def init_random(seed):
        import numpy.random as random
        random.seed(seed)



    @property
    def num_elems(self):
        return self.numpy_array.size

    @property
    def shape(self):
        return self.numpy_array.shape

    def cheap_transpose(self):
        return CUDAMatrix(self.reshape((self.shape[1], self.shape[0])))

    def reshape(self, shape):
        assert shape[0]*shape[1] == self.shape[0]*self.shape[1]
        #self.numpy_array.resize(shape)
        #self.numpy_array = self.numpy_array.reshape(shape, order='F')
        self.numpy_array.resize(*shape)
        return self


    def copy(self):
        return empty().assign(self)


    def set_np_array(self, X):
        assert X.shape == self.shape
        self.numpy_array[:] = X
        self.copy_to_device()
        return self



    def zero_copy(self):
        return self.copy().assign(0)


    def resize(self, shape):

        if self.shape != shape:

            print 'CUDAMatrix: resize (%s -> %s)' % (self.shape, shape)
            #self.numpy_array = np.resize(self.numpy_array, shape).astype(__DTYPE__)
            self.numpy_array.resize(shape)
            self.numpy_array[:] = 0


        return self

    @property
    def T(self):
        return CUDAMatrix(self.numpy_array.T)

    @property
    def mat(self):
        return self.numpy_array


    @deprecated
    def set_shape(self, shape):
        return self.resize(shape)


    def asarray(self):
        """
        Copies the matrix to an ndarray on the CPU and returns it.
        """

        #return reformat(self.numpy_array.copy())
        return self.numpy_array

    def copy_to_device(self):
        """
        Copy the matrix to the GPU.
        """

        pass



    def select_columns(self, indices, target):
        """
        copies some columns of self into target.
        <indices> must be a row vector. Its elements are float32's representing integers, e.g. "34.0" means the integer "34".
        after this call, for all r,c, target[r,c]=self[r,indices[c]].
        This returns target.
        Negative indices are interpreted in the usual Python way: all elements of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
        This does bounds checking, but out of bounds indices do not raise an exception (because the programmer was lazy). Instead, they result in NaN values in <target>.
        """

        assert target.shape[0]==self.shape[0]
        assert indices.shape[0]==1
        assert indices.shape[1] == target.shape[1]

        for c in range(target.shape[1]):
            try:
                target.numpy_array[:,c] = self.numpy_array[:, int(indices.numpy_array.ravel()[c])]
            except IndexError:
                target.numpy_array[:,c] = np.nan
        return target

    def set_selected_columns(self, indices, source):
        """
        copies all columns of source into some columns of self.
        <indices> must be a row vector. Its elements are float32's representing
        integers, e.g. "34.0" means the integer "34". after this call, for all
        r,c, self[r,indices[c]]=source[r,c]. This returns self.
        Negative indices are interpreted in the usual Python way: all elements
        of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
        This does bounds checking, but out of bounds indices do not raise an
        exception (because the programmer was lazy). Instead, they result in NaN
        values in <self>.
        """

        assert self.shape[0]==source.shape[0]
        assert indices.shape[0]==1
        assert indices.shape[1]==source.shape[1]

        for c in range(source.shape[1]):
            try:
                self.numpy_array[:,int(indices.numpy_array.ravel()[c])] = source.numpy_array[:,c]
            except IndexError:
                self.numpy_array[:,int(indices.numpy_array.ravel()[c])] = np.nan
        return self


    def copy_to_host(self):
        """
        Copy the matrix to the CPU.
        """
        return self.asarray()


    def np(self):
        return self.copy_to_host()




    def assign(self, val):
        """Assign val to self, where val can be a scalar or a CUDAMatrix
        with the same dimensions as self. """


        if isinstance(val, CUDAMatrix):
            self.resize(val.shape)
            self.numpy_array[:] = val.numpy_array


        elif isinstance(val, (int, float, __DTYPE__)):
            self.numpy_array[:] = val

        return self

    def free_device_memory(self):
        """
        Free memory used up by the matrix on the GPU.
        """
        pass


    def set_trans(self, is_trans):
        """
        Set the transposedness flag to is_trans.
        """
        if is_trans is True:
            self.numpy_array = self.numpy_array.T



    def slice(self, first_col, last_col):
        return CUDAMatrix(self.numpy_array[:, first_col:last_col], ref=False)

    def get_row_slice(self, start, end, target = None):
        """
        Get the rows with indices start through end. If target is not provided
        memory for a new matrix will be allocated.
        """



        ans = CUDAMatrix(self.numpy_array[start:end, :].copy())

        if target is not None:
            target.assign(ans)
        else:
            target = ans

        return target


    def set_row_slice(self, start, end, mat):
        try:
            self.numpy_array[start:end] = mat.numpy_array
        except ValueError:
            raise IncompatibleDimensionsException
        return self


    def get_col_slice(self, start, end, target = None):
        ## NOTE: no .copy()
        ans = self.slice(start, end)

        if target is not None:
            target.assign(ans)
        else:
            target = ans

        return target

    def set_col_slice(self, start, end, mat):
        return self.slice(start, end).assign(mat)





    # def select_columns(self, indices, target):
    #     """
    #     Copies selected columns into a target matrix.
    #     <self>, <indices>, and <target> are all cudamat matrices.
    #     <self> is an M by K matrix.
    #     <indices> is of shape 1 by N. All elements x are expected to be
    #     0<=x<K, and are expected to have nothing after the decimal point (i.e.
    #     to be floats representing integers).
    #     <target> is an M by N matrix that will be filled with the result.
    #     After the operation, for all i,j, target[i, j] = self[i, int(indices[j])]
    #     This returns <target>.
    #     ? idea: No bounds checking is done.
    #     """
    #     M, K = self.shape

    #     one, N = indices.shape
    #     assert one == 1
    #     M_, N_ = target.shape
    #     assert M_ == M and N == N_

    #     np_ints = indices.numpy_array.astype(int)

    #     if not (np_ints.max() < K and np_ints.min() >= 0):
    #         raise ValueError("Index out of bounds.")


    #     target.numpy_array[:] = self.numpy_array[:, np_ints.flatten()]



    #     return target




    def transpose(self, target = None):

        if target is None:
            return CUDAMatrix(self.numpy_array.T.copy())
        else:
            target.numpy_array.resize((self.shape[1], self.shape[0]))
            target.numpy_array[:] = self.numpy_array.T

        return target


    def assign_transpose(self, t):
        return t.transpose(target = self)



    def fill_with_rand(self):
        """
        Fill matrix on the GPU with random numbers drawn from the uniform
        distribution over the (0,1) interval.
        """
        self.numpy_array[:] = np.random.rand(*self.shape)

        return self





    def fill_with_randn(self):
        """
        Fill matrix on the GPU with random numbers drawn from the standard normal
        distribution.
        """

        self.numpy_array[:] = np.random.randn(*self.shape)

        return self



    def add_col_vec(self, vec, target = None):
        """
        Add vector vec to every column of the matrix. If a target is provided,
        it is used to store the result instead of self.
        """

        a, b = self.shape
        a_, b_ = vec.shape

        if not (b_ == 1 and a_ == a):
            raise IncompatibleDimensionsException


        if target is None:
            target = self

        target.resize(self.shape)

        target.numpy_array[:] = self.numpy_array + vec.numpy_array

        return target

    def assign_add_col_vec(self, a, b):
        return a.add_col_vec(b, target = self)



    def add_col_mult(self, vec, mult, target = None):
        """
        Add a multiple of vector vec to every column of the matrix. If a target
        is provided, it is used to store the result instead of self.
        """

        a, b = self.shape
        a_, b_ = vec.shape

        if not (b_ == 1 and a_ == a):
            raise IncompatibleDimensionsException


        if target is None:
            target = self

        target.resize(self.shape)

        target.numpy_array[:] = self.numpy_array + vec.numpy_array * mult

        return target





    def assign_add_col_mult(self, a, m, b):
        return a.add_col_vec(b, m, target = self)



    def add_row_vec(self, vec, target = None):
        """
        Add vector vec to every row of the matrix. If a target is provided,
        it is used to store the result instead of self.
        """

        a, b = self.shape
        a_, b_ = vec.shape

        if not (a_ == 1 and b_ == b):
            raise IncompatibleDimensionsException


        if target is None:
            target = self

        target.resize(self.shape)

        target.numpy_array[:] = vec.numpy_array + self.numpy_array

        return target



    def assign_add_row_vec(self, a, b):
        return a.add_row_vec(b, target = self)



    def mult_by_col(self, vec, target = None):
        """
        Multiply vector vec into every column of the matrix. If a target is
        provided, it is used to store the result instead of self.
        """


        a, b = self.shape
        a_, b_ = vec.shape

        if not (b_ == 1 and a_ == a):
            raise IncompatibleDimensionsException

        if target is None:
            target = self

        target.resize(self.shape)


        target.numpy_array[:] = vec.numpy_array * self.numpy_array


        return target



    def mult_by_row(self, vec, target = None):
        """
        Multiply vector vec into every row of the matrix. If a target is
        provided, it is used to store the result instead of self.
        """

        a, b = self.shape
        a_, b_ = vec.shape

        if not (b_ == b and a_ == 1):
            raise IncompatibleDimensionsException

        if target is None:
            target = self

        target.resize(self.shape)


        target.numpy_array[:] = vec.numpy_array * self.numpy_array

        return target





    def sum(self, axis, target = None):
        """
        Sum the matrix along the given dimension, where 0 represents the leading
        dimension and 1 represents the non-leading dimension. If a target is
        not prvided, a new vector is created for storing the result.
        """



        if axis == 0:
            ans = self.numpy_array.sum(0)[np.newaxis, :]
        elif axis == 1:
            ans = self.numpy_array.sum(1)[:, np.newaxis]
        else:
            raise ValueError("axis must be only 0 or 1; instead, got %s\n", axis)

        ans = CUDAMatrix(ans)

        if target is not None:
            target.assign(ans)
        else:
            target = ans
        return target


    def mean(self, axis, target = None):




        if axis == 0:
            ans = self.numpy_array.mean(0)[np.newaxis, :]
        elif axis == 1:
            ans = self.numpy_array.mean(1)[:, np.newaxis]
        else:
            raise ValueError("axis must be only 0 or 1; instead, got %s\n", axis)

        ans = CUDAMatrix(ans)

        if target is not None:
            target.assign(ans)
        else:
            target = ans
        return target





    def assign_sum(self, mat, axis):
        return mat.sum(axis, target = self)

    def assign_mean(self, mat, axis):
        return mat.mean(axis, target = self)



    def add_sums(self, mat, axis, mult = 1.):
        """
        Add a multiple of the sums of the matrix mat along the given dimension
        to self.
        """



        if self.numpy_array.shape != self.mat.shape:
            raise IncompatibleDimensionsException

        sum = mat.sum(axis)

        sum.numpy_array *= mult

        if axis == 0:
            self.add_row_vec(sum)
        elif axis == 1:
            self.add_col_vec(sum)

        return self


    def less_than(self, val, target = None):
        """
        Perform the operation target = 1. * (self < val), where val can be a matrix or a scalar.
        """


        if target is None:
            target = self

        target.resize(self.shape)

        if isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array < val

        else:
            if val.shape != self.shape:
                raise IncompatibleDimensionsException


            target.numpy_array[:] = (self.numpy_array < val.numpy_array).astype(__DTYPE__)

        return target

    def assign_less_than(self, mat, val):
        return mat.less_than(val, self)




    def greater_than(self, val, target = None):
        """
        Perform the operation target = 1. * (self > val), where val can be a matrix or a scalar.
        """


        if target is None:
            target = self

        target.resize(self.shape)

        if isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = (self.numpy_array > val).astype(__DTYPE__)
        else:
            if val.shape != self.shape:
                raise IncompatibleDimensionsException


            target.numpy_array[:] = (self.numpy_array > val.numpy_array).astype(__DTYPE__)

        return target


    def assign_greater_than(self, mat, val):
        return mat.greater_than(val, self)




    def max(self, axis, target = None, transpose_aux=None):
        """
        Find the maximum value along the given dimension, where 0 represents the
        leading dimension and 1 represents the non-leading dimension. If a target
        is not prvided, a new vector is created for storing the result.
        """



        m, n = self.shape

        if axis == 0:
            if target is None:
                target = empty((1, n))

            target.resize((1, n))


            target.numpy_array[:] = self.numpy_array.max(0)



        elif axis == 1:
            # IN theory: we are supposed to do this:

#             if not target:
#                 #target = CUDAMatrix(np.empty((m, 1), dtype=np.float32, order = 'F'))
#                 target = empty((m, 1))
#             else:
#                 target.resize((m, 1))



#             err_code =  _cudamat.max_by_axis(self.p_mat, target.p_mat, ct.c_int(axis))
#             if err_code:
#                 raise generate_exception(err_code)

            assert transpose_aux != None

            self.transpose(target = transpose_aux)

            target.reshape(target.shape[::-1])

            transpose_aux.max(axis = 0, target = target)

            target.reshape(target.shape[::-1])




        return target

    def assign_max(self, mat, axis, transpose_aux=None):
        return mat.max(axis, target = self, transpose_aux = transpose_aux)

    def total_max(self):
        row_maxes = empty((1, 1)).assign_max(self, axis = 0)
        return row_maxes.reshape((row_maxes.shape[1], row_maxes.shape[0])).max(axis = 0).asarray()[0,0]

    def total_sum(self):
        return self.numpy_array.sum()


    def sign(self, target = None):

        if target is None:
            target = empty(self.shape)

        target.resize(self.shape)

        target.numpy_array[:] = np.sign(self.numpy_array)

        return target


    def assign_sign(self, a):
        return a.sign(target = self)


    def apply_sigmoid(self, target = None):
        """
        Apply the logistic sigmoid to each element of the matrix.
        """

        return sigmoid(self, target)

    def sigmoid(self, target = None):
        """
        Apply the logistic sigmoid to each element of the matrix.
        """

        return sigmoid(self, target)


    def assign_sigmoid(self, t):
        return sigmoid(t, self)


    def log(self, target = None):
        return log(self, target)

    def assign_log(self, t):
        return log(t, self)

    def exp(self, target = None):
        return exp(self, target)

    def assign_exp(self, t):
        return exp(t, self)

    def pow(self, p, target = None):
        return pow(self, p, target)

    def assign_pow(self, mat, p):
        return pow(mat, p, self)


    def sqrt(self, target = None):
        return sqrt(self, target)


    def assign_sqrt(self, mat):
        return sqrt(mat, self)


    def reciprocal(self, target = None):
        """
        Find the reciprocal of each element of the matrix.
        """

        if not target:
            target = self

        target.resize(self.shape)


        target.numpy_array[:] = 1./self.numpy_array[:]

        return target

    def assign_reciprocal(self, mat):
        return mat.reciprocal(target = self)



    def dot(self, mat2, target = None):
        """
        Multiply the matrix by mat2 from the right.
        """

        return dot(self, mat2, target)


    def assign_dot(self, m1, m2):
        m1.dot(m2, target = self)
        return self


    def add_dot(self, m1, m2):
        """
        Add the dot product of m1 and m2 to the matrix.
        """


        m3 = dot(m1, m2)

        if m3.shape != self.shape:
            raise IncompatibleDimensionsException

        self.numpy_array += m3.numpy_array


        return self

    def subtract_dot(self, m1, m2):
        """
        Subtract the dot product of m1 and m2 from the matrix.
        """



        m3 = dot(m1, m2)

        if m3.shape != self.shape:
            raise IncompatibleDimensionsException

        self.numpy_array -= m3.numpy_array


        return self


    def add_mult(self, mat2, alpha = 1.):
        """
        Add multiple of mat2 to the matrix.
        """

        if mat2.shape != self.shape:
            raise IncompatibleDimensionsException

        self.numpy_array += mat2.numpy_array * alpha

        return self

    def assign_mult(self, mat2, alpha):
        self.resize(mat2.shape)
        self.assign(0)
        self.add_mult(mat2, alpha)
        return self


    def subtract_mult(self, mat2, alpha = 1.):
        """
        Subtract a multiple of mat2 from the matrix.
        """

        if mat2.shape != self.shape:
            raise IncompatibleDimensionsException

        self.numpy_array -= mat2.numpy_array * alpha

        return self


    def add(self, val, target = None):
        """Add val to self, where val can be a scalar or a CUDAMatrix with the
        same dimensions as self. """

        if not target:
            target = self

        target.resize(self.shape)




        if isinstance(val, CUDAMatrix):
            if target.shape != val.shape:
                raise IncompatibleDimensionsException
            target.numpy_array[:] = self.numpy_array + val.numpy_array

        elif isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array + val
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."



        return target

    def assign_add(self, a, b):
        a.add(b, target = self)
        return self



    def subtract(self, val, target = None):
        """Subtract val from self, where val can be a scalar or a CUDAMatrix with
        the same dimensions as self. """

        if not target:
            target = self

        target.resize(self.shape)



        if isinstance(val, CUDAMatrix):
            if target.shape != val.shape:
                raise IncompatibleDimensionsException
            target.numpy_array[:] = self.numpy_array - val.numpy_array

        elif isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array - val
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."



        return target



    def assign_subtract(self, a, b):
        a.subtract(b, target = self)
        return self




    def divide(self, val, target = None):
        """Divide self by val, where val can be a scalar or a CUDAMatrix with the
        same dimensions as self. """

        if not target:
            target = self

        target.resize(self.shape)


        if isinstance(val, CUDAMatrix):
            if target.shape != val.shape:
                raise IncompatibleDimensionsException
            target.numpy_array[:] = self.numpy_array / val.numpy_array

        elif isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array / val
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."



        return target



    def assign_divide(self, a, b):
        a.divide(b, target = self)
        return self



    def mult(self, val, target = None):
        """Multiply self by val, where val can be a scalar or a CUDAMatrix with
        the same dimensions as self. """

        if not target:
            target = self

        target.resize(self.shape)


        if isinstance(val, CUDAMatrix):
            if target.shape != val.shape:
                raise IncompatibleDimensionsException
            target.numpy_array[:] = self.numpy_array * val.numpy_array

        elif isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array * val
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."



        return target





    def assign_mult(self, a, b):
        a.mult(b, target = self)
        return self




    @deprecated
    def assign_scalar(self, alpha):
        """
        Assign scalar alpha to every element of the matrix.
        """
        self.assign(alpha)
        return self

    @deprecated
    def mult_by_scalar(self, alpha, target = None):
        """
        Multiply the matrix by a scalar.
        """
        return self.mult(alpha, target)




    @deprecated
    def div_by_scalar(self, alpha, target = None):
        """
        Divide the matrix by a scalar.
        """

        return self.divide(alpha, target)



    @deprecated
    def add_scalar(self, alpha, target = None):
        """
        Increment the matrix by a scalar.
        """
        return self.add(alpha, target)


    def euclid_norm(self):
        return np.sqrt((self.numpy_array**2).sum())


def empty(shape=None):
    """
    Creates and returns a new CUDAMatrix with the given shape.
    """

    if shape is None:
        shape = (1, 1)

    return CUDAMatrix(np.empty(shape))


def zeros(shape):
    return empty(shape).assign(0)

def randn(a, b):
    ans = empty((a, b)).fill_with_randn()
    return ans



def sum(mat, axis, target = None):
    """
    Sum the matrix along the given dimension, where 0 represents the leading
    dimension and 1 represents the non-leading dimension. If a target is
    not prvided, a new vector is created for storing the result.
    """
    return mat.sum(axis, target)


def dot(m1, m2, target = None):
    """
    Find the dot product between m1 and m2.
    """

    m = m1.shape[0]
    n = m2.shape[1]

    target_shape = (m, n)
    if not target:
        target = empty(target_shape)

    target.resize(target_shape)

    try:
        target.numpy_array[:] = np.dot(m1.numpy_array, m2.numpy_array)
    except ValueError:
        raise IncompatibleDimensionsException

    return target

def vdot(m1, m2):
    assert m1.shape == m2.shape
    return (m1.asarray() * m2.asarray()).sum()



def sigmoid(mat, target = None):
    """
    Apply the logistic sigmoid to each element of the matrix mat.
    """


    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = 1. / (1 + np.exp(-mat.numpy_array))

    return target


def tanh(mat, target = None):
    """
    Apply the logistic sigmoid to each element of the matrix mat.
    """


    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = np.tanh(mat.numpy_array)

    return target


def gammaln(mat, target = None):



    if not target:
        target = mat

    target.resize(mat.shape)

    import scipy.special
    target.numpy_array[:] = scipy.special.gammaln(mat.numpy_array)

    return target





def abs(mat, target = None):
    """
    Apply the logistic sigmoid to each element of the matrix mat.
    """


    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = abs(mat.numpy_array)

    return target




def log_1_plus_exp(mat, target = None):
   """
   Apply log(1+exp(x)) to each element of the matrix mat.
   """
   if not target:
       target = mat
   mask = mat.numpy_array > 0
   target.numpy_array[mask] = mat.numpy_array[mask] + np.log(1+np.exp(-mat.numpy_array[mask]))
   mask = np.logical_not(mask)
   target.numpy_array[mask] = np.log(1+np.exp(mat.numpy_array[mask]))
   return target
log_1_sum_exp = log_1_plus_exp

def log(mat, target = None):
    """
    Find the natural logarithm of each element of the matrix mat.
    """

    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = np.log(mat.numpy_array)

    return target

def exp(mat, target = None):
    """
    Apply the exponential function to each element of the matrix mat.
    """

    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = np.exp(mat.numpy_array)

    return target


    if not target:
        target = mat

    target.resize(mat.shape)

    return target


def sqrt(mat, target = None):
    """
    Compute the square root of each element of the matrix mat.
    """

    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = np.sqrt(mat.numpy_array)

    return target


    if not target:
        target = mat

    target.resize(mat.shape)

    return target

def pow(mat, p, target = None):
    """
    Compute the 'p'th power of each element of the matrix mat.
    """

    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = mat.numpy_array[:] ** p

    return target

def cuda_sync_threads():
    pass

def reformat(array):
    """
    Returns array as a float32 array in FORTRAN order.
    """
    return np.array(array, dtype=__DTYPE__, order='F')


def cuda_set_some_device():
    return 0

def cuda_set_device(dev_id):
    """
    Selects the CUDA device with the given ID.
    """


    return 0

def cuda_get_free_device():
    """
    Returns the ID of the first free CUDA device.
    """
    return 0



def cublas_init():
    """
    Initialize Cublas.
    """

    return 0

def cublas_shutdown():
    """
    Shut down Cublas.
    """
    return 0


# The following functions are for implementing things like coarse filters and
# models with replicated local filters. At the moment they are quite slow.

def sum_superpixels(source, target, w, temp = None):
    raise NotImplemented()



def kronecker(mat1, mat2, target = None):
    raise NotIMplemented



def flat_to_tiled(source, target, stride):
    raise NotImplemented()

def tiled_to_flat(source, target, stride, temp = None):
    raise NotImplemented()

def flat_to_tiled3(source, target, stride):
    raise NotImplemented()






def get_item_from_each_row(source, target, inds, num_rows, num_cols):
    if source.numpy_array.shape == (num_cols, num_rows):
        src = source.numpy_array.T
    else:
        src = source.numpy_array.reshape(num_rows, num_cols)
    ix = inds.numpy_array.reshape(num_rows).astype(int)
    t = target.numpy_array.reshape(num_rows)

    for i in range(num_rows):
        t[i] = src[i,ix[i]]
    return target


def set_item_to_each_row(source, target, inds, num_rows, num_cols):
    if source.numpy_array.shape == (num_cols, num_rows):
        src = source.numpy_array.T
    else:
        src = source.numpy_array.reshape(num_rows, num_cols)

    ix = inds.numpy_array.reshape(num_rows).astype(int)
    t = target.numpy_array.reshape(num_rows)

    for i in range(num_rows):
        src[i,ix[i]] = t[i]
    return source
















def abs(X, aux):
    return aux.assign_mult(X, X).sqrt()

def total_sum(X):
    return X.total_sum()


def mean(mat, axis, target = None):

    target = sum(mat, axis, target)



    target.mult_by_scalar(1. / mat.shape[axis])

    return target


def total_mean(mat):
    s = total_sum(mat)
    return s / mat.num_elems








def cumsum(mat, target):

    target.resize(mat.shape)

    target.numpy_array[:] = mat.numpy_array.cumsum(1)

    return target




# def multi_transpose(IN, OUT, w, h, batch_size):
#     """
#     the order of w, h seems wrong, but it is consistent with the one on cudamat.py
#     """
#     assert IN.shape == (w*h, batch_size)
#     assert OUT.shape == (w*h, batch_size)


#     from pylab import amap, transpose
#     OUT.numpy_array[:] = amap(transpose,IN.numpy_array.reshape(h, w, batch_size).transpose([2,0,1])).transpose([1,2,0]).reshape(w*h, batch_size)


def multi_transpose(IN, OUT, w, h, batch_size):
    i = IN.numpy_array
    o = OUT.numpy_array

#     o = o.reshape(batch_size, w, h)
#     o[:] = i.reshape(batch_size, h, w).transpose([0,2,1])
#     OUT.numpy_array[:] = o.reshape(*OUT.numpy_array.shape)

    o = o.ravel()
    o[:] = i.reshape(h, w, batch_size).transpose([1,0,2]).ravel()
    OUT.numpy_array[:] = o.reshape(*OUT.numpy_array.shape)


    return OUT

def ind_incr(target, inds, axis):


    assert target.shape[1] == inds.shape[0] * inds.shape[1]
    assert inds.shape[1] == 1 or inds.shape[0] == 1

    if axis == 1:
        try:
            for i in inds:
                target.numpy_array[:, i] += 1
        except IndexError:
            raise IncompatibleDimensionsException


        return target

    elif axis == 0:

        try:
            for i in inds:
                target.numpy_array[i, :] += 1
        except IndexError:
            raise IncompatibleDimensionsException


        return target


    else:
        raise Exception ("bad axis.")




## The code below has been lifted from cudamat. It needs to work with numpy.


MAX_ELEMS = 2 ** 16 - 10
class softmax:
    def __init__(self, axis):
        self.axis = axis

        self.transpose_aux = empty()
        self.neg_max = empty()
        self.mat = empty()
        self.exp = empty()
        self.Z = empty()
        self.probs = empty()


        self.transpose_aux_small = empty()
        self.neg_max_small = empty()
        self.mat_small = empty()
        self.exp_small = empty()
        self.Z_small = empty()
        self.probs_small = empty()



    def __call__(self, mat, target):


        if mat.shape != target.shape:
            target.resize(mat.shape)

        if self.axis == 1:
            return self.__call_helper_small__(mat, target)




        pos = 0
        step = MAX_ELEMS

        ## width is how many elems we have to work with.
        width = mat.shape[1 - self.axis]

        while pos < width:
            next = min(width, pos + step)

            step_size = next - pos

            if step_size == step:
                self.__call_helper__(mat.slice(pos, next),
                                     target.slice(pos, next))
            else:
                self.__call_helper_small__(mat.slice(pos, next),
                                           target.slice(pos, next))

            pos += step_size

        return target



    def __call_helper__(self, mat, target):






        self.neg_max.\
            assign_max(mat,
                       axis = self.axis,
                       transpose_aux = self.transpose_aux).\
            mult(-1)

        if self.axis == 0:
            self.mat.assign_add_row_vec(mat, self.neg_max)
        else:
            self.mat.assign_add_col_vec(mat, self.neg_max)

        self.exp.assign_exp(self.mat)

        self.Z.assign_sum(self.exp, self.axis).reciprocal()

        self.probs.assign(self.exp)
        if self.axis == 0:
            self.probs.mult_by_row(self.Z)
        else:
            self.probs.mult_by_col(self.Z)

        target.assign(self.probs)




    def __call_helper_small__(self, mat, target):

        self.neg_max_small.\
            assign_max(mat,
                       axis = self.axis,
                       transpose_aux = self.transpose_aux_small).\
            mult(-1)

        if self.axis == 0:
            self.mat_small.assign_add_row_vec(mat, self.neg_max_small)
        else:
            self.mat_small.assign_add_col_vec(mat, self.neg_max_small)

        self.exp_small.assign_exp(self.mat_small)

        self.Z_small.assign_sum(self.exp_small, self.axis).reciprocal()



        self.probs_small.assign(self.exp_small)
        if self.axis == 0:
            self.probs_small.mult_by_row(self.Z_small)
        else:
            self.probs_small.mult_by_col(self.Z_small)





        target.assign(self.probs_small)









    def log_Zs(self, mat, target):

        self.neg_max.\
            assign_max(mat,
                       axis = self.axis,
                       transpose_aux = self.transpose_aux).\
            mult(-1)

        if self.axis == 0:
            self.mat.assign_add_row_vec(mat, self.neg_max)
        else:
            self.mat.assign_add_col_vec(mat, self.neg_max)

        ## the exps without the max
        self.exp.assign_exp(self.mat)

        ## take the sums of the exps, take the log, and add subtruct the maxes.
        target.assign_sum(self.exp, self.axis).log().add(self.neg_max.mult(-1))

        return target








class sample_multinomial:
    def __init__(self, probs, axis):
        raise NotImplementedError("use robust_multinomial instead.")

        self.axis = axis
        self.cumsums = empty()
        self.cumsums_t = empty()
        self.probs_t = empty()



        self.cumsums_small = empty()
        self.cumsums_t_small = empty()
        self.probs_t_small = empty()





        self.set_probs(probs)


        self.samples = empty()
        self.samples_small = empty()


        if axis == 0:

            width = probs.shape[1]
            std_width = min(width, MAX_ELEMS)



            self.rand_vals = empty((1, std_width))
            self.ones      = empty((probs.shape[0], 1)).assign(1.)



            small_width = max(0, width % MAX_ELEMS)



            self.rand_vals_small = empty((1, small_width))
            self.ones_small      = empty((probs.shape[1], 1)).assign(1.)



        elif axis == 1:


            width = probs.shape[0]
            std_width = min(width, MAX_ELEMS)



            self.rand_vals = empty((std_width, 1))
            self.ones      = empty((1, probs.shape[1])).assign(1.)



            small_width = max(0, width % MAX_ELEMS)


            self.rand_vals_small = empty((small_width, 1))
            self.ones_small      = empty((1, probs.shape[1])).assign(1.)







        self.rand_mat = empty()
        self.threshs = empty()


        self.rand_mat_small = empty()
        self.threshs_small = empty()




    def set_probs(self, probs):
        if self.axis == 1:
            cumsum(probs, self.cumsums)

        else:
            probs.transpose(target = self.probs_t)
            cumsum(self.probs_t, self.cumsums_t)
            self.cumsums_t.transpose(target = self.cumsums)









    def multi_sample(self, target, k):
        target.resize(self.cumsums.shape)


        for i in range(k):

            self.rand_vals.fill_with_rand()

            if self.axis == 1:
                self.rand_mat.assign_dot(self.rand_vals, self.ones)
            else:
                self.rand_mat.assign_dot(self.ones, self.rand_vals)


            self.threshs.\
                assign_less_than(self.cumsums, self.rand_mat).\
                sum(self.axis, target = self.samples)




            ind_incr(target, self.samples, self.axis)

        return target









    def set_probs_helper_small(self, probs):
        self.probs = probs
        if self.axis == 1:
            cumsum(probs, self.cumsums_small)

        else:
            probs.transpose(target = self.probs_t_small)
            cumsum(self.probs_t_small, self.cumsums_t_small)
            self.cumsums_t_small.transpose(target = self.cumsums_small)



    def multi_sample_helper_small(self, target, k):
        target.resize(self.cumsums_small.shape)


        for i in range(k):

            self.rand_vals_small.fill_with_rand()

            if self.axis == 1:
                self.rand_mat_small.assign_dot(self.rand_vals_small, self.ones_small)
            else:
                self.rand_mat_small.assign_dot(self.ones_small, self.rand_vals_small)


            self.threshs_small.\
                assign_less_than(self.cumsums_small, self.rand_mat_small).\
                sum(self.axis, target = self.samples_small)




            ind_incr(target, self.samples_small, self.axis)

        return target






    def sample_from_probs(self, probs, target):

        if probs.shape != target.shape:
            target.resize(probs.shape)


        ## yes: we make a loop.

        pos = 0
        step = MAX_ELEMS
        width = probs.shape[1]
        while pos < width:
            next = min(width, pos + step)

            step_size = next - pos

            if step_size == step:
                p = probs.slice(pos, next)
                t = target.slice(pos, next)

                self.set_probs(p)
                self.multi_sample(t, 1)

            else:
                p = probs.slice(pos, next)
                t = target.slice(pos, next)


                self.set_probs_helper_small(probs)
                self.multi_sample_helper_small(t, 1)

            pos += step_size



        return target






class robust_multinomial:
    def __init__(self, shape, axis):
        self.axis = axis
        self.cumsums = empty()
        self.cumsums_t = empty()
        self.probs_t = empty()



        self.cumsums_small = empty()
        self.cumsums_t_small = empty()
        self.probs_t_small = empty()






        self.samples = empty()
        self.samples_small = empty()


        if axis == 0:

            width = shape[1]
            std_width = min(width, MAX_ELEMS)



            self.rand_vals = empty((1, std_width))
            self.ones      = empty((shape[0], 1)).assign(1.)



            small_width = max(0, width % MAX_ELEMS)



            self.rand_vals_small = empty((1, small_width))
            self.ones_small      = empty((shape[0], 1)).assign(1.)



        elif axis == 1:


            width = shape[0]
            std_width = min(width, MAX_ELEMS)



            self.rand_vals = empty((std_width, 1))
            self.ones      = empty((1, shape[1])).assign(1.)



            small_width = max(0, width % MAX_ELEMS)


            self.rand_vals_small = empty((small_width, 1))
            self.ones_small      = empty((1, shape[1])).assign(1.)







        self.rand_mat = empty()
        self.threshs = empty()


        self.rand_mat_small = empty()
        self.threshs_small = empty()




    def set_probs(self, probs):
        self.probs = probs
        if self.axis == 1:
            cumsum(probs, self.cumsums)

        else:
            probs.transpose(target = self.probs_t)
            cumsum(self.probs_t, self.cumsums_t)
            self.cumsums_t.transpose(target = self.cumsums)









    def multi_sample(self, target, k):
        target.resize(self.cumsums.shape)


        for i in range(k):

            self.rand_vals.fill_with_rand()

            if self.axis == 1:
                self.rand_mat.assign_dot(self.rand_vals, self.ones)
            else:
                self.rand_mat.assign_dot(self.ones, self.rand_vals)


            self.threshs.\
                assign_less_than(self.cumsums, self.rand_mat).\
                sum(self.axis, target = self.samples)




            ind_incr(target, self.samples, self.axis)

        return target









    def set_probs_helper_small(self, probs):
        if self.axis == 1:
            cumsum(probs, self.cumsums_small)

        else:
            probs.transpose(target = self.probs_t_small)
            cumsum(self.probs_t_small, self.cumsums_t_small)
            self.cumsums_t_small.transpose(target = self.cumsums_small)




    def multi_sample_helper_small(self, target, k):
        target.resize(self.cumsums_small.shape)

        for i in range(k):

            self.rand_vals_small.fill_with_rand()

            if self.axis == 1:
                self.rand_mat_small.assign_dot(self.rand_vals_small, self.ones_small)
            else:
                self.rand_mat_small.assign_dot(self.ones_small, self.rand_vals_small)


            self.threshs_small.\
                assign_less_than(self.cumsums_small, self.rand_mat_small).\
                sum(self.axis, target = self.samples_small)




            ind_incr(target, self.samples_small, self.axis)

        return target






    def sample_from_probs(self, probs, target):

        if probs.shape != target.shape:
            target.resize(probs.shape)


        ## yes: we make a loop.

        pos = 0
        step = MAX_ELEMS

        width = probs.shape[1 - self.axis]

        while pos < width:
            next = min(width, pos + step)

            step_size = next - pos

            p = probs.slice(pos, next)
            t = target.slice(pos, next)


            if step_size == step:

                self.set_probs(p)
                self.multi_sample(t, 1)

            else:

                self.set_probs_helper_small(p)
                self.multi_sample_helper_small(t, 1)

            pos += step



        return target

########NEW FILE########
__FILENAME__ = pretrain
"""
 Copyright (c) 2011,2012 George Dahl

 Permission is hereby granted, free of charge, to any person  obtaining
 a copy of this software and associated documentation  files (the
 "Software"), to deal in the Software without  restriction, including
 without limitation the rights to use,  copy, modify, merge, publish,
 distribute, sublicense, and/or sell  copies of the Software, and to
 permit persons to whom the  Software is furnished to do so, subject
 to the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.  THE
 SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT  HOLDERS
 BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,  WHETHER IN AN
 ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING  FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR  OTHER DEALINGS IN THE
 SOFTWARE.
"""

import numpy as num
import gnumpy as gnp

class Binary(object):
    def activate(self, netInput):
        return netInput.sigmoid()
    def sampleStates(self, acts):
        return gnp.rand(*acts.shape) <= acts

class Gaussian(object):
    def activate(self, netInput):
        return netInput
    def sampleStates(self, acts): #probably shouldn't use this
        return acts + gnp.randn(*acts.shape)

class ReLU(object):
    def __init__(self, krizNoise = False):
        self.krizNoise = krizNoise
    def activate(self, netInput):
        return netInput*(netInput > 0)
    def sampleStates(self, acts):
        if self.krizNoise:
            return self.activate(acts + gnp.randn(*acts.shape))
        tiny = 1e-30
        stddev = gnp.sqrt(acts.sigmoid() + tiny)
        return self.activate( acts + stddev*gnp.randn(*acts.shape) )


def CD1(vis, visToHid, visBias, hidBias, visUnit = Binary(), hidUnit = Binary()):
    """
    Using Gaussian hidden units hasn't been tested. By assuming the
    visible units are Binary, ReLU, or Gaussian and the hidden units
    are Binary or ReLU this function becomes quite simple.
    """
    posHid = hidUnit.activate(gnp.dot(vis, visToHid) + hidBias)
    posHidStates = hidUnit.sampleStates(posHid)

    negVis = visUnit.activate(gnp.dot(posHidStates, visToHid.T) + visBias)
    negHid = hidUnit.activate(gnp.dot(negVis, visToHid) + hidBias)

    visHidStats = gnp.dot(vis.T, posHid) - gnp.dot(negVis.T, negHid)
    visBiasStats = vis.sum(axis=0).reshape(*visBias.shape) - negVis.sum(axis=0).reshape(*visBias.shape)
    hidBiasStats = posHid.sum(axis=0).reshape(*hidBias.shape) - negHid.sum(axis=0).reshape(*hidBias.shape)

    return visHidStats, hidBiasStats, visBiasStats, negVis

########NEW FILE########
__FILENAME__ = metrics
import numpy as np


def rmsle(y_test, y_pred):
    ans = np.log1p(y_pred) - np.log1p(y_test)
    ans = np.power(ans, 2)
    return np.sqrt(ans.mean())

########NEW FILE########
__FILENAME__ = wrappers
# encoding: utf-8
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.preprocessing import OneHotEncoder

class FeatureMixer(BaseEstimator):

    def __init__(self, clfs, ignorefit=False):
        self.clfs = clfs
        self.ignorefit = ignorefit

    def fit_transform(self, X, y=None):
        if not self.ignorefit:
            self.fit(X, y)
        return self.transform(X)

    def fit(self, X, y=None):
        if not self.ignorefit:
            for clf in self.clfs:
                new = clf.fit_transform(X, y)

    def transform(self, X):
        ans = None
        for clf in self.clfs:
            new = clf.transform(X)
            if ans is None:
                ans = new
            else:
                ans = np.hstack((ans, new))
        return ans


class TransformWrapper(BaseEstimator):

    def __init__(self, clf, transformation, fit_transform=True):
        self.clf = clf
        self.fit_transform = fit_transform
        self.transformation = transformation

    def fit(self, X, y=None):
        if self.fit_transform:
            self.transformation.fit(X)
        _X = self._pretransform(X)
        if y is None:
            self.clf.fit(_X)
        else:
            self.clf.fit(_X, y)

    def predict(self, X):
        _X = self._pretransform(X)
        return self.clf.predict(_X)

    def predict_proba(self, X):
        _X = self._pretransform(X)
        return self.clf.predict_proba(_X)

    def transform(self, X):
        _X = self._pretransform(X)
        return self.clf.transform(_X)

    def _pretransform(self, X):
        return self.transformation.transform(X)


class GMMWrapper(TransformWrapper):

    def fit(self, X, y=None):
        if self.fit_transform:
            self.transformation.fit(X)
            t = self.transformation.predict(X)[np.newaxis].T
            self.enc = OneHotEncoder()
            self.enc.fit(t)
        _X = self._pretransform(X)
        if y is None:
            self.clf.fit(_X)
        else:
            self.clf.fit(_X, y)

    def _pretransform(self, X):
        t = self.transformation.predict(X)[np.newaxis].T
        return self.enc.transform(t).toarray()

########NEW FILE########
__FILENAME__ = test_compare
from __future__ import division
import math
import random
import copper
import numpy as np
import pandas as pd
from sklearn import cross_validation
from sklearn.linear_model import LogisticRegression

from nose.tools import raises, ok_
from copper.tests.utils import eq_


def get_iris():
    from sklearn import datasets
    iris = datasets.load_iris()

    X = iris.data
    Y = iris.target
    return X, Y


def get_iris_ds():
    X, Y = get_iris()
    df = pd.DataFrame(X)
    df['Target'] = pd.Series(Y, name='Target')

    ds = copper.Dataset(df)
    ds.role['Target'] = ds.TARGET
    return ds


# -----------------------------------------------------------------------------
#                           Train and test values

def test_get_set_train_test_directly():
    X, Y = get_iris()
    X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, Y, test_size=0.2)

    mc = copper.ModelComparison()
    mc.X_train = X_train
    mc.y_train = y_train
    mc.X_test = X_test
    mc.y_test = y_test

    eq_(mc.X_train.shape, (150 * 0.8, 4))
    eq_(mc.y_train.shape, (150 * 0.8, ))
    eq_(mc.X_test.shape, (150 * 0.2, 4))
    eq_(mc.y_test.shape, (150 * 0.2, ))
    eq_(mc.X_train, X_train)
    eq_(mc.y_train, y_train)
    eq_(mc.X_test, X_test)
    eq_(mc.y_test, y_test)


def test_get_set_train_test_dataset_property():
    X, Y = get_iris()
    X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, Y, test_size=0.6)

    train = np.hstack((X_train, y_train[np.newaxis].T))
    train = pd.DataFrame(train)
    train = copper.Dataset(train)
    train.role[4] = train.TARGET

    test = np.hstack((X_test, y_test[np.newaxis].T))
    test = pd.DataFrame(test)
    test = copper.Dataset(test)
    test.role[4] = test.TARGET
    # --
    mc = copper.ModelComparison()
    mc.train = train
    mc.test = test

    eq_(mc.X_train.shape, (150 * 0.4, 4))
    eq_(mc.y_train.shape, (150 * 0.4, ))
    eq_(mc.X_test.shape, (150 * 0.6, 4))
    eq_(mc.y_test.shape, (150 * 0.6, ))
    eq_(mc.X_train, X_train)
    eq_(mc.y_train, y_train)
    eq_(mc.X_test, X_test)
    eq_(mc.y_test, y_test)


def test_train_test_split():
    ds = get_iris_ds()
    mc = copper.ModelComparison()
    state = int(math.floor(random.random() * 1000))
    mc.train_test_split(ds, test_size=0.4, random_state=state)
    eq_(mc.X_train.shape, (150 * 0.6, 4))
    eq_(mc.y_train.shape, (150 * 0.6, ))
    eq_(mc.X_test.shape, (150 * 0.4, 4))
    eq_(mc.y_test.shape, (150 * 0.4, ))
    eq_((mc.X_train, mc.y_train), mc.train)
    eq_((mc.X_test, mc.y_test), mc.test)
    eq_(mc.le, None)
    # --
    X, Y = get_iris()
    X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, Y, test_size=0.4, random_state=state)
    eq_(mc.X_train, X_train)
    eq_(mc.y_train, y_train)
    eq_(mc.X_test, X_test)
    eq_(mc.y_test, y_test)


# -----------------------------------------------------------------------------
#                        Algorithms list/dictionary

def test_get_set_algorithms():
    mc = copper.ModelComparison()
    lr = LogisticRegression()
    mc['LR'] = lr
    eq_(mc['LR'], lr)

    lr2 = LogisticRegression(penalty='l1')
    mc['LR l1'] = lr2
    eq_(mc['LR l1'], lr2)
    eq_(len(mc), 2)


def test_del_algorithm_len():
    mc = copper.ModelComparison()
    lr = LogisticRegression()
    mc['LR'] = lr
    eq_(mc['LR'], lr)

    lr2 = LogisticRegression(penalty='l1')
    mc['LR l1'] = lr2
    eq_(mc['LR l1'], lr2)
    eq_(len(mc), 2)

    del mc['LR']
    eq_(mc['LR l1'], lr2)
    eq_(len(mc), 1)

    del mc['LR l1']
    eq_(len(mc), 0)


@raises(KeyError)
def test_deleted_algorithm():
    mc = copper.ModelComparison()
    lr = LogisticRegression()
    mc['LR'] = lr
    eq_(mc['LR'], lr)

    lr2 = LogisticRegression(penalty='l1')
    mc['LR l1'] = lr2
    eq_(mc['LR l1'], lr2)

    del mc['LR']
    eq_(mc['LR l1'], lr2)  # Not deleted
    mc['LR']  # deleted

# -----------------------------------------------------------------------------


@raises(AttributeError)
def test_no_auto_fit():
    mc = copper.ModelComparison()
    lr = LogisticRegression()
    mc['LR'] = lr

    mc['LR'].coef_  # Doesn't exist yet


def test_fit():
    ds = get_iris_ds()
    mc = copper.ModelComparison()
    mc.train_test_split(ds, test_size=0.4)


    lr = LogisticRegression()
    lr2 = LogisticRegression(penalty='l1')
    mc['LR'] = lr
    mc['LR l1'] = lr2

    mc.fit()
    ok_(mc['LR'].coef_ is not None)
    ok_(mc['LR l1'].coef_ is not None)
    ok_(mc['LR'] != mc['LR l1'])


# -----------------------------------------------------------------------------
#                        With target as string

def get_iris_ds_string():
    ds = get_iris_ds()
    ds.type['Target'] = ds.CATEGORY
    ds['Target'] = ds['Target'].apply(lambda x: str(x))
    ds['Target'][ds['Target'] == '0'] = 'Iris-A'
    ds['Target'][ds['Target'] == '1'] = 'Iris-B'
    ds['Target'][ds['Target'] == '2'] = 'Iris-C'
    eq_(ds.metadata['dtype']['Target'], object)
    return ds


def test_train_test_split_string():
    ds = get_iris_ds_string()
    mc = copper.ModelComparison()
    state = int(math.floor(random.random() * 1000))
    mc.train_test_split(ds, test_size=0.4, random_state=state)
    eq_(mc.X_train.shape, (150 * 0.6, 4))
    eq_(mc.y_train.shape, (150 * 0.6, ))
    eq_(mc.X_test.shape, (150 * 0.4, 4))
    eq_(mc.y_test.shape, (150 * 0.4, ))
    eq_((mc.X_train, mc.y_train), mc.train)
    eq_((mc.X_test, mc.y_test), mc.test)
    eq_(mc.le.classes_.tolist(), ['Iris-A', 'Iris-B', 'Iris-C'])
    # --
    X, Y = get_iris()
    X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, Y, test_size=0.4, random_state=state)
    eq_(mc.X_train, X_train)
    eq_(mc.y_train, y_train)
    eq_(mc.X_test, X_test)
    eq_(mc.y_test, y_test)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)

########NEW FILE########
__FILENAME__ = test_compare_metrics_iris
from __future__ import division
import copper
import pandas as pd

from nose.tools import raises
from copper.tests.utils import eq_


def get_iris():
    from sklearn import datasets
    iris = datasets.load_iris()

    X = iris.data
    Y = iris.target
    return X, Y


def get_iris_ds():
    X, Y = get_iris()
    df = pd.DataFrame(X)
    df['Target'] = pd.Series(Y, name='Target')

    ds = copper.Dataset(df)
    ds.role['Target'] = ds.TARGET
    return ds


def get_mc():
    ds = get_iris_ds()
    mc = copper.ModelComparison()
    mc.train_test_split(ds, random_state=0)
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    mc['LR'] = LogisticRegression()
    mc['SVM'] = SVC(probability=True)
    mc.fit()
    return mc

# -----------------------------------------------------------------------------


def test_accuracy_score(mc=None):
    mc = get_mc() if mc is None else mc
    # print mc.accuracy_score()
    score = mc.accuracy_score()
    eq_(score['SVM'], 0.973684, 6)
    eq_(score['LR'], 0.868421, 6)


@raises(ValueError)  # Not binary classification
def test_auc_score(mc=None):
    mc = get_mc() if mc is None else mc
    mc.auc_score()


@raises(ValueError)  # Not binary classification
def test_average_precision_score(mc=None):
    mc = get_mc() if mc is None else mc
    mc.average_precision_score()


def test_f1_score(mc=None):
    mc = get_mc() if mc is None else mc
    score = mc.f1_score()
    eq_(score['SVM'], 0.973952, 6)
    eq_(score['LR'], 0.870540, 6)


def test_fbeta_score(mc=None):
    mc = get_mc() if mc is None else mc
    score = mc.fbeta_score(beta=0.1)
    eq_(score['SVM'], 0.976249, 6)
    eq_(score['LR'], 0.914067, 6)
    score = mc.fbeta_score()
    eq_(score['SVM'], 0.973952, 6)
    eq_(score['LR'], 0.870540, 6)


def test_hinge_loss(mc=None):
    mc = get_mc() if mc is None else mc
    score = mc.hinge_loss()
    eq_(score['SVM'], 1.921052, 4)
    eq_(score['LR'], 2.026315, 4)


def test_matthews_corrcoef(mc=None):
    pass
    ''' Multiclass not supported for this metric
    mc = get_mc() if mc is None else mc
    score = mc.matthews_corrcoef()
    eq_(score['SVM'], 0.978391)
    eq_(score['LR'], 0.916242)
    '''


def test_precision_score(mc=None):
    mc = get_mc() if mc is None else mc
    score = mc.precision_score()
    eq_(score['SVM'], 0.976316, 6)
    eq_(score['LR'], 0.915414, 6)


def test_recall_score(mc=None):
    mc = get_mc() if mc is None else mc
    score = mc.recall_score()
    eq_(score['SVM'], 0.973684, 6)
    eq_(score['LR'], 0.868421, 6)


def test_recall_score_average_none(mc=None):
    mc = get_mc() if mc is None else mc
    score = mc.recall_score(average=None)
    eq_(score['LR (2)'], 1, 6)
    eq_(score['LR (0)'], 1, 6)
    eq_(score['SVM (2)'], 1, 6)
    eq_(score['SVM (0)'], 1, 6)
    eq_(score['SVM (1)'], 0.9375, 4)
    eq_(score['LR (1)'], 0.6875, 4)


def test_zero_one_loss(mc=None):
    mc = get_mc() if mc is None else mc
    score = mc.zero_one_loss()
    eq_(score['SVM'], 0.026316, 6)
    eq_(score['LR'], 0.131579, 6)



# -----------------------------------------------------------------------------
#                        With target as string

def get_mc_string():
    ds = get_iris_ds()
    ds.type['Target'] = ds.CATEGORY
    ds['Target'] = ds['Target'].apply(lambda x: str(x))
    ds['Target'][ds['Target'] == '0'] = 'Iris-setosa'
    ds['Target'][ds['Target'] == '1'] = 'Iris-versicolor'
    ds['Target'][ds['Target'] == '2'] = 'Iris-virginica'
    eq_(ds.metadata['dtype']['Target'], object)

    mc = copper.ModelComparison()
    mc.train_test_split(ds, random_state=0)

    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    mc['LR'] = LogisticRegression()
    mc['SVM'] = SVC(probability=True)
    mc.fit()
    return mc


def test_repeat_tests_with_target_string():
    mc = get_mc_string()
    test_accuracy_score(mc)
    test_f1_score(mc)
    test_fbeta_score(mc)
    test_hinge_loss(mc)
    test_matthews_corrcoef(mc)
    test_precision_score(mc)
    test_recall_score(mc)
    # test_recall_score_average_none(mc)
    test_zero_one_loss(mc)


def test_recall_score_average_none_string(mc=None):
    mc = get_mc_string() if mc is None else mc
    score = mc.recall_score(average=None)
    eq_(score['LR (Iris-virginica)'], 1, 6)
    eq_(score['LR (Iris-setosa)'], 1, 6)
    eq_(score['SVM (Iris-virginica)'], 1, 6)
    eq_(score['SVM (Iris-setosa)'], 1, 6)
    eq_(score['SVM (Iris-versicolor)'], 0.9375, 4)
    eq_(score['LR (Iris-versicolor)'], 0.6875, 4)

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)

########NEW FILE########
__FILENAME__ = test_compare_metrics_manual
from __future__ import division
import copper
import numpy as np
import pandas as pd

from copper.tests.utils import eq_


def get_train():
    X = np.ones((12, 3))
    y = ['b', 'z', 'b', 'g', 'g', 'z', 'b', 'z', 'g', 'b', 'g', 'z']
    #   [ 0,   2,   0,   1,   1,   2,   0,   2,   1,   0,   1,   0]
    df = pd.DataFrame(X)
    df['target'] = y
    ds = copper.Dataset(df)
    ds.role['target'] = ds.TARGET
    return ds


class BaseFake():

    def fit(self, X, t):
        pass

    def predict(self, X):
        return np.array(self.encode)


class FakePerfect(BaseFake):
    labels = ['b', 'z', 'b', 'g', 'g', 'z', 'b', 'z', 'g', 'b', 'g', 'z']
    encode = [0,   2,   0,   1,   1,   2,   0,   2,   1,   0,   1,   2]


class Fake1(BaseFake):
    labels = ['g', 'z', 'b', 'z', 'g', 'z', 'b', 'b', 'g', 'b', 'g', 'z']
    encode = [1,   2,   0,   2,   1,   2,   0,   0,   1,   0,   1,   2]


class Fake2(BaseFake):
    labels = ['g', 'g', 'g', 'g', 'g', 'g', 'g', 'g', 'b', 'g', 'g', 'g']
    encode = [1,   1,   1,   1,   1,   1,   1,   1,   0,   1,   1,   1]


def get_mc():
    mc = copper.ModelComparison()
    mc.train = get_train()
    mc.test = get_train()

    mc['perf'] = FakePerfect()
    mc['f1'] = Fake1()
    mc['f2'] = Fake2()
    mc.fit()
    return mc


# -----------------------------------------------------------------------------

def test_classes():
    mc = get_mc()
    eq_(mc.le.classes_, np.array(['b', 'g', 'z']))


def test_target_values():
    mc = get_mc()
    eq_(mc.y_train, np.array([0, 2, 0, 1, 1, 2, 0, 2, 1, 0, 1, 2]))


def test_accuracy():
    mc = get_mc()
    scores = mc.accuracy_score()
    eq_(scores['perf'], 1.0)
    eq_(scores['f1'], 0.75)
    eq_(scores['f2'], 0.25)


def test_f1_score_avg_none():
    mc = get_mc()
    scores = mc.f1_score(average=None)
    eq_(scores['perf (b)'], 1.0)
    eq_(scores['perf (g)'], 1.0)
    eq_(scores['perf (z)'], 1.0)
    eq_(scores['f1 (b)'], 0.75)
    eq_(scores['f1 (g)'], 0.75)
    eq_(scores['f1 (z)'], 0.75)
    eq_(scores['f2 (b)'], 0)
    eq_(scores['f2 (g)'], 0.4, 1)
    eq_(scores['f2 (z)'], 0)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)

########NEW FILE########
__FILENAME__ = test_dataset
from __future__ import division
import os
import math
import random
import tempfile
import copper
import numpy as np
import pandas as pd

from nose.tools import raises
from copper.tests.utils import eq_


# -----------------------------------------------------------------------------
#                               Properties

def test_create_empty():
    # Checks empty Dataframes
    ds = copper.Dataset()
    eq_(ds.role, pd.Series())
    eq_(ds.type, pd.Series())
    eq_(ds.frame.empty, True)
    eq_(ds.metadata.empty, True)


def test_create_noempty():
    df = pd.DataFrame(np.random.rand(10, 5))
    ds = copper.Dataset(df)
    eq_(ds.frame, df)
    eq_(len(ds), 10)
    eq_(len(ds), len(df))
    eq_(len(ds.role), 5)
    eq_(len(ds.type), 5)
    eq_(len(ds.metadata), 5)
    eq_(ds.metadata['Role'], ds.role)
    eq_(ds.metadata['Type'], ds.type)
    eq_(ds.index, df.index)
    eq_(ds.columns, df.columns)
    eq_(str(ds), str(ds.metadata))


def test_create_empty_and_set():
    df = pd.DataFrame(np.random.rand(10, 5))
    ds = copper.Dataset()
    eq_(ds.role, pd.Series())
    eq_(ds.type, pd.Series())
    eq_(ds.metadata.empty, True)
    eq_(ds.frame.empty, True)

    ds.frame = df.copy()
    eq_(ds.frame, df)
    eq_(len(ds), 10)
    eq_(len(ds), len(df))
    eq_(len(ds.role), 5)
    eq_(len(ds.type), 5)
    eq_(len(ds.metadata), 5)
    eq_(ds.metadata['Role'], ds.role)
    eq_(ds.metadata['Type'], ds.type)
    eq_(ds.index, df.index)
    eq_(ds.columns, df.columns)
    eq_(str(ds), str(ds.metadata))
    eq_(unicode(ds), unicode(ds.metadata))


def test_set_frame_different_length_same_cols():
    # Tests that the metadata is mantained if columns are the same
    df1 = pd.DataFrame(np.random.rand(5, 5))
    ds = copper.Dataset(df1.copy())
    ds.role[[2, 4]] = ds.TARGET
    ds.type[[1, 2]] = ds.CATEGORY
    meta_old = ds.metadata.copy()

    df2 = pd.DataFrame(np.random.rand(10, 5))
    ds.frame = df2
    eq_(ds.metadata, meta_old)


@raises(AssertionError)
def test_set_frame_different_length_same_cols_fail():
    # By failing is testing that the default metadata is not in place
    df1 = pd.DataFrame(np.random.rand(5, 5))
    ds = copper.Dataset(df1.copy())
    default_meta = ds.metadata.copy()
    ds.role[[2, 4]] = ds.TARGET
    ds.type[[1, 2]] = ds.CATEGORY

    df2 = pd.DataFrame(np.random.rand(10, 5))
    ds.frame = df2
    eq_(ds.metadata, default_meta)


def test_set_frame_different_cols():
    # Checks default metadata is placed
    df1 = pd.DataFrame(np.random.rand(5, 5))
    ds = copper.Dataset(df1)
    ds.role[[2, 4]] = ds.TARGET
    ds.type[[1, 2]] = ds.CATEGORY

    df2 = pd.DataFrame(np.random.rand(10, 10))
    ds.frame = df2
    eq_(ds.role[2], ds.INPUT)
    eq_(ds.role[4], ds.INPUT)
    eq_(ds.type[1], ds.NUMBER)
    eq_(ds.type[2], ds.NUMBER)


@raises(AssertionError)
def test_set_frame_different_cols_fail():
    # By failing it checks that the metadata is different == was recreated
    df1 = pd.DataFrame(np.random.rand(5, 5))
    ds = copper.Dataset(df1)
    meta_old = ds.metadata.copy()

    df2 = pd.DataFrame(np.random.rand(10, 10))
    ds.frame = df2
    eq_(ds.metadata, meta_old)


def test_default_type():
    df = pd.DataFrame(np.random.rand(5, 20))
    rand_col = math.floor(random.random() * 20)
    rand_col2 = math.floor(random.random() * 20)
    df[rand_col] = df[rand_col].apply(lambda x: str(x))
    df[rand_col2] = df[rand_col].apply(lambda x: str(x))
    ds = copper.Dataset(df)

    eq_(ds.type[rand_col], ds.CATEGORY)
    for col in ds.columns:
        if col not in (rand_col, rand_col2):
            eq_(ds.type[col], ds.NUMBER)


def test_set_metadata():
    df = pd.DataFrame(np.random.rand(5, 5))
    ds = copper.Dataset(df)

    rand_col = math.floor(random.random() * 5)
    meta = ds.metadata.copy()
    meta['Role'][rand_col] = ds.TARGET
    eq_(ds.role[rand_col], ds.INPUT)  # Not changes until reasigment
    ds.metadata = meta
    eq_(ds.role[rand_col], ds.TARGET)  # Change

    for i in range(5):
        rand_col = math.floor(random.random() * 5)
        meta = ds.metadata.copy()
        meta['Role'][rand_col] = ds.TARGET
        ds.metadata = meta
        eq_(ds.role[rand_col], ds.TARGET)

    rand_col = math.floor(random.random() * 5)
    meta = ds.metadata.copy()
    meta['Type'][rand_col] = ds.CATEGORY
    eq_(ds.type[rand_col], ds.NUMBER)  # Not changes until reasigment
    ds.metadata = meta
    eq_(ds.type[rand_col], ds.CATEGORY)  # Change

    for i in range(5):
        rand_col = math.floor(random.random() * 5)
        meta = ds.metadata.copy()
        meta['Type'][rand_col] = ds.CATEGORY
        ds.metadata = meta
        eq_(ds.type[rand_col], ds.CATEGORY)


@raises(AssertionError)
def test_set_metadata_fail_length():
    df = pd.DataFrame(np.random.rand(5, 5))
    ds = copper.Dataset(df)

    meta = ds.metadata.copy()
    meta = meta.drop(0)
    ds.metadata = meta


@raises(AssertionError)
def test_set_metadata_fail_index():
    df = pd.DataFrame(np.random.rand(5, 5))
    ds = copper.Dataset(df)

    meta = ds.metadata.copy()
    meta = meta.reindex([11, 1, 2, 3, 4])
    ds.metadata = meta


def test_save_load_metadata():
    tempdir = tempfile.gettempdir()
    # Save
    df = pd.DataFrame(np.random.rand(5, 10))
    ds = copper.Dataset(df)
    ds.role[2] = ds.TARGET
    ds.role[7] = ds.IGNORE
    ds.type[1] = ds.CATEGORY
    ds.type[5] = ds.CATEGORY
    ds.metadata.to_csv(os.path.join(tempdir, 'metadata.csv'))
    # Load
    ds2 = copper.Dataset(df)
    loaded_meta = pd.read_csv(os.path.join(tempdir, 'metadata.csv'))
    loaded_meta = loaded_meta.set_index('Columns')
    ds2.metadata = loaded_meta
    eq_(ds2.role[2], ds.TARGET)
    eq_(ds2.role[7], ds.IGNORE)
    eq_(ds2.type[1], ds.CATEGORY)
    eq_(ds2.type[5], ds.CATEGORY)


def test_copy_metadata():
    cols = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    df1 = pd.DataFrame(np.random.rand(5, 10), columns=cols)
    ds1 = copper.Dataset(df1)
    ds1.role[['c', 'd', 'h', 'i']] = ds1.TARGET
    ds1.type[['b', 'c', 'g', 'i']] = ds1.CATEGORY
    # meta_old = ds1.metadata.copy()

    df2 = pd.DataFrame(np.random.rand(5, 10), columns=cols)
    ds2 = copper.Dataset(df2)
    ds2.copy_metadata(ds1.metadata)
    eq_(ds2.metadata, ds1.metadata)


def test_copy_metadata_ignore_true():
    cols = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    df1 = pd.DataFrame(np.random.rand(5, 10), columns=cols)
    ds1 = copper.Dataset(df1)
    ds1.role[['a', 'd', 'h', 'i']] = ds1.TARGET
    ds1.type[['b', 'd', 'g', 'i']] = ds1.CATEGORY

    cols = ['z', 'y', 'f', 'a', 'b', 'd', 'e']
    df2 = pd.DataFrame(np.random.rand(5, 7), columns=cols)
    ds2 = copper.Dataset(df2)
    ds2.copy_metadata(ds1.metadata)
    eq_(ds2.role['z'], ds1.INPUT)
    eq_(ds2.role['y'], ds1.INPUT)
    eq_(ds2.role['a'], ds1.TARGET)
    eq_(ds2.role['b'], ds1.INPUT)
    eq_(ds2.role['d'], ds1.TARGET)
    eq_(ds2.role['e'], ds1.INPUT)

    eq_(ds2.type['z'], ds1.NUMBER)
    eq_(ds2.type['y'], ds1.NUMBER)
    eq_(ds2.type['a'], ds1.NUMBER)
    eq_(ds2.type['b'], ds1.CATEGORY)
    eq_(ds2.type['d'], ds1.CATEGORY)
    eq_(ds2.type['e'], ds1.NUMBER)


def test_copy_metadata_ignore_false():
    cols = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    df1 = pd.DataFrame(np.random.rand(5, 10), columns=cols)
    ds1 = copper.Dataset(df1)
    ds1.role[['a', 'd', 'h', 'i']] = ds1.TARGET
    ds1.type[['b', 'd', 'g', 'i']] = ds1.CATEGORY

    cols = ['z', 'y', 'f', 'a', 'b', 'd', 'e']
    df2 = pd.DataFrame(np.random.rand(5, 7), columns=cols)
    ds2 = copper.Dataset(df2)
    ds2.copy_metadata(ds1.metadata, ignoreMissing=False)
    eq_(ds2.role['z'], ds1.IGNORE)
    eq_(ds2.role['y'], ds1.IGNORE)
    eq_(ds2.role['a'], ds1.TARGET)
    eq_(ds2.role['b'], ds1.INPUT)
    eq_(ds2.role['d'], ds1.TARGET)
    eq_(ds2.role['e'], ds1.INPUT)

    eq_(ds2.type['z'], ds1.NUMBER)
    eq_(ds2.type['y'], ds1.NUMBER)
    eq_(ds2.type['a'], ds1.NUMBER)
    eq_(ds2.type['b'], ds1.CATEGORY)
    eq_(ds2.type['d'], ds1.CATEGORY)
    eq_(ds2.type['e'], ds1.NUMBER)


# -----------------------------------------------------------------------------
#                            Functions

def test_update_cat_to_num_int():
    sol = np.arange(100)
    strings = np.array(['a(%f)' % d for d in sol])
    df = pd.DataFrame(strings)
    ds = copper.Dataset(df)
    ds.type[0] = ds.NUMBER
    ds.update()
    eq_(sol, ds[0].values)


def test_update_cat_to_num_float():
    sol = np.arange(100) / 100
    strings = np.array(['a(%f)' % d for d in sol])
    df = pd.DataFrame(strings)
    ds = copper.Dataset(df)
    ds.type[0] = ds.NUMBER
    ds.update()
    eq_(sol, ds[0].values)


def test_filter_role():
    df = pd.DataFrame(np.random.rand(5, 10))
    ds = copper.Dataset(df)
    ds.role[[0, 2, 4, 5, 9]] = ds.IGNORE
    eq_(ds.filter(role=ds.INPUT), ds[[1, 3, 6, 7, 8]])

    ds.role[:] = ds.IGNORE
    ds.role[[1, 3, 4, 6, 8]] = ds.INPUT
    eq_(ds.filter(role=ds.INPUT), ds[[1, 3, 4, 6, 8]])

    ds.role[[2, 9]] = ds.TARGET
    eq_(ds.filter(role=ds.TARGET), ds[[2, 9]])

    eq_(ds.filter(role=[ds.INPUT, ds.TARGET]), ds[[1, 2, 3, 4, 6, 8, 9]])

    eq_(ds.filter(), df)


def test_filter_type():
    df = pd.DataFrame(np.random.rand(5, 10))
    ds = copper.Dataset(df)
    ds.type[[0, 2, 4, 5, 9]] = ds.CATEGORY
    eq_(ds.filter(type=ds.CATEGORY), ds[[0, 2, 4, 5, 9]])

    ds.type[:] = ds.CATEGORY
    ds.type[[1, 3, 6, 7, 9]] = ds.NUMBER
    eq_(ds.filter(type=ds.NUMBER), ds[[1, 3, 6, 7, 9]])

    eq_(ds.filter(type=[ds.NUMBER, ds.CATEGORY]), df)

    eq_(ds.filter(), df)


def test_filter_role_and_type():
    df = pd.DataFrame(np.random.rand(5, 5))
    ds = copper.Dataset(df)
    ds.role[:] = ds.IGNORE

    ds.role[2] = ds.INPUT
    ds.type[2] = ds.CATEGORY
    eq_(ds.filter(role=ds.INPUT, type=ds.CATEGORY), df[[2]])

    ds.role[4] = ds.INPUT
    ds.type[4] = ds.CATEGORY
    eq_(ds.filter(role=ds.INPUT, type=ds.CATEGORY), df[[2, 4]])

    eq_(ds.filter(role=ds.IGNORE, type=ds.NUMBER), df[[0, 1, 3]])

    ds.role[4] = ds.IGNORE
    eq_(ds.filter(role=ds.INPUT, type=ds.CATEGORY), df[[2]])

    eq_(ds.filter(), df)


# -----------------------------------------------------------------------------
#                            Pandas API

def test_get_column():
    df = pd.DataFrame(np.random.rand(5, 10))
    ds = copper.Dataset(df)
    eq_(ds[0], df[0])
    eq_(ds[5], df[5])
    eq_(ds[9], df[9])


def test_set_column():
    df = pd.DataFrame(np.random.rand(5, 10))
    ds = copper.Dataset(df)
    new_col = np.random.rand(5, 1)
    eq_(ds[3].values, df[3].values)
    ds[3] = new_col
    eq_(ds[[3]].values, new_col)


def test_head():
    df = pd.DataFrame(np.random.rand(5, 10))
    ds = copper.Dataset(df.copy())
    l = math.floor(random.random() * 10)
    eq_(ds.head(l), df.head(l))


def test_tail():
    df = pd.DataFrame(np.random.rand(5, 10))
    ds = copper.Dataset(df.copy())
    l = math.floor(random.random() * 10)
    eq_(ds.head(l), df.head(l))

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)

########NEW FILE########
__FILENAME__ = test_dbn
import os
import numpy as np
from copper.ml.dbn.dbn import DBN
from copper.tests.utils import eq_


def get_iris():
    from sklearn import datasets
    iris = datasets.load_iris()

    X = iris.data
    Y = iris.target
    return X, Y


def test_sklearn_api():
    ''' sklearn API: not functionality
    '''
    dbn = DBN([5])
    X, y = get_iris()
    dbn.fit(X, y)
    dbn.predict_proba(X)
    dbn.predict(X)


def test_instance():
    from sklearn.base import BaseEstimator
    dbn = DBN([5])
    assert isinstance(dbn, BaseEstimator)


def test_reproducible():
    X, y = get_iris()

    dbn1 = DBN([5], random_state=123)
    dbn1.fit(X, y)
    pred1 = dbn1.predict(X)
    prob1 = dbn1.predict_proba(X)

    dbn2 = DBN([5], random_state=123)
    dbn2.fit(X, y)
    pred2 = dbn2.predict(X)
    prob2 = dbn2.predict_proba(X)

    eq_(dbn1.coef_, dbn2.coef_)
    eq_(pred1, pred2)
    eq_(prob1, prob2)


def test_coef_eq_layers_0():
    dbn = DBN([5], pretrain_epochs=0, finetune_epochs=0, random_state=1234)
    X, y = get_iris()
    dbn.fit(X, y)

    eq_(dbn.coef_[:5], dbn.layers[0].b)
    eq_(dbn.coef_[5:25], dbn.layers[0].W.reshape(-1))
    eq_(dbn.coef_[25:28], dbn.layers[1].b)
    eq_(dbn.coef_[28:], dbn.layers[1].W.reshape(-1))


def test_coef_eq_layers_1():
    dbn = DBN([5], pretrain_epochs=0, finetune_epochs=1, random_state=1234)
    X, y = get_iris()
    dbn.fit(X, y)

    eq_(dbn.coef_[:5], dbn.layers[0].b)
    eq_(dbn.coef_[5:25], dbn.layers[0].W.reshape(-1))
    eq_(dbn.coef_[25:28], dbn.layers[1].b)
    eq_(dbn.coef_[28:], dbn.layers[1].W.reshape(-1))


def test_coef_eq_layers_change():
    # Test that the coef_ and layers weights are connected in memory
    dbn = DBN([5], pretrain_epochs=0, finetune_epochs=0, random_state=1234)
    X, y = get_iris()
    dbn.fit(X, y)

    eq_(dbn.layers[0].b, np.zeros(5))
    eq_(dbn.layers[1].b, np.zeros(3))

    dbn.coef_[:] = np.ones(len(dbn.coef_))
    eq_(dbn.layers[0].b, np.ones(5))
    eq_(dbn.layers[0].W, np.ones((4, 5)))
    eq_(dbn.layers[1].b, np.ones(3))
    eq_(dbn.layers[1].W, np.ones((5, 3)))

    eq_(dbn.layers[0].b[0], 1)
    dbn.coef_[0] = 2
    eq_(dbn.layers[0].b[0], 2)

    eq_(dbn.coef_[1], 1)
    dbn.layers[0].b[1] = 3
    eq_(dbn.coef_[1], 3)


def test_iris_accuracy():
    dbn = DBN([25], pretrain_epochs=0, finetune_epochs=10, finetune_batch_size=10, random_state=1)
    X, y = get_iris()
    dbn.fit(X, y)

    acc = (dbn.predict(X) == y).mean()
    eq_(acc, 0.95333, 5)


def test_save_load_weights():
    import tempfile
    tempdir = tempfile.gettempdir()
    tempfile = os.path.join(tempdir, 'w.json')
    # tempfile = os.path.join('', 'w.json')

    dbn1 = DBN([5], random_state=1234)
    X, y = get_iris()
    dbn1.fit(X, y)
    pred1 = dbn1.predict(X)
    prob1 = dbn1.predict_proba(X)

    dbn1.save(tempfile)

    dbn2 = DBN([5])
    dbn2.load(tempfile)
    pred2 = dbn2.predict(X)
    prob2 = dbn2.predict_proba(X)

    eq_(dbn1.coef_, dbn2.coef_)
    for i, layer in enumerate(dbn1.layers):
        eq_(dbn1.layers[i].W, dbn2.layers[i].W)

    eq_(pred1, pred2)
    eq_(prob1, prob2)

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)

########NEW FILE########
__FILENAME__ = test_gdbn
from __future__ import division

from copper.ml.gdbn.gdbn import DBN


def get_iris():
    from sklearn import datasets
    iris = datasets.load_iris()

    X = iris.data
    Y = iris.target
    return X, Y


def test_basic():
    ''' sklearn API: not functionality
    '''
    dbn = DBN()
    X, y = get_iris()
    dbn.fit(X, y)
    dbn.predict_proba(X)
    dbn.predict(X)

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)

########NEW FILE########
__FILENAME__ = test_transforms
from __future__ import division
import math
import random
import copper
import numpy as np
import pandas as pd

from nose.tools import raises
from copper.tests.utils import eq_


def test_transform_int_regex():
    eq_(copper.t.to_int('0.2'), 0)
    eq_(copper.t.to_int('.8753'), 8753)
    eq_(copper.t.to_int('3.2'), 3)
    eq_(copper.t.to_int('1.2'), 1)
    eq_(copper.t.to_int('1.0'), 1)
    eq_(copper.t.to_int('NN1.0'), 1)
    eq_(copper.t.to_int('NN3.4DD'), 3)
    eq_(copper.t.to_int('(35.2)'), 35)
    eq_(copper.t.to_int('FAKE') is np.nan, True)
    eq_(copper.t.to_int('FAKE.') is np.nan, True)
    eq_(copper.t.to_int('FAKE.321'), 321)
    eq_(copper.t.to_int('FAKE.321.111'), 321)


def test_transform_float_regex():
    eq_(copper.t.to_float('0.2'), 0.2)
    eq_(copper.t.to_float('.8753'), 0.8753)
    eq_(copper.t.to_float('3.2'), 3.2)
    eq_(copper.t.to_float('1.2'), 1.2)
    eq_(copper.t.to_float('1.0'), 1.0)
    eq_(copper.t.to_float('NN1.0'), 1.0)
    eq_(copper.t.to_float('NN3.4DD'), 3.4)
    eq_(copper.t.to_float('(35.2)'), 35.2)
    eq_(copper.t.to_float('FAKE') is np.nan, True)
    eq_(copper.t.to_float('FAKE.') is np.nan, True)
    eq_(copper.t.to_float('FAKE.321'), 0.321)
    eq_(copper.t.to_float('FAKE.321.111'), 0.321)


def test_transform_int():
    array = np.arange(10)
    strings = []
    for i, item in enumerate(array):
        strings.append("STRING(%i)" % item)
    ser = pd.Series(strings)
    sol = pd.Series(array)
    eq_(ser.apply(copper.t.to_int), sol)


def test_transform_float():
    array = np.arange(10) / 10
    strings = []
    for i, item in enumerate(array):
        strings.append("STRING(%f)" % item)
    ser = pd.Series(strings)
    sol = pd.Series(array)
    eq_(ser.apply(copper.t.to_float), sol)


def test_cat_encode_simple():
    strings = np.array(['1', '2', '1', '3', '5', '2', '1', '5'])
    sol = np.array([[1., 0, 0, 0], [0, 1, 0, 0], [1, 0, 0, 0],
                    [0, 0, 1, 0], [0, 0, 0, 1], [0, 1, 0, 0],
                    [1, 0, 0, 0], [0, 0, 0, 1]])
    eq_(copper.t.cat_encode(strings), sol)


def test_cat_encode_simple_list():
    strings = ['1', '2', '1', '3', '5', '2', '1', '5']
    sol = np.array([[1., 0, 0, 0], [0, 1, 0, 0], [1, 0, 0, 0],
                    [0, 0, 1, 0], [0, 0, 0, 1], [0, 1, 0, 0],
                    [1, 0, 0, 0], [0, 0, 0, 1]])
    eq_(copper.t.cat_encode(strings), sol)


def test_cat_encode_big():
    abc = 'abcdefghijklmnopqrstuvwxyz'
    array = np.floor(np.random.rand(100000) * 26)
    strings = np.array([abc[int(i)] for i in array])
    ans = copper.t.cat_encode(strings)
    eq_(len(ans), 100000)
    eq_(ans.sum(axis=1), np.ones(100000))
    eq_(ans.sum(), 100000)


def test_ml_inputs_simple():
    df = pd.DataFrame(np.random.rand(8, 6))
    strings = ['1', '2', '1', '3', '5', '2', '1', '5']
    df[1] = np.array(strings)
    df[3] = np.array(strings)
    ds = copper.Dataset(df)
    ds.type[[1, 3]] = ds.CATEGORY

    ans = copper.t.ml_inputs(ds)
    eq_(ans.shape, (8, 6 - 2 + 4 * 2))
    eq_(ans[:, 0], df[0].values)
    eq_(ans[:, [1, 2, 3, 4]], copper.t.cat_encode(df[1].values))
    eq_(ans[:, 5], df[2].values)
    eq_(ans[:, [6, 7, 8, 9]], copper.t.cat_encode(df[3].values))
    eq_(ans[:, 10], df[4].values)
    eq_(ans[:, 11], df[5].values)


def test_ml_inputs_simple_with_target():
    df = pd.DataFrame(np.random.rand(8, 6))
    strings = ['1', '2', '1', '3', '5', '2', '1', '5']
    df[1] = np.array(strings)
    df[3] = np.array(strings)
    ds = copper.Dataset(df)
    ds.type[[1, 3]] = ds.CATEGORY
    ds.role[[2]] = ds.TARGET

    ans = copper.t.ml_inputs(ds)
    eq_(ans.shape, (8, 5 - 2 + 4 * 2))
    eq_(ans[:, 0], df[0].values)
    eq_(ans[:, [1, 2, 3, 4]], copper.t.cat_encode(df[1].values))
    eq_(ans[:, [5, 6, 7, 8]], copper.t.cat_encode(df[3].values))
    eq_(ans[:, 9], df[4].values)
    eq_(ans[:, 10], df[5].values)


def test_ml_inputs_simple_with_ignore():
    df = pd.DataFrame(np.random.rand(8, 6))
    strings = ['1', '2', '1', '3', '5', '2', '1', '5']
    df[1] = np.array(strings)
    df[3] = np.array(strings)
    ds = copper.Dataset(df)
    ds.type[[1, 3]] = ds.CATEGORY
    ds.role[[2]] = ds.IGNORE

    ans = copper.t.ml_inputs(ds)
    eq_(ans.shape, (8, 5 - 2 + 4 * 2))
    eq_(ans[:, 0], df[0].values)
    eq_(ans[:, [1, 2, 3, 4]], copper.t.cat_encode(df[1].values))
    eq_(ans[:, [5, 6, 7, 8]], copper.t.cat_encode(df[3].values))
    eq_(ans[:, 9], df[4].values)
    eq_(ans[:, 10], df[5].values)


def test_ml_inputs_big():
    abc = 'abcdefghijklmnopqrstuvwxyz'
    m, n = 1000, 10
    array = np.floor(np.random.rand(m) * 26)
    strings = np.array([abc[int(i)] for i in array])
    df = pd.DataFrame(np.random.rand(m, 100))
    abc_cols = np.arange(n) * 10
    for col in abc_cols:
        df[col] = strings
    ds = copper.Dataset(df)
    ds.type[abc_cols.tolist()] = ds.CATEGORY

    ans = copper.t.ml_inputs(ds)
    eq_(ans.shape, (m, 100 - n + 26 * n))
    encoded = copper.t.cat_encode(strings)
    for i, abc_col in enumerate(abc_cols):
        s = abc_col + 25 * i
        f = abc_col + 25 * i + 26
        eq_(ans[:, s:f], encoded)


@raises(Exception)
def test_ml_target_error():
    df = pd.DataFrame(np.random.rand(8, 6))
    ds = copper.Dataset(df)
    copper.t.ml_target(ds)


def test_ml_target_number():
    df = pd.DataFrame(np.random.rand(8, 6))
    ds = copper.Dataset(df)

    target_col = math.floor(random.random() * 6)
    ds.role[target_col] = ds.TARGET

    le, target = copper.t.ml_target(ds)
    eq_(target, ds[target_col].values)
    eq_(le, None)


def test_ml_target_string():
    df = pd.DataFrame(np.random.rand(6, 6))
    strings = ['z', 'h', 'z', 'c', 'h', 'c']
    sol = [2, 1, 2, 0, 1, 0]
    df['T'] = strings

    ds = copper.Dataset(df)
    ds.role['T'] = ds.TARGET

    le, target = copper.t.ml_target(ds)
    eq_(target, np.array(sol))
    eq_(le.classes_.tolist(), ['c', 'h', 'z'])


def test_ml_target_more_than_one():
    df = pd.DataFrame(np.random.rand(8, 6))
    ds = copper.Dataset(df)

    ds.role[3] = ds.TARGET
    ds.role[5] = ds.TARGET

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        le, target = copper.t.ml_target(ds)
        eq_(le, None)
        eq_(target, ds[3].values)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)

########NEW FILE########
__FILENAME__ = utils
import numpy as np
import pandas as pd
import numpy.testing as np_test
import pandas.util.testing as pd_test
from nose.tools import eq_ as nose_eq


def eq_(ans, sol, digits=0):
    if type(ans) == np.ndarray and type(sol) == np.ndarray:
        array_eq(ans, sol, digits)
    elif type(ans) == pd.Series and type(sol) == pd.Series:
        series_eq(ans, sol)
    elif type(ans) == pd.TimeSeries and type(sol) == pd.TimeSeries:
        series_eq(ans, sol, digits)
    elif type(ans) == pd.DataFrame and type(sol) == pd.DataFrame:
        frame_eq(ans, sol, digits)
    elif isinstance(ans, pd.Index) and isinstance(sol, pd.Index):
        array_eq(ans.values, sol.values, digits)
    elif digits != 0:
        nose_eq(round(ans-sol, digits), 0)
    else:
        nose_eq(ans, sol, digits)


def array_eq(ans, sol, digits=0):
    if digits == 0:
        np_test.assert_array_equal(ans, sol)
    else:
        np_test.assert_array_almost_equal(ans, sol, digits)


def series_eq(ans, sol, digits=0):
    if digits == 0:
        pd_test.assert_series_equal(ans, sol, digits)
    else:
        nose_eq(ans.name, sol.name)
        np_test.assert_array_almost_equal(ans.values, sol.values, digits)


def frame_eq(ans, sol, digits=0):
    if digits == 0:
        pd_test.assert_frame_equal(ans, sol)
    else:
        nose_eq(ans.index.name, sol.index.name)
        nose_eq(ans.columns.name, sol.columns.name)
        np_test.assert_array_almost_equal(ans.values, sol.values, digits)

########NEW FILE########
__FILENAME__ = transform
import re
import numpy as np
from sklearn.preprocessing import LabelEncoder

intRE = re.compile('[-+]?[0-9]+')
floatRE = re.compile('[-+]?[0-9]*\.?[0-9]+')


def to_int(x):
    """ Convert from string to int. Usefull when used inside pandas.apply

    Regular expression: ``[-+]?[0-9]+``

    Examples
    --------
    >>> data = pd.Series(['1', 'a2', '(-3)', '___4___', '$31', '15%'])
    >>> data
        0          1
        1         a2
        2       (-3)
        3    ___4___
        4        $31
        5        15%
dtype: object
    >>> data.apply(copper.t.to_int)
        0     1
        1     2
        2    -3
        3     4
        4    31
        5    15
        dtype: int64
    """

    match = intRE.search(x)
    return np.nan if match is None else int(match.group())


def to_float(x):
    """ Convert from string to floats. Usefull when used inside pandas.apply

    Regular expression: ``[-+]?[0-9]*\.?[0-9]+``

    Examples
    --------
    >>> df = pd.Series(['1', 'a2', '(-3.5)', '___4.00001______', '$31.312', '15%'])
    >>> df
        0                       1
        1                      a2
        2                  (-3.5)
        3    ___4.00001___
        4                 $31.312
        5                     15%
    >>> df.apply(copper.t.to_int)
        0     1.00000
        1     2.00000
        2    -3.50000
        3     4.00001
        4    31.31200
        5    15.00000
        dtype: float64
    """
    match = floatRE.search(x)
    return np.nan if match is None else float(match.group())


def cat_encode(values):
    """ Encodes a category into multiple columns ready for machine learning

    Parameters
    ----------
    values: np.array or list

    Returns
    -------
    np.array

    Examples
    --------
    >>> cat_encode(np.array(['z', 'a', 'h', 'z', 'h']))
        [[ 0.  0.  1.]
        [ 1.  0.  0.]
        [ 0.  1.  0.]
        [ 0.  0.  1.]
        [ 0.  1.  0.]]
    """
    if type(values) is list:
        values = np.array(values)
    labels = np.unique(values)
    ans = np.zeros((len(values), len(labels)))
    for i, label in enumerate(labels):
        ans[:, i][values == label] = 1
    return ans


def ml_inputs(dataset):
    """ Takes a dataset and retuns the inputs in a numpy.array ready for
    machine learning.
    Mainly transforms non-numerical variables(columns) to numbers.

    Parameters
    ----------
    copper.Dataset

    Returns
    -------
    np.array
    """
    columns = dataset.filter_cols(role=dataset.INPUT)
    assert len(columns) > 0, 'No input variables on Dataset'

    ans = np.zeros((len(dataset), 1))
    for column in columns:
        if dataset.type[column] == dataset.NUMBER:
            ans = np.hstack((ans, dataset[[column]].values))
        elif dataset.type[column] == dataset.CATEGORY:
            ans = np.hstack((ans, cat_encode(dataset[column])))
    ans = np.delete(ans, 0, axis=1)
    return ans


def ml_target(dataset):
    """ Takes a dataset and retuns the target in a numpy.array ready for
    machine learning.
    Mainly transforms non-numerical variables(columns) to numbers.

    Parameters
    ----------
    copper.Dataset

    Returns
    -------
    (label_encoder, np.array)

    Notes
    -----
    If dataset has more than one variable with role=TARGET then the first one
    is selected.
    """
    cols = dataset.filter_cols(role=dataset.TARGET)
    assert len(cols) > 0, 'No target variables on Dataset'
    if len(cols) > 1:
        import warnings
        warnings.warn("Dataset contains more than one target, %s was choosed" % cols[0])

    if dataset[cols[0]].dtype in (np.int, np.float):
        return None, dataset[cols[0]].values
    else:
        le = LabelEncoder()
        encoded = le.fit_transform(dataset[cols[0]].values)
        return le, encoded


'''
import copper
import pandas as pd
from copper.tests.utils import eq_
# from copper.utils import transforms
from nose.tools import raises



if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vs', '--nologcapture'], exit=False)
'''

########NEW FILE########
__FILENAME__ = opti
# -*- coding: utf-8 -*-
from __future__ import division, print_function
import math
import numpy as np
from scipy import optimize


def minibatches(X, y=None, batch_size=50, batches=-1, random_state=None):
    if random_state is None:
        rnd = np.random.RandomState()
    elif isinstance(random_state, int):
        rnd = np.random.RandomState(random_state)
    else:
       rnd = random_state

    m = X.shape[0]
    batch_size = batch_size if batch_size >= 1 else int(math.floor(m * batch_size))

    if batches == -1:
        batches = int(math.ceil(m / batch_size))

    random_indices = rnd.choice(np.arange(m), m, replace=False)
    for i in range(batches):
        batch_indices = np.arange(i * batch_size, (i + 1) * batch_size)
        indices = random_indices[batch_indices]
        if y is None:
            yield X[indices]
        else:
            yield X[indices], y[indices]


def GD(fun, weights, grad, X, y, options, args=()):
    return weights - options['learning_rate'] * grad(weights, X, y, *args)


def GD_momentum(fun, weights, grad, X, y, options, args=()):
    bigjump = options['momentum'] * options['step']
    weights -= bigjump
    correction = options['learning_rate'] * grad(weights, X, y, *args)
    step = bigjump + correction
    options['step'] = step
    return weights - step


def RMSPROP(fun, weights, grad, X, y, options, args=()):
    gradient = grad(weights, X, y, *args)
    options['moving_mean_squared'] = options['decay'] * options['moving_mean_squared'] \
                                     + (1 - options['decay']) * gradient ** 2
    return weights - gradient / np.sqrt(options['moving_mean_squared'] + 1e-8)


def CG(fun, weights, grad, X, y, options, args=()):
    ans = optimize.minimize(fun, weights, jac=grad, method='CG', args=(X, y) + args, options={'maxiter': options['mb_maxiter']})
    return ans.x


def LBFGSB(fun, weights, grad, X, y, options, args=()):
    ans = optimize.minimize(fun, weights, jac=grad, method='L-BFGS-B', args=(X, y) + args, options={'maxiter': options['mb_maxiter']})
    return ans.x


def minimize(weights0, X, y, fun, grad, weights, method,
             epochs=10, batches_per_epoch=None, batch_size=50,
             random_state=None,
             options=None, args=None, callback=None):
    update = None
    update_params = None
    if method == 'GD':
        if 'learning_rate' not in options:
            options['learning_rate'] = 0.3
        if 'learning_rate_decay' not in options:
            options['learning_rate_decay'] = 0.9

        if 'momentum' in options:
            if 'momentum_decay' not in options:
                options['momentum_decay'] = 0.9
            options['step'] = 0
            update = GD_momentum

            def update_params():
                options['learning_rate'] = options['learning_rate'] * options['learning_rate_decay']
                options['momentum'] = options['momentum'] * options['momentum_decay']
        else:
            def update_params():
                options['learning_rate'] = options['learning_rate'] * options['learning_rate_decay']

            update = GD
    elif method == 'RMSPROP':
        if 'decay' not in options:
                options['decay'] = 0.9
        options['moving_mean_squared'] = 1
        update = RMSPROP
    elif method == 'CG':
        if 'mb_maxiter' not in options:
                options['mb_maxiter'] = 10
        update = CG
    elif method == 'L-BFGS-B':
        if 'mb_maxiter' not in options:
                options['mb_maxiter'] = 10
        update = LBFGSB
    else:
        raise Exception('Optimization method not found')

    if random_state is None:
        rnd = np.random.RandomState()
    elif isinstance(random_state, int):
        rnd = np.random.RandomState(random_state)
    else:
        rnd = random_state

    for epoch in range(epochs):
        batches = minibatches(X, y, batch_size=batch_size,
                              batches=batches_per_epoch,
                              random_state=rnd)
        if update_params is not None:
            update_params()
        i = 0
        for _X, _y in batches:
            weights[:] = update(fun, weights, grad, _X, _y, options, args=args)
            if callback is not None:
                stop = callback(epoch + 1, i + 1)
                if stop == True:
                    break
                i += 1

########NEW FILE########
__FILENAME__ = progress
# -*- coding: utf-8 -*-
from __future__ import division, print_function
import sys
import uuid
from IPython.display import HTML, Javascript, display


class ProgressBar(object):
    ''' IPython Notebook ready text progressbar
    '''
    def __init__(self, max, index=0, desc='', border='|', fill_char='#', width=50):
        self.max = max
        self.index = index
        self.desc = desc
        self.border = border
        self.fill_char = fill_char
        self.width = width
        self.prog_bar = ''
        self.update()

    def next(self):
        if self.index <= self.max:
            self.index += 1
            self.update()

    def set(self, index):
        self.index = index
        self.update()

    def update(self):
        percent_done = self.index / self.max
        all_full = self.width - 2
        num_hashes = int(round(percent_done * all_full))
        self.prog_bar = self.desc + ' ' + self.border
        self.prog_bar += self.fill_char * num_hashes
        self.prog_bar += ' ' * (all_full - num_hashes)
        self.prog_bar += self.border
        self.prog_bar += '  %.2f%%' % (percent_done * 100)

        print('\r', self, end='')
        sys.stdout.flush()

    def complete(self, finish=True):
        self.index = self.max
        self.update()
        if finish:
            self.finish()

    def finish(self):
        print('\r', self)

    def __str__(self):
        return str(self.prog_bar)




class JSProgressbar(object):
    ''' IPython notebook ready Javascript ProgressBar
    Uses JQuery UI.

    Note: Depending on the number of iterations and number of bars on the
    same notebooks makes the notebook goes slow.
    Need to work on cleaning the javascript.
    '''
    def __init__(self, max=100, index=0):
        self.divid = str(uuid.uuid4())
        self.max = max
        self.index = index

        pb = HTML( """
            <script src="http://code.jquery.com/ui/1.10.3/jquery-ui.js"></script>
            <div id="{0}" class="progressbar"><div class="progress-label">...</div></div>
            <style>
            .ui-progressbar {{
                position: relative;
                height: 20px;
                width: 70%;
            }}
            .progress-label {{
                position: absolute;
                left: 49.5%;
                top: 2px;
                font-weight: bold;
            }}
            </style>
        """.format(self.divid))
        display(pb)
        self.update()

    def next(self):
        if self.index < self.max:
            self.index += 1
            self.update()

    def animate(self, index):
        self.index = index

    def update(self):
        display(Javascript("""$(function() {{
                            var progressbar = $("#{0}.progressbar");
                            var progressLabel = $("#{0} .progress-label");

                            progressbar.progressbar({{
                                value: {1}
                            }});

                            progressLabel.text({1} + "%" );
                  }});""".format(self.divid, 100 * self.percent())))

    def percent(self):
        return self.index / self.max

########NEW FILE########
__FILENAME__ = gc_rbm
"""
This is the exact code of Edwin Chen's RBM:
https://raw.github.com/echen/restricted-boltzmann-machines/master/rbm.py
"""

import numpy as np

class RBM:

  def __init__(self, num_visible, num_hidden, learning_rate=0.1):
    self.num_hidden = num_hidden
    self.num_visible = num_visible
    self.learning_rate = learning_rate

    # Initialize a weight matrix, of dimensions (num_visible x num_hidden), using
    # a Gaussian distribution with mean 0 and standard deviation 0.1.
    self.weights = 0.1 * np.random.randn(self.num_visible, self.num_hidden)
    # Insert weights for the bias units into the first row and first column.
    self.weights = np.insert(self.weights, 0, 0, axis=0)
    self.weights = np.insert(self.weights, 0, 0, axis=1)

  def train(self, data, max_epochs=1000):
    """
    Train the machine.

    Parameters
    ----------
    data: A matrix where each row is a training example consisting of the states of visible units.
    """

    num_examples = data.shape[0]

    # Insert bias units of 1 into the first column.
    data = np.insert(data, 0, 1, axis=1)

    for epoch in range(max_epochs):
      # Clamp to the data and sample from the hidden units.
      # (This is the "positive CD phase", aka the reality phase.)
      pos_hidden_activations = np.dot(data, self.weights)
      pos_hidden_probs = self._logistic(pos_hidden_activations)
      pos_hidden_states = pos_hidden_probs > np.random.rand(num_examples, self.num_hidden + 1)
      # Note that we're using the activation *probabilities* of the hidden states, not the hidden states
      # themselves, when computing associations. We could also use the states; see section 3 of Hinton's
      # "A Practical Guide to Training Restricted Boltzmann Machines" for more.
      pos_associations = np.dot(data.T, pos_hidden_probs)

      # Reconstruct the visible units and sample again from the hidden units.
      # (This is the "negative CD phase", aka the daydreaming phase.)
      neg_visible_activations = np.dot(pos_hidden_states, self.weights.T)
      neg_visible_probs = self._logistic(neg_visible_activations)
      neg_visible_probs[:,0] = 1 # Fix the bias unit.
      neg_hidden_activations = np.dot(neg_visible_probs, self.weights)
      neg_hidden_probs = self._logistic(neg_hidden_activations)
      # Note, again, that we're using the activation *probabilities* when computing associations, not the states
      # themselves.
      neg_associations = np.dot(neg_visible_probs.T, neg_hidden_probs)

      # Update weights.
      self.weights += self.learning_rate * ((pos_associations - neg_associations) / num_examples)

      error = np.sum((data - neg_visible_probs) ** 2)
      print "Epoch %s: error is %s" % (epoch, error)

  def run_visible(self, data):
    """
    Assuming the RBM has been trained (so that weights for the network have been learned),
    run the network on a set of visible units, to get a sample of the hidden units.

    Parameters
    ----------
    data: A matrix where each row consists of the states of the visible units.

    Returns
    -------
    hidden_states: A matrix where each row consists of the hidden units activated from the visible
    units in the data matrix passed in.
    """

    num_examples = data.shape[0]

    # Create a matrix, where each row is to be the hidden units (plus a bias unit)
    # sampled from a training example.
    hidden_states = np.ones((num_examples, self.num_hidden + 1))

    # Insert bias units of 1 into the first column of data.
    data = np.insert(data, 0, 1, axis = 1)

    # Calculate the activations of the hidden units.
    hidden_activations = np.dot(data, self.weights)
    # Calculate the probabilities of turning the hidden units on.
    hidden_probs = self._logistic(hidden_activations)
    # Turn the hidden units on with their specified probabilities.
    hidden_states[:,:] = hidden_probs > np.random.rand(num_examples, self.num_hidden + 1)
    # Always fix the bias unit to 1.
    # hidden_states[:,0] = 1

    # Ignore the bias units.
    hidden_states = hidden_states[:,1:]
    return hidden_states

  # TODO: Remove the code duplication between this method and `run_visible`?
  def run_hidden(self, data):
    """
    Assuming the RBM has been trained (so that weights for the network have been learned),
    run the network on a set of hidden units, to get a sample of the visible units.

    Parameters
    ----------
    data: A matrix where each row consists of the states of the hidden units.

    Returns
    -------
    visible_states: A matrix where each row consists of the visible units activated from the hidden
    units in the data matrix passed in.
    """

    num_examples = data.shape[0]

    # Create a matrix, where each row is to be the visible units (plus a bias unit)
    # sampled from a training example.
    visible_states = np.ones((num_examples, self.num_visible + 1))

    # Insert bias units of 1 into the first column of data.
    data = np.insert(data, 0, 1, axis = 1)

    # Calculate the activations of the visible units.
    visible_activations = np.dot(data, self.weights.T)
    # Calculate the probabilities of turning the visible units on.
    visible_probs = self._logistic(visible_activations)
    # Turn the visible units on with their specified probabilities.
    visible_states[:,:] = visible_probs > np.random.rand(num_examples, self.num_visible + 1)
    # Always fix the bias unit to 1.
    # visible_states[:,0] = 1

    # Ignore the bias units.
    visible_states = visible_states[:,1:]
    return visible_states

  def daydream(self, num_samples):
    """
    Randomly initialize the visible units once, and start running alternating Gibbs sampling steps
    (where each step consists of updating all the hidden units, and then updating all of the visible units),
    taking a sample of the visible units at each step.
    Note that we only initialize the network *once*, so these samples are correlated.

    Returns
    -------
    samples: A matrix, where each row is a sample of the visible units produced while the network was
    daydreaming.
    """

    # Create a matrix, where each row is to be a sample of of the visible units
    # (with an extra bias unit), initialized to all ones.
    samples = np.ones((num_samples, self.num_visible + 1))

    # Take the first sample from a uniform distribution.
    samples[0,1:] = np.random.rand(self.num_visible)

    # Start the alternating Gibbs sampling.
    # Note that we keep the hidden units binary states, but leave the
    # visible units as real probabilities. See section 3 of Hinton's
    # "A Practical Guide to Training Restricted Boltzmann Machines"
    # for more on why.
    for i in range(1, num_samples):
      visible = samples[i-1,:]

      # Calculate the activations of the hidden units.
      hidden_activations = np.dot(visible, self.weights)
      # Calculate the probabilities of turning the hidden units on.
      hidden_probs = self._logistic(hidden_activations)
      # Turn the hidden units on with their specified probabilities.
      hidden_states = hidden_probs > np.random.rand(self.num_hidden + 1)
      # Always fix the bias unit to 1.
      hidden_states[0] = 1

      # Recalculate the probabilities that the visible units are on.
      visible_activations = np.dot(hidden_states, self.weights.T)
      visible_probs = self._logistic(visible_activations)
      visible_states = visible_probs > np.random.rand(self.num_visible + 1)
      samples[i,:] = visible_states

    # Ignore the bias units (the first column), since they're always set to 1.
    return samples[:,1:]

  def _logistic(self, x):
    return 1.0 / (1 + np.exp(-x))

if __name__ == '__main__':
  r = RBM(num_visible = 6, num_hidden = 2)
  training_data = np.array([[1,1,1,0,0,0],[1,0,1,0,0,0],[1,1,1,0,0,0],[0,0,1,1,1,0], [0,0,1,1,0,0],[0,0,1,1,1,0]])
  r.train(training_data, max_epochs = 5000)
  print r.weights
  user = np.array([[0,0,0,1,1,0]])
  print r.run_visible(user)

########NEW FILE########
__FILENAME__ = activationFunctions
"""
 Copyright (c) 2011,2012 George Dahl

 Permission is hereby granted, free of charge, to any person  obtaining
 a copy of this software and associated documentation  files (the
 "Software"), to deal in the Software without  restriction, including
 without limitation the rights to use,  copy, modify, merge, publish,
 distribute, sublicense, and/or sell  copies of the Software, and to
 permit persons to whom the  Software is furnished to do so, subject
 to the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.  THE
 SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT  HOLDERS
 BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,  WHETHER IN AN
 ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING  FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR  OTHER DEALINGS IN THE
 SOFTWARE.
"""


import numpy as num
import gnumpy as gnp

#NOTATION:
#we use y_l for the output of layer l
#y_0 is input
#
#we use x_l for the net input so, using * as matrix multiply and h_l
#for the elementwise activation function of layer l,
#x_l = y_{l-1} * W_l + b_l
#y_l = h_l(x_l)
#
#A neural net with L layers implements the function f(y_0, W) = y_L where
#y_0 is the input to the network and W represents all of the weights
#and biases of the network.
#We train neural nets to minimize some error function
# error(y, t) for fixed targets t.
#So given training inputs y_0 and targets t we minimize the function
#Error(W) = error( f(y_0, W), t)
#
#An activation function suitable for use as a hidden layer
#nonlinearity defines the following methods:
# 1A. activation(netInput)
# 2A. dEdNetInput(acts)
#
#An activation function suitable for use as the output layer
#nonlinearity defines the following methods in addiction to 1A:
# 1B. error(targets, netInput, acts = None)
# 2B. dErrordNetInput(targets, netInput, acts = None)
# 3.  HProd(vect, acts)
#
# 1B takes as an argument the net input to the output units because
# sometimes having that quantity allows the loss to be computed in a
# more numerically stable way. Optionally, 1B also takes the output
# unit activations, since sometimes that allows a more efficient
# computation of the loss.
#
# For "matching" error functions and output activation functions 2B
# should be just acts-targets.
# The difference between 2B and 2A (above) is that 2B incorporates the
# training criterion error(y,t) instead of just the error *at the
# output of this layer* the way 2A does.
#
# HProd gives the product of the H_{L,M} Hessian (Notation from "Fast
# Curvature Matrix-Vector Products for Second-Order Gradient Descent
# by N. Schraudolph) with a vector.

#If gnumpy gets replaced and a logOnePlusExp is needed, be sure to make it numerically stable.
#def logOnePlusExp(x):
#    # log(1+exp(x)) when x < 0 and
#    # x + log(1+exp(-x)) when x > 0


class Sigmoid(object):
    def activation(self, netInput):
        return netInput.sigmoid()
    def dEdNetInput(self, acts):
        return acts*(1-acts)
    def error(self, targets, netInput, acts = None):
        #return (targets*logOnePlusExp(-netInput) + (1-targets)*logOnePlusExp(netInput)).sum()
        #return (logOnePlusExp(netInput)-targets*netInput).sum()
        return (netInput.log_1_plus_exp()-targets*netInput).sum()
    def HProd(self, vect, acts):
        return vect*acts*(1-acts)
    def dErrordNetInput(self, targets, netInput, acts = None):
        if acts == None:
            acts = self.activation(netInput)
        return acts - targets

#You can write tanh in terms of sigmoid.
#def tanh(ar):
#    return 2*(2*ar).sigmoid()-1
# There might be a "better" tanh to use based on Yann LeCun's
# efficient backprop paper, but I forget what the constants A and B
# are in A * tanh ( B * x).
class Tanh(object):
    def activation(self, netInput):
        return gnp.tanh(netInput)
    def dEdNetInput(self, acts):
        return 1-acts*acts

class ReLU(object):
    def activation(self, netInput):
        return netInput*(netInput > 0)
    def dEdNetInput(self, acts):
        return acts > 0

class Linear(object):
    def activation(self, netInput):
        return netInput
    def dEdNetInput(self, acts):
        return 1 #perhaps returning ones(acts.shape) is more appropriate?
    def error(self, targets, netInput, acts = None):
        diff = targets-netInput
        return 0.5*(diff*diff).sum()
    def HProd(self, vect, acts):
        return vect
    def dErrordNetInput(self, targets, netInput, acts = None):
        if acts == None:
            acts = self.activation(netInput)
        return acts - targets

class Softmax(object):
    def activation(self, netInput):
        Zshape = (netInput.shape[0],1)
        acts = netInput - netInput.max(axis=1).reshape(*Zshape)
        acts = acts.exp()
        return acts/acts.sum(axis=1).reshape(*Zshape)
    def HProd(self, vect, acts):
        return acts*(vect-(acts*vect).sum(1).reshape(-1,1))
    def dErrordNetInput(self, targets, netInput, acts = None):
        if acts == None:
            acts = self.activation(netInput)
        return acts - targets
    def error(self, targets, netInput, acts = None):
        ntInpt = netInput - netInput.max(axis=1).reshape(netInput.shape[0],1)
        logZs = ntInpt.exp().sum(axis=1).log().reshape(-1,1)
        err = targets*(ntInpt - logZs)
        return -err.sum()







########NEW FILE########
__FILENAME__ = counter
"""
 Copyright (c) 2011,2012 George Dahl

 Permission is hereby granted, free of charge, to any person  obtaining
 a copy of this software and associated documentation  files (the
 "Software"), to deal in the Software without  restriction, including
 without limitation the rights to use,  copy, modify, merge, publish,
 distribute, sublicense, and/or sell  copies of the Software, and to
 permit persons to whom the  Software is furnished to do so, subject
 to the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.  THE
 SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT  HOLDERS
 BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,  WHETHER IN AN
 ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING  FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR  OTHER DEALINGS IN THE
 SOFTWARE.
"""

from sys import stderr

class Counter(object):
    def __init__(self, step=10):
        self.cur = 0
        self.step = step

    def tick(self):
        self.cur += 1
        if self.cur % self.step == 0:
            stderr.write( str(self.cur ) )
            stderr.write( "\r" )
            stderr.flush()
        
    def done(self):
        stderr.write( str(self.cur ) )
        stderr.write( "\n" )
        stderr.flush()

class Progress(object):
    def __init__(self, numSteps):
        self.total = numSteps
        self.cur = 0
        self.curPercent = 0
    def tick(self):
        self.cur += 1
        newPercent = (100*self.cur)/self.total
        if newPercent > self.curPercent:
            self.curPercent = newPercent
            stderr.write( str(self.curPercent)+"%" )
            stderr.write( "\r" )
            stderr.flush()
    def done(self):
        stderr.write( '100%' )
        stderr.write( "\n" )
        stderr.flush()

def ProgressLine(line):
    stderr.write(line)
    stderr.write( "\r" )
    stderr.flush()
    
def main():
    from time import sleep
    for i in range(500):
        s = str(2.379*i)
        ProgressLine(s)
        sleep(0.02)
    c = Counter(5)
    for i in range(500):
        c.tick()
        sleep(.005)
    c.done()
    p = Progress(5000)
    for i in range(5000):
        p.tick()
        sleep(.0005)
    p.done()


if __name__ == "__main__":
    main()
    

########NEW FILE########
__FILENAME__ = dbn
"""
 Copyright (c) 2011,2012 George Dahl

 Permission is hereby granted, free of charge, to any person  obtaining
 a copy of this software and associated documentation  files (the
 "Software"), to deal in the Software without  restriction, including
 without limitation the rights to use,  copy, modify, merge, publish,
 distribute, sublicense, and/or sell  copies of the Software, and to
 permit persons to whom the  Software is furnished to do so, subject
 to the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.  THE
 SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT  HOLDERS
 BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,  WHETHER IN AN
 ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING  FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR  OTHER DEALINGS IN THE
 SOFTWARE.
"""

import numpy as num
import gnumpy as gnp
import itertools
from activationFunctions import *
from pretrain import CD1
from pretrain import Binary as RBMBinary
from pretrain import Gaussian as RBMGaussian
from pretrain import ReLU as RBMReLU
from counter import Progress

class DummyProgBar(object):
    def __init__(self, *args): pass
    def tick(self): pass
    def done(self): pass

def initWeightMatrix(shape, scale, maxNonZeroPerColumn = None, uniform = False):
    #number of nonzero incoming connections to a hidden unit
    fanIn = shape[0] if maxNonZeroPerColumn==None else min(maxNonZeroPerColumn, shape[0])
    if uniform:
        W = scale*(2*num.random.rand(*shape)-1)
    else:
        W = scale*num.random.randn(*shape)
    for j in range(shape[1]):
        perm = num.random.permutation(shape[0])
        W[perm[fanIn:],j] *= 0
    return W

def validShapes(weights, biases):
    if len(weights) + 1 == len(biases):
        t1 = all(b.shape[0] == 1 for b in biases)
        t2 = all(wA.shape[1] == wB.shape[0] for wA, wB in zip(weights[:-1], weights[1:]))
        t3 = all(w.shape[1] == hb.shape[1] for w, hb in zip(weights, biases[1:]))
        t4 = all(w.shape[0] == vb.shape[1] for w, vb in zip(weights, biases[:-1]))
        return t1 and t2 and t3 and t4
    return False

def garrayify(arrays):
    return [ar if isinstance(ar, gnp.garray) else gnp.garray(ar) for ar in arrays]

def numpyify(arrays):
    return [ar if isinstance(ar, num.ndarray) else ar.as_numpy_array(dtype=num.float32) for ar in arrays]

def loadDBN(path, outputActFunct, realValuedVis = False, useReLU = False):
    fd = open(path, 'rb')
    d = num.load(fd)
    weights = garrayify(d['weights'].flatten())
    biases = garrayify(d['biases'].flatten())
    genBiases = []
    if 'genBiases' in d:
        genBiases = garrayify(d['genBiases'].flatten())
    fd.close()
    return DBN(weights, biases, genBiases, outputActFunct, realValuedVis, useReLU)

def buildDBN(layerSizes, scales, fanOuts, outputActFunct, realValuedVis, useReLU = False, uniforms = None):
    shapes = [(layerSizes[i-1],layerSizes[i]) for i in range(1, len(layerSizes))]
    assert(len(scales) == len(shapes) == len(fanOuts))
    if uniforms == None:
        uniforms = [False for s in shapes]
    assert(len(scales) == len(uniforms))

    initialBiases = [gnp.garray(0*num.random.rand(1, layerSizes[i])) for i in range(1, len(layerSizes))]
    initialGenBiases = [gnp.garray(0*num.random.rand(1, layerSizes[i])) for i in range(len(layerSizes) - 1)]
    initialWeights = [gnp.garray(initWeightMatrix(shapes[i], scales[i], fanOuts[i], uniforms[i])) \
                      for i in range(len(shapes))]

    net = DBN(initialWeights, initialBiases, initialGenBiases, outputActFunct, realValuedVis, useReLU)
    return net

def columnRMS(W):
    return gnp.sqrt(gnp.mean(W*W,axis=0))

def limitColumnRMS(W, rmsLim):
    """
    All columns of W with rms entry above the limit are scaled to equal the limit.
    The limit can either be a row vector or a scalar.
    """
    rmsScale = rmsLim/columnRMS(W)
    return W*(1 + (rmsScale < 1)*(rmsScale-1))

class DBN(object):
    def __init__(self, initialWeights, initialBiases, initialGenBiases, outputActFunct, realValuedVis = False, useReLU = False):
        self.realValuedVis = realValuedVis
        self.learnRates = [0.05 for i in range(len(initialWeights))]
        self.momentum = 0.9
        self.L2Costs = [0.0001 for i in range(len(initialWeights))]
        self.dropouts = [0 for i in range(len(initialWeights))]
        self.nesterov = False
        self.nestCompare = False
        self.rmsLims = [None for i in range(len(initialWeights))]

        if self.realValuedVis:
            self.learnRates[0] = 0.005

        self.weights = initialWeights
        self.biases = initialBiases
        self.genBiases = initialGenBiases

        if useReLU:
            self.RBMHidUnitType = RBMReLU()
            self.hidActFuncts = [ReLU() for i in range(len(self.weights) - 1)]
        else:
            self.RBMHidUnitType = RBMBinary()
            self.hidActFuncts = [Sigmoid() for i in range(len(self.weights) - 1)]
        self.outputActFunct = outputActFunct

        #state variables modified in bprop
        self.WGrads = [gnp.zeros(self.weights[i].shape) for i in range(len(self.weights))]
        self.biasGrads = [gnp.zeros(self.biases[i].shape) for i in range(len(self.biases))]

    def weightsDict(self):
        d = {}
        if len(self.weights) == 1:
            d['weights'] = num.empty((1,), dtype=num.object)
            d['weights'][0] = numpyify(self.weights)[0]
            d['biases'] = num.empty((1,), dtype=num.object)
            d['biases'][0] = numpyify(self.biases)[0]
        else:
            d['weights'] = num.array(numpyify(self.weights)).flatten()
            d['biases'] = num.array(numpyify(self.biases)).flatten()
            if len(self.genBiases) == 1:
                d['genBiases'] = num.empty((1,), dtype=num.object)
                d['genBiases'][0] = numpyify(self.genBiases)[0]
            else:
                d['genBiases'] = num.array(numpyify(self.genBiases)).flatten()
        return d

    def scaleDerivs(self, scale):
        for i in range(len(self.weights)):
            self.WGrads[i] *= scale
            self.biasGrads[i] *= scale

    def loadWeights(self, path, layersToLoad = None):
        fd = open(path, 'rb')
        d = num.load(fd)
        if layersToLoad != None:
            self.weights[:layersToLoad] = garrayify(d['weights'].flatten())[:layersToLoad]
            self.biases[:layersToLoad] = garrayify(d['biases'].flatten())[:layersToLoad]
            self.genBiases[:layersToLoad] = garrayify(d['genBiases'].flatten())[:layersToLoad] #this might not be quite right
        else:
            self.weights = garrayify(d['weights'].flatten())
            self.biases = garrayify(d['biases'].flatten())
            if 'genBiases' in d:
                self.genBiases = garrayify(d['genBiases'].flatten())
            else:
                self.genBiases = []
        fd.close()

    def saveWeights(self, path):
        num.savez(path, **self.weightsDict())

    def preTrainIth(self, i, minibatchStream, epochs, mbPerEpoch):
        #initialize CD gradient variables
        self.dW = gnp.zeros(self.weights[i].shape)
        self.dvb = gnp.zeros(self.genBiases[i].shape)
        self.dhb = gnp.zeros(self.biases[i].shape)

        for ep in range(epochs):
            recErr = 0
            totalCases = 0
            for j in range(mbPerEpoch):
                inpMB = minibatchStream.next()
                curRecErr = self.CDStep(inpMB, i, self.learnRates[i], self.momentum, self.L2Costs[i])
                recErr += curRecErr
                totalCases += inpMB.shape[0]
            yield recErr/float(totalCases)

    def fineTune(self, minibatchStream, epochs, mbPerEpoch, loss = None, progressBar = True, useDropout = False):
        for ep in range(epochs):
            totalCases = 0
            sumErr = 0
            sumLoss = 0
            if self.nesterov:
                step = self.stepNesterov
            else:
                step = self.step
            prog = Progress(mbPerEpoch) if progressBar else DummyProgBar()
            for i in range(mbPerEpoch):
                inpMB, targMB = minibatchStream.next()
                err, outMB = step(inpMB, targMB, self.learnRates, self.momentum, self.L2Costs, useDropout)
                sumErr += err
                if loss != None:
                    sumLoss += loss(targMB, outMB)
                totalCases += inpMB.shape[0]
                prog.tick()
            prog.done()
            yield sumErr/float(totalCases), sumLoss/float(totalCases)

    def totalLoss(self, minibatchStream, lossFuncts):
        totalCases = 0
        sumLosses = num.zeros((1+len(lossFuncts),))
        for inpMB, targMB in minibatchStream:
            inputBatch = inpMB if isinstance(inpMB, gnp.garray) else gnp.garray(inpMB)
            targetBatch = targMB if isinstance(targMB, gnp.garray) else gnp.garray(targMB)

            outputActs = self.fprop(inputBatch)
            sumLosses[0] += self.outputActFunct.error(targetBatch, self.state[-1], outputActs)
            for j,f in enumerate(lossFuncts):
                sumLosses[j+1] += f(targetBatch, outputActs)
            totalCases += inpMB.shape[0]
        return sumLosses / float(totalCases)

    def predictions(self, minibatchStream, asNumpy = False):
        for inpMB in minibatchStream:
            inputBatch = inpMB if isinstance(inpMB, gnp.garray) else gnp.garray(inpMB)
            outputActs = self.fprop(inputBatch)
            yield outputActs.as_numpy_array() if asNumpy else outputActs

    def CDStep(self, inputBatch, layer, learnRate, momentum, L2Cost = 0):
        """
        layer=0 will train the first RBM directly on the input
        """
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        mbsz = inputBatch.shape[0]
        vis = self.fprop(inputBatch, layer)
        GRBMFlag = layer==0 and self.realValuedVis
        visType = RBMGaussian() if GRBMFlag else self.RBMHidUnitType
        visHidStats, hidBiasStats, visBiasStats, negVis = \
                     CD1(vis, self.weights[layer], self.genBiases[layer], self.biases[layer], visType, self.RBMHidUnitType)
        factor = 1-momentum if not self.nestCompare else 1
        self.dW = momentum*self.dW + factor*visHidStats
        self.dvb = momentum*self.dvb + factor*visBiasStats
        self.dhb = momentum*self.dhb + factor*hidBiasStats

        if L2Cost > 0:
            self.weights[layer] *= 1-L2Cost*learnRate*factor

        self.weights[layer] += (learnRate/mbsz) * self.dW
        self.genBiases[layer] += (learnRate/mbsz) * self.dvb
        self.biases[layer] += (learnRate/mbsz) * self.dhb

        #we compute squared error even for binary visible unit RBMs because who cares
        return gnp.sum((vis-negVis)**2)

    def fpropBprop(self, inputBatch, targetBatch, useDropout):
        if useDropout:
            outputActs = self.fpropDropout(inputBatch)
        else:
            outputActs = self.fprop(inputBatch)
        outputErrSignal = -self.outputActFunct.dErrordNetInput(targetBatch, self.state[-1], outputActs)
        error = self.outputActFunct.error(targetBatch, self.state[-1], outputActs)
        errSignals = self.bprop(outputErrSignal)
        return errSignals, outputActs, error

    def constrainWeights(self):
        for i in range(len(self.rmsLims)):
            if self.rmsLims[i] != None:
                self.weights[i] = limitColumnRMS(self.weights[i], self.rmsLims[i])

    def step(self, inputBatch, targetBatch, learnRates, momentum, L2Costs, useDropout = False):
        mbsz = inputBatch.shape[0]
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        targetBatch = targetBatch if isinstance(targetBatch, gnp.garray) else gnp.garray(targetBatch)

        errSignals, outputActs, error = self.fpropBprop(inputBatch, targetBatch, useDropout)

        factor = 1-momentum if not self.nestCompare else 1.0
        self.scaleDerivs(momentum)
        for i, (WGrad, biasGrad) in enumerate(self.gradients(self.state, errSignals)):
            self.WGrads[i] += learnRates[i]*factor*(WGrad/mbsz - L2Costs[i]*self.weights[i])
            self.biasGrads[i] += (learnRates[i]*factor/mbsz)*biasGrad
        self.applyUpdates(self.weights, self.biases, self.weights, self.biases, self.WGrads, self.biasGrads)
        self.constrainWeights()
        return error, outputActs

    def applyUpdates(self, destWeights, destBiases, curWeights, curBiases, WGrads, biasGrads):
        for i in range(len(destWeights)):
            destWeights[i] = curWeights[i] + WGrads[i]
            destBiases[i] = curBiases[i] + biasGrads[i]

    def stepNesterov(self, inputBatch, targetBatch, learnRates, momentum, L2Costs, useDropout = False):
        mbsz = inputBatch.shape[0]
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        targetBatch = targetBatch if isinstance(targetBatch, gnp.garray) else gnp.garray(targetBatch)

        curWeights = [w.copy() for w in self.weights]
        curBiases = [b.copy() for b in self.biases]
        self.scaleDerivs(momentum)
        self.applyUpdates(self.weights, self.biases, curWeights, curBiases, self.WGrads, self.biasGrads)

        errSignals, outputActs, error = self.fpropBprop(inputBatch, targetBatch, useDropout)

        #self.scaleDerivs(momentum)
        for i, (WGrad, biasGrad) in enumerate(self.gradients(self.state, errSignals)):
            self.WGrads[i] += learnRates[i]*(WGrad/mbsz - L2Costs[i]*self.weights[i])
            self.biasGrads[i] += (learnRates[i]/mbsz)*biasGrad

        self.applyUpdates(self.weights, self.biases, curWeights, curBiases, self.WGrads, self.biasGrads)
        self.constrainWeights()
        return error, outputActs

    def gradDebug(self, inputBatch, targetBatch):
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        targetBatch = targetBatch if isinstance(targetBatch, gnp.garray) else gnp.garray(targetBatch)

        # mbsz = inputBatch.shape[0]
        outputActs = self.fprop(inputBatch)
        outputErrSignal = -self.outputActFunct.dErrordNetInput(targetBatch, self.state[-1], outputActs)
        #error = self.outputActFunct.error(targetBatch, self.state[-1], outputActs)
        errSignals = self.bprop(outputErrSignal)
        for i, (WGrad, biasGrad) in enumerate(self.gradients(self.state, errSignals)):
            #update the weight increments
            self.WGrads[i] = WGrad
            self.biasGrads[i] = biasGrad
        allWeightGrads = itertools.chain(self.WGrads, self.biasGrads)
        return gnp.as_numpy_array(gnp.concatenate([dw.ravel() for dw in allWeightGrads]))

    def fprop(self, inputBatch, weightsToStopBefore = None ):
        """
        Perform a (possibly partial) forward pass through the
        network. Updates self.state which, on a full forward pass,
        holds the input followed by each hidden layer's activation and
        finally the net input incident on the output layer. For a full
        forward pass, we return the actual output unit activations. In
        a partial forward pass we return None.
        """
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        if weightsToStopBefore == None:
            weightsToStopBefore = len(self.weights)
        #self.state holds everything before the output nonlinearity, including the net input to the output units
        self.state = [inputBatch]
        for i in range(min(len(self.weights) - 1, weightsToStopBefore)):
            curActs = self.hidActFuncts[i].activation(gnp.dot(self.state[-1], self.weights[i]) + self.biases[i])
            self.state.append(curActs)
        if weightsToStopBefore >= len(self.weights):
            self.state.append(gnp.dot(self.state[-1], self.weights[-1]) + self.biases[-1])
            self.acts = self.outputActFunct.activation(self.state[-1])
            return self.acts
        #we didn't reach the output units
        # To return the first set of hidden activations, we would set
        # weightsToStopBefore to 1.
        return self.state[weightsToStopBefore]

    def fpropDropout(self, inputBatch, weightsToStopBefore = None ):
        """
        Perform a (possibly partial) forward pass through the
        network. Updates self.state which, on a full forward pass,
        holds the input followed by each hidden layer's activation and
        finally the net input incident on the output layer. For a full
        forward pass, we return the actual output unit activations. In
        a partial forward pass we return None.
        """
        inputBatch = inputBatch if isinstance(inputBatch, gnp.garray) else gnp.garray(inputBatch)
        if weightsToStopBefore == None:
            weightsToStopBefore = len(self.weights)
        #self.state holds everything before the output nonlinearity, including the net input to the output units
        self.state = [inputBatch * (gnp.rand(*inputBatch.shape) > self.dropouts[0])]
        for i in range(min(len(self.weights) - 1, weightsToStopBefore)):
            dropoutMultiplier = 1.0/(1.0-self.dropouts[i])
            curActs = self.hidActFuncts[i].activation(gnp.dot(dropoutMultiplier*self.state[-1], self.weights[i]) + self.biases[i])
            self.state.append(curActs * (gnp.rand(*curActs.shape) > self.dropouts[i+1]) )
        if weightsToStopBefore >= len(self.weights):
            dropoutMultiplier = 1.0/(1.0-self.dropouts[-1])
            self.state.append(gnp.dot(dropoutMultiplier*self.state[-1], self.weights[-1]) + self.biases[-1])
            self.acts = self.outputActFunct.activation(self.state[-1])
            return self.acts
        #we didn't reach the output units
        # To return the first set of hidden activations, we would set
        # weightsToStopBefore to 1.
        return self.state[weightsToStopBefore]

    def bprop(self, outputErrSignal, fpropState = None):
        """
        Perform a backward pass through the network. fpropState
        defaults to self.state (set during fprop) and outputErrSignal
        should be self.outputActFunct.dErrordNetInput(...).
        """
        #if len(errSignals)==len(self.weights)==len(self.biases)==h+1 then
        # len(fpropState) == h+2 because it includes the input and the net input to the output layer and thus
        #fpropState[-2] is the activation of the penultimate hidden layer (or the input if there are no hidden layers)
        if fpropState == None:
            fpropState = self.state
        assert(len(fpropState) == len(self.weights) + 1)

        errSignals = [None for i in range(len(self.weights))]
        errSignals[-1] = outputErrSignal
        for i in reversed(range(len(self.weights) - 1)):
            errSignals[i] = gnp.dot(errSignals[i+1], self.weights[i+1].T)*self.hidActFuncts[i].dEdNetInput(fpropState[i+1])
        return errSignals

    def gradients(self, fpropState, errSignals):
        """
        Lazily generate (negative) gradients for the weights and biases given
        the result of fprop (fpropState) and the result of bprop
        (errSignals).
        """
        assert(len(fpropState) == len(self.weights)+1)
        assert(len(errSignals) == len(self.weights) == len(self.biases))
        for i in range(len(self.weights)):
            yield gnp.dot(fpropState[i].T, errSignals[i]), errSignals[i].sum(axis=0)




########NEW FILE########
__FILENAME__ = gnumpy
"""Documentation can be found at http://www.cs.toronto.edu/~tijmen/gnumpy.html"""

"""

Copyright (c) 2010-2012 Tijmen Tieleman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

If you use Gnumpy for scientific work that gets published, you should include
in that publication a citation of the technical report that describes Gnumpy.
That report can be found at http://www.cs.toronto.edu/~tijmen/gnumpyTr.pdf

"""





"""
This file is not intended to be read by anyone other than gnumpy developers. It's long, it's weakly documented (much of the internal documentation is elsewhere), and many lines are unnaturally long & illegible because I did a lot of inlining.

If you really want to know how gnumpy works internally, or if you want to extend it, you can ask me for the original, which doesn't have the inlining, and the internal documentation.
"""




# ------------------------------------------------------------------------------- module init & shutdown

import numpy, operator, sys as _sys, types as types, time as _time, os as _os, __builtin__, collections as _collections, pdb as _pdb, gc as _gc, ctypes as _ctypes, weakref as _weakref

_useGpu = _os.environ.get('GNUMPY_USE_GPU', 'auto')
assert _useGpu in ('auto', 'yes', 'no'), "environment variable GNUMPY_USE_GPU, if present, should be one of 'auto', 'yes', 'no'."
if _useGpu == 'auto':
 try: import cudamat as _cudamat; _useGpu = 'yes'
 except: print 'gnumpy: failed to import cudamat. Using npmat instead. No GPU will be used.'; _useGpu = 'no'
if _useGpu == 'yes':
 import cudamat as _cudamat
elif _useGpu == 'no':
 import npmat as _cudamat
 _precision = _os.environ.get('GNUMPY_CPU_PRECISION', '32')
 assert _precision in ('32', '64', '128'), 'environment variable GNUMPY_CPU_PRECISION, if present, should have value 32, 64, or 128.'
 _cudamat.__DTYPE__ = eval('numpy.float'+_precision)

_cmType = _cudamat.CUDAMatrix
_isTijmen = False
if hasattr(_cudamat, 'ct'): _ctInt = _cudamat.ct.c_int

def board_id_to_use():
 try:
  import gpu_lock
  return gpu_lock.obtain_lock_id()
 except:
  print 'gnumpy: failed to use gpu_lock. Using board #0 without knowing whether it is in use or not.'
  return 0

class GnumpyGpuUnavailableException(Exception): pass

_boardId = None
def _init_gpu():
 """ picks a board and claims it (if using cudamat aot npmat). exception if there is no board. """
 if '__gpu_inited' in globals(): return
 global _boardId
 if _useGpu=='yes':
  _boardId = ( board_id_to_use() if callable(board_id_to_use) else board_id_to_use)
  if _boardId==-1: raise GnumpyGpuUnavailableException('No gpu board is available. gnumpy will not function. Consider telling it to run on the CPU by setting environment variable GNUMPY_USE_GPU to "no".')
  _cudamat.cuda_set_device(_boardId)
  _cudamat.cublas_init()
 _cudamat.CUDAMatrix.init_random(0)
 globals()['__gpu_inited'] = None

def usingGpu():
 assert _useGpu in ('yes', 'no'), 'first initialize gnumpy'
 return _useGpu=='yes'

expensive_check_probability = 1
acceptable_number_types = 'anything goes' # alternatives: 'no nans'; 'no nans or infs'; or a number indicating the max allowed abs
dont__check_number_types_in_non_garrays = True
class GnumpyNumberTypeException(Exception): pass

_checking_number_type_now = False
def _check_number_types(x):
 """ does some checks, and then returns x. """
 if acceptable_number_types == 'anything goes': return x # this is the typical case, and in this case I just want to leave this checking function asap.

 global _checking_number_type_now
 if dont__check_number_types_in_non_garrays and not isinstance(x, garray): return x
 if _checking_number_type_now: return x # to prevent checks upon checks upon checks (infinite recursion)
 try:
  _checking_number_type_now = True
  if acceptable_number_types == 'no nans': raise NotImplementedError
  elif acceptable_number_types == 'no nans or infs':
   if not garray(x, copy=False).all_real(): raise GnumpyNumberTypeException('Found values that violate the rule set by gnumpy.acceptable_number_types: "%s"' % acceptable_number_types)
  elif type(acceptable_number_types) in _numberTypes:
   if (abs(garray(x, copy=False)) > acceptable_number_types).any2(): raise GnumpyNumberTypeException('Found values that violate the rule set by gnumpy.acceptable_number_types: "%s"' % acceptable_number_types)
  else: assert False, 'gnumpy: the value of variable "acceptable_number_types" must be one of "anything goes", "no nans", "no nans or infs".'
 finally:
  _checking_number_type_now = False
 return x



# ------------------------------------------------------------------------------- helpers copied from other files

def _isFullSlice(x): return type(x) == types.SliceType and x == slice(None) # the first check is necessary to avoid returning a broadcast array of False's if x is an array
def _isSequence(x): return type(x) == list or type(x) == tuple or type(x)==xrange
def _insertT(tup, index, tupleToInsert): return tuple(tup[:index]) + tuple(tupleToInsert) + tuple(tup[index:])
def _modifyT(tup, index, newValue): return tuple(tup[:index]) + (newValue,) + tuple(tup[index+1:])
def _deleteT(tup, start, end): return tup[:start] + tup[end:]
def _prodT(x): return reduce(operator.mul, x, 1)
def _findIndex3(tupOrGenerator): return ( i for i, x in enumerate(tuple(tupOrGenerator)) if x).next()
def _isNumber(x): return type(x) in _numberTypes
def _nonSeqAsS(x): return ( x if _isSequence(x) else (x,))
_t0=()
def reduceAdd(x): return reduce(operator.add, x)

def _deleteT2(tup, index):
 index %= len(tup)
 return tup[:index] + tup[index+1:]

_intTypes = set((types.IntType, types.LongType, numpy.int16, numpy.int32, numpy.int8, numpy.int64))
_floatTypes = set((types.FloatType, numpy.float64, numpy.float32, getattr(numpy, 'float128', numpy.float64), getattr(numpy, 'float96', numpy.float64))) # considering numpy.float64 a number is debatable. it really is a numpy object, and behaves that way, too: it has a __mul__ which prevents garray.__rmul__ from getting the task. However, for most purposes it's a number.
_numberTypes = _intTypes | _floatTypes

def _allTheSame(tup):
 tup = tuple(tup)
 if len(tup)<=1: return True
 for elt in tup[1:]:
  if elt != tup[0]: return False
 return True





# ------------------------------------------------------------------------------- gnumpy specific helpers

def _all2_(t, pred): return reduce(operator.and_, map(pred, t), True)
def _any2_(t, pred): return reduce(operator.or_, map(pred, t), False)

def _doExpensiveCheck(): return numpy.random.rand() < expensive_check_probability

def as_garray(x): return ( x if isinstance(x, garray) else garray(x))
def as_garray_or_scalar(x): return ( x if type(x) in _numberTypes or isinstance(x, garray) else garray(x))
def as_numpy_array(x): return ( x.as_numpy_array() if isinstance(x, garray) else numpy.array(x))

def _cm_reshape(cm, newShape):
 if _prodT(newShape)==0: return cm
 else: return cm.reshape(tuple(reversed(newShape)))

def _cm_col_slice_write(cm, start, end, sourceCm):
 cm.set_row_slice(start, end, sourceCm)

def _cm_col_slice_read(cm, start, end, target):
 cm.get_row_slice(start, end, target)
 return target

def _cm_row_slice_read(cm, start, end):
 if start==end: return _new_cm((0, cm.shape[0])) # cudamat special case workaround
 if cm.shape[1]==1 and start==0 and end==1: return cm # cudamat special case workaround
 ret = cm.get_col_slice(start, end)
 return ret

def _read_single_index(index, axisLen):
 index = int(index)
 if index>=axisLen or index<-axisLen: raise IndexError('index out of bounds. index %d requested on an axis of length %d' % (index, axisLen))
 return index % axisLen

def _short_slice(i): return slice(i, i+1)

def _read_simple_slice(sl, axisLen):
 assert sl.step in (None, 1), 'simple slice not understood'
 sFrom, sTo = slice(( None if sl.start==None else int(sl.start)), ( None if sl.stop==None else int(sl.stop))).indices(axisLen)[:2]
 if sFrom>sTo: sTo = sFrom
 return (sFrom, sTo, sTo-sFrom)

def _extend_shape(shape, nAxes): return (1,) * (nAxes-len(shape)) + shape

def cudamatHas(name):
 if not hasattr(_cudamat, '_cudamat'): return False
 return hasattr(_cudamat._cudamat, name)


# ------------------------------------------------------------------------------- memory management

max_memory_usage = numpy.inf # public

_cmsForReuse = _collections.defaultdict(list) # dict from size to list of reusable (abandoned) cms
__memoryInUse = 0
_memoryUsers = _collections.defaultdict(lambda: (0, 0))
track_memory_usage = False
tracked_arrays = _weakref.WeakValueDictionary() # dict of id() to array. The key is never used. This remains empty if track_memory_usage remains False.

def _new_cm(sizeOrShape):
 """
 Internal.
 Returns a new CUDAMatrix object of the given size.
 This is the only proc that allocs gpu mem.
 """
 global __memoryInUse
 if type(sizeOrShape) == tuple:
  if _prodT(sizeOrShape)==0: return _new_cm(1) # cudamat workaround: cudamat can't handle size 0 arrays
  else: return _new_cm(sizeOrShape[0]*sizeOrShape[1]).reshape((sizeOrShape[1], sizeOrShape[0]))
 size = sizeOrShape
 if size==0: return _cudamat.empty((1, 1)) # cudamat workaround
 if len(_cmsForReuse[size])!=0:
  return _cm_reshape(_cmsForReuse[size].pop(), (1, size)) # re-use an abandoned cm
 _init_gpu()
 if __memoryInUse+size*4*5 > max_memory_usage: free_reuse_cache(False) # if we're somewhat close to the limit, then free what's easy to free, and hope that there are contiguous blocks available.
 if __memoryInUse+size*4 > max_memory_usage: # if we're (still) OVER the limit, then do whatever can be done to make more mem available
  free_reuse_cache(True) # gc.collect can take quite some time
  if __memoryInUse+size*4 > max_memory_usage:
   raise MemoryError('Gnumpy ran out of memory. Currently in use are %s; the maximum allowed is %s; so the present request for %s is refused. Free some memory and try again.' % (_n_bytes_str(__memoryInUse), _n_bytes_str(max_memory_usage), _n_bytes_str(size*4)))
 try:
  ret = _cudamat.empty((size, 1))
  __memoryInUse += size*4 # do this only if the malloc succeeded
  return ret
 except _cudamat.CUDAMatException, e: # this means that malloc failed
  raise MemoryError('The GPU failed to allocate the requested %d bytes of memory. This doesn\'t mean that your program is using too much memory. It does, however, mean that you should reduce the value of gnumpy.max_memory_usage (currently %s), to always have some memory unused (which is necessary to find contiguous large blocks of memory to allocate). Failing to allocate enough memory makes the GPU feel very unwell, so you are advised to restart Python now, or expect to see incoherent error messages and risk causing more serious damage.' % (size*4, str(max_memory_usage)))

def free_reuse_cache(completely=True):
 """
 This frees all GPU memory that is not in use but is kept allocated for re-use.
 If <completely> is set to False, this works quicker but less thoroughly.
 """
 if completely: _gc.collect() # this has to happen before the loop, because this may add more entries in _cmsForReuse which then have to be freed by the loop
 global __memoryInUse
 for size in _cmsForReuse:
  while _cmsForReuse[size]:
   _cmsForReuse[size].pop()
   __memoryInUse -= size*4
 del _gc.garbage[:] # this shouldn't be necessary at all, but for some reason perfectly referenced AND perfectly deletable cms get put there

def _n_bytes_str(n):
 def _base(s): return ( _base(s[:-3]) + ',' + s[-3:] if len(s)>=4 else s)
 return _base(str(n)) + ' bytes'

def memory_in_use(in_megabytes=False):
 """ returns the number of bytes (or megabytes if you asked for that) of GPU memory that are in use. """
 return __memoryInUse // ( 2**20 if in_megabytes else 1)

def memory_available(free_reuse_cache_first):
 if free_reuse_cache_first: free_reuse_cache()
 return max_memory_usage - memory_in_use()

def _calling_line():
 """ Internal. Inspects the current python call stack and returns a nice string description of the line of code that called gnumpy. """
 stack = _pdb.traceback.extract_stack()[::-1] # newest first
 stack = stack[( i for i, x in enumerate(stack) if x[0] != stack[0][0]).next():] # skip any gnumpy procs on the stack
 def stackFrameToString(frame): return 'File "%s", line %d, in function %s:    %s' % (frame[0], frame[1], frame[2], ( '<command unknown>' if frame[3]==None else frame[3]))
 ret = stackFrameToString(stack[0])
 for frame in stack[1:]:
  if 'File "<ipython console>",' in ret: break
  if 'File "<stdin>",' in ret: break
  ret += '\n  Called by: ' + stackFrameToString(frame)
 return ret

def memory_allocators(minimum_n_bytes=1, new_style=False):
 """ Prints a list of lines in your code that allocated GPU memory that's still in use. """
 if not track_memory_usage:
  print 'The variable gnumpy.track_memory_usage must be set to True, to enable memory data collection (which can slow down your program a lot).'
  return
 if new_style:
  sigs = _collections.defaultdict(int) # dict of t2(line; n bytes) to total n bytes
  for a in tuple(tracked_arrays.values()): # I want to be totally sure that this is a loop over something that doesn't change in the process
   k = (a.allocating_line, a.nbytes)
   sigs[k] += a.nbytes
  for (line, nb_each), nb_total in sorted(sigs.items(), key = lambda x: x[1])[::-1]:
   if nb_total < minimum_n_bytes: continue
   print '%d objects of %s (total %s), that are still in use, were allocated by: \n%s\n' % (nb_total/nb_each, _n_bytes_str(nb_each), _n_bytes_str(nb_total), line)
 else:
  for line, (n,amt) in sorted(_memoryUsers.items(), key=lambda x:x[1][1]) [::-1] : # this is the version that doesn't explicitly track arrays
   if amt >= minimum_n_bytes:
    print '%d objects, totalling %s, that are still in use, were allocated by: %s' % (n, _n_bytes_str(amt), line)
    print



# ------------------------------------------------------------------------------- external procs

def status():
 if not usingGpu(): print 'gnumpy is running on the CPU, i.e. in simulation mode. The data type is float%s.' % _precision
 if usingGpu():
  if _boardId==None: print 'gnumpy is planning to run on a GPU, but hasn\'t yet chosen & initialized a board.'
  else: print 'gnumpy is running on GPU board #%d.' % _boardId
 print '%s of gpu memory are in use, of which at least %s can be freed immediately by gnumpy.free_reuse_cache().' % (_n_bytes_str(__memoryInUse), _n_bytes_str(__builtin__.sum( size*len(cms)*4 for size, cms in _cmsForReuse.items())))



def _rand__base(shapeInfo, distribution, zero_d_means_scalar):
 if len(shapeInfo)==1 and _isSequence(shapeInfo[0]): zero_d_means_scalar = False; shapeInfo = shapeInfo[0]
 ret = empty(shapeInfo)
 {'uniform': _cmType.fill_with_rand, 'normal': _cmType.fill_with_randn}[distribution](ret._base)
 if ret.size!=0 and _doExpensiveCheck(): assert ret.sum() < 100 + 2*ret.size, 'numerical gpu error: rand() gave a result>100'
 if len(shapeInfo) == 0 and zero_d_means_scalar: return ret.item()
 else: return ret

def tile(a, reps):
 if type(reps) in _numberTypes: reps = (reps,)
 reps = tuple(reps) # for generator expressions
 if type(a) in _numberTypes:
  ret = empty(reps)
  ret._base.assign(a)
  return ret
 a = as_garray(a)
 if len(reps) > a.ndim: a = a._add_axes(len(reps))
 if len(reps) < a.ndim: reps = _extend_shape(reps, a.ndim) # now len(reps)==a.ndim
 retShape = tuple([ a.shape[i] * reps[i] for i in tuple(xrange(len(reps)))])
 if _prodT(retShape)==0: return zeros(retShape)
 if _prodT(reps)==1: return a
 for i in range(a.ndim-1): # merge replication requests on adjacent axes, for efficiency.
  if reps[i]!=1 and reps[i+1]!=1 and a.shape[i]==1: return a.reshape(_deleteT2(a.shape, i)).tile(reps[:i]+(_prodT(reps[i:i+2]),)+reps[i+2:]).reshape(map(operator.mul, a.shape, reps))
 def dataIDone(nextA, i): return nextA.reshape(_modifyT(a.shape, i, a.shape[i]*reps[i])).tile(_modifyT(reps, i, 1))
 if reps[0]!=1: # replicating rows is easy and efficient: just repeat the data a number of times.
  temp = empty((reps[0], a.size)) # shape doesn't matter because dataIDone changes it
  tempCm = temp._base_shaped(1)
  if reps[0]>=1:
   _cm_row_slice_read(tempCm, 0, 1).assign(a._base_as_row())
   nCopiesDone = 1
   while nCopiesDone < reps[0]:
    nNow = __builtin__.min(nCopiesDone, reps[0]-nCopiesDone)
    _cm_row_slice_read(tempCm, nCopiesDone, nCopiesDone + nNow).assign(_cm_row_slice_read(tempCm, 0, nNow))
    nCopiesDone += nNow
  return dataIDone(temp, 0)
 # the general case is repeating a subset (aot the whole array) n times, before moving on to the next subset
 # using a transpose with the right shape, the subsets can become columns. those can be lengthened because that is replicating rows; a second transpose makes them now-lengthened subsets again
 axis = __builtin__.min( i for i in range(a.ndim) if reps[i]!=1)
 return dataIDone(a.reshape_2d(axis).T.tile((reps[axis], 1)).T, axis)

def is_garray(x): return isinstance(x, garray)
def is_array(x): return isinstance(x, garray) or type(x) == numpy.ndarray

def rand(*shapeInfo):
 """ the desired array shape can be entered either as integers or as a tuple of integers. If you enter a tuple you always get an array; if you enter nothing you get a scalar. """
 return _rand__base(shapeInfo, 'uniform', True)

def randn(*shapeInfo):
 """ the desired array shape can be entered either as integers or as a tuple of integers. If you enter a tuple you always get an array; if you enter nothing you get a scalar. """
 return _rand__base(shapeInfo, 'normal', True)

def empty(shape):
 if _isSequence(shape) or type(shape) == types.GeneratorType: shape = tuple(shape)
 else: shape = (shape,)
 return garray(_new_cm(_prodT(shape)), shape, None)

def zeros (shape): return tile(0, shape)
def ones (shape): return tile(1, shape)

def seed_rand(seed=None):
 _init_gpu()
 if seed==None: seed = int(_time.time())
 _cudamat.CUDAMatrix.init_random(seed)

def dot(a1, a2):
 # internally: for matrix-matrix multiplies only; vectors are treated like special cases.
 a1 = as_garray(a1); a2 = as_garray(a2)
 if a1.ndim==0 or a2.ndim==0: return a1*a2
 if a1.ndim==a2.ndim==1:
  if a1 is a2: return sum(a1**2)
  else: return dot(a1.reshape(1, a1.size), a2.reshape(a2.size, 1)).item()
 if a1.ndim==2 and a2.ndim==1: return dot(a1, a2.reshape(a2.size, 1)).ravel() # treat a2 like a column vector
 if a1.ndim==1 and a2.ndim==2: return dot(a1._add_axes(2), a2)[0]   # treat a1 like a row vector
 if a1.shape[-1] != a2.shape[-2]: raise ValueError('arrays not aligned for dot product. a dot product was requested of arrays with shapes %s and %s' % (a1.shape, a2.shape))
 if a1.ndim==a2.ndim==2:
  retShape = (a1.shape[0], a2.shape[1])
  if a1.shape[1]==0: return zeros(retShape) # cudamat bug workaround
  ret = empty(retShape)
  if ret.size!=0: _cudamat.dot(a2._base_as_2d(), a1._base_as_2d(), ret._base_as_2d())
  return ret
 if a1.ndim >= 2 and a2.ndim >= 2:
  # this is not necessarily fast, because if a2.ndim>=3 then it involves a transpose
  a12 = ( a1.reshape_2d(-1) if a1.ndim!=2 else a1)
  a22 = ( a2.transpose((a2.ndim-2,) + tuple(xrange(a2.ndim-2)) + (a2.ndim-1,)).reshape_2d(1)
          if a2.ndim!=2 else
          a2)
  retShape = _deleteT2(a1.shape, -1) + _deleteT2(a2.shape, -2)
  return dot(a12, a22).reshape(retShape)
 raise NotImplementedError('dot with arguments of shapes %s and %s' % (a1.shape, a2.shape))

def outer(vec1, vec2): return dot(vec1.ravel()[:, newaxis], vec2.ravel()[newaxis, :])

def concatenate(arrays, axis=0):
 arrays = tuple(map(as_garray, arrays))
 if axis<0: axis += arrays[0].ndim
 if not _isSequence(arrays) or not type(axis) in _numberTypes: raise ValueError('wrong argument types to gnumpy.concatenate: expected <arrays> to be a sequence and <axis> to be a number, but got types %s and %s.' % (type(arrays), type(axis)))
 if axis not in range(arrays[0].ndim): raise ValueError('bad axis number (%d) specified (the first array has %d axes)' % (axis, arrays[0].ndim))
 if not _allTheSame( _deleteT2(a.shape, axis) for a in arrays): raise ValueError('array dimensions must agree except possibly for axis #%d. The given array shapes are: %s' % (axis, tuple( a.shape for a in arrays)))
 finalShape = _modifyT(arrays[0].shape, axis, __builtin__.sum( a.shape[axis] for a in arrays))
 if axis==0:
  ret = empty(finalShape)
  nextI = 0
  for a in arrays:
   _cm_row_slice_read(ret._base_shaped(ret.ndim), nextI, nextI+a.size).assign(a._base_shaped(a.ndim))
   nextI += a.size
  return ret
 else:
  return concatenate(tuple([ a.reshape_2d(axis).T for a in arrays]), 0).T.reshape(finalShape)

def where(a, *vararg):
 """
 Note: if only one argument is provided, the returned value will be a tuple of *numpy* arrays of integer indices (gpu arrays can only contain floats).
 """
 if vararg==_t0: return numpy.where(as_numpy_array(a))
 assert len(vararg)==2, 'wrong number of arguments to gnumpy.where()'
 return garray(numpy.where(as_numpy_array(a), as_numpy_array(vararg[0]), as_numpy_array(vararg[1])))

def nonzero(a):
 """ See notes for where(). """
 return where(a)

newaxis = None

def eye(n): return diagflat(ones(n))

def diagflat(a, k=0):
 if isinstance(a, garray): return a.diagflat(k)
 else: return numpy.diagflat(a,k)

def tensordot(a, b, axes=2):
 if type(axes) in _numberTypes: return dot(a.reshape_2d(a.ndim-axes), b.reshape_2d(axes)).reshape(a.shape[:a.ndim-axes] + b.shape[axes:])
 assert len(axes)==2 and len(axes[0])==len(axes[1]), 'the axes parameter to gnumpy.tensordot looks bad'
 aRemove, bRemove = (tuple(axes[0]), tuple(axes[1]))
 return tensordot(a.transpose(filter(lambda x: x not in aRemove, tuple(xrange(a.ndim))) + aRemove),
                  b.transpose(bRemove + filter(lambda x: x not in bRemove, tuple(xrange(b.ndim)))),
                  len(aRemove))



# ------------------------------------------------------------------------------- reductors

def _reductor__base(x, axis, gpuOp, npOp):
 if _isTijmen: numTimeIncurred(x.size, '%s onDim0=%s' % (npOp.__name__, axis in (0, None)))
 if type(x) == numpy.ndarray: return npOp(x, axis)
 if not isinstance(x, garray): x = garray(x)
 if gpuOp==None: return garray(npOp(x.as_numpy_array(), axis))
 else: return gpuOp(x, axis)

def all(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.all, numpy.all)

def any(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.any, numpy.any)

def sum(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.sum, numpy.sum)

def mean(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.mean, numpy.mean)

def max(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.max, numpy.max)

def min(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, garray.min, numpy.min)

def prod(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, None, numpy.prod)

def std(x, axis=None):
 """ On numpy arrays this returns a numpy array; on garrays and other array-likes this returns a garray. """
 return _reductor__base(x, axis, None, numpy.std)



# ------------------------------------------------------------------------------- elementwise operations

def _elementwise__base(x, opGpu, opNp):
 if type(x) in _numberTypes: return _check_number_types(float(opNp(x)))
 if opGpu==None or type(x) == numpy.ndarray: # else, time admin happens in the method
  if _isTijmen: numTimeIncurred(x.size, opNp.__name__)
 if isinstance(x, garray):
  if opGpu==None: return _check_number_types(garray(opNp(x.as_numpy_array())))
  else: return _check_number_types(opGpu(x))
 if type(x) == numpy.ndarray:
  if x.ndim==0: return _check_number_types(numpy.array(opNp(x)))
  else: return _check_number_types(opNp(x))
 raise TypeError('value %s of unexpected type %s provided to %s()' % (x, type(x), str(opNp).split("'")[1]))

def abs(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.abs, numpy.abs)

def exp(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.exp, numpy.exp)

def isinf(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.isinf, numpy.isinf)

def isnan(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.isnan, numpy.isnan)

def log(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.log, numpy.log)

def log_1_plus_exp(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.log_1_plus_exp, lambda x: log(1.+exp(x)))

def logistic(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.logistic, lambda x: 1./(1. + exp(-x)))

def negative(x):
 """
 Like -x, except that a zero dimensional numpy array input results in a numpy array return value.
 This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats).
 """
 return _elementwise__base(x, operator.neg, operator.neg)

def sign(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.sign, numpy.sign)

def sqrt(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.sqrt, numpy.sqrt)

def tanh(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, garray.tanh, numpy.tanh)

def log10(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, None, numpy.log10)

def log2(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, None, numpy.log2)

def cos(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, None, numpy.cos)

def sin(x):
 """ This works on garrays, numpy arrays, and numbers, preserving type (though all numbers become floats). """
 return _elementwise__base(x, None, numpy.sin)





class garray(object):
 """
 A class designed to interface like numpy arrays, and internally do its work on a GPU.
 Documentation can be found at http://www.cs.toronto.edu/~tijmen/gnumpy.html
 """

 # ------------------------------------------------------------------------------- internal aux

 def _set_shape_info(self, shape): # setting these as attributes rather than properties saves exec time
  self.shape = shape
  self.size = _prodT(shape)
  self.ndim = len(shape)

 @property
 def nbytes(self): return self.size * 4
 @property
 def nMBytes(self): return self.nbytes / 2**20

 def _base_shaped(self, nDimsAsRows): return _cm_reshape(self._base, (_prodT(self.shape[:nDimsAsRows]), _prodT(self.shape[nDimsAsRows:])))
 def _base_as_row(self): return _cm_reshape(self._base, (1, self.size))
 def _base_as_2d(self): return self._base.reshape((self.shape[1], self.shape[0])) # optimized from self._base_shaped(1) by inlining

 def _new_cm(self, nDimsAsRows=0): return _new_cm((_prodT(self.shape[:nDimsAsRows]), _prodT(self.shape[nDimsAsRows:]))) # same size as self, with given shape

 def _new(self, cm): return garray(cm, self.shape, None) # short notation for the result of elementwise ops

 def _tile_to_broadcast(self, otherShape, indicesToBroadcast='all'):
  """ self.shape and otherShape must already be of the same length. otherShape is relevant only where self.shape is 1. """
  if otherShape == self.shape: return self
  assert self.ndim == len(otherShape), 'dimensionality mismatch in _tile_to_broadcast'
  if indicesToBroadcast=='all': indicesToBroadcast = tuple( i for i in range(self.ndim) if self.shape[i]==1 and otherShape[i]!=1)
  return self.tile( ( 1 if i not in indicesToBroadcast else otherShape[i] ) for i in range(self.ndim))

 def _broadcastable_op(self, other, operatorName):
  """
  accepted ops: "add", "multiply", "less than", "greater than", "pow".
  other must be either scalar or garray.
  """
  basicHandler = {'add': _cmType.add, 'multiply': _cmType.mult, 'less than': _cmType.less_than, 'greater than': _cmType.greater_than, 'pow': _cudamat.pow}[operatorName]
  if (type(other) in _numberTypes or (other.size==1 and other.ndim <= self.ndim)): # having other be a scalar is faster than doing a broadcast
   if _isTijmen: numTimeIncurred(self.size, 'AS eltwise')
   return self._new(basicHandler(self._base_as_row(), ( other.item() if isinstance(other, garray) else other), self._new_cm()))
  if operatorName=='pow': raise NotImplementedError('a**b where b is anything other than a scalar')
  other = as_garray(other)
  if self.ndim > other.ndim: other = other._add_axes(self.ndim)
  if self.ndim < other.ndim: return self._add_axes(other.ndim)._broadcastable_op(other, operatorName)
  if operatorName in ('less than', 'greater than'):
   self2 = self._tile_to_broadcast(other.shape)
   if _isTijmen: numTimeIncurred(self.size, 'eltwise binary, no bc')
   return self2._new(basicHandler(self2._base_as_row(), other._tile_to_broadcast(self2.shape)._base_as_row(), self2._new_cm()))
  if self.ndim < other.ndim: return other._broadcastable_op(self, operatorName) # now self.ndim == other.ndim
  selfToBroadcast =  tuple( self.shape[i]==1 and other.shape[i]!=1 for i in range(self.ndim))
  otherToBroadcast = tuple( other.shape[i]==1 and self.shape[i]!=1 for i in range(self.ndim))
  bc = otherToBroadcast; bci = tuple( i for i in tuple(xrange(len(bc))) if bc[i])
  if reduce(operator.or_, selfToBroadcast, False) and reduce(operator.or_, otherToBroadcast, False): return self._broadcastable_op(other._tile_to_broadcast(self.shape, bci), operatorName)
  if reduce(operator.or_, selfToBroadcast, False): return other._broadcastable_op(self, operatorName) # now only other may have dims that need to be broadcast
  if reduce(operator.or_, ( other.shape[i] not in (1, self.shape[i]) for i in range(self.ndim)), False): raise ValueError('shape mismatch: objects cannot be broadcast to a single shape')
  if not reduce(operator.or_, otherToBroadcast, False): # handle case: nothing to bc
   if _isTijmen: numTimeIncurred(self.size, 'eltwise binary, no bc')
   return self._new(( _cmType.add if operatorName=='add' else _cmType.mult)(self._base_as_row(), other._base_as_row(), self._new_cm()))
  if self.size==0: return self
  if bci == tuple(xrange(len(bci))): # handle case: only the first dims need broadcasting
   if operatorName in ('multiply', 'add') and _isTijmen and usingGpu(): # using optimized cuda code
    ret = empty(self.shape)
    axis0len = _prodT(self.shape[:len(bci)])
    axis1len = _prodT(self.shape[len(bci):])
    nThreadsPerBlock = 512
    nBlocks = axis1len//nThreadsPerBlock+1
    cudaFn = getattr(_cudamat._cudamat, '%sBcAxis0' % operatorName)
    cudaFn.restype = _ctypes.c_int
    assert 0==cudaFn(_ctInt(nBlocks), _ctInt(nThreadsPerBlock), self._base.p_mat, other._base.p_mat, ret._base.p_mat, _ctInt(axis0len), _ctInt(axis1len))
    if _isTijmen: numTimeIncurred(self.size, 'eltwise bc axis 0')
    return ret
   #return self._new(( _cmType.add_col_vec if operatorName=='add' else _cmType.mult_by_col)(self._base_shaped(len(bci)), other._base_as_row(), self._new_cm(len(bci))))
  if bci == tuple(xrange(self.ndim-len(bci), self.ndim)): # handle case: only the last dims need broadcasting
   if _isTijmen: numTimeIncurred(self.size, 'eltwise bc axis -1')
   return self._new(( _cmType.add_row_vec if operatorName=='add' else _cmType.mult_by_row)(self._base_shaped(self.ndim-len(bci)), other._base_shaped(self.ndim-len(bci)), self._new_cm(self.ndim-len(bci))))
  # remaining case: broadcasting neither just the first dims nor just the last dims. this can be done very intelligently, but for now I won't bother
  if operatorName=='multiply' and len(bci)==1 and cudamatHas('multiplyBcAxis1'): # special case: using optimized multiplyBcAxis1 (my cuda code)
   ret = empty(self.shape)
   axisI = bci[0]
   axis0len = _prodT(self.shape[:bci[0]])
   axis1len = self.shape[bci[0]]
   axis2len = _prodT(self.shape[bci[0]+1:])
   _cudamat._cudamat.multiplyBcAxis1.restype = _ctypes.c_int
   assert 0==_cudamat._cudamat.multiplyBcAxis1(_ctInt(__builtin__.min(512, axis2len)),
                                          self._base.p_mat,
                                          other._base.p_mat,
                                          ret._base.p_mat,
                                          _ctInt(axis0len),
                                          _ctInt(axis1len),
                                          _ctInt(axis2len),
                                          )
   if _isTijmen: numTimeIncurred(self.size, 'eltwise bc axis 1')
   return ret
  return self._broadcastable_op(other._tile_to_broadcast(self.shape, bci[:1]), operatorName)

 def _elementwise_unary(self, handler):
  if _isTijmen: numTimeIncurred(self.size, handler.__name__)
  return _check_number_types(self._new(handler(self._base_as_row(), self._new_cm())))

 def _reduction__base(self, operatorName, axis):
  if axis==None: return self.ravel()._reduction__base(operatorName, 0).item()
  if not type(axis) in _numberTypes: raise TypeError('the value %s is not appropriate for the "axis" parameter.' % str(axis))
  if axis < -self.ndim or axis>=self.ndim: raise ValueError('axis (%d) out of bounds for an array with %d axes.' % (axis, self.ndim))
  axis = int(axis) % self.ndim
  if self.size==0:
   retShape = _deleteT2(self.shape, axis)
   if operatorName=='sum': return zeros(retShape)
   elif operatorName=='max': return tile(-inf, retShape)
   else: assert False
  if operatorName=='max' and axis==0 and cudamatHas('maxAxis0'): # my own fast implementation
   ret = empty(self.shape[1:])
   _ctInt = _cudamat.ct.c_int
   nThreadsPerBlock = 32
   gridX, gridY = ((ret.size+nThreadsPerBlock-1)//nThreadsPerBlock), 1
   while gridX>65535: gridY*=2; gridX = (gridX+1)//2;
   _cudamat._cudamat.maxAxis0.restype = _ctypes.c_int
   assert 0==_cudamat._cudamat.maxAxis0(_ctInt(gridX), _ctInt(gridY), _ctInt(nThreadsPerBlock), self._base.p_mat, ret._base.p_mat, _ctInt(self.shape[0]), _ctInt(ret.size))
   return ret
  if axis==0 and operatorName=='max': # max over rows is not yet supported in cudamat
   return self.reshape_2d(1).T.max(1).reshape(self.shape[1:])
  if axis==0 and self.ndim==1 and self.size>5000 and operatorName=='sum': # optimization. apparently, cudamat is not maximally efficient.
   n = int(numpy.sqrt(self.size-1))
   return self[:n*n].reshape((n, n))._reduction__base(operatorName, 0)._reduction__base(operatorName, 0) + self[n*n:]._reduction__base(operatorName, 0)
  if operatorName=='sum':
   chunkSize = 1024*256 # sum over longer dimensions fails in cudamat
   nChunks = (self.shape[axis] + chunkSize-1) // chunkSize
   if nChunks>1:
    return reduceAdd( self[(slice(None),) * axis + (slice(chunkI*chunkSize, __builtin__.min(self.shape[axis], (chunkI+1)*chunkSize)),)]._reduction__base(operatorName, axis)
                      for chunkI in range(nChunks))
  if operatorName=='max' and self.isnan().any2(): # cudamat bug workaround
   return garray(self.asarray().max(axis))
  operatorInCm = {'sum': _cmType.sum, 'max': _cmType.max}[operatorName]
  if axis==0: return _check_number_types(garray(operatorInCm(self._base_shaped(1), 1, _new_cm(_prodT(self.shape[1:]))), self.shape[1:], None))
  if axis==self.ndim-1:
   if self.ndim!=2: return self.reshape_2d(-1)._reduction__base(operatorName, 1).reshape(self.shape[:-1])
   if self.ndim==2:
    chunkSize = 2**16-1
    nChunks = (len(self) + chunkSize-1) // chunkSize
    if nChunks>1: # cudamat chokes on big arrays, so break it in pieces for cudamat
     chunks = tuple([ self[chunkI*chunkSize : __builtin__.min((chunkI+1)*chunkSize, len(self))]
                      for chunkI in range(nChunks)])
     return concatenate([ chunk._reduction__base(operatorName, 1) for chunk in chunks])
    else: # small array
     return _check_number_types(garray(operatorInCm(self._base_shaped(1), 0, _new_cm((len(self), 1))), (len(self),), None))
  return self.transpose_simple(axis)._reduction__base(operatorName, 0).transpose_simple(-axis)



 # ------------------------------------------------------------------------------- external misc non-numerical

 def __init__(self, data, copy=True, ndmin=0):
  """ the parameters mean the same as in numpy.array() """
  if type(data)!=_cmType: assert copy in (True, False) and type(ndmin) in _numberTypes, 'garray() parameters copy=%s, ndmin=%s are not of the right type' % (str(copy), str(ndmin))
  if type(data)==_cmType: # internal use only. the 3 arguments are, unlike their names suggest, the ._base, .shape, ._is_alias_of
   self._base = data
   self._set_shape_info(copy)
   self._is_alias_of = ndmin
   if self._is_alias_of==None and track_memory_usage:
    self.allocating_line = _calling_line()
    tracked_arrays[id(self)] = self
    _memoryUsers[self.allocating_line] = (_memoryUsers[self.allocating_line][0]+1, _memoryUsers[self.allocating_line][1]+self.size*4)
  elif isinstance(data, garray):
   if ndmin>0: data = data._add_axes(ndmin)
   garray.__init__(self,
    ( _new_cm(data.size).assign(data._base_as_row()) if copy else data._base),
    data.shape,
    ( None if copy else data))
  elif type(data) == types.GeneratorType: garray.__init__(self, tuple(data), ndmin=ndmin)
  elif _isSequence(data):
   if len(data)==0 or not _any2_(data, is_garray): garray.__init__(self, numpy.array(data, ndmin=ndmin), copy=False)
   else: garray.__init__(self, concatenate( as_garray(element)[None] for element in data), ndmin=ndmin) # no need to copy, because concat copies.
  else: # remaining cases. essentially init from numpy array.
   npa = numpy.array(data, copy=False) # in case data was a number
   if str(npa.dtype) in ('object', '|S3'): raise TypeError('Cannot convert "%s" to a garray.' % data)
   # we're not using the cudamat constructor, because that always allocs gpu mem, and this way the mem may come from re-use.
   cm = _new_cm(npa.size)
   if not hasattr(cm, 'numpy_array'):
    #cm.copy_to_host() # if cm was created using cudamat.empty, this is needed to associate cm with a numpy array
    # follows an inlined version of the relevant portion of cm.copy_to_host(). This is quicker because it doesn't actually copy.
    cm.numpy_array = numpy.empty((cm.mat.size[0], cm.mat.size[1]), dtype=numpy.float32, order='F')
    cm.mat.data_host = cm.numpy_array.ctypes.data_as(_ctypes.POINTER(_ctypes.c_float))
    cm.mat.on_host = 1
   if npa.size!=0: cm.numpy_array[:] = npa.reshape((-1, 1), order='C') # no cudamat.reformat is needed, because that's only dtype and order change, which are handled by the assignment anyway
   cm.copy_to_device()
   garray.__init__(self, cm, _extend_shape(npa.shape, ndmin), None)

 def __new__(cls, *args, **kwarg): return object.__new__(cls)

 def as_numpy_array(self, dtype=numpy.float64):
  if self.size==0: return numpy.zeros(self.shape, dtype)
  return numpy.array(self._base_as_row().asarray(), copy=True, order='C', dtype=dtype).reshape(self.shape)

 asarray = as_numpy_array # the cudamat name

 def astype(self, type): return self.asarray().astype(type)

 tile = tile

 def ravel(self): return self.reshape(-1)

 def item(self): return self.as_numpy_array().item()

 def _add_axes(self, finalNdim): return self.reshape(_extend_shape(self.shape, finalNdim))

 def sort(self, axis=-1, kind='quicksort', order=None):
  """ like numpy.sort, this sorts in place and returns None. """
  temp = self.as_numpy_array()
  temp.sort(axis, kind, order)
  self[:] = temp

 def reshape(self, *newShape):
  if len(newShape)==1 and not type(newShape[0]) in _numberTypes: newShape = tuple(newShape[0])
  if not _all2_(newShape, _isNumber): raise TypeError('the parameters to reshape don\'t look like a valid shape')
  if -1 in newShape:
   if _prodT(newShape)==0: raise ValueError("-1 as a parameter to reshape is not allowed if one of the other parameters is zero.")
   newShape = _modifyT(newShape, operator.indexOf(newShape, -1), self.size//-_prodT(newShape))
  if _prodT(newShape) != self.size: raise ValueError('the total number of items cannot be changed in a reshape')
  return garray(self._base, newShape, self)

 def reshape_2d(self, n_dimensions_as_rows):
  """ reshapes to 2 axes. The first <n_dimensions_as_rows> axes of the array become the first axis of the returned value. The remaining ones form the second axis. """
  if n_dimensions_as_rows<0: n_dimensions_as_rows += self.ndim
  return self.reshape((_prodT(self.shape[:n_dimensions_as_rows]), _prodT(self.shape[n_dimensions_as_rows:])))

 @property
 def T(self):
  if self.ndim==2: # _base case
   if self.size==0: return self.reshape(tuple(reversed(self.shape))) # cudamat bug workaround
   if self.shape[1]>1e6: # cudamat bug workaround. with 2m columns it fails
    return concatenate([ self[:, i*10**6 : (i+1)*10**6].T for i in range((self.shape[1]+10**6-1)//10**6)])
   if self.shape[0]>1e6: # cudamat bug workaround. using concat is not an option, because that uses transpose.
    ret = empty(tuple(reversed(self.shape)))
    for i in range((self.shape[0]+10**6-1)//10**6):
     ret[:, i*10**6 : (i+1)*10**6] = self[i*10**6 : (i+1)*10**6].T
    return ret
   return garray(self._base_as_2d().transpose(_new_cm(tuple(reversed(self.shape)))), tuple(reversed(self.shape)), None)
  else: return self.transpose()

 def transpose_simple(self, nDimsToGroup):
  """ shifts the first <nDimsToGroup> axes to the end, and the remaining ones to the start. This returns a new array, not an alias. """
  if nDimsToGroup<0: nDimsToGroup += self.ndim
  return self.reshape_2d(nDimsToGroup).T.reshape(self.shape[nDimsToGroup:] + self.shape[:nDimsToGroup])

 def transpose(self, *axes):
  """ like numpy.transpose, except that this doesn't return an alias, but rather a new array. """
  # This is not really supported by cudamat, so it takes creativity. I handle a variety of cases differently.
  if len(axes)==1 and not type(axes[0]) in _numberTypes: axes = tuple(axes[0])
  if axes==_t0: axes = tuple(reversed(tuple(xrange(self.ndim))))
  if axes == tuple(xrange(self.ndim)): return self.copy()
  if tuple(sorted(axes)) != tuple(xrange(self.ndim)): raise ValueError("%s is not a valid argument to transpose() of an array of %d axes" % (axes, self.ndim))
  for i in range(self.ndim-1):
   if axes[i+1]==axes[i]+1: return (self. # see if the task can be simplified by collapsing some axes that are kept adjacent
    reshape(self.shape[:axes[i]] + (_prodT(self.shape[axes[i]:axes[i]+2]),) + self.shape[axes[i]+2:]).
    transpose((originalAxisI-(originalAxisI>axes[i])) for originalAxisI in _deleteT2(axes, i+1)).
    reshape(self.shape[axisI] for axisI in axes))
  if self.ndim==3 and hasattr(_cudamat, '_cudamat') and cudamatHas('transpose3') and self.size!=0:
   reorderingI = {(0, 2, 1): 0, (1, 0, 2): 1, (2, 1, 0): 2}[axes]
   ret = empty(tuple( self.shape[axisI] for axisI in axes))
   gridX, gridY = (self.size+511)//512, 1
   while gridX>65535: gridY*=2; gridX = (gridX+1)//2;
   _cudamat._cudamat.transpose3.restype = _ctypes.c_int
   assert 0==_cudamat._cudamat.transpose3(_ctInt(gridX), _ctInt(gridY), self._base.p_mat, ret._base.p_mat, _ctInt(self.shape[0]), _ctInt(self.shape[1]), _ctInt(self.shape[2]), _ctInt(reorderingI))
   return ret
  def shiftAxesRight(shiftN): return self.transpose_simple(-shiftN).transpose( (axisI+shiftN)%self.ndim for axisI in axes)
  for i in range(self.ndim-1): # see if the task can be simplified by rotating axes right by 1. if so, the loop before this one can simplify further
   if axes[i:i+2] == (self.ndim-1, 0): return shiftAxesRight(1)
  # no further simplifications can be done. we need to proceed with a loop over the first axis. First rotate the intended axis to position 0.
  if axes[0]!=0: return shiftAxesRight(-axes[0])
  ret = empty( self.shape[axisI] for axisI in axes)
  for i in range(self.shape[0]): ret[i] = self[i].transpose( x-1 for x in axes[1:])
  return ret

 def copy(self): return garray(self, copy=True)

 def diagflat(self, k=0):
  if self.ndim!=1: return self.ravel().diagflat(k)
  if k!=0: raise NotImplementedError('k!=0 for garray.diagflat')
  selfSize = self.size
  ret = zeros((selfSize, selfSize))
  ret.ravel()[:-1].reshape((selfSize-1, selfSize+1))[:, 0] = self[:-1]
  if selfSize!=0: ret.ravel()[-1] = self[-1]
  return ret

 def diagonal(self):
  if self.ndim==1: return self.diagflat()
  if self.ndim==2:
   if self.shape[0] > self.shape[1]: return self[:self.shape[1]].diagonal()
   if self.shape[1] > self.shape[0]: return self[:, :self.shape[0]].diagonal()
   return self.ravel()[::self.shape[0]+1]
  raise NotImplementedError('garray.diagonal for arrays with ndim other than 1 or 2.')
 def diag(self): return self.diagonal()



 # ------------------------------------------------------------------------------- elementwise type checking

 def all_real(self):
  """ returns True iff all array elements are regular floats, as opposed to inf's, -inf's, and NaN's.  """
  return (self*0).sum()==0

 def isinf(self):
  """ elementwise, checking for inf or -inf. """
  return 1 - self.isreal() - self.isnan()

 def isreal(self):
  """ elementwise, checking for real numbers. See also .all_real() """
  return (self<numpy.inf) * (self>-numpy.inf)

 def isnan(self):
  """ elementwise, checking for NaN's. """
  return (self>0) + (self<1) < .5

 def isnumber(self):
  """ elementwise, checking for anything other than NaN's """
  return (self>0) + (self<1) > .5



 # ------------------------------------------------------------------------------- external misc numerical

 def __abs__(self): return self._elementwise_unary(_cudamat.abs)
 def abs(self): return __builtin__.abs(self)
 def as_bool(self): return self!=0
 def exp(self): return self._elementwise_unary(_cudamat.exp)
 def log(self): return self._elementwise_unary(_cudamat.log)
 def log_1_plus_exp(self): return self._elementwise_unary(_cudamat.log_1_plus_exp)
 def logistic(self): return self._elementwise_unary(_cudamat.sigmoid)
 sigmoid = logistic
 def sign(self): return self._elementwise_unary(_cmType.sign)
 def sqrt(self): return self._elementwise_unary(_cudamat.sqrt)
 def tanh(self): return self._elementwise_unary(_cudamat.tanh)


 def sum(self, axis=None): return self._reduction__base('sum', axis)
 def max(self, axis=None): return self._reduction__base('max', axis)
 def mean(self, axis=None): return self.sum(axis) / ( self.size if axis==None else self.shape[axis])
 def argmax(self, axis=None): return numpy.argmax(self.asarray(), axis)
 def argmin(self, axis=None): return numpy.argmin(self.asarray(), axis)
 def min(self, axis=None): return -(-self).max(axis)
 def all(self, axis=None): return ( True if self.size==0 else (self.as_bool()).min())
 def any(self, axis=None): return ( False if self.size==0 else (self.as_bool()).max())

 def all2(self, axis=None): return 1-(1-self).any2(axis)  # optimized for when I'm sure that the content is boolean
 def any2(self, axis=None): return self.sum(axis) > 0  # optimized for when I'm sure that the content is boolean

 def rand(self, distribution = 'uniform'):
  """
  returns a new garray, of the same shape as self, filled with random numbers.
  <distribution> can be either 'uniform' or 'normal'.
  """
  return _rand__base(self.shape, distribution, False)

 def euclid_norm(self): return self._base.euclid_norm()

 dot = dot
 where = where
 nonzero = nonzero

 def __nonzero__(self): return self.size==1 and self.item()!=0


 # ------------------------------------------------------------------------------- operator overloads, numerical

 def __add__(self, other): return _check_number_types(self._broadcastable_op(as_garray_or_scalar(other), 'add'))
 def __mul__(self, other): return _check_number_types(self._broadcastable_op(as_garray_or_scalar(other), 'multiply'))
 def __or__(self, other): return (self.as_bool() + other.as_bool()).as_bool()
 def __and__(self, other): return self.as_bool() * other.as_bool()

 def __pow__(self, other, modulo=None):
  if modulo!=None: raise NotImplementedError('power with modulo')
  if type(other) in _numberTypes and other==2: return self*self # faster
  return self._broadcastable_op(as_garray_or_scalar(other), 'pow')


 # the following would be a lot simpler if I wouldn't have to deal with nans

 def __lt__(self, other): return _check_number_types(self._broadcastable_op(as_garray_or_scalar(other), 'less than'))

 def __gt__(self, other): return _check_number_types(self._broadcastable_op(as_garray_or_scalar(other), 'greater than'))

 def __le__(self, other): return self.isnumber() * as_garray(other).isnumber() * (1-(self>other))

 def __ge__(self, other): return self.isnumber() * as_garray(other).isnumber() * (1-(self<other))

 def __ne__(self, other): return ( 1-(self==other) if type(other) in _castableTypes else True)

 def __eq__(self, other): return ( (self<=other) * (self>=other) if type(other) in _castableTypes else False)

 def eq2(self, other):
  """
  Returns a boolean: True if self and other are the same (arrays with the same shape and contents); False otherwise.
  This is what == does on most Python objects (on arrays it's been strangely overloaded though).
  garrays compare equal to numpy arrays with the same contents, even if the data types differ.
  """
  if self is other: return True
  if not is_array(other): return False
  if self.shape != other.shape: return False
  return all(self==other)==1

 def __sub__(self, other):
  if isinstance(other, garray) and other.shape==self.shape: # use specialized method
   return self._new(self._base_as_row().subtract(other._base_as_row(), self._new_cm()))
  else: return self + -as_garray(other) # if i need to broadcast, making use of the row add and col add methods is probably faster

 def __div__(self, other):
  if type(other) in _numberTypes: return self * (1./other)
  other = as_garray(other)
  return self * other._new(other._base_as_row().reciprocal(other._new_cm()))

 def __rmul__(self, other): return self*other
 def __radd__(self, other): return self+other
 def __rsub__(self, other): return other + -self
 def __rdiv__(self, other): return as_garray(other) / self
 def __rpow__(self, other): raise NotImplementedError('a**b where only b is a garray')

 def __pos__(self): return self
 def __neg__(self): return self*-1

 def __iadd__(self, other): self[_t0] = self+other; return self # not as direct as it might have been, but the effect is the same. "self[:]" doesn't work for 0das.
 def __imul__(self, other): self[_t0] = self*other; return self
 def __isub__(self, other): self[_t0] = self-other; return self
 def __idiv__(self, other): self[_t0] = self/other; return self
 def __imod__(self, other): self[_t0] = self%other; return self
 def __ipow__(self, other, modulo=None): self[_t0] = self.__pow__(other, modulo); return self



 # ------------------------------------------------------------------------------- operator overloads, non-numerical

 def __len__(self):
  if self.ndim==0: raise TypeError('len() of unsized object')
  return self.shape[0]

 def __getitem__(self, selectors):
  selectors = _nonSeqAsS(selectors)
  for i,sel in enumerate(selectors): # deal with newaxis and ellipsis
   if sel is Ellipsis: return self[selectors[:i] + (slice(None),)* (self.ndim - (__builtin__.sum( x != None for x in selectors)-1)) + selectors[i+1:]] # sel==Ellipsis is bad when sel is an array
   if sel is newaxis: return self.reshape(_insertT(self.shape, i, (1,)))[_modifyT(selectors, i, slice(None))]
  if len(selectors) > self.ndim: raise IndexError('more indices than axes')
  if _all2_(selectors, _isFullSlice): return self
  if reduce(operator.and_, ( _isSequence(sel) or is_array(sel) for sel in selectors), True) and len(selectors)>=2:
   selectors = tuple(map(as_garray, selectors))
   if reduce(operator.or_, ( (sel < 0).sum() > 0 for sel in selectors), False): raise NotImplementedError('negative indices in index arrays, combined with having multiple indices arrays')
   # ravel the first two dimensions into one, and translate the corresponding indices arrays into one accordingly
   return self.reshape((self.shape[0]*self.shape[1],) + self.shape[2:])[(selectors[0]*self.shape[1]+selectors[1],) + selectors[2:]]
  if __builtin__.sum( _isSequence(sel) or is_array(sel) for sel in selectors)>1:
   raise NotImplementedError('slicing with more than one sequence/array among the indices, with also other kinds of values among the indices')
  # handle the operations on different axes one by one; earlier axes are handled earlier
  axisI = ( i for i, x in enumerate(selectors) if not _isFullSlice(x)).next()
  axisLen = self.shape[axisI]
  axisSelector = selectors[axisI]
  if not _all2_(selectors[axisI+1:], _isFullSlice): return self[selectors[:axisI+1]][(slice(None),)*(axisI+(not type(axisSelector) in _numberTypes)) + selectors[axisI+1:]] # first select on axisI only; then do the further axes.
  # from here, axisI is the only axis on which we don't take a full slice
  if type(axisSelector) == types.SliceType and axisSelector.step not in (1, None): axisSelector = numpy.arange(axisLen)[axisSelector]
  if type(axisSelector) in _numberTypes: # selecting a single location on axisI, and thus reducing the dimensionality by 1
   ret = self[selectors[:axisI] + (_short_slice(_read_single_index(axisSelector, axisLen)),)]  .reshape(_deleteT2(self.shape, axisI))
   return ( ret.item() if ret.shape==_t0 else ret) # exception, to have the same behavior as numpy
  if _isSequence(axisSelector) or type(axisSelector) == numpy.ndarray: axisSelector = garray(axisSelector)
  if isinstance(axisSelector, garray):
   # a 1d index means re-arranging this axis. I.e. a number of length 1 selections on this axis, concatenated on this axis.
   # other dimensionality means using the raveled version, and then reshaping to reflect the selector dimensionality
   if hasattr(_cmType, 'select_columns'):
    if axisI==0:
     if _doExpensiveCheck() and (axisSelector> len(self)-.01).sum() !=0: raise IndexError('index %d (found in an indices array) is too large, for an axis of length %d' % (max(axisSelector), len(self)))
     if _doExpensiveCheck() and (axisSelector<-len(self)-.5).sum() !=0: raise IndexError('index %d (found in an indices array) is too small, for an axis of length %d' % (min(axisSelector), len(self)))
     return garray(self._base_shaped(1).select_columns(axisSelector._base_shaped(axisSelector.ndim), _new_cm((axisSelector.size, self.size/self.shape[0]))), axisSelector.shape + self.shape[1:], None)
    else: return self.transpose_simple(axisI)[axisSelector].transpose_simple(-axisI)
   else: return (concatenate(tuple( self[_modifyT(selectors, axisI, slice(choiceOnThisAxis, choiceOnThisAxis+1))] for choiceOnThisAxis in axisSelector.ravel()), axisI)
                 .reshape(self.shape[:axisI] + axisSelector.shape + self.shape[axisI+1:]))
  if not type(axisSelector) == types.SliceType: raise ValueError('index not understood: %s' % axisSelector)
  # from here, selector is a simple slice
  sFrom, sTo, sLen = _read_simple_slice(axisSelector, axisLen)
  retShape = _modifyT(self.shape, axisI, sLen)
  if _prodT(retShape)==0: return zeros(retShape)
  if axisI==0: return garray(_cm_row_slice_read(self._base_shaped(1), sFrom, sTo), retShape, self) # slice on axis 0 is free, using _cm_row_slice_read
  if axisI!=1: return self.reshape((_prodT(self.shape[:axisI]),) + self.shape[axisI:])[:, sFrom:sTo].reshape(retShape) # redirect: collapse earlier axes into one
  if self.ndim != 2: return self.reshape_2d(1)[:, sFrom * _prodT(self.shape[axisI+1:]) : sTo * _prodT(self.shape[axisI+1:])].reshape(retShape) # redirect: use long elements
  chunkSize = int(2e6)
  nChunks = (len(self) + chunkSize - 1) // chunkSize
  if nChunks>1: return concatenate( tuple(self[chunkI*chunkSize : (chunkI+1)*chunkSize, sFrom:sTo] for chunkI in range(nChunks)), 0) # redirect in batches, bc cudamat chokes on big jobs, i.e. jobs with many rows
  if self.shape[0]==1: # then redo as row slice. This also avoids a cudamat limitation (on slicing many columns), sometimes.
   return self.ravel()[sFrom:sTo][newaxis].copy()
  # _base case for column slice
  retCm = _new_cm(retShape)
  _cm_col_slice_read(self._base_shaped(1), sFrom, sTo, retCm)
  return garray(retCm, retShape, None)

 def __iter__(self):
  for i in tuple(xrange(len(self))): yield self[i]

 def __setitem__(self, selectors, other):
  # this is different from getitem. There, I can handle the axes one at a time. Here, it's more integrated.
  selectors = _nonSeqAsS(selectors)
  for i,sel in enumerate(selectors): # deal with ellipsis
   if sel is Ellipsis: return self.__setitem__(selectors[:i] + (slice(None),)* (self.ndim - (len(selectors)-1)) + selectors[i+1:], other) # sel==Ellipsis is bad when sel is an array
  if len(selectors) > self.ndim: raise IndexError('more indices than axes')
  if reduce(operator.and_, ( is_array(sel) or _isSequence(sel) for sel in selectors), True) and selectors!=_t0:
   if len(selectors)==1:
    if not hasattr(_cmType, 'set_selected_columns'):
     raise NotImplementedError("slice assign with a sequence/array as index. Get the newest version of cudamat (or npmat if you're running on the cpu).")
    sel = as_garray(selectors[0])
    if len(sel) != len(other): raise ValueError('number of rows to set != number of provided rows')
    if other.shape[1:] != self.shape[1:]: raise ValueError('shape mismatch in assignment')
    if sel.ndim!=1: raise NotImplementedError('assignment with as index an array of ndim!=1')
    if sel.size==0: return # the current implementation of set_selected_columns doesn't handle that well
    self._base_shaped(1).set_selected_columns(sel._base_shaped(1), other._base_shaped(1))
   else: # >1 selectors, all arrays/sequences. ravel the first dimension of self, and correspondingly unify the first two selectors
    self.reshape((_prodT(self.shape[:2]),) + self.shape[2:])[(as_garray(selectors[0])*self.shape[1]+as_garray(selectors[1]),) + selectors[2:]] = as_garray(other)
   return
  if reduce(operator.or_, ( _isSequence(axisSel) or is_array(axisSel) for axisSel in selectors), False): raise NotImplementedError('slice assign with a sequence/array as index, as well as other indexing objects')
  if reduce(operator.or_, ( type(axisSel) == types.SliceType and axisSel.step not in (1, None) for axisSel in selectors), False): raise NotImplementedError('slice assign with stride != 1')
  if not reduce(operator.and_, ( type(axisSel) in _numberTypes or type(axisSel) == types.SliceType for axisSel in selectors), True): raise ValueError('index not understood, in slice assignment.')
  selectors = selectors + (slice(None),)*(self.ndim-len(selectors))
  # now len(selectors) == ndim, and all selectors are single indices or simple slices
  # task: broadcast other, and do shape check.
  other = as_garray_or_scalar(other)
  assignedShape = tuple( _read_simple_slice(axisSel, self.shape[axisI])[2] for axisI, axisSel in enumerate(selectors) if not type(axisSel) in _numberTypes)
  if isinstance(other, garray):
   if other.ndim < len(assignedShape): other = other._add_axes(len(assignedShape))
   if other.ndim > len(assignedShape):
    if _prodT(other.shape[: other.ndim-len(assignedShape)]) != 1: raise ValueError('Incompatible shapes in slice assign: the assigned area has shape %s, and the incoming values have shape %s.' % (assignedShape, other.shape))
    other = other.reshape(other.shape[-len(assignedShape):])
   # now other.ndim == len(assignedShape)
   if not reduce(operator.and_, ( other.shape[axisNr] in (1, assignedShape[axisNr]) for axisNr in tuple(xrange(len(assignedShape)))), True):
    raise ValueError('Incompatible shapes in slice assign: the incoming values have shape %s, but the assigned area has shape %s.' % (other.shape, assignedShape))
   other = other._tile_to_broadcast(assignedShape)
  # the only time I can use scalar assign is when I don't need cudamat's column assign at all. that only happens when all selectors other than optionally the first are full slices.
  if _all2_(selectors[1:], _isFullSlice):
   ( _cm_row_slice_read(self._base_shaped(1), _read_single_index(selectors[0], self.shape[0]), _read_single_index(selectors[0], self.shape[0])+1)
     if self.ndim==1 and type(selectors[0]) in _numberTypes else
     self[selectors[:1]]._base_as_row() # I want this to work even when selectors = _t0
     ).assign( other if type(other) in _numberTypes else other._base_as_row())
   return
  if type(other) in _numberTypes: other = garray(other)._add_axes(len(assignedShape))._tile_to_broadcast(assignedShape)
  # now other is a garray of exactly the expected shape, and there are things other than complete slices beyond axis #0 so I'm going to need a col assign.
  # task: get rid of single indices in selectors
  for i in range(self.ndim):
   if type(selectors[i]) in _numberTypes:
    selectors = _modifyT(selectors, i, _short_slice(_read_single_index(selectors[i], self.shape[i])))
    other = other.reshape(_insertT(other.shape, i, (1,)))
  if not _isFullSlice(selectors[0]): return self[selectors[0]].__setitem__((slice(None),) + selectors[1:], other)
  # now all selectors are either full or simple slices; axis 0 is a full slice; and at least one other axis is a simple slice.
  axisI = ( i for i, x in enumerate(tuple( not _isFullSlice(sel) for sel in selectors)) if x).next()
  if _all2_(selectors[axisI+1:], _isFullSlice): # then do a column slice assign directly using cudamat.
   sFrom, sTo = _read_simple_slice(selectors[axisI], self.shape[axisI])[:2]
   elementWidth = _prodT(self.shape[axisI+1:])
   if other.size!=0: # cudamat chokes on that
    _cm_col_slice_write(self._base_shaped(axisI), sFrom*elementWidth, sTo*elementWidth, other._base_shaped(axisI))
   return
  # remaining case: there are multiple non-full slices, and the slice on axis 0 is full. strategy: transpose to bring one of those non-full slices to the front.
  selfT = self.transpose_simple(axisI)
  selfT[selectors[axisI:] + selectors[:axisI]] = other.transpose_simple(axisI)
  self._base_as_row().assign(selfT.transpose_simple(self.ndim-axisI)._base_as_row())



 # ------------------------------------------------------------------------------- external, but not for user to see

 def __getstate__(self):
  return (self.shape, self._base_as_row().asarray())

 def __setstate__(self, state):
  garray.__init__(self, state[1])
  self._set_shape_info(state[0])

 def __array__(self, *dtype):
  _envInstruction = _os.environ.get('GNUMPY_IMPLICIT_CONVERSION', 'refuse')
  assert _envInstruction in ('allow', 'warn', 'refuse'), "environment variable GNUMPY_IMPLICIT_CONVERSION, if present, should be one of 'allow', 'warn', 'refuse'."
  if _envInstruction=='refuse': raise TypeError("garray objects cannot be quietly converted to numpy arrays, because the environment variable GNUMPY_IMPLICIT_CONVERSION is set to 'refuse', or is not set at all (the default is 'refuse'). Set that variable to 'allow' or 'warn' if you wish to allow quiet conversion. garray's can always be explicitly converted using the .as_numpy_array() method.")
  if _envInstruction=='warn': print "gnumpy: warning: a garray object is being quietly converted to a numpy array, and the environment variable GNUMPY_IMPLICIT_CONVERSION is set to 'warn'. garray objects can be explicitly converted using the .as_numpy_array() method."
  return self.as_numpy_array().__array__(*dtype)

 def __repr__(self): return self.as_numpy_array().__repr__().replace('array(', 'garray(').replace('\n', '\n ').replace(', dtype=float32', '').replace(', dtype=float64', '') # 64 happens for empty arrays

 def __del__(self):
  if not hasattr(self, '_is_alias_of'):
   if _isTijmen: print 'gnumpy cleaning up an unfinished garray. mem counting may be off now.'
   return # this object was never finished, because an exception (error or interrupt) occurred in the constructor. This check avoids error messages.
  if self._is_alias_of is None:
   # this is not true in one case: if a reference to self._base is stored somewhere explicitly (somewhere outside self but not in another garray). This happens internally sometimes. I saw it happening on the last line of setitem: a transpose is created (transposes own their mem, are not aliases), and then it's dropped but _base (obtained by _base_as_row) is still in use for a cm assign call. assert _sys.getrefcount(self._base)==2, _sys.getrefcount(self._base)
   _cmsForReuse[self.size].append(self._base)
   if track_memory_usage: _memoryUsers[self.allocating_line] = (_memoryUsers[self.allocating_line][0]-1, _memoryUsers[self.allocating_line][1]-self.size*4)
  else:
   assert type(self._is_alias_of).__name__ == 'garray', '_is_alias_of is of unexpected type, of which the str() is: "%s"' % str(type(self._is_alias_of))
   # del self._base # this is only to make the refcount assert not fail




_castableTypes = _numberTypes | set([tuple, list, numpy.array, garray])


########NEW FILE########
__FILENAME__ = npmat


import os, pdb, time, warnings
import numpy as np

__DTYPE__ = np.float64


def dummy():
    return CUDAMatrix(np.zeros((1, 1)))

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used."""

    def newFunc(*args, **kwargs):
        warnings.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning)
        return func(*args, **kwargs)
    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

#from cudamat import CUDAMatException
class CUDAMatException(Exception):
    pass



IncompatibleDimensionsException = CUDAMatException("Incompatible matrix dimensions.")

InvalidConfig = CUDAMatException("Invalid Configuration Error (i.e., a dim of the array must be smaller than 2**16.")
## TODO: Figure out which functions produce an invalid config error. These are those who allocate a thread per col/row/elem.
## Those who allocate a bunch of rows per thread, like mult, add, sub, etc, should be immune to the invalid
## configuration error. PS: this error occurs on the real cudamat, which is why it happens.
## Sum/Max/Cumsum
MAX_DIM = 2**16


class CUDAMatrix(object):
    """
    A CUDAMatrix object represents a matrix of single precision floating point
    numbers on a GPU.
    """

    def __init__(self, array, ref=True):
        if ref:
            self.numpy_array = reformat(array)
        else:
            self.numpy_array = array
        assert self.numpy_array.ndim == 2
        self.trans = False

    def __del__(self):
        pass

    @staticmethod
    def init_random(seed):
        import numpy.random as random
        random.seed(seed)



    @property
    def num_elems(self):
        return self.numpy_array.size

    @property
    def shape(self):
        return self.numpy_array.shape

    def cheap_transpose(self):
        return CUDAMatrix(self.reshape((self.shape[1], self.shape[0])))

    def reshape(self, shape):
        assert shape[0]*shape[1] == self.shape[0]*self.shape[1]
        #self.numpy_array.resize(shape)
        #self.numpy_array = self.numpy_array.reshape(shape, order='F')
        self.numpy_array.resize(*shape)
        return self


    def copy(self):
        return empty().assign(self)


    def set_np_array(self, X):
        assert X.shape == self.shape
        self.numpy_array[:] = X
        self.copy_to_device()
        return self



    def zero_copy(self):
        return self.copy().assign(0)


    def resize(self, shape):

        if self.shape != shape:

            print 'CUDAMatrix: resize (%s -> %s)' % (self.shape, shape)
            #self.numpy_array = np.resize(self.numpy_array, shape).astype(__DTYPE__)
            self.numpy_array.resize(shape)
            self.numpy_array[:] = 0


        return self

    @property
    def T(self):
        return CUDAMatrix(self.numpy_array.T)

    @property
    def mat(self):
        return self.numpy_array


    @deprecated
    def set_shape(self, shape):
        return self.resize(shape)


    def asarray(self):
        """
        Copies the matrix to an ndarray on the CPU and returns it.
        """

        #return reformat(self.numpy_array.copy())
        return self.numpy_array

    def copy_to_device(self):
        """
        Copy the matrix to the GPU.
        """

        pass



    def select_columns(self, indices, target):
        """
        copies some columns of self into target.
        <indices> must be a row vector. Its elements are float32's representing integers, e.g. "34.0" means the integer "34".
        after this call, for all r,c, target[r,c]=self[r,indices[c]].
        This returns target.
        Negative indices are interpreted in the usual Python way: all elements of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
        This does bounds checking, but out of bounds indices do not raise an exception (because the programmer was lazy). Instead, they result in NaN values in <target>.
        """

        assert target.shape[0]==self.shape[0]
        assert indices.shape[0]==1
        assert indices.shape[1] == target.shape[1]

        for c in range(target.shape[1]):
            try:
                target.numpy_array[:,c] = self.numpy_array[:, int(indices.numpy_array.ravel()[c])]
            except IndexError:
                target.numpy_array[:,c] = np.nan
        return target

    def set_selected_columns(self, indices, source):
        """
        copies all columns of source into some columns of self.
        <indices> must be a row vector. Its elements are float32's representing
        integers, e.g. "34.0" means the integer "34". after this call, for all
        r,c, self[r,indices[c]]=source[r,c]. This returns self.
        Negative indices are interpreted in the usual Python way: all elements
        of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
        This does bounds checking, but out of bounds indices do not raise an
        exception (because the programmer was lazy). Instead, they result in NaN
        values in <self>.
        """

        assert self.shape[0]==source.shape[0]
        assert indices.shape[0]==1
        assert indices.shape[1]==source.shape[1]

        for c in range(source.shape[1]):
            try:
                self.numpy_array[:,int(indices.numpy_array.ravel()[c])] = source.numpy_array[:,c]
            except IndexError:
                self.numpy_array[:,int(indices.numpy_array.ravel()[c])] = np.nan
        return self


    def copy_to_host(self):
        """
        Copy the matrix to the CPU.
        """
        return self.asarray()


    def np(self):
        return self.copy_to_host()




    def assign(self, val):
        """Assign val to self, where val can be a scalar or a CUDAMatrix
        with the same dimensions as self. """


        if isinstance(val, CUDAMatrix):
            self.resize(val.shape)
            self.numpy_array[:] = val.numpy_array


        elif isinstance(val, (int, float, __DTYPE__)):
            self.numpy_array[:] = val

        return self

    def free_device_memory(self):
        """
        Free memory used up by the matrix on the GPU.
        """
        pass


    def set_trans(self, is_trans):
        """
        Set the transposedness flag to is_trans.
        """
        if is_trans is True:
            self.numpy_array = self.numpy_array.T



    def slice(self, first_col, last_col):
        return CUDAMatrix(self.numpy_array[:, first_col:last_col], ref=False)

    def get_row_slice(self, start, end, target = None):
        """
        Get the rows with indices start through end. If target is not provided
        memory for a new matrix will be allocated.
        """



        ans = CUDAMatrix(self.numpy_array[start:end, :].copy())

        if target is not None:
            target.assign(ans)
        else:
            target = ans

        return target


    def set_row_slice(self, start, end, mat):
        try:
            self.numpy_array[start:end] = mat.numpy_array
        except ValueError:
            raise IncompatibleDimensionsException
        return self


    def get_col_slice(self, start, end, target = None):
        ## NOTE: no .copy()
        ans = self.slice(start, end)

        if target is not None:
            target.assign(ans)
        else:
            target = ans

        return target

    def set_col_slice(self, start, end, mat):
        return self.slice(start, end).assign(mat)





    # def select_columns(self, indices, target):
    #     """
    #     Copies selected columns into a target matrix.
    #     <self>, <indices>, and <target> are all cudamat matrices.
    #     <self> is an M by K matrix.
    #     <indices> is of shape 1 by N. All elements x are expected to be
    #     0<=x<K, and are expected to have nothing after the decimal point (i.e.
    #     to be floats representing integers).
    #     <target> is an M by N matrix that will be filled with the result.
    #     After the operation, for all i,j, target[i, j] = self[i, int(indices[j])]
    #     This returns <target>.
    #     ? idea: No bounds checking is done.
    #     """
    #     M, K = self.shape

    #     one, N = indices.shape
    #     assert one == 1
    #     M_, N_ = target.shape
    #     assert M_ == M and N == N_

    #     np_ints = indices.numpy_array.astype(int)

    #     if not (np_ints.max() < K and np_ints.min() >= 0):
    #         raise ValueError("Index out of bounds.")


    #     target.numpy_array[:] = self.numpy_array[:, np_ints.flatten()]



    #     return target




    def transpose(self, target = None):

        if target is None:
            return CUDAMatrix(self.numpy_array.T.copy())
        else:
            target.numpy_array.resize((self.shape[1], self.shape[0]))
            target.numpy_array[:] = self.numpy_array.T

        return target


    def assign_transpose(self, t):
        return t.transpose(target = self)



    def fill_with_rand(self):
        """
        Fill matrix on the GPU with random numbers drawn from the uniform
        distribution over the (0,1) interval.
        """
        self.numpy_array[:] = np.random.rand(*self.shape)

        return self





    def fill_with_randn(self):
        """
        Fill matrix on the GPU with random numbers drawn from the standard normal
        distribution.
        """

        self.numpy_array[:] = np.random.randn(*self.shape)

        return self



    def add_col_vec(self, vec, target = None):
        """
        Add vector vec to every column of the matrix. If a target is provided,
        it is used to store the result instead of self.
        """

        a, b = self.shape
        a_, b_ = vec.shape

        if not (b_ == 1 and a_ == a):
            raise IncompatibleDimensionsException


        if target is None:
            target = self

        target.resize(self.shape)

        target.numpy_array[:] = self.numpy_array + vec.numpy_array

        return target

    def assign_add_col_vec(self, a, b):
        return a.add_col_vec(b, target = self)



    def add_col_mult(self, vec, mult, target = None):
        """
        Add a multiple of vector vec to every column of the matrix. If a target
        is provided, it is used to store the result instead of self.
        """

        a, b = self.shape
        a_, b_ = vec.shape

        if not (b_ == 1 and a_ == a):
            raise IncompatibleDimensionsException


        if target is None:
            target = self

        target.resize(self.shape)

        target.numpy_array[:] = self.numpy_array + vec.numpy_array * mult

        return target





    def assign_add_col_mult(self, a, m, b):
        return a.add_col_vec(b, m, target = self)



    def add_row_vec(self, vec, target = None):
        """
        Add vector vec to every row of the matrix. If a target is provided,
        it is used to store the result instead of self.
        """

        a, b = self.shape
        a_, b_ = vec.shape

        if not (a_ == 1 and b_ == b):
            raise IncompatibleDimensionsException


        if target is None:
            target = self

        target.resize(self.shape)

        target.numpy_array[:] = vec.numpy_array + self.numpy_array

        return target



    def assign_add_row_vec(self, a, b):
        return a.add_row_vec(b, target = self)



    def mult_by_col(self, vec, target = None):
        """
        Multiply vector vec into every column of the matrix. If a target is
        provided, it is used to store the result instead of self.
        """


        a, b = self.shape
        a_, b_ = vec.shape

        if not (b_ == 1 and a_ == a):
            raise IncompatibleDimensionsException

        if target is None:
            target = self

        target.resize(self.shape)


        target.numpy_array[:] = vec.numpy_array * self.numpy_array


        return target



    def mult_by_row(self, vec, target = None):
        """
        Multiply vector vec into every row of the matrix. If a target is
        provided, it is used to store the result instead of self.
        """

        a, b = self.shape
        a_, b_ = vec.shape

        if not (b_ == b and a_ == 1):
            raise IncompatibleDimensionsException

        if target is None:
            target = self

        target.resize(self.shape)


        target.numpy_array[:] = vec.numpy_array * self.numpy_array

        return target





    def sum(self, axis, target = None):
        """
        Sum the matrix along the given dimension, where 0 represents the leading
        dimension and 1 represents the non-leading dimension. If a target is
        not prvided, a new vector is created for storing the result.
        """



        if axis == 0:
            ans = self.numpy_array.sum(0)[np.newaxis, :]
        elif axis == 1:
            ans = self.numpy_array.sum(1)[:, np.newaxis]
        else:
            raise ValueError("axis must be only 0 or 1; instead, got %s\n", axis)

        ans = CUDAMatrix(ans)

        if target is not None:
            target.assign(ans)
        else:
            target = ans
        return target


    def mean(self, axis, target = None):




        if axis == 0:
            ans = self.numpy_array.mean(0)[np.newaxis, :]
        elif axis == 1:
            ans = self.numpy_array.mean(1)[:, np.newaxis]
        else:
            raise ValueError("axis must be only 0 or 1; instead, got %s\n", axis)

        ans = CUDAMatrix(ans)

        if target is not None:
            target.assign(ans)
        else:
            target = ans
        return target





    def assign_sum(self, mat, axis):
        return mat.sum(axis, target = self)

    def assign_mean(self, mat, axis):
        return mat.mean(axis, target = self)



    def add_sums(self, mat, axis, mult = 1.):
        """
        Add a multiple of the sums of the matrix mat along the given dimension
        to self.
        """



        if self.numpy_array.shape != self.mat.shape:
            raise IncompatibleDimensionsException

        sum = mat.sum(axis)

        sum.numpy_array *= mult

        if axis == 0:
            self.add_row_vec(sum)
        elif axis == 1:
            self.add_col_vec(sum)

        return self


    def less_than(self, val, target = None):
        """
        Perform the operation target = 1. * (self < val), where val can be a matrix or a scalar.
        """


        if target is None:
            target = self

        target.resize(self.shape)

        if isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array < val

        else:
            if val.shape != self.shape:
                raise IncompatibleDimensionsException


            target.numpy_array[:] = (self.numpy_array < val.numpy_array).astype(__DTYPE__)

        return target

    def assign_less_than(self, mat, val):
        return mat.less_than(val, self)




    def greater_than(self, val, target = None):
        """
        Perform the operation target = 1. * (self > val), where val can be a matrix or a scalar.
        """


        if target is None:
            target = self

        target.resize(self.shape)

        if isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = (self.numpy_array > val).astype(__DTYPE__)
        else:
            if val.shape != self.shape:
                raise IncompatibleDimensionsException


            target.numpy_array[:] = (self.numpy_array > val.numpy_array).astype(__DTYPE__)

        return target


    def assign_greater_than(self, mat, val):
        return mat.greater_than(val, self)




    def max(self, axis, target = None, transpose_aux=None):
        """
        Find the maximum value along the given dimension, where 0 represents the
        leading dimension and 1 represents the non-leading dimension. If a target
        is not prvided, a new vector is created for storing the result.
        """



        m, n = self.shape

        if axis == 0:
            if target is None:
                target = empty((1, n))

            target.resize((1, n))


            target.numpy_array[:] = self.numpy_array.max(0)



        elif axis == 1:
            # IN theory: we are supposed to do this:

#             if not target:
#                 #target = CUDAMatrix(np.empty((m, 1), dtype=np.float32, order = 'F'))
#                 target = empty((m, 1))
#             else:
#                 target.resize((m, 1))



#             err_code =  _cudamat.max_by_axis(self.p_mat, target.p_mat, ct.c_int(axis))
#             if err_code:
#                 raise generate_exception(err_code)

            assert transpose_aux != None

            self.transpose(target = transpose_aux)

            target.reshape(target.shape[::-1])

            transpose_aux.max(axis = 0, target = target)

            target.reshape(target.shape[::-1])




        return target

    def assign_max(self, mat, axis, transpose_aux=None):
        return mat.max(axis, target = self, transpose_aux = transpose_aux)

    def total_max(self):
        row_maxes = empty((1, 1)).assign_max(self, axis = 0)
        return row_maxes.reshape((row_maxes.shape[1], row_maxes.shape[0])).max(axis = 0).asarray()[0,0]

    def total_sum(self):
        return self.numpy_array.sum()


    def sign(self, target = None):

        if target is None:
            target = empty(self.shape)

        target.resize(self.shape)

        target.numpy_array[:] = np.sign(self.numpy_array)

        return target


    def assign_sign(self, a):
        return a.sign(target = self)


    def apply_sigmoid(self, target = None):
        """
        Apply the logistic sigmoid to each element of the matrix.
        """

        return sigmoid(self, target)

    def sigmoid(self, target = None):
        """
        Apply the logistic sigmoid to each element of the matrix.
        """

        return sigmoid(self, target)


    def assign_sigmoid(self, t):
        return sigmoid(t, self)


    def log(self, target = None):
        return log(self, target)

    def assign_log(self, t):
        return log(t, self)

    def exp(self, target = None):
        return exp(self, target)

    def assign_exp(self, t):
        return exp(t, self)

    def pow(self, p, target = None):
        return pow(self, p, target)

    def assign_pow(self, mat, p):
        return pow(mat, p, self)


    def sqrt(self, target = None):
        return sqrt(self, target)


    def assign_sqrt(self, mat):
        return sqrt(mat, self)


    def reciprocal(self, target = None):
        """
        Find the reciprocal of each element of the matrix.
        """

        if not target:
            target = self

        target.resize(self.shape)


        target.numpy_array[:] = 1./self.numpy_array[:]

        return target

    def assign_reciprocal(self, mat):
        return mat.reciprocal(target = self)



    def dot(self, mat2, target = None):
        """
        Multiply the matrix by mat2 from the right.
        """

        return dot(self, mat2, target)


    def assign_dot(self, m1, m2):
        m1.dot(m2, target = self)
        return self


    def add_dot(self, m1, m2):
        """
        Add the dot product of m1 and m2 to the matrix.
        """


        m3 = dot(m1, m2)

        if m3.shape != self.shape:
            raise IncompatibleDimensionsException

        self.numpy_array += m3.numpy_array


        return self

    def subtract_dot(self, m1, m2):
        """
        Subtract the dot product of m1 and m2 from the matrix.
        """



        m3 = dot(m1, m2)

        if m3.shape != self.shape:
            raise IncompatibleDimensionsException

        self.numpy_array -= m3.numpy_array


        return self


    def add_mult(self, mat2, alpha = 1.):
        """
        Add multiple of mat2 to the matrix.
        """

        if mat2.shape != self.shape:
            raise IncompatibleDimensionsException

        self.numpy_array += mat2.numpy_array * alpha

        return self

    def assign_mult(self, mat2, alpha):
        self.resize(mat2.shape)
        self.assign(0)
        self.add_mult(mat2, alpha)
        return self


    def subtract_mult(self, mat2, alpha = 1.):
        """
        Subtract a multiple of mat2 from the matrix.
        """

        if mat2.shape != self.shape:
            raise IncompatibleDimensionsException

        self.numpy_array -= mat2.numpy_array * alpha

        return self


    def add(self, val, target = None):
        """Add val to self, where val can be a scalar or a CUDAMatrix with the
        same dimensions as self. """

        if not target:
            target = self

        target.resize(self.shape)




        if isinstance(val, CUDAMatrix):
            if target.shape != val.shape:
                raise IncompatibleDimensionsException
            target.numpy_array[:] = self.numpy_array + val.numpy_array

        elif isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array + val
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."



        return target

    def assign_add(self, a, b):
        a.add(b, target = self)
        return self



    def subtract(self, val, target = None):
        """Subtract val from self, where val can be a scalar or a CUDAMatrix with
        the same dimensions as self. """

        if not target:
            target = self

        target.resize(self.shape)



        if isinstance(val, CUDAMatrix):
            if target.shape != val.shape:
                raise IncompatibleDimensionsException
            target.numpy_array[:] = self.numpy_array - val.numpy_array

        elif isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array - val
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."



        return target



    def assign_subtract(self, a, b):
        a.subtract(b, target = self)
        return self




    def divide(self, val, target = None):
        """Divide self by val, where val can be a scalar or a CUDAMatrix with the
        same dimensions as self. """

        if not target:
            target = self

        target.resize(self.shape)


        if isinstance(val, CUDAMatrix):
            if target.shape != val.shape:
                raise IncompatibleDimensionsException
            target.numpy_array[:] = self.numpy_array / val.numpy_array

        elif isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array / val
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."



        return target



    def assign_divide(self, a, b):
        a.divide(b, target = self)
        return self



    def mult(self, val, target = None):
        """Multiply self by val, where val can be a scalar or a CUDAMatrix with
        the same dimensions as self. """

        if not target:
            target = self

        target.resize(self.shape)


        if isinstance(val, CUDAMatrix):
            if target.shape != val.shape:
                raise IncompatibleDimensionsException
            target.numpy_array[:] = self.numpy_array * val.numpy_array

        elif isinstance(val, (int, float, __DTYPE__)):
            target.numpy_array[:] = self.numpy_array * val
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."



        return target





    def assign_mult(self, a, b):
        a.mult(b, target = self)
        return self




    @deprecated
    def assign_scalar(self, alpha):
        """
        Assign scalar alpha to every element of the matrix.
        """
        self.assign(alpha)
        return self

    @deprecated
    def mult_by_scalar(self, alpha, target = None):
        """
        Multiply the matrix by a scalar.
        """
        return self.mult(alpha, target)




    @deprecated
    def div_by_scalar(self, alpha, target = None):
        """
        Divide the matrix by a scalar.
        """

        return self.divide(alpha, target)



    @deprecated
    def add_scalar(self, alpha, target = None):
        """
        Increment the matrix by a scalar.
        """
        return self.add(alpha, target)


    def euclid_norm(self):
        return np.sqrt((self.numpy_array**2).sum())


def empty(shape=None):
    """
    Creates and returns a new CUDAMatrix with the given shape.
    """

    if shape is None:
        shape = (1, 1)

    return CUDAMatrix(np.empty(shape))


def zeros(shape):
    return empty(shape).assign(0)

def randn(a, b):
    ans = empty((a, b)).fill_with_randn()
    return ans



def sum(mat, axis, target = None):
    """
    Sum the matrix along the given dimension, where 0 represents the leading
    dimension and 1 represents the non-leading dimension. If a target is
    not prvided, a new vector is created for storing the result.
    """
    return mat.sum(axis, target)


def dot(m1, m2, target = None):
    """
    Find the dot product between m1 and m2.
    """

    m = m1.shape[0]
    n = m2.shape[1]

    target_shape = (m, n)
    if not target:
        target = empty(target_shape)

    target.resize(target_shape)

    try:
        target.numpy_array[:] = np.dot(m1.numpy_array, m2.numpy_array)
    except ValueError:
        raise IncompatibleDimensionsException

    return target

def vdot(m1, m2):
    assert m1.shape == m2.shape
    return (m1.asarray() * m2.asarray()).sum()



def sigmoid(mat, target = None):
    """
    Apply the logistic sigmoid to each element of the matrix mat.
    """


    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = 1. / (1 + np.exp(-mat.numpy_array))

    return target


def tanh(mat, target = None):
    """
    Apply the logistic sigmoid to each element of the matrix mat.
    """


    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = np.tanh(mat.numpy_array)

    return target


def gammaln(mat, target = None):



    if not target:
        target = mat

    target.resize(mat.shape)

    import scipy.special
    target.numpy_array[:] = scipy.special.gammaln(mat.numpy_array)

    return target





def abs(mat, target = None):
    """
    Apply the logistic sigmoid to each element of the matrix mat.
    """


    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = abs(mat.numpy_array)

    return target




def log_1_plus_exp(mat, target = None):
   """
   Apply log(1+exp(x)) to each element of the matrix mat.
   """
   if not target:
       target = mat
   mask = mat.numpy_array > 0
   target.numpy_array[mask] = mat.numpy_array[mask] + np.log(1+np.exp(-mat.numpy_array[mask]))
   mask = np.logical_not(mask)
   target.numpy_array[mask] = np.log(1+np.exp(mat.numpy_array[mask]))
   return target
log_1_sum_exp = log_1_plus_exp

def log(mat, target = None):
    """
    Find the natural logarithm of each element of the matrix mat.
    """

    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = np.log(mat.numpy_array)

    return target

def exp(mat, target = None):
    """
    Apply the exponential function to each element of the matrix mat.
    """

    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = np.exp(mat.numpy_array)

    return target


    if not target:
        target = mat

    target.resize(mat.shape)

    return target


def sqrt(mat, target = None):
    """
    Compute the square root of each element of the matrix mat.
    """

    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = np.sqrt(mat.numpy_array)

    return target


    if not target:
        target = mat

    target.resize(mat.shape)

    return target

def pow(mat, p, target = None):
    """
    Compute the 'p'th power of each element of the matrix mat.
    """

    if not target:
        target = mat

    target.resize(mat.shape)

    target.numpy_array[:] = mat.numpy_array[:] ** p

    return target

def cuda_sync_threads():
    pass

def reformat(array):
    """
    Returns array as a float32 array in FORTRAN order.
    """
    return np.array(array, dtype=__DTYPE__, order='F')


def cuda_set_some_device():
    return 0

def cuda_set_device(dev_id):
    """
    Selects the CUDA device with the given ID.
    """


    return 0

def cuda_get_free_device():
    """
    Returns the ID of the first free CUDA device.
    """
    return 0



def cublas_init():
    """
    Initialize Cublas.
    """

    return 0

def cublas_shutdown():
    """
    Shut down Cublas.
    """
    return 0


# The following functions are for implementing things like coarse filters and
# models with replicated local filters. At the moment they are quite slow.

def sum_superpixels(source, target, w, temp = None):
    raise NotImplemented()



def kronecker(mat1, mat2, target = None):
    raise NotIMplemented



def flat_to_tiled(source, target, stride):
    raise NotImplemented()

def tiled_to_flat(source, target, stride, temp = None):
    raise NotImplemented()

def flat_to_tiled3(source, target, stride):
    raise NotImplemented()






def get_item_from_each_row(source, target, inds, num_rows, num_cols):
    if source.numpy_array.shape == (num_cols, num_rows):
        src = source.numpy_array.T
    else:
        src = source.numpy_array.reshape(num_rows, num_cols)
    ix = inds.numpy_array.reshape(num_rows).astype(int)
    t = target.numpy_array.reshape(num_rows)

    for i in range(num_rows):
        t[i] = src[i,ix[i]]
    return target


def set_item_to_each_row(source, target, inds, num_rows, num_cols):
    if source.numpy_array.shape == (num_cols, num_rows):
        src = source.numpy_array.T
    else:
        src = source.numpy_array.reshape(num_rows, num_cols)

    ix = inds.numpy_array.reshape(num_rows).astype(int)
    t = target.numpy_array.reshape(num_rows)

    for i in range(num_rows):
        src[i,ix[i]] = t[i]
    return source
















def abs(X, aux):
    return aux.assign_mult(X, X).sqrt()

def total_sum(X):
    return X.total_sum()


def mean(mat, axis, target = None):

    target = sum(mat, axis, target)



    target.mult_by_scalar(1. / mat.shape[axis])

    return target


def total_mean(mat):
    s = total_sum(mat)
    return s / mat.num_elems








def cumsum(mat, target):

    target.resize(mat.shape)

    target.numpy_array[:] = mat.numpy_array.cumsum(1)

    return target




# def multi_transpose(IN, OUT, w, h, batch_size):
#     """
#     the order of w, h seems wrong, but it is consistent with the one on cudamat.py
#     """
#     assert IN.shape == (w*h, batch_size)
#     assert OUT.shape == (w*h, batch_size)


#     from pylab import amap, transpose
#     OUT.numpy_array[:] = amap(transpose,IN.numpy_array.reshape(h, w, batch_size).transpose([2,0,1])).transpose([1,2,0]).reshape(w*h, batch_size)


def multi_transpose(IN, OUT, w, h, batch_size):
    i = IN.numpy_array
    o = OUT.numpy_array

#     o = o.reshape(batch_size, w, h)
#     o[:] = i.reshape(batch_size, h, w).transpose([0,2,1])
#     OUT.numpy_array[:] = o.reshape(*OUT.numpy_array.shape)

    o = o.ravel()
    o[:] = i.reshape(h, w, batch_size).transpose([1,0,2]).ravel()
    OUT.numpy_array[:] = o.reshape(*OUT.numpy_array.shape)


    return OUT

def ind_incr(target, inds, axis):


    assert target.shape[1] == inds.shape[0] * inds.shape[1]
    assert inds.shape[1] == 1 or inds.shape[0] == 1

    if axis == 1:
        try:
            for i in inds:
                target.numpy_array[:, i] += 1
        except IndexError:
            raise IncompatibleDimensionsException


        return target

    elif axis == 0:

        try:
            for i in inds:
                target.numpy_array[i, :] += 1
        except IndexError:
            raise IncompatibleDimensionsException


        return target


    else:
        raise Exception ("bad axis.")




## The code below has been lifted from cudamat. It needs to work with numpy.


MAX_ELEMS = 2 ** 16 - 10
class softmax:
    def __init__(self, axis):
        self.axis = axis

        self.transpose_aux = empty()
        self.neg_max = empty()
        self.mat = empty()
        self.exp = empty()
        self.Z = empty()
        self.probs = empty()


        self.transpose_aux_small = empty()
        self.neg_max_small = empty()
        self.mat_small = empty()
        self.exp_small = empty()
        self.Z_small = empty()
        self.probs_small = empty()



    def __call__(self, mat, target):


        if mat.shape != target.shape:
            target.resize(mat.shape)

        if self.axis == 1:
            return self.__call_helper_small__(mat, target)




        pos = 0
        step = MAX_ELEMS

        ## width is how many elems we have to work with.
        width = mat.shape[1 - self.axis]

        while pos < width:
            next = min(width, pos + step)

            step_size = next - pos

            if step_size == step:
                self.__call_helper__(mat.slice(pos, next),
                                     target.slice(pos, next))
            else:
                self.__call_helper_small__(mat.slice(pos, next),
                                           target.slice(pos, next))

            pos += step_size

        return target



    def __call_helper__(self, mat, target):






        self.neg_max.\
            assign_max(mat,
                       axis = self.axis,
                       transpose_aux = self.transpose_aux).\
            mult(-1)

        if self.axis == 0:
            self.mat.assign_add_row_vec(mat, self.neg_max)
        else:
            self.mat.assign_add_col_vec(mat, self.neg_max)

        self.exp.assign_exp(self.mat)

        self.Z.assign_sum(self.exp, self.axis).reciprocal()

        self.probs.assign(self.exp)
        if self.axis == 0:
            self.probs.mult_by_row(self.Z)
        else:
            self.probs.mult_by_col(self.Z)

        target.assign(self.probs)




    def __call_helper_small__(self, mat, target):

        self.neg_max_small.\
            assign_max(mat,
                       axis = self.axis,
                       transpose_aux = self.transpose_aux_small).\
            mult(-1)

        if self.axis == 0:
            self.mat_small.assign_add_row_vec(mat, self.neg_max_small)
        else:
            self.mat_small.assign_add_col_vec(mat, self.neg_max_small)

        self.exp_small.assign_exp(self.mat_small)

        self.Z_small.assign_sum(self.exp_small, self.axis).reciprocal()



        self.probs_small.assign(self.exp_small)
        if self.axis == 0:
            self.probs_small.mult_by_row(self.Z_small)
        else:
            self.probs_small.mult_by_col(self.Z_small)





        target.assign(self.probs_small)









    def log_Zs(self, mat, target):

        self.neg_max.\
            assign_max(mat,
                       axis = self.axis,
                       transpose_aux = self.transpose_aux).\
            mult(-1)

        if self.axis == 0:
            self.mat.assign_add_row_vec(mat, self.neg_max)
        else:
            self.mat.assign_add_col_vec(mat, self.neg_max)

        ## the exps without the max
        self.exp.assign_exp(self.mat)

        ## take the sums of the exps, take the log, and add subtruct the maxes.
        target.assign_sum(self.exp, self.axis).log().add(self.neg_max.mult(-1))

        return target








class sample_multinomial:
    def __init__(self, probs, axis):
        raise NotImplementedError("use robust_multinomial instead.")

        self.axis = axis
        self.cumsums = empty()
        self.cumsums_t = empty()
        self.probs_t = empty()



        self.cumsums_small = empty()
        self.cumsums_t_small = empty()
        self.probs_t_small = empty()





        self.set_probs(probs)


        self.samples = empty()
        self.samples_small = empty()


        if axis == 0:

            width = probs.shape[1]
            std_width = min(width, MAX_ELEMS)



            self.rand_vals = empty((1, std_width))
            self.ones      = empty((probs.shape[0], 1)).assign(1.)



            small_width = max(0, width % MAX_ELEMS)



            self.rand_vals_small = empty((1, small_width))
            self.ones_small      = empty((probs.shape[1], 1)).assign(1.)



        elif axis == 1:


            width = probs.shape[0]
            std_width = min(width, MAX_ELEMS)



            self.rand_vals = empty((std_width, 1))
            self.ones      = empty((1, probs.shape[1])).assign(1.)



            small_width = max(0, width % MAX_ELEMS)


            self.rand_vals_small = empty((small_width, 1))
            self.ones_small      = empty((1, probs.shape[1])).assign(1.)







        self.rand_mat = empty()
        self.threshs = empty()


        self.rand_mat_small = empty()
        self.threshs_small = empty()




    def set_probs(self, probs):
        if self.axis == 1:
            cumsum(probs, self.cumsums)

        else:
            probs.transpose(target = self.probs_t)
            cumsum(self.probs_t, self.cumsums_t)
            self.cumsums_t.transpose(target = self.cumsums)









    def multi_sample(self, target, k):
        target.resize(self.cumsums.shape)


        for i in range(k):

            self.rand_vals.fill_with_rand()

            if self.axis == 1:
                self.rand_mat.assign_dot(self.rand_vals, self.ones)
            else:
                self.rand_mat.assign_dot(self.ones, self.rand_vals)


            self.threshs.\
                assign_less_than(self.cumsums, self.rand_mat).\
                sum(self.axis, target = self.samples)




            ind_incr(target, self.samples, self.axis)

        return target









    def set_probs_helper_small(self, probs):
        self.probs = probs
        if self.axis == 1:
            cumsum(probs, self.cumsums_small)

        else:
            probs.transpose(target = self.probs_t_small)
            cumsum(self.probs_t_small, self.cumsums_t_small)
            self.cumsums_t_small.transpose(target = self.cumsums_small)



    def multi_sample_helper_small(self, target, k):
        target.resize(self.cumsums_small.shape)


        for i in range(k):

            self.rand_vals_small.fill_with_rand()

            if self.axis == 1:
                self.rand_mat_small.assign_dot(self.rand_vals_small, self.ones_small)
            else:
                self.rand_mat_small.assign_dot(self.ones_small, self.rand_vals_small)


            self.threshs_small.\
                assign_less_than(self.cumsums_small, self.rand_mat_small).\
                sum(self.axis, target = self.samples_small)




            ind_incr(target, self.samples_small, self.axis)

        return target






    def sample_from_probs(self, probs, target):

        if probs.shape != target.shape:
            target.resize(probs.shape)


        ## yes: we make a loop.

        pos = 0
        step = MAX_ELEMS
        width = probs.shape[1]
        while pos < width:
            next = min(width, pos + step)

            step_size = next - pos

            if step_size == step:
                p = probs.slice(pos, next)
                t = target.slice(pos, next)

                self.set_probs(p)
                self.multi_sample(t, 1)

            else:
                p = probs.slice(pos, next)
                t = target.slice(pos, next)


                self.set_probs_helper_small(probs)
                self.multi_sample_helper_small(t, 1)

            pos += step_size



        return target






class robust_multinomial:
    def __init__(self, shape, axis):
        self.axis = axis
        self.cumsums = empty()
        self.cumsums_t = empty()
        self.probs_t = empty()



        self.cumsums_small = empty()
        self.cumsums_t_small = empty()
        self.probs_t_small = empty()






        self.samples = empty()
        self.samples_small = empty()


        if axis == 0:

            width = shape[1]
            std_width = min(width, MAX_ELEMS)



            self.rand_vals = empty((1, std_width))
            self.ones      = empty((shape[0], 1)).assign(1.)



            small_width = max(0, width % MAX_ELEMS)



            self.rand_vals_small = empty((1, small_width))
            self.ones_small      = empty((shape[0], 1)).assign(1.)



        elif axis == 1:


            width = shape[0]
            std_width = min(width, MAX_ELEMS)



            self.rand_vals = empty((std_width, 1))
            self.ones      = empty((1, shape[1])).assign(1.)



            small_width = max(0, width % MAX_ELEMS)


            self.rand_vals_small = empty((small_width, 1))
            self.ones_small      = empty((1, shape[1])).assign(1.)







        self.rand_mat = empty()
        self.threshs = empty()


        self.rand_mat_small = empty()
        self.threshs_small = empty()




    def set_probs(self, probs):
        self.probs = probs
        if self.axis == 1:
            cumsum(probs, self.cumsums)

        else:
            probs.transpose(target = self.probs_t)
            cumsum(self.probs_t, self.cumsums_t)
            self.cumsums_t.transpose(target = self.cumsums)









    def multi_sample(self, target, k):
        target.resize(self.cumsums.shape)


        for i in range(k):

            self.rand_vals.fill_with_rand()

            if self.axis == 1:
                self.rand_mat.assign_dot(self.rand_vals, self.ones)
            else:
                self.rand_mat.assign_dot(self.ones, self.rand_vals)


            self.threshs.\
                assign_less_than(self.cumsums, self.rand_mat).\
                sum(self.axis, target = self.samples)




            ind_incr(target, self.samples, self.axis)

        return target









    def set_probs_helper_small(self, probs):
        if self.axis == 1:
            cumsum(probs, self.cumsums_small)

        else:
            probs.transpose(target = self.probs_t_small)
            cumsum(self.probs_t_small, self.cumsums_t_small)
            self.cumsums_t_small.transpose(target = self.cumsums_small)




    def multi_sample_helper_small(self, target, k):
        target.resize(self.cumsums_small.shape)

        for i in range(k):

            self.rand_vals_small.fill_with_rand()

            if self.axis == 1:
                self.rand_mat_small.assign_dot(self.rand_vals_small, self.ones_small)
            else:
                self.rand_mat_small.assign_dot(self.ones_small, self.rand_vals_small)


            self.threshs_small.\
                assign_less_than(self.cumsums_small, self.rand_mat_small).\
                sum(self.axis, target = self.samples_small)




            ind_incr(target, self.samples_small, self.axis)

        return target






    def sample_from_probs(self, probs, target):

        if probs.shape != target.shape:
            target.resize(probs.shape)


        ## yes: we make a loop.

        pos = 0
        step = MAX_ELEMS

        width = probs.shape[1 - self.axis]

        while pos < width:
            next = min(width, pos + step)

            step_size = next - pos

            p = probs.slice(pos, next)
            t = target.slice(pos, next)


            if step_size == step:

                self.set_probs(p)
                self.multi_sample(t, 1)

            else:

                self.set_probs_helper_small(p)
                self.multi_sample_helper_small(t, 1)

            pos += step



        return target

########NEW FILE########
__FILENAME__ = pretrain
"""
 Copyright (c) 2011,2012 George Dahl

 Permission is hereby granted, free of charge, to any person  obtaining
 a copy of this software and associated documentation  files (the
 "Software"), to deal in the Software without  restriction, including
 without limitation the rights to use,  copy, modify, merge, publish,
 distribute, sublicense, and/or sell  copies of the Software, and to
 permit persons to whom the  Software is furnished to do so, subject
 to the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.  THE
 SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT  HOLDERS
 BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,  WHETHER IN AN
 ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING  FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR  OTHER DEALINGS IN THE
 SOFTWARE.
"""

import numpy as num
import gnumpy as gnp

class Binary(object):
    def activate(self, netInput):
        return netInput.sigmoid()
    def sampleStates(self, acts):
        return gnp.rand(*acts.shape) <= acts

class Gaussian(object):
    def activate(self, netInput):
        return netInput
    def sampleStates(self, acts): #probably shouldn't use this
        return acts + gnp.randn(*acts.shape)

class ReLU(object):
    def __init__(self, krizNoise = False):
        self.krizNoise = krizNoise
    def activate(self, netInput):
        return netInput*(netInput > 0)
    def sampleStates(self, acts):
        if self.krizNoise:
            return self.activate(acts + gnp.randn(*acts.shape))
        tiny = 1e-30
        stddev = gnp.sqrt(acts.sigmoid() + tiny)
        return self.activate( acts + stddev*gnp.randn(*acts.shape) )


def CD1(vis, visToHid, visBias, hidBias, visUnit = Binary(), hidUnit = Binary()):
    """
    Using Gaussian hidden units hasn't been tested. By assuming the
    visible units are Binary, ReLU, or Gaussian and the hidden units
    are Binary or ReLU this function becomes quite simple.
    """
    posHid = hidUnit.activate(gnp.dot(vis, visToHid) + hidBias)
    posHidStates = hidUnit.sampleStates(posHid)

    negVis = visUnit.activate(gnp.dot(posHidStates, visToHid.T) + visBias)
    negHid = hidUnit.activate(gnp.dot(negVis, visToHid) + hidBias)

    visHidStats = gnp.dot(vis.T, posHid) - gnp.dot(negVis.T, negHid)
    visBiasStats = vis.sum(axis=0).reshape(*visBias.shape) - negVis.sum(axis=0).reshape(*visBias.shape)
    hidBiasStats = posHid.sum(axis=0).reshape(*hidBias.shape) - negHid.sum(axis=0).reshape(*hidBias.shape)

    return visHidStats, hidBiasStats, visBiasStats, negVis

########NEW FILE########
__FILENAME__ = gevent-alone
import os
import gevent
from gevent import Greenlet

class MyAlgorithm(object):

    def __init__(self):
        self.n = 0

    def fit(self):
        print "Fit", os.getpid()
        while self.n < 5:
            self.n += 1
            gevent.sleep(1)

g = MyAlgorithm()


def foo():
    g.fit()


def bar():
    print "Print", os.getpid()
    while g.n < 5:
        print g.n
        gevent.sleep(0.5)


gevent.joinall([
    gevent.spawn(foo),
    gevent.spawn(bar),
])


########NEW FILE########
__FILENAME__ = gevent-async
import gevent
from gevent.event import AsyncResult

a = AsyncResult()

class MyAlgorithm(object):

    def __init__(self):
        self.n = 0

    def fit(self):
        while self.n < 5:
            self.n += 1
            gevent.sleep(1)
            a.set()

g = MyAlgorithm()

def setter():
    g.fit()

def waiter():
    # while g.n < 5:
        a.get() # blocking
        print g.n
        # gevent.sleep(0.1)

gevent.joinall([
    gevent.spawn(setter),
    gevent.spawn(waiter),
])

########NEW FILE########
__FILENAME__ = gevent-group
import os
import gevent
from gevent.pool import Group

def talk(msg):
    for i in xrange(3):
        print(msg, os.getpid())

g1 = gevent.spawn(talk, 'bar')
g2 = gevent.spawn(talk, 'foo')
g3 = gevent.spawn(talk, 'fizz')

group = Group()
group.add(g1)
group.add(g2)
group.join()

group.add(g3)
group.join()
########NEW FILE########
__FILENAME__ = gevent-multi-pipe
import os
import time
import gevent
from multiprocessing import Process, Pipe
from gevent.socket import wait_read, wait_write

a, b = Pipe()

class MyAlgorithm(object):

    def __init__(self):
        self.n = 0

    def fit(self):
        print "Fit", os.getpid()
        while self.n < 5:
            self.n += 1
            time.sleep(0.5)
            a.send(self.n)

def relay():
    g = MyAlgorithm()
    g.fit()

def get_msg():
    print "Print", os.getpid()
    while True:
        wait_read(b.fileno())
        print(b.recv())

if __name__ == '__main__':
    proc = Process(target=relay)
    proc.start()

    g1 = gevent.spawn(get_msg)
    gevent.joinall([g1], timeout=5)
########NEW FILE########
__FILENAME__ = gevent-multi-queue
import os
import time
import gevent
from multiprocessing import Process, Pipe
from gevent.socket import wait_read, wait_write

a, b = Pipe()

class MyAlgorithm(object):

    def __init__(self):
        self.n = 0

    def fit(self):
        print 1, os.getpid()
        while self.n < 5:
            self.n += 1
            time.sleep(0.5)
            a.send(self.n)

g = MyAlgorithm()
def relay():
    g.fit()


def get_msg():
    print 2, os.getpid()
    while True:
        wait_read(b.fileno())
        print(b.recv())

if __name__ == '__main__':
    proc = Process(target=relay)
    proc.start()

    g1 = gevent.spawn(get_msg)
    gevent.joinall([g1], timeout=5)
########NEW FILE########
__FILENAME__ = gevent-multi
import os
import gevent
from multiprocessing import Process, Pipe
from gevent.socket import wait_read, wait_write

# To Process
a, b = Pipe()

# From Process
c, d = Pipe()

def relay():
    for i in xrange(10):
        print 1, os.getpid()
        msg = b.recv()
        c.send(msg + " in " + str(i))

def put_msg():
    for i in xrange(10):
        print 2, os.getpid()
        wait_write(a.fileno())
        a.send('hi')

def get_msg():
    for i in xrange(10):
        print 3, os.getpid()
        wait_read(d.fileno())
        # print(d.recv())

if __name__ == '__main__':
    proc = Process(target=relay)
    proc.start()

    g1 = gevent.spawn(get_msg)
    g2 = gevent.spawn(put_msg)
    gevent.joinall([g1, g2], timeout=1)
########NEW FILE########
__FILENAME__ = gevent-queues
import os
import gevent
from gevent.queue import Queue

tasks = Queue()

class MyAlgorithm(object):

    def __init__(self):
        self.n = 0

    def fit(self):
        print "Fit", os.getpid()
        while self.n < 5:
            self.n += 1
            gevent.sleep(1)
            tasks.put_nowait(self.n)

g = MyAlgorithm()

def setter():
    g.fit()

def waiter():
    print "Print", os.getpid()
    while g.n < 5:
        print tasks.get()
        print os.getpid()

gevent.joinall([
    gevent.spawn(setter),
    gevent.spawn(waiter),
])

########NEW FILE########
__FILENAME__ = multi-compare
import os
import time

def echo(i):
    time.sleep(0.001)
    print os.getpid()
    return i

# Non Deterministic Process Pool

from multiprocessing.pool import Pool

p = Pool(10)
run1 = [a for a in p.imap_unordered(echo, xrange(10))]
run2 = [a for a in p.imap_unordered(echo, xrange(10))]
run3 = [a for a in p.imap_unordered(echo, xrange(10))]
run4 = [a for a in p.imap_unordered(echo, xrange(10))]

print( run1 == run2 == run3 == run4 )
print
print
# Deterministic Gevent Pool

from gevent.pool import Pool

p = Pool(10)
run1 = [a for a in p.imap_unordered(echo, xrange(10))]
run2 = [a for a in p.imap_unordered(echo, xrange(10))]
run3 = [a for a in p.imap_unordered(echo, xrange(10))]
run4 = [a for a in p.imap_unordered(echo, xrange(10))]

print( run1 == run2 == run3 == run4 )
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# copper documentation build configuration file, created by
# sphinx-quickstart on Sun Jul  7 21:29:06 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'numpydoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'copper'
copyright = u'2013, Daniel Rodriguez'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.0.5'
# The full version, including alpha/beta/rc tags.
release = '0.0.5'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'copperdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'copper.tex', u'copper Documentation',
   u'Daniel Rodriguez', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'copper', u'copper Documentation',
     [u'Daniel Rodriguez'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'copper', u'copper Documentation',
   u'Daniel Rodriguez', 'copper', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
