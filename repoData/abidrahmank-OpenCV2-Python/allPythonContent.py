__FILENAME__ = display_image
''' filename : display_image.py

Description : This sample demonstrates how to read an image, display it on the window and print image size.

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/introduction/display_image/display_image.html#display-image

Level : Beginner

Benefits : Learn to load image and display it in window

Usage : python display_image.py <image_file> 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import sys
import numpy as np

if len(sys.argv)!=2:                  ## Check for error in usage syntax
    print "Usage : python display_image.py <image_file>"

else:
    img = cv2.imread(sys.argv[1],cv2.CV_LOAD_IMAGE_COLOR)  ## Read image file

    if (img == None):                      ## Check for invalid input
        print "Could not open or find the image"
    else:
        cv2.namedWindow('Display Window')        ## create window for display
        cv2.imshow('Display Window',img)         ## Show image in the window
        print "size of image: ",img.shape        ## print size of image
        cv2.waitKey(0)                           ## Wait for keystroke
        cv2.destroyAllWindows()                  ## Destroy all windows

########NEW FILE########
__FILENAME__ = modify_image
''' file name : modify_image.py

Description : This sample shows how to convert a color image to grayscale and save it into disk

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/introduction/load_save_image/load_save_image.html

Level : Beginner

Benefits : Learn 1) to convert RGB image to grayscale, 2) save image to disk

Usage : python modify_image.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np
import sys

image = cv2.imread('lena.jpg') # change image name as you need or give sys.argv[1] to read from command line
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # convert image to gray

cv2.imwrite('gray_image.jpg',gray_image)   # saves gray image to disk

cv2.imshow('color_image',image)
cv2.imshow('gray_image',gray_image)

cv2.waitKey(0)
cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = add_images
''' file name : simple_linear_blender.py

Discription : This sample shows how to blend two images.

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/core/adding_images/adding_images.html#adding-images

Level : Beginner

Benefits : 1) Learns usage of cv2.addWeighted and 2) its numpy implementation

Usage : python simple_linear_blender.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

print ''' Simple Linear Blender
------------------------------------------

Enter value of alpha [0:1] :'''

alpha = float(input())                 # Ask the value of alpha

if 0<=alpha<=1:                        # Check if 0<= alpha <=1
    beta = 1.0 - alpha                 # Calculate beta = 1 - alpha
    gamma = 0.0                        # parameter gamma = 0

    img1 = cv2.imread('lena.jpg')
    img2 = cv2.imread('res.jpg')

    if img1==None:
        print "img1 not ready"
    elif img2==None:
        print "img2 not ready"
    else:
        dst = cv2.addWeighted(img1,alpha,img2,beta,gamma)  # Get weighted sum of img1 and img2
        #dst = np.uint8(alpha*(img1)+beta*(img2))    # This is simple numpy version of above line. But cv2 function is around 2x faster
        cv2.imshow('dst',dst)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
else:
    print "value of alpha should be 0 and 1"


########NEW FILE########
__FILENAME__ = BasicLinearTransforms
''' file name : BasicLinearTransforms.py

Description : This sample shows how apply an equation on an image, g(x) = alpha*i(x) + beta

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/core/basic_linear_transform/basic_linear_transform.html

Level : Beginner

Benefits : Learn use of basic matrix operations in OpenCV and how they differ from corresponding numpy operations

Usage : python BasicLinearTransforms.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np


alpha = float(input('* Enter the alpha value [1.0-3.0]: '))     # Simple contrast control
beta = int(input('Enter the beta value [0-100]: '))             # Simple brightness control

print " Basic Linear Transforms "
print "-----------------------------"

img = cv2.imread('lena.jpg')

mul_img = cv2.multiply(img,np.array([alpha]))                    # mul_img = img*alpha
new_img = cv2.add(mul_img,np.array([beta]))                      # new_img = img*alpha + beta

cv2.imshow('original_image', img)
cv2.imshow('new_image',new_img)

cv2.waitKey(0)
cv2.destroyAllWindows()

## NB : Please visit for more details: http://opencvpython.blogspot.com/2012/06/difference-between-matrix-arithmetic-in.html 

########NEW FILE########
__FILENAME__ = fiter2d
''' file name : filter2d.py

Description : This sample shows how to filter/convolve an image with a kernel

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/core/mat-mask-operations/mat-mask-operations.html#the-filter2d-function

Level : Beginner

Benefits : Learn to convolve with cv2.filter2D function

Usage : python filter2d.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

img = cv2.imread('lena.jpg')

kernel = np.array([ [0,-1,0],
                    [-1,5,-1],
                    [0,-1,0] ],np.float32)   # kernel should be floating point type.

new_img = cv2.filter2D(img,-1,kernel)        # ddepth = -1, means destination image has depth same as input image.

cv2.imshow('img',img)
cv2.imshow('new',new_img)

cv2.waitKey(0)
cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = border
''' file name : border.py

Description : This sample shows how to add border to an image

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/imgtrans/copyMakeBorder/copyMakeBorder.html#copymakebordertutorial

Level : Beginner

Benefits : Learn to use cv2.copyMakeBorder()

Usage : python border.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

print " Press r to replicate the border with a random color "
print " Press c to replicate the border "
print " Press Esc to exit "

img = cv2.imread('home.jpg')
rows,cols = img.shape[:2]

dst = img.copy()

top = int (0.05*rows)
bottom = int (0.05*rows)

left = int (0.05*cols)
right = int (0.05*cols)

while(True):
    
    cv2.imshow('border',dst)
    k = cv2.waitKey(500)
    
    if k==27:
        break
    elif k == ord('c'):
        value = np.random.randint(0,255,(3,)).tolist()
        dst = cv2.copyMakeBorder(img,top,bottom,left,right,cv2.BORDER_CONSTANT,value = value)
    elif k == ord('r'):
        dst = cv2.copyMakeBorder(img,top,bottom,left,right,cv2.BORDER_REPLICATE)

cv2.destroyAllWindows()    

########NEW FILE########
__FILENAME__ = boundingrect
''' file name : boundingrect.py

Description : This sample shows how to find the bounding rectangle and minimum enclosing circle of a contour

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/shapedescriptors/bounding_rects_circles/bounding_rects_circles.html
Level : Beginner

Benefits : Learn to use 1) cv2.boundingRect() and 2) cv2.minEnclosingCircle()

Usage : python boundingrect.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials'''

import cv2
import numpy as np

def thresh_callback(thresh):
    edges = cv2.Canny(blur,thresh,thresh*2)
    drawing = np.zeros(img.shape,np.uint8)     # Image to draw the contours
    contours,hierarchy = cv2.findContours(edges,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        bx,by,bw,bh = cv2.boundingRect(cnt)
        (cx,cy),radius = cv2.minEnclosingCircle(cnt)
        cv2.drawContours(drawing,[cnt],0,(0,255,0),1)   # draw contours in green color
        cv2.circle(drawing,(int(cx),int(cy)),int(radius),(0,0,255),2)   # draw circle in red color
        cv2.rectangle(drawing,(bx,by),(bx+bw,by+bh),(255,0,0),3) # draw rectangle in blue color)
        cv2.imshow('output',drawing)
        cv2.imshow('input',img)

img = cv2.imread('messi5.jpg')
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray,(5,5),0)

cv2.namedWindow('input')

thresh = 100
max_thresh = 255

cv2.createTrackbar('canny thresh:','input',thresh,max_thresh,thresh_callback)

thresh_callback(0)

if cv2.waitKey(0) == 27:
    cv2.destroyAllWindows()

### For more details & feature extraction on contours, visit : http://opencvpython.blogspot.com/2012/04/contour-features.html

########NEW FILE########
__FILENAME__ = canny
''' file name : canny.py

Description : This sample shows how to find edges using canny edge detection

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/imgtrans/canny_detector/canny_detector.html

Level : Beginner

Benefits : Learn to apply canny edge detection to images.

Usage : python canny.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''


import cv2
import numpy as np

def CannyThreshold(lowThreshold):
    detected_edges = cv2.GaussianBlur(gray,(3,3),0)
    detected_edges = cv2.Canny(detected_edges,lowThreshold,lowThreshold*ratio,apertureSize = kernel_size)
    dst = cv2.bitwise_and(img,img,mask = detected_edges)  # just add some colours to edges from original image.
    cv2.imshow('canny demo',dst)

lowThreshold = 0
max_lowThreshold = 100
ratio = 3
kernel_size = 3

img = cv2.imread('messi5.jpg')
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

cv2.namedWindow('canny demo')

cv2.createTrackbar('Min threshold','canny demo',lowThreshold, max_lowThreshold, CannyThreshold)

CannyThreshold(0)  # initialization
if cv2.waitKey(0) == 27:
    cv2.destroyAllWindows()

# visit for output results : http://opencvpython.blogspot.com/2012/06/image-derivatives-sobel-and-scharr.html

########NEW FILE########
__FILENAME__ = comparehist
''' file name : comparehist.py

Description : This sample shows how to determine how well two histograms match each other.

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/histograms/histogram_comparison/histogram_comparison.html

Level : Beginner

Benefits : Learn to use cv2.compareHist and create 2D histograms

Usage : python comparehist.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

base = cv2.imread('base.png')
test1 = cv2.imread('test1.jpg')
test2 = cv2.imread('test2.jpg')

rows,cols = base.shape[:2]

basehsv = cv2.cvtColor(base,cv2.COLOR_BGR2HSV)
test1hsv = cv2.cvtColor(test1,cv2.COLOR_BGR2HSV)
test2hsv = cv2.cvtColor(test2,cv2.COLOR_BGR2HSV)

halfhsv = basehsv[rows/2:rows-1,cols/2:cols-1].copy()  # Take lower half of the base image for testing

hbins = 180
sbins = 255
hrange = [0,180]
srange = [0,256]
ranges = hrange+srange                                  # ranges = [0,180,0,256]


histbase = cv2.calcHist(basehsv,[0,1],None,[180,256],ranges)
cv2.normalize(histbase,histbase,0,255,cv2.NORM_MINMAX)

histhalf = cv2.calcHist(halfhsv,[0,1],None,[180,256],ranges)
cv2.normalize(histhalf,histhalf,0,255,cv2.NORM_MINMAX)

histtest1 = cv2.calcHist(test1hsv,[0,1],None,[180,256],ranges)
cv2.normalize(histtest1,histtest1,0,255,cv2.NORM_MINMAX)

histtest2 = cv2.calcHist(test2hsv,[0,1],None,[180,256],ranges)
cv2.normalize(histtest2,histtest2,0,255,cv2.NORM_MINMAX)

for i in xrange(4):
    base_base = cv2.compareHist(histbase,histbase,i)
    base_half = cv2.compareHist(histbase,histhalf,i)
    base_test1 = cv2.compareHist(histbase,histtest1,i)
    base_test2 = cv2.compareHist(histbase,histtest2,i)
    print "Method: {0} -- base-base: {1} , base-half: {2} , base-test1: {3}, base_test2: {4}".format(i,base_base,base_half,base_test1,base_test2)

    

########NEW FILE########
__FILENAME__ = convexhull
''' file name : convexhull.py

Description : This sample shows how to find the convex hull of contours

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/shapedescriptors/hull/hull.html

Level : Beginner

Benefits : Learn to use cv2.convexHull()

Usage : python convexhull.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials'''

import cv2
import numpy as np

def thresh_callback(thresh):
    edges = cv2.Canny(blur,thresh,thresh*2)
    drawing = np.zeros(img.shape,np.uint8)     # Image to draw the contours
    contours,hierarchy = cv2.findContours(edges,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        hull = cv2.convexHull(cnt)
        cv2.drawContours(drawing,[cnt],0,(0,255,0),2)   # draw contours in green color
        cv2.drawContours(drawing,[hull],0,(0,0,255),2)  # draw contours in red color
        cv2.imshow('output',drawing)
        cv2.imshow('input',img)

img = cv2.imread('messi5.jpg')
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray,(5,5),0)

cv2.namedWindow('input')

thresh = 100
max_thresh = 255

cv2.createTrackbar('canny thresh:','input',thresh,max_thresh,thresh_callback)

thresh_callback(0)

if cv2.waitKey(0) == 27:
    cv2.destroyAllWindows()

### For more details & feature extraction on contours, visit : http://opencvpython.blogspot.com/2012/04/contour-features.html

########NEW FILE########
__FILENAME__ = equalizehist
''' file name : equalizehist.py

Description : This sample shows how to equalize histogram

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/histograms/histogram_equalization/histogram_equalization.html

Level : Beginner

Benefits : Learn to use cv2.equalizeHist()

Usage : python equalizehist.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

img = cv2.imread('messi5.jpg')
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

equ = cv2.equalizeHist(gray)    # Remember histogram equalization works only for grayscale images

cv2.imshow('src',gray)
cv2.imshow('equ',equ)
cv2.waitKey(0)
cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = findcontours
''' file name : findcontours.py

Description : This sample shows how to find and draw contours

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/shapedescriptors/find_contours/find_contours.html#find-contours

Level : Beginner

Benefits : Learn to use 1) cv2.findContours() and 2)cv2.drawContours()

Usage : python findcontours.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials'''

import cv2
import numpy as np

def thresh_callback(thresh):
    edges = cv2.Canny(blur,thresh,thresh*2)
    drawing = np.zeros(img.shape,np.uint8)     # Image to draw the contours
    contours,hierarchy = cv2.findContours(edges,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        color = np.random.randint(0,255,(3)).tolist()  # Select a random color
        cv2.drawContours(drawing,[cnt],0,color,2)
        cv2.imshow('output',drawing)
    cv2.imshow('input',img)

img = cv2.imread('jonty2.jpg')
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray,(5,5),0)

cv2.namedWindow('input',cv2.WINDOW_AUTOSIZE)

thresh = 100
max_thresh = 255

cv2.createTrackbar('canny thresh:','input',thresh,max_thresh,thresh_callback)

thresh_callback(thresh)

if cv2.waitKey(0) == 27:
    cv2.destroyAllWindows()

### For more details & feature extraction on contours, visit : http://opencvpython.blogspot.com/2012/04/contour-features.html

########NEW FILE########
__FILENAME__ = geometric_transform
''' file name : geometric_transform.py

Description : This sample shows image transformation and rotation

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/imgtrans/warp_affine/warp_affine.html

Level : Beginner

Benefits : Learn 1) Affine transformation 2) Image Rotation

Usage : python 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

img = cv2.imread('messi5.jpg')
rows,cols = img.shape[:2]

# Source points
srcTri = np.array([(0,0),(cols-1,0),(0,rows-1)], np.float32)

# Corresponding Destination Points. Remember, both sets are of float32 type
dstTri = np.array([(cols*0.0,rows*0.33),(cols*0.85,rows*0.25), (cols*0.15,rows*0.7)],np.float32)

# Affine Transformation
warp_mat = cv2.getAffineTransform(srcTri,dstTri)   # Generating affine transform matrix of size 2x3
dst = cv2.warpAffine(img,warp_mat,(cols,rows))     # Now transform the image, notice dst_size=(cols,rows), not (rows,cols)

# Image Rotation
center = (cols/2,rows/2)                           # Center point about which image is transformed
angle = -50.0                                      # Angle, remember negative angle denotes clockwise rotation
scale = 0.6                                        # Isotropic scale factor.

rot_mat = cv2.getRotationMatrix2D(center,angle,scale) # Rotation matrix generated
dst_rot = cv2.warpAffine(dst,rot_mat,(cols,rows))     # Now transform the image wrt rotation matrix

cv2.imshow('dst_rt',dst_rot)
cv2.waitKey(0)
cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = histogram1d
''' file name : histogram1d.py

Description : This sample shows how to draw histogram for RGB color images

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/histograms/histogram_calculation/histogram_calculation.html

Level : Beginner

Benefits : Learn to use 1)cv2.calcHist(), 2)cv2.normalize and 3)cv2.polylines()

Usage : python histogram1d.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

img = cv2.imread('messi5.jpg')
h = np.zeros((300,256,3))                                    # image to draw histogram

bins = np.arange(256).reshape(256,1)                         # Number of bins, since 256 colors, we need 256 bins
color = [ (255,0,0),(0,255,0),(0,0,255) ]

for ch,col in enumerate(color):
    hist_item = cv2.calcHist([img],[ch],None,[256],[0,256])  # Calculates the histogram
    cv2.normalize(hist_item,hist_item,0,255,cv2.NORM_MINMAX) # Normalize the value to fall below 255, to fit in image 'h'
    hist=np.int32(np.around(hist_item))                      
    pts = np.column_stack((bins,hist))                       # stack bins and hist, ie [[0,h0],[1,h1]....,[255,h255]]
    cv2.polylines(h,[pts],False,col)

h=np.flipud(h)                                               # You will need to flip the image vertically

cv2.imshow('colorhist',h)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Here, there is no need of splitting the image to color planes,since calcHist will do it itself.
# For more details, visit : http://opencvpython.blogspot.com/2012/04/drawing-histogram-in-opencv-python.html

########NEW FILE########
__FILENAME__ = houghcircles
''' file name : houghcircles.py

Description : This sample shows how to detect circles in image with Hough Transform

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/imgtrans/hough_circle/hough_circle.html

Level : Beginner

Benefits : Learn to find circles in the image and draw them

Usage : python houghcircles.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np
import sys

if len(sys.argv)>1:
    filename = sys.argv[1]
else:
    filename = 'board.jpg'

img = cv2.imread(filename,0)
if img==None:
    print "cannot open ",filename

else:
    img = cv2.medianBlur(img,5)
    cimg = cv2.cvtColor(img,cv2.COLOR_GRAY2BGR)
    circles = cv2.HoughCircles(img,cv2.cv.CV_HOUGH_GRADIENT,1,10,param1=100,param2=30,minRadius=5,maxRadius=20)
    circles = np.uint16(np.around(circles))
    for i in circles[0,:]:
        cv2.circle(cimg,(i[0],i[1]),i[2],(0,255,0),1)  # draw the outer circle
        cv2.circle(cimg,(i[0],i[1]),2,(0,0,255),3)     # draw the center of the circle

    cv2.imshow('detected circles',cimg)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = houghlines
''' file name : houghlines.py

Description : This sample shows how to detect lines using Hough Transform

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/imgtrans/hough_lines/hough_lines.html

Level : Beginner

Benefits : Learn to find lines in an image and draw them

Usage : python houghlines.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

print " Hough Lines demo "
print " Press h to draw lines using cv2.HoughLines()"
print " Press p to draw lines using cv2.HoughLinesP()"
print " All the parameter values selected at random, Change it the way you like"

im = cv2.imread('building.jpg')
gray = cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray,150,200,apertureSize = 3)

cv2.imshow('houghlines',im)

while(True):
    img = im.copy()
    k = cv2.waitKey(0)

    if k == ord('h'):   # Press 'h' to enable cv2.HoughLines()
        lines = cv2.HoughLines(edges,1,np.pi/180,275)
        for rho,theta in lines[0]:
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a*rho
            y0 = b*rho
            x1 = int(x0 + 1000*(-b))   # Here i have used int() instead of rounding the decimal value, so 3.8 --> 3
            y1 = int(y0 + 1000*(a))    # But if you want to round the number, then use np.around() function, then 3.8 --> 4.0
            x2 = int(x0 - 1000*(-b))   # But we need integers, so use int() function after that, ie int(np.around(x))
            y2 = int(y0 - 1000*(a))
            cv2.line(img,(x1,y1),(x2,y2),(0,255,0),2)
        cv2.imshow('houghlines',img)

    elif k == ord('p'): # Press 'p' to enable cv2.HoughLinesP()
        lines = cv2.HoughLinesP(edges,1,np.pi/180,150, minLineLength = 100, maxLineGap = 10)
        for x1,y1,x2,y2 in lines[0]:
            cv2.line(img,(x1,y1),(x2,y2),(0,255,0),2)
        cv2.imshow('houghlines',img)

    elif k == 27:    # Press 'ESC' to exit
        break

cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = laplacian
''' file name : laplacian.py

Description : This sample shows how to find laplacian of an image

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/imgtrans/laplace_operator/laplace_operator.html

Level : Beginner

Benefits : Learn to find laplacian of an image

Usage : python laplacian.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

kernel_size = 3
scale = 1
delta = 0
ddepth = cv2.CV_16S

img = cv2.imread('messi5.jpg')
img = cv2.GaussianBlur(img,(3,3),0)
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

gray_lap = cv2.Laplacian(gray,ddepth,ksize = kernel_size,scale = scale,delta = delta)
dst = cv2.convertScaleAbs(gray_lap)

cv2.imshow('laplacian',dst)
cv2.waitKey(0)
cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = linear_filter
''' file name : linear_filter.py

Description : This sample shows how to create a linear filter and apply convolution

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/imgtrans/filter_2d/filter_2d.html#filter-2d

Level : Beginner

Benefits : Learn to 1) create a kernel and 2) apply convolution

Usage : python linear_filter.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

img = cv2.imread('home.jpg')

anchor = (-1,-1)
delta = 0
ddepth = -1

ind = 0

while(True):
    
    cv2.imshow('image',img)
    k = cv2.waitKey(500)

    if k==27:
        break

    kernel_size = 3 + 2*( ind%5 )   # trying for kernel sizes [3,5,7,9,11]
    kernel = np.ones((kernel_size,kernel_size),np.float32)/(kernel_size*kernel_size)

    cv2.filter2D(img,ddepth,kernel,img,anchor,delta,cv2.BORDER_DEFAULT)
    
    ind = ind+1

cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = minarearect
''' file name : minarearect.py

Description : This sample shows how to find minimum area rectangle and fit an ellipse to a contour

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/shapedescriptors/bounding_rotated_ellipses/bounding_rotated_ellipses.html

Level : Beginner

Benefits : Learn to use 1)cv2.minAreaRect() and 2) cv2.fitEllipse()

Usage : python minarearect.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials'''

import cv2
import numpy as np

def thresh_callback(thresh):
    global contours
    edges = cv2.Canny(blur,thresh,thresh*2)
    drawing = np.zeros(img.shape,np.uint8)      # Image to draw the contours
    contours,hierarchy = cv2.findContours(edges,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        rect = cv2.minAreaRect(cnt)             # rect = ((center_x,center_y),(width,height),angle)
        points = cv2.cv.BoxPoints(rect)         # Find four vertices of rectangle from above rect
        points = np.int0(np.around(points))     # Round the values and make it integers

        ellipse = cv2.fitEllipse(cnt)           # ellipse = ((center),(width,height of bounding rect), angle)
        
        cv2.drawContours(drawing,[cnt],0,(0,255,0),2)   # draw contours in green color
        cv2.ellipse(drawing,ellipse,(0,0,255),2)        # draw ellipse in red color
        cv2.polylines(drawing,[points],True,(255,0,0),2)# draw rectangle in blue color

        cv2.imshow('output',drawing)
        cv2.imshow('input',img)

img = cv2.imread('new.bmp')
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray,(5,5),0)

cv2.namedWindow('input')

thresh = 200
max_thresh = 255

cv2.createTrackbar('canny thresh:','input',thresh,max_thresh,thresh_callback)

thresh_callback(200)

if cv2.waitKey(0) == 27:
    cv2.destroyAllWindows()

### For more details & feature extraction on contours, visit : http://opencvpython.blogspot.com/2012/04/contour-features.html

########NEW FILE########
__FILENAME__ = moments
''' file name : moments.py

Description : This sample shows how to find area and centroid of a contour

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/shapedescriptors/moments/moments.html#moments

Level : Beginner

Benefits : Learn to use 1) cv2.moments and 2) cv.contourArea

Usage : python moments.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials'''

import cv2
import numpy as np

def thresh_callback(thresh):
    edges = cv2.Canny(blur,thresh,thresh*2)
    drawing = np.zeros(img.shape,np.uint8)                  # Image to draw the contours
    contours,hierarchy = cv2.findContours(edges,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        moments = cv2.moments(cnt)                          # Calculate moments
        if moments['m00']!=0:
            cx = int(moments['m10']/moments['m00'])         # cx = M10/M00
            cy = int(moments['m01']/moments['m00'])         # cy = M01/M00
            moment_area = moments['m00']                    # Contour area from moment
            contour_area = cv2.contourArea(cnt)             # Contour area using in_built function
            
            cv2.drawContours(drawing,[cnt],0,(0,255,0),1)   # draw contours in green color
            cv2.circle(drawing,(cx,cy),5,(0,0,255),-1)      # draw centroids in red color
    cv2.imshow('output',drawing)
    cv2.imshow('input',img)

img = cv2.imread('messi5.jpg')
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray,(5,5),0)

cv2.namedWindow('input')

thresh = 200
max_thresh = 255

cv2.createTrackbar('canny thresh:','input',thresh,max_thresh,thresh_callback)

thresh_callback(200)

if cv2.waitKey(0) == 27:
    cv2.destroyAllWindows()

### For more details & feature extraction on contours, visit : http://opencvpython.blogspot.com/2012/04/contour-features.html

########NEW FILE########
__FILENAME__ = morphology_1
''' file name : morphology_1.py

Description : This sample shows how to erode and dilate images

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/erosion_dilatation/erosion_dilatation.html#morphology-1

Level : Beginner

Benefits : Learn to 1) Erode, 2) Dilate and 3) Use trackbar

Usage : python morphology_1.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

global img

def erode(erosion_size):
    erosion_size = 2*erosion_size+1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(erosion_size,erosion_size))
    eroded = cv2.erode(img,kernel)
    cv2.imshow('erosion demo',eroded)

def dilate(dilation_size):
    dilation_size = 2*dilation_size+1
    kernel =  cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(dilation_size,dilation_size))
    dilated = cv2.dilate(img,kernel)
    cv2.imshow('dilation demo',dilated)


erosion_size = 0   # initial kernel size  = 1
dilation_size = 0

max_kernel_size = 21  # maximum kernel size = 43

img = cv2.imread('home.jpg')

cv2.namedWindow('erosion demo',cv2.CV_WINDOW_AUTOSIZE)
cv2.namedWindow('dilation demo',cv2.CV_WINDOW_AUTOSIZE)

# Creating trackbar for kernel size
cv2.createTrackbar('Size: 2n+1','erosion demo',erosion_size,max_kernel_size,erode)
cv2.createTrackbar('Size: 2n+1','dilation demo',dilation_size,max_kernel_size,dilate)

erode(0)
dilate(0)
if cv2.waitKey(0) == 27:
    cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = pointpolygontest
''' file name : pointpolygontest.py

Description : This sample shows how to find distance from a point to a contour

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/shapedescriptors/point_polygon_test/point_polygon_test.html

Level : Beginner

Benefits : Learn to use cv2.pointPolygonTest()

Usage : python pointpolygontest.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

r = 100

src = np.zeros((4*r,4*r),np.uint8)
rows,cols = src.shape

# draw an polygon on image src
points = [ [1.5*r,1.34*r], [r,2*r], [1.5*r,2.866*r], [2.5*r,2.866*r],[3*r,2*r],[2.5*r,1.34*r] ]
points = np.array(points,np.int0)
cv2.polylines(src,[points],True,255,3)

contours,hierarchy = cv2.findContours(src,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

res = np.zeros(src.shape,np.float32)                # array to store distances
drawing = np.zeros((rows,cols,3),np.uint8)          # image to draw the distance
cnt = contours[0]                                   # We take only one contour for testing

# Calculate distance from each point
for i in xrange(rows):
    for j in xrange(cols):
        res.itemset((i,j),cv2.pointPolygonTest(cnt,(j,i),True))


mini,maxi = np.abs(cv2.minMaxLoc(res)[:2])          # Find minimum and maximum to adjust colors
mini = 255.0/mini
maxi = 255.0/maxi

for i in xrange(rows):                              # Now we colorise as per distance
    for j in xrange(cols):
        if res.item((i,j))<0:
            drawing.itemset((i,j,0),255-int(abs(res.item(i,j))*mini))   # If outside, blue color
        elif res.item((i,j))>0:
            drawing.itemset((i,j,2),255-int(res.item(i,j)*maxi))        # If inside, red color
        else:
            drawing[i,j]=[255,255,255]                                  # If on the contour, white color.

cv2.imshow('point',drawing)
cv2.waitKey(0)
cv2.destroyAllWindows()

### For more details & feature extraction on contours, visit : http://opencvpython.blogspot.com/2012/04/contour-features.html
### For much more better and faster (50X) method, visit:http://opencvpython.blogspot.com/2012/06/fast-array-manipulation-in-numpy.html

########NEW FILE########
__FILENAME__ = pyramids
import cv2
import numpy as np

img = cv2.imread('home.jpg')

''' file name : pyramids.py

Description : This sample shows how to downsample and upsample images

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/pyramids/pyramids.html#pyramids

Level : Beginner

Benefits : Learn to use 1) cv2.pyrUp and 2) cv2.pyrDown

Usage : python pyramids.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''


print " Zoom In-Out demo "
print " Press u to zoom "
print " Press d to zoom "

img = cv2.imread('home.jpg')

while(1):
    h,w = img.shape[:2]
    
    cv2.imshow('image',img)
    k = cv2.waitKey(10)
    
    if k==27 :
        break

    elif k == ord('u'):  # Zoom in, make image double size
        img = cv2.pyrUp(img,dstsize = (2*w,2*h))

    elif k == ord('d'):  # Zoom down, make image half the size
        img = cv2.pyrDown(img,dstsize = (w/2,h/2))

cv2.destroyAllWindows()    

########NEW FILE########
__FILENAME__ = remap
''' file name : remap.py

Description : This sample shows how to remap images

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/imgtrans/remap/remap.html#remap

Level : Beginner

Benefits : Learn to use remap function

Usage : python remap.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

def update():
    global ind
    ind = ind%4
    for j in xrange(rows):
        for i in xrange(cols):
            if ind == 0:   # Resize and center the image
                if 0.25*cols< i <0.75*cols and 0.25*rows< j <0.75*rows:
                    map_x.itemset((j,i),2*( i - cols*0.25 ) + 0.5)
                    map_y.itemset((j,i),2*( j - rows*0.25 ) + 0.5)
                else:     # Other pixel values set to zero
                    map_x.itemset((j,i),0)
                    map_y.itemset((j,i),0)

            elif ind == 1: # Flip image in vertical direction, alternatively you can use np.flipud or cv2.flip
                map_x.itemset((j,i),i)
                map_y.itemset((j,i),rows-j)

            elif ind == 2: # Flip image in horizontal direction, you can use np.fliplr or cv2.flip
                map_x.itemset((j,i),cols-i)
                map_y.itemset((j,i),j)

            elif ind == 3: # Flip image in both the directions, you can use cv2.flip(flag = -1)
                map_x.itemset((j,i),cols-i)
                map_y.itemset((j,i),rows-j)
    ind = ind+1

img = cv2.imread('messi5.jpg')
ind = 0
map_x = np.zeros(img.shape[:2],np.float32)
map_y = np.zeros(img.shape[:2],np.float32)
rows,cols = img.shape[:2]
while(True):
    update()
    dst = cv2.remap(img,map_x,map_y,cv2.INTER_LINEAR)
    cv2.imshow('dst',dst)
    if cv2.waitKey(1000)==27:
        break
cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = smoothing
''' file name : smoothing.py

Description : This sample shows how to smooth image using various filters

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/gausian_median_blur_bilateral_filter/gausian_median_blur_bilateral_filter.html#smoothing

Level : Beginner

Benefits : Learn to use 1) Blur, 2) GaussianBlur, 3) MedianBlur, 4) BilateralFilter and differences between them

Usage : python smoothing.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

DELAY_CAPTION = 1500;
DELAY_BLUR = 500;

img = cv2.imread('lena.jpg')

for i in xrange(1,31,2):
    blur = cv2.blur(img,(i,i))
    string = 'blur : kernel size - '+str(i)
    cv2.putText(blur,string,(20,20),cv2.FONT_HERSHEY_COMPLEX_SMALL,1,(255,255,255))
    cv2.imshow('Blur',blur)
    cv2.waitKey(DELAY_BLUR)

for i in xrange(1,31,2):
    gaussian_blur = cv2.GaussianBlur(img,(i,i),0)
    string = 'guassian_blur : kernel size - '+str(i)
    cv2.putText(gaussian_blur,string,(20,20),cv2.FONT_HERSHEY_COMPLEX_SMALL,1,(255,255,255))
    cv2.imshow('Blur',gaussian_blur)
    cv2.waitKey(DELAY_BLUR)

cv2.waitKey(DELAY_CAPTION)

for i in xrange(1,31,2):
    median_blur = cv2.medianBlur(img,i)
    string = 'median_blur : kernel size - '+str(i)
    cv2.putText(median_blur,string,(20,20),cv2.FONT_HERSHEY_COMPLEX_SMALL,1,(255,255,255))
    cv2.imshow('Blur',median_blur)
    cv2.waitKey(DELAY_BLUR)

cv2.waitKey(DELAY_CAPTION)

for i in xrange(1,31,2):       # Remember, bilateral is a bit slow, so as value go higher, it takes long time 
    bilateral_blur = cv2.bilateralFilter(img,i, i*2,i/2)
    string = 'bilateral_blur : kernel size - '+str(i)
    cv2.putText(bilateral_blur,string,(20,20),cv2.FONT_HERSHEY_COMPLEX_SMALL,1,(255,255,255))
    cv2.imshow('Blur',bilateral_blur)
    cv2.waitKey(DELAY_BLUR)

cv2.waitKey(DELAY_CAPTION)
cv2.destroyAllWindows()

## For more info about this , visit: http://opencvpython.blogspot.com/2012/06/smoothing-techniques-in-opencv.html

########NEW FILE########
__FILENAME__ = sobel
''' file name : sobel.py

Description : This sample shows how to find derivatives of an image

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/imgtrans/sobel_derivatives/sobel_derivatives.html#sobel-derivatives

Level : Beginner

Benefits : Learn to use Sobel and Scharr derivatives

Usage : python sobel.py 

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

scale = 1
delta = 0
ddepth = cv2.CV_16S

img = cv2.imread('messi5.jpg')
img = cv2.GaussianBlur(img,(3,3),0)
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

# Gradient-X
grad_x = cv2.Sobel(gray,ddepth,1,0,ksize = 3, scale = scale, delta = delta,borderType = cv2.BORDER_DEFAULT)
#grad_x = cv2.Scharr(gray,ddepth,1,0)

# Gradient-Y
grad_y = cv2.Sobel(gray,ddepth,0,1,ksize = 3, scale = scale, delta = delta, borderType = cv2.BORDER_DEFAULT)
#grad_y = cv2.Scharr(gray,ddepth,0,1)

abs_grad_x = cv2.convertScaleAbs(grad_x)   # converting back to uint8
abs_grad_y = cv2.convertScaleAbs(grad_y)

dst = cv2.addWeighted(abs_grad_x,0.5,abs_grad_y,0.5,0)
#dst = cv2.add(abs_grad_x,abs_grad_y)

cv2.imshow('dst',dst)
cv2.waitKey(0)
cv2.destroyAllWindows()

# To see the results, visit : http://opencvpython.blogspot.com/2012/06/image-derivatives-sobel-and-scharr.html

########NEW FILE########
__FILENAME__ = templatematching
''' file name : templatematching.py

Description : This sample shows how to find location of a template image in original image

This is Python version of this tutorial : http://opencv.itseez.com/doc/tutorials/imgproc/histograms/template_matching/template_matching.html#template-matching

Level : Beginner

Benefits : Learn to use 1) cv2.matchTemplate and 2) cv2.minMaxLoc()

Usage : python templatematching.py

Written by : Abid K. (abidrahman2@gmail.com) , Visit opencvpython.blogspot.com for more tutorials '''

import cv2
import numpy as np

def match(matchvalue):
    img2 = img.copy()

    result = cv2.matchTemplate(img,template,matchvalue)

    cv2.normalize(result,result,0,255,cv2.NORM_MINMAX)

    mini,maxi,(mx,my),(Mx,My) = cv2.minMaxLoc(result)    # We find minimum and maximum value locations in result

    if matchvalue in [0,1]: # For SQDIFF and SQDIFF_NORMED, the best matches are lower values.
        MPx,MPy = mx,my
    else:                   # Other cases, best matches are higher values.
        MPx,MPy = Mx,My

    # Normed methods give better results, ie matchvalue = [1,3,5], others sometimes shows errors
    cv2.rectangle(img2, (MPx,MPy),(MPx+tcols,MPy+trows),(0,0,255),2)

    cv2.imshow('input',img2)
    cv2.imshow('output',result)

img = cv2.imread('messi4.jpg')
template = cv2.imread('template.jpg')

trows,tcols = template.shape[:2]    # template rows and cols

cv2.namedWindow('input')

matchvalue = 0
max_Trackbar = 5

cv2.createTrackbar('method','input',matchvalue,max_Trackbar,match)

match(0)

if cv2.waitKey(0) == 27:
    cv2.destroyAllWindows()

########NEW FILE########
__FILENAME__ = perfect
''' This module solves a sudoku, This is actually written by Peter Norvig
    Code and Explanation can be found here : norvig.com/sudoku.html'''

def cross(A, B):
    "Cross product of elements in A and elements in B."
    return [a+b for a in A for b in B]

digits   = '123456789'
rows     = 'ABCDEFGHI'
cols     = digits
squares  = cross(rows, cols)
unitlist = ([cross(rows, c) for c in cols] +
            [cross(r, cols) for r in rows] +
            [cross(rs, cs) for rs in ('ABC','DEF','GHI') for cs in ('123','456','789')])
units = dict((s, [u for u in unitlist if s in u]) for s in squares)
#print(units)
peers = dict((s, set(sum(units[s],[]))-set([s])) for s in squares)

def parse_grid(grid):
    """Convert grid to a dict of possible values, {square: digits}, or
    return False if a contradiction is detected."""
    ## To start, every square can be any digit; then assign values from the grid.
    values = dict((s, digits) for s in squares)
    for s,d in grid_values(grid).items():
        if d in digits and not assign(values, s, d):
            return False ## (Fail if we can't assign d to square s.)
    return values

def grid_values(grid):
    "Convert grid into a dict of {square: char} with '0' or '.' for empties."
    chars = [c for c in grid if c in digits or c in '0.']
    assert len(chars) == 81
    return dict(zip(squares, chars))

def assign(values, s, d):
    """Eliminate all the other values (except d) from values[s] and propagate.
    Return values, except return False if a contradiction is detected."""
    other_values = values[s].replace(d, '')
    if all(eliminate(values, s, d2) for d2 in other_values):
        return values
    else:
        return False

def eliminate(values, s, d):
    """Eliminate d from values[s]; propagate when values or places <= 2.
    Return values, except return False if a contradiction is detected."""
    if d not in values[s]:
        return values ## Already eliminated
    values[s] = values[s].replace(d,'')
    ## (1) If a square s is reduced to one value d2, then eliminate d2 from the peers.
    if len(values[s]) == 0:
        return False ## Contradiction: removed last value
    elif len(values[s]) == 1:
        d2 = values[s]
        if not all(eliminate(values, s2, d2) for s2 in peers[s]):
            return False
    ## (2) If a unit u is reduced to only one place for a value d, then put it there.
    for u in units[s]:
        dplaces = [s for s in u if d in values[s]]
        if len(dplaces) == 0:
            return False ## Contradiction: no place for this value
        elif len(dplaces) == 1:
            # d can only be in one place in unit; assign it there
                if not assign(values, dplaces[0], d):
                    return False
    return values

def display(values):
    "Display these values as a 2-D grid."
    width = 1+max(len(values[s]) for s in squares)
    line = '+'.join(['-'*(width*3)]*3)
    for r in rows:
        print (''.join(values[r+c].center(width)+('|' if c in '36' else '') for c in cols))
        if r in 'CF': print(line)
    print

def solve(grid): return search(parse_grid(grid))

def search(values):
    "Using depth-first search and propagation, try all possible values."
    if values is False:
        return False ## Failed earlier
    if all(len(values[s]) == 1 for s in squares): 
        return values ## Solved!
    ## Chose the unfilled square s with the fewest possibilities
    n,s = min((len(values[s]), s) for s in squares if len(values[s]) > 1)
    return some(search(assign(values.copy(), s, d)) 
        for d in values[s])

def some(seq):
    "Return some element of seq that is true."
    for e in seq:
        if e: return e
    return False

import time, random

def solve_all(grids, name='', showif=0.0):
    """Attempt to solve a sequence of grids. Report results.
    When showif is a number of seconds, display puzzles that take longer.
    When showif is None, don't display any puzzles."""
    def time_solve(grid):
        start = time.clock()
        values = solve(grid)
        t = time.clock()-start
        ## Display puzzles that take long enough
        if showif is not None and t > showif:
            display(grid_values(grid))
            if values: display(values)
            print ('(%.2f seconds)\n' % t)
        return (t, solved(values))
    times, results = zip(*[time_solve(grid) for grid in grids])
    N = len(grids)
    if N > 1:
        print ("Solved %d of %d %s puzzles (avg %.2f secs (%d Hz), max %.2f secs)." % (sum(results), N, name, sum(times)/N, N/sum(times), max(times)))

def solved(values):
    "A puzzle is solved if each unit is a permutation of the digits 1 to 9."
    def unitsolved(unit): return set(values[s] for s in unit) == set(digits)
    return values is not False and all(unitsolved(unit) for unit in unitlist)

def from_file(filename, sep='\n'):
    "Parse a file into a list of strings, separated by sep."
#    return file(filename).read().strip().split(sep)
    pass

def random_puzzle(N=17):
    """Make a random puzzle by making N assignments. Restart on contradictions.
    Note the resulting puzzle is not guaranteed to be solvable, but empirically
    about 99.8% of them are solvable."""
    values = dict((s, digits) for s in squares)
    for s in random.sample(squares, N):
        if not assign(values, s, random.choice(values[s])):
            return random_puzzle(N) ## Give up and make a new puzzle
    return ''.join(values[s] if len(values[s])==1 else '.' for s in squares)

def shuffled(seq):
    "Return a randomly shuffled copy of the input sequence."
    seq = list(seq)
    random.shuffle(seq)
    return seq

grid1  = '003020600900305001001806400008102900700000008006708200002609500800203009005010300'
grid2  = '4.....8.5.3..........7......2.....6.....8.4......1.......6.3.7.5..2.....1.4......'
hard1  = '.....6....59.....82....8....45........3........6..3.54...325..6..................'
grid3 =  '79......3.......6.8.1..4..2..5......3..1......4...62.92...3...6.3.6.5421.........'
extreme ='.26....1.75......2..86.1.9......3....9.4.8.2....1......1.5.92..6......57.3....98.'
#result = solved(grid_values(extreme))    
def solve_sudoku(s):
	k=solve(s)

	keys = k.keys()
	keys.sort()
	ans = ''.join(k[i] for i in keys)
	return ans


########NEW FILE########
__FILENAME__ = sudoku
''' This script takes a sudoku image as input, solves it and puts answer on image itself.

Usage : python sudoku.py <image_file> '''

import cv2
import numpy as np
import time,sys
from perfect import solve_sudoku

##############  Load OCR data for training #######################################
samples = np.float32(np.loadtxt('feature_vector_pixels.data'))
responses = np.float32(np.loadtxt('samples_pixels.data'))

model = cv2.KNearest()
model.train(samples, responses)

#############  Function to put vertices in clockwise order ######################
def rectify(h):
		''' this function put vertices of square we got, in clockwise order '''
		h = h.reshape((4,2))
		hnew = np.zeros((4,2),dtype = np.float32)

		add = h.sum(1)
		hnew[0] = h[np.argmin(add)]
		hnew[2] = h[np.argmax(add)]
		
		diff = np.diff(h,axis = 1)
		hnew[1] = h[np.argmin(diff)]
		hnew[3] = h[np.argmax(diff)]

		return hnew
		
################ Now starts main program ###########################

img =  cv2.imread('sudoku.jpg')
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

thresh = cv2.adaptiveThreshold(gray,255,1,1,5,2)
contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

image_area = gray.size	# this is area of the image

for i in contours:
	if cv2.contourArea(i)> image_area/2: # if area of box > half of image area, it is possibly the biggest blob
		peri = cv2.arcLength(i,True)
		approx = cv2.approxPolyDP(i,0.02*peri,True)
		#cv2.drawContours(img,[approx],0,(0,255,0),2,cv2.CV_AA)
		break

#################      Now we got sudoku boundaries, Transform it to perfect square ######################

h = np.array([ [0,0],[449,0],[449,449],[0,449] ],np.float32)	# this is corners of new square image taken in CW order

approx=rectify(approx)	# we put the corners of biggest square in CW order to match with h

retval = cv2.getPerspectiveTransform(approx,h)	# apply perspective transformation
warp = cv2.warpPerspective(img,retval,(450,450))  # Now we get perfect square with size 450x450

warpg = cv2.cvtColor(warp,cv2.COLOR_BGR2GRAY)	# kept a gray-scale copy of warp for further use

############ now take each element for inspection ##############

sudo = np.zeros((9,9),np.uint8)		# a 9x9 matrix to store our sudoku puzzle

smooth = cv2.GaussianBlur(warpg,(3,3),3)
thresh = cv2.adaptiveThreshold(smooth,255,0,1,5,2)
kernel = cv2.getStructuringElement(cv2.MORPH_CROSS,(3,3))
erode = cv2.erode(thresh,kernel,iterations =1)
dilate =cv2.dilate(erode,kernel,iterations =1)
contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

for cnt in contours:
	area = cv2.contourArea(cnt)
	if 100<area<800:
	
		(bx,by,bw,bh) = cv2.boundingRect(cnt)
		if (100<bw*bh<1200) and (10<bw<40) and (25<bh<45):
			roi = dilate[by:by+bh,bx:bx+bw]
			small_roi = cv2.resize(roi,(10,10))
			feature = small_roi.reshape((1,100)).astype(np.float32)
			ret,results,neigh,dist = model.find_nearest(feature,k=1)
			integer = int(results.ravel()[0])
			
			gridy,gridx = (bx+bw/2)/50,(by+bh/2)/50	# gridx and gridy are indices of row and column in sudo
			sudo.itemset((gridx,gridy),integer)
sudof= sudo.flatten()
strsudo = ''.join(str(n) for n in sudof)
ans = solve_sudoku(strsudo)		# ans is the solved sudoku we get as a string

#################### Uncomment below two lines if you want to print solved 9x9 matrix sudoku on terminal, optional ####################

#l = [int(i) for i in ans]		# we make string ans to a list 
#ansarray = np.array(l,np.uint8).reshape((9,9))  # Now we make it into an array of sudoku

############### Below print sudoku answer on our image.  #########################################

for i in xrange(81):
	if strsudo[i]=='0':
		r,c = i/9, i%9
		posx,posy = c*50+20,r*50+40
		cv2.putText(warp,ans[i],(posx,posy),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
		
cv2.imshow('img',warp)

cv2.waitKey(0)
cv2.destroyAllWindows()



########NEW FILE########
