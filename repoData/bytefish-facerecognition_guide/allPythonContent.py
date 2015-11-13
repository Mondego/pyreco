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
  rotation = -math.atan2(float(eye_direction[1]),float(eye_direction[0]))
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
  CropFace(image, eye_left=(252,364), eye_right=(420,366), offset_pct=(0.1,0.1), dest_sz=(200,200)).save("arnie_10_10_200_200.jpg")
  CropFace(image, eye_left=(252,364), eye_right=(420,366), offset_pct=(0.2,0.2), dest_sz=(200,200)).save("arnie_20_20_200_200.jpg")
  CropFace(image, eye_left=(252,364), eye_right=(420,366), offset_pct=(0.3,0.3), dest_sz=(200,200)).save("arnie_30_30_200_200.jpg")
  CropFace(image, eye_left=(252,364), eye_right=(420,366), offset_pct=(0.2,0.2)).save("arnie_20_20_70_70.jpg")

########NEW FILE########
__FILENAME__ = example_eigenfaces
import sys
# append tinyfacerec to module search path
sys.path.append("..")
# import numpy and matplotlib colormaps
import numpy as np
# import tinyfacerec modules
from tinyfacerec.subspace import pca
from tinyfacerec.util import normalize, asRowMatrix, read_images
from tinyfacerec.visual import subplot

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print "USAGE: example_eigenfaces.py </path/to/images>"
        sys.exit()
    
    # read images
    [X,y] = read_images(sys.argv[1])

    # perform a full pca
    [D, W, mu] = pca(asRowMatrix(X), y)

    import matplotlib.cm as cm

    # turn the first (at most) 16 eigenvectors into grayscale
    # images (note: eigenvectors are stored by column!)
    E = []
    for i in xrange(min(len(X), 16)):
	    e = W[:,i].reshape(X[0].shape)
	    E.append(normalize(e,0,255))
    # plot them and store the plot to "python_eigenfaces.pdf"
    subplot(title="Eigenfaces AT&T Facedatabase", images=E, rows=4, cols=4, sptitle="Eigenface", colormap=cm.jet, filename="python_pca_eigenfaces.png")

    from tinyfacerec.subspace import project, reconstruct

    # reconstruction steps
    steps=[i for i in xrange(10, min(len(X), 320), 20)]
    E = []
    for i in xrange(min(len(steps), 16)):
	    numEvs = steps[i]
	    P = project(W[:,0:numEvs], X[0].reshape(1,-1), mu)
	    R = reconstruct(W[:,0:numEvs], P, mu)
	    # reshape and append to plots
	    R = R.reshape(X[0].shape)
	    E.append(normalize(R,0,255))
    # plot them and store the plot to "python_reconstruction.pdf"
    subplot(title="Reconstruction AT&T Facedatabase", images=E, rows=4, cols=4, sptitle="Eigenvectors", sptitles=steps, colormap=cm.gray, filename="python_pca_reconstruction.png")

########NEW FILE########
__FILENAME__ = example_fisherfaces
import sys
# append tinyfacerec to module search path
sys.path.append("..")
# import numpy and matplotlib colormaps
import numpy as np
# import tinyfacerec modules
from tinyfacerec.subspace import fisherfaces
from tinyfacerec.util import normalize, asRowMatrix, read_images
from tinyfacerec.visual import subplot

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print "USAGE: example_fisherfaces.py </path/to/images>"
        sys.exit()

    # read images
    [X,y] = read_images(sys.argv[1])
    # perform a full pca
    [D, W, mu] = fisherfaces(asRowMatrix(X), y)
    #import colormaps
    import matplotlib.cm as cm
    # turn the first (at most) 16 eigenvectors into grayscale
    # images (note: eigenvectors are stored by column!)
    E = []
    for i in xrange(min(W.shape[1], 16)):
	    e = W[:,i].reshape(X[0].shape)
	    E.append(normalize(e,0,255))
    # plot them and store the plot to "python_fisherfaces_fisherfaces.pdf"
    subplot(title="Fisherfaces AT&T Facedatabase", images=E, rows=4, cols=4, sptitle="Fisherface", colormap=cm.jet, filename="python_fisherfaces_fisherfaces.png")

    from tinyfacerec.subspace import project, reconstruct

    E = []
    for i in xrange(min(W.shape[1], 16)):
	    e = W[:,i].reshape(-1,1)
	    P = project(e, X[0].reshape(1,-1), mu)
	    R = reconstruct(e, P, mu)
	    # reshape and append to plots
	    R = R.reshape(X[0].shape)
	    E.append(normalize(R,0,255))
    # plot them and store the plot to "python_reconstruction.pdf"
    subplot(title="Fisherfaces Reconstruction Yale FDB", images=E, rows=4, cols=4, sptitle="Fisherface", colormap=cm.gray, filename="python_fisherfaces_reconstruction.png")

########NEW FILE########
__FILENAME__ = example_model_eigenfaces
import sys
# append tinyfacerec to module search path
sys.path.append("..")
# import numpy and matplotlib colormaps
import numpy as np
# import tinyfacerec modules
from tinyfacerec.util import read_images
from tinyfacerec.model import EigenfacesModel

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print "USAGE: example_model_eigenfaces.py </path/to/images>"
        sys.exit()
    
    # read images
    [X,y] = read_images(sys.argv[1])
    # compute the eigenfaces model
    model = EigenfacesModel(X[1:], y[1:])
    # get a prediction for the first observation
    print "expected =", y[0], "/", "predicted =", model.predict(X[0])

########NEW FILE########
__FILENAME__ = example_model_fisherfaces
import sys
# append tinyfacerec to module search path
sys.path.append("..")
# import numpy and matplotlib colormaps
import numpy as np
# import tinyfacerec modules
from tinyfacerec.util import read_images
from tinyfacerec.model import FisherfacesModel

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print "USAGE: example_model_fisherfaces.py </path/to/images>"
        sys.exit()
    
    # read images
    [X,y] = read_images(sys.argv[1])
    # compute the eigenfaces model
    model = FisherfacesModel(X[1:], y[1:])
    # get a prediction for the first observation
    print "expected =", y[0], "/", "predicted =", model.predict(X[0])

########NEW FILE########
__FILENAME__ = example_pca
import sys
# append tinyfacerec to module search path
sys.path.append("..")
# import numpy and matplotlib colormaps
import numpy as np
# import tinyfacerec modules
from tinyfacerec.subspace import pca
from tinyfacerec.util import normalize, asRowMatrix, read_images
from tinyfacerec.visual import subplot

# read images
[X,y] = read_images("/home/philipp/facerec/data/at")
# perform a full pca
[D, W, mu] = pca(asRowMatrix(X), y)

import matplotlib.cm as cm

# turn the first (at most) 16 eigenvectors into grayscale
# images (note: eigenvectors are stored by column!)
E = []
for i in xrange(min(len(X), 16)):
	e = W[:,i].reshape(X[0].shape)
	E.append(normalize(e,0,255))
# plot them and store the plot to "python_eigenfaces.pdf"
subplot(title="Eigenfaces AT&T Facedatabase", images=E, rows=4, cols=4, sptitle="Eigenface", colormap=cm.jet, filename="python_pca_eigenfaces.pdf")

from tinyfacerec.subspace import project, reconstruct

# reconstruction steps
steps=[i for i in xrange(10, min(len(X), 320), 20)]
E = []
for i in xrange(min(len(steps), 16)):
	numEvs = steps[i]
	P = project(W[:,0:numEvs], X[0].reshape(1,-1), mu)
	R = reconstruct(W[:,0:numEvs], P, mu)
	# reshape and append to plots
	R = R.reshape(X[0].shape)
	E.append(normalize(R,0,255))
# plot them and store the plot to "python_reconstruction.pdf"
subplot(title="Reconstruction AT&T Facedatabase", images=E, rows=4, cols=4, sptitle="Eigenvectors", sptitles=steps, colormap=cm.gray, filename="python_pca_reconstruction.pdf")

########NEW FILE########
__FILENAME__ = distance
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

	def __init__(self):
		AbstractDistance.__init__(self,"CosineDistance")

	def __call__(self, p, q):
		p = np.asarray(p).flatten()
		q = np.asarray(q).flatten()
		return -np.dot(p.T,q) / (np.sqrt(np.dot(p,p.T)*np.dot(q,q.T)))


########NEW FILE########
__FILENAME__ = model
import numpy as np
from util import asRowMatrix
from subspace import pca, lda, fisherfaces, project
from distance import EuclideanDistance

class BaseModel(object):
	def __init__(self, X=None, y=None, dist_metric=EuclideanDistance(), num_components=0):
		self.dist_metric = dist_metric
		self.num_components = 0
		self.projections = []
		self.W = []
		self.mu = []
		if (X is not None) and (y is not None):
			self.compute(X,y)
	
	def compute(self, X, y):
		raise NotImplementedError("Every BaseModel must implement the compute method.")
		
	def predict(self, X):
		minDist = np.finfo('float').max
		minClass = -1
		Q = project(self.W, X.reshape(1,-1), self.mu)
		for i in xrange(len(self.projections)):
			dist = self.dist_metric(self.projections[i], Q)
			if dist < minDist:
				minDist = dist
				minClass = self.y[i]
		return minClass

class EigenfacesModel(BaseModel):

	def __init__(self, X=None, y=None, dist_metric=EuclideanDistance(), num_components=0):
		super(EigenfacesModel, self).__init__(X=X,y=y,dist_metric=dist_metric,num_components=num_components)

	def compute(self, X, y):
		[D, self.W, self.mu] = pca(asRowMatrix(X),y, self.num_components)
		# store labels
		self.y = y
		# store projections
		for xi in X:
			self.projections.append(project(self.W, xi.reshape(1,-1), self.mu))

class FisherfacesModel(BaseModel):

	def __init__(self, X=None, y=None, dist_metric=EuclideanDistance(), num_components=0):
		super(FisherfacesModel, self).__init__(X=X,y=y,dist_metric=dist_metric,num_components=num_components)

	def compute(self, X, y):
		[D, self.W, self.mu] = fisherfaces(asRowMatrix(X),y, self.num_components)
		# store labels
		self.y = y
		# store projections
		for xi in X:
			self.projections.append(project(self.W, xi.reshape(1,-1), self.mu))

########NEW FILE########
__FILENAME__ = subspace
import numpy as np

def project(W, X, mu=None):
	if mu is None:
		return np.dot(X,W)
	return np.dot(X - mu, W)

def reconstruct(W, Y, mu=None):
	if mu is None:
		return np.dot(Y,W.T)
	return np.dot(Y, W.T) + mu

def pca(X, y, num_components=0):
	[n,d] = X.shape
	if (num_components <= 0) or (num_components>n):
		num_components = n
	mu = X.mean(axis=0)
	X = X - mu
	if n>d:
		C = np.dot(X.T,X)
		[eigenvalues,eigenvectors] = np.linalg.eigh(C)
	else:
		C = np.dot(X,X.T)
		[eigenvalues,eigenvectors] = np.linalg.eigh(C)
		eigenvectors = np.dot(X.T,eigenvectors)
		for i in xrange(n):
			eigenvectors[:,i] = eigenvectors[:,i]/np.linalg.norm(eigenvectors[:,i])
	# or simply perform an economy size decomposition
	# eigenvectors, eigenvalues, variance = np.linalg.svd(X.T, full_matrices=False)
	# sort eigenvectors descending by their eigenvalue
	idx = np.argsort(-eigenvalues)
	eigenvalues = eigenvalues[idx]
	eigenvectors = eigenvectors[:,idx]
	# select only num_components
	eigenvalues = eigenvalues[0:num_components].copy()
	eigenvectors = eigenvectors[:,0:num_components].copy()
	return [eigenvalues, eigenvectors, mu]
		
def lda(X, y, num_components=0):
	y = np.asarray(y)
	[n,d] = X.shape
	c = np.unique(y)
	if (num_components <= 0) or (num_component>(len(c)-1)):
		num_components = (len(c)-1)
	meanTotal = X.mean(axis=0)
	Sw = np.zeros((d, d), dtype=np.float32)
	Sb = np.zeros((d, d), dtype=np.float32)
	for i in c:
		Xi = X[np.where(y==i)[0],:]
		meanClass = Xi.mean(axis=0)
		Sw = Sw + np.dot((Xi-meanClass).T, (Xi-meanClass))
		Sb = Sb + n * np.dot((meanClass - meanTotal).T, (meanClass - meanTotal))
	eigenvalues, eigenvectors = np.linalg.eig(np.linalg.inv(Sw)*Sb)
	idx = np.argsort(-eigenvalues.real)
	eigenvalues, eigenvectors = eigenvalues[idx], eigenvectors[:,idx]
	eigenvalues = np.array(eigenvalues[0:num_components].real, dtype=np.float32, copy=True)
	eigenvectors = np.array(eigenvectors[0:,0:num_components].real, dtype=np.float32, copy=True)
	return [eigenvalues, eigenvectors]

def fisherfaces(X,y,num_components=0):
	y = np.asarray(y)
	[n,d] = X.shape
	c = len(np.unique(y))
	[eigenvalues_pca, eigenvectors_pca, mu_pca] = pca(X, y, (n-c))
	[eigenvalues_lda, eigenvectors_lda] = lda(project(eigenvectors_pca, X, mu_pca), y, num_components)
	eigenvectors = np.dot(eigenvectors_pca,eigenvectors_lda)
	return [eigenvalues_lda, eigenvectors, mu_pca]

########NEW FILE########
__FILENAME__ = util
import os, sys
import numpy as np
import PIL.Image as Image

def normalize(X, low, high, dtype=None):
	X = np.asarray(X)
	minX, maxX = np.min(X), np.max(X)
	# normalize to [0...1].	
	X = X - float(minX)
	X = X / float((maxX - minX))
	# scale to [low...high].
	X = X * (high-low)
	X = X + low
	if dtype is None:
		return np.asarray(X)
	return np.asarray(X, dtype=dtype)

def read_images(path, sz=None):
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
						im = im.resize(sz, Image.ANTIALIAS)
					X.append(np.asarray(im, dtype=np.uint8))
					y.append(c)
				except IOError:
					print "I/O error({0}): {1}".format(errno, strerror)
				except:
					print "Unexpected error:", sys.exc_info()[0]
					raise
			c = c+1
	return [X,y]

def asRowMatrix(X):
	if len(X) == 0:
		return np.array([])
	mat = np.empty((0, X[0].size), dtype=X[0].dtype)
	for row in X:
		mat = np.vstack((mat, np.asarray(row).reshape(1,-1)))
	return mat

def asColumnMatrix(X):
	if len(X) == 0:
		return np.array([])
	mat = np.empty((X[0].size, 0), dtype=X[0].dtype)
	for col in X:
		mat = np.hstack((mat, np.asarray(col).reshape(-1,1)))
	return mat

########NEW FILE########
__FILENAME__ = visual
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

def create_font(fontname='Tahoma', fontsize=10):
	return { 'fontname': fontname, 'fontsize':fontsize }

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
		
def imsave(image, title="", filename=None):
	plt.figure()
	plt.imshow(np.asarray(image))
	plt.title(title, create_font('Tahoma',10))
	if filename is None:
		plt.show()
	else:
		fig.savefig(filename)

########NEW FILE########
