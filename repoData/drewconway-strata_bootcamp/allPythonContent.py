__FILENAME__ = create_instances
#!/usr/bin/env python

import boto
import sys
import os
from os.path import expanduser
from time import sleep

if __name__=='__main__':

    if len(sys.argv) == 1:
        print "usage:" , sys.argv[0] , "<ami> <keypair> <n>"
        sys.exit(1)

    ami = sys.argv[1]
    keypair = sys.argv[2]
    num_instances = sys.argv[3]

    f = open('%s/.awssecret' % expanduser('~'), 'r')
    AWS_KEY = f.readline().strip()
    AWS_SECRET = f.readline().strip()
    f.close()

    print AWS_KEY
    print AWS_SECRET

    print "connecting to ec2"
    ec2_conn = boto.connect_ec2(AWS_KEY, AWS_SECRET)

    print "getting image", ami
    images = ec2_conn.get_all_images(image_ids=[ami])

    print "requesting", num_instances , "instance(s)"
    rsrv = images[0].run(1, num_instances, keypair)

    f = open('instances','w')
    pending = list(rsrv.instances)
    running = []
    configured = []
    while len(configured) < len(rsrv.instances):

        print "pending:" , pending
        print "running:" , running
        print "configured: " , configured
        for instance in rsrv.instances:

            print "checking" , instance.id
            instance.update()

            if instance.state == 'running':
                if instance not in running:
                    print instance.id , "is up at" , instance.dns_name
                    f.write('%s %s\n' % (instance.id, instance.dns_name))
                    pending.remove(instance)
                    running.append(instance)
            else:
                print "still pending"
                
            if (instance in running) and (instance not in configured):
                print "configuring" , instance.id
                cmd="ssh -o StrictHostKeyChecking=no -i ~/.ec2/*-%s ubuntu@%s 'hostname'" % (keypair, instance.dns_name)
                status = os.system(cmd)

                if status == 0:
                    cmd="cat setup | ssh -o StrictHostKeyChecking=no -i ~/.ec2/*-%s ubuntu@%s &> %s.log &" % (keypair, instance.dns_name, instance.id)
                    print cmd
                    status = os.system(cmd)

                    configured.append(instance)
                else:
                    print "configuration failed"

        print "sleeping"
        sleep(10)

    f.close()

########NEW FILE########
__FILENAME__ = classify_digits
#!/usr/bin/env python

import scipy as sp
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from digits import *
from knn import *
from mltools import *


if __name__=='__main__':

    # set seed so we all see the same random numbers
    sp.random.seed(20110201)

    # read digit data
    X, y = read_digits()

    # generate a random train/test split
    Xtrain, ytrain, Xtest, ytest = train_test_split(X, y, 0.8)
    del X, y

    # build nearest-neighbors classifier on training data
    classifier = KNN()
    classifier.add_examples(Xtrain, ytrain)
    classifier.train()

    # generate predictions for test data
    print "classifying test examples"
    ypred = classifier.predict(Xtest, k=1)

    # compute confusion matrix 
    confmat = accumarray( ytest, ypred )
    acc = confmat.diagonal().sum() / confmat.sum()
    print "confusion matrix:"
    print confmat
    print "accuracy:" , acc
    # accuracy directly:
    # print sp.mean( sp.around(ypred) == ytest )

    # generate heatmap of confusion matrix
    plt.imshow(confmat, interpolation='nearest')
    #plt.imshow(sp.log10(confmat+1), cmap=cm.hot, interpolation='nearest')
    plt.xlabel('actual')
    plt.ylabel('predicted')
    plt.colorbar()

    # save confusion matrix image
    print "saving digits_confmat.png"
    plt.savefig('digits_confmat.png')
    #plt.show()

########NEW FILE########
__FILENAME__ = classify_flickr
#!/usr/bin/env python

import sys
import os.path
import scipy as sp
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from scipy.cluster.vq import whiten

from imgtools import *
from mltools import *
from knn import *

if __name__=='__main__':

    # default to classifying headshots vs landscapes
    bins = 16
    K = 9
    dirs = ['flickr_headshot','flickr_landscape']
    
    # take bins, number of neighbors, and image directories from command line
    try:
        bins = int(sys.argv[1])
        K = int(sys.argv[2])
        dirs = sys.argv[3:]
    except:
        pass

    print "using 3*%d bins for image intensity features" % bins

    # load images from each directory
    images = []
    for d, directory in enumerate(dirs):
        imagesd = read_image_dir(directory, '*.jpg')

        Xd = sp.array( [rgb_features(I, bins) for I in imagesd] )

        # create vector of labels
        yd = d*sp.ones(Xd.shape[0])

        try:
            # append digits and labels to X and y, respectively
            X = sp.vstack((X, Xd))
            y = sp.concatenate((y, yd))
        except NameError:
            # create X and y if they don't exist
            X = Xd
            y = yd

        images.append(imagesd)


    # set seed so we all see the same random numbers
    sp.random.seed(20110201)

    # generate a random train/test split
    Xtrain, ytrain, Xtest, ytest = train_test_split(X, y, 0.8)
    del X, y

    # normalize training features
    Xtrain = whiten(Xtrain)

    # "build" k-nearest neighbors classifier on training data
    print "building k-nearest neighbors classifier"
    classifier = KNN()
    classifier.add_examples(Xtrain, ytrain)
    classifier.train()

    # normalize test features
    Xtest = whiten(Xtest)

    Ks = range(1,K+1,2)
    accuracy = []
    for k in Ks:
        # generate predictions for test data
        ypred = classifier.predict(Xtest, k)

        # compute confusion matrix 
        confmat = accumarray( ytest, ypred )
        acc = confmat.diagonal().sum() / confmat.sum()
        print "k = %d, accuracy = %.4f" % (k,acc)

        accuracy.append(acc)

    plt.plot(Ks, accuracy, 'x--')
    plt.show()
    plt.xlabel('neighbors')
    plt.ylabel('accuracy')

########NEW FILE########
__FILENAME__ = cluster_flickr
#!/usr/bin/env python

import scipy as sp
import scipy.cluster.vq as spvq
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import glob
from math import sqrt, ceil

from imgtools import *

def plot_montage(images, ndx, ncol=None):

    N = len(ndx)
    
    if not ncol:
        ncol = int(sqrt(N))

    f = plt.figure(dpi=100)
    
    row = 0
    col = 0
    tot_height = 0
    for i in range(N):

        I = sp.array(images[ndx[i]], dtype='float')
        I = I / I.max()
        
        height = I.shape[0]
        width = I.shape[1]
        ax = plt.figimage(I, xo=width*col, yo=height*row, origin='lower')

        col += 1
        if col % ncol == 0:
            row += 1
            col = 0
            tot_height += height

    tot_height += height
    tot_width = width*ncol
    
    f.set_figheight(tot_height/100)
    f.set_figwidth(tot_width/100)

    return f

if __name__=='__main__':

    if len(sys.argv) == 4:
        # take image directory, number of clusters, bins from command line
        directory = sys.argv[1]
        K = int(sys.argv[2])
        bins = int(sys.argv[3])
    else:
        # default to pictures tagged with 'vivid', 3 clusters, 10 bins
        directory = 'flickr_vivid'
        K = 7
        bins = 10
    
    # read images
    images = read_image_dir(directory, '*.jpg')
    N = len(images)

    # generate bag-of-pixels features
    X = sp.zeros( (N,3*bins) )
    for i, image in enumerate(images):
        X[i,:] = rgb_features(image, bins)
    # normalize features
    X = spvq.whiten(X)

    # set seed so we all see the same random numbers
    sp.random.seed(20110201)

    # run k-means
    centers, err = spvq.kmeans(X, K)
    # get cluster assignments for each image
    assignments, err = spvq.vq(X, centers)

    # plot images in each cluster
    for k in range(K):
        # index of images in this cluster
        ndx = sp.where(assignments == k)

        # plot montage
        f = plot_montage(images, ndx[0], 20)

        # save figure
        fname = '%s_cluster_%d.png' % (directory, k)
        print "saving" , fname
        plt.savefig(fname)
        del(f)

    # montage of random selection of images, for comparison
    ndx = sp.random.randint(0, N, 80)
    plot_montage(images, ndx, 20)
    fname = '%s_sample.png' % directory
    print "saving", fname
    plt.savefig(fname)

########NEW FILE########
__FILENAME__ = cluster_pixels
#!/usr/bin/env python

import sys
import os.path
import scipy as sp
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import scipy.cluster.vq as spvq
import matplotlib.cm as cm
from mpl_toolkits.mplot3d import Axes3D

if __name__=='__main__':
    if len(sys.argv) == 3:
        # take image filename and number of clusters from command line
        fname = sys.argv[1]
        K = int(sys.argv[2])
    else:
        # default to picture of candy
        fname = 'candy.jpg'

        # number of clusters
        K = 7

        if not os.path.exists(fname):
            # download the image from flickr if missing
            from urllib import urlretrieve
            print "downloading http://www.flickr.com/photos/minebilder/68826730/ to" , fname
            urlretrieve('http://farm1.static.flickr.com/35/68826730_a6556f07cf_s_d.jpg', filename='candy.jpg')


    # read image
    I = mpimg.imread(fname)
    # each pixel is an example, with with (r,g,b) values as the feature vector
    X = sp.reshape(I, (-1,3), order='F')

    # set seed so we all see the same random numbers
    sp.random.seed(20110201)

    # run k-means
    centers, err = spvq.kmeans(X, K)
    # get cluster assignments for each pixel
    assignments, err = spvq.vq(X, centers)
    Z = centers[assignments]

    # begin 3-panel plot

    # plot original image on the left
    plt.subplot(131)
    plt.imshow(I, cmap=cm.gray, interpolation='nearest', origin='lower')


    # NOTE: if you are using a version of matplotlib < 1.0 you will
    # either need to upgrade to the newest version, or use the fix
    # suggested here: http://stackoverflow.com/questions/3810865/need-help-with-matplotlib

    # plot clustered pixels in rgb space in the center
    ax = plt.subplot(132, projection='3d', aspect='equal')
    #ax.view_init(30, 135)
    #colors = assignments
    colors = sp.array(Z, dtype='float') / 255
    ax.scatter(X[:,0], X[:,1], X[:,2], color=colors, alpha=0.25)
    ax.set_xlabel('R')
    ax.set_ylabel('G')
    ax.set_zlabel('B')

    # plot compressed image on the right
    plt.subplot(133)
    Icomp = sp.reshape(Z, I.shape, order='F')
    plt.imshow(Icomp, interpolation='nearest', origin='lower')

    # redraw to fix bug in center panel
    plt.draw()

    # save 3-panel plot
    base, ext = os.path.splitext(fname)
    fname = '%s_clustered.png' % base
    print "saving" , fname
    plt.savefig(fname, bbox_inches='tight')

########NEW FILE########
__FILENAME__ = digits
#!/usr/bin/env python

import scipy as sp
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.image as image

# image width
IM_WIDTH=16

def read_digits(dir='digits'):
    """
    read all example digits return a matrix X, where each row is the
    (flattened) pixels of an example digit and a vector y, where each
    entry gives the digit as an integer
    """
    
    for d in range(10):
        fname = '%s/train.%d' % (dir, d)

        print "reading" , fname

        # read digits from train.d
        Xd = sp.loadtxt(fname, delimiter=',')

        # create vector of labels
        yd = d*sp.ones(Xd.shape[0])

        try:
            # append digits and labels to X and y, respectively
            X = sp.vstack((X, Xd))
            y = sp.concatenate((y, yd))
        except UnboundLocalError:
            # create X and y if they don't exist
            X = Xd
            y = yd
            
    return X, y


def reshape_digit(X, i, width=IM_WIDTH):
    """
    reshape the i-th example (row of X) to a 2d array
    """
    return X[i,:].reshape(-1,width)

def plot_digit(X, i, width=IM_WIDTH):
    """
    plot the i-th example (row of X) as an image
    """

    I = reshape_digit(X, i, width)
    plt.imshow(I, cmap=cm.gray, interpolation='nearest')


def save_digit(X, i, fname, width=IM_WIDTH):
    """
    save the i-th example (row of X) to a file
    """

    plt.imsave(fname, reshape_digit(X, i, width), cmap=cm.gray)

def plot_digits(X, ndx, ncol=50, width=IM_WIDTH, cmap=cm.gray):
    """
    plot a montage of the examples specified in ndx (as rows of X)
    """

    row = 0
    col = 0
    for i in range(ndx.shape[0]):
        
        plt.figimage(reshape_digit(X, ndx[i]),
                     xo=width*col, yo=width*row,
                     origin='upper', cmap=cmap)

        col += 1
        if col % ncol == 0:
            row += 1
            col = 0

            
if __name__=='__main__':

    # read digits
    X, y = read_digits()

    # number of example digits
    N = y.shape[0]

    # set seed so we all see the same random data
    sp.random.seed(20110201)

    # save a random digit to sample_digit.png
    i = sp.random.randint(N)
    print "saving sample_digit.png"
    save_digit(X, i, 'sample_digit.png')

    # save a montage of random digits to a sample_digits.png
    ndx = sp.random.randint(0, N, 2000)
    plot_digits(X, ndx)
    print "saving sample_digits.png"
    plt.savefig('sample_digits.png')

    #plt.show()


########NEW FILE########
__FILENAME__ = download_flickr
#!/usr/bin/env python

from simpleyql import *
import simplejson as json
from urllib import urlretrieve
import os

def photo_url(photo, size='s'):
    url = "http://farm%s.static.flickr.com/%s/%s_%s_%s.jpg" % (photo['farm'],
                                                               photo['server'],
                                                               photo['id'],
                                                               photo['secret'],
                                                               size)    
    return url

if __name__=='__main__':

    if len(sys.argv) == 3:
        # take tags and number of images from command line
        tags = sys.argv[1]
        n = int(sys.argv[2])
    else:
        # default to 500 pictures tagged with 'vivid'
        tags = 'vivid'
        n = 500

    # grab the top-n most interesting photos tagged with 'tags'
    query = '''select * from flickr.photos.search(%d) where
    tags="%s" and sort="interestingness-desc"
    ''' % (n, tags)

    # make yql call
    print "fetching %d photos tagged with %s from flickr" % (n, tags)
    results = yql_public(query)

    # create output directory if it doesn't exist
    directory = 'flickr_%s' % tags
    if not os.path.exists(directory):
        print "creating directory %s" % directory
        os.mkdir(directory)

    # run over results
    print "downloading %d results" % len(results['photo'])
    for photo in results['photo']:
        # build url of square image
        square_url = photo_url(photo)

        # download square image
        fname = '%s/%s.jpg' % (directory, photo['id'])
        if not os.path.exists(fname):
            print square_url , "->" , fname
            urlretrieve(square_url, filename=fname)

########NEW FILE########
__FILENAME__ = imgtools
#!/usr/bin/env python

import scipy as sp
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import sys
import os.path
import glob

def rgb_hist(I, ax, bins=256):

    # run over red, green, and blue channels
    channels = ('r','g','b')
    for i, color in enumerate(channels):
        # get count pixel intensities for this channel
        counts, bins, patches = plt.hist(I[:,:,i].flatten(), bins=bins, normed=True, visible=False)

        # hack: choose mid-point of bins as centers
        centers = bins[:-1] + sp.diff(bins)/2

        # line plot with fill
        plt.plot(centers, counts, color=color)
        ax.fill_between(centers, 0, counts, color=color, alpha=0.25)

    # hack for matlab's axes('square') function
    # http://www.mail-archive.com/matplotlib-users@lists.sourceforge.net/msg08388.html
    plt.axis('tight')
    ax.set_aspect(1./ax.get_data_ratio())


def imshow_hist(I, bins=256):

    f = plt.figure()

    # show image in left panel
    plt.subplot(121)
    plt.imshow(I, origin='lower')

    # show histogram in right panel
    ax = plt.subplot(122)
    rgb_hist(I, ax, bins)

    return f


def rgb_features(I, bins=10):

    x = sp.array([])

    # run over red, green, and blue channels
    channels = ('r','g','b')
    for i, color in enumerate(channels):
        # get count pixel intensities for this channel
        counts, bins = sp.histogram(I[:,:,i].flatten(), bins=bins)

        x = sp.concatenate( (x, counts) )

    return x


def read_image_dir(directory, pattern='*.jpg'):
    # glob for image files
    fnames = glob.glob('%s/%s' % (directory, pattern))
    N = len(fnames)

    # read images 
    print "reading %d image files from %s" % (N, directory)
    images = []
    for i, fname in enumerate(fnames):
        try:
            I = mpimg.imread(fname)
            images.append(I)            
        except IOError:
            print "error reading" , fname

        # show progress
        if i % int(N/10) == 0:
            print "%d/%d images read" % (i,N)

    return images


if __name__=='__main__':

    if len(sys.argv) == 3:
        # take image filename and number of bins from command line
        fname = sys.argv[1]
        bins = int(sys.argv[2])
    else:
        # default to picture of chairs
        fname = 'chairs.jpg'
        bins = 64

        # download the image from flickr if missing
        if not os.path.exists(fname):
            from urllib import urlretrieve
            print "downloading http://www.flickr.com/photos/dcdead/4871475924/ to" , fname
            urlretrieve('http://farm5.static.flickr.com/4097/4871475924_dcc135dd8f_b_d.jpg', filename='chairs.jpg')

    # load the image
    I = mpimg.imread(fname)

    # display with a histogram
    imshow_hist(I, bins)

    # save figure
    base, ext = os.path.splitext(fname)
    fname = '%s_%d.png' % (base, bins)
    print "saving" , fname
    plt.savefig(fname, bbox_inches='tight')

########NEW FILE########
__FILENAME__ = knn
#!/usr/bin/env python

import scipy as sp
import scipy.spatial as spat
import matplotlib.pyplot as plt
from scipy.stats import mode

class KNN():

    def __init__(self, X=None, y=None):
        if X and y:
            # add training data if provided
            self.add_examples(X, y)

    def add_examples(self, X, y):
        # memorize training data
        try:
            self.X = sp.vstack((self.X, X))
            self.y = sp.concatenate((self.y, y))
        except AttributeError:
            self.X = X
            self.y = y
            
    def train(self):
        # do nothing
        return
    
    def predict(self, X, k=1):
        # coerce test examples to be N-by-2 scipy array
        X = sp.array(X, ndmin=2)
        # number of test examples
        N = X.shape[0]

        # create empty vector for predictions
        yhat = sp.zeros(N)

        # use the cdist function to quickly compute distances
        # between all test and training examples
        D = spat.distance.cdist(X, self.X, 'euclidean')

        for i in range(N):
            # grab the indices of the k closest points
            ndx = D[i,:].argsort()[:k]

            # take a majority vote over the nearest points' labels
            yhat[i] = mode(self.y[ndx])[0]
            
        return yhat

class KNNKDTree(KNN):

    def train(self):
        # build kd-tree for quick lookup
        self.kdtree = spat.KDTree(self.X)
        
    def predict(self, X, k=1):
        # coerce test examples to be N-by-2 scipy array
        X = sp.array(X, ndmin=2)
        # number of test examples
        N = X.shape[0]

        # create empty vector for predictions
        yhat = sp.zeros(N)

        # use the kd-tree query function to quickly lookup nearest
        # neighbors
        D, ndx = self.kdtree.query(X, k=k)
        for i in range(N):
            # take a majority vote over the nearest points' labels
            yhat[i] = mode(self.y[ndx])[0]

        return yhat


if __name__=='__main__':
    # number of examples (N) and dimensions (D)
    N = 100
    D = 2

    # set seed so we all see the same random data
    sp.random.seed(20110201)

    # todo: help functions for synthetic data

    # generate N examples from class "0" and
    # N examples from class "1"
    # from normal distributions with different means
    y = sp.concatenate( (sp.zeros(N),
                         sp.ones(N)) )
    X = sp.vstack( (sp.random.randn(N,D) + [1, 1],
                    sp.random.randn(N,D) - [1, 1]) )

    # plot training data
    ndx = sp.where(y == 0)
    plt.plot(X[ndx,0], X[ndx,1], 'rx', alpha=0.25)
    ndx = sp.where(y == 1)
    plt.plot(X[ndx,0], X[ndx,1], 'bo', alpha=0.25)

    # build and train k-nearest neighbor classifier
    classifier = KNN()
    classifier.add_examples(X, y)
    classifier.train()

    # generate two easy-to-classify test examples
    Xtest = sp.array([[0.75, 0.75],
                      [-0.75, -0.75]])
    ytest = classifier.predict(Xtest, k=3)

    # plot test examples with predicted labels
    ndx = sp.where(ytest == 0)
    plt.plot(Xtest[ndx,0], Xtest[ndx,1], 'rx', alpha=1)
    ndx = sp.where(ytest == 1)
    plt.plot(Xtest[ndx,0], Xtest[ndx,1], 'bo', alpha=1)
    
    plt.show()

########NEW FILE########
__FILENAME__ = mltools
#!/usr/bin/env python

import scipy as sp
from scipy.sparse import coo_matrix

def accumarray(i, j, val=None):
    # hack from http://www.meliza.org/itoaeky/graphics.php?itemid=35
    # to provide functionality similar to matlab's accumarray

    if not val:
        val = sp.ones(len(i))

    return coo_matrix( (val, (i, j)) ).todense()


def train_test_split(X, y, frac=0.8):
    # number of examples
    N = y.shape[0]

    # shuffle example digits
    ndx = sp.random.permutation(N)
    X = X[ndx,:]
    y = y[ndx,:]

    # number of training examples as fraction of total
    Ntrain = int(frac*N)

    # split data into training and test sets
    Xtrain = X[:Ntrain,:]
    ytrain = y[:Ntrain]

    Xtest = X[Ntrain:,:]
    ytest = y[Ntrain:]

    return (Xtrain, ytrain, Xtest, ytest)

########NEW FILE########
__FILENAME__ = simpleyql
#!/usr/bin/env python

from urllib import urlencode
from urllib2 import urlopen
import simplejson as json
import sys

YQL_PUBLIC = 'http://query.yahooapis.com/v1/public/yql'

def yql_public(query):
    # escape query
    query_str = urlencode({'q': query, 'format': 'json'})

    # fetch results
    url = '%s?%s' % (YQL_PUBLIC, query_str)
    result = urlopen(url)

    # parse json and return
    return json.load(result)['query']['results']

if __name__=='__main__':

    if len(sys.argv) == 2:
        # take yql query from first command line argument
        query = sys.argv[1]
    else:
        # default to pictures of kittens
        query = 'select * from flickr.photos.search where tags="kittens" and sort="interestingness-desc" limit 10'

    print query

    # make call to yql
    results = yql_public(query)

    # pretty-print results
    print json.dumps(results, indent=2)


########NEW FILE########
__FILENAME__ = parse_html
#!/usr/bin/env python
# encoding: utf-8
"""
parse_html.py

Created by Hilary Mason on 2011-01-31.
Copyright (c) 2011 Hilary Mason. All rights reserved.
"""

import sys, os
from BeautifulSoup import BeautifulSoup

def main():
    f = open('bootcamp.html', 'r')     # load file
    contents = f.read()
    f.close()
    
    soup = BeautifulSoup(contents) # parse file
    
    description = soup.find(attrs={'class':'en_session_description description'}) # find node
    
    print description.prettify() #explore
    
    print description.text
    
    
if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = email_classify
#!/usr/bin/env python
# encoding: utf-8
"""
email_classify.py

Created by Hilary Mason on 2011-01-30.
Copyright (c) 2011 Hilary Mason. All rights reserved.
"""

import sys, os
import re
import string

from nltk import FreqDist
from nltk.tokenize import word_tokenize

from gmail import Gmail


class emailClassify(object):

    def __init__(self, username, password, folders=['commercial','friends']):
        g = Gmail(username, password)

        # gather data from our e-mail
        msg_data = {}
        for folder_name in folders:
            msg_data[folder_name] = g.get_all_messages_from_folder(folder_name)
		    
        nb = NaiveBayesClassifier()
        nb.train_from_data(msg_data)
        print nb.probability("elephant", 'friends')
        print nb.probability("elephant", 'commercial')
		    

class NaiveBayesClassifier(object):
    
    def __init__(self):
        self.feature_count = {}
        self.category_count = {}
    
    def probability(self, item, category):
        """
        probability: prob that an item is in a category
        """
        category_prob = self.get_category_count(category) / sum(self.category_count.values())
        return self.document_probability(item, category) * category_prob
    
    def document_probability(self, item, category):
        features = self.get_features(item)
        
        p = 1
        for feature in features:
            p *= self.weighted_prob(feature, category)
            
        return p
        
    def train_from_data(self, data):
        for category, documents in data.items():
            for doc in documents:
                self.train(doc, category)
        
        
    def get_features(self, document):
        all_words = word_tokenize(document)
        all_words_freq = FreqDist(all_words)
        
        # print sorted(all_words_freq.items(), key=lambda(w,c):(-c, w))
        return all_words_freq
        
    # def get_features(self, document):
    #     document = re.sub('[%s]' % re.escape(string.punctuation), '', document)
    #     document = document.lower()
    #     all_words = [w for w in word_tokenize(document) if len(w) > 3 and len(w) < 16]
    #     all_words_freq = FreqDist(all_words)
    #     
    #     # print sorted(all_words_freq.items(), key=lambda(w,c):(-c, w))
    #     return all_words_freq
        
    def increment_feature(self, feature, category):
        self.feature_count.setdefault(feature,{})
        self.feature_count[feature].setdefault(category, 0)
        self.feature_count[feature][category] += 1
        
    def increment_cat(self, category):
        self.category_count.setdefault(category, 0)
        self.category_count[category] += 1
        
    def get_feature_count(self, feature, category):
        if feature in self.feature_count and category in self.feature_count[feature]:
            return float(self.feature_count[feature][category])
        else:
            return 0.0
            
    def get_category_count(self, category):
        if category in self.category_count:
            return float(self.category_count[category])
        else:
            return 0.0
    
    def feature_prob(self, f, category): # Pr(A|B)
        if self.get_category_count(category) == 0:
            return 0
        
        return (self.get_feature_count(f, category) / self.get_category_count(category))
        
    def weighted_prob(self, f, category, weight=1.0, ap=0.5):
        basic_prob = self.feature_prob(f, category)
        
        totals = sum([self.get_feature_count(f, category) for category in self.category_count.keys()])
        
        w_prob = ((weight*ap) + (totals * basic_prob)) / (weight + totals)
        return w_prob
            
    def train(self, item, category):
        features = self.get_features(item)
        
        for f in features:
            self.increment_feature(f, category)
        
        self.increment_cat(category)
		
        

if __name__ == '__main__':
    e = emailClassify('ann9enigma@gmail.com', 'stratar0x')
    
    

########NEW FILE########
__FILENAME__ = email_edges
#!/usr/bin/env python
# encoding: utf-8
"""
email_edges.py

Created by Hilary Mason on 2011-01-29.
Copyright (c) 2011 Hilary Mason. All rights reserved.
"""

import sys, os
import csv
from gmail import Gmail

class email_edges(object):

    def __init__(self, username, password):
        g = Gmail(username, password)
        
        graph_out = csv.writer(open('email_graph.csv', 'wb'))
        
        viewed_messages = []
        for folder in g.list_folders(): # iterate through all folders in the account
            # print "%s: %s" % (folder, g.get_message_ids(folder)) # NOTE: uncomment this to see which ids are in each folder
            for message_id in g.get_message_ids(folder): # iterate through message IDs
                if message_id not in viewed_messages: # ...but don't repeat messages
                    # print "Processing %s" % message_id
                    msg = g.get_message(message_id)
                    
                    for line in msg.split('\n'): # grab the from and to lines
                        line = line.strip()
                        if line[0:5] == "From:":
                            msg_from = line[5:].strip()
                        elif line[0:3] == "To:":
                            msg_to = line[3:].strip()
                        
                    try:
                        # print "%s, %s" % (msg_from, msg_to) # DEBUG
                        graph_out.writerow([msg_from, msg_to]) # output the from and to
                    except UnboundLocalError: # ignore if we can't read the headers
                        pass
                        
        

if __name__ == '__main__':
    try:
        filename = sys.argv[1]
    except IndexError:
        filename = "email_graph.csv"
        
    username = 'ann9enigma@gmail.com'
    password = 'stratar0x'
	
    e = email_edges(username, password)


########NEW FILE########
__FILENAME__ = email_stats
#!/usr/bin/env python
# encoding: utf-8
"""
email_stats.py

Created by Hilary Mason on 2011-01-31.
Copyright (c) 2011 Hilary Mason. All rights reserved.
"""

import sys, os
from gmail import Gmail

if __name__ == '__main__':
	g = Gmail("ann9enigma@gmail.com", "stratar0x")
	
	folder_stats = {}
	folder_stats['inbox'] = len(g.get_message_ids())
	
	for folder_name in g.list_folders():
	    folder_stats[folder_name] = len(g.get_message_ids(folder_name))
	    
	for folder_name, count in folder_stats.items():
	    print "Folder %s, # messages: %s" % (folder_name, count)


########NEW FILE########
__FILENAME__ = email_timestamps
#!/usr/bin/env python
# encoding: utf-8
"""
email_timestamps.py

Created by Hilary Mason on 2011-02-01.
Copyright (c) 2011 Hilary Mason. All rights reserved.
"""

import sys, os
import email
from gmail import Gmail

class emailTimestamps(object):

    def __init__(self, username, password):

        e = Gmail(username, password)
        # e.select_folder("waiting")
        message_ids = e.get_message_ids()
        self.get_date(e, message_ids)        
        
    def get_date(self, e, message_ids):
        
        for emailid in message_ids:
            resp, data = e.m.fetch(emailid, "(RFC822)") # fetching the mail, "`(RFC822)`" means "get the whole stuff", but you can ask for headers only, etc
            email_body = data[0][1] # getting the mail content
            mail = email.message_from_string(email_body) # parsing the mail content to get a mail object
            
            # print mail
            for received in mail.get_all("Received"):
                date_string = received.split(';').pop().strip()
                print date_string
        

if __name__ == '__main__':
	e = emailTimestamps("ann9enigma@gmail.com", "stratar0x")


########NEW FILE########
__FILENAME__ = email_viz
#!/usr/bin/env python
# encoding: utf-8
"""
email_viz.py

Purpose:  Visualize ann9enigma@gmail.com e-mail network with NetworkX

Author:   Drew Conway
Email:    drew.conway@nyu.edu
Date:     2011-01-30

Copyright (c) 2011, under the Simplified BSD License.  
For more information on FreeBSD see: http://www.opensource.org/licenses/bsd-license.php
All rights reserved.
"""

import sys
import os
import csv
import networkx as nx
import re
import matplotlib.pylab as plt

def lattice_plot(component_list, file_path):
    """
    Creates a lattice style plot of all graph components
    """
    graph_fig=plt.figure(figsize=(20,10))    # Create figure
    
    # Set the number of rows in the plot based on an odd or
    # even number of components  
    num_components=len(component_list)
    if num_components % 2 > 0:
        num_cols=(num_components/2)+1
    else:
        num_cols=num_components/2
    
    # Plot subgraphs, with centrality annotation
    plot_count=1
    for G in component_list:
        # Find actor in each component with highest degree
        in_cent=nx.degree(G)
        in_cent=[(b,a) for (a,b) in in_cent.items()]
        in_cent.sort()
        in_cent.reverse()
        high_in=in_cent[0][1]
        
        # Plot with annotation
        plt.subplot(2,num_cols,plot_count)
        nx.draw_spring(G, node_size=35, with_labels=False)
        plt.text( 0,-.1,"Highest degree: "+high_in, color="darkgreen")
        plot_count+=1
    
    plt.savefig(file_path)


def ego_plot(graph, n, file_path):
    """Draw the ego graph for a given node 'n' """
    ego_plot=plt.figure(figsize=(10,10))
    ego=nx.ego_graph(graph,n) # Get ego graph for n
    
    # Draw graph
    pos=nx.spring_layout(ego, iterations=5000)
    nx.draw_networkx_nodes(ego,pos,node_color='b',node_size=100)
    nx.draw_networkx_edges(ego,pos)
    # Create label offset
    label_pos=dict([(a,[b[0],b[1]+0.03]) for (a,b) in pos.items()])
    nx.draw_networkx_labels(ego, pos=label_pos,font_color="darkgreen")
    
    # Draw ego as large and red
    nx.draw_networkx_nodes(ego,pos,nodelist=[n],node_size=300,node_color='r', font_color="darkgreen")
    plt.savefig(file_path)
    

def getEmail(email_string):
    """Convert an email string on the type 'Ann Smith <ann.smith@email.com>'
    to only 'ann.smith@email.com'
    """
    # Need to clean up the messy CSV data to ge the graph right
    if email_string.find("<") > -1:
        email_address=re.split("[<>]",email_string)     # First, extract Address from brackets
        address_index=map(lambda x: x.find("@"), email_address) # Find where address is
        address_index=map(lambda y: y>0, address_index).index(True) 
        email_address=email_address[address_index]  # Get address string
        email_address=email_address.replace('"','') # Do final string cleaning
        return email_address.strip()
    else:
        return email_string


def graphFromCSV(file_path, create_using=nx.DiGraph()):
    """
    Create a NetworkX graph object from a csv file
    """
    # Create NetworkX object for storing graph
    csv_graph = create_using
    
    # Create reader CSV reader object from file path
    csv_file=open(file_path, "rb")
    csv_reader=csv.reader(csv_file)

    #  Add rows from CSV file as 
    for row in csv_reader:
        clean_edges=map(getEmail, row)
        csv_graph.add_edge(clean_edges[0], clean_edges[1])

    # Return graph object
    return csv_graph


def main():
    # Create a NetworkX graph object 
    gmail_graph=graphFromCSV("../email_analysis/email_graph.csv")

    # Draw entire graph
    full_graph=plt.figure(figsize=(10,10))
    nx.draw_spring(gmail_graph, arrows=False, node_size=50, with_labels=False)
    plt.savefig("../../../images/graphs/full_graph.png")
    
    # Draw ann9enigma@gmail.com's Ego graph
    ego_plot(gmail_graph, "ann9enigma@gmail.com", "../../../images/graphs/ann9enigma_ego.png")

    # Create a lattice plot of all weakly connected components
    gmail_components=nx.weakly_connected_component_subgraphs(gmail_graph)
    lattice_plot(gmail_components, "../../../images/graphs/gmail_subgraphs.png")
    

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = first_viz
#!/usr/bin/env python
# encoding: utf-8
"""
first_viz.py

Purpose:  Creating a first matplotlib visualization
            (Strata - Data Bootcamp Tutorial)
Author:   Drew Conway
Email:    drew.conway@nyu.edu
Date:     2011-01-25

Copyright (c) 2011, under the Simplified BSD License.  
For more information on FreeBSD see: http://www.opensource.org/licenses/bsd-license.php
All rights reserved.
"""

import sys
import os
import matplotlib.pylab as plt
from scipy.stats import norm

def plot_normal(random_numbers, path=""):
    """
    A function to graphically check a random distribution's
    fit to a theoretical normal.
    """
    fig=plt.figure(figsize = (8,6)) # Create a figure to plot in (good habit)
    # Histogram of random numbers with 25 bins
    n, bins, pataches = plt.hist(random_numbers,normed=True,bins=25,alpha=0.75)  
    # Add "best fit" line
    y = norm.pdf(bins)
    plt.plot(bins,y,"r-")
    # Save plot
    plt.xlabel("Random numbers")
    plt.ylabel("Density")
    plt.title("My first matplotlib visualization!")
    plt.savefig(path)

def main():
    random_normal = norm.rvs(0,1,size=10000)
    plot_normal(random_normal,"../../../images/figures/matplotlib_first.png")

if __name__ == '__main__':
	main()


########NEW FILE########
