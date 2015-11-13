__FILENAME__ = ch1_morphology
from PIL import Image
from numpy import *

from scipy.ndimage import measurements,morphology

"""
This is the morphology counting objects example in Section 1.4.
"""

# load image and threshold to make sure it is binary
im = array(Image.open('../data/houses.png').convert('L'))
im = (im<128)

labels, nbr_objects = measurements.label(im)
print "Number of objects:", nbr_objects

# morphology - opening to separate objects better
im_open = morphology.binary_opening(im,ones((9,5)),iterations=2) 

labels_open, nbr_objects_open = measurements.label(im_open)
print "Number of objects:", nbr_objects_open
########NEW FILE########
__FILENAME__ = ch1_rof_denoise
from pylab import *
from numpy import *
from numpy import random
from scipy.ndimage import filters
from scipy.misc import imsave

from PCV.tools import rof

"""
This is the de-noising example using ROF in Section 1.5.
"""

# create synthetic image with noise
im = zeros((500,500))
im[100:400,100:400] = 128
im[200:300,200:300] = 255
im = im + 30*random.standard_normal((500,500))

U,T = rof.denoise(im,im)
G = filters.gaussian_filter(im,10)


# save the result
imsave('synth_original.pdf',im)
imsave('synth_rof.pdf',U)
imsave('synth_gaussian.pdf',G)


# plot
figure()
gray()

subplot(1,3,1)
imshow(im)
axis('equal')
axis('off')

subplot(1,3,2)
imshow(G)
axis('equal')
axis('off')

subplot(1,3,3)
imshow(U)
axis('equal')
axis('off')

show()
########NEW FILE########
__FILENAME__ = ch2_download_panoramio
import os
import urllib, urlparse 
import json

"""
This is the Panoramio image download example from section 2.3.
"""

# query for images
url = 'http://www.panoramio.com/map/get_panoramas.php?order=popularity&set=public&from=0&to=20&minx=-77.037564&miny=38.896662&maxx=-77.035564&maxy=38.898662&size=medium'
c = urllib.urlopen(url)

# get the urls of individual images from JSON
j = json.loads(c.read()) 
imurls = []
for im in j['photos']:
    imurls.append(im['photo_file_url'])

# download images
for url in imurls:
    image = urllib.URLopener()
    image.retrieve(url, os.path.basename(urlparse.urlparse(url).path)) 
    print 'downloading:', url
########NEW FILE########
__FILENAME__ = ch2_harris_corners
from pylab import *
from numpy import *
from PIL import Image

from PCV.localdescriptors import harris

"""
Example of detecting Harris corner points (Figure 2-1 in the book).
"""

# open image
im = array(Image.open('../data/empire.jpg').convert('L'))

# detect corners and plot
harrisim = harris.compute_harris_response(im)
filtered_coords = harris.get_harris_points(harrisim, 10, threshold=0.01)
harris.plot_harris_points(im, filtered_coords)

# plot only 200 strongest
harris.plot_harris_points(im, filtered_coords[:200])
########NEW FILE########
__FILENAME__ = ch2_harris_matching
from pylab import *
from numpy import *
from PIL import Image

from PCV.localdescriptors import harris
from PCV.tools.imtools import imresize

"""
This is the Harris point matching example in Figure 2-2.
"""

im1 = array(Image.open("../data/crans_1_small.jpg").convert("L"))
im2 = array(Image.open("../data/crans_2_small.jpg").convert("L"))

# resize to make matching faster
im1 = imresize(im1,(im1.shape[1]/2,im1.shape[0]/2))
im2 = imresize(im2,(im2.shape[1]/2,im2.shape[0]/2))

wid = 5
harrisim = harris.compute_harris_response(im1,5) 
filtered_coords1 = harris.get_harris_points(harrisim,wid+1) 
d1 = harris.get_descriptors(im1,filtered_coords1,wid)

harrisim = harris.compute_harris_response(im2,5) 
filtered_coords2 = harris.get_harris_points(harrisim,wid+1) 
d2 = harris.get_descriptors(im2,filtered_coords2,wid)

print 'starting matching'
matches = harris.match_twosided(d1,d2)

figure()
gray() 
harris.plot_matches(im1,im2,filtered_coords1,filtered_coords2,matches) 
show()
########NEW FILE########
__FILENAME__ = ch2_matching_graph
from pylab import *
from numpy import *
from PIL import Image

from PCV.localdescriptors import sift
from PCV.tools import imtools

import pydot

"""
This is the example graph illustration of matching images from Figure 2-10.
To download the images, see ch2_download_panoramio.py.
"""

download_path = "panoimages" # set this to the path where you downloaded the panoramio images
path = "/FULLPATH/panoimages/" # path to save thumbnails (pydot needs the full system path)

# list of downloaded filenames
imlist = imtools.get_imlist(download_path)
nbr_images = len(imlist)

# extract features
featlist = [imname[:-3]+'sift' for imname in imlist]
for i,imname in enumerate(imlist):
    sift.process_image(imname, featlist[i])

matchscores = zeros((nbr_images,nbr_images))

for i in range(nbr_images):
    for j in range(i,nbr_images): # only compute upper triangle
        print 'comparing ', imlist[i], imlist[j]
        l1,d1 = sift.read_features_from_file(featlist[i]) 
        l2,d2 = sift.read_features_from_file(featlist[j])
        matches = sift.match_twosided(d1,d2)
        nbr_matches = sum(matches > 0)
        print 'number of matches = ', nbr_matches 
        matchscores[i,j] = nbr_matches

# copy values
for i in range(nbr_images):
    for j in range(i+1,nbr_images): # no need to copy diagonal
        matchscores[j,i] = matchscores[i,j]

threshold = 2 # min number of matches needed to create link

g = pydot.Dot(graph_type='graph') # don't want the default directed graph 

for i in range(nbr_images):
    for j in range(i+1,nbr_images):
        if matchscores[i,j] > threshold:
            # first image in pair
            im = Image.open(imlist[i])
            im.thumbnail((100,100))
            filename = path+str(i)+'.png'
            im.save(filename) # need temporary files of the right size 
            g.add_node(pydot.Node(str(i),fontcolor='transparent',shape='rectangle',image=filename))
    
            # second image in pair
            im = Image.open(imlist[j])
            im.thumbnail((100,100))
            filename = path+str(j)+'.png'
            im.save(filename) # need temporary files of the right size 
            g.add_node(pydot.Node(str(j),fontcolor='transparent',shape='rectangle',image=filename)) 
            
            g.add_edge(pydot.Edge(str(i),str(j)))

g.write_png('whitehouse.png')
########NEW FILE########
__FILENAME__ = ch2_match_features
from pylab import *
from numpy import *
from PIL import Image

from PCV.localdescriptors import sift

"""
This is the twosided SIFT feature matching example from Section 2.2 (p 44).
"""

imname1 = '../data/climbing_1_small.jpg'
imname2 = '../data/climbing_2_small.jpg'

# process and save features to file
sift.process_image(imname1, imname1+'.sift')
sift.process_image(imname2, imname2+'.sift')

# read features and match
l1,d1 = sift.read_features_from_file(imname1+'.sift')
l2,d2 = sift.read_features_from_file(imname2+'.sift')
matchscores = sift.match_twosided(d1, d2)

# load images and plot
im1 = array(Image.open(imname1))
im2 = array(Image.open(imname2))

sift.plot_matches(im1,im2,l1,l2,matchscores,show_below=True)
show()

########NEW FILE########
__FILENAME__ = ch3_panorama
from pylab import *
from numpy import *
from PIL import Image

# If you have PCV installed, these imports should work
from PCV.geometry import homography, warp
from PCV.localdescriptors import sift

"""
This is the panorama example from section 3.3.
"""

# set paths to data folder
featname = ['../data/Univ'+str(i+1)+'.sift' for i in range(5)] 
imname = ['../data/Univ'+str(i+1)+'.jpg' for i in range(5)]

# extract features and match
l = {}
d = {}
for i in range(5): 
    sift.process_image(imname[i],featname[i])
    l[i],d[i] = sift.read_features_from_file(featname[i])

matches = {}
for i in range(4):
    matches[i] = sift.match(d[i+1],d[i])

# visualize the matches (Figure 3-11 in the book)
for i in range(4):
    im1 = array(Image.open(imname[i]))
    im2 = array(Image.open(imname[i+1]))
    figure()
    sift.plot_matches(im2,im1,l[i+1],l[i],matches[i],show_below=True)


# function to convert the matches to hom. points
def convert_points(j):
    ndx = matches[j].nonzero()[0]
    fp = homography.make_homog(l[j+1][ndx,:2].T) 
    ndx2 = [int(matches[j][i]) for i in ndx]
    tp = homography.make_homog(l[j][ndx2,:2].T) 
    
    # switch x and y - TODO this should move elsewhere
    fp = vstack([fp[1],fp[0],fp[2]])
    tp = vstack([tp[1],tp[0],tp[2]])
    return fp,tp


# estimate the homographies
model = homography.RansacModel() 

fp,tp = convert_points(1)
H_12 = homography.H_from_ransac(fp,tp,model)[0] #im 1 to 2 

fp,tp = convert_points(0)
H_01 = homography.H_from_ransac(fp,tp,model)[0] #im 0 to 1 

tp,fp = convert_points(2) #NB: reverse order
H_32 = homography.H_from_ransac(fp,tp,model)[0] #im 3 to 2 

tp,fp = convert_points(3) #NB: reverse order
H_43 = homography.H_from_ransac(fp,tp,model)[0] #im 4 to 3    


# warp the images
delta = 2000 # for padding and translation

im1 = array(Image.open(imname[1]), "uint8")
im2 = array(Image.open(imname[2]), "uint8")
im_12 = warp.panorama(H_12,im1,im2,delta,delta)

im1 = array(Image.open(imname[0]), "f")
im_02 = warp.panorama(dot(H_12,H_01),im1,im_12,delta,delta)

im1 = array(Image.open(imname[3]), "f")
im_32 = warp.panorama(H_32,im1,im_02,delta,delta)

im1 = array(Image.open(imname[4]), "f")
im_42 = warp.panorama(dot(H_32,H_43),im1,im_32,delta,2*delta)


figure()
imshow(array(im_42, "uint8"))
axis('off')
show()


########NEW FILE########
__FILENAME__ = ch3_pwaffine_warp
from pylab import *
from numpy import *
from PIL import Image

from PCV.geometry import homography, warp

"""
This is the piecewise affine warp example from Section 3.2, Figure 3-5.
"""

# open image to warp
fromim = array(Image.open('../data/sunset_tree.jpg')) 
x,y = meshgrid(range(5),range(6))

x = (fromim.shape[1]/4) * x.flatten()
y = (fromim.shape[0]/5) * y.flatten()

# triangulate
tri = warp.triangulate_points(x,y)

# open image and destination points
im = array(Image.open('../data/turningtorso1.jpg'))
tp = loadtxt('../data/turningtorso1_points.txt', 'int') # destination points

# convert points to hom. coordinates (make sure they are of type int)
fp = array( vstack((y,x,ones((1,len(x))))), 'int')
tp = array( vstack((tp[:,1],tp[:,0],ones((1,len(tp))))), 'int')

# warp triangles
im = warp.pw_affine(fromim,im,fp,tp,tri)

# plot
figure()
imshow(im) 
warp.plot_mesh(tp[1],tp[0],tri) 
axis('off')
show()
########NEW FILE########
__FILENAME__ = ch3_registration
from PCV.tools import imregistration

"""
This is the face image registration example from Figure 3-6.
Make sure to create a folder 'aligned' under the jkfaces folder.
"""

# load the location of control points
xml_filename = '../data/jkfaces.xml'
points = imregistration.read_points_from_xml(xml_filename)

# register
imregistration.rigid_alignment(points,'../data/jkfaces/')
########NEW FILE########
__FILENAME__ = ch4_ar_cube
from pylab import *
from numpy import *
from PIL import Image

# If you have PCV installed, these imports should work
from PCV.geometry import homography, camera
from PCV.localdescriptors import sift

"""
This is the augmented reality and pose estimation cube example from Section 4.3.
"""

def cube_points(c,wid):
    """ Creates a list of points for plotting
        a cube with plot. (the first 5 points are
        the bottom square, some sides repeated). """
    p = []
    # bottom
    p.append([c[0]-wid,c[1]-wid,c[2]-wid])
    p.append([c[0]-wid,c[1]+wid,c[2]-wid])
    p.append([c[0]+wid,c[1]+wid,c[2]-wid])
    p.append([c[0]+wid,c[1]-wid,c[2]-wid])
    p.append([c[0]-wid,c[1]-wid,c[2]-wid]) #same as first to close plot
    
    # top
    p.append([c[0]-wid,c[1]-wid,c[2]+wid])
    p.append([c[0]-wid,c[1]+wid,c[2]+wid])
    p.append([c[0]+wid,c[1]+wid,c[2]+wid])
    p.append([c[0]+wid,c[1]-wid,c[2]+wid])
    p.append([c[0]-wid,c[1]-wid,c[2]+wid]) #same as first to close plot
    
    # vertical sides
    p.append([c[0]-wid,c[1]-wid,c[2]+wid])
    p.append([c[0]-wid,c[1]+wid,c[2]+wid])
    p.append([c[0]-wid,c[1]+wid,c[2]-wid])
    p.append([c[0]+wid,c[1]+wid,c[2]-wid])
    p.append([c[0]+wid,c[1]+wid,c[2]+wid])
    p.append([c[0]+wid,c[1]-wid,c[2]+wid])
    p.append([c[0]+wid,c[1]-wid,c[2]-wid])
    
    return array(p).T


def my_calibration(sz):
    """
    Calibration function for the camera (iPhone4) used in this example.
    """
    row,col = sz
    fx = 2555*col/2592
    fy = 2586*row/1936
    K = diag([fx,fy,1])
    K[0,2] = 0.5*col
    K[1,2] = 0.5*row
    return K



# compute features
sift.process_image('../data/book_frontal.JPG','im0.sift')
l0,d0 = sift.read_features_from_file('im0.sift')

sift.process_image('../data/book_perspective.JPG','im1.sift')
l1,d1 = sift.read_features_from_file('im1.sift')


# match features and estimate homography
matches = sift.match_twosided(d0,d1)
ndx = matches.nonzero()[0]
fp = homography.make_homog(l0[ndx,:2].T) 
ndx2 = [int(matches[i]) for i in ndx]
tp = homography.make_homog(l1[ndx2,:2].T)

model = homography.RansacModel()
H, inliers = homography.H_from_ransac(fp,tp,model) 

# camera calibration
K = my_calibration((747,1000))

# 3D points at plane z=0 with sides of length 0.2
box = cube_points([0,0,0.1],0.1)

# project bottom square in first image
cam1 = camera.Camera( hstack((K,dot(K,array([[0],[0],[-1]])) )) )
# first points are the bottom square
box_cam1 = cam1.project(homography.make_homog(box[:,:5])) 


# use H to transfer points to the second image
box_trans = homography.normalize(dot(H,box_cam1))

# compute second camera matrix from cam1 and H
cam2 = camera.Camera(dot(H,cam1.P))
A = dot(linalg.inv(K),cam2.P[:,:3])
A = array([A[:,0],A[:,1],cross(A[:,0],A[:,1])]).T 
cam2.P[:,:3] = dot(K,A)

# project with the second camera
box_cam2 = cam2.project(homography.make_homog(box))



# plotting
im0 = array(Image.open('book_frontal.JPG'))
im1 = array(Image.open('book_perspective.JPG'))

figure()
imshow(im0)
plot(box_cam1[0,:],box_cam1[1,:],linewidth=3)
title('2D projection of bottom square')
axis('off')

figure()
imshow(im1)
plot(box_trans[0,:],box_trans[1,:],linewidth=3)
title('2D projection transfered with H')
axis('off')

figure()
imshow(im1)
plot(box_cam2[0,:],box_cam2[1,:],linewidth=3)
title('3D points projected in second image')
axis('off')

show()
########NEW FILE########
__FILENAME__ = ch7_searchdemo
import cherrypy, os, urllib, pickle
from numpy import *

from PCV.imagesearch import imagesearch

"""
This is the image search demo in Section 7.6.
"""

class SearchDemo:
    
    def __init__(self):
        # load list of images
        f = open('webimlist.txt')
        self.imlist = f.readlines()
        f.close()
        self.nbr_images = len(self.imlist)
        self.ndx = range(self.nbr_images)
        
        # load vocabulary
        f = open('vocabulary.pkl', 'rb')
        self.voc = pickle.load(f)
        f.close()
        
        # set max number of results to show
        self.maxres = 15
        
        # header and footer html
        self.header = """
            <!doctype html>
            <head>
            <title>Image search example</title>
            </head>
            <body>
            """
        self.footer = """
            </body>
            </html>
            """
        
    def index(self,query=None):
        self.src = imagesearch.Searcher('web.db',self.voc)
        
        html = self.header
        html += """
            <br />
            Click an image to search. <a href='?query='> Random selection </a> of images.
            <br /><br />
            """
        if query:
            # query the database and get top images
            res = self.src.query(query)[:self.maxres]
            for dist,ndx in res:
                imname = self.src.get_filename(ndx)
                html += "<a href='?query="+imname+"'>"
                html += "<img src='"+imname+"' width='100' />"
                html += "</a>"
        else:
            # show random selection if no query
            random.shuffle(self.ndx)
            for i in self.ndx[:self.maxres]:
                imname = self.imlist[i]
                html += "<a href='?query="+imname+"'>"
                html += "<img src='"+imname+"' width='100' />"
                html += "</a>"
                
        html += self.footer
        return html
    
    index.exposed = True

cherrypy.quickstart(SearchDemo(), '/', config=os.path.join(os.path.dirname(__file__), 'service.conf'))
########NEW FILE########
__FILENAME__ = ch9_chan_vese
from PIL import Image
from numpy import *
from scipy.misc import imsave

from PCV.tools import rof

"""
Simple example of Chan-Vese segmentation from Section 9.3.
Load an image, segment in two classes and save result.
"""

im = array(Image.open('../data/houses.png').convert('L')) 
U,T = rof.denoise(im,im,tolerance=0.001)
t = 0.4

imsave('result.pdf',U < t*U.max())
########NEW FILE########
__FILENAME__ = lktrack
from numpy import *
import cv2


# some constants and default parameters
lk_params = dict(winSize=(15,15),maxLevel=2,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,10,0.03)) 

subpix_params = dict(zeroZone=(-1,-1),winSize=(10,10),
                     criteria = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS,20,0.03))

feature_params = dict(maxCorners=500,qualityLevel=0.01,minDistance=10)


class LKTracker(object):
    """    Class for Lucas-Kanade tracking with 
        pyramidal optical flow."""

    def __init__(self,imnames):
        """    Initialize with a list of image names. """

        self.imnames = imnames
        self.features = []
        self.tracks = []
        self.current_frame = 0

    def step(self,framenbr=None):
        """    Step to another frame. If no argument is 
            given, step to the next frame. """

        if framenbr is None:
            self.current_frame = (self.current_frame + 1) % len(self.imnames)
        else:
            self.current_frame = framenbr % len(self.imnames)

    def detect_points(self):
        """    Detect 'good features to track' (corners) in the current frame
            using sub-pixel accuracy. """

        # load the image and create grayscale
        self.image = cv2.imread(self.imnames[self.current_frame])
        self.gray = cv2.cvtColor(self.image,cv2.COLOR_BGR2GRAY)

        # search for good points
        features = cv2.goodFeaturesToTrack(self.gray, **feature_params)

        # refine the corner locations
        cv2.cornerSubPix(self.gray,features, **subpix_params)
        
        self.features = features
        self.tracks = [[p] for p in features.reshape((-1,2))]
        
        self.prev_gray = self.gray

    def track_points(self):
        """    Track the detected features. """

        if self.features != []:
            self.step() # move to the next frame
            
            # load the image and create grayscale
            self.image = cv2.imread(self.imnames[self.current_frame])
            self.gray = cv2.cvtColor(self.image,cv2.COLOR_BGR2GRAY)
            
            # reshape to fit input format
            tmp = float32(self.features).reshape(-1, 1, 2)
            
            # calculate optical flow
            features,status,track_error = cv2.calcOpticalFlowPyrLK(self.prev_gray,self.gray,tmp,None,**lk_params)

            # remove points lost
            self.features = [p for (st,p) in zip(status,features) if st]
            
            # clean tracks from lost points
            features = array(features).reshape((-1,2))
            for i,f in enumerate(features):
                self.tracks[i].append(f)
            ndx = [i for (i,st) in enumerate(status) if not st]
            ndx.reverse() #remove from back
            for i in ndx:
                self.tracks.pop(i)
            
            self.prev_gray = self.gray
            
    def track(self):
        """    Generator for stepping through a sequence."""

        for i in range(len(self.imnames)):
            if self.features == []:
                self.detect_points()
            else:
                self.track_points()
            
            # create a copy in RGB
            f = array(self.features).reshape(-1,2)
            im = cv2.cvtColor(self.image,cv2.COLOR_BGR2RGB)
            yield im,f

    def draw(self):
        """    Draw the current image with points using
            OpenCV's own drawing functions. 
            Press ant key to close window."""

        # draw points as green circles
        for point in self.features:
            cv2.circle(self.image,(int(point[0][0]),int(point[0][1])),3,(0,255,0),-1)
        
        cv2.imshow('LKtrack',self.image)
        cv2.waitKey()

########NEW FILE########
__FILENAME__ = pca_graylevel
from PIL import Image
from pylab import *
from numpy import *

from PCV.tools import imtools, pca

# Get list of images and their size
imlist = imtools.get_imlist('fontimages/') # fontimages.zip is part of the book data set
im = array(Image.open(imlist[0])) # open one image to get the size 
m,n = im.shape[:2]

# Create matrix to store all flattened images
immatrix = array([array(Image.open(imname)).flatten() for imname in imlist],'f')

# Perform PCA
V,S,immean = pca.pca(immatrix)

# Show the images (mean and 7 first modes)
# This gives figure 1-8 (p15) in the book.
figure()
gray()
subplot(2,4,1)
imshow(immean.reshape(m,n))
for i in range(7):
    subplot(2,4,i+2)
    imshow(V[i].reshape(m,n))
show()

########NEW FILE########
__FILENAME__ = unsharp
from PIL import Image
from pylab import *
from scipy.ndimage import filters


"""
This is an example of unsharp masking using Gaussian blur.
"""

# load sample eye image from http://en.wikipedia.org/wiki/Unsharp_masking
im = array(Image.open("unsharpen.jpg").convert("L"), "f")

# create blurred version of the image
sigma = 3
blurred = filters.gaussian_filter(im,sigma)

# create unsharp version (no thresholding)
weight = 0.25
unsharp = im - 0.25*blurred


# plot the original and the unsharpened image
figure()
imshow(im)
gray()
title("original image")

figure()
imshow(unsharp)
gray()
title("unsharp mask with weight {}".format(weight))

show()

########NEW FILE########
__FILENAME__ = expand_tabs
import os
import re

reg_pyfile=re.compile(r'.*\.py$',re.I)

def expand_tabs(file0):
    '''
    This function takes the name of a python source file, expands all tabs to 4 spaces (for
PEP 8 compliance), and rewrites the file in place.
    '''
    str_file_contents=open(file0,'rb').read()
    str_pep_contents=str_file_contents.replace('\x09',4*'\x20')
    open(file0,'wb').write(str_pep_contents)
    return None

def pepify_directory(path_root):
    for (path,subdir,lst_file) in os.walk(path_root):
        for file0 in (file1 for file1 in lst_file if reg_pyfile.match(file1)):
            expand_tabs(os.path.join(path,file0))
            print(os.path.join(path,file0))
            pass
        pass
    return None

if __name__=='__main__':
    pepify_directory('.')
    pass


########NEW FILE########
__FILENAME__ = bayes
from numpy import * 


class BayesClassifier(object):
    
    def __init__(self):
        """ Initialize classifier with training data. """
        
        self.labels = []    # class labels
        self.mean = []        # class mean
        self.var = []        # class variances
        self.n = 0            # nbr of classes
        
    def train(self,data,labels=None):
        """ Train on data (list of arrays n*dim). 
            Labels are optional, default is 0...n-1. """
        
        if labels==None:
            labels = range(len(data))
        self.labels = labels
        self.n = len(labels)
                
        for c in data:
            self.mean.append(mean(c,axis=0))
            self.var.append(var(c,axis=0))
        
    def classify(self,points):
        """ Classify the points by computing probabilities 
            for each class and return most probable label. """
        
        # compute probabilities for each class
        est_prob = array([gauss(m,v,points) for m,v in zip(self.mean,self.var)])
                
        print 'est prob',est_prob.shape,self.labels
        # get index of highest probability, this gives class label
        ndx = est_prob.argmax(axis=0)
        
        est_labels = array([self.labels[n] for n in ndx])
        
        return est_labels, est_prob


def gauss(m,v,x):
    """ Evaluate Gaussian in d-dimensions with independent 
        mean m and variance v at the points in (the rows of) x. 
        http://en.wikipedia.org/wiki/Multivariate_normal_distribution """
    
    if len(x.shape)==1:
        n,d = 1,x.shape[0]
    else:
        n,d = x.shape
            
    # covariance matrix, subtract mean
    S = diag(1/v)
    x = x-m
    # product of probabilities
    y = exp(-0.5*diag(dot(x,dot(S,x.T))))
    
    # normalize and return
    return y * (2*pi)**(-d/2.0) / ( sqrt(prod(v)) + 1e-6)




########NEW FILE########
__FILENAME__ = knn
from numpy import * 

class KnnClassifier(object):
    
    def __init__(self,labels,samples):
        """ Initialize classifier with training data. """
        
        self.labels = labels
        self.samples = samples
    
    def classify(self,point,k=3):
        """ Classify a point against k nearest 
            in the training data, return label. """
        
        # compute distance to all training points
        dist = array([L2dist(point,s) for s in self.samples])
        
        # sort them
        ndx = dist.argsort()
        
        # use dictionary to store the k nearest
        votes = {}
        for i in range(k):
            label = self.labels[ndx[i]]
            votes.setdefault(label,0)
            votes[label] += 1
            
        return max(votes)


def L2dist(p1,p2):
    return sqrt( sum( (p1-p2)**2) )

def L1dist(v1,v2):
    return sum(abs(v1-v2))
########NEW FILE########
__FILENAME__ = hcluster
from numpy import *
from itertools import combinations


class ClusterNode(object):
    def __init__(self,vec,left,right,distance=0.0,count=1):
        self.left = left
        self.right = right
        self.vec = vec
        self.distance = distance
        self.count = count # only used for weighted average

    def extract_clusters(self,dist):
        """ Extract list of sub-tree clusters from 
            hcluster tree with distance<dist. """
        if self.distance < dist:
            return [self]
        return self.left.extract_clusters(dist) + self.right.extract_clusters(dist)

    def get_cluster_elements(self):
        """    Return ids for elements in a cluster sub-tree. """
        return self.left.get_cluster_elements() + self.right.get_cluster_elements()

    def get_height(self):
        """    Return the height of a node, 
            height is sum of each branch. """
        return self.left.get_height() + self.right.get_height()

    def get_depth(self):
        """    Return the depth of a node, depth is 
            max of each child plus own distance. """
        return max(self.left.get_depth(), self.right.get_depth()) + self.distance

    def draw(self,draw,x,y,s,imlist,im):
        """    Draw nodes recursively with image 
            thumbnails for leaf nodes. """
    
        h1 = int(self.left.get_height()*20 / 2)
        h2 = int(self.right.get_height()*20 /2)
        top = y-(h1+h2)
        bottom = y+(h1+h2)
        
        # vertical line to children    
        draw.line((x,top+h1,x,bottom-h2),fill=(0,0,0))    
        
        # horizontal lines 
        ll = self.distance*s
        draw.line((x,top+h1,x+ll,top+h1),fill=(0,0,0))    
        draw.line((x,bottom-h2,x+ll,bottom-h2),fill=(0,0,0))        
        
        # draw left and right child nodes recursively    
        self.left.draw(draw,x+ll,top+h1,s,imlist,im)
        self.right.draw(draw,x+ll,bottom-h2,s,imlist,im)
    

class ClusterLeafNode(object):
    def __init__(self,vec,id):
        self.vec = vec
        self.id = id

    def extract_clusters(self,dist):
        return [self] 

    def get_cluster_elements(self):
        return [self.id]

    def get_height(self):
        return 1

    def get_depth(self):
        return 0
    
    def draw(self,draw,x,y,s,imlist,im):
        nodeim = Image.open(imlist[self.id])
        nodeim.thumbnail([20,20])
        ns = nodeim.size
        im.paste(nodeim,[int(x),int(y-ns[1]//2),int(x+ns[0]),int(y+ns[1]-ns[1]//2)])


def L2dist(v1,v2):
    return sqrt(sum((v1-v2)**2))

    
def L1dist(v1,v2):
    return sum(abs(v1-v2))


def hcluster(features,distfcn=L2dist):
    """ Cluster the rows of features using 
        hierarchical clustering. """
    
    # cache of distance calculations
    distances = {}
    
    # initialize with each row as a cluster 
    node = [ClusterLeafNode(array(f),id=i) for i,f in enumerate(features)]
    
    while len(node)>1:
        closest = float('Inf')
        
        # loop through every pair looking for the smallest distance
        for ni,nj in combinations(node,2):
            if (ni,nj) not in distances: 
                distances[ni,nj] = distfcn(ni.vec,nj.vec)
                
            d = distances[ni,nj]
            if d<closest:
                closest = d 
                lowestpair = (ni,nj)
        ni,nj = lowestpair
        
        # average the two clusters
        new_vec = (ni.vec + nj.vec) / 2.0
        
        # create new node
        new_node = ClusterNode(new_vec,left=ni,right=nj,distance=closest)
        node.remove(ni)
        node.remove(nj)
        node.append(new_node)
    
    return node[0]


from PIL import Image,ImageDraw
 
def draw_dendrogram(node,imlist,filename='clusters.jpg'):
    """    Draw a cluster dendrogram and save to a file. """
    
    # height and width
    rows = node.get_height()*20
    cols = 1200
    
    # scale factor for distances to fit image width
    s = float(cols-150)/node.get_depth()
    
    # create image and draw object
    im = Image.new('RGB',(cols,rows),(255,255,255))
    draw = ImageDraw.Draw(im)
    
    # initial line for start of tree
    draw.line((0,rows/2,20,rows/2),fill=(0,0,0))    
    
    # draw the nodes recursively
    node.draw(draw,20,(rows/2),s,imlist,im)
    im.save(filename)
    im.show()

########NEW FILE########
__FILENAME__ = camera
from numpy import *
from scipy import linalg


class Camera(object):
    """ Class for representing pin-hole cameras. """
    
    def __init__(self,P):
        """ Initialize P = K[R|t] camera model. """
        self.P = P
        self.K = None # calibration matrix
        self.R = None # rotation
        self.t = None # translation
        self.c = None # camera center
        
    
    def project(self,X):
        """    Project points in X (4*n array) and normalize coordinates. """
        
        x = dot(self.P,X)
        for i in range(3):
            x[i] /= x[2]    
        return x
        
        
    def factor(self):
        """    Factorize the camera matrix into K,R,t as P = K[R|t]. """
        
        # factor first 3*3 part
        K,R = linalg.rq(self.P[:,:3])
        
        # make diagonal of K positive
        T = diag(sign(diag(K)))
        if linalg.det(T) < 0:
            T[1,1] *= -1
        
        self.K = dot(K,T)
        self.R = dot(T,R) # T is its own inverse
        self.t = dot(linalg.inv(self.K),self.P[:,3])
        
        return self.K, self.R, self.t
        
    
    def center(self):
        """    Compute and return the camera center. """
    
        if self.c is not None:
            return self.c
        else:
            # compute c by factoring
            self.factor()
            self.c = -dot(self.R.T,self.t)
            return self.c



# helper functions    

def rotation_matrix(a):
    """    Creates a 3D rotation matrix for rotation
        around the axis of the vector a. """
    R = eye(4)
    R[:3,:3] = linalg.expm([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
    return R
    

def rq(A):
    from scipy.linalg import qr
    
    Q,R = qr(flipud(A).T)
    R = flipud(R.T)
    Q = Q.T
    
    return R[:,::-1],Q[::-1,:]

########NEW FILE########
__FILENAME__ = homography
from numpy import *
from scipy import ndimage
    

class RansacModel(object):
    """ Class for testing homography fit with ransac.py from
        http://www.scipy.org/Cookbook/RANSAC"""
    
    def __init__(self,debug=False):
        self.debug = debug
        
    def fit(self, data):
        """ Fit homography to four selected correspondences. """
        
        # transpose to fit H_from_points()
        data = data.T
        
        # from points
        fp = data[:3,:4]
        # target points
        tp = data[3:,:4]
        
        # fit homography and return
        return H_from_points(fp,tp)
    
    def get_error( self, data, H):
        """ Apply homography to all correspondences, 
            return error for each transformed point. """
        
        data = data.T
        
        # from points
        fp = data[:3]
        # target points
        tp = data[3:]
        
        # transform fp
        fp_transformed = dot(H,fp)
        
        # normalize hom. coordinates
        fp_transformed = normalize(fp_transformed)
                
        # return error per point
        return sqrt( sum((tp-fp_transformed)**2,axis=0) )
        

def H_from_ransac(fp,tp,model,maxiter=1000,match_theshold=10):
    """ Robust estimation of homography H from point 
        correspondences using RANSAC (ransac.py from
        http://www.scipy.org/Cookbook/RANSAC).
        
        input: fp,tp (3*n arrays) points in hom. coordinates. """
    
    from PCV.tools import ransac
    
    # group corresponding points
    data = vstack((fp,tp))
    
    # compute H and return
    H,ransac_data = ransac.ransac(data.T,model,4,maxiter,match_theshold,10,return_all=True)
    return H,ransac_data['inliers']


def H_from_points(fp,tp):
    """ Find homography H, such that fp is mapped to tp
        using the linear DLT method. Points are conditioned
        automatically. """
    
    if fp.shape != tp.shape:
        raise RuntimeError('number of points do not match')
        
    # condition points (important for numerical reasons)
    # --from points--
    m = mean(fp[:2], axis=1)
    maxstd = max(std(fp[:2], axis=1)) + 1e-9
    C1 = diag([1/maxstd, 1/maxstd, 1]) 
    C1[0][2] = -m[0]/maxstd
    C1[1][2] = -m[1]/maxstd
    fp = dot(C1,fp)
    
    # --to points--
    m = mean(tp[:2], axis=1)
    maxstd = max(std(tp[:2], axis=1)) + 1e-9
    C2 = diag([1/maxstd, 1/maxstd, 1])
    C2[0][2] = -m[0]/maxstd
    C2[1][2] = -m[1]/maxstd
    tp = dot(C2,tp)
    
    # create matrix for linear method, 2 rows for each correspondence pair
    nbr_correspondences = fp.shape[1]
    A = zeros((2*nbr_correspondences,9))
    for i in range(nbr_correspondences):        
        A[2*i] = [-fp[0][i],-fp[1][i],-1,0,0,0,
                    tp[0][i]*fp[0][i],tp[0][i]*fp[1][i],tp[0][i]]
        A[2*i+1] = [0,0,0,-fp[0][i],-fp[1][i],-1,
                    tp[1][i]*fp[0][i],tp[1][i]*fp[1][i],tp[1][i]]
    
    U,S,V = linalg.svd(A)
    H = V[8].reshape((3,3))    
    
    # decondition
    H = dot(linalg.inv(C2),dot(H,C1))
    
    # normalize and return
    return H / H[2,2]


def Haffine_from_points(fp,tp):
    """ Find H, affine transformation, such that 
        tp is affine transf of fp. """
    
    if fp.shape != tp.shape:
        raise RuntimeError('number of points do not match')
        
    # condition points
    # --from points--
    m = mean(fp[:2], axis=1)
    maxstd = max(std(fp[:2], axis=1)) + 1e-9
    C1 = diag([1/maxstd, 1/maxstd, 1]) 
    C1[0][2] = -m[0]/maxstd
    C1[1][2] = -m[1]/maxstd
    fp_cond = dot(C1,fp)
    
    # --to points--
    m = mean(tp[:2], axis=1)
    C2 = C1.copy() #must use same scaling for both point sets
    C2[0][2] = -m[0]/maxstd
    C2[1][2] = -m[1]/maxstd
    tp_cond = dot(C2,tp)
    
    # conditioned points have mean zero, so translation is zero
    A = concatenate((fp_cond[:2],tp_cond[:2]), axis=0)
    U,S,V = linalg.svd(A.T)
    
    # create B and C matrices as Hartley-Zisserman (2:nd ed) p 130.
    tmp = V[:2].T
    B = tmp[:2]
    C = tmp[2:4]
    
    tmp2 = concatenate((dot(C,linalg.pinv(B)),zeros((2,1))), axis=1) 
    H = vstack((tmp2,[0,0,1]))
    
    # decondition
    H = dot(linalg.inv(C2),dot(H,C1))
    
    return H / H[2,2]


def normalize(points):
    """ Normalize a collection of points in 
        homogeneous coordinates so that last row = 1. """

    for row in points:
        row /= points[-1]
    return points
    
    
def make_homog(points):
    """ Convert a set of points (dim*n array) to 
        homogeneous coordinates. """
        
    return vstack((points,ones((1,points.shape[1])))) 
 
########NEW FILE########
__FILENAME__ = sfm
from pylab import *
from numpy import *
from scipy import linalg


def compute_P(x,X):
    """    Compute camera matrix from pairs of
        2D-3D correspondences (in homog. coordinates). """

    n = x.shape[1]
    if X.shape[1] != n:
        raise ValueError("Number of points don't match.")
        
    # create matrix for DLT solution
    M = zeros((3*n,12+n))
    for i in range(n):
        M[3*i,0:4] = X[:,i]
        M[3*i+1,4:8] = X[:,i]
        M[3*i+2,8:12] = X[:,i]
        M[3*i:3*i+3,i+12] = -x[:,i]
        
    U,S,V = linalg.svd(M)
    
    return V[-1,:12].reshape((3,4))


def triangulate_point(x1,x2,P1,P2):
    """ Point pair triangulation from 
        least squares solution. """
        
    M = zeros((6,6))
    M[:3,:4] = P1
    M[3:,:4] = P2
    M[:3,4] = -x1
    M[3:,5] = -x2

    U,S,V = linalg.svd(M)
    X = V[-1,:4]

    return X / X[3]


def triangulate(x1,x2,P1,P2):
    """    Two-view triangulation of points in 
        x1,x2 (3*n homog. coordinates). """
        
    n = x1.shape[1]
    if x2.shape[1] != n:
        raise ValueError("Number of points don't match.")

    X = [ triangulate_point(x1[:,i],x2[:,i],P1,P2) for i in range(n)]
    return array(X).T


def compute_fundamental(x1,x2):
    """    Computes the fundamental matrix from corresponding points 
        (x1,x2 3*n arrays) using the 8 point algorithm.
        Each row in the A matrix below is constructed as
        [x'*x, x'*y, x', y'*x, y'*y, y', x, y, 1] """
    
    n = x1.shape[1]
    if x2.shape[1] != n:
        raise ValueError("Number of points don't match.")
    
    # build matrix for equations
    A = zeros((n,9))
    for i in range(n):
        A[i] = [x1[0,i]*x2[0,i], x1[0,i]*x2[1,i], x1[0,i]*x2[2,i],
                x1[1,i]*x2[0,i], x1[1,i]*x2[1,i], x1[1,i]*x2[2,i],
                x1[2,i]*x2[0,i], x1[2,i]*x2[1,i], x1[2,i]*x2[2,i] ]
            
    # compute linear least square solution
    U,S,V = linalg.svd(A)
    F = V[-1].reshape(3,3)
        
    # constrain F
    # make rank 2 by zeroing out last singular value
    U,S,V = linalg.svd(F)
    S[2] = 0
    F = dot(U,dot(diag(S),V))
    
    return F/F[2,2]


def compute_epipole(F):
    """ Computes the (right) epipole from a 
        fundamental matrix F. 
        (Use with F.T for left epipole.) """
    
    # return null space of F (Fx=0)
    U,S,V = linalg.svd(F)
    e = V[-1]
    return e/e[2]
    
    
def plot_epipolar_line(im,F,x,epipole=None,show_epipole=True):
    """ Plot the epipole and epipolar line F*x=0
        in an image. F is the fundamental matrix 
        and x a point in the other image."""
    
    m,n = im.shape[:2]
    line = dot(F,x)
    
    # epipolar line parameter and values
    t = linspace(0,n,100)
    lt = array([(line[2]+line[0]*tt)/(-line[1]) for tt in t])

    # take only line points inside the image
    ndx = (lt>=0) & (lt<m) 
    plot(t[ndx],lt[ndx],linewidth=2)
    
    if show_epipole:
        if epipole is None:
            epipole = compute_epipole(F)
        plot(epipole[0]/epipole[2],epipole[1]/epipole[2],'r*')
    

def skew(a):
    """ Skew matrix A such that a x v = Av for any v. """

    return array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])


def compute_P_from_fundamental(F):
    """    Computes the second camera matrix (assuming P1 = [I 0]) 
        from a fundamental matrix. """
        
    e = compute_epipole(F.T) # left epipole
    Te = skew(e)
    return vstack((dot(Te,F.T).T,e)).T


def compute_P_from_essential(E):
    """    Computes the second camera matrix (assuming P1 = [I 0]) 
        from an essential matrix. Output is a list of four 
        possible camera matrices. """
    
    # make sure E is rank 2
    U,S,V = svd(E)
    if det(dot(U,V))<0:
        V = -V
    E = dot(U,dot(diag([1,1,0]),V))    
    
    # create matrices (Hartley p 258)
    Z = skew([0,0,-1])
    W = array([[0,-1,0],[1,0,0],[0,0,1]])
    
    # return all four solutions
    P2 = [vstack((dot(U,dot(W,V)).T,U[:,2])).T,
             vstack((dot(U,dot(W,V)).T,-U[:,2])).T,
            vstack((dot(U,dot(W.T,V)).T,U[:,2])).T,
            vstack((dot(U,dot(W.T,V)).T,-U[:,2])).T]

    return P2


def compute_fundamental_normalized(x1,x2):
    """    Computes the fundamental matrix from corresponding points 
        (x1,x2 3*n arrays) using the normalized 8 point algorithm. """

    n = x1.shape[1]
    if x2.shape[1] != n:
        raise ValueError("Number of points don't match.")

    # normalize image coordinates
    x1 = x1 / x1[2]
    mean_1 = mean(x1[:2],axis=1)
    S1 = sqrt(2) / std(x1[:2])
    T1 = array([[S1,0,-S1*mean_1[0]],[0,S1,-S1*mean_1[1]],[0,0,1]])
    x1 = dot(T1,x1)
    
    x2 = x2 / x2[2]
    mean_2 = mean(x2[:2],axis=1)
    S2 = sqrt(2) / std(x2[:2])
    T2 = array([[S2,0,-S2*mean_2[0]],[0,S2,-S2*mean_2[1]],[0,0,1]])
    x2 = dot(T2,x2)

    # compute F with the normalized coordinates
    F = compute_fundamental(x1,x2)

    # reverse normalization
    F = dot(T1.T,dot(F,T2))

    return F/F[2,2]


class RansacModel(object):
    """ Class for fundmental matrix fit with ransac.py from
        http://www.scipy.org/Cookbook/RANSAC"""
    
    def __init__(self,debug=False):
        self.debug = debug
    
    def fit(self,data):
        """ Estimate fundamental matrix using eight 
            selected correspondences. """
        
        # transpose and split data into the two point sets
        data = data.T
        x1 = data[:3,:8]
        x2 = data[3:,:8]
        
        # estimate fundamental matrix and return
        F = compute_fundamental_normalized(x1,x2)
        return F
    
    def get_error(self,data,F):
        """ Compute x^T F x for all correspondences, 
            return error for each transformed point. """
        
        # transpose and split data into the two point
        data = data.T
        x1 = data[:3]
        x2 = data[3:]
        
        # Sampson distance as error measure
        Fx1 = dot(F,x1)
        Fx2 = dot(F,x2)
        denom = Fx1[0]**2 + Fx1[1]**2 + Fx2[0]**2 + Fx2[1]**2
        err = ( diag(dot(x1.T,dot(F,x2))) )**2 / denom 
        
        # return error per point
        return err


def F_from_ransac(x1,x2,model,maxiter=5000,match_theshold=1e-6):
    """ Robust estimation of a fundamental matrix F from point 
        correspondences using RANSAC (ransac.py from
        http://www.scipy.org/Cookbook/RANSAC).

        input: x1,x2 (3*n arrays) points in hom. coordinates. """

    from PCV.tools import ransac

    data = vstack((x1,x2))
    
    # compute F and return with inlier index
    F,ransac_data = ransac.ransac(data.T,model,8,maxiter,match_theshold,20,return_all=True)
    return F, ransac_data['inliers']

########NEW FILE########
__FILENAME__ = warp
import matplotlib.delaunay as md 
from scipy import ndimage
from pylab import *
from numpy import *

from PCV.geometry import homography
    

def image_in_image(im1,im2,tp):
    """ Put im1 in im2 with an affine transformation
        such that corners are as close to tp as possible.
        tp are homogeneous and counter-clockwise from top left. """ 
    
    # points to warp from
    m,n = im1.shape[:2]
    fp = array([[0,m,m,0],[0,0,n,n],[1,1,1,1]])
    
    # compute affine transform and apply
    H = homography.Haffine_from_points(tp,fp)
    im1_t = ndimage.affine_transform(im1,H[:2,:2],
                    (H[0,2],H[1,2]),im2.shape[:2])
    alpha = (im1_t > 0)
    
    return (1-alpha)*im2 + alpha*im1_t


def combine_images(im1,im2,alpha):
    """ Blend two images with weights as in alpha. """
    return (1-alpha)*im1 + alpha*im2    
    

def alpha_for_triangle(points,m,n):
    """ Creates alpha map of size (m,n) 
        for a triangle with corners defined by points
        (given in normalized homogeneous coordinates). """
    
    alpha = zeros((m,n))
    for i in range(min(points[0]),max(points[0])):
        for j in range(min(points[1]),max(points[1])):
            x = linalg.solve(points,[i,j,1])
            if min(x) > 0: #all coefficients positive
                alpha[i,j] = 1
    return alpha
    

def triangulate_points(x,y):
    """ Delaunay triangulation of 2D points. """
    
    centers,edges,tri,neighbors = md.delaunay(x,y)
    return tri


def plot_mesh(x,y,tri):
    """ Plot triangles. """ 
    
    for t in tri:
        t_ext = [t[0], t[1], t[2], t[0]] # add first point to end
        plot(x[t_ext],y[t_ext],'r')


def pw_affine(fromim,toim,fp,tp,tri):
    """ Warp triangular patches from an image.
        fromim = image to warp 
        toim = destination image
        fp = from points in hom. coordinates
        tp = to points in hom.  coordinates
        tri = triangulation. """
                
    im = toim.copy()
    
    # check if image is grayscale or color
    is_color = len(fromim.shape) == 3
    
    # create image to warp to (needed if iterate colors)
    im_t = zeros(im.shape, 'uint8') 
    
    for t in tri:
        # compute affine transformation
        H = homography.Haffine_from_points(tp[:,t],fp[:,t])
        
        if is_color:
            for col in range(fromim.shape[2]):
                im_t[:,:,col] = ndimage.affine_transform(
                    fromim[:,:,col],H[:2,:2],(H[0,2],H[1,2]),im.shape[:2])
        else:
            im_t = ndimage.affine_transform(
                    fromim,H[:2,:2],(H[0,2],H[1,2]),im.shape[:2])
        
        # alpha for triangle
        alpha = alpha_for_triangle(tp[:,t],im.shape[0],im.shape[1])
        
        # add triangle to image
        im[alpha>0] = im_t[alpha>0]
        
    return im
    
    
def panorama(H,fromim,toim,padding=2400,delta=2400):
    """ Create horizontal panorama by blending two images 
        using a homography H (preferably estimated using RANSAC).
        The result is an image with the same height as toim. 'padding' 
        specifies number of fill pixels and 'delta' additional translation. """ 
    
    # check if images are grayscale or color
    is_color = len(fromim.shape) == 3
    
    # homography transformation for geometric_transform()
    def transf(p):
        p2 = dot(H,[p[0],p[1],1])
        return (p2[0]/p2[2],p2[1]/p2[2])
    
    if H[1,2]<0: # fromim is to the right
        print 'warp - right'
        # transform fromim
        if is_color:
            # pad the destination image with zeros to the right
            toim_t = hstack((toim,zeros((toim.shape[0],padding,3))))
            fromim_t = zeros((toim.shape[0],toim.shape[1]+padding,toim.shape[2]))
            for col in range(3):
                fromim_t[:,:,col] = ndimage.geometric_transform(fromim[:,:,col],
                                        transf,(toim.shape[0],toim.shape[1]+padding))
        else:
            # pad the destination image with zeros to the right
            toim_t = hstack((toim,zeros((toim.shape[0],padding))))
            fromim_t = ndimage.geometric_transform(fromim,transf,
                                    (toim.shape[0],toim.shape[1]+padding)) 
    else:
        print 'warp - left'
        # add translation to compensate for padding to the left
        H_delta = array([[1,0,0],[0,1,-delta],[0,0,1]])
        H = dot(H,H_delta)
        # transform fromim
        if is_color:
            # pad the destination image with zeros to the left
            toim_t = hstack((zeros((toim.shape[0],padding,3)),toim))
            fromim_t = zeros((toim.shape[0],toim.shape[1]+padding,toim.shape[2]))
            for col in range(3):
                fromim_t[:,:,col] = ndimage.geometric_transform(fromim[:,:,col],
                                            transf,(toim.shape[0],toim.shape[1]+padding))
        else:
            # pad the destination image with zeros to the left
            toim_t = hstack((zeros((toim.shape[0],padding)),toim))
            fromim_t = ndimage.geometric_transform(fromim,
                                    transf,(toim.shape[0],toim.shape[1]+padding))
    
    # blend and return (put fromim above toim)
    if is_color:
        # all non black pixels
        alpha = ((fromim_t[:,:,0] * fromim_t[:,:,1] * fromim_t[:,:,2] ) > 0)
        for col in range(3):
            toim_t[:,:,col] = fromim_t[:,:,col]*alpha + toim_t[:,:,col]*(1-alpha)
    else:
        alpha = (fromim_t > 0)
        toim_t = fromim_t*alpha + toim_t*(1-alpha)
    
    return toim_t


########NEW FILE########
__FILENAME__ = imagesearch
from numpy import *
import pickle
from pysqlite2 import dbapi2 as sqlite


class Indexer(object):
    
    def __init__(self,db,voc):
        """ Initialize with the name of the database 
            and a vocabulary object. """
            
        self.con = sqlite.connect(db)
        self.voc = voc
    
    def __del__(self):
        self.con.close()
    
    def db_commit(self):
        self.con.commit()
    
    def get_id(self,imname):
        """ Get an entry id and add if not present. """
        
        cur = self.con.execute(
        "select rowid from imlist where filename='%s'" % imname)
        res=cur.fetchone()
        if res==None:
            cur = self.con.execute(
            "insert into imlist(filename) values ('%s')" % imname)
            return cur.lastrowid
        else:
            return res[0] 
    
    def is_indexed(self,imname):
        """ Returns True if imname has been indexed. """
        
        im = self.con.execute("select rowid from imlist where filename='%s'" % imname).fetchone()
        return im != None
    
    def add_to_index(self,imname,descr):
        """ Take an image with feature descriptors, 
            project on vocabulary and add to database. """
            
        if self.is_indexed(imname): return
        print 'indexing', imname
        
        # get the imid
        imid = self.get_id(imname)
        
        # get the words
        imwords = self.voc.project(descr)
        nbr_words = imwords.shape[0]
        
        # link each word to image
        for i in range(nbr_words):
            word = imwords[i]
            # wordid is the word number itself
            self.con.execute("insert into imwords(imid,wordid,vocname) values (?,?,?)", (imid,word,self.voc.name))
            
        # store word histogram for image
        # use pickle to encode NumPy arrays as strings
        self.con.execute("insert into imhistograms(imid,histogram,vocname) values (?,?,?)", (imid,pickle.dumps(imwords),self.voc.name))
    
    def create_tables(self): 
        """ Create the database tables. """
        
        self.con.execute('create table imlist(filename)')
        self.con.execute('create table imwords(imid,wordid,vocname)')
        self.con.execute('create table imhistograms(imid,histogram,vocname)')        
        self.con.execute('create index im_idx on imlist(filename)')
        self.con.execute('create index wordid_idx on imwords(wordid)')
        self.con.execute('create index imid_idx on imwords(imid)')
        self.con.execute('create index imidhist_idx on imhistograms(imid)')
        self.db_commit()


class Searcher(object):
    
    def __init__(self,db,voc):
        """ Initialize with the name of the database. """
        self.con = sqlite.connect(db)
        self.voc = voc
    
    def __del__(self):
        self.con.close()
    
    def get_imhistogram(self,imname):
        """ Return the word histogram for an image. """
        
        im_id = self.con.execute(
            "select rowid from imlist where filename='%s'" % imname).fetchone()
        s = self.con.execute(
            "select histogram from imhistograms where rowid='%d'" % im_id).fetchone()
        
        # use pickle to decode NumPy arrays from string
        return pickle.loads(str(s[0]))
    
    def candidates_from_word(self,imword):
        """ Get list of images containing imword. """
        
        im_ids = self.con.execute(
            "select distinct imid from imwords where wordid=%d" % imword).fetchall()
        return [i[0] for i in im_ids]
    
    def candidates_from_histogram(self,imwords):
        """ Get list of images with similar words. """
        
        # get the word ids
        words = imwords.nonzero()[0]
        
        # find candidates
        candidates = []
        for word in words:
            c = self.candidates_from_word(word)
            candidates+=c
        
        # take all unique words and reverse sort on occurrence 
        tmp = [(w,candidates.count(w)) for w in set(candidates)]
        tmp.sort(cmp=lambda x,y:cmp(x[1],y[1]))
        tmp.reverse()
        
        # return sorted list, best matches first    
        return [w[0] for w in tmp] 
    
    def query(self,imname):
        """ Find a list of matching images for imname. """
        
        h = self.get_imhistogram(imname)
        candidates = self.candidates_from_histogram(h)
        
        matchscores = []
        for imid in candidates:
            # get the name
            cand_name = self.con.execute(
                "select filename from imlist where rowid=%d" % imid).fetchone()
            cand_h = self.get_imhistogram(cand_name)
            cand_dist = sqrt( sum( self.voc.idf*(h-cand_h)**2 ) )
            matchscores.append( (cand_dist,imid) )
        
        # return a sorted list of distances and database ids
        matchscores.sort()
        return matchscores
    
    def get_filename(self,imid):
        """ Return the filename for an image id. """
        
        s = self.con.execute(
            "select filename from imlist where rowid='%d'" % imid).fetchone()
        return s[0]


def tf_idf_dist(voc,v1,v2):
    
    v1 /= sum(v1)
    v2 /= sum(v2)
    
    return sqrt( sum( voc.idf*(v1-v2)**2 ) )


def compute_ukbench_score(src,imlist):
    """ Returns the average number of correct
        images on the top four results of queries. """
        
    nbr_images = len(imlist)
    pos = zeros((nbr_images,4))
    # get first four results for each image
    for i in range(nbr_images):
        pos[i] = [w[1]-1 for w in src.query(imlist[i])[:4]]
    
    # compute score and return average
    score = array([ (pos[i]//4)==(i//4) for i in range(nbr_images)])*1.0
    return sum(score) / (nbr_images)


# import PIL and pylab for plotting        
from PIL import Image
from pylab import *

def plot_results(src,res):
    """ Show images in result list 'res'. """
    
    figure()
    nbr_results = len(res)
    for i in range(nbr_results):
        imname = src.get_filename(res[i])
        subplot(1,nbr_results,i+1)
        imshow(array(Image.open(imname)))
        axis('off')
    show()
########NEW FILE########
__FILENAME__ = vocabulary
from numpy import *
from scipy.cluster.vq import *

from PCV.localdescriptors import sift


class Vocabulary(object):
    
    def __init__(self,name):
        self.name = name
        self.voc = []
        self.idf = []
        self.trainingdata = []
        self.nbr_words = 0
    
    def train(self,featurefiles,k=100,subsampling=10):
        """ Train a vocabulary from features in files listed 
            in featurefiles using k-means with k number of words. 
            Subsampling of training data can be used for speedup. """
        
        nbr_images = len(featurefiles)
        # read the features from file
        descr = []
        descr.append(sift.read_features_from_file(featurefiles[0])[1])
        descriptors = descr[0] #stack all features for k-means
        for i in arange(1,nbr_images):
            descr.append(sift.read_features_from_file(featurefiles[i])[1])
            descriptors = vstack((descriptors,descr[i]))
            
        # k-means: last number determines number of runs
        self.voc,distortion = kmeans(descriptors[::subsampling,:],k,1)
        self.nbr_words = self.voc.shape[0]
        
        # go through all training images and project on vocabulary
        imwords = zeros((nbr_images,self.nbr_words))
        for i in range( nbr_images ):
            imwords[i] = self.project(descr[i])
        
        nbr_occurences = sum( (imwords > 0)*1 ,axis=0)
        
        self.idf = log( (1.0*nbr_images) / (1.0*nbr_occurences+1) )
        self.trainingdata = featurefiles
    
    def project(self,descriptors):
        """ Project descriptors on the vocabulary
            to create a histogram of words. """
        
        # histogram of image words 
        imhist = zeros((self.nbr_words))
        words,distance = vq(descriptors,self.voc)
        for w in words:
            imhist[w] += 1
        
        return imhist
    
    def get_words(self,descriptors):
        """ Convert descriptors to words. """
        return vq(descriptors,self.voc)[0]

########NEW FILE########
__FILENAME__ = dsift
from PIL import Image
from numpy import *
import os

from PCV.localdescriptors import sift


def process_image_dsift(imagename,resultname,size=20,steps=10,force_orientation=False,resize=None):
    """ Process an image with densely sampled SIFT descriptors 
        and save the results in a file. Optional input: size of features, 
        steps between locations, forcing computation of descriptor orientation 
        (False means all are oriented upwards), tuple for resizing the image."""

    im = Image.open(imagename).convert('L')
    if resize!=None:
        im = im.resize(resize)
    m,n = im.size
    
    if imagename[-3:] != 'pgm':
        #create a pgm file
        im.save('tmp.pgm')
        imagename = 'tmp.pgm'

    # create frames and save to temporary file
    scale = size/3.0
    x,y = meshgrid(range(steps,m,steps),range(steps,n,steps))
    xx,yy = x.flatten(),y.flatten()
    frame = array([xx,yy,scale*ones(xx.shape[0]),zeros(xx.shape[0])])
    savetxt('tmp.frame',frame.T,fmt='%03.3f')
    
    if force_orientation:
        cmmd = str("sift "+imagename+" --output="+resultname+
                    " --read-frames=tmp.frame --orientations")
    else:
        cmmd = str("sift "+imagename+" --output="+resultname+
                    " --read-frames=tmp.frame")
    os.system(cmmd)
    print 'processed', imagename, 'to', resultname


########NEW FILE########
__FILENAME__ = harris
from pylab import *
from numpy import *
from scipy.ndimage import filters


def compute_harris_response(im,sigma=3):
    """ Compute the Harris corner detector response function 
        for each pixel in a graylevel image. """
    
    # derivatives
    imx = zeros(im.shape)
    filters.gaussian_filter(im, (sigma,sigma), (0,1), imx)
    imy = zeros(im.shape)
    filters.gaussian_filter(im, (sigma,sigma), (1,0), imy)
    
    # compute components of the Harris matrix
    Wxx = filters.gaussian_filter(imx*imx,sigma)
    Wxy = filters.gaussian_filter(imx*imy,sigma)
    Wyy = filters.gaussian_filter(imy*imy,sigma)
    
    # determinant and trace
    Wdet = Wxx*Wyy - Wxy**2
    Wtr = Wxx + Wyy
    
    return Wdet / Wtr
   
    
def get_harris_points(harrisim,min_dist=10,threshold=0.1):
    """ Return corners from a Harris response image
        min_dist is the minimum number of pixels separating 
        corners and image boundary. """
    
    # find top corner candidates above a threshold
    corner_threshold = harrisim.max() * threshold
    harrisim_t = (harrisim > corner_threshold) * 1
    
    # get coordinates of candidates
    coords = array(harrisim_t.nonzero()).T
    
    # ...and their values
    candidate_values = [harrisim[c[0],c[1]] for c in coords]
    
    # sort candidates (reverse to get descending order)
    index = argsort(candidate_values)[::-1]
    
    # store allowed point locations in array
    allowed_locations = zeros(harrisim.shape)
    allowed_locations[min_dist:-min_dist,min_dist:-min_dist] = 1
    
    # select the best points taking min_distance into account
    filtered_coords = []
    for i in index:
        if allowed_locations[coords[i,0],coords[i,1]] == 1:
            filtered_coords.append(coords[i])
            allowed_locations[(coords[i,0]-min_dist):(coords[i,0]+min_dist), 
                        (coords[i,1]-min_dist):(coords[i,1]+min_dist)] = 0
    
    return filtered_coords
    
    
def plot_harris_points(image,filtered_coords):
    """ Plots corners found in image. """
    
    figure()
    gray()
    imshow(image)
    plot([p[1] for p in filtered_coords],
                [p[0] for p in filtered_coords],'*')
    axis('off')
    show()
    

def get_descriptors(image,filtered_coords,wid=5):
    """ For each point return pixel values around the point
        using a neighbourhood of width 2*wid+1. (Assume points are 
        extracted with min_distance > wid). """
    
    desc = []
    for coords in filtered_coords:
        patch = image[coords[0]-wid:coords[0]+wid+1,
                            coords[1]-wid:coords[1]+wid+1].flatten()
        desc.append(patch)
    
    return desc


def match(desc1,desc2,threshold=0.5):
    """ For each corner point descriptor in the first image, 
        select its match to second image using
        normalized cross correlation. """
    
    n = len(desc1[0])
    
    # pair-wise distances
    d = -ones((len(desc1),len(desc2)))
    for i in range(len(desc1)):
        for j in range(len(desc2)):
            d1 = (desc1[i] - mean(desc1[i])) / std(desc1[i])
            d2 = (desc2[j] - mean(desc2[j])) / std(desc2[j])
            ncc_value = sum(d1 * d2) / (n-1) 
            if ncc_value > threshold:
                d[i,j] = ncc_value
            
    ndx = argsort(-d)
    matchscores = ndx[:,0]
    
    return matchscores


def match_twosided(desc1,desc2,threshold=0.5):
    """ Two-sided symmetric version of match(). """
    
    matches_12 = match(desc1,desc2,threshold)
    matches_21 = match(desc2,desc1,threshold)
    
    ndx_12 = where(matches_12 >= 0)[0]
    
    # remove matches that are not symmetric
    for n in ndx_12:
        if matches_21[matches_12[n]] != n:
            matches_12[n] = -1
    
    return matches_12


def appendimages(im1,im2):
    """ Return a new image that appends the two images side-by-side. """
    
    # select the image with the fewest rows and fill in enough empty rows
    rows1 = im1.shape[0]    
    rows2 = im2.shape[0]
    
    if rows1 < rows2:
        im1 = concatenate((im1,zeros((rows2-rows1,im1.shape[1]))),axis=0)
    elif rows1 > rows2:
        im2 = concatenate((im2,zeros((rows1-rows2,im2.shape[1]))),axis=0)
    # if none of these cases they are equal, no filling needed.
    
    return concatenate((im1,im2), axis=1)
    
    
def plot_matches(im1,im2,locs1,locs2,matchscores,show_below=True):
    """ Show a figure with lines joining the accepted matches 
        input: im1,im2 (images as arrays), locs1,locs2 (feature locations), 
        matchscores (as output from 'match()'), 
        show_below (if images should be shown below matches). """
    
    im3 = appendimages(im1,im2)
    if show_below:
        im3 = vstack((im3,im3))
    
    imshow(im3)
    
    cols1 = im1.shape[1]
    for i,m in enumerate(matchscores):
        if m>0:
            plot([locs1[i][1],locs2[m][1]+cols1],[locs1[i][0],locs2[m][0]],'c')
    axis('off')

########NEW FILE########
__FILENAME__ = sift
from PIL import Image
from numpy import *
from pylab import *
import os


def process_image(imagename,resultname,params="--edge-thresh 10 --peak-thresh 5"):
    """ Process an image and save the results in a file. """

    if imagename[-3:] != 'pgm':
        # create a pgm file
        im = Image.open(imagename).convert('L')
        im.save('tmp.pgm')
        imagename = 'tmp.pgm'

    cmmd = str("sift "+imagename+" --output="+resultname+
                " "+params)
    os.system(cmmd)
    print 'processed', imagename, 'to', resultname


def read_features_from_file(filename):
    """ Read feature properties and return in matrix form. """
    
    f = loadtxt(filename)
    return f[:,:4],f[:,4:] # feature locations, descriptors


def write_features_to_file(filename,locs,desc):
    """ Save feature location and descriptor to file. """
    savetxt(filename,hstack((locs,desc)))
    

def plot_features(im,locs,circle=False):
    """ Show image with features. input: im (image as array), 
        locs (row, col, scale, orientation of each feature). """

    def draw_circle(c,r):
        t = arange(0,1.01,.01)*2*pi
        x = r*cos(t) + c[0]
        y = r*sin(t) + c[1]
        plot(x,y,'b',linewidth=2)

    imshow(im)
    if circle:
        for p in locs:
            draw_circle(p[:2],p[2]) 
    else:
        plot(locs[:,0],locs[:,1],'ob')
    axis('off')


def match(desc1,desc2):
    """ For each descriptor in the first image, 
        select its match in the second image.
        input: desc1 (descriptors for the first image), 
        desc2 (same for second image). """
    
    desc1 = array([d/linalg.norm(d) for d in desc1])
    desc2 = array([d/linalg.norm(d) for d in desc2])
    
    dist_ratio = 0.6
    desc1_size = desc1.shape
    
    matchscores = zeros((desc1_size[0]),'int')
    desc2t = desc2.T # precompute matrix transpose
    for i in range(desc1_size[0]):
        dotprods = dot(desc1[i,:],desc2t) # vector of dot products
        dotprods = 0.9999*dotprods
        # inverse cosine and sort, return index for features in second image
        indx = argsort(arccos(dotprods))
        
        # check if nearest neighbor has angle less than dist_ratio times 2nd
        if arccos(dotprods)[indx[0]] < dist_ratio * arccos(dotprods)[indx[1]]:
            matchscores[i] = int(indx[0])
    
    return matchscores


def appendimages(im1,im2):
    """ Return a new image that appends the two images side-by-side. """
    
    # select the image with the fewest rows and fill in enough empty rows
    rows1 = im1.shape[0]    
    rows2 = im2.shape[0]
    
    if rows1 < rows2:
        im1 = concatenate((im1,zeros((rows2-rows1,im1.shape[1]))), axis=0)
    elif rows1 > rows2:
        im2 = concatenate((im2,zeros((rows1-rows2,im2.shape[1]))), axis=0)
    # if none of these cases they are equal, no filling needed.
    
    return concatenate((im1,im2), axis=1)


def plot_matches(im1,im2,locs1,locs2,matchscores,show_below=True):
    """ Show a figure with lines joining the accepted matches
        input: im1,im2 (images as arrays), locs1,locs2 (location of features), 
        matchscores (as output from 'match'), show_below (if images should be shown below). """
    
    im3 = appendimages(im1,im2)
    if show_below:
        im3 = vstack((im3,im3))
    
    # show image
    imshow(im3)
    
    # draw lines for matches
    cols1 = im1.shape[1]
    for i,m in enumerate(matchscores):
        if m>0:
            plot([locs1[i][0],locs2[m][0]+cols1],[locs1[i][1],locs2[m][1]],'c')
    axis('off')


def match_twosided(desc1,desc2):
    """ Two-sided symmetric version of match(). """
    
    matches_12 = match(desc1,desc2)
    matches_21 = match(desc2,desc1)
    
    ndx_12 = matches_12.nonzero()[0]
    
    # remove matches that are not symmetric
    for n in ndx_12:
        if matches_21[int(matches_12[n])] != n:
            matches_12[n] = 0
    
    return matches_12


########NEW FILE########
__FILENAME__ = graphcut
from pylab import *
from numpy import *

from pygraph.classes.digraph import digraph
from pygraph.algorithms.minmax import maximum_flow

from PCV.classifiers import bayes

""" 
Graph Cut image segmentation using max-flow/min-cut. 
"""

def build_bayes_graph(im,labels,sigma=1e2,kappa=1):
    """    Build a graph from 4-neighborhood of pixels. 
        Foreground and background is determined from
        labels (1 for foreground, -1 for background, 0 otherwise) 
        and is modeled with naive Bayes classifiers."""
    
    m,n = im.shape[:2]
    
    # RGB vector version (one pixel per row)
    vim = im.reshape((-1,3))
    
    # RGB for foreground and background
    foreground = im[labels==1].reshape((-1,3))
    background = im[labels==-1].reshape((-1,3))    
    train_data = [foreground,background]
    
    # train naive Bayes classifier
    bc = bayes.BayesClassifier()
    bc.train(train_data)

    # get probabilities for all pixels
    bc_lables,prob = bc.classify(vim)
    prob_fg = prob[0]
    prob_bg = prob[1]
    
    # create graph with m*n+2 nodes
    gr = digraph()
    gr.add_nodes(range(m*n+2))
    
    source = m*n # second to last is source
    sink = m*n+1 # last node is sink

    # normalize
    for i in range(vim.shape[0]):
        vim[i] = vim[i] / (linalg.norm(vim[i]) + 1e-9)
    
    # go through all nodes and add edges
    for i in range(m*n):
        # add edge from source
        gr.add_edge((source,i), wt=(prob_fg[i]/(prob_fg[i]+prob_bg[i])))
        
        # add edge to sink
        gr.add_edge((i,sink), wt=(prob_bg[i]/(prob_fg[i]+prob_bg[i])))
        
        # add edges to neighbors
        if i%n != 0: # left exists
            edge_wt = kappa*exp(-1.0*sum((vim[i]-vim[i-1])**2)/sigma)
            gr.add_edge((i,i-1), wt=edge_wt)
        if (i+1)%n != 0: # right exists
            edge_wt = kappa*exp(-1.0*sum((vim[i]-vim[i+1])**2)/sigma)
            gr.add_edge((i,i+1), wt=edge_wt)
        if i//n != 0: # up exists
            edge_wt = kappa*exp(-1.0*sum((vim[i]-vim[i-n])**2)/sigma)
            gr.add_edge((i,i-n), wt=edge_wt)
        if i//n != m-1: # down exists
            edge_wt = kappa*exp(-1.0*sum((vim[i]-vim[i+n])**2)/sigma)
            gr.add_edge((i,i+n), wt=edge_wt)
        
    return gr    
        
    
def cut_graph(gr,imsize):
    """    Solve max flow of graph gr and return binary 
        labels of the resulting segmentation."""
    
    m,n = imsize
    source = m*n # second to last is source
    sink = m*n+1 # last is sink
    
    # cut the graph
    flows,cuts = maximum_flow(gr,source,sink)
    
    # convert graph to image with labels
    res = zeros(m*n)
    for pos,label in cuts.items()[:-2]: #don't add source/sink
        res[pos] = label

    return res.reshape((m,n))
    
    
def save_as_pdf(gr,filename,show_weights=False):

    from pygraph.readwrite.dot import write
    import gv
    dot = write(gr, weighted=show_weights)
    gvv = gv.readstring(dot)
    gv.layout(gvv,'fdp')
    gv.render(gvv,'pdf',filename)


def show_labeling(im,labels):
    """    Show image with foreground and background areas.
        labels = 1 for foreground, -1 for background, 0 otherwise."""
    
    imshow(im)
    contour(labels,[-0.5,0.5])
    contourf(labels,[-1,-0.5],colors='b',alpha=0.25)
    contourf(labels,[0.5,1],colors='r',alpha=0.25)
    #axis('off')
    xticks([])
    yticks([])


########NEW FILE########
__FILENAME__ = imregistration
from PIL import Image
from xml.dom import minidom
from numpy import *
from pylab import *

from scipy import ndimage, linalg
from scipy.misc import imsave
import os

def read_points_from_xml(xmlFileName):
    """ Reads control points for face alignment. """

    xmldoc = minidom.parse(xmlFileName)
    facelist = xmldoc.getElementsByTagName('face')    
    faces = {}    
    for xmlFace in facelist:
        fileName = xmlFace.attributes['file'].value
        xf = int(xmlFace.attributes['xf'].value)
        yf = int(xmlFace.attributes['yf'].value)     
        xs = int(xmlFace.attributes['xs'].value)
        ys = int(xmlFace.attributes['ys'].value)
        xm = int(xmlFace.attributes['xm'].value)
        ym = int(xmlFace.attributes['ym'].value)
        faces[fileName] = array([xf, yf, xs, ys, xm, ym])
    return faces
    
    
def write_points_to_xml(faces, xmlFileName):
    xmldoc = minidom.Document()
    xmlFaces = xmldoc.createElement("faces")

    keys = faces.keys()
    for k in keys:
        xmlFace = xmldoc.createElement("face")
        xmlFace.setAttribute("file", k)
        xmlFace.setAttribute("xf", "%d" % faces[k][0])    
        xmlFace.setAttribute("yf", "%d" % faces[k][1])
        xmlFace.setAttribute("xs", "%d" % faces[k][2])    
        xmlFace.setAttribute("ys", "%d" % faces[k][3])
        xmlFace.setAttribute("xm", "%d" % faces[k][4])
        xmlFace.setAttribute("ym", "%d" % faces[k][5])
        xmlFaces.appendChild(xmlFace)

    xmldoc.appendChild(xmlFaces)

    fp = open(xmlFileName, "w")
    fp.write(xmldoc.toprettyxml(encoding='utf-8'))    
    fp.close()


def compute_rigid_transform(refpoints,points):
    """ Computes rotation, scale and translation for
        aligning points to refpoints. """
    
    A = array([    [points[0], -points[1], 1, 0],
                [points[1],  points[0], 0, 1],
                [points[2], -points[3], 1, 0],
                [points[3],  points[2], 0, 1],
                [points[4], -points[5], 1, 0],
                [points[5],  points[4], 0, 1]])

    y = array([    refpoints[0],
                refpoints[1],
                refpoints[2],
                refpoints[3],
                refpoints[4],
                refpoints[5]])
    
    # least sq solution to mimimize ||Ax - y||
    a,b,tx,ty = linalg.lstsq(A,y)[0]
    R = array([[a, -b], [b, a]]) # rotation matrix incl scale

    return R,tx,ty


def rigid_alignment(faces,path,plotflag=False):
    """    Align images rigidly and save as new images.
        path determines where the aligned images are saved
        set plotflag=True to plot the images. """
    
    # take the points in the first image as reference points
    refpoints = faces.values()[0]
    
    # warp each image using affine transform
    for face in faces:
        points = faces[face]
        
        R,tx,ty = compute_rigid_transform(refpoints, points)
        T = array([[R[1][1], R[1][0]], [R[0][1], R[0][0]]])    
        
        im = array(Image.open(os.path.join(path,face)))
        im2 = zeros(im.shape, 'uint8')
        
        # warp each color channel
        for i in range(len(im.shape)):
            im2[:,:,i] = ndimage.affine_transform(im[:,:,i],linalg.inv(T),offset=[-ty,-tx])
            
        if plotflag:
            imshow(im2)
            show()
            
        # crop away border and save aligned images
        h,w = im2.shape[:2]
        border = (w+h)/20
        
        # crop away border
        imsave(os.path.join(path, 'aligned/'+face),im2[border:h-border,border:w-border,:])


########NEW FILE########
__FILENAME__ = imtools
import os
from PIL import Image
from pylab import *
from numpy import *



def get_imlist(path):
    """    Returns a list of filenames for 
        all jpg images in a directory. """
        
    return [os.path.join(path,f) for f in os.listdir(path) if f.endswith('.jpg')]


def compute_average(imlist):
    """    Compute the average of a list of images. """
    
    # open first image and make into array of type float
    averageim = array(Image.open(imlist[0]), 'f') 

    skipped = 0
    
    for imname in imlist[1:]:
        try: 
            averageim += array(Image.open(imname))
        except:
            print imname + "...skipped"  
            skipped += 1

    averageim /= (len(imlist) - skipped)
    
    # return average as uint8
    return array(averageim, 'uint8')

    
def convert_to_grayscale(imlist):
    """    Convert a set of images to grayscale. """
    
    for imname in imlist:
        im = Image.open(imname).convert("L")
        im.save(imname)


def imresize(im,sz):
    """    Resize an image array using PIL. """
    pil_im = Image.fromarray(uint8(im))
    
    return array(pil_im.resize(sz))


def histeq(im,nbr_bins=256):
    """    Histogram equalization of a grayscale image. """
    
    # get image histogram
    imhist,bins = histogram(im.flatten(),nbr_bins,normed=True)
    cdf = imhist.cumsum() # cumulative distribution function
    cdf = 255 * cdf / cdf[-1] # normalize
    
    # use linear interpolation of cdf to find new pixel values
    im2 = interp(im.flatten(),bins[:-1],cdf)
    
    return im2.reshape(im.shape), cdf
    
    
def plot_2D_boundary(plot_range,points,decisionfcn,labels,values=[0]):
    """    Plot_range is (xmin,xmax,ymin,ymax), points is a list
        of class points, decisionfcn is a funtion to evaluate, 
        labels is a list of labels that decisionfcn returns for each class, 
        values is a list of decision contours to show. """
        
    clist = ['b','r','g','k','m','y'] # colors for the classes
    
    # evaluate on a grid and plot contour of decision function
    x = arange(plot_range[0],plot_range[1],.1)
    y = arange(plot_range[2],plot_range[3],.1)
    xx,yy = meshgrid(x,y)
    xxx,yyy = xx.flatten(),yy.flatten() # lists of x,y in grid
    zz = array(decisionfcn(xxx,yyy)) 
    zz = zz.reshape(xx.shape)
    # plot contour(s) at values
    contour(xx,yy,zz,values) 
        
    # for each class, plot the points with '*' for correct, 'o' for incorrect
    for i in range(len(points)):
        d = decisionfcn(points[i][:,0],points[i][:,1])
        correct_ndx = labels[i]==d
        incorrect_ndx = labels[i]!=d
        plot(points[i][correct_ndx,0],points[i][correct_ndx,1],'*',color=clist[i])
        plot(points[i][incorrect_ndx,0],points[i][incorrect_ndx,1],'o',color=clist[i])
    
    axis('equal')

########NEW FILE########
__FILENAME__ = ncut
from PIL import Image
from pylab import *
from numpy import *
from scipy.cluster.vq import *


def cluster(S,k,ndim):
    """ Spectral clustering from a similarity matrix."""
    
    # check for symmetry
    if sum(abs(S-S.T)) > 1e-10:
        print 'not symmetric'
    
    # create Laplacian matrix
    rowsum = sum(abs(S),axis=0)
    D = diag(1 / sqrt(rowsum + 1e-6))
    L = dot(D,dot(S,D))
    
    # compute eigenvectors of L
    U,sigma,V = linalg.svd(L,full_matrices=False)
    
    # create feature vector from ndim first eigenvectors
    # by stacking eigenvectors as columns
    features = array(V[:ndim]).T

    # k-means
    features = whiten(features)
    centroids,distortion = kmeans(features,k)
    code,distance = vq(features,centroids)
        
    return code,V


def ncut_graph_matrix(im,sigma_d=1e2,sigma_g=1e-2):
    """ Create matrix for normalized cut. The parameters are 
        the weights for pixel distance and pixel similarity. """
    
    m,n = im.shape[:2] 
    N = m*n
    
    # normalize and create feature vector of RGB or grayscale
    if len(im.shape)==3:
        for i in range(3):
            im[:,:,i] = im[:,:,i] / im[:,:,i].max()
        vim = im.reshape((-1,3))
    else:
        im = im / im.max()
        vim = im.flatten()
    
    # x,y coordinates for distance computation
    xx,yy = meshgrid(range(n),range(m))
    x,y = xx.flatten(),yy.flatten()
    
    # create matrix with edge weights
    W = zeros((N,N),'f')
    for i in range(N):
        for j in range(i,N):
            d = (x[i]-x[j])**2 + (y[i]-y[j])**2 
            W[i,j] = W[j,i] = exp(-1.0*sum((vim[i]-vim[j])**2)/sigma_g) * exp(-d/sigma_d)
    
    return W

########NEW FILE########
__FILENAME__ = pca
from PIL import Image
from numpy import *


def pca(X):
    """    Principal Component Analysis
        input: X, matrix with training data stored as flattened arrays in rows
        return: projection matrix (with important dimensions first), variance and mean.
    """
    
    # get dimensions
    num_data,dim = X.shape
    
    # center data
    mean_X = X.mean(axis=0)
    X = X - mean_X
    
    if dim>num_data:
        # PCA - compact trick used
        M = dot(X,X.T) # covariance matrix
        e,EV = linalg.eigh(M) # eigenvalues and eigenvectors
        tmp = dot(X.T,EV).T # this is the compact trick
        V = tmp[::-1] # reverse since last eigenvectors are the ones we want
        S = sqrt(e)[::-1] # reverse since eigenvalues are in increasing order
        for i in range(V.shape[1]):
            V[:,i] /= S
    else:
        # PCA - SVD used
        U,S,V = linalg.svd(X)
        V = V[:num_data] # only makes sense to return the first num_data
    
    # return the projection matrix, the variance and the mean
    return V,S,mean_X


def center(X):
    """    Center the square matrix X (subtract col and row means). """
    
    n,m = X.shape
    if n != m:
        raise Exception('Matrix is not square.')
    
    colsum = X.sum(axis=0) / n
    rowsum = X.sum(axis=1) / n
    totalsum = X.sum() / (n**2)
    
    #center
    Y = array([[ X[i,j]-rowsum[i]-colsum[j]+totalsum for i in range(n) ] for j in range(n)])
    
    return Y
########NEW FILE########
__FILENAME__ = ransac
import numpy
import scipy # use numpy if scipy unavailable
import scipy.linalg # use numpy if scipy unavailable

## Copyright (c) 2004-2007, Andrew D. Straw. All rights reserved.

## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:

##     * Redistributions of source code must retain the above copyright
##       notice, this list of conditions and the following disclaimer.

##     * Redistributions in binary form must reproduce the above
##       copyright notice, this list of conditions and the following
##       disclaimer in the documentation and/or other materials provided
##       with the distribution.

##     * Neither the name of the Andrew D. Straw nor the names of its
##       contributors may be used to endorse or promote products derived
##       from this software without specific prior written permission.

## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

def ransac(data,model,n,k,t,d,debug=False,return_all=False):
    """fit model parameters to data using the RANSAC algorithm
    
This implementation written from pseudocode found at
http://en.wikipedia.org/w/index.php?title=RANSAC&oldid=116358182

{{{
Given:
    data - a set of observed data points
    model - a model that can be fitted to data points
    n - the minimum number of data values required to fit the model
    k - the maximum number of iterations allowed in the algorithm
    t - a threshold value for determining when a data point fits a model
    d - the number of close data values required to assert that a model fits well to data
Return:
    bestfit - model parameters which best fit the data (or nil if no good model is found)
iterations = 0
bestfit = nil
besterr = something really large
while iterations < k {
    maybeinliers = n randomly selected values from data
    maybemodel = model parameters fitted to maybeinliers
    alsoinliers = empty set
    for every point in data not in maybeinliers {
        if point fits maybemodel with an error smaller than t
             add point to alsoinliers
    }
    if the number of elements in alsoinliers is > d {
        % this implies that we may have found a good model
        % now test how good it is
        bettermodel = model parameters fitted to all points in maybeinliers and alsoinliers
        thiserr = a measure of how well model fits these points
        if thiserr < besterr {
            bestfit = bettermodel
            besterr = thiserr
        }
    }
    increment iterations
}
return bestfit
}}}
"""
    iterations = 0
    bestfit = None
    besterr = numpy.inf
    best_inlier_idxs = None
    while iterations < k:
        maybe_idxs, test_idxs = random_partition(n,data.shape[0])
        maybeinliers = data[maybe_idxs,:]
        test_points = data[test_idxs]
        maybemodel = model.fit(maybeinliers)
        test_err = model.get_error( test_points, maybemodel)
        also_idxs = test_idxs[test_err < t] # select indices of rows with accepted points
        alsoinliers = data[also_idxs,:]
        if debug:
            print 'test_err.min()',test_err.min()
            print 'test_err.max()',test_err.max()
            print 'numpy.mean(test_err)',numpy.mean(test_err)
            print 'iteration %d:len(alsoinliers) = %d'%(
                iterations,len(alsoinliers))
        if len(alsoinliers) > d:
            betterdata = numpy.concatenate( (maybeinliers, alsoinliers) )
            bettermodel = model.fit(betterdata)
            better_errs = model.get_error( betterdata, bettermodel)
            thiserr = numpy.mean( better_errs )
            if thiserr < besterr:
                bestfit = bettermodel
                besterr = thiserr
                best_inlier_idxs = numpy.concatenate( (maybe_idxs, also_idxs) )
        iterations+=1
    if bestfit is None:
        raise ValueError("did not meet fit acceptance criteria")
    if return_all:
        return bestfit, {'inliers':best_inlier_idxs}
    else:
        return bestfit

def random_partition(n,n_data):
    """return n random rows of data (and also the other len(data)-n rows)"""
    all_idxs = numpy.arange( n_data )
    numpy.random.shuffle(all_idxs)
    idxs1 = all_idxs[:n]
    idxs2 = all_idxs[n:]
    return idxs1, idxs2

class LinearLeastSquaresModel:
    """linear system solved using linear least squares

    This class serves as an example that fulfills the model interface
    needed by the ransac() function.
    
    """
    def __init__(self,input_columns,output_columns,debug=False):
        self.input_columns = input_columns
        self.output_columns = output_columns
        self.debug = debug
    def fit(self, data):
        A = numpy.vstack([data[:,i] for i in self.input_columns]).T
        B = numpy.vstack([data[:,i] for i in self.output_columns]).T
        x,resids,rank,s = numpy.linalg.lstsq(A,B)
        return x
    def get_error( self, data, model):
        A = numpy.vstack([data[:,i] for i in self.input_columns]).T
        B = numpy.vstack([data[:,i] for i in self.output_columns]).T
        B_fit = scipy.dot(A,model)
        err_per_point = numpy.sum((B-B_fit)**2,axis=1) # sum squared error per row
        return err_per_point
        
def test():
    # generate perfect input data

    n_samples = 500
    n_inputs = 1
    n_outputs = 1
    A_exact = 20*numpy.random.random((n_samples,n_inputs) )
    perfect_fit = 60*numpy.random.normal(size=(n_inputs,n_outputs) ) # the model
    B_exact = scipy.dot(A_exact,perfect_fit)
    assert B_exact.shape == (n_samples,n_outputs)

    # add a little gaussian noise (linear least squares alone should handle this well)
    A_noisy = A_exact + numpy.random.normal(size=A_exact.shape )
    B_noisy = B_exact + numpy.random.normal(size=B_exact.shape )

    if 1:
        # add some outliers
        n_outliers = 100
        all_idxs = numpy.arange( A_noisy.shape[0] )
        numpy.random.shuffle(all_idxs)
        outlier_idxs = all_idxs[:n_outliers]
        non_outlier_idxs = all_idxs[n_outliers:]
        A_noisy[outlier_idxs] =  20*numpy.random.random((n_outliers,n_inputs) )
        B_noisy[outlier_idxs] = 50*numpy.random.normal(size=(n_outliers,n_outputs) )

    # setup model

    all_data = numpy.hstack( (A_noisy,B_noisy) )
    input_columns = range(n_inputs) # the first columns of the array
    output_columns = [n_inputs+i for i in range(n_outputs)] # the last columns of the array
    debug = True
    model = LinearLeastSquaresModel(input_columns,output_columns,debug=debug)
    
    linear_fit,resids,rank,s = numpy.linalg.lstsq(all_data[:,input_columns],all_data[:,output_columns])

    # run RANSAC algorithm
    ransac_fit, ransac_data = ransac(all_data,model,
                                     5, 5000, 7e4, 50, # misc. parameters
                                     debug=debug,return_all=True)
    if 1:
        import pylab

        sort_idxs = numpy.argsort(A_exact[:,0])
        A_col0_sorted = A_exact[sort_idxs] # maintain as rank-2 array

        if 1:
            pylab.plot( A_noisy[:,0], B_noisy[:,0], 'k.', label='data' )
            pylab.plot( A_noisy[ransac_data['inliers'],0], B_noisy[ransac_data['inliers'],0], 'bx', label='RANSAC data' )
        else:
            pylab.plot( A_noisy[non_outlier_idxs,0], B_noisy[non_outlier_idxs,0], 'k.', label='noisy data' )
            pylab.plot( A_noisy[outlier_idxs,0], B_noisy[outlier_idxs,0], 'r.', label='outlier data' )
        pylab.plot( A_col0_sorted[:,0],
                    numpy.dot(A_col0_sorted,ransac_fit)[:,0],
                    label='RANSAC fit' )
        pylab.plot( A_col0_sorted[:,0],
                    numpy.dot(A_col0_sorted,perfect_fit)[:,0],
                    label='exact system' )
        pylab.plot( A_col0_sorted[:,0],
                    numpy.dot(A_col0_sorted,linear_fit)[:,0],
                    label='linear fit' )
        pylab.legend()
        pylab.show()

if __name__=='__main__':
    test()
    

########NEW FILE########
__FILENAME__ = rof
from numpy import *


def denoise(im,U_init,tolerance=0.1,tau=0.125,tv_weight=100):
    """ An implementation of the Rudin-Osher-Fatemi (ROF) denoising model
        using the numerical procedure presented in Eq. (11) of A. Chambolle
        (2005). Implemented using periodic boundary conditions.
        
        Input: noisy input image (grayscale), initial guess for U, weight of 
        the TV-regularizing term, steplength, tolerance for the stop criterion
        
        Output: denoised and detextured image, texture residual. """
        
    m,n = im.shape #size of noisy image

    # initialize
    U = U_init
    Px = zeros((m, n)) #x-component to the dual field
    Py = zeros((m, n)) #y-component of the dual field
    error = 1 
    
    while (error > tolerance):
        Uold = U
        
        # gradient of primal variable
        GradUx = roll(U,-1,axis=1)-U # x-component of U's gradient
        GradUy = roll(U,-1,axis=0)-U # y-component of U's gradient
        
        # update the dual varible
        PxNew = Px + (tau/tv_weight)*GradUx # non-normalized update of x-component (dual)
        PyNew = Py + (tau/tv_weight)*GradUy # non-normalized update of y-component (dual)
        NormNew = maximum(1,sqrt(PxNew**2+PyNew**2))
        
        Px = PxNew/NormNew # update of x-component (dual)
        Py = PyNew/NormNew # update of y-component (dual)
        
        # update the primal variable
        RxPx = roll(Px,1,axis=1) # right x-translation of x-component
        RyPy = roll(Py,1,axis=0) # right y-translation of y-component
        
        DivP = (Px-RxPx)+(Py-RyPy) # divergence of the dual field.
        U = im + tv_weight*DivP # update of the primal variable
        
        # update of error
        error = linalg.norm(U-Uold)/sqrt(n*m);
        
    return U,im-U # denoised image and texture residual

########NEW FILE########
__FILENAME__ = bayes
from numpy import * 


class BayesClassifier(object):
    
    def __init__(self):
        """ Initialize classifier with training data. """
        
        self.labels = []    # class labels
        self.mean = []        # class mean
        self.var = []        # class variances
        self.n = 0            # nbr of classes
        
    def train(self,data,labels=None):
        """ Train on data (list of arrays n*dim). 
            Labels are optional, default is 0...n-1. """
        
        if labels==None:
            labels = range(len(data))
        self.labels = labels
        self.n = len(labels)
                
        for c in data:
            self.mean.append(mean(c,axis=0))
            self.var.append(var(c,axis=0))
        
    def classify(self,points):
        """ Classify the points by computing probabilities 
            for each class and return most probable label. """
        
        # compute probabilities for each class
        est_prob = array([gauss(m,v,points) for m,v in zip(self.mean,self.var)])
                
        print 'est prob',est_prob.shape,self.labels
        # get index of highest probability, this gives class label
        ndx = est_prob.argmax(axis=0)
        
        est_labels = array([self.labels[n] for n in ndx])
        
        return est_labels, est_prob


def gauss(m,v,x):
    """ Evaluate Gaussian in d-dimensions with independent 
        mean m and variance v at the points in (the rows of) x. 
        http://en.wikipedia.org/wiki/Multivariate_normal_distribution """
    
    if len(x.shape)==1:
        n,d = 1,x.shape[0]
    else:
        n,d = x.shape
            
    # covariance matrix, subtract mean
    S = diag(1/v)
    x = x-m
    # product of probabilities
    y = exp(-0.5*diag(dot(x,dot(S,x.T))))
    
    # normalize and return
    return y * (2*pi)**(-d/2.0) / ( sqrt(prod(v)) + 1e-6)




########NEW FILE########
__FILENAME__ = camera
from numpy import *
from scipy import linalg


class Camera(object):
    """ Class for representing pin-hole cameras. """
    
    def __init__(self,P):
        """ Initialize P = K[R|t] camera model. """
        self.P = P
        self.K = None # calibration matrix
        self.R = None # rotation
        self.t = None # translation
        self.c = None # camera center
        
    
    def project(self,X):
        """    Project points in X (4*n array) and normalize coordinates. """
        
        x = dot(self.P,X)
        for i in range(3):
            x[i] /= x[2]    
        return x
        
        
    def factor(self):
        """    Factorize the camera matrix into K,R,t as P = K[R|t]. """
        
        # factor first 3*3 part
        K,R = linalg.rq(self.P[:,:3])
        
        # make diagonal of K positive
        T = diag(sign(diag(K)))
        if linalg.det(T) < 0:
            T[1,1] *= -1
        
        self.K = dot(K,T)
        self.R = dot(T,R) # T is its own inverse
        self.t = dot(linalg.inv(self.K),self.P[:,3])
        
        return self.K, self.R, self.t
        
    
    def center(self):
        """    Compute and return the camera center. """
    
        if self.c is not None:
            return self.c
        else:
            # compute c by factoring
            self.factor()
            self.c = -dot(self.R.T,self.t)
            return self.c



# helper functions    

def rotation_matrix(a):
    """    Creates a 3D rotation matrix for rotation
        around the axis of the vector a. """
    R = eye(4)
    R[:3,:3] = linalg.expm([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
    return R
    

def rq(A):
    from scipy.linalg import qr
    
    Q,R = qr(flipud(A).T)
    R = flipud(R.T)
    Q = Q.T
    
    return R[:,::-1],Q[::-1,:]

########NEW FILE########
__FILENAME__ = dsift
from PIL import Image
import os
from numpy import *
import sift


def process_image_dsift(imagename,resultname,size=20,steps=10,force_orientation=False,resize=None):
    """ Process an image with densely sampled SIFT descriptors 
        and save the results in a file. Optional input: size of features, 
        steps between locations, forcing computation of descriptor orientation 
        (False means all are oriented upwards), tuple for resizing the image."""

    im = Image.open(imagename).convert('L')
    if resize!=None:
        im = im.resize(resize)
    m,n = im.size
    
    if imagename[-3:] != 'pgm':
        #create a pgm file
        im.save('tmp.pgm')
        imagename = 'tmp.pgm'

    # create frames and save to temporary file
    scale = size/3.0
    x,y = meshgrid(range(steps,m,steps),range(steps,n,steps))
    xx,yy = x.flatten(),y.flatten()
    frame = array([xx,yy,scale*ones(xx.shape[0]),zeros(xx.shape[0])])
    savetxt('tmp.frame',frame.T,fmt='%03.3f')
    
    if force_orientation:
        cmmd = str("sift "+imagename+" --output="+resultname+
                    " --read-frames=tmp.frame --orientations")
    else:
        cmmd = str("sift "+imagename+" --output="+resultname+
                    " --read-frames=tmp.frame")
    os.system(cmmd)
    print 'processed', imagename, 'to', resultname


########NEW FILE########
__FILENAME__ = graphcut
from pylab import *
from numpy import *

from pygraph.classes.digraph import digraph
from pygraph.algorithms.minmax import maximum_flow

import bayes

""" 
Graph Cut image segmentation using max-flow/min-cut. 
"""

def build_bayes_graph(im,labels,sigma=1e2,kappa=1):
    """    Build a graph from 4-neighborhood of pixels. 
        Foreground and background is determined from
        labels (1 for foreground, -1 for background, 0 otherwise) 
        and is modeled with naive Bayes classifiers."""
    
    m,n = im.shape[:2]
    
    # RGB vector version (one pixel per row)
    vim = im.reshape((-1,3))
    
    # RGB for foreground and background
    foreground = im[labels==1].reshape((-1,3))
    background = im[labels==-1].reshape((-1,3))    
    train_data = [foreground,background]
    
    # train naive Bayes classifier
    bc = bayes.BayesClassifier()
    bc.train(train_data)

    # get probabilities for all pixels
    bc_lables,prob = bc.classify(vim)
    prob_fg = prob[0]
    prob_bg = prob[1]
    
    # create graph with m*n+2 nodes
    gr = digraph()
    gr.add_nodes(range(m*n+2))
    
    source = m*n # second to last is source
    sink = m*n+1 # last node is sink

    # normalize
    for i in range(vim.shape[0]):
        vim[i] = vim[i] / (linalg.norm(vim[i]) + 1e-9)
    
    # go through all nodes and add edges
    for i in range(m*n):
        # add edge from source
        gr.add_edge((source,i), wt=(prob_fg[i]/(prob_fg[i]+prob_bg[i])))
        
        # add edge to sink
        gr.add_edge((i,sink), wt=(prob_bg[i]/(prob_fg[i]+prob_bg[i])))
        
        # add edges to neighbors
        if i%n != 0: # left exists
            edge_wt = kappa*exp(-1.0*sum((vim[i]-vim[i-1])**2)/sigma)
            gr.add_edge((i,i-1), wt=edge_wt)
        if (i+1)%n != 0: # right exists
            edge_wt = kappa*exp(-1.0*sum((vim[i]-vim[i+1])**2)/sigma)
            gr.add_edge((i,i+1), wt=edge_wt)
        if i//n != 0: # up exists
            edge_wt = kappa*exp(-1.0*sum((vim[i]-vim[i-n])**2)/sigma)
            gr.add_edge((i,i-n), wt=edge_wt)
        if i//n != m-1: # down exists
            edge_wt = kappa*exp(-1.0*sum((vim[i]-vim[i+n])**2)/sigma)
            gr.add_edge((i,i+n), wt=edge_wt)
        
    return gr    
        
    
def cut_graph(gr,imsize):
    """    Solve max flow of graph gr and return binary 
        labels of the resulting segmentation."""
    
    m,n = imsize
    source = m*n # second to last is source
    sink = m*n+1 # last is sink
    
    # cut the graph
    flows,cuts = maximum_flow(gr,source,sink)
    
    # convert graph to image with labels
    res = zeros(m*n)
    for pos,label in cuts.items()[:-2]: #don't add source/sink
        res[pos] = label

    return res.reshape((m,n))
    
    
def save_as_pdf(gr,filename,show_weights=False):

    from pygraph.readwrite.dot import write
    import gv
    dot = write(gr, weighted=show_weights)
    gvv = gv.readstring(dot)
    gv.layout(gvv,'fdp')
    gv.render(gvv,'pdf',filename)


def show_labeling(im,labels):
    """    Show image with foreground and background areas.
        labels = 1 for foreground, -1 for background, 0 otherwise."""
    
    imshow(im)
    contour(labels,[-0.5,0.5])
    contourf(labels,[-1,-0.5],colors='b',alpha=0.25)
    contourf(labels,[0.5,1],colors='r',alpha=0.25)
    #axis('off')
    xticks([])
    yticks([])


########NEW FILE########
__FILENAME__ = harris
from pylab import *
from numpy import *
from scipy.ndimage import filters


def compute_harris_response(im,sigma=3):
    """ Compute the Harris corner detector response function 
        for each pixel in a graylevel image. """
    
    # derivatives
    imx = zeros(im.shape)
    filters.gaussian_filter(im, (sigma,sigma), (0,1), imx)
    imy = zeros(im.shape)
    filters.gaussian_filter(im, (sigma,sigma), (1,0), imy)
    
    # compute components of the Harris matrix
    Wxx = filters.gaussian_filter(imx*imx,sigma)
    Wxy = filters.gaussian_filter(imx*imy,sigma)
    Wyy = filters.gaussian_filter(imy*imy,sigma)
    
    # determinant and trace
    Wdet = Wxx*Wyy - Wxy**2
    Wtr = Wxx + Wyy
    
    return Wdet / (Wtr*Wtr)
   
    
def get_harris_points(harrisim,min_dist=10,threshold=0.1):
    """ Return corners from a Harris response image
        min_dist is the minimum number of pixels separating 
        corners and image boundary. """
    
    # find top corner candidates above a threshold
    corner_threshold = harrisim.max() * threshold
    harrisim_t = (harrisim > corner_threshold) * 1
    
    # get coordinates of candidates
    coords = array(harrisim_t.nonzero()).T
    
    # ...and their values
    candidate_values = [harrisim[c[0],c[1]] for c in coords]
    
    # sort candidates
    index = argsort(candidate_values)
    
    # store allowed point locations in array
    allowed_locations = zeros(harrisim.shape)
    allowed_locations[min_dist:-min_dist,min_dist:-min_dist] = 1
    
    # select the best points taking min_distance into account
    filtered_coords = []
    for i in index:
        if allowed_locations[coords[i,0],coords[i,1]] == 1:
            filtered_coords.append(coords[i])
            allowed_locations[(coords[i,0]-min_dist):(coords[i,0]+min_dist), 
                        (coords[i,1]-min_dist):(coords[i,1]+min_dist)] = 0
    
    return filtered_coords
    
    
def plot_harris_points(image,filtered_coords):
    """ Plots corners found in image. """
    
    figure()
    gray()
    imshow(image)
    plot([p[1] for p in filtered_coords],
                [p[0] for p in filtered_coords],'*')
    axis('off')
    show()
    

def get_descriptors(image,filtered_coords,wid=5):
    """ For each point return pixel values around the point
        using a neighbourhood of width 2*wid+1. (Assume points are 
        extracted with min_distance > wid). """
    
    desc = []
    for coords in filtered_coords:
        patch = image[coords[0]-wid:coords[0]+wid+1,
                            coords[1]-wid:coords[1]+wid+1].flatten()
        desc.append(patch)
    
    return desc


def match(desc1,desc2,threshold=0.5):
    """ For each corner point descriptor in the first image, 
        select its match to second image using
        normalized cross correlation. """
    
    n = len(desc1[0])
    
    # pair-wise distances
    d = -ones((len(desc1),len(desc2)))
    for i in range(len(desc1)):
        for j in range(len(desc2)):
            d1 = (desc1[i] - mean(desc1[i])) / std(desc1[i])
            d2 = (desc2[j] - mean(desc2[j])) / std(desc2[j])
            ncc_value = sum(d1 * d2) / (n-1) 
            if ncc_value > threshold:
                d[i,j] = ncc_value
            
    ndx = argsort(-d)
    matchscores = ndx[:,0]
    
    return matchscores


def match_twosided(desc1,desc2,threshold=0.5):
    """ Two-sided symmetric version of match(). """
    
    matches_12 = match(desc1,desc2,threshold)
    matches_21 = match(desc2,desc1,threshold)
    
    ndx_12 = where(matches_12 >= 0)[0]
    
    # remove matches that are not symmetric
    for n in ndx_12:
        if matches_21[matches_12[n]] != n:
            matches_12[n] = -1
    
    return matches_12


def appendimages(im1,im2):
    """ Return a new image that appends the two images side-by-side. """
    
    # select the image with the fewest rows and fill in enough empty rows
    rows1 = im1.shape[0]    
    rows2 = im2.shape[0]
    
    if rows1 < rows2:
        im1 = concatenate((im1,zeros((rows2-rows1,im1.shape[1]))),axis=0)
    elif rows1 > rows2:
        im2 = concatenate((im2,zeros((rows1-rows2,im2.shape[1]))),axis=0)
    # if none of these cases they are equal, no filling needed.
    
    return concatenate((im1,im2), axis=1)
    
    
def plot_matches(im1,im2,locs1,locs2,matchscores,show_below=True):
    """ Show a figure with lines joining the accepted matches 
        input: im1,im2 (images as arrays), locs1,locs2 (feature locations), 
        matchscores (as output from 'match()'), 
        show_below (if images should be shown below matches). """
    
    im3 = appendimages(im1,im2)
    if show_below:
        im3 = vstack((im3,im3))
    
    imshow(im3)
    
    cols1 = im1.shape[1]
    for i,m in enumerate(matchscores):
        if m>0:
            plot([locs1[i][1],locs2[m][1]+cols1],[locs1[i][0],locs2[m][0]],'c')
    axis('off')

########NEW FILE########
__FILENAME__ = hcluster
from numpy import *
from itertools import combinations


class ClusterNode(object):
    def __init__(self,vec,left,right,distance=0.0,count=1):
        self.left = left
        self.right = right
        self.vec = vec
        self.distance = distance
        self.count = count # only used for weighted average

    def extract_clusters(self,dist):
        """ Extract list of sub-tree clusters from 
            hcluster tree with distance<dist. """
        if self.distance < dist:
            return [self]
        return self.left.extract_clusters(dist) + self.right.extract_clusters(dist)

    def get_cluster_elements(self):
        """    Return ids for elements in a cluster sub-tree. """
        return self.left.get_cluster_elements() + self.right.get_cluster_elements()

    def get_height(self):
        """    Return the height of a node, 
            height is sum of each branch. """
        return self.left.get_height() + self.right.get_height()

    def get_depth(self):
        """    Return the depth of a node, depth is 
            max of each child plus own distance. """
        return max(self.left.get_depth(), self.right.get_depth()) + self.distance

    def draw(self,draw,x,y,s,imlist,im):
        """    Draw nodes recursively with image 
            thumbnails for leaf nodes. """
    
        h1 = int(self.left.get_height()*20 / 2)
        h2 = int(self.right.get_height()*20 /2)
        top = y-(h1+h2)
        bottom = y+(h1+h2)
        
        # vertical line to children    
        draw.line((x,top+h1,x,bottom-h2),fill=(0,0,0))    
        
        # horizontal lines 
        ll = self.distance*s
        draw.line((x,top+h1,x+ll,top+h1),fill=(0,0,0))    
        draw.line((x,bottom-h2,x+ll,bottom-h2),fill=(0,0,0))        
        
        # draw left and right child nodes recursively    
        self.left.draw(draw,x+ll,top+h1,s,imlist,im)
        self.right.draw(draw,x+ll,bottom-h2,s,imlist,im)
    

class ClusterLeafNode(object):
    def __init__(self,vec,id):
        self.vec = vec
        self.id = id

    def extract_clusters(self,dist):
        return [self] 

    def get_cluster_elements(self):
        return [self.id]

    def get_height(self):
        return 1

    def get_depth(self):
        return 0
    
    def draw(self,draw,x,y,s,imlist,im):
        nodeim = Image.open(imlist[self.id])
        nodeim.thumbnail([20,20])
        ns = nodeim.size
        im.paste(nodeim,[int(x),int(y-ns[1]//2),int(x+ns[0]),int(y+ns[1]-ns[1]//2)])


def L2dist(v1,v2):
    return sqrt(sum((v1-v2)**2))

    
def L1dist(v1,v2):
    return sum(abs(v1-v2))


def hcluster(features,distfcn=L2dist):
    """ Cluster the rows of features using 
        hierarchical clustering. """
    
    # cache of distance calculations
    distances = {}
    
    # initialize with each row as a cluster 
    node = [ClusterLeafNode(array(f),id=i) for i,f in enumerate(features)]
    
    while len(node)>1:
        closest = float('Inf')
        
        # loop through every pair looking for the smallest distance
        for ni,nj in combinations(node,2):
            if (ni,nj) not in distances: 
                distances[ni,nj] = distfcn(ni.vec,nj.vec)
                
            d = distances[ni,nj]
            if d<closest:
                closest = d 
                lowestpair = (ni,nj)
        ni,nj = lowestpair
        
        # average the two clusters
        new_vec = (ni.vec + nj.vec) / 2.0
        
        # create new node
        new_node = ClusterNode(new_vec,left=ni,right=nj,distance=closest)
        node.remove(ni)
        node.remove(nj)
        node.append(new_node)
    
    return node[0]


from PIL import Image,ImageDraw
 
def draw_dendrogram(node,imlist,filename='clusters.jpg'):
    """    Draw a cluster dendrogram and save to a file. """
    
    # height and width
    rows = node.get_height()*20
    cols = 1200
    
    # scale factor for distances to fit image width
    s = float(cols-150)/node.get_depth()
    
    # create image and draw object
    im = Image.new('RGB',(cols,rows),(255,255,255))
    draw = ImageDraw.Draw(im)
    
    # initial line for start of tree
    draw.line((0,rows/2,20,rows/2),fill=(0,0,0))    
    
    # draw the nodes recursively
    node.draw(draw,20,(rows/2),s,imlist,im)
    im.save(filename)
    im.show()

########NEW FILE########
__FILENAME__ = homography
from numpy import *
from scipy import ndimage
    

class RansacModel(object):
    """ Class for testing homography fit with ransac.py from
        http://www.scipy.org/Cookbook/RANSAC"""
    
    def __init__(self,debug=False):
        self.debug = debug
        
    def fit(self, data):
        """ Fit homography to four selected correspondences. """
        
        # transpose to fit H_from_points()
        data = data.T
        
        # from points
        fp = data[:3,:4]
        # target points
        tp = data[3:,:4]
        
        # fit homography and return
        return H_from_points(fp,tp)
    
    def get_error( self, data, H):
        """ Apply homography to all correspondences, 
            return error for each transformed point. """
        
        data = data.T
        
        # from points
        fp = data[:3]
        # target points
        tp = data[3:]
        
        # transform fp
        fp_transformed = dot(H,fp)
        
        # normalize hom. coordinates
        fp_transformed = normalize(fp_transformed)
                
        # return error per point
        return sqrt( sum((tp-fp_transformed)**2,axis=0) )
        

def H_from_ransac(fp,tp,model,maxiter=1000,match_theshold=10):
    """ Robust estimation of homography H from point 
        correspondences using RANSAC (ransac.py from
        http://www.scipy.org/Cookbook/RANSAC).
        
        input: fp,tp (3*n arrays) points in hom. coordinates. """
    
    import ransac
    
    # group corresponding points
    data = vstack((fp,tp))
    
    # compute H and return
    H,ransac_data = ransac.ransac(data.T,model,4,maxiter,match_theshold,10,return_all=True)
    return H,ransac_data['inliers']


def H_from_points(fp,tp):
    """ Find homography H, such that fp is mapped to tp
        using the linear DLT method. Points are conditioned
        automatically. """
    
    if fp.shape != tp.shape:
        raise RuntimeError('number of points do not match')
        
    # condition points (important for numerical reasons)
    # --from points--
    m = mean(fp[:2], axis=1)
    maxstd = max(std(fp[:2], axis=1)) + 1e-9
    C1 = diag([1/maxstd, 1/maxstd, 1]) 
    C1[0][2] = -m[0]/maxstd
    C1[1][2] = -m[1]/maxstd
    fp = dot(C1,fp)
    
    # --to points--
    m = mean(tp[:2], axis=1)
    maxstd = max(std(tp[:2], axis=1)) + 1e-9
    C2 = diag([1/maxstd, 1/maxstd, 1])
    C2[0][2] = -m[0]/maxstd
    C2[1][2] = -m[1]/maxstd
    tp = dot(C2,tp)
    
    # create matrix for linear method, 2 rows for each correspondence pair
    nbr_correspondences = fp.shape[1]
    A = zeros((2*nbr_correspondences,9))
    for i in range(nbr_correspondences):        
        A[2*i] = [-fp[0][i],-fp[1][i],-1,0,0,0,
                    tp[0][i]*fp[0][i],tp[0][i]*fp[1][i],tp[0][i]]
        A[2*i+1] = [0,0,0,-fp[0][i],-fp[1][i],-1,
                    tp[1][i]*fp[0][i],tp[1][i]*fp[1][i],tp[1][i]]
    
    U,S,V = linalg.svd(A)
    H = V[8].reshape((3,3))    
    
    # decondition
    H = dot(linalg.inv(C2),dot(H,C1))
    
    # normalize and return
    return H / H[2,2]


def Haffine_from_points(fp,tp):
    """ Find H, affine transformation, such that 
        tp is affine transf of fp. """
    
    if fp.shape != tp.shape:
        raise RuntimeError('number of points do not match')
        
    # condition points
    # --from points--
    m = mean(fp[:2], axis=1)
    maxstd = max(std(fp[:2], axis=1)) + 1e-9
    C1 = diag([1/maxstd, 1/maxstd, 1]) 
    C1[0][2] = -m[0]/maxstd
    C1[1][2] = -m[1]/maxstd
    fp_cond = dot(C1,fp)
    
    # --to points--
    m = mean(tp[:2], axis=1)
    C2 = C1.copy() #must use same scaling for both point sets
    C2[0][2] = -m[0]/maxstd
    C2[1][2] = -m[1]/maxstd
    tp_cond = dot(C2,tp)
    
    # conditioned points have mean zero, so translation is zero
    A = concatenate((fp_cond[:2],tp_cond[:2]), axis=0)
    U,S,V = linalg.svd(A.T)
    
    # create B and C matrices as Hartley-Zisserman (2:nd ed) p 130.
    tmp = V[:2].T
    B = tmp[:2]
    C = tmp[2:4]
    
    tmp2 = concatenate((dot(C,linalg.pinv(B)),zeros((2,1))), axis=1) 
    H = vstack((tmp2,[0,0,1]))
    
    # decondition
    H = dot(linalg.inv(C2),dot(H,C1))
    
    return H / H[2,2]


def normalize(points):
    """ Normalize a collection of points in 
        homogeneous coordinates so that last row = 1. """

    for row in points:
        row /= points[-1]
    return points
    
    
def make_homog(points):
    """ Convert a set of points (dim*n array) to 
        homogeneous coordinates. """
        
    return vstack((points,ones((1,points.shape[1])))) 
 
########NEW FILE########
__FILENAME__ = imagesearch
from numpy import *
import pickle
from pysqlite2 import dbapi2 as sqlite


class Indexer(object):
    
    def __init__(self,db,voc):
        """ Initialize with the name of the database 
            and a vocabulary object. """
            
        self.con = sqlite.connect(db)
        self.voc = voc
    
    def __del__(self):
        self.con.close()
    
    def db_commit(self):
        self.con.commit()
    
    def get_id(self,imname):
        """ Get an entry id and add if not present. """
        
        cur = self.con.execute(
        "select rowid from imlist where filename='%s'" % imname)
        res=cur.fetchone()
        if res==None:
            cur = self.con.execute(
            "insert into imlist(filename) values ('%s')" % imname)
            return cur.lastrowid
        else:
            return res[0] 
    
    def is_indexed(self,imname):
        """ Returns True if imname has been indexed. """
        
        im = self.con.execute("select rowid from imlist where filename='%s'" % imname).fetchone()
        return im != None
    
    def add_to_index(self,imname,descr):
        """ Take an image with feature descriptors, 
            project on vocabulary and add to database. """
            
        if self.is_indexed(imname): return
        print 'indexing', imname
        
        # get the imid
        imid = self.get_id(imname)
        
        # get the words
        imwords = self.voc.project(descr)
        nbr_words = imwords.shape[0]
        
        # link each word to image
        for i in range(nbr_words):
            word = imwords[i]
            # wordid is the word number itself
            self.con.execute("insert into imwords(imid,wordid,vocname) values (?,?,?)", (imid,word,self.voc.name))
            
        # store word histogram for image
        # use pickle to encode NumPy arrays as strings
        self.con.execute("insert into imhistograms(imid,histogram,vocname) values (?,?,?)", (imid,pickle.dumps(imwords),self.voc.name))
    
    def create_tables(self): 
        """ Create the database tables. """
        
        self.con.execute('create table imlist(filename)')
        self.con.execute('create table imwords(imid,wordid,vocname)')
        self.con.execute('create table imhistograms(imid,histogram,vocname)')        
        self.con.execute('create index im_idx on imlist(filename)')
        self.con.execute('create index wordid_idx on imwords(wordid)')
        self.con.execute('create index imid_idx on imwords(imid)')
        self.con.execute('create index imidhist_idx on imhistograms(imid)')
        self.db_commit()


class Searcher(object):
    
    def __init__(self,db,voc):
        """ Initialize with the name of the database. """
        self.con = sqlite.connect(db)
        self.voc = voc
    
    def __del__(self):
        self.con.close()
    
    def get_imhistogram(self,imname):
        """ Return the word histogram for an image. """
        
        im_id = self.con.execute(
            "select rowid from imlist where filename='%s'" % imname).fetchone()
        s = self.con.execute(
            "select histogram from imhistograms where rowid='%d'" % im_id).fetchone()
        
        # use pickle to decode NumPy arrays from string
        return pickle.loads(str(s[0]))
    
    def candidates_from_word(self,imword):
        """ Get list of images containing imword. """
        
        im_ids = self.con.execute(
            "select distinct imid from imwords where wordid=%d" % imword).fetchall()
        return [i[0] for i in im_ids]
    
    def candidates_from_histogram(self,imwords):
        """ Get list of images with similar words. """
        
        # get the word ids
        words = imwords.nonzero()[0]
        
        # find candidates
        candidates = []
        for word in words:
            c = self.candidates_from_word(word)
            candidates+=c
        
        # take all unique words and reverse sort on occurrence 
        tmp = [(w,candidates.count(w)) for w in set(candidates)]
        tmp.sort(cmp=lambda x,y:cmp(x[1],y[1]))
        tmp.reverse()
        
        # return sorted list, best matches first    
        return [w[0] for w in tmp] 
    
    def query(self,imname):
        """ Find a list of matching images for imname. """
        
        h = self.get_imhistogram(imname)
        candidates = self.candidates_from_histogram(h)
        
        matchscores = []
        for imid in candidates:
            # get the name
            cand_name = self.con.execute(
                "select filename from imlist where rowid=%d" % imid).fetchone()
            cand_h = self.get_imhistogram(cand_name)
            cand_dist = sqrt( sum( self.voc.idf*(h-cand_h)**2 ) )
            matchscores.append( (cand_dist,imid) )
        
        # return a sorted list of distances and database ids
        matchscores.sort()
        return matchscores
    
    def get_filename(self,imid):
        """ Return the filename for an image id. """
        
        s = self.con.execute(
            "select filename from imlist where rowid='%d'" % imid).fetchone()
        return s[0]


def tf_idf_dist(voc,v1,v2):
    
    v1 /= sum(v1)
    v2 /= sum(v2)
    
    return sqrt( sum( voc.idf*(v1-v2)**2 ) )


def compute_ukbench_score(src,imlist):
    """ Returns the average number of correct
        images on the top four results of queries. """
        
    nbr_images = len(imlist)
    pos = zeros((nbr_images,4))
    # get first four results for each image
    for i in range(nbr_images):
        pos[i] = [w[1]-1 for w in src.query(imlist[i])[:4]]
    
    # compute score and return average
    score = array([ (pos[i]//4)==(i//4) for i in range(nbr_images)])*1.0
    return sum(score) / (nbr_images)


# import PIL and pylab for plotting        
from PIL import Image
from pylab import *

def plot_results(src,res):
    """ Show images in result list 'res'. """
    
    figure()
    nbr_results = len(res)
    for i in range(nbr_results):
        imname = src.get_filename(res[i])
        subplot(1,nbr_results,i+1)
        imshow(array(Image.open(imname)))
        axis('off')
    show()
########NEW FILE########
__FILENAME__ = imregistration
from PIL import Image
from xml.dom import minidom
from numpy import *
from pylab import *

from scipy import ndimage, linalg
from scipy.misc import imsave
import os

def read_points_from_xml(xmlFileName):
    """ Reads control points for face alignment. """

    xmldoc = minidom.parse(xmlFileName)
    facelist = xmldoc.getElementsByTagName('face')    
    faces = {}    
    for xmlFace in facelist:
        fileName = xmlFace.attributes['file'].value
        xf = int(xmlFace.attributes['xf'].value)
        yf = int(xmlFace.attributes['yf'].value)     
        xs = int(xmlFace.attributes['xs'].value)
        ys = int(xmlFace.attributes['ys'].value)
        xm = int(xmlFace.attributes['xm'].value)
        ym = int(xmlFace.attributes['ym'].value)
        faces[fileName] = array([xf, yf, xs, ys, xm, ym])
    return faces
    
    
def write_points_to_xml(faces, xmlFileName):
    xmldoc = minidom.Document()
    xmlFaces = xmldoc.createElement("faces")

    keys = faces.keys()
    for k in keys:
        xmlFace = xmldoc.createElement("face")
        xmlFace.setAttribute("file", k)
        xmlFace.setAttribute("xf", "%d" % faces[k][0])    
        xmlFace.setAttribute("yf", "%d" % faces[k][1])
        xmlFace.setAttribute("xs", "%d" % faces[k][2])    
        xmlFace.setAttribute("ys", "%d" % faces[k][3])
        xmlFace.setAttribute("xm", "%d" % faces[k][4])
        xmlFace.setAttribute("ym", "%d" % faces[k][5])
        xmlFaces.appendChild(xmlFace)

    xmldoc.appendChild(xmlFaces)

    fp = open(xmlFileName, "w")
    fp.write(xmldoc.toprettyxml(encoding='utf-8'))    
    fp.close()


def compute_rigid_transform(refpoints,points):
    """ Computes rotation, scale and translation for
        aligning points to refpoints. """
    
    A = array([    [points[0], -points[1], 1, 0],
                [points[1],  points[0], 0, 1],
                [points[2], -points[3], 1, 0],
                [points[3],  points[2], 0, 1],
                [points[4], -points[5], 1, 0],
                [points[5],  points[4], 0, 1]])

    y = array([    refpoints[0],
                refpoints[1],
                refpoints[2],
                refpoints[3],
                refpoints[4],
                refpoints[5]])
    
    # least sq solution to mimimize ||Ax - y||
    a,b,tx,ty = linalg.lstsq(A,y)[0]
    R = array([[a, -b], [b, a]]) # rotation matrix incl scale

    return R,tx,ty


def rigid_alignment(faces,path,plotflag=False):
    """    Align images rigidly and save as new images.
        path determines where the aligned images are saved
        set plotflag=True to plot the images. """
    
    # take the points in the first image as reference points
    refpoints = faces.values()[0]
    
    # warp each image using affine transform
    for face in faces:
        points = faces[face]
        
        R,tx,ty = compute_rigid_transform(refpoints, points)
        T = array([[R[1][1], R[1][0]], [R[0][1], R[0][0]]])    
        
        im = array(Image.open(os.path.join(path,face)))
        im2 = zeros(im.shape, 'uint8')
        
        # warp each color channel
        for i in range(len(im.shape)):
            im2[:,:,i] = ndimage.affine_transform(im[:,:,i],linalg.inv(T),offset=[-ty,-tx])
            
        if plotflag:
            imshow(im2)
            show()
            
        # crop away border and save aligned images
        h,w = im2.shape[:2]
        border = (w+h)/20
        
        # crop away border
        imsave(os.path.join(path, 'aligned/'+face),im2[border:h-border,border:w-border,:])


########NEW FILE########
__FILENAME__ = imtools
import os
from PIL import Image
from pylab import *
from numpy import *



def get_imlist(path):
    """    Returns a list of filenames for 
        all jpg images in a directory. """
        
    return [os.path.join(path,f) for f in os.listdir(path) if f.endswith('.jpg')]


def compute_average(imlist):
    """    Compute the average of a list of images. """
    
    # open first image and make into array of type float
    averageim = array(Image.open(imlist[0]), 'f') 

    skipped = 0
    
    for imname in imlist[1:]:
        try: 
            averageim += array(Image.open(imname))
        except:
            print imname + "...skipped"  
            skipped += 1

    averageim /= (len(imlist) - skipped)
    
    # return average as uint8
    return array(averageim, 'uint8')

    
def convert_to_grayscale(imlist):
    """    Convert a set of images to grayscale. """
    
    for imname in imlist:
        im = Image.open(imname).convert("L")
        im.save(imname)


def imresize(im,sz):
    """    Resize an image array using PIL. """
    pil_im = Image.fromarray(uint8(im))
    
    return array(pil_im.resize(sz))


def histeq(im,nbr_bins=256):
    """    Histogram equalization of a grayscale image. """
    
    # get image histogram
    imhist,bins = histogram(im.flatten(),nbr_bins,normed=True)
    cdf = imhist.cumsum() # cumulative distribution function
    cdf = 255 * cdf / cdf[-1] # normalize
    
    # use linear interpolation of cdf to find new pixel values
    im2 = interp(im.flatten(),bins[:-1],cdf)
    
    return im2.reshape(im.shape), cdf
    
    
def plot_2D_boundary(plot_range,points,decisionfcn,labels,values=[0]):
    """    Plot_range is (xmin,xmax,ymin,ymax), points is a list
        of class points, decisionfcn is a funtion to evaluate, 
        labels is a list of labels that decisionfcn returns for each class, 
        values is a list of decision contours to show. """
        
    clist = ['b','r','g','k','m','y'] # colors for the classes
    
    # evaluate on a grid and plot contour of decision function
    x = arange(plot_range[0],plot_range[1],.1)
    y = arange(plot_range[2],plot_range[3],.1)
    xx,yy = meshgrid(x,y)
    xxx,yyy = xx.flatten(),yy.flatten() # lists of x,y in grid
    zz = array(decisionfcn(xxx,yyy)) 
    zz = zz.reshape(xx.shape)
    # plot contour(s) at values
    contour(xx,yy,zz,values) 
        
    # for each class, plot the points with '*' for correct, 'o' for incorrect
    for i in range(len(points)):
        d = decisionfcn(points[i][:,0],points[i][:,1])
        correct_ndx = labels[i]==d
        incorrect_ndx = labels[i]!=d
        plot(points[i][correct_ndx,0],points[i][correct_ndx,1],'*',color=clist[i])
        plot(points[i][incorrect_ndx,0],points[i][incorrect_ndx,1],'o',color=clist[i])
    
    axis('equal')

########NEW FILE########
__FILENAME__ = knn
from numpy import * 

class KnnClassifier(object):
    
    def __init__(self,labels,samples):
        """ Initialize classifier with training data. """
        
        self.labels = labels
        self.samples = samples
    
    def classify(self,point,k=3):
        """ Classify a point against k nearest 
            in the training data, return label. """
        
        # compute distance to all training points
        dist = array([L2dist(point,s) for s in self.samples])
        
        # sort them
        ndx = dist.argsort()
        
        # use dictionary to store the k nearest
        votes = {}
        for i in range(k):
            label = self.labels[ndx[i]]
            votes.setdefault(label,0)
            votes[label] += 1
            
        return max(votes)


def L2dist(p1,p2):
    return sqrt( sum( (p1-p2)**2) )

def L1dist(v1,v2):
    return sum(abs(v1-v2))
########NEW FILE########
__FILENAME__ = lktrack
from numpy import *
import cv2


# some constants and default parameters
lk_params = dict(winSize=(15,15),maxLevel=2,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,10,0.03)) 

subpix_params = dict(zeroZone=(-1,-1),winSize=(10,10),
                     criteria = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS,20,0.03))

feature_params = dict(maxCorners=500,qualityLevel=0.01,minDistance=10)


class LKTracker(object):
    """    Class for Lucas-Kanade tracking with 
        pyramidal optical flow."""

    def __init__(self,imnames):
        """    Initialize with a list of image names. """

        self.imnames = imnames
        self.features = []
        self.tracks = []
        self.current_frame = 0

    def step(self,framenbr=None):
        """    Step to another frame. If no argument is 
            given, step to the next frame. """

        if framenbr is None:
            self.current_frame = (self.current_frame + 1) % len(self.imnames)
        else:
            self.current_frame = framenbr % len(self.imnames)

    def detect_points(self):
        """    Detect 'good features to track' (corners) in the current frame
            using sub-pixel accuracy. """

        # load the image and create grayscale
        self.image = cv2.imread(self.imnames[self.current_frame])
        self.gray = cv2.cvtColor(self.image,cv2.COLOR_BGR2GRAY)

        # search for good points
        features = cv2.goodFeaturesToTrack(self.gray, **feature_params)

        # refine the corner locations
        cv2.cornerSubPix(self.gray,features, **subpix_params)
        
        self.features = features
        self.tracks = [[p] for p in features.reshape((-1,2))]
        
        self.prev_gray = self.gray

    def track_points(self):
        """    Track the detected features. """

        if self.features != []:
            self.step() # move to the next frame
            
            # load the image and create grayscale
            self.image = cv2.imread(self.imnames[self.current_frame])
            self.gray = cv2.cvtColor(self.image,cv2.COLOR_BGR2GRAY)
            
            # reshape to fit input format
            tmp = float32(self.features).reshape(-1, 1, 2)
            
            # calculate optical flow
            features,status,track_error = cv2.calcOpticalFlowPyrLK(self.prev_gray,self.gray,tmp,None,**lk_params)

            # remove points lost
            self.features = [p for (st,p) in zip(status,features) if st]
            
            # clean tracks from lost points
            features = array(features).reshape((-1,2))
            for i,f in enumerate(features):
                self.tracks[i].append(f)
            ndx = [i for (i,st) in enumerate(status) if not st]
            ndx.reverse() #remove from back
            for i in ndx:
                self.tracks.pop(i)
            
            self.prev_gray = self.gray
            
    def track(self):
        """    Generator for stepping through a sequence."""

        for i in range(len(self.imnames)):
            if self.features == []:
                self.detect_points()
            else:
                self.track_points()
            
            # create a copy in RGB
            f = array(self.features).reshape(-1,2)
            im = cv2.cvtColor(self.image,cv2.COLOR_BGR2RGB)
            yield im,f

    def draw(self):
        """    Draw the current image with points using
            OpenCV's own drawing functions. 
            Press ant key to close window."""

        # draw points as green circles
        for point in self.features:
            cv2.circle(self.image,(int(point[0][0]),int(point[0][1])),3,(0,255,0),-1)
        
        cv2.imshow('LKtrack',self.image)
        cv2.waitKey()

########NEW FILE########
__FILENAME__ = ncut
from PIL import Image
from pylab import *
from numpy import *
from scipy.cluster.vq import *


def cluster(S,k,ndim):
    """ Spectral clustering from a similarity matrix."""
    
    # check for symmetry
    if sum(abs(S-S.T)) > 1e-10:
        print 'not symmetric'
    
    # create Laplacian matrix
    rowsum = sum(abs(S),axis=0)
    D = diag(1 / sqrt(rowsum + 1e-6))
    L = dot(D,dot(S,D))
    
    # compute eigenvectors of L
    U,sigma,V = linalg.svd(L,full_matrices=False)
    
    # create feature vector from ndim first eigenvectors
    # by stacking eigenvectors as columns
    features = array(V[:ndim]).T

    # k-means
    features = whiten(features)
    centroids,distortion = kmeans(features,k)
    code,distance = vq(features,centroids)
        
    return code,V


def ncut_graph_matrix(im,sigma_d=1e2,sigma_g=1e-2):
    """ Create matrix for normalized cut. The parameters are 
        the weights for pixel distance and pixel similarity. """
    
    m,n = im.shape[:2] 
    N = m*n
    
    # normalize and create feature vector of RGB or grayscale
    if len(im.shape)==3:
        for i in range(3):
            im[:,:,i] = im[:,:,i] / im[:,:,i].max()
        vim = im.reshape((-1,3))
    else:
        im = im / im.max()
        vim = im.flatten()
    
    # x,y coordinates for distance computation
    xx,yy = meshgrid(range(n),range(m))
    x,y = xx.flatten(),yy.flatten()
    
    # create matrix with edge weights
    W = zeros((N,N),'f')
    for i in range(N):
        for j in range(i,N):
            d = (x[i]-x[j])**2 + (y[i]-y[j])**2 
            W[i,j] = W[j,i] = exp(-1.0*sum((vim[i]-vim[j])**2)/sigma_g) * exp(-d/sigma_d)
    
    return W

########NEW FILE########
__FILENAME__ = pca
from PIL import Image
from numpy import *


def pca(X):
    """    Principal Component Analysis
        input: X, matrix with training data stored as flattened arrays in rows
        return: projection matrix (with important dimensions first), variance and mean.
    """
    
    # get dimensions
    num_data,dim = X.shape
    
    # center data
    mean_X = X.mean(axis=0)
    X = X - mean_X
    
    if dim>num_data:
        # PCA - compact trick used
        M = dot(X,X.T) # covariance matrix
        e,EV = linalg.eigh(M) # eigenvalues and eigenvectors
        tmp = dot(X.T,EV).T # this is the compact trick
        V = tmp[::-1] # reverse since last eigenvectors are the ones we want
        S = sqrt(e)[::-1] # reverse since eigenvalues are in increasing order
        for i in range(V.shape[1]):
            V[:,i] /= S
    else:
        # PCA - SVD used
        U,S,V = linalg.svd(X)
        V = V[:num_data] # only makes sense to return the first num_data
    
    # return the projection matrix, the variance and the mean
    return V,S,mean_X


def center(X):
    """    Center the square matrix X (subtract col and row means). """
    
    n,m = X.shape
    if n != m:
        raise Exception('Matrix is not square.')
    
    colsum = X.sum(axis=0) / n
    rowsum = X.sum(axis=1) / n
    totalsum = X.sum() / (n**2)
    
    #center
    Y = array([[ X[i,j]-rowsum[i]-colsum[j]+totalsum for i in range(n) ] for j in range(n)])
    
    return Y
########NEW FILE########
__FILENAME__ = ransac
import numpy
import scipy # use numpy if scipy unavailable
import scipy.linalg # use numpy if scipy unavailable

## Copyright (c) 2004-2007, Andrew D. Straw. All rights reserved.

## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:

##     * Redistributions of source code must retain the above copyright
##       notice, this list of conditions and the following disclaimer.

##     * Redistributions in binary form must reproduce the above
##       copyright notice, this list of conditions and the following
##       disclaimer in the documentation and/or other materials provided
##       with the distribution.

##     * Neither the name of the Andrew D. Straw nor the names of its
##       contributors may be used to endorse or promote products derived
##       from this software without specific prior written permission.

## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

def ransac(data,model,n,k,t,d,debug=False,return_all=False):
    """fit model parameters to data using the RANSAC algorithm
    
This implementation written from pseudocode found at
http://en.wikipedia.org/w/index.php?title=RANSAC&oldid=116358182

{{{
Given:
    data - a set of observed data points
    model - a model that can be fitted to data points
    n - the minimum number of data values required to fit the model
    k - the maximum number of iterations allowed in the algorithm
    t - a threshold value for determining when a data point fits a model
    d - the number of close data values required to assert that a model fits well to data
Return:
    bestfit - model parameters which best fit the data (or nil if no good model is found)
iterations = 0
bestfit = nil
besterr = something really large
while iterations < k {
    maybeinliers = n randomly selected values from data
    maybemodel = model parameters fitted to maybeinliers
    alsoinliers = empty set
    for every point in data not in maybeinliers {
        if point fits maybemodel with an error smaller than t
             add point to alsoinliers
    }
    if the number of elements in alsoinliers is > d {
        % this implies that we may have found a good model
        % now test how good it is
        bettermodel = model parameters fitted to all points in maybeinliers and alsoinliers
        thiserr = a measure of how well model fits these points
        if thiserr < besterr {
            bestfit = bettermodel
            besterr = thiserr
        }
    }
    increment iterations
}
return bestfit
}}}
"""
    iterations = 0
    bestfit = None
    besterr = numpy.inf
    best_inlier_idxs = None
    while iterations < k:
        maybe_idxs, test_idxs = random_partition(n,data.shape[0])
        maybeinliers = data[maybe_idxs,:]
        test_points = data[test_idxs]
        maybemodel = model.fit(maybeinliers)
        test_err = model.get_error( test_points, maybemodel)
        also_idxs = test_idxs[test_err < t] # select indices of rows with accepted points
        alsoinliers = data[also_idxs,:]
        if debug:
            print 'test_err.min()',test_err.min()
            print 'test_err.max()',test_err.max()
            print 'numpy.mean(test_err)',numpy.mean(test_err)
            print 'iteration %d:len(alsoinliers) = %d'%(
                iterations,len(alsoinliers))
        if len(alsoinliers) > d:
            betterdata = numpy.concatenate( (maybeinliers, alsoinliers) )
            bettermodel = model.fit(betterdata)
            better_errs = model.get_error( betterdata, bettermodel)
            thiserr = numpy.mean( better_errs )
            if thiserr < besterr:
                bestfit = bettermodel
                besterr = thiserr
                best_inlier_idxs = numpy.concatenate( (maybe_idxs, also_idxs) )
        iterations+=1
    if bestfit is None:
        raise ValueError("did not meet fit acceptance criteria")
    if return_all:
        return bestfit, {'inliers':best_inlier_idxs}
    else:
        return bestfit

def random_partition(n,n_data):
    """return n random rows of data (and also the other len(data)-n rows)"""
    all_idxs = numpy.arange( n_data )
    numpy.random.shuffle(all_idxs)
    idxs1 = all_idxs[:n]
    idxs2 = all_idxs[n:]
    return idxs1, idxs2

class LinearLeastSquaresModel:
    """linear system solved using linear least squares

    This class serves as an example that fulfills the model interface
    needed by the ransac() function.
    
    """
    def __init__(self,input_columns,output_columns,debug=False):
        self.input_columns = input_columns
        self.output_columns = output_columns
        self.debug = debug
    def fit(self, data):
        A = numpy.vstack([data[:,i] for i in self.input_columns]).T
        B = numpy.vstack([data[:,i] for i in self.output_columns]).T
        x,resids,rank,s = numpy.linalg.lstsq(A,B)
        return x
    def get_error( self, data, model):
        A = numpy.vstack([data[:,i] for i in self.input_columns]).T
        B = numpy.vstack([data[:,i] for i in self.output_columns]).T
        B_fit = scipy.dot(A,model)
        err_per_point = numpy.sum((B-B_fit)**2,axis=1) # sum squared error per row
        return err_per_point
        
def test():
    # generate perfect input data

    n_samples = 500
    n_inputs = 1
    n_outputs = 1
    A_exact = 20*numpy.random.random((n_samples,n_inputs) )
    perfect_fit = 60*numpy.random.normal(size=(n_inputs,n_outputs) ) # the model
    B_exact = scipy.dot(A_exact,perfect_fit)
    assert B_exact.shape == (n_samples,n_outputs)

    # add a little gaussian noise (linear least squares alone should handle this well)
    A_noisy = A_exact + numpy.random.normal(size=A_exact.shape )
    B_noisy = B_exact + numpy.random.normal(size=B_exact.shape )

    if 1:
        # add some outliers
        n_outliers = 100
        all_idxs = numpy.arange( A_noisy.shape[0] )
        numpy.random.shuffle(all_idxs)
        outlier_idxs = all_idxs[:n_outliers]
        non_outlier_idxs = all_idxs[n_outliers:]
        A_noisy[outlier_idxs] =  20*numpy.random.random((n_outliers,n_inputs) )
        B_noisy[outlier_idxs] = 50*numpy.random.normal(size=(n_outliers,n_outputs) )

    # setup model

    all_data = numpy.hstack( (A_noisy,B_noisy) )
    input_columns = range(n_inputs) # the first columns of the array
    output_columns = [n_inputs+i for i in range(n_outputs)] # the last columns of the array
    debug = True
    model = LinearLeastSquaresModel(input_columns,output_columns,debug=debug)
    
    linear_fit,resids,rank,s = numpy.linalg.lstsq(all_data[:,input_columns],all_data[:,output_columns])

    # run RANSAC algorithm
    ransac_fit, ransac_data = ransac(all_data,model,
                                     5, 5000, 7e4, 50, # misc. parameters
                                     debug=debug,return_all=True)
    if 1:
        import pylab

        sort_idxs = numpy.argsort(A_exact[:,0])
        A_col0_sorted = A_exact[sort_idxs] # maintain as rank-2 array

        if 1:
            pylab.plot( A_noisy[:,0], B_noisy[:,0], 'k.', label='data' )
            pylab.plot( A_noisy[ransac_data['inliers'],0], B_noisy[ransac_data['inliers'],0], 'bx', label='RANSAC data' )
        else:
            pylab.plot( A_noisy[non_outlier_idxs,0], B_noisy[non_outlier_idxs,0], 'k.', label='noisy data' )
            pylab.plot( A_noisy[outlier_idxs,0], B_noisy[outlier_idxs,0], 'r.', label='outlier data' )
        pylab.plot( A_col0_sorted[:,0],
                    numpy.dot(A_col0_sorted,ransac_fit)[:,0],
                    label='RANSAC fit' )
        pylab.plot( A_col0_sorted[:,0],
                    numpy.dot(A_col0_sorted,perfect_fit)[:,0],
                    label='exact system' )
        pylab.plot( A_col0_sorted[:,0],
                    numpy.dot(A_col0_sorted,linear_fit)[:,0],
                    label='linear fit' )
        pylab.legend()
        pylab.show()

if __name__=='__main__':
    test()
    

########NEW FILE########
__FILENAME__ = rof
from numpy import *


def denoise(im,U_init,tolerance=0.1,tau=0.125,tv_weight=100):
    """ An implementation of the Rudin-Osher-Fatemi (ROF) denoising model
        using the numerical procedure presented in Eq. (11) of A. Chambolle
        (2005). Implemented using periodic boundary conditions.
        
        Input: noisy input image (grayscale), initial guess for U, weight of 
        the TV-regularizing term, steplength, tolerance for the stop criterion
        
        Output: denoised and detextured image, texture residual. """
        
    m,n = im.shape #size of noisy image

    # initialize
    U = U_init
    Px = zeros((m, n)) # x-component to the dual field (NOTE: this initialization changed from what's in the book)
    Py = zeros((m, n)) # y-component of the dual field
    error = 1 
    
    while (error > tolerance):
        Uold = U
        
        # gradient of primal variable
        GradUx = roll(U,-1,axis=1)-U # x-component of U's gradient
        GradUy = roll(U,-1,axis=0)-U # y-component of U's gradient
        
        # update the dual varible
        PxNew = Px + (tau/tv_weight)*GradUx # non-normalized update of x-component (dual)
        PyNew = Py + (tau/tv_weight)*GradUy # non-normalized update of y-component (dual)
        NormNew = maximum(1,sqrt(PxNew**2+PyNew**2))
        
        Px = PxNew/NormNew # update of x-component (dual)
        Py = PyNew/NormNew # update of y-component (dual)
        
        # update the primal variable
        RxPx = roll(Px,1,axis=1) # right x-translation of x-component
        RyPy = roll(Py,1,axis=0) # right y-translation of y-component
        
        DivP = (Px-RxPx)+(Py-RyPy) # divergence of the dual field.
        U = im + tv_weight*DivP # update of the primal variable
        
        # update of error
        error = linalg.norm(U-Uold)/sqrt(n*m);
        
    return U,im-U # denoised image and texture residual

########NEW FILE########
__FILENAME__ = searchdemo
import cherrypy, os, urllib, pickle
from numpy import *
import imagesearch


class SearchDemo:
    
    def __init__(self):
        # load list of images
        f = open('webimlist.txt')
        self.imlist = f.readlines()
        f.close()
        self.nbr_images = len(self.imlist)
        self.ndx = range(self.nbr_images)
        
        # load vocabulary
        f = open('vocabulary.pkl', 'rb')
        self.voc = pickle.load(f)
        f.close()
        
        # set max number of results to show
        self.maxres = 15
        
        # header and footer html
        self.header = """
            <!doctype html>
            <head>
            <title>Image search example</title>
            </head>
            <body>
            """
        self.footer = """
            </body>
            </html>
            """
        
    def index(self,query=None):
        self.src = imagesearch.Searcher('web.db',self.voc)
        
        html = self.header
        html += """
            <br />
            Click an image to search. <a href='?query='> Random selection </a> of images.
            <br /><br />
            """
        if query:
            # query the database and get top images
            res = self.src.query(query)[:self.maxres]
            for dist,ndx in res:
                imname = self.src.get_filename(ndx)
                html += "<a href='?query="+imname+"'>"
                html += "<img src='"+imname+"' width='100' />"
                html += "</a>"
        else:
            # show random selection if no query
            random.shuffle(self.ndx)
            for i in self.ndx[:self.maxres]:
                imname = self.imlist[i]
                html += "<a href='?query="+imname+"'>"
                html += "<img src='"+imname+"' width='100' />"
                html += "</a>"
                
        html += self.footer
        return html
    
    index.exposed = True

cherrypy.quickstart(SearchDemo(), '/', config=os.path.join(os.path.dirname(__file__), 'service.conf'))
########NEW FILE########
__FILENAME__ = sfm
from pylab import *
from numpy import *
from scipy import linalg


def compute_P(x,X):
    """    Compute camera matrix from pairs of
        2D-3D correspondences (in homog. coordinates). """

    n = x.shape[1]
    if X.shape[1] != n:
        raise ValueError("Number of points don't match.")
        
    # create matrix for DLT solution
    M = zeros((3*n,12+n))
    for i in range(n):
        M[3*i,0:4] = X[:,i]
        M[3*i+1,4:8] = X[:,i]
        M[3*i+2,8:12] = X[:,i]
        M[3*i:3*i+3,i+12] = -x[:,i]
        
    U,S,V = linalg.svd(M)
    
    return V[-1,:12].reshape((3,4))


def triangulate_point(x1,x2,P1,P2):
    """ Point pair triangulation from 
        least squares solution. """
        
    M = zeros((6,6))
    M[:3,:4] = P1
    M[3:,:4] = P2
    M[:3,4] = -x1
    M[3:,5] = -x2

    U,S,V = linalg.svd(M)
    X = V[-1,:4]

    return X / X[3]


def triangulate(x1,x2,P1,P2):
    """    Two-view triangulation of points in 
        x1,x2 (3*n homog. coordinates). """
        
    n = x1.shape[1]
    if x2.shape[1] != n:
        raise ValueError("Number of points don't match.")

    X = [ triangulate_point(x1[:,i],x2[:,i],P1,P2) for i in range(n)]
    return array(X).T


def compute_fundamental(x1,x2):
    """    Computes the fundamental matrix from corresponding points 
        (x1,x2 3*n arrays) using the 8 point algorithm.
        Each row in the A matrix below is constructed as
        [x'*x, x'*y, x', y'*x, y'*y, y', x, y, 1] """
    
    n = x1.shape[1]
    if x2.shape[1] != n:
        raise ValueError("Number of points don't match.")
    
    # build matrix for equations
    A = zeros((n,9))
    for i in range(n):
        A[i] = [x1[0,i]*x2[0,i], x1[0,i]*x2[1,i], x1[0,i]*x2[2,i],
                x1[1,i]*x2[0,i], x1[1,i]*x2[1,i], x1[1,i]*x2[2,i],
                x1[2,i]*x2[0,i], x1[2,i]*x2[1,i], x1[2,i]*x2[2,i] ]
            
    # compute linear least square solution
    U,S,V = linalg.svd(A)
    F = V[-1].reshape(3,3)
        
    # constrain F
    # make rank 2 by zeroing out last singular value
    U,S,V = linalg.svd(F)
    S[2] = 0
    F = dot(U,dot(diag(S),V))
    
    return F/F[2,2]


def compute_epipole(F):
    """ Computes the (right) epipole from a 
        fundamental matrix F. 
        (Use with F.T for left epipole.) """
    
    # return null space of F (Fx=0)
    U,S,V = linalg.svd(F)
    e = V[-1]
    return e/e[2]
    
    
def plot_epipolar_line(im,F,x,epipole=None,show_epipole=True):
    """ Plot the epipole and epipolar line F*x=0
        in an image. F is the fundamental matrix 
        and x a point in the other image."""
    
    m,n = im.shape[:2]
    line = dot(F,x)
    
    # epipolar line parameter and values
    t = linspace(0,n,100)
    lt = array([(line[2]+line[0]*tt)/(-line[1]) for tt in t])

    # take only line points inside the image
    ndx = (lt>=0) & (lt<m) 
    plot(t[ndx],lt[ndx],linewidth=2)
    
    if show_epipole:
        if epipole is None:
            epipole = compute_epipole(F)
        plot(epipole[0]/epipole[2],epipole[1]/epipole[2],'r*')
    

def skew(a):
    """ Skew matrix A such that a x v = Av for any v. """

    return array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])


def compute_P_from_fundamental(F):
    """    Computes the second camera matrix (assuming P1 = [I 0]) 
        from a fundamental matrix. """
        
    e = compute_epipole(F.T) # left epipole
    Te = skew(e)
    return vstack((dot(Te,F.T).T,e)).T


def compute_P_from_essential(E):
    """    Computes the second camera matrix (assuming P1 = [I 0]) 
        from an essential matrix. Output is a list of four 
        possible camera matrices. """
    
    # make sure E is rank 2
    U,S,V = svd(E)
    if det(dot(U,V))<0:
        V = -V
    E = dot(U,dot(diag([1,1,0]),V))    
    
    # create matrices (Hartley p 258)
    Z = skew([0,0,-1])
    W = array([[0,-1,0],[1,0,0],[0,0,1]])
    
    # return all four solutions
    P2 = [vstack((dot(U,dot(W,V)).T,U[:,2])).T,
             vstack((dot(U,dot(W,V)).T,-U[:,2])).T,
            vstack((dot(U,dot(W.T,V)).T,U[:,2])).T,
            vstack((dot(U,dot(W.T,V)).T,-U[:,2])).T]

    return P2


def compute_fundamental_normalized(x1,x2):
    """    Computes the fundamental matrix from corresponding points 
        (x1,x2 3*n arrays) using the normalized 8 point algorithm. """

    n = x1.shape[1]
    if x2.shape[1] != n:
        raise ValueError("Number of points don't match.")

    # normalize image coordinates
    x1 = x1 / x1[2]
    mean_1 = mean(x1[:2],axis=1)
    S1 = sqrt(2) / std(x1[:2])
    T1 = array([[S1,0,-S1*mean_1[0]],[0,S1,-S1*mean_1[1]],[0,0,1]])
    x1 = dot(T1,x1)
    
    x2 = x2 / x2[2]
    mean_2 = mean(x2[:2],axis=1)
    S2 = sqrt(2) / std(x2[:2])
    T2 = array([[S2,0,-S2*mean_2[0]],[0,S2,-S2*mean_2[1]],[0,0,1]])
    x2 = dot(T2,x2)

    # compute F with the normalized coordinates
    F = compute_fundamental(x1,x2)

    # reverse normalization
    F = dot(T1.T,dot(F,T2))

    return F/F[2,2]


class RansacModel(object):
    """ Class for fundmental matrix fit with ransac.py from
        http://www.scipy.org/Cookbook/RANSAC"""
    
    def __init__(self,debug=False):
        self.debug = debug
    
    def fit(self,data):
        """ Estimate fundamental matrix using eight 
            selected correspondences. """
        
        # transpose and split data into the two point sets
        data = data.T
        x1 = data[:3,:8]
        x2 = data[3:,:8]
        
        # estimate fundamental matrix and return
        F = compute_fundamental_normalized(x1,x2)
        return F
    
    def get_error(self,data,F):
        """ Compute x^T F x for all correspondences, 
            return error for each transformed point. """
        
        # transpose and split data into the two point
        data = data.T
        x1 = data[:3]
        x2 = data[3:]
        
        # Sampson distance as error measure
        Fx1 = dot(F,x1)
        Fx2 = dot(F,x2)
        denom = Fx1[0]**2 + Fx1[1]**2 + Fx2[0]**2 + Fx2[1]**2
        err = ( diag(dot(x1.T,dot(F,x2))) )**2 / denom 
        
        # return error per point
        return err


def F_from_ransac(x1,x2,model,maxiter=5000,match_theshold=1e-6):
    """ Robust estimation of a fundamental matrix F from point 
        correspondences using RANSAC (ransac.py from
        http://www.scipy.org/Cookbook/RANSAC).

        input: x1,x2 (3*n arrays) points in hom. coordinates. """

    import ransac

    data = vstack((x1,x2))
    
    # compute F and return with inlier index
    F,ransac_data = ransac.ransac(data.T,model,8,maxiter,match_theshold,20,return_all=True)
    return F, ransac_data['inliers']

########NEW FILE########
__FILENAME__ = sift
from PIL import Image
import os
from numpy import *
from pylab import *


def process_image(imagename,resultname,params="--edge-thresh 10 --peak-thresh 5"):
    """ Process an image and save the results in a file. """

    if imagename[-3:] != 'pgm':
        # create a pgm file
        im = Image.open(imagename).convert('L')
        im.save('tmp.pgm')
        imagename = 'tmp.pgm'

    cmmd = str("sift "+imagename+" --output="+resultname+
                " "+params)
    os.system(cmmd)
    print 'processed', imagename, 'to', resultname


def read_features_from_file(filename):
    """ Read feature properties and return in matrix form. """
    
    f = loadtxt(filename)
    return f[:,:4],f[:,4:] # feature locations, descriptors


def write_features_to_file(filename,locs,desc):
    """ Save feature location and descriptor to file. """
    savetxt(filename,hstack((locs,desc)))
    

def plot_features(im,locs,circle=False):
    """ Show image with features. input: im (image as array), 
        locs (row, col, scale, orientation of each feature). """

    def draw_circle(c,r):
        t = arange(0,1.01,.01)*2*pi
        x = r*cos(t) + c[0]
        y = r*sin(t) + c[1]
        plot(x,y,'b',linewidth=2)

    imshow(im)
    if circle:
        for p in locs:
            draw_circle(p[:2],p[2]) 
    else:
        plot(locs[:,0],locs[:,1],'ob')
    axis('off')


def match(desc1,desc2):
    """ For each descriptor in the first image, 
        select its match in the second image.
        input: desc1 (descriptors for the first image), 
        desc2 (same for second image). """
    
    desc1 = array([d/linalg.norm(d) for d in desc1])
    desc2 = array([d/linalg.norm(d) for d in desc2])
    
    dist_ratio = 0.6
    desc1_size = desc1.shape
    
    matchscores = zeros((desc1_size[0]),'int')
    desc2t = desc2.T # precompute matrix transpose
    for i in range(desc1_size[0]):
        dotprods = dot(desc1[i,:],desc2t) # vector of dot products
        dotprods = 0.9999*dotprods
        # inverse cosine and sort, return index for features in second image
        indx = argsort(arccos(dotprods))
        
        # check if nearest neighbor has angle less than dist_ratio times 2nd
        if arccos(dotprods)[indx[0]] < dist_ratio * arccos(dotprods)[indx[1]]:
            matchscores[i] = int(indx[0])
    
    return matchscores


def appendimages(im1,im2):
    """ Return a new image that appends the two images side-by-side. """
    
    # select the image with the fewest rows and fill in enough empty rows
    rows1 = im1.shape[0]    
    rows2 = im2.shape[0]
    
    if rows1 < rows2:
        im1 = concatenate((im1,zeros((rows2-rows1,im1.shape[1]))), axis=0)
    elif rows1 > rows2:
        im2 = concatenate((im2,zeros((rows1-rows2,im2.shape[1]))), axis=0)
    # if none of these cases they are equal, no filling needed.
    
    return concatenate((im1,im2), axis=1)


def plot_matches(im1,im2,locs1,locs2,matchscores,show_below=True):
    """ Show a figure with lines joining the accepted matches
        input: im1,im2 (images as arrays), locs1,locs2 (location of features), 
        matchscores (as output from 'match'), show_below (if images should be shown below). """
    
    im3 = appendimages(im1,im2)
    if show_below:
        im3 = vstack((im3,im3))
    
    # show image
    imshow(im3)
    
    # draw lines for matches
    cols1 = im1.shape[1]
    for i,m in enumerate(matchscores):
        if m>0:
            plot([locs1[i][1],locs2[m][1]+cols1],[locs1[i][0],locs2[m][0]],'c')
    axis('off')


def match_twosided(desc1,desc2):
    """ Two-sided symmetric version of match(). """
    
    matches_12 = match(desc1,desc2)
    matches_21 = match(desc2,desc1)
    
    ndx_12 = matches_12.nonzero()[0]
    
    # remove matches that are not symmetric
    for n in ndx_12:
        if matches_21[int(matches_12[n])] != n:
            matches_12[n] = 0
    
    return matches_12


########NEW FILE########
__FILENAME__ = vocabulary
from numpy import *
from scipy.cluster.vq import *
import sift


class Vocabulary(object):
    
    def __init__(self,name):
        self.name = name
        self.voc = []
        self.idf = []
        self.trainingdata = []
        self.nbr_words = 0
    
    def train(self,featurefiles,k=100,subsampling=10):
        """ Train a vocabulary from features in files listed 
            in featurefiles using k-means with k number of words. 
            Subsampling of training data can be used for speedup. """
        
        nbr_images = len(featurefiles)
        # read the features from file
        descr = []
        descr.append(sift.read_features_from_file(featurefiles[0])[1])
        descriptors = descr[0] #stack all features for k-means
        for i in arange(1,nbr_images):
            descr.append(sift.read_features_from_file(featurefiles[i])[1])
            descriptors = vstack((descriptors,descr[i]))
            
        # k-means: last number determines number of runs
        self.voc,distortion = kmeans(descriptors[::subsampling,:],k,1)
        self.nbr_words = self.voc.shape[0]
        
        # go through all training images and project on vocabulary
        imwords = zeros((nbr_images,self.nbr_words))
        for i in range( nbr_images ):
            imwords[i] = self.project(descr[i])
        
        nbr_occurences = sum( (imwords > 0)*1 ,axis=0)
        
        self.idf = log( (1.0*nbr_images) / (1.0*nbr_occurences+1) )
        self.trainingdata = featurefiles
    
    def project(self,descriptors):
        """ Project descriptors on the vocabulary
            to create a histogram of words. """
        
        # histogram of image words 
        imhist = zeros((self.nbr_words))
        words,distance = vq(descriptors,self.voc)
        for w in words:
            imhist[w] += 1
        
        return imhist
    
    def get_words(self,descriptors):
        """ Convert descriptors to words. """
        return vq(descriptors,self.voc)[0]

########NEW FILE########
__FILENAME__ = warp
import matplotlib.delaunay as md 
from scipy import ndimage
from pylab import *
from numpy import *

import homography
    

def image_in_image(im1,im2,tp):
    """ Put im1 in im2 with an affine transformation
        such that corners are as close to tp as possible.
        tp are homogeneous and counter-clockwise from top left. """ 
    
    # points to warp from
    m,n = im1.shape[:2]
    fp = array([[0,m,m,0],[0,0,n,n],[1,1,1,1]])
    
    # compute affine transform and apply
    H = homography.Haffine_from_points(tp,fp)
    im1_t = ndimage.affine_transform(im1,H[:2,:2],
                    (H[0,2],H[1,2]),im2.shape[:2])
    alpha = (im1_t > 0)
    
    return (1-alpha)*im2 + alpha*im1_t


def combine_images(im1,im2,alpha):
    """ Blend two images with weights as in alpha. """
    return (1-alpha)*im1 + alpha*im2    
    

def alpha_for_triangle(points,m,n):
    """ Creates alpha map of size (m,n) 
        for a triangle with corners defined by points
        (given in normalized homogeneous coordinates). """
    
    alpha = zeros((m,n))
    for i in range(min(points[0]),max(points[0])):
        for j in range(min(points[1]),max(points[1])):
            x = linalg.solve(points,[i,j,1])
            if min(x) > 0: #all coefficients positive
                alpha[i,j] = 1
    return alpha
    

def triangulate_points(x,y):
    """ Delaunay triangulation of 2D points. """
    
    centers,edges,tri,neighbors = md.delaunay(x,y)
    return tri


def plot_mesh(x,y,tri):
    """ Plot triangles. """ 
    
    for t in tri:
        t_ext = [t[0], t[1], t[2], t[0]] # add first point to end
        plot(x[t_ext],y[t_ext],'r')


def pw_affine(fromim,toim,fp,tp,tri):
    """ Warp triangular patches from an image.
        fromim = image to warp 
        toim = destination image
        fp = from points in hom. coordinates
        tp = to points in hom.  coordinates
        tri = triangulation. """
                
    im = toim.copy()
    
    # check if image is grayscale or color
    is_color = len(fromim.shape) == 3
    
    # create image to warp to (needed if iterate colors)
    im_t = zeros(im.shape, 'uint8') 
    
    for t in tri:
        # compute affine transformation
        H = homography.Haffine_from_points(tp[:,t],fp[:,t])
        
        if is_color:
            for col in range(fromim.shape[2]):
                im_t[:,:,col] = ndimage.affine_transform(
                    fromim[:,:,col],H[:2,:2],(H[0,2],H[1,2]),im.shape[:2])
        else:
            im_t = ndimage.affine_transform(
                    fromim,H[:2,:2],(H[0,2],H[1,2]),im.shape[:2])
        
        # alpha for triangle
        alpha = alpha_for_triangle(tp[:,t],im.shape[0],im.shape[1])
        
        # add triangle to image
        im[alpha>0] = im_t[alpha>0]
        
    return im
    
    
def panorama(H,fromim,toim,padding=2400,delta=2400):
    """ Create horizontal panorama by blending two images 
        using a homography H (preferably estimated using RANSAC).
        The result is an image with the same height as toim. 'padding' 
        specifies number of fill pixels and 'delta' additional translation. """ 
    
    # check if images are grayscale or color
    is_color = len(fromim.shape) == 3
    
    # homography transformation for geometric_transform()
    def transf(p):
        p2 = dot(H,[p[0],p[1],1])
        return (p2[0]/p2[2],p2[1]/p2[2])
    
    if H[1,2]<0: # fromim is to the right
        print 'warp - right'
        # transform fromim
        if is_color:
            # pad the destination image with zeros to the right
            toim_t = hstack((toim,zeros((toim.shape[0],padding,3))))
            fromim_t = zeros((toim.shape[0],toim.shape[1]+padding,toim.shape[2]))
            for col in range(3):
                fromim_t[:,:,col] = ndimage.geometric_transform(fromim[:,:,col],
                                        transf,(toim.shape[0],toim.shape[1]+padding))
        else:
            # pad the destination image with zeros to the right
            toim_t = hstack((toim,zeros((toim.shape[0],padding))))
            fromim_t = ndimage.geometric_transform(fromim,transf,
                                    (toim.shape[0],toim.shape[1]+padding)) 
    else:
        print 'warp - left'
        # add translation to compensate for padding to the left
        H_delta = array([[1,0,0],[0,1,-delta],[0,0,1]])
        H = dot(H,H_delta)
        # transform fromim
        if is_color:
            # pad the destination image with zeros to the left
            toim_t = hstack((zeros((toim.shape[0],padding,3)),toim))
            fromim_t = zeros((toim.shape[0],toim.shape[1]+padding,toim.shape[2]))
            for col in range(3):
                fromim_t[:,:,col] = ndimage.geometric_transform(fromim[:,:,col],
                                            transf,(toim.shape[0],toim.shape[1]+padding))
        else:
            # pad the destination image with zeros to the left
            toim_t = hstack((zeros((toim.shape[0],padding)),toim))
            fromim_t = ndimage.geometric_transform(fromim,
                                    transf,(toim.shape[0],toim.shape[1]+padding))
    
    # blend and return (put fromim above toim)
    if is_color:
        # all non black pixels
        alpha = ((fromim_t[:,:,0] * fromim_t[:,:,1] * fromim_t[:,:,2] ) > 0)
        for col in range(3):
            toim_t[:,:,col] = fromim_t[:,:,col]*alpha + toim_t[:,:,col]*(1-alpha)
    else:
        alpha = (fromim_t > 0)
        toim_t = fromim_t*alpha + toim_t*(1-alpha)
    
    return toim_t


########NEW FILE########
