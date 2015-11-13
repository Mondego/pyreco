__FILENAME__ = opencv
import os
import sys
import cv2
import numpy as np
import logging
import shutil
from peewee import *

MODEL_FILE = "model.mdl"

def detect(img, cascade):
  gray = to_grayscale(img)
  rects = cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=4, minSize=(30, 30), flags = cv2.CASCADE_SCALE_IMAGE)

  if len(rects) == 0:
    return []
  return rects

def detect_faces(img):
  cascade = cv2.CascadeClassifier("data/haarcascade_frontalface_alt.xml")
  return detect(img, cascade)

def to_grayscale(img):
  gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
  gray = cv2.equalizeHist(gray)
  return gray

def contains_face(img):
  return len(detect_faces(img)) > 0

def save(path, img):
  cv2.imwrite(path, img)

def crop_faces(img, faces):
  for face in faces:
    x, y, h, w = [result for result in face]
    return img[y:y+h,x:x+w]

def load_images(path):
  images, labels = [], []
  c = 0
  print "test " + path
  for dirname, dirnames, filenames in os.walk(path):
    print "test"
    for subdirname in dirnames:
      subjectPath = os.path.join(dirname, subdirname)
      for filename in os.listdir(subjectPath):
        try:
          img = cv2.imread(os.path.join(subjectPath, filename), cv2.IMREAD_GRAYSCALE)
          images.append(np.asarray(img, dtype=np.uint8))
          labels.append(c)
        except IOError, (errno, strerror):
          print "IOError({0}): {1}".format(errno, strerror)
        except:
          print "Unexpected error:" , sys.exc_info()[0]
          raise
      c += 1
    return images, labels

def load_images_to_db(path):
  for dirname, dirnames, filenames in os.walk(path):
    for subdirname in dirnames:
      subject_path = os.path.join(dirname, subdirname)
      label = Label.get_or_create(name=subdirname)
      label.save()
      for filename in os.listdir(subject_path):
        path = os.path.abspath(os.path.join(subject_path, filename))
        logging.info('saving path %s' % path)
        image = Image.get_or_create(path=path, label=label)
        image.save()

def load_images_from_db():
  images, labels = [],[]
  for label in Label.select():
    for image in label.image_set:
      try:
        cv_image = cv2.imread(image.path, cv2.IMREAD_GRAYSCALE)
        cv_image = cv2.resize(cv_image, (100,100))
        images.append(np.asarray(cv_image, dtype=np.uint8))
        labels.append(label.id)
      except IOError, (errno, strerror):
       print "IOError({0}): {1}".format(errno, strerror)
  return images, np.asarray(labels)

def train():
  images, labels = load_images_from_db()
  model = cv2.createFisherFaceRecognizer()
  #model = cv2.createEigenFaceRecognizer()
  model.train(images,labels)
  model.save(MODEL_FILE)

def predict(cv_image):
  faces = detect_faces(cv_image)
  result = None
  if len(faces) > 0:
    cropped = to_grayscale(crop_faces(cv_image, faces))
    resized = cv2.resize(cropped, (100,100))

    model = cv2.createFisherFaceRecognizer()
    #model = cv2.createEigenFaceRecognizer()
    model.load(MODEL_FILE)
    prediction = model.predict(resized)
    result = {
      'face': {
        'name': Label.get(Label.id == prediction[0]).name,
        'distance': prediction[1],
        'coords': {
          'x': str(faces[0][0]),
          'y': str(faces[0][1]),
          'width': str(faces[0][2]),
          'height': str(faces[0][3])
          }
       }
    }
  return result

db = SqliteDatabase("data/images.db")
class BaseModel(Model):
  class Meta:
    database = db

class Label(BaseModel):
  IMAGE_DIR = "data/images"

  name = CharField()

  def persist(self):
    path = os.path.join(self.IMAGE_DIR, self.name)
    #if directory exists with 10 images
    #delete it and recreate
    if os.path.exists(path) and len(os.listdir(path)) >= 10:
      shutil.rmtree(path)

    if not os.path.exists(path):
      logging.info("Created directory: %s" % self.name)
      os.makedirs(path)

    Label.get_or_create(name=self.name)

class Image(BaseModel):
  IMAGE_DIR = "data/images"
  path = CharField()
  label = ForeignKeyField(Label)

  def persist(self, cv_image):
    path = os.path.join(self.IMAGE_DIR, self.label.name)
    nr_of_images = len(os.listdir(path))
    if nr_of_images >= 10:
      return 'Done'
    faces = detect_faces(cv_image)
    if len(faces) > 0 and nr_of_images < 10:
      path += "/%s.jpg" % nr_of_images
      path = os.path.abspath(path)
      logging.info("Saving %s" % path)
      cropped = to_grayscale(crop_faces(cv_image, faces))
      cv2.imwrite(path, cropped)
      self.path = path
      self.save()


if __name__ == "__main__":
  load_images_to_db("data/images")
  #train()

  print 'done'
  #predict()
  #train()

########NEW FILE########
__FILENAME__ = server
import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid
from PIL import Image
import time
import StringIO
import uuid
import numpy
import json
from tornado.options import define, options
import opencv

define("port", default=8888, help="run on the given poort", type=int)

class Application(tornado.web.Application):
  def __init__(self):
    handlers = [
        #(r"/", MainHandler),
        #(r"/facedetector", FaceDetectHandler),
        (r"/", SetupHarvestHandler),
        (r"/harvesting", HarvestHandler),
        (r"/predict", PredictHandler),
        (r"/train", TrainHandler)
        ]

    settings = dict(
        cookie_secret="asdsafl.rleknknfkjqweonrkbknoijsdfckjnk 234jn",
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        xsrf_cookies=False,
        autoescape=None,
        debug=True
        )
    tornado.web.Application.__init__(self, handlers, **settings)

class MainHandler(tornado.web.RequestHandler):
  def get(self):
    self.render("facedetect.html")

class SocketHandler(tornado.websocket.WebSocketHandler):

  def open(self):
    logging.info('new connection')

  def on_message(self, message):
    image = Image.open(StringIO.StringIO(message))
    cv_image = numpy.array(image)
    self.process(cv_image)

  def on_close(self):
    logging.info('connection closed')

  def process(self, cv_image):
    pass

class FaceDetectHandler(SocketHandler):

  def process(self, cv_image):
    faces = opencv.detect_faces(cv_image)
    if len(faces) > 0:
      result = json.dumps(faces.tolist())
      self.write_message(result)

class SetupHarvestHandler(tornado.web.RequestHandler):
  def get(self):
    self.render("harvest.html")

  def post(self):
    name = self.get_argument("label", None)
    if not name:
      logging.error("No label, bailing out")
      return
    logging.info("Got label %s" %  name)
    opencv.Label.get_or_create(name=name).persist()
    logging.info("Setting secure cookie %s" % name)
    self.set_secure_cookie('label', name)
    self.redirect("/")

class HarvestHandler(SocketHandler):
  def process(self, cv_image):
    label = opencv.Label.get(opencv.Label.name == self.get_secure_cookie('label'))
    logging.info("Got label: %s" % label.name)
    if not label:
      logging.info("No cookie, bailing out")
      return
    logging.info("About to save image")
    result = opencv.Image(label=label).persist(cv_image)
    if result == 'Done':
      self.write_message(json.dumps(result))

class TrainHandler(tornado.web.RequestHandler):
  def post(self):
    opencv.train()

class PredictHandler(SocketHandler):
  def process(self, cv_image):
    result = opencv.predict(cv_image)
    if result: 
      self.write_message(json.dumps(result))

def main():
  tornado.options.parse_command_line()
  opencv.Image().delete()
  logging.info("Images deleted")
  opencv.Label().delete()
  logging.info("Labels deleted")
  opencv.load_images_to_db("data/images")
  logging.info("Labels and images loaded")
  opencv.train()
  logging.info("Model trained")
  app = Application()
  app.listen(options.port)
  tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
  main()

########NEW FILE########
__FILENAME__ = validation
# from http://bytefish.de/blog/validating_algorithms

import os
import sys
import cv2
import numpy as np

from sklearn.base import BaseEstimator
from sklearn import cross_validation as cval
from sklearn.metrics import precision_score
import opencv

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
      subjectPath = os.path.join(dirname, subdirname)
      for filename in os.listdir(subjectPath):
        try:
          img = cv2.imread(os.path.join(subjectPath, filename), cv2.IMREAD_GRAYSCALE)
          if sz is not None:
            img = cv2.resize(img, sz)
          X.append(np.asarray(img, dtype=np.uint8))
          y.append(c)
        except IOError, (errno, strerror):
          print "IOError({0}): {1}".format(errno, strerror)
        except:
          print "Unexpected error:" , sys.exc_info()[0]
          raise
      c += 1
  return [X,y]


class FaceRecognizer(BaseEstimator):
  def __init__(self):
    #self.model = model
    #self.model = cv2.createFisherFaceRecognizer()
    self.model = cv2.createEigenFaceRecognizer()

  def fit(self, X, y):
    self.model.train(X, y)

  def predict(self, T):
    return [self.model.predict(T[i]) for i in range(0, T.shape[0])]

if __name__ == "__main__":
  #[X, y] = read_images(sys.argv[1], (100,100))

  [X, y] = opencv.load_images_from_db()
  y = np.asarray(y, dtype=np.int32)
  cv = cval.StratifiedKFold(y, 10)

  estimator = FaceRecognizer()

  precision_scores = cval.cross_val_score(estimator, X, y, score_func=precision_score, cv=cv)
  print precision_scores
  print sum(precision_scores)/len(precision_scores)



########NEW FILE########
