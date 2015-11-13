__FILENAME__ = backend
"""
Provides a protected administrative area for uploading and deleteing images
"""

import os
import datetime

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images
from google.appengine.ext.webapp import template
from google.appengine.api import users

from models import Image

class Index(webapp.RequestHandler):
    """
    Main view for the application.
    Protected to logged in users only.
    """
    def get(self):
        "Responds to GET requets with the admin interface"
        # query the datastore for images owned by
        # the current user. You can't see anyone elses images
        # in the admin
        images = Image.all()
        images.filter("user =", users.get_current_user())
        images.order("-date")

        # we are enforcing loggins so we know we have a user
        user = users.get_current_user()
        # we need the logout url for the frontend
        logout = users.create_logout_url("/")

        # prepare the context for the template
        context = {
            "images": images,
            "logout": logout,
        }
        # calculate the template path
        path = os.path.join(os.path.dirname(__file__), 'templates',
            'index.html')
        # render the template with the provided context
        self.response.out.write(template.render(path, context))

class Deleter(webapp.RequestHandler):
    "Deals with deleting images"
    def post(self):
        "Delete a given image"
        # we get the user as you can only delete your own images
        user = users.get_current_user()
        key = self.request.get("key")
        if key:
            image = db.get(key)
            # check that we own this image
            if image.user == user:
                image.delete()
        # whatever happens rediect back to the main admin view
        self.redirect('/')
       
class Uploader(webapp.RequestHandler):
    "Deals with uploading new images to the datastore"
    def post(self):
        "Upload via a multitype POST message"
        
        img = self.request.get("img")

        # if we don't have image data we'll quit now
        if not img:
            self.redirect('/')
            return 
            
        # we have image data
        try:
            # check we have numerical width and height values
            width = int(self.request.get("width"))
            height = int(self.request.get("height"))
        except ValueError:
            # if we don't have valid width and height values
            # then just use the original image
            image_content = img
        else:
            # if we have valid width and height values
            # then resize according to those values
            image_content = images.resize(img, width, height)
        
        # get the image data from the form
        original_content = img
        # always generate a thumbnail for use on the admin page
        thumb_content = images.resize(img, 100, 100)
        
        # create the image object
        image = Image()
        # and set the properties to the relevant values
        image.image = db.Blob(image_content)
        # we always store the original here in case of errors
        # although it's currently not exposed via the frontend
        image.original = db.Blob(original_content)
        image.thumb = db.Blob(thumb_content)
        image.user = users.get_current_user()
                
        # store the image in the datasore
        image.put()
        # and redirect back to the admin page
        self.redirect('/')
                
# wire up the views
application = webapp.WSGIApplication([
    ('/', Index),
    ('/upload', Uploader),
    ('/delete', Deleter)
], debug=True)

def main():
    "Run the application"
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = frontend
"""
Frontend for the image host. This does the actual serving of the images
for use on others sites and within the admin
"""

import os
import datetime

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from models import Image
  
class GenericServer(webapp.RequestHandler):
    """
    Image server designed to handle serving png images from
    different object properties
    """
    property = 'image'
    def get(self):
        # key is provided in the query string
        img = self.request.get("id")
        try:
            # it might be an invalid key so we better check
            image = db.get(img)
        except db.BadKeyError:
            # if it is then return a 404
            self.error(404)
            return
            
        if image and image.image:
            # we have an image so prepare the response
            # with the relevant headers
            self.response.headers['Content-Type'] = "image/png"
            # and then write our the image data direct to the response
            self.response.out.write(eval("image.%s" % self.property))
        else:
            # we should probably return an image with the correct header
            # here instead of the default html 404
            self.error(404)

class ImageServer(GenericServer):
    "Serve the main image"
    property = 'image'

class ThumbServer(GenericServer):
    "Serve the thumbnail image"
    property = 'thumb'

class OriginalServer(GenericServer):
    "Serve the original uploaded image. Currently unused."
    property = 'original'

application = webapp.WSGIApplication([
    ('/i/img', ImageServer),
    ('/i/thumb', ThumbServer),
], debug=True)

def main():
    "Run the application"
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = models
from google.appengine.ext import db
from google.appengine.api.users import User

class Image(db.Model):
    "Represents an image stored in the datastore"
    # blog properties storing up to 1MB of binary data
    image = db.BlobProperty()
    thumb = db.BlobProperty()
    original = db.BlobProperty()
    # store the date just in case
    date = db.DateTimeProperty(auto_now_add=True)
    # all images are associated with the user who uploades them
    # this way we can make it a multi user system if that's useful
    user = db.UserProperty()
########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

"""
PyUnit Test runner suitable for use with Google App Engine.
Drop this file into your project directory, create a directory called
tests in the same directory and create a blank file in that called 
__init__.py. You directory structure should be something like this:

  - root
    - app.yaml
    - main.py
    - test.py
    - tests
      - __init__.py
    
You should now be able to just drop valid PyUnit test cases into the tests
directory and they should be run when you run test.py via the command line.
"""

import os
import unittest
import coverage
from optparse import OptionParser
     
def run_tests(verbosity):
    "Run test suite"

    # list all the files in the top level directory
    file_list = os.listdir(os.path.join(os.path.abspath(
        os.path.dirname(os.path.realpath(__file__)))))

    # list all the files in the tests directory
    test_list = os.listdir(os.path.join(os.path.abspath(
        os.path.dirname(os.path.realpath(__file__))), 'tests'))

    code_modules = []
    # loop over all the file names
    for file_name in file_list:
        extension = os.path.splitext(file_name)[-1]
        # if they are python files or the test runner
        if extension == '.py' and file_name != 'test.py':
            # work out the module name
            code_module_name = os.path.splitext(file_name)[0:-1][0]
            # now import the module
            module = __import__(code_module_name, globals(), locals(), 
                code_module_name)
            # and add it to the list of available modules
            code_modules.append(module)

    test_modules = []
    # loop over all the file names
    for file_name in test_list:
        extension = os.path.splitext(file_name)[-1]
        # if they are python files
        if extension == '.py':
            # work out the module name
            test_module_name = "tests." + os.path.splitext(file_name)[0:-1][0]
            # now import the module
            module = __import__(test_module_name, globals(), locals(), 
                test_module_name)
            # and add it to the list of available modules
            test_modules.append(module)
        
    # populate a test suite from the individual tests from the list of modules
    suite = unittest.TestSuite(map(
        unittest.defaultTestLoader.loadTestsFromModule, test_modules))

    # set up the test runner
    runner = unittest.TextTestRunner(verbosity=int(verbosity))
    
    # set up coverage reporting
    coverage.use_cache(0)
    coverage.start()
    
    # run the tests
    runner.run(suite)
    
    # stop coverage reporting
    coverage.stop()
    
    # output coverage report
    coverage.report(code_modules, show_missing=1)
    
if __name__ == '__main__':
    # instantiate the arguments parser
    PARSER = OptionParser()
    # add an option so we can set the test runner verbosity
    PARSER.add_option('--verbosity', 
                        action='store', 
                        dest='verbosity', 
                        default='1',
                        type='choice', 
                        choices=['0', '1', '2'],
                        help="""Verbosity level; 0=minimal output, 
                            1=normal output, 2=all output"""
                        ),
    # parse the command arguments
    (OPTIONS, ARGS) = PARSER.parse_args()
        
    # run the tests with the passed verbosity
    run_tests(OPTIONS.verbosity)
########NEW FILE########
__FILENAME__ = backend_tests
#!/usr/bin/env python

import os
import unittest
from webtest import TestApp, AppError

from google.appengine.api import apiproxy_stub_map, user_service_stub, datastore_file_stub

from backend import application

class BooksTest(unittest.TestCase):

    def setUp(self):
        self.app = TestApp(application)
        os.environ['APPLICATION_ID'] = "temp"
        os.environ['USER_EMAIL'] = "test@example.com"
        os.environ['SERVER_NAME'] = "localhost"
        os.environ['SERVER_PORT'] = "8080"
        
        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
        apiproxy_stub_map.apiproxy.RegisterStub('user', user_service_stub.UserServiceStub())
        stub = datastore_file_stub.DatastoreFileStub('temp', '/dev/null', '/dev/null')
        apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)
    
    def test_index_returns_200(self):
        response = self.app.get('/', expect_errors=True) 
        self.assertEquals("200 OK", response.status)

    def test_index_has_correct_title(self):
        response = self.app.get('/', expect_errors=True)        
        response.mustcontain("<title>App Engine Image Host</title>")
        
    def test_index_returns_correct_mime_type(self):
        response = self.app.get('/', expect_errors=True)
        self.assertEquals(response.content_type, "text/html")

    def test_image_upload(self):
        # post image binary
        # check retrieve record
        pass
        
    def test_delete_image(self):
        # post image binary
        # check presense of Image object
        # then post data to delete object
        # and check object presense
        pass
########NEW FILE########
__FILENAME__ = frontend_tests
#!/usr/bin/env python

import os
import unittest
from webtest import TestApp, AppError

from google.appengine.api import apiproxy_stub_map, user_service_stub, datastore_file_stub

from backend import application

class BooksTest(unittest.TestCase):

    def setUp(self):
        self.app = TestApp(application)
        os.environ['APPLICATION_ID'] = "temp"
        os.environ['USER_EMAIL'] = "test@example.com"
        os.environ['SERVER_NAME'] = "localhost"
        os.environ['SERVER_PORT'] = "8080"
        
        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
        apiproxy_stub_map.apiproxy.RegisterStub('user', user_service_stub.UserServiceStub())
        stub = datastore_file_stub.DatastoreFileStub('temp', '/dev/null', '/dev/null')
        apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)

    def test_thumbnail_renders(self):
        # post image binary
        # request url based on key
        # check image/png header
        # check status code
        pass
        
    def test_image_renders(self):
        # post image binary
        # request url based on key
        # check image/png header
        # check status code
        pass
########NEW FILE########
