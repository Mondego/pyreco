__FILENAME__ = multipart
#!/usr/bin/python

####
# 02/2006 Will Holcomb <wholcomb@gmail.com>
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# 7/26/07 Slightly modified by Brian Schneider  
# in order to support unicode files ( multipart_encode function )
"""
Usage:
  Enables the use of multipart/form-data for posting forms

Inspirations:
  Upload files in python:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/146306
  urllib2_file:
    Fabien Seisen: <fabien@seisen.org>

Example:
  import MultipartPostHandler, urllib2, cookielib

  cookies = cookielib.CookieJar()
  opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies),
                                MultipartPostHandler.MultipartPostHandler)
  params = { "username" : "bob", "password" : "riviera",
             "file" : open("filename", "rb") }
  opener.open("http://wwww.bobsite.com/upload/", params)

Further Example:
  The main function of this file is a sample which downloads a page and
  then uploads it to the W3C validator.
"""

import urllib
import urllib2
import mimetools, mimetypes
import os, stat
from cStringIO import StringIO

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

# Controls how sequences are uncoded. If true, elements may be given multiple values by
#  assigning a sequence.
doseq = 1

class MultipartPostHandler(urllib2.BaseHandler):
    handler_order = urllib2.HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.get_data()
        if data is not None and type(data) != str:
            v_files = []
            v_vars = []
            try:
                 for(key, value) in data.items():
                     if type(value) == file:
                         v_files.append((key, value))
                     else:
                         v_vars.append((key, value))
            except TypeError:
                systype, value, traceback = sys.exc_info()
                raise TypeError, "not a valid non-string sequence or mapping object", traceback

            if len(v_files) == 0:
                data = urllib.urlencode(v_vars, doseq)
            else:
                boundary, data = self.multipart_encode(v_vars, v_files)

                contenttype = 'multipart/form-data; boundary=%s' % boundary
                if(request.has_header('Content-Type')
                   and request.get_header('Content-Type').find('multipart/form-data') != 0):
                    print "Replacing %s with %s" % (request.get_header('content-type'), 'multipart/form-data')
                request.add_unredirected_header('Content-Type', contenttype)

            request.add_data(data)
        
        return request

    def multipart_encode(vars, files, boundary = None, buf = None):
        if boundary is None:
            boundary = mimetools.choose_boundary()
        if buf is None:
            buf = StringIO()
        for(key, value) in vars:
            buf.write('--%s\r\n' % boundary)
            buf.write('Content-Disposition: form-data; name="%s"' % key)
            buf.write('\r\n\r\n' + value + '\r\n')
        for(key, fd) in files:
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            filename = fd.name.split('/')[-1]
            contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            buf.write('--%s\r\n' % boundary)
            buf.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename))
            buf.write('Content-Type: %s\r\n' % contenttype)
            # buffer += 'Content-Length: %s\r\n' % file_size
            fd.seek(0)
            buf.write('\r\n' + fd.read() + '\r\n')
        buf.write('--' + boundary + '--\r\n\r\n')
        buf = buf.getvalue()
        return boundary, buf
    multipart_encode = Callable(multipart_encode)

    https_request = http_request

def main():
    import tempfile, sys

    validatorURL = "http://validator.w3.org/check"
    opener = urllib2.build_opener(MultipartPostHandler)

    def validateFile(url):
        temp = tempfile.mkstemp(suffix=".html")
        os.write(temp[0], opener.open(url).read())
        params = { "ss" : "0",            # show source
                   "doctype" : "Inline",
                   "uploaded_file" : open(temp[1], "rb") }
        print opener.open(validatorURL, params).read()
        os.remove(temp[1])

    if len(sys.argv[1:]) > 0:
        for arg in sys.argv[1:]:
            validateFile(arg)
    else:
        validateFile("http://www.google.com")

if __name__=="__main__":
    main()



########NEW FILE########
__FILENAME__ = upload_to_minus
#!/usr/env python

# upload_to_minus.py - Nautilus Extension for uploading image or 
# batch of images to http://min.us.
# Copyright (C) 2010  Dejan Noveski <dr.mote@gmail.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
    Check README.rst
"""

import gconf
import nautilus
import urllib, urllib2
import mimetools, mimetypes
import os, stat
from StringIO import StringIO
from exceptions import ImportError
import simplejson as json
from minus_utils import *

# Any other mimetypes i forgot?
SUPPORTED_FORMATS = ('image/jpeg', 
                    'image/png', 
                    'image/gif',
                    'image/bmp',)

# Min.us urls
MINUS_URL = "http://min.us/"
API_URL = MINUS_URL + "api/"
GALLERY_URL = API_URL + "CreateGallery"
UPLOAD_URL = API_URL + "UploadItem"

class MinusUploaderExtension(nautilus.MenuProvider):

    """
        Minus Uploader provider class - Adds an item in the contex menu in
        nautilus for image mimetypes. 
    """
    def __init__(self):
        self.gconf = gconf.client_get_default()

    def menu_activate(self, menu, files):
        """ Callback for menu item activate """
        return self.upload_gallery(files)

    def get_file_items(self, window, files):
        """ Shows the menu item """
        if len(files) == 0:
            return

        for f in files:
            if not f.get_mime_type() in SUPPORTED_FORMATS:
                return 
            if f.get_uri_scheme() != 'file':
                return

        item = nautilus.MenuItem('Nautilus::upload_to_min_us',
                                 'Upload to min.us',
                                 'Upload to min.us',
                                 'up')
        # connect to callback
        item.connect('activate', self.menu_activate, files)
        return item,

    def upload_gallery(self, files):
        """ Uploads selected images to imgur """
        # create a gallery - minus works like that
        gallery = self.create_gallery()
        if gallery:
            editor_id = gallery["editor_id"]
            reader_id = gallery["reader_id"]
            
            for f in files:
                # use the created gallery and add the images there
                self.upload_image(f.get_uri(), editor_id, reader_id)
        
            try:
                # Open the default browser and show the gallery
                import webbrowser
                webbrowser.open(MINUS_URL + "m" + editor_id)
            except ImportError, e:
                # No browser? Show the url in notification.
                notify(MINUS_URL + "m" + editor_id)

    def upload_image(self, image, editor_id, reader_id):

        try:
            image_path = path_from_uri(image) 
            params = {
                    "file": open(image_path, "rb")}
            notify("Uploading %s to min.us"%os.path.basename(image_path))
            urlopener = urllib2.build_opener(MultipartPostHandler)
            response = urlopener.open(
                    "%s?key=%s&editor_id=%s&filename=%s" % 
                    (UPLOAD_URL, "nautilus-uploader-"+editor_id, 
                        editor_id, os.path.basename(image_path),),
                    params)
        except URLError, e:
            notify(e.reason)

    def create_gallery(self):
        request = urllib2.Request(GALLERY_URL)
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError, e:
            notify(e.reason)
            return None
        
        return json.loads(response.read()) 


########NEW FILE########
__FILENAME__ = create_gallery
#/usr/bin/env python

import sys, subprocess, urllib, urllib2, os
from time import strftime
import json
import unicodedata

''' 
	REPLACE FOLLOWING WITH VALID EDITOR AND VIEWER URLS 
'''
MINUS_URL = 'http://min.us/'
# MINUS_URL = 'http://192.168.0.190:8001/'
READER_ID = "veTYOJ"
EDITOR_ID = "cXLjZ5CjJr5J"


def upload_file(filename, editor_id, key):
	basename = os.path.basename(filename)
	url ='%sapi/UploadItem?editor_id=%s&key=%s&filename=%s' % (MINUS_URL, editor_id, key, basename)
	file_arg = 'file=@%s' % filename
	p = subprocess.Popen(['curl', '-s', '-S', '-F', file_arg, url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output,error = p.communicate()
	if p.returncode == 0:
		dd = parseDict(output)
		print 'Uploaded %s (%s)' % (basename, dd['filesize'])
	else:
		print 'Failed %s : %s' % (basename, error)

def parseDict(dictStr):
	dictStr = dictStr.translate(None,'\"{}')
	items = [s for s in dictStr.split(', ') if s]
	dd = {}
	for item in items:
		key,value = item.split(': ')
		dd[key] = value

	return dd	

def create_gallery():
	f = urllib2.urlopen('%sapi/CreateGallery' % MINUS_URL)
	result = f.read()
	dd = parseDict(result)

	return (dd['editor_id'], "", dd['reader_id'])

def saveGallery(name, editor_id, items):
	name = "test"
	params = { "name" : name, "id" : editor_id, "key" : "OK", "items" : json.dumps(items) }
	params = urllib.urlencode(params)
	try:
		f = urllib2.urlopen('%sapi/SaveGallery' % MINUS_URL, params)
	except urllib2.HTTPError, e:
		print "\n", e.code
		print "SaveGallery Failed:\n", "params: ", params

def generateImageList(reader_id):

	formattedList = []
	f = urllib2.urlopen('%sapi/GetItems/m%s' % (MINUS_URL, reader_id))
	jsonData = json.loads( f.read())
	imagesList = jsonData[u'ITEMS_GALLERY']
	for image in imagesList:
		image = unicodedata.normalize('NFKD', image).encode('ascii','ignore')
		image = image[17:]
		image = image.split(".")[0]
		formattedList.append(image)
	return formattedList
		

def main():
	#editor_id,key,reader_id = create_gallery()
	#args = sys.argv[1:]
	#for arg in args:
	#	upload_file(arg,editor_id,key)
	imageList = generateImageList(READER_ID)	
	saveGallery("Testing rename - %s" % strftime("%Y-%m-%d %H:%M"), EDITOR_ID, imageList)
	print 'Editor URL: http://min.us/m%s' % EDITOR_ID 
	print 'Viewer URL: http://min.us/m%s' % READER_ID

if __name__ == '__main__':
	main()
########NEW FILE########
