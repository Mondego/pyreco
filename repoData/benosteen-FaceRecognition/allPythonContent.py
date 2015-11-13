__FILENAME__ = pygame_face
import pygame
import Image
from pygame.locals import *
import sys

from opencv import cv as opencv
# Magic class with a method for grabbing images
from opencv import highgui

from opencv import Ipl2PIL

camera = highgui.cvCreateCameraCapture(-1)
cascade = opencv.cvLoadHaarClassifierCascade('haarcascade_hand_fist.xml', opencv.cvSize(1,1))
eye_cascade = opencv.cvLoadHaarClassifierCascade('/usr/local/share/opencv/haarcascades/haarcascade_mcs_mouth.xml', opencv.cvSize(1,1))

def get_image():
    im = highgui.cvQueryFrame(camera)
    detect(im)
    #convert Ipl image to PIL image
    return Ipl2PIL(im)

def draw_bounding_boxes(cascade_list, img, r,g,b, width):
    if cascade_list:
        for rect in cascade_list:
            opencv.cvRectangle(img, opencv.cvPoint( int(rect.x), int(rect.y)),
                         opencv.cvPoint(int(rect.x + rect.width), int(rect.y + rect.height)),
                         opencv.CV_RGB(r,g,b), width)

def detect(image):
    image_size = opencv.cvGetSize(image)
 
    # create grayscale version
    grayscale = opencv.cvCreateImage(image_size, 8, 1)
    opencv.cvCvtColor(image, grayscale, opencv.CV_BGR2GRAY)
 
    # create storage
    storage = opencv.cvCreateMemStorage(0)
    opencv.cvClearMemStorage(storage)
 
    # equalize histogram
    opencv.cvEqualizeHist(grayscale, grayscale)
 
    # detect objects
    faces = opencv.cvHaarDetectObjects(grayscale, cascade, storage, 1.2, 2, opencv.CV_HAAR_DO_CANNY_PRUNING, opencv.cvSize(100, 100))
#    eyes = opencv.cvHaarDetectObjects(grayscale, eye_cascade, storage, 1.2, 2, opencv.CV_HAAR_DO_CANNY_PRUNING, opencv.cvSize(60,60))
    draw_bounding_boxes(faces, image, 127,255,0, 3)
 #   draw_bounding_boxes(eyes, image, 255,127,0, 1)
    

fps = 30.0
pygame.init()
window = pygame.display.set_mode((640,480))

pygame.display.set_caption("Face-recognition Demo")
screen = pygame.display.get_surface()

#demo image preparation
cv_im = highgui.cvLoadImage("demo.jpg")
detect(cv_im)
pil_im = Ipl2PIL(cv_im)

def read_demo_image():
    return pil_im

while True:
    # Fixed demo for when you have no Webcam
    #im = read_demo_image()
    
    # UNCOMMENT this and comment out the demo when you wish to use webcam
    im = get_image()
    
    pil_img = pygame.image.frombuffer(im.tostring(), im.size, im.mode)
    screen.blit(pil_img, (0,0))
    pygame.display.flip()
    pygame.time.delay(int(1000.0/fps))

########NEW FILE########
__FILENAME__ = recogniser
import opencv
from opencv import highgui

import PIL

import os

class CascadeNotFound(Exception):
  pass

class CouldntReadAsImagefile(Exception):
  pass

class ImageFileNotFound(Exception):
  pass

class Recogniser(object):
  def __init__(self, cascade_dir="/usr/local/share/opencv/haarcascades"):
    self._cached_cascades = {}
    self.cascade_dir = cascade_dir
    self.register_cascades()

  def register_cascades(self):
    self.cascades = []
    for cached_cascade in self._cached_cascades:
      del self._cached_cascades[cached_cascade]
    if os.path.isdir(self.cascade_dir):
      for file in [x for x in os.listdir(self.cascade_dir) if x.endswith(".xml")]:
        self.cascades.append(file)

  def get_cascade(self, cascade_name):
    self._cached_cascades[cascade_name] = opencv.cvLoadHaarClassifierCascade(
            os.path.join(self.cascade_dir, cascade_name), opencv.cvSize(1,1))
            #cascade_name, opencv.cvSize(1,1))
    return self._cached_cascades[cascade_name]


  def detect_in_image_file(self, filename, cascade_name, recogn_w = 50, recogn_h = 50, autosearchsize=False):
    if os.path.isfile(filename):
      try:
        pil_image = PIL.Image.open(filename)
      except:
        raise CouldntReadAsImagefile
      if autosearchsize:
        recogn_w, recogn_h = int(pil_image.size[0]/10.0), int(pil_image.size[1]/10.0)
      return self.detect(pil_image, cascade_name, recogn_w, recogn_h)
    else:
      raise ImageFileNotFound

  def detect(self, pil_image, cascade_name, recogn_w = 50, recogn_h = 50):
    # Get cascade:
    cascade = self.get_cascade(cascade_name)

    image = opencv.PIL2Ipl(pil_image) 
    image_size = opencv.cvGetSize(image)
    grayscale = image
    if pil_image.mode == "RGB": 
      # create grayscale version
      grayscale = opencv.cvCreateImage(image_size, 8, 1)
      # Change to RGB2Gray - I dont think itll affect the conversion
      opencv.cvCvtColor(image, grayscale, opencv.CV_BGR2GRAY)
 
    # create storage
    storage = opencv.cvCreateMemStorage(0)
    opencv.cvClearMemStorage(storage)
 
    # equalize histogram
    opencv.cvEqualizeHist(grayscale, grayscale)
 
    # detect objects
    return opencv.cvHaarDetectObjects(grayscale, cascade, storage, 1.2, 2, opencv.CV_HAAR_DO_CANNY_PRUNING, opencv.cvSize(recogn_w, recogn_h))


########NEW FILE########
__FILENAME__ = recogn_ui
import web

import sys

import simplejson

import mimetypes
mimetypes.init()

import os

from recogniser import Recogniser

import PIL

import Image, ImageDraw
from web.contrib.template import render_mako

from urllib import urlencode, unquote, quote

from datetime import datetime

import tempfile

urls = (
        '/', 'usage',
        )

app = web.application(urls, globals(), autoreload=True)



# input_encoding and output_encoding is important for unicode
# template file. Reference:
# http://www.makotemplates.org/docs/documentation.html#unicode
render = render_mako(
        directories=['templates'],
        input_encoding='utf-8',
        output_encoding='utf-8',
        )

class usage:
    def GET(self):
        r = Recogniser()
        web.header('Content-type','text/html; charset=utf-8', unique=True)
        return render.usage(r = r)
        
    def POST(self):
        r = Recogniser()
        x = web.input(part={})
        if x.has_key("cascade"):
            if x['cascade'] not in r.cascades:
                return web.notfound("Invalid cascade file selected")
        else:
            return web.notfound("You must supply a valid cascade file to use")
        if x.has_key("part"):
            path = x['part'].filename
            ext = path.split(".")[-1]
            tmp_fd, tmp_fname = tempfile.mkstemp(suffix="."+ext)
            tmpfile = os.fdopen(tmp_fd, "w+b")
            tmpfile.write(x['part'].file.read())
            x['part'].file.close()
            tmpfile.close()
            if True:
                objs = r.detect_in_image_file(tmp_fname, str(x['cascade']), autosearchsize=True)
                if x.has_key("json"):
                    web.header('Content-type','application/json', unique=True)
                    os.remove(tmp_fname)
                    data = []
                    for obj in objs:
                       print "%(x)s %(y)s %(w)s %(h)s" % ({'x':obj.x, 'y':obj.x, 'w':obj.width, 'h':obj.height})
                       data.append({'x':obj.x, 'y':obj.x, 'w':obj.width, 'h':obj.height})
                    return simplejson.dumps(data)
                else:
                    img = Image.open(tmp_fname)
                    drawing = ImageDraw.Draw(img)
                    for obj in objs:
                        print "%(x)s %(y)s %(w)s %(h)s" % ({'x':obj.x, 'y':obj.x, 'w':obj.width, 'h':obj.height})
                        drawing.rectangle([obj.x, obj.y, obj.x+obj.width, obj.y+obj.height], outline=128)
                    del drawing
                    fd_png, png_fname = tempfile.mkstemp(suffix=".png")
                    tmpfile = os.fdopen(fd_png, "w+b")
                    img.save(tmpfile, "PNG")
                    os.remove(tmp_fname)
                    tmpfile.seek(0)
                    web.header('Content-type','image/png', unique=True)
                    return tmpfile.read()

if __name__ == "__main__":
    app.run()

########NEW FILE########
