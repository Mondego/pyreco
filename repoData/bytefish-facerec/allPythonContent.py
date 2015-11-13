__FILENAME__ = crop_face
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Philipp Wagner
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of the Willow Garage nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys, math, Image

def Distance(p1,p2):
  dx = p2[0] - p1[0]
  dy = p2[1] - p1[1]
  return math.sqrt(dx*dx+dy*dy)

def ScaleRotateTranslate(image, angle, center = None, new_center = None, scale = None, resample=Image.BICUBIC):
  if (scale is None) and (center is None):
    return image.rotate(angle=angle, resample=resample)
  nx,ny = x,y = center
  sx=sy=1.0
  if new_center:
    (nx,ny) = new_center
  if scale:
    (sx,sy) = (scale, scale)
  cosine = math.cos(angle)
  sine = math.sin(angle)
  a = cosine/sx
  b = sine/sx
  c = x-nx*a-ny*b
  d = -sine/sy
  e = cosine/sy
  f = y-nx*d-ny*e
  return image.transform(image.size, Image.AFFINE, (a,b,c,d,e,f), resample=resample)

def CropFace(image, eye_left=(0,0), eye_right=(0,0), offset_pct=(0.2,0.2), dest_sz = (70,70)):
  # calculate offsets in original image
  offset_h = math.floor(float(offset_pct[0])*dest_sz[0])
  offset_v = math.floor(float(offset_pct[1])*dest_sz[1])
  # get the direction
  eye_direction = (eye_right[0] - eye_left[0], eye_right[1] - eye_left[1])
  # calc rotation angle in radians
  rotation = -math.atan(float(eye_direction[1])/float(eye_direction[0]))
  # distance between them
  dist = Distance(eye_left, eye_right)
  # calculate the reference eye-width
  reference = dest_sz[0] - 2.0*offset_h
  # scale factor
  scale = float(dist)/float(reference)
  # rotate original around the left eye
  image = ScaleRotateTranslate(image, center=eye_left, angle=rotation)
  # crop the rotated image
  crop_xy = (eye_left[0] - scale*offset_h, eye_left[1] - scale*offset_v)
  crop_size = (dest_sz[0]*scale, dest_sz[1]*scale)
  image = image.crop((int(crop_xy[0]), int(crop_xy[1]), int(crop_xy[0]+crop_size[0]), int(crop_xy[1]+crop_size[1])))
  # resize it
  image = image.resize(dest_sz, Image.ANTIALIAS)
  return image
  
if __name__ == "__main__":
  image =  Image.open("arnie.jpg")
  CropFace(image, eye_left=(280,322), eye_right=(435,395), offset_pct=(0.3,0.3), dest_sz=(200,200)).save("arnie_10_10_200_200.jpg")
#  CropFace(image, eye_left=(252,364), eye_right=(420,366), offset_pct=(0.2,0.2), dest_sz=(200,200)).save("arnie_20_20_200_200.jpg")
#  CropFace(image, eye_left=(252,364), eye_right=(420,366), offset_pct=(0.3,0.3), dest_sz=(200,200)).save("arnie_30_30_200_200.jpg")
#  CropFace(image, eye_left=(252,364), eye_right=(420,366), offset_pct=(0.2,0.2)).save("arnie_20_20_70_70.jpg")

########NEW FILE########
__FILENAME__ = extract_faces
import sys
# append facerec to module search path
sys.path.append("../..")
import cv2
from facedet.detector import SkinFaceDetector
import numpy as np
import os


def extract_faces(src_dir, dst_dir, detector, face_sz = (130,130)):
	"""
	Extracts the faces from all images in a given src_dir and writes the extracted faces
	to dst_dir. Needs a facedet.Detector object to perform the actual detection.
	
	Args:
		src_dir [string] 
		dst_dir [string] 
		detector [facedet.Detector]
		face_sz [tuple] 
	"""
	if not os.path.exists(dst_dir):
		try:
			os.mkdir(dst_dir)
		except:
			raise OSError("Can't create destination directory (%s)!" % (dst_dir))
	for dirname, dirnames, filenames in os.walk(src_dir):
		for subdir in dirnames:
				src_subdir = os.path.join(dirname, subdir)
				dst_subdir = os.path.join(dst_dir,subdir)
				if not os.path.exists(dst_subdir):
					try:
						os.mkdir(dst_subdir)
					except:
						raise OSError("Can't create destination directory (%s)!" % (dst_dir))
				for filename in os.listdir(src_subdir):
					name, ext = os.path.splitext(filename)
					src_fn = os.path.join(src_subdir,filename)
					img = cv2.imread(src_fn)
					rects = detector.detect(img)
					for i,rect in enumerate(rects):
						x0,y0,x1,y1 = rect
						face = img[y0:y1,x0:x1]
						face = cv2.resize(face, face_sz, interpolation = cv2.INTER_CUBIC)
						print os.path.join(dst_subdir, "%s_%s_%d%s" % (subdir, name,i,ext))
						cv2.imwrite(os.path.join(dst_subdir, "%s_%s_%d%s" % (subdir, name,i,ext)), face)

if __name__ == "__main__":
	if len(sys.argv) < 3:
		print "usage: python extract_faces.py <src_dir> <dst_dir>"
		sys.exit()
	src_dir = sys.argv[1]
	dst_dir = sys.argv[2]
	detector = SkinFaceDetector(threshold=0.3, cascade_fn="/home/philipp/projects/opencv2/OpenCV-2.3.1/data/haarcascades/haarcascade_frontalface_alt2.xml")
	extract_faces(src_dir=src_dir, dst_dir=dst_dir, detector=detector)

########NEW FILE########
__FILENAME__ = fisherfaces_example
import sys
# append facerec to module search path
sys.path.append("../..")
# import facerec stuff
from facerec.dataset import DataSet
from facerec.feature import Fisherfaces
from facerec.distance import EuclideanDistance, CosineDistance
from facerec.classifier import NearestNeighbor
from facerec.classifier import SVM
from facerec.model import PredictableModel
from facerec.validation import KFoldCrossValidation
from facerec.visual import subplot
from facerec.util import minmax_normalize
# import numpy
import numpy as np
# import matplotlib colormaps
import matplotlib.cm as cm
# import for logging
import logging,sys
# set up a handler for logging
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
# add handler to facerec modules
logger = logging.getLogger("facerec")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
# load a dataset (e.g. AT&T Facedatabase)
dataSet = DataSet("/home/philipp/facerec/data/yalefaces_recognition")
# define Fisherfaces as feature extraction method
feature = Fisherfaces()
# define a 1-NN classifier with Euclidean Distance
classifier = NearestNeighbor(dist_metric=EuclideanDistance(), k=1)
# define the model as the combination
model = PredictableModel(feature=feature, classifier=classifier)
# show fisherfaces
model.compute(dataSet.data, dataSet.labels)
# turn the first (at most) 16 eigenvectors into grayscale
# images (note: eigenvectors are stored by column!)
E = []
for i in xrange(min(model.feature.eigenvectors.shape[1], 16)):
    e = model.feature.eigenvectors[:,i].reshape(dataSet.data[0].shape)
    E.append(minmax_normalize(e,0,255, dtype=np.uint8))
# plot them and store the plot to "python_fisherfaces_fisherfaces.pdf"
subplot(title="Fisherfaces", images=E, rows=4, cols=4, sptitle="Fisherface", colormap=cm.jet, filename="fisherfaces.pdf")
# perform a 10-fold cross validation
cv = KFoldCrossValidation(model, k=10)
cv.validate(dataSet.data, dataSet.labels)
cv.print_results()

########NEW FILE########
__FILENAME__ = lpq_experiment
#!/usr/bin/python
#
# coding: utf-8
#
# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Philipp Wagner <bytefish[at]gmx[dot]de>.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of the author nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import numpy as np
from scipy import ndimage
import os
import sys

sys.path.append("../..")

from PIL import Image
import matplotlib.pyplot as plt
import textwrap

import logging

from facerec.feature import PCA, Fisherfaces, SpatialHistogram
from facerec.distance import EuclideanDistance, ChiSquareDistance
from facerec.classifier import NearestNeighbor
from facerec.model import PredictableModel
from facerec.lbp import LPQ, ExtendedLBP
from facerec.validation import KFoldCrossValidation, ValidationResult, precision


EXPERIMENT_NAME = "LocalPhaseQuantizationExperiment"

def read_images(path, sz=None):
    """Reads the images in a given folder, resizes images on the fly if size is given.

    Args:
        path: Path to a folder with subfolders representing the subjects (persons).
        sz: A tuple with the size Resizes 

    Returns:
        A list [X,y]

            X: The images, which is a Python list of numpy arrays.
            y: The corresponding labels (the unique number of the subject, person) in a Python list.
    """
    c = 0
    X,y = [], []
    for dirname, dirnames, filenames in os.walk(path):
        for subdirname in dirnames:
            subject_path = os.path.join(dirname, subdirname)
            for filename in os.listdir(subject_path):
                try:
                    im = Image.open(os.path.join(subject_path, filename))
                    im = im.convert("L")
                    # resize to given size (if given)
                    if (sz is not None):
                        im = im.resize(self.sz, Image.ANTIALIAS)
                    X.append(np.asarray(im, dtype=np.uint8))
                    y.append(c)
                except IOError, (errno, strerror):
                    print "I/O error({0}): {1}".format(errno, strerror)
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    raise
            c = c+1
    return [X,y]
    
def apply_gaussian(X, sigma):
    """A simple function to apply a Gaussian Blur on each image in X.
    
    Args:
        X: A list of images.
        sigma: sigma to apply
        
    Returns:
        Y: The processed images
    """
    return np.array([ndimage.gaussian_filter(x, sigma) for x in X])


def results_to_list(validation_results):
    return [precision(result.true_positives,result.false_positives) for result in validation_results]
    
    
if __name__ == "__main__":
    # This is where we write the results to, if an output_dir is given
    # in command line:
    out_dir = None
    # You'll need at least a path to your image data, please see
    # the tutorial coming with this source code on how to prepare
    # your image data:
    if len(sys.argv) < 2:
        print "USAGE: lpq_experiment.py </path/to/images>"
        sys.exit()
    # Now read in the image data. This must be a valid path!
    [X,y] = read_images(sys.argv[1])
    # Set up a handler for logging:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    # Add handler to facerec modules, so we see what's going on inside:
    logger = logging.getLogger("facerec")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    # The models we want to evaluate:
    model0 = PredictableModel(feature=PCA(num_components=50), classifier=NearestNeighbor(dist_metric=EuclideanDistance(), k=1))
    model1 = PredictableModel(feature=Fisherfaces(), classifier=NearestNeighbor(dist_metric=EuclideanDistance(), k=1))
    model2 = PredictableModel(feature=SpatialHistogram(lbp_operator=ExtendedLBP()), classifier=NearestNeighbor(dist_metric=ChiSquareDistance(), k=1))
    model3 = PredictableModel(feature=SpatialHistogram(lbp_operator=LPQ()), classifier=NearestNeighbor(dist_metric=ChiSquareDistance(), k=1))
    # I should rewrite the framework to offer a less memory-intense solution here:
    cv0 = KFoldCrossValidation(model0, k=10)
    cv1 = KFoldCrossValidation(model1, k=10)
    cv2 = KFoldCrossValidation(model2, k=10)
    cv3 = KFoldCrossValidation(model3, k=10)
    # Make it a list, so we can iterate through:
    validators = [cv0, cv1, cv2, cv3]
    # The sigmas we'll apply for each run:
    sigmas = [0, 1, 2, 4]
    # If everything went fine, we should have the results of each model:
    for sigma in sigmas:
        Xs = apply_gaussian(X, sigma)
        for validator in validators:
            experiment_description = "%s (sigma=%.2f)" % (EXPERIMENT_NAME, sigma)
            validator.validate(Xs, y, experiment_description)
    # Print the results:
    for validator in validators:
        validator.print_results()
    # Make a nice plot of this textual output:
    fig = plt.figure()
    # Add the Validation results:
    plt.plot(sigmas, results_to_list(cv0.validation_results), linestyle='--', marker='*', color='r')
    plt.plot(sigmas, results_to_list(cv1.validation_results), linestyle='--', marker='s', color='b')
    plt.plot(sigmas, results_to_list(cv2.validation_results), linestyle='--', marker='^', color='g')
    plt.plot(sigmas, results_to_list(cv3.validation_results), linestyle='--', marker='x', color='k')
    # Put the legend below the plot:
    plt.legend(
        (
            "\n".join(textwrap.wrap(repr(model0), 120)),
            "\n".join(textwrap.wrap(repr(model1), 120)),
            "\n".join(textwrap.wrap(repr(model2), 120)),
            "\n".join(textwrap.wrap(repr(model3), 120))
        ), prop={'size':6}, numpoints=1, loc='upper center', bbox_to_anchor=(0.5, -0.2),  fancybox=True, shadow=True, ncol=1)
    # Scale Precision correctly:
    plt.ylim(0,1)
    # Finally add the labels:
    plt.title(EXPERIMENT_NAME)
    plt.ylabel('Precision')
    plt.xlabel('Sigma')
    fig.subplots_adjust(bottom=0.5)
    # Save the gifure and we are out of here!
    plt.savefig("lpq_experiment.png", bbox_inches='tight',dpi=100)
########NEW FILE########
__FILENAME__ = simple_example
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Philipp Wagner <bytefish[at]gmx[dot]de>.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of the author nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys, os
sys.path.append("../..")
# import facerec modules
from facerec.feature import Fisherfaces, SpatialHistogram, Identity
from facerec.distance import EuclideanDistance, ChiSquareDistance
from facerec.classifier import NearestNeighbor
from facerec.model import PredictableModel
from facerec.validation import KFoldCrossValidation
from facerec.visual import subplot
from facerec.util import minmax_normalize
from facerec.serialization import save_model, load_model
# import numpy, matplotlib and logging
import numpy as np
from PIL import Image
import matplotlib.cm as cm
import logging
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from facerec.lbp import LPQ, ExtendedLBP


def read_images(path, sz=None):
    """Reads the images in a given folder, resizes images on the fly if size is given.

    Args:
        path: Path to a folder with subfolders representing the subjects (persons).
        sz: A tuple with the size Resizes 

    Returns:
        A list [X,y]

            X: The images, which is a Python list of numpy arrays.
            y: The corresponding labels (the unique number of the subject, person) in a Python list.
    """
    c = 0
    X,y = [], []
    for dirname, dirnames, filenames in os.walk(path):
        for subdirname in dirnames:
            subject_path = os.path.join(dirname, subdirname)
            for filename in os.listdir(subject_path):
                try:
                    im = Image.open(os.path.join(subject_path, filename))
                    im = im.convert("L")
                    # resize to given size (if given)
                    if (sz is not None):
                        im = im.resize(self.sz, Image.ANTIALIAS)
                    X.append(np.asarray(im, dtype=np.uint8))
                    y.append(c)
                except IOError, (errno, strerror):
                    print "I/O error({0}): {1}".format(errno, strerror)
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    raise
            c = c+1
    return [X,y]

if __name__ == "__main__":
    # This is where we write the images, if an output_dir is given
    # in command line:
    out_dir = None
    # You'll need at least a path to your image data, please see
    # the tutorial coming with this source code on how to prepare
    # your image data:
    if len(sys.argv) < 2:
        print "USAGE: facerec_demo.py </path/to/images>"
        sys.exit()
    # Now read in the image data. This must be a valid path!
    [X,y] = read_images(sys.argv[1])
    # Then set up a handler for logging:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    # Add handler to facerec modules, so we see what's going on inside:
    logger = logging.getLogger("facerec")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    # Define the Fisherfaces as Feature Extraction method:
    feature = Fisherfaces()
    # Define a 1-NN classifier with Euclidean Distance:
    classifier = NearestNeighbor(dist_metric=EuclideanDistance(), k=1)
    # Define the model as the combination
    my_model = PredictableModel(feature=feature, classifier=classifier)
    # Compute the Fisherfaces on the given data (in X) and labels (in y):
    my_model.compute(X, y)
    # We then save the model, which uses Pythons pickle module:
    save_model('model.pkl', my_model)
    model = load_model('model.pkl')
    # Then turn the first (at most) 16 eigenvectors into grayscale
    # images (note: eigenvectors are stored by column!)
    E = []
    for i in xrange(min(model.feature.eigenvectors.shape[1], 16)):
        e = model.feature.eigenvectors[:,i].reshape(X[0].shape)
        E.append(minmax_normalize(e,0,255, dtype=np.uint8))
    # Plot them and store the plot to "python_fisherfaces_fisherfaces.pdf"
    subplot(title="Fisherfaces", images=E, rows=4, cols=4, sptitle="Fisherface", colormap=cm.jet, filename="fisherfaces.png")
    # Perform a 10-fold cross validation
    cv = KFoldCrossValidation(model, k=10)
    cv.validate(X, y)
    # And print the result:
    cv.print_results()
########NEW FILE########
__FILENAME__ = common
'''
This module contais some common routines used by other samples.
'''

import numpy as np
import cv2
import os
from contextlib import contextmanager
import itertools as it

image_extensions = ['.bmp', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.pbm', '.pgm', '.ppm']

class Bunch(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)
    def __str__(self):
        return str(self.__dict__)

def splitfn(fn):
    path, fn = os.path.split(fn)
    name, ext = os.path.splitext(fn)
    return path, name, ext

def anorm2(a):
    return (a*a).sum(-1)
def anorm(a):
    return np.sqrt( anorm2(a) )

def homotrans(H, x, y):
    xs = H[0, 0]*x + H[0, 1]*y + H[0, 2]
    ys = H[1, 0]*x + H[1, 1]*y + H[1, 2]
    s  = H[2, 0]*x + H[2, 1]*y + H[2, 2]
    return xs/s, ys/s

def to_rect(a):
    a = np.ravel(a)
    if len(a) == 2:
        a = (0, 0, a[0], a[1])
    return np.array(a, np.float64).reshape(2, 2)

def rect2rect_mtx(src, dst):
    src, dst = to_rect(src), to_rect(dst)
    cx, cy = (dst[1] - dst[0]) / (src[1] - src[0])
    tx, ty = dst[0] - src[0] * (cx, cy)
    M = np.float64([[ cx,  0, tx],
                    [  0, cy, ty],
                    [  0,  0,  1]])
    return M


def lookat(eye, target, up = (0, 0, 1)):
    fwd = np.asarray(target, np.float64) - eye
    fwd /= anorm(fwd)
    right = np.cross(fwd, up)
    right /= anorm(right)
    down = np.cross(fwd, right)
    R = np.float64([right, down, fwd])
    tvec = -np.dot(R, eye)
    return R, tvec

def mtx2rvec(R):
    w, u, vt = cv2.SVDecomp(R - np.eye(3))
    p = vt[0] + u[:,0]*w[0]    # same as np.dot(R, vt[0])
    c = np.dot(vt[0], p)
    s = np.dot(vt[1], p)
    axis = np.cross(vt[0], vt[1])
    return axis * np.arctan2(s, c)

def draw_str(dst, (x, y), s):
    cv2.putText(dst, s, (x+1, y+1), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 0), thickness = 2, lineType=cv2.CV_AA)
    cv2.putText(dst, s, (x, y), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), lineType=cv2.CV_AA)

class Sketcher:
    def __init__(self, windowname, dests, colors_func):
        self.prev_pt = None
        self.windowname = windowname
        self.dests = dests
        self.colors_func = colors_func
        self.dirty = False
        self.show()
        cv2.setMouseCallback(self.windowname, self.on_mouse)

    def show(self):
        cv2.imshow(self.windowname, self.dests[0])

    def on_mouse(self, event, x, y, flags, param):
        pt = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            self.prev_pt = pt
        if self.prev_pt and flags & cv2.EVENT_FLAG_LBUTTON:
            for dst, color in zip(self.dests, self.colors_func()):
                cv2.line(dst, self.prev_pt, pt, color, 5)
            self.dirty = True
            self.prev_pt = pt
            self.show()
        else:
            self.prev_pt = None


# palette data from matplotlib/_cm.py
_jet_data =   {'red':   ((0., 0, 0), (0.35, 0, 0), (0.66, 1, 1), (0.89,1, 1),
                         (1, 0.5, 0.5)),
               'green': ((0., 0, 0), (0.125,0, 0), (0.375,1, 1), (0.64,1, 1),
                         (0.91,0,0), (1, 0, 0)),
               'blue':  ((0., 0.5, 0.5), (0.11, 1, 1), (0.34, 1, 1), (0.65,0, 0),
                         (1, 0, 0))}

cmap_data = { 'jet' : _jet_data }

def make_cmap(name, n=256):
    data = cmap_data[name]
    xs = np.linspace(0.0, 1.0, n)
    channels = []
    eps = 1e-6
    for ch_name in ['blue', 'green', 'red']:
        ch_data = data[ch_name]
        xp, yp = [], []
        for x, y1, y2 in ch_data:
            xp += [x, x+eps]
            yp += [y1, y2]
        ch = np.interp(xs, xp, yp)
        channels.append(ch)
    return np.uint8(np.array(channels).T*255)

def nothing(*arg, **kw):
    pass

def clock():
    return cv2.getTickCount() / cv2.getTickFrequency()

@contextmanager
def Timer(msg):
    print msg, '...',
    start = clock()
    try:
        yield
    finally:
        print "%.2f ms" % ((clock()-start)*1000)

class StatValue:
    def __init__(self, smooth_coef = 0.5):
        self.value = None
        self.smooth_coef = smooth_coef
    def update(self, v):
        if self.value is None:
            self.value = v
        else:
            c = self.smooth_coef
            self.value = c * self.value + (1.0-c) * v

class RectSelector:
    def __init__(self, win, callback):
        self.win = win
        self.callback = callback
        cv2.setMouseCallback(win, self.onmouse)
        self.drag_start = None
        self.drag_rect = None
    def onmouse(self, event, x, y, flags, param):
        x, y = np.int16([x, y]) # BUG
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drag_start = (x, y)
        if self.drag_start:
            if flags & cv2.EVENT_FLAG_LBUTTON:
                xo, yo = self.drag_start
                x0, y0 = np.minimum([xo, yo], [x, y])
                x1, y1 = np.maximum([xo, yo], [x, y])
                self.drag_rect = None
                if x1-x0 > 0 and y1-y0 > 0:
                    self.drag_rect = (x0, y0, x1, y1)
            else:
                rect = self.drag_rect
                self.drag_start = None
                self.drag_rect = None
                if rect:
                    self.callback(rect)
    def draw(self, vis):
        if not self.drag_rect:
            return False
        x0, y0, x1, y1 = self.drag_rect
        cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 0), 2)
        return True
    @property
    def dragging(self):
        return self.drag_rect is not None


def grouper(n, iterable, fillvalue=None):
    '''grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx'''
    args = [iter(iterable)] * n
    return it.izip_longest(fillvalue=fillvalue, *args)

def mosaic(w, imgs):
    '''Make a grid from images.

    w    -- number of grid columns
    imgs -- images (must have same size and format)
    '''
    imgs = iter(imgs)
    img0 = imgs.next()
    pad = np.zeros_like(img0)
    imgs = it.chain([img0], imgs)
    rows = grouper(w, imgs, pad)
    return np.vstack(map(np.hstack, rows))

def getsize(img):
    h, w = img.shape[:2]
    return w, h

def mdot(*args):
    return reduce(np.dot, args)

def draw_keypoints(vis, keypoints, color = (0, 255, 255)):
    for kp in keypoints:
            x, y = kp.pt
            cv2.circle(vis, (int(x), int(y)), 2, color)


########NEW FILE########
__FILENAME__ = video
import numpy as np
import cv2
from time import clock
from numpy import pi, sin, cos
import common

class VideoSynthBase(object):
    def __init__(self, size=None, noise=0.0, bg = None, **params):
        self.bg = None
        self.frame_size = (640, 480)
        if bg is not None:
            self.bg = cv2.imread(bg, 1)
            h, w = self.bg.shape[:2]
            self.frame_size = (w, h)
            
        if size is not None:
            w, h = map(int, size.split('x'))
            self.frame_size = (w, h)
            self.bg = cv2.resize(self.bg, self.frame_size)

        self.noise = float(noise)

    def render(self, dst):
        pass
        
    def read(self, dst=None):
        w, h = self.frame_size

        if self.bg is None:
            buf = np.zeros((h, w, 3), np.uint8)
        else:
            buf = self.bg.copy()

        self.render(buf)

        if self.noise > 0.0:
            noise = np.zeros((h, w, 3), np.int8)
            cv2.randn(noise, np.zeros(3), np.ones(3)*255*self.noise)
            buf = cv2.add(buf, noise, dtype=cv2.CV_8UC3)
        return True, buf

class Chess(VideoSynthBase):
    def __init__(self, **kw):
        super(Chess, self).__init__(**kw)

        w, h = self.frame_size

        self.grid_size = sx, sy = 10, 7
        white_quads = []
        black_quads = []
        for i, j in np.ndindex(sy, sx):
            q = [[j, i, 0], [j+1, i, 0], [j+1, i+1, 0], [j, i+1, 0]]
            [white_quads, black_quads][(i + j) % 2].append(q)
        self.white_quads = np.float32(white_quads)
        self.black_quads = np.float32(black_quads)

        fx = 0.9
        self.K = np.float64([[fx*w, 0, 0.5*(w-1)],
                        [0, fx*w, 0.5*(h-1)],
                        [0.0,0.0,      1.0]])

        self.dist_coef = np.float64([-0.2, 0.1, 0, 0])
        self.t = 0

    def draw_quads(self, img, quads, color = (0, 255, 0)):
        img_quads = cv2.projectPoints(quads.reshape(-1, 3), self.rvec, self.tvec, self.K, self.dist_coef) [0]
        img_quads.shape = quads.shape[:2] + (2,) 
        for q in img_quads:
            cv2.fillConvexPoly(img, np.int32(q*4), color, cv2.CV_AA, shift=2)

    def render(self, dst):
        t = self.t
        self.t += 1.0/30.0
        
        sx, sy = self.grid_size
        center = np.array([0.5*sx, 0.5*sy, 0.0])
        phi = pi/3 + sin(t*3)*pi/8
        c, s = cos(phi), sin(phi)
        ofs = np.array([sin(1.2*t), cos(1.8*t), 0]) * sx * 0.2
        eye_pos = center + np.array([cos(t)*c, sin(t)*c, s]) * 15.0 + ofs
        target_pos = center + ofs

        R, self.tvec = common.lookat(eye_pos, target_pos)
        self.rvec = common.mtx2rvec(R)

        self.draw_quads(dst, self.white_quads, (245, 245, 245))
        self.draw_quads(dst, self.black_quads, (10, 10, 10))



classes = dict(chess=Chess)

def create_capture(source):
    '''
      source: <int> or '<int>' or '<filename>' or 'synth:<params>'
    '''
    try: source = int(source)
    except ValueError: pass
    else:
        return cv2.VideoCapture(source)
    source = str(source).strip()
    if source.startswith('synth'):
        ss = filter(None, source.split(':'))
        params = dict( s.split('=') for s in ss[1:] )
        try: Class = classes[params['class']]
        except: Class = VideoSynthBase

        return Class(**params)
    return cv2.VideoCapture(source)


presets = dict(
    empty = 'synth:',
    lena = 'synth:bg=../cpp/lena.jpg:noise=0.1',
    chess = 'synth:class=chess:bg=../cpp/lena.jpg:noise=0.1:size=640x480'
)

if __name__ == '__main__':
    import sys
    import getopt

    print 'USAGE: video.py [--shotdir <dir>] [source0] [source1] ...'
    print "source: '<int>' or '<filename>' or 'synth:<params>'"
    print

    args, sources = getopt.getopt(sys.argv[1:], '', 'shotdir=')
    args = dict(args)
    shotdir = args.get('--shotdir', '.')
    if len(sources) == 0:
        sources = [ presets['chess'] ]

    print 'Press SPACE to save current frame'

    caps = map(create_capture, sources)
    shot_idx = 0
    while True:
        imgs = []
        for i, cap in enumerate(caps):
            ret, img = cap.read()
            imgs.append(img)
            cv2.imshow('capture %d' % i, img)
        ch = cv2.waitKey(1)
        if ch == 27:
            break
        if ch == ord(' '):
            for i, img in enumerate(imgs):
                fn = '%s/shot_%d_%03d.bmp' % (shotdir, i, shot_idx)
                cv2.imwrite(fn, img)
                print fn, 'saved'
            shot_idx += 1

########NEW FILE########
__FILENAME__ = simple_videofacerec
#    Copyright (c) 2012. Philipp Wagner <bytefish[at]gmx[dot]de>.
#    Released to public domain under terms of the BSD Simplified license.
#
#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions are met:
#        * Redistributions of source code must retain the above copyright
#          notice, this list of conditions and the following disclaimer.
#        * Redistributions in binary form must reproduce the above copyright
#          notice, this list of conditions and the following disclaimer in the
#          documentation and/or other materials provided with the distribution.
#        * Neither the name of the organization nor the names of its contributors 
#          may be used to endorse or promote products derived from this software 
#          without specific prior written permission.
#
#    See <http://www.opensource.org/licenses/bsd-license>
import logging
# cv2 and helper:
import cv2
from helper.common import *
from helper.video import *
# add facerec to system path
import sys
sys.path.append("../..")
# facerec imports
from facerec.model import PredictableModel
from facerec.feature import Fisherfaces
from facerec.distance import EuclideanDistance
from facerec.classifier import NearestNeighbor
from facerec.validation import KFoldCrossValidation
from facerec.serialization import save_model, load_model
# for face detection (you can also use OpenCV2 directly):
from facedet.detector import CascadedDetector

class ExtendedPredictableModel(PredictableModel):
    """ Subclasses the PredictableModel to store some more
        information, so we don't need to pass the dataset
        on each program call...
    """

    def __init__(self, feature, classifier, image_size, subject_names):
        PredictableModel.__init__(self, feature=feature, classifier=classifier)
        self.image_size = image_size
        self.subject_names = subject_names

def get_model(image_size, subject_names):
    """ This method returns the PredictableModel which is used to learn a model
        for possible further usage. If you want to define your own model, this
        is the method to return it from!
    """
    # Define the Fisherfaces Method as Feature Extraction method:
    feature = Fisherfaces()
    # Define a 1-NN classifier with Euclidean Distance:
    classifier = NearestNeighbor(dist_metric=EuclideanDistance(), k=1)
    # Return the model as the combination:
    return ExtendedPredictableModel(feature=feature, classifier=classifier, image_size=image_size, subject_names=subject_names)

def read_subject_names(path):
    """Reads the folders of a given directory, which are used to display some
        meaningful name instead of simply displaying a number.

    Args:
        path: Path to a folder with subfolders representing the subjects (persons).

    Returns:
        folder_names: The names of the folder, so you can display it in a prediction.
    """
    folder_names = []
    for dirname, dirnames, filenames in os.walk(path):
        for subdirname in dirnames:
            folder_names.append(subdirname)
    return folder_names

def read_images(path, image_size=None):
    """Reads the images in a given folder, resizes images on the fly if size is given.

    Args:
        path: Path to a folder with subfolders representing the subjects (persons).
        sz: A tuple with the size Resizes 

    Returns:
        A list [X, y, folder_names]

            X: The images, which is a Python list of numpy arrays.
            y: The corresponding labels (the unique number of the subject, person) in a Python list.
            folder_names: The names of the folder, so you can display it in a prediction.
    """
    c = 0
    X = []
    y = []
    folder_names = []
    for dirname, dirnames, filenames in os.walk(path):
        for subdirname in dirnames:
            folder_names.append(subdirname)
            subject_path = os.path.join(dirname, subdirname)
            for filename in os.listdir(subject_path):
                try:
                    im = cv2.imread(os.path.join(subject_path, filename), cv2.IMREAD_GRAYSCALE)
                    # resize to given size (if given)
                    if (image_size is not None):
                        im = cv2.resize(im, image_size)
                    X.append(np.asarray(im, dtype=np.uint8))
                    y.append(c)
                except IOError, (errno, strerror):
                    print "I/O error({0}): {1}".format(errno, strerror)
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    raise
            c = c+1
    return [X,y,folder_names]


class App(object):
    def __init__(self, model, camera_id, cascade_filename):
        self.model = model
        self.detector = CascadedDetector(cascade_fn=cascade_filename, minNeighbors=5, scaleFactor=1.1)
        self.cam = create_capture(camera_id)
            
    def run(self):
        while True:
            ret, frame = self.cam.read()
            # Resize the frame to half the original size for speeding up the detection process:
            img = cv2.resize(frame, (frame.shape[1]/2, frame.shape[0]/2), interpolation = cv2.INTER_CUBIC)
            imgout = img.copy()
            for i,r in enumerate(self.detector.detect(img)):
                x0,y0,x1,y1 = r
                # (1) Get face, (2) Convert to grayscale & (3) resize to image_size:
                face = img[y0:y1, x0:x1]
                face = cv2.cvtColor(face,cv2.COLOR_BGR2GRAY)
                face = cv2.resize(face, self.model.image_size, interpolation = cv2.INTER_CUBIC)
                # Get a prediction from the model:
                prediction = self.model.predict(face)[0]
                # Draw the face area in image:
                cv2.rectangle(imgout, (x0,y0),(x1,y1),(0,255,0),2)
                # Draw the predicted name (folder name...):
                draw_str(imgout, (x0-20,y0-20), self.model.subject_names[prediction])
            cv2.imshow('videofacerec', imgout)
            # Show image & exit on escape:
            ch = cv2.waitKey(10)
            if ch == 27:
                break

if __name__ == '__main__':
    from optparse import OptionParser
    # model.pkl is a pickled (hopefully trained) PredictableModel, which is
    # used to make predictions. You can learn a model yourself by passing the
    # parameter -d (or --dataset) to learn the model from a given dataset.
    usage = "usage: %prog [options] model_filename"
    # Add options for training, resizing, validation and setting the camera id:
    parser = OptionParser(usage=usage)
    parser.add_option("-r", "--resize", action="store", type="string", dest="size", default="100x100", 
        help="Resizes the given dataset to a given size in format [width]x[height] (default: 100x100).")
    parser.add_option("-v", "--validate", action="store", dest="numfolds", type="int", default=None, 
        help="Performs a k-fold cross validation on the dataset, if given (default: None).")
    parser.add_option("-t", "--train", action="store", dest="dataset", type="string", default=None,
        help="Trains the model on the given dataset.")
    parser.add_option("-i", "--id", action="store", dest="camera_id", type="int", default=0, 
        help="Sets the Camera Id to be used (default: 0).")
    parser.add_option("-c", "--cascade", action="store", dest="cascade_filename", default="haarcascade_frontalface_alt2.xml",
        help="Sets the path to the Haar Cascade used for the face detection part (default: haarcascade_frontalface_alt2.xml).")
    # Show the options to the user:
    parser.print_help()
    print "Press [ESC] to exit the program!"
    print "Script output:"
    # Parse arguments:
    (options, args) = parser.parse_args()
    # Check if a model name was passed:
    if len(args) == 0:
        print "[Error] No prediction model was given."
        sys.exit()
    # This model will be used (or created if the training parameter (-t, --train) exists:
    model_filename = args[0]
    # Check if the given model exists, if no dataset was passed:
    if (options.dataset is None) and (not os.path.exists(model_filename)):
        print "[Error] No prediction model found at '%s'." % model_filename
        sys.exit()
    # Check if the given (or default) cascade file exists:
    if not os.path.exists(options.cascade_filename):
        print "[Error] No Cascade File found at '%s'." % options.cascade_filename
        sys.exit()
    # We are resizing the images to a fixed size, as this is neccessary for some of
    # the algorithms, some algorithms like LBPH don't have this requirement. To 
    # prevent problems from popping up, we resize them with a default value if none
    # was given:
    try:
        image_size = (int(options.size.split("x")[0]), int(options.size.split("x")[1]))
    except:
        print "[Error] Unable to parse the given image size '%s'. Please pass it in the format [width]x[height]!" % options.size
        sys.exit()
    # We have got a dataset to learn a new model from:
    if options.dataset:
        # Check if the given dataset exists:
        if not os.path.exists(options.dataset):
            print "[Error] No dataset found at '%s'." % dataset_path
            sys.exit()    
        # Reads the images, labels and folder_names from a given dataset. Images
        # are resized to given size on the fly:
        print "Loading dataset..."
        [images, labels, subject_names] = read_images(options.dataset, image_size)
        # Zip us a {label, name} dict from the given data:
        list_of_labels = list(xrange(max(labels)+1))
        subject_dictionary = dict(zip(list_of_labels, subject_names))
        # Get the model we want to compute:
        model = get_model(image_size=image_size, subject_names=subject_dictionary)
        # Sometimes you want to know how good the model may perform on the data
        # given, the script allows you to perform a k-fold Cross Validation before
        # the Detection & Recognition part starts:
        if options.numfolds:
            print "Validating model with %s folds..." % options.numfolds
            # We want to have some log output, so set up a new logging handler
            # and point it to stdout:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            # Add a handler to facerec modules, so we see what's going on inside:
            logger = logging.getLogger("facerec")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
            # Perform the validation & print results:
            crossval = KFoldCrossValidation(model, k=options.numfolds)
            crossval.validate(images, labels)
            crossval.print_results()
        # Compute the model:
        print "Computing the model..."
        model.compute(images, labels)
        # And save the model, which uses Pythons pickle module:
        print "Saving the model..."
        save_model(model_filename, model)
    else:
        print "Loading the model..."
        model = load_model(model_filename)
    # We operate on an ExtendedPredictableModel. Quit the application if this
    # isn't what we expect it to be:
    if not isinstance(model, ExtendedPredictableModel):
        print "[Error] The given model is not of type '%s'." % "ExtendedPredictableModel"
        sys.exit()
    # Now it's time to finally start the Application! It simply get's the model
    # and the image size the incoming webcam or video images are resized to:
    print "Starting application..."
    App(model=model,
        camera_id=options.camera_id,
        cascade_filename=options.cascade_filename).run()

########NEW FILE########
__FILENAME__ = detector
import sys
import os
import cv2
import numpy as np
	
class Detector:
	def detect(self, src):
		raise NotImplementedError("Every Detector must implement the detect method.")

class SkinDetector(Detector):
	"""
	Implements common color thresholding rules for the RGB, YCrCb and HSV color 
	space. The values are taken from a paper, which I can't find right now, so
	be careful with this detector.
	
	"""
	def _R1(self,BGR):
		# channels
		B = BGR[:,:,0]
		G = BGR[:,:,1]
		R = BGR[:,:,2]
		e1 = (R>95) & (G>40) & (B>20) & ((np.maximum(R,np.maximum(G,B)) - np.minimum(R, np.minimum(G,B)))>15) & (np.abs(R-G)>15) & (R>G) & (R>B)
		e2 = (R>220) & (G>210) & (B>170) & (abs(R-G)<=15) & (R>B) & (G>B)
		return (e1|e2)
	
	def _R2(self,YCrCb):
		Y = YCrCb[:,:,0]
		Cr = YCrCb[:,:,1]
		Cb = YCrCb[:,:,2]
		e1 = Cr <= (1.5862*Cb+20)
		e2 = Cr >= (0.3448*Cb+76.2069)
		e3 = Cr >= (-4.5652*Cb+234.5652)
		e4 = Cr <= (-1.15*Cb+301.75)
		e5 = Cr <= (-2.2857*Cb+432.85)
		return e1 & e2 & e3 & e4 & e5
	
	def _R3(self,HSV):
		H = HSV[:,:,0]
		S = HSV[:,:,1]
		V = HSV[:,:,2]
		return ((H<25) | (H>230))
	
	def detect(self, src):
		if np.ndim(src) < 3:
			return np.ones(src.shape, dtype=np.uint8)
		if src.dtype != np.uint8:
			return np.ones(src.shape, dtype=np.uint8)
		srcYCrCb = cv2.cvtColor(src, cv2.COLOR_BGR2YCR_CB)
		srcHSV = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
		skinPixels = self._R1(src) & self._R2(srcYCrCb) & self._R3(srcHSV)
		return np.asarray(skinPixels, dtype=np.uint8)

class CascadedDetector(Detector):
	"""
	Uses the OpenCV cascades to perform the detection. Returns the Regions of Interest, where
	the detector assumes a face. You probably have to play around with the scaleFactor, 
	minNeighbors and minSize parameters to get good results for your use case. From my 
	personal experience, all I can say is: there's no parameter combination which *just 
	works*.	
	"""
	def __init__(self, cascade_fn="./cascades/haarcascade_frontalface_alt2.xml", scaleFactor=1.2, minNeighbors=5, minSize=(30,30)):
		if not os.path.exists(cascade_fn):
			raise IOError("No valid cascade found for path=%s." % cascade_fn)
		self.cascade = cv2.CascadeClassifier(cascade_fn)
		self.scaleFactor = scaleFactor
		self.minNeighbors = minNeighbors
		self.minSize = minSize
	
	def detect(self, src):
		if np.ndim(src) == 3:
			src = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
		src = cv2.equalizeHist(src)
		rects = self.cascade.detectMultiScale(src, scaleFactor=self.scaleFactor, minNeighbors=self.minNeighbors, minSize=self.minSize)
		if len(rects) == 0:
			return []
		rects[:,2:] += rects[:,:2]
		return rects

class SkinFaceDetector(Detector):
	"""
	Uses the SkinDetector to accept only faces over a given skin color tone threshold (ignored for 
	grayscale images). Be careful with skin color tone thresholding, as it won't work in uncontrolled 
	scenarios (without preprocessing)!
	
	"""
	def __init__(self, threshold=0.3, cascade_fn="./cascades/haarcascade_frontalface_alt2.xml", scaleFactor=1.2, minNeighbors=5, minSize=(30,30)):
		self.faceDetector = CascadedDetector(cascade_fn=cascade_fn, scaleFactor=scaleFactor, minNeighbors=minNeighbors, minSize=minSize)
		self.skinDetector = SkinDetector()
		self.threshold = threshold

	def detect(self, src):
		rects = []
		for i,r in enumerate(self.faceDetector.detect(src)):
			x0,y0,x1,y1 = r
			face = src[y0:y1,x0:x1]
			skinPixels = self.skinDetector.detect(face)
			skinPercentage = float(np.sum(skinPixels)) / skinPixels.size
			print skinPercentage
			if skinPercentage > self.threshold:
				rects.append(r)
		return rects
		
if __name__ == "__main__":
	# script parameters
	if len(sys.argv) < 2:
		raise Exception("No image given.")
	inFileName = sys.argv[1]
	outFileName = None
	if len(sys.argv) > 2:
		outFileName = sys.argv[2]
	if outFileName == inFileName:
		outFileName = None
	# detection begins here
	img = np.array(cv2.imread(inFileName), dtype=np.uint8)
	imgOut = img.copy()
	# set up detectors
	#detector = SkinFaceDetector(threshold=0.3, cascade_fn="/home/philipp/projects/opencv2/OpenCV-2.3.1/data/haarcascades/haarcascade_frontalface_alt2.xml")
	detector = CascadedDetector(cascade_fn="/home/philipp/projects/opencv2/OpenCV-2.3.1/data/haarcascades/haarcascade_frontalface_alt2.xml")
	eyesDetector = CascadedDetector(scaleFactor=1.1,minNeighbors=5, minSize=(20,20), cascade_fn="/home/philipp/projects/opencv2/OpenCV-2.3.1/data/haarcascades/haarcascade_eye.xml")
	# detection
	for i,r in enumerate(detector.detect(img)):
		x0,y0,x1,y1 = r
		cv2.rectangle(imgOut, (x0,y0),(x1,y1),(0,255,0),1)
		face = img[y0:y1,x0:x1]
		for j,r2 in enumerate(eyesDetector.detect(face)):
			ex0,ey0,ex1,ey1 = r2
			cv2.rectangle(imgOut, (x0+ex0,y0+ey0),(x0+ex1,y0+ey1),(0,255,0),1)
	# display image or write to file
	if outFileName is None:
		cv2.imshow('faces', imgOut)
		cv2.waitKey(0)
		cv2.imwrite(outFileName, imgOut) 

########NEW FILE########
__FILENAME__ = classifier
from facerec.distance import EuclideanDistance
from facerec.util import asRowMatrix
import logging
import numpy as np
import operator as op

class AbstractClassifier(object):
    def compute(self,X,y):
        raise NotImplementedError("Every AbstractClassifier must implement the compute method.")
    
    def predict(self,X):
        raise NotImplementedError("Every AbstractClassifier must implement the predict method.")

class NearestNeighbor(AbstractClassifier):
    """
    Implements a k-Nearest Neighbor Model with a generic distance metric.
    """
    def __init__(self, dist_metric=EuclideanDistance(), k=1):
        AbstractClassifier.__init__(self)
        self.k = k
        self.dist_metric = dist_metric

    def compute(self, X, y):
        self.X = X
        self.y = np.asarray(y)
    
    def predict(self, q):
        """
        Predicts the k-nearest neighbor for a given query in q. 
        
        Args:
        
            q: The given query sample, which is an array.
            
        Returns:
        
            A list with the classifier output. In this framework it is
            assumed, that the predicted class is always returned as first
            element. Moreover, this class returns the distances for the 
            first k-Nearest Neighbors. 
            
            Example:
            
                [ 0, 
                   { 'labels'    : [ 0,      0,      1      ],
                     'distances' : [ 10.132, 10.341, 13.314 ]
                   }
                ]
            
            So if you want to perform a thresholding operation, you could 
            pick the distances in the second array of the generic classifier
            output.    
                    
        """
        distances = []
        for xi in self.X:
            xi = xi.reshape(-1,1)
            d = self.dist_metric(xi, q)
            distances.append(d)
        if len(distances) > len(self.y):
            raise Exception("More distances than classes. Is your distance metric correct?")
        distances = np.asarray(distances)
        # Get the indices in an ascending sort order:
        idx = np.argsort(distances)
        # Sort the labels and distances accordingly:
        sorted_y = self.y[idx]
        sorted_distances = distances[idx]
        # Take only the k first items:
        sorted_y = sorted_y[0:self.k]
        sorted_distances = sorted_distances[0:self.k]
        # Make a histogram of them:
        hist = dict((key,val) for key, val in enumerate(np.bincount(sorted_y)) if val)
        # And get the bin with the maximum frequency:
        predicted_label = max(hist.iteritems(), key=op.itemgetter(1))[0]
        # A classifier should output a list with the label as first item and
        # generic data behind. The k-nearest neighbor classifier outputs the 
        # distance of the k first items. So imagine you have a 1-NN and you
        # want to perform a threshold against it, you should take the first
        # item 
        return [predicted_label, { 'labels' : sorted_y, 'distances' : sorted_distances }]
        
    def __repr__(self):
        return "NearestNeighbor (k=%s, dist_metric=%s)" % (self.k, repr(self.dist_metric))

# libsvm
try:
    from svmutil import *
except ImportError:
    logger = logging.getLogger("facerec.classifier.SVM")
    logger.debug("Import Error: libsvm bindings not available.")
except:
    logger = logging.getLogger("facerec.classifier.SVM")
    logger.debug("Import Error: libsvm bindings not available.")

import sys
from StringIO import StringIO
bkp_stdout=sys.stdout

class SVM(AbstractClassifier):
    """
    This class is just a simple wrapper to use libsvm in the 
    CrossValidation module. If you don't use this framework
    use the validation methods coming with LibSVM, they are
    much easier to access (simply pass the correct class 
    labels in svm_predict and you are done...).

    The grid search method in this class is somewhat similar
    to libsvm grid.py, as it performs a parameter search over
    a logarithmic scale.    Again if you don't use this framework, 
    use the libsvm tools as they are much easier to access.

    Please keep in mind to normalize your input data, as expected
    for the model. There's no way to assume a generic normalization
    step.
    """

    def __init__(self, param=None):
        AbstractClassifier.__init__(self)
        self.logger = logging.getLogger("facerec.classifier.SVM")
        self.param = param
        self.svm = svm_model()
        self.param = param
        if self.param is None:
            self.param = svm_parameter("-q")
    
    def compute(self, X, y):
        self.logger.debug("SVM TRAINING (C=%.2f,gamma=%.2f,p=%.2f,nu=%.2f,coef=%.2f,degree=%.2f)" % (self.param.C, self.param.gamma, self.param.p, self.param.nu, self.param.coef0, self.param.degree))
        # turn data into a row vector (needed for libsvm)
        X = asRowMatrix(X)
        y = np.asarray(y)
        problem = svm_problem(y, X.tolist())        
        self.svm = svm_train(problem, self.param)
        self.y = y
    
    def predict(self, X):
        """
        
        Args:
        
            X: The query image, which is an array.
        
        Returns:
        
            A list with the classifier output. In this framework it is
            assumed, that the predicted class is always returned as first
            element. Moreover, this class returns the libsvm output for
            p_labels, p_acc and p_vals. The libsvm help states:
            
                p_labels: a list of predicted labels
                p_acc: a tuple including  accuracy (for classification), mean-squared 
                   error, and squared correlation coefficient (for regression).
                p_vals: a list of decision values or probability estimates (if '-b 1' 
                    is specified). If k is the number of classes, for decision values,
                    each element includes results of predicting k(k-1)/2 binary-class
                    SVMs. For probabilities, each element contains k values indicating
                    the probability that the testing instance is in each class.
                    Note that the order of classes here is the same as 'model.label'
                    field in the model structure.
        """
        X = np.asarray(X).reshape(1,-1)
        sys.stdout=StringIO() 
        p_lbl, p_acc, p_val = svm_predict([0], X.tolist(), self.svm)
        sys.stdout=bkp_stdout
        predicted_label = int(p_lbl[0])
        return [predicted_label, { 'p_lbl' : p_lbl, 'p_acc' : p_acc, 'p_val' : p_val }]
    
    def __repr__(self):        
        return "Support Vector Machine (kernel_type=%s, C=%.2f,gamma=%.2f,p=%.2f,nu=%.2f,coef=%.2f,degree=%.2f)" % (KERNEL_TYPE[self.param.kernel_type], self.param.C, self.param.gamma, self.param.p, self.param.nu, self.param.coef0, self.param.degree)



########NEW FILE########
__FILENAME__ = dataset
import os as os
import numpy as np
import PIL.Image as Image
import random
import csv

class DataSet(object):
    def __init__(self, filename=None, sz=None):
        self.labels = []
        self.groups = []
        self.names = {}
        self.data = []
        self.sz = sz
        if filename is not None:
            self.load(filename)

    def shuffle(self):
        idx = np.argsort([random.random() for i in xrange(len(self.labels))])
        self.data = [self.data[i] for i in idx]
        self.labels = self.labels[idx]
        if len(self.groups) == len(self.labels):
            self.groups = self.groups[idx]

    def load(self, path):
        c = 0
        for dirname, dirnames, filenames in os.walk(path):
            for subdirname in dirnames:
                subject_path = os.path.join(dirname, subdirname)
                for filename in os.listdir(subject_path):
                    try:
                        im = Image.open(os.path.join(subject_path, filename))
                        im = im.convert("L")
                        # resize to given size (if given)
                        if (self.sz is not None) and isinstance(self.sz, tuple) and (len(self.sz) == 2):
                            im = im.resize(self.sz, Image.ANTIALIAS)
                        self.data.append(np.asarray(im, dtype=np.uint8))
                        self.labels.append(c)
                    except IOError:
                        pass
                self.names[c] = subdirname
                c = c+1
        self.labels = np.array(self.labels, dtype=np.int)
        
    def readFromCSV(self, filename):
        # <filename>;<classId>;<groupId>
        data = [ [str(line[0]), int(line[1]),int(line[2])] for line in csv.reader(open(filename, 'rb'), delimiter=";")]
        self.labels = np.array([item[1] for item in data])
        self.groups = np.array([item[2] for item in data])
        print self.labels
        print self.groups
        for item in data:
            im_filename = item[0]
            print im_filename
            im = Image.open(os.path.join(im_filename))
            im = im.convert("L")
            # resize to given size (if given)
            if (self.sz is not None) and isinstance(self.sz, tuple) and (len(self.sz) == 2):
                im = im.resize(self.sz, Image.ANTIALIAS)
            self.data.append(np.asarray(im, dtype=np.uint8))

########NEW FILE########
__FILENAME__ = distance
# Implements various distance metrics (because my old scipy.spatial.distance module is horrible)
import numpy as np


class AbstractDistance(object):
    def __init__(self, name):
        self._name = name
        
    def __call__(self,p,q):
        raise NotImplementedError("Every AbstractDistance must implement the __call__ method.")
        
    @property
    def name(self):
        return self._name

    def __repr__(self):
        return self._name
        
class EuclideanDistance(AbstractDistance):
    def __init__(self):
        AbstractDistance.__init__(self,"EuclideanDistance")

    def __call__(self, p, q):
        p = np.asarray(p).flatten()
        q = np.asarray(q).flatten()
        return np.sqrt(np.sum(np.power((p-q),2)))

class CosineDistance(AbstractDistance):
    """
        Negated Mahalanobis Cosine Distance.
    
        Literature:
            "Studies on sensitivity of face recognition performance to eye location accuracy.". Master Thesis (2004), Wang
    """
    def __init__(self):
        AbstractDistance.__init__(self,"CosineDistance")

    def __call__(self, p, q):
        p = np.asarray(p).flatten()
        q = np.asarray(q).flatten()
        return -np.dot(p.T,q) / (np.sqrt(np.dot(p,p.T)*np.dot(q,q.T)))

class NormalizedCorrelation(AbstractDistance):
    """
        Calculates the NormalizedCorrelation Coefficient for two vectors.
    
        Literature:
            "Multi-scale Local Binary Pattern Histogram for Face Recognition". PhD (2008). Chi Ho Chan, University Of Surrey.
    """
    def __init__(self):
        AbstractDistance.__init__(self,"NormalizedCorrelation")
    
    def __call__(self, p, q):
        p = np.asarray(p).flatten()
        q = np.asarray(q).flatten()
        pmu = p.mean()
        qmu = q.mean()
        pm = p - pmu
        qm = q - qmu
        return 1.0 - (np.dot(pm, qm) / (np.sqrt(np.dot(pm, pm)) * np.sqrt(np.dot(qm, qm))))
        
class ChiSquareDistance(AbstractDistance):
    """
        Negated Mahalanobis Cosine Distance.
    
        Literature:
            "Studies on sensitivity of face recognition performance to eye location accuracy.". Master Thesis (2004), Wang
    """
    def __init__(self):
        AbstractDistance.__init__(self,"ChiSquareDistance")

    def __call__(self, p, q):
        p = np.asarray(p).flatten()
        q = np.asarray(q).flatten()
        bin_dists = (p-q)**2 / (p+q+np.finfo('float').eps)
        return np.sum(bin_dists)

class HistogramIntersection(AbstractDistance):
    def __init__(self):
        AbstractDistance.__init__(self,"HistogramIntersection")

    def __call__(self, p, q):
        p = np.asarray(p).flatten()
        q = np.asarray(q).flatten()
        return np.sum(np.minimum(p,q))

class BinRatioDistance(AbstractDistance):
    """
    Calculates the Bin Ratio Dissimilarity.

    Literature:
      "Use Bin-Ratio Information for Category and Scene Classification" (2010), Xie et.al. 
    """
    def __init__(self):
        AbstractDistance.__init__(self,"BinRatioDistance")

    def __call__(self, p, q):
        p = np.asarray(p).flatten()
        q = np.asarray(q).flatten()
        a = np.abs(1-np.dot(p,q.T)) # NumPy needs np.dot instead of * for reducing to tensor
        b = ((p-q)**2 + 2*a*(p*q))/((p+q)**2+np.finfo('float').eps)
        return np.abs(np.sum(b))

class L1BinRatioDistance(AbstractDistance):
    """
    Calculates the L1-Bin Ratio Dissimilarity.

    Literature:
      "Use Bin-Ratio Information for Category and Scene Classification" (2010), Xie et.al. 
    """
    def __init__(self):
        AbstractDistance.__init__(self,"L1-BinRatioDistance")
    
    def __call__(self, p, q):
        p = np.asarray(p, dtype=np.float).flatten()
        q = np.asarray(q, dtype=np.float).flatten()
        a = np.abs(1-np.dot(p,q.T)) # NumPy needs np.dot instead of * for reducing to tensor
        b = ((p-q)**2 + 2*a*(p*q)) * abs(p-q) / ((p+q)**2+np.finfo('float').eps)
        return np.abs(np.sum(b))

class ChiSquareBRD(AbstractDistance):
    """
    Calculates the ChiSquare-Bin Ratio Dissimilarity.

    Literature:
      "Use Bin-Ratio Information for Category and Scene Classification" (2010), Xie et.al. 
    """
    def __init__(self):
        AbstractDistance.__init__(self,"ChiSquare-BinRatioDistance")
    
    def __call__(self, p, q):
        p = np.asarray(p, dtype=np.float).flatten()
        q = np.asarray(q, dtype=np.float).flatten()
        a = np.abs(1-np.dot(p,q.T)) # NumPy needs np.dot instead of * for reducing to tensor
        b = ((p-q)**2 + 2*a*(p*q)) * (p-q)**2 / ((p+q)**3+np.finfo('float').eps)
        return np.abs(np.sum(b))

########NEW FILE########
__FILENAME__ = feature
import numpy as np

class AbstractFeature(object):

    def compute(self,X,y):
        raise NotImplementedError("Every AbstractFeature must implement the compute method.")
    
    def extract(self,X):
        raise NotImplementedError("Every AbstractFeature must implement the extract method.")
        
    def save(self):
        raise NotImplementedError("Not implemented yet (TODO).")
    
    def load(self):
        raise NotImplementedError("Not implemented yet (TODO).")
        
    def __repr__(self):
        return "AbstractFeature"

class Identity(AbstractFeature):
    """
    Simplest AbstractFeature you could imagine. It only forwards the data and does not operate on it, 
    probably useful for learning a Support Vector Machine on raw data for example!
    """
    def __init__(self):
        AbstractFeature.__init__(self)
        
    def compute(self,X,y):
        return X
    
    def extract(self,X):
        return X
    
    def __repr__(self):
        return "Identity"


from facerec.util import asColumnMatrix
from facerec.operators import ChainOperator, CombineOperator
        
class PCA(AbstractFeature):
    def __init__(self, num_components=0):
        AbstractFeature.__init__(self)
        self._num_components = num_components
        
    def compute(self,X,y):
        # build the column matrix
        XC = asColumnMatrix(X)
        y = np.asarray(y)
        # set a valid number of components
        if self._num_components <= 0 or (self._num_components > XC.shape[1]-1):
            self._num_components = XC.shape[1]-1
        # center dataset
        self._mean = XC.mean(axis=1).reshape(-1,1)
        XC = XC - self._mean
        # perform an economy size decomposition (may still allocate too much memory for computation)
        self._eigenvectors, self._eigenvalues, variances = np.linalg.svd(XC, full_matrices=False)
        # sort eigenvectors by eigenvalues in descending order
        idx = np.argsort(-self._eigenvalues)
        self._eigenvalues, self._eigenvectors = self._eigenvalues[idx], self._eigenvectors[:,idx]
        # use only num_components
        self._eigenvectors = self._eigenvectors[0:,0:self._num_components].copy()
        self._eigenvalues = self._eigenvalues[0:self._num_components].copy()
        # finally turn singular values into eigenvalues 
        self._eigenvalues = np.power(self._eigenvalues,2) / XC.shape[1]
        # get the features from the given data
        features = []
        for x in X:
            xp = self.project(x.reshape(-1,1))
            features.append(xp)
        return features
    
    def extract(self,X):
        X = np.asarray(X).reshape(-1,1)
        return self.project(X)
        
    def project(self, X):
        X = X - self._mean
        return np.dot(self._eigenvectors.T, X)

    def reconstruct(self, X):
        X = np.dot(self._eigenvectors, X)
        return X + self._mean

    @property
    def num_components(self):
        return self._num_components

    @property
    def eigenvalues(self):
        return self._eigenvalues
        
    @property
    def eigenvectors(self):
        return self._eigenvectors

    @property
    def mean(self):
        return self._mean
        
    def __repr__(self):
        return "PCA (num_components=%d)" % (self._num_components)
        
class LDA(AbstractFeature):

    def __init__(self, num_components=0):
        AbstractFeature.__init__(self)
        self._num_components = num_components

    def compute(self, X, y):
        # build the column matrix
        XC = asColumnMatrix(X)
        y = np.asarray(y)
        # calculate dimensions
        d = XC.shape[0]
        c = len(np.unique(y))        
        # set a valid number of components
        if self._num_components <= 0:
            self._num_components = c-1
        elif self._num_components > (c-1):
            self._num_components = c-1
        # calculate total mean
        meanTotal = XC.mean(axis=1).reshape(-1,1)
        # calculate the within and between scatter matrices
        Sw = np.zeros((d, d), dtype=np.float32)
        Sb = np.zeros((d, d), dtype=np.float32)
        for i in range(0,c):
            Xi = XC[:,np.where(y==i)[0]]
            meanClass = np.mean(Xi, axis = 1).reshape(-1,1)
            Sw = Sw + np.dot((Xi-meanClass), (Xi-meanClass).T)
            Sb = Sb + Xi.shape[1] * np.dot((meanClass - meanTotal), (meanClass - meanTotal).T)
        # solve eigenvalue problem for a general matrix
        self._eigenvalues, self._eigenvectors = np.linalg.eig(np.linalg.inv(Sw)*Sb)
        # sort eigenvectors by their eigenvalue in descending order
        idx = np.argsort(-self._eigenvalues.real)
        self._eigenvalues, self._eigenvectors = self._eigenvalues[idx], self._eigenvectors[:,idx]
        # only store (c-1) non-zero eigenvalues
        self._eigenvalues = np.array(self._eigenvalues[0:self._num_components].real, dtype=np.float32, copy=True)
        self._eigenvectors = np.matrix(self._eigenvectors[0:,0:self._num_components].real, dtype=np.float32, copy=True)
        # get the features from the given data
        features = []
        for x in X:
            xp = self.project(x.reshape(-1,1))
            features.append(xp)
        return features
        
    def project(self, X):
        return np.dot(self._eigenvectors.T, X)

    def reconstruct(self, X):
        return np.dot(self._eigenvectors, X)

    @property
    def num_components(self):
        return self._num_components

    @property
    def eigenvectors(self):
        return self._eigenvectors
    
    @property
    def eigenvalues(self):
        return self._eigenvalues
    
    def __repr__(self):
        return "LDA (num_components=%d)" % (self._num_components)
        
class Fisherfaces(AbstractFeature):

    def __init__(self, num_components=0):
        AbstractFeature.__init__(self)
        self._num_components = num_components
    
    def compute(self, X, y):
        # turn into numpy representation
        Xc = asColumnMatrix(X)
        y = np.asarray(y)
        # gather some statistics about the dataset
        n = len(y)
        c = len(np.unique(y))
        # define features to be extracted
        pca = PCA(num_components = (n-c))
        lda = LDA(num_components = self._num_components)
        # fisherfaces are a chained feature of PCA followed by LDA
        model = ChainOperator(pca,lda)
        # computing the chained model then calculates both decompositions
        model.compute(X,y)
        # store eigenvalues and number of components used
        self._eigenvalues = lda.eigenvalues
        self._num_components = lda.num_components
        # compute the new eigenspace as pca.eigenvectors*lda.eigenvectors
        self._eigenvectors = np.dot(pca.eigenvectors,lda.eigenvectors)
        # finally compute the features (these are the Fisherfaces)
        features = []
        for x in X:
            xp = self.project(x.reshape(-1,1))
            features.append(xp)
        return features

    def extract(self,X):
        X = np.asarray(X).reshape(-1,1)
        return self.project(X)

    def project(self, X):
        return np.dot(self._eigenvectors.T, X)
    
    def reconstruct(self, X):
        return np.dot(self._eigenvectors, X)

    @property
    def num_components(self):
        return self._num_components
        
    @property
    def eigenvalues(self):
        return self._eigenvalues
    
    @property
    def eigenvectors(self):
        return self._eigenvectors

    def __repr__(self):
        return "Fisherfaces (num_components=%s)" % (self.num_components)

from facerec.lbp import LocalDescriptor, ExtendedLBP

class SpatialHistogram(AbstractFeature):
    def __init__(self, lbp_operator=ExtendedLBP(), sz = (8,8)):
        AbstractFeature.__init__(self)
        if not isinstance(lbp_operator, LocalDescriptor):
            raise TypeError("Only an operator of type facerec.lbp.LocalDescriptor is a valid lbp_operator.")
        self.lbp_operator = lbp_operator
        self.sz = sz
        
    def compute(self,X,y):
        features = []
        for x in X:
            x = np.asarray(x)
            h = self.spatially_enhanced_histogram(x)
            features.append(h)
        return features
    
    def extract(self,X):
        X = np.asarray(X)
        return self.spatially_enhanced_histogram(X)

    def spatially_enhanced_histogram(self, X):
        # calculate the LBP image
        L = self.lbp_operator(X)
        # calculate the grid geometry
        lbp_height, lbp_width = L.shape
        grid_rows, grid_cols = self.sz
        py = int(np.floor(lbp_height/grid_rows))
        px = int(np.floor(lbp_width/grid_cols))
        E = []
        for row in range(0,grid_rows):
            for col in range(0,grid_cols):
                C = L[row*py:(row+1)*py,col*px:(col+1)*px]
                H = np.histogram(C, bins=2**self.lbp_operator.neighbors, range=(0, 2**self.lbp_operator.neighbors), normed=True)[0]
                # probably useful to apply a mapping?
                E.extend(H)
        return np.asarray(E)
    
    def __repr__(self):
        return "SpatialHistogram (operator=%s, grid=%s)" % (repr(self.lbp_operator), str(self.sz))

########NEW FILE########
__FILENAME__ = lbp
# coding: utf-8
import numpy as np
from scipy.signal import convolve2d

class LocalDescriptor(object):
    def __init__(self, neighbors):
        self._neighbors = neighbors

    def __call__(self,X):
        raise NotImplementedError("Every LBPOperator must implement the __call__ method.")
        
    @property
    def neighbors(self):
        return self._neighbors
        
    def __repr__(self):
        return "LBPOperator (neighbors=%s)" % (self._neighbors)

class OriginalLBP(LocalDescriptor):
    def __init__(self):
        LocalDescriptor.__init__(self, neighbors=8)
    
    def __call__(self,X):
        X = np.asarray(X)
        X = (1<<7) * (X[0:-2,0:-2] >= X[1:-1,1:-1]) \
            + (1<<6) * (X[0:-2,1:-1] >= X[1:-1,1:-1]) \
            + (1<<5) * (X[0:-2,2:] >= X[1:-1,1:-1]) \
            + (1<<4) * (X[1:-1,2:] >= X[1:-1,1:-1]) \
            + (1<<3) * (X[2:,2:] >= X[1:-1,1:-1]) \
            + (1<<2) * (X[2:,1:-1] >= X[1:-1,1:-1]) \
            + (1<<1) * (X[2:,:-2] >= X[1:-1,1:-1]) \
            + (1<<0) * (X[1:-1,:-2] >= X[1:-1,1:-1])
        return X
        
    def __repr__(self):
        return "OriginalLBP (neighbors=%s)" % (self._neighbors)

class ExtendedLBP(LocalDescriptor):
    def __init__(self, radius=1, neighbors=8):
        LocalDescriptor.__init__(self, neighbors=neighbors)
        self._radius = radius
        
    def __call__(self,X):
        X = np.asanyarray(X)
        ysize, xsize = X.shape
        # define circle
        angles = 2*np.pi/self._neighbors
        theta = np.arange(0,2*np.pi,angles)
        # calculate sample points on circle with radius
        sample_points = np.array([-np.sin(theta), np.cos(theta)]).T
        sample_points *= self._radius
        # find boundaries of the sample points
        miny=min(sample_points[:,0])
        maxy=max(sample_points[:,0])
        minx=min(sample_points[:,1])
        maxx=max(sample_points[:,1])
        # calculate block size, each LBP code is computed within a block of size bsizey*bsizex
        blocksizey = np.ceil(max(maxy,0)) - np.floor(min(miny,0)) + 1
        blocksizex = np.ceil(max(maxx,0)) - np.floor(min(minx,0)) + 1
        # coordinates of origin (0,0) in the block
        origy =  0 - np.floor(min(miny,0))
        origx =  0 - np.floor(min(minx,0))
        # calculate output image size
        dx = xsize - blocksizex + 1
        dy = ysize - blocksizey + 1
        # get center points
        C = np.asarray(X[origy:origy+dy,origx:origx+dx], dtype=np.uint8)
        result = np.zeros((dy,dx), dtype=np.uint32)
        for i,p in enumerate(sample_points):
            # get coordinate in the block
            y,x = p + (origy, origx)
            # Calculate floors, ceils and rounds for the x and y.
            fx = np.floor(x)
            fy = np.floor(y)
            cx = np.ceil(x)
            cy = np.ceil(y)
            # calculate fractional part    
            ty = y - fy
            tx = x - fx
            # calculate interpolation weights
            w1 = (1 - tx) * (1 - ty)
            w2 =      tx  * (1 - ty)
            w3 = (1 - tx) *      ty
            w4 =      tx  *      ty
            # calculate interpolated image
            N = w1*X[fy:fy+dy,fx:fx+dx]
            N += w2*X[fy:fy+dy,cx:cx+dx]
            N += w3*X[cy:cy+dy,fx:fx+dx]
            N += w4*X[cy:cy+dy,cx:cx+dx]
            # update LBP codes        
            D = N >= C
            result += (1<<i)*D
        return result

    @property
    def radius(self):
        return self._radius
    
    def __repr__(self):
        return "ExtendedLBP (neighbors=%s, radius=%s)" % (self._neighbors, self._radius)
        
class VarLBP(LocalDescriptor):
    def __init__(self, radius=1, neighbors=8):
        LocalDescriptor.__init__(self, neighbors=neighbors)
        self._radius = radius
        
    def __call__(self,X):
        X = np.asanyarray(X)
        ysize, xsize = X.shape
        # define circle
        angles = 2*np.pi/self._neighbors
        theta = np.arange(0,2*np.pi,angles)
        # calculate sample points on circle with radius
        sample_points = np.array([-np.sin(theta), np.cos(theta)]).T
        sample_points *= self._radius
        # find boundaries of the sample points
        miny=min(sample_points[:,0])
        maxy=max(sample_points[:,0])
        minx=min(sample_points[:,1])
        maxx=max(sample_points[:,1])
        # calculate block size, each LBP code is computed within a block of size bsizey*bsizex
        blocksizey = np.ceil(max(maxy,0)) - np.floor(min(miny,0)) + 1
        blocksizex = np.ceil(max(maxx,0)) - np.floor(min(minx,0)) + 1
        # coordinates of origin (0,0) in the block
        origy =  0 - np.floor(min(miny,0))
        origx =  0 - np.floor(min(minx,0))
        # Calculate output image size:
        dx = xsize - blocksizex + 1
        dy = ysize - blocksizey + 1
        # Allocate memory for online variance calculation:
        mean = np.zeros((dy,dx), dtype=np.float32)
        delta = np.zeros((dy,dx), dtype=np.float32)
        m2 = np.zeros((dy,dx), dtype=np.float32)
        # Holds the resulting variance matrix:
        result = np.zeros((dy,dx), dtype=np.float32)
        for i,p in enumerate(sample_points):
            # Get coordinate in the block:
            y,x = p + (origy, origx)
            # Calculate floors, ceils and rounds for the x and y:
            fx = np.floor(x)
            fy = np.floor(y)
            cx = np.ceil(x)
            cy = np.ceil(y)
            # Calculate fractional part:
            ty = y - fy
            tx = x - fx
            # Calculate interpolation weights:
            w1 = (1 - tx) * (1 - ty)
            w2 =      tx  * (1 - ty)
            w3 = (1 - tx) *      ty
            w4 =      tx  *      ty
            # Calculate interpolated image:
            N = w1*X[fy:fy+dy,fx:fx+dx]
            N += w2*X[fy:fy+dy,cx:cx+dx]
            N += w3*X[cy:cy+dy,fx:fx+dx]
            N += w4*X[cy:cy+dy,cx:cx+dx]
            # Update the matrices for Online Variance calculation (http://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#On-line_algorithm):
            delta = N - mean
            mean = mean + delta/float(i+1)
            m2 = m2 + delta * (N-mean)
        # Optional estimate for variance is m2/self._neighbors:
        result = m2/(self._neighbors-1)
        return result

    @property
    def radius(self):
        return self._radius
    
    def __repr__(self):
        return "VarLBP (neighbors=%s, radius=%s)" % (self._neighbors, self._radius)

class LPQ(LocalDescriptor):
    """ This implementation of Local Phase Quantization (LPQ) is a 1:1 adaption of the 
        original implementation by Ojansivu V & Heikkilä J, which is available at:
        
            * http://www.cse.oulu.fi/CMV/Downloads/LPQMatlab
            
        So all credit goes to them.
      
      Reference: 
        Ojansivu V & Heikkilä J (2008) Blur insensitive texture classification 
        using local phase quantization. Proc. Image and Signal Processing 
        (ICISP 2008), Cherbourg-Octeville, France, 5099:236-243.

        Copyright 2008 by Heikkilä & Ojansivu
    """
    
    def __init__(self, radius=3):
        LocalDescriptor.__init__(self, neighbors=8)
        self._radius = radius
    
    def euc_dist(self, X):
        Y = X = X.astype(np.float)
        XX = np.sum(X * X, axis=1)[:, np.newaxis]
        YY = XX.T
        distances = np.dot(X,Y.T)
        distances *= -2
        distances += XX
        distances += YY
        np.maximum(distances, 0, distances)
        distances.flat[::distances.shape[0] + 1] = 0.0
        return np.sqrt(distances)
        
    def __call__(self,X):
        f = 1.0
        x = np.arange(-self._radius,self._radius+1)
        n = len(x)
        rho = 0.95
        [xp, yp] = np.meshgrid(np.arange(1,(n+1)),np.arange(1,(n+1)))
        pp = np.concatenate((xp,yp)).reshape(2,-1)
        dd = self.euc_dist(pp.T) # squareform(pdist(...)) would do the job, too...
        C = np.power(rho,dd)
        
        w0 = (x*0.0+1.0)
        w1 = np.exp(-2*np.pi*1j*x*f/n)
        w2 = np.conj(w1)
        
        q1 = w0.reshape(-1,1)*w1
        q2 = w1.reshape(-1,1)*w0
        q3 = w1.reshape(-1,1)*w1
        q4 = w1.reshape(-1,1)*w2

        u1 = np.real(q1)
        u2 = np.imag(q1)
        u3 = np.real(q2)
        u4 = np.imag(q2)
        u5 = np.real(q3)
        u6 = np.imag(q3)
        u7 = np.real(q4)
        u8 = np.imag(q4)
        
        M = np.matrix([u1.flatten(1), u2.flatten(1), u3.flatten(1), u4.flatten(1), u5.flatten(1), u6.flatten(1), u7.flatten(1), u8.flatten(1)])
        
        D = np.dot(np.dot(M,C), M.T)
        U,S,V = np.linalg.svd(D)

        Qa = convolve2d(convolve2d(X,w0.reshape(-1,1),mode='same'),w1.reshape(1,-1),mode='same')
        Qb = convolve2d(convolve2d(X,w1.reshape(-1,1),mode='same'),w0.reshape(1,-1),mode='same')
        Qc = convolve2d(convolve2d(X,w1.reshape(-1,1),mode='same'),w1.reshape(1,-1),mode='same')
        Qd = convolve2d(convolve2d(X, w1.reshape(-1,1),mode='same'),w2.reshape(1,-1),mode='same')

        Fa = np.real(Qa)
        Ga = np.imag(Qa)
        Fb = np.real(Qb) 
        Gb = np.imag(Qb)
        Fc = np.real(Qc) 
        Gc = np.imag(Qc)
        Fd = np.real(Qd) 
        Gd = np.imag(Qd)
        
        F = np.array([Fa.flatten(1), Ga.flatten(1), Fb.flatten(1), Gb.flatten(1), Fc.flatten(1), Gc.flatten(1), Fd.flatten(1), Gd.flatten(1)])
        G = np.dot(V.T, F)
        
        t = 0

        # Calculate the LPQ Patterns:
        B = (G[0,:]>=t)*1 + (G[1,:]>=t)*2 + (G[2,:]>=t)*4 + (G[3,:]>=t)*8 + (G[4,:]>=t)*16 + (G[5,:]>=t)*32 + (G[6,:]>=t)*64 + (G[7,:]>=t)*128
        
        return np.reshape(B, np.shape(Fa))
        
    @property
    def radius(self):
        return self._radius
    
    def __repr__(self):
        return "LPQ (neighbors=%s, radius=%s)" % (self._neighbors, self._radius)
########NEW FILE########
__FILENAME__ = model
from facerec.feature import AbstractFeature
from facerec.classifier import AbstractClassifier

class PredictableModel(object):
    def __init__(self, feature, classifier):
        if not isinstance(feature, AbstractFeature):
            raise TypeError("feature must be of type AbstractFeature!")
        if not isinstance(classifier, AbstractClassifier):
            raise TypeError("classifier must be of type AbstractClassifier!")
        
        self.feature = feature
        self.classifier = classifier
    
    def compute(self, X, y):
        features = self.feature.compute(X,y)
        self.classifier.compute(features,y)

    def predict(self, X):
        q = self.feature.extract(X)
        return self.classifier.predict(q)
        
    def __repr__(self):
        feature_repr = repr(self.feature)
        classifier_repr = repr(self.classifier)
        return "PredictableModel (feature=%s, classifier=%s)" % (feature_repr, classifier_repr)

########NEW FILE########
__FILENAME__ = normalization
import numpy as np

def minmax(X, low, high, minX=None, maxX=None, dtype=np.float):
    X = np.asarray(X)
    if minX is None:
        minX = np.min(X)
    if maxX is None:
        maxX = np.max(X)
    # normalize to [0...1].    
    X = X - float(minX)
    X = X / float((maxX - minX))
    # scale to [low...high].
    X = X * (high-low)
    X = X + low
    return np.asarray(X,dtype=dtype)

def zscore(X, mean=None, std=None):
    X = np.asarray(X)
    if mean is None:
        mean = X.mean()
    if std is None:
        std = X.std()
    X = (X-mean)/std
    return X

########NEW FILE########
__FILENAME__ = operators
from facerec.feature import AbstractFeature
import numpy as np

class FeatureOperator(AbstractFeature):
    """
    A FeatureOperator operates on two feature models.
    
    Args:
        model1 [AbstractFeature]
        model2 [AbstractFeature]
    """
    def __init__(self,model1,model2):
        if (not isinstance(model1,AbstractFeature)) or (not isinstance(model2,AbstractFeature)):
            raise Exception("A FeatureOperator only works on classes implementing an AbstractFeature!")
        self.model1 = model1
        self.model2 = model2
    
    def __repr__(self):
        return "FeatureOperator(" + repr(self.model1) + "," + repr(self.model2) + ")"
    
class ChainOperator(FeatureOperator):
    """
    The ChainOperator chains two feature extraction modules:
        model2.compute(model1.compute(X,y),y)
    Where X can be generic input data.
    
    Args:
        model1 [AbstractFeature]
        model2 [AbstractFeature]
    """
    def __init__(self,model1,model2):
        FeatureOperator.__init__(self,model1,model2)
        
    def compute(self,X,y):
        X = self.model1.compute(X,y)
        return self.model2.compute(X,y)
        
    def extract(self,X):
        X = self.model1.extract(X)
        return self.model2.extract(X)
    
    def __repr__(self):
        return "ChainOperator(" + repr(self.model1) + "," + repr(self.model2) + ")"
        
class CombineOperator(FeatureOperator):
    """
    The CombineOperator combines the output of two feature extraction modules as:
      (model1.compute(X,y),model2.compute(X,y))
    , where    the output of each feature is a [1xN] or [Nx1] feature vector.
        
        
    Args:
        model1 [AbstractFeature]
        model2 [AbstractFeature]
        
    """
    def __init__(self,model1,model2):
        FeatureOperator.__init__(self, model1, model2)
        
    def compute(self,X,y):
        A = self.model1.compute(X,y)
        B = self.model2.compute(X,y)
        C = []
        for i in range(0, len(A)):
            ai = np.asarray(A[i]).reshape(1,-1)
            bi = np.asarray(B[i]).reshape(1,-1)
            C.append(np.hstack((ai,bi)))
        return C
    
    def extract(self,X):
        ai = self.model1.extract(X)
        bi = self.model2.extract(X)
        ai = np.asarray(ai).reshape(1,-1)
        bi = np.asarray(bi).reshape(1,-1)
        return np.hstack((ai,bi))

    def __repr__(self):
        return "CombineOperator(" + repr(self.model1) + "," + repr(self.model2) + ")"
        
class CombineOperatorND(FeatureOperator):
    """
    The CombineOperator combines the output of two multidimensional feature extraction modules.
        (model1.compute(X,y),model2.compute(X,y))
        
    Args:
        model1 [AbstractFeature]
        model2 [AbstractFeature]
        hstack [bool] stacks data horizontally if True and vertically if False
        
    """
    def __init__(self,model1,model2, hstack=True):
        FeatureOperator.__init__(self, model1, model2)
        self._hstack = hstack
        
    def compute(self,X,y):
        A = self.model1.compute(X,y)
        B = self.model2.compute(X,y)
        C = []
        for i in range(0, len(A)):
            if self._hstack:
                C.append(np.hstack((A[i],B[i])))
            else:
                C.append(np.vstack((A[i],B[i])))
        return C
    
    def extract(self,X):
        ai = self.model1.extract(X)
        bi = self.model2.extract(X)
        if self._hstack:
            return np.hstack((ai,bi))
        return np.vstack((ai,bi))

    def __repr__(self):
        return "CombineOperatorND(" + repr(self.model1) + "," + repr(self.model2) + ", hstack=" + str(self._hstack) + ")"

########NEW FILE########
__FILENAME__ = preprocessing
import numpy as np
from facerec.feature import AbstractFeature
from facerec.util import asColumnMatrix
from scipy import ndimage
    
class HistogramEqualization(AbstractFeature):
    def __init__(self, num_bins=256):
        AbstractFeature.__init__(self)
        self._num_bins = num_bins
        
    def compute(self,X,y):
        Xp = []
        for xi in X:
            Xp.append(self.extract(xi))
        return Xp
        
    def extract(self,X):
        h, b = np.histogram(X.flatten(), self._num_bins, normed=True)
        cdf = h.cumsum()
        cdf = 255 * cdf / cdf[-1]
        return np.interp(X.flatten(), b[:-1], cdf).reshape(X.shape)
    
    def __repr__(self):
        return "HistogramEqualization (num_bins=%s)" % (self._num_bins)
        
class TanTriggsPreprocessing(AbstractFeature):
    def __init__(self, alpha = 0.1, tau = 10.0, gamma = 0.2, sigma0 = 1.0, sigma1 = 2.0):
        AbstractFeature.__init__(self)
        self._alpha = float(alpha)
        self._tau = float(tau)
        self._gamma = float(gamma)
        self._sigma0 = float(sigma0)
        self._sigma1 = float(sigma1)
    
    def compute(self,X,y):
        Xp = []
        for xi in X:
            Xp.append(self.extract(xi))
        return Xp

    def extract(self,X):
        X = np.array(X, dtype=np.float32)
        X = np.power(X,self._gamma)
        X = np.asarray(ndimage.gaussian_filter(X,self._sigma1) - ndimage.gaussian_filter(X,self._sigma0))
        X = X / np.power(np.mean(np.power(np.abs(X),self._alpha)), 1.0/self._alpha)
        X = X / np.power(np.mean(np.power(np.minimum(np.abs(X),self._tau),self._alpha)), 1.0/self._alpha)
        X = self._tau*np.tanh(X/self._tau)
        return X

    def __repr__(self):
        return "TanTriggsPreprocessing (alpha=%.3f,tau=%.3f,gamma=%.3f,sigma0=%.3f,sigma1=%.3f)" % (self._alpha,self._tau,self._gamma,self._sigma0,self._sigma1)

from facerec.lbp import ExtendedLBP

class LBPPreprocessing(AbstractFeature):

    def __init__(self, lbp_operator = ExtendedLBP(radius=1, neighbors=8)):
        AbstractFeature.__init__(self)
        self._lbp_operator = lbp_operator
    
    def compute(self,X,y):
        Xp = []
        for xi in X:
            Xp.append(self.extract(xi))
        return Xp

    def extract(self,X):
        return self._lbp_operator(X)

    def __repr__(self):
        return "LBPPreprocessing (lbp_operator=%s)" % (repr(self._lbp_operator))

from facerec.normalization import zscore, minmax

class MinMaxNormalizePreprocessing(AbstractFeature):
    def __init__(self, low=0, high=1):
        AbstractFeature.__init__(self)
        self._low = low
        self._high = high
        
    def compute(self,X,y):
        Xp = []
        XC = asColumnMatrix(X)
        self._min = np.min(XC)
        self._max = np.max(XC)
        for xi in X:
            Xp.append(self.extract(xi))
        return Xp
    
    def extract(self,X):
        return minmax(X, self._low, self._high, self._min, self._max)
        
    def __repr__(self):
        return "MinMaxNormalizePreprocessing (low=%s, high=%s)" % (self._low, self._high)
        
class ZScoreNormalizePreprocessing(AbstractFeature):
    def __init__(self):
        AbstractFeature.__init__(self)
        self._mean = 0.0 
        self._std = 1.0
        
    def compute(self,X,y):
        XC = asColumnMatrix(X)
        self._mean = XC.mean()
        self._std = XC.std()
        Xp = []
        for xi in X:
            Xp.append(self.extract(xi))
        return Xp
    
    def extract(self,X):
        return zscore(X,self._mean, self._std)

    def __repr__(self):
        return "ZScoreNormalizePreprocessing (mean=%s, std=%s)" % (self._mean, self._std)

########NEW FILE########
__FILENAME__ = serialization
import cPickle

def save_model(filename, model):
    output = open(filename, 'wb')
    cPickle.dump(model, output)
    output.close()
    
def load_model(filename):
    pkl_file = open(filename, 'rb')
    res = cPickle.load(pkl_file)
    pkl_file.close()
    return res

########NEW FILE########
__FILENAME__ = svm
from facerec.classifier import SVM
from facerec.validation import KFoldCrossValidation
from facerec.model import PredictableModel
from svmutil import *
from itertools import product
import numpy as np
import logging


def range_f(begin, end, step):
    seq = []
    while True:
        if step == 0: break
        if step > 0 and begin > end: break
        if step < 0 and begin < end: break
        seq.append(begin)
        begin = begin + step
    return seq

def grid(grid_parameters):
    grid = []
    for parameter in grid_parameters:
        begin, end, step = parameter
        grid.append(range_f(begin, end, step))
    return product(*grid)

def grid_search(model, X, y, C_range=(-5,  15, 2), gamma_range=(3, -15, -2), k=5, num_cores=1):
    
    if not isinstance(model, PredictableModel):
        raise TypeError("GridSearch expects a PredictableModel. If you want to perform optimization on raw data use facerec.feature.Identity to pass unpreprocessed data!")
    if not isinstance(model.classifier, SVM):
        raise TypeError("GridSearch expects a SVM as classifier. Please use a facerec.classifier.SVM!")
    
    logger = logging.getLogger("facerec.svm.gridsearch")
    logger.info("Performing a Grid Search.")
    
    # best parameter combination to return
    best_parameter = svm_parameter("-q")
    best_parameter.kernel_type = model.classifier.param.kernel_type
    best_parameter.nu = model.classifier.param.nu
    best_parameter.coef0 = model.classifier.param.coef0
    # either no gamma given or kernel is linear (only C to optimize)
    if (gamma_range is None) or (model.classifier.param.kernel_type == LINEAR):
        gamma_range = (0, 0, 1)
    
    # best validation error so far
    best_accuracy = np.finfo('float').min
    
    # create grid (cartesian product of ranges)        
    g = grid([C_range, gamma_range])
    results = []
    for p in g:
        C, gamma = p
        C, gamma = 2**C, 2**gamma
        model.classifier.param.C, model.classifier.param.gamma = C, gamma

        # perform a k-fold cross validation
        cv = KFoldCrossValidation(model=model,k=k)
        cv.validate(X,y)

        # append parameter into list with accuracies for all parameter combinations
        results.append([C, gamma, cv.accuracy])
        
        # store best parameter combination
        if cv.accuracy > best_accuracy:
            logger.info("best_accuracy=%s" % (cv.accuracy))
            best_accuracy = cv.accuracy
            best_parameter.C, best_parameter.gamma = C, gamma
        
        logger.info("%d-CV Result = %.2f." % (k, cv.accuracy))
        
    # set best parameter combination to best found
    return best_parameter, results

########NEW FILE########
__FILENAME__ = util
import numpy as np
import random
from scipy import ndimage

def read_image(filename):
    imarr = np.array([])
    try:
        im = Image.open(os.path.join(filename))
        im = im.convert("L") # convert to greyscale
        imarr = np.array(im, dtype=np.uint8)
    except IOError as (errno, strerror):
        print "I/O error({0}): {1}".format(errno, strerror)
    except:
        print "Cannot open image."
    return imarr

def asRowMatrix(X):
    """
    Creates a row-matrix from multi-dimensional data items in list l.
    
    X [list] List with multi-dimensional data.
    """
    if len(X) == 0:
        return np.array([])
    total = 1
    for i in range(0, np.ndim(X[0])):
        total = total * X[0].shape[i]
    mat = np.empty([0, total], dtype=X[0].dtype)
    for row in X:
        mat = np.append(mat, row.reshape(1,-1), axis=0) # same as vstack
    return np.asmatrix(mat)

def asColumnMatrix(X):
    """
    Creates a column-matrix from multi-dimensional data items in list l.
    
    X [list] List with multi-dimensional data.
    """
    if len(X) == 0:
        return np.array([])
    total = 1
    for i in range(0, np.ndim(X[0])):
        total = total * X[0].shape[i]
    mat = np.empty([total, 0], dtype=X[0].dtype)
    for col in X:
        mat = np.append(mat, col.reshape(-1,1), axis=1) # same as hstack
    return np.asmatrix(mat)


def minmax_normalize(X, low, high, minX=None, maxX=None, dtype=np.float):
    """ min-max normalize a given matrix to given range [low,high].
    
    Args:
        X [rows x columns] input data
        low [numeric] lower bound
        high [numeric] upper bound
    """
    if minX is None:
        minX = np.min(X)
    if maxX is None:
        maxX = np.max(X)
    minX = float(minX)
    maxX = float(maxX)
    # Normalize to [0...1].    
    X = X - minX
    X = X / (maxX - minX)
    # Scale to [low...high].
    X = X * (high-low)
    X = X + low
    return np.asarray(X, dtype=dtype)

def zscore(X):
    X = np.asanyarray(X)
    mean = X.mean()
    std = X.std() 
    X = (X-mean)/std
    return X, mean, std

def shuffle(X,y):
    idx = np.argsort([random.random() for i in xrange(y.shape[0])])
    return X[:,idx], y[idx]

########NEW FILE########
__FILENAME__ = validation
import numpy as np
import math as math
import random as random
import logging

from facerec.model import PredictableModel
from facerec.classifier import AbstractClassifier

# TODO The evaluation of a model should be completely moved to the generic ValidationStrategy. The specific Validation 
#       implementations should only care about partition the data, which would make a lot sense. Currently it is not 
#       possible to calculate the true_negatives and false_negatives with the way the predicitions are generated and 
#       data is prepared.
#       
#     The mentioned problem makes a change in the PredictionResult necessary, which basically means refactoring the 
#       entire framework. The refactoring is planned, but I can't give any details as time of writing.
#
#     Please be careful, when referring to the Performance Metrics at the moment, only the Precision is implemented,
#       and the rest has no use at the moment. Due to the missing refactoring discussed above.
#

def shuffle(X, y):
    """ Shuffles two arrays by column (len(X) == len(y))
        
        Args:
        
            X [dim x num_data] input data
            y [1 x num_data] classes

        Returns:

            Shuffled input arrays.
    """
    idx = np.argsort([random.random() for i in xrange(len(y))])
    y = np.asarray(y)
    X = [X[i] for i in idx]
    y = y[idx]
    return (X, y)
    
def slice_2d(X,rows,cols):
    """
    
    Slices a 2D list to a flat array. If you know a better approach, please correct this.
    
    Args:
    
        X [num_rows x num_cols] multi-dimensional data
        rows [list] rows to slice
        cols [list] cols to slice
    
    Example:
    
        >>> X=[[1,2,3,4],[5,6,7,8]]
        >>> # slice first two rows and first column
        >>> Commons.slice(X, range(0,2), range(0,1)) # returns [1, 5]
        >>> Commons.slice(X, range(0,1), range(0,4)) # returns [1,2,3,4]
    """
    return [X[i][j] for j in cols for i in rows]

def precision(true_positives, false_positives):
    """Returns the precision, calculated as:
        
        true_positives/(true_positives+false_positives)
        
    """
    return accuracy(true_positives, 0, false_positives, 0)
    
def accuracy(true_positives, true_negatives, false_positives, false_negatives, description=None):
    """Returns the accuracy, calculated as:
    
        (true_positives+true_negatives)/(true_positives+false_positives+true_negatives+false_negatives)
        
    """
    true_positives = float(true_positives)
    true_negatives = float(true_negatives)
    false_positives = float(false_positives)
    false_negatives = float(false_negatives)
    if (true_positives + true_negatives + false_positives + false_negatives) < 1e-15:
       return 0.0
    return (true_positives+true_negatives)/(true_positives+false_positives+true_negatives+false_negatives)

class ValidationResult(object):
    """Holds a validation result.
    """
    def __init__(self, true_positives, true_negatives, false_positives, false_negatives, description):
        self.true_positives = true_positives
        self.true_negatives = true_negatives
        self.false_positives = false_positives
        self.false_negatives = false_negatives
        self.description = description
        
    def __repr__(self):
        res_precision = precision(self.true_positives, self.false_positives) * 100
        res_accuracy = accuracy(self.true_positives, self.true_negatives, self.false_positives, self.false_negatives) * 100
        return "ValidationResult (Description=%s, Precision=%.2f%%, Accuracy=%.2f%%)" % (self.description, res_precision, res_accuracy)
    
class ValidationStrategy(object):
    """ Represents a generic Validation kernel for all Validation strategies.
    """
    def __init__(self, model):
        """    
        Initialize validation with empty results.
        
        Args:
        
            model [PredictableModel] The model, which is going to be validated.
        """
        if not isinstance(model,PredictableModel):
            raise TypeError("Validation can only validate the type PredictableModel.")
        self.model = model
        self.validation_results = []
    
    def add(self, validation_result):
        self.validation_results.append(validation_result)
        
    def validate(self, X, y, description):
        """
        
        Args:
            X [list] Input Images
            y [y] Class Labels
            description [string] experiment description
        
        """
        raise NotImplementedError("Every Validation module must implement the validate method!")
        
    
    def print_results(self):
        print self.model
        for validation_result in self.validation_results:
            print validation_result

    def __repr__(self):
        return "Validation Kernel (model=%s)" % (self.model)
        
class KFoldCrossValidation(ValidationStrategy):
    """ 
    
    Divides the Data into 10 equally spaced and non-overlapping folds for training and testing.
    
    Here is a 3-fold cross validation example for 9 observations and 3 classes, so each observation is given by its index [c_i][o_i]:
                
        o0 o1 o2        o0 o1 o2        o0 o1 o2  
    c0 | A  B  B |  c0 | B  A  B |  c0 | B  B  A |
    c1 | A  B  B |  c1 | B  A  B |  c1 | B  B  A |
    c2 | A  B  B |  c2 | B  A  B |  c2 | B  B  A |
    
    Please note: If there are less than k observations in a class, k is set to the minimum of observations available through all classes.
    """
    def __init__(self, model, k=10):
        """
        Args:
            k [int] number of folds in this k-fold cross-validation (default 10)
        """
        super(KFoldCrossValidation, self).__init__(model=model)
        self.k = k
        self.logger = logging.getLogger("facerec.validation.KFoldCrossValidation")

    def validate(self, X, y, description="ExperimentName"):
        """ Performs a k-fold cross validation
        
        Args:

            X [dim x num_data] input data to validate on
            y [1 x num_data] classes
        """
        X,y = shuffle(X,y)
        c = len(np.unique(y))
        foldIndices = []
        n = np.iinfo(np.int).max
        for i in range(0,c):
            idx = np.where(y==i)[0]
            n = min(n, idx.shape[0])
            foldIndices.append(idx.tolist()); 

        # I assume all folds to be of equal length, so the minimum
        # number of samples in a class is responsible for the number
        # of folds. This is probably not desired. Please adjust for
        # your use case.
        if n < self.k:
            self.k = n

        foldSize = int(math.floor(n/self.k))
        
        true_positives, false_positives, true_negatives, false_negatives = (0,0,0,0)
        for i in range(0,self.k):
        
            self.logger.info("Processing fold %d/%d." % (i+1, self.k))
                
            # calculate indices
            l = int(i*foldSize)
            h = int((i+1)*foldSize)
            testIdx = slice_2d(foldIndices, cols=range(l,h), rows=range(0, c))
            trainIdx = slice_2d(foldIndices,cols=range(0,l), rows=range(0,c))
            trainIdx.extend(slice_2d(foldIndices,cols=range(h,n),rows=range(0,c)))
            
            # build training data subset
            Xtrain = [X[t] for t in trainIdx]
            ytrain = y[trainIdx]
                        
            self.model.compute(Xtrain, ytrain)
            
            # TODO I have to add the true_negatives and false_negatives. Models also need to support it,
            # so we should use a PredictionResult, instead of trying to do this by simply comparing
            # the predicted and actual class.
            #
            # This is inteneded of the next version! Feel free to contribute.
            for j in testIdx:
                prediction = self.model.predict(X[j])[0]
                if prediction == y[j]:
                    true_positives = true_positives + 1
                else:
                    false_positives = false_positives + 1
                    
        self.add(ValidationResult(true_positives, true_negatives, false_positives, false_negatives, description))
    
    def __repr__(self):
        return "k-Fold Cross Validation (model=%s, k=%s)" % (self.model, self.k)

class LeaveOneOutCrossValidation(ValidationStrategy):
    """ Leave-One-Cross Validation (LOOCV) uses one observation for testing and the rest for training a classifier:

        o0 o1 o2        o0 o1 o2        o0 o1 o2           o0 o1 o2
    c0 | A  B  B |  c0 | B  A  B |  c0 | B  B  A |     c0 | B  B  B |
    c1 | B  B  B |  c1 | B  B  B |  c1 | B  B  B |     c1 | B  B  B |
    c2 | B  B  B |  c2 | B  B  B |  c2 | B  B  B | ... c2 | B  B  A |
    
    Arguments:
        model [Model] model for this validation
        ... see [Validation]
    """

    def __init__(self, model):
        """ Intialize Cross-Validation module.
        
        Args:
            model [Model] model for this validation
        """
        super(LeaveOneOutCrossValidation, self).__init__(model=model)
        self.logger = logging.getLogger("facerec.validation.LeaveOneOutCrossValidation")
        
    def validate(self, X, y, description="ExperimentName"):
        """ Performs a LOOCV.
        
        Args:
            X [dim x num_data] input data to validate on
            y [1 x num_data] classes
        """
        #(X,y) = shuffle(X,y)
        true_positives, false_positives, true_negatives, false_negatives = (0,0,0,0)
        n = y.shape[0]
        for i in range(0,n):
            
            self.logger.info("Processing fold %d/%d." % (i+1, n))
            
            # create train index list
            trainIdx = []
            trainIdx.extend(range(0,i))
            trainIdx.extend(range(i+1,n))
            
            # build training data/test data subset
            Xtrain = [X[t] for t in trainIdx]
            ytrain = y[trainIdx]
            
            # compute the model
            self.model.compute(Xtrain, ytrain)
            
            # get prediction
            prediction = self.model.predict(X[i])[0]
            if prediction == y[i]:
                true_positives = true_positives + 1
            else:
                false_positives = false_positives + 1
                
        self.add(ValidationResult(true_positives, true_negatives, false_positives, false_negatives, description))
    
    def __repr__(self):
        return "Leave-One-Out Cross Validation (model=%s)" % (self.model)

class LeaveOneClassOutCrossValidation(ValidationStrategy):
    """ Leave-One-Cross Validation (LOOCV) uses one observation for testing and the rest for training a classifier:

        o0 o1 o2        o0 o1 o2        o0 o1 o2           o0 o1 o2
    c0 | A  B  B |  c0 | B  A  B |  c0 | B  B  A |     c0 | B  B  B |
    c1 | B  B  B |  c1 | B  B  B |  c1 | B  B  B |     c1 | B  B  B |
    c2 | B  B  B |  c2 | B  B  B |  c2 | B  B  B | ... c2 | B  B  A |
    
    Arguments:
        model [Model] model for this validation
        ... see [Validation]
    """

    def __init__(self, model):
        """ Intialize Cross-Validation module.
        
        Args:
            model [Model] model for this validation
        """
        super(LeaveOneClassOutCrossValidation, self).__init__(model=model)
        self.logger = logging.getLogger("facerec.validation.LeaveOneClassOutCrossValidation")
        
    def validate(self, X, y, g, description="ExperimentName"):
        """
        TODO Add example and refactor into proper interface declaration.
        """
        true_positives, false_positives, true_negatives, false_negatives = (0,0,0,0)
        
        for i in range(0,len(np.unique(y))):
            self.logger.info("Validating Class %s." % i)
            # create folds
            trainIdx = np.where(y!=i)[0]
            testIdx = np.where(y==i)[0]
            # build training data/test data subset
            Xtrain = [X[t] for t in trainIdx]
            gtrain = g[trainIdx]
            
            # Compute the model, this time on the group:
            self.model.compute(Xtrain, gtrain)
            
            for j in testIdx:
                # get prediction
                prediction = self.model.predict(X[j])[0]
                if prediction == g[j]:
                    true_positives = true_positives + 1
                else:
                    false_positives = false_positives + 1
        self.add(ValidationResult(true_positives, true_negatives, false_positives, false_negatives, description))
    
    def __repr__(self):
        return "Leave-One-Class-Out Cross Validation (model=%s)" % (self.model)

class SimpleValidation(ValidationStrategy):
    """Implements a simple Validation, which allows you to partition the data yourself.
    """
    def __init__(self, model):
        """
        Args:
            model [PredictableModel] model to perform the validation on
        """
        super(SimpleValidation, self).__init__(model=model)
        self.logger = logging.getLogger("facerec.validation.SimpleValidation")
            
    def validate(self, X, y, trainIndices, testIndices, description="ExperimentName"):
        """
        Performs a validation given training data and test data. User is responsible for non-overlapping assignment of indices.

        Args:
            X [dim x num_data] input data to validate on
            y [1 x num_data] classes
        """
        self.logger.info("Simple Validation.")
        
        Xtrain = [X[t] for t in trainIndices]
        ytrain = y[trainIndices]
        
        self.model.compute(Xtrain, ytrain)

        self.logger.debug("Model computed.")

        true_positives, false_positives, true_negatives, false_negatives = (0,0,0,0)
        count = 0
        for i in testIndices:
            self.logger.debug("Predicting %s/%s." % (count, len(testIndices)))
            prediction = self.model.predict(X[i])[0]
            if prediction == y[i]:
                true_positives = true_positives + 1
            else:
                false_positives = false_positives + 1
            count = count + 1
        self.add(ValidationResult(true_positives, true_negatives, false_positives, false_negatives, description))
        
    def __repr__(self):
        return "Simple Validation (model=%s)" % (self.model)

########NEW FILE########
__FILENAME__ = visual
from facerec.normalization import minmax

import os as os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import PIL.Image as Image

import math as math


def create_font(fontname='Tahoma', fontsize=10):
    return { 'fontname': fontname, 'fontsize':fontsize }

def plot_gray(X,  sz=None, filename=None):
    if not sz is None:
        X = X.reshape(sz)
    X = minmax(I, 0, 255)
    fig = plt.figure()
    implot = plt.imshow(np.asarray(Ig), cmap=cm.gray)
    if filename is None:
        plt.show()
    else:
        fig.savefig(filename, format="png", transparent=False)
    
def plot_eigenvectors(eigenvectors, num_components, sz, filename=None, start_component=0, rows = None, cols = None, title="Subplot", color=True):
        if (rows is None) or (cols is None):
            rows = cols = int(math.ceil(np.sqrt(num_components)))
        num_components = np.min(num_components, eigenvectors.shape[1])
        fig = plt.figure()
        for i in range(start_component, num_components):
            vi = eigenvectors[0:,i].copy()
            vi = minmax(np.asarray(vi), 0, 255, dtype=np.uint8)
            vi = vi.reshape(sz)
            
            ax0 = fig.add_subplot(rows,cols,(i-start_component)+1)
            
            plt.setp(ax0.get_xticklabels(), visible=False)
            plt.setp(ax0.get_yticklabels(), visible=False)
            plt.title("%s #%d" % (title, i), create_font('Tahoma',10))
            if color:
                implot = plt.imshow(np.asarray(vi))
            else:
                implot = plt.imshow(np.asarray(vi), cmap=cm.grey)
        if filename is None:
            fig.show()
        else:
            fig.savefig(filename, format="png", transparent=False)
            
def subplot(title, images, rows, cols, sptitle="subplot", sptitles=[], colormap=cm.gray, ticks_visible=True, filename=None):
    fig = plt.figure()
    # main title
    fig.text(.5, .95, title, horizontalalignment='center') 
    for i in xrange(len(images)):
        ax0 = fig.add_subplot(rows,cols,(i+1))
        plt.setp(ax0.get_xticklabels(), visible=False)
        plt.setp(ax0.get_yticklabels(), visible=False)
        if len(sptitles) == len(images):
            plt.title("%s #%s" % (sptitle, str(sptitles[i])), create_font('Tahoma',10))
        else:
            plt.title("%s #%d" % (sptitle, (i+1)), create_font('Tahoma',10))
        plt.imshow(np.asarray(images[i]), cmap=colormap)
    if filename is None:
        plt.show()
    else:
        fig.savefig(filename)


# using plt plot:
#filename="/home/philipp/facerec/at_database_vs_accuracy_xy.png"
#t = np.arange(2., 10., 1.)
#fig = plt.figure()
#plt.plot(t, r0, 'k--', t, r1, 'k')
#plt.legend(("Eigenfaces", "Fisherfaces"), 'lower right', shadow=True, fancybox=True)
#plt.ylim(0,1)
#plt.ylabel('Recognition Rate')
#plt.xlabel('Database Size (Images per Person)')
#fig.savefig(filename, format="png", transparent=False)
#plt.show()



########NEW FILE########
