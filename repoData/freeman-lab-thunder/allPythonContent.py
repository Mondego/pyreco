__FILENAME__ = timedTransfer
#!/usr/bin/env python

#
# test a streaming app by dumping files from one directory
# into another, at a specified rate
#
# <streaming_test> srcPath targetPath waitTime
#
# example:
# data/streaming_test.py /groups/ahrens/ahrenslab/Misha/forJeremy_SparkStreamingSample/ /nobackup/freeman/buffer/ 1
#

import sys, os, time, glob;

srcPath = str(sys.argv[1])
targetPath = str(sys.argv[2])
waitTime = float(sys.argv[3])
files = sorted(glob.glob(srcPath+"*"),key=os.path.getmtime)
count = 1
for f in files:
	cmd = "scp " + f + " " + targetPath 
	os.system(cmd)
	print('writing file ' +str(count))
	count = count + 1
	time.sleep(waitTime)


########NEW FILE########
__FILENAME__ = thunder-ec2
#!/usr/bin/env python

# Wrapper for the Spark EC2 launch script that additionally
# installs Thunder and its dependencies, and optionally
# loads an example data set

from boto import ec2
import sys
import os
import time
import random
import subprocess
from sys import stderr
from optparse import OptionParser
from spark_ec2 import ssh, launch_cluster, get_existing_cluster, wait_for_cluster, deploy_files, setup_spark_cluster, \
    get_spark_ami, ssh_command, ssh_read, ssh_write


def get_s3_keys():
    """ Get user S3 keys from environmental variables"""
    if os.getenv('S3_AWS_ACCESS_KEY_ID') is not None:
        s3_access_key = os.getenv("S3_AWS_ACCESS_KEY_ID")
    else:
        s3_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    if os.getenv('S3_AWS_SECRET_ACCESS_KEY') is not None:
        s3_secret_key = os.getenv("S3_AWS_SECRET_ACCESS_KEY")
    else:
        s3_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    return s3_access_key, s3_secret_key


def install_thunder(master, opts):
    """ Install Thunder and dependencies on a Spark EC2 cluster"""
    print "Installing Thunder on the cluster..."
    ssh(master, opts, "git clone https://github.com/freeman-lab/thunder.git")
    ssh(master, opts, "chmod u+x thunder/helper/ec2/setup.sh")
    ssh(master, opts, "thunder/helper/ec2/setup.sh")
    print "Done!"


def load_data(master, opts):
    """ Load an example data set into a Spark EC2 cluster"""
    print "Transferring example data to the cluster..."
    ssh(master, opts, "/root/ephemeral-hdfs/bin/stop-all.sh")
    ssh(master, opts, "/root/ephemeral-hdfs/bin/start-all.sh")
    time.sleep(10)
    (s3_access_key, s3_secret_key) = get_s3_keys()
    ssh(master, opts, "/root/ephemeral-hdfs/bin/hadoop distcp "
                              "s3n://" + s3_access_key + ":" + s3_secret_key +
                              "@thunder.datasets/test/iris.txt hdfs:///data")
    print "Done!"


def setup_cluster(conn, master_nodes, slave_nodes, opts, deploy_ssh_key):
    """Modified version of the setup_cluster function (borrowed from spark-ec.py)
    in order to manually set the folder with the deploy code"""
    master = master_nodes[0].public_dns_name
    if deploy_ssh_key:
        print "Generating cluster's SSH key on master..."
        key_setup = """
      [ -f ~/.ssh/id_rsa ] ||
        (ssh-keygen -q -t rsa -N '' -f ~/.ssh/id_rsa &&
         cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys)
        """
        ssh(master, opts, key_setup)
        dot_ssh_tar = ssh_read(master, opts, ['tar', 'c', '.ssh'])
        print "Transferring cluster's SSH key to slaves..."
        for slave in slave_nodes:
            print slave.public_dns_name
            ssh_write(slave.public_dns_name, opts, ['tar', 'x'], dot_ssh_tar)

    modules = ['spark', 'shark', 'ephemeral-hdfs', 'persistent-hdfs',
             'mapreduce', 'spark-standalone', 'tachyon']

    if opts.hadoop_major_version == "1":
        modules = filter(lambda x: x != "mapreduce", modules)

    if opts.ganglia:
        modules.append('ganglia')

    ssh(master, opts, "rm -rf spark-ec2 && git clone https://github.com/mesos/spark-ec2.git -b v2")

    print "Deploying files to master..."
    deploy_folder = os.path.join(os.environ['SPARK_HOME'], "ec2", "deploy.generic")
    deploy_files(conn, deploy_folder, opts, master_nodes, slave_nodes, modules)

    print "Running setup on master..."
    setup_spark_cluster(master, opts)
    print "Done!"


if __name__ == "__main__":
    parser = OptionParser(usage="thunder-ec2 [options] <action> <clustername>",  add_help_option=False)
    parser.add_option("-h", "--help", action="help", help="Show this help message and exit")
    parser.add_option("-k", "--key-pair", help="Key pair to use on instances")
    parser.add_option("-s", "--slaves", type="int", default=1, help="Number of slaves to launch (default: 1)")
    parser.add_option("-i", "--identity-file", help="SSH private key file to use for logging into instances")
    parser.add_option("-r", "--region", default="us-east-1", help="EC2 region zone to launch instances "
                                                                  "in (default: us-east-1)")
    parser.add_option("-t", "--instance-type", default="m1.large", help="Type of instance to launch (default: m1.large)."
                                                                        " WARNING: must be 64-bit; small instances "
                                                                        "won't work")
    parser.add_option("-u", "--user", default="root", help="User name for cluster (default: root)")
    parser.add_option("-z", "--zone", default="", help="Availability zone to launch instances in, or 'all' to spread "
                                                       "slaves across multiple (an additional $0.01/Gb for "
                                                       "bandwidth between zones applies)")
    parser.add_option("--resume", default=False, action="store_true", help="Resume installation on a previously "
                                                        "launched cluster (for debugging)")

    (opts, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_help()
        sys.exit(1)
    (action, cluster_name) = args

    # Launch a cluster, setting several options to defaults
    # (use spark-ec2.py included with Spark for more control)
    if action == "launch":
        try:
            conn = ec2.connect_to_region(opts.region)
        except Exception as e:
            print >> stderr, (e)
            sys.exit(1)

        if opts.zone == "":
            opts.zone = random.choice(conn.get_all_zones()).name

        opts.ami = get_spark_ami(opts)
        opts.ebs_vol_size = 0
        opts.spot_price = None
        opts.master_instance_type = ""
        opts.wait = 160
        opts.hadoop_major_version = "1"
        opts.ganglia = True
        opts.spark_version = "0.9.1"
        opts.swap = 1024
        opts.worker_instances = 1
        opts.master_opts = ""

        if opts.resume:
            (master_nodes, slave_nodes) = get_existing_cluster(conn, opts, cluster_name)
        else:
            (master_nodes, slave_nodes) = launch_cluster(conn, opts, cluster_name)

        wait_for_cluster(conn, opts.wait, master_nodes, slave_nodes)
        setup_cluster(conn, master_nodes, slave_nodes, opts, True)
        master = master_nodes[0].public_dns_name
        install_thunder(master, opts)

    if action != "launch":
        conn = ec2.connect_to_region(opts.region)
        (master_nodes, slave_nodes) = get_existing_cluster(conn, opts, cluster_name)
        master = master_nodes[0].public_dns_name

        # Login to the cluster
        if action == "login":
            print "Logging into master " + master + "..."
            proxy_opt = []
            subprocess.check_call(ssh_command(opts) + proxy_opt + ['-t', '-t', "%s@%s" % (opts.user, master)])

        # Install thunder on the cluster
        elif action == "install":
            install_thunder(master, opts)

        # Load example data into the cluster
        elif action == "loaddata":
            load_data(master, opts)

        # Destroy the cluster
        elif action == "destroy":
            response = raw_input("Are you sure you want to destroy the cluster " + cluster_name +
                                 "?\nALL DATA ON ALL NODES WILL BE LOST!!\n" +
                                 "Destroy cluster " + cluster_name + " (y/N): ")
            if response == "y":
                (master_nodes, slave_nodes) = get_existing_cluster(conn, opts, cluster_name, die_on_error=False)
            print "Terminating master..."
            for inst in master_nodes:
                inst.terminate()
            print "Terminating slaves..."
            for inst in slave_nodes:
                inst.terminate()



########NEW FILE########
__FILENAME__ = thunderdatatest
import abc
import os
from datetime import datetime
from numpy import arange, add, float16, random, outer, dot, zeros, real, transpose, diag, argsort, sqrt, inner
from scipy.linalg import sqrtm, inv, orth, eig
from scipy.io import savemat
from thunder.util.load import load
from thunder.sigprocessing.util import SigProcessingMethod
from thunder.regression.util import RegressionModel
from thunder.factorization.util import svd
from thunder.clustering.kmeans import kmeans


class ThunderDataTest(object):

    def __init__(self, sc):
        self.sc = sc

    @abc.abstractmethod
    def runtest(self, **args):
        return

    @staticmethod
    def initialize(testname, sc):
        return TESTS[testname](sc)

    def createinputdata(self, numrecords, numdims, numpartitions):
        rdd = self.sc.parallelize(arange(0, numrecords), numpartitions)
        self.rdd = rdd

    def loadinputdata(self, datafile, savefile=None):
        rdd = load(self.sc, datafile, preprocessmethod="dff-percentile")
        self.rdd = rdd
        self.datafile = datafile
        if savefile is not None:
            self.savefile = savefile
        self.modelfile = os.path.join(os.path.split(self.datafile)[0], 'stim')

    def run(self, numtrials, persistencetype):

        if persistencetype == "memory":
            self.rdd.cache()
            self.rdd.count()

        def timedtest(func):
            start = datetime.now()
            func()
            end = datetime.now()
            dt = end - start
            time = (dt.microseconds + (dt.seconds + dt.days * 24.0 * 3600.0) * 10.0**6.0) / 10.0**6.0
            return time

        results = map(lambda i: timedtest(self.runtest), range(0, numtrials))

        return results


class Stats(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)
        self.method = SigProcessingMethod.load("stats", statistic="std")

    def runtest(self):
        vals = self.method.calc(self.rdd)
        vals.count()


class Average(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)

    def runtest(self):
        vec = self.rdd.map(lambda (_, v): v).mean()


class Regress(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)

    def runtest(self):
        model = RegressionModel.load(os.path.join(self.modelfile, "linear"), "linear")
        betas, stats, resid = model.fit(self.rdd)
        stats.count()


class RegressWithSave(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)

    def runtest(self):
        model = RegressionModel.load(os.path.join(self.modelfile, "linear"), "linear")
        betas, stats, resid = model.fit(self.rdd)
        result = stats.map(lambda (_, v): float16(v)).collect()
        savemat(self.savefile + "tmp.mat", mdict={"tmp": result}, oned_as='column')


class CrossCorr(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)

    def runtest(self):
        method = SigProcessingMethod.load("crosscorr", sigfile=os.path.join(self.modelfile, "crosscorr"), lag=0)
        betas = method.calc(self.rdd)
        betas.count()


class Fourier(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)
        self.method = SigProcessingMethod.load("fourier", freq=5)

    def runtest(self):
        vals = self.method.calc(self.rdd)
        vals.count()


class Load(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)

    def runtest(self):
        self.rdd.count()


class Save(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)

    def runtest(self):
        result = self.rdd.map(lambda (_, v): float16(v[0])).collect()
        savemat(self.savefile + "tmp.mat", mdict={"tmp": result}, oned_as='column')


class KMeans(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)

    def runtest(self):
        labels, centers = kmeans(self.rdd, 3, maxiter=5, tol=0)


class ICA(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)

    def runtest(self):
        k = len(self.rdd.first()[1])
        c = 3
        n = 1000
        B = orth(random.randn(k, c))
        Bold = zeros((k, c))
        iterNum = 0
        errVec = zeros(20)
        while (iterNum < 5):
            iterNum += 1
            B = self.rdd.map(lambda (_, v): v).map(lambda x: outer(x, dot(x, B) ** 3)).reduce(lambda x, y: x + y) / n - 3 * B
            B = dot(B, real(sqrtm(inv(dot(transpose(B), B)))))
            minAbsCos = min(abs(diag(dot(transpose(B), Bold))))
            Bold = B
            errVec[iterNum-1] = (1 - minAbsCos)

        sigs = self.rdd.mapValues(lambda x: dot(B, x))


class PCADirect(ThunderDataTest):
 
    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)
 
    def runtest(self):
        scores, latent, comps = svd(self.rdd, 3, meansubtract=0, method="direct")
 

class PCAIterative(ThunderDataTest):

    def __init__(self, sc):
        ThunderDataTest.__init__(self, sc)

    def runtest(self):
        m = len(self.rdd.first()[1])
        k = 3
        n = 1000

        def outerprod(x):
            return outer(x, x)

        c = random.rand(k, m)
        iter = 0
        error = 100

        while (iter < 5):
            c_old = c
            c_inv = dot(transpose(c), inv(dot(c, transpose(c))))
            premult1 = self.rdd.context.broadcast(c_inv)
            xx = self.rdd.map(lambda (_, v): v).map(lambda x: outerprod(dot(x, premult1.value))).sum()
            xx_inv = inv(xx)
            premult2 = self.rdd.context.broadcast(dot(c_inv, xx_inv))
            c = self.rdd.map(lambda (_, v): v).map(lambda x: outer(x, dot(x, premult2.value))).sum()
            c = transpose(c)
            error = sum(sum((c - c_old) ** 2))
            iter += 1


TESTS = {
    'stats': Stats,
    'average': Average,
    'regress': Regress,
    'regresswithsave': RegressWithSave,
    'crosscorr': CrossCorr,
    'fourier': Fourier,
    'load': Load,
    'save': Save,
    'ica': ICA,
    'pca-direct': PCADirect,
    'pca-iterative': PCAIterative,
    'kmeans': KMeans
}

########NEW FILE########
__FILENAME__ = thundertestrunner
import argparse
import os
import glob

from pyspark import SparkContext

from thunderdatatest import ThunderDataTest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="run mllib performance tests")
    parser.add_argument("master", type=str)
    parser.add_argument("numtrials", type=int)
    parser.add_argument("datatype", type=str, choices=("create", "datafile"))
    parser.add_argument("persistencetype", type=str, choices=("memory", "disk", "none"))
    parser.add_argument("testname", type=str)
    parser.add_argument("--numrecords", type=int, required=False)
    parser.add_argument("--numdims", type=int, required=False)
    parser.add_argument("--numpartitions", type=int, required=False)
    parser.add_argument("--numiterations", type=int, required=False)
    parser.add_argument("--savefile", type=str, default=None, required=False)
    parser.add_argument("--datafile", type=str, default=None, required=False)

    args = parser.parse_args()

    if args.datatype == "datafile":
        if args.datafile is None:
            raise ValueError("must specify a datafile location if datatype is datafile, use '--datafile myfile' ")

    if "save" in args.testname:
        if args.savefile is None:
            raise ValueError("must specify a savefile location if test includes saving, use '--savefile myfile' ")

    sc = SparkContext(args.master, "ThunderTestRunner: " + args.testname)

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    test = ThunderDataTest.initialize(args.testname, sc)

    if args.datatype == "datafile":
        test.loadinputdata(args.datafile, args.savefile)
    elif args.datatype == "create":
        test.createinputdata(args.testname, args.numrecords, args.numdims, args.numpartitions)

    results = test.run(args.numtrials, args.persistencetype)

    print("results: " + str(results))
    print("minimum: " + str(min(results)))


########NEW FILE########
__FILENAME__ = thunder-startup
#!/usr/bin/env python

import glob
import os
egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
sc.addPyFile(egg[0])

from thunder.util.load import load, getdims
from thunder.util.save import save

from thunder.clustering.kmeans import kmeans, closestpoint

from thunder.regression.regress import regress
from thunder.regression.util import RegressionModel, TuningModel

from thunder.factorization.pca import pca
from thunder.factorization.ica import ica
from thunder.factorization.util import svd

from thunder.sigprocessing.stats import stats
from thunder.sigprocessing.localcorr import localcorr
from thunder.sigprocessing.query import query
from thunder.sigprocessing.util import FourierMethod, StatsMethod, QueryMethod, CrossCorrMethod

########NEW FILE########
__FILENAME__ = matdiff
#!/usr/bin/env python
"""
Simple diff of Matlab .mat files.  These files can contain modification
timestamps in their headers, so regular `diff` won't work.

Arrays are compared using numpy.allclose after converting NaN values
using numpy.nan_to_num().

Can compare two directories with .mat files that have the same filenames,
or two .mat files.  This is useful for verifying that code modifications
didn't change the computations' results.
"""
import numpy as np
import os
import sys
from scipy.io import loadmat


def mat_files_equal(a_filename, b_filename):
    a = loadmat(a_filename)
    b = loadmat(b_filename)
    if a.keys() != b.keys():
        print "Files have different keys"
        return False
    else:
        for key in a.keys():
            if key == "__header__":
                # Headers are allowed to differ, since they could have
                # different creation timestamps.
                continue
            elif isinstance(a[key], np.ndarray):
                # nan is unequal to anything, so let's replace it:
                if not np.allclose(np.nan_to_num(a[key]),
                                   np.nan_to_num(b[key])):
                    print "Unequal arrays for key '%s'" % key
                    return False
            elif a[key] != b[key]:
                print "Unequal scalars for key '%s'" % key
                return False
        return True


def assert_mat_files_equal(a, b):
    if not mat_files_equal(a, b):
        print "Files %s and %s are different" % (a, b)
        exit(-1)


if __name__ == "__main__":
    a = sys.argv[1]
    b = sys.argv[2]
    if os.path.isdir(a) and os.path.isdir(b):
        for filename in os.listdir(a):
            assert_mat_files_equal(os.path.join(a, filename),
                                   os.path.join(b, filename))
    elif os.path.isfile(a) and os.path.isfile(b):
        assert_mat_files_equal(a, b)
    else:
        print "Must compare two files or two directories"
        sys.exit(-1)

########NEW FILE########
__FILENAME__ = test_classification
import shutil
import tempfile
from numpy import array, vstack
from numpy.testing import assert_array_almost_equal
from scipy.stats import ttest_ind
from thunder.classification.util import MassUnivariateClassifier
from test_utils import PySparkTestCase


class ClassificationTestCase(PySparkTestCase):
    def setUp(self):
        super(ClassificationTestCase, self).setUp()
        self.outputdir = tempfile.mkdtemp()

    def tearDown(self):
        super(ClassificationTestCase, self).tearDown()
        shutil.rmtree(self.outputdir)


class TestMassUnivariateClassification(ClassificationTestCase):
    """Test accuracy of mass univariate classification on small
    test data sets with either 1 or 2 features
    """

    def test_mass_univariate_classification_ttest_1d(self):
        """Simple classification problem, 1d features"""
        X = array([-1, -0.1, -0.1, 1, 1, 1.1])
        labels = array([1, 1, 1, 2, 2, 2])
        params = dict([('labels', labels)])

        clf = MassUnivariateClassifier.load(params, "ttest")

        # should match direct calculation using scipy
        data = self.sc.parallelize(zip([1], [X]))
        result = clf.classify(data).map(lambda (_, v): v).collect()
        ground_truth = ttest_ind(X[labels == 1], X[labels == 2])
        assert_array_almost_equal(result[0], ground_truth[0])

    def test_mass_univariate_classification_ttest_2d(self):
        """Simple classification problem, 2d features"""
        X = array([-1, -2, -0.1, -2, -0.1, -2.1, 1, 1.1, 1, 1, 1.1, 2])
        features = array([1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2])
        samples = array([1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6])
        labels = array([1, 1, 1, 2, 2, 2])
        params = dict([('labels', labels), ('features', features), ('samples', samples)])

        clf = MassUnivariateClassifier.load(params, "ttest")

        # should match direct calculation using scipy

        # test first feature only
        data = self.sc.parallelize(zip([1], [X]))
        result = clf.classify(data, [[1]]).map(lambda (_, v): v).collect()
        ground_truth = ttest_ind(X[features == 1][:3], X[features == 1][3:])
        assert_array_almost_equal(result[0], ground_truth[0])

        # test both features
        result = clf.classify(data, [[1, 2]]).map(lambda (_, v): v).collect()
        ground_truth = ttest_ind(vstack((X[features == 1][:3], X[features == 2][:3])).T,
                                 vstack((X[features == 1][3:], X[features == 2][3:])).T)
        assert_array_almost_equal(result[0][0], ground_truth[0])

    def test_mass_univariate_classification_gnb_1d(self):
        """Simple classification problem, 1d features"""
        X1 = array([-1, -1, -1.2, 1, 1, 1.2])
        X2 = array([-1, -1, 1.2, 1, 1, 1.2])
        labels = array([1, 1, 1, 2, 2, 2])
        params = dict([('labels', labels)])

        clf = MassUnivariateClassifier.load(params, "gaussnaivebayes", cv=0)

        # should predict perfectly
        data = self.sc.parallelize(zip([1], [X1]))
        result = clf.classify(data).map(lambda (_, v): v).collect()
        assert_array_almost_equal(result[0], [1.0])

        # should predict all but one correctly
        data = self.sc.parallelize(zip([1], [X2]))
        result = clf.classify(data).map(lambda (_, v): v).collect()
        assert_array_almost_equal(result[0], [5.0/6.0])

    def test_mass_univariate_classification_gnb_2d(self):
        """Simple classification problem, 2d features"""

        X = array([-1, 1, -2, -1, -3, -2, 1, 1, 2, 1, 3, 2])
        features = array([1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2])
        samples = array([1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6])
        labels = array([1, 1, 1, 2, 2, 2])
        params = dict([('labels', labels), ('features', features), ('samples', samples)])
        clf = MassUnivariateClassifier.load(params, "gaussnaivebayes", cv=0)

        data = self.sc.parallelize(zip([1], [X]))

        # first feature predicts perfectly
        result = clf.classify(data, [[1]]).map(lambda (_, v): v).collect()
        assert_array_almost_equal(result[0], [1.0])

        # second feature gets one wrong
        result = clf.classify(data, [[2]]).map(lambda (_, v): v).collect()
        assert_array_almost_equal(result[0], [5.0/6.0])

        # two features together predict perfectly
        result = clf.classify(data, [[1, 2]]).map(lambda (_, v): v).collect()
        assert_array_almost_equal(result[0], [1.0])

        # test iteration over multiple feature sets
        result = clf.classify(data, [[1, 2], [2]]).map(lambda (_, v): v).collect()
        assert_array_almost_equal(result[0], [1.0, 5.0/6.0])




########NEW FILE########
__FILENAME__ = test_clustering
import shutil
import tempfile
from numpy import array, array_equal
from thunder.clustering.kmeans import kmeans
from test_utils import PySparkTestCase


class ClusteringTestCase(PySparkTestCase):
    def setUp(self):
        super(ClusteringTestCase, self).setUp()
        self.outputdir = tempfile.mkdtemp()

    def tearDown(self):
        super(ClusteringTestCase, self).tearDown()
        shutil.rmtree(self.outputdir)


class TestKMeans(ClusteringTestCase):
    def test_kmeans(self):
        """ With k=1 always get one cluster centered on the mean"""

        data_local = [
            array([1.0, 2.0, 6.0]),
            array([1.0, 3.0, 0.0]),
            array([1.0, 4.0, 6.0])]

        data = self.sc.parallelize(zip(range(1, 4), data_local))

        labels, centers = kmeans(data, k=1, maxiter=20, tol=0.001)
        assert array_equal(centers[0], array([1.0, 3.0, 4.0]))
        assert array_equal(labels.map(lambda (_, v): v).collect(), array([0, 0, 0]))




########NEW FILE########
__FILENAME__ = test_factorization
import os
import shutil
import tempfile
from numpy import array, allclose, transpose
import scipy.linalg as LinAlg
from scipy.io import loadmat
from thunder.factorization.ica import ica
from thunder.factorization.util import svd
from thunder.util.load import load
from test_utils import PySparkTestCase

# Hack to find the data files:
DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")


class FactorizationTestCase(PySparkTestCase):
    def setUp(self):
        super(FactorizationTestCase, self).setUp()
        self.outputdir = tempfile.mkdtemp()

    def tearDown(self):
        super(FactorizationTestCase, self).tearDown()
        shutil.rmtree(self.outputdir)


class TestSVD(FactorizationTestCase):
    """Test accuracy of direct and em methods
    for SVD against scipy.linalg method,

    Only uses k=1 otherwise results of iterative approaches can
    vary up to an orthogonal transform

    Checks if answers match up to a sign flip
    """
    def test_svd_direct(self):
        data_local = [
            array([1.0, 2.0, 6.0]),
            array([1.0, 3.0, 0.0]),
            array([1.0, 4.0, 6.0]),
            array([5.0, 1.0, 4.0])
        ]
        data = self.sc.parallelize(zip(range(1, 5), data_local))

        u, s, v = svd(data, 1, meansubtract=0, method="direct")
        u_true, s_true, v_true = LinAlg.svd(array(data_local))
        u_test = transpose(array(u.map(lambda (_, v): v).collect()))[0]
        v_test = v[0]
        assert(allclose(s[0], s_true[0]))
        assert(allclose(v_test, v_true[0, :]) | allclose(-v_test, v_true[0, :]))
        assert(allclose(u_test, u_true[:, 0]) | allclose(-u_test, u_true[:, 0]))

    def test_svd_em(self):
        data_local = [
            array([1.0, 2.0, 6.0]),
            array([1.0, 3.0, 0.0]),
            array([1.0, 4.0, 6.0]),
            array([5.0, 1.0, 4.0])
        ]
        data = self.sc.parallelize(zip(range(1, 5), data_local))

        u, s, v = svd(data, 1, meansubtract=0, method="em")
        u_true, s_true, v_true = LinAlg.svd(array(data_local))
        u_test = transpose(array(u.map(lambda (_, v): v).collect()))[0]
        v_test = v[0]
        tol = 10e-04  # allow small error for iterative method
        assert(allclose(s[0], s_true[0], atol=tol))
        assert(allclose(v_test, v_true[0, :], atol=tol) | allclose(-v_test, v_true[0, :], atol=tol))
        assert(allclose(u_test, u_true[:, 0], atol=tol) | allclose(-u_test, u_true[:, 0], atol=tol))


class TestICA(FactorizationTestCase):
    """Test that ICA returns correct
    results by comparing to known, vetted
    results for the example data set
    and a fixed random seed
    """
    def test_ica(self):
        ica_data = os.path.join(DATA_DIR, "ica.txt")
        ica_results = os.path.join(DATA_DIR, "results/ica")
        data = load(self.sc, ica_data, "raw")
        w, sigs = ica(data, 4, 4, svdmethod="direct", seed=1)
        w_true = loadmat(os.path.join(ica_results, "w.mat"))["w"]
        sigs_true = loadmat(os.path.join(ica_results, "sigs.mat"))["sigs"]
        tol = 10e-02
        assert(allclose(w, w_true, atol=tol))
        assert(allclose(transpose(sigs.map(lambda (_, v): v).collect()), sigs_true, atol=tol))


########NEW FILE########
__FILENAME__ = test_load
import shutil
import tempfile
from numpy import array, allclose
from thunder.util.load import subtoind, indtosub, getdims
from test_utils import PySparkTestCase


class LoadTestCase(PySparkTestCase):
    def setUp(self):
        super(LoadTestCase, self).setUp()
        self.outputdir = tempfile.mkdtemp()

    def tearDown(self):
        super(LoadTestCase, self).tearDown()
        shutil.rmtree(self.outputdir)


class TestSubToInd(LoadTestCase):
    """Test conversion between linear and subscript indexing"""

    def test_sub_to_ind_rdd(self):
        subs = [(1, 1, 1), (2, 1, 1), (1, 2, 1), (2, 2, 1), (1, 3, 1), (2, 3, 1),
                (1, 1, 2), (2, 1, 2), (1, 2, 2), (2, 2, 2), (1, 3, 2), (2, 3, 2)]
        data_local = map(lambda x: (x, array([1.0])), subs)

        data = self.sc.parallelize(data_local)
        dims = [2, 3, 2]
        inds = subtoind(data, dims).map(lambda (k, _): k).collect()
        assert(allclose(inds, array(range(1, 13))))

    def test_ind_to_sub_rdd(self):
        data_local = map(lambda x: (x, array([1.0])), range(1, 13))

        data = self.sc.parallelize(data_local)
        dims = [2, 3, 2]
        subs = indtosub(data, dims).map(lambda (k, _): k).collect()
        assert(allclose(subs, array([(1, 1, 1), (2, 1, 1), (1, 2, 1), (2, 2, 1), (1, 3, 1), (2, 3, 1),
                                     (1, 1, 2), (2, 1, 2), (1, 2, 2), (2, 2, 2), (1, 3, 2), (2, 3, 2)])))

    def test_sub_to_ind_array(self):
        subs = [(1, 1, 1), (2, 1, 1), (1, 2, 1), (2, 2, 1), (1, 3, 1), (2, 3, 1),
                (1, 1, 2), (2, 1, 2), (1, 2, 2), (2, 2, 2), (1, 3, 2), (2, 3, 2)]
        data_local = map(lambda x: (x, array([1.0])), subs)
        dims = [2, 3, 2]
        inds = map(lambda x: x[0], subtoind(data_local, dims))
        assert(allclose(inds, array(range(1, 13))))

    def test_ind_to_sub_array(self):
        data_local = map(lambda x: (x, array([1.0])), range(1, 13))
        dims = [2, 3, 2]
        subs = map(lambda x: x[0], indtosub(data_local, dims))
        assert(allclose(subs, array([(1, 1, 1), (2, 1, 1), (1, 2, 1), (2, 2, 1), (1, 3, 1), (2, 3, 1),
                                     (1, 1, 2), (2, 1, 2), (1, 2, 2), (2, 2, 2), (1, 3, 2), (2, 3, 2)])))


class TestGetDims(LoadTestCase):
    """Test getting dimensions"""

    def test_get_dims_rdd(self):
        subs = [(1, 1, 1), (2, 1, 1), (1, 2, 1), (2, 2, 1), (1, 3, 1), (2, 3, 1),
                (1, 1, 2), (2, 1, 2), (1, 2, 2), (2, 2, 2), (1, 3, 2), (2, 3, 2)]
        data_local = map(lambda x: (x, array([1.0])), subs)
        data = self.sc.parallelize(data_local)
        dims = getdims(data)
        assert(allclose(dims.max, (2, 3, 2)))
        assert(allclose(dims.count(), (2, 3, 2)))
        assert(allclose(dims.min, (1, 1, 1)))

    def test_get_dims_array(self):
        subs = [(1, 1, 1), (2, 1, 1), (1, 2, 1), (2, 2, 1), (1, 3, 1), (2, 3, 1),
                (1, 1, 2), (2, 1, 2), (1, 2, 2), (2, 2, 2), (1, 3, 2), (2, 3, 2)]
        data_local = map(lambda x: (x, array([1.0])), subs)
        dims = getdims(data_local)
        assert(allclose(dims.max, (2, 3, 2)))
        assert(allclose(dims.count(), (2, 3, 2)))
        assert(allclose(dims.min, (1, 1, 1)))

########NEW FILE########
__FILENAME__ = test_matrixrdd
import shutil
import tempfile
from numpy import array, array_equal, add
from thunder.util.matrixrdd import MatrixRDD
from test_utils import PySparkTestCase


class MatrixRDDTestCase(PySparkTestCase):
    def setUp(self):
        super(MatrixRDDTestCase, self).setUp()
        self.outputDir = tempfile.mkdtemp()

    def tearDown(self):
        super(MatrixRDDTestCase, self).tearDown()
        shutil.rmtree(self.outputDir)


class TestElementWise(MatrixRDDTestCase):

    def test_elementwise_rdd(self):
        mat1 = MatrixRDD(self.sc.parallelize([(1, array([1, 2, 3])), (2, array([4, 5, 6]))]))
        mat2 = MatrixRDD(self.sc.parallelize([(1, array([7, 8, 9])), (2, array([10, 11, 12]))]))
        result = mat1.elementwise(mat2, add).collect()
        truth = array([[8, 10, 12], [14, 16, 18]])
        assert array_equal(result, truth)

    def test_elementwise_array(self):
        mat = MatrixRDD(self.sc.parallelize([(1, array([1, 2, 3]))]))
        assert array_equal(mat.elementwise(2, add).collect()[0], array([3, 4, 5]))


class TestTimes(MatrixRDDTestCase):

    def test_times_rdd(self):
        mat1 = MatrixRDD(self.sc.parallelize([(1, array([1, 2, 3])), (2, array([4, 5, 6]))]))
        mat2 = MatrixRDD(self.sc.parallelize([(1, array([7, 8, 9])), (2, array([10, 11, 12]))]))
        truth = array([[47, 52, 57], [64, 71, 78], [81, 90, 99]])
        resultA = mat1.times(mat2)
        resultB = mat1.times(mat2, "accum")
        assert array_equal(resultA, truth)
        assert array_equal(resultB, truth)

    def test_times_array(self):
        mat1 = MatrixRDD(self.sc.parallelize([(1, array([1, 2, 3])), (2, array([4, 5, 6]))]))
        mat2 = array([[7, 8], [9, 10], [11, 12]])
        truth = [array([58, 64]), array([139, 154])]
        result = mat1.times(mat2).collect()
        assert array_equal(result, truth)


class TestOuter(MatrixRDDTestCase):

    def test_outer(self):
        mat1 = MatrixRDD(self.sc.parallelize([(1, array([1, 2, 3])), (2, array([4, 5, 6]))]))
        resultA = mat1.outer()
        resultB = mat1.outer("accum")
        truth = array([[17, 22, 27], [22, 29, 36], [27, 36, 45]])
        assert array_equal(resultA, truth)
        assert array_equal(resultB, truth)

# TODO: TestCenter, TestZScore
########NEW FILE########
__FILENAME__ = test_regression
import shutil
import tempfile
from numpy import array, allclose, pi
from thunder.regression.util import RegressionModel, TuningModel
from thunder.regression.regress import regress
from thunder.regression.regresswithpca import regresswithpca
from thunder.regression.tuning import tuning
from test_utils import PySparkTestCase


class RegressionTestCase(PySparkTestCase):
    def setUp(self):
        super(RegressionTestCase, self).setUp()
        self.outputdir = tempfile.mkdtemp()

    def tearDown(self):
        super(RegressionTestCase, self).tearDown()
        shutil.rmtree(self.outputdir)


class TestRegress(RegressionTestCase):
    """Test accuracy of linear and bilinear regression
    models by building small design matrices and testing
    on small data against ground truth
    (ground truth derived by doing the algebra in MATLAB)

    Also tests that main analysis scripts run without crashing
    """
    def test_linear_regress(self):
        data = self.sc.parallelize([(1, array([1.5, 2.3, 6.2, 5.1, 3.4, 2.1]))])
        x = array([
            array([1, 0, 0, 0, 0, 0]),
            array([0, 1, 0, 0, 0, 0])
        ])
        model = RegressionModel.load(x, "linear")
        betas, stats, resid = model.fit(data)
        assert(allclose(betas.map(lambda (_, v): v).collect()[0], array([-2.7, -1.9])))
        assert(allclose(stats.map(lambda (_, v): v).collect()[0], array([0.42785299])))
        assert(allclose(resid.map(lambda (_, v): v).collect()[0], array([0, 0, 2, 0.9, -0.8, -2.1])))

        stats, betas = regress(data, x, "linear")
        stats.collect()
        betas.collect()

        stats, comps, latent, scores, traj = regresswithpca(data, x, "linear")
        stats.collect()
        scores.collect()

    def test_blinear_regress(self):
        data = self.sc.parallelize([(1, array([1.5, 2.3, 6.2, 5.1, 3.4, 2.1]))])
        x1 = array([
            array([1, 0, 1, 0, 1, 0]),
            array([0, 1, 0, 1, 0, 1])
        ])
        x2 = array([
            array([1, 1, 0, 0, 0, 0]),
            array([0, 0, 1, 1, 0, 0]),
            array([0, 0, 0, 0, 1, 1])
        ])
        model = RegressionModel.load((x1, x2), "bilinear")
        betas, stats, resid = model.fit(data)
        tol = 1E-4  # to handle rounding errors
        assert(allclose(betas.map(lambda (_, v): v).collect()[0], array([-3.1249, 5.6875, 0.4375]), atol=tol))
        assert(allclose(stats.map(lambda (_, v): v).collect()[0], array([0.6735]), tol))
        assert(allclose(resid.map(lambda (_, v): v).collect()[0], array([0, -0.8666, 0, 1.9333, 0, -1.0666]), atol=tol))

        stats, betas = regress(data, (x1, x2), "bilinear")
        stats.collect()
        betas.collect()

        stats, comps, latent, scores, traj = regresswithpca(data, (x1, x2), "bilinear")
        stats.collect()
        scores.collect()


class TestTuning(RegressionTestCase):
    """Test accuracy of gaussian and circular tuning
    by building small stimulus arrays and testing
    on small data against ground truth
    (ground truth for gaussian tuning
    derived by doing the algebra in MATLAB,
    ground truth for circular tuning
    derived from MATLAB's circular statistics toolbox
    circ_mean and circ_kappa functions)

    Also tests that main analysis script runs without crashing
    (separately, to test a variety of inputs)
    """
    def test_gaussian_tuning_model(self):
        data = self.sc.parallelize([(1, array([1.5, 2.3, 6.2, 5.1, 3.4, 2.1]))])
        s = array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        model = TuningModel.load(s, "gaussian")
        params = model.fit(data)
        tol = 1E-4  # to handle rounding errors
        assert(allclose(params.map(lambda (_, v): v).collect()[0], array([0.36262, 0.01836]), atol=tol))

    def test_circular_tuning_model(self):
        data = self.sc.parallelize([(1, array([1.5, 2.3, 6.2, 5.1, 3.4, 2.1]))])
        s = array([-pi/2, -pi/3, -pi/4, pi/4, pi/3, pi/2])
        model = TuningModel.load(s, "circular")
        params = model.fit(data)
        tol = 1E-4  # to handle rounding errors
        assert(allclose(params.map(lambda (_, v): v).collect()[0], array([0.10692, 1.61944]), atol=tol))

    def test_tuning_scripts(self):
        data = self.sc.parallelize([(1, array([1.5, 2.3, 6.2, 5.1, 3.4, 2.1]))])
        x1 = array([
            array([1, 0, 1, 0, 1, 0]),
            array([0, 1, 0, 1, 0, 1])
        ])
        x2 = array([
            array([1, 1, 0, 0, 0, 0]),
            array([0, 0, 1, 1, 0, 0]),
            array([0, 0, 0, 0, 1, 1])
        ])
        s = array([-pi/4, pi/4, pi/3])
        params = tuning(data, s, "circular", (x1, x2), "bilinear")
        params.collect()
        params = tuning(data, s, "gaussian", (x1, x2), "bilinear")
        params.collect()

        s = array([-pi/2, -pi/3, -pi/4, pi/4, pi/3, pi/2])
        params = tuning(data, s, "gaussian")
        params.collect()

########NEW FILE########
__FILENAME__ = test_sigprocessing
import os
import shutil
import tempfile
from numpy import array, allclose, mean, median, std, corrcoef
from scipy.linalg import norm
from thunder.sigprocessing.util import SigProcessingMethod
from thunder.sigprocessing.stats import stats
from thunder.sigprocessing.fourier import fourier
from thunder.sigprocessing.crosscorr import crosscorr
from thunder.sigprocessing.localcorr import localcorr
from thunder.sigprocessing.query import query
from test_utils import PySparkTestCase


class SigProcessingTestCase(PySparkTestCase):
    def setUp(self):
        super(SigProcessingTestCase, self).setUp()
        self.outputdir = tempfile.mkdtemp()

    def tearDown(self):
        super(SigProcessingTestCase, self).tearDown()
        shutil.rmtree(self.outputdir)


class TestStats(SigProcessingTestCase):
    """Test accuracy for signal statistics
    by comparison to direct evaluation using numpy/scipy
    """
    def test_stats(self):
        data_local = [
            array([1.0, 2.0, -4.0, 5.0]),
            array([2.0, 2.0, -4.0, 5.0]),
            array([3.0, 2.0, -4.0, 5.0]),
            array([4.0, 2.0, -4.0, 5.0]),
        ]

        data = self.sc.parallelize(zip(range(1, 5), data_local))
        data_local = array(data_local)

        vals = stats(data, "mean").map(lambda (_, v): v)

        assert(allclose(vals.collect(), mean(data_local, axis=1)))

        vals = stats(data, "median").map(lambda (_, v): v)
        assert(allclose(vals.collect(), median(data_local, axis=1)))

        vals = stats(data, "std").map(lambda (_, v): v)
        assert(allclose(vals.collect(), std(data_local, axis=1)))

        vals = stats(data, "norm").map(lambda (_, v): v)
        for i in range(0, 4):
            assert(allclose(vals.collect()[i], norm(data_local[i, :] - mean(data_local[i, :]))))


class TestFourier(SigProcessingTestCase):
    """Test accuracy for fourier analysis
    by comparison to known result
    (verified in MATLAB)
    """
    def test_fourier(self):
        data_local = [
            array([1.0, 2.0, -4.0, 5.0, 8.0, 3.0, 4.1, 0.9, 2.3]),
            array([2.0, 2.0, -4.0, 5.0, 3.1, 4.5, 8.2, 8.1, 9.1]),
        ]

        data = self.sc.parallelize(zip(range(1, 3), data_local))

        co, ph = fourier(data, 2)
        assert(allclose(co.map(lambda (_, v): v).collect()[0], 0.578664))
        assert(allclose(ph.map(lambda (_, v): v).collect()[0], 4.102501))


class TestLocalCorr(SigProcessingTestCase):
    """Test accuracy for local correlation
    by comparison to known result
    (verified by directly computing
    result with numpy's mean and corrcoef)

    Test with indexing from both 0 and 1
    """
    def test_localcorr_0_indexing(self):

        data_local = [
            ((0, 0, 0), array([1.0, 2.0, 3.0])),
            ((0, 1, 0), array([2.0, 2.0, 4.0])),
            ((0, 2, 0), array([9.0, 2.0, 1.0])),
            ((1, 0, 0), array([5.0, 2.0, 5.0])),
            ((2, 0, 0), array([4.0, 2.0, 6.0])),
            ((1, 1, 0), array([4.0, 2.0, 8.0])),
            ((1, 2, 0), array([5.0, 4.0, 1.0])),
            ((2, 1, 0), array([6.0, 3.0, 2.0])),
            ((2, 2, 0), array([0.0, 2.0, 1.0]))
        ]

        # get ground truth by correlating mean with the center
        ts = map(lambda x: x[1], data_local)
        mn = mean(ts, axis=0)
        truth = corrcoef(mn, array([4.0, 2.0, 8.0]))[0, 1]

        data = self.sc.parallelize(data_local)

        corr = localcorr(data, 1).sortByKey()

        assert(allclose(corr.collect()[4][1], truth))

    def test_localcorr_1_indexing(self):

        data_local = [
            ((1, 1, 1), array([1.0, 2.0, 3.0])),
            ((1, 2, 1), array([2.0, 2.0, 4.0])),
            ((1, 3, 1), array([9.0, 2.0, 1.0])),
            ((2, 1, 1), array([5.0, 2.0, 5.0])),
            ((3, 1, 1), array([4.0, 2.0, 6.0])),
            ((2, 2, 1), array([4.0, 2.0, 8.0])),
            ((2, 3, 1), array([5.0, 4.0, 1.0])),
            ((3, 2, 1), array([6.0, 3.0, 2.0])),
            ((3, 3, 1), array([0.0, 2.0, 1.0]))
        ]

        # get ground truth by correlating mean with the center
        ts = map(lambda x: x[1], data_local)
        mn = mean(ts, axis=0)
        truth = corrcoef(mn, array([4.0, 2.0, 8.0]))[0, 1]

        data = self.sc.parallelize(data_local)

        corr = localcorr(data, 1).sortByKey()

        assert(allclose(corr.collect()[4][1], truth))


class TestQuery(SigProcessingTestCase):
    """Test accuracy for query
    by comparison to known result
    (calculated by hand)

    Test data with both linear and
    subscript indicing for data
    """
    def test_query_subscripts(self):
        data_local = [
            ((1, 1), array([1.0, 2.0, 3.0])),
            ((2, 1), array([2.0, 2.0, 4.0])),
            ((1, 2), array([4.0, 2.0, 1.0]))
        ]

        data = self.sc.parallelize(data_local)

        inds = array([array([1, 2]), array([3])])
        ts = query(data, inds)
        assert(allclose(ts[0, :], array([1.5, 2., 3.5])))
        assert(allclose(ts[1, :], array([4.0, 2.0, 1.0])))

    def test_query_linear(self):
        data_local = [
            ((1,), array([1.0, 2.0, 3.0])),
            ((2,), array([2.0, 2.0, 4.0])),
            ((3,), array([4.0, 2.0, 1.0]))
        ]

        data = self.sc.parallelize(data_local)

        inds = array([array([1, 2]), array([3])])
        ts = query(data, inds)
        assert(allclose(ts[0, :], array([1.5, 2., 3.5])))
        assert(allclose(ts[1, :], array([4.0, 2.0, 1.0])))


class TestCrossCorr(SigProcessingTestCase):
    """Test accuracy for cross correlation
    by comparison to known result
    (lag=0 case tested with numpy corrcoef function,
    lag>0 case tested against result from MATLAB's xcov)

    Also tests main analysis script
    """
    def test_crosscorr(self):
        data_local = array([
            array([1.0, 2.0, -4.0, 5.0, 8.0, 3.0, 4.1, 0.9, 2.3]),
            array([2.0, 2.0, -4.0, 5.0, 3.1, 4.5, 8.2, 8.1, 9.1]),
        ])

        sig = array([1.5, 2.1, -4.2, 5.6, 8.1, 3.9, 4.2, 0.3, 2.1])

        data = self.sc.parallelize(zip(range(1, 3), data_local))

        method = SigProcessingMethod.load("crosscorr", sigfile=sig, lag=0)
        betas = method.calc(data).map(lambda (_, v): v)
        assert(allclose(betas.collect()[0], corrcoef(data_local[0, :], sig)[0, 1]))
        assert(allclose(betas.collect()[1], corrcoef(data_local[1, :], sig)[0, 1]))

        method = SigProcessingMethod.load("crosscorr", sigfile=sig, lag=2)
        betas = method.calc(data).map(lambda (_, v): v)
        tol = 1E-5  # to handle rounding errors
        assert(allclose(betas.collect()[0], array([-0.18511, 0.03817, 0.99221, 0.06567, -0.25750]), atol=tol))
        assert(allclose(betas.collect()[1], array([-0.35119, -0.14190, 0.44777, -0.00408, 0.45435]), atol=tol))

        betas = crosscorr(data, sig, 0).map(lambda (_, v): v)
        assert(allclose(betas.collect()[0], corrcoef(data_local[0, :], sig)[0, 1]))
        assert(allclose(betas.collect()[1], corrcoef(data_local[1, :], sig)[0, 1]))







########NEW FILE########
__FILENAME__ = test_utils
import unittest
from pyspark import SparkContext


class PySparkTestCase(unittest.TestCase):
    def setUp(self):
        class_name = self.__class__.__name__
        self.sc = SparkContext('local', class_name)

    def tearDown(self):
        self.sc.stop()
        # To avoid Akka rebinding to the same port, since it doesn't unbind
        # immediately on shutdown
        self.sc._jvm.System.clearProperty("spark.driver.port")
########NEW FILE########
__FILENAME__ = classify
import os
import argparse
import glob
from thunder.classification.util import MassUnivariateClassifier
from thunder.util.load import load
from thunder.util.save import save
from pyspark import SparkContext


def classify(data, params, classifymode, featureset=None, cv=0):
    """Perform mass univariate classification

    :param data: RDD of data points as key value pairs
    :param params: string with file location, or dictionary of parameters for classification
    :param classifymode: form of classifier ("naivebayes")
    :param featureset: set of features to use for classification (default=None)
    :param cv: number of cross validation folds (default=0, for no cv)

    :return perf: performance
    """
    # create classifier
    clf = MassUnivariateClassifier.load(params, classifymode, cv)

    # do classification
    perf = clf.classify(data, featureset)

    return perf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fit a regression model")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("paramfile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("classifymode", choices="naivebayes", help="form of classifier")
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()

    sc = SparkContext(args.master, "classify")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    data = load(sc, args.datafile, args.preprocess)

    perf = classify(data, args.paramfile, args.classifymode)

    outputdir = args.outputdir + "-classify"

    save(perf, outputdir, "perf", "matlab")

########NEW FILE########
__FILENAME__ = util
from numpy import in1d, zeros, array, size, float64
from scipy.io import loadmat
from scipy.stats import ttest_ind
from sklearn.naive_bayes import GaussianNB
from sklearn import cross_validation


class MassUnivariateClassifier(object):
    """Class for loading and classifying with classifiers"""

    def __init__(self, paramfile):
        """Initialize classifier using parameters derived from a Matlab file,
        or a python dictionary. At a minimum, must contain a "labels" field, with the
        label to classify at each time point. Can additionally include fields for
        "features" (which feature was present at each time point)
        and "samples" (which sample was present at each time point)

        :param paramfile: string of filename, or dictionary, containing parameters
        """
        if type(paramfile) is str:
            params = loadmat(paramfile, squeeze_me=True)
        elif type(paramfile) is dict:
            params = paramfile
        else:
            raise TypeError("Parameters for classification must be provided as string with file location, or dictionary")

        self.labels = params['labels']

        if 'features' in params:
            self.features = params['features']
            self.nfeatures = len(list(set(self.features.flatten())))
            self.samples = params['samples']
            self.sampleids = list(set(self.samples.flatten()))
            self.nsamples = len(self.sampleids)
        else:
            self.nfeatures = 1
            self.nsamples = len(self.labels)

    @staticmethod
    def load(paramfile, classifymode, cv=0):
        return CLASSIFIERS[classifymode](paramfile, cv)

    def get(self, x, set=None):
        pass

    def classify(self, data, featureset=None):
        """Do the classification on an RDD using a map

        :param data: RDD of data points as key value pairs
        :param featureset: list of lists containing the features to use
        :return: perf: RDD of key value pairs with classification performance
        """

        if self.nfeatures == 1:
            perf = data.mapValues(lambda x: [self.get(x)])
        else:
            if featureset is None:
                featureset = [[self.features[0]]]
            for i in featureset:
                assert array([item in i for item in self.features]).sum() != 0, "Feature set invalid"
            perf = data.mapValues(lambda x: map(lambda i: self.get(x, i), featureset))

        return perf


class GaussNaiveBayesClassifier(MassUnivariateClassifier):
    """Class for gaussian naive bayes classification"""

    def __init__(self, paramfile, cv):
        """Create classifier

        :param paramfile: string of filename or dictionary with parameters (see MassUnivariateClassifier)
        :param cv: number of cross validation folds (none if 0)
        """
        MassUnivariateClassifier.__init__(self, paramfile)

        self.cv = cv
        self.func = GaussianNB()

    def get(self, x, featureset=None):
        """Compute classification performance"""

        y = self.labels
        if self.nfeatures == 1:
            X = zeros((self.nsamples, 1))
            X[:, 0] = x
        else:
            X = zeros((self.nsamples, size(featureset)))
            for i in range(0, self.nsamples):
                inds = (self.samples == self.sampleids[i]) & (in1d(self.features, featureset))
                X[i, :] = x[inds]

        if self.cv > 0:
            return cross_validation.cross_val_score(self.func, X, y, cv=self.cv).mean()
        else:
            ypred = self.func.fit(X, y).predict(X)
            return array(y == ypred).mean()


class TTestClassifier(MassUnivariateClassifier):
    """Class for t test classification"""

    def __init__(self, paramfile, cv):
        """Create classifier

        :param paramfile: string of filename or dictionary with parameters (see MassUnivariateClassifer)
        """
        MassUnivariateClassifier.__init__(self, paramfile)

        self.func = ttest_ind
        unique = list(set(list(self.labels)))
        if len(unique) != 2:
            raise TypeError("Only two types of labels allowed for t-test classificaiton")
        if unique != set((0, 1)):
            self.labels = array(map(lambda i: 0 if i == unique[0] else 1, self.labels))

    def get(self, x, featureset=None):
        """Compute t-statistic

        :param x: vector of signals to use in classification
        :param featureset: which features to test"""

        if (self.nfeatures > 1) & (size(featureset) > 1):
            X = zeros((self.nsamples, size(featureset)))
            for i in range(0, size(featureset)):
                X[:, i] = x[self.features == featureset[i]]
            return float64(self.func(X[self.labels == 0, :], X[self.labels == 1, :])[0])

        else:
            if self.nfeatures > 1:
                x = x[self.features == featureset]
            return float64(self.func(x[self.labels == 0], x[self.labels == 1])[0])


CLASSIFIERS = {
    'gaussnaivebayes': GaussNaiveBayesClassifier,
    'ttest': TTestClassifier
}

########NEW FILE########
__FILENAME__ = kmeans
import os
import argparse
import glob
from numpy import sum
from thunder.util.load import load
from thunder.util.save import save
from pyspark import SparkContext


def closestpoint(p, centers):
    """Return the index of the closest point in centers to p"""

    bestindex = 0
    closest = float("+inf")
    for i in range(len(centers)):
        tempdist = sum((p - centers[i]) ** 2)
        if tempdist < closest:
            closest = tempdist
            bestindex = i
    return bestindex


def kmeans(data, k, maxiter=20, tol=0.001):
    """Perform kmeans clustering

    :param data: RDD of data points as key value pairs
    :param k: number of clusters
    :param maxiter: maximum number of iterations (default = 20)
    :param tol: change tolerance for stopping algorithm (default = 0.001)

    :return labels: RDD with labels for each data point
    :return centers: array of cluster centroids
    """
    centers = map(lambda (_, v): v, data.take(k))

    tempdist = 1.0
    iter = 0

    while (tempdist > tol) & (iter < maxiter):
        closest = data.map(lambda (_, v): v).map(lambda p: (closestpoint(p, centers), (p, 1)))
        pointstats = closest.reduceByKey(lambda (x1, y1), (x2, y2): (x1 + x2, y1 + y2))
        newpoints = pointstats.map(lambda (x, (y, z)): (x, y / z)).collect()
        tempdist = sum(sum((centers[x] - y) ** 2) for (x, y) in newpoints)

        for (i, j) in newpoints:
            centers[i] = j

        iter += 1

    labels = data.mapValues(lambda p: closestpoint(p, centers))

    return labels, centers

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="do kmeans clustering")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("k", type=int)
    parser.add_argument("--maxiter", type=float, default=20, required=False)
    parser.add_argument("--tol", type=float, default=0.001, required=False)
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()

    sc = SparkContext(args.master, "kmeans")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    data = load(sc, args.datafile, args.preprocess).cache()

    labels, centers = kmeans(data, k=args.k, maxiter=args.maxiter, tol=args.tol)

    outputdir = args.outputdir + "-kmeans"

    save(labels, outputdir, "labels", "matlab")
    save(centers, outputdir, "centers", "matlab")
########NEW FILE########
__FILENAME__ = ica
import os
import argparse
import glob
from numpy import random, sqrt, zeros, real, dot, outer, diag, transpose
from scipy.linalg import sqrtm, inv, orth
from thunder.util.load import load
from thunder.util.save import save
from thunder.factorization.util import svd
from pyspark import SparkContext


def ica(data, k, c, svdmethod="direct", maxiter=100, tol=0.000001, seed=0):
    """Perform independent components analysis

    :param: data: RDD of data points
    :param k: number of principal components to use
    :param c: number of independent components to find
    :param maxiter: maximum number of iterations (default = 100)
    :param: tol: tolerance for change in estimate (default = 0.000001)

    :return w: the mixing matrix
    :return: sigs: the independent components

    TODO: also return unmixing matrix
    """
    # get count
    n = data.count()

    # reduce dimensionality
    scores, latent, comps = svd(data, k, meansubtract=0, method=svdmethod)

    # whiten data
    whtmat = real(dot(inv(diag(latent/sqrt(n))), comps))
    unwhtmat = real(dot(transpose(comps), diag(latent/sqrt(n))))
    wht = data.mapValues(lambda x: dot(whtmat, x))

    # do multiple independent component extraction
    if seed != 0:
        random.seed(seed)
    b = orth(random.randn(k, c))
    b_old = zeros((k, c))
    iter = 0
    minabscos = 0
    errvec = zeros(maxiter)

    while (iter < maxiter) & ((1 - minabscos) > tol):
        iter += 1
        # update rule for pow3 non-linearity (TODO: add others)
        b = wht.map(lambda (_, v): v).map(lambda x: outer(x, dot(x, b) ** 3)).sum() / n - 3 * b
        # make orthogonal
        b = dot(b, real(sqrtm(inv(dot(transpose(b), b)))))
        # evaluate error
        minabscos = min(abs(diag(dot(transpose(b), b_old))))
        # store results
        b_old = b
        errvec[iter-1] = (1 - minabscos)

    # get un-mixing matrix
    w = dot(transpose(b), whtmat)

    # get components
    sigs = data.mapValues(lambda x: dot(w, x))

    return w, sigs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="do independent components analysis")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("k", type=int)
    parser.add_argument("c", type=int)
    parser.add_argument("--svdmethod", choices=("direct", "em"), default="direct", required=False)
    parser.add_argument("--maxiter", type=float, default=100, required=False)
    parser.add_argument("--tol", type=float, default=0.000001, required=False)
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)
    parser.add_argument("--seed", type=int, default=0, required=False)

    args = parser.parse_args()
    
    sc = SparkContext(args.master, "ica")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])
    
    data = load(sc, args.datafile, args.preprocess).cache()

    w, sigs = ica(data, args.k, args.c, svdmethod=args.svdmethod, maxiter=args.maxiter, tol=args.tol, seed=args.seed)

    outputdir = args.outputdir + "-ica"

    save(w, outputdir, "w", "matlab")
    save(sigs, outputdir, "sigs", "matlab")

########NEW FILE########
__FILENAME__ = pca
import os
import argparse
import glob
from thunder.util.load import load
from thunder.util.save import save
from thunder.factorization.util import svd
from pyspark import SparkContext


def pca(data, k, svdmethod="direct"):
    """Perform principal components analysis
    using the singular value decomposition

    :param data: RDD of data points as key value pairs
    :param k: number of principal components to recover
    :param svdmethod: which svd algorithm to use (default = "direct")

    :return comps: the k principal components (as array)
    :return latent: the latent values
    :return scores: the k scores (as RDD)
    """
    scores, latent, comps = svd(data, k, meansubtract=0, method=svdmethod)

    return scores, latent, comps

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="do principal components analysis")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("k", type=int)
    parser.add_argument("--svdmethod", choices=("direct", "em"), default="direct", required=False)
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()

    sc = SparkContext(args.master, "pca")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    data = load(sc, args.datafile, args.preprocess).cache()

    scores, latent, comps = pca(data, args.k, args.svdmethod)

    outputdir = args.outputdir + "-pca"

    save(comps, outputdir, "comps", "matlab")
    save(latent, outputdir, "latent", "matlab")
    save(scores, outputdir, "scores", "matlab")
########NEW FILE########
__FILENAME__ = util
from numpy import random, sum, real, argsort, mean, transpose, dot, inner, outer, zeros, shape, sqrt
from scipy.linalg import eig, inv, orth
from pyspark.accumulators import AccumulatorParam


def svd(data, k, meansubtract=1, method="direct", maxiter=20, tol=0.00001):
    """Large-scale singular value decomposition for dense matrices

    Direct method uses an accumulator to distribute and sum outer products
    only efficient when n >> m (tall and skinny)
    requires that n ** 2 fits in memory

    EM method uses an iterative algorithm based on expectation maximization

    TODO: select method automatically based on data dimensions
    TODO: return fractional variance explained by k eigenvectors

    :param data: RDD of data points as key value pairs
    :param k: number of components to recover
    :param method: choice of algorithm, "direct", "em" (default = "direct")
    :param meansubtract: whether or not to subtract the mean

    :return comps: the left k eigenvectors (as array)
    :return latent: the singular values
    :return scores: the right k eigenvectors (as RDD)
    """
    if method == "direct":

        # set up a matrix accumulator
        class MatrixAccumulatorParam(AccumulatorParam):
            def zero(self, value):
                return zeros(shape(value))

            def addInPlace(self, val1, val2):
                val1 += val2
                return val1

        n = data.count()
        m = len(data.first()[1])
        if meansubtract == 1:
            data = data.mapValues(lambda x: x - mean(x))

        # create a variable and method to compute sums of outer products
        global cov
        cov = data.context.accumulator(zeros((m, m)), MatrixAccumulatorParam())

        def outersum(x):
            global cov
            cov += outer(x, x)

        # compute the covariance matrix
        data.map(lambda (_, v): v).foreach(outersum)

        # do local eigendecomposition
        w, v = eig(cov.value / n)
        w = real(w)
        v = real(v)
        inds = argsort(w)[::-1]
        latent = sqrt(w[inds[0:k]]) * sqrt(n)
        comps = transpose(v[:, inds[0:k]])

        # project back into data, normalize by singular values
        scores = data.mapValues(lambda x: inner(x, comps) / latent)

        return scores, latent, comps

    if method == "em":

        n = data.count()
        m = len(data.first()[1])
        if meansubtract == 1:
            data = data.mapValues(lambda x: x - mean(x))

        def outerprod(x):
            return outer(x, x)

        c = random.rand(k, m)
        iter = 0
        error = 100

        # iterative update subspace using expectation maximization
        # e-step: x = (c'c)^-1 c' y
        # m-step: c = y x' (xx')^-1
        while (iter < maxiter) & (error > tol):
            c_old = c
            # pre compute (c'c)^-1 c'
            c_inv = dot(transpose(c), inv(dot(c, transpose(c))))
            premult1 = data.context.broadcast(c_inv)
            # compute (xx')^-1 through a map reduce
            xx = data.map(lambda (_, v): v).map(lambda x: outerprod(dot(x, premult1.value))).sum()
            xx_inv = inv(xx)
            # pre compute (c'c)^-1 c' (xx')^-1
            premult2 = data.context.broadcast(dot(c_inv, xx_inv))
            # compute the new c through a map reduce
            c = data.map(lambda (_, v): v).map(lambda x: outer(x, dot(x, premult2.value))).sum()
            c = transpose(c)

            error = sum(sum((c - c_old) ** 2))
            iter += 1

        # project data into subspace spanned by columns of c
        # use standard eigendecomposition to recover an orthonormal basis
        c = transpose(orth(transpose(c)))
        premult3 = data.context.broadcast(c)
        cov = data.map(lambda (_, v): v).map(lambda x: dot(x, transpose(premult3.value))).map(lambda x: outerprod(x)).mean()
        w, v = eig(cov)
        w = real(w)
        v = real(v)
        inds = argsort(w)[::-1]
        latent = sqrt(w[inds[0:k]]) * sqrt(n)
        comps = dot(transpose(v[:, inds[0:k]]), c)
        scores = data.mapValues(lambda x: inner(x, comps) / latent)

        return scores, latent, comps

########NEW FILE########
__FILENAME__ = regress
import os
import argparse
import glob
from thunder.regression.util import RegressionModel
from thunder.util.load import load
from thunder.util.save import save
from pyspark import SparkContext


def regress(data, modelfile, regressmode):
    """Perform mass univariate regression

    :param data: RDD of data points as key value pairs
    :param modelfile: model parameters (string with file location, array, or tuple)
    :param regressmode: form of regression ("linear" or "bilinear")

    :return stats: statistics of the fit
    :return betas: regression coefficients
    """
    # create model
    model = RegressionModel.load(modelfile, regressmode)

    # do regression
    betas, stats, resid = model.fit(data)

    return stats, betas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fit a regression model")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("modelfile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("regressmode", choices=("linear", "bilinear"), help="form of regression")
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()

    sc = SparkContext(args.master, "regress")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])
    
    data = load(sc, args.datafile, args.preprocess)

    stats, betas = regress(data, args.modelfile, args.regressmode)

    outputdir = args.outputdir + "-regress"

    save(stats, outputdir, "stats", "matlab")
    save(betas, outputdir, "betas", "matlab")

########NEW FILE########
__FILENAME__ = regresswithpca
import os
import argparse
import glob
from thunder.regression.util import RegressionModel
from thunder.factorization.util import svd
from thunder.util.load import load
from thunder.util.save import save
from pyspark import SparkContext


def regresswithpca(data, modelfile, regressmode, k=2):
    """Perform univariate regression,
    followed by principal components analysis
    to reduce dimensionality

    :param data: RDD of data points as key value pairs
    :param modelfile: model parameters (string with file location, array, or tuple)
    :param regressmode: form of regression ("linear" or "bilinear")
    :param k: number of principal components to compute

    :return stats: statistics of the fit
    :return comps: compoents from PCA
    :return scores: scores from PCA
    :return latent: latent variances from PCA
    """
    # create model
    model = RegressionModel.load(modelfile, regressmode)

    # do regression
    betas, stats, resid = model.fit(data)

    # do principal components analysis
    scores, latent, comps = svd(betas, k)

    # compute trajectories from raw data
    traj = model.fit(data, comps)

    return stats, comps, latent, scores, traj


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fit a regression model")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("modelfile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("regressmode", choices=("linear", "bilinear"), help="form of regression")
    parser.add_argument("--k", type=int, default=2)
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()
    
    sc = SparkContext(args.master, "regresswithpca")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    data = load(sc, args.datafile, args.preprocess).cache()

    stats, comps, latent, scores, traj = regresswithpca(data, args.modelfile, args.regressmode, args.k)

    outputdir = args.outputdir + "-regress"

    save(stats, outputdir, "stats", "matlab")
    save(comps, outputdir, "comps", "matlab")
    save(latent, outputdir, "latent", "matlab")
    save(scores, outputdir, "scores", "matlab")
    save(traj, outputdir, "traj", "matlab")
########NEW FILE########
__FILENAME__ = tuning
import os
import argparse
import glob
from thunder.regression.util import RegressionModel, TuningModel
from thunder.util.load import load
from thunder.util.save import save
from pyspark import SparkContext


def tuning(data, tuningmodelfile, tuningmode, regressmodelfile=None, regressmode=None):
    """Estimate parameters of a tuning curve model,
    optionally preceeded by regression

    :param data: RDD of data points as key value pairs
    :param tuningmodelfile: model parameters for tuning (string with file location, array, or tuple)
    :param: tuningmode: form of tuning ("gaussian" or "circular")
    :param regressmodelfile: model parameters for regression (default=None)
    :param regressmode: form of regression ("linear" or "bilinear") (default=None)

    :return params: tuning curve parameters
    """
    # create tuning model
    tuningmodel = TuningModel.load(tuningmodelfile, tuningmode)

    # get tuning curves
    if regressmodelfile is not None:
        # use regression results
        regressmodel = RegressionModel.load(regressmodelfile, regressmode)
        betas, stats, resid = regressmodel.fit(data)
        params = tuningmodel.fit(betas)
    else:
        # use data
        params = tuningmodel.fit(data)

    return params

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fit a parametric tuning curve to regression results")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("tuningmodelfile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("tuningmode", choices=("circular", "gaussian"), help="form of tuning curve")
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)
    parser.add_argument("--regressmodelfile", type=str)
    parser.add_argument("--regressmode", choices=("linear", "bilinear"), help="form of regression")

    args = parser.parse_args()
    
    sc = SparkContext(args.master, "tuning")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    data = load(sc, args.datafile, args.preprocess).cache()

    params = tuning(data, args.tuningmodelfile, args.tuningmode, args.regressmodelfile, args.regressmode)

    outputdir = args.outputdir + "-tuning"

    save(params, outputdir, "params", "matlab")

########NEW FILE########
__FILENAME__ = util
"""
Utilities for regression and tuning curve fitting
"""

from scipy.io import loadmat
from numpy import array, sum, outer, inner, mean, shape, dot, transpose, concatenate, ones, angle, abs, exp
from scipy.linalg import inv


class RegressionModel(object):
    """Class for loading and fitting a regression"""

    @staticmethod
    def load(modelfile, regressmode, *opts):
        return REGRESSION_MODELS[regressmode](modelfile, *opts)

    def get(self, y):
        pass

    def fit(self, data, comps=None):
        if comps is not None:
            traj = data.map(lambda (_, v): v).map(
                lambda x: outer(x, inner(self.get(x)[0] - mean(self.get(x)[0]), comps))).reduce(
                    lambda x, y: x + y) / data.count()
            return traj
        else:
            result = data.mapValues(lambda x: self.get(x))
            betas = result.mapValues(lambda x: x[0])
            stats = result.mapValues(lambda x: x[1])
            resid = result.mapValues(lambda x: x[2])
            return betas, stats, resid


class LinearRegressionModel(RegressionModel):
    """Class for linear regression"""

    def __init__(self, modelfile):
        """Load model

        :param modelfile: An array, or a string (assumes a MAT file
        with name modelfile_X containing variable X)
        """
        if type(modelfile) is str:
            x = loadmat(modelfile + "_X.mat")['X']
        else:
            x = modelfile
        x = concatenate((ones((1, shape(x)[1])), x))
        x_hat = dot(inv(dot(x, transpose(x))), x)
        self.x = x
        self.x_hat = x_hat

    def get(self, y):
        """Compute regression coefficients, r2 statistic, and residuals"""

        b = dot(self.x_hat, y)
        predic = dot(b, self.x)
        resid = y - predic
        sse = sum((predic - y) ** 2)
        sst = sum((y - mean(y)) ** 2)
        if sst == 0:
            r2 = 0
        else:
            r2 = 1 - sse / sst
        return b[1:], r2, resid


class BilinearRegressionModel(RegressionModel):
    """Class for bilinear regression"""

    def __init__(self, modelfile):
        """Load model

        :param modelfile: A tuple of arrays, or a string (assumes two MAT files
        with names modelfile_X1 and modefile_X2 containing variables X1 nd X2)
        """
        if type(modelfile) is str:
            x1 = loadmat(modelfile + "_X1.mat")['X1']
            x2 = loadmat(modelfile + "_X2.mat")['X2']
        else:
            x1 = modelfile[0]
            x2 = modelfile[1]
        x1_hat = dot(inv(dot(x1, transpose(x1))), x1)
        self.x1 = x1
        self.x2 = x2
        self.x1_hat = x1_hat

    def get(self, y):
        """Compute two sets of regression coefficients, r2 statistic, and residuals"""

        b1 = dot(self.x1_hat, y)
        b1 = b1 - min(b1)
        b1_hat = dot(transpose(self.x1), b1)
        if sum(b1_hat) == 0:
            b1_hat += 1E-06
        x3 = self.x2 * b1_hat
        x3 = concatenate((ones((1, shape(x3)[1])), x3))
        x3_hat = dot(inv(dot(x3, transpose(x3))), x3)
        b2 = dot(x3_hat, y)
        predic = dot(b2, x3)
        resid = y - predic
        sse = sum((predic - y) ** 2)
        sst = sum((y - mean(y)) ** 2)
        if sst == 0:
            r2 = 0
        else:
            r2 = 1 - sse / sst

        return b2[1:], r2, resid


class TuningModel(object):
    """Class for loading and fitting a tuning model"""

    def __init__(self, modelfile):
        """Load model

        :param modelfile: An array, or a string (assumes a MAT file
        with name modelfile_s containing variable s)
        """
        if type(modelfile) is str:
            self.s = loadmat(modelfile + "_s.mat")['s']
        else:
            self.s = modelfile

    @staticmethod
    def load(modelfile, tuningmode):
        return TUNING_MODELS[tuningmode](modelfile)

    def get(self, y):
        pass

    def fit(self, data):
        return data.mapValues(lambda x: self.get(x))


class CircularTuningModel(TuningModel):
    """Class for circular tuning"""

    def get(self, y):
        """Estimates the circular mean and variance ("kappa")
        identical to the max likelihood estimates of the
        parameters of the best fitting von-mises function
        """
        y = y - min(y)
        if sum(y) == 0:
            y += 1E-06
        y = y / sum(y)
        r = inner(y, exp(1j * self.s))
        mu = angle(r)
        v = abs(r) / sum(y)
        if v < 0.53:
            k = 2 * v + (v ** 3) + 5 * (v ** 5) / 6
        elif (v >= 0.53) & (v < 0.85):
            k = -.4 + 1.39 * v + 0.43 / (1 - v)
        elif (v ** 3 - 4 * (v ** 2) + 3 * v) == 0:
            k = array([0.0])
        else:
            k = 1 / (v ** 3 - 4 * (v ** 2) + 3 * v)
        if k > 1E8:
            k = array([0.0])
        return mu, k


class GaussianTuningModel(TuningModel):
    """Class for gaussian tuning"""

    def get(self, y):
        """Estimates the mean and variance
        similar to the max likelihood estimates of the
        parameters of the best fitting gaussian
        but non-infinite supports may bias estimates
        """
        y[y < 0] = 0
        if sum(y) == 0:
            y += 1E-06
        y = y / sum(y)
        mu = dot(self.s, y)
        sigma = dot((self.s - mu) ** 2, y)
        return mu, sigma


TUNING_MODELS = {
    'circular': CircularTuningModel,
    'gaussian': GaussianTuningModel
}

REGRESSION_MODELS = {
    'linear': LinearRegressionModel,
    'bilinear': BilinearRegressionModel
}
########NEW FILE########
__FILENAME__ = crosscorr
import os
import argparse
import glob
from thunder.sigprocessing.util import SigProcessingMethod
from thunder.factorization.util import svd
from thunder.util.load import load
from thunder.util.save import save
from pyspark import SparkContext


def crosscorr(data, sigfile, lag):
    """Cross-correlate data points
    (typically time series data)
    against a signal over the specified lags

    :param data: RDD of data points as key value pairs
    :param sigfile: signal to correlate with (string with file location or array)
    :param lag: maximum lag (result will be length 2*lag + 1)

    :return betas: cross-correlations at different time lags
    :return scores: scores from PCA (if lag > 0)
    :return latent: scores from PCA (if lag > 0)
    :return comps: components from PCA (if lag > 0)
    """

    # compute cross correlations
    method = SigProcessingMethod.load("crosscorr", sigfile=sigfile, lag=lag)
    betas = method.calc(data)

    if lag is not 0:
        # do PCA
        scores, latent, comps = svd(betas, 2)
        return betas, scores, latent, comps
    else:
        return betas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fit a regression model")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("sigfile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("lag", type=int)
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()

    sc = SparkContext(args.master, "crosscorr")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])
    
    data = load(sc, args.datafile, args.preprocess).cache()

    outputdir = args.outputdir + "-crosscorr"

    # post-process data with pca if lag greater than 0
    if args.lag is not 0:
        betas, scores, latent, comps = crosscorr(data, args.sigfile, args.lag)
        save(comps, outputdir, "comps", "matlab")
        save(latent, outputdir, "latent", "matlab")
        save(scores, outputdir, "scores", "matlab")
    else:
        betas = crosscorr(data, args.sigfile, args.lag)
        save(betas, outputdir, "stats", "matlab")

########NEW FILE########
__FILENAME__ = fourier
import os
import argparse
import glob
from thunder.sigprocessing.util import SigProcessingMethod
from thunder.util.load import load
from thunder.util.save import save
from pyspark import SparkContext


def fourier(data, freq):
    """Compute fourier transform of data points
    (typically time series data)

    :param data: RDD of data points as key value pairs
    :param freq: frequency (number of cycles)

    :return: co: RDD of coherence (normalized amplitude)
    :return: ph: RDD of phase
    """

    method = SigProcessingMethod.load("fourier", freq=freq)
    out = method.calc(data)

    co = out.mapValues(lambda x: x[0])
    ph = out.mapValues(lambda x: x[1])

    return co, ph

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="compute a fourier transform on each time series")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("freq", type=int)
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()

    sc = SparkContext(args.master, "fourier")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    data = load(sc, args.datafile, args.preprocess).cache()

    co, ph = fourier(data, args.freq)

    outputdir = args.outputdir + "-fourier"

    save(co, outputdir, "co", "matlab")
    save(ph, outputdir, "ph", "matlab")

########NEW FILE########
__FILENAME__ = localcorr
import os
import argparse
import glob
from numpy import corrcoef
from thunder.util.load import load
from thunder.util.save import save
from pyspark import SparkContext


def clip(val, mn, mx):
    """clip a value below by mn and above by mx"""

    if val < mn:
        return mn
    if val > mx:
        return mx
    else:
        return val


def maptoneighborhood(ind, ts, sz, mn_x, mx_x, mn_y, mx_y):
    """Create a list of key value pairs with multiple shifted copies
    of the time series ts over a region specified by sz
    """
    rng_x = range(-sz, sz+1, 1)
    rng_y = range(-sz, sz+1, 1)
    out = list()
    for x in rng_x:
        for y in rng_y:
            new_x = clip(ind[0] + x, mn_x, mx_x)
            new_y = clip(ind[1] + y, mn_y, mx_y)
            newind = (new_x, new_y, ind[2])
            out.append((newind, ts))
    return out


def localcorr(data, sz):
    """Compute correlation between every data point
    and the average of a local neighborhood in x and y
    (typically time series data)

    :param data: RDD of data points as key value pairs
    :param sz: neighborhood size (total neighborhood is a 2*sz+1 square)

    :return corr: RDD of correlations
    """

    # get boundaries
    xs = data.map(lambda (k, _): k[0])
    ys = data.map(lambda (k, _): k[1])
    mx_x = xs.reduce(max)
    mn_x = xs.reduce(min)
    mx_y = ys.reduce(max)
    mn_y = ys.reduce(min)

    # flat map to key value pairs where the key is neighborhood identifier and value is time series
    neighbors = data.flatMap(lambda (k, v): maptoneighborhood(k, v, sz, mn_x, mx_x, mn_y, mx_y))

    # printing here seems to fix a hang later, possibly a PySpark bug
    print(neighbors.first())

    # reduce by key to get the average time series for each neighborhood
    means = neighbors.reduceByKey(lambda x, y: x + y).mapValues(lambda x: x / ((2*sz+1)**2))

    # join with the original time series data to compute correlations
    result = data.join(means)

    # get correlations
    corr = result.mapValues(lambda x: corrcoef(x[0], x[1])[0, 1]).sortByKey()

    return corr


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="correlate time series with neighbors")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("sz", type=int)
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()


    sc = SparkContext(args.master, "localcorr")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    data = load(sc, args.datafile, args.preprocess).cache()

    corrs = localcorr(data, args.sz)

    outputdir = args.outputdir + "-localcorr"

    save(corrs, outputdir, "corr", "matlab")
########NEW FILE########
__FILENAME__ = query
import os
import argparse
import glob
from numpy import zeros
from thunder.sigprocessing.util import SigProcessingMethod
from thunder.util.load import load, subtoind, getdims
from thunder.util.save import save
from pyspark import SparkContext


def query(data, indsfile):
    """Query data by averaging together
    data points with the given indices

    :param data: RDD of data points as key value pairs
    :param indsfile: string with file location or array

    :return ts: array with averages
    """
    # load indices
    method = SigProcessingMethod.load("query", indsfile=indsfile)

    # convert to linear indexing
    dims = getdims(data)
    data = subtoind(data, dims.max)

    # loop over indices, averaging time series
    ts = zeros((method.n, len(data.first()[1])))
    for i in range(0, method.n):
        indsb = data.context.broadcast(method.inds[i])
        ts[i, :] = data.filter(lambda (k, _): k in indsb.value).map(
            lambda (k, x): x).mean()

    return ts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="query time series data by averaging values for given indices")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("indsfile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()

    sc = SparkContext(args.master, "query")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    data = load(sc, args.datafile, args.preprocess).cache()

    ts = query(data, args.indsfile)

    outputdir = args.outputdir + "-query"

    save(ts, outputdir, "ts", "matlab")

########NEW FILE########
__FILENAME__ = stats
import os
import argparse
import glob
from thunder.sigprocessing.util import SigProcessingMethod
from thunder.util.load import load
from thunder.util.save import save
from pyspark import SparkContext


def stats(data, statistic):
    """compute summary statistics on every data point

    arguments:
    data - RDD of data points
    mode - which statistic to compute ("median", "mean", "std", "norm")

    returns:
    vals - RDD of statistics
    """

    method = SigProcessingMethod.load("stats", statistic=statistic)
    vals = method.calc(data)

    return vals

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="compute summary statistics on time series data")
    parser.add_argument("master", type=str)
    parser.add_argument("datafile", type=str)
    parser.add_argument("outputdir", type=str)
    parser.add_argument("mode", choices=("mean", "median", "std", "norm"),
                        help="which summary statistic")
    parser.add_argument("--preprocess", choices=("raw", "dff", "dff-highpass", "sub"), default="raw", required=False)

    args = parser.parse_args()

    sc = SparkContext(args.master, "stats")

    if args.master != "local":
        egg = glob.glob(os.path.join(os.environ['THUNDER_EGG'], "*.egg"))
        sc.addPyFile(egg[0])

    data = load(sc, args.datafile, args.preprocess).cache()

    vals = stats(data, args.mode)

    outputdir = args.outputdir + "-stats"

    save(vals, outputdir, "stats_" + args.mode, "matlab")
########NEW FILE########
__FILENAME__ = util
"""
utilities for signal processing
"""

from numpy import sqrt, fix, pi, median, std, sum, mean, shape, zeros, roll, dot, angle, abs
from scipy.linalg import norm
from scipy.io import loadmat
from numpy.fft import fft


class SigProcessingMethod(object):
    """class for doing signal processing"""

    @staticmethod
    def load(method, **opts):
        return SIGPROCESSING_METHODS[method](**opts)

    def get(self, y):
        pass

    def calc(self, data):
        result = data.mapValues(lambda x: self.get(x))
        return result


class FourierMethod(SigProcessingMethod):
    """class for computing fourier transform"""

    def __init__(self, freq):
        """get frequency"""

        self.freq = freq

    def get(self, y):
        """compute fourier amplitude (coherence) and phase"""

        y = y - mean(y)
        nframes = len(y)
        ft = fft(y)
        ft = ft[0:int(fix(nframes/2))]
        amp_ft = 2*abs(ft)/nframes
        amp = amp_ft[self.freq]
        amp_sum = sqrt(sum(amp_ft**2))
        co = amp / amp_sum
        ph = -(pi/2) - angle(ft[self.freq])
        if ph < 0:
            ph += pi * 2
        return co, ph


class StatsMethod(SigProcessingMethod):
    """class for computing simple summary statistics"""

    def __init__(self, statistic):
        """get mode"""
        self.func = {
            'median': lambda x: median(x),
            'mean': lambda x: mean(x),
            'std': lambda x: std(x),
            'norm': lambda x: norm(x - mean(x)),
        }[statistic]

    def get(self, y):
        """compute fourier amplitude (coherence) and phase"""

        return self.func(y)


class QueryMethod(SigProcessingMethod):
    """class for computing averages over indices"""

    def __init__(self, indsfile):
        """get indices"""
        if type(indsfile) is str:
            inds = loadmat(indsfile)['inds'][0]
        else:
            inds = indsfile
        self.inds = inds
        self.n = len(inds)


class CrossCorrMethod(SigProcessingMethod):
    """class for computing lagged cross correlations"""

    def __init__(self, sigfile, lag):
        """load parameters. paramfile can be an array, or a string
        if its a string, assumes signal is a MAT file
        with name modelfile_X
        """
        if type(sigfile) is str:
            x = loadmat(sigfile + "_X.mat")['X'][0]
        else:
            x = sigfile
        x = x - mean(x)
        x = x / norm(x)

        if lag is not 0:
            shifts = range(-lag, lag+1)
            d = len(x)
            m = len(shifts)
            x_shifted = zeros((m, d))
            for ix in range(0, len(shifts)):
                tmp = roll(x, shifts[ix])
                if shifts[ix] < 0:  # zero padding
                    tmp[(d+shifts[ix]):] = 0
                if shifts[ix] > 0:
                    tmp[:shifts[ix]] = 0
                x_shifted[ix, :] = tmp
            self.x = x_shifted
        else:
            self.x = x

    def get(self, y):
        """compute cross correlation between y and x"""

        y = y - mean(y)
        n = norm(y)
        if n == 0:
            b = zeros((shape(self.x)[0],))
        else:
            y /= norm(y)
            b = dot(self.x, y)
        return b


SIGPROCESSING_METHODS = {
    'stats': StatsMethod,
    'fourier': FourierMethod,
    'crosscorr': CrossCorrMethod,
    'query': QueryMethod
}
########NEW FILE########
__FILENAME__ = load
"""
Utilities for loading and preprocessing data
"""

import pyspark

from numpy import array, mean, cumprod, append, mod, ceil, size, polyfit, polyval, arange, percentile, inf, subtract
from scipy.signal import butter, lfilter


class Dimensions(object):

    def __init__(self, values=[], n=3):
        self.min = tuple(map(lambda i: inf, range(0, n)))
        self.max = tuple(map(lambda i: -inf, range(0, n)))

        for v in values:
            self.merge(v)

    def merge(self, value):
        self.min = tuple(map(min, self.min, value))
        self.max = tuple(map(max, self.max, value))
        return self

    def count(self):
        return tuple(map(lambda x: x + 1, map(subtract, self.max, self.min)))

    def mergedims(self, other):
        self.min = tuple(map(min, self.min, other.min))
        self.max = tuple(map(max, self.max, other.max))
        return self


class DataLoader(object):
    """Class for loading lines of a data file"""

    def __init__(self, nkeys):
        def func(line):
            vec = [float(x) for x in line.split(' ')]
            ts = array(vec[nkeys:])
            keys = tuple(int(x) for x in vec[:nkeys])
            return keys, ts

        self.func = func

    def get(self, y):
        return self.func(y)


class DataPreProcessor(object):
    """Class for preprocessing data"""

    def __init__(self, preprocessmethod):
        if preprocessmethod == "sub":
            func = lambda y: y - mean(y)

        if preprocessmethod == "dff":
            def func(y):
                mnval = mean(y)
                return (y - mnval) / (mnval + 0.1)

        if preprocessmethod == "raw":
            func = lambda x: x

        if preprocessmethod == "dff-percentile":

            def func(y):
                mnval = percentile(y, 20)
                y = (y - mnval) / (mnval + 0.1)   
                return y

        if preprocessmethod == "dff-detrend":

            def func(y):
                mnval = mean(y)
                y = (y - mnval) / (mnval + 0.1)   
                x = arange(1, len(y)+1) 
                p = polyfit(x, y, 1)
                yy = polyval(p, x)
                return y - yy

        if preprocessmethod == "dff-detrendnonlin":

            def func(y):
                mnval = mean(y)
                y = (y - mnval) / (mnval + 0.1)   
                x = arange(1, len(y)+1) 
                p = polyfit(x, y, 5)
                yy = polyval(p, x)
                return y - yy

        if preprocessmethod == "dff-highpass":
            fs = 1
            nyq = 0.5 * fs
            cutoff = (1.0/360) / nyq
            b, a = butter(6, cutoff, "highpass")

            def func(y):
                mnval = mean(y)
                y = (y - mnval) / (mnval + 0.1)
                return lfilter(b, a, y)

        self.func = func

    def get(self, y):
        return self.func(y)


def isrdd(data):
    """ Check whether data is an RDD or not
    :param data: data object (potentially an RDD)
    :return: true (is rdd) or false (is not rdd)
    """
    dtype = type(data)
    if (dtype == pyspark.rdd.RDD) | (dtype == pyspark.rdd.PipelinedRDD):
        return True
    else:
        return False


def getdims(data):
    """Get dimensions of keys; ranges can have arbtirary minima
    and maximum, but they must be contiguous (e.g. the indices of a dense matrix).

    :param data: RDD of data points as key value pairs, or numpy list of key-value tuples
    :return dims: Instantiation of Dimensions class containing the dimensions of the data
    """

    def redfunc(left, right):
        return left.mergedims(right)

    if isrdd(data):
        entry = data.first()[0]
        n = size(entry)
        d = data.map(lambda (k, _): k).mapPartitions(lambda i: [Dimensions(i, n)]).reduce(redfunc)
    else:
        entry = data[0][0]
        rng = range(0, size(entry))
        d = Dimensions()
        if size(entry) == 1:
            distinctvals = list(set(map(lambda x: x[0][0], data)))
        else:
            distinctvals = map(lambda i: list(set(map(lambda x: x[0][i], data))), rng)
        d.max = tuple(map(max, distinctvals))
        d.min = tuple(map(min, distinctvals))

    return d


def subtoind(data, dims):
    """Convert subscript indexing to linear indexing

    :param data: RDD with subscript indices as keys
    :param dims: Array with maximum along each dimension
    :return RDD with linear indices as keys
    """
    def subtoind_inline(k, dimprod):
        return sum(map(lambda (x, y): (x - 1) * y, zip(k[1:], dimprod))) + k[0]
    if size(dims) > 1:
        dimprod = cumprod(dims)[0:-1]
        if isrdd(data):
            return data.map(lambda (k, v): (subtoind_inline(k, dimprod), v))
        else:
            return map(lambda (k, v): (subtoind_inline(k, dimprod), v), data)
    else:
        return data


def indtosub(data, dims):
    """Convert linear indexing to subscript indexing

    :param data: RDD with linear indices as keys
    :param dims: Array with maximum along each dimension
    :return RDD with sub indices as keys
    """
    def indtosub_inline(k, dimprod):
        return tuple(map(lambda (x, y): int(mod(ceil(float(k)/y) - 1, x) + 1), dimprod))

    if size(dims) > 1:
        dimprod = zip(dims, append(1, cumprod(dims)[0:-1]))
        if isrdd(data):
            return data.map(lambda (k, v): (indtosub_inline(k, dimprod), v))
        else:
            return map(lambda (k, v): (indtosub_inline(k, dimprod), v), data)

    else:
        return data


def load(sc, datafile, preprocessmethod="raw", nkeys=3):
    """Load data from a text file with format
    <k1> <k2> ... <t1> <t2> ...
    where <k1> <k2> ... are keys (Int) and <t1> <t2> ... are the data values (Double)
    If multiple keys are provided (e.g. x, y, z), they are converted to linear indexing

    :param sc: SparkContext
    :param datafile: Location of raw data
    :param preprocessmethod: Type of preprocessing to perform ("raw", "dff", "sub")
    :param nkeys: Number of keys per data point
    :return data: RDD of data points as key value pairs
    """

    lines = sc.textFile(datafile)
    loader = DataLoader(nkeys)

    data = lines.map(loader.get)

    if preprocessmethod != "raw":
        preprocessor = DataPreProcessor(preprocessmethod)
        data = data.mapValues(preprocessor.get)

    return data



########NEW FILE########
__FILENAME__ = matrixrdd
"""
class for doing matrix operations on RDDs of (int, ndarray) pairs
(experimental!)

TODO: right divide and left divide
TODO: common operation is multiplying an RDD by its transpose times a matrix, how do this cleanly?
TODO: test using these in the various analyses packages (especially thunder.factorization)
"""

import sys
from numpy import dot, allclose, outer, shape, ndarray, mean, add, subtract, multiply, zeros, std, divide
from pyspark.accumulators import AccumulatorParam


def matrixsum_iterator_self(iterator):
    yield sum(outer(x, x) for x in iterator)


def matrixsum_iterator_other(iterator):
    yield sum(outer(x, y) for x, y in iterator)


class MatrixAccumulatorParam(AccumulatorParam):
    def zero(self, value):
        return zeros(shape(value))

    def addInPlace(self, val1, val2):
        val1 += val2
        return val1


class MatrixRDD(object):
    def __init__(self, rdd, n=None, d=None):
        self.rdd = rdd
        if n is None:
            self.n = rdd.count()
        else:
            self.n = n
        if d is None:
            vec = rdd.first()[1]
            if type(vec) is ndarray:
                self.d = len(vec)
            else:
                self.d = 1
        else:
            self.d = d

    def collect(self):
        """
        collect the rows of the matrix
        """
        return self.rdd.map(lambda (k, v): v).collect()

    def first(self):
        """
        get the first row of the matrix
        """
        return self.rdd.first()[1]

    def cov(self, axis=None):
        """
        compute a covariance matrix

        arguments:
        axis - axis for mean subtraction, 0 (rows) or 1 (columns)
        """
        if axis is None:
            return self.outer() / self.n
        else:
            return self.center(axis).outer() / self.n

    def outer(self, method="reduce"):
        """
        compute outer product of the MatrixRDD with itself

        arguments:
        method - "reduce" (use a reducer) or "accum" (use an accumulator)
        """
        if method is "reduce":
            return self.rdd.map(lambda (k, v): v).mapPartitions(matrixsum_iterator_self).sum()
        if method is "accum":
            global mat
            mat = self.rdd.context.accumulator(zeros((self.d, self.d)), MatrixAccumulatorParam())

            def outerSum(x):
                global mat
                mat += outer(x, x)
            self.rdd.map(lambda (k, v): v).foreach(outerSum)
            return mat.value
        else:
            raise Exception("method must be reduce or accum")

    def times(self, other, method="reduce"):
        """
        Multiply a MatrixRDD by another matrix

        arguments:
        other - MatrixRDD, scalar, or numpy array
        method - "reduce" (use a reducer) or "accum" (use an accumulator)
        """
        dtype = type(other)
        if dtype == MatrixRDD:
            if self.n != other.n:
                raise Exception(
                    "cannot multiply shapes ("+str(self.n)+","+str(self.d)+") and ("+str(other.n)+","+str(other.d)+")")
            else:
                if method is "reduce":
                    return self.rdd.join(other.rdd).map(lambda (k, v): v).mapPartitions(matrixsum_iterator_other).sum()
                if method is "accum":
                    global mat
                    mat = self.rdd.context.accumulator(zeros((self.d, other.d)), MatrixAccumulatorParam())

                    def outerSum(x):
                        global mat
                        mat += outer(x[0], x[1])
                    self.rdd.join(other.rdd).map(lambda (k, v): v).foreach(outerSum)
                    return mat.value
                else:
                    raise Exception("method must be reduce or accum")
        else:
            # TODO: check size of array, broadcast if too big
            if dtype == ndarray:
                dims = shape(other)
                if (len(dims) == 1 and sum(allclose(dims, self.d) == 0)) or (len(dims) == 2 and dims[0] != self.d):
                    raise Exception(
                        "cannot multiply shapes ("+str(self.n)+","+str(self.d)+") and " + str(dims))
                if len(dims) == 0:
                    new_d = 1
                else:
                    new_d = dims[0]
            return MatrixRDD(self.rdd.mapValues(lambda x: dot(x, other)), self.n, new_d)

    def elementwise(self, other, op):
        """
        apply elementwise operation to a MatrixRDD

        arguments:
        other - MatrixRDD, scalar, or numpy array
        op - binary operator, e.g. add, subtract
        """
        dtype = type(other)
        if dtype is MatrixRDD:
            if (self.n is not other.n) | (self.d is not other.d):
                print >> sys.stderr, \
                    "cannot do elementwise operation for shapes ("+self.n+","+self.d+") and ("+other.n+","+other.d+")"
            else:
                return MatrixRDD(self.rdd.join(other.rdd).mapValues(lambda (x, y): op(x, y)), self.n, self.d)
        else:
            if dtype is ndarray:
                dims = shape(other)
                if len(dims) > 1 or dims[0] is not self.d:
                    raise Exception(
                        "cannot do elementwise operation for shapes ("+str(self.n)+","+str(self.d)+") and " + str(dims))
            return MatrixRDD(self.rdd.mapValues(lambda x: op(x, other)), self.n, self.d)

    def plus(self, other):
        """
        elementwise addition (see elementwise)
        """
        return MatrixRDD.elementwise(self, other, add)

    def minus(self, other):
        """
        elementwise subtraction (see elementwise)
        """
        return MatrixRDD.elementwise(self, other, subtract)

    def dottimes(self, other):
        """
        elementwise multiplcation (see elementwise)
        """
        return MatrixRDD.elementwise(self, other, multiply)

    def dotdivide(self, other):
        """
        elementwise division (see elementwise)
        """
        return MatrixRDD.elementwise(self, other, divide)

    def center(self, axis=0):
        """
        center a MatrixRDD by mean subtraction

        arguments:
        axis - center rows (0) or columns (1)
        """
        if axis is 0:
            return MatrixRDD(self.rdd.mapValues(lambda x: x - mean(x)), self.n, self.d)
        if axis is 1:
            meanVec = self.rdd.map(lambda (k, v): v).mean()
            return self.minus(meanVec)
        else:
            raise Exception("axis must be 0 or 1")

    def zscore(self, axis=0):
        """
        zscore a MatrixRDD by mean subtraction and division by standard deviation

        arguments:
        axis - center rows (0) or columns (1)
        """
        if axis is 0:
            return MatrixRDD(self.rdd.mapValues(lambda x: (x - mean(x))/std(x)), self.n, self.d)
        if axis is 1:
            meanvec = self.rdd.map(lambda (k, v): v).mean()
            stdvec = self.rdd.map(lambda (k, v): v).std()
            return self.minus(meanvec).dotdivide(stdvec)
        else:
            raise Exception("axis must be 0 or 1")


########NEW FILE########
__FILENAME__ = save
"""
Utilities for saving data
"""

import os
from scipy.io import savemat
from math import isnan
from numpy import array, squeeze, sum, shape, reshape, transpose, maximum, minimum, float16, uint8, savetxt, size
from PIL import Image

from thunder.util.load import getdims, subtoind, isrdd


def arraytoim(mat, filename, format="tif"):
    """Write a numpy array to a png image

    If mat is 3D will separately write each image
    along the 3rd dimension

    :param mat: Numpy array, 2d or 3d, dtype must be uint8
    :param filename: Base filename for writing
    :param format: Image format to write, default="tif" (see PIL for options)
    """
    dims = shape(mat)
    if len(dims) > 2:
        for z in range(0, dims[2]):
            cdata = mat[:, :, z]
            Image.fromarray(cdata).save(filename+"-"+str(z)+"."+format)
    elif len(dims) == 2:
        Image.fromarray(mat).save(filename+"."+format)
    else:
        raise NotImplementedError('array must be 2 or 3 dimensions for image writing')


def rescale(data):
    """Rescale data to lie between 0 and 255 and convert to uint8

    For strictly positive data, subtract the min and divide by max
    otherwise, divide by the maximum absolute value and center

    If each element of data has multiple entries,
    they will be rescaled separately

    :param data: RDD of (Int, Array(Double)) pairs
    """
    if size(data.first()[1]) > 1:
        data = data.mapValues(lambda x: map(lambda y: 0 if isnan(y) else y, x))
    else:
        data = data.mapValues(lambda x: 0 if isnan(x) else x)
    mnvals = data.map(lambda (_, v): v).reduce(minimum)
    mxvals = data.map(lambda (_, v): v).reduce(maximum)
    if sum(mnvals < 0) == 0:
        data = data.mapValues(lambda x: uint8(255 * (x - mnvals)/(mxvals - mnvals)))
    else:
        mxvals = maximum(abs(mxvals), abs(mnvals))
        data = data.mapValues(lambda x: uint8(255 * ((x / (2 * mxvals)) + 0.5)))
    return data


def save(data, outputdir, outputfile, outputformat):
    """
    Save data to a variety of formats
    Automatically determines whether data is an array
    or an RDD and handles appropriately
    For RDDs, data are sorted and reshaped based on the keys

    :param data: RDD of key value pairs or array
    :param outputdir: Location to save data to
    :param outputfile: file name to save data to
    :param outputformat: format for data ("matlab", "text", or "image")
    """

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    filename = os.path.join(outputdir, outputfile)

    if (outputformat == "matlab") | (outputformat == "text"):
        if isrdd(data):
            dims = getdims(data)
            data = subtoind(data, dims.max)
            keys = data.map(lambda (k, _): int(k)).collect()
            nout = size(data.first()[1])
            if nout > 1:
                for iout in range(0, nout):
                    result = data.map(lambda (_, v): float16(v[iout])).collect()
                    result = array([v for (k, v) in sorted(zip(keys, result), key=lambda (k, v): k)])
                    if outputformat == "matlab":
                        savemat(filename+"-"+str(iout)+".mat",
                                mdict={outputfile+str(iout): squeeze(transpose(reshape(result, dims.count()[::-1])))},
                                oned_as='column', do_compression='true')
                    if outputformat == "text":
                        savetxt(filename+"-"+str(iout)+".txt", result, fmt="%.6f")
            else:
                result = data.map(lambda (_, v): float16(v)).collect()
                result = array([v for (k, v) in sorted(zip(keys, result), key=lambda (k, v): k)])
                if outputformat == "matlab":
                    savemat(filename+".mat", mdict={outputfile: squeeze(transpose(reshape(result, dims.count()[::-1])))},
                            oned_as='column', do_compression='true')
                if outputformat == "text":
                    savetxt(filename+".txt", result, fmt="%.6f")

        else:
            if outputformat == "matlab":
                savemat(filename+".mat", mdict={outputfile: data}, oned_as='column', do_compression='true')
            if outputformat == "text":
                savetxt(filename+".txt", data, fmt="%.6f")

    if outputformat == "image":

        if isrdd(data):
            data = rescale(data)
            dims = getdims(data)
            data = subtoind(data, dims.max)
            keys = data.map(lambda (k, _): int(k)).collect()
            nout = size(data.first()[1])
            if nout > 1:
                for iout in range(0, nout):
                    result = data.map(lambda (_, v): v[iout]).collect()
                    result = array([v for (k, v) in sorted(zip(keys, result), key=lambda (k, v): k)])
                    arraytoim(squeeze(transpose(reshape(result, dims.count()[::-1]))), filename+"-"+str(iout))
            else:
                result = data.map(lambda (_, v): v).collect()
                result = array([v for (k, v) in sorted(zip(keys, result), key=lambda (k, v): k)])
                arraytoim(squeeze(transpose(reshape(result, dims.count()[::-1]))), filename)
        else:
            arraytoim(data, filename)




########NEW FILE########
