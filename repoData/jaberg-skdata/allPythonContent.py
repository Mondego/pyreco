__FILENAME__ = base
"""
Base classes serving as design documentation.
"""

import numpy as np

class DatasetNotDownloadable(Exception):
    pass

class DatasetNotPresent(Exception):
    pass


class Task(object):
    """
    A Task is the smallest unit of data packaging for training a machine
    learning model.  For different machine learning applications (semantics)
    the attributes are different, but there are some conventions.

    For example:
    semantics='vector_classification'
        - self.x is a matrix-like feature matrix with a row for each example
          and a column for each feature.
        - self.y is a array of labels (any type, but often integer or string)

    semantics='image_classification'
        - self.x is a 4D structure images x height x width x channels
        - self.y is a array of labels (any type, but often integer or string)

    semantics='indexed_vector_classification'
        - self.all_vectors is a matrix (examples x features)
        - self.all_labels is a vector of labels
        - self.idxs is a vector of relevant example positions

    semantics='indexed_image_classification'
        - self.all_images is a 4D structure (images x height x width x channels)
        - self.all_labels is a vector of labels
        - self.idxs is a vector of relevant example positions

    The design taken in skdata is that each data set view file defines

    * a semantics object (a string in the examples above) that uniquely
      *identifies* what a learning algorithm is supposed to do with the Task,
      and

    * documentation to *describe* to the user what a learning algorithm is
      supposed to do with the Task.

    As library designers, it is our hope that data set authors can re-use each
    others' semantics as much as possible, so that learning algorithms are
    more portable between tasks.

    """
    def __init__(self, semantics=None, name=None, **kwargs):
        self.semantics = semantics
        self.name = name
        self.__dict__.update(kwargs)


class Split(object):
    """
    A Split is a (train, test) pair of Tasks with no common examples.

    This class is used in cross-validation to select / learn parameters
    based on the `train` task, and then to evaluate them on the `valid` task.
    """
    # XXX This class is no longer necessary in the View API

    def __init__(self, train, test):
        self.train = train
        self.test = test


class View(object):
    """
    A View is an interpretation of a data set as a standard learning problem.
    """

    def __init__(self, dataset=None):
        """
        dataset: a reference to a low-level object that offers access to the
                 raw data. It is not standardized in any way, and the
                 reference itself is optional.

        """
        self.dataset = dataset

    def protocol(self, algo):
        """
        Return a list of instructions for a learning algorithm.

        An instruction is a 3-tuple of (attr, args, kwargs) such that
        algo.<attr>(*args, **kwargs) can be interpreted by the learning algo
        as a sensible operation, like train a model from some data, or test a
        previously trained model.

        See `LearningAlgo` below for a list of standard instructions that a
        learning algorithm implementation should support, but the protocol is
        left open deliberately so that new View objects can call any method
        necessary on a LearningAlgo, even if it means calling a relatively
        unique method that only particular LearningAlgo implementations
        support.

        """
        raise NotImplementedError()


class LearningAlgo(object):
    """
    A base class for learning algorithms that can be driven by the protocol()
    functions that are sometimes included in View subclasses.

    The idea is that a protocol driver will call these methods in a particular
    order with appropriate tasks, splits, etc. and a subclass of this instance
    will thereby perform an experiment by side effect on `self`.
    """

    def task(self, *args, **kwargs):
        # XXX This is a typo right? Surely there is no reason for a
        # LearningAlgo to have a self.task method...
        return Task(*args, **kwargs)

    def best_model(self, train, valid=None, return_promising=False):
        """
        Train a model from task `train` optionally optimizing for
        cross-validated performance on `valid`.

        If `return_promising` is False, this function returns a tuple:

            (model, train_error, valid_error)

        In which
            model is an opaque model for the task,
            train_error is a scalar loss criterion on the training task
            valid_error is a scalar loss criterion on the validation task.

        If `return_promising` is True, this function returns

            (model, train_error, valid_error, promising)

        The `promising` term is a boolean flag indicating whether the model
        seemed to work (1) or if it appeared to be degenerate (0).

        """
        raise NotImplementedError('implement me')

    def loss(self, model, task):
        """
        Return scalar-valued training criterion of `model` on `task`.

        This function can modify `self` but it should not semantically modify
        `model` or `task`.
        """
        raise NotImplementedError('implement me')

    # -- as an example of weird methods an algo might be required to implement
    #    to accommodate bizarre protocols, see this one, which is required by
    #    LFW.  Generally there is no need for this base class to list such
    #    special-case functions.
    def retrain_classifier(self, model, train, valid=None):
        """
        To the extent that `model` includes a feature extractor that is distinct from
        a classifier, re-train the classifier only. This unusual step is
        required in the original View1 / View2 LFW protocol. It is included
        here as encouragement to add dataset-specific steps in LearningAlgo subclasses.
        """
        raise NotImplementedError('implement me')


    def forget_task(self, task_name):
        """
        Signal that it is OK to delete any features / statistics etc related
        specifically to task `task_name`.  This can be safely ignored
        for small data sets but deleting such intermediate results can
        be crucial to keeping memory use under control.
        """
        pass


class SemanticsDelegator(LearningAlgo):
    def best_model(self, train, valid=None):
        if valid:
            assert train.semantics == valid.semantics
        return getattr(self, 'best_model_' + train.semantics)(train, valid)

    def loss(self, model, task):
        return getattr(self, 'loss_' + task.semantics)(model, task)


class SklearnClassifier(SemanticsDelegator):
    """
    Implement a LearningAlgo as much as possible in terms of an sklearn
    classifier.

    This class is meant to illustrate how to create an adapter between an
    existing implementation of a machine learning algorithm, and the various
    data sets defined in the skdata library.

    Researchers are encouraged to implement their own Adapter classes
    following the example of this class (i.e. cut & paste this class)
    to measure the statistics they care about when handling the various
    methods (e.g. best_model_vector_classification) and to save those
    statistics to a convenient place. The practice of appending a summary
    dictionary to the lists in self.results has proved to be useful for me,
    but I don't see why it should in general be the right thing for others.


    This class is also used for internal unit testing of Protocol interfaces,
    so it should be free of bit rot.

    """
    def __init__(self, new_model):
        self.new_model = new_model
        self.results = {
            'best_model': [],
            'loss': [],
        }

    def best_model_vector_classification(self, train, valid):
        # TODO: use validation set if not-None
        model = self.new_model()
        print 'SklearnClassifier training on data set of shape', train.x.shape
        model.fit(train.x, train.y)
        model.trained_on = train.name
        self.results['best_model'].append(
            {
                'train_name': train.name,
                'valid_name': valid.name if valid else None,
                'model': model,
            })
        return model

    def loss_vector_classification(self, model, task):
        p = model.predict(task.x)
        err_rate = np.mean(p != task.y)

        self.results['loss'].append(
            {
                'model_trained_on': model.trained_on,
                'predictions': p,
                'err_rate': err_rate,
                'n': len(p),
                'task_name': task.name,
            })

        return err_rate

    @staticmethod
    def _fallback_indexed_vector(self, task):
        return Task(
            name=task.name,
            semantics="vector_classification",
            x=task.all_vectors[task.idxs],
            y=task.all_labels[task.idxs])

    def best_model_indexed_vector_classification(self, train, valid):
        return self.best_model_vector_classification(
            self._fallback_indexed_vector(train),
            self._fallback_indexed_vector(valid))

    def loss_indexed_vector_classification(self, model, task):
        return self.loss_vector_classification(model,
            self._fallback_indexed_vector(task))

    @staticmethod
    def _fallback_indexed_image_task(task):
        if task is None:
            return None
        x = task.all_images[task.idxs]
        y = task.all_labels[task.idxs]
        if 'int' in str(x.dtype):
            x = x.astype('float32') / 255
        else:
            x = x.astype('float32')
        x2d = x.reshape(len(x), -1)
        rval = Task(
            name=task.name,
            semantics="vector_classification",
            x=x2d,
            y=y)
        return rval

    def best_model_indexed_image_classification(self, train, valid):
        return self.best_model_vector_classification(
            self._fallback_indexed_image_task(train),
            self._fallback_indexed_image_task(valid))

    def loss_indexed_image_classification(self, model, task):
        return self.loss_vector_classification(model,
            self._fallback_indexed_image_task(task))



########NEW FILE########
__FILENAME__ = brodatz
"""
Brodatz texture dataset.

http://www.ux.uis.no/~tranden/brodatz.html

"""

import hashlib
import logging
import os
import urllib

from PIL import Image

from .data_home import get_data_home
from .utils.image import ImgLoader
from .larray import lmap


logger = logging.getLogger(__name__)
url_template = 'http://www.ux.uis.no/~tranden/brodatz/D%i.gif'

valid_nums = range(1, 113)
del valid_nums[13]


class Brodatz(object):
    """
    self.meta is a list of dictionaries with the following structure:

    - id: a unique number within the list of dictionaries
    - basename: relative filename such as "D1.gif"
    - image: sub-dictionary
        - shape: (<height>, <width>)
        - dtype: 'uint8'

    """

    DOWNLOAD_IF_MISSING = True

    def home(self, *names):
        return os.path.join(get_data_home(), 'brodatz', *names)

    @property
    def meta(self):
        try:
            return self._meta
        except AttributeError:
            self.fetch(download_if_missing=self.DOWNLOAD_IF_MISSING)
            self._meta = self.build_meta()
            return self._meta

    def fetch(self, download_if_missing=None):
        if download_if_missing is None:
            download_if_missing = self.DOWNLOAD_IF_MISSING

        if download_if_missing:
            if not os.path.isdir(self.home()):
                os.makedirs(self.home())

        sha1s = sha1_list.split('\n')

        for ii, image_num in enumerate(valid_nums):
            url = url_template % image_num
            dest = self.home(os.path.basename(url))
            if not os.path.exists(dest):
                if download_if_missing:
                    logger.warn("Downloading ~100K %s => %s" % (url, dest))
                    downloader = urllib.urlopen(url)
                    data = downloader.read()
                    tmp = open(dest, 'wb')
                    tmp.write(data)
                    tmp.close()
                else:
                    raise IOError(dest)
            sha1 = hashlib.sha1(open(dest).read()).hexdigest()
            if sha1 != sha1s[ii + 1]:
                raise IOError('SHA1 mismatch on image %s', dest)

    def build_meta(self):
        meta = []
        for i, image_num in enumerate(valid_nums):
            basename = 'D%i.gif' % image_num
            try:
                img_i = Image.open(self.home(basename))
            except:
                logger.error('failed to load image %s' % self.home(basename))
                raise
            meta.append(dict(
                    id=i,
                    basename=basename,
                    image=dict(
                        shape=img_i.size,
                        dtype='uint8',
                        )
                    ))
        return meta

    @classmethod
    def main_fetch(cls):
        return cls().fetch(download_if_missing=True)

    @classmethod
    def main_clean_up(cls):
        return cls().clean_up()

    def images_larray(self, dtype='uint8'):
        img_paths = [self.home(m['basename']) for m in self.meta]
        imgs = lmap(ImgLoader(ndim=2, dtype=dtype, mode='L'),
                           img_paths)
        return imgs

    @classmethod
    def main_show(cls):
        from utils.glviewer import glumpy_viewer, command, glumpy
        self = cls()
        imgs = self.images_larray('uint8')
        Y = range(len(imgs))
        glumpy_viewer(
                img_array=imgs,
                arrays_to_print=[Y],
                cmap=glumpy.colormap.Grey)


def gen_sha1_list():
    ds = Brodatz()
    foo = open('foo.txt', 'w')
    for image_num in valid_nums:
        data = open(ds.home('D%i.gif' % image_num)).read()
        sha1 = hashlib.sha1(data).hexdigest()
        print >> foo, sha1


def main_fetch():
    Brodatz.main_fetch()


def main_show():
    Brodatz.main_show()


def main_clean_up():
    Brodatz.main_clean_up()


if __name__ == '__main__':
    gen_sha1_list()


sha1_list = """
6aea21c25826a22222045befb90e5def42040cc1
ff2ee9e834e61e30c5cb915a34ad4fdbfd736cf7
7ac47673659ddcea3143bb90e766dc145ca45bf6
1b0ede375d2a19ca61d8343d428b4f72be747a0f
7ffb4161c6c78742e970cef1f264fe69151304a1
1e9c45897662d6e9f238b0c101f686e581de9aca
0e45e15a3031bd36b5e5272e943dfaad06c4a886
36c3a413a357e10b0462a2e7eeaa57a4b489312f
0036b3196a6d3e84bc43c31a0f9d355340dd4359
5de79b9f56fbae5cd6373045ed32a3aa31480599
e7f1c262256ac00fa08cb5de6f9a3eb8a6547408
a499f68f8b2345cd4f1ad1a07220187928a46aea
105b82cb4ff1f115b799ff51d6f220d6667e2cff
83c618339db659dcfe5152153adfdfc8e6fedf76
7d409e860116934df6acbd301ee715b02addeb57
246684aa363923b9d429a08b84ec00fb84a9e4e5
e23792018a6053c77e639dd604330d590611c311
5f8d4e7667b2119dbc60c87b6037a17165509a63
31b16441452138edf84f532afa0c1a7180d62fb4
c2afb40c2915d535bf253a74db6070b71e2edbe7
08e2c583ec90b7f0d8441cc5f6a1aa80a8d41248
b68a1ace83d438aba08473263db24d4ec9ae0f21
60a52085468e3abb98467282812ab3be4b9ff2f4
0786200ab65e4e301b64eb93ec2f066a2a82da8b
c99d7b85365f2ff2e76b53390c6165595b2168f2
ae5903d5b4e1ee2c420cd45f321fe3d19cfe118f
a69b1ef0cc1cd4be39602965ebc7a53ddd75b0a6
bf5733046ab98caaa430a8907c99ca90ce9e7788
5c1b8b0cf5abef47659dea3a863537dd8805321f
a7e74d916024d2c9438d2ed5396c9bbe9afaff9b
dc42adf47e3df5902e1405487745c28a14424416
0a8e7c7a18cdea2548c46684be707a3374209784
c19afb81855571984422cf13daa8bd24d5001d7d
f5e17d13897fa116c22c77a99b6c712c8effd865
7f60c98fa6a017f95f55eb34fd8edcc3f0e8dc5c
7f5a021572c602d11428d352b9f67493873c0efc
9199ac4d864287928925eea0c22e39a4d3baa88a
ba49f85a54727ede2adf767b7920fe73a22127c2
a6c53c51087face6ed82978c3da4ce3f26faa0c9
dc34603d037031af73a28d83ebfb8fbca5915f5b
607029253bdc179e52fb98be6f37174724da14f8
a8bac24d2abee2eb918451ccdc6068eaa96b9107
798ec414d36574ccf70644e6d7817f19d5487a68
e510dae0ac04c0777a7d6ba1c7cf2704f6241e14
0ea65d7e1c02a64059c940b70ce6cc9cd769aac7
ab078bf1f3aa323326696724bde2a4da326b7934
befca82ece334e44ea22a01c2c607289dc124235
f81b8faa5b6f9d1b4b7f36a3b31a6e8577ee98b9
1df2ce25ae49892c8989a6769160af0c1dfb97c7
e97b97334b29539db7bd37005dabc9866ec93b29
53de157b2c6ed794da12dabe8d7b8992fb272eef
666b0e98b7065acc20165eadc2cd3524ff29215e
c5dacf7c2d96e38bda0122241705dcd2ca597276
8cf86108974c390601dfa0a43dd266b3b548d2e4
c8caac53a4eaf3eb1369fb4e91d034fc120671bc
f38777eb82b382ce98ba97baa27801504634ba87
cdafce0f6a481b7ed545daf6e9fd8b1b0cf62668
4d65bc3f718f935a231efcd6cb0c227cfc60f3d0
cfe5243b07a2d97e30a211a4e97ffbade8f317e8
fecdf27729853a98f2b5108429167f3dbc62b4eb
f06bb13968c7a08f5698d4a2e0b41dbcf30ccda9
ab683e55d4c3d47b4fc0ca347514ac157b907d3b
1a9ba577d5a3600d3f1c002644bc55d6a1800e10
e39c4aa064ed20880a52111a887745470adc6779
913ca78db851f7b17380eacf11d80546a34b3106
1a63e33d4db18c3b0838e2f63a9d64cd087260d6
07245841bca7eb9fada1f3ed4baecd875561430d
30d6d58fd1ba2580e5006d64edfac8bf8ca89db6
e27bb5e24813b8f107cf20445fced07e466beb94
3e99f3c00f65adee54e8208086a4a1edb6719bcd
47eca012a7b878c730bc588d27c877602b6ca557
903f4fb23c7f3999d55c724c2a0549f00e022ac5
502933bd77c9b956ebb5a463f7000f6795cb1d8a
1b1895d0a08a96dafe93d08de19b41269e171b8e
3959cf92cb01f59219f028bf1be2997a943b8d51
03d2962a642e989dfd94d09800083f8f2972beb0
98ee9dc3ba7062759ef0715edf1ddbc8598c20f2
c1d8816c4b3c6c38a3bfff649d232dd72cf18138
277da2112d65d25c18e444fa129f80887e2c7389
cfc24d04acd1ec1f766654ffb10a451ea7fc0b51
3eadd78b4994fb8c1f99bd8fe2031afe46545014
8daa87856f87d5f7eaca082951df9ec53643b76b
defdb079e6101390f57360c812efc5b635e2b9e1
2fcf58f0527bdcf55328ebe47fa2b6d53152dbda
48cdb4014c75283de1b1ba8c8ac25622c3086881
f02edcc7a7a9639d92538e925d6f66a20aa9b9d8
fd4b399d54edc14782db726a79e161e149a24444
a32607c4f0a414205fce6d8c83a942a30031107c
aa17150ca98d659827d49d006d6faa642ba8d578
500f8749556ad44e4ec9d76c7b05dd2bfe183d71
120065d86a2c2c96c18a07d2d73379406b31d11c
c95232ef22c988eeb1bec35493da056fbb97550e
e336c1bca6815291231d67e8e152ab18027b8f58
ca709c085e71b2aa79a04c0c62ff4ed4d85b79f1
2066566e70a55ac3f10046825ec77a652a16401a
3edd31e7a2764f97be19712a339c7e7d51b0dca9
279644656faf50b569ed778f9701b8a104655ac0
d0e3b068368d98e4081199a90aaa174bbc96d2ae
a86a410a1498ab7d535bf8f675dc6c1855cec2a0
75b9636f0a2db93d4394e03fd02e87bb926d6ef6
d57e5a296d0fc2858bdf61f5f8ab97b924a8a288
5c428868ba39275a4b55c43235ca6e6ec5cfdcb7
423d727f3bfd62a1f66942ff27d2ffa90d7595fd
b308c2a346b6321acff87bee927ba2ae38e26b43
9431fba01bf3c9c1b711d69fc2167418084e36bb
95b8d95cd6287c9f581fd783fe5513a867a0b18d
29ee33df0d4df5fdabd2c94eb80f5b98587ec5f4
dbb601aaf26f4b93e32643c03d594495958de962
6ffff10c8e8959ddd8c5d35b6d95a55f2537df78
db9911e79ddf3984304a5c5fad1c9720f79334ce
b2e01384421741e899c850f9144609a80d7f0c46
"""


########NEW FILE########
__FILENAME__ = caltech
# -*- coding: utf-8 -*-
"""Caltech Object Datasets

Caltech 101: http://www.vision.caltech.edu/Image_Datasets/Caltech101
Caltech 256: http://www.vision.caltech.edu/Image_Datasets/Caltech256

If you make use of this data, please cite the following papers:
http://www.vision.caltech.edu/Image_Datasets/Caltech256/

The Caltech-256
Griffin, G. Holub, AD. Perona, P.
Caltech Technical Report (2007)
http://www.vision.caltech.edu/Image_Datasets/Caltech256/paper/256.pdf

Learning generative visual models from few training examples: an incremental
Bayesian approach tested on 101 object categories.
L. Fei-Fei, R. Fergus and P. Perona.
IEEE CVPR, Workshop on Generative-Model Based Vision (2004)
http://www.vision.caltech.edu/feifeili/Fei-Fei_GMBV04.pdf
"""

# Copyright (C) 2011
# Authors: Nicolas Pinto <pinto@rowland.harvard.edu>

# License: Simplified BSD

import cPickle
import os
from os import path
import shutil
from glob import glob
import hashlib

import numpy as np

import larray
from data_home import get_data_home
from utils import download, extract, int_labels
from utils.image import ImgLoader


class BaseCaltech(object):
    """Caltech Object Dataset

    Attributes
    ----------
    meta: list of dict
        Metadata associated with the dataset. For each image with index i,
        meta[i] is a dict with keys:
            name: str
                Name of the individual's face in the image.
            filename: str
                Full path to the image.
            id: int
                Identifier of the image.
            sha1: str
                SHA-1 hash of the image.

    Notes
    -----
    If joblib is available, then `meta` will be cached for faster
    processing. To install joblib use 'pip install -U joblib' or
    'easy_install -U joblib'.
    """

    def __init__(self, meta=None, seed=0, ntrain=15, ntest=15, num_splits=10):

        self.seed = seed
        self.ntrain = ntrain
        self.ntest = ntest
        self.num_splits = num_splits

        if meta is not None:
            self._meta = meta

        self.name = self.__class__.__name__

        try:
            from joblib import Memory
            mem = Memory(cachedir=self.home('cache'))
            self._get_meta = mem.cache(self._get_meta)
        except ImportError:
            pass

    def home(self, *suffix_paths):
        return path.join(get_data_home(), self.name, *suffix_paths)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: fetch()
    # ------------------------------------------------------------------------

    def fetch(self, download_if_missing=True):
        """Download and extract the dataset."""

        home = self.home()

        if not download_if_missing:
            raise IOError("'%s' exists!" % home)

        # download archive
        url = self.URL
        sha1 = self.SHA1
        basename = path.basename(url)
        archive_filename = path.join(home, basename)
        if not path.exists(archive_filename):
            if not download_if_missing:
                return
            if not path.exists(home):
                os.makedirs(home)
            download(url, archive_filename, sha1=sha1)

        # extract it
        if not path.exists(self.home(self.SUBDIR)):
            extract(archive_filename, home, sha1=sha1, verbose=True)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: meta
    # ------------------------------------------------------------------------

    @property
    def meta(self):
        if not hasattr(self, '_meta'):
            self.fetch(download_if_missing=True)
            self._meta = self._get_meta()
            self.names = sorted(os.listdir(self.home(self.SUBDIR)))
        return self._meta

    def _get_meta(self):
        try:
            rval = cPickle.load(
                    open(
                        self.home(self.SUBDIR + '.meta.pkl')))
            open(rval[0]['filename'])
            return rval
        except IOError:
            # IOError may come either from a missing pkl file
            # or from a missing image (rval[0]['filename']) but in both
            # cases the response is to rebuild the metadata
            names = sorted(os.listdir(self.home(self.SUBDIR)))

            meta = []
            ind = 0

            for name in names:

                pattern = self.home(self.SUBDIR, name, '*.jpg')

                img_filenames = sorted(glob(pattern))

                for img_filename in img_filenames:
                    img_data = open(img_filename, 'rb').read()
                    sha1 = hashlib.sha1(img_data).hexdigest()

                    data = dict(name=name,
                                id=ind,
                                filename=img_filename,
                                sha1=sha1)

                    meta.append(data)
                    ind += 1

            cPickle.dump(
                    meta,
                    open(self.home(self.SUBDIR + '.meta.pkl'), 'w'))

            return meta

    @property
    def splits(self):
        """
        generates splits and attaches them in the "splits" attribute

        """
        if not hasattr(self, '_splits'):
            seed = self.seed
            ntrain = self.ntrain
            ntest = self.ntest
            num_splits = self.num_splits
            self._splits = self.generate_splits(seed, ntrain,
                                                ntest, num_splits)
        return self._splits

    def generate_splits(self, seed, ntrain, ntest, num_splits):
        meta = self.meta
        ntrain = self.ntrain
        ntest = self.ntest
        rng = np.random.RandomState(seed)
        splits = {}
        for split_id in range(num_splits):
            splits['train_' + str(split_id)] = []
            splits['test_' + str(split_id)] = []
            for name in self.names:
                cat = [m for m in meta if m['name'] == name]
                L = len(cat)
                assert L >= ntrain + ntest, 'category %s too small' % name
                perm = rng.permutation(L)
                for ind in perm[:ntrain]:
                    splits['train_' + str(split_id)].append(cat[ind]['id'])
                for ind in perm[ntrain: ntrain + ntest]:
                    splits['test_' + str(split_id)].append(cat[ind]['id'])
        return splits

    # ------------------------------------------------------------------------
    # -- Dataset Interface: clean_up()
    # ------------------------------------------------------------------------

    def clean_up(self):
        if path.isdir(self.home()):
            shutil.rmtree(self.home())

    # ------------------------------------------------------------------------
    # -- Standard Tasks
    # ------------------------------------------------------------------------

    def raw_classification_task(self, split=None):
        """Return image_paths, labels"""
        if split:
            inds = self.splits[split]
        else:
            inds = xrange(len(self.meta))
        image_paths = [self.meta[ind]['filename'] for ind in inds]
        names = [self.meta[ind]['name'] for ind in inds]
        labels = np.searchsorted(self.names, names)
        return image_paths, labels

    def img_classification_task(self, dtype='uint8', split=None):
        img_paths, labels = self.raw_classification_task(split=split)
        imgs = larray.lmap(ImgLoader(ndim=3, dtype=dtype, mode='RGB'),
                           img_paths)
        return imgs, labels


class Caltech101(BaseCaltech):
    URL = ('http://www.vision.caltech.edu/Image_Datasets/'
           'Caltech101/101_ObjectCategories.tar.gz')
    SHA1 = 'b8ca4fe15bcd0921dfda882bd6052807e63b4c96'
    SUBDIR = '101_ObjectCategories'


class Caltech256(BaseCaltech):
    URL = ('http://www.vision.caltech.edu/Image_Datasets/'
           'Caltech256/256_ObjectCategories.tar')
    SHA1 = '2195e9a478cf78bd23a1fe51f4dabe1c33744a1c'
    SUBDIR = '256_ObjectCategories'

########NEW FILE########
__FILENAME__ = dataset
"""
CIFAR-10 Image classification dataset

Data available from and described at:
http://www.cs.toronto.edu/~kriz/cifar.html

If you use this dataset, please cite "Learning Multiple Layers of Features from
Tiny Images", Alex Krizhevsky, 2009.
http://www.cs.toronto.edu/~kriz/learning-features-2009-TR.pdf

"""

# Authors: James Bergstra <bergstra@rowland.harvard.edu>
# License: BSD 3 clause

import os
import cPickle
import logging
import shutil

import numpy as np

from ..data_home import get_data_home
from ..utils.download_and_extract import download_and_extract

logger = logging.getLogger(__name__)

URL = 'http://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz'

LABELS = ['airplane', 'automobile', 'bird', 'cat', 'deer', 'dog', 'frog',
          'horse', 'ship', 'truck']

class CIFAR10(object):
    """

    meta[i] is dict with keys:
        id: int identifier of this example
        label: int in range(10)
        split: 'train' or 'test'

    meta_const is dict with keys:
        image:
            shape: 32, 32, 3
            dtype: 'uint8'


    """

    DOWNLOAD_IF_MISSING = True  # the value when accessing .meta

    def __init__(self):
        self.meta_const = dict(
                image = dict(
                    shape = (32, 32, 3),
                    dtype = 'uint8',
                    )
                )
        self.descr = dict(
                n_classes = 10,
                )

    def __get_meta(self):
        try:
            return self._meta
        except AttributeError:
            self.fetch(download_if_missing=self.DOWNLOAD_IF_MISSING)
            self._meta = self.build_meta()
            return self._meta
    meta = property(__get_meta)

    def home(self, *names):
        return os.path.join(get_data_home(), 'cifar10', *names)

    def fetch(self, download_if_missing):
        if os.path.isdir(self.home('cifar-10-batches-py')):
            return

        if not os.path.isdir(self.home()):
            if download_if_missing:
                os.makedirs(self.home())
            else:
                raise IOError(self.home())

        download_and_extract(URL, self.home())

    def clean_up(self):
        logger.info('recursively erasing %s' % self.home())
        if os.path.isdir(self.home()):
            shutil.rmtree(self.home())

    def build_meta(self):
        try:
            self._pixels
        except AttributeError:
            # load data into class attributes _pixels and _labels
            pixels = np.zeros((60000, 32, 32, 3), dtype='uint8')
            labels = np.zeros(60000, dtype='int32')
            fnames = ['data_batch_%i'%i for i in range(1,6)]
            fnames.append('test_batch')

            # load train and validation data
            n_loaded = 0
            for i, fname in enumerate(fnames):
                data = self.unpickle(fname)
                assert data['data'].dtype == np.uint8
                def futz(X):
                    return X.reshape((10000, 3, 32, 32)).transpose(0, 2, 3, 1)
                pixels[n_loaded:n_loaded + 10000] = futz(data['data'])
                labels[n_loaded:n_loaded + 10000] = data['labels']
                n_loaded += 10000
            assert n_loaded == len(labels)
            CIFAR10._pixels = pixels
            CIFAR10._labels = labels

            # -- mark memory as read-only to prevent accidental modification
            pixels.flags['WRITEABLE'] = False
            labels.flags['WRITEABLE'] = False

            assert LABELS == self.unpickle('batches.meta')['label_names']
        meta = [dict(
                    id=i,
                    split='train' if i < 50000 else 'test',
                    label=LABELS[l])
                for i,l in enumerate(self._labels)]
        return meta

    def unpickle(self, basename):
        fname = self.home('cifar-10-batches-py', basename)
        logger.info('loading file %s' % fname)
        fo = open(fname, 'rb')
        data = cPickle.load(fo)
        fo.close()
        return data


########NEW FILE########
__FILENAME__ = main
"""
A few helpful scripts specific to the CIFAR10 data set.

"""
import sys
import logging

from skdata.cifar10.dataset import CIFAR10

usage = """
Usage: main.py {fetch, show, clean_up}
"""


def main_fetch():
    """
    Download the CIFAR10 data set to the skdata cache dir
    """
    CIFAR10().fetch(True)


def main_show():
    """
    Use glumpy to launch a data set viewer.
    """
    from skdata.utils.glviewer import glumpy_viewer
    self = CIFAR10()
    Y = [m['label'] for m in self.meta]
    glumpy_viewer(
            img_array=self._pixels,
            arrays_to_print=[Y],
            window_shape=(32 * 4, 32 * 4))


def main_clean_up():
    """
    Delete all memmaps and data set files related to CIFAR10.
    """
    CIFAR10().clean_up()


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    if len(sys.argv) <= 1:
        print usage
        return 1
    else:
        try:
            fn = globals()['main_' + sys.argv[1]]
        except:
            print 'command %s not recognized' % sys.argv[1]
            print usage
            return 1
        return fn()


if __name__ == '__main__':
    sys.exit(main())


########NEW FILE########
__FILENAME__ = views
import logging
from sklearn.cross_validation import StratifiedShuffleSplit

import numpy as np

from .dataset import CIFAR10
from ..dslang import Task

logger = logging.getLogger(__name__)


class OfficialImageClassificationTask(object):
    def __init__(self, x_dtype='uint8', y_dtype='int', n_train=50000):
        if x_dtype not in ('uint8', 'float32'):
            raise TypeError()

        if y_dtype not in ('str', 'int'):
            raise TypeError()

        if not (0 <= n_train <= 50000):
            raise ValueError('n_train must fall in range(50000)', n_train)

        dataset = CIFAR10()
        dataset.meta  #trigger loading things

        y = dataset._labels
        if y_dtype == 'str':
            y = np.asarray(dataset.LABELS)[y]

        train = Task('image_classification',
                x=dataset._pixels[:n_train].astype(x_dtype),
                y=y[:n_train])
        test = Task('image_classification',
                x=dataset._pixels[50000:].astype(x_dtype),
                y=y[50000:])

        if 'float' in x_dtype:
            # N.B. that (a) _pixels are not writeable
            #      _pixels are uint8, so we must have copied
            train.x /= 255.0
            test.x /= 255.0

        self.dataset = dataset
        self.train = train
        self.test = test

class OfficialVectorClassificationTask(OfficialImageClassificationTask):
    def __init__(self, x_dtype='float32', y_dtype='int', n_train=50000):
        OfficialImageClassificationTask.__init__(self,
                x_dtype, y_dtype, n_train)
        self.train.x.shape = (len(self.train.x), 32 * 32 * 3)
        self.test.x.shape = (len(self.test.x), 32 * 32 * 3)


OfficialImageClassification = OfficialImageClassificationTask
OfficialVectorClassification = OfficialVectorClassificationTask


class StratifiedImageClassification(object):
    """
    Data set is partitioned at top level into a testing set (tst) and a model
    selection set (sel).  The selection set is subdivided into a fitting set
    (fit) and a validation set (val).

    The evaluation protocol is to fit a classifier to the (fit) set, and judge
    it on (val). The best model on (val) is re-trained on the entire selection
    set, and finally evaluated on the test set.

    """
    def __init__(self, dtype, n_train, n_valid, n_test, shuffle_seed=123,
            channel_major=False):


        assert n_train + n_valid <= 50000
        assert n_test <= 10000

        cf10 = CIFAR10()
        cf10.meta  # -- trigger data load
        if str(dtype) != str(cf10._pixels.dtype):
            raise NotImplementedError(dtype)

        # -- divide up the dataset as it was meant: train / test

        if shuffle_seed:
            rng = np.random.RandomState(shuffle_seed)
        else:
            rng = None

        ((fit_idxs, val_idxs),) = StratifiedShuffleSplit(
            y=cf10._labels[:50000],
            n_iterations=1,
            test_size=n_valid,
            train_size=n_train,
            indices=True,
            random_state=rng)

        sel_idxs = np.concatenate([fit_idxs, val_idxs])

        if n_test < 10000:
            ((ign_idxs, tst_idxs),) = StratifiedShuffleSplit(
                y=cf10._labels[50000:],
                n_iterations=1,
                test_size=n_test,
                indices=True,
                random_state=rng)
            tst_idxs += 50000
            del ign_idxs
        else:
            tst_idxs = np.arange(50000, 60000)

        self.dataset = cf10
        self.n_classes = 10
        self.fit_idxs = fit_idxs
        self.val_idxs = val_idxs
        self.sel_idxs = sel_idxs
        self.tst_idxs = tst_idxs

    def protocol(self, algo):
        for _ in self.protocol_iter(algo):
            pass
        return algo

    def protocol_iter(self, algo):

        def task(name, idxs):
            return Task(
                'indexed_image_classification',
                name=name,
                idxs=idxs,
                all_images=self.dataset._pixels,
                all_labels=self.dataset._labels,
                n_classes=self.n_classes)

        task_fit = task('fit', self.fit_idxs)
        task_val = task('val', self.val_idxs)
        task_sel = task('sel', self.sel_idxs)
        task_tst = task('tst', self.tst_idxs)


        model1 = algo.best_model(train=task_fit, valid=task_val)
        yield ('model validation complete', model1)

        model2 = algo.best_model(train=task_sel)
        algo.loss(model2, task_tst)
        yield ('model testing complete', model2)



########NEW FILE########
__FILENAME__ = data_home
"""Manage the scikit-data cache directory.

This folder is used by some large dataset loaders to avoid downloading the data
several times.

By default the data dir is set to a folder named '.scikit-data'
in the user home folder.  This directory can be specified prior to importing
this module via the SKDATA_ROOT environment variable.

After importing the module that environment variable is no longer consulted,
and a module-level variable called DATA_HOME becomes the new point of reference.

DATA_HOME can be read or modified directly, or via the two functions
get_data_home() and set_data_home(). Compared to the raw DATA_HOME variable,
the functions have the side effect of ensuring that the DATA_HOME directory
exists, and is readable.

"""

import os
import shutil

DATA_HOME = os.path.abspath(
    os.path.expanduser(
        os.environ.get(
            'SKDATA_ROOT',
            os.path.join('~', '.skdata'))))

def get_data_home():
    if not os.path.isdir(DATA_HOME):
        os.makedirs(DATA_HOME)
    # XXX: ensure it is dir and readable
    return DATA_HOME


def set_data_home(newpath):
    global DATA_HOME
    DATA_HOME = newpath
    return get_data_home()


def clear_data_home():
    """Delete all the content of the data home cache."""
    data_home = get_data_home()
    shutil.rmtree(data_home)

########NEW FILE########
__FILENAME__ = diabetes
"""
Diabetes - a small non-synthetic dataset for binary classification with
temporal data.

http://archive.ics.uci.edu/ml/datasets/Diabetes

"""
import csv
import os

import numpy as np

import utils

from .toy import BuildOnInit

class Diabetes(BuildOnInit):
    """Dataset of diabetes results (classification)

    meta[i] is dict with
        data: ?
        label: ?

    """
    # XXX:  what is this data?
    def build_meta(self):
        base_dir = os.path.join(os.path.dirname(__file__), 'data')
        data = np.loadtxt(os.path.join(base_dir, 'diabetes_data.csv.gz'))
        target = np.loadtxt(os.path.join(base_dir, 'diabetes_target.csv.gz'))
        itarget = map(int, target)
        assert all(itarget == target)
        assert len(data) == len(target)
        return [dict(d=d, l=l) for (d,l) in zip(data, itarget)]

    def classification_task(self):
        X = np.asarray([m['d'] for m in self.meta])
        y = np.asarray([m['l'] for m in self.meta])
        return X, y



########NEW FILE########
__FILENAME__ = digits
"""
Digits - small non-synthetic dataset of 10-way image classification

XXX: What's the source on this dataset?

"""
import csv
import os

import numpy as np

from .toy import BuildOnInit

class Digits(BuildOnInit):
    """Dataset of small digit images (classification)

    meta[i] is dict with
        img: an 8x8 ndarray
        label: int 0 <= label < 10
    """
    def build_all(self):
        module_path = os.path.dirname(__file__)
        data = np.loadtxt(os.path.join(module_path, 'data', 'digits.csv.gz'),
                          delimiter=',')
        descr = open(os.path.join(module_path, 'descr', 'digits.rst')).read()
        target = data[:, -1]
        images = np.reshape(data[:, :-1], (-1, 8, 8))
        assert len(images) == len(target)
        itarget = map(int, target)
        assert all(itarget == target)
        meta = [dict(img=i, label=t) for i, t in zip(images, itarget)]
        return meta, descr, {}

    def classification_task(self):
        X = np.asarray([m['img'].flatten() for m in self.meta])
        y = np.asarray([m['label'] for m in self.meta])
        return X, y

    # XXX: is img JSON-encodable ?
    # return img_classification_task interface


########NEW FILE########
__FILENAME__ = dslang
"""

AST elements of a DSL for describing cross-validation experiment protocols.

"""
import numpy as np

from .base import Task, Split

class Average(object):
    def __init__(self, values):
        self.values = values


class Score(object):
    def __init__(self, model, task):
        self.model = model
        self.task = task


class BestModel(object):
    """
    Return the best model for a given task.
    """
    def __init__(self, task):
        self.task = task


class BestModelByCrossValidation(object):
    """
    Return the best model on `split.test` by training on `split.train`.
    """
    def __init__(self, split):
        self.split = split


class RetrainClassifier(object):
    def __init__(self, model, task):
        self.model = model
        self.task = task


class TestModel(object):
    """
    Similar to Score() but returns model rather than score.

    The intent is for the visitor to measure test error and record it
    somewhere as a side-effect within the protocol graph.
    """
    def __init__(self, model, task):
        self.model = model
        self.task = task

#
#
#

class Visitor(object):

    def evaluate(self, node, memo):
        if memo is None:
            memo = {}

        if id(node) not in memo:
            fname = 'on_' + node.__class__.__name__
            rval = getattr(self, fname)(node, memo)
            memo[node] = rval

        return memo[node]

    def on_Average(self, node, memo):
        return np.mean([self.evaluate(value, memo) for value in node.values])

    def on_Score(self, node, memo):
        model = self.evaluate(node.model, memo)
        task = self.evaluate(node.task, memo)
        raise NotImplementedError('implement me')

    def on_BestModel(self, node, memo):
        split = self.evaluate(node.split, memo)
        raise NotImplementedError('implement me')

    def on_Train(self, node, memo):
        task = self.evaluate(node.task, memo)
        raise NotImplementedError('implement me')

    def on_Task(self, node, memo):
        return node

    def on_Split(self, node, memo):
        return node

    def on_TestModel(self, node, memo):
        model = self.evaluate(node.model, memo)
        task = self.evaluate(node.task, memo)
        raise NotImplementedError('implement me')


########NEW FILE########
__FILENAME__ = iicbu
# -*- coding: utf-8 -*-
"""IICBU 2008 Datasets

http://ome.grc.nia.nih.gov/iicbu2008

For more information, please refer to:

IICBU 2008 - A Proposed Benchmark Suite for Biological Image Analysis
Shamir, L., Orlov, N., Eckley, D.M., Macura, T., Goldberg, I.G.
Medical & Biological Engineering & Computing (2008)
Vol. 46, No. 9, pp. 943-947
http://ome.grc.nia.nih.gov/iicbu2008/IICBU2008-benchmark.pdf
"""

# Copyright (C) 2011
# Authors: Nicolas Pinto <pinto@rowland.harvard.edu>

# License: Simplified BSD

# XXX: standard categorization tasks (csv-based)


import os
from os import path
import shutil
from glob import glob
import hashlib

from data_home import get_data_home
from utils import download, extract


class BaseIICBU(object):
    """IICBU Biomedical Dataset

    Attributes
    ----------
    meta: list of dict
        Metadata associated with the dataset. For each image with index i,
        meta[i] is a dict with keys:
            name: str
                Name of the individual's face in the image.
            filename: str
                Full path to the image.
            id: int
                Identifier of the image.
            sha1: str
                SHA-1 hash of the image.

    Notes
    -----
    If joblib is available, then `meta` will be cached for faster
    processing. To install joblib use 'pip install -U joblib' or
    'easy_install -U joblib'.
    """

    EXTRACT_DIR = 'images'

    def __init__(self, meta=None):
        if meta is not None:
            self._meta = meta

        self.name = self.__class__.__name__

        try:
            from joblib import Memory
            mem = Memory(cachedir=self.home('cache'))
            self._get_meta = mem.cache(self._get_meta)
        except ImportError:
            pass

    def home(self, *suffix_paths):
        return path.join(get_data_home(), 'iicbu', self.name, *suffix_paths)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: fetch()
    # ------------------------------------------------------------------------

    def fetch(self, download_if_missing=True):
        """Download and extract the dataset."""

        home = self.home()

        if not download_if_missing:
            raise IOError("'%s' exists!" % home)

        # download archive
        url = self.URL
        sha1 = self.SHA1
        basename = path.basename(url)
        archive_filename = path.join(home, basename)
        if not path.exists(archive_filename):
            if not download_if_missing:
                return
            if not path.exists(home):
                os.makedirs(home)
            download(url, archive_filename, sha1=sha1)

        # extract it
        dst_dirname = self.home(self.EXTRACT_DIR)
        if not path.exists(dst_dirname):
            extract(archive_filename, dst_dirname, sha1=sha1, verbose=True)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: meta
    # ------------------------------------------------------------------------

    @property
    def meta(self):
        if hasattr(self, '_meta'):
            return self._meta
        else:
            self.fetch(download_if_missing=True)
            self._meta = self._get_meta()
            return self._meta

    def _get_meta(self):

        names = sorted(os.listdir(self.home(self.EXTRACT_DIR)))

        meta = []
        ind = 0

        for name in names:

            pattern = path.join(self.home(self.EXTRACT_DIR, name), '*.*')
            img_filenames = sorted(glob(pattern))

            for img_filename in img_filenames:
                img_data = open(img_filename, 'rb').read()
                sha1 = hashlib.sha1(img_data).hexdigest()

                data = dict(name=name,
                            id=ind,
                            filename=img_filename,
                            sha1=sha1)

                meta += [data]
                ind += 1

        return meta

    # ------------------------------------------------------------------------
    # -- Dataset Interface: clean_up()
    # ------------------------------------------------------------------------

    def clean_up(self):
        if path.isdir(self.home()):
            shutil.rmtree(self.home())

    # ------------------------------------------------------------------------
    # -- Standard Tasks
    # ------------------------------------------------------------------------
    # TODO


class Pollen(BaseIICBU):
    URL = 'http://ome.grc.nia.nih.gov/iicbu2008/pollen.tar.gz'
    SHA1 = '99014ff40054b244b98474cd26125c55a90e0970'


class RNAi(BaseIICBU):
    URL = 'http://ome.grc.nia.nih.gov/iicbu2008/rnai.tar.gz'
    SHA1 = '8de7f55c9a73b8d5050c8bc06f962de1d5a236ef'


class CelegansMuscleAge(BaseIICBU):
    URL = 'http://ome.grc.nia.nih.gov/iicbu2008/celegans.tar.gz'
    SHA1 = '244404cb9504d39f765d2bf161a1ba32809e7256'


class TerminalBulbAging(BaseIICBU):
    URL = 'http://ome.grc.nia.nih.gov/iicbu2008/terminalbulb.tar.gz'
    SHA1 = '2e81b3a5dea4df6c4e7d31f2999655084e54385b'


class Binucleate(BaseIICBU):
    URL = 'http://ome.grc.nia.nih.gov/iicbu2008/binucleate.tar.gz'
    SHA1 = '7c0752899519b286c0948eb145fb2b6bd2bd2134'


class Lymphoma(BaseIICBU):
    URL = 'http://ome.grc.nia.nih.gov/iicbu2008/lymphoma.tar.gz'
    SHA1 = '5af6bf000a9f7d0bb9b54ae0558fbeccc1758fe6'

#http://ome.grc.nia.nih.gov/iicbu2008/agemap/index.html'
#class LiverGenderCR(BaseIICBU):
#class LiverGenderAL(BaseIICBU):
#class LiverAging(BaseIICBU):

class Hela2D(BaseIICBU):
    URL = 'http://ome.grc.nia.nih.gov/iicbu2008/hela.tar.gz'
    SHA1 = 'f5b13a8efd19dee9c53ab8da5ea6c017fdfb65a2'


class CHO(BaseIICBU):
    URL = 'http://ome.grc.nia.nih.gov/iicbu2008/cho.tar.gz'
    SHA1 = '0c55f49d34f50ef0a0d526afde0fa16fee07ba08'

########NEW FILE########
__FILENAME__ = dataset
"""

Iris Plants Database
====================

Notes
-----
Data Set Characteristics:
    :Number of Instances: 150 (50 in each of three classes)
    :Number of Attributes: 4 numeric, predictive attributes and the class
    :Attribute Information:
        - sepal length in cm
        - sepal width in cm
        - petal length in cm
        - petal width in cm
        - class:
                - Iris-Setosa
                - Iris-Versicolour
                - Iris-Virginica
    :Summary Statistics:
    ============== ==== ==== ======= ===== ====================
                    Min  Max   Mean    SD   Class Correlation
    ============== ==== ==== ======= ===== ====================
    sepal length:   4.3  7.9   5.84   0.83    0.7826
    sepal width:    2.0  4.4   3.05   0.43   -0.4194
    petal length:   1.0  6.9   3.76   1.76    0.9490  (high!)
    petal width:    0.1  2.5   1.20  0.76     0.9565  (high!)
    ============== ==== ==== ======= ===== ====================
    :Missing Attribute Values: None
    :Class Distribution: 33.3% for each of 3 classes.
    :Creator: R.A. Fisher
    :Donor: Michael Marshall (MARSHALL%PLU@io.arc.nasa.gov)
    :Date: July, 1988

This is a copy of UCI ML iris datasets.
http://archive.ics.uci.edu/ml/datasets/Iris

The famous Iris database, first used by Sir R.A Fisher

This is perhaps the best known database to be found in the
pattern recognition literature.  Fisher's paper is a classic in the field and
is referenced frequently to this day.  (See Duda & Hart, for example.)  The
data set contains 3 classes of 50 instances each, where each class refers to a
type of iris plant.  One class is linearly separable from the other 2; the
latter are NOT linearly separable from each other.

References
----------
   - Fisher,R.A. "The use of multiple measurements in taxonomic problems"
     Annual Eugenics, 7, Part II, 179-188 (1936); also in "Contributions to
     Mathematical Statistics" (John Wiley, NY, 1950).
   - Duda,R.O., & Hart,P.E. (1973) Pattern Classification and Scene Analysis.
     (Q327.D83) John Wiley & Sons.  ISBN 0-471-22361-1.  See page 218.
   - Dasarathy, B.V. (1980) "Nosing Around the Neighborhood: A New System
     Structure and Classification Rule for Recognition in Partially Exposed
     Environments".  IEEE Transactions on Pattern Analysis and Machine
     Intelligence, Vol. PAMI-2, No. 1, 67-71.
   - Gates, G.W. (1972) "The Reduced Nearest Neighbor Rule".  IEEE Transactions
     on Information Theory, May 1972, 431-433.
   - See also: 1988 MLC Proceedings, 54-64.  Cheeseman et al"s AUTOCLASS II
     conceptual clustering system finds 3 classes in the data.
   - Many, many more ...

"""

import csv
import os

import numpy as np

from ..toy import BuildOnInit


class Iris(BuildOnInit):
    """Dataset of flower properties (classification)

    self.meta has elements with following structure:

        meta[i] = dict
            sepal_length: float
            sepal_width: float
            petal_length: float
            petal_width: float
            name: one of 'setosa', 'versicolor', 'virginica'

    There are 150 examples.

    """
    def build_meta(self):
        module_path = os.path.dirname(__file__)
        data_file = csv.reader(open(os.path.join(module_path, 'iris.csv')))
        temp = data_file.next()
        n_samples = int(temp[0])
        n_features = int(temp[1])
        target_names = np.array(temp[2:])
        temp = list(data_file)
        data = [map(float, t[:-1]) for t in temp]
        target = [target_names[int(t[-1])] for t in temp]
        meta = [dict(
            sepal_length=d[0],
            sepal_width=d[1],
            petal_length=d[2],
            petal_width=d[3],
            name=t)
                for d, t in zip(data, target)]
        return meta


########NEW FILE########
__FILENAME__ = tests

from sklearn.svm import LinearSVC
from skdata.iris.view import KfoldClassification
from skdata.base import SklearnClassifier


def test_protocol(cls=LinearSVC, N=1, show=True, net=None):
    ### run on 36 subjects
    algo = SklearnClassifier(cls)

    pk = KfoldClassification(4)
    mean_test_error = pk.protocol(algo)

    assert len(algo.results['loss']) == 4
    assert len(algo.results['best_model']) == 4

    print cls
    for loss_report in algo.results['loss']:
        print loss_report['task_name'] + \
            (": err = %0.3f" % (loss_report['err_rate']))

    assert mean_test_error < 0.1


########NEW FILE########
__FILENAME__ = view
"""
Experiment views on the Iris data set.

"""

import numpy as np
from sklearn import cross_validation

from .dataset import Iris
from ..base import Task
from ..utils import int_labels


class KfoldClassification(object):
    """
    Access train/test splits for K-fold cross-validation as follows:

    >>> self.splits[k].train.x
    >>> self.splits[k].train.y
    >>> self.splits[k].test.x
    >>> self.splits[k].test.y

    """

    def __init__(self, K, rseed=1):
        self.K = K
        self.dataset = Iris()
        self.rseed = rseed

    def task(self, name, x, y, split_idx=None):
        return Task('vector_classification',
                    name=name,
                    x=np.asarray(x),
                    y=np.asarray(y),
                    n_classes=3,
                    split_idx=split_idx,
                   )

    def protocol(self, algo, stop_after=None):
        x_all = np.asarray([
                [
                    m['sepal_length'],
                    m['sepal_width'],
                    m['petal_length'],
                    m['petal_width'],
                    ]
                for m in self.dataset.meta])
        y_all = np.asarray(int_labels([m['name'] for m in self.dataset.meta]))

        kf = cross_validation.KFold(len(y_all), self.K)
        idxmap = np.random.RandomState(self.rseed).permutation(len(y_all))

        losses = []

        for i, (train_idxs, test_idxs) in enumerate(kf):
            if stop_after is not None and i >= stop_after:
                break
            train = self.task(
                'train_%i' % i,
                x=x_all[idxmap[train_idxs]],
                y=y_all[idxmap[train_idxs]])
            test = self.task(
                'test_%i' % i,
                x=x_all[idxmap[test_idxs]],
                y=y_all[idxmap[test_idxs]])

            model = algo.best_model(train=train, valid=None)
            losses.append(algo.loss(model, test))

        return np.mean(losses)


class SimpleCrossValidation(object):
    """ Simple demo version of KfoldClassification that stops
    after a single fold for brevity.
    """
    def __init__(self):
        self.kfold = KfoldClassification(5)

    def protocol(self, algo):
        return self.kfold.protocol(algo, stop_after=1)



########NEW FILE########
__FILENAME__ = dataset
"""
This data set was released as the

"Challengest in Representation Learning:
Facial Expression Recognition Challenge"

on Kaggle on April 12 2013, as part of an ICML-2013 workshop on representation
learning.

Kaggle Contest Description Text
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The data consists of 48x48 pixel grayscale images of faces. The faces have
been automatically registered so that the face is more or less centered and
occupies about the same amount of space in each image. The task is to
categorize each face based on the emotion shown in the facial expression in to
one of seven categories (0=Angry, 1=Disgust, 2=Fear, 3=Happy, 4=Sad,
5=Surprise, 6=Neutral).

train.csv contains two columns, "emotion" and "pixels". The "emotion" column
contains a numeric code ranging from 0 to 6, inclusive, for the emotion that
is present in the image. The "pixels" column contains a string surrounded in
quotes for each image. The contents of this string a space-separated pixel
values in row major order. test.csv contains only the "pixels" column and your
task is to predict the emotion column.

The training set consists of 28,709 examples. The public test set used for the
leaderboard consists of 3,589 examples. The final test set, to be released 72
hours before the end of the competition, consists of another 3,589 examples.

This dataset was prepared by Pierre-Luc Carrier and Aaron Courville, as part
of an ongoing research project. They have graciously provided the workshop
organizers with a preliminary version of their dataset to use for this
contest.

"""

import cPickle
import lockfile
import logging
import os
import shutil

import numpy as np

from skdata.data_home import get_data_home
from skdata.utils.download_and_extract import verify_sha1, extract

logger = logging.getLogger(__name__)

FILES_SHA1s = [
    ('test.csv', '3f9199ae6e9a40137e72cb63264490e622d9c798'),
    ('train.csv', '97651a1fffc7e0af22ebdd5de36700b0e7e0c12c'),
    ('example_submission.csv', '14fac7ef24e3ab6d9fcaa9edd273fe08abfa5c51')]

TGZ_FILENAME = 'fer2013.tar.gz'

FULL_URL = '/'.join([
    'http://www.kaggle.com',
    'c',
    ('challenges-in-representation-learning'
     '-facial-expression-recognition-challenge'),
    'download',
    TGZ_FILENAME])

TGZ_SHA1 = 'b0e7632c70853f4d3b6a2a73031dd8c71d8d536d'


class KaggleFacialExpression(object):
    N_TRAIN = 28709
    N_TEST = 7178

    def __init__(self):
        self.name = 'kaggle_facial_expression'

    def home(self, *suffix_paths):
        return os.path.join(get_data_home(), self.name, *suffix_paths)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: fetch()
    # ------------------------------------------------------------------------

    def install(self, local_fer2013):
        """
        Verify SHA1 and copy given file into .skdata cache directory.
        """
        verify_sha1(local_fer2013, TGZ_SHA1)
        if not os.path.isdir(self.home()):
            os.makedirs(self.home())
        lock = lockfile.FileLock(self.home())
        if lock.is_locked():
            logger.warn('%s is locked, waiting for release' % self.home())

        with lock:
            shutil.copyfile(local_fer2013, self.home(TGZ_FILENAME))
            extract(self.home(TGZ_FILENAME), self.home())

    @property
    def meta(self):
        try:
            return self._meta
        except AttributeError:
            self._meta = self._get_meta()
            return self._meta

    def _get_meta(self):
        filename = 'meta_%s.pkl' % self._build_meta_version
        try:
            if self._build_meta_version:
                meta = cPickle.load(open(self.home(filename)))
            else:
                raise IOError()
        except (IOError, cPickle.PickleError), e:
            meta = self._build_meta()
            outfile = open(self.home(filename), 'wb')
            cPickle.dump(meta, outfile, -1)
            outfile.close()
        return meta

    _build_meta_version = '3'
    def _build_meta(self):
        meta = []

        # -- load train.csv
        for ii, line in enumerate(open(self.home('fer2013', 'fer2013.csv'))):
            if ii == 0:
                continue
            label, pixels, usage = line.split(',')
            assert int(label) < 7
            if 0:
                assert pixels[-3] == '"'
                assert pixels[0] == '"'
                pixels = np.asarray(map(int, pixels[1:-3].split(' ')), dtype=np.uint8)
            else:
                pixels = np.asarray(map(int, pixels.split(' ')), dtype=np.uint8)
            meta.append({
                'label': int(label),
                'pixels': pixels.reshape(48, 48),
                'usage': usage.strip(' \n'),
                })

        return meta



########NEW FILE########
__FILENAME__ = main
import sys
import logging
import time

from skdata.kaggle_facial_expression.dataset \
        import KaggleFacialExpression, FULL_URL

usage = """
Usage: main.py {bib, clean_up, install, show, stats}
"""

def main_install():
    """
    Download the CIFAR10 data set to the skdata cache dir
    """
    try:
        KaggleFacialExpression().install(sys.argv[2])
    except IndexError:
        print "To download the Facial Recognition Challenge dataset"
        print "log into Kaggle and retrieve", FULL_URL
        print "then run this script again with the downloaded filename"
        print "as an argument, like:"
        print "python -m %s.main install fer2013.tgz" % __package__


def main_bib():
    """
    Print out the proper citation for this dataset.
    """
    print open(KaggleFacialExpression().home('fer2013', 'fer2013.bib')).read()


def main_stats():
    """
    Print some basic stats about the dataset (proving that it can be loaded).
    """
    self = KaggleFacialExpression()
    t0 = time.time()
    print 'loading dataset ...'
    meta = self.meta
    print ' ... done. (%.2f seconds)' % (time.time() - t0)
    print ''
    print 'n. Examples', len(meta)
    #print 'Usages', set([m['usage'] for m in meta])
    print 'n. Training', len([m for m in meta if m['usage'] == 'Training'])
    print 'n. PublicTest', len([m for m in meta if m['usage'] == 'PublicTest'])
    print 'n. PrivateTest', len([m for m in meta if m['usage'] == 'PrivateTest'])


def main_show():
    """
    Use glumpy to launch a data set viewer.
    """
    self = KaggleFacialExpression()
    from skdata.utils.glviewer import glumpy_viewer
    glumpy_viewer(
            img_array=[m['pixels'] for m in self.meta],
            arrays_to_print=self.meta,
            window_shape=(48 * 4, 48 * 4))


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    if len(sys.argv) <= 1:
        print usage
        return 1
    else:
        try:
            fn = globals()['main_' + sys.argv[1]]
        except:
            print 'command %s not recognized' % sys.argv[1]
            print usage
            return 1
        return fn()

if __name__ == '__main__':
    sys.exit(main())



########NEW FILE########
__FILENAME__ = test
from unittest import TestCase
from functools import partial

import nose
import numpy as np
try:
    import sklearn.svm
except ImportError:
    pass

from dataset import KaggleFacialExpression
from view import ContestCrossValid
from ..base import DatasetNotPresent
from ..base import SklearnClassifier

ds = KaggleFacialExpression()
try:
    ds.fetch()
    skip_all = False
except DatasetNotPresent:
    skip_all = True

class TestKFE(TestCase):

    def setUp(self):
        if skip_all:
            raise nose.SkipTest()

    def test_len_train(self):
        n = len([mi for mi in ds.meta
            if mi['file'] == 'train.csv'])
        assert n == KaggleFacialExpression.N_TRAIN, n

    def test_len_test(self):
        n = len([mi for mi in ds.meta
            if mi['file'] == 'test.csv'])
        assert n == KaggleFacialExpression.N_TEST, n


class TestContestXV(TestCase):
    def setUp(self):
        if skip_all:
            raise nose.SkipTest()
        self.xv = ContestCrossValid(
                n_train=ContestCrossValid.max_n_train - 7500,
                n_valid=7500,
                ds=ds)

    def test_protocol_smoke(self):
        # -- smoke test that it just runs
        class Algo(object):
            def best_model(algo_self, train, valid=None):
                # -- all training labels should be legit
                assert np.all(train.all_labels[train.idxs] < 7)
                assert np.all(train.all_labels[train.idxs] >= 0)

                # -- N.B. test labels might be unknown, and 
                #    replaced with dummy ones which may or may
                #    not be in range(7)
                return None

            def loss(algo_self, model, task):
                return 1.0

        algo = Algo()
        self.xv.protocol(algo)

    def test_protocol_svm(self):
        if 'sklearn' not in globals():
            raise nose.SkipTest()
        self.xv = ContestCrossValid(
                n_train=200,
                n_valid=100,
                ds=ds)
        algo = SklearnClassifier(
            partial(sklearn.svm.SVC, kernel='linear'))
        self.xv.protocol(algo)
        print algo.results


########NEW FILE########
__FILENAME__ = view
"""
Specific learning problems for the kaggle_facial_expression dataset.

"""
import numpy as np

from sklearn.cross_validation import StratifiedShuffleSplit

from ..dslang import Task

from dataset import KaggleFacialExpression


class ContestCrossValid(object):
    """
    This View implements the official contest evaluation protocol.
    
    https://www.kaggle.com/c/challenges-in-representation-learning-facial
    -expression-recognition-challenge

    """
    max_n_train = KaggleFacialExpression.N_TRAIN
    max_n_test = KaggleFacialExpression.N_TEST

    def __init__(self, x_dtype=np.float32,
                 n_train=max_n_train,
                 n_valid=0,
                 n_test=max_n_test,
                 shuffle_seed=123,
                 channel_major=False,
                 ds=None
                ):

        if ds is None:
            ds = KaggleFacialExpression()

        assert n_train + n_valid <= self.max_n_train
        assert n_test <= self.max_n_test

        if shuffle_seed:
            rng = np.random.RandomState(shuffle_seed)
        else:
            rng = None

        # examples x rows x cols
        all_pixels = np.asarray([mi['pixels'] for mi in ds.meta])
        all_labels = np.asarray([mi['label'] for mi in ds.meta],
                                dtype='int32')

        assert len(all_pixels) == self.max_n_test + self.max_n_train

        if channel_major:
            all_images = all_pixels[:, None, :, :].astype(x_dtype)
        else:
            all_images = all_pixels[:, :, :, None].astype(x_dtype)

        if 'float' in str(x_dtype):
            all_images /= 255

        for ii in xrange(self.max_n_train):
            assert ds.meta[ii]['usage'] == 'Training'

        if n_train < self.max_n_train:
            ((fit_idxs, val_idxs),) = StratifiedShuffleSplit(
                y=all_labels[:self.max_n_train],
                n_iterations=1,
                test_size=n_valid,
                train_size=n_train,
                indices=True,
                random_state=rng)
        else:
            fit_idxs = np.arange(self.max_n_train)
            val_idxs = np.arange(0)

        sel_idxs = np.concatenate([fit_idxs, val_idxs])
        if n_test < self.max_n_test:
            ((ign_idxs, tst_idxs),) = StratifiedShuffleSplit(
                y=all_labels[self.max_n_train:],
                n_iterations=1,
                test_size=n_test,
                indices=True,
                random_state=rng)
            tst_idxs += self.max_n_train
            del ign_idxs
        else:
            tst_idxs = np.arange(self.max_n_train, len(all_labels))

        self.dataset = ds
        self.n_classes = 7
        self.fit_idxs = fit_idxs
        self.val_idxs = val_idxs
        self.sel_idxs = sel_idxs
        self.tst_idxs = tst_idxs
        self.all_labels = all_labels
        self.all_images = all_images

    def protocol(self, algo):
        for _ in self.protocol_iter(algo):
            pass
        return algo

    def protocol_iter(self, algo):

        def task(name, idxs):
            return Task(
                'indexed_image_classification',
                name=name,
                idxs=idxs,
                all_images=self.all_images,
                all_labels=self.all_labels,
                n_classes=self.n_classes)

        task_fit = task('fit', self.fit_idxs)
        task_val = task('val', self.val_idxs)
        task_sel = task('sel', self.sel_idxs)
        task_tst = task('tst', self.tst_idxs)

        if len(self.val_idxs):
            model1 = algo.best_model(train=task_fit, valid=task_val)
            yield ('model validation complete', model1)

        model2 = algo.best_model(train=task_sel)
        algo.loss(model2, task_tst)
        yield ('model testing complete', model2)


########NEW FILE########
__FILENAME__ = dataset
"""MNIST Variations, Rectanges, and Convex from Larochelle et al. 2007

http://www.iro.umontreal.ca/~lisa/twiki/pub/Public/DeepVsShallowComparisonICML2007

Datasets:

- convex
- rectangles
- rectangles images
- mnist basic
- mnist rotated
- mnist background images
- mnist background random
- mnist noise {1,2,3,4,5,6}

These datasets were introduced in the paper:

"An Empirical Evaluation of Deep Architectures on Problems with Many Factors of
Variation"
H. Larochelle, D. Erhan, A. Courville, J. Bergstra and Y. Bengio.
In Proc. of International Conference on Machine Learning (2007).

"""

# Authors: James Bergstra <bergstra@rowland.harvard.edu>
# License: BSD 3 clause

#
# ISSUES (XXX)
# ------------
# - These datasets are all built algorithmically by modifying image datasets.
#   It would be nice to have the code for those modifications in this file.
#   The original matlab code is available here:
#     http://www.iro.umontreal.ca/~lisa/twiki/pub/Public/
#     DeepVsShallowComparisonICML2007/scripts_only.tar.gz
#

import array  # XXX why is this used not numpy?
import os
import shutil

import numpy as np

import lockfile

from ..data_home import get_data_home
from .. import utils

import logging
logger = logging.getLogger(__name__)

# TODO: standardize the API for downloading papers describing a dataset?
PAPER_URL = '/'.join([
        'http://www.iro.umontreal.ca/~lisa/twiki/pub/Public'
        'Public/DeepVsShallowComparisonICML2007',
        'icml-2007-camera-ready.pdf'])


class AMat:
    """access a plearn amat file as a periodic unrandomized stream

    Attributes:

    input -- all columns of input
    target -- all columns of target
    weight -- all columns of weight
    extra -- all columns of extra

    all -- the entire data contents of the amat file
    n_examples -- the number of training examples in the file

    AMat stands for Ascii Matri[x,ces]

    """

    marker_size = '#size:'
    marker_sizes = '#sizes:'
    marker_col_names = '#:'

    def __init__(self, path, head=None):

        """Load the amat at <path> into memory.
        path - str: location of amat file
        head - int: stop reading after this many data rows

        """
        logger.info('Loading AMat: %s' % path)
        self.all = None
        self.input = None
        self.target = None
        self.weight = None
        self.extra = None

        self.header = False
        self.header_size = None
        self.header_rows = None
        self.header_cols = None
        self.header_sizes = None
        self.header_col_names = []

        data_started = False
        data = array.array('d')

        f = open(path)
        n_data_lines = 0
        len_float_line = None

        for i, line in enumerate(f):
            if n_data_lines == head:
                # we've read enough data,
                # break even if there's more in the file
                break
            if len(line) == 0 or line == '\n':
                continue
            if line[0] == '#':
                if not data_started:
                    # the condition means that the file has a header, and we're
                    # on some header line
                    self.header = True
                    if line.startswith(AMat.marker_size):
                        info = line[len(AMat.marker_size):]
                        self.header_size = [int(s) for s in info.split()]
                        self.header_rows, self.header_cols = self.header_size
                    if line.startswith(AMat.marker_col_names):
                        info = line[len(AMat.marker_col_names):]
                        self.header_col_names = info.split()
                    elif line.startswith(AMat.marker_sizes):
                        info = line[len(AMat.marker_sizes):]
                        self.header_sizes = [int(s) for s in info.split()]
            else:
                #the first non-commented line tells us that the header is done
                data_started = True
                float_line = [float(s) for s in line.split()]
                if len_float_line is None:
                    len_float_line = len(float_line)
                    if (self.header_cols is not None) \
                            and self.header_cols != len_float_line:
                        logger.warn(('header declared %i cols'
                            ' but first line has %i, using %i') % (
                            self.header_cols, len_float_line,
                            len_float_line))
                else:
                    if len_float_line != len(float_line):
                        raise IOError('wrong line length', i, line)
                data.extend(float_line)
                n_data_lines += 1

        f.close()

        # convert from array.array to np.ndarray
        nshape = (len(data) / len_float_line, len_float_line)
        self.all = np.frombuffer(data).reshape(nshape)
        self.n_examples = self.all.shape[0]
        logger.info('AMat loaded all shape: %s' % repr(self.all.shape))

        # assign
        if self.header_sizes is not None:
            if len(self.header_sizes) > 4:
                logger.warn('ignoring sizes after 4th in %s' % path)
            leftmost = 0
            #here we make use of the fact that if header_sizes has len < 4
            # the loop will exit before 4 iterations
            attrlist = ['input', 'target', 'weight', 'extra']
            for attr, ncols in zip(attrlist, self.header_sizes):
                setattr(self, attr, self.all[:, leftmost:leftmost + ncols])
                leftmost += ncols
            logger.info('AMat loaded %s shape: %s' % (attr,
                repr(getattr(self, attr).shape)))
        else:
            logger.info('AMat had no header: %s' % path)


class BaseL2007(object):
    """Base class for fetching and loading Larochelle etal datasets

    This class has functionality to:

    - download the dataset from the internet  (in amat format)
    - convert the dataset from amat format to npy format
    - load the dataset from either amat or npy source files

    meta[i] is a dict with keys:
        id: int identifier of this example
        label: int in range(10)
        split: 'train', 'valid', or 'test'

    meta_const is dict with keys:
        image:
            shape: 28, 28
            dtype: 'float32'

    """

    BASE_URL = 'http://www.iro.umontreal.ca/~lisa/icml2007data'
    DOWNLOAD_IF_MISSING = True  # value used on first access to .meta
    MMAP_MODE = 'r'             # _labels and _inputs are loaded this way.
                                # See numpy.load / numpy.memmap for semantics.
    TRANSPOSE_IMAGES = False    # Some of the datasets were saved sideways.

    meta_const = dict(
            image=dict(
                shape=(28, 28),
                dtype='float32'))

    def home(self, *names):
        return os.path.join(
                get_data_home(),
                'larochelle_etal_2007',
                self.NAME,
                *names)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: fetch()
    # ------------------------------------------------------------------------

    def test_amat(self):
        return self.home(self.AMAT + '_test.amat')

    def train_amat(self):
        return self.home(self.AMAT + '_train.amat')

    def fetch(self, download_if_missing):
        if not os.path.isdir(self.home()):
            os.makedirs(self.home())
        with lockfile.FileLock(self.home()):
            try:
                open(self.home(self.NAME + '_inputs.npy')).close()
                open(self.home(self.NAME + '_labels.npy')).close()
            except IOError:
                if download_if_missing:
                    try:
                        amat_test = AMat(self.test_amat())
                    except IOError:
                        logger.info('Failed to read %s, downloading %s' % (
                            self.test_amat(),
                            os.path.join(self.BASE_URL, self.REMOTE)))
                        if not os.path.exists(self.home()):
                            os.makedirs(self.home())
                        utils.download_and_extract(
                            os.path.join(self.BASE_URL, self.REMOTE),
                            self.home(),
                            verbose=False,
                            sha1=self.SHA1)
                        amat_test = AMat(self.test_amat())
                    amat_train = AMat(self.train_amat())
                    n_inputs = 28**2
                    n_train = self.descr['n_train']
                    n_valid = self.descr['n_valid']
                    n_test = self.descr['n_test']
                    assert amat_train.all.shape[0] == n_train + n_valid
                    assert amat_test.all.shape[0] == n_test
                    assert amat_train.all.shape[1] == amat_test.all.shape[1]
                    assert amat_train.all.shape[1] == n_inputs + 1
                    allmat = np.vstack((amat_train.all, amat_test.all))
                    inputs = np.reshape(
                            allmat[:, :n_inputs].astype('float32'),
                            (-1, 28, 28))
                    labels = allmat[:, n_inputs].astype('int32')
                    assert np.all(labels == allmat[:, n_inputs])
                    assert np.all(labels < self.descr['n_classes'])
                    np.save(self.home(self.NAME + '_inputs.npy'), inputs)
                    np.save(self.home(self.NAME + '_labels.npy'), labels)
                    # clean up the .amat files we downloaded
                    os.remove(self.test_amat())
                    os.remove(self.train_amat())
                else:
                    raise

    # ------------------------------------------------------------------------
    # -- Dataset Interface: meta
    # ------------------------------------------------------------------------

    def __get_meta(self):
        try:
            return self._meta
        except AttributeError:
            self.fetch(download_if_missing=self.DOWNLOAD_IF_MISSING)
            self._meta = self.build_meta()
            return self._meta
    meta = property(__get_meta)

    def build_meta(self):
        try:
            self._labels
        except AttributeError:
            # load data into class attributes _pixels and _labels
            inputs = np.load(self.home(self.NAME + '_inputs.npy'),
                    mmap_mode=self.MMAP_MODE)
            labels = np.load(self.home(self.NAME + '_labels.npy'),
                    mmap_mode=self.MMAP_MODE)
            if self.TRANSPOSE_IMAGES:
                inputs = inputs.transpose(0, 2, 1)
            self.__class__._inputs = inputs
            self.__class__._labels = labels
            assert len(inputs) == len(labels)

        def split_of_pos(i):
            if i < self.descr['n_train']:
                return 'train'
            if i < self.descr['n_train'] + self.descr['n_valid']:
                return 'valid'
            return 'test'

        assert len(self._labels) == sum(
                [self.descr[s] for s in 'n_train', 'n_valid', 'n_test'])

        meta = [dict(id=i, split=split_of_pos(i), label=l)
                for i, l in enumerate(self._labels)]

        return meta

    # ------------------------------------------------------------------------
    # -- Dataset Interface: clean_up()
    # ------------------------------------------------------------------------

    def clean_up(self):
        if os.path.isdir(self.home()):
            shutil.rmtree(self.home())

    # ------------------------------------------------------------------------
    # -- Driver routines to be called by skdata.main
    # ------------------------------------------------------------------------

    @classmethod
    def main_fetch(cls):
        cls().fetch(download_if_missing=True)

    @classmethod
    def main_show(cls):
        from utils.glviewer import glumpy_viewer, glumpy
        self = cls()
        labels = [m['label'] for m in self.meta]
        glumpy_viewer(
                img_array=self._inputs,
                arrays_to_print=[labels],
                cmap=glumpy.colormap.Grey,
                window_shape=(28 * 3, 28 * 3))

    @classmethod
    def main_clean_up(cls):
        cls().clean_up()

    # ------------------------------------------------------------------------
    # -- Task Interface: constructors for standard tasks
    # ------------------------------------------------------------------------

    def classification_task(self):
        #XXX: use .meta
        self.meta   # touch self.meta to ensure it's been built
        y = self._labels
        X = self.latent_structure_task()
        return X, y

    def latent_structure_task(self):
        #XXX: use .meta
        self.meta   # touch self.meta to ensure it's been built
        # Consider: is it right to use TRANSPOSE_IMAGES to un-transpose?
        #      pro - it prevents a usually un-necessary copy
        #      con - it means the pixels aren't in a standard point in the 784
        #            feature vector.
        #      I think con wins here, it's better to make the copy and have
        #      standard features.  In the future the TRANSPOSE_IMAGES should be
        #      consulted during fetch, before even writing the npy file.
        #      XXX: use TRANSPOSE_IMAGES during fetch.
        return self._inputs.reshape((-1, 784))


#
# MNIST Variations
#

class BaseMNIST(BaseL2007):
    descr = dict(
            n_classes=10,
            n_train=10000,
            n_valid=2000,
            n_test=50000
            )


class MNIST_Basic(BaseMNIST):
    REMOTE = 'mnist.zip'  # fetch BASE_URL/REMOTE
    SHA1 = '14ac2e9135705499b80bf7efac981377940150c8'
    REMOTE_SIZE = '23M'
    AMAT = 'mnist'        # matches name unzip'd from REMOTE
    NAME = 'mnist_basic'  # use this as root filename for saved npy files


class MNIST_BackgroundImages(BaseMNIST):
    TRANSPOSE_IMAGES = True
    REMOTE = 'mnist_background_images.zip'
    SHA1 = 'fb6fce9ed6372e0068ff7cb3e7b9e78dbda7ceae'
    REMOTE_SIZE = '88M'
    AMAT = 'mnist_background_images'
    NAME = 'mnist_background_images'


class MNIST_BackgroundRandom(BaseMNIST):
    TRANSPOSE_IMAGES = True
    REMOTE = 'mnist_background_random.zip'
    SHA1 = '75e11ec966459c1162979e78ab4e21f9ab7fb5cd'
    REMOTE_SIZE = '219M'
    AMAT = 'mnist_background_random'
    NAME = 'mnist_background_random'


class MNIST_Rotated(BaseMNIST):
    """
    There are two versions of this dataset available for download.

    1. the original dataset used in the ICML paper.

    2. a corrected dataset used to produce revised numbers for the web page
       version of the paper.

    This class loads the corrected dataset.
    """
    REMOTE = 'mnist_rotation_new.zip'
    SHA1 = 'e67f72fa42029f62fd8eb92b0638c1b9761c9a63'
    REMOTE_SIZE = '56M'
    NAME = 'mnist_rotated'

    def test_amat(self):
        return self.home(
                'mnist_all_rotation_normalized_float_test.amat')

    def train_amat(self):
        return self.home(
                'mnist_all_rotation_normalized_float_train_valid.amat')


class MNIST_RotatedBackgroundImages(BaseMNIST):
    """
    There are two versions of this dataset available for download.

    1. the original dataset used in the ICML paper.

    2. a corrected dataset used to produce revised numbers for the web page
       version of the paper.

    This class loads the corrected dataset.
    """
    REMOTE = 'mnist_rotation_back_image_new.zip'
    SHA1 = '902bb7e96136dd76e9f2924d7fdb9eb832f7bc33'
    REMOTE_SIZE = '115M'
    NAME = 'mnist_rotated_background_images'

    def test_amat(self):
        return self.home(
            'mnist_all_background_images_rotation_normalized_test.amat')

    def train_amat(self):
        return self.home(
            'mnist_all_background_images_rotation_normalized_train_valid.amat')


class BaseNoise(BaseMNIST):
    TRANSPOSE_IMAGES = True
    REMOTE = 'mnist_noise_variation.tar.gz'
    SHA1 = '2d2cfa47c4aa51cc7a8fd1e52abadc7df4b7bfbd'
    REMOTE_SIZE = '304M'
    descr = dict(
            n_classes=10,
            n_train=10000,
            n_valid=2000,
            n_test=2000
            )

    def __init__(self, level=None):
        if level is not None:
            self.LEVEL = level
        self.NAME = 'mnist_noise_%i' % self.LEVEL

    def level_amat(self, level):
        return self.home(
                'mnist_noise_variations_all_%i.amat' % level)

    def fetch(self, download_if_missing):
        try:
            open(self.home(self.NAME + '_inputs.npy')).close()
            open(self.home(self.NAME + '_labels.npy')).close()
        except IOError:
            if download_if_missing:
                all_amat_filename = self.level_amat(self.LEVEL)
                try:
                    amat_all = AMat(all_amat_filename)
                except IOError:
                    logger.info('Failed to read %s, downloading %s' % (
                        all_amat_filename,
                        os.path.join(self.BASE_URL, self.REMOTE)))
                    if not os.path.exists(self.home()):
                        os.makedirs(self.home())
                    utils.download_and_extract(
                        os.path.join(self.BASE_URL, self.REMOTE),
                        self.home(),
                        verbose=False,
                        sha1=self.SHA1)
                    amat_all = AMat(all_amat_filename)
                # at this point self.home() contains not only the
                # all_amat_filename, but it also contains the amats for all
                # the other levels too.
                #
                # This for loop transfers each amat to the dataset folder where
                # it belongs.
                for level in range(1, 7):
                    if level == self.LEVEL:
                        continue
                    if not os.path.exists(self.level_amat(level)):
                        continue
                    other = BaseNoise(level)
                    try:
                        # try loading the other one
                        other.fetch(download_if_missing=False)

                        # if that worked, then delete just-downloaded amat
                        # required for the other's build_meta
                        os.remove(self.level_amat(level))
                    except IOError:
                        # assuming this was because fetch failed,
                        # move the amat for the other level into the
                        # home folder of the other dataset.
                        # next time the other dataset is fetched,
                        # it will load the amat, save a npy, and delete the
                        # amat.
                        if not os.path.exists(other.home()):
                            os.makedirs(other.home())
                        os.rename(
                                self.level_amat(level),
                                other.level_amat(level))

                # now carry on loading as usual
                n_inputs = 28**2
                n_train = self.descr['n_train']
                n_valid = self.descr['n_valid']
                n_test = self.descr['n_test']
                assert amat_all.all.shape[0] == n_train + n_valid + n_test
                assert amat_all.all.shape[1] == n_inputs + 1
                inputs = np.reshape(
                        amat_all.all[:, :n_inputs].astype('float32'),
                        (-1, 28, 28))
                labels = amat_all.all[:, n_inputs].astype('int32')
                assert np.all(labels == amat_all.all[:, n_inputs])
                assert np.all(labels < self.descr['n_classes'])
                np.save(self.home(self.NAME + '_inputs.npy'), inputs)
                np.save(self.home(self.NAME + '_labels.npy'), labels)
                # clean up the .amat files we downloaded
                os.remove(all_amat_filename)
            else:
                raise


class MNIST_Noise1(BaseNoise):
    LEVEL = 1


class MNIST_Noise2(BaseNoise):
    LEVEL = 2


class MNIST_Noise3(BaseNoise):
    LEVEL = 3


class MNIST_Noise4(BaseNoise):
    LEVEL = 4


class MNIST_Noise5(BaseNoise):
    LEVEL = 5


class MNIST_Noise6(BaseNoise):
    LEVEL = 6


#
# Rectangles Variations
#

class Rectangles(BaseL2007):
    REMOTE = 'rectangles.zip'
    SHA1 = 'b8d456b1f83bea5efebe76a47a9535adc4b72586'
    REMOTE_SIZE = '2.7M'
    AMAT = 'rectangles'
    NAME = 'rectangles'
    descr = dict(
        n_classes=2,
        n_train=1000,
        n_valid=200,
        n_test=50000)


class RectanglesImages(BaseL2007):
    REMOTE = 'rectangles_images.zip'
    SHA1 = '2700ba92129ae195e93070d8b27f830323573a57'
    REMOTE_SIZE = '82M'
    AMAT = 'rectangles_im'
    NAME = 'rectangles_images'
    descr = dict(
        n_classes=2,
        n_train=10000,
        n_valid=2000,
        n_test=50000)


#
# Convex
#

class Convex(BaseL2007):
    REMOTE = 'convex.zip'
    SHA1 = '61eab3c60e0e1caeaa0b82abf827f1809cfd2ef9'
    REMOTE_SIZE = '3.4M'
    AMAT = 'convex'
    NAME = 'convex'
    descr = dict(
        n_classes=2,
        n_train=6500,
        n_valid=1500,
        n_test=50000)

    def train_amat(self):
        return self.home('convex_train.amat')

    def test_amat(self):
        return self.home('50k', 'convex_test.amat')

########NEW FILE########
__FILENAME__ = view
import dataset
from ..base import Task

class VectorXV(object):
    def protocol(self, algo):
        ds = self.dataset
        ds.fetch(True)
        ds.build_meta()
        n_train = ds.descr['n_train']
        n_valid = ds.descr['n_valid']
        n_test = ds.descr['n_test']

        start = 0
        end = n_train
        train = Task('vector_classification',
                name='train',
                x=ds._inputs[start:end].reshape((end-start), -1),
                y=ds._labels[start:end],
                n_classes=ds.descr['n_classes'])

        start = n_train
        end = n_train + n_valid
        valid = Task('vector_classification',
                name='valid',
                x=ds._inputs[start:end].reshape((end-start), -1),
                y=ds._labels[start:end],
                n_classes=ds.descr['n_classes'])

        start = n_train + n_valid
        end = n_train + n_valid + n_test
        test = Task('vector_classification',
                name='test',
                x=ds._inputs[start:end].reshape((end-start), -1),
                y=ds._labels[start:end],
                n_classes=ds.descr['n_classes'])

        model = algo.best_model(train=train, valid=valid)
        algo.loss(model, train)
        algo.loss(model, valid)
        return algo.loss(model, test)


class MNIST_Basic_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_Basic()


class MNIST_BackgroundImages_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_BackgroundImages()


class MNIST_BackgroundRandom_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_BackgroundRandom()


class MNIST_Rotated_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_Rotated()


class MNIST_RotatedBackgroundImages_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_RotatedBackgroundImages()


class MNIST_Noise1_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_Noise1()


class MNIST_Noise2_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_Noise2()


class MNIST_Noise3_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_Noise3()


class MNIST_Noise4_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_Noise4()


class MNIST_Noise5_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_Noise5()


class MNIST_Noise6_VectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.MNIST_Noise6()


class RectanglesVectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.Rectangles()


class RectanglesImagesVectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.RectanglesImages()


class ConvexVectorXV(VectorXV):
    def __init__(self):
        self.dataset = dataset.Convex()


########NEW FILE########
__FILENAME__ = larray
"""
LazyArray
"""
import atexit
import cPickle
import logging
import os
import StringIO
import subprocess
import sys
import numpy as np

from .data_home import get_data_home

logger = logging.getLogger(__name__)

class InferenceError(Exception):
    """Information about a lazily-evaluated quantity could not be inferred"""


class UnknownShape(InferenceError):
    """Shape could not be inferred"""


def is_int_idx(idx):
    return isinstance(idx, (int, np.integer))


def is_larray(thing):
    return isinstance(thing, larray)


def given_get(given, thing):
    try:
        return given.get(thing, thing)
    except TypeError:
        return thing


class lazy(object):
    def __str__(self):
        return lprint_str(self)

    def __print__(self):
        return self.__repr__()

    def clone(self, given):
        """
        Return a new object that will behave like self, but with new
        inputs.  For any input `obj` to self, the clone should have
        input `given_get(given, self.obj)`.
        """
        raise NotImplementedError('override-me',
                                  (self.__class__, 'clone'))

    def inputs(self):
        raise NotImplementedError('override-me',
                                 (self.__class__, 'inputs'))

    def lazy_inputs(self):
        return [ii for ii in self.inputs() if is_larray(ii)]


class larray(lazy):
    """
    A class inheriting from larray is like `lazy` but promises
    additionally to provide three attributes or properties:
    - .shape
    - .ndim
    - .dtype
    - .strides

    These should be used to maintain consistency with numpy.
    """
    def loop(self):
        return loop(self)

    def __len__(self):
        return self.shape[0]


class lmap(larray):
    """
    Return a lazily-evaluated mapping.

    fn can be a normal lambda expression, but it can also respond to the
    following attributes:

    - rval_getattr
        `fn.rval_getattr(name)` if it returns, must return the same thing as
        `getattr(fn(*args), name)` would return.
    """
    def __init__(self, fn, obj0, *objs, **kwargs):
        """
        ragged - optional kwargs, defaults to False. Iff true, objs of
            different lengths are allowed.

        f_map - optional kwargs: defaults to None. If provided, it is used
            to process input sub-sequences in one call.
            `f_map(*args)` should return the same(*) thing as `map(fn, *args)`,
            but the idea is that it would be faster.
            (*) returning an ndarray instead of a list is allowed.
        """
        ragged = kwargs.pop('ragged', False)
        f_map = kwargs.pop('f_map', None)
        if f_map is None:
            f_map = getattr(fn, 'f_map', None)

        if kwargs:
            raise TypeError('unrecognized kwarg', kwargs.keys())

        self.fn = fn
        self.objs = [obj0] + list(objs)
        self.ragged = ragged
        self.f_map = f_map
        if not ragged:
            for o in objs:
                if len(obj0) != len(o):
                    raise ValueError('objects have different length')

    def __len__(self):
        if len(self.objs)>1:
            return min(*[len(o) for o in self.objs])
        else:
            return len(self.objs[0])

    @property
    def shape(self):
        shape_0 = len(self)
        if hasattr(self.fn, 'rval_getattr'):
            shape_rest = self.fn.rval_getattr('shape', objs=self.objs)
            return (shape_0,) + shape_rest
        raise UnknownShape()

    @property
    def dtype(self):
        return self.fn.rval_getattr('dtype', objs=self.objs)

    @property
    def ndim(self):
        return 1 + self.fn.rval_getattr('ndim', objs=self.objs)

    def __getitem__(self, idx):
        if is_int_idx(idx):
            return self.fn(*[o[idx] for o in self.objs])
        else:
            try:
                tmps = [o[idx] for o in self.objs]
            except TypeError:
                # this can happen if idx is for numpy advanced indexing
                # and `o` isn't an ndarray.
                # try one element at a time
                tmps = [[o[i] for i in idx] for o in self.objs]

            # we loaded the subsequence of args
            if self.f_map:
                return self.f_map(*tmps)
            else:
                return map(self.fn, *tmps)

    def __array__(self):
        return np.asarray(self[:])

    def __print__(self):
        if hasattr(self.fn, '__name__'):
            return 'lmap(%s, ...)' % self.fn.__name__
        else:
            return 'lmap(%s, ...)' % str(self.fn)

    def clone(self, given):
        return lmap(self.fn, *[given_get(given, obj) for obj in self.objs],
                ragged=self.ragged,
                f_map=self.f_map)

    def inputs(self):
        return list(self.objs)


class RvalGetattr(object):
    """
    See `lmap_info`
    """
    def __init__(self, info):
        self.info = info

    def __call__(self, name, objs=None):
        try:
            return self.info[name]
        except KeyError:
            raise InferenceError(name)


def lmap_info(**kwargs):
    """Decorator for providing information for lmap

    >>> @lmap_info(shape=(10, 20), dtype='float32')
    >>> def foo(i):
    >>>     return np.zeros((10, 20), dtype='float32') + i
    >>>
    """

    # -- a little hack of convenience
    if 'shape' in kwargs:
        if 'ndim' in kwargs:
            assert len(kwargs['shape']) == kwargs['ndim']
        else:
            kwargs['ndim'] = len(kwargs['shape'])

    def wrapper(f):
        f.rval_getattr = RvalGetattr(kwargs)
        return f

    return wrapper


def lzip(*arrays):
    # XXX: make a version of this method that supports call_batch
    class fn(object):
        __name__ = 'lzip'
        def __call__(self, *args):
            return np.asarray(args)
        def rval_getattr(self, name, objs=None):
            if name == 'shape':
                shps = [o.shape for o in objs]
                shp1 = len(objs)
                # if all the rest of the shapes are equal
                # then we have something to say,
                # otherwise no idea.
                if all(shps[0][1:] == s[1:] for s in shps):
                    return (shp1,) + shps[0][1:]
                else:
                    raise InferenceError('dont know shape')
                raise NotImplementedError()
            if name == 'dtype':
                # if a shape cannot be inferred, then the
                # zip result might be ragged, in which case the dtype would be
                # `object`.
                shape = self.rval_getattr('shape', objs)
                # postcondition: result is ndarray-like

                if all(o.dtype == objs[0].dtype for o in objs[1:]):
                    return objs[0].dtype
                else:
                    # XXX upcasting rules
                    raise NotImplementedError()
            if name == 'ndim':
                # if a shape cannot be inferred, then the
                # zip result might be ragged, in which case the dtype would be
                # `object`.
                shape = self.rval_getattr('shape', objs)
                return len(shape)
            raise AttributeError(name)
    return lmap(fn(), *arrays)


class loop(larray):
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, idx):
        if is_int_idx(idx):
            return self.obj[idx % len(self.obj)]
        elif isinstance(idx, slice):
            raise NotImplementedError()
        elif isinstance(idx, (tuple, list, np.ndarray)):
            idx = np.asarray(idx) % len(self.obj)
            #XXX: fallback if o does not support advanced indexing
            return self.obj[idx]

    def clone(self, given):
        return loop(given_get(given, self.obj))

    def inputs(self):
        return [self.obj]


class reindex(larray):
    """
    Lazily re-index list-like `obj` so that
    `self[i]` means `obj[imap[i]]`
    """
    def __init__(self, obj, imap):
        self.obj = obj
        self.imap = np.asarray(imap)
        if 'int' not in str(self.imap.dtype):
            #XXX: diagnostic info
            raise TypeError(imap.dtype)

    def __len__(self):
        return len(self.imap)

    def __getitem__(self, idx):
        mapped_idx = self.imap[idx]
        try:
            return self.obj[mapped_idx]
        except TypeError:
            # XXX: try this, and restore original exception on failure
            return [self.obj[ii] for ii in mapped_idx]

    def __get_shape(self):
        return (len(self),) + self.obj.shape[1:]
    shape = property(__get_shape)

    def __get_dtype(self):
        return self.obj.dtype
    dtype = property(__get_dtype)

    def __get_ndim(self):
        return self.obj.ndim
    ndim = property(__get_ndim)

    def clone(self, given):
        return reindex(
                given_get(given, self.obj),
                given_get(given, self.imap)
                )

    def inputs(self):
        return [self.obj, self.imap]


def clone_helper(thing, given):
    if thing in given:
        return
    for ii in thing.lazy_inputs():
        clone_helper(ii, given)
    given[thing] = thing.clone(given)


def clone(thing, given):
    _given = dict(given)
    clone_helper(thing, _given)
    return _given[thing]


def lprint(thing, prefix='', buf=None):
    if buf is None:
        buf = sys.stdout
    if hasattr(thing, '__print__'):
        print >> buf, '%s%s'%(prefix, thing.__print__())
    else:
        print >> buf, '%s%s'%(prefix, str(thing))
    if is_larray(thing):
        for ii in thing.inputs():
            lprint(ii, prefix+'    ', buf)


def lprint_str(thing):
    sio = StringIO.StringIO()
    lprint(thing, '', sio)
    return sio.getvalue()


def Flatten(object):
    def rval_getattr(self, attr, objs):
        if attr == 'shape':
            shp = objs[0].shape[1:]
            if None in shp:
                return (None,)
            else:
                return (np.prod(shp),)
        if attr == 'ndim':
            return 1
        if attr == 'dtype':
            return objs[0].dtype
        raise AttributeError(attr)
    def __call__(self, thing):
        return np.flatten(thing)

def flatten_elements(seq):
    return lmap(Flatten(), seq)


memmap_README = """\
Memmap files created by LazyCacheMemmap

  data.raw - memmapped array data file, no header
  valid.raw - memmapped array validity file, no header
  header.pkl - python pickle of meta-data (dtype, shape) for data.raw

The validitiy file is a byte array that indicates which elements of
data.raw are valid.  If valid.raw byte `i` is 1, then the `i`'th tensor
slice of data.raw has been computed and is usable. If it is 0, then it
has not been computed and the slice value is undefined. No other values
should appear in the valid.raw array.
"""

class CacheMixin(object):
    def populate(self, batchsize=1):
        """
        Populate a lazy array cache node by iterating over the source in
        increments of `batchsize`.
        """
        if batchsize <= 0:
            raise ValueError('non-positive batch size')
        if batchsize == 1:
            for i in xrange(len(self)):
                self[i]
        else:
            i = 0
            while i < len(self):
                self[i:i + batchsize]
                i += batchsize

    @property
    def shape(self):
        try:
            return self._obj_shape
        except:
            return self.obj.shape

    @property
    def dtype(self):
        try:
            return self._obj_dtype
        except:
            return self.obj.dtype

    @property
    def ndim(self):
        try:
            return self._obj_ndim
        except:
            return self.obj.ndim

    def inputs(self):
        return [self.obj]

    def __getitem__(self, item):
        if isinstance(item, (int, np.integer)):
            if self._valid[item]:
                return self._data[item]
            else:
                obj_item = self.obj[item]
                self._data[item] = obj_item
                self._valid[item] = 1
                self.rows_computed += 1
                return self._data[item]
        else:
            # could be a slice, an intlist, a tuple
            v = self._valid[item]
            assert v.ndim == 1
            if np.all(v):
                return self._data[item]

            # -- Quick and dirty, yes.
            # -- Accurate, ?
            try:
                list(item)
                is_int_list = True
            except:
                is_int_list = False

            if np.sum(v) == 0:
                # -- we need to re-compute everything in item
                sub_item = item
            elif is_int_list:
                # -- in this case advanced indexing has been used
                #    and only some of the elements need to be recomputed
                assert self._valid.max() <= 1
                item = np.asarray(item)
                assert 'int' in str(item.dtype)
                sub_item = item[v == 0]
            elif isinstance(item, slice):
                # -- in this case slice indexing has been used
                #    and only some of the elements need to be recomputed
                #    so we are converting the slice to an int_list
                idxs_of_v = np.arange(len(self._valid))[item]
                sub_item = idxs_of_v[v == 0]
            else:
                sub_item = item

            self.rows_computed += v.sum()
            sub_values = self.obj[sub_item]  # -- retrieve missing elements
            self._valid[sub_item] = 1
            try:
                self._data[sub_item] = sub_values
            except:
                logger.error('data dtype %s' % str(self._data.dtype))
                logger.error('data shape %s' % str(self._data.shape))

                logger.error('sub_item str %s' % str(sub_item))
                logger.error('sub_item type %s' % type(sub_item))
                logger.error('sub_item len %s' % len(sub_item))
                logger.error('sub_item shape %s' % getattr(sub_item, 'shape',
                    None))

                logger.error('sub_values str %s' % str(sub_values))
                logger.error('sub_values type %s' % type(sub_values))
                logger.error('sub_values len %s' % len(sub_values))
                logger.error('sub_values shape %s' % getattr(sub_values, 'shape',
                    None))
                raise
            assert np.all(self._valid[item])
            return self._data[item]


class cache_memory(CacheMixin, larray):
    """
    Provide a lazily-filled cache of a larray (obj) via an in-memmory
    array.
    """

    def __init__(self, obj):
        """
        If new files are created, then `msg` will be written to README.msg
        """
        self.obj = obj
        self._data = np.empty(obj.shape, dtype=obj.dtype)
        self._valid = np.zeros(len(obj), dtype='int8')
        self.rows_computed = 0

    def clone(self, given):
        return self.__class__(obj=given_get(given, self.obj))


class cache_memmap(CacheMixin, larray):
    """
    Provide a lazily-filled cache of a larray (obj) via a memmap file
    associated with (name).


    The memmap will be stored in `basedir`/`name` which defaults to
    `cache_memmap.ROOT`/`name`,
    which defaults to '~/.skdata/memmaps'/`name`.
    """

    ROOT = os.path.join(get_data_home(), 'memmaps')

    def __init__(self, obj, name, basedir=None, msg=None, del_atexit=False):
        """
        If new files are created, then `msg` will be written to README.msg
        """

        self.obj = obj
        if basedir is None:
            basedir = self.ROOT
        self.dirname = dirname = os.path.join(basedir, name)
        subprocess.call(['mkdir', '-p', dirname])

        data_path = os.path.join(dirname, 'data.raw')
        valid_path = os.path.join(dirname, 'valid.raw')
        header_path = os.path.join(dirname, 'header.pkl')

        try:
            dtype, shape = cPickle.load(open(header_path))
            if obj is None or (dtype == obj.dtype and shape == obj.shape):
                mode = 'r+'
                logger.info('Re-using memmap %s with dtype %s, shape %s' % (
                        data_path,
                        str(dtype),
                        str(shape)))
                self._obj_shape = shape
                self._obj_dtype = dtype
                self._obj_ndim = len(shape)
            else:
                mode = 'w+'
                logger.warn("Problem re-using memmap: dtype/shape mismatch")
                logger.info('Creating memmap %s with dtype %s, shape %s' % (
                        data_path,
                        str(obj.dtype),
                        str(obj.shape)))
                dtype = obj.dtype
                shape = obj.shape
        except IOError:
            dtype = obj.dtype
            shape = obj.shape
            mode = 'w+'
            logger.info('Creating memmap %s with dtype %s, shape %s' % (
                    data_path,
                    str(dtype),
                    str(obj.shape)))

        self._data = np.memmap(data_path,
            dtype=dtype,
            mode=mode,
            shape=shape)

        self._valid = np.memmap(valid_path,
            dtype='int8',
            mode=mode,
            shape=(shape[0],))

        if mode == 'w+':
            # initialize a new set of files
            cPickle.dump((dtype, shape),
                         open(header_path, 'w'))
            # mark all memmap elements as uncomputed
            self._valid[:] = 0

            open(os.path.join(dirname, 'README.txt'), 'w').write(
                memmap_README)
            if msg is not None:
                open(os.path.join(dirname, 'README.msg'), 'w').write(
                    str(msg))
            warning = ( 'WARNING_THIS_DIR_WILL_BE_DELETED'
                        '_BY_cache_memmap.delete_files()')
            open(os.path.join(dirname, warning), 'w').close()

        self.rows_computed = 0

        if del_atexit:
            atexit.register(self.delete_files)

    def delete_files(self):
        logger.info('deleting cache_memmap at %s' % self.dirname)
        subprocess.call(['rm', '-Rf', self.dirname])

    def clone(self, given):
        raise NotImplementedError()
        # XXX: careful to ensure that any instance can be cloned multiple
        # times, and the clones can themselves be cloned recursively.


########NEW FILE########
__FILENAME__ = dataset
"""Loader for the Labeled Faces in the Wild (LFW) dataset

This dataset is a collection of JPEG pictures of famous people collected
over the internet, all details are available on the official website:

    http://vis-www.cs.umass.edu/lfw/

Each picture is centered on a single face. The typical task is called
Face Verification: given a pair of two pictures, a binary classifier
must predict whether the two images are from the same person.

An alternative task, Face Recognition or Face Identification is:
given the picture of the face of an unknown person, identify the name
of the person by refering to a gallery of previously seen pictures of
identified persons.

Both Face Verification and Face Recognition are tasks that are typically
performed on the output of a model trained to perform Face Detection. The
most popular model for Face Detection is called Viola-Jones and is
implemented in the OpenCV library. The LFW faces were extracted by this face
detector from various online websites.
"""

# Copyright (c) 2011 James Bergstra <bergstra@rowland.harvard.edu>
# Copyright (c) 2011 Olivier Grisel <olivier.grisel@ensta.org>
# Copyright (c) 2012 Nicolas Pinto <pinto@rowland.harvard.edu>

# License: Simplified BSD


# ISSUES (XXX)
# - Extra pairs.txt files in the funneled dataset.  The lfw-funneled.tgz dataset
#   has, in the same dir as the names, a bunch of pairs_0N.txt files and a
#   pairs.txt file. Why are they there?  Should we be using them?

import os
from os import path
from glob import glob
import shutil

import lockfile
import numpy as np

from skdata.data_home import get_data_home
from skdata.utils import download, download_and_extract

import logging
log = logging.getLogger(__name__)
# XXX: logging config (e.g. formatting, etc.) should be factored out in
# skdata and not be imposed on the caller (like in http://goo.gl/7xEeB)


NAMELEN = 48

PAIRS_BASE_URL = "http://vis-www.cs.umass.edu/lfw/"
PAIRS_FILENAMES = [
    ('pairsDevTrain.txt', '082b7adb005fd30ad35476c18943ce66ab8ff9ff'),
    ('pairsDevTest.txt', 'f33ea17f58dac4401801c5c306f81d9ff56e30e9'),
    ('pairs.txt', '020efa51256818a30d3033a98fc98b97a8273df2'),
]


class BaseLFW(object):
    """XXX

    The lfw subdirectory in the datasets cache has the following structure, when
    it has been populated by calling `fetch()`.

    .. code-block::

        lfw/
            funneled/
                pairs.txt
                pairsDevTrain.txt
                pairsDevTrain.txt
                images/
                    lfw_funneled/
                        <names>/
                            <jpgs>
            original/
                pairs.txt
                pairsDevTrain.txt
                pairsDevTrain.txt
                images/
                    lfw/
                        <names>/
                            <jpgs>

            ...

    The meta-data is dictionaries (one-per-image) with keys:
    * filename
    * name
    * image_number

    """

    def __init__(self):

        self.name = self.__class__.__name__

        try:
            from joblib import Memory
            mem = Memory(cachedir=self.home('cache'), verbose=False)
            self._get_meta = mem.cache(self._get_meta)
        except ImportError:
            pass

    def home(self, *suffix_paths):
        return path.join(get_data_home(), 'lfw', self.name, *suffix_paths)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: fetch()
    # ------------------------------------------------------------------------

    def fetch(self):
        """Download and extract the dataset."""

        home = self.home()

        lock = lockfile.FileLock(home)
        if lock.is_locked():
            log.warn('%s is locked, waiting for release' % home)

        with lock:
            # -- download pair labels
            for fname, sha1 in PAIRS_FILENAMES:
                url = path.join(PAIRS_BASE_URL, fname)
                basename = path.basename(url)
                filename = path.join(home, basename)
                if not path.exists(filename):
                    if not path.exists(home):
                        os.makedirs(home)
                    download(url, filename, sha1=sha1)

            # -- download and extract images
            url = self.URL
            sha1 = self.SHA1
            output_dirname = self.home('images')
            if not path.exists(output_dirname):
                os.makedirs(output_dirname)

            # -- various disruptions might cause this to fail
            #    but if any process gets as far as writing the completion
            #    marker, then it should be all good.
            done_marker = os.path.join(output_dirname, 'completion_marker')
            if not path.exists(done_marker):
                download_and_extract(url, output_dirname, sha1=sha1)
                open(done_marker, 'w').close()

    # ------------------------------------------------------------------------
    # -- Dataset Interface: meta
    # ------------------------------------------------------------------------

    @property
    def meta(self):
        if not hasattr(self, '_meta'):
            self.fetch()
            self._meta = self._get_meta()
        return self._meta

    def _get_meta(self):

        log.info('Building metadata...')

        # -- Filenames
        pattern = self.home('images', self.IMAGE_SUBDIR, '*', '*.jpg')
        fnames = sorted(glob(pattern))
        n_images = len(fnames)
        log.info('# images = %d' % n_images)

        meta = []
        for fname in fnames:
            name = path.split(path.split(fname)[0])[-1]
            image_number = int(path.splitext(path.split(fname)[-1])[0][-4:])
            data = dict(filename=fname, name=name, image_number=image_number)
            meta += [data]

        return np.array(meta)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: clean_up()
    # ------------------------------------------------------------------------

    def clean_up(self):
        if path.isdir(self.home()):
            shutil.rmtree(self.home())

    # ------------------------------------------------------------------------
    # -- LFW Specific
    # ------------------------------------------------------------------------

    def parse_pairs_file(self, filename):
        """
        Return recarray of n_folds x n_labels x n_pairs x 2

        There are 2 labels: label 0 means same, label 1 means different

        Each element of the recarray has two fields: 'name' and 'inum'.
        - The name is the name of the person in the LFW picture.
        - The inum is the number indicating which LFW picture of the person
          should be used.
        """
        self.fetch()

        # -- load the pairs/labels txt file into one string per line
        lines = np.loadtxt(filename, dtype=str, delimiter='\n')
        header = lines[0].split()
        header_tokens = map(int, header)
        if len(header_tokens) == 2:
            n_folds, n_pairs = header_tokens
        elif len(header_tokens) == 1:
            n_folds, n_pairs = [1] + header_tokens
        else:
            raise ValueError('Failed to parse header', header_tokens)

        # -- checks number of lines by side-effect
        elems = lines[1:].reshape(n_folds, 2, n_pairs)
        rval = np.recarray((n_folds, 2, n_pairs, 2),
                dtype=np.dtype([('name', 'S%i' % NAMELEN),
                    ('inum', np.int32)]))

        for fold_i in xrange(n_folds):
            # parse the same-name lines
            for pair_i in xrange(n_pairs):
                name, inum0, inum1 = elems[fold_i, 0, pair_i].split()
                assert len(name) < NAMELEN
                rval[fold_i, 0, pair_i, 0] = name, int(inum0)
                rval[fold_i, 0, pair_i, 1] = name, int(inum1)

                assert rval[fold_i, 0, pair_i, 0]['name'] == name

            # parse the different-name lines
            for pair_i in xrange(n_pairs):
                name0, inum0, name1, inum1 = elems[fold_i, 1, pair_i].split()
                assert len(name0) < NAMELEN
                assert len(name1) < NAMELEN
                rval[fold_i, 1, pair_i, 0] = name0, int(inum0)
                rval[fold_i, 1, pair_i, 1] = name1, int(inum1)

        return rval

    @property
    def pairsDevTrain(self):
        return self.parse_pairs_file(self.home('pairsDevTrain.txt'))

    @property
    def pairsDevTest(self):
        return self.parse_pairs_file(self.home('pairsDevTest.txt'))

    @property
    def pairsView2(self):
        return self.parse_pairs_file(self.home('pairs.txt'))


class Original(BaseLFW):
    URL = "http://vis-www.cs.umass.edu/lfw/lfw.tgz"
    SHA1 = '1aeea1f6b1cfabc8a0e103d974b590fda315e147'
    IMAGE_SUBDIR = 'lfw'
    COLOR = True


class Funneled(BaseLFW):
    URL = "http://vis-www.cs.umass.edu/lfw/lfw-funneled.tgz"
    SHA1 = '7f5c008acbd96597ee338fbb2d6c0045979783f7'
    IMAGE_SUBDIR = 'lfw_funneled'
    COLOR = True


class Aligned(BaseLFW):
    URL = "http://www.openu.ac.il/home/hassner/data/lfwa/lfwa.tar.gz"
    SHA1 = '38ecda590870e7dc91fb1040759caccddbe25375'
    IMAGE_SUBDIR = 'lfw2'
    COLOR = False

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

import sys
import logging


#import dataset
import view

from skdata.utils.glviewer import glumpy_viewer, glumpy

logger = logging.getLogger(__name__)

usage = """
Usage: main.py show <variant>

    <variant> can be one of {original, aligned, funneled}
"""


def main_show():
    """
    Use glumpy to launch a data set viewer.
    """
    variant = sys.argv[2]
    if variant == 'original':
        obj = view.Original()
        cmap=None
    elif variant == 'aligned':
        obj = view.Aligned()
        cmap=glumpy.colormap.Grey
    elif variant == 'funneled':
        obj = view.Funneled()
        cmap=None
    else:
        raise ValueError(variant)

    glumpy_viewer(
        img_array=obj.image_pixels,
        arrays_to_print=[obj.image_pixels],
        cmap=cmap,
        window_shape=(250, 250),
        )


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    if len(sys.argv) <= 1:
        print usage
        return 1
    else:
        try:
            fn = globals()['main_' + sys.argv[1]]
        except:
            print 'command %s not recognized' % sys.argv[1]
            print usage
            return 1
        return fn()


if __name__ == '__main__':
    sys.exit(main())


########NEW FILE########
__FILENAME__ = test_fake
"""This test for the LFW require medium-size data dowloading and processing

If the data has not been already downloaded by runnning the examples,
the tests won't run (skipped).

If the test are run, the first execution will be long (typically a bit
more than a couple of minutes) but as the dataset loader is leveraging
joblib, successive runs will be fast (less than 200ms).
"""

import random
import os
import tempfile
import numpy as np
try:
    try:
        from scipy.misc import imsave
    except ImportError:
        from scipy.misc.pilutil import imsave
except ImportError:
    imsave = None

from skdata.lfw import dataset, view
from skdata import tasks

from numpy.testing import assert_raises
from nose import SkipTest
from nose.tools import raises


SCIKIT_LEARN_DATA = tempfile.mkdtemp(prefix="scikit_learn_lfw_test_")
SCIKIT_LEARN_DATA_EMPTY = tempfile.mkdtemp(prefix="scikit_learn_empty_test_")

FAKE_NAMES = [
    'Abdelatif_Smith',
    'Abhati_Kepler',
    'Camara_Alvaro',
    'Chen_Dupont',
    'John_Lee',
    'Lin_Bauman',
    'Onur_Lopez',
]


def namelike(fullpath):
    """Returns part of an image full path that has the name in it"""
    return fullpath[-18:-8]


class EmptyLFW(dataset.BaseLFW):
    ARCHIVE_NAME = "i_dont_exist.tgz"
    img_shape = (250, 250, 3)
    COLOR = True
    IMAGE_SUBDIR = 'image_subdir'

    def home(self, *names):
        return os.path.join(SCIKIT_LEARN_DATA_EMPTY, 'lfw', self.name, *names)

    def fetch(self, download_if_missing=True):
        return


class FakeLFW(dataset.BaseLFW):
    IMAGE_SUBDIR = 'lfw_fake'  # corresponds to lfw, lfw_funneled, lfw_aligned
    img_shape = (250, 250, 3)
    COLOR = True

    def home(self, *names):
        return os.path.join(SCIKIT_LEARN_DATA, 'lfw', self.name, *names)

    def fetch(self, download_if_missing=True):
        if not os.path.exists(self.home()):
            os.makedirs(self.home())

        random_state = random.Random(42)
        np_rng = np.random.RandomState(42)

        # generate some random jpeg files for each person
        counts = FakeLFW.counts = {}
        for name in FAKE_NAMES:
            folder_name = self.home('images', self.IMAGE_SUBDIR, name)
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

            n_faces = np_rng.randint(1, 5)
            counts[name] = n_faces
            for i in range(n_faces):
                file_path = os.path.join(folder_name,
                                         name + '_%04d.jpg' % (i + 1))
                uniface = np_rng.randint(0, 255, size=(250, 250, 3))
                try:
                    imsave(file_path, uniface)
                except ImportError:
                    # PIL is not properly installed, skip those tests
                    raise SkipTest

        if not os.path.exists(self.home('lfw_funneled')):
            os.makedirs(self.home('lfw_funneled'))

        # add some random file pollution to test robustness
        f = open(os.path.join(self.home(), 'lfw_funneled', '.test.swp'), 'wb')
        f.write('Text file to be ignored by the dataset loader.')
        f.close()

        # generate some pairing metadata files using the same format as LFW
        def write_fake_pairs(filename, n_match, n_splits):
            f = open(os.path.join(self.home(), filename), 'wb')
            if n_splits == 1:
                f.write("%d\n" % n_match)
            else:
                f.write("%d\t%i\n" % (n_splits, n_match))
            for split in xrange(n_splits):
                more_than_two = [name for name, count in counts.iteritems()
                                 if count >= 2]
                for i in range(n_match):
                    name = random_state.choice(more_than_two)
                    first, second = random_state.sample(range(counts[name]), 2)
                    f.write('%s\t%d\t%d\n' % (name, first + 1, second + 1))

                for i in range(n_match):
                    first_name, second_name = random_state.sample(FAKE_NAMES, 2)
                    first_index = random_state.choice(range(counts[first_name]))
                    second_index = random_state.choice(range(counts[second_name]))
                    f.write('%s\t%d\t%s\t%d\n' % (first_name, first_index + 1,
                                                  second_name, second_index + 1))
            f.close()
        write_fake_pairs('pairsDevTrain.txt', 5, 1)
        write_fake_pairs('pairsDevTest.txt', 7, 1)
        write_fake_pairs('pairs.txt', 4, 3)


class FP_Empty(view.FullProtocol):
    DATASET_CLASS = EmptyLFW


class FP_Fake(view.FullProtocol):
    DATASET_CLASS = FakeLFW


def setup_module():
    """Test fixture run once and common to all tests of this module"""
    FakeLFW().fetch()


def teardown_module():
    """Test fixture (clean up) run once after all tests of this module"""
    FakeLFW().clean_up()


def test_empty_load():
    assert len(EmptyLFW().meta) == 0


def test_fake_load():
    fake = FakeLFW()
    counts_copy = dict(FakeLFW.counts)
    for m in fake.meta:
        counts_copy[m['name']] -= 1
    assert all(c == 0 for c in counts_copy.values())

    for m in fake.meta:
        assert m['filename'].endswith('.jpg')


def test_fake_verification_task():
    fake = FakeLFW()

    assert fake.pairsDevTrain.shape == (1, 2, 5, 2), fake.pairsDevTrain.shape
    assert fake.pairsDevTest.shape == (1, 2, 7, 2)
    assert fake.pairsView2.shape == (3, 2, 4, 2)

    for i in range(5):
        (lname, lnum) = fake.pairsDevTrain[0, 0, i, 0]
        (rname, rnum) = fake.pairsDevTrain[0, 0, i, 1]
        assert lname == rname

    for i in range(5):
        (lname, lnum) = fake.pairsDevTrain[0, 1, i, 0]
        (rname, rnum) = fake.pairsDevTrain[0, 1, i, 1]
        assert lname != rname



def test_fake_imgs():
    fp = FP_Fake()
    # test the default case
    images = fp.image_pixels
    assert images.dtype == 'uint8', images.dtype
    assert images.ndim == 4, images.ndim
    assert images.shape == (17, 250, 250, 3), images.shape

    img0 = images[0]
    assert isinstance(img0, np.ndarray)
    assert img0.dtype == 'uint8'
    assert img0.ndim == 3
    assert img0.shape == (250, 250, 3)



########NEW FILE########
__FILENAME__ = test_view
from skdata import lfw

DATASET_NAMES = ['Original', 'Funneled', 'Aligned']


def test_view2_smoke_shape():
    for ds_name in DATASET_NAMES:
        view2 = getattr(lfw.view, '%sView2' % ds_name)()
        assert len(view2.x) == 6000
        assert len(view2.y) == 6000
        assert len(view2.x[0]) == 2
        assert view2.x[0][0].shape[:2] == (250, 250)
        if view2.dataset.COLOR:
            view2.x[0][0].shape[-1] == 3
        assert len(view2.splits) == 10
        assert len(view2.splits[0].train.x) == 5400
        assert len(view2.splits[0].train.y) == 5400
        assert len(view2.splits[0].test.x) == 600
        assert len(view2.splits[0].test.y) == 600

########NEW FILE########
__FILENAME__ = view
# Copyright (C) 2012
# Authors: Nicolas Pinto <pinto@alum.mit.edu>

# License: Simplified BSD

import logging

import numpy as np

from skdata.utils import dotdict
from skdata.utils import ImgLoader
from skdata.larray import lmap

import dataset

logger = logging.getLogger(__name__)


def paths_labels(pairs):
    """
    Returns tensor of shape (n_folds, n_labels * n_pairs) of recarrays with
    ['lpath', 'rpath', 'label'] fields.
    """
    n_folds, n_labels, n_pairs, n_per_pair = pairs.shape
    assert n_per_pair == 2

    def foo(lr):
        (lname, lnum), (rname, rnum) = lr
        lpath = '%s/%s_%04d.jpg' % (lname, lname, lnum)
        rpath = '%s/%s_%04d.jpg' % (rname, rname, rnum)
        assert len(lpath) < (3 * dataset.NAMELEN)
        assert len(rpath) < (3 * dataset.NAMELEN)
        label = 1 if lname == rname else -1
        return lpath, rpath, label

    rval = np.recarray(n_folds * n_labels * n_pairs,
            dtype=np.dtype([
                ('lpath', 'S' + str(3 * dataset.NAMELEN)),
                ('rpath', 'S' + str(3 * dataset.NAMELEN)),
                ('label', np.int8)]))
    # -- interleave the labels, so that indexing just the first few
    #    examples will return a stratified sample.
    rval[:] = map(foo, pairs.transpose(0, 2, 1, 3).reshape((-1, 2)))
    return rval.reshape((n_folds, n_labels * n_pairs))


def sorted_paths(paths_labels):
    """
    Return a sorted sequence of all paths that occur in paths_labels
    """
    paths = list(set(
        list(paths_labels['lpath'].flatten())
        + list(paths_labels['rpath'].flatten())))
    paths.sort()
    return paths


def paths_labels_lookup(paths_labels, path_list):
    """
    `paths_labels` is a ndarray of recarrays with string paths
    replace the path strings with integers of where to find paths in the
    pathlist.

    Return recarray has fields ['lpathidx', 'rpathidx', 'label'].
    """
    rval = np.recarray(paths_labels.shape,
            dtype=np.dtype([
                ('lpathidx', np.int32),
                ('rpathidx', np.int32),
                ('label', np.int8)]))
    rval['lpathidx'] = np.searchsorted(path_list, paths_labels['lpath'])
    rval['rpathidx'] = np.searchsorted(path_list, paths_labels['rpath'])
    rval['label'] = paths_labels['label']
    return rval


class FullProtocol(object):

    """
    image_pixels:
        lazy array of grey or rgb images as pixels, all images in
        dataset.

    view2: integer recarray of shape (10, 600) whose fields are:
        'lpathidx': index of left image in image_pixels
        'rpathidx': index of right image in image_pixels
        'label':    -1 or 1

    """

    DATASET_CLASS = None

    def __init__(self, x_dtype='uint8', x_height=250, x_width=250,
            max_n_per_class=None,
            channel_major=False):
        if self.DATASET_CLASS is None:
            raise NotImplementedError("This is an abstract class")

        # -- build/fetch dataset
        self.dataset = self.DATASET_CLASS()
        self.dataset.meta

        pairsDevTrain = self.dataset.pairsDevTrain
        pairsDevTest = self.dataset.pairsDevTest
        pairsView2 = self.dataset.pairsView2

        if max_n_per_class is not None:
            pairsDevTrain = pairsDevTrain[:, :, :max_n_per_class]
            pairsDevTest = pairsDevTest[:, :, :max_n_per_class]
            pairsView2 = pairsView2[:, :, :max_n_per_class]

        logging.info('pairsDevTrain shape %s' % str(pairsDevTrain.shape))
        logging.info('pairsDevTest shape %s' % str(pairsDevTest.shape))
        logging.info('pairsView2 shape %s' % str(pairsView2.shape))

        paths_labels_dev_train = paths_labels(pairsDevTrain)
        paths_labels_dev_test = paths_labels(pairsDevTest)
        paths_labels_view2 = paths_labels(pairsView2)

        all_paths_labels = np.concatenate([
            paths_labels_dev_train.flatten(),
            paths_labels_dev_test.flatten(),
            paths_labels_view2.flatten()])

        rel_paths = sorted_paths(all_paths_labels)

        self.image_paths = [
                self.dataset.home('images', self.dataset.IMAGE_SUBDIR, pth)
                for pth in rel_paths]

        def lookup(pairs):
            rval = paths_labels_lookup(paths_labels(pairs), rel_paths)
            return rval

        self.dev_train = lookup(pairsDevTrain)
        self.dev_test = lookup(pairsDevTest)
        self.view2 = lookup(pairsView2)

        # -- lazy array helper function
        if self.dataset.COLOR:
            ndim, mode, shape = (3, 'RGB', (x_height, x_width, 3))
        else:
            ndim, mode, shape = (3, 'L', (x_height, x_width, 1))
        loader = ImgLoader(ndim=ndim, dtype=x_dtype, mode=mode, shape=shape)

        self.image_pixels = lmap(loader, self.image_paths)
        self.paths_labels_dev_train = paths_labels_dev_train
        self.paths_labels_dev_test = paths_labels_dev_test
        self.paths_labels_view2 = paths_labels_view2

        assert str(self.image_pixels[0].dtype) == x_dtype
        assert self.image_pixels[0].ndim == 3

    def protocol(self, algo):
        for dummy in self.protocol_iter(algo):
            pass

    def protocol_iter(self, algo):

        def task(obj, name):
            return algo.task(semantics='image_match_indexed',
                    lidx=obj['lpathidx'],
                    ridx=obj['rpathidx'],
                    y=obj['label'],
                    images=self.image_pixels,
                    name=name)

        model = algo.best_model(
            train=task(self.dev_train[0], name='devTrain'),
            valid=task(self.dev_test[0], name='devTest'),
            )

        algo.forget_task('devTrain')
        algo.forget_task('devTest')

        yield ('model validation complete', model)

        v2_losses = []
        algo.generalization_error_k_fold = []

        for i, v2i_tst in enumerate(self.view2):
            v2i_tst = task(self.view2[i], 'view2_test_%i' % i)
            v2i_trn = algo.task(semantics='image_match_indexed',
                    lidx=np.concatenate([self.view2[j]['lpathidx']
                        for j in range(10) if j != i]),
                    ridx=np.concatenate([self.view2[j]['rpathidx']
                        for j in range(10) if j != i]),
                    y=np.concatenate([self.view2[j]['label']
                        for j in range(10) if j != i]),
                    images=self.image_pixels,
                    name='view2_train_%i' % i,
                    )
            v2i_model = algo.retrain_classifier(model, v2i_trn)
            v2_losses.append(algo.loss(v2i_model, v2i_tst))
            algo.generalization_error_k_fold.append(dict(
                train_task_name=v2i_trn.name,
                test_task_name=v2i_tst.name,
                test_error_rate=v2_losses[-1],
                ))
            algo.forget_task('view2_test_%i' % i)
            algo.forget_task('view2_train_%i' % i)
        algo.generalization_error = np.mean(v2_losses)

        yield 'model testing complete'


class Original(FullProtocol):
    DATASET_CLASS = dataset.Original


class Funneled(FullProtocol):
    DATASET_CLASS = dataset.Funneled


class Aligned(FullProtocol):
    DATASET_CLASS = dataset.Aligned


class BaseView2(FullProtocol):

    """
    self.dataset - a dataset.BaseLFW subclass instance
    self.x all image pairs in view2
    self.y all image pair labels in view2
    self.splits : list of 10 View2 splits, each one has
        splits[i].x : all of the image pairs in View2
        splits[i].y : all labels of splits[i].x
        splits[i].train.x : subset of splits[i].x
        splits[i].train.y : subset of splits[i].x
        splits[i].test.x : subset of splits[i].x
        splits[i].test.y : subset of splits[i].x
    """

    def load_pair(self, idxpair):
        lidx, ridx, label = idxpair

        # XXX
        # WTF why does loading this as a numpy int32 cause it
        # to try to load a path '/' whereas int() make it load the right path?
        l = self.image_pixels[int(lidx)]
        r = self.image_pixels[int(ridx)]
        return np.asarray([l, r])

    def __init__(self, *args, **kwargs):
        FullProtocol.__init__(self, *args, **kwargs)
        view2 = self.view2

        all_x = lmap(self.load_pair, view2.flatten())
        all_y = self.view2.flatten()['label']
        splits = []
        for fold_i, test_fold in enumerate(view2):

            # -- test
            test_x = lmap(self.load_pair, test_fold)
            test_y = test_fold['label']

            train_x = lmap(self.load_pair,
                    np.concatenate([
                        fold
                        for fold_j, fold in enumerate(view2)
                        if fold_j != fold_i]))
            train_y = np.concatenate([
                fold['label']
                for fold_j, fold in enumerate(view2)
                if fold_j != fold_i])

            splits.append(
                    dotdict(
                        x=all_x,
                        y=all_y,
                        train=dotdict(x=train_x, y=train_y),
                        test=dotdict(x=test_x, y=test_y),
                        )
                    )

        self.x = all_x
        self.y = all_y
        self.splits = splits

    @property
    def protocol(self):
        raise NotImplementedError()


class OriginalView2(BaseView2):
    DATASET_CLASS = dataset.Original


class FunneledView2(BaseView2):
    DATASET_CLASS = dataset.Funneled


class AlignedView2(BaseView2):
    DATASET_CLASS = dataset.Aligned

########NEW FILE########
__FILENAME__ = main
"""
Entry point for bin/* scripts

XXX
"""
import sys
import logging
logger = logging.getLogger(__name__)

def import_tokens(tokens):
    # XXX Document me
    # import as many as we can
    rval = None
    for i in range(len(tokens)):
        modname = '.'.join(tokens[:i+1])
        # XXX: try using getattr, and then merge with load_tokens
        try:
            logger.info('importing %s' % modname)
            exec "import %s" % modname
            exec "rval = %s" % modname
        except ImportError, e:
            logger.info('failed to import %s' % modname)
            logger.info('reason: %s' % str(e))
            break
    return rval, tokens[i:]

def load_tokens(tokens):
    # XXX: merge with import_tokens
    logger.info('load_tokens: %s' % str(tokens))
    symbol, remainder = import_tokens(tokens)
    for attr in remainder:
        symbol = getattr(symbol, attr)
    return symbol

def main(cmd):
    """
    Entry point for bin/* scripts
    XXX
    """
    try:
        runner = dict(
                fetch='main_fetch',
                show='main_show',
                clean_up='main_clean_up')[cmd]
    except KeyError:
        print >> sys.stderr, "Command not recognized:", cmd
        # XXX: Usage message
        sys.exit(1)

    try:
        argv1 = sys.argv[1]
    except IndexError:
        logger.error('Module name required (XXX: print Usage)')
        return 1

    symbol = load_tokens(['skdata'] + argv1.split('.') + [runner])
    logger.info('running: %s' % str(symbol))
    sys.exit(symbol())

########NEW FILE########
__FILENAME__ = dataset
"""
MNIST hand-drawn digit dataset

The data set consists of 70 000 greyscale images (28x28 pixels) of handwritten
digits, and their labels (0-9). It is customary to train classifiers on the
first 50K images, to use the next 10K images for model selection, and the last
10K images for testing.  Steady progress over the last fifteen years has
culminated in the best convolutional classification models achieving < 1%
error.  An extensive collection of published results is available from the
official website.


Official web site:

http://yann.lecun.com/exdb/mnist/


Reference:

Y. LeCun, L. Bottou, Y. Bengio, and P. Haffner.
"Gradient-based learning applied to document recognition."
Proceedings of the IEEE, 86(11):2278-2324, November 1998.

"""

import os
import gzip
import logging
import urllib
import shutil

import numpy as np

from ..data_home import get_data_home

logger = logging.getLogger(__name__)

URLS = dict(
    train_images="http://yann.lecun.com/exdb/mnist/train-images-idx3-ubyte.gz",
    train_labels="http://yann.lecun.com/exdb/mnist/train-labels-idx1-ubyte.gz",
    test_images="http://yann.lecun.com/exdb/mnist/t10k-images-idx3-ubyte.gz",
    test_labels="http://yann.lecun.com/exdb/mnist/t10k-labels-idx1-ubyte.gz",
    )

FILE_SIZES_PRETTY = dict(
    train_images='9.5M',
    train_labels='29K',
    test_images='1.6M',
    test_labels='4.5K',
    )

def _read_int32(f):
    """unpack a 4-byte integer from the current position in file f"""
    s = f.read(4)
    s_array = np.fromstring(s, dtype='int32')
    a = s_array.item()
    return s_array.item()


def _reverse_bytes_int32(i):
    a = np.asarray(i, 'int32')
    b = np.frombuffer(a.data, dtype='int8')
    assert b.shape == (4,)
    c = b[[3, 2, 1, 0]]
    d = np.frombuffer(c.data, dtype='int32')
    assert d.shape == (1,), d.shape
    return d.item()


def _read_header(f, debug=False, fromgzip=None):
    """
    :param f: an open file handle.
    :type f: a file or gzip.GzipFile object

    :param fromgzip: bool or None
    :type fromgzip: if None determine the type of file handle.

    :returns: data type, element size, rank, shape, size
    """
    if fromgzip is None:
        fromgzip = isinstance(f, gzip.GzipFile)

    magic = _read_int32(f)
    if magic in (2049, 2051):
        logger.info('Reading on big-endian machine.')
        endian = 'big'
        next_int32 = lambda : _read_int32(f)
    elif _reverse_bytes_int32(magic) in (2049, 2051):
        logger.info('Reading on little-endian machine.')
        magic = _reverse_bytes_int32(magic)
        endian = 'little'
        next_int32 = lambda : _reverse_bytes_int32(_read_int32(f))
    else:
        raise IOError('MNIST data file appears to be corrupt')

    if magic == 2049:
        logger.info('reading MNIST labels file')
        n_elements = next_int32()
        return (n_elements,)
    elif magic == 2051:
        logger.info('reading MNIST images file')
        n_elements = next_int32()
        n_rows = next_int32()
        n_cols = next_int32()
        return (n_elements, n_rows, n_cols)
    else:
        assert 0, magic


def read(f, debug=False):
    """Load all or part of file 'f' into a numpy ndarray

    :param f: file from which to read
    :type f: file-like object. Can be a gzip open file.

    """
    shape = _read_header(f, debug)
    data = f.read(np.prod(shape))
    return np.fromstring(data, dtype='uint8').reshape(shape)


class MNIST(object):
    """
    meta[i] is dict with keys:
        id: int identifier of this example
        label: int in range(10)
        split: 'train' or 'test'

    meta_const is dict with keys:
        image:
            shape: 28, 28
            dtype: 'uint8'

    """

    DOWNLOAD_IF_MISSING = True  # the value when accessing .meta

    def __init__(self):
        self.meta_const = dict(
                image=dict(
                    shape=(28, 28),
                    dtype='uint8'))
        self.descr = dict(
                n_classes=10)

    def __get_meta(self):
        try:
            return self._meta
        except AttributeError:
            self.fetch(download_if_missing=self.DOWNLOAD_IF_MISSING)
            self._meta = self.build_meta()
            return self._meta
    meta = property(__get_meta)

    def home(self, *names):
        return os.path.join(get_data_home(), 'mnist', *names)

    def fetch(self, download_if_missing):
        if download_if_missing:
            if not os.path.isdir(self.home()):
                os.makedirs(self.home())

        for role, url in URLS.items():
            dest = self.home(os.path.basename(url))
            try:
                gzip.open(dest, 'rb').close()
            except IOError:
                if download_if_missing:
                    logger.warn("Downloading %s %s: %s => %s" % (
                        FILE_SIZES_PRETTY[role], role, url, dest))
                    downloader = urllib.urlopen(url)
                    data = downloader.read()
                    tmp = open(dest, 'wb')
                    tmp.write(data)
                    tmp.close()
                    gzip.open(dest, 'rb').close()
                else:
                    raise

    def clean_up(self):
        logger.info('recursively erasing %s' % self.home())
        if os.path.isdir(self.home()):
            shutil.rmtree(self.home())

    def build_meta(self):
        try:
            arrays = self.arrays
        except AttributeError:
            arrays = {}
            for role, url in URLS.items():
                dest = self.home(os.path.basename(url))
                logger.info('opening %s' % dest)
                arrays[role] = read(gzip.open(dest, 'rb'), debug=True)
                arrays[role].flags['WRITEABLE'] = False
            # cache the arrays in memory, the aren't that big (12M total)
            MNIST.arrays = arrays
        assert arrays['train_images'].shape == (60000, 28, 28)
        assert arrays['test_images'].shape == (10000, 28, 28)
        assert arrays['train_labels'].shape == (60000,)
        assert arrays['test_labels'].shape == (10000,)
        assert len(arrays['train_images']) == len(arrays['train_labels'])
        assert len(arrays['test_images']) == len(arrays['test_labels'])
        meta = [dict(id=i, split='train', label=l)
                for i,l in enumerate(arrays['train_labels'])]
        meta.extend([dict(id=i + j + 1, split='test', label=l)
                for j, l in enumerate(arrays['test_labels'])])
        assert i + j + 2 == 70000, (i, j)
        return meta


########NEW FILE########
__FILENAME__ = main
"""
A helpful scripts specific to the MNIST data set.

"""
import sys
import logging


from skdata.mnist.dataset import MNIST
from skdata.utils.glviewer import glumpy_viewer, glumpy

logger = logging.getLogger(__name__)

usage = """
Usage: main.py {fetch, show, clean_up}
"""


def main_fetch():
    """
    Download the MNIST data set to the skdata cache dir
    """
    MNIST().fetch(download_if_missing=True)


def main_show():
    """
    Use glumpy to launch a data set viewer.
    """
    self = MNIST()
    Y = [m['label'] for m in self.meta]
    glumpy_viewer(
            img_array=self.arrays['train_images'],
            arrays_to_print=[Y],
            cmap=glumpy.colormap.Grey,
            window_shape=(28 * 4, 28 * 4)
            )


def main_clean_up():
    """
    Delete all memmaps and data set files related to MNIST.
    """
    logger.setLevel(logging.INFO)
    MNIST().clean_up()



def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    if len(sys.argv) <= 1:
        print usage
        return 1
    else:
        try:
            fn = globals()['main_' + sys.argv[1]]
        except:
            print 'command %s not recognized' % sys.argv[1]
            print usage
            return 1
        return fn()


if __name__ == '__main__':
    sys.exit(main())


########NEW FILE########
__FILENAME__ = test_dataset
from skdata.mnist import dataset, view
# XXX It appears that these tests are *way* out of date. They use use the old
# interface, whereas MNIST uses the view interface now.

def test_MNIST():
    M = dataset.MNIST()  # just make sure we can create the class
    M.DOWNLOAD_IF_MISSING = False
    assert M.meta_const['image']['shape'] == (28, 28)
    assert M.meta_const['image']['dtype'] == 'uint8'
    assert M.descr['n_classes'] == 10
    assert M.meta[0] == dict(id=0, split='train', label=5), M.meta[0]
    assert M.meta[69999] == dict(id=69999, split='test', label=6), M.meta[69999]
    assert len(M.meta) == 70000



########NEW FILE########
__FILENAME__ = test_view
import numpy as np
from skdata.mnist import view
from skdata.base import SklearnClassifier

def test_image_classification():

    class ConstantPredictor(object):
        def __init__(self, dtype='int', output=0):
            self.dtype = dtype
            self.output = output

        def fit(self, X, y):
            assert X.shape[0] in (50000, 60000), X.shape
            # -- the SklearnClassifier flattens image
            #    data sets to be compatible with sklearn classifiers,
            #    which expect vectors. That's why this method sees
            #    flattened images.
            assert np.prod(X.shape[1:]) == 784, X.shape

        def predict(self, X):
            return np.zeros(len(X), dtype=self.dtype) + self.output

    view_protocol = view.OfficialImageClassification()
    learn_algo = SklearnClassifier(ConstantPredictor)
    view_protocol.protocol(learn_algo)
    assert learn_algo.results['loss'][0]['task_name'] == 'tst'
    assert np.allclose(
            learn_algo.results['loss'][0]['err_rate'],
            0.9,
            atol=.01)


def test_vector_classification():

    class ConstantPredictor(object):
        def __init__(self, dtype='int', output=0):
            self.dtype = dtype
            self.output = output

        def fit(self, X, y):
            assert X.shape[0] in (50000, 60000), X.shape
            assert X.shape[1:] == (784,), X.shape

        def predict(self, X):
            return np.zeros(len(X), dtype=self.dtype) + self.output

    view_protocol = view.OfficialVectorClassification()
    learn_algo = SklearnClassifier(ConstantPredictor)
    view_protocol.protocol(learn_algo)
    assert learn_algo.results['loss'][0]['task_name'] == 'tst'
    assert np.allclose(
            learn_algo.results['loss'][0]['err_rate'],
            0.9,
            atol=.01)

########NEW FILE########
__FILENAME__ = view
import numpy as np

from .dataset import MNIST
from ..dslang import Task

class OfficialImageClassification(object):
    def __init__(self, x_dtype='uint8', y_dtype='int'):
        self.dataset = dataset = MNIST()
        dataset.meta  # -- trigger load if necessary

        all_images = np.vstack((dataset.arrays['train_images'],
                                dataset.arrays['test_images']))
        all_labels = np.concatenate([dataset.arrays['train_labels'],
                                     dataset.arrays['test_labels']])

        if len(all_images) != 70000:
            raise ValueError()
        if len(all_labels) != 70000:
            raise ValueError()

        # TODO: add random shuffling options like in cifar10
        # XXX: ensure this is read-only view
        self.sel_idxs = np.arange(60000)
        self.tst_idxs = np.arange(60000, 70000)
        self.fit_idxs = np.arange(50000)
        self.val_idxs = np.arange(50000, 60000)

        # XXX: ensure this is read-only view
        self.all_images = all_images[:, :, :, np.newaxis].astype(x_dtype)
        self.all_labels = all_labels.astype(y_dtype)

        self.n_classes = 10

    def protocol(self, algo):
        for _ in self.protocol_iter(algo):
            pass
        return algo

    def protocol_iter(self, algo):

        def task(name, idxs):
            return Task(
                'indexed_image_classification',
                name=name,
                idxs=idxs,
                all_images=self.all_images,
                all_labels=self.all_labels,
                n_classes=self.n_classes)

        task_fit = task('fit', self.fit_idxs)
        task_val = task('val', self.val_idxs)
        task_sel = task('sel', self.sel_idxs)
        task_tst = task('tst', self.tst_idxs)


        model1 = algo.best_model(train=task_fit, valid=task_val)
        yield ('model validation complete', model1)

        model2 = algo.best_model(train=task_sel)
        algo.loss(model2, task_tst)
        yield ('model testing complete', model2)


class OfficialVectorClassification(OfficialImageClassification):
    def __init__(self, *args, **kwargs):
        OfficialImageClassification.__init__(self, *args, **kwargs)
        self.all_vectors = self.all_images.reshape(len(self.all_images), -1)

    def protocol_iter(self, algo):

        def task(name, idxs):
            return Task(
                'indexed_vector_classification',
                name=name,
                idxs=idxs,
                all_vectors=self.all_vectors,
                all_labels=self.all_labels,
                n_classes=self.n_classes)

        task_fit = task('fit', self.fit_idxs)
        task_val = task('val', self.val_idxs)
        task_sel = task('sel', self.sel_idxs)
        task_tst = task('tst', self.tst_idxs)


        model1 = algo.best_model(train=task_fit, valid=task_val)
        yield ('model validation complete', model1)

        model2 = algo.best_model(train=task_sel)
        algo.loss(model2, task_tst)
        yield ('model testing complete', model2)

########NEW FILE########
__FILENAME__ = pascal
# -*- coding: utf-8 -*-
"""PASCAL Visual Object Classes (VOC) Datasets

http://pascallin.ecs.soton.ac.uk/challenges/VOC

If you make use of this data, please cite the following journal paper in
any publication:

The PASCAL Visual Object Classes (VOC) Challenge
Everingham, M., Van Gool, L., Williams, C. K. I., Winn, J. and Zisserman,
A.  International Journal of Computer Vision, 88(2), 303-338, 2010

http://pascallin.ecs.soton.ac.uk/challenges/VOC/pubs/everingham10.pdf
http://pascallin.ecs.soton.ac.uk/challenges/VOC/pubs/everingham10.html#abstract
http://pascallin.ecs.soton.ac.uk/challenges/VOC/pubs/everingham10.html#bibtex
"""

# Copyright (C) 2011
# Authors: Nicolas Pinto <pinto@rowland.harvard.edu>
#          Nicolas Poilvert <poilvert@rowland.harvard.edu>
# License: Simplified BSD

import os
from os import path
import shutil
from distutils import dir_util
from glob import glob
import hashlib

import numpy as np

from data_home import get_data_home
from utils import download, extract, xml2dict


class BasePASCAL(object):
    """PASCAL VOC Dataset

    Attributes
    ----------
    meta: list of dict
        Metadata associated with the dataset. For each image with index i,
        meta[i] is a dict with keys:

            id: str
                Identifier of the image.

            filename: str
                Full path to the image.

            sha1: str
                SHA-1 hash of the image.

            shape: dict with int values
                Shape of the image. dict with keys 'height', 'width', 'depth'
                and int values.

            split: str
                'train', 'val' or 'test'.

            objects: list of dict [optional]
                Description of the objects present in the image. Note that this
                key may not be available if split is 'test'. If the key is
                present, then objects[i] is a dict with keys:

                    name: str
                        Name (label) of the object.

                    bounding_box: dict with int values
                        Bounding box coordinates (0-based index). dict with
                        keys 'x_min', 'x_max', 'y_min', 'y_max' and int values
                        such that:
                        +-----------------------------------------▶ x-axis
                        |
                        |   +-------+    .  .  .  y_min (top)
                        |   | bbox  |
                        |   +-------+    .  .  .  y_max (bottom)
                        |
                        |   .       .
                        |
                        |   .       .
                        |
                        |  x_min   x_max
                        |  (left)  (right)
                        |
                        ▼
                        y-axis

                    pose: str
                        'Left', 'Right', 'Frontal', 'Rear' or 'Unspecified'

                    truncated: boolean
                        True if the object is occluded / truncated.

                    difficult: boolean
                        True if the object has been tagged as difficult (should
                        be ignored during evaluation?).

            segmented: boolean
                True if segmentation information is available.

            owner: dict [optional]
                Owner of the image (self-explanatory).

            source: dict
                Source of the image (self-explanatory).


    Notes
    -----
    If joblib is available, then `meta` will be cached for faster processing.
    To install joblib use 'pip install -U joblib' or 'easy_install -U joblib'.
    """

    def __init__(self, meta=None):
        if meta is not None:
            self._meta = meta

        self.name = self.__class__.__name__

        try:
            from joblib import Memory
            mem = Memory(cachedir=self.home('cache'))
            self._get_meta = mem.cache(self._get_meta)
        except ImportError:
            pass

    def home(self, *suffix_paths):
        return path.join(get_data_home(), 'pascal', self.name, *suffix_paths)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: fetch()
    # ------------------------------------------------------------------------

    def fetch(self):
        """Download and extract the dataset."""

        home = self.home()
        if not path.exists(home):
            os.makedirs(home)

        # download archives
        archive_filenames = []
        for key, archive in self.ARCHIVES.iteritems():
            url = archive['url']
            sha1 = archive['sha1']
            basename = path.basename(url)
            archive_filename = path.join(home, basename)
            if not path.exists(archive_filename):
                download(url, archive_filename, sha1=sha1)
            archive_filenames += [(archive_filename, sha1)]
            self.ARCHIVES[key]['archive_filename'] = archive_filename

        # extract them
        if not path.exists(path.join(home, 'VOCdevkit')):
            for archive in self.ARCHIVES.itervalues():
                url = archive['url']
                sha1 = archive['sha1']
                archive_filename = archive['archive_filename']
                extract(archive_filename, home, sha1=sha1, verbose=True)
                # move around stuff if needed
                if 'moves' in archive:
                    for move in archive['moves']:
                        src = self.home(move['source'])
                        dst = self.home(move['destination'])
                        # We can't use shutil here since the destination folder
                        # may already exist. Fortunately the distutils can help
                        # us here (see standard library).
                        dir_util.copy_tree(src, dst)
                        dir_util.remove_tree(src)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: meta
    # ------------------------------------------------------------------------

    @property
    def meta(self):
        if hasattr(self, '_meta'):
            return self._meta
        else:
            self.fetch()
            self._meta = self._get_meta()
            return self._meta

    def _get_meta(self):

        base_dirname = self.home('VOCdevkit', self.name)
        dirs = dict([(basename, path.join(base_dirname, basename))
                      for basename in os.listdir(base_dirname)
                      if path.isdir(path.join(base_dirname, basename))])

        img_pattern = path.join(dirs['JPEGImages'], "*.jpg")
        img_filenames = sorted(glob(img_pattern))
        n_imgs = len(img_filenames)

        # --
        print "Parsing annotations..."
        meta = []
        unique_object_names = []
        n_objects = 0
        img_ids = []
        for ii, img_filename in enumerate(img_filenames):

            data = {}

            data['filename'] = img_filename

            # sha1 hash
            sha1 = hashlib.sha1(open(img_filename).read()).hexdigest()
            data['sha1'] = sha1

            # image id
            img_basename = path.basename(path.split(img_filename)[1])
            img_id = path.splitext(img_basename)[0]
            img_ids += [img_id]

            data['id'] = img_id

            # -- get xml filename
            xml_filename = path.join(dirs['Annotations'],
                                     "%s.xml" % img_id)
            if not path.exists(xml_filename):
                # annotation missing
                meta += [data]
                continue

            # -- parse xml
            xd = xml2dict(xml_filename)

            # image basename
            assert img_basename == xd['filename']

            # source
            data['source'] = xd['source']

            # owner (if available)
            if 'owner' in xd:
                data['owner'] = xd['owner']

            # size / shape
            size = xd['size']
            width = int(size['width'])
            height = int(size['height'])
            depth = int(size['depth'])
            data['shape'] = dict(height=height, width=width, depth=depth)

            # segmentation ?
            segmented = bool(xd['segmented'])
            data['segmented'] = segmented
            if segmented:
                # TODO: parse segmentation data (in 'SegmentationClass') or
                # lazy-evaluate it ?
                pass

            # objects with their bounding boxes
            objs = xd['object']
            if isinstance(objs, dict):  # case where there is only one bbox
                objs = [objs]
            objects = []
            for obj in objs:
                # parse bounding box coordinates and convert them to valid
                # 0-indexed coordinates
                bndbox = obj.pop('bndbox')
                x_min = max(0,
                            (int(np.round(float(bndbox['xmin']))) - 1))
                x_max = min(width - 1,
                            (int(np.round(float(bndbox['xmax']))) - 1))
                y_min = max(0,
                            (int(np.round(float(bndbox['ymin']))) - 1))
                y_max = min(height - 1,
                            (int(np.round(float(bndbox['ymax']))) - 1))
                bounding_box = dict(x_min=x_min, x_max=x_max,
                                    y_min=y_min, y_max=y_max)
                assert (np.array(bounding_box) >= 0).all()
                obj['bounding_box'] = bounding_box
                n_objects += 1
                if obj['name'] not in unique_object_names:
                    unique_object_names += [obj['name']]

                # convert 'difficult' to boolean
                if 'difficult' in obj:
                    obj['difficult'] = bool(int(obj['difficult']))
                else:
                    # assume difficult=False if key not present
                    obj['difficult'] = False

                # convert 'truncated' to boolean
                if 'truncated' in obj:
                    obj['truncated'] = bool(int(obj['truncated']))
                else:
                    # assume truncated=False if key not present
                    obj['truncated'] = False

                objects += [obj]

            data['objects'] = objects

            # -- print progress
            n_done = ii + 1
            status = ("Progress: %d/%d [%.1f%%]"
                      % (n_done, len(img_filenames), 100. * n_done / n_imgs))
            status += chr(8) * (len(status) + 1)
            print status,

            # -- append to meta
            meta += [data]

        print

        print " Number of images: %d" % len(meta)
        print " Number of unique object names: %d" % len(unique_object_names)
        print " Unique object names: %s" % unique_object_names

        # --
        print "Parsing splits..."
        main_dirname = path.join(dirs['ImageSets'], 'Main')

        # We use 'aeroplane_{train,trainval}.txt' to get the list of 'train'
        # and 'val' ids
        train_filename = path.join(main_dirname, 'aeroplane_train.txt')
        assert path.exists(train_filename)
        train_ids = np.loadtxt(train_filename, dtype=str)[:, 0]

        trainval_filename = path.join(main_dirname, 'aeroplane_trainval.txt')
        assert path.exists(trainval_filename)
        trainval_ids = np.loadtxt(trainval_filename, dtype=str)[:, 0]

        splits = 'train', 'val', 'test'
        split_counts = dict([(split, 0) for split in splits])
        for data in meta:
            img_id = data['id']
            if img_id in trainval_ids:
                if img_id in train_ids:
                    data['split'] = 'train'
                else:
                    data['split'] = 'val'
            else:
                data['split'] = 'test'
            split_counts[data['split']] += 1

        for split in splits:
            count = split_counts[split]
            assert count > 0
            print(" Number of images in '%s': %d"
                  % (split, count))

        meta = np.array(meta)
        return meta

    # ------------------------------------------------------------------------
    # -- Dataset Interface: clean_up()
    # ------------------------------------------------------------------------

    def clean_up(self):
        if path.isdir(self.home()):
            shutil.rmtree(self.home())

    # ------------------------------------------------------------------------
    # -- Driver routines to be called by skdata.main
    # ------------------------------------------------------------------------

    @classmethod
    def main_fetch(cls):
        cls.fetch(download_if_missing=True)

    @classmethod
    def main_show(cls):
        raise NotImplementedError


class VOC2007(BasePASCAL):
    ARCHIVES = {
        'trainval': {
            'url': ('http://pascallin.ecs.soton.ac.uk/challenges/VOC/voc2007/'
                    'VOCtrainval_06-Nov-2007.tar'),
            'sha1': '34ed68851bce2a36e2a223fa52c661d592c66b3c',
        },
        'test': {
            'url': ('http://pascallin.ecs.soton.ac.uk/challenges/VOC/voc2007/'
                    'VOCtest_06-Nov-2007.tar'),
            'sha1': '41a8d6e12baa5ab18ee7f8f8029b9e11805b4ef1',
        },
    }


class VOC2008(BasePASCAL):
    ARCHIVES = {
        'trainval': {
            'url': ('http://pascallin.ecs.soton.ac.uk/challenges/VOC/voc2008/'
                    'VOCtrainval_14-Jul-2008.tar'),
            'sha1': 'fc87d2477a1ae78c6748dc25b88c052eb8b06d75',
        },
        'test': {
            'url': ('https://s3.amazonaws.com/scikit-data/pascal/'
                    'VOC2008test.tar'),
            'sha1': '2044e7c61c407ca1f085e2bff5f188c7f7df7f48',
        },
    }


class VOC2009(BasePASCAL):
    ARCHIVES = {
        'trainval': {
            'url': ('http://pascallin.ecs.soton.ac.uk/challenges/VOC/voc2009/'
                    'VOCtrainval_11-May-2009.tar'),
            'sha1': '0bc2be22b76a9bcb744c0458c535f3a84f054bbc',
        },
        'test': {
            'url': ('https://s3.amazonaws.com/scikit-data/pascal/'
                    'VOC2009test.tar'),
            'sha1': 'e638975ae3faca04aabc3ddb577d13e04da60950',
        }
    }


class VOC2010(BasePASCAL):
    ARCHIVES = {
        'trainval': {
            'url': ('http://pascallin.ecs.soton.ac.uk/challenges/VOC/voc2010/'
                    'VOCtrainval_03-May-2010.tar'),
            'sha1': 'bf9985e9f2b064752bf6bd654d89f017c76c395a',
        },
        'test': {
            'url': ('https://s3.amazonaws.com/scikit-data/pascal/'
                    'VOC2010test.tar'),
            'sha1': '8f426aee2cb0ed0e07b5fceb45eff6a38595abfb',
        }
    }


class VOC2011(BasePASCAL):
    ARCHIVES = {
        'trainval': {
            'url': ('http://pascallin.ecs.soton.ac.uk/challenges/VOC/voc2011/'
                    'VOCtrainval_25-May-2011.tar'),
            'sha1': '71ceda5bc8ce4a6486f7996b0924eee265133895',
            # the following will fix the fact that a prefix dir has been added
            # to the archive
            'moves': [{'source': 'TrainVal/VOCdevkit',
                       'destination': 'VOCdevkit'}],
        },
        'test': {
            'url': ('https://s3.amazonaws.com/scikit-data/pascal/'
                    'VOC2011test.tar.gz'),
            'sha1': 'e988fa911f2199309f76a6f44691e9471a011c45',
        }
    }


def main_fetch():
    raise NotImplementedError


def main_show():
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = dataset
"""
The data set implemented here is a synthetic visual data set of random dot
patterns, introduced by two fundamental psychological experiments for the study
pattern representation.  Subjects are trained to distinguish
3 broadly-different random patterns by inferring a rule from labeled
distortions of 3 prototypes.

Posner, M. I., & Keele, S. W. (1968).  On the genesis of abstract ideas.
Journal of experimental psychology, 77(3p1), 353.

Posner, M. I., Goldsmith, R., & Welton Jr, K. E. (1967). Perceived distance
and the classification of distorted patterns. Journal of Experimental
Psychology, 73(1), 28.

"""
import numpy as np
from scipy.ndimage.filters import gaussian_filter

level_of_distortion = {
    '0': [1.0, 0, 0, 0, 0],
    '1': [.88, .1, .015, .004, .001],
    '2': [.75, .15, .05, .03, .02],
    '3': [.59, .20, .16, .03, .02],
    '4': [.36, .48, .06, .05, .05],
    '5': [.2, .3, .4, .05, .05],
    '6': [.0, .4, .32, .15, .13],
    '7.7': [.0, .24, .16, .3, .3],
}

# these are (low, high) randint ranges into the
# locations enumerated below in spiral400
adjacency_areas = [
    (0, 1),
    (1, 9),
    (9, 25),
    (25, 100),
    (100, 400)]


def int_spiral(N):
    """
    Return a list of 2d locations forming a spiral
    (0, 0),
    (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1),
    (2, -1), (2, 0), ...
    """

    def cw(a, b):
        if (a, b) == (1, 0):
            return (0, 1)
        elif (a, b) == (0, 1):
            return (-1, 0)
        elif (a, b) == (-1, 0):
            return (0, -1)
        else:
            return (1, 0)

    rval = []
    seen = set()
    rval.append((0, 0))
    seen.add((0, 0))

    i, j = 1, 0
    ti, tj = -1, 0
    di, dj = 0, 1

    while len(rval) < N:
        assert (i, j) not in seen
        rval.append((i, j))
        seen.add((i, j))
        if (i + ti, j + tj) in seen:
            i += di
            j += dj
        else: # -- turn a corner
            ti, tj = cw(ti, tj)
            di, dj = cw(di, dj)
            i += di
            j += dj
    return rval

spiral400 = int_spiral(400)


def distort(rowcols, level, rng):
    """
    Apply the distortion algorithm described in (Posner et al. 1967).
    """
    N = len(rowcols)
    rval = []
    if level in level_of_distortion:
        pvals = level_of_distortion[level]
        areas = rng.multinomial(n=1, pvals=pvals, size=(N,)).argmax(axis=1)
        assert len(rowcols) == len(areas)
        for (r, c), area_i in zip(rowcols, areas):
            pos = rng.randint(*adjacency_areas[area_i])
            dr, dc = spiral400[pos]
            rval.append((r + dr, c + dc))
    elif level == '8.6':
        for (r, c) in rowcols:
            pos = rng.randint(400)
            dr, dc = spiral400[pos]
            rval.append((r + dr, c + dc))
    elif level == '9.7':
        for (r, c) in rowcols:
            r, c = rng.randint(10, 40, size=(2,))
            rval.append((r, c))
    return np.asarray(rval)


def prototype_coords(rng):
    """
    Sample 2-d coordinates for a Posner-Keele trial.

    Returns a 9x2 matrix of point locations within a 50x50 grid. Points all
    lie within the 30x30 region at the centre of the 50x50 grid.

    """
    return rng.randint(10, 40, size=(9, 2))


def render_coords(coords, blur=True, blur_sigma=1.5, crop_30=True):
    """
    Render point coordinates into a two-dimensional image matrix.

    Returns: a 50x50 rendering (lossless) or a 30x30 crop from the centre if
    `crop_30` is True.
    """
    rval = np.zeros((50, 50))
    rval[coords[:, 0], coords[:, 1]] = 1

    if blur:
        # rval = gaussian_filter(rval, sigma=1.0, mode='constant')
        rval = gaussian_filter(rval, sigma=blur_sigma, mode='constant')
        rval = rval / rval.max()

        if crop_30:
            maxval = 0.8
            return rval[10:40, 10:40].clip(0,maxval) / maxval
        else:
            return rval
    else:

        if crop_30:
            return rval[10:40, 10:40]
        else:
            return rval





########NEW FILE########
__FILENAME__ = main
import sys
import numpy as np

from dataset import prototype_coords
from dataset import render_coords
from dataset import distort
from view import PosnerKeele1968E3

import skdata

def main_show():
    import matplotlib.pyplot as plt
    rng = np.random.RandomState(1)
    coords = prototype_coords(rng)
    img = render_coords(coords)
    img3 = render_coords(distort(coords, '3', rng))
    img6 = render_coords(distort(coords, '6', rng))
    plt.imshow(np.asarray([img, img3, img6]).T,
               cmap='gray',
               interpolation='nearest')
    plt.show()


def main_dump_to_png():
    from PIL import Image
    class DumpAlgo(skdata.base.LearningAlgo):
        def __init__(self, seed=123):
            self.rng = np.random.RandomState(seed)

        def forget(self, model):
            pass

        def best_model(self, train, valid=None):
            return getattr(self, 'best_model_' + train.semantics)(train, valid)

        def best_model_indexed_image_classification(self, train, valid):
            assert valid is None
            self.loss(None, train)

        def loss(self, model, task):
            for ii in task.idxs:
                filename = 'pk_%s_%i_label_%i.png' % (
                    task.name, ii, task.all_labels[ii])
                imga = task.all_images[ii][:, :, 0]
                print 'Saving', filename
                Image.fromarray(imga, 'L').save(filename)

    pk = PosnerKeele1968E3()
    pk.protocol(DumpAlgo())


if __name__ == '__main__':
    sys.exit(globals()['main_' + sys.argv[1]]())


########NEW FILE########
__FILENAME__ = test_dataset
import numpy as np

from skdata.posner_keele.dataset import level_of_distortion
from skdata.posner_keele.dataset import distort
from skdata.posner_keele.dataset import int_spiral
from skdata.posner_keele.dataset import prototype_coords
from skdata.posner_keele.dataset import render_coords

def test_lod():
    for key, value in level_of_distortion.items():
        assert np.allclose(np.sum(value), 1.0)


def test_spiral():
    s0 = int_spiral(0)
    assert s0 == [(0, 0)]

    s1 = int_spiral(11)
    assert s1 == [
        (0, 0), (1, 0), (1, 1), (0, 1), (-1, 1),
        (-1, 0), (-1, -1), (0, -1), (1, -1), (2, -1), (2, 0)]

    s2 = int_spiral(400)
    assert s2[-4:] == [(-6, 10), (-7, 10), (-8, 10), (-9, 10)]


def test_distort():
    rng = np.random.RandomState(4)
    new_pts = distort([[0, 0], [2, 1], [1, 3]], '2', rng)
    assert np.allclose(new_pts, [(1, -1), (2, -1), (1, 3)])

    new_pts = distort([[0, 0], [2, 1], [1, 3]], '7.7', rng)
    assert np.allclose(new_pts, [(5, -4), (2, 2), (-5, -5)])


def test_boundary_conditions():
    rng = np.random.RandomState(4)
    acc = None
    for i in range(1000):
        coords = prototype_coords(rng)
        dcoords = distort(coords, '7.7', rng)
        assert dcoords.min() >= 0
        assert dcoords.max() < 50
        if acc is None:
            acc = render_coords(dcoords)
        else:
            acc += render_coords(dcoords)

    if 0:
        import matplotlib.pyplot as plt
        plt.imshow(acc, cmap='gray', interpolation='nearest')
        plt.show()





########NEW FILE########
__FILENAME__ = test_view
from skdata.posner_keele.view import PosnerKeele1968E3

import numpy as np

from sklearn.svm import LinearSVC
from skdata.base import SklearnClassifier


def test_protocol(cls=LinearSVC, N=1, show=True, net=None):
    ### run on 36 subjects
    results = {}
    algo = SklearnClassifier(cls)

    pk = PosnerKeele1968E3()
    pk.protocol(algo)

    print cls
    for loss_report in algo.results['loss']:
        print loss_report['task_name'] + \
            (": err = %0.3f" % (loss_report['err_rate']))
    print

    for loss_report in algo.results['loss']:
        task = loss_report['task_name']
        if task not in results: results[task] = []
        results[task].append((loss_report['err_rate'], loss_report['n']))

    stats = {}
    for k, v in results.items():
        p = np.mean([vv[0] for vv in v])
        std = np.sqrt(p*(1-p))
        n = np.sum([vv[1] for vv in v])
        stats[k] = [p, std, n]

    metastats = dict([(k, [np.mean(vi) for vi in v]) for k, v in stats.items()])
    return metastats



########NEW FILE########
__FILENAME__ = view
import copy
import functools

import numpy as np
from scipy.ndimage.filters import gaussian_filter
from scipy.misc import imresize

from skdata.base import Task

from dataset import prototype_coords
from dataset import distort
from dataset import render_coords

def render_coords_uint8_channels(coords):
    n_points, n_dims = coords.shape
    assert n_dims == 2
    rval = render_coords(coords)
    rval *= 255
    rval = rval.astype('uint8')
    rval = rval[:, :, np.newaxis]
    return rval


def blur(self, X):
    rval = np.empty(X.shape)
    for i, Xi in enumerate(X):
        rval[i] = gaussian_filter(X[i].astype('float') / 255,
                                  sigma=self.blur_sigma,
                                  mode='constant')

    ### downsample
    down_size = (11,11)
    rval = rval[:,:,:,0]

    X2 = []
    for x in rval:
        X2.append( imresize(x, down_size) )
    rval = np.array(X2, dtype='float64') / 255.0

    return rval



class PosnerKeele1968E3(object):
    """

    Protocol of Experiment 3 from Posner and Keele, 1968.
    "On the Genesis of Abstract Ideas"

    """
    def __init__(self, seed=1, train_level='7.7'):
        self.seed = seed
        self.train_level = train_level
        self.n_prototypes = 3
        self.n_train_per_prototype = 4
        self.n_test_5_per_prototype = 2
        self.n_test_7_per_prototype = 2

    def distortion_set(self, N, coords, level, rng):
        images = []
        labels = []
        assert len(coords) == self.n_prototypes
        for proto, coord in enumerate(coords):
            # --apply the same distortions to each example
            rng_copy = copy.deepcopy(rng)
            for i in range(N):
                dcoord = distort(coord, level, rng_copy)
                img = render_coords_uint8_channels(dcoord)
                images.append(img)
                labels.append(proto)
        rng.seed(int(rng_copy.randint(2**30)))
        return np.asarray(images), np.asarray(labels)

    def task(self, name, images, labels):
        images = np.asarray(images)
        if images.ndim == 3:
            images = images[:, :, :, np.newaxis]
        return Task(
            'indexed_image_classification',
            name=name,
            idxs=range(len(images)),
            all_images=images,
            all_labels=np.asarray(labels),
            n_classes=self.n_prototypes)

    def protocol(self, algo):
        rng = np.random.RandomState(self.seed)
        n_prototypes = self.n_prototypes

        coords = [prototype_coords(rng) for i in range(n_prototypes)]

        dset = functools.partial(self.distortion_set,
                                 coords=coords,
                                 rng=rng,
                                )

        train_images, train_labels = dset(
            N=self.n_train_per_prototype,
            level=self.train_level)

        test_5_images, test_5_labels = dset(
            N=self.n_test_5_per_prototype,
            level='5')
        test_7_images, test_7_labels = dset(
            N=self.n_test_7_per_prototype,
            level='7.7')

        test_proto_images, test_proto_labels = dset(N=1, level='0')
        test_proto_labels = range(self.n_prototypes)

        # XXX: Careful not to actually expect the model to get these right.
        test_random_images = [
            render_coords_uint8_channels(prototype_coords(rng))
            for c in range(n_prototypes)]
        test_random_labels = range(self.n_prototypes)

        model = algo.best_model(
            train=self.task('train', train_images, train_labels))


        loss_5 = algo.loss(model,
             self.task('test_5', test_5_images, test_5_labels))
        loss_7 = algo.loss(model,
             self.task('test_7', test_7_images, test_7_labels))
        loss_train = algo.loss(model,
             self.task('test_train', train_images, train_labels))
        loss_proto = algo.loss(model,
             self.task('test_proto', test_proto_images, test_proto_labels))
        loss_random = algo.loss(model,
             self.task('test_random', test_random_images, test_random_labels))

        return algo


########NEW FILE########
__FILENAME__ = dataset
"""
http://www.cs.columbia.edu/CAVE/databases/pubfig/

The PubFig database is a large, real-world face dataset consisting of 58,797
images of 200 people collected from the internet. Unlike most other existing
face datasets, these images are taken in completely uncontrolled situations
with non-cooperative subjects. Thus, there is large variation in pose,
lighting, expression, scene, camera, imaging conditions and parameters, etc.

Citation

The database is made available only for non-commercial use. If you use this
dataset, please cite the following paper:

    "Attribute and Simile Classifiers for Face Verification,"
    Neeraj Kumar, Alexander C. Berg, Peter N. Belhumeur, and Shree K. Nayar,
    International Conference on Computer Vision (ICCV), 2009.

"""

# Copyright (C) 2013
# Authors: James Bergstra <james.bergstra@uwaterloo.ca>

# License: Simplified BSD
import os

from skdata.data_home import get_data_home
from skdata.utils import download


def url_of(filename):
    root = 'http://www.cs.columbia.edu/CAVE/databases/pubfig/download/'
    return root + filename

urls = dict([(filename, url_of(filename)) for filename in [
    'dev_people.txt',
    'dev_urls.txt',
    'eval_people.txt',
    'eval_urls.txt',
    'pubfig_labels.txt',
    'pubfig_full.txt',
    'pubfig_attributes.txt',
        ]])

md5s = {
    'dev_people.txt': None,
    'dev_urls.txt': None,
    'eval_people.txt': None,
    'eval_urls.txt': None,
    'pubfig_labels.txt': None,
    'pubfig_full.txt': None,
    'pubfig_attributes.txt': None,
        }

class PubFig(object):
    def __init__(self):
        self.name = self.__class__.__name__

    def home(self, *suffix_paths):
        return os.path.join(get_data_home(), self.name, *suffix_paths)

    def fetch(self, download_if_missing=True):
        """Download and extract the dataset."""

        home = self.home()

        if not os.path.exists(home):
            if download_if_missing:
                raise NotImplementedError()
            else:
                raise IOError("'%s' does not exists!" % home)

        for filename, url in urls.items():
            download(url, self.home(filename), md5=md5s[filename])

        return  # XXX REST IS CUT AND PASTE FROM ELSEWHERE

        for fkey, (fname, sha1) in self.FILES.iteritems():
            url = path.join(BASE_URL, fname)
            basename = path.basename(url)
            archive_filename = path.join(home, basename)
            if not path.exists(archive_filename):
                if not download_if_missing:
                    return
                if not path.exists(home):
                    os.makedirs(home)
                download(url, archive_filename, sha1=sha1)


########NEW FILE########
__FILENAME__ = main

from dataset import PubFig

PubFig().fetch()


########NEW FILE########
__FILENAME__ = pubfig83
# -*- coding: utf-8 -*-
"""PubFig83 Dataset

http://www.eecs.harvard.edu/~zak/pubfig83

If you make use of this data, please cite the following paper:

"Scaling-up Biologically-Inspired Computer Vision: A Case-Study on Facebook."
Nicolas Pinto, Zak Stone, Todd Zickler, David D. Cox
IEEE CVPR, Workshop on Biologically Consistent Vision (2011).
http://pinto.scripts.mit.edu/uploads/Research/pinto-stone-zickler-cox-cvpr2011.pdf

Please consult the publication for further information.
"""

# Copyright (C) 2011
# Authors: Zak Stone <zak@eecs.harvard.edu>
#          Dan Yamins <yamins@mit.edu>
#          James Bergstra <bergstra@rowland.harvard.edu>
#          Nicolas Pinto <pinto@rowland.harvard.edu>

# License: Simplified BSD

# XXX: splits (csv-based) for verification and identification tasks (CVPR'11)


import os
from os import path
import shutil
from glob import glob
import hashlib

from data_home import get_data_home
from utils import download, extract
import utils
import utils.image


class PubFig83(object):
    """PubFig83 Face Dataset

    Attributes
    ----------
    meta: list of dict
        Metadata associated with the dataset. For each image with index i,
        meta[i] is a dict with keys:
            name: str
                Name of the individual's face in the image.
            filename: str
                Full path to the image.
            gender: str
                'male or 'female'
            id: int
                Identifier of the image.
            sha1: str
                SHA-1 hash of the image.

    Notes
    -----
    If joblib is available, then `meta` will be cached for faster
    processing. To install joblib use 'pip install -U joblib' or
    'easy_install -U joblib'.
    """

    URL = 'http://www.eecs.harvard.edu/~zak/pubfig83/pubfig83_first_draft.tgz'
    SHA1 = '1fd55188bf7d9c5cc9d68baee57aa09c41bd2246'

    _GENDERS = ['male', 'male', 'female', 'female', 'male', 'female', 'male',
                'male', 'female', 'male', 'female', 'female', 'female',
                'female', 'female', 'male', 'male', 'male', 'male', 'male',
                'male', 'male', 'male', 'female', 'female', 'male', 'male',
                'female', 'female', 'male', 'male', 'female', 'female', 'male',
                'male', 'male', 'male', 'female', 'female', 'female', 'female',
                'female', 'male', 'male', 'female', 'female', 'female',
                'female', 'female', 'female', 'male', 'male', 'female',
                'female', 'female', 'male', 'female', 'female', 'male', 'male',
                'female', 'male', 'female', 'female', 'male', 'female',
                'female', 'male', 'male', 'female', 'female', 'male', 'female',
                'female', 'male', 'male', 'male', 'male', 'female', 'female',
                'male', 'male', 'male']

    def __init__(self, meta=None):
        if meta is not None:
            self._meta = meta

        self.name = self.__class__.__name__

        try:
            from joblib import Memory
            mem = Memory(cachedir=self.home('cache'))
            self._get_meta = mem.cache(self._get_meta)
        except ImportError:
            pass

    def home(self, *suffix_paths):
        return path.join(get_data_home(), self.name, *suffix_paths)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: fetch()
    # ------------------------------------------------------------------------

    def fetch(self, download_if_missing=True):
        """Download and extract the dataset."""

        home = self.home()

        if not download_if_missing:
            raise IOError("'%s' exists!" % home)

        # download archive
        url = self.URL
        sha1 = self.SHA1
        basename = path.basename(url)
        archive_filename = path.join(home, basename)
        if not path.exists(archive_filename):
            if not download_if_missing:
                return
            if not path.exists(home):
                os.makedirs(home)
            download(url, archive_filename, sha1=sha1)

        # extract it
        if not path.exists(self.home('pubfig83')):
            extract(archive_filename, home, sha1=sha1, verbose=True)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: meta
    # ------------------------------------------------------------------------

    @property
    def meta(self):
        if hasattr(self, '_meta'):
            return self._meta
        else:
            self.fetch(download_if_missing=True)
            self._meta = self._get_meta()
            return self._meta

    def _get_meta(self):
        names = sorted(os.listdir(self.home('pubfig83')))
        genders = self._GENDERS
        assert len(names) == len(genders)
        meta = []
        ind = 0
        for gender, name in zip(genders, names):
            img_filenames = sorted(glob(self.home('pubfig83', name, '*.jpg')))
            for img_filename in img_filenames:
                img_data = open(img_filename, 'rb').read()
                sha1 = hashlib.sha1(img_data).hexdigest()
                meta.append(dict(gender=gender, name=name, id=ind,
                                 filename=img_filename, sha1=sha1))
                ind += 1
        return meta

    # ------------------------------------------------------------------------
    # -- Dataset Interface: clean_up()
    # ------------------------------------------------------------------------

    def clean_up(self):
        if path.isdir(self.home()):
            shutil.rmtree(self.home())

    # ------------------------------------------------------------------------
    # -- Helpers
    # ------------------------------------------------------------------------

    def image_path(self, m):
        return self.home('pubfig83', m['name'], m['jpgfile'])

    # ------------------------------------------------------------------------
    # -- Standard Tasks
    # ------------------------------------------------------------------------

    def raw_recognition_task(self):
        names = [m['name'] for m in self.meta]
        paths = [self.image_path(m) for m in self.meta]
        labels = utils.int_labels(names)
        return paths, labels

    def raw_gender_task(self):
        genders = [m['gender'] for m in self.meta]
        paths = [self.image_path(m) for m in self.meta]
        return paths, utils.int_labels(genders)


# ------------------------------------------------------------------------
# -- Drivers for skdata/bin executables
# ------------------------------------------------------------------------

def main_fetch():
    """compatibility with bin/datasets-fetch"""
    PubFig83.fetch(download_if_missing=True)


def main_show():
    """compatibility with bin/datasets-show"""
    from utils.glviewer import glumpy_viewer
    import larray
    pf = PubFig83()
    names = [m['name'] for m in pf.meta]
    paths = [pf.image_path(m) for m in pf.meta]
    glumpy_viewer(
            img_array=larray.lmap(utils.image.ImgLoader(), paths),
            arrays_to_print=[names])

########NEW FILE########
__FILENAME__ = dataset

"""

This is a real-time dataset, reflecting the current situation on the streets of Austin TX.

No declared Dangerous Dog in the City of Austin and Travis County should ever be running at
large. They are court ordered to be restrained at all times and should be wearing a large tag
identifying them as a Dangerous Dog. They have attacked in the past. The owner is required to
provide $100,000 in financial responsibility. If they attack again the court could order them
put to sleep.

Data provided by: City of Austin

"""
import httplib
import json

root = "data.austintexas.gov"
dangerous_dogs_json = "/resource/ri75-pahg.json"

skdata_category = 'Public Safety'
skdata_tags = 'dangerous', 'dogs', 'public safety', 'pets', 'animals'

class DangerousDogs(object):
    """

    Attributes
    ----------
    `meta` is a list of dictionaries with keys:
        'first_name': dog owner's first name
        'last_name': dog owner's last name
        'address': dog owner's address
        'zip_code': dog owner's zip code
        'description_of_dog': free-form string, usually dog's name first
        'location': unclear, I'm guessing estimated location of dog.

    """
    def __init__(self):
        self.conn = httplib.HTTPConnection(root)
        self.conn.request("GET", dangerous_dogs_json)
        r1 = self.conn.getresponse()
        if r1.status == 200: # -- OK
            data1 = r1.read()
            self.meta = json.loads(data1)
        else:
            raise IOError('JSON resource not found', (r1.status, r1.reason))



########NEW FILE########
__FILENAME__ = dataset

"""
Restaurant Inspection Scores

Provides restaurant scores for inspections performed within the last three
years. Online search of this data set also available at:
http://www.ci.austin.tx.us/health/restaurant/search.cfm


Data provided by: City of Austin

"""
import datetime
import httplib
import json

root = "data.austintexas.gov"
resource_json = "/resource/ecmv-9xxi.json"

skdata_tags = 'public safety', 'health', 'restaurants'

def do_casts(dct):
    rval = {
        'score': float(dct['score']),
        'restaurant_name': dct['restaurant_name'],
        'address': {
            'latitude': float(dct['address']['latitude']),
            'longitude': float(dct['address']['longitude']),
            'human_address': dct['address']['human_address'],
            'needs_recoding': bool(dct['address']['needs_recoding']),
            },
        'zip_code': dct['zip_code'],
        'inspection_date': datetime.datetime.fromtimestamp(
            int(dct['inspection_date'])),
        }
    return rval

class RestaurantInspectionScores(object):
    """

    Attributes
    ----------
    `meta` is a list of dictionaries with keys:
        'score': integer score <= 100
        'restaurant_name': string
        'address': dict
            'latitude': float
            'longitude': float
            'human_address': dict
                'address': string
                'city': string
                'zip': string
            'needs_recoding': bool
        'zip_code': string
        'inspection_date': date

    """
    def __init__(self):
        self.conn = httplib.HTTPConnection(root)
        self.conn.request("GET", resource_json)
        r1 = self.conn.getresponse()
        if r1.status == 200: # -- OK
            # XXX: retrieve *all* listings, not just first 1000 given by
            # default
            data1 = r1.read()
            self.meta = map(do_casts, json.loads(data1))
        else:
            raise IOError('JSON resource not found', (r1.status, r1.reason))


########NEW FILE########
__FILENAME__ = main
"""
Commands for the restaurant_inspection

"""
import sys
import logging
import numpy as np

from sklearn.svm import LinearSVC
from skdata.base import SklearnClassifier

from skdata.socrata.austin.restaurant_inspection.dataset \
        import RestaurantInspectionScores

logger = logging.getLogger(__name__)

usage = """
Usage: main.py {print, hist}
"""

def main_print():
    ris = RestaurantInspectionScores()
    for dct in ris.meta:
        print dct


def main_hist():
    import matplotlib.pyplot as plt
    ris = RestaurantInspectionScores()
    scores = [float(dct['score']) for dct in ris.meta]
    print scores
    plt.hist(scores)
    plt.xlabel('Inspection Score')
    plt.ylabel('Frequency')
    plt.title('Restaurant Inspection Scores: Austin, TX')
    plt.show()


def main_coord_scatter():
    import matplotlib.pyplot as plt
    ris = RestaurantInspectionScores()
    scores = [dct['score'] for dct in ris.meta]
    latitudes = [dct['address']['latitude'] for dct in ris.meta]
    longitudes = [dct['address']['longitude'] for dct in ris.meta]
    c = ((np.asarray(scores) - 50) / 50.0)[:, None] + [0, 0, 0]

    plt.scatter(latitudes, longitudes, c=c)
    plt.xlabel('Latitude')
    plt.ylabel('Longitude')
    plt.title('Restaurant Inspection Scores By Location: Austin, TX')
    plt.show()


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    if len(sys.argv) <= 1:
        print usage
        return 1
    else:
        try:
            fn = globals()['main_' + sys.argv[1]]
        except:
            print 'command %s not recognized' % sys.argv[1]
            print usage
            return 1
        return fn()


if __name__ == '__main__':
    sys.exit(main())


########NEW FILE########
__FILENAME__ = test
from functools import partial
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier
from skdata.base import SklearnClassifier
from skdata.socrata.austin.restaurant_inspection.view \
        import LocationClassification5

def test_location_prediction():
    K = 10
    lp = LocationClassification5(K=K)
    algo = SklearnClassifier(
        partial(DecisionTreeClassifier,
            max_depth=1))

    mean_test_error = lp.protocol(algo)

    assert len(algo.results['loss']) == K
    assert len(algo.results['best_model']) == K

    for loss_report in algo.results['loss']:
        print loss_report['task_name'] + \
            (": err = %0.3f" % (loss_report['err_rate']))

    print 'mean test error:', mean_test_error

    # -- the dataset changes with each query potentially, and
    #    for sure changes with time, so don't assert anything too specific about
    #    accuracy.
    #
    #    FWIW, June 22, 2013, I was seeing error like around .48


########NEW FILE########
__FILENAME__ = view
"""
Experiment views on the Iris data set.

"""

import numpy as np
from sklearn import cross_validation

from .dataset import RestaurantInspectionScores
from skdata.base import Task

def remove_dups(lst):
    rval = []
    seen = set()
    for l in lst:
        if l not in seen:
            rval.append(l)
            seen.add(l)
    return rval


class LocationClassification5(object):
    """
    Access train/test splits for K-fold cross-validation as follows:

    """

    def __init__(self, K, rseed=1):
        self.K = K
        self.dataset = RestaurantInspectionScores()
        self.rseed = rseed

    def task(self, name, x, y, split_idx=None):
        return Task('vector_classification',
                    name=name,
                    x=np.asarray(x),
                    y=np.asarray(y),
                    n_classes=3,
                    split_idx=split_idx,
                   )

    def protocol(self, algo):
        meta = list(self.dataset.meta)
        np.random.RandomState(self.rseed).shuffle(meta)
        indexable_names = np.asarray(
            remove_dups(m['restaurant_name'] for m in meta))
        kf = cross_validation.KFold(len(indexable_names), self.K)

        losses = []

        for i, (train_name_idxs, test_name_idxs) in enumerate(kf):
            train_names = set(indexable_names[train_name_idxs])
            test_names = set(indexable_names[test_name_idxs])

            # TODO: there is a numpy idiom for this right?
            #  (searchsorted?)
            def task_of_names(names):
                try:
                    x = [(m['address']['latitude'], m['address']['longitude'])
                        for m in meta if m['restaurant_name'] in names]
                except KeyError:
                    print m
                    raise
                y = [int((m['score'] - 50) / 10)
                        for m in meta if m['restaurant_name'] in names]
                return self.task( 'train_%i' % i, x=x, y=y)

            model = algo.best_model(
                train=task_of_names(train_names),
                valid=None)
            losses.append(
                algo.loss(model,
                    task=task_of_names(test_names)))

        return np.mean(losses)


########NEW FILE########
__FILENAME__ = dataset
# -*- coding: utf-8 -*-
"""The Street View House Numbers (SVHN) Dataset

SVHN is a real-world image dataset for developing machine learning and
object recognition algorithms with minimal requirement on data
preprocessing and formatting. It can be seen as similar in flavor to
MNIST (e.g., the images are of small cropped digits), but incorporates
an order of magnitude more labeled data (over 600,000 digit images) and
comes from a significantly harder, unsolved, real world problem
(recognizing digits and numbers in natural scene images). SVHN is
obtained from house numbers in Google Street View images. 

Overview
--------

    * 10 classes, 1 for each digit. Digit '1' has label 1, '9' has label
    9 and '0' has label 10.

    * 73257 digits for training, 26032 digits for testing, and 531131
    additional, somewhat less difficult samples, to use as extra
    training data

    * Comes in two formats:
        1. Original images with character level bounding boxes.
        2. MNIST-like 32-by-32 images centered around a single character
        (many of the images do contain some distractors at the sides).

Reference
---------

Please cite the following reference in papers using this dataset: Yuval
Netzer, Tao Wang, Adam Coates, Alessandro Bissacco, Bo Wu, Andrew Y. Ng
Reading Digits in Natural Images with Unsupervised Feature Learning NIPS
Workshop on Deep Learning and Unsupervised Feature Learning 2011.

http://ufldl.stanford.edu/housenumbers

For questions regarding the dataset, please contact
streetviewhousenumbers@gmail.com

"""

# Copyright (C) 2012
# Authors: Nicolas Pinto <pinto@rowland.harvard.edu>
#          James Bergstra

# License: Simplified BSD

import logging
import os
from os import path
import shutil

import lockfile

from skdata.data_home import get_data_home
from skdata.utils import download

log = logging.getLogger(__name__)
BASE_URL = "http://ufldl.stanford.edu/housenumbers/"


class CroppedDigits(object):
    """XXX

    Notes
    -----
    If joblib is available, then `meta` will be cached for faster
    processing. To install joblib use 'pip install -U joblib' or
    'easy_install -U joblib'.
    """

    FILES = dict(
        train=('train_32x32.mat', 'e6588cae42a1a5ab5efe608cc5cd3fb9aaffd674'),
        test=('test_32x32.mat', '29b312382ca6b9fba48d41a7b5c19ad9a5462b20'),
        extra=('extra_32x32.mat', 'd7d93fbeec3a7cf69236a18015d56c7794ef7744'),
        )

    def __init__(self, need_extra=True):

        self.name = self.__class__.__name__
        self.need_extra=need_extra

        try:
            from joblib import Memory
            mem = Memory(cachedir=self.home('cache'), verbose=False)
            self._get_meta = mem.cache(self._get_meta)
        except ImportError:
            pass

    def home(self, *suffix_paths):
        return path.join(get_data_home(), self.name, *suffix_paths)

    # ------------------------------------------------------------------------
    # -- Dataset Interface: fetch()
    # ------------------------------------------------------------------------

    def fetch(self, download_if_missing=True):
        """Download and extract the dataset."""

        home = self.home()

        if not download_if_missing:
            raise IOError("'%s' exists!" % home)

        lock = lockfile.FileLock(home)
        if lock.is_locked():
            log.warn('%s is locked, waiting for release' % home)

        with lock:
            for fkey, (fname, sha1) in self.FILES.iteritems():
                url = path.join(BASE_URL, fname)
                basename = path.basename(url)
                archive_filename = self.home(basename)
                marker = self.home(basename + '.marker')
                
                if ('extra' not in url) or self.need_extra:
                    if not path.exists(marker):
                        if not download_if_missing:
                            return
                        if not path.exists(home):
                            os.makedirs(home)
                        download(url, archive_filename, sha1=sha1)
                        open(marker, 'w').close()

    # ------------------------------------------------------------------------
    # -- Dataset Interface: meta
    # ------------------------------------------------------------------------

    @property
    def meta(self):
        if not hasattr(self, '_meta'):
            self.fetch(download_if_missing=True)
            self._meta = self._get_meta()
        return self._meta

    def _get_meta(self):
        meta = dict([(k, {'filename': self.home(v[0])})
                     for k, v in self.FILES.iteritems()])
        return meta

    # ------------------------------------------------------------------------
    # -- Dataset Interface: clean_up()
    # ------------------------------------------------------------------------

    def clean_up(self):
        if path.isdir(self.home()):
            shutil.rmtree(self.home())

########NEW FILE########
__FILENAME__ = test_view
from skdata import svhn


def test_view1_smoke_shape():
    ds = svhn.view.CroppedDigitsStratifiedKFoldView1(k=2)
    assert len(ds.splits) == 2
    assert ds.splits[0].train.x.shape == (36628, 32, 32, 3)
    assert ds.splits[0].train.y.shape == (36628,)
    assert ds.splits[1].train.x.shape == (36629, 32, 32, 3) 
    assert ds.splits[1].train.y.shape == (36629,)


def test_view2_smoke_shape():
    ds = svhn.view.CroppedDigitsView2()
    assert len(ds.splits) == 1
    assert len(ds.splits[0].train.x) == 73257
    assert len(ds.splits[0].train.y) == 73257
    assert ds.splits[0].train.x[0].shape == (32, 32, 3)

########NEW FILE########
__FILENAME__ = view
# Copyright (C) 2012
# Authors: Nicolas Pinto <pinto@rowland.harvard.edu>

# License: Simplified BSD

import numpy as np
from scipy import io

from sklearn.cross_validation import StratifiedShuffleSplit

from ..utils import dotdict
from ..larray import lmap
from ..dslang import Task

from dataset import CroppedDigits


class CroppedDigitsStratifiedKFoldView1(object):

    def __init__(self, k=10):

        from sklearn.cross_validation import StratifiedKFold

        ds = CroppedDigits(need_extra=False)

        mat = io.loadmat(ds.meta['train']['filename'])
        x = np.rollaxis(mat['X'], -1)
        y = mat['y'].ravel()

        cv = StratifiedKFold(y, k=k)

        def split_func(*args):
            trn_idx, tst_idx = args[0][0]
            trn_x, trn_y = x[trn_idx], y[trn_idx]
            tst_x, tst_y = x[tst_idx], y[tst_idx]
            split = dotdict(
                train=dotdict(x=trn_x, y=trn_y),
                test=dotdict(x=tst_x, y=tst_y),
                )
            return split

        splits = lmap(split_func, zip(cv))
        self.dataset = ds
        self.splits = splits


class CroppedDigitsView2(object):

    def __init__(self, x_dtype=np.float32):

        ds = CroppedDigits()

        train_mat = io.loadmat(ds.meta['train']['filename'])
        train_x = np.rollaxis(train_mat['X'], -1).astype(x_dtype)
        train_y = train_mat['y'].ravel().astype(np.int32)
        train = Task(x=train_x, y=train_y)

        test_mat = io.loadmat(ds.meta['test']['filename'])
        test_x = np.rollaxis(test_mat['X'], -1).astype(x_dtype)
        test_y = test_mat['y'].ravel().astype(np.int32)
        test = Task(x=test_x, y=test_y)

        split = dotdict()
        split['train'] = train
        split['test'] = test

        self.dataset = ds
        self.splits = [split]
        self.train = train
        self.test = test


class CroppedDigitsSupervised(object):
    max_n_train = 73257
    max_n_test = 26032

    def __init__(self, x_dtype=np.float32,
                 n_train=max_n_train,
                 n_valid=0,
                 n_test=max_n_test,
                 shuffle_seed=123,
                 channel_major=False,
                ):

        assert n_train + n_valid <= self.max_n_train
        assert n_test <= self.max_n_test

        if shuffle_seed:
            rng = np.random.RandomState(shuffle_seed)
        else:
            rng = None

        ds = CroppedDigits(need_extra=False)

        train_mat = io.loadmat(ds.meta['train']['filename'])
        train_x = np.rollaxis(train_mat['X'], -1)
        train_y = train_mat['y'].ravel().astype(np.int32)
        assert len(train_x) == self.max_n_train

        test_mat = io.loadmat(ds.meta['test']['filename'])
        test_x = np.rollaxis(test_mat['X'], -1)
        test_y = test_mat['y'].ravel().astype(np.int32)
        assert len(test_x) == self.max_n_test

        # train_x and test_x are piled together here partly because I haven't
        # tested downstream code's robustness to Tasks with different values
        # for `all_images`, which should be fine in principle.
        all_x = np.concatenate((train_x, test_x), axis=0)
        all_y = np.concatenate((train_y, test_y), axis=0)
        del train_x, test_x

        assert all_x.dtype == np.uint8
        if 'float' in str(x_dtype):
            all_x = all_x.astype(x_dtype) / 255.0
        else:
            all_x = all_x.astype(x_dtype)

        all_y -= 1
        assert all_y.min() == 0
        assert all_y.max() == 9

        if channel_major:
            all_x = all_x.transpose(0, 3, 1, 2).copy()
            assert all_x.shape[1] == 3
        else:
            assert all_x.shape[3] == 3

        if n_train < self.max_n_train:
            ((fit_idxs, val_idxs),) = StratifiedShuffleSplit(
                y=all_y[:self.max_n_train],
                n_iterations=1,
                test_size=n_valid,
                train_size=n_train,
                indices=True,
                random_state=rng)
        else:
            fit_idxs = np.arange(self.max_n_train)
            val_idxs = np.arange(0)

        sel_idxs = np.concatenate([fit_idxs, val_idxs])

        if n_test < self.max_n_test:
            ((ign_idxs, tst_idxs),) = StratifiedShuffleSplit(
                y=all_y[self.max_n_train:],
                n_iterations=1,
                test_size=n_test,
                indices=True,
                random_state=rng)
            tst_idxs += self.max_n_train
            del ign_idxs
        else:
            tst_idxs = np.arange(self.max_n_train, len(all_x))

        self.dataset = ds
        self.n_classes = 10
        self.fit_idxs = fit_idxs
        self.val_idxs = val_idxs
        self.sel_idxs = sel_idxs
        self.tst_idxs = tst_idxs
        self.all_x = all_x
        self.all_y = all_y

    def protocol(self, algo):
        for _ in self.protocol_iter(algo):
            pass
        return algo

    def protocol_iter(self, algo):

        def task(name, idxs):
            return Task(
                'indexed_image_classification',
                name=name,
                idxs=idxs,
                all_images=self.all_x,
                all_labels=self.all_y,
                n_classes=self.n_classes)

        task_fit = task('fit', self.fit_idxs)
        task_val = task('val', self.val_idxs)
        task_sel = task('sel', self.sel_idxs)
        task_tst = task('tst', self.tst_idxs)

        if len(self.val_idxs):
            model1 = algo.best_model(train=task_fit, valid=task_val)
            yield ('model validation complete', model1)

        model2 = algo.best_model(train=task_sel)
        algo.loss(model2, task_tst)
        yield ('model testing complete', model2)


########NEW FILE########
__FILENAME__ = synthetic
"""
Synthetic data sets.
"""

# Authors: B. Thirion, G. Varoquaux, A. Gramfort, V. Michel, O. Grisel,
#          G. Louppe, J. Bergstra, D. Warde-Farley
# License: BSD 3 clause

# XXX: main_show would be nice to have for several of these datasets
# 
# XXX: by these datasets default to using a different random state on every call
#      - I think this is bad. Thoughts?
#
# XXX: make some of these datasets infinite to test out that lazy-evaluation
# machinery on meta data.

import numpy as np
from scipy import linalg, sparse

from .utils import check_random_state


class Base(object):
    def __init__(self, X, y=None):
        self._X = X
        self._Y = y

        if y is None:
            self.meta = [dict(x=xi) for xi in self._X]
        else:
            self.meta = [dict(x=xi, y=yi) for xi, yi in zip(self._X, self._Y)]
        self.meta_const = {}
        self.descr = {}


class Regression(object):
    def regression_task(self):
        # XXX: try this
        #      and fall back on rebuilding from self.meta
        return self._X, self._Y


class Classification(object):
    def classification_task(self):
        # XXX: try this
        #      and fall back on rebuilding from self.meta
        return self._X, self._Y


class LatentStructure(object):
    def latent_structure_task(self):
        # XXX: try this
        #      and fall back on rebuilding from self.meta
        return self._X


class Madelon(Base, Classification):
    """Random classification task.

    The algorithm is adapted from Guyon [1] and was designed to generate
    the "Madelon" dataset.

    References
    ----------
    .. [1] I. Guyon, "Design of experiments for the NIPS 2003 variable
           selection benchmark", 2003.

    """
    def __init__(self,
            n_samples=100,
            n_features=20,
            n_informative=2,
            n_redundant=2,
            n_repeated=0,
            n_classes=2,
            n_clusters_per_class=2,
            weights=None,
            flip_y=0.01,
            class_sep=1.0,
            hypercube=True,
            shift=0.0,
            scale=1.0,
            shuffle=True,
            random_state=None):
        """
        Generate a random n-class classification problem.

        Parameters
        ----------
        n_samples : int, optional (default=100)
            The number of samples.

        n_features : int, optional (default=20)
            The total number of features. These comprise `n_informative`
            informative features, `n_redundant` redundant features, `n_repeated`
            dupplicated features and `n_features-n_informative-n_redundant-
            n_repeated` useless features drawn at random.

        n_informative : int, optional (default=2)
            The number of informative features. Each class is composed of a number
            of gaussian clusters each located around the vertices of a hypercube
            in a subspace of dimension `n_informative`. For each cluster,
            informative features are drawn independently from  N(0, 1) and then
            randomly linearly combined in order to add covariance. The clusters
            are then placed on the vertices of the hypercube.

        n_redundant : int, optional (default=2)
            The number of redundant features. These features are generated as
            random linear combinations of the informative features.

        n_repeated : int, optional (default=2)
            The number of dupplicated features, drawn randomly from the informative
            and the redundant features.

        n_classes : int, optional (default=2)
            The number of classes (or labels) of the classification problem.

        n_clusters_per_class : int, optional (default=2)
            The number of clusters per class.

        weights : list of floats or None (default=None)
            The proportions of samples assigned to each class. If None, then
            classes are balanced. Note that if `len(weights) == n_classes - 1`,
            then the last class weight is automatically inferred.

        flip_y : float, optional (default=0.01)
            The fraction of samples whose class are randomly exchanged.

        class_sep : float, optional (default=1.0)
            The factor multiplying the hypercube dimension.

        hypercube : boolean, optional (default=True)
            If True, the clusters are put on the vertices of a hypercube. If
            False, the clusters are put on the vertices of a random polytope.

        shift : float or None, optional (default=0.0)
            Shift all features by the specified value. If None, then features
            are shifted by a random value drawn in [-class_sep, class_sep].

        scale : float or None, optional (default=1.0)
            Multiply all features by the specified value. If None, then features
            are scaled by a random value drawn in [1, 100]. Note that scaling
            happens after shifting.

        shuffle : boolean, optional (default=True)
            Shuffle the samples and the features.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.

        Return
        ------
        X : array of shape [n_samples, n_features]
            The generated samples.

        y : array of shape [n_samples]
            The integer labels for class membership of each sample.
        """
        generator = check_random_state(random_state)

        # Count features, clusters and samples
        assert n_informative + n_redundant + n_repeated <= n_features
        assert 2 ** n_informative >= n_classes * n_clusters_per_class
        assert weights is None or (len(weights) == n_classes or
                                   len(weights) == (n_classes - 1))

        n_useless = n_features - n_informative - n_redundant - n_repeated
        n_clusters = n_classes * n_clusters_per_class

        if weights and len(weights) == (n_classes - 1):
            weights.append(1.0 - sum(weights))

        if weights is None:
            weights = [1.0 / n_classes] * n_classes
            weights[-1] = 1.0 - sum(weights[:-1])

        n_samples_per_cluster = []

        for k in xrange(n_clusters):
            n_samples_per_cluster.append(int(n_samples * weights[k % n_classes]
                                         / n_clusters_per_class))

        for i in xrange(n_samples - sum(n_samples_per_cluster)):
            n_samples_per_cluster[i % n_clusters] += 1

        # Intialize X and y
        X = np.zeros((n_samples, n_features))
        y = np.zeros(n_samples, dtype='int')

        # Build the polytope
        from itertools import product
        C = np.array(list(product([-class_sep, class_sep], repeat=n_informative)))

        if not hypercube:
            for k in xrange(n_clusters):
                C[k, :] *= generator.rand()

            for f in xrange(n_informative):
                C[:, f] *= generator.rand()

        generator.shuffle(C)

        # Loop over all clusters
        pos = 0
        pos_end = 0

        for k in xrange(n_clusters):
            # Number of samples in cluster k
            n_samples_k = n_samples_per_cluster[k]

            # Define the range of samples
            pos = pos_end
            pos_end = pos + n_samples_k

            # Assign labels
            y[pos:pos_end] = k % n_classes

            # Draw features at random
            X[pos:pos_end, :n_informative] = generator.randn(n_samples_k,
                                                             n_informative)

            # Multiply by a random matrix to create co-variance of the features
            A = 2 * generator.rand(n_informative, n_informative) - 1
            X[pos:pos_end, :n_informative] = np.dot(X[pos:pos_end, :n_informative],
                                                    A)

            # Shift the cluster to a vertice
            X[pos:pos_end, :n_informative] += np.tile(C[k, :], (n_samples_k, 1))

        # Create redundant features
        if n_redundant > 0:
            B = 2 * generator.rand(n_informative, n_redundant) - 1
            X[:, n_informative:n_informative + n_redundant] = \
                                                np.dot(X[:, :n_informative], B)

        # Repeat some features
        if n_repeated > 0:
            n = n_informative + n_redundant
            indices = ((n - 1) * generator.rand(n_repeated) + 0.5).astype(np.int)
            X[:, n:n + n_repeated] = X[:, indices]

        # Fill useless features
        X[:, n_features - n_useless:] = generator.randn(n_samples, n_useless)

        # Randomly flip labels
        if flip_y >= 0.0:
            for i in xrange(n_samples):
                if generator.rand() < flip_y:
                    y[i] = generator.randint(n_classes)

        # Randomly shift and scale
        constant_shift = shift is not None
        constant_scale = scale is not None

        for f in xrange(n_features):
            if not constant_shift:
                shift = (2 * generator.rand() - 1) * class_sep

            if not constant_scale:
                scale = 1 + 100 * generator.rand()

            X[:, f] += shift
            X[:, f] *= scale

        # Randomly permute samples and features
        if shuffle:
            indices = range(n_samples)
            generator.shuffle(indices)
            X = X[indices]
            y = y[indices]

            indices = range(n_features)
            generator.shuffle(indices)
            X[:, :] = X[:, indices]

        Base.__init__(self, X, y)


class FourRegions(Base, Classification):
    """The four regions classification task.

    A classic benchmark task for non-linear classifiers. Generates
    a 2-dimensional dataset on the [-1, 1]^2 square where two
    concentric rings are divided in half, and opposing sides of
    the inner and outer circles are assigned to the same class,
    with two more classes formed from the two halves of the square
    excluding the rings.

    References
    ----------

    .. [1] S. Singhal and L. Wu, "Training multilayer perceptrons
           with the extended Kalman algorithm". Advances in Neural
           Information Processing Systems, Proceedings of the 1988
           Conference, pp.133-140.
           http://books.nips.cc/papers/files/nips01/0133.pdf
    """
    def __init__(self, n_samples=100, n_features=2, random_state=None):
        """Generate a (finite) dataset for the four regions task.

        Parameters
        ----------
        n_samples : int, optional
            The number of samples to generate in this instance of the
            dataset.

        n_features : int, optional
            The number of features (dimensionality of the task). The
            default, 2, recovers the standard four regions task, but
            the task can be meaningfully generalized to higher
            dimensions (though the class balance will change).

        random_state : int, RandomState instance or None, optional
            If int, random_state is the seed used by the random number
            generator; If RandomState instance, random_state is the
            random number generator; If None, the random number
            generator is the RandomState instance used by `np.random`.
        """
        assert n_features >= 2, ("Cannot generate FourRegions dataset with "
                                 "n_features < 2")
        generator = check_random_state(random_state)
        X = generator.uniform(-1, 1, size=(n_samples, n_features))
        y = -np.ones(X.shape[0], dtype=int)
        top_half = X[:, 1] > 0
        right_half = X[:, 0] > 0
        dists = np.sqrt(np.sum(X ** 2, axis=1))

        # The easy ones -- the outer shelf.
        outer = dists > 5. / 6.
        y[np.logical_and(top_half, outer)] = 2
        y[np.logical_and(np.logical_not(top_half), outer)] = 3
        first_ring = np.logical_and(dists > 1. / 6., dists <= 1. / 2.)
        second_ring = np.logical_and(dists > 1. / 2., dists <= 5. / 6.)

        # Region 2 -- right inner and left outer, excluding center nut
        y[np.logical_and(first_ring, right_half)] = 1
        y[np.logical_and(second_ring, np.logical_not(right_half))] = 1

        # Region 1 -- left inner and right outer, including center nut
        y[np.logical_and(second_ring, right_half)] = 0
        y[np.logical_and(np.logical_not(right_half), dists < 1. / 2.)] = 0
        y[np.logical_and(right_half, dists < 1. / 6.)] = 0

        assert np.all(y >= 0)
        Base.__init__(self, X, y)

    @classmethod
    def main_show(cls, n_samples=50000):
        dataset = cls(n_samples=n_samples)
        import matplotlib.pyplot as plt
        X, y = dataset.classification_task()
        plt.scatter(X[:, 0], X[:, 1], 10, y, cmap='gray')
        plt.axis('equal')
        plt.title('%d samples from the four regions task' % len(X))
        plt.show()


class Randlin(Base, Regression):
    """Random linear regression problem.

    The input set can either be well conditioned (by default) or have a low
    rank-fat tail singular profile. See the `make_low_rank_matrix` for
    more details.

    The output is generated by applying a (potentially biased) random linear
    regression model with `n_informative` nonzero regressors to the previously
    generated input and some gaussian centered noise with some adjustable
    scale.
    """
    def __init__(self, n_samples=100, n_features=100, n_informative=10,
            bias=0.0, effective_rank=None, tail_strength=0.5, noise=0.0,
            shuffle=True, coef=False, random_state=None):
        """

        Parameters
        ----------
        n_samples : int, optional (default=100)
            The number of samples.

        n_features : int, optional (default=100)
            The number of features.

        n_informative : int, optional (default=10)
            The number of informative features, i.e., the number of features used
            to build the linear model used to generate the output.

        bias : float, optional (default=0.0)
            The bias term in the underlying linear model.

        effective_rank : int or None, optional (default=None)
            if not None:
                The approximate number of singular vectors required to explain most
                of the input data by linear combinations. Using this kind of
                singular spectrum in the input allows the generator to reproduce
                the correlations often observed in practice.
            if None:
                The input set is well conditioned, centered and gaussian with
                unit variance.

        tail_strength : float between 0.0 and 1.0, optional (default=0.5)
            The relative importance of the fat noisy tail of the singular values
            profile if `effective_rank` is not None.

        noise : float, optional (default=0.0)
            The standard deviation of the gaussian noise applied to the output.

        shuffle : boolean, optional (default=True)
            Shuffle the samples and the features.

        coef : boolean, optional (default=False)
            If True, the coefficients of the underlying linear model are returned.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.

        Returns
        -------
        X : array of shape [n_samples, n_features]
            The input samples.

        y : array of shape [n_samples]
            The output values.

        coef : array of shape [n_features], optional
            The coefficient of the underlying linear model. It is returned only if
            coef is True.
        """
        generator = check_random_state(random_state)

        if effective_rank is None:
            # Randomly generate a well conditioned input set
            X = generator.randn(n_samples, n_features)

        else:
            # Randomly generate a low rank, fat tail input set
            X = LowRankMatrix(n_samples=n_samples,
                                     n_features=n_features,
                                     effective_rank=effective_rank,
                                     tail_strength=tail_strength,
                                     random_state=generator)._X

        # Generate a ground truth model with only n_informative features being non
        # zeros (the other features are not correlated to y and should be ignored
        # by a sparsifying regularizers such as L1 or elastic net)
        ground_truth = np.zeros(n_features)
        ground_truth[:n_informative] = 100 * generator.rand(n_informative)

        y = np.dot(X, ground_truth) + bias

        # Add noise
        if noise > 0.0:
            y += generator.normal(scale=noise, size=y.shape)

        # Randomly permute samples and features
        if shuffle:
            indices = range(n_samples)
            generator.shuffle(indices)
            X = X[indices]
            y = y[indices]

            indices = range(n_features)
            generator.shuffle(indices)
            X[:, :] = X[:, indices]
            ground_truth = ground_truth[indices]

        Base.__init__(self, X, y[:, None])
        self.ground_truth = ground_truth


class Blobs(Base, Classification, LatentStructure):
    """Generate isotropic Gaussian blobs for clustering.
    """
    def __init__(self, n_samples=100, n_features=2, centers=3, cluster_std=1.0,
                   center_box=(-10.0, 10.0), shuffle=True, random_state=None):
        """

        Parameters
        ----------
        n_samples : int, optional (default=100)
            The total number of points equally divided among clusters.

        n_features : int, optional (default=2)
            The number of features for each sample.

        centers : int or array of shape [n_centers, n_features], optional (default=3)
            The number of centers to generate, or the fixed center locations.

        cluster_std: float or sequence of floats, optional (default=1.0)
            The standard deviation of the clusters.

        center_box: pair of floats (min, max), optional (default=(-10.0, 10.0))
            The bounding box for each cluster center when centers are
            generated at random.

        shuffle : boolean, optional (default=True)
            Shuffle the samples.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.

        Return
        ------
        X : array of shape [n_samples, n_features]
            The generated samples.

        y : array of shape [n_samples]
            The integer labels for cluster membership of each sample.

        """
        generator = check_random_state(random_state)

        if isinstance(centers, int):
            centers = generator.uniform(center_box[0], center_box[1],
                                        size=(centers, n_features))
        else:
            centers = np.atleast_2d(centers)
            n_features = centers.shape[1]

        X = []
        y = []

        n_centers = centers.shape[0]
        n_samples_per_center = [n_samples / n_centers] * n_centers

        for i in xrange(n_samples % n_centers):
            n_samples_per_center[i] += 1

        for i, n in enumerate(n_samples_per_center):
            X.append(centers[i] + generator.normal(scale=cluster_std,
                                                   size=(n, n_features)))
            y += [i] * n

        X = np.concatenate(X)
        y = np.array(y)

        if shuffle:
            indices = np.arange(n_samples)
            generator.shuffle(indices)
            X = X[indices]
            y = y[indices]

        Base.__init__(self, X, y)

    @classmethod
    def main_show(cls):
        self = cls(n_samples=500)
        import matplotlib.pyplot as plt
        plt.scatter(self._X[:, 0], self._X[:, 1])
        plt.show()


class Friedman1(Base, Regression):
    def __init__(self, n_samples=100, n_features=10, noise=0.0, random_state=None):
        """
        Generate the "Friedman #1" regression problem as described in Friedman [1]
        and Breiman [2].

        Inputs `X` are independent features uniformly distributed on the interval
        [0, 1]. The output `y` is created according to the formula::

            y(X) = 10 * sin(pi * X[:, 0] * X[:, 1]) + 20 * (X[:, 2] - 0.5) ** 2 \
                   + 10 * X[:, 3] + 5 * X[:, 4] + noise * N(0, 1).

        Out of the `n_features` features, only 5 are actually used to compute
        `y`. The remaining features are independent of `y`.

        The number of features has to be >= 5.

        Parameters
        ----------
        n_samples : int, optional (default=100)
            The number of samples.

        n_features : int, optional (default=10)
            The number of features. Should be at least 5.

        noise : float, optional (default=0.0)
            The standard deviation of the gaussian noise applied to the output.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.

        Returns
        -------
        X : array of shape [n_samples, n_features]
            The input samples.

        y : array of shape [n_samples]
            The output values.

        References
        ----------
        .. [1] J. Friedman, "Multivariate adaptive regression splines", The Annals
               of Statistics 19 (1), pages 1-67, 1991.

        .. [2] L. Breiman, "Bagging predictors", Machine Learning 24,
               pages 123-140, 1996.
        """
        assert n_features >= 5

        generator = check_random_state(random_state)

        X = generator.rand(n_samples, n_features)
        y = 10 * np.sin(np.pi * X[:, 0] * X[:, 1]) + 20 * (X[:, 2] - 0.5) ** 2 \
            + 10 * X[:, 3] + 5 * X[:, 4] + noise * generator.randn(n_samples)

        Base.__init__(self, X, y[:, None])


class Friedman2(Base, Regression):
    def __init__(self, n_samples=100, noise=0.0, random_state=None):
        """
        Generate the "Friedman #2" regression problem as described in Friedman [1]
        and Breiman [2].

        Inputs `X` are 4 independent features uniformly distributed on the
        intervals::

            0 <= X[:, 0] <= 100,
            40 * pi <= X[:, 1] <= 560 * pi,
            0 <= X[:, 2] <= 1,
            1 <= X[:, 3] <= 11.

        The output `y` is created according to the formula::

            y(X) = (X[:, 0] ** 2 \
                       + (X[:, 1] * X[:, 2] \
                             - 1 / (X[:, 1] * X[:, 3])) ** 2) ** 0.5 \
                   + noise * N(0, 1).

        Parameters
        ----------
        n_samples : int, optional (default=100)
            The number of samples.

        noise : float, optional (default=0.0)
            The standard deviation of the gaussian noise applied to the output.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.

        Returns
        -------
        X : array of shape [n_samples, 4]
            The input samples.

        y : array of shape [n_samples]
            The output values.

        References
        ----------
        .. [1] J. Friedman, "Multivariate adaptive regression splines", The Annals
               of Statistics 19 (1), pages 1-67, 1991.

        .. [2] L. Breiman, "Bagging predictors", Machine Learning 24,
               pages 123-140, 1996.
        """
        generator = check_random_state(random_state)

        X = generator.rand(n_samples, 4)
        X[:, 0] *= 100
        X[:, 1] *= 520 * np.pi
        X[:, 1] += 40 * np.pi
        X[:, 3] *= 10
        X[:, 3] += 1

        y = (X[:, 0] ** 2
                + (X[:, 1] * X[:, 2] - 1 / (X[:, 1] * X[:, 3])) ** 2) ** 0.5 \
            + noise * generator.randn(n_samples)

        return Base.__init__(self, X, y[:, None])


class Friedman3(Base, Regression):
    def __init__(self, n_samples=100, noise=0.0, random_state=None):
        """
        Generate the "Friedman #3" regression problem as described in Friedman [1]
        and Breiman [2].

        Inputs `X` are 4 independent features uniformly distributed on the
        intervals::

            0 <= X[:, 0] <= 100,
            40 * pi <= X[:, 1] <= 560 * pi,
            0 <= X[:, 2] <= 1,
            1 <= X[:, 3] <= 11.

        The output `y` is created according to the formula::

            y(X) = arctan((X[:, 1] * X[:, 2] \
                              - 1 / (X[:, 1] * X[:, 3])) \
                          / X[:, 0]) \
                   + noise * N(0, 1).

        Parameters
        ----------
        n_samples : int, optional (default=100)
            The number of samples.

        noise : float, optional (default=0.0)
            The standard deviation of the gaussian noise applied to the output.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.

        Returns
        -------
        X : array of shape [n_samples, 4]
            The input samples.

        y : array of shape [n_samples]
            The output values.

        References
        ----------
        .. [1] J. Friedman, "Multivariate adaptive regression splines", The Annals
               of Statistics 19 (1), pages 1-67, 1991.

        .. [2] L. Breiman, "Bagging predictors", Machine Learning 24,
               pages 123-140, 1996.
        """
        generator = check_random_state(random_state)

        X = generator.rand(n_samples, 4)
        X[:, 0] *= 100
        X[:, 1] *= 520 * np.pi
        X[:, 1] += 40 * np.pi
        X[:, 3] *= 10
        X[:, 3] += 1

        y = np.arctan((X[:, 1] * X[:, 2] - 1 / (X[:, 1] * X[:, 3])) / X[:, 0]) \
            + noise * generator.randn(n_samples)

        Base.__init__(self, X, y[:, None])


class LowRankMatrix(Base, LatentStructure):
    """Mostly low rank random matrix with bell-shaped singular values profile.

    Most of the variance can be explained by a bell-shaped curve of width
    effective_rank: the low rank part of the singular values profile is::

        (1 - tail_strength) * exp(-1.0 * (i / effective_rank) ** 2)

    The remaining singular values' tail is fat, decreasing as::

        tail_strength * exp(-0.1 * i / effective_rank).

    The low rank part of the profile can be considered the structured
    signal part of the data while the tail can be considered the noisy
    part of the data that cannot be summarized by a low number of linear
    components (singular vectors).

    This kind of singular profiles is often seen in practice, for instance:
     - graw level pictures of faces
     - TF-IDF vectors of text documents crawled from the web
    """
    def __init__(self, n_samples=100, n_features=100, effective_rank=10,
                             tail_strength=0.5, random_state=None):
        """

        Parameters
        ----------
        n_samples : int, optional (default=100)
            The number of samples.

        n_features : int, optional (default=100)
            The number of features.

        effective_rank : int, optional (default=10)
            The approximate number of singular vectors required to explain most of
            the data by linear combinations.

        tail_strength : float between 0.0 and 1.0, optional (default=0.5)
            The relative importance of the fat noisy tail of the singular values
            profile.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.

        Returns
        -------
        X : array of shape [n_samples, n_features]
            The matrix.
        """
        generator = check_random_state(random_state)
        n = min(n_samples, n_features)

        # Random (ortho normal) vectors
        from .utils import qr_economic
        u, _ = qr_economic(generator.randn(n_samples, n))
        v, _ = qr_economic(generator.randn(n_features, n))

        # Index of the singular values
        singular_ind = np.arange(n, dtype=np.float64)

        # Build the singular profile by assembling signal and noise components
        low_rank = (1 - tail_strength) * \
                   np.exp(-1.0 * (singular_ind / effective_rank) ** 2)
        tail = tail_strength * np.exp(-0.1 * singular_ind / effective_rank)
        s = np.identity(n) * (low_rank + tail)

        Base.__init__(self, np.dot(np.dot(u, s), v.T))

        self.descr['mask'] = generator.randint(3, size=self._X.shape)

    def matrix_completion_task(self):
        X = sparse.csr_matrix(self._X * (self.descr['mask'] == 0))
        Y = sparse.csr_matrix(self._X * (self.descr['mask'] == 1))
        assert X.nnz == (self.descr['mask'] == 0).sum()
        assert Y.nnz == (self.descr['mask'] == 1).sum()
        # where mask is 2 is neither in X nor Y
        return X, Y


class SparseCodedSignal(Base, LatentStructure):
    """Generate a signal as a sparse combination of dictionary elements.

    Returns a matrix Y = DX, such as D is (n_features, n_components),
    X is (n_components, n_samples) and each column of X has exactly
    n_nonzero_coefs non-zero elements.

    """
    def __init__(self, n_samples, n_components, n_features, n_nonzero_coefs,
            random_state=None):
        """
        Parameters
        ----------
        n_samples : int
            number of samples to generate

        n_components:  int,
            number of components in the dictionary

        n_features : int
            number of features of the dataset to generate

        n_nonzero_coefs : int
            number of active (non-zero) coefficients in each sample

        random_state: int or RandomState instance, optional (default=None)
            seed used by the pseudo random number generator

        Returns
        -------
        data: array of shape [n_features, n_samples]
            The encoded signal (Y).

        dictionary: array of shape [n_features, n_components]
            The dictionary with normalized components (D).

        code: array of shape [n_components, n_samples]
            The sparse code such that each column of this matrix has exactly
            n_nonzero_coefs non-zero items (X).

        """
        generator = check_random_state(random_state)

        # generate dictionary
        D = generator.randn(n_features, n_components)
        D /= np.sqrt(np.sum((D ** 2), axis=0))

        # generate code
        X = np.zeros((n_components, n_samples))
        for i in xrange(n_samples):
            idx = np.arange(n_components)
            generator.shuffle(idx)
            idx = idx[:n_nonzero_coefs]
            X[idx, i] = generator.randn(n_nonzero_coefs)

        # XXX: self.meta should include list of non-zeros in X
        # XXX: self.descr should include dictionary D
        self.D = D
        self.X = X
        Base.__init__(self, np.dot(D, X))


class SparseUncorrelated(Base, Regression):
    """Generate a random regression problem with sparse uncorrelated design
    as described in Celeux et al [1].::

        X ~ N(0, 1)
        y(X) = X[:, 0] + 2 * X[:, 1] - 2 * X[:, 2] - 1.5 * X[:, 3]

    Only the first 4 features are informative. The remaining features are
    useless.

    References
    ----------
    .. [1] G. Celeux, M. El Anbari, J.-M. Marin, C. P. Robert,
           "Regularization in regression: comparing Bayesian and frequentist
           methods in a poorly informative situation", 2009.

    """
    def __init__(self, n_samples=100, n_features=10, random_state=None):
        """
        Parameters
        ----------
        n_samples : int, optional (default=100)
            The number of samples.

        n_features : int, optional (default=10)
            The number of features.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.

        """
        generator = check_random_state(random_state)
        X = generator.normal(loc=0, scale=1, size=(n_samples, n_features))
        y = generator.normal(loc=(X[:, 0] +
                                  2 * X[:, 1] -
                                  2 * X[:, 2] -
                                  1.5 * X[:, 3]), scale=np.ones(n_samples))
        Base.__init__(self, X, y[:, None])


class SwissRoll(Base, Regression, LatentStructure):
    """Generate a swiss roll dataset.

    Notes
    -----
    The algorithm is from Marsland [1].

    References
    ----------
    .. [1] S. Marsland, "Machine Learning: An Algorithmic Perpsective",
           Chapter 10, 2009.
           http://www-ist.massey.ac.nz/smarsland/Code/10/lle.py
    """
    def __init__(self, n_samples=100, noise=0.0, random_state=None):
        """
        Parameters
        ----------
        n_samples : int, optional (default=100)
            The number of sample points on the S curve.

        noise : float, optional (default=0.0)
            The standard deviation of the gaussian noise.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.

        Returns
        -------
        X : array of shape [n_samples, 3]
            The points.

        t : array of shape [n_samples]
            The univariate position of the sample according to the main dimension
            of the points in the manifold.
        """
        generator = check_random_state(random_state)

        t = 1.5 * np.pi * (1 + 2 * generator.rand(1, n_samples))
        x = t * np.cos(t)
        y = 21 * generator.rand(1, n_samples)
        z = t * np.sin(t)

        X = np.concatenate((x, y, z))
        X += noise * generator.randn(3, n_samples)
        X = X.T
        t = np.squeeze(t)
        Base.__init__(self, X, t[:, None])

    @classmethod
    def main_show(cls):
        self = cls(n_samples=1000)
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(self._X[:, 2], self._X[:, 1], self._X[:, 0])
        plt.show()


class S_Curve(Base, Regression, LatentStructure):
    """Generate an S curve dataset.
    """
    def __init__(self, n_samples=100, noise=0.0, random_state=None):
        """

        Parameters
        ----------
        n_samples : int, optional (default=100)
            The number of sample points on the S curve.

        noise : float, optional (default=0.0)
            The standard deviation of the gaussian noise.

        random_state : int, RandomState instance or None, optional (default=None)
            If int, random_state is the seed used by the random number generator;
            If RandomState instance, random_state is the random number generator;
            If None, the random number generator is the RandomState instance used
            by `np.random`.
        """
        generator = check_random_state(random_state)

        t = 3 * np.pi * (generator.rand(1, n_samples) - 0.5)
        x = np.sin(t)
        y = 2.0 * generator.rand(1, n_samples)
        z = np.sign(t) * (np.cos(t) - 1)

        X = np.concatenate((x, y, z))
        X += noise * generator.randn(3, n_samples)
        X = X.T
        t = np.squeeze(t)

        Base.__init__(self, X, t[:, None])

    @classmethod
    def main_show(cls):
        self = cls(n_samples=1000)
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(self._X[:, 2], self._X[:, 1], self._X[:, 0])
        plt.show()



########NEW FILE########
__FILENAME__ = tasks
"""Task API
"""
import numpy as np

import larray


def assert_classification(X, y, N=None):
    assert X.ndim == 2
    assert y.ndim == 1
    A = len(X)  # xxx: replace with X.shape[0] if using shapes with unknowns?
    C, = y.shape
    assert A == C == (C if N is None else N)
    assert 'float' in str(X.dtype)
    assert 'int' in str(y.dtype), y.dtype


def assert_img_classification(X, y, N=None):
    assert X.ndim == 4
    assert y.ndim == 1
    A = len(X)  # xxx: replace with X.shape[0] if using shapes with unknowns?
    C, = y.shape
    #todo:  if we get to handling shapes with 'unknowns', e.g. None's
    #then maybe here we could check that X.shape[2] is not None, e.g. the
    #number of channels  of the images are all the same.  or maybe not?
    assert A == C == (C if N is None else N)
    assert 'float' in str(X.dtype)
    assert 'int' in str(y.dtype), y.dtype


def assert_img_verification(X, Y, z, N=None):
    assert X.ndim == 4
    assert Y.ndim == 4
    assert z.ndim == 1
    A = len(X)
    B = len(Y)
    C, = z.shape
    assert A == B == C == (C if N is None else N)
    assert 'float' in str(X.dtype)
    assert 'float' in str(Y.dtype)
    assert 'int' in str(z.dtype), z.dtype
    assert set(np.unique(z)) <= set([0, 1])


def assert_classification_train_valid_test(train, valid, test):
    assert_classification(*train)
    assert_classification(*valid)
    assert_classification(*test)

    X_train, y_train = train
    X_valid, y_valid = valid
    X_test, y_test = test

    assert X_train.shape[1] == X_valid.shape[1]
    assert X_train.shape[1] == X_test.shape[1]


def assert_regression(X, Y, N=None):
    assert X.ndim == 2
    assert Y.ndim == 2
    A, B = X.shape
    C, D = Y.shape
    assert A == C == (C if N is None else N)
    assert 'float' in str(X.dtype)
    assert 'float' in str(Y.dtype)


def assert_matrix_completion(X, Y, N=None):
    A, B = X.shape
    C, D = Y.shape
    assert A == C == (C if N is None else N)
    assert 'float' in str(X.dtype)
    assert 'float' in str(Y.dtype)
    assert X.nnz
    assert Y.nnz


def assert_latent_structure(X, N=None):
    assert X.ndim == 2
    A, B = X.shape
    assert A == (A if N is None else N)
    assert 'float' in str(X.dtype)


def classification_train_valid_test(dataset):
    """
    :returns: the standard train/valid/test split.
    :rtype: (X_train, y_train), (X_valid, y_valid), (X_test, y_test)

    """

    if hasattr(dataset, 'classification_train_valid_test_task'):
        return dataset.classification_train_valid_test_task()

    X, y = dataset.classification_task()

    # construct the standard splits by convention of the .meta attribute
    splits = [m['split'] for m in dataset.meta]
    train_idxs = [i for i, s in enumerate(splits) if s == 'train']
    valid_idxs = [i for i, s in enumerate(splits) if s == 'valid']
    test_idxs = [i for i, s in enumerate(splits) if s == 'test']

    if len(splits) != len(X):
        raise ValueError('Length of X does not match length of meta data')

    if len(train_idxs) + len(valid_idxs) + len(test_idxs) != len(splits):
        raise ValueError('meta contains splits other than train, valid, test.')

    X_train = larray.reindex(X, train_idxs)
    X_valid = larray.reindex(X, valid_idxs)
    X_test = larray.reindex(X, test_idxs)

    y_train = larray.reindex(y, train_idxs)
    y_valid = larray.reindex(y, valid_idxs)
    y_test = larray.reindex(y, test_idxs)

    return (X_train, y_train), (X_valid, y_valid), (X_test, y_test)

########NEW FILE########
__FILENAME__ = test_brodatz

from skdata.brodatz import *


def test_smoke():
    ds = Brodatz()
    assert len(ds.meta) == 111

    for m in ds.meta:
        assert (600, 600) < m['image']['shape'] < (700, 700), m


########NEW FILE########
__FILENAME__ = test_caltech
import numpy as np

from skdata import caltech
from skdata import tasks

counts_101 = [467, 435, 435, 200, 798, 55, 800, 42, 42, 47, 54, 46, 33, 128,
98, 43, 85, 91, 50, 43, 123, 47, 59, 62, 107, 47, 69, 73, 70, 50, 51, 57, 67,
52, 65, 68, 75, 64, 53, 64, 85, 67, 67, 45, 34, 34, 51, 99, 100, 42, 54, 88,
80, 31, 64, 86, 114, 61, 81, 78, 41, 66, 43, 40, 87, 32, 76, 55, 35, 39, 47,
38, 45, 53, 34, 57, 82, 59, 49, 40, 63, 39, 84, 57, 35, 64, 45, 86, 59, 64, 35,
85, 49, 86, 75, 239, 37, 59, 34, 56, 39, 60]

caltech_101_breaks = [466, 901, 1336, 1536, 2334, 2389, 3189, 3231, 3273, 3320,
3374, 3420, 3453, 3581, 3679, 3722, 3807, 3898, 3948, 3991, 4114, 4161, 4220,
4282, 4389, 4436, 4505, 4578, 4648, 4698, 4749, 4806, 4873, 4925, 4990, 5058,
5133, 5197, 5250, 5314, 5399, 5466, 5533, 5578, 5612, 5646, 5697, 5796, 5896,
5938, 5992, 6080, 6160, 6191, 6255, 6341, 6455, 6516, 6597, 6675, 6716, 6782,
6825, 6865, 6952, 6984, 7060, 7115, 7150, 7189, 7236, 7274, 7319, 7372, 7406,
7463, 7545, 7604, 7653, 7693, 7756, 7795, 7879, 7936, 7971, 8035, 8080, 8166,
8225, 8289, 8324, 8409, 8458, 8544, 8619, 8858, 8895, 8954, 8988, 9044, 9083]


def test_Caltech101():
    dset = caltech.Caltech101()
    task = dset.img_classification_task(dtype='float32')
    tasks.assert_img_classification(*task, N=9144)

    X, y = task
    assert X[0].shape == (144, 145, 3)
    assert X[1].shape == (817, 656, 3)
    assert X[100].shape == (502, 388, 3)

    assert len(np.unique(y)) == 102  # number of categories
    ylist = y.tolist()
    counts = [ylist.count(z) for z in np.unique(ylist)]
    assert counts == counts_101

    z = y.copy()
    z.sort()
    assert (y == z).all()

    assert (y[1:] != y[:-1]).nonzero()[0].tolist() == caltech_101_breaks

def test_Caltech256():
    dset = caltech.Caltech256()
    task = dset.img_classification_task(dtype='float32')
    tasks.assert_img_classification(*task)

########NEW FILE########
__FILENAME__ = test_cifar10
from skdata import cifar10, tasks

def test_CIFAR10():
    cifar = cifar10.CIFAR10()  # just make sure we can create the class
    cifar.DOWNLOAD_IF_MISSING = False
    assert cifar.meta_const['image']['shape'] == (32, 32, 3)
    assert cifar.meta_const['image']['dtype'] == 'uint8'
    assert cifar.descr['n_classes'] == 10
    assert cifar.meta[0] == dict(id=0, label='frog', split='train')
    assert cifar.meta[49999] == dict(id=49999, label='automobile', split='train')
    assert cifar.meta[50000] == dict(id=50000, label='cat', split='test')
    assert cifar.meta[59999] == dict(id=59999, label='horse', split='test')
    assert len(cifar.meta) == 60000


def test_classification():
    cifar = cifar10.CIFAR10()  # just make sure we can create the class
    cifar.DOWNLOAD_IF_MISSING = False
    X, y = cifar.classification_task()
    tasks.assert_classification(X, y, 60000)


def test_latent_structure():
    cifar = cifar10.CIFAR10()  # just make sure we can create the class
    cifar.DOWNLOAD_IF_MISSING = False
    X = cifar.latent_structure_task()
    tasks.assert_latent_structure(X, 60000)


def test_meta_cache():
    a = cifar10.CIFAR10()
    b = cifar10.CIFAR10()
    assert a.meta == b.meta

########NEW FILE########
__FILENAME__ = test_dslang
from ..dslang import Visitor
from ..iris.views import KfoldClassification
import sklearn.linear_model


class SVMAlgo(Visitor):
    def __init__(self, model_factory):
        self.model_factory = model_factory

    def on_BestModel(self, node, memo):
        train = self.evaluate(node.split, memo)
        model = self.model_factory()
        model.fit(train.x, train.y)
        return model

    def on_Score(self, node, memo):
        model = self.evaluate(node.model, memo)
        task = self.evaluate(node.task, memo)
        y_pred = model.predict(task.x)
        return (y_pred == task.y).mean()

def test_dslang():
    kfc = KfoldClassification(2, y_as_int=True)

    def new_model():
        return sklearn.linear_model.SGDClassifier()

    memo = {}
    dsl = kfc.dsl
    SVMAlgo(new_model).evaluate(dsl, memo)

    print 'final score', memo[dsl]



########NEW FILE########
__FILENAME__ = test_larochelle_etal_2007
from skdata import larochelle_etal_2007 as L2007
from skdata import tasks

def dset(name):
    rval = getattr(L2007, name)()
    rval.DOWNLOAD_IF_MISSING = False
    return rval

def test_MnistBasic():
    dsetname = 'MNIST_Basic'

    aa = dset(dsetname)
    aa.DOWNLOAD_IF_MISSING = False
    assert aa.meta_const['image']['shape'] == (28, 28)
    assert aa.meta_const['image']['dtype'] == 'float32'
    assert aa.descr['n_classes'] == 10
    assert aa.meta[0] == dict(id=0, label=5, split='train')
    assert aa.meta[9999] == dict(id=9999, label=7, split='train')
    assert aa.meta[10000] == dict(id=10000, label=3, split='valid')
    assert aa.meta[11999] == dict(id=11999, label=3, split='valid')
    assert aa.meta[12000] == dict(id=12000, label=7, split='test')
    assert aa.meta[50000] == dict(id=50000, label=3, split='test')
    assert aa.meta[61989] == dict(id=61989, label=4, split='test')
    assert len(aa.meta) == 62000

    bb = dset(dsetname)
    assert bb.meta == aa.meta

def test_several():
    dsetnames = ['MNIST_Basic',
            'MNIST_BackgroundImages',
            'MNIST_BackgroundRandom',
            'Rectangles',
            'RectanglesImages',
            'Convex']
    dsetnames.extend(['MNIST_Noise%i' % i for i in range(1,7)])
    for dsetname in dsetnames:

        aa = dset(dsetname)
        assert len(aa.meta) == sum(
                [aa.descr[s] for s in 'n_train', 'n_valid', 'n_test'])

        bb = dset(dsetname)
        assert aa.meta == bb.meta

        tasks.assert_classification(*aa.classification_task())
        tasks.assert_latent_structure(aa.latent_structure_task())


########NEW FILE########
__FILENAME__ = test_larray
import tempfile
import numpy as np
from skdata import larray


def test_usage():
    np.random.seed(123)

    def load_rgb(pth):
        return pth + '_rgb'
    def load_grey(pth):
        return pth + '_grey'
    def to_64x64(img):
        return img + '_64x64'

    paths = ['a', 'b', 'c', 'd']  # imagine some huge list of image paths
    rgb_imgs = larray.lmap(load_rgb, paths)

    train_set = larray.reindex(rgb_imgs, np.random.permutation(len(paths))
                              ).loop()

    l10 = list(train_set[range(10)])
    print l10
    assert ['d', 'a', 'b', 'c'] == [l[0] for l in l10[:4]]


def test_using_precompute():
    np.random.seed(123)

    # example library code  starts here
    def load_rgb(pth):
        return pth + '_rgb'
    def load_grey(pth):
        return pth + '_grey'
    def to_64x64(img):
        return img + '_64x64'

    paths = ['a', 'b', 'c', 'd']  # imagine some huge list of image paths
    grey_imgs = larray.lmap(load_grey, paths)
    paths_64x64 = larray.lmap(to_64x64, grey_imgs)

    train_set = larray.reindex(paths_64x64, np.random.permutation(len(paths))
                              ).loop()

    # example user code starts here.
    # It is easy to memmap the __array__ of paths_64x64, but
    # it is more difficult to compute derived things using that
    # memmap.
    
    # pretend this is a memmap of a precomputed quantity, for example.
    use_paths_64x64 = ['stuff', 'i', 'saved', 'from', 'disk']

    # the rest of the original graph (e.g. train_set)
    # doesn't know about our new memmap
    # or mongo-backed proxy, or whatever we're doing.

    new_train_set = larray.clone(train_set, given={paths_64x64: use_paths_64x64})

    l10 = list(new_train_set[range(10)])
    print l10
    assert l10 == [
            'from', 'stuff', 'i', 'saved',
            'from', 'stuff', 'i', 'saved',
            'from', 'stuff']


def test_lprint():
    paths = None
    rgb_imgs = larray.lmap(test_lprint, paths)
    rgb_imgs2 = larray.lmap(test_lprint, rgb_imgs)
    s = larray.lprint_str(rgb_imgs2)
    print s
    assert s == """lmap(test_lprint, ...)
    lmap(test_lprint, ...)
        None\n"""

larray.cache_memmap.ROOT = tempfile.mkdtemp(prefix="skdata_test_memmap_root")

class TestCache(object):
    def battery(self, cls):
        base0 = np.arange(10)
        base1 = -np.arange(10)
        base = np.vstack([base0, base1]).T
        # base[0] = [0, 0]
        # base[1] = [1, -1]
        # ...
        cpy = larray.lzip(base0, base1)
        cached = cls(cpy)
        assert cached.dtype == base.dtype
        assert cached.shape == base.shape
        def assert_np_eq(l, r):
            assert np.all(l == r), (l, r)
        assert_np_eq(cached._valid, 0)
        assert cached.rows_computed == 0
        assert_np_eq(cached[4], base[4])
        assert_np_eq(cached._valid, [0, 0, 0, 0, 1, 0, 0, 0, 0, 0])
        assert cached.rows_computed == 1
        assert_np_eq(cached[1], base[1])
        assert_np_eq(cached._valid, [0, 1, 0, 0, 1, 0, 0, 0, 0, 0])
        assert_np_eq(cached[0:5], base[0:5])
        n_computed = cached.rows_computed
        assert_np_eq(cached._valid, [1, 1, 1, 1, 1, 0, 0, 0, 0, 0])

        # test that asking for existing stuff doen't mess anything up
        # or compute any new rows
        assert_np_eq(cached[0:5], base[0:5])
        assert_np_eq(cached._valid, [1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
        assert n_computed == cached.rows_computed

        # test that we can ask for things off the end
        assert_np_eq(cpy[8:16], base[8:16])
        assert_np_eq(cached[8:16], base[8:16])
        assert_np_eq(cached._valid, [1, 1, 1, 1, 1, 0, 0, 0, 1, 1])

        cached.populate()
        assert np.all(cached._valid)
        assert_np_eq(cached._data, base)

    def test_memmap_cache(self):
        self.battery(lambda obj: larray.cache_memmap(obj, 'name_foo'))

    def test_memory_cache(self):
        self.battery(larray.cache_memory)

########NEW FILE########
__FILENAME__ = test_synthetic
import numpy as np
from numpy.testing import assert_equal, assert_approx_equal, \
                          assert_array_almost_equal, assert_array_less

from skdata import synthetic as SG
from skdata import tasks

def test_madelon():
    madelon = SG.Madelon(n_samples=100, n_features=20, n_informative=5,
                               n_redundant=1, n_repeated=1, n_classes=3,
                               n_clusters_per_class=1, hypercube=False,
                               shift=None, scale=None, weights=[0.1, 0.25],
                               random_state=0)
    X, y = madelon.classification_task()
    tasks.assert_classification(X, y, 100)

    assert_equal(X.shape, (100, 20), "X shape mismatch")
    assert_equal(y.shape, (100,), "y shape mismatch")
    assert_equal(np.unique(y).shape, (3,), "Unexpected number of classes")
    assert_equal(sum(y == 0), 10, "Unexpected number of samples in class #0")
    assert_equal(sum(y == 1), 25, "Unexpected number of samples in class #1")
    assert_equal(sum(y == 2), 65, "Unexpected number of samples in class #2")


def test_four_regions():
    four_regions = SG.FourRegions(n_samples=100, random_state=0)
    X, y = four_regions.classification_task()
    tasks.assert_classification(X, y, 100)

    assert_equal(X.shape, (100, 2), "X shape mismatch")
    assert_equal(y.shape, (100,), "y shape mismatch")
    assert_equal(np.unique(y).shape, (4,), "Unexpected number of classes")
    assert_equal(sum(y == 0), 22, "Unexpected number of samples in class #0")
    assert_equal(sum(y == 1), 31, "Unexpected number of samples in class #1")
    assert_equal(sum(y == 2), 24, "Unexpected number of samples in class #2")
    assert_equal(sum(y == 3), 23, "Unexpected number of samples in class #3")


def test_randlin():
    randlin = SG.Randlin(n_samples=100, n_features=10, n_informative=3,
            effective_rank=5, coef=True, bias=0.0, noise=1.0, random_state=0)

    X, y = randlin.regression_task()
    tasks.assert_regression(X, y, 100)
    assert_equal(X.shape, (100, 10), "X shape mismatch")
    assert_equal(y.shape, (100, 1), "y shape mismatch")

    c = randlin.ground_truth
    assert_equal(c.shape, (10,), "coef shape mismatch")
    assert_equal(sum(c != 0.0), 3, "Unexpected number of informative features")

    # Test that y ~= np.dot(X, c) + bias + N(0, 1.0)
    assert_approx_equal(np.std(y[:,0] - np.dot(X, c)), 1.0, significant=2)


def test_blobs():
    blobs = SG.Blobs(n_samples=50, n_features=2,
            centers=[[0.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            random_state=0)
    X, y = blobs.classification_task()
    tasks.assert_classification(X, y)

    assert_equal(X.shape, (50, 2), "X shape mismatch")
    assert_equal(y.shape, (50,), "y shape mismatch")
    assert_equal(np.unique(y).shape, (3,), "Unexpected number of blobs")


def test_friedman1():
    X, y = SG.Friedman1(n_samples=5, n_features=10, noise=0.0,
                          random_state=0).regression_task()

    assert_equal(X.shape, (5, 10), "X shape mismatch")
    assert_equal(y.shape, (5, 1), "y shape mismatch")

    assert_array_almost_equal(y[:,0], 10 * np.sin(np.pi * X[:, 0] * X[:, 1])
                                 + 20 * (X[:, 2] - 0.5) ** 2 \
                                 + 10 * X[:, 3] + 5 * X[:, 4])


def test_friedman2():
    X, y = SG.Friedman2(n_samples=5, noise=0.0, random_state=0).regression_task()

    assert_equal(X.shape, (5, 4), "X shape mismatch")
    assert_equal(y.shape, (5, 1), "y shape mismatch")

    assert_array_almost_equal(y[:,0], (X[:, 0] ** 2
                                 + (X[:, 1] * X[:, 2]
                                    - 1 / (X[:, 1] * X[:, 3])) ** 2) ** 0.5)


def test_friedman3():
    X, y = SG.Friedman3(n_samples=5, noise=0.0, random_state=0).regression_task()

    assert_equal(X.shape, (5, 4), "X shape mismatch")
    assert_equal(y.shape, (5, 1), "y shape mismatch")

    assert_array_almost_equal(y[:,0], np.arctan((X[:, 1] * X[:, 2]
                                            - 1 / (X[:, 1] * X[:, 3]))
                                           / X[:, 0]))


def test_low_rank_matrix():
    lrm = SG.LowRankMatrix(n_samples=50, n_features=25, effective_rank=5,
                             tail_strength=0.01, random_state=0)
    X = lrm.latent_structure_task()
    tasks.assert_latent_structure(X)

    assert_equal(X.shape, (50, 25), "X shape mismatch")

    from numpy.linalg import svd
    u, s, v = svd(X)
    assert sum(s) - 5 < 0.1, "X rank is not approximately 5"

    X, Y = lrm.matrix_completion_task()
    tasks.assert_matrix_completion(X, Y)


def test_sparse_coded_signal():
    scs = SG.SparseCodedSignal(n_samples=5, n_components=8, n_features=10,
            n_nonzero_coefs=3, random_state=0)
    Y = scs.latent_structure_task()
    D = scs.D # XXX use scs.descr
    X = scs.X # XXX use scs.meta
    tasks.assert_latent_structure(Y)
    assert_equal(Y.shape, (10, 5), "Y shape mismatch")
    assert_equal(D.shape, (10, 8), "D shape mismatch")
    assert_equal(X.shape, (8, 5), "X shape mismatch")
    for col in X.T:
        assert_equal(len(np.flatnonzero(col)), 3, 'Non-zero coefs mismatch')
    assert_equal(np.dot(D, X), Y)
    assert_array_almost_equal(np.sqrt((D ** 2).sum(axis=0)),
                              np.ones(D.shape[1]))


def test_sparse_uncorrelated():
    X, y = SG.SparseUncorrelated(n_samples=5, n_features=10,
            random_state=0).regression_task()
    tasks.assert_regression(X, y)
    assert_equal(X.shape, (5, 10), "X shape mismatch")
    assert_equal(y.shape, (5, 1), "y shape mismatch")


def test_swiss_roll():
    X, t = SG.SwissRoll(n_samples=5, noise=0.0,
            random_state=0).regression_task()

    assert_equal(X.shape, (5, 3), "X shape mismatch")
    assert_equal(t.shape, (5, 1), "t shape mismatch")
    t = t[:, 0]
    assert_equal(X[:, 0], t * np.cos(t))
    assert_equal(X[:, 2], t * np.sin(t))


def test_make_s_curve():
    X, t = SG.S_Curve(n_samples=5, noise=0.0, random_state=0).regression_task()

    assert_equal(X.shape, (5, 3), "X shape mismatch")
    assert_equal(t.shape, (5, 1), "t shape mismatch")
    t = t[:, 0]
    assert_equal(X[:, 0], np.sin(t))
    assert_equal(X[:, 2], np.sign(t) * (np.cos(t) - 1))

########NEW FILE########
__FILENAME__ = test_tasks
import unittest
import numpy as np
from skdata import larochelle_etal_2007, tasks

def rnd(dtype, *shp):
    return np.random.rand(*shp).astype(dtype)

class TestAssertMethods(unittest.TestCase):
    def test_assert_classification(self):
        # things that work:
        tasks.assert_classification(
                rnd('float32', 4, 2), rnd('int8', 4))
        tasks.assert_classification(
                rnd('float64', 4, 2), rnd('uint64', 4))
        tasks.assert_classification(
                rnd('float64', 4, 2), rnd('uint64', 4), 4)

        # things that break:
        self.assertRaises(AssertionError, tasks.assert_classification,
                rnd('int8', 4, 2), rnd('int8', 4))        # X not float
        self.assertRaises(AssertionError, tasks.assert_classification,
                rnd('float32', 4, 2), rnd('float64', 4))  # y not int
        self.assertRaises(AssertionError, tasks.assert_classification,
                rnd('float32', 4, 2), rnd('int8', 5))     # y wrong len
        self.assertRaises(AssertionError, tasks.assert_classification,
                rnd('float32', 4, 2), rnd('int8', 4, 1))  # y wrong rank
        self.assertRaises(AssertionError, tasks.assert_classification,
                rnd('float32', 4, 2), rnd('int8', 4, 7))  # y wrong rank
        self.assertRaises(AssertionError, tasks.assert_classification,
                rnd('float32', 4, 2, 2), rnd('int8', 4))  # X wrong rank
        self.assertRaises(AssertionError, tasks.assert_classification,
                rnd('float64', 4), rnd('int8', 4))        # X wrong rank
        self.assertRaises(AssertionError, tasks.assert_classification,
                rnd('float64', 4, 3), rnd('int8', 4), 5)  # N mismatch

    # TODO: test_assert_classification_train_valid_test

    def test_assert_regression(self):
        # things that work:
        tasks.assert_regression(
                rnd('float32', 4, 2), rnd('float64', 4, 1))
        tasks.assert_regression(
                rnd('float64', 4, 2), rnd('float32', 4, 3))
        tasks.assert_regression(
                rnd('float64', 4, 2), rnd('float32', 4, 3), 4)

        # things that break:
        self.assertRaises(AssertionError, tasks.assert_regression,
                rnd('int8', 4, 2), rnd('float32', 4, 1))        # X not float
        self.assertRaises(AssertionError, tasks.assert_regression,
                rnd('float32', 4, 2), rnd('int32', 4, 1))       # y not float
        self.assertRaises(AssertionError, tasks.assert_regression,
                rnd('float32', 4, 2), rnd('float32', 5, 1))     # y wrong len
        self.assertRaises(AssertionError, tasks.assert_regression,
                rnd('float32', 4, 2), rnd('float32', 4))        # y wrong rank
        self.assertRaises(AssertionError, tasks.assert_regression,
                rnd('float32', 4, 2), rnd('float32', 4, 7, 3))  # y wrong rank
        self.assertRaises(AssertionError, tasks.assert_regression,
                rnd('float32', 4, 2, 2), rnd('float32', 4, 1))  # X wrong rank
        self.assertRaises(AssertionError, tasks.assert_regression,
                rnd('float64', 4), rnd('float32', 4, 1))        # X wrong rank
        self.assertRaises(AssertionError, tasks.assert_regression,
                rnd('float64', 4, 3), rnd('float32', 4, 1), 5)  # N mismatch


    # TODO: test_assert_matrix_completion

    def test_assert_latent_structure(self):
        # things that work:
        tasks.assert_latent_structure(rnd('float32', 4, 2))
        tasks.assert_latent_structure(rnd('float64', 11, 1))
        tasks.assert_latent_structure(rnd('float64', 11, 1), 11)

        # things that break:
        self.assertRaises(AssertionError, tasks.assert_latent_structure,
                rnd('int8', 4, 2))        # X not float
        self.assertRaises(AssertionError, tasks.assert_latent_structure,
                rnd('float32', 4, 2, 2))  # X wrong rank
        self.assertRaises(AssertionError, tasks.assert_latent_structure,
                rnd('float64', 4))        # X wrong rank
        self.assertRaises(AssertionError, tasks.assert_latent_structure,
                rnd('float64', 4, 3), 5)  # N mismatch

    def test_classification_train_valid_test(self):

        dataset = larochelle_etal_2007.Rectangles() # smallest one with splits
        assert not hasattr(dataset, 'classification_train_valid_test_task')

        train, valid, test = tasks.classification_train_valid_test(dataset)
        tasks.assert_classification(*train)
        tasks.assert_classification(*valid)
        tasks.assert_classification(*test)

        assert len(train[0]) == dataset.descr['n_train']
        assert len(valid[0]) == dataset.descr['n_valid']
        assert len(test[0]) == dataset.descr['n_test']

        tasks.assert_classification_train_valid_test(train, valid, test)

########NEW FILE########
__FILENAME__ = test_toy

from skdata import toy
from skdata.iris import Iris
from skdata.diabetes import Diabetes
from skdata.digits import Digits
# TODO: move these datasets into their own file too
from skdata.toy import Linnerud
from skdata.toy import Boston
from skdata.toy import SampleImages
from skdata.tasks import assert_classification, assert_regression

def check_classification_Xy(X, y, N=None):
    assert_classification(X, y, N)


def check_regression_XY(X, Y, N=None):
    assert_regression(X, Y, N)


def test_iris():
    iris = Iris()
    assert len(iris.meta) == 150
    assert iris.meta[0]['sepal_length'] == 5.1
    assert iris.meta[-1]['petal_width'] == 1.8
    assert iris.meta[-2]['name'] == 'virginica'

    X, y = iris.classification_task()
    check_classification_Xy(X, y, len(iris.meta))
    assert y.min() == 0
    assert y.max() == 2


def test_digits():
    digits = Digits()
    assert len(digits.meta) == 1797, len(digits.meta)
    assert digits.descr  #ensure it's been loaded
    assert digits.meta[3]['img'].shape == (8, 8)
    X, y = digits.classification_task()
    check_classification_Xy(X, y, len(digits.meta))
    assert y.min() == 0
    assert y.max() == 9


def test_diabetes():
    diabetes = Diabetes()
    assert len(diabetes.meta) == 442, len(diabetes.meta)
    X, y = diabetes.classification_task()
    check_classification_Xy(X, y, len(diabetes.meta))


def test_linnerud():
    linnerud = Linnerud()
    assert len(linnerud.meta) == 20
    assert list(sorted(linnerud.meta[5].keys())) == [
            'chins', 'jumps', 'pulse', 'situps', 'waist', 'weight']
    X, Y = linnerud.regression_task()
    check_regression_XY(X, Y, 20)


def test_boston():
    boston = Boston()
    assert len(boston.meta) == 506
    keys = ["CRIM","ZN","INDUS","CHAS","NOX","RM","AGE","DIS","RAD",
            "TAX","PTRATIO","B","LSTAT","MEDV"]
    assert set(keys) == set(boston.meta[6].keys())
    X, Y = boston.regression_task()
    check_regression_XY(X, Y, 506)


def test_sample_images():
    si = SampleImages()
    assert len(si.meta) == 2, len(si.meta)
    images = si.images()
    assert len(images) == 2
    assert images[0].shape == (427, 640, 3)
    assert images[1].shape == (427, 640, 3)

########NEW FILE########
__FILENAME__ = test_xml2x
from ..utils import get_my_path, xml2list, xml2dict
from os import path

MY_PATH = get_my_path()


def test_xml2list_voc07():
    gt = ['VOC2007',
          '000001.jpg',
          {'annotation': 'PASCAL VOC2007',
           'database': 'The VOC2007 Database',
           'flickrid': '341012865',
           'image': 'flickr'},
          {'flickrid': 'Fried Camels', 'name': 'Jinky the Fruit Bat'},
          {'depth': '3', 'height': '500', 'width': '353'},
          '0',
          {'bndbox': {'xmax': '195', 'xmin': '48', 'ymax': '371', 'ymin': '240'},
           'difficult': '0',
           'name': 'dog',
           'pose': 'Left',
           'truncated': '1'},
          {'bndbox': {'xmax': '352', 'xmin': '8', 'ymax': '498', 'ymin': '12'},
           'difficult': '0',
           'name': 'person',
           'pose': 'Left',
           'truncated': '1'}]
    xml_filename = path.join(MY_PATH, 'test.xml')
    gv = xml2list(xml_filename)
    assert gt == gv


def test_xml2dict_voc07():
    gt = {'filename': '000001.jpg',
          'folder': 'VOC2007',
          'object': [{'bndbox': {'xmax': '195',
                                 'xmin': '48',
                                 'ymax': '371',
                                 'ymin': '240'},
                      'difficult': '0',
                      'name': 'dog',
                      'pose': 'Left',
                      'truncated': '1'},
                     {'bndbox': {'xmax': '352',
                                 'xmin': '8',
                                 'ymax': '498',
                                 'ymin': '12'},
                      'difficult': '0',
                      'name': 'person',
                      'pose': 'Left',
                      'truncated': '1'}],
          'owner': {'flickrid': 'Fried Camels', 'name': 'Jinky the Fruit Bat'},
          'segmented': '0',
          'size': {'depth': '3', 'height': '500', 'width': '353'},
          'source': {'annotation': 'PASCAL VOC2007',
                     'database': 'The VOC2007 Database',
                     'flickrid': '341012865',
                     'image': 'flickr'}}
    xml_filename = path.join(MY_PATH, 'test.xml')
    gv = xml2dict(xml_filename)
    assert gt == gv

########NEW FILE########
__FILENAME__ = toy
"""
Several small non-synthetic datasets that do not require any downloading.

"""
import csv
import os

import numpy as np

import utils
import utils.image

class BuildOnInit(object):
    """Base class that calls build_meta and build_all
    """
    def __init__(self):
        try:
            self.meta, self.descr, self.meta_const
        except AttributeError:
            meta, descr, meta_const = self.build_all()
            self.meta = meta
            self.descr = descr
            self.meta_const = meta_const


    def memoize(self):
        # cause future __init__ not to build_meta()
        self.__class__.meta = self.meta
        self.__class__.descr = self.descr
        self.__class__.meta_const = self.meta_const

    def build_all(self):
        return self.build_meta(), self.build_descr(), self.build_meta_const()

    def build_descr(self):
        return {}

    def build_meta_const(self):
        return {}


class Linnerud(BuildOnInit):
    """Dataset of exercise and physiological measurements (regression).

    meta[i] is dict of
        weight: float
        waist: float
        pulse: float
        chins: float
        situps: float
        jumps: float
    """
    def build_all(self):
        base_dir = os.path.join(os.path.dirname(__file__), 'data/')
        data_exercise = np.loadtxt(base_dir + 'linnerud_exercise.csv', skiprows=1)
        data_physiological = np.loadtxt(base_dir + 'linnerud_physiological.csv',
                                        skiprows=1)
        #header_physiological == ['Weight', 'Waist', 'Pulse']
        #header_exercise == ['Chins', 'Situps', 'Jumps']
        assert data_exercise.shape == (20, 3)
        assert data_physiological.shape == (20, 3)
        meta = [dict(weight=p[0], waist=p[1], pulse=p[2],
                     chins=e[0], situps=e[1], jumps=e[2])
                for e, p in zip(data_exercise, data_physiological)]
        descr = open(os.path.dirname(__file__) + '/descr/linnerud.rst').read()
        return meta, dict(txt=descr), {}

    def regression_task(self):
        # Task as defined on pg 15 of
        #    Tenenhaus, M. (1998). La regression PLS: theorie et pratique.
        #    Paris: Editions Technic.
        X = [(m['weight'], m['waist'], m['pulse']) for m in self.meta]
        Y = [(m['chins'], m['situps'], m['jumps']) for m in self.meta]
        return np.asarray(X, dtype=np.float), np.asarray(Y, dtype=np.float)


class Boston(BuildOnInit):
    """Dataset of real estate features (regression)

    meta[i] is dict of
        CRIM: float
        ZN: float
        INDUS: float
        CHAS: float
        NOX: float
        RM: float
        AGE: float
        DIS: float
        RAD: float
        TAX: float
        PTRATIO: float
        B: float
        LSTAT: float
        MEDV: float

    descr is dict of
        txt: textual description of dataset
        X_features: list of keys for standard regression task
        Y_features: list of keys for standard regression task

    The standard regression task is to predict MEDV (median value?) from the
    other features.
    """
    def build_all(self):
        module_path = os.path.dirname(__file__)
        descr = open(os.path.join(
            module_path, 'descr', 'boston_house_prices.rst')).read()
        data_file = csv.reader(open(os.path.join(
            module_path, 'data', 'boston_house_prices.csv')))
        n_samples, n_features = [int(t) for t in data_file.next()[:2]]
        feature_names = data_file.next()
        meta = [dict(zip(feature_names, map(float, d))) for d in data_file]
        return (meta,
                dict(txt=descr,
                    X_features=feature_names[:-1],
                    Y_features=feature_names[-1:]),
                {})

    def regression_task(self):
        X_features = self.descr['X_features']
        Y_features = self.descr['Y_features']
        X = map(lambda m: [m[f] for f in X_features], self.meta)
        Y = map(lambda m: [m[f] for f in Y_features], self.meta)
        return np.asarray(X, np.float), np.asarray(Y, np.float)


class SampleImages(BuildOnInit):
    """Dataset of 2 sample jpg images (no specific task)

    meta[i] is dict of:
        filename: str (relative to self.imgdir)
    """
    def __init__(self):
        self.imgdir = os.path.join(os.path.dirname(__file__), "images")
        BuildOnInit.__init__(self)

    def fullpath(self, relpath):
        return os.path.join(self.imgdir, relpath)

    def build_all(self):
        descr = open(os.path.join(self.imgdir, 'README.txt')).read()
        meta = [dict(filename=filename)
                     for filename in os.listdir(self.imgdir)
                     if filename.endswith(".jpg")]
        return (meta,
                dict(txt=descr),
                {})

    def images(self):
        return map(
                utils.image.load_rgb_f32,
                map( lambda m: self.fullpath(m['filename']), self.meta))

########NEW FILE########
__FILENAME__ = archive
"""
Copyright (c) 2010 Gary Wilson Jr. <gary.wilson@gmail.com> and contributers.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

From:
http://pypi.python.org/pypi/python-archive/0.1
http://code.google.com/p/python-archive/

Changelog:
----------

* 2011/09/02: Cosmetic changes and add verbose kwarg to {Tar,Zip}Archive
classes by Nicolas Pinto <pinto@rowland.harvard.edu>

"""

import os
import tarfile
import zipfile


class ArchiveException(Exception):
    """Base exception class for all archive errors."""


class UnrecognizedArchiveFormat(ArchiveException):
    """Error raised when passed file is not a recognized archive format."""


def extract(archive_filename, output_dirname='./', verbose=True):
    """
    Unpack the tar or zip file at the specified `archive_filename` to the
    directory specified by `output_dirname`.
    """
    Archive(archive_filename).extract(output_dirname, verbose=verbose)


class Archive(object):
    """
    The external API class that encapsulates an archive implementation.
    """

    def __init__(self, file):
        self._archive = self._archive_cls(file)(file)

    @staticmethod
    def _archive_cls(file):
        cls = None
        if isinstance(file, basestring):
            filename = file
        else:
            try:
                filename = file.name
            except AttributeError:
                raise UnrecognizedArchiveFormat(
                    "File object not a recognized archive format.")
        base, tail_ext = os.path.splitext(filename.lower())
        cls = extension_map.get(tail_ext)
        if not cls:
            base, ext = os.path.splitext(base)
            cls = extension_map.get(ext)
        if not cls:
            raise UnrecognizedArchiveFormat(
                "Path not a recognized archive format: %s" % filename)
        return cls

    def extract(self, output_dirname='', verbose=True):
        self._archive.extract(output_dirname, verbose=verbose)

    def list(self):
        self._archive.list()


class BaseArchive(object):
    """
    Base Archive class.  Implementations should inherit this class.
    """

    def extract(self):
        raise NotImplementedError

    def list(self):
        raise NotImplementedError


class ExtractInterface(object):
    """
    Interface class exposing common extract functionalities for
    standard-library-based Archive classes (e.g. based on modules like tarfile,
    zipfile).
    """

    def extract(self, output_dirname, verbose=True):
        if not verbose:
            self._archive.extractall(output_dirname)
        else:
            members = self.get_members()
            n_members = len(members)
            for mi, member in enumerate(members):
                self._archive.extract(member, path=output_dirname)
                extracted = mi + 1
                status = (r"Progress: %20i files extracted [%4.1f%%]"
                          % (extracted, extracted * 100. / n_members))
                status += chr(8) * (len(status) + 1)
                print status,
            print


class TarArchive(ExtractInterface, BaseArchive):

    def __init__(self, filename):
        self._archive = tarfile.open(filename)

    def list(self, *args, **kwargs):
        self._archive.list(*args, **kwargs)

    def get_members(self):
        return self._archive.getmembers()


class ZipArchive(ExtractInterface, BaseArchive):

    def __init__(self, filename):
        self._archive = zipfile.ZipFile(filename)

    def list(self, *args, **kwargs):
        self._archive.printdir(*args, **kwargs)

    def get_members(self):
        return self._archive.namelist()


extension_map = {
    '.egg': ZipArchive,
    '.jar': ZipArchive,
    '.tar': TarArchive,
    '.tar.bz2': TarArchive,
    '.tar.gz': TarArchive,
    '.tgz': TarArchive,
    '.tz2': TarArchive,
    '.zip': ZipArchive,
}

########NEW FILE########
__FILENAME__ = dotdict
class dotdict(dict):
    def __getattr__(self, attr):
        if attr in self:
            return self.get(attr, None)
        else:
            raise KeyError
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

########NEW FILE########
__FILENAME__ = download_and_extract
"""Helpers to download and extract archives"""

# Authors: Nicolas Pinto <pinto@rowland.harvard.edu>
#          Nicolas Poilvert <poilvert@rowland.harvard.edu>
# License: BSD 3 clause

from urllib2 import urlopen
from os import path
import hashlib

import archive


def verify_sha1(filename, sha1):
    data = open(filename, 'rb').read()
    if sha1 != hashlib.sha1(data).hexdigest():
        raise IOError("File '%s': invalid SHA-1 hash! You may want to delete "
                      "this corrupted file..." % filename)

def verify_md5(filename, md5):
    data = open(filename, 'rb').read()
    if md5 != hashlib.md5(data).hexdigest():
        raise IOError("File '%s': invalid md5 hash! You may want to delete "
                      "this corrupted file..." % filename)


def download(url, output_filename, sha1=None, verbose=True, md5=None):
    """Downloads file at `url` and write it in `output_dirname`"""

    page = urlopen(url)
    page_info = page.info()

    output_file = open(output_filename, 'wb+')

    # size of the download unit
    block_size = 2 ** 15
    dl_size = 0

    if verbose:
        print "Downloading '%s' to '%s'" % (url, output_filename)
    # display  progress only if we know the length
    if 'content-length' in page_info and verbose:
        # file size in Kilobytes
        file_size = int(page_info['content-length']) / 1024.
        while True:
            buffer = page.read(block_size)
            if not buffer:
                break
            dl_size += block_size / 1024
            output_file.write(buffer)
            percent = min(100, 100. * dl_size / file_size)
            status = r"Progress: %20d kilobytes [%4.1f%%]" \
                    % (dl_size, percent)
            status = status + chr(8) * (len(status) + 1)
            print status,
        print ''
    else:
        output_file.write(page.read())

    output_file.close()

    if sha1 is not None:
        verify_sha1(output_filename, sha1)

    if md5 is not None:
        verify_md5(output_filename, md5)


def extract(archive_filename, output_dirname, sha1=None, verbose=True):
    """Extracts `archive_filename` in `output_dirname`.

    Supported archives:
    -------------------
    * Zip formats and equivalents: .zip, .egg, .jar
    * Tar and compressed tar formats: .tar, .tar.gz, .tgz, .tar.bz2, .tz2
    """
    if verbose:
        print "Extracting '%s' to '%s'" % (archive_filename, output_dirname)
    if sha1 is not None:
        if verbose:
            print " SHA-1 verification..."
        verify_sha1(archive_filename, sha1)
    archive.extract(archive_filename, output_dirname, verbose=verbose)


def download_and_extract(url, output_dirname, sha1=None, verbose=True):
    """Downloads and extracts archive in `url` into `output_dirname`.

    Note that `output_dirname` has to exist and won't be created by this
    function.
    """
    archive_basename = path.basename(url)
    archive_filename = path.join(output_dirname, archive_basename)
    download(url, archive_filename, sha1=sha1, verbose=verbose)
    extract(archive_filename, output_dirname, sha1=sha1, verbose=verbose)

########NEW FILE########
__FILENAME__ = glviewer
"""This file provides glumpy_viewer, a simple image-viewing mini-application.

The application is controlled via a state dictionary, whose keys are:

    'pos' - the current position in the image column we're viewing
    'window' - the glumpy window
    'I' - the glumpy.Image of the current column element
    'len' - the length of the image column

The application can be controlled by keys that have been registered with the
`command` decorator.  Some basic commands are set up by default:

    command('j') - advance the position
    command('k') - rewind the position
    command('0') - reset to position 0
    command('q') - quit

You can add new commands by importing the command decorator and using like this:

    >>> @command('r')
    >>> def action_on_press_r(state):
    >>>    ...          # modify state in place
    >>>    return None  # the return value is not used currently

The main point of commands right now is to update the current position
(state['pos']), in which case the window will be redrawn after the keypress
command returns to reflect the current position.

If you redefine a command, the new command clobbers the old one.

"""
import sys
import numpy as np
import glumpy


_commands = {}
def command(char):
    """
    Returns a decorator that registers its function for `char` keypress.
    """
    def deco(f):
        assert type(char) == str and len(char) == 1
        _commands[char] = f
        return f
    return deco


@command('j')
def inc_pos(state):
    state['pos'] = (state['pos'] + 1) % state['len']


@command('k')
def dec_pos(state):
    state['pos'] = (state['pos'] - 1) % state['len']


@command('0')
def reset_pos(state):
    state['pos'] = 0


@command('q')
def quit(state):
    sys.exit()


def glumpy_viewer(img_array,
        arrays_to_print = [],
        commands=None,
        cmap=None,
        window_shape=(512, 512),
        contrast_norm=None
        ):
    """
    Setup and start glumpy main loop to visualize Image array `img_array`.

    img_array - an array-like object whose elements are float32 or uint8
                ndarrays that glumpy can show.  larray objects work here.

    arrays_to_print - arrays whose elements will be printed to stdout
                      after a keypress changes the current position.

    """
    if contrast_norm not in (None, 'each', 'all'):
        raise ValueError('contrast_norm', contrast_norm)

    if contrast_norm == 'all':
        np.array(img_array, 'float32')
        img_array -= img_array.min()
        img_array /= max(img_array.max(), 1e-12)

    try:
        n_imgs = len(img_array)
    except TypeError:
        n_imgs = None

    state = dict(
            pos=0,
            fig=glumpy.figure((window_shape[1], window_shape[0])),
            I=glumpy.Image(img_array[0], colormap=cmap),
            len=n_imgs
            )

    fig = state['fig']
    if commands is None:
        commands = _commands

    @fig.event
    def on_draw():
        fig.clear()
        state['I'].draw(x=0, y=0, z=0,
                width=fig.width, height=fig.height)

    @fig.event
    def on_key_press(symbol, modifiers):
        if chr(symbol) not in commands:
            print 'unused key', chr(symbol), modifiers
            return

        pos = state['pos']
        commands[chr(symbol)](state)
        if pos == state['pos']:
            return
        else:
            img_i = img_array[state['pos']]
            if contrast_norm == 'each':
                # -- force copy
                img_i = np.array(img_i, 'float32')
                img_i -= img_i.min()
                img_i /= max(img_i.max(), 1e-12)

            #print img_i.shape
            #print img_i.dtype
            #print img_i.max()
            #print img_i.min()
            state['I'] = glumpy.Image(img_i,
                    colormap=cmap,
                    vmin=0.0,
                    vmax=1.0
                    )
            print state['pos'], [o[state['pos']] for o in arrays_to_print]
            fig.redraw()

    glumpy.show()


########NEW FILE########
__FILENAME__ = image
import numpy as np

import logging
logger = logging.getLogger(__name__)

try:
    from PIL import Image
    from scipy.misc import fromimage
except ImportError:
    logger.warn("The Python Imaging Library (PIL)"
            " is required to load data from jpeg files.")


def imread(name, flatten=0, mode=None):
    im = Image.open(name)
    if mode is not None and im.mode != mode:
        im = im.convert(mode)
    return fromimage(im, flatten=flatten)


class ImgLoader(object):
    def __init__(self, shape=None, ndim=None, dtype='uint8', mode=None):
        self._shape = shape
        if ndim is None:
            self._ndim = None if (shape is None) else len(shape)
        else:
            self._ndim = ndim
        self._dtype = dtype
        self.mode = mode

    def rval_getattr(self, attr, objs):
        if attr == 'shape' and self._shape is not None:
            return self._shape
        if attr == 'ndim' and self._ndim is not None:
            return self._ndim
        if attr == 'dtype':
            return self._dtype
        raise AttributeError(attr)

    def f_map(self, file_paths):
        if isinstance(file_paths, str):
            raise TypeError(file_paths)
        if self._shape:
            rval = np.empty((len(file_paths),) + self._shape, dtype='uint8')
        else:
            rval = [None] * len(file_paths)
        for ii, file_path in enumerate(file_paths):
            im_ii = imread(file_path, mode=self.mode)
            if len(im_ii.shape) not in (2, 3):
                raise IOError('Failed to decode %s' % file_path)
            img_ii = np.asarray(im_ii, dtype='uint8')
            assert len(img_ii.shape) in (2, 3)
            # -- broadcast pixels over channels if channels have been
            #    requested (_shape has len 3) and are not present
            #    (img_ii.ndim == 2)
            if img_ii.ndim == 2 and rval.ndim == 4:
                rval[ii] =  img_ii[:, :, np.newaxis]
            else:
                rval[ii] =  img_ii
        rval = rval.astype(self._dtype)
        if 'float' in str(self._dtype):
            rval /= 255.0
        return rval

    def __call__(self, file_path):
        return self.f_map([file_path])[0]


# XXX: these loaders currently do not coerce the loaded images
#      to be e.g. rgb or bw. Should they?
load_rgb_f32 = ImgLoader(ndim=3, dtype='float32')
load_rgb_u8 = ImgLoader(ndim=3, dtype='uint8')
load_bw_f32 = ImgLoader(ndim=2, dtype='float32')
load_bw_u8 = ImgLoader(ndim=2, dtype='uint8')


########NEW FILE########
__FILENAME__ = my_path
from os import path

__all__ = ['get_my_path',
           'get_my_path_basename',
          ]


def get_my_path(my_file=None):
    if my_file is None:
        import inspect
        caller = inspect.currentframe().f_back
        my_file = caller.f_globals['__file__']
    return path.dirname(path.abspath(my_file))


def get_my_path_basename(my_file=None):
    if my_file is None:
        import inspect
        caller = inspect.currentframe().f_back
        my_file = caller.f_globals['__file__']
    dirname = path.dirname(path.abspath(my_file))
    basename = path.basename(dirname)
    return basename

########NEW FILE########
__FILENAME__ = test_utils
import numpy as np
from numpy.testing import assert_equal, assert_array_almost_equal

from skdata import utils

def test_random_spd_matrix():
    X = utils.random_spd_matrix(n_dim=5, random_state=0)

    assert_equal(X.shape, (5, 5), "X shape mismatch")
    assert_array_almost_equal(X, X.T)

    from numpy.linalg import eig
    eigenvalues, _ = eig(X)
    assert_equal(eigenvalues > 0, np.array([True] * 5),
                 "X is not positive-definite")

########NEW FILE########
__FILENAME__ = xml2x
# WARNING: this module and its functions/objects are not bulletproof and they
# may fail to deliver the expected results in some situations, use at your own
# risk!


def xml2dict(xml_filename):
    tree = ElementTree.parse(xml_filename)
    root = tree.getroot()
    xml_dict = XmlDictConfig(root)
    return xml_dict


def xml2list(xml_filename):
    tree = ElementTree.parse(xml_filename)
    root = tree.getroot()
    xml_list = XmlListConfig(root)
    return xml_list

# -----------------------------------------------------------------------------
# Modified from http://code.activestate.com/recipes/410469-xml-as-dictionary
# -----------------------------------------------------------------------------
from xml.etree import ElementTree


class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if len(element):
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class XmlDictConfig(dict):
    '''
    Example usage:

    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:

    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)

    And then use xmldict for what it is... a dict.
    '''
    def __init__(self, parent_element):

        children_names = [child.tag for child in parent_element.getchildren()]

        if parent_element.items():
            self.update(dict(parent_element.items()))

        for element in parent_element:

            if len(element):

                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    child_dict = XmlDictConfig(element)

                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    child_dict = {element[0].tag: XmlListConfig(element)}

                # if the tag has attributes, add those to the dict
                if element.items():
                    child_dict.update(dict(element.items()))

                if children_names.count(element.tag) > 1:
                    if element.tag not in self:
                        # the first of its kind, an empty list must be created
                        self[element.tag] = [child_dict]
                    else:
                        self[element.tag] += [child_dict]
                else:
                    self.update({element.tag: child_dict})

            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})

            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                self.update({element.tag: element.text})

########NEW FILE########
__FILENAME__ = dataset
"""

NOTES ON THE VAN HATEREN IMAGE DATASET: 
http://bethgelab.org/datasets/vanhateren/
  * Only pixels within a two-pixel wide border around the image are guaranteed
    to be valid
  * Images seem to have a maximum value of 6282.0


Differences between *.imc and *.iml
-----------------------------------

(from http://bethgelab.org/datasets/vanhateren/)

The *.iml image set ('linear') are the raw images produced by the camera,
linearized with the lookup table generated by the camera for each image. The
images are slightly blurred by the point-spread function of the camera (in
particular due to the optics of the lens). For projects where a stricly linear
relationship between scene luminance and pixel values is important (e.g., when
looking at contrast variations over images) this may be the set of choice.

The *.imc image set ('calibrated') is computed from the *.iml set by
deconvolving the images with the point-spread function corresponding to the
used lens aperture (see the methods section of the article cited above). This
strongly reduces the blur at sharp edges and lines. The deconvolution
occasionally leads to overshoots and undershoots; the latter can produce
negative pixel values in a minority of images. For those images this was
compensated by adding a fixed offset to all pixel values of the image. These
offsets are listed below in the IMC offest list. Although they are generally
quite small, they slightly compromise the linearity of the relationship
between scene luminance and pixel value. Therefore this image set is best
suited for projects where well-defined edges are of more importance than
strict linearity.


Loading Patches
---------------

The van Hateren data set is typically used as a source of natural image
patches [citations needed, but see for example work on sparse coding and RBM
and autoencoder dictionary learning]

"""

# Copyright (C) 2012
# Authors: Eric Hunsberger, James Bergstra

# License: Simplified BSD

import hashlib
import os
import numpy as np

from skdata.data_home import get_data_home
from skdata.utils import download
from skdata.utils import random_patches


class Calibrated(object):
    """

    Attributes
    ----------

    self.meta - a list of dictionaries of the form
        {
        'basename': <something like 'imk04118.imc'>
        'md5': the desired md5 checksum for that file,
        'calibrated': True,
        'image_shape': (1024, 1536),
        'image_dtype': 'uint16'
        }

    """

    BASE_URL = 'http://pirsquared.org/research/vhatdb/imc/'

    imshape = (1024, 1536)

    def __init__(self, n_item_limit=None):
        self.name = self.__class__.__name__
        self.n_item_limit = n_item_limit

    def home(self, *suffix_paths):
        return os.path.join(get_data_home(), 'vanhateren', self.name,
                            *suffix_paths)

    @property
    def meta(self):
        if not hasattr(self, '_meta'):
            self.fetch(download_if_missing=True)
            self._meta = self._get_meta()
        return self._meta

    def _get_meta(self):
        meta = []
        for line in open(self.home('md5sums')):
            md5hash, basename = line.strip().split()
            basename = basename[1:]
            if 'HEADER' in basename:
                continue
            meta.append({'basename': basename,
                         'md5': md5hash,
                         'calibrated': True,
                         'image_shape': (1024, 1536),
                         'image_dtype': 'uint16',
                        })
        return meta

    def fetch(self, download_if_missing=True):
        if not download_if_missing:
            return
        if not os.path.exists(self.home()):
            os.makedirs(self.home())

        def checkmd5md5():
            md5sums = open(self.home('md5sums'), 'rb').read()
            md5md5 = hashlib.md5(md5sums).hexdigest()
            if md5md5 != 'da55092603cb2628e91e759aec79f654':
                print 'Re-downloading corrupt md5sums file'
                download(self.BASE_URL + 'md5sums', self.home('md5sums'))
        try:
            checkmd5md5()
        except IOError:
            download(self.BASE_URL + 'md5sums', self.home('md5sums'))
            checkmd5md5()

        meta = self._get_meta()
        for ii, item in enumerate(meta):
            if self.n_item_limit is None:
                required = True
            else:
                required = ii < self.n_item_limit
            try:
                data = open(self.home(item['basename']), 'rb').read()
                if hashlib.md5(data).hexdigest() != item['md5']:
                    # -- ignore 'required' flag for incorrect files
                    print 'Re-downloading incorrect file', item['basename']
                    download(self.BASE_URL + item['basename'],
                             self.home(item['basename']),
                             md5=item['md5'])
                    # TODO: catch ctrl-C, check md5,
                    # and remove partial download
            except IOError:
                if required:
                    download(self.BASE_URL + item['basename'],
                             self.home(item['basename']),
                             md5=item['md5'])

    def read_image(self, item):
        """Return one image from the Van Hateren image dataset

        Returns a (1024, 1536) in the original uint16 dtype
        """
        assert item['image_dtype'] == 'uint16'

        filename = os.path.join(self.home(item['basename']))
        s = open(filename, 'rb').read()
        assert hashlib.md5(s).hexdigest() == item['md5']
        img = np.fromstring(s, dtype=item['image_dtype']).byteswap()
        img = img.reshape(item['image_shape'])
        return img

    def raw_patches(self, rshape, rng=None, items=None):
        """Return random patches drawn randomly from natural images

        Parameters
        ----------
        rshape - tuple (N, rows, cols)
            The shape of the returned ndarray

        rng - np.RandomState
            RandomState

        items - None or items from self.meta
            A list of images from which to draw patches

        """
        if rng is None:
            rng = np.random
        if items is None:
            items = self.meta
        N, prows, pcols = rshape

        images = np.asarray(map(self.read_image, items))

        rval4 = random_patches(images[:, :, :, None], N, prows, pcols, rng)
        return rval4[:, :, :, 0]


########NEW FILE########
__FILENAME__ = main
"""
Commands related to the van Hateren data set:

    python main.py fetch - download the data set (ctrl-C midway if you don't
        need the whole thing)

    python main.py show - show images from the data set using glumpy. Use 'j'
        and 'k' to move between images. For dependencies, type
        
        pip install glumpy && pip install pyopengl

    python main.py show_patches - show image patches from the data set using
        glumpy.  Use 'j' and 'k' to move between images. For dependencies, type
        
        pip install glumpy && pip install pyopengl
    
"""

import sys
import numpy as np
import dataset

def fetch():
    vh = dataset.Calibrated()
    vh.fetch()

def show():
    from skdata.utils.glviewer import glumpy_viewer
    vh = dataset.Calibrated(10)
    items = vh.meta[:10]
    images = np.asarray(map(vh.read_image, items))

    images = images.astype('float32')
    images /= images.reshape(10, 1024 * 1536).max(axis=1)[:, None, None]
    images = 1.0 - images

    glumpy_viewer(
            img_array=images,
            arrays_to_print=[items],
            window_shape=vh.meta[0]['image_shape'])

def show_patches():
    N = 100
    S = 128
    from skdata.utils.glviewer import glumpy_viewer
    vh = dataset.Calibrated(10)
    patches = vh.raw_patches((N, S, S), items=vh.meta[:10])

    patches = patches.astype('float32')
    patches /= patches.reshape(N, S * S).max(axis=1)[:, None, None]
    patches = 1.0 - patches


    SS = S
    while SS < 256:
        SS *= 2

    glumpy_viewer(
            img_array=patches,
            arrays_to_print=[vh.meta],
            window_shape=(SS, SS))

if __name__ == '__main__':
    sys.exit(globals()[sys.argv[1]]())

########NEW FILE########
__FILENAME__ = view

# There are currently no experimental protocols defined for this data set.


########NEW FILE########
