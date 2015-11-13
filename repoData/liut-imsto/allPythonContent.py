__FILENAME__ = handle

import os
from imsto import load_imsto, UrlError, guess_mimetype
from django.http import HttpResponse, HttpResponseNotFound, StreamingHttpResponse
from django.conf import settings

__all__ = ['ImageHandle', 'ManageHandle']

def ImageHandle(request, path):
	environ = request.META
	SECTION = get_section(request.META)

	imsto = load_imsto(SECTION)
	try:
		dst_file, dst_path = imsto.load(path)
	except UrlError, e:
		return HttpResponseNotFound(str(e))
	except Exception, e:
		raise e
	finally:
		imsto.close()

	THUMB_PATH = imsto.get_config('thumb_path').rstrip('/')
	mimetype = guess_mimetype(dst_path)
	server_soft = environ.get('SERVER_SOFTWARE','')
	if server_soft[:5] == 'nginx' and os.name != 'nt':
		print('path: {0}/{1}'.format(THUMB_PATH, dst_path))
		response = HttpResponse(content_type=mimetype)
		response['X-Accel-Redirect'] = '{0}/{1}'.format(THUMB_PATH, dst_path)
		return response

	fd = open(dst_file,'r')
	response = StreamingHttpResponse(fd, content_type=mimetype)
	response['Content-Length'] = os.path.getsize(dst_file)
	response['Via'] = 'imsto'
	return response
	#return environ['wsgi.file_wrapper'](fd, 4096)

def ManageHandle(request, path):
	#print request
	#print path
	# TODO:
	return HttpResponse('manage')

def get_section(environ):
	if hasattr(settings, 'IMSTO_SECTION'):
		return settings.IMSTO_SECTION
	elif environ.has_key('IMSTO_SECTION'):
		return environ.get('IMSTO_SECTION')
	else:
		return 'imsto'

########NEW FILE########
__FILENAME__ = storage
import os
import itertools
from django.core.files.storage import Storage
from django.conf import settings
from imsto import load_imsto
from urlparse import urljoin

MIN_PATH_LEN = 28

class ImageStorage(Storage):
	"""A custom storage backend to store files in GridFS

		to use this backend, change your settings.py:

			DEFAULT_FILE_STORAGE = 'imsto.django.ImageStorage'

	"""

	def __init__(self, base_url=None):

		if base_url is None:
			base_url = settings.MEDIA_URL
		self.base_url = base_url
		self.imsto = load_imsto()
		self.field = 'image_path'

	def delete(self, name):
		"""Deletes the specified file from the storage system.
		TODO:
		"""
		pass

	def exists(self, name):
		"""Returns True if a file referened by the given name already exists in the
		storage system, or False if the name is available for a new file.
		"""
		image = self.imsto.exists(filename=name)
		return bool(image.name)

	def listdir(self, path=None):
		"""Lists the contents of the specified path, returning a 2-tuple of lists;
		the first item being directories, the second item being files.
		"""
		return self.imsto.browse(limit=20,start=0)

	def size(self, name):
		"""Returns the total size, in bytes, of the file specified by name.
		"""
		img = self.imsto.get(filename=name)
		if img:
			return img.length
		else:
			raise ValueError("No such file or directory: '%s'" % name)

	def url(self, name, size='orig'):
		"""Returns an absolute URL where the file's contents can be accessed
		directly by a web browser.
		"""
		if len(name) > MIN_PATH_LEN and name[2] == name[5] == '/':
			return self.imsto.url(name, size)
		return urljoin(self.base_url, name).replace('\\', '/')

	def _open(self, name, mode='rb'):
		img = self.imsto.get(filename=name)
		if img:
			return img
		else:
			raise ValueError("No file found with the name '%s'." % name)

	def get_available_name(self, name):
		"""Returns a filename that's free on the target storage system, and
		available for new content to be written to.
		"""
		print 'src name: %s' % name
		return os.path.basename(name)


	def _save(self, name, content):
		print 'available name: %s' % name
		print 'type of content: %s' % type(content)
		if hasattr(content, 'temporary_file_path'):
			file = content.temporary_file_path()
			print 'temp file: %s' % file
		r, id, filename = self.imsto.store(content.file,name=name)

		if r:
			print 'stored {}, {}, {}'.format(r, id, filename)
			return filename

		print 'store failed, name: %s' % name
		return None
	

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from handle import ImageHandle, ManageHandle

urlpatterns = patterns('',
    url(r'^t/(.+)$', ImageHandle),
    url(r'^Manage/(.*)$', ManageHandle),
)

########NEW FILE########
__FILENAME__ = widgets
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe

class AdminImageWidget(AdminFileWidget):
    def render(self, name, value, attrs=None):
        output = []
        print 'value: {} type {}'.format(value, type(value))
        if value and getattr(value, "url", None):
            image_url = value.url
            file_name=str(value)
            output.append(u' <a href="%s" target="_blank"><img src="%s" alt="%s" /></a> %s ' % \
                (image_url, image_url, file_name, _('Change:')))
        output.append(super(AdminFileWidget, self).render(name, value, attrs))
        return mark_safe(u''.join(output))

########NEW FILE########
__FILENAME__ = handlers
# encoding: utf-8
"""
handlers.py

Created by liut on 2010-12-04.
Copyright (c) 2010-2013 liut. All rights reserved.
"""

import os,re
import json
from sys import exc_info
from traceback import format_tb
from imsto import *

__all__ = [
'ErrorWrap','AuthWrap',
'AuthAdminHandle','ImageHandler','AdminHandler'
]

def abuilding(self, environ, start_response):
	"""show abuilding"""
	start_response('200 OK', [('Content-type', 'text/plain')])
	return ['Abuilding']

def not_found(environ, start_response, message = 'Not Found'):
	"""Called if no URL matches."""
	start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
	return [message]

def redirect(environ, start_response, redirect_to, message = 'Found'):
	start_response('302 Found', [('Location', redirect_to)])
	return []

def print_env(environ, start_response):
	"""list environ items"""
	start_response('200 OK', [('Content-Type', 'text/plain')])
	return ['\n'.join(['%s: %r' % item for item in environ.items()])]

def get_path_info(environ):
	if environ.has_key('app.url_args'):
		path = ''.join(environ.get('app.url_args'))
	else:
		path = environ.get('PATH_INFO', '')

	#print 'path: %s (%s)' % (path, type(path))
	return path

class ErrorWrap(object):
	"""The middleware we use."""
	def __init__(self, app):
		self.app = app

	def __call__(self, environ, start_response):
		"""Call the application can catch exceptions."""
		appiter = None
		try:
			appiter = self.app(environ, start_response)
			for item in appiter:
				yield item
		except:
			traceback = get_traceback()
			try:
				start_response('500 INTERNAL SERVER ERROR', [
							   ('Content-Type', 'text/plain')])
			except:
				pass
			yield '\n'.join(traceback)

		if hasattr(appiter, 'close'):
			appiter.close()

def get_traceback():
	e_type, e_value, tb = exc_info()
	traceback = ['Traceback (most recent call last):']
	traceback += format_tb(tb)
	traceback.append('%s: %s' % (e_type.__name__, e_value))
	return traceback

class AuthWrap(object):

	def __init__(self, app):
		self.app = app
		self.section = 'imsto'
		self.config = Config()

	def __call__(self, environ, start_response):
		self.section = environ.get('IMSTO_SECTION', 'imsto')
		if not self.authorized(environ.get('HTTP_AUTHORIZATION')):
			return self.auth_required(environ, start_response)
		return self.app(environ, start_response)

	def authorized(self, auth_header):
		if not auth_header:
			# If they didn't give a header, they better login...
			return False
		# .split(None, 1) means split in two parts on whitespace:
		auth_type, encoded_info = auth_header.split(None, 1)
		#print '{}, {}'.format(auth_type, encoded_info)
		assert auth_type.lower() == 'basic'
		unencoded_info = encoded_info.decode('base64')
		username, password = unencoded_info.split(':', 1)
		return self.check_password(username, password)

	def check_password(self, username, password):
		# Not very high security authentication...
		admin_name = self.config.get('admin_name')
		admin_pass = self.config.get('admin_pass')
		#print 'input %s:%s' % (username, password)
		if username != admin_name:
			return False
		if admin_pass == '':
			print 'admin_pass is empty!'
			return True

		#hashed = password_hash(username, password)
		#print '{} admin_pass\n{} hashed'.format(admin_pass, hashed)
		return password_hash(username, password) == admin_pass

	def auth_required(self, environ, start_response):
		start_response('401 Authentication Required',
			[('Content-type', 'text/html'),
			 ('WWW-Authenticate', 'Basic realm="imsto"')])
		return ["""
		<html>
		 <head><title>Authentication Required</title></head>
		 <body>
		  <h1>Authentication Required</h1>
		  If you can't get in, then stay out.
		 </body>
		</html>"""]



def ImageHandler(environ, start_response):
	"""main image url handler"""
	SECTION = environ.get('IMSTO_SECTION', 'imsto')
	print 'section from env: {0}'.format(SECTION)
	imsto = load_imsto(SECTION)
	path = get_path_info(environ)
	#print 'path: %s' % path
	try:
		dst_file, dst_path = imsto.load(path)
	except HttpFound, e:
		return redirect(environ, start_response, e.path, e.message)
	except UrlError, e:
		return not_found(environ, start_response, e.message)
	except Exception, e:
		raise
	finally:
		imsto.close()

	print('dst_path: {}'.format(dst_path))
	#print('dst_file: {}'.format(dst_file))
	
	THUMB_PATH = imsto.get_config('thumb_path').rstrip('/')
	server_soft = environ.get('SERVER_SOFTWARE','')
	if server_soft[:5] == 'nginx' and os.name != 'nt':
		print('path: {0}/{1}'.format(THUMB_PATH, dst_path))
		start_response('200 OK', [('X-Accel-Redirect', '{0}/{1}'.format(THUMB_PATH, dst_path))])
		return []
	#print(file.type) 
	mimetype = guess_mimetype(dst_path)
	filesize = os.path.getsize(dst_file)
	headers = [('Content-Type', str(mimetype)), ('Content-Length', '{0}'.format(filesize)), ('Via','imsto')]
	#print(headers)
	start_response('200 OK', headers)
	fd = open(dst_file,'r')
	return environ['wsgi.file_wrapper'](fd, 4096)

def AdminHandler(environ, start_response):
	path = get_path_info(environ)
	
	man_regex = r'(env|Gallery|Stored|Sections)$'
	match = re.search(man_regex, path)
	#print('match: {0}'.format(match))
	if match is None:
		return not_found(environ, start_response)
	
	from cgi import FieldStorage
	form = FieldStorage(environ=environ)
	section = form.getfirst('roof', 'imsto')
	action, = match.groups()
	if (action == 'Gallery'):
		limit = 20
		start = 0
		if form.has_key("page") and form["page"].value != "":
			page = int(form["page"].value)
			if page < 1:
				page = 1
			start = limit * (page - 1)
		
		start_response('200 OK', [('Content-type', 'text/javascript')])
		
		imsto = load_imsto(section)
		gallery = imsto.browse(limit, start)
		import datetime
		dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else None
		if hasattr(imsto, 'close'):
			imsto.close()
		return [json.dumps(gallery, default=dthandler)]
	elif (action == 'Stored'):
		return StoredHandler(environ, start_response)
		#start_response('200 OK', [('Content-type', 'text/plain')])
		#return ['Stored']
	elif  (action == 'env'):
		return print_env(environ, start_response)
	elif action == 'Sections':
		start_response('200 OK', [('Content-type', 'text/javascript')])
		config = Config()
		return [json.dumps(config.sections())]
	
	start_response('200 OK', [('Content-type', 'text/plain')])
	return [path_info]


def StoredHandler(environ, start_response):
	from cgi import FieldStorage
	import cgitb; cgitb.enable(display=0, logdir="/tmp")
	form = FieldStorage(fp=environ['wsgi.input'], environ=environ)
	print(form.keys())

	start_response('200 Ok', [('Content-type', 'text/javascript')])

	if "oper" not in form:
		#print("Bad Request")
		return [json.dumps([False, 'Bad Request'])]

	method = environ['REQUEST_METHOD'].upper()
	if method == 'GET' or method == 'HEAD':
		return [json.dumps([False, 'bad request'])]
	oper = form['oper']
	print(oper)
	section = form.getfirst('roof', 'imsto')
	# section = form['section'] if form.has_key('section') else 'imsto'

	imsto = load_imsto(section)
	if oper.value == 'delete':
		id = form['id']
		r = imsto.delete(id.value)
		print r
		return [json.dumps(r)]
	if oper.value == 'add':

		if "new_file" not in form:
			return [json.dumps([False, 'please select a file'])]

		new_file = form['new_file']
		if new_file is None:
			return [json.dumps([False, 'invalid upload field'])]
		# print(type(new_file))
		result = []
		if type(new_file) == type([]):
			for f in new_file:
				print('%r %r %r %r %r %r' % (f.name, f.filename, f.type, f.disposition, f.file, f.length))
				r = imsto.store(f.file, ctype=f.type, name=f.filename)
				print 'store: %r, result %r' % (f.name, r)
				if type(r) == type([]):
					result.append(r)
				else:
					result.append(False)
		else:
			f = new_file
			print('single file %r %r' % (f.name, f.filename))
			try:
				result = imsto.store(f.file, ctype=f.type, name=f.filename)
				print 'store: %r, result %r' % (f.name, result)
			except Exception, e:
				result = [False, e.message]
				print "\n".join(get_traceback()) + "\n"
			
		if hasattr(imsto, 'close'):
			imsto.close()
		
		return [json.dumps(result)]
	else:
		return [json.dumps([False, 'invalid operation'])]


AuthAdminHandle = ErrorWrap(AuthWrap(AdminHandler))


# map urls to functions
default_urls = [
	(r't\d?/(.+)$', ImageHandler),
	(r'Manage/(.*)$', AuthWrap(AdminHandler))
]

def application(environ, start_response):
	"""
	The main WSGI application. Dispatch the current request to
	the functions from above and store the regular expression
	captures in the WSGI environment as  `app.url_args` so that
	the functions from above can access the url placeholders.

	If nothing matches call the `not_found` function.
	"""
	import re
	path = environ.get('PATH_INFO', '').strip('/')
	for regex, callback in default_urls:
		match = re.search(regex, path)
		if match is not None:
			environ['app.url_args'] = match.groups()
			return callback(environ, start_response)
	return not_found(environ, start_response)



if __name__ == '__main__':
	from wsgiref.simple_server import make_server
	httpd = make_server('', 8000, application)
	print("Listening on port 8000....\n image url example: http://localhost:8000/aj/3f/1ow9y7ks8w8s888kswkg8.jpg\n")
	httpd.serve_forever()

else:
	application = ErrorWrap(application)




########NEW FILE########
__FILENAME__ = image
# encoding: utf-8
"""
image.py

Created by liut on 2010-12-04.
Copyright (c) 2010-2013 liut. All rights reserved.
"""

__all__ = ['SimpImage', 'MIN_QUALITY']

import ctypes,collections
from _wand import (NewMagickWand,DestroyMagickWand,CloneMagickWand,ClearMagickWand,
MagickReadImageBlob,MagickReadImage,MagickWriteImage,MagickGetImageBlob,
MagickGetImageFormat,MagickSetImageFormat,MagickGetImageWidth,MagickGetImageHeight,
MagickGetImageCompressionQuality,MagickSetImageCompressionQuality,
MagickScaleImage,MagickRelinquishMemory,MagickStripImage,MagickThumbnailImage,MagickCropImage,MagickSetImagePage,
MagickSetImageArtifact,
BlendCompositeOp,DissolveCompositeOp,ModulateCompositeOp,
MagickCompositeImage,MagickLabelImage,
MagickSetImageGravity,CenterGravity,SouthGravity,
MagickGetException,MagickClearException,
)
import warnings

import os

# FORMAT_JPEG = 'JPEG'
# FORMAT_PNG = 'PNG'
# FORMAT_GIF = 'GIF'

MIN_QUALITY = 72

class SimpImage(object):
	_max_width, _max_height = 0, 0

	"""docstring for ClassName"""
	def __init__(self, file = None, image=None, blob=None):
		if isinstance(image, SimpImage):
			self._wand = CloneMagickWand(image.wand)
		elif blob is not None:
			if not isinstance(blob, collections.Iterable):
				raise TypeError( 'blob must be iterable, not {}'.format(repr(blob)) )
			if not isinstance(blob, basestring):
				blob = ''.join(blob)
			elif not isinstance(blob, str):
				blob = str(blob)
			self._wand = NewMagickWand()
			r = MagickReadImageBlob( self._wand, blob, len( blob ) )
			if not r:
				self.error()
		else:
			self._wand = NewMagickWand()
			self.read(file)

	def __del__(self):
		if self._wand:
			self._wand = DestroyMagickWand( self._wand )


	def __copy__( self ):
		return self.clone()

	def clone( self ):
		return type(self)(image=self)


	def _clear( self ):
		ClearMagickWand( self._wand )


	def read( self, file):
		self._clear()
		
		if isinstance(file, basestring):
			if os.access(file, os.R_OK):
				r = MagickReadImage( self._wand, file )
			else:
				#print 'image {} not found or access deny'.format(file)
				raise IOError('image {} not found or access deny'.format(file))
		elif hasattr( file, 'read' ):
			c = file.read()
			r = MagickReadImageBlob( self._wand, c, len( c ) )
		else:
			raise TypeError('file must be a readable file path or filelike object')

		if not r:
			self.error()


	@property
	def wand(self):
		return self._wand

	@property
	def format( self ):
		format = MagickGetImageFormat( self._wand )
		if format == '':
			return None
		else:
			return format

	@format.setter
	def format(self, value):
		'''The image format as a string, eg. "PNG".'''
		MagickSetImageFormat( self._wand, value )

	def max_height():
		doc = "The max_height property."
		def fget(self):
			return self._max_height
		def fset(self, value):
			self._max_height = value
		def fdel(self):
			del self._max_height
		return locals()
	max_height = property(**max_height())

	def max_width():
		doc = "The max_width property."
		def fget(self):
			#if self._max_width is None:
			#	self._max_width = 0
			return self._max_width
		def fset(self, value):
			self._max_width = value
		def fdel(self):
			del self._max_width
		return locals()
	max_width = property(**max_width())

	@property
	def quality(self):
		return MagickGetImageCompressionQuality( self._wand )

	@quality.setter
	def quality(self, value):
		MagickSetImageCompressionQuality( self._wand, int( round( value, 0 ) ) )

	@property
	def width(self):
		return MagickGetImageWidth( self._wand )

	@property
	def height(self):
		return MagickGetImageHeight( self._wand )

	def scale( self, size ):
		''' Scales the size of image to the given dimensions.
			size - A tuple containing the size of the scaled image.'''
		MagickScaleImage( self._wand, size[0], size[1] )

	def get_size( self ):
		return ( self.width, self.height )
	size = property( get_size, scale, None, 'A tuple containing the size of the image. Setting the size is the same as calling scale().' )

	@property
	def meta(self):
		return {'format': self.format, 'width': int(self.width), 'height': int(self.height), 'quality': int(self.quality)}

	def get_blob(self):
		size = ctypes.c_size_t()
		b = MagickGetImageBlob( self._wand, ctypes.byref(size) )
		if b and size.value:
			blob = ctypes.string_at(b, size.value)
			MagickRelinquishMemory(b)
			return blob
		self.error()

	def save( self, file = None ):
		''' Saves the image to a file.  If no file is specified, the file is
			saved with the original filename.'''
		if hasattr( file, 'write' ):
			return file.write( self.get_blob() )
		else:
			r = MagickWriteImage( self._wand, file )

			if not r:
				self.error()
			return r

	def thumbnail( self, columns, rows = None, fit = True, max_width = 0, max_height = 0 ):
		if rows is None: rows = columns
		print "thumbnail columns: {}, rows: {}, max_width: {}, max_height: {}".format(columns, rows, max_width, max_height)

		org_width, org_height = self.size

		if org_width <= columns and org_height <= rows:
			if MagickStripImage(self._wand):
				return True
			return False

		if fit:
			rel = float( org_width ) / float( org_height )
			if max_width > 0:
				columns = max_width
				rows = int( columns / rel )
			elif max_height > 0:
				rows = max_height
				columns = int( rows * rel )
			else:
				bounds = float( columns ) / float( rows )
				if rel >= bounds: rows = int( columns / rel )
				else: columns = int( rows * rel )
			print "fit columns: {}, rows: {}".format(columns, rows)
		if not MagickThumbnailImage( self._wand, columns, rows ):
			print('error: MagickThumbnailImage')

			self.error()
			
			return False
		return True


	def cropThumbnail( self, dst_width, dst_height = None ):
		if dst_height is None: dst_height = dst_width

		org_width, org_height = self.size

		if org_width <= dst_width and org_height <= dst_height:
			if MagickStripImage(self._wand):
				return True
			return False

		ratio_x = float( dst_width ) / float( org_width );
		ratio_y = float( dst_height ) / float( org_height );

		if ratio_x > ratio_y:
			new_width  = int(dst_width)
			new_height = int(ratio_x * float( org_height ))
		else:
			new_height = int(dst_height)
			new_width  = int(ratio_y * float( org_width ))
		
		if not MagickThumbnailImage(self._wand, new_width, new_height):
			print('error: MagickThumbnailImage')
			return False

		if new_width == dst_width and new_height == dst_height:
			return True

		crop_x = int((new_width - dst_width) / 2);
		crop_y = int((new_height - dst_height) / 2);

		print "crop_x: {0}, crop_y: {1}".format(crop_x, crop_y)

		if not MagickCropImage(self._wand, dst_width, dst_height, crop_x, crop_y):
			print('error: MagickCropImage')
			return False
		
		r = MagickSetImagePage(self._wand, dst_width, dst_height, 0, 0);

		if not r:
			self.error()
		
		return True

	def watermark(self, image, transparency=0.0, left=0, top=0, position=None, copyright=None):
		"""
		watermark methods:
		1. convert bgnd overlay   -compose modulate \
			-define compose:args={brigthness}[,{saturation}] \
			-composite  result
		2. convert bgnd overlay   -compose dissolve \
			-define compose:args={src_percent},{dst_percent} \
			-composite  result
		"""
		watermark_image = image.clone()
		s_width, s_height = self.size
		w_width, w_height = watermark_image.size

		if s_width < w_width or s_height < w_height:
			print 'source image is too small, must large than {} x {}'.format(w_width, w_height)
			return False

		if position == 'bottom-right':
			left = s_width - w_width - 10
			top = s_height - w_height - 10
		elif position == 'top-left':
			left = top = 10
		elif position == 'top-right':
			left = s_width - w_width - 10
			top = 10
		elif position == 'bottom-left':
			left = 10
			top = s_height - w_height - 10
		elif position == 'center':
			left = (s_width - w_width) / 2
			top = (s_height - w_height) / 2
		elif position == 'golden':
			#left = s_width * 0.382 - w_width / 2
			left = (s_width - w_width) / 2
			top = s_height * 0.618 - w_height / 2

		MagickSetImageArtifact(watermark_image.wand,"compose:args", "15%")
		#MagickSetImageArtifact(watermark_image.wand,"compose:args", "5")
		#MagickSetImageGravity(watermark_image.wand, SouthGravity)
		#op = DissolveCompositeOp
		#op = ModulateCompositeOp
		op = BlendCompositeOp
		r = MagickCompositeImage(self.wand, watermark_image.wand, op, int(left), int(top))
		del watermark_image

		if not r:
			self.error()

		if copyright and isinstance(copyright, SimpImage):
			ci = copyright.clone()
			MagickSetImageArtifact(ci.wand,"compose:args", "40%")
			MagickCompositeImage(self.wand, ci.wand, op, int(s_width * 0.382 - w_width / 2), int(s_height - w_height - s_height*.1))
			del ci

		return r


	def error(self, stacklevel=1):
		severity = ctypes.c_int()
		desc = MagickGetException(self.wand, ctypes.byref(severity))
		print severity
		print desc
		MagickClearException(self.wand)
		# TODO: process exception or warning
		#if isinstance(e, Warning):
		#	warnings.warn(e, stacklevel=stacklevel + 1)
		#elif isinstance(e, Exception):
		#	raise e

########NEW FILE########
__FILENAME__ = migrate
#!/usr/bin/env python
# encoding: utf-8
"""
tool.py

Created by liut on 2013-06-18.
Copyright (c) 2010-2013 liut. All rights reserved.
"""

import sys
import os
from numbers import Integral
from store import load_imsto, Config, encode_upload
# from _config import log


def test_section(section):
	config = Config()
	return config.has_section(section)

def migrate(from_section, to_section, skip=0, limit=50, end_count=0, id=None):
	"""merge and sync data between 2 storage engines"""
	if from_section == to_section:
		return False

	if not test_section(from_section) or not test_section(to_section):
		return False

	imsto1 = load_imsto(from_section)
	imsto2 = load_imsto(to_section)

	if id is not None:
		item = imsto1.get_meta(id)
		if item:
			print "start trans {},{},{}".format(item.id, item.filename, item.size)
			r = _store_item(imsto2, item)
			print 'trans ok: %s, %s' % (r, item.name)
		else:
			print 'item id %s not found' % id
		return

	total = imsto1.count()
	print 'total: {}'.format(total)

	p_count = 0
	offset = skip if isinstance(skip, Integral) and skip > 0 else 0
	while offset < total:
		print 'migrating page {}/{}'.format(offset, total)
		i = offset
		for item in imsto1.browse(limit, offset, only_items=True):
			print "start trans {:4d} {},{},{}".format(i, item.id, item.filename, item.size)
			r = _store_item(imsto2, item)
			print 'trans ok: %s, %s' % (r, item.name)
			i += 1
			p_count += 1
			if end_count > 0 and p_count >= end_count:
				print 'end count done'
				return
		offset += limit

	print 'all done!'

def _store_item(imsto2, item):
	# print 'item size: %s' % item.size
	return imsto2.store(item.file, ctype=item.mime, name=item.name, created=item.created, id=item.id)

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(usage='%(prog)s command')
	parser.add_argument('-F','--src',metavar='section',type=str)
	parser.add_argument('-T','--dst',metavar='section',type=str)
	parser.add_argument('--skip', type=int, default=0)
	parser.add_argument('--count', type=int, default=0)
	parser.add_argument('--id', type=str, default=None)
	args, remaining = parser.parse_known_args()

	#migrate('imsto', 'weed')
	if args.src and args.dst:
		migrate(args.src, args.dst, skip=args.skip, end_count=args.count, id=args.id)
	else:
		parser.print_help()

########NEW FILE########
__FILENAME__ = store
# encoding: utf-8
"""
store.py

imsto: core module

Created by liut on 2010-12-16.
Copyright (c) 2010-2013 liut. All rights reserved.
"""

import os,re,datetime
from urlparse import urljoin
from hashlib import md5
from numbers import Integral
from pymongo import ASCENDING, DESCENDING, MongoClient, MongoReplicaSetClient, ReadPreference
from _config import Config
from _base import base_convert
from _util import *

__all__ = [
	'load_imsto',
	'EngineError', 'UrlError', 'HttpFound', 'DuplicateError', 
]

def load_imsto(section='imsto'):
	config = Config()
	engine = config.get('engine', section)
	print 'loading {} engine: {}'.format(section, engine)
	if engine == 'mongodb':
		return StoreEngineGridFs(section)
	if engine == 's3':
		return StoreEngineS3(section)
	if engine == 'weedfs':
		return StoreEngineWeedFs(section)
	raise ValueError('bad engine_code')

class StoreBase:
	engine = None
	_db = None
	_fs = None
	_coll = None

	def __init__(self, section='imsto'):
		"""engine: mongodb(default), s3"""
		self.section = section
		self._config = Config()

		self.engine = self.get_config('engine')
		self.fs_prefix = self.get_config('fs_prefix')
		print 'init section: {self.section}, engine: {self.engine}, fs_prefix: {self.fs_prefix}'.format(self=self)

	def get_config(self, key):
		return self._config.get(key, self.section)
		
	def browse(self, limit=20, start=0, sort=None, only_items = False):
		"""retrieve files from mongodb for gallery"""
		#return fs().list()
		if sort is None or not isinstance(sort, list):
			sort = [('uploadDate',DESCENDING)]

		cursor = self.collection.find(limit=limit,skip=start,sort=sort)
		items = [StoreItem(self, item) for item in cursor]
		if only_items:
			return items
		url_prefix = urljoin(self.get_config('url_prefix'), self.get_config('thumb_path'))
		return {'items':items,'total':cursor.count(),'url_prefix': url_prefix + '/'}

	def count(self):
		return self.collection.count();

	# def __iter__(self):
	# 	self.__cursor = self.collection.find(limit=0,skip=0,sort=[('uploadDate',DESCENDING)])
	# 	return self
	# def next(self):
	# 	if self.__cursor:
	# 		return StoreItem(self, self.__cursor.next())
	# 	raise StopIteration

	def store(self, file=None, content=None, ctype=None, **kwd):
		"""save a file-like item"""
		if content is None and not hasattr(file, 'read'):
			raise TypeError('invalid file-like object')

		data = content if content is not None else file.read()
		size = len(data)
		ext = guessImageType(data[:32])
		if ext is None:
			raise ValueError('invalid image file')

		hashes = [md5(data).hexdigest()]
		_exists_id = self.exists(hashed=hashes[0])
		if _exists_id:
			id = _exists_id
			filename = _make_filename(id, ext)
			print ('id {} or hash {} exists!!'.format(id, hashes[0]))
			#raise DuplicateError('already exists')
			return [True, id, filename]
		ids = [_make_id(hashes[0])]
		if 'id' in kwd and kwd['id'] and kwd['id'] not in ids:
			ids += [kwd['id']]

		from image import SimpImage, MIN_QUALITY

		max_file_size = int(self.get_config('max_file_size'))
		max_jpeg_quality = int(self.get_config('max_jpeg_quality'))
		max_width = int(self.get_config('max_width'))
		max_height = int(self.get_config('max_height'))

		if size > max_file_size: max_jpeg_quality -= 1
		if max_jpeg_quality < MIN_QUALITY: max_jpeg_quality = MIN_QUALITY

		im = SimpImage(blob=data)
		meta = im.meta
		if meta['width'] > max_width or meta['height'] > max_height:
			if self.get_config('auto_scale') and im.thumbnail(max_width, max_height):
				if im.format == 'JPEG' and im.quality > max_jpeg_quality:
					im.quality = max_jpeg_quality
				data = im.get_blob()
				size = len(data)
				print im.meta
				print 'new scaled size {}'.format(size)
				hashes += [md5(data).hexdigest()]
			else:
				raise ValueError('file: {} dimension {}x{} is too big, max is {}x{}'.format(kwd['name'] if 'name' in kwd else '', meta['width'], meta['height'], max_width, max_height))

		if im.format == 'JPEG':
			if im.quality > max_jpeg_quality:
				print 'quality {} is too high, hash {}'.format(im.quality, hashes[0])
				from tempfile import NamedTemporaryFile
				_tmp = NamedTemporaryFile('w+b',dir=self.get_config('temp_root'),delete=False)
				_tmp.file.close()
				save_file(_tmp.name, blob=data)
				if jpegoptim(_tmp.name):
					fp = open(_tmp.name)
					data = fp.read()
					size = len(data)

					# print 'new optimized size {}'.format(size)
					fp.close()
					_tmp.unlink(_tmp.name)
					del im
					im = SimpImage(blob=data)
					meta = im.meta
					hashes += [md5(data).hexdigest()]
				else:
					raise EnvironmentError('jpeg qualty is too high, or need jpegoptim')
		elif im.format == 'PNG' and self.get_config('force_jpeg'):
			im.format = 'JPEG'
			im.quality = max_jpeg_quality
			data = im.get_blob()
			size = len(data)
			hashes += [md5(data).hexdigest()]
			ext = 'jpg'
			meta = im.meta
		del im

		if (size > max_file_size):
			raise ValueError('file: {} size {} is too big, max is {}'.format(kwd['name'] if 'name' in kwd else '', size, max_file_size))

		hashed = hashes[len(hashes)-1] #md5(data).hexdigest()
		# print ('md5 hash: {}'.format(hashed))

		# TODO: add for support (md5 + size) id
		id = _make_id(hashed)

		# print ('new filename: %r' % filename)

		# TODO: fix for support s3 front browse
		_exists_id = self.exists(id) or self.exists(hashed=hashed)
		if _exists_id:
			id = _exists_id
			filename = _make_filename(id, ext)
			print ('id {} or hash {} exists!!'.format(id, hashed))
			#raise DuplicateError('already exists')
			return [True, id, filename]
		filename = _make_filename(id, ext)
		# print ('id: {}'.format(id))

		# if ctype is None or ctype == '':
		from _util import guess_mimetype
		ctype = guess_mimetype(filename)

		# save to mongodb
		spec = {'_id': id,'filename': filename, 'hash': hashes, 'mime': ctype, 'size': size, 'meta': meta, 'ids': ids}

		if 'name' in kwd and isinstance(kwd['name'], (str, unicode)):
			spec['name'] = kwd['name']

		for k in ['created', 'app_id']:
			if k in kwd and kwd[k]:
				spec[k] = kwd[k]

		if self._store_exists(id, filename=filename):
			self._save_meta(id, spec)
			return [True, id, filename]

		rr = self._put(data, **spec)
		if rr:
			return [True, rr, filename]
	
	def get_meta(self, id=None, filename=None, ids=None):
		spec = None
		if id:
			spec = id
		elif filename:
			spec = {'filename': filename}
		elif ids and isinstance(ids, type([])):
			spec = {'ids': {'$in': ids}}

		if spec:
			print 'spec %s' % spec
			item = self.collection.find_one(spec)
			if item:
			 	return StoreItem(self, item)

	def _save_meta(self, id, spec):
		'''mongo special meta data'''
		#if not hasattr(spec, '_id'):
		#	spec['_id'] = id
		if 'created' not in spec:
			spec['created'] = datetime.datetime.utcnow()

		if 'filename' not in spec:
			print spec
			raise ValueError('need filename')

		return self.collection.update({'_id': id}, spec, upsert=True)

	def delete(self, id):
		raise NotImplemented()

	def _get(self, id):
		raise NotImplemented()

	def _put(self, data, **spec):
		raise NotImplemented()

	def _store_exists(self, id=None, *args, **kwargs):
		raise NotImplemented()

	def exists(self, id=None, hashed=None, filename=None, *args, **kwargs):
		"""check special hash value TODO: more args"""
		#print args
		#print kwargs
		if id and self.collection.find_one({"_id": id}):
			return id
		if hashed:
			doc = self.collection.find_one({'md5': hashed})
			if doc:
				return doc['_id']
			doc = self.collection.find_one({'hash': {'$in': [hashed]}})
			if doc:
				return doc['_id']

		if filename:
			doc = self.collection.find_one(filename=filename)
			if doc:
				return doc['_id']

		if self._store_exists(id, hashed=hashed, filename=filename, *args, **kwargs):
			return id

	@property
	def db(self):
		if self._db is None:
			self._db = get_mongo_db(self.get_config('servers'), self.get_config('db_name'), self.get_config('replica_set'))
		return self._db

	@property
	def collection(self):
		if self._coll is None:
			cn = '{0}.files'.format(self.fs_prefix)
			self._coll = self.db[cn]
		return self._coll

	def close(self):
		""" close db connection"""
		if self.db is not None:
			self.db.connection.disconnect()

	def load(self, path):
		""" load from url path """
		#print 'path: %s (%s)' % (path, type(path))
		image_url_regex = r'(?P<size>[scwh]\d{2,4}(?P<x>x\d{2,4})?|orig)(?P<mop>[a-z])?/(?P<t1>[a-z0-9]{2})/(?P<t2>[a-z0-9]{2})/(?P<t3>[a-z0-9]{19,36})\.(?P<ext>gif|jpg|jpeg|png)$'
		match = re.search(image_url_regex, path)
		#print(image_url_regex, path, match)
		if match is None:
			raise UrlError('invalid path')

		ids = match.groupdict()
		#print(ids)

		id = '{t1}{t2}{t3}'.format(**ids)

		THUMB_ROOT = self.get_config('thumb_root').rstrip('/')
		SUPPORTED_SIZE = self.get_config('support_size').split(',')

		org_path = '{t1}/{t2}/{t3}.{ext}'.format(**ids)
		org_file = '{0}/orig/{1}'.format(THUMB_ROOT, org_path)

		if not os.path.exists(org_file):

			# check old id for redirect
			doc = self.get_meta(ids=[id])
			if doc and doc['id'] != id and 'filename' in doc:
				print 'found %s' % doc['filename']
				thumb_path = self.get_config('thumb_path')
				new_path = '{}/{}/{}'.format(thumb_path, ids['size'], doc['filename'])
				raise HttpFound('found', path=new_path)

			print('fetching file: {}'.format(org_path))
			file = self.fetch(id, path=org_path)
			if file is None:
				print('fetch failed')
				raise UrlError('id {} not found'.format(id))
			save_file(org_file, file)

		if not os.path.exists(org_file):
			raise UrlError('file not found')

		# start thumbnail image

		if ids['size'] == 'orig':
			dst_path = 'orig/{}'.format(org_path)
			dst_file = org_file
		else:
			dst_path = '{0}/{1}'.format(ids['size'], org_path)
			dst_file = '{0}/{1}'.format(THUMB_ROOT, dst_path)

			mode = ids['size'][0]
			dimension = ids['size'][1:]
			if dimension not in SUPPORTED_SIZE:
				#print('unsupported size: {} {}'.format(mode, dimension))
				raise UrlError('unsupported size')
			if ids['x'] is None:
				size = int(dimension)
				width, height = size, size
			else:
				width, height = map(int, dimension.split('x'))

			if not os.path.exists(dst_file):
				print('start thumbnail image {} {} => {}x{}'.format(mode, dimension, width, height))
				thumb_image(org_file, width, height, dst_file, mode)

			if ids['mop'] == 'w' and width < 100:
				raise UrlError('bad size')

		if ids['mop'] is not None:
			if ids['mop'] == 'w': # watermark modifier
				org_file = '{}/{}/{}'.format(THUMB_ROOT, ids['size'], org_path)
				dst_file = '{}/{}{}/{}'.format(THUMB_ROOT, ids['size'], ids['mop'], org_path)

				if watermark_image(org_file, dst_file):
					dst_path = '{}{}/{}'.format(ids['size'], ids['mop'], org_path)

			else:
				raise UrlError('bad modifier')

		#print('dst_path: {}'.format(dst_path))
		#print('dst_file: {}'.format(dst_file))

		return (dst_file, dst_path)

	def fetch(self, id, path):
		key = path if self.engine == 's3' else id

		return self._get(key)
		# try:
		# 	return self._get(key)
		# except Exception, e:
		# 	print('prepare: {} not found'.format(key))
		# 	print e
		# 	raise e
		


	def url(self, path, size='orig'):
		url_prefix = self.get_config('url_prefix')
		thumb_path = self.get_config('thumb_path')
		return '{}/{}/{}/{}'.format(url_prefix.rstrip('/'), thumb_path.strip('/'), size, path)

class StoreItem(dict):
	"""docstring for Item"""
	imsto = None
	id = None
	def __init__(self, imsto, meta):
		self.imsto = imsto
		if isinstance(meta, dict):
			item = self._fix_meta(meta)
			for key, value in item.iteritems():
				self[key.lower()] = value
				if key == 'id':
					self.id = value
			# if not self.has_key('name') or self['name'] is None:
			# 	self.name = self.id + guess_ext(self['mime'])

	def __getattr__(self, name):
		if name == 'dict':
			return self
		else:
			return self.get(name, None)

	def _fix_meta(self, item):
		'''convert mongo item to simple'''
		item['id'] = item.pop('_id')
		if item.has_key('length'):
			item['size'] = item.pop('length')
		elif item.has_key('content_length'):
			item['size'] = item.pop('content_length')
		if item.has_key('uploadDate'):
			item['created'] = item.pop('uploadDate')
		if item.has_key('contentType'):
			item['mime'] = item.pop('contentType')
		if item.has_key('content_type'):
			item['mime'] = item.pop('content_type')
		if not item.has_key('filename') and item.has_key('path'):
			item['filename'] = item.pop('path')
		item.pop('chunkSize', None)
		item.pop('app_id', None)
		if item.has_key('md5') and not item.has_key('hash'):
			item['hash'] = [item['md5']]
			# item.pop('md5', None)
		# print item
		return item

	@property
	def file(self):
		return self.imsto._get(self)


class EngineError(Exception):
	""" Invalid Engine """
	pass

class UrlError(Exception):
	""" Invalid Url or path """
	pass

class HttpFound(Exception):
	""" TODO: path has been changed """

	def __init__(self, message, path, **kwds):
		self.args = message, kwds.copy()
		self.msg, self.extra = self.args
		self.path = path


class DuplicateError(Exception):
	""" Entry Duplicated """
	pass

def get_mongo_db(host_or_uri, db_name, replica_set = None):
	if replica_set:
		c = MongoReplicaSetClient(host_or_uri, replicaSet=replica_set,read_preference=ReadPreference.NEAREST)
	else:
		c = MongoClient(host_or_uri,read_preference=ReadPreference.NEAREST)
	return c[db_name]

def _make_id(hashed, size=None):
	"""make mongo item id by file hash value"""
	if size is None or size < 1:
		return base_convert(hashed, 16, 36)
	if not isinstance(size, Integral):
		raise TypeError('expected a int, not ' + repr(size))
	return base_convert('{}{:02x}'.format(hashed, size % 255), 16, 36)

def _make_filename(id, ext):
	match = re.match('([a-z0-9]{2})([a-z0-9]{2})([a-z0-9]{16,36})',id)
	if match:
		return '{0[0]}/{0[1]}/{0[2]}.{1}'.format(match.groups(), ext)
	raise ValueError('invalid id %s' % id)
	# return id + '.' + ext


class StoreEngineGridFs(StoreBase):
	"""docstring for StoreEngineGridFs"""
	_db = None
	_fs = None
	def __init__(self, section):
		StoreBase.__init__(self, section)

	def _get(self, id):
		if isinstance(id, StoreItem):
			id = id.id
		if id and self.exists(id):
			return self.fs.get(id)
	
	def delete(self, id):
		self.fs.delete(id)
		if self.fs.exists(id):
			return False
		return True

	def _put(self, data, **spec):
		return self.fs.put(data, **spec)

	def _store_exists(self, id=None, *args, **kwargs):
		#print id
		return self.fs.exists(id)

	@property
	def fs(self):
		if not self._fs:
			import gridfs
			self._fs = gridfs.GridFS(self.db,self.fs_prefix)

		return self._fs

class StoreEngineS3(StoreBase):
	"""docstring for StoreEngineS3"""
	_bucket = None
	def __init__(self, section):
		StoreBase.__init__(self, section)

	def _get(self, id):
		if isinstance(id, str):
			if id.rfind('.') > 0:
				key = id
			else:
				item = self.get_meta(id)
				if item:
					key = item.filename
					# print 'found %s' % item
		elif isinstance(id, StoreItem):
			key = id.filename
		else:
			raise ValueError('invalid id or key')
		return self.bucket.get(key)

	def delete(self, id):
		key = None
		if isinstance(id, str):
			item = self.get_meta(id)
			if item:
				print 'found item id: %s' % id
				key = item.filename
		elif isinstance(id, StoreItem):
			key = id.filename
			id = id.id
		else:
			raise ValueError('invalid id or key')
		if key is not None and id and self.bucket.delete(key):
			print 'delete filename: %s ok' % key
		 	r = self.collection.remove(id,safe=True)
		 	return 'ok' in r and r['err'] is None
		return False

	def _put(self, data, **spec):

		metadata = {}
		for k in spec['meta']:
			metadata[k] = str(spec['meta'][k])

		if 'name' in spec and isinstance(spec['name'], (str, unicode)):
			from urllib import quote_plus
			metadata['name'] = quote_plus(spec['name'].encode('utf-8') if isinstance(spec['name'], unicode) else spec['name'])
			# print metadata['name']

		headers = {'Content-Length': spec['size']}
		try:
			filename = spec['filename']
			self.bucket.put(filename, data=data, mimetype=spec['mime'], metadata=metadata, headers=headers)
			print "save ok %s to s3" % filename
			self._save_meta(spec['_id'], spec)
			print "save ok meta %s" % spec['_id']
			return spec['_id']
		except Exception, e:
			raise e
		

	def _store_exists(self, id=None, *args, **kwargs):
		if 'filename' in kwargs and kwargs['filename'] is not None:
			return kwargs["filename"] in self.bucket
		return False

	@property
	def bucket(self):
		if self._bucket is None:
			from simples3 import S3Bucket, KeyNotFound
			bucket_name = self.get_config('bucket_name')
			if bucket_name is None:
				raise ValueError("no bucket_name in section '%s'" % self.section)
			access_key = self.get_config('s3_access_key')
			secret_key = self.get_config('s3_secret_key')
			self._bucket = S3Bucket(bucket_name, access_key=access_key, secret_key=secret_key)
		return self._bucket

WEED_HOST = 'weed_vol_host'
WEED_FID = 'weed_fid'

class StoreEngineWeedFs(StoreBase):
	"""docstring for StoreEngineWeedFs"""
	def __init__(self, section):
		StoreBase.__init__(self, section)
		from weedfs import WeedClient
		self.client = WeedClient()

	def _get(self, id):
		print '_get {}'.format(id)
		item = id if isinstance(id, StoreItem) else self.get_meta(id)
		if not item.has_key(WEED_HOST) or not item.has_key(WEED_HOST):
			raise ValueError('the entry has no special value ' + WEED_HOST + ' and ' + WEED_FID)
		volume_host, fid = item[WEED_HOST], item[WEED_FID]
		ctype, size, content = self.client.retrieve(volume_host, fid)
		print 'weed retrieved: %s %s' % (ctype, size)
		if content:
			from StringIO import StringIO
			return StringIO(content)
		raise ValueError('weed client.retrieve error: invalid response')

	def delete(self, id):
		raise NotImplemented()

	def _put(self, data, **spec):
		volume_host, fid = self.client.assign()
		ret = self.client.store(volume_host, fid, content=data, name=spec['filename'], content_type=spec['mime'])
		if isinstance(ret, int) and ret > 0:
			print 'saved {}/{} size {} bytes'.format(volume_host, fid, ret)
			spec[WEED_HOST] = volume_host
			spec[WEED_FID] = fid
			self._save_meta(spec['_id'], spec)
			return spec['_id']
		print 'store error: %s' % ret
		

	def _store_exists(self, id=None, *args, **kwargs):
		if hasattr(kwargs, WEED_HOST) and hasattr(kwargs, WEED_FID):
			ctype, size = self.client.retrieve(kwargs[WEED_HOST],kwargs[WEED_FID], head=True)
			print 'exists %s %s' % (ctype, size)
			return True
		return False




########NEW FILE########
__FILENAME__ = tool
#!/usr/bin/env python
# encoding: utf-8
"""
tool.py

Created by liut on 2010-12-24.
Copyright (c) 2010-2013 liut. All rights reserved.
"""

import sys
import os
from store import load_imsto, Config


section = 'imsto'


def list_dir(limit=5,start=0,prefix=''):
	imsto = load_imsto(section)
	gallery = imsto.browse(limit, start)
	if gallery['total'] == 0:
		print 'total 0, empty'
		return

	print 'total {}'.format(gallery['total'])
	for item in gallery['items']:
		#print hasattr(item.file, 'read')
		#print(item)
		print("{0[filename]}\t{0[size]:8,d}".format(item))

def store_file(filename):
	if os.access(filename, os.R_OK):
		imsto = load_imsto(section)
		from _util import guess_mimetype
		ctype = guess_mimetype(filename)
		with open(filename) as fp:
			ret = imsto.store(fp, ctype, name=os.path.basename(filename))
			print ret
	else:
		print 'image {} not found or access deny'.format(filename)


if __name__ == "__main__":
	import argparse
	config = Config()
	parser = argparse.ArgumentParser(usage='%(prog)s [options]')
	parser.add_argument('-s', '--section', metavar='section', default='imsto', choices=config.sections(), type=str, help='Special config section')
	parser.add_argument('-i', '--add', metavar='filename', type=str, help='Import file to storeage')
	parser.add_argument('-q', '--query', metavar='[exist|meta]', type=str, choices=['exist', 'meta'], help='query a file')
	parser.add_argument('-f', '--fetch', metavar='path', type=str, help='fetch a file')
	parser.add_argument('--id', metavar='id', type=str, help='Special file id')
	parser.add_argument('--path', metavar='path', type=str, help='Special file path')
	parser.add_argument('-v', '--verbose', action='store_true')
	parser.add_argument('-l', '--list', action='store_true', help='List files')
	#default=argparse.SUPPRESS
	parser.add_argument('--limit', type=int, default=5)
	parser.add_argument('--start', type=int, default=0)
	parser.add_argument('--prefix', type=str, default='')
	args, remaining = parser.parse_known_args()
	#print args

	section = args.section
	print section
	if args.list:
		list_dir(args.limit, args.start, prefix=args.prefix)
	elif args.fetch:
		imsto = load_imsto(section)
		_file, _path = imsto.load('orig/{}'.format(args.fetch))
		print _path
	elif args.query:
		imsto = load_imsto(section)
		method = imsto.get_meta if args.query == 'meta' else imsto.exists
		# print method
		print method(args.id or None,filename=args.path or None)
	elif args.add:
		store_file(filename=args.add)
	else:
		parser.print_help()
	#sys.exit(main())


########NEW FILE########
__FILENAME__ = weedfs
# encoding: utf-8
"""
weedfs.py

Created by liut on 2013-06-09.
Copyright (c) 2010-2013 liut. All rights reserved.
"""


import os
import urllib
import httplib2
import json
from _util import *

class WeedClient(object):
	"""Client for weed-fs
		Learn from: https://github.com/micjohnson/weed-php
	"""
	def __init__(self, master = 'localhost:9333', replication = None):
		self.master = master
		self.default_replication = replication

	def _request(self, url, method = 'GET', body = None, headers = None):
		print '_request: %s' % url
		h = httplib2.Http()
		if method == 'POST':
			resp, content, = h.request(url, method, body=body, headers=headers)
		else:
			resp, content = h.request(url, method)

		#print resp
		#print content
		try:
			if resp.status >= 400:
				print 'request error: {} {}'.format(resp.status, resp.reason)
				print 'response: {}'.format(content)
				return resp.status, resp.reason, json.loads(content) if content.startswith('{') else content
			if resp['content-type'] == 'application/javascript' or resp.status == 201 and resp['content-type'] == 'text/plain; charset=utf-8':
				return resp.status, resp.reason, json.loads(content)
			# get content
			return resp['content-type'], int(resp['content-length']), content
		except Exception, e:
			print e
			print resp
			return resp.status, e, None

	def assign(self, count = 1, replication = None):
		url = 'http://{}/dir/assign?count={}'.format(self.master,int(count))
		if replication is None:
			replication = self.default_replication
		if replication:
			url = '{}&replication={}'.format(url, replication)
		#{"count":1,"fid":"2,753b19e78fe6","publicUrl":"127.0.0.1:9334","url":"localhost:9334"}
		first, second, result = self._request(url)
		#volume_host, fid = 
		if first >= 200 and first < 300 and isinstance(result, dict):
			return result['publicUrl'], result['fid']
		print 'error assign {}: {}, content: {}'.format(first, second, result)

	def status(self):
		url = 'http://{}/dir/status'.format(self.master)

		return self._request(url)

	def retrieve(self, volume_host, fid, head=False):
		url = 'http://{}/{}'.format(volume_host, fid)
		#f = urllib.urlopen(url)
		first, second, content = self._request(url, 'HEAD' if head else 'GET')
		#print 'retrieve %s %s' % (first, second)
		if isinstance(first, str):
			return first, second, content
		print 'error retrieve: {}: {}, content: {}'.format(first, second, len(content))
		return first, second, None

	def delete(self, volume_host, fid):
		url = 'http://{}/{}'.format(volume_host, fid)
		return self._request(url, 'DELETE')

	def lookup(self, volumeId):
		url = 'http://{}/dir/lookup?volumeId={}'.format(self.master, volumeId)
		return self._request(url)

	def grow(self, count, replication):
		url = 'http://{}/dir/grow?count={}&replication={}'.format(self.master,int(count),replication)
		return self._request(url)

	def store(self, volume_host, fid, file = None, content = None, name = None, content_type = None):
		content_type, body = encode_upload(file=file, content=content, name=name, content_type=content_type)
		headers = { 'Content-Type': content_type }
		url = 'http://{}/{}'.format(volume_host, fid)
		first, second, result = self._request(url, 'POST', body=body, headers=headers)
		print type(result)
		print result
		if isinstance(result, dict):
			return result['size']




if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(usage='%(prog)s command')
	parser.add_argument('-a','--assign',metavar='count',type=int)
	parser.add_argument('-l','--lookup',metavar='volumeId',type=int)
	parser.add_argument('-u','--upload',metavar='filename',type=str)
	parser.add_argument('-f','--fetch',metavar='host/fid',type=str)
	parser.add_argument('-r','--replication',metavar='type',type=str,default=None)
	parser.add_argument('-s','--status', action='store_true')
	args, remaining = parser.parse_known_args()

	client = WeedClient()
	if args.assign:
		ret = client.assign(args.assign,args.replication)
		print type(ret)
		print json.dumps(ret, indent=4)
	elif args.lookup:
		ret = client.lookup(args.lookup)
		print type(ret)
		print json.dumps(ret, indent=4)
	elif args.status:
		ret = client.status()
		print json.dumps(ret, indent=4)
	elif args.upload:
		volume_host, fid = client.assign(1,args.replication)
		ret = client.store(volume_host, fid, args.upload)
		#ret = client.store(volume_host, fid, open(args.upload, 'rb'), name=os.path.basename(args.upload))
		print type(ret)
		print ret
	elif args.fetch:
		volume_host, fid = args.fetch.split('/', 2)
		ret = client.retrieve(volume_host, fid, head=True)
		print ret
	else:
		parser.print_help()

########NEW FILE########
__FILENAME__ = _base

__all__ = ['base_convert']

#BASE2 = "01"
#BASE10 = "0123456789"
#BASE16 = "0123456789abcdef"
#BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def base_convert(number,frombase = 10, tobase = 36):
	""" converts a "number" between two bases of arbitrary digits

	The input number is assumed to be a string of digits from the
	fromdigits string (which is in order of smallest to largest
	digit). The return value is a string of elements from todigits
	(ordered in the same way). The input and output bases are
	determined from the lengths of the digit strings. Negative 
	signs are passed through.


	"""
	
	if not 2 <= frombase <= 62 or not 2 <= tobase <= 62:
		raise ValueError, 'The base number must be between 2 and 36.'

	if str(number)[0]=='-':
		number = str(number)[1:]
		neg=1
	else:
		neg=0

	fromdigits = BASE62[:frombase]
	todigits = BASE62[:tobase]
	
	#print(fromdigits, todigits)
	#print(len(fromdigits), len(todigits))
	
	# make an integer out of the number
	x=long(0)
	for digit in str(number):
		#print '%d %s %d' % (x, digit, fromdigits.index(digit))
		x = x*frombase + fromdigits.index(digit)
	
	#print 'last x: %s' % x
	## create the result in base 'len(todigits)'
	res=""
	while x>0:
		digit = x % tobase
		#print 'x %s d %s' % (x, digit)
		res = todigits[digit] + res
		x /= tobase
	if neg:
		res = "-"+res

	return res

if __name__ == '__main__':
	a = 45
	print '{0}: {1}'.format(a, base_convert(a, 10, 36))
	a = 'abcd'
	print '{0}: {1}'.format(a, base_convert(a, 16, 36))
	a = '5cc163b92ab9b482b4486999d354f91e'
	print '{0}: {1}'.format(a, base_convert(a, 16, 36))

########NEW FILE########
__FILENAME__ = _config
# encoding: utf-8
"""
ImSto Config

Created by liut on 2010-12-15.
Copyright (c) 2010-2013 liut. All rights reserved.
"""

__all__ = ['Config']

import ConfigParser,os

class Singleton(type):
	_instances = {}
	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls._instances[cls]

class Config(object):
	__metaclass__ = Singleton

	"""docstring for Config"""
	def __init__(self):
		
		self.defaulting = {
		'servers': 'localhost',
		'replica_set': None,
		'engine': 'mongodb',
		'db_name': 'storage',
		'fs_prefix': 'img',
		'thumb_path': '/thumb',
		'thumb_root': '/opt/imsto/cache/thumb/',
		'temp_root': '/tmp/',
		'thumb_method': 'shell', # shell, wand, pil
		'url_prefix': 'http://m.imsto.net/',
		'eggs_cache': '/opt/imsto/cache/eggs',
		'max_file_size': '102400',
		'max_jpeg_quality': '88',
		'max_width': '1920',
		'max_height': '1920',
		'support_size': '120,160,250,400',
		'admin_name': 'imsto',
		'admin_pass': '',
		}
		self.config = ConfigParser.ConfigParser()
		if os.environ.has_key('IMSTO_CONF_DIR'):
			ini_file = os.path.join(os.environ['IMSTO_CONF_DIR'], 'imsto.ini')
		else:
			ini_file = os.path.join(os.getcwd(), 'config/imsto.ini')
		print 'config: {}'.format(ini_file)

		ret = self.config.read(ini_file)
		if len(ret) == 0:
			print('Error: imsto.ini not found or read error')
		
		if os.environ.has_key('PYTHON_EGG_CACHE') and not (os.environ['PYTHON_EGG_CACHE'] is None):
			pass
		else:
			pass
			#os.environ['PYTHON_EGG_CACHE'] = self.get('eggs_cache')
	
	def get(self, name, section='imsto'):
		"""docstring for get"""
		for s in [section, 'common']:
			if self.config.has_option(s, name):
				return self.config.get(s, name)

		if name.startswith('s3_'):
			if not name.upper() in os.environ:
				print 'ENV %s not found' % name.upper()
			return os.environ.get(name.upper(), None)

		if self.defaulting.has_key(name):
			return self.defaulting[name];

		return None

	def sections(self):
		ss = self.config.sections()
		if 'common' in ss:
			del ss[ss.index('common')]
		return ss

	def has_section(self, section):
		return self.config.has_section(section)


if __name__ == '__main__':
	config = Config()
	config2 = Config()
	print id(config)
	print id(config2)
	print(config.config.sections())
	print(config.get('servers'))
	print config.get('thumb_root')
	print config.get('thumb_root', 'avatar')
########NEW FILE########
__FILENAME__ = _util
# encoding: utf-8
"""
_util.py

Created by liut on 2010-12-04.
Copyright (c) 2010-2013 liut. All rights reserved.
"""

import os

from _wand import NewMagickWand,MagickReadImage,MagickToMime,\
MagickGetImageFormat,MagickGetImageWidth,MagickGetImageHeight,MagickGetImageCompressionQuality

__all__ = [
'check_dirs', 'save_file', 'identify_image', 'guessImageType',
'identify_image', 'thumb_image', 'watermark_image', 
'guess_mimetype', 'guess_ext', 'password_hash',
'encode_upload', 'jpegoptim'
]

def check_dirs(filename):
	dir_name = os.path.dirname(filename)
	if not os.path.exists(dir_name):
		os.makedirs(dir_name, 0777)

def save_file(filename, file = None, blob = None):
	check_dirs(filename)
	if file is None and blob is None:
		raise ValueError('invalid argument: file and blob are both None')
	fp = open(filename, 'wb')
	try:
		fp.write(blob if blob else file.read())
	except Exception, e:
		print('save file {} failed, error: {}'.format(filename, e))
	finally:
		fp.close()

	statinfo = os.stat(filename)
	if statinfo.st_size == 0:
		print('file size is zero, remove it')
		os.remove(filename)

sig_gif = b'GIF'
sig_jpg = b'\xff\xd8\xff'
#sig_png = b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'
sig_png = b"\211PNG\r\n\032\n"

def guessImageType(data):
	if data[:3] == sig_gif:
		return 'gif'
	elif data[:3] == sig_jpg:
		return 'jpg'
	elif data[:8] == sig_png:
		return 'png'
	else:
		return None

"""
test log
magickwand: 25M
PIL: 12M
shell: 11M
"""
def thumbnail_shell(filename, size_1, distname):
	size = size_1, size_1
	info = identify_shell(filename)
	if info is None:
		return None
	if info['size'] > size:
		print('thumbnail {0} to: {1}'.format(filename, size_1))
		from subprocess import check_call
		check_call(['convert','-thumbnail',str(size_1),filename,distname])
	else:
		from shutil import copyfile
		copyfile(filename, distname)

def identify_shell(imagefile):
	from subprocess import check_output
	try:
		output = check_output(['identify', '-format', '%m %w %h %Q', imagefile])
		info = output.split(' ')
		return {'format': info[0], 'size': (int(info[1]), int(info[2])), 'quality': int(info[3])}
	except CalledProcessError, e:
		print (e)
		return None

def identify_wand(imagefile):
	magick_wand = NewMagickWand()
	if not MagickReadImage(magick_wand, imagefile):
		return False
	format = MagickGetImageFormat(magick_wand)
	info = {
		'format': format,
		'mime': MagickToMime(format),
		'size': (MagickGetImageWidth(magick_wand), MagickGetImageHeight(magick_wand)),
		'quality': MagickGetImageCompressionQuality(magick_wand)
	}

	DestroyMagickWand(magick_wand)

	return info

def identify_image(imagefile, method = 'wand'):
	if method == 'wand':
		return identify_wand(imagefile)
	if method == 'shell':
		return identify_shell(imagefile)

def thumbnail_wand(filename, width, height, distname, mode='s'):
	from image import SimpImage
	im = SimpImage(filename)
	if mode == 'c':
		ret = im.cropThumbnail(width, height)
	elif mode == 'w':
		ret = im.thumbnail(width, max_width=width)
	elif mode == 'h':
		ret = im.thumbnail(width, max_height=width)
	else:
		ret = im.thumbnail(width, height)

	print "thumbnail {} {}x{} result: {}".format(mode, width, height, ret)
	if ret:
		ret = im.save(distname)
	del im

	return ret



def thumbnail_pil(filename, size_1, distname):
	size = size_1, size_1
	from PIL import Image
	im = Image.open(filename)
	if im.size > size:
		im.thumbnail(size, Image.ANTIALIAS)
	im.save(distname, im.format)
	del im

def thumb_image(filename, width, height, distname, mode='s', method='wand'):
	check_dirs(distname)
	if method == 'shell':
		return thumbnail_shell(filename, width, distname)
	elif method == 'wand':
		return thumbnail_wand(filename, width, height, distname, mode=mode)
	elif method == 'pil':
		return thumbnail_pil(filename, width, distname)



def guess_mimetype(fn, default="application/octet-stream"):
	"""Guess a mimetype from filename *fn*.

	>>> guess_mimetype("foo.txt")
	'text/plain'
	>>> guess_mimetype("foo")
	'application/octet-stream'
	"""
	import mimetypes
	if "." not in fn:
		return default
	bfn, ext = fn.lower().rsplit(".", 1)
	if ext == "jpg": ext = "jpeg"
	return mimetypes.guess_type(bfn + "." + ext)[0] or default

def guess_ext(mime):
	import mimetypes
	ext = mimetypes.guess_extension(mime)
	if ext == '.jpe':
		return '.jpg'
	return ext

def watermark_image(filename, distname):
	from image import SimpImage
	im = SimpImage(filename)
	if os.environ.has_key('IMSTO_CONF_DIR'):
		watermark = os.path.join(os.environ['IMSTO_CONF_DIR'], 'watermark.png')
		copyright = os.path.join(os.environ['IMSTO_CONF_DIR'], 'watermark-copy.png')
	else:
		watermark = os.path.join(os.getcwd(), 'config/watermark.png')
		copyright = os.path.join(os.getcwd(), 'config/watermark-copy.png')
	#print ini_file
	im_w = SimpImage(watermark)
	#print im_w.wand
	check_dirs(distname)
	ci = SimpImage(copyright) if os.access(copyright, os.R_OK) else None
	r = None
	if im.watermark(im_w, 0.5, position='golden', copyright=ci):
		print 'watermark ok'
		r = im.save(distname)

	if r is None:
		print 'error watermark'

	del im
	del im_w
	return r

def password_hash(username, password):
	from hashlib import sha1
	return sha1(':'.join([username.lower(), password])).hexdigest()


def encode_upload(file=None, content=None, content_type=None, name=None, ext_data=[]):
	"""encode a upload file form
		Learn from: http://mancoosi.org/~abate/upload-file-using-httplib
	"""
	BOUNDARY = '----------bundary------'
	CRLF = '\r\n'
	#print CRLF
	body = []
	# Add the metadata about the upload first
	for key, value in ext_data:
		body.extend(
		  ['--' + BOUNDARY,
		   'Content-Disposition: form-data; name="%s"' % key,
		   '',
		   value,
		   ])
	# Now add the file itself
	if content is None:
		if file is None:
			raise ValueError('need file or content argument')
	 	if hasattr(file, 'read'):
			content = file.read()
		else:
			name = os.path.basename(file)
			f = open(file, 'rb')
			content = f.read()
			f.close()

	#print 'type content: %s, len content: %s' % (type(content), len(content))

	if name is None:
		ext = guessImageType(content[:32])
		name = 'data.{}'.format(ext)

	if content_type is None:
		content_type = guess_mimetype(name)

	body.extend(
	  ['--' + BOUNDARY,
	   str('Content-Disposition: form-data; name="file"; filename="%s"' % name),
	   # The upload server determines the mime-type, no need to set it.
	   str('Content-Type: %s' % content_type),
	   '',
	   content,
	   ])
	# Finalize the form body
	body.extend(['--' + BOUNDARY + '--', ''])
	return 'multipart/form-data; boundary=%s' % BOUNDARY, CRLF.join(body)

def jpegoptim(imagefile, max_quality = 88):
	print 'jpegoptim {} (max {})'.format(imagefile, max_quality)
	import subprocess
	r = subprocess.call(["jpegoptim","--strip-all", "--max={}".format(max_quality), imagefile])
	if r != 0:
		print 'call jpegoptim failed {}'.format(r)
		return False
	return True



########NEW FILE########
__FILENAME__ = _wand
# ImageMagick MagickWand 5 API Wrapper, generated and edited
#
from ctypes import *
from ctypes.util import find_library

def load_library():
    for suffix in '-6.Q16', '-Q16', '', '-Q8':
        wand_lib = find_library('MagickWand' + suffix)
        if not wand_lib:
            continue
        try:
            _lib = CDLL(wand_lib)
        except (IOError, OSError):
            continue
        return _lib
    raise ImportError('MagickWand library cannot be found or import failed.')

_lib = load_library()
wand_version = 5
# end of edit

STRING = c_char_p
WSTRING = c_wchar_p

# values for enumeration 'MagickBooleanType'
MagickFalse = 0
MagickTrue = 1
MagickBooleanType = c_int # enum
class _Image(Structure):
    pass
Image = _Image
class KernelInfo(Structure):
    pass
class _ExceptionInfo(Structure):
    pass
ExceptionInfo = _ExceptionInfo
AccelerateConvolveImage = _lib.AccelerateConvolveImage
AccelerateConvolveImage.restype = MagickBooleanType
AccelerateConvolveImage.argtypes = [POINTER(Image), POINTER(KernelInfo), POINTER(Image), POINTER(ExceptionInfo)]
class _ImageInfo(Structure):
    pass
ImageInfo = _ImageInfo
AnimateImages = _lib.AnimateImages
AnimateImages.restype = MagickBooleanType
AnimateImages.argtypes = [POINTER(ImageInfo), POINTER(Image)]
AnnotateComponentGenesis = _lib.AnnotateComponentGenesis
AnnotateComponentGenesis.restype = MagickBooleanType
AnnotateComponentGenesis.argtypes = []
class _DrawInfo(Structure):
    pass
DrawInfo = _DrawInfo
AnnotateImage = _lib.AnnotateImage
AnnotateImage.restype = MagickBooleanType
AnnotateImage.argtypes = [POINTER(Image), POINTER(DrawInfo)]
class _TypeMetric(Structure):
    pass
TypeMetric = _TypeMetric
GetMultilineTypeMetrics = _lib.GetMultilineTypeMetrics
GetMultilineTypeMetrics.restype = MagickBooleanType
GetMultilineTypeMetrics.argtypes = [POINTER(Image), POINTER(DrawInfo), POINTER(TypeMetric)]
GetTypeMetrics = _lib.GetTypeMetrics
GetTypeMetrics.restype = MagickBooleanType
GetTypeMetrics.argtypes = [POINTER(Image), POINTER(DrawInfo), POINTER(TypeMetric)]
__ssize_t = c_long
ssize_t = __ssize_t
FormatMagickCaption = _lib.FormatMagickCaption
FormatMagickCaption.restype = ssize_t
FormatMagickCaption.argtypes = [POINTER(Image), POINTER(DrawInfo), MagickBooleanType, POINTER(TypeMetric), POINTER(STRING)]
AnnotateComponentTerminus = _lib.AnnotateComponentTerminus
AnnotateComponentTerminus.restype = None
AnnotateComponentTerminus.argtypes = []
GetNextImageArtifact = _lib.GetNextImageArtifact
GetNextImageArtifact.restype = STRING
GetNextImageArtifact.argtypes = [POINTER(Image)]
RemoveImageArtifact = _lib.RemoveImageArtifact
RemoveImageArtifact.restype = STRING
RemoveImageArtifact.argtypes = [POINTER(Image), STRING]
GetImageArtifact = _lib.GetImageArtifact
GetImageArtifact.restype = STRING
GetImageArtifact.argtypes = [POINTER(Image), STRING]
CloneImageArtifacts = _lib.CloneImageArtifacts
CloneImageArtifacts.restype = MagickBooleanType
CloneImageArtifacts.argtypes = [POINTER(Image), POINTER(Image)]
DefineImageArtifact = _lib.DefineImageArtifact
DefineImageArtifact.restype = MagickBooleanType
DefineImageArtifact.argtypes = [POINTER(Image), STRING]
DeleteImageArtifact = _lib.DeleteImageArtifact
DeleteImageArtifact.restype = MagickBooleanType
DeleteImageArtifact.argtypes = [POINTER(Image), STRING]
SetImageArtifact = _lib.SetImageArtifact
SetImageArtifact.restype = MagickBooleanType
SetImageArtifact.argtypes = [POINTER(Image), STRING, STRING]
DestroyImageArtifacts = _lib.DestroyImageArtifacts
DestroyImageArtifacts.restype = None
DestroyImageArtifacts.argtypes = [POINTER(Image)]
ResetImageArtifactIterator = _lib.ResetImageArtifactIterator
ResetImageArtifactIterator.restype = None
ResetImageArtifactIterator.argtypes = [POINTER(Image)]

# values for enumeration 'ImageType'
UndefinedType = 0
BilevelType = 1
GrayscaleType = 2
GrayscaleMatteType = 3
PaletteType = 4
PaletteMatteType = 5
TrueColorType = 6
TrueColorMatteType = 7
ColorSeparationType = 8
ColorSeparationMatteType = 9
OptimizeType = 10
PaletteBilevelMatteType = 11
ImageType = c_int # enum
GetImageType = _lib.GetImageType
GetImageType.restype = ImageType
GetImageType.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
IsGrayImage = _lib.IsGrayImage
IsGrayImage.restype = MagickBooleanType
IsGrayImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
IsMonochromeImage = _lib.IsMonochromeImage
IsMonochromeImage.restype = MagickBooleanType
IsMonochromeImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
IsOpaqueImage = _lib.IsOpaqueImage
IsOpaqueImage.restype = MagickBooleanType
IsOpaqueImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]

# values for enumeration 'ChannelType'
UndefinedChannel = 0
RedChannel = 1
GrayChannel = 1
CyanChannel = 1
GreenChannel = 2
MagentaChannel = 2
BlueChannel = 4
YellowChannel = 4
AlphaChannel = 8
OpacityChannel = 8
MatteChannel = 8
BlackChannel = 32
IndexChannel = 32
CompositeChannels = 47
AllChannels = -1
TrueAlphaChannel = 64
RGBChannels = 128
GrayChannels = 128
SyncChannels = 256
DefaultChannels = -9
ChannelType = c_int # enum
size_t = c_ulong
SetImageChannelDepth = _lib.SetImageChannelDepth
SetImageChannelDepth.restype = MagickBooleanType
SetImageChannelDepth.argtypes = [POINTER(Image), ChannelType, size_t]
SetImageDepth = _lib.SetImageDepth
SetImageDepth.restype = MagickBooleanType
SetImageDepth.argtypes = [POINTER(Image), size_t]
class _RectangleInfo(Structure):
    pass
RectangleInfo = _RectangleInfo
GetImageBoundingBox = _lib.GetImageBoundingBox
GetImageBoundingBox.restype = RectangleInfo
GetImageBoundingBox.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
GetImageChannelDepth = _lib.GetImageChannelDepth
GetImageChannelDepth.restype = size_t
GetImageChannelDepth.argtypes = [POINTER(Image), ChannelType, POINTER(ExceptionInfo)]
GetImageDepth = _lib.GetImageDepth
GetImageDepth.restype = size_t
GetImageDepth.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
GetImageQuantumDepth = _lib.GetImageQuantumDepth
GetImageQuantumDepth.restype = size_t
GetImageQuantumDepth.argtypes = [POINTER(Image), MagickBooleanType]
class _IO_FILE(Structure):
    pass
FILE = _IO_FILE
GetBlobFileHandle = _lib.GetBlobFileHandle
GetBlobFileHandle.restype = POINTER(FILE)
GetBlobFileHandle.argtypes = [POINTER(Image)]
BlobToImage = _lib.BlobToImage
BlobToImage.restype = POINTER(Image)
BlobToImage.argtypes = [POINTER(ImageInfo), c_void_p, size_t, POINTER(ExceptionInfo)]
PingBlob = _lib.PingBlob
PingBlob.restype = POINTER(Image)
PingBlob.argtypes = [POINTER(ImageInfo), c_void_p, size_t, POINTER(ExceptionInfo)]
BlobToFile = _lib.BlobToFile
BlobToFile.restype = MagickBooleanType
BlobToFile.argtypes = [STRING, c_void_p, size_t, POINTER(ExceptionInfo)]
FileToImage = _lib.FileToImage
FileToImage.restype = MagickBooleanType
FileToImage.argtypes = [POINTER(Image), STRING]
GetBlobError = _lib.GetBlobError
GetBlobError.restype = MagickBooleanType
GetBlobError.argtypes = [POINTER(Image)]
ImageToFile = _lib.ImageToFile
ImageToFile.restype = MagickBooleanType
ImageToFile.argtypes = [POINTER(Image), STRING, POINTER(ExceptionInfo)]
InjectImageBlob = _lib.InjectImageBlob
InjectImageBlob.restype = MagickBooleanType
InjectImageBlob.argtypes = [POINTER(ImageInfo), POINTER(Image), POINTER(Image), STRING, POINTER(ExceptionInfo)]
IsBlobExempt = _lib.IsBlobExempt
IsBlobExempt.restype = MagickBooleanType
IsBlobExempt.argtypes = [POINTER(Image)]
IsBlobSeekable = _lib.IsBlobSeekable
IsBlobSeekable.restype = MagickBooleanType
IsBlobSeekable.argtypes = [POINTER(Image)]
IsBlobTemporary = _lib.IsBlobTemporary
IsBlobTemporary.restype = MagickBooleanType
IsBlobTemporary.argtypes = [POINTER(Image)]
MagickSizeType = c_ulonglong
GetBlobSize = _lib.GetBlobSize
GetBlobSize.restype = MagickSizeType
GetBlobSize.argtypes = [POINTER(Image)]
StreamHandler = CFUNCTYPE(size_t, POINTER(Image), c_void_p, size_t)
GetBlobStreamHandler = _lib.GetBlobStreamHandler
GetBlobStreamHandler.restype = StreamHandler
GetBlobStreamHandler.argtypes = [POINTER(Image)]
FileToBlob = _lib.FileToBlob
FileToBlob.restype = POINTER(c_ubyte)
FileToBlob.argtypes = [STRING, size_t, POINTER(size_t), POINTER(ExceptionInfo)]
GetBlobStreamData = _lib.GetBlobStreamData
GetBlobStreamData.restype = POINTER(c_ubyte)
GetBlobStreamData.argtypes = [POINTER(Image)]
ImageToBlob = _lib.ImageToBlob
ImageToBlob.restype = POINTER(c_ubyte)
ImageToBlob.argtypes = [POINTER(ImageInfo), POINTER(Image), POINTER(size_t), POINTER(ExceptionInfo)]
ImagesToBlob = _lib.ImagesToBlob
ImagesToBlob.restype = POINTER(c_ubyte)
ImagesToBlob.argtypes = [POINTER(ImageInfo), POINTER(Image), POINTER(size_t), POINTER(ExceptionInfo)]
DestroyBlob = _lib.DestroyBlob
DestroyBlob.restype = None
DestroyBlob.argtypes = [POINTER(Image)]
DuplicateBlob = _lib.DuplicateBlob
DuplicateBlob.restype = None
DuplicateBlob.argtypes = [POINTER(Image), POINTER(Image)]
SetBlobExempt = _lib.SetBlobExempt
SetBlobExempt.restype = None
SetBlobExempt.argtypes = [POINTER(Image), MagickBooleanType]
class _CacheView(Structure):
    pass
CacheView = _CacheView
AcquireCacheView = _lib.AcquireCacheView
AcquireCacheView.restype = POINTER(CacheView)
AcquireCacheView.argtypes = [POINTER(Image)]
CloneCacheView = _lib.CloneCacheView
CloneCacheView.restype = POINTER(CacheView)
CloneCacheView.argtypes = [POINTER(CacheView)]
DestroyCacheView = _lib.DestroyCacheView
DestroyCacheView.restype = POINTER(CacheView)
DestroyCacheView.argtypes = [POINTER(CacheView)]

# values for enumeration 'ClassType'
UndefinedClass = 0
DirectClass = 1
PseudoClass = 2
ClassType = c_int # enum
GetCacheViewStorageClass = _lib.GetCacheViewStorageClass
GetCacheViewStorageClass.restype = ClassType
GetCacheViewStorageClass.argtypes = [POINTER(CacheView)]

# values for enumeration 'ColorspaceType'
UndefinedColorspace = 0
RGBColorspace = 1
GRAYColorspace = 2
TransparentColorspace = 3
OHTAColorspace = 4
LabColorspace = 5
XYZColorspace = 6
YCbCrColorspace = 7
YCCColorspace = 8
YIQColorspace = 9
YPbPrColorspace = 10
YUVColorspace = 11
CMYKColorspace = 12
sRGBColorspace = 13
HSBColorspace = 14
HSLColorspace = 15
HWBColorspace = 16
Rec601LumaColorspace = 17
Rec601YCbCrColorspace = 18
Rec709LumaColorspace = 19
Rec709YCbCrColorspace = 20
LogColorspace = 21
CMYColorspace = 22
ColorspaceType = c_int # enum
GetCacheViewColorspace = _lib.GetCacheViewColorspace
GetCacheViewColorspace.restype = ColorspaceType
GetCacheViewColorspace.argtypes = [POINTER(CacheView)]
Quantum = c_ushort
IndexPacket = Quantum
GetCacheViewVirtualIndexQueue = _lib.GetCacheViewVirtualIndexQueue
GetCacheViewVirtualIndexQueue.restype = POINTER(IndexPacket)
GetCacheViewVirtualIndexQueue.argtypes = [POINTER(CacheView)]
class _PixelPacket(Structure):
    pass
PixelPacket = _PixelPacket
GetCacheViewVirtualPixels = _lib.GetCacheViewVirtualPixels
GetCacheViewVirtualPixels.restype = POINTER(PixelPacket)
GetCacheViewVirtualPixels.argtypes = [POINTER(CacheView), ssize_t, ssize_t, size_t, size_t, POINTER(ExceptionInfo)]
GetCacheViewVirtualPixelQueue = _lib.GetCacheViewVirtualPixelQueue
GetCacheViewVirtualPixelQueue.restype = POINTER(PixelPacket)
GetCacheViewVirtualPixelQueue.argtypes = [POINTER(CacheView)]
GetCacheViewException = _lib.GetCacheViewException
GetCacheViewException.restype = POINTER(ExceptionInfo)
GetCacheViewException.argtypes = [POINTER(CacheView)]
GetCacheViewAuthenticIndexQueue = _lib.GetCacheViewAuthenticIndexQueue
GetCacheViewAuthenticIndexQueue.restype = POINTER(IndexPacket)
GetCacheViewAuthenticIndexQueue.argtypes = [POINTER(CacheView)]
GetOneCacheViewVirtualPixel = _lib.GetOneCacheViewVirtualPixel
GetOneCacheViewVirtualPixel.restype = MagickBooleanType
GetOneCacheViewVirtualPixel.argtypes = [POINTER(CacheView), ssize_t, ssize_t, POINTER(PixelPacket), POINTER(ExceptionInfo)]

# values for enumeration 'VirtualPixelMethod'
UndefinedVirtualPixelMethod = 0
BackgroundVirtualPixelMethod = 1
ConstantVirtualPixelMethod = 2
DitherVirtualPixelMethod = 3
EdgeVirtualPixelMethod = 4
MirrorVirtualPixelMethod = 5
RandomVirtualPixelMethod = 6
TileVirtualPixelMethod = 7
TransparentVirtualPixelMethod = 8
MaskVirtualPixelMethod = 9
BlackVirtualPixelMethod = 10
GrayVirtualPixelMethod = 11
WhiteVirtualPixelMethod = 12
HorizontalTileVirtualPixelMethod = 13
VerticalTileVirtualPixelMethod = 14
HorizontalTileEdgeVirtualPixelMethod = 15
VerticalTileEdgeVirtualPixelMethod = 16
CheckerTileVirtualPixelMethod = 17
VirtualPixelMethod = c_int # enum
GetOneCacheViewVirtualMethodPixel = _lib.GetOneCacheViewVirtualMethodPixel
GetOneCacheViewVirtualMethodPixel.restype = MagickBooleanType
GetOneCacheViewVirtualMethodPixel.argtypes = [POINTER(CacheView), VirtualPixelMethod, ssize_t, ssize_t, POINTER(PixelPacket), POINTER(ExceptionInfo)]
GetOneCacheViewAuthenticPixel = _lib.GetOneCacheViewAuthenticPixel
GetOneCacheViewAuthenticPixel.restype = MagickBooleanType
GetOneCacheViewAuthenticPixel.argtypes = [POINTER(CacheView), ssize_t, ssize_t, POINTER(PixelPacket), POINTER(ExceptionInfo)]
SetCacheViewStorageClass = _lib.SetCacheViewStorageClass
SetCacheViewStorageClass.restype = MagickBooleanType
SetCacheViewStorageClass.argtypes = [POINTER(CacheView), ClassType]
SetCacheViewVirtualPixelMethod = _lib.SetCacheViewVirtualPixelMethod
SetCacheViewVirtualPixelMethod.restype = MagickBooleanType
SetCacheViewVirtualPixelMethod.argtypes = [POINTER(CacheView), VirtualPixelMethod]
SyncCacheViewAuthenticPixels = _lib.SyncCacheViewAuthenticPixels
SyncCacheViewAuthenticPixels.restype = MagickBooleanType
SyncCacheViewAuthenticPixels.argtypes = [POINTER(CacheView), POINTER(ExceptionInfo)]
GetCacheViewExtent = _lib.GetCacheViewExtent
GetCacheViewExtent.restype = MagickSizeType
GetCacheViewExtent.argtypes = [POINTER(CacheView)]
GetCacheViewChannels = _lib.GetCacheViewChannels
GetCacheViewChannels.restype = size_t
GetCacheViewChannels.argtypes = [POINTER(CacheView)]
GetCacheViewAuthenticPixelQueue = _lib.GetCacheViewAuthenticPixelQueue
GetCacheViewAuthenticPixelQueue.restype = POINTER(PixelPacket)
GetCacheViewAuthenticPixelQueue.argtypes = [POINTER(CacheView)]
GetCacheViewAuthenticPixels = _lib.GetCacheViewAuthenticPixels
GetCacheViewAuthenticPixels.restype = POINTER(PixelPacket)
GetCacheViewAuthenticPixels.argtypes = [POINTER(CacheView), ssize_t, ssize_t, size_t, size_t, POINTER(ExceptionInfo)]
QueueCacheViewAuthenticPixels = _lib.QueueCacheViewAuthenticPixels
QueueCacheViewAuthenticPixels.restype = POINTER(PixelPacket)
QueueCacheViewAuthenticPixels.argtypes = [POINTER(CacheView), ssize_t, ssize_t, size_t, size_t, POINTER(ExceptionInfo)]
GetVirtualIndexQueue = _lib.GetVirtualIndexQueue
GetVirtualIndexQueue.restype = POINTER(IndexPacket)
GetVirtualIndexQueue.argtypes = [POINTER(Image)]
GetVirtualPixels = _lib.GetVirtualPixels
GetVirtualPixels.restype = POINTER(PixelPacket)
GetVirtualPixels.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t, POINTER(ExceptionInfo)]
GetVirtualPixelQueue = _lib.GetVirtualPixelQueue
GetVirtualPixelQueue.restype = POINTER(PixelPacket)
GetVirtualPixelQueue.argtypes = [POINTER(Image)]
AcquirePixelCachePixels = _lib.AcquirePixelCachePixels
AcquirePixelCachePixels.restype = c_void_p
AcquirePixelCachePixels.argtypes = [POINTER(Image), POINTER(MagickSizeType), POINTER(ExceptionInfo)]
GetAuthenticIndexQueue = _lib.GetAuthenticIndexQueue
GetAuthenticIndexQueue.restype = POINTER(IndexPacket)
GetAuthenticIndexQueue.argtypes = [POINTER(Image)]
CacheComponentGenesis = _lib.CacheComponentGenesis
CacheComponentGenesis.restype = MagickBooleanType
CacheComponentGenesis.argtypes = []
class _MagickPixelPacket(Structure):
    pass
MagickPixelPacket = _MagickPixelPacket
GetOneVirtualMagickPixel = _lib.GetOneVirtualMagickPixel
GetOneVirtualMagickPixel.restype = MagickBooleanType
GetOneVirtualMagickPixel.argtypes = [POINTER(Image), ssize_t, ssize_t, POINTER(MagickPixelPacket), POINTER(ExceptionInfo)]
GetOneVirtualPixel = _lib.GetOneVirtualPixel
GetOneVirtualPixel.restype = MagickBooleanType
GetOneVirtualPixel.argtypes = [POINTER(Image), ssize_t, ssize_t, POINTER(PixelPacket), POINTER(ExceptionInfo)]
GetOneVirtualMethodPixel = _lib.GetOneVirtualMethodPixel
GetOneVirtualMethodPixel.restype = MagickBooleanType
GetOneVirtualMethodPixel.argtypes = [POINTER(Image), VirtualPixelMethod, ssize_t, ssize_t, POINTER(PixelPacket), POINTER(ExceptionInfo)]
GetOneAuthenticPixel = _lib.GetOneAuthenticPixel
GetOneAuthenticPixel.restype = MagickBooleanType
GetOneAuthenticPixel.argtypes = [POINTER(Image), ssize_t, ssize_t, POINTER(PixelPacket), POINTER(ExceptionInfo)]
MagickOffsetType = c_longlong
PersistPixelCache = _lib.PersistPixelCache
PersistPixelCache.restype = MagickBooleanType
PersistPixelCache.argtypes = [POINTER(Image), STRING, MagickBooleanType, POINTER(MagickOffsetType), POINTER(ExceptionInfo)]
SyncAuthenticPixels = _lib.SyncAuthenticPixels
SyncAuthenticPixels.restype = MagickBooleanType
SyncAuthenticPixels.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
GetImageExtent = _lib.GetImageExtent
GetImageExtent.restype = MagickSizeType
GetImageExtent.argtypes = [POINTER(Image)]
GetAuthenticPixels = _lib.GetAuthenticPixels
GetAuthenticPixels.restype = POINTER(PixelPacket)
GetAuthenticPixels.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t, POINTER(ExceptionInfo)]
GetAuthenticPixelQueue = _lib.GetAuthenticPixelQueue
GetAuthenticPixelQueue.restype = POINTER(PixelPacket)
GetAuthenticPixelQueue.argtypes = [POINTER(Image)]
QueueAuthenticPixels = _lib.QueueAuthenticPixels
QueueAuthenticPixels.restype = POINTER(PixelPacket)
QueueAuthenticPixels.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t, POINTER(ExceptionInfo)]
GetPixelCacheVirtualMethod = _lib.GetPixelCacheVirtualMethod
GetPixelCacheVirtualMethod.restype = VirtualPixelMethod
GetPixelCacheVirtualMethod.argtypes = [POINTER(Image)]
SetPixelCacheVirtualMethod = _lib.SetPixelCacheVirtualMethod
SetPixelCacheVirtualMethod.restype = VirtualPixelMethod
SetPixelCacheVirtualMethod.argtypes = [POINTER(Image), VirtualPixelMethod]
CacheComponentTerminus = _lib.CacheComponentTerminus
CacheComponentTerminus.restype = None
CacheComponentTerminus.argtypes = []
GetPixelCachePixels = _lib.GetPixelCachePixels
GetPixelCachePixels.restype = c_void_p
GetPixelCachePixels.argtypes = [POINTER(Image), POINTER(MagickSizeType), POINTER(ExceptionInfo)]
DecipherImage = _lib.DecipherImage
DecipherImage.restype = MagickBooleanType
DecipherImage.argtypes = [POINTER(Image), STRING, POINTER(ExceptionInfo)]
EncipherImage = _lib.EncipherImage
EncipherImage.restype = MagickBooleanType
EncipherImage.argtypes = [POINTER(Image), STRING, POINTER(ExceptionInfo)]
class _StringInfo(Structure):
    pass
StringInfo = _StringInfo
PasskeyDecipherImage = _lib.PasskeyDecipherImage
PasskeyDecipherImage.restype = MagickBooleanType
PasskeyDecipherImage.argtypes = [POINTER(Image), POINTER(StringInfo), POINTER(ExceptionInfo)]
PasskeyEncipherImage = _lib.PasskeyEncipherImage
PasskeyEncipherImage.restype = MagickBooleanType
PasskeyEncipherImage.argtypes = [POINTER(Image), POINTER(StringInfo), POINTER(ExceptionInfo)]
GetClientPath = _lib.GetClientPath
GetClientPath.restype = STRING
GetClientPath.argtypes = []
GetClientName = _lib.GetClientName
GetClientName.restype = STRING
GetClientName.argtypes = []
SetClientName = _lib.SetClientName
SetClientName.restype = STRING
SetClientName.argtypes = [STRING]
SetClientPath = _lib.SetClientPath
SetClientPath.restype = STRING
SetClientPath.argtypes = [STRING]
GetCoderList = _lib.GetCoderList
GetCoderList.restype = POINTER(STRING)
GetCoderList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
class _CoderInfo(Structure):
    pass
CoderInfo = _CoderInfo
GetCoderInfo = _lib.GetCoderInfo
GetCoderInfo.restype = POINTER(CoderInfo)
GetCoderInfo.argtypes = [STRING, POINTER(ExceptionInfo)]
GetCoderInfoList = _lib.GetCoderInfoList
GetCoderInfoList.restype = POINTER(POINTER(CoderInfo))
GetCoderInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
CoderComponentGenesis = _lib.CoderComponentGenesis
CoderComponentGenesis.restype = MagickBooleanType
CoderComponentGenesis.argtypes = []
ListCoderInfo = _lib.ListCoderInfo
ListCoderInfo.restype = MagickBooleanType
ListCoderInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
CoderComponentTerminus = _lib.CoderComponentTerminus
CoderComponentTerminus.restype = None
CoderComponentTerminus.argtypes = []
GetColorList = _lib.GetColorList
GetColorList.restype = POINTER(STRING)
GetColorList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
class _ColorInfo(Structure):
    pass
ColorInfo = _ColorInfo
GetColorInfo = _lib.GetColorInfo
GetColorInfo.restype = POINTER(ColorInfo)
GetColorInfo.argtypes = [STRING, POINTER(ExceptionInfo)]
GetColorInfoList = _lib.GetColorInfoList
GetColorInfoList.restype = POINTER(POINTER(ColorInfo))
GetColorInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
ColorComponentGenesis = _lib.ColorComponentGenesis
ColorComponentGenesis.restype = MagickBooleanType
ColorComponentGenesis.argtypes = []
IsColorSimilar = _lib.IsColorSimilar
IsColorSimilar.restype = MagickBooleanType
IsColorSimilar.argtypes = [POINTER(Image), POINTER(PixelPacket), POINTER(PixelPacket)]
IsImageSimilar = _lib.IsImageSimilar
IsImageSimilar.restype = MagickBooleanType
IsImageSimilar.argtypes = [POINTER(Image), POINTER(Image), POINTER(ssize_t), POINTER(ssize_t), POINTER(ExceptionInfo)]
IsMagickColorSimilar = _lib.IsMagickColorSimilar
IsMagickColorSimilar.restype = MagickBooleanType
IsMagickColorSimilar.argtypes = [POINTER(MagickPixelPacket), POINTER(MagickPixelPacket)]
IsOpacitySimilar = _lib.IsOpacitySimilar
IsOpacitySimilar.restype = MagickBooleanType
IsOpacitySimilar.argtypes = [POINTER(Image), POINTER(PixelPacket), POINTER(PixelPacket)]
ListColorInfo = _lib.ListColorInfo
ListColorInfo.restype = MagickBooleanType
ListColorInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]

# values for enumeration 'ComplianceType'
UndefinedCompliance = 0
NoCompliance = 0
SVGCompliance = 1
X11Compliance = 2
XPMCompliance = 4
AllCompliance = 2147483647
ComplianceType = c_int # enum
QueryColorCompliance = _lib.QueryColorCompliance
QueryColorCompliance.restype = MagickBooleanType
QueryColorCompliance.argtypes = [STRING, ComplianceType, POINTER(PixelPacket), POINTER(ExceptionInfo)]
QueryColorDatabase = _lib.QueryColorDatabase
QueryColorDatabase.restype = MagickBooleanType
QueryColorDatabase.argtypes = [STRING, POINTER(PixelPacket), POINTER(ExceptionInfo)]
QueryColorname = _lib.QueryColorname
QueryColorname.restype = MagickBooleanType
QueryColorname.argtypes = [POINTER(Image), POINTER(PixelPacket), ComplianceType, STRING, POINTER(ExceptionInfo)]
QueryMagickColorCompliance = _lib.QueryMagickColorCompliance
QueryMagickColorCompliance.restype = MagickBooleanType
QueryMagickColorCompliance.argtypes = [STRING, ComplianceType, POINTER(MagickPixelPacket), POINTER(ExceptionInfo)]
QueryMagickColor = _lib.QueryMagickColor
QueryMagickColor.restype = MagickBooleanType
QueryMagickColor.argtypes = [STRING, POINTER(MagickPixelPacket), POINTER(ExceptionInfo)]
QueryMagickColorname = _lib.QueryMagickColorname
QueryMagickColorname.restype = MagickBooleanType
QueryMagickColorname.argtypes = [POINTER(Image), POINTER(MagickPixelPacket), ComplianceType, STRING, POINTER(ExceptionInfo)]
ColorComponentTerminus = _lib.ColorComponentTerminus
ColorComponentTerminus.restype = None
ColorComponentTerminus.argtypes = []
ConcatenateColorComponent = _lib.ConcatenateColorComponent
ConcatenateColorComponent.restype = None
ConcatenateColorComponent.argtypes = [POINTER(MagickPixelPacket), ChannelType, ComplianceType, STRING]
GetColorTuple = _lib.GetColorTuple
GetColorTuple.restype = None
GetColorTuple.argtypes = [POINTER(MagickPixelPacket), MagickBooleanType, STRING]
AcquireImageColormap = _lib.AcquireImageColormap
AcquireImageColormap.restype = MagickBooleanType
AcquireImageColormap.argtypes = [POINTER(Image), size_t]
CycleColormapImage = _lib.CycleColormapImage
CycleColormapImage.restype = MagickBooleanType
CycleColormapImage.argtypes = [POINTER(Image), ssize_t]
SortColormapByIntensity = _lib.SortColormapByIntensity
SortColormapByIntensity.restype = MagickBooleanType
SortColormapByIntensity.argtypes = [POINTER(Image)]
RGBTransformImage = _lib.RGBTransformImage
RGBTransformImage.restype = MagickBooleanType
RGBTransformImage.argtypes = [POINTER(Image), ColorspaceType]
SetImageColorspace = _lib.SetImageColorspace
SetImageColorspace.restype = MagickBooleanType
SetImageColorspace.argtypes = [POINTER(Image), ColorspaceType]
TransformImageColorspace = _lib.TransformImageColorspace
TransformImageColorspace.restype = MagickBooleanType
TransformImageColorspace.argtypes = [POINTER(Image), ColorspaceType]
TransformRGBImage = _lib.TransformRGBImage
TransformRGBImage.restype = MagickBooleanType
TransformRGBImage.argtypes = [POINTER(Image), ColorspaceType]

# values for enumeration 'MetricType'
UndefinedMetric = 0
AbsoluteErrorMetric = 1
MeanAbsoluteErrorMetric = 2
MeanErrorPerPixelMetric = 3
MeanSquaredErrorMetric = 4
PeakAbsoluteErrorMetric = 5
PeakSignalToNoiseRatioMetric = 6
RootMeanSquaredErrorMetric = 7
NormalizedCrossCorrelationErrorMetric = 8
FuzzErrorMetric = 9
MetricType = c_int # enum
GetImageChannelDistortions = _lib.GetImageChannelDistortions
GetImageChannelDistortions.restype = POINTER(c_double)
GetImageChannelDistortions.argtypes = [POINTER(Image), POINTER(Image), MetricType, POINTER(ExceptionInfo)]
CompareImageChannels = _lib.CompareImageChannels
CompareImageChannels.restype = POINTER(Image)
CompareImageChannels.argtypes = [POINTER(Image), POINTER(Image), ChannelType, MetricType, POINTER(c_double), POINTER(ExceptionInfo)]
CompareImages = _lib.CompareImages
CompareImages.restype = POINTER(Image)
CompareImages.argtypes = [POINTER(Image), POINTER(Image), MetricType, POINTER(c_double), POINTER(ExceptionInfo)]
SimilarityImage = _lib.SimilarityImage
SimilarityImage.restype = POINTER(Image)
SimilarityImage.argtypes = [POINTER(Image), POINTER(Image), POINTER(RectangleInfo), POINTER(c_double), POINTER(ExceptionInfo)]
SimilarityMetricImage = _lib.SimilarityMetricImage
SimilarityMetricImage.restype = POINTER(Image)
SimilarityMetricImage.argtypes = [POINTER(Image), POINTER(Image), MetricType, POINTER(RectangleInfo), POINTER(c_double), POINTER(ExceptionInfo)]
GetImageChannelDistortion = _lib.GetImageChannelDistortion
GetImageChannelDistortion.restype = MagickBooleanType
GetImageChannelDistortion.argtypes = [POINTER(Image), POINTER(Image), ChannelType, MetricType, POINTER(c_double), POINTER(ExceptionInfo)]
GetImageDistortion = _lib.GetImageDistortion
GetImageDistortion.restype = MagickBooleanType
GetImageDistortion.argtypes = [POINTER(Image), POINTER(Image), MetricType, POINTER(c_double), POINTER(ExceptionInfo)]
IsImagesEqual = _lib.IsImagesEqual
IsImagesEqual.restype = MagickBooleanType
IsImagesEqual.argtypes = [POINTER(Image), POINTER(Image)]

# values for enumeration 'CompositeOperator'
UndefinedCompositeOp = 0
NoCompositeOp = 1
ModulusAddCompositeOp = 2
AtopCompositeOp = 3
BlendCompositeOp = 4
BumpmapCompositeOp = 5
ChangeMaskCompositeOp = 6
ClearCompositeOp = 7
ColorBurnCompositeOp = 8
ColorDodgeCompositeOp = 9
ColorizeCompositeOp = 10
CopyBlackCompositeOp = 11
CopyBlueCompositeOp = 12
CopyCompositeOp = 13
CopyCyanCompositeOp = 14
CopyGreenCompositeOp = 15
CopyMagentaCompositeOp = 16
CopyOpacityCompositeOp = 17
CopyRedCompositeOp = 18
CopyYellowCompositeOp = 19
DarkenCompositeOp = 20
DstAtopCompositeOp = 21
DstCompositeOp = 22
DstInCompositeOp = 23
DstOutCompositeOp = 24
DstOverCompositeOp = 25
DifferenceCompositeOp = 26
DisplaceCompositeOp = 27
DissolveCompositeOp = 28
ExclusionCompositeOp = 29
HardLightCompositeOp = 30
HueCompositeOp = 31
InCompositeOp = 32
LightenCompositeOp = 33
LinearLightCompositeOp = 34
LuminizeCompositeOp = 35
MinusDstCompositeOp = 36
ModulateCompositeOp = 37
MultiplyCompositeOp = 38
OutCompositeOp = 39
OverCompositeOp = 40
OverlayCompositeOp = 41
PlusCompositeOp = 42
ReplaceCompositeOp = 43
SaturateCompositeOp = 44
ScreenCompositeOp = 45
SoftLightCompositeOp = 46
SrcAtopCompositeOp = 47
SrcCompositeOp = 48
SrcInCompositeOp = 49
SrcOutCompositeOp = 50
SrcOverCompositeOp = 51
ModulusSubtractCompositeOp = 52
ThresholdCompositeOp = 53
XorCompositeOp = 54
DivideDstCompositeOp = 55
DistortCompositeOp = 56
BlurCompositeOp = 57
PegtopLightCompositeOp = 58
VividLightCompositeOp = 59
PinLightCompositeOp = 60
LinearDodgeCompositeOp = 61
LinearBurnCompositeOp = 62
MathematicsCompositeOp = 63
DivideSrcCompositeOp = 64
MinusSrcCompositeOp = 65
DarkenIntensityCompositeOp = 66
LightenIntensityCompositeOp = 67
CompositeOperator = c_int # enum
CompositeImage = _lib.CompositeImage
CompositeImage.restype = MagickBooleanType
CompositeImage.argtypes = [POINTER(Image), CompositeOperator, POINTER(Image), ssize_t, ssize_t]
CompositeImageChannel = _lib.CompositeImageChannel
CompositeImageChannel.restype = MagickBooleanType
CompositeImageChannel.argtypes = [POINTER(Image), ChannelType, CompositeOperator, POINTER(Image), ssize_t, ssize_t]
TextureImage = _lib.TextureImage
TextureImage.restype = MagickBooleanType
TextureImage.argtypes = [POINTER(Image), POINTER(Image)]
HuffmanDecodeImage = _lib.HuffmanDecodeImage
HuffmanDecodeImage.restype = MagickBooleanType
HuffmanDecodeImage.argtypes = [POINTER(Image)]
HuffmanEncodeImage = _lib.HuffmanEncodeImage
HuffmanEncodeImage.restype = MagickBooleanType
HuffmanEncodeImage.argtypes = [POINTER(ImageInfo), POINTER(Image), POINTER(Image)]
LZWEncodeImage = _lib.LZWEncodeImage
LZWEncodeImage.restype = MagickBooleanType
LZWEncodeImage.argtypes = [POINTER(Image), size_t, POINTER(c_ubyte)]
PackbitsEncodeImage = _lib.PackbitsEncodeImage
PackbitsEncodeImage.restype = MagickBooleanType
PackbitsEncodeImage.argtypes = [POINTER(Image), size_t, POINTER(c_ubyte)]
ZLIBEncodeImage = _lib.ZLIBEncodeImage
ZLIBEncodeImage.restype = MagickBooleanType
ZLIBEncodeImage.argtypes = [POINTER(Image), size_t, POINTER(c_ubyte)]
Ascii85Encode = _lib.Ascii85Encode
Ascii85Encode.restype = None
Ascii85Encode.argtypes = [POINTER(Image), c_ubyte]
Ascii85Flush = _lib.Ascii85Flush
Ascii85Flush.restype = None
Ascii85Flush.argtypes = [POINTER(Image)]
Ascii85Initialize = _lib.Ascii85Initialize
Ascii85Initialize.restype = None
Ascii85Initialize.argtypes = [POINTER(Image)]
GetConfigureList = _lib.GetConfigureList
GetConfigureList.restype = POINTER(STRING)
GetConfigureList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
GetConfigureOption = _lib.GetConfigureOption
GetConfigureOption.restype = STRING
GetConfigureOption.argtypes = [STRING]
class _ConfigureInfo(Structure):
    pass
ConfigureInfo = _ConfigureInfo
GetConfigureValue = _lib.GetConfigureValue
GetConfigureValue.restype = STRING
GetConfigureValue.argtypes = [POINTER(ConfigureInfo)]
GetConfigureInfo = _lib.GetConfigureInfo
GetConfigureInfo.restype = POINTER(ConfigureInfo)
GetConfigureInfo.argtypes = [STRING, POINTER(ExceptionInfo)]
GetConfigureInfoList = _lib.GetConfigureInfoList
GetConfigureInfoList.restype = POINTER(POINTER(ConfigureInfo))
GetConfigureInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
class _LinkedListInfo(Structure):
    pass
LinkedListInfo = _LinkedListInfo
DestroyConfigureOptions = _lib.DestroyConfigureOptions
DestroyConfigureOptions.restype = POINTER(LinkedListInfo)
DestroyConfigureOptions.argtypes = [POINTER(LinkedListInfo)]
GetConfigurePaths = _lib.GetConfigurePaths
GetConfigurePaths.restype = POINTER(LinkedListInfo)
GetConfigurePaths.argtypes = [STRING, POINTER(ExceptionInfo)]
GetConfigureOptions = _lib.GetConfigureOptions
GetConfigureOptions.restype = POINTER(LinkedListInfo)
GetConfigureOptions.argtypes = [STRING, POINTER(ExceptionInfo)]
ConfigureComponentGenesis = _lib.ConfigureComponentGenesis
ConfigureComponentGenesis.restype = MagickBooleanType
ConfigureComponentGenesis.argtypes = []
ListConfigureInfo = _lib.ListConfigureInfo
ListConfigureInfo.restype = MagickBooleanType
ListConfigureInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
ConfigureComponentTerminus = _lib.ConfigureComponentTerminus
ConfigureComponentTerminus.restype = None
ConfigureComponentTerminus.argtypes = []

# values for enumeration 'StorageType'
UndefinedPixel = 0
CharPixel = 1
DoublePixel = 2
FloatPixel = 3
IntegerPixel = 4
LongPixel = 5
QuantumPixel = 6
ShortPixel = 7
StorageType = c_int # enum
ConstituteImage = _lib.ConstituteImage
ConstituteImage.restype = POINTER(Image)
ConstituteImage.argtypes = [size_t, size_t, STRING, StorageType, c_void_p, POINTER(ExceptionInfo)]
PingImage = _lib.PingImage
PingImage.restype = POINTER(Image)
PingImage.argtypes = [POINTER(ImageInfo), POINTER(ExceptionInfo)]
PingImages = _lib.PingImages
PingImages.restype = POINTER(Image)
PingImages.argtypes = [POINTER(ImageInfo), POINTER(ExceptionInfo)]
ReadImage = _lib.ReadImage
ReadImage.restype = POINTER(Image)
ReadImage.argtypes = [POINTER(ImageInfo), POINTER(ExceptionInfo)]
ReadImages = _lib.ReadImages
ReadImages.restype = POINTER(Image)
ReadImages.argtypes = [POINTER(ImageInfo), POINTER(ExceptionInfo)]
ReadInlineImage = _lib.ReadInlineImage
ReadInlineImage.restype = POINTER(Image)
ReadInlineImage.argtypes = [POINTER(ImageInfo), STRING, POINTER(ExceptionInfo)]
ConstituteComponentGenesis = _lib.ConstituteComponentGenesis
ConstituteComponentGenesis.restype = MagickBooleanType
ConstituteComponentGenesis.argtypes = []
WriteImage = _lib.WriteImage
WriteImage.restype = MagickBooleanType
WriteImage.argtypes = [POINTER(ImageInfo), POINTER(Image)]
WriteImages = _lib.WriteImages
WriteImages.restype = MagickBooleanType
WriteImages.argtypes = [POINTER(ImageInfo), POINTER(Image), STRING, POINTER(ExceptionInfo)]
ConstituteComponentTerminus = _lib.ConstituteComponentTerminus
ConstituteComponentTerminus.restype = None
ConstituteComponentTerminus.argtypes = []
BorderImage = _lib.BorderImage
BorderImage.restype = POINTER(Image)
BorderImage.argtypes = [POINTER(Image), POINTER(RectangleInfo), POINTER(ExceptionInfo)]
class _FrameInfo(Structure):
    pass
FrameInfo = _FrameInfo
FrameImage = _lib.FrameImage
FrameImage.restype = POINTER(Image)
FrameImage.argtypes = [POINTER(Image), POINTER(FrameInfo), POINTER(ExceptionInfo)]
RaiseImage = _lib.RaiseImage
RaiseImage.restype = MagickBooleanType
RaiseImage.argtypes = [POINTER(Image), POINTER(RectangleInfo), MagickBooleanType]
GetDelegateCommand = _lib.GetDelegateCommand
GetDelegateCommand.restype = STRING
GetDelegateCommand.argtypes = [POINTER(ImageInfo), POINTER(Image), STRING, STRING, POINTER(ExceptionInfo)]
GetDelegateList = _lib.GetDelegateList
GetDelegateList.restype = POINTER(STRING)
GetDelegateList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
class _DelegateInfo(Structure):
    pass
DelegateInfo = _DelegateInfo
GetDelegateCommands = _lib.GetDelegateCommands
GetDelegateCommands.restype = STRING
GetDelegateCommands.argtypes = [POINTER(DelegateInfo)]
GetDelegateInfo = _lib.GetDelegateInfo
GetDelegateInfo.restype = POINTER(DelegateInfo)
GetDelegateInfo.argtypes = [STRING, STRING, POINTER(ExceptionInfo)]
GetDelegateInfoList = _lib.GetDelegateInfoList
GetDelegateInfoList.restype = POINTER(POINTER(DelegateInfo))
GetDelegateInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
GetDelegateMode = _lib.GetDelegateMode
GetDelegateMode.restype = ssize_t
GetDelegateMode.argtypes = [POINTER(DelegateInfo)]
DelegateComponentGenesis = _lib.DelegateComponentGenesis
DelegateComponentGenesis.restype = MagickBooleanType
DelegateComponentGenesis.argtypes = []
GetDelegateThreadSupport = _lib.GetDelegateThreadSupport
GetDelegateThreadSupport.restype = MagickBooleanType
GetDelegateThreadSupport.argtypes = [POINTER(DelegateInfo)]
InvokeDelegate = _lib.InvokeDelegate
InvokeDelegate.restype = MagickBooleanType
InvokeDelegate.argtypes = [POINTER(ImageInfo), POINTER(Image), STRING, STRING, POINTER(ExceptionInfo)]
ListDelegateInfo = _lib.ListDelegateInfo
ListDelegateInfo.restype = MagickBooleanType
ListDelegateInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
DelegateComponentTerminus = _lib.DelegateComponentTerminus
DelegateComponentTerminus.restype = None
DelegateComponentTerminus.argtypes = []
CloseCacheView = _lib.CloseCacheView
CloseCacheView.restype = POINTER(CacheView)
CloseCacheView.argtypes = [POINTER(CacheView)]
OpenCacheView = _lib.OpenCacheView
OpenCacheView.restype = POINTER(CacheView)
OpenCacheView.argtypes = [POINTER(Image)]
AllocateString = _lib.AllocateString
AllocateString.restype = STRING
AllocateString.argtypes = [STRING]
InterpretImageAttributes = _lib.InterpretImageAttributes
InterpretImageAttributes.restype = STRING
InterpretImageAttributes.argtypes = [POINTER(ImageInfo), POINTER(Image), STRING]
PostscriptGeometry = _lib.PostscriptGeometry
PostscriptGeometry.restype = STRING
PostscriptGeometry.argtypes = [STRING]
TranslateText = _lib.TranslateText
TranslateText.restype = STRING
TranslateText.argtypes = [POINTER(ImageInfo), POINTER(Image), STRING]
class _ImageAttribute(Structure):
    pass
ImageAttribute = _ImageAttribute
GetImageAttribute = _lib.GetImageAttribute
GetImageAttribute.restype = POINTER(ImageAttribute)
GetImageAttribute.argtypes = [POINTER(Image), STRING]
GetImageClippingPathAttribute = _lib.GetImageClippingPathAttribute
GetImageClippingPathAttribute.restype = POINTER(ImageAttribute)
GetImageClippingPathAttribute.argtypes = [POINTER(Image)]
GetNextImageAttribute = _lib.GetNextImageAttribute
GetNextImageAttribute.restype = POINTER(ImageAttribute)
GetNextImageAttribute.argtypes = [POINTER(Image)]
AcquireCacheViewIndexes = _lib.AcquireCacheViewIndexes
AcquireCacheViewIndexes.restype = POINTER(IndexPacket)
AcquireCacheViewIndexes.argtypes = [POINTER(CacheView)]
AcquireIndexes = _lib.AcquireIndexes
AcquireIndexes.restype = POINTER(IndexPacket)
AcquireIndexes.argtypes = [POINTER(Image)]
AcquirePixels = _lib.AcquirePixels
AcquirePixels.restype = POINTER(PixelPacket)
AcquirePixels.argtypes = [POINTER(Image)]
AcquireCacheViewPixels = _lib.AcquireCacheViewPixels
AcquireCacheViewPixels.restype = POINTER(PixelPacket)
AcquireCacheViewPixels.argtypes = [POINTER(CacheView), ssize_t, ssize_t, size_t, size_t, POINTER(ExceptionInfo)]
AcquireImagePixels = _lib.AcquireImagePixels
AcquireImagePixels.restype = POINTER(PixelPacket)
AcquireImagePixels.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t, POINTER(ExceptionInfo)]
OpenMagickStream = _lib.OpenMagickStream
OpenMagickStream.restype = POINTER(FILE)
OpenMagickStream.argtypes = [STRING, STRING]
AllocateImage = _lib.AllocateImage
AllocateImage.restype = POINTER(Image)
AllocateImage.argtypes = [POINTER(ImageInfo)]
AverageImages = _lib.AverageImages
AverageImages.restype = POINTER(Image)
AverageImages.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
ExtractSubimageFromImage = _lib.ExtractSubimageFromImage
ExtractSubimageFromImage.restype = POINTER(Image)
ExtractSubimageFromImage.argtypes = [POINTER(Image), POINTER(Image), POINTER(ExceptionInfo)]
GetImageFromMagickRegistry = _lib.GetImageFromMagickRegistry
GetImageFromMagickRegistry.restype = POINTER(Image)
GetImageFromMagickRegistry.argtypes = [STRING, POINTER(ssize_t), POINTER(ExceptionInfo)]
GetImageList = _lib.GetImageList
GetImageList.restype = POINTER(Image)
GetImageList.argtypes = [POINTER(Image), ssize_t, POINTER(ExceptionInfo)]
GetNextImage = _lib.GetNextImage
GetNextImage.restype = POINTER(Image)
GetNextImage.argtypes = [POINTER(Image)]
GetPreviousImage = _lib.GetPreviousImage
GetPreviousImage.restype = POINTER(Image)
GetPreviousImage.argtypes = [POINTER(Image)]
FlattenImages = _lib.FlattenImages
FlattenImages.restype = POINTER(Image)
FlattenImages.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
MaximumImages = _lib.MaximumImages
MaximumImages.restype = POINTER(Image)
MaximumImages.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
MedianFilterImage = _lib.MedianFilterImage
MedianFilterImage.restype = POINTER(Image)
MedianFilterImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
ModeImage = _lib.ModeImage
ModeImage.restype = POINTER(Image)
ModeImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
MinimumImages = _lib.MinimumImages
MinimumImages.restype = POINTER(Image)
MinimumImages.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
MosaicImages = _lib.MosaicImages
MosaicImages.restype = POINTER(Image)
MosaicImages.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
PopImageList = _lib.PopImageList
PopImageList.restype = POINTER(Image)
PopImageList.argtypes = [POINTER(POINTER(Image))]
RecolorImage = _lib.RecolorImage
RecolorImage.restype = POINTER(Image)
RecolorImage.argtypes = [POINTER(Image), size_t, POINTER(c_double), POINTER(ExceptionInfo)]
ReduceNoiseImage = _lib.ReduceNoiseImage
ReduceNoiseImage.restype = POINTER(Image)
ReduceNoiseImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
ShiftImageList = _lib.ShiftImageList
ShiftImageList.restype = POINTER(Image)
ShiftImageList.argtypes = [POINTER(POINTER(Image))]
SpliceImageList = _lib.SpliceImageList
SpliceImageList.restype = POINTER(Image)
SpliceImageList.argtypes = [POINTER(Image), ssize_t, size_t, POINTER(Image), POINTER(ExceptionInfo)]
ZoomImage = _lib.ZoomImage
ZoomImage.restype = POINTER(Image)
ZoomImage.argtypes = [POINTER(Image), size_t, size_t, POINTER(ExceptionInfo)]
GetCacheViewIndexes = _lib.GetCacheViewIndexes
GetCacheViewIndexes.restype = POINTER(IndexPacket)
GetCacheViewIndexes.argtypes = [POINTER(CacheView)]
GetIndexes = _lib.GetIndexes
GetIndexes.restype = POINTER(IndexPacket)
GetIndexes.argtypes = [POINTER(Image)]
ValidateColormapIndex = _lib.ValidateColormapIndex
ValidateColormapIndex.restype = IndexPacket
ValidateColormapIndex.argtypes = [POINTER(Image), size_t]
GetImageGeometry = _lib.GetImageGeometry
GetImageGeometry.restype = c_int
GetImageGeometry.argtypes = [POINTER(Image), STRING, c_uint, POINTER(RectangleInfo)]
ParseImageGeometry = _lib.ParseImageGeometry
ParseImageGeometry.restype = c_int
ParseImageGeometry.argtypes = [STRING, POINTER(ssize_t), POINTER(ssize_t), POINTER(size_t), POINTER(size_t)]
AcquireOneCacheViewPixel = _lib.AcquireOneCacheViewPixel
AcquireOneCacheViewPixel.restype = MagickBooleanType
AcquireOneCacheViewPixel.argtypes = [POINTER(CacheView), ssize_t, ssize_t, POINTER(PixelPacket), POINTER(ExceptionInfo)]
AcquireOneCacheViewVirtualPixel = _lib.AcquireOneCacheViewVirtualPixel
AcquireOneCacheViewVirtualPixel.restype = MagickBooleanType
AcquireOneCacheViewVirtualPixel.argtypes = [POINTER(CacheView), VirtualPixelMethod, ssize_t, ssize_t, POINTER(PixelPacket), POINTER(ExceptionInfo)]
class _QuantizeInfo(Structure):
    pass
QuantizeInfo = _QuantizeInfo
AffinityImage = _lib.AffinityImage
AffinityImage.restype = MagickBooleanType
AffinityImage.argtypes = [POINTER(QuantizeInfo), POINTER(Image), POINTER(Image)]
AffinityImages = _lib.AffinityImages
AffinityImages.restype = MagickBooleanType
AffinityImages.argtypes = [POINTER(QuantizeInfo), POINTER(Image), POINTER(Image)]
AllocateImageColormap = _lib.AllocateImageColormap
AllocateImageColormap.restype = MagickBooleanType
AllocateImageColormap.argtypes = [POINTER(Image), size_t]
ClipPathImage = _lib.ClipPathImage
ClipPathImage.restype = MagickBooleanType
ClipPathImage.argtypes = [POINTER(Image), STRING, MagickBooleanType]
CloneImageAttributes = _lib.CloneImageAttributes
CloneImageAttributes.restype = MagickBooleanType
CloneImageAttributes.argtypes = [POINTER(Image), POINTER(Image)]

# values for enumeration 'PaintMethod'
UndefinedMethod = 0
PointMethod = 1
ReplaceMethod = 2
FloodfillMethod = 3
FillToBorderMethod = 4
ResetMethod = 5
PaintMethod = c_int # enum
ColorFloodfillImage = _lib.ColorFloodfillImage
ColorFloodfillImage.restype = MagickBooleanType
ColorFloodfillImage.argtypes = [POINTER(Image), POINTER(DrawInfo), PixelPacket, ssize_t, ssize_t, PaintMethod]
DeleteImageAttribute = _lib.DeleteImageAttribute
DeleteImageAttribute.restype = MagickBooleanType
DeleteImageAttribute.argtypes = [POINTER(Image), STRING]
DeleteMagickRegistry = _lib.DeleteMagickRegistry
DeleteMagickRegistry.restype = MagickBooleanType
DeleteMagickRegistry.argtypes = [ssize_t]
DescribeImage = _lib.DescribeImage
DescribeImage.restype = MagickBooleanType
DescribeImage.argtypes = [POINTER(Image), POINTER(FILE), MagickBooleanType]
FormatImageAttribute = _lib.FormatImageAttribute
FormatImageAttribute.restype = MagickBooleanType
FormatImageAttribute.argtypes = [POINTER(Image), STRING, STRING]
class __va_list_tag(Structure):
    pass
FormatImageAttributeList = _lib.FormatImageAttributeList
FormatImageAttributeList.restype = MagickBooleanType
FormatImageAttributeList.argtypes = [POINTER(Image), STRING, STRING, POINTER(__va_list_tag)]
FormatImagePropertyList = _lib.FormatImagePropertyList
FormatImagePropertyList.restype = MagickBooleanType
FormatImagePropertyList.argtypes = [POINTER(Image), STRING, STRING, POINTER(__va_list_tag)]
FuzzyColorCompare = _lib.FuzzyColorCompare
FuzzyColorCompare.restype = MagickBooleanType
FuzzyColorCompare.argtypes = [POINTER(Image), POINTER(PixelPacket), POINTER(PixelPacket)]
FuzzyOpacityCompare = _lib.FuzzyOpacityCompare
FuzzyOpacityCompare.restype = MagickBooleanType
FuzzyOpacityCompare.argtypes = [POINTER(Image), POINTER(PixelPacket), POINTER(PixelPacket)]
LevelImageColors = _lib.LevelImageColors
LevelImageColors.restype = MagickBooleanType
LevelImageColors.argtypes = [POINTER(Image), ChannelType, POINTER(MagickPixelPacket), POINTER(MagickPixelPacket), MagickBooleanType]
MagickMonitor = _lib.MagickMonitor
MagickMonitor.restype = MagickBooleanType
MagickMonitor.argtypes = [STRING, MagickOffsetType, MagickSizeType, c_void_p]
MapImage = _lib.MapImage
MapImage.restype = MagickBooleanType
MapImage.argtypes = [POINTER(Image), POINTER(Image), MagickBooleanType]
MapImages = _lib.MapImages
MapImages.restype = MagickBooleanType
MapImages.argtypes = [POINTER(Image), POINTER(Image), MagickBooleanType]
MatteFloodfillImage = _lib.MatteFloodfillImage
MatteFloodfillImage.restype = MagickBooleanType
MatteFloodfillImage.argtypes = [POINTER(Image), PixelPacket, Quantum, ssize_t, ssize_t, PaintMethod]
OpaqueImage = _lib.OpaqueImage
OpaqueImage.restype = MagickBooleanType
OpaqueImage.argtypes = [POINTER(Image), PixelPacket, PixelPacket]
PaintFloodfillImage = _lib.PaintFloodfillImage
PaintFloodfillImage.restype = MagickBooleanType
PaintFloodfillImage.argtypes = [POINTER(Image), ChannelType, POINTER(MagickPixelPacket), ssize_t, ssize_t, POINTER(DrawInfo), PaintMethod]
PaintOpaqueImage = _lib.PaintOpaqueImage
PaintOpaqueImage.restype = MagickBooleanType
PaintOpaqueImage.argtypes = [POINTER(Image), POINTER(MagickPixelPacket), POINTER(MagickPixelPacket)]
PaintOpaqueImageChannel = _lib.PaintOpaqueImageChannel
PaintOpaqueImageChannel.restype = MagickBooleanType
PaintOpaqueImageChannel.argtypes = [POINTER(Image), ChannelType, POINTER(MagickPixelPacket), POINTER(MagickPixelPacket)]
PaintTransparentImage = _lib.PaintTransparentImage
PaintTransparentImage.restype = MagickBooleanType
PaintTransparentImage.argtypes = [POINTER(Image), POINTER(MagickPixelPacket), Quantum]

# values for enumeration 'ExceptionType'
UndefinedException = 0
WarningException = 300
ResourceLimitWarning = 300
TypeWarning = 305
OptionWarning = 310
DelegateWarning = 315
MissingDelegateWarning = 320
CorruptImageWarning = 325
FileOpenWarning = 330
BlobWarning = 335
StreamWarning = 340
CacheWarning = 345
CoderWarning = 350
FilterWarning = 352
ModuleWarning = 355
DrawWarning = 360
ImageWarning = 365
WandWarning = 370
RandomWarning = 375
XServerWarning = 380
MonitorWarning = 385
RegistryWarning = 390
ConfigureWarning = 395
PolicyWarning = 399
ErrorException = 400
ResourceLimitError = 400
TypeError = 405
OptionError = 410
DelegateError = 415
MissingDelegateError = 420
CorruptImageError = 425
FileOpenError = 430
BlobError = 435
StreamError = 440
CacheError = 445
CoderError = 450
FilterError = 452
ModuleError = 455
DrawError = 460
ImageError = 465
WandError = 470
RandomError = 475
XServerError = 480
MonitorError = 485
RegistryError = 490
ConfigureError = 495
PolicyError = 499
FatalErrorException = 700
ResourceLimitFatalError = 700
TypeFatalError = 705
OptionFatalError = 710
DelegateFatalError = 715
MissingDelegateFatalError = 720
CorruptImageFatalError = 725
FileOpenFatalError = 730
BlobFatalError = 735
StreamFatalError = 740
CacheFatalError = 745
CoderFatalError = 750
FilterFatalError = 752
ModuleFatalError = 755
DrawFatalError = 760
ImageFatalError = 765
WandFatalError = 770
RandomFatalError = 775
XServerFatalError = 780
MonitorFatalError = 785
RegistryFatalError = 790
ConfigureFatalError = 795
PolicyFatalError = 799
ExceptionType = c_int # enum
SetExceptionInfo = _lib.SetExceptionInfo
SetExceptionInfo.restype = MagickBooleanType
SetExceptionInfo.argtypes = [POINTER(ExceptionInfo), ExceptionType]
SetImageAttribute = _lib.SetImageAttribute
SetImageAttribute.restype = MagickBooleanType
SetImageAttribute.argtypes = [POINTER(Image), STRING, STRING]
SyncCacheViewPixels = _lib.SyncCacheViewPixels
SyncCacheViewPixels.restype = MagickBooleanType
SyncCacheViewPixels.argtypes = [POINTER(CacheView)]
SyncImagePixels = _lib.SyncImagePixels
SyncImagePixels.restype = MagickBooleanType
SyncImagePixels.argtypes = [POINTER(Image)]
TransparentImage = _lib.TransparentImage
TransparentImage.restype = MagickBooleanType
TransparentImage.argtypes = [POINTER(Image), PixelPacket, Quantum]
AcquireOneMagickPixel = _lib.AcquireOneMagickPixel
AcquireOneMagickPixel.restype = MagickPixelPacket
AcquireOneMagickPixel.argtypes = [POINTER(Image), ssize_t, ssize_t, POINTER(ExceptionInfo)]
MonitorHandler = CFUNCTYPE(MagickBooleanType, STRING, MagickOffsetType, MagickSizeType, POINTER(ExceptionInfo))
GetMonitorHandler = _lib.GetMonitorHandler
GetMonitorHandler.restype = MonitorHandler
GetMonitorHandler.argtypes = []
SetMonitorHandler = _lib.SetMonitorHandler
SetMonitorHandler.restype = MonitorHandler
SetMonitorHandler.argtypes = [MonitorHandler]
SizeBlob = _lib.SizeBlob
SizeBlob.restype = MagickOffsetType
SizeBlob.argtypes = [POINTER(Image)]

# values for enumeration 'InterpolatePixelMethod'
UndefinedInterpolatePixel = 0
AverageInterpolatePixel = 1
BicubicInterpolatePixel = 2
BilinearInterpolatePixel = 3
FilterInterpolatePixel = 4
IntegerInterpolatePixel = 5
MeshInterpolatePixel = 6
NearestNeighborInterpolatePixel = 7
SplineInterpolatePixel = 8
InterpolatePixelMethod = c_int # enum
InterpolatePixelColor = _lib.InterpolatePixelColor
InterpolatePixelColor.restype = MagickPixelPacket
InterpolatePixelColor.argtypes = [POINTER(Image), POINTER(CacheView), InterpolatePixelMethod, c_double, c_double, POINTER(ExceptionInfo)]
MagickStatusType = c_uint
ParseSizeGeometry = _lib.ParseSizeGeometry
ParseSizeGeometry.restype = MagickStatusType
ParseSizeGeometry.argtypes = [POINTER(Image), STRING, POINTER(RectangleInfo)]
AcquireOnePixel = _lib.AcquireOnePixel
AcquireOnePixel.restype = PixelPacket
AcquireOnePixel.argtypes = [POINTER(Image), ssize_t, ssize_t, POINTER(ExceptionInfo)]
AcquireOneVirtualPixel = _lib.AcquireOneVirtualPixel
AcquireOneVirtualPixel.restype = PixelPacket
AcquireOneVirtualPixel.argtypes = [POINTER(Image), VirtualPixelMethod, ssize_t, ssize_t, POINTER(ExceptionInfo)]
GetCacheView = _lib.GetCacheView
GetCacheView.restype = POINTER(PixelPacket)
GetCacheView.argtypes = [POINTER(CacheView), ssize_t, ssize_t, size_t, size_t]
GetCacheViewPixels = _lib.GetCacheViewPixels
GetCacheViewPixels.restype = POINTER(PixelPacket)
GetCacheViewPixels.argtypes = [POINTER(CacheView), ssize_t, ssize_t, size_t, size_t]
GetImagePixels = _lib.GetImagePixels
GetImagePixels.restype = POINTER(PixelPacket)
GetImagePixels.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t]
GetOnePixel = _lib.GetOnePixel
GetOnePixel.restype = PixelPacket
GetOnePixel.argtypes = [POINTER(Image), ssize_t, ssize_t]
GetPixels = _lib.GetPixels
GetPixels.restype = POINTER(PixelPacket)
GetPixels.argtypes = [POINTER(Image)]
SetCacheViewPixels = _lib.SetCacheViewPixels
SetCacheViewPixels.restype = POINTER(PixelPacket)
SetCacheViewPixels.argtypes = [POINTER(CacheView), ssize_t, ssize_t, size_t, size_t]
SetImagePixels = _lib.SetImagePixels
SetImagePixels.restype = POINTER(PixelPacket)
SetImagePixels.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t]
GetImageListSize = _lib.GetImageListSize
GetImageListSize.restype = size_t
GetImageListSize.argtypes = [POINTER(Image)]

# values for enumeration 'QuantumType'
UndefinedQuantum = 0
AlphaQuantum = 1
BlackQuantum = 2
BlueQuantum = 3
CMYKAQuantum = 4
CMYKQuantum = 5
CyanQuantum = 6
GrayAlphaQuantum = 7
GrayQuantum = 8
GreenQuantum = 9
IndexAlphaQuantum = 10
IndexQuantum = 11
MagentaQuantum = 12
OpacityQuantum = 13
RedQuantum = 14
RGBAQuantum = 15
BGRAQuantum = 16
RGBOQuantum = 17
RGBQuantum = 18
YellowQuantum = 19
GrayPadQuantum = 20
RGBPadQuantum = 21
CbYCrYQuantum = 22
CbYCrQuantum = 23
CbYCrAQuantum = 24
CMYKOQuantum = 25
BGRQuantum = 26
BGROQuantum = 27
QuantumType = c_int # enum
PopImagePixels = _lib.PopImagePixels
PopImagePixels.restype = size_t
PopImagePixels.argtypes = [POINTER(Image), QuantumType, POINTER(c_ubyte)]
PushImagePixels = _lib.PushImagePixels
PushImagePixels.restype = size_t
PushImagePixels.argtypes = [POINTER(Image), QuantumType, POINTER(c_ubyte)]
FormatMagickString = _lib.FormatMagickString
FormatMagickString.restype = ssize_t
FormatMagickString.argtypes = [STRING, size_t, STRING]
FormatMagickStringList = _lib.FormatMagickStringList
FormatMagickStringList.restype = ssize_t
FormatMagickStringList.argtypes = [STRING, size_t, STRING, POINTER(__va_list_tag)]
GetImageListIndex = _lib.GetImageListIndex
GetImageListIndex.restype = ssize_t
GetImageListIndex.argtypes = [POINTER(Image)]

# values for enumeration 'RegistryType'
UndefinedRegistryType = 0
ImageRegistryType = 1
ImageInfoRegistryType = 2
StringRegistryType = 3
RegistryType = c_int # enum
SetMagickRegistry = _lib.SetMagickRegistry
SetMagickRegistry.restype = ssize_t
SetMagickRegistry.argtypes = [RegistryType, c_void_p, size_t, POINTER(ExceptionInfo)]
ChannelImage = _lib.ChannelImage
ChannelImage.restype = c_uint
ChannelImage.argtypes = [POINTER(Image), ChannelType]
ChannelThresholdImage = _lib.ChannelThresholdImage
ChannelThresholdImage.restype = c_uint
ChannelThresholdImage.argtypes = [POINTER(Image), STRING]
DispatchImage = _lib.DispatchImage
DispatchImage.restype = c_uint
DispatchImage.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t, STRING, StorageType, c_void_p, POINTER(ExceptionInfo)]
FuzzyColorMatch = _lib.FuzzyColorMatch
FuzzyColorMatch.restype = c_uint
FuzzyColorMatch.argtypes = [POINTER(PixelPacket), POINTER(PixelPacket), c_double]
GetNumberScenes = _lib.GetNumberScenes
GetNumberScenes.restype = c_uint
GetNumberScenes.argtypes = [POINTER(Image)]
GetMagickGeometry = _lib.GetMagickGeometry
GetMagickGeometry.restype = c_uint
GetMagickGeometry.argtypes = [STRING, POINTER(ssize_t), POINTER(ssize_t), POINTER(size_t), POINTER(size_t)]
IsSubimage = _lib.IsSubimage
IsSubimage.restype = c_uint
IsSubimage.argtypes = [STRING, c_uint]
PushImageList = _lib.PushImageList
PushImageList.restype = c_uint
PushImageList.argtypes = [POINTER(POINTER(Image)), POINTER(Image), POINTER(ExceptionInfo)]
QuantizationError = _lib.QuantizationError
QuantizationError.restype = c_uint
QuantizationError.argtypes = [POINTER(Image)]
RandomChannelThresholdImage = _lib.RandomChannelThresholdImage
RandomChannelThresholdImage.restype = c_uint
RandomChannelThresholdImage.argtypes = [POINTER(Image), STRING, STRING, POINTER(ExceptionInfo)]
SetImageList = _lib.SetImageList
SetImageList.restype = c_uint
SetImageList.argtypes = [POINTER(POINTER(Image)), POINTER(Image), ssize_t, POINTER(ExceptionInfo)]
TransformColorspace = _lib.TransformColorspace
TransformColorspace.restype = c_uint
TransformColorspace.argtypes = [POINTER(Image), ColorspaceType]
ThresholdImage = _lib.ThresholdImage
ThresholdImage.restype = c_uint
ThresholdImage.argtypes = [POINTER(Image), c_double]
ThresholdImageChannel = _lib.ThresholdImageChannel
ThresholdImageChannel.restype = c_uint
ThresholdImageChannel.argtypes = [POINTER(Image), STRING]
UnshiftImageList = _lib.UnshiftImageList
UnshiftImageList.restype = c_uint
UnshiftImageList.argtypes = [POINTER(POINTER(Image)), POINTER(Image), POINTER(ExceptionInfo)]
AcquireMemory = _lib.AcquireMemory
AcquireMemory.restype = c_void_p
AcquireMemory.argtypes = [size_t]
AllocateNextImage = _lib.AllocateNextImage
AllocateNextImage.restype = None
AllocateNextImage.argtypes = [POINTER(ImageInfo), POINTER(Image)]
CloneMemory = _lib.CloneMemory
CloneMemory.restype = c_void_p
CloneMemory.argtypes = [c_void_p, c_void_p, size_t]
DestroyConstitute = _lib.DestroyConstitute
DestroyConstitute.restype = None
DestroyConstitute.argtypes = []
DestroyImageAttributes = _lib.DestroyImageAttributes
DestroyImageAttributes.restype = None
DestroyImageAttributes.argtypes = [POINTER(Image)]
DestroyImages = _lib.DestroyImages
DestroyImages.restype = None
DestroyImages.argtypes = [POINTER(Image)]
DestroyMagick = _lib.DestroyMagick
DestroyMagick.restype = None
DestroyMagick.argtypes = []
DestroyMagickRegistry = _lib.DestroyMagickRegistry
DestroyMagickRegistry.restype = None
DestroyMagickRegistry.argtypes = []
GetConfigureBlob = _lib.GetConfigureBlob
GetConfigureBlob.restype = c_void_p
GetConfigureBlob.argtypes = [STRING, STRING, POINTER(size_t), POINTER(ExceptionInfo)]
GetMagickRegistry = _lib.GetMagickRegistry
GetMagickRegistry.restype = c_void_p
GetMagickRegistry.argtypes = [ssize_t, POINTER(RegistryType), POINTER(size_t), POINTER(ExceptionInfo)]
class _AffineMatrix(Structure):
    pass
AffineMatrix = _AffineMatrix
IdentityAffine = _lib.IdentityAffine
IdentityAffine.restype = None
IdentityAffine.argtypes = [POINTER(AffineMatrix)]
LiberateMemory = _lib.LiberateMemory
LiberateMemory.restype = None
LiberateMemory.argtypes = [POINTER(c_void_p)]
class SemaphoreInfo(Structure):
    pass
LiberateSemaphoreInfo = _lib.LiberateSemaphoreInfo
LiberateSemaphoreInfo.restype = None
LiberateSemaphoreInfo.argtypes = [POINTER(POINTER(SemaphoreInfo))]
FormatString = _lib.FormatString
FormatString.restype = None
FormatString.argtypes = [STRING, STRING]
FormatStringList = _lib.FormatStringList
FormatStringList.restype = None
FormatStringList.argtypes = [STRING, STRING, POINTER(__va_list_tag)]
HSLTransform = _lib.HSLTransform
HSLTransform.restype = None
HSLTransform.argtypes = [c_double, c_double, c_double, POINTER(Quantum), POINTER(Quantum), POINTER(Quantum)]
InitializeMagick = _lib.InitializeMagick
InitializeMagick.restype = None
InitializeMagick.argtypes = [STRING]
MagickIncarnate = _lib.MagickIncarnate
MagickIncarnate.restype = None
MagickIncarnate.argtypes = [STRING]
ReacquireMemory = _lib.ReacquireMemory
ReacquireMemory.restype = None
ReacquireMemory.argtypes = [POINTER(c_void_p), size_t]
ResetImageAttributeIterator = _lib.ResetImageAttributeIterator
ResetImageAttributeIterator.restype = None
ResetImageAttributeIterator.argtypes = [POINTER(Image)]
SetCacheThreshold = _lib.SetCacheThreshold
SetCacheThreshold.restype = None
SetCacheThreshold.argtypes = [size_t]
SetImage = _lib.SetImage
SetImage.restype = None
SetImage.argtypes = [POINTER(Image), Quantum]
Strip = _lib.Strip
Strip.restype = None
Strip.argtypes = [STRING]
TemporaryFilename = _lib.TemporaryFilename
TemporaryFilename.restype = None
TemporaryFilename.argtypes = [STRING]
TransformHSL = _lib.TransformHSL
TransformHSL.restype = None
TransformHSL.argtypes = [Quantum, Quantum, Quantum, POINTER(c_double), POINTER(c_double), POINTER(c_double)]
DisplayImages = _lib.DisplayImages
DisplayImages.restype = MagickBooleanType
DisplayImages.argtypes = [POINTER(ImageInfo), POINTER(Image)]
RemoteDisplayCommand = _lib.RemoteDisplayCommand
RemoteDisplayCommand.restype = MagickBooleanType
RemoteDisplayCommand.argtypes = [POINTER(ImageInfo), STRING, STRING, POINTER(ExceptionInfo)]
AffineTransformImage = _lib.AffineTransformImage
AffineTransformImage.restype = POINTER(Image)
AffineTransformImage.argtypes = [POINTER(Image), POINTER(AffineMatrix), POINTER(ExceptionInfo)]

# values for enumeration 'DistortImageMethod'
UndefinedDistortion = 0
AffineDistortion = 1
AffineProjectionDistortion = 2
ScaleRotateTranslateDistortion = 3
PerspectiveDistortion = 4
PerspectiveProjectionDistortion = 5
BilinearForwardDistortion = 6
BilinearDistortion = 6
BilinearReverseDistortion = 7
PolynomialDistortion = 8
ArcDistortion = 9
PolarDistortion = 10
DePolarDistortion = 11
Cylinder2PlaneDistortion = 12
Plane2CylinderDistortion = 13
BarrelDistortion = 14
BarrelInverseDistortion = 15
ShepardsDistortion = 16
ResizeDistortion = 17
SentinelDistortion = 18
DistortImageMethod = c_int # enum
DistortImage = _lib.DistortImage
DistortImage.restype = POINTER(Image)
DistortImage.argtypes = [POINTER(Image), DistortImageMethod, size_t, POINTER(c_double), MagickBooleanType, POINTER(ExceptionInfo)]
DistortResizeImage = _lib.DistortResizeImage
DistortResizeImage.restype = POINTER(Image)
DistortResizeImage.argtypes = [POINTER(Image), size_t, size_t, POINTER(ExceptionInfo)]
RotateImage = _lib.RotateImage
RotateImage.restype = POINTER(Image)
RotateImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]

# values for enumeration 'SparseColorMethod'
UndefinedColorInterpolate = 0
BarycentricColorInterpolate = 1
BilinearColorInterpolate = 7
PolynomialColorInterpolate = 8
ShepardsColorInterpolate = 16
VoronoiColorInterpolate = 18
InverseColorInterpolate = 19
SparseColorMethod = c_int # enum
SparseColorImage = _lib.SparseColorImage
SparseColorImage.restype = POINTER(Image)
SparseColorImage.argtypes = [POINTER(Image), ChannelType, SparseColorMethod, size_t, POINTER(c_double), POINTER(ExceptionInfo)]
AcquireDrawInfo = _lib.AcquireDrawInfo
AcquireDrawInfo.restype = POINTER(DrawInfo)
AcquireDrawInfo.argtypes = []
CloneDrawInfo = _lib.CloneDrawInfo
CloneDrawInfo.restype = POINTER(DrawInfo)
CloneDrawInfo.argtypes = [POINTER(ImageInfo), POINTER(DrawInfo)]
DestroyDrawInfo = _lib.DestroyDrawInfo
DestroyDrawInfo.restype = POINTER(DrawInfo)
DestroyDrawInfo.argtypes = [POINTER(DrawInfo)]
DrawAffineImage = _lib.DrawAffineImage
DrawAffineImage.restype = MagickBooleanType
DrawAffineImage.argtypes = [POINTER(Image), POINTER(Image), POINTER(AffineMatrix)]
DrawClipPath = _lib.DrawClipPath
DrawClipPath.restype = MagickBooleanType
DrawClipPath.argtypes = [POINTER(Image), POINTER(DrawInfo), STRING]
DrawGradientImage = _lib.DrawGradientImage
DrawGradientImage.restype = MagickBooleanType
DrawGradientImage.argtypes = [POINTER(Image), POINTER(DrawInfo)]
DrawImage = _lib.DrawImage
DrawImage.restype = MagickBooleanType
DrawImage.argtypes = [POINTER(Image), POINTER(DrawInfo)]
DrawPatternPath = _lib.DrawPatternPath
DrawPatternPath.restype = MagickBooleanType
DrawPatternPath.argtypes = [POINTER(Image), POINTER(DrawInfo), STRING, POINTER(POINTER(Image))]
class _PrimitiveInfo(Structure):
    pass
PrimitiveInfo = _PrimitiveInfo
DrawPrimitive = _lib.DrawPrimitive
DrawPrimitive.restype = MagickBooleanType
DrawPrimitive.argtypes = [POINTER(Image), POINTER(DrawInfo), POINTER(PrimitiveInfo)]
GetAffineMatrix = _lib.GetAffineMatrix
GetAffineMatrix.restype = None
GetAffineMatrix.argtypes = [POINTER(AffineMatrix)]
GetDrawInfo = _lib.GetDrawInfo
GetDrawInfo.restype = None
GetDrawInfo.argtypes = [POINTER(ImageInfo), POINTER(DrawInfo)]
AdaptiveBlurImage = _lib.AdaptiveBlurImage
AdaptiveBlurImage.restype = POINTER(Image)
AdaptiveBlurImage.argtypes = [POINTER(Image), c_double, c_double, POINTER(ExceptionInfo)]
AdaptiveBlurImageChannel = _lib.AdaptiveBlurImageChannel
AdaptiveBlurImageChannel.restype = POINTER(Image)
AdaptiveBlurImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, POINTER(ExceptionInfo)]
AdaptiveSharpenImage = _lib.AdaptiveSharpenImage
AdaptiveSharpenImage.restype = POINTER(Image)
AdaptiveSharpenImage.argtypes = [POINTER(Image), c_double, c_double, POINTER(ExceptionInfo)]
AdaptiveSharpenImageChannel = _lib.AdaptiveSharpenImageChannel
AdaptiveSharpenImageChannel.restype = POINTER(Image)
AdaptiveSharpenImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, POINTER(ExceptionInfo)]
BlurImage = _lib.BlurImage
BlurImage.restype = POINTER(Image)
BlurImage.argtypes = [POINTER(Image), c_double, c_double, POINTER(ExceptionInfo)]
BlurImageChannel = _lib.BlurImageChannel
BlurImageChannel.restype = POINTER(Image)
BlurImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, POINTER(ExceptionInfo)]
ConvolveImage = _lib.ConvolveImage
ConvolveImage.restype = POINTER(Image)
ConvolveImage.argtypes = [POINTER(Image), size_t, POINTER(c_double), POINTER(ExceptionInfo)]
ConvolveImageChannel = _lib.ConvolveImageChannel
ConvolveImageChannel.restype = POINTER(Image)
ConvolveImageChannel.argtypes = [POINTER(Image), ChannelType, size_t, POINTER(c_double), POINTER(ExceptionInfo)]
DespeckleImage = _lib.DespeckleImage
DespeckleImage.restype = POINTER(Image)
DespeckleImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
EdgeImage = _lib.EdgeImage
EdgeImage.restype = POINTER(Image)
EdgeImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
EmbossImage = _lib.EmbossImage
EmbossImage.restype = POINTER(Image)
EmbossImage.argtypes = [POINTER(Image), c_double, c_double, POINTER(ExceptionInfo)]
FilterImage = _lib.FilterImage
FilterImage.restype = POINTER(Image)
FilterImage.argtypes = [POINTER(Image), POINTER(KernelInfo), POINTER(ExceptionInfo)]
FilterImageChannel = _lib.FilterImageChannel
FilterImageChannel.restype = POINTER(Image)
FilterImageChannel.argtypes = [POINTER(Image), ChannelType, POINTER(KernelInfo), POINTER(ExceptionInfo)]
GaussianBlurImage = _lib.GaussianBlurImage
GaussianBlurImage.restype = POINTER(Image)
GaussianBlurImage.argtypes = [POINTER(Image), c_double, c_double, POINTER(ExceptionInfo)]
GaussianBlurImageChannel = _lib.GaussianBlurImageChannel
GaussianBlurImageChannel.restype = POINTER(Image)
GaussianBlurImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, POINTER(ExceptionInfo)]
MotionBlurImage = _lib.MotionBlurImage
MotionBlurImage.restype = POINTER(Image)
MotionBlurImage.argtypes = [POINTER(Image), c_double, c_double, c_double, POINTER(ExceptionInfo)]
MotionBlurImageChannel = _lib.MotionBlurImageChannel
MotionBlurImageChannel.restype = POINTER(Image)
MotionBlurImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, c_double, POINTER(ExceptionInfo)]

# values for enumeration 'PreviewType'
UndefinedPreview = 0
RotatePreview = 1
ShearPreview = 2
RollPreview = 3
HuePreview = 4
SaturationPreview = 5
BrightnessPreview = 6
GammaPreview = 7
SpiffPreview = 8
DullPreview = 9
GrayscalePreview = 10
QuantizePreview = 11
DespecklePreview = 12
ReduceNoisePreview = 13
AddNoisePreview = 14
SharpenPreview = 15
BlurPreview = 16
ThresholdPreview = 17
EdgeDetectPreview = 18
SpreadPreview = 19
SolarizePreview = 20
ShadePreview = 21
RaisePreview = 22
SegmentPreview = 23
SwirlPreview = 24
ImplodePreview = 25
WavePreview = 26
OilPaintPreview = 27
CharcoalDrawingPreview = 28
JPEGPreview = 29
PreviewType = c_int # enum
PreviewImage = _lib.PreviewImage
PreviewImage.restype = POINTER(Image)
PreviewImage.argtypes = [POINTER(Image), PreviewType, POINTER(ExceptionInfo)]
RadialBlurImage = _lib.RadialBlurImage
RadialBlurImage.restype = POINTER(Image)
RadialBlurImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
RadialBlurImageChannel = _lib.RadialBlurImageChannel
RadialBlurImageChannel.restype = POINTER(Image)
RadialBlurImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, POINTER(ExceptionInfo)]
SelectiveBlurImage = _lib.SelectiveBlurImage
SelectiveBlurImage.restype = POINTER(Image)
SelectiveBlurImage.argtypes = [POINTER(Image), c_double, c_double, c_double, POINTER(ExceptionInfo)]
SelectiveBlurImageChannel = _lib.SelectiveBlurImageChannel
SelectiveBlurImageChannel.restype = POINTER(Image)
SelectiveBlurImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, c_double, POINTER(ExceptionInfo)]
ShadeImage = _lib.ShadeImage
ShadeImage.restype = POINTER(Image)
ShadeImage.argtypes = [POINTER(Image), MagickBooleanType, c_double, c_double, POINTER(ExceptionInfo)]
SharpenImage = _lib.SharpenImage
SharpenImage.restype = POINTER(Image)
SharpenImage.argtypes = [POINTER(Image), c_double, c_double, POINTER(ExceptionInfo)]
SharpenImageChannel = _lib.SharpenImageChannel
SharpenImageChannel.restype = POINTER(Image)
SharpenImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, POINTER(ExceptionInfo)]
SpreadImage = _lib.SpreadImage
SpreadImage.restype = POINTER(Image)
SpreadImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]

# values for enumeration 'StatisticType'
UndefinedStatistic = 0
GradientStatistic = 1
MaximumStatistic = 2
MeanStatistic = 3
MedianStatistic = 4
MinimumStatistic = 5
ModeStatistic = 6
NonpeakStatistic = 7
StandardDeviationStatistic = 8
StatisticType = c_int # enum
StatisticImage = _lib.StatisticImage
StatisticImage.restype = POINTER(Image)
StatisticImage.argtypes = [POINTER(Image), StatisticType, size_t, size_t, POINTER(ExceptionInfo)]
StatisticImageChannel = _lib.StatisticImageChannel
StatisticImageChannel.restype = POINTER(Image)
StatisticImageChannel.argtypes = [POINTER(Image), ChannelType, StatisticType, size_t, size_t, POINTER(ExceptionInfo)]
UnsharpMaskImage = _lib.UnsharpMaskImage
UnsharpMaskImage.restype = POINTER(Image)
UnsharpMaskImage.argtypes = [POINTER(Image), c_double, c_double, c_double, c_double, POINTER(ExceptionInfo)]
UnsharpMaskImageChannel = _lib.UnsharpMaskImageChannel
UnsharpMaskImageChannel.restype = POINTER(Image)
UnsharpMaskImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, c_double, c_double, POINTER(ExceptionInfo)]
AutoGammaImage = _lib.AutoGammaImage
AutoGammaImage.restype = MagickBooleanType
AutoGammaImage.argtypes = [POINTER(Image)]
AutoGammaImageChannel = _lib.AutoGammaImageChannel
AutoGammaImageChannel.restype = MagickBooleanType
AutoGammaImageChannel.argtypes = [POINTER(Image), ChannelType]
AutoLevelImage = _lib.AutoLevelImage
AutoLevelImage.restype = MagickBooleanType
AutoLevelImage.argtypes = [POINTER(Image)]
AutoLevelImageChannel = _lib.AutoLevelImageChannel
AutoLevelImageChannel.restype = MagickBooleanType
AutoLevelImageChannel.argtypes = [POINTER(Image), ChannelType]
BrightnessContrastImage = _lib.BrightnessContrastImage
BrightnessContrastImage.restype = MagickBooleanType
BrightnessContrastImage.argtypes = [POINTER(Image), c_double, c_double]
BrightnessContrastImageChannel = _lib.BrightnessContrastImageChannel
BrightnessContrastImageChannel.restype = MagickBooleanType
BrightnessContrastImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double]
ClutImage = _lib.ClutImage
ClutImage.restype = MagickBooleanType
ClutImage.argtypes = [POINTER(Image), POINTER(Image)]
ClutImageChannel = _lib.ClutImageChannel
ClutImageChannel.restype = MagickBooleanType
ClutImageChannel.argtypes = [POINTER(Image), ChannelType, POINTER(Image)]
ColorDecisionListImage = _lib.ColorDecisionListImage
ColorDecisionListImage.restype = MagickBooleanType
ColorDecisionListImage.argtypes = [POINTER(Image), STRING]
ContrastImage = _lib.ContrastImage
ContrastImage.restype = MagickBooleanType
ContrastImage.argtypes = [POINTER(Image), MagickBooleanType]
ContrastStretchImage = _lib.ContrastStretchImage
ContrastStretchImage.restype = MagickBooleanType
ContrastStretchImage.argtypes = [POINTER(Image), STRING]
ContrastStretchImageChannel = _lib.ContrastStretchImageChannel
ContrastStretchImageChannel.restype = MagickBooleanType
ContrastStretchImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double]
EqualizeImage = _lib.EqualizeImage
EqualizeImage.restype = MagickBooleanType
EqualizeImage.argtypes = [POINTER(Image)]
EqualizeImageChannel = _lib.EqualizeImageChannel
EqualizeImageChannel.restype = MagickBooleanType
EqualizeImageChannel.argtypes = [POINTER(Image), ChannelType]
GammaImage = _lib.GammaImage
GammaImage.restype = MagickBooleanType
GammaImage.argtypes = [POINTER(Image), STRING]
GammaImageChannel = _lib.GammaImageChannel
GammaImageChannel.restype = MagickBooleanType
GammaImageChannel.argtypes = [POINTER(Image), ChannelType, c_double]
HaldClutImage = _lib.HaldClutImage
HaldClutImage.restype = MagickBooleanType
HaldClutImage.argtypes = [POINTER(Image), POINTER(Image)]
HaldClutImageChannel = _lib.HaldClutImageChannel
HaldClutImageChannel.restype = MagickBooleanType
HaldClutImageChannel.argtypes = [POINTER(Image), ChannelType, POINTER(Image)]
LevelImage = _lib.LevelImage
LevelImage.restype = MagickBooleanType
LevelImage.argtypes = [POINTER(Image), STRING]
LevelImageChannel = _lib.LevelImageChannel
LevelImageChannel.restype = MagickBooleanType
LevelImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, c_double]
LevelizeImage = _lib.LevelizeImage
LevelizeImage.restype = MagickBooleanType
LevelizeImage.argtypes = [POINTER(Image), c_double, c_double, c_double]
LevelizeImageChannel = _lib.LevelizeImageChannel
LevelizeImageChannel.restype = MagickBooleanType
LevelizeImageChannel.argtypes = [POINTER(Image), ChannelType, c_double, c_double, c_double]
LevelColorsImage = _lib.LevelColorsImage
LevelColorsImage.restype = MagickBooleanType
LevelColorsImage.argtypes = [POINTER(Image), POINTER(MagickPixelPacket), POINTER(MagickPixelPacket), MagickBooleanType]
LevelColorsImageChannel = _lib.LevelColorsImageChannel
LevelColorsImageChannel.restype = MagickBooleanType
LevelColorsImageChannel.argtypes = [POINTER(Image), ChannelType, POINTER(MagickPixelPacket), POINTER(MagickPixelPacket), MagickBooleanType]
LinearStretchImage = _lib.LinearStretchImage
LinearStretchImage.restype = MagickBooleanType
LinearStretchImage.argtypes = [POINTER(Image), c_double, c_double]
ModulateImage = _lib.ModulateImage
ModulateImage.restype = MagickBooleanType
ModulateImage.argtypes = [POINTER(Image), STRING]
NegateImage = _lib.NegateImage
NegateImage.restype = MagickBooleanType
NegateImage.argtypes = [POINTER(Image), MagickBooleanType]
NegateImageChannel = _lib.NegateImageChannel
NegateImageChannel.restype = MagickBooleanType
NegateImageChannel.argtypes = [POINTER(Image), ChannelType, MagickBooleanType]
NormalizeImage = _lib.NormalizeImage
NormalizeImage.restype = MagickBooleanType
NormalizeImage.argtypes = [POINTER(Image)]
NormalizeImageChannel = _lib.NormalizeImageChannel
NormalizeImageChannel.restype = MagickBooleanType
NormalizeImageChannel.argtypes = [POINTER(Image), ChannelType]
SigmoidalContrastImage = _lib.SigmoidalContrastImage
SigmoidalContrastImage.restype = MagickBooleanType
SigmoidalContrastImage.argtypes = [POINTER(Image), MagickBooleanType, STRING]
SigmoidalContrastImageChannel = _lib.SigmoidalContrastImageChannel
SigmoidalContrastImageChannel.restype = MagickBooleanType
SigmoidalContrastImageChannel.argtypes = [POINTER(Image), ChannelType, MagickBooleanType, c_double, c_double]
EnhanceImage = _lib.EnhanceImage
EnhanceImage.restype = POINTER(Image)
EnhanceImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
GetExceptionMessage = _lib.GetExceptionMessage
GetExceptionMessage.restype = STRING
GetExceptionMessage.argtypes = [c_int]
GetLocaleExceptionMessage = _lib.GetLocaleExceptionMessage
GetLocaleExceptionMessage.restype = STRING
GetLocaleExceptionMessage.argtypes = [ExceptionType, STRING]
ErrorHandler = CFUNCTYPE(None, ExceptionType, STRING, STRING)
SetErrorHandler = _lib.SetErrorHandler
SetErrorHandler.restype = ErrorHandler
SetErrorHandler.argtypes = [ErrorHandler]
AcquireExceptionInfo = _lib.AcquireExceptionInfo
AcquireExceptionInfo.restype = POINTER(ExceptionInfo)
AcquireExceptionInfo.argtypes = []
DestroyExceptionInfo = _lib.DestroyExceptionInfo
DestroyExceptionInfo.restype = POINTER(ExceptionInfo)
DestroyExceptionInfo.argtypes = [POINTER(ExceptionInfo)]
FatalErrorHandler = CFUNCTYPE(None, ExceptionType, STRING, STRING)
SetFatalErrorHandler = _lib.SetFatalErrorHandler
SetFatalErrorHandler.restype = FatalErrorHandler
SetFatalErrorHandler.argtypes = [FatalErrorHandler]
ThrowException = _lib.ThrowException
ThrowException.restype = MagickBooleanType
ThrowException.argtypes = [POINTER(ExceptionInfo), ExceptionType, STRING, STRING]
ThrowMagickException = _lib.ThrowMagickException
ThrowMagickException.restype = MagickBooleanType
ThrowMagickException.argtypes = [POINTER(ExceptionInfo), STRING, STRING, size_t, ExceptionType, STRING, STRING]
ThrowMagickExceptionList = _lib.ThrowMagickExceptionList
ThrowMagickExceptionList.restype = MagickBooleanType
ThrowMagickExceptionList.argtypes = [POINTER(ExceptionInfo), STRING, STRING, size_t, ExceptionType, STRING, STRING, POINTER(__va_list_tag)]
CatchException = _lib.CatchException
CatchException.restype = None
CatchException.argtypes = [POINTER(ExceptionInfo)]
ClearMagickException = _lib.ClearMagickException
ClearMagickException.restype = None
ClearMagickException.argtypes = [POINTER(ExceptionInfo)]
GetExceptionInfo = _lib.GetExceptionInfo
GetExceptionInfo.restype = None
GetExceptionInfo.argtypes = [POINTER(ExceptionInfo)]
InheritException = _lib.InheritException
InheritException.restype = None
InheritException.argtypes = [POINTER(ExceptionInfo), POINTER(ExceptionInfo)]
MagickError = _lib.MagickError
MagickError.restype = None
MagickError.argtypes = [ExceptionType, STRING, STRING]
MagickFatalError = _lib.MagickFatalError
MagickFatalError.restype = None
MagickFatalError.argtypes = [ExceptionType, STRING, STRING]
MagickWarning = _lib.MagickWarning
MagickWarning.restype = None
MagickWarning.argtypes = [ExceptionType, STRING, STRING]
WarningHandler = CFUNCTYPE(None, ExceptionType, STRING, STRING)
SetWarningHandler = _lib.SetWarningHandler
SetWarningHandler.restype = WarningHandler
SetWarningHandler.argtypes = [WarningHandler]
class _ChannelFeatures(Structure):
    pass
ChannelFeatures = _ChannelFeatures
GetImageChannelFeatures = _lib.GetImageChannelFeatures
GetImageChannelFeatures.restype = POINTER(ChannelFeatures)
GetImageChannelFeatures.argtypes = [POINTER(Image), size_t, POINTER(ExceptionInfo)]
ForwardFourierTransformImage = _lib.ForwardFourierTransformImage
ForwardFourierTransformImage.restype = POINTER(Image)
ForwardFourierTransformImage.argtypes = [POINTER(Image), MagickBooleanType, POINTER(ExceptionInfo)]
InverseFourierTransformImage = _lib.InverseFourierTransformImage
InverseFourierTransformImage.restype = POINTER(Image)
InverseFourierTransformImage.argtypes = [POINTER(Image), POINTER(Image), MagickBooleanType, POINTER(ExceptionInfo)]

# values for enumeration 'NoiseType'
UndefinedNoise = 0
UniformNoise = 1
GaussianNoise = 2
MultiplicativeGaussianNoise = 3
ImpulseNoise = 4
LaplacianNoise = 5
PoissonNoise = 6
RandomNoise = 7
NoiseType = c_int # enum
AddNoiseImage = _lib.AddNoiseImage
AddNoiseImage.restype = POINTER(Image)
AddNoiseImage.argtypes = [POINTER(Image), NoiseType, POINTER(ExceptionInfo)]
AddNoiseImageChannel = _lib.AddNoiseImageChannel
AddNoiseImageChannel.restype = POINTER(Image)
AddNoiseImageChannel.argtypes = [POINTER(Image), ChannelType, NoiseType, POINTER(ExceptionInfo)]
BlueShiftImage = _lib.BlueShiftImage
BlueShiftImage.restype = POINTER(Image)
BlueShiftImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
CharcoalImage = _lib.CharcoalImage
CharcoalImage.restype = POINTER(Image)
CharcoalImage.argtypes = [POINTER(Image), c_double, c_double, POINTER(ExceptionInfo)]
ColorizeImage = _lib.ColorizeImage
ColorizeImage.restype = POINTER(Image)
ColorizeImage.argtypes = [POINTER(Image), STRING, PixelPacket, POINTER(ExceptionInfo)]
ColorMatrixImage = _lib.ColorMatrixImage
ColorMatrixImage.restype = POINTER(Image)
ColorMatrixImage.argtypes = [POINTER(Image), POINTER(KernelInfo), POINTER(ExceptionInfo)]
FxImage = _lib.FxImage
FxImage.restype = POINTER(Image)
FxImage.argtypes = [POINTER(Image), STRING, POINTER(ExceptionInfo)]
FxImageChannel = _lib.FxImageChannel
FxImageChannel.restype = POINTER(Image)
FxImageChannel.argtypes = [POINTER(Image), ChannelType, STRING, POINTER(ExceptionInfo)]
ImplodeImage = _lib.ImplodeImage
ImplodeImage.restype = POINTER(Image)
ImplodeImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
MorphImages = _lib.MorphImages
MorphImages.restype = POINTER(Image)
MorphImages.argtypes = [POINTER(Image), size_t, POINTER(ExceptionInfo)]
PolaroidImage = _lib.PolaroidImage
PolaroidImage.restype = POINTER(Image)
PolaroidImage.argtypes = [POINTER(Image), POINTER(DrawInfo), c_double, POINTER(ExceptionInfo)]
SepiaToneImage = _lib.SepiaToneImage
SepiaToneImage.restype = POINTER(Image)
SepiaToneImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
ShadowImage = _lib.ShadowImage
ShadowImage.restype = POINTER(Image)
ShadowImage.argtypes = [POINTER(Image), c_double, c_double, ssize_t, ssize_t, POINTER(ExceptionInfo)]
SketchImage = _lib.SketchImage
SketchImage.restype = POINTER(Image)
SketchImage.argtypes = [POINTER(Image), c_double, c_double, c_double, POINTER(ExceptionInfo)]
SteganoImage = _lib.SteganoImage
SteganoImage.restype = POINTER(Image)
SteganoImage.argtypes = [POINTER(Image), POINTER(Image), POINTER(ExceptionInfo)]
StereoImage = _lib.StereoImage
StereoImage.restype = POINTER(Image)
StereoImage.argtypes = [POINTER(Image), POINTER(Image), POINTER(ExceptionInfo)]
StereoAnaglyphImage = _lib.StereoAnaglyphImage
StereoAnaglyphImage.restype = POINTER(Image)
StereoAnaglyphImage.argtypes = [POINTER(Image), POINTER(Image), ssize_t, ssize_t, POINTER(ExceptionInfo)]
SwirlImage = _lib.SwirlImage
SwirlImage.restype = POINTER(Image)
SwirlImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
TintImage = _lib.TintImage
TintImage.restype = POINTER(Image)
TintImage.argtypes = [POINTER(Image), STRING, PixelPacket, POINTER(ExceptionInfo)]
VignetteImage = _lib.VignetteImage
VignetteImage.restype = POINTER(Image)
VignetteImage.argtypes = [POINTER(Image), c_double, c_double, ssize_t, ssize_t, POINTER(ExceptionInfo)]
WaveImage = _lib.WaveImage
WaveImage.restype = POINTER(Image)
WaveImage.argtypes = [POINTER(Image), c_double, c_double, POINTER(ExceptionInfo)]
class _SegmentInfo(Structure):
    pass
SegmentInfo = _SegmentInfo
PlasmaImage = _lib.PlasmaImage
PlasmaImage.restype = MagickBooleanType
PlasmaImage.argtypes = [POINTER(Image), POINTER(SegmentInfo), size_t, size_t]
SolarizeImage = _lib.SolarizeImage
SolarizeImage.restype = MagickBooleanType
SolarizeImage.argtypes = [POINTER(Image), c_double]
ExpandAffine = _lib.ExpandAffine
ExpandAffine.restype = c_double
ExpandAffine.argtypes = [POINTER(AffineMatrix)]
class _RandomInfo(Structure):
    pass
RandomInfo = _RandomInfo
MagickRealType = c_double
GenerateDifferentialNoise = _lib.GenerateDifferentialNoise
GenerateDifferentialNoise.restype = c_double
GenerateDifferentialNoise.argtypes = [POINTER(RandomInfo), Quantum, NoiseType, MagickRealType]
GetOptimalKernelWidth = _lib.GetOptimalKernelWidth
GetOptimalKernelWidth.restype = size_t
GetOptimalKernelWidth.argtypes = [c_double, c_double]
GetOptimalKernelWidth1D = _lib.GetOptimalKernelWidth1D
GetOptimalKernelWidth1D.restype = size_t
GetOptimalKernelWidth1D.argtypes = [c_double, c_double]
GetOptimalKernelWidth2D = _lib.GetOptimalKernelWidth2D
GetOptimalKernelWidth2D.restype = size_t
GetOptimalKernelWidth2D.argtypes = [c_double, c_double]
ConvertHSBToRGB = _lib.ConvertHSBToRGB
ConvertHSBToRGB.restype = None
ConvertHSBToRGB.argtypes = [c_double, c_double, c_double, POINTER(Quantum), POINTER(Quantum), POINTER(Quantum)]
ConvertHSLToRGB = _lib.ConvertHSLToRGB
ConvertHSLToRGB.restype = None
ConvertHSLToRGB.argtypes = [c_double, c_double, c_double, POINTER(Quantum), POINTER(Quantum), POINTER(Quantum)]
ConvertHWBToRGB = _lib.ConvertHWBToRGB
ConvertHWBToRGB.restype = None
ConvertHWBToRGB.argtypes = [c_double, c_double, c_double, POINTER(Quantum), POINTER(Quantum), POINTER(Quantum)]
ConvertRGBToHSB = _lib.ConvertRGBToHSB
ConvertRGBToHSB.restype = None
ConvertRGBToHSB.argtypes = [Quantum, Quantum, Quantum, POINTER(c_double), POINTER(c_double), POINTER(c_double)]
ConvertRGBToHSL = _lib.ConvertRGBToHSL
ConvertRGBToHSL.restype = None
ConvertRGBToHSL.argtypes = [Quantum, Quantum, Quantum, POINTER(c_double), POINTER(c_double), POINTER(c_double)]
ConvertRGBToHWB = _lib.ConvertRGBToHWB
ConvertRGBToHWB.restype = None
ConvertRGBToHWB.argtypes = [Quantum, Quantum, Quantum, POINTER(c_double), POINTER(c_double), POINTER(c_double)]
GetPageGeometry = _lib.GetPageGeometry
GetPageGeometry.restype = STRING
GetPageGeometry.argtypes = [STRING]
IsGeometry = _lib.IsGeometry
IsGeometry.restype = MagickBooleanType
IsGeometry.argtypes = [STRING]
IsSceneGeometry = _lib.IsSceneGeometry
IsSceneGeometry.restype = MagickBooleanType
IsSceneGeometry.argtypes = [STRING, MagickBooleanType]
GetGeometry = _lib.GetGeometry
GetGeometry.restype = MagickStatusType
GetGeometry.argtypes = [STRING, POINTER(ssize_t), POINTER(ssize_t), POINTER(size_t), POINTER(size_t)]
ParseAbsoluteGeometry = _lib.ParseAbsoluteGeometry
ParseAbsoluteGeometry.restype = MagickStatusType
ParseAbsoluteGeometry.argtypes = [STRING, POINTER(RectangleInfo)]
ParseAffineGeometry = _lib.ParseAffineGeometry
ParseAffineGeometry.restype = MagickStatusType
ParseAffineGeometry.argtypes = [STRING, POINTER(AffineMatrix), POINTER(ExceptionInfo)]
class _GeometryInfo(Structure):
    pass
GeometryInfo = _GeometryInfo
ParseGeometry = _lib.ParseGeometry
ParseGeometry.restype = MagickStatusType
ParseGeometry.argtypes = [STRING, POINTER(GeometryInfo)]
ParseGravityGeometry = _lib.ParseGravityGeometry
ParseGravityGeometry.restype = MagickStatusType
ParseGravityGeometry.argtypes = [POINTER(Image), STRING, POINTER(RectangleInfo), POINTER(ExceptionInfo)]
ParseMetaGeometry = _lib.ParseMetaGeometry
ParseMetaGeometry.restype = MagickStatusType
ParseMetaGeometry.argtypes = [STRING, POINTER(ssize_t), POINTER(ssize_t), POINTER(size_t), POINTER(size_t)]
ParsePageGeometry = _lib.ParsePageGeometry
ParsePageGeometry.restype = MagickStatusType
ParsePageGeometry.argtypes = [POINTER(Image), STRING, POINTER(RectangleInfo), POINTER(ExceptionInfo)]
ParseRegionGeometry = _lib.ParseRegionGeometry
ParseRegionGeometry.restype = MagickStatusType
ParseRegionGeometry.argtypes = [POINTER(Image), STRING, POINTER(RectangleInfo), POINTER(ExceptionInfo)]

# values for enumeration 'GravityType'
UndefinedGravity = 0
ForgetGravity = 0
NorthWestGravity = 1
NorthGravity = 2
NorthEastGravity = 3
WestGravity = 4
CenterGravity = 5
EastGravity = 6
SouthWestGravity = 7
SouthGravity = 8
SouthEastGravity = 9
StaticGravity = 10
GravityType = c_int # enum
GravityAdjustGeometry = _lib.GravityAdjustGeometry
GravityAdjustGeometry.restype = None
GravityAdjustGeometry.argtypes = [size_t, size_t, GravityType, POINTER(RectangleInfo)]
SetGeometry = _lib.SetGeometry
SetGeometry.restype = None
SetGeometry.argtypes = [POINTER(Image), POINTER(RectangleInfo)]
SetGeometryInfo = _lib.SetGeometryInfo
SetGeometryInfo.restype = None
SetGeometryInfo.argtypes = [POINTER(GeometryInfo)]
class _HashmapInfo(Structure):
    pass
HashmapInfo = _HashmapInfo
DestroyHashmap = _lib.DestroyHashmap
DestroyHashmap.restype = POINTER(HashmapInfo)
DestroyHashmap.argtypes = [POINTER(HashmapInfo)]
NewHashmap = _lib.NewHashmap
NewHashmap.restype = POINTER(HashmapInfo)
NewHashmap.argtypes = [size_t, CFUNCTYPE(size_t, c_void_p), CFUNCTYPE(MagickBooleanType, c_void_p, c_void_p), CFUNCTYPE(c_void_p, c_void_p), CFUNCTYPE(c_void_p, c_void_p)]
DestroyLinkedList = _lib.DestroyLinkedList
DestroyLinkedList.restype = POINTER(LinkedListInfo)
DestroyLinkedList.argtypes = [POINTER(LinkedListInfo), CFUNCTYPE(c_void_p, c_void_p)]
NewLinkedList = _lib.NewLinkedList
NewLinkedList.restype = POINTER(LinkedListInfo)
NewLinkedList.argtypes = [size_t]
AppendValueToLinkedList = _lib.AppendValueToLinkedList
AppendValueToLinkedList.restype = MagickBooleanType
AppendValueToLinkedList.argtypes = [POINTER(LinkedListInfo), c_void_p]
CompareHashmapString = _lib.CompareHashmapString
CompareHashmapString.restype = MagickBooleanType
CompareHashmapString.argtypes = [c_void_p, c_void_p]
CompareHashmapStringInfo = _lib.CompareHashmapStringInfo
CompareHashmapStringInfo.restype = MagickBooleanType
CompareHashmapStringInfo.argtypes = [c_void_p, c_void_p]
InsertValueInLinkedList = _lib.InsertValueInLinkedList
InsertValueInLinkedList.restype = MagickBooleanType
InsertValueInLinkedList.argtypes = [POINTER(LinkedListInfo), size_t, c_void_p]
InsertValueInSortedLinkedList = _lib.InsertValueInSortedLinkedList
InsertValueInSortedLinkedList.restype = MagickBooleanType
InsertValueInSortedLinkedList.argtypes = [POINTER(LinkedListInfo), CFUNCTYPE(c_int, c_void_p, c_void_p), POINTER(c_void_p), c_void_p]
IsHashmapEmpty = _lib.IsHashmapEmpty
IsHashmapEmpty.restype = MagickBooleanType
IsHashmapEmpty.argtypes = [POINTER(HashmapInfo)]
IsLinkedListEmpty = _lib.IsLinkedListEmpty
IsLinkedListEmpty.restype = MagickBooleanType
IsLinkedListEmpty.argtypes = [POINTER(LinkedListInfo)]
LinkedListToArray = _lib.LinkedListToArray
LinkedListToArray.restype = MagickBooleanType
LinkedListToArray.argtypes = [POINTER(LinkedListInfo), POINTER(c_void_p)]
PutEntryInHashmap = _lib.PutEntryInHashmap
PutEntryInHashmap.restype = MagickBooleanType
PutEntryInHashmap.argtypes = [POINTER(HashmapInfo), c_void_p, c_void_p]
GetNumberOfElementsInLinkedList = _lib.GetNumberOfElementsInLinkedList
GetNumberOfElementsInLinkedList.restype = size_t
GetNumberOfElementsInLinkedList.argtypes = [POINTER(LinkedListInfo)]
GetNumberOfEntriesInHashmap = _lib.GetNumberOfEntriesInHashmap
GetNumberOfEntriesInHashmap.restype = size_t
GetNumberOfEntriesInHashmap.argtypes = [POINTER(HashmapInfo)]
HashPointerType = _lib.HashPointerType
HashPointerType.restype = size_t
HashPointerType.argtypes = [c_void_p]
HashStringType = _lib.HashStringType
HashStringType.restype = size_t
HashStringType.argtypes = [c_void_p]
HashStringInfoType = _lib.HashStringInfoType
HashStringInfoType.restype = size_t
HashStringInfoType.argtypes = [c_void_p]
ClearLinkedList = _lib.ClearLinkedList
ClearLinkedList.restype = None
ClearLinkedList.argtypes = [POINTER(LinkedListInfo), CFUNCTYPE(c_void_p, c_void_p)]
GetLastValueInLinkedList = _lib.GetLastValueInLinkedList
GetLastValueInLinkedList.restype = c_void_p
GetLastValueInLinkedList.argtypes = [POINTER(LinkedListInfo)]
GetNextKeyInHashmap = _lib.GetNextKeyInHashmap
GetNextKeyInHashmap.restype = c_void_p
GetNextKeyInHashmap.argtypes = [POINTER(HashmapInfo)]
GetNextValueInHashmap = _lib.GetNextValueInHashmap
GetNextValueInHashmap.restype = c_void_p
GetNextValueInHashmap.argtypes = [POINTER(HashmapInfo)]
GetNextValueInLinkedList = _lib.GetNextValueInLinkedList
GetNextValueInLinkedList.restype = c_void_p
GetNextValueInLinkedList.argtypes = [POINTER(LinkedListInfo)]
GetValueFromHashmap = _lib.GetValueFromHashmap
GetValueFromHashmap.restype = c_void_p
GetValueFromHashmap.argtypes = [POINTER(HashmapInfo), c_void_p]
GetValueFromLinkedList = _lib.GetValueFromLinkedList
GetValueFromLinkedList.restype = c_void_p
GetValueFromLinkedList.argtypes = [POINTER(LinkedListInfo), size_t]
RemoveElementByValueFromLinkedList = _lib.RemoveElementByValueFromLinkedList
RemoveElementByValueFromLinkedList.restype = c_void_p
RemoveElementByValueFromLinkedList.argtypes = [POINTER(LinkedListInfo), c_void_p]
RemoveElementFromLinkedList = _lib.RemoveElementFromLinkedList
RemoveElementFromLinkedList.restype = c_void_p
RemoveElementFromLinkedList.argtypes = [POINTER(LinkedListInfo), size_t]
RemoveEntryFromHashmap = _lib.RemoveEntryFromHashmap
RemoveEntryFromHashmap.restype = c_void_p
RemoveEntryFromHashmap.argtypes = [POINTER(HashmapInfo), c_void_p]
RemoveLastElementFromLinkedList = _lib.RemoveLastElementFromLinkedList
RemoveLastElementFromLinkedList.restype = c_void_p
RemoveLastElementFromLinkedList.argtypes = [POINTER(LinkedListInfo)]
ResetHashmapIterator = _lib.ResetHashmapIterator
ResetHashmapIterator.restype = None
ResetHashmapIterator.argtypes = [POINTER(HashmapInfo)]
ResetLinkedListIterator = _lib.ResetLinkedListIterator
ResetLinkedListIterator.restype = None
ResetLinkedListIterator.argtypes = [POINTER(LinkedListInfo)]
class _ColorPacket(Structure):
    pass
ColorPacket = _ColorPacket
GetImageHistogram = _lib.GetImageHistogram
GetImageHistogram.restype = POINTER(ColorPacket)
GetImageHistogram.argtypes = [POINTER(Image), POINTER(size_t), POINTER(ExceptionInfo)]
UniqueImageColors = _lib.UniqueImageColors
UniqueImageColors.restype = POINTER(Image)
UniqueImageColors.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
IsHistogramImage = _lib.IsHistogramImage
IsHistogramImage.restype = MagickBooleanType
IsHistogramImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
IsPaletteImage = _lib.IsPaletteImage
IsPaletteImage.restype = MagickBooleanType
IsPaletteImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
MinMaxStretchImage = _lib.MinMaxStretchImage
MinMaxStretchImage.restype = MagickBooleanType
MinMaxStretchImage.argtypes = [POINTER(Image), ChannelType, c_double, c_double]
GetNumberColors = _lib.GetNumberColors
GetNumberColors.restype = size_t
GetNumberColors.argtypes = [POINTER(Image), POINTER(FILE), POINTER(ExceptionInfo)]
IdentifyImage = _lib.IdentifyImage
IdentifyImage.restype = MagickBooleanType
IdentifyImage.argtypes = [POINTER(Image), POINTER(FILE), MagickBooleanType]
class _ImageView(Structure):
    pass
ImageView = _ImageView
GetImageViewException = _lib.GetImageViewException
GetImageViewException.restype = STRING
GetImageViewException.argtypes = [POINTER(ImageView), POINTER(ExceptionType)]
GetImageViewVirtualIndexes = _lib.GetImageViewVirtualIndexes
GetImageViewVirtualIndexes.restype = POINTER(IndexPacket)
GetImageViewVirtualIndexes.argtypes = [POINTER(ImageView)]
GetImageViewVirtualPixels = _lib.GetImageViewVirtualPixels
GetImageViewVirtualPixels.restype = POINTER(PixelPacket)
GetImageViewVirtualPixels.argtypes = [POINTER(ImageView)]
GetImageViewImage = _lib.GetImageViewImage
GetImageViewImage.restype = POINTER(Image)
GetImageViewImage.argtypes = [POINTER(ImageView)]
CloneImageView = _lib.CloneImageView
CloneImageView.restype = POINTER(ImageView)
CloneImageView.argtypes = [POINTER(ImageView)]
DestroyImageView = _lib.DestroyImageView
DestroyImageView.restype = POINTER(ImageView)
DestroyImageView.argtypes = [POINTER(ImageView)]
NewImageView = _lib.NewImageView
NewImageView.restype = POINTER(ImageView)
NewImageView.argtypes = [POINTER(Image)]
NewImageViewRegion = _lib.NewImageViewRegion
NewImageViewRegion.restype = POINTER(ImageView)
NewImageViewRegion.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t]
GetImageViewAuthenticIndexes = _lib.GetImageViewAuthenticIndexes
GetImageViewAuthenticIndexes.restype = POINTER(IndexPacket)
GetImageViewAuthenticIndexes.argtypes = [POINTER(ImageView)]
DuplexTransferImageViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(ImageView), POINTER(ImageView), POINTER(ImageView), ssize_t, c_int, c_void_p)
DuplexTransferImageViewIterator = _lib.DuplexTransferImageViewIterator
DuplexTransferImageViewIterator.restype = MagickBooleanType
DuplexTransferImageViewIterator.argtypes = [POINTER(ImageView), POINTER(ImageView), POINTER(ImageView), DuplexTransferImageViewMethod, c_void_p]
GetImageViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(ImageView), ssize_t, c_int, c_void_p)
GetImageViewIterator = _lib.GetImageViewIterator
GetImageViewIterator.restype = MagickBooleanType
GetImageViewIterator.argtypes = [POINTER(ImageView), GetImageViewMethod, c_void_p]
IsImageView = _lib.IsImageView
IsImageView.restype = MagickBooleanType
IsImageView.argtypes = [POINTER(ImageView)]
SetImageViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(ImageView), ssize_t, c_int, c_void_p)
SetImageViewIterator = _lib.SetImageViewIterator
SetImageViewIterator.restype = MagickBooleanType
SetImageViewIterator.argtypes = [POINTER(ImageView), SetImageViewMethod, c_void_p]
TransferImageViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(ImageView), POINTER(ImageView), ssize_t, c_int, c_void_p)
TransferImageViewIterator = _lib.TransferImageViewIterator
TransferImageViewIterator.restype = MagickBooleanType
TransferImageViewIterator.argtypes = [POINTER(ImageView), POINTER(ImageView), TransferImageViewMethod, c_void_p]
UpdateImageViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(ImageView), ssize_t, c_int, c_void_p)
UpdateImageViewIterator = _lib.UpdateImageViewIterator
UpdateImageViewIterator.restype = MagickBooleanType
UpdateImageViewIterator.argtypes = [POINTER(ImageView), UpdateImageViewMethod, c_void_p]
GetImageViewAuthenticPixels = _lib.GetImageViewAuthenticPixels
GetImageViewAuthenticPixels.restype = POINTER(PixelPacket)
GetImageViewAuthenticPixels.argtypes = [POINTER(ImageView)]
GetImageViewExtent = _lib.GetImageViewExtent
GetImageViewExtent.restype = RectangleInfo
GetImageViewExtent.argtypes = [POINTER(ImageView)]
SetImageViewDescription = _lib.SetImageViewDescription
SetImageViewDescription.restype = None
SetImageViewDescription.argtypes = [POINTER(ImageView), STRING]
SetImageViewThreads = _lib.SetImageViewThreads
SetImageViewThreads.restype = None
SetImageViewThreads.argtypes = [POINTER(ImageView), size_t]
CatchImageException = _lib.CatchImageException
CatchImageException.restype = ExceptionType
CatchImageException.argtypes = [POINTER(Image)]
GetImageInfoFile = _lib.GetImageInfoFile
GetImageInfoFile.restype = POINTER(FILE)
GetImageInfoFile.argtypes = [POINTER(ImageInfo)]
AcquireImage = _lib.AcquireImage
AcquireImage.restype = POINTER(Image)
AcquireImage.argtypes = [POINTER(ImageInfo)]
AppendImages = _lib.AppendImages
AppendImages.restype = POINTER(Image)
AppendImages.argtypes = [POINTER(Image), MagickBooleanType, POINTER(ExceptionInfo)]
CloneImage = _lib.CloneImage
CloneImage.restype = POINTER(Image)
CloneImage.argtypes = [POINTER(Image), size_t, size_t, MagickBooleanType, POINTER(ExceptionInfo)]
CombineImages = _lib.CombineImages
CombineImages.restype = POINTER(Image)
CombineImages.argtypes = [POINTER(Image), ChannelType, POINTER(ExceptionInfo)]
DestroyImage = _lib.DestroyImage
DestroyImage.restype = POINTER(Image)
DestroyImage.argtypes = [POINTER(Image)]
GetImageClipMask = _lib.GetImageClipMask
GetImageClipMask.restype = POINTER(Image)
GetImageClipMask.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
GetImageMask = _lib.GetImageMask
GetImageMask.restype = POINTER(Image)
GetImageMask.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
NewMagickImage = _lib.NewMagickImage
NewMagickImage.restype = POINTER(Image)
NewMagickImage.argtypes = [POINTER(ImageInfo), size_t, size_t, POINTER(MagickPixelPacket)]
ReferenceImage = _lib.ReferenceImage
ReferenceImage.restype = POINTER(Image)
ReferenceImage.argtypes = [POINTER(Image)]
SeparateImages = _lib.SeparateImages
SeparateImages.restype = POINTER(Image)
SeparateImages.argtypes = [POINTER(Image), ChannelType, POINTER(ExceptionInfo)]
SmushImages = _lib.SmushImages
SmushImages.restype = POINTER(Image)
SmushImages.argtypes = [POINTER(Image), MagickBooleanType, ssize_t, POINTER(ExceptionInfo)]
AcquireImageInfo = _lib.AcquireImageInfo
AcquireImageInfo.restype = POINTER(ImageInfo)
AcquireImageInfo.argtypes = []
CloneImageInfo = _lib.CloneImageInfo
CloneImageInfo.restype = POINTER(ImageInfo)
CloneImageInfo.argtypes = [POINTER(ImageInfo)]
DestroyImageInfo = _lib.DestroyImageInfo
DestroyImageInfo.restype = POINTER(ImageInfo)
DestroyImageInfo.argtypes = [POINTER(ImageInfo)]
ClipImage = _lib.ClipImage
ClipImage.restype = MagickBooleanType
ClipImage.argtypes = [POINTER(Image)]
ClipImagePath = _lib.ClipImagePath
ClipImagePath.restype = MagickBooleanType
ClipImagePath.argtypes = [POINTER(Image), STRING, MagickBooleanType]
GetImageAlphaChannel = _lib.GetImageAlphaChannel
GetImageAlphaChannel.restype = MagickBooleanType
GetImageAlphaChannel.argtypes = [POINTER(Image)]
IsTaintImage = _lib.IsTaintImage
IsTaintImage.restype = MagickBooleanType
IsTaintImage.argtypes = [POINTER(Image)]
IsMagickConflict = _lib.IsMagickConflict
IsMagickConflict.restype = MagickBooleanType
IsMagickConflict.argtypes = [STRING]
IsHighDynamicRangeImage = _lib.IsHighDynamicRangeImage
IsHighDynamicRangeImage.restype = MagickBooleanType
IsHighDynamicRangeImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
IsImageObject = _lib.IsImageObject
IsImageObject.restype = MagickBooleanType
IsImageObject.argtypes = [POINTER(Image)]
ListMagickInfo = _lib.ListMagickInfo
ListMagickInfo.restype = MagickBooleanType
ListMagickInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
ModifyImage = _lib.ModifyImage
ModifyImage.restype = MagickBooleanType
ModifyImage.argtypes = [POINTER(POINTER(Image)), POINTER(ExceptionInfo)]
ResetImagePage = _lib.ResetImagePage
ResetImagePage.restype = MagickBooleanType
ResetImagePage.argtypes = [POINTER(Image), STRING]
SeparateImageChannel = _lib.SeparateImageChannel
SeparateImageChannel.restype = MagickBooleanType
SeparateImageChannel.argtypes = [POINTER(Image), ChannelType]

# values for enumeration 'AlphaChannelType'
UndefinedAlphaChannel = 0
ActivateAlphaChannel = 1
BackgroundAlphaChannel = 2
CopyAlphaChannel = 3
DeactivateAlphaChannel = 4
ExtractAlphaChannel = 5
OpaqueAlphaChannel = 6
ResetAlphaChannel = 7
SetAlphaChannel = 8
ShapeAlphaChannel = 9
TransparentAlphaChannel = 10
AlphaChannelType = c_int # enum
SetImageAlphaChannel = _lib.SetImageAlphaChannel
SetImageAlphaChannel.restype = MagickBooleanType
SetImageAlphaChannel.argtypes = [POINTER(Image), AlphaChannelType]
SetImageBackgroundColor = _lib.SetImageBackgroundColor
SetImageBackgroundColor.restype = MagickBooleanType
SetImageBackgroundColor.argtypes = [POINTER(Image)]
SetImageClipMask = _lib.SetImageClipMask
SetImageClipMask.restype = MagickBooleanType
SetImageClipMask.argtypes = [POINTER(Image), POINTER(Image)]
SetImageColor = _lib.SetImageColor
SetImageColor.restype = MagickBooleanType
SetImageColor.argtypes = [POINTER(Image), POINTER(MagickPixelPacket)]
SetImageExtent = _lib.SetImageExtent
SetImageExtent.restype = MagickBooleanType
SetImageExtent.argtypes = [POINTER(Image), size_t, size_t]
SetImageInfo = _lib.SetImageInfo
SetImageInfo.restype = MagickBooleanType
SetImageInfo.argtypes = [POINTER(ImageInfo), c_uint, POINTER(ExceptionInfo)]
SetImageMask = _lib.SetImageMask
SetImageMask.restype = MagickBooleanType
SetImageMask.argtypes = [POINTER(Image), POINTER(Image)]
SetImageOpacity = _lib.SetImageOpacity
SetImageOpacity.restype = MagickBooleanType
SetImageOpacity.argtypes = [POINTER(Image), Quantum]
SetImageChannels = _lib.SetImageChannels
SetImageChannels.restype = MagickBooleanType
SetImageChannels.argtypes = [POINTER(Image), size_t]
SetImageStorageClass = _lib.SetImageStorageClass
SetImageStorageClass.restype = MagickBooleanType
SetImageStorageClass.argtypes = [POINTER(Image), ClassType]
SetImageType = _lib.SetImageType
SetImageType.restype = MagickBooleanType
SetImageType.argtypes = [POINTER(Image), ImageType]
StripImage = _lib.StripImage
StripImage.restype = MagickBooleanType
StripImage.argtypes = [POINTER(Image)]
SyncImage = _lib.SyncImage
SyncImage.restype = MagickBooleanType
SyncImage.argtypes = [POINTER(Image)]
SyncImageSettings = _lib.SyncImageSettings
SyncImageSettings.restype = MagickBooleanType
SyncImageSettings.argtypes = [POINTER(ImageInfo), POINTER(Image)]
SyncImagesSettings = _lib.SyncImagesSettings
SyncImagesSettings.restype = MagickBooleanType
SyncImagesSettings.argtypes = [POINTER(ImageInfo), POINTER(Image)]
InterpretImageFilename = _lib.InterpretImageFilename
InterpretImageFilename.restype = size_t
InterpretImageFilename.argtypes = [POINTER(ImageInfo), POINTER(Image), STRING, c_int, STRING]
GetImageReferenceCount = _lib.GetImageReferenceCount
GetImageReferenceCount.restype = ssize_t
GetImageReferenceCount.argtypes = [POINTER(Image)]
GetImageChannels = _lib.GetImageChannels
GetImageChannels.restype = size_t
GetImageChannels.argtypes = [POINTER(Image)]
GetImageVirtualPixelMethod = _lib.GetImageVirtualPixelMethod
GetImageVirtualPixelMethod.restype = VirtualPixelMethod
GetImageVirtualPixelMethod.argtypes = [POINTER(Image)]
SetImageVirtualPixelMethod = _lib.SetImageVirtualPixelMethod
SetImageVirtualPixelMethod.restype = VirtualPixelMethod
SetImageVirtualPixelMethod.argtypes = [POINTER(Image), VirtualPixelMethod]
AcquireNextImage = _lib.AcquireNextImage
AcquireNextImage.restype = None
AcquireNextImage.argtypes = [POINTER(ImageInfo), POINTER(Image)]
DestroyImagePixels = _lib.DestroyImagePixels
DestroyImagePixels.restype = None
DestroyImagePixels.argtypes = [POINTER(Image)]
DisassociateImageStream = _lib.DisassociateImageStream
DisassociateImageStream.restype = None
DisassociateImageStream.argtypes = [POINTER(Image)]
GetImageException = _lib.GetImageException
GetImageException.restype = None
GetImageException.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
GetImageInfo = _lib.GetImageInfo
GetImageInfo.restype = None
GetImageInfo.argtypes = [POINTER(ImageInfo)]
SetImageInfoBlob = _lib.SetImageInfoBlob
SetImageInfoBlob.restype = None
SetImageInfoBlob.argtypes = [POINTER(ImageInfo), c_void_p, size_t]
SetImageInfoFile = _lib.SetImageInfoFile
SetImageInfoFile.restype = None
SetImageInfoFile.argtypes = [POINTER(ImageInfo), POINTER(FILE)]
CoalesceImages = _lib.CoalesceImages
CoalesceImages.restype = POINTER(Image)
CoalesceImages.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
DisposeImages = _lib.DisposeImages
DisposeImages.restype = POINTER(Image)
DisposeImages.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]

# values for enumeration 'ImageLayerMethod'
UndefinedLayer = 0
CoalesceLayer = 1
CompareAnyLayer = 2
CompareClearLayer = 3
CompareOverlayLayer = 4
DisposeLayer = 5
OptimizeLayer = 6
OptimizeImageLayer = 7
OptimizePlusLayer = 8
OptimizeTransLayer = 9
RemoveDupsLayer = 10
RemoveZeroLayer = 11
CompositeLayer = 12
MergeLayer = 13
FlattenLayer = 14
MosaicLayer = 15
TrimBoundsLayer = 16
ImageLayerMethod = c_int # enum
CompareImageLayers = _lib.CompareImageLayers
CompareImageLayers.restype = POINTER(Image)
CompareImageLayers.argtypes = [POINTER(Image), ImageLayerMethod, POINTER(ExceptionInfo)]
DeconstructImages = _lib.DeconstructImages
DeconstructImages.restype = POINTER(Image)
DeconstructImages.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
MergeImageLayers = _lib.MergeImageLayers
MergeImageLayers.restype = POINTER(Image)
MergeImageLayers.argtypes = [POINTER(Image), ImageLayerMethod, POINTER(ExceptionInfo)]
OptimizeImageLayers = _lib.OptimizeImageLayers
OptimizeImageLayers.restype = POINTER(Image)
OptimizeImageLayers.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
OptimizePlusImageLayers = _lib.OptimizePlusImageLayers
OptimizePlusImageLayers.restype = POINTER(Image)
OptimizePlusImageLayers.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
CompositeLayers = _lib.CompositeLayers
CompositeLayers.restype = None
CompositeLayers.argtypes = [POINTER(Image), CompositeOperator, POINTER(Image), ssize_t, ssize_t, POINTER(ExceptionInfo)]
OptimizeImageTransparency = _lib.OptimizeImageTransparency
OptimizeImageTransparency.restype = None
OptimizeImageTransparency.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
RemoveDuplicateLayers = _lib.RemoveDuplicateLayers
RemoveDuplicateLayers.restype = None
RemoveDuplicateLayers.argtypes = [POINTER(POINTER(Image)), POINTER(ExceptionInfo)]
RemoveZeroDelayLayers = _lib.RemoveZeroDelayLayers
RemoveZeroDelayLayers.restype = None
RemoveZeroDelayLayers.argtypes = [POINTER(POINTER(Image)), POINTER(ExceptionInfo)]
CloneImageList = _lib.CloneImageList
CloneImageList.restype = POINTER(Image)
CloneImageList.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
CloneImages = _lib.CloneImages
CloneImages.restype = POINTER(Image)
CloneImages.argtypes = [POINTER(Image), STRING, POINTER(ExceptionInfo)]
DestroyImageList = _lib.DestroyImageList
DestroyImageList.restype = POINTER(Image)
DestroyImageList.argtypes = [POINTER(Image)]
DuplicateImages = _lib.DuplicateImages
DuplicateImages.restype = POINTER(Image)
DuplicateImages.argtypes = [POINTER(Image), size_t, STRING, POINTER(ExceptionInfo)]
GetFirstImageInList = _lib.GetFirstImageInList
GetFirstImageInList.restype = POINTER(Image)
GetFirstImageInList.argtypes = [POINTER(Image)]
GetImageFromList = _lib.GetImageFromList
GetImageFromList.restype = POINTER(Image)
GetImageFromList.argtypes = [POINTER(Image), ssize_t]
GetLastImageInList = _lib.GetLastImageInList
GetLastImageInList.restype = POINTER(Image)
GetLastImageInList.argtypes = [POINTER(Image)]
GetNextImageInList = _lib.GetNextImageInList
GetNextImageInList.restype = POINTER(Image)
GetNextImageInList.argtypes = [POINTER(Image)]
GetPreviousImageInList = _lib.GetPreviousImageInList
GetPreviousImageInList.restype = POINTER(Image)
GetPreviousImageInList.argtypes = [POINTER(Image)]
ImageListToArray = _lib.ImageListToArray
ImageListToArray.restype = POINTER(POINTER(Image))
ImageListToArray.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
NewImageList = _lib.NewImageList
NewImageList.restype = POINTER(Image)
NewImageList.argtypes = []
RemoveImageFromList = _lib.RemoveImageFromList
RemoveImageFromList.restype = POINTER(Image)
RemoveImageFromList.argtypes = [POINTER(POINTER(Image))]
RemoveLastImageFromList = _lib.RemoveLastImageFromList
RemoveLastImageFromList.restype = POINTER(Image)
RemoveLastImageFromList.argtypes = [POINTER(POINTER(Image))]
RemoveFirstImageFromList = _lib.RemoveFirstImageFromList
RemoveFirstImageFromList.restype = POINTER(Image)
RemoveFirstImageFromList.argtypes = [POINTER(POINTER(Image))]
SpliceImageIntoList = _lib.SpliceImageIntoList
SpliceImageIntoList.restype = POINTER(Image)
SpliceImageIntoList.argtypes = [POINTER(POINTER(Image)), size_t, POINTER(Image)]
SplitImageList = _lib.SplitImageList
SplitImageList.restype = POINTER(Image)
SplitImageList.argtypes = [POINTER(Image)]
SyncNextImageInList = _lib.SyncNextImageInList
SyncNextImageInList.restype = POINTER(Image)
SyncNextImageInList.argtypes = [POINTER(Image)]
GetImageListLength = _lib.GetImageListLength
GetImageListLength.restype = size_t
GetImageListLength.argtypes = [POINTER(Image)]
GetImageIndexInList = _lib.GetImageIndexInList
GetImageIndexInList.restype = ssize_t
GetImageIndexInList.argtypes = [POINTER(Image)]
AppendImageToList = _lib.AppendImageToList
AppendImageToList.restype = None
AppendImageToList.argtypes = [POINTER(POINTER(Image)), POINTER(Image)]
DeleteImageFromList = _lib.DeleteImageFromList
DeleteImageFromList.restype = None
DeleteImageFromList.argtypes = [POINTER(POINTER(Image))]
DeleteImages = _lib.DeleteImages
DeleteImages.restype = None
DeleteImages.argtypes = [POINTER(POINTER(Image)), STRING, POINTER(ExceptionInfo)]
InsertImageInList = _lib.InsertImageInList
InsertImageInList.restype = None
InsertImageInList.argtypes = [POINTER(POINTER(Image)), POINTER(Image)]
PrependImageToList = _lib.PrependImageToList
PrependImageToList.restype = None
PrependImageToList.argtypes = [POINTER(POINTER(Image)), POINTER(Image)]
ReplaceImageInList = _lib.ReplaceImageInList
ReplaceImageInList.restype = None
ReplaceImageInList.argtypes = [POINTER(POINTER(Image)), POINTER(Image)]
ReplaceImageInListReturnLast = _lib.ReplaceImageInListReturnLast
ReplaceImageInListReturnLast.restype = None
ReplaceImageInListReturnLast.argtypes = [POINTER(POINTER(Image)), POINTER(Image)]
ReverseImageList = _lib.ReverseImageList
ReverseImageList.restype = None
ReverseImageList.argtypes = [POINTER(POINTER(Image))]
SyncImageList = _lib.SyncImageList
SyncImageList.restype = None
SyncImageList.argtypes = [POINTER(Image)]
GetLocaleList = _lib.GetLocaleList
GetLocaleList.restype = POINTER(STRING)
GetLocaleList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
GetLocaleMessage = _lib.GetLocaleMessage
GetLocaleMessage.restype = STRING
GetLocaleMessage.argtypes = [STRING]
class _LocaleInfo(Structure):
    pass
LocaleInfo = _LocaleInfo
GetLocaleInfo_ = _lib.GetLocaleInfo_
GetLocaleInfo_.restype = POINTER(LocaleInfo)
GetLocaleInfo_.argtypes = [STRING, POINTER(ExceptionInfo)]
GetLocaleInfoList = _lib.GetLocaleInfoList
GetLocaleInfoList.restype = POINTER(POINTER(LocaleInfo))
GetLocaleInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
InterpretLocaleValue = _lib.InterpretLocaleValue
InterpretLocaleValue.restype = c_double
InterpretLocaleValue.argtypes = [STRING, POINTER(STRING)]
DestroyLocaleOptions = _lib.DestroyLocaleOptions
DestroyLocaleOptions.restype = POINTER(LinkedListInfo)
DestroyLocaleOptions.argtypes = [POINTER(LinkedListInfo)]
GetLocaleOptions = _lib.GetLocaleOptions
GetLocaleOptions.restype = POINTER(LinkedListInfo)
GetLocaleOptions.argtypes = [STRING, POINTER(ExceptionInfo)]
ListLocaleInfo = _lib.ListLocaleInfo
ListLocaleInfo.restype = MagickBooleanType
ListLocaleInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
LocaleComponentGenesis = _lib.LocaleComponentGenesis
LocaleComponentGenesis.restype = MagickBooleanType
LocaleComponentGenesis.argtypes = []
FormatLocaleFile = _lib.FormatLocaleFile
FormatLocaleFile.restype = ssize_t
FormatLocaleFile.argtypes = [POINTER(FILE), STRING]
FormatLocaleFileList = _lib.FormatLocaleFileList
FormatLocaleFileList.restype = ssize_t
FormatLocaleFileList.argtypes = [POINTER(FILE), STRING, POINTER(__va_list_tag)]
FormatLocaleString = _lib.FormatLocaleString
FormatLocaleString.restype = ssize_t
FormatLocaleString.argtypes = [STRING, size_t, STRING]
FormatLocaleStringList = _lib.FormatLocaleStringList
FormatLocaleStringList.restype = ssize_t
FormatLocaleStringList.argtypes = [STRING, size_t, STRING, POINTER(__va_list_tag)]
LocaleComponentTerminus = _lib.LocaleComponentTerminus
LocaleComponentTerminus.restype = None
LocaleComponentTerminus.argtypes = []
GetLogList = _lib.GetLogList
GetLogList.restype = POINTER(STRING)
GetLogList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
GetLogName = _lib.GetLogName
GetLogName.restype = STRING
GetLogName.argtypes = []
SetLogName = _lib.SetLogName
SetLogName.restype = STRING
SetLogName.argtypes = [STRING]
class _LogInfo(Structure):
    pass
LogInfo = _LogInfo
GetLogInfoList = _lib.GetLogInfoList
GetLogInfoList.restype = POINTER(POINTER(LogInfo))
GetLogInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]

# values for enumeration 'LogEventType'
UndefinedEvents = 0
NoEvents = 0
TraceEvent = 1
AnnotateEvent = 2
BlobEvent = 4
CacheEvent = 8
CoderEvent = 16
ConfigureEvent = 32
DeprecateEvent = 64
DrawEvent = 128
ExceptionEvent = 256
ImageEvent = 512
LocaleEvent = 1024
ModuleEvent = 2048
PolicyEvent = 4096
ResourceEvent = 8192
TransformEvent = 16384
UserEvent = 36864
WandEvent = 65536
X11Event = 131072
AccelerateEvent = 262144
AllEvents = 2147483647
LogEventType = c_int # enum
SetLogEventMask = _lib.SetLogEventMask
SetLogEventMask.restype = LogEventType
SetLogEventMask.argtypes = [STRING]
IsEventLogging = _lib.IsEventLogging
IsEventLogging.restype = MagickBooleanType
IsEventLogging.argtypes = []
ListLogInfo = _lib.ListLogInfo
ListLogInfo.restype = MagickBooleanType
ListLogInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
LogComponentGenesis = _lib.LogComponentGenesis
LogComponentGenesis.restype = MagickBooleanType
LogComponentGenesis.argtypes = []
LogMagickEvent = _lib.LogMagickEvent
LogMagickEvent.restype = MagickBooleanType
LogMagickEvent.argtypes = [LogEventType, STRING, STRING, size_t, STRING]
LogMagickEventList = _lib.LogMagickEventList
LogMagickEventList.restype = MagickBooleanType
LogMagickEventList.argtypes = [LogEventType, STRING, STRING, size_t, STRING, POINTER(__va_list_tag)]
CloseMagickLog = _lib.CloseMagickLog
CloseMagickLog.restype = None
CloseMagickLog.argtypes = []
LogComponentTerminus = _lib.LogComponentTerminus
LogComponentTerminus.restype = None
LogComponentTerminus.argtypes = []
SetLogFormat = _lib.SetLogFormat
SetLogFormat.restype = None
SetLogFormat.argtypes = [STRING]
GetMagicList = _lib.GetMagicList
GetMagicList.restype = POINTER(STRING)
GetMagicList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
class _MagicInfo(Structure):
    pass
MagicInfo = _MagicInfo
GetMagicName = _lib.GetMagicName
GetMagicName.restype = STRING
GetMagicName.argtypes = [POINTER(MagicInfo)]
ListMagicInfo = _lib.ListMagicInfo
ListMagicInfo.restype = MagickBooleanType
ListMagicInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
MagicComponentGenesis = _lib.MagicComponentGenesis
MagicComponentGenesis.restype = MagickBooleanType
MagicComponentGenesis.argtypes = []
GetMagicInfo = _lib.GetMagicInfo
GetMagicInfo.restype = POINTER(MagicInfo)
GetMagicInfo.argtypes = [POINTER(c_ubyte), size_t, POINTER(ExceptionInfo)]
GetMagicInfoList = _lib.GetMagicInfoList
GetMagicInfoList.restype = POINTER(POINTER(MagicInfo))
GetMagicInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
MagicComponentTerminus = _lib.MagicComponentTerminus
MagicComponentTerminus.restype = None
MagicComponentTerminus.argtypes = []
GetMagickList = _lib.GetMagickList
GetMagickList.restype = POINTER(STRING)
GetMagickList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
class _MagickInfo(Structure):
    pass
MagickInfo = _MagickInfo
GetMagickDescription = _lib.GetMagickDescription
GetMagickDescription.restype = STRING
GetMagickDescription.argtypes = [POINTER(MagickInfo)]
DecodeImageHandler = CFUNCTYPE(POINTER(Image), POINTER(ImageInfo), POINTER(ExceptionInfo))
GetImageDecoder = _lib.GetImageDecoder
GetImageDecoder.restype = POINTER(DecodeImageHandler)
GetImageDecoder.argtypes = [POINTER(MagickInfo)]
EncodeImageHandler = CFUNCTYPE(MagickBooleanType, POINTER(ImageInfo), POINTER(Image))
GetImageEncoder = _lib.GetImageEncoder
GetImageEncoder.restype = POINTER(EncodeImageHandler)
GetImageEncoder.argtypes = [POINTER(MagickInfo)]
GetMagickPrecision = _lib.GetMagickPrecision
GetMagickPrecision.restype = c_int
GetMagickPrecision.argtypes = []
SetMagickPrecision = _lib.SetMagickPrecision
SetMagickPrecision.restype = c_int
SetMagickPrecision.argtypes = [c_int]
GetImageMagick = _lib.GetImageMagick
GetImageMagick.restype = MagickBooleanType
GetImageMagick.argtypes = [POINTER(c_ubyte), size_t, STRING]
GetMagickAdjoin = _lib.GetMagickAdjoin
GetMagickAdjoin.restype = MagickBooleanType
GetMagickAdjoin.argtypes = [POINTER(MagickInfo)]
GetMagickBlobSupport = _lib.GetMagickBlobSupport
GetMagickBlobSupport.restype = MagickBooleanType
GetMagickBlobSupport.argtypes = [POINTER(MagickInfo)]
GetMagickEndianSupport = _lib.GetMagickEndianSupport
GetMagickEndianSupport.restype = MagickBooleanType
GetMagickEndianSupport.argtypes = [POINTER(MagickInfo)]
GetMagickRawSupport = _lib.GetMagickRawSupport
GetMagickRawSupport.restype = MagickBooleanType
GetMagickRawSupport.argtypes = [POINTER(MagickInfo)]
GetMagickSeekableStream = _lib.GetMagickSeekableStream
GetMagickSeekableStream.restype = MagickBooleanType
GetMagickSeekableStream.argtypes = [POINTER(MagickInfo)]
IsMagickInstantiated = _lib.IsMagickInstantiated
IsMagickInstantiated.restype = MagickBooleanType
IsMagickInstantiated.argtypes = []
MagickComponentGenesis = _lib.MagickComponentGenesis
MagickComponentGenesis.restype = MagickBooleanType
MagickComponentGenesis.argtypes = []
UnregisterMagickInfo = _lib.UnregisterMagickInfo
UnregisterMagickInfo.restype = MagickBooleanType
UnregisterMagickInfo.argtypes = [STRING]
GetMagickInfo = _lib.GetMagickInfo
GetMagickInfo.restype = POINTER(MagickInfo)
GetMagickInfo.argtypes = [STRING, POINTER(ExceptionInfo)]
GetMagickInfoList = _lib.GetMagickInfoList
GetMagickInfoList.restype = POINTER(POINTER(MagickInfo))
GetMagickInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
RegisterMagickInfo = _lib.RegisterMagickInfo
RegisterMagickInfo.restype = POINTER(MagickInfo)
RegisterMagickInfo.argtypes = [POINTER(MagickInfo)]
SetMagickInfo = _lib.SetMagickInfo
SetMagickInfo.restype = POINTER(MagickInfo)
SetMagickInfo.argtypes = [STRING]
GetMagickThreadSupport = _lib.GetMagickThreadSupport
GetMagickThreadSupport.restype = MagickStatusType
GetMagickThreadSupport.argtypes = [POINTER(MagickInfo)]
MagickComponentTerminus = _lib.MagickComponentTerminus
MagickComponentTerminus.restype = None
MagickComponentTerminus.argtypes = []
MagickCoreGenesis = _lib.MagickCoreGenesis
MagickCoreGenesis.restype = None
MagickCoreGenesis.argtypes = [STRING, MagickBooleanType]
MagickCoreTerminus = _lib.MagickCoreTerminus
MagickCoreTerminus.restype = None
MagickCoreTerminus.argtypes = []
AcquireMagickMatrix = _lib.AcquireMagickMatrix
AcquireMagickMatrix.restype = POINTER(POINTER(c_double))
AcquireMagickMatrix.argtypes = [size_t, size_t]
RelinquishMagickMatrix = _lib.RelinquishMagickMatrix
RelinquishMagickMatrix.restype = POINTER(POINTER(c_double))
RelinquishMagickMatrix.argtypes = [POINTER(POINTER(c_double)), size_t]
GaussJordanElimination = _lib.GaussJordanElimination
GaussJordanElimination.restype = MagickBooleanType
GaussJordanElimination.argtypes = [POINTER(POINTER(c_double)), POINTER(POINTER(c_double)), size_t, size_t]
LeastSquaresAddTerms = _lib.LeastSquaresAddTerms
LeastSquaresAddTerms.restype = None
LeastSquaresAddTerms.argtypes = [POINTER(POINTER(c_double)), POINTER(POINTER(c_double)), POINTER(c_double), POINTER(c_double), size_t, size_t]
AcquireAlignedMemory = _lib.AcquireAlignedMemory
AcquireAlignedMemory.restype = c_void_p
AcquireAlignedMemory.argtypes = [size_t, size_t]
AcquireMagickMemory = _lib.AcquireMagickMemory
AcquireMagickMemory.restype = c_void_p
AcquireMagickMemory.argtypes = [size_t]
AcquireQuantumMemory = _lib.AcquireQuantumMemory
AcquireQuantumMemory.restype = c_void_p
AcquireQuantumMemory.argtypes = [size_t, size_t]
CopyMagickMemory = _lib.CopyMagickMemory
CopyMagickMemory.restype = c_void_p
CopyMagickMemory.argtypes = [c_void_p, c_void_p, size_t]
DestroyMagickMemory = _lib.DestroyMagickMemory
DestroyMagickMemory.restype = None
DestroyMagickMemory.argtypes = []
AcquireMemoryHandler = CFUNCTYPE(c_void_p, size_t)
ResizeMemoryHandler = CFUNCTYPE(c_void_p, c_void_p, size_t)
DestroyMemoryHandler = CFUNCTYPE(None, c_void_p)
GetMagickMemoryMethods = _lib.GetMagickMemoryMethods
GetMagickMemoryMethods.restype = None
GetMagickMemoryMethods.argtypes = [POINTER(AcquireMemoryHandler), POINTER(ResizeMemoryHandler), POINTER(DestroyMemoryHandler)]
RelinquishAlignedMemory = _lib.RelinquishAlignedMemory
RelinquishAlignedMemory.restype = c_void_p
RelinquishAlignedMemory.argtypes = [c_void_p]
RelinquishMagickMemory = _lib.RelinquishMagickMemory
RelinquishMagickMemory.restype = c_void_p
RelinquishMagickMemory.argtypes = [c_void_p]
ResetMagickMemory = _lib.ResetMagickMemory
ResetMagickMemory.restype = c_void_p
ResetMagickMemory.argtypes = [c_void_p, c_int, size_t]
ResizeMagickMemory = _lib.ResizeMagickMemory
ResizeMagickMemory.restype = c_void_p
ResizeMagickMemory.argtypes = [c_void_p, size_t]
ResizeQuantumMemory = _lib.ResizeQuantumMemory
ResizeQuantumMemory.restype = c_void_p
ResizeQuantumMemory.argtypes = [c_void_p, size_t, size_t]
SetMagickMemoryMethods = _lib.SetMagickMemoryMethods
SetMagickMemoryMethods.restype = None
SetMagickMemoryMethods.argtypes = [AcquireMemoryHandler, ResizeMemoryHandler, DestroyMemoryHandler]
GetMimeList = _lib.GetMimeList
GetMimeList.restype = POINTER(STRING)
GetMimeList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
MagickToMime = _lib.MagickToMime
MagickToMime.restype = STRING
MagickToMime.argtypes = [STRING]
class _MimeInfo(Structure):
    pass
MimeInfo = _MimeInfo
GetMimeDescription = _lib.GetMimeDescription
GetMimeDescription.restype = STRING
GetMimeDescription.argtypes = [POINTER(MimeInfo)]
GetMimeType = _lib.GetMimeType
GetMimeType.restype = STRING
GetMimeType.argtypes = [POINTER(MimeInfo)]
ListMimeInfo = _lib.ListMimeInfo
ListMimeInfo.restype = MagickBooleanType
ListMimeInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
LoadMimeLists = _lib.LoadMimeLists
LoadMimeLists.restype = MagickBooleanType
LoadMimeLists.argtypes = [STRING, POINTER(ExceptionInfo)]
MimeComponentGenesis = _lib.MimeComponentGenesis
MimeComponentGenesis.restype = MagickBooleanType
MimeComponentGenesis.argtypes = []
GetMimeInfo = _lib.GetMimeInfo
GetMimeInfo.restype = POINTER(MimeInfo)
GetMimeInfo.argtypes = [STRING, POINTER(c_ubyte), size_t, POINTER(ExceptionInfo)]
GetMimeInfoList = _lib.GetMimeInfoList
GetMimeInfoList.restype = POINTER(POINTER(MimeInfo))
GetMimeInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
MimeComponentTerminus = _lib.MimeComponentTerminus
MimeComponentTerminus.restype = None
MimeComponentTerminus.argtypes = []

# values for enumeration 'MagickModuleType'
MagickImageCoderModule = 0
MagickImageFilterModule = 1
MagickModuleType = c_int # enum
GetModuleList = _lib.GetModuleList
GetModuleList.restype = POINTER(STRING)
GetModuleList.argtypes = [STRING, MagickModuleType, POINTER(size_t), POINTER(ExceptionInfo)]
class _ModuleInfo(Structure):
    pass
ModuleInfo = _ModuleInfo
GetModuleInfoList = _lib.GetModuleInfoList
GetModuleInfoList.restype = POINTER(POINTER(ModuleInfo))
GetModuleInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
InitializeModuleList = _lib.InitializeModuleList
InitializeModuleList.restype = MagickBooleanType
InitializeModuleList.argtypes = [POINTER(ExceptionInfo)]
InvokeDynamicImageFilter = _lib.InvokeDynamicImageFilter
InvokeDynamicImageFilter.restype = MagickBooleanType
InvokeDynamicImageFilter.argtypes = [STRING, POINTER(POINTER(Image)), c_int, POINTER(STRING), POINTER(ExceptionInfo)]
ListModuleInfo = _lib.ListModuleInfo
ListModuleInfo.restype = MagickBooleanType
ListModuleInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
ModuleComponentGenesis = _lib.ModuleComponentGenesis
ModuleComponentGenesis.restype = MagickBooleanType
ModuleComponentGenesis.argtypes = []
OpenModule = _lib.OpenModule
OpenModule.restype = MagickBooleanType
OpenModule.argtypes = [STRING, POINTER(ExceptionInfo)]
OpenModules = _lib.OpenModules
OpenModules.restype = MagickBooleanType
OpenModules.argtypes = [POINTER(ExceptionInfo)]
GetModuleInfo = _lib.GetModuleInfo
GetModuleInfo.restype = POINTER(ModuleInfo)
GetModuleInfo.argtypes = [STRING, POINTER(ExceptionInfo)]
DestroyModuleList = _lib.DestroyModuleList
DestroyModuleList.restype = None
DestroyModuleList.argtypes = []
ModuleComponentTerminus = _lib.ModuleComponentTerminus
ModuleComponentTerminus.restype = None
ModuleComponentTerminus.argtypes = []
RegisterStaticModules = _lib.RegisterStaticModules
RegisterStaticModules.restype = None
RegisterStaticModules.argtypes = []
UnregisterStaticModules = _lib.UnregisterStaticModules
UnregisterStaticModules.restype = None
UnregisterStaticModules.argtypes = []
MagickProgressMonitor = CFUNCTYPE(MagickBooleanType, STRING, MagickOffsetType, MagickSizeType, c_void_p)
SetImageProgressMonitor = _lib.SetImageProgressMonitor
SetImageProgressMonitor.restype = MagickProgressMonitor
SetImageProgressMonitor.argtypes = [POINTER(Image), MagickProgressMonitor, c_void_p]
SetImageInfoProgressMonitor = _lib.SetImageInfoProgressMonitor
SetImageInfoProgressMonitor.restype = MagickProgressMonitor
SetImageInfoProgressMonitor.argtypes = [POINTER(ImageInfo), MagickProgressMonitor, c_void_p]
class _MontageInfo(Structure):
    pass
MontageInfo = _MontageInfo
MontageImages = _lib.MontageImages
MontageImages.restype = POINTER(Image)
MontageImages.argtypes = [POINTER(Image), POINTER(MontageInfo), POINTER(ExceptionInfo)]
MontageImageList = _lib.MontageImageList
MontageImageList.restype = POINTER(Image)
MontageImageList.argtypes = [POINTER(ImageInfo), POINTER(MontageInfo), POINTER(Image), POINTER(ExceptionInfo)]
CloneMontageInfo = _lib.CloneMontageInfo
CloneMontageInfo.restype = POINTER(MontageInfo)
CloneMontageInfo.argtypes = [POINTER(ImageInfo), POINTER(MontageInfo)]
DestroyMontageInfo = _lib.DestroyMontageInfo
DestroyMontageInfo.restype = POINTER(MontageInfo)
DestroyMontageInfo.argtypes = [POINTER(MontageInfo)]
GetMontageInfo = _lib.GetMontageInfo
GetMontageInfo.restype = None
GetMontageInfo.argtypes = [POINTER(ImageInfo), POINTER(MontageInfo)]
AcquireKernelInfo = _lib.AcquireKernelInfo
AcquireKernelInfo.restype = POINTER(KernelInfo)
AcquireKernelInfo.argtypes = [STRING]

# values for enumeration 'KernelInfoType'
UndefinedKernel = 0
UnityKernel = 1
GaussianKernel = 2
DoGKernel = 3
LoGKernel = 4
BlurKernel = 5
CometKernel = 6
LaplacianKernel = 7
SobelKernel = 8
FreiChenKernel = 9
RobertsKernel = 10
PrewittKernel = 11
CompassKernel = 12
KirschKernel = 13
DiamondKernel = 14
SquareKernel = 15
RectangleKernel = 16
OctagonKernel = 17
DiskKernel = 18
PlusKernel = 19
CrossKernel = 20
RingKernel = 21
PeaksKernel = 22
EdgesKernel = 23
CornersKernel = 24
DiagonalsKernel = 25
LineEndsKernel = 26
LineJunctionsKernel = 27
RidgesKernel = 28
ConvexHullKernel = 29
ThinSEKernel = 30
SkeletonKernel = 31
ChebyshevKernel = 32
ManhattanKernel = 33
OctagonalKernel = 34
EuclideanKernel = 35
UserDefinedKernel = 36
KernelInfoType = c_int # enum
AcquireKernelBuiltIn = _lib.AcquireKernelBuiltIn
AcquireKernelBuiltIn.restype = POINTER(KernelInfo)
AcquireKernelBuiltIn.argtypes = [KernelInfoType, POINTER(GeometryInfo)]
CloneKernelInfo = _lib.CloneKernelInfo
CloneKernelInfo.restype = POINTER(KernelInfo)
CloneKernelInfo.argtypes = [POINTER(KernelInfo)]
DestroyKernelInfo = _lib.DestroyKernelInfo
DestroyKernelInfo.restype = POINTER(KernelInfo)
DestroyKernelInfo.argtypes = [POINTER(KernelInfo)]

# values for enumeration 'MorphologyMethod'
UndefinedMorphology = 0
ConvolveMorphology = 1
CorrelateMorphology = 2
ErodeMorphology = 3
DilateMorphology = 4
ErodeIntensityMorphology = 5
DilateIntensityMorphology = 6
DistanceMorphology = 7
OpenMorphology = 8
CloseMorphology = 9
OpenIntensityMorphology = 10
CloseIntensityMorphology = 11
SmoothMorphology = 12
EdgeInMorphology = 13
EdgeOutMorphology = 14
EdgeMorphology = 15
TopHatMorphology = 16
BottomHatMorphology = 17
HitAndMissMorphology = 18
ThinningMorphology = 19
ThickenMorphology = 20
VoronoiMorphology = 21
MorphologyMethod = c_int # enum
MorphologyImage = _lib.MorphologyImage
MorphologyImage.restype = POINTER(Image)
MorphologyImage.argtypes = [POINTER(Image), MorphologyMethod, ssize_t, POINTER(KernelInfo), POINTER(ExceptionInfo)]
MorphologyImageChannel = _lib.MorphologyImageChannel
MorphologyImageChannel.restype = POINTER(Image)
MorphologyImageChannel.argtypes = [POINTER(Image), ChannelType, MorphologyMethod, ssize_t, POINTER(KernelInfo), POINTER(ExceptionInfo)]
ScaleGeometryKernelInfo = _lib.ScaleGeometryKernelInfo
ScaleGeometryKernelInfo.restype = None
ScaleGeometryKernelInfo.argtypes = [POINTER(KernelInfo), STRING]
ShowKernelInfo = _lib.ShowKernelInfo
ShowKernelInfo.restype = None
ShowKernelInfo.argtypes = [POINTER(KernelInfo)]

# values for enumeration 'CommandOption'
MagickUndefinedOptions = -1
MagickAlignOptions = 0
MagickAlphaOptions = 1
MagickBooleanOptions = 2
MagickChannelOptions = 3
MagickClassOptions = 4
MagickClipPathOptions = 5
MagickCoderOptions = 6
MagickColorOptions = 7
MagickColorspaceOptions = 8
MagickCommandOptions = 9
MagickComposeOptions = 10
MagickCompressOptions = 11
MagickConfigureOptions = 12
MagickDataTypeOptions = 13
MagickDebugOptions = 14
MagickDecorateOptions = 15
MagickDelegateOptions = 16
MagickDirectionOptions = 17
MagickDisposeOptions = 18
MagickDistortOptions = 19
MagickDitherOptions = 20
MagickEndianOptions = 21
MagickEvaluateOptions = 22
MagickFillRuleOptions = 23
MagickFilterOptions = 24
MagickFontOptions = 25
MagickFontsOptions = 26
MagickFormatOptions = 27
MagickFunctionOptions = 28
MagickGravityOptions = 29
MagickIntentOptions = 30
MagickInterlaceOptions = 31
MagickInterpolateOptions = 32
MagickKernelOptions = 33
MagickLayerOptions = 34
MagickLineCapOptions = 35
MagickLineJoinOptions = 36
MagickListOptions = 37
MagickLocaleOptions = 38
MagickLogEventOptions = 39
MagickLogOptions = 40
MagickMagicOptions = 41
MagickMethodOptions = 42
MagickMetricOptions = 43
MagickMimeOptions = 44
MagickModeOptions = 45
MagickModuleOptions = 46
MagickMorphologyOptions = 47
MagickNoiseOptions = 48
MagickOrientationOptions = 49
MagickPolicyOptions = 50
MagickPolicyDomainOptions = 51
MagickPolicyRightsOptions = 52
MagickPreviewOptions = 53
MagickPrimitiveOptions = 54
MagickQuantumFormatOptions = 55
MagickResolutionOptions = 56
MagickResourceOptions = 57
MagickSparseColorOptions = 58
MagickStatisticOptions = 59
MagickStorageOptions = 60
MagickStretchOptions = 61
MagickStyleOptions = 62
MagickThresholdOptions = 63
MagickTypeOptions = 64
MagickValidateOptions = 65
MagickVirtualPixelOptions = 66
CommandOption = c_int # enum
GetCommandOptions = _lib.GetCommandOptions
GetCommandOptions.restype = POINTER(STRING)
GetCommandOptions.argtypes = [CommandOption]
GetNextImageOption = _lib.GetNextImageOption
GetNextImageOption.restype = STRING
GetNextImageOption.argtypes = [POINTER(ImageInfo)]
RemoveImageOption = _lib.RemoveImageOption
RemoveImageOption.restype = STRING
RemoveImageOption.argtypes = [POINTER(ImageInfo), STRING]
CommandOptionToMnemonic = _lib.CommandOptionToMnemonic
CommandOptionToMnemonic.restype = STRING
CommandOptionToMnemonic.argtypes = [CommandOption, ssize_t]
GetImageOption = _lib.GetImageOption
GetImageOption.restype = STRING
GetImageOption.argtypes = [POINTER(ImageInfo), STRING]
CloneImageOptions = _lib.CloneImageOptions
CloneImageOptions.restype = MagickBooleanType
CloneImageOptions.argtypes = [POINTER(ImageInfo), POINTER(ImageInfo)]
DefineImageOption = _lib.DefineImageOption
DefineImageOption.restype = MagickBooleanType
DefineImageOption.argtypes = [POINTER(ImageInfo), STRING]
DeleteImageOption = _lib.DeleteImageOption
DeleteImageOption.restype = MagickBooleanType
DeleteImageOption.argtypes = [POINTER(ImageInfo), STRING]
IsCommandOption = _lib.IsCommandOption
IsCommandOption.restype = MagickBooleanType
IsCommandOption.argtypes = [STRING]
ListCommandOptions = _lib.ListCommandOptions
ListCommandOptions.restype = MagickBooleanType
ListCommandOptions.argtypes = [POINTER(FILE), CommandOption, POINTER(ExceptionInfo)]
SetImageOption = _lib.SetImageOption
SetImageOption.restype = MagickBooleanType
SetImageOption.argtypes = [POINTER(ImageInfo), STRING, STRING]
GetCommandOptionFlags = _lib.GetCommandOptionFlags
GetCommandOptionFlags.restype = ssize_t
GetCommandOptionFlags.argtypes = [CommandOption, MagickBooleanType, STRING]
ParseChannelOption = _lib.ParseChannelOption
ParseChannelOption.restype = ssize_t
ParseChannelOption.argtypes = [STRING]
ParseCommandOption = _lib.ParseCommandOption
ParseCommandOption.restype = ssize_t
ParseCommandOption.argtypes = [CommandOption, MagickBooleanType, STRING]
DestroyImageOptions = _lib.DestroyImageOptions
DestroyImageOptions.restype = None
DestroyImageOptions.argtypes = [POINTER(ImageInfo)]
ResetImageOptions = _lib.ResetImageOptions
ResetImageOptions.restype = None
ResetImageOptions.argtypes = [POINTER(ImageInfo)]
ResetImageOptionIterator = _lib.ResetImageOptionIterator
ResetImageOptionIterator.restype = None
ResetImageOptionIterator.argtypes = [POINTER(ImageInfo)]
OilPaintImage = _lib.OilPaintImage
OilPaintImage.restype = POINTER(Image)
OilPaintImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
FloodfillPaintImage = _lib.FloodfillPaintImage
FloodfillPaintImage.restype = MagickBooleanType
FloodfillPaintImage.argtypes = [POINTER(Image), ChannelType, POINTER(DrawInfo), POINTER(MagickPixelPacket), ssize_t, ssize_t, MagickBooleanType]

# values for enumeration 'GradientType'
UndefinedGradient = 0
LinearGradient = 1
RadialGradient = 2
GradientType = c_int # enum

# values for enumeration 'SpreadMethod'
UndefinedSpread = 0
PadSpread = 1
ReflectSpread = 2
RepeatSpread = 3
SpreadMethod = c_int # enum
GradientImage = _lib.GradientImage
GradientImage.restype = MagickBooleanType
GradientImage.argtypes = [POINTER(Image), GradientType, SpreadMethod, POINTER(PixelPacket), POINTER(PixelPacket)]
OpaquePaintImage = _lib.OpaquePaintImage
OpaquePaintImage.restype = MagickBooleanType
OpaquePaintImage.argtypes = [POINTER(Image), POINTER(MagickPixelPacket), POINTER(MagickPixelPacket), MagickBooleanType]
OpaquePaintImageChannel = _lib.OpaquePaintImageChannel
OpaquePaintImageChannel.restype = MagickBooleanType
OpaquePaintImageChannel.argtypes = [POINTER(Image), ChannelType, POINTER(MagickPixelPacket), POINTER(MagickPixelPacket), MagickBooleanType]
TransparentPaintImage = _lib.TransparentPaintImage
TransparentPaintImage.restype = MagickBooleanType
TransparentPaintImage.argtypes = [POINTER(Image), POINTER(MagickPixelPacket), Quantum, MagickBooleanType]
TransparentPaintImageChroma = _lib.TransparentPaintImageChroma
TransparentPaintImageChroma.restype = MagickBooleanType
TransparentPaintImageChroma.argtypes = [POINTER(Image), POINTER(MagickPixelPacket), POINTER(MagickPixelPacket), Quantum, MagickBooleanType]
ExportImagePixels = _lib.ExportImagePixels
ExportImagePixels.restype = MagickBooleanType
ExportImagePixels.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t, STRING, StorageType, c_void_p, POINTER(ExceptionInfo)]
ImportImagePixels = _lib.ImportImagePixels
ImportImagePixels.restype = MagickBooleanType
ImportImagePixels.argtypes = [POINTER(Image), ssize_t, ssize_t, size_t, size_t, STRING, StorageType, c_void_p]
CacheView_ = _CacheView
InterpolateMagickPixelPacket = _lib.InterpolateMagickPixelPacket
InterpolateMagickPixelPacket.restype = MagickBooleanType
InterpolateMagickPixelPacket.argtypes = [POINTER(Image), POINTER(CacheView_), InterpolatePixelMethod, c_double, c_double, POINTER(MagickPixelPacket), POINTER(ExceptionInfo)]
GetMagickPixelPacket = _lib.GetMagickPixelPacket
GetMagickPixelPacket.restype = None
GetMagickPixelPacket.argtypes = [POINTER(Image), POINTER(MagickPixelPacket)]
GetPolicyValue = _lib.GetPolicyValue
GetPolicyValue.restype = STRING
GetPolicyValue.argtypes = [STRING]
GetPolicyList = _lib.GetPolicyList
GetPolicyList.restype = POINTER(STRING)
GetPolicyList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
class _PolicyInfo(Structure):
    pass
PolicyInfo = _PolicyInfo
GetPolicyInfoList = _lib.GetPolicyInfoList
GetPolicyInfoList.restype = POINTER(POINTER(PolicyInfo))
GetPolicyInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]

# values for enumeration 'PolicyDomain'
UndefinedPolicyDomain = 0
CoderPolicyDomain = 1
DelegatePolicyDomain = 2
FilterPolicyDomain = 3
PathPolicyDomain = 4
ResourcePolicyDomain = 5
SystemPolicyDomain = 6
PolicyDomain = c_int # enum

# values for enumeration 'PolicyRights'
UndefinedPolicyRights = 0
NoPolicyRights = 0
ReadPolicyRights = 1
WritePolicyRights = 2
ExecutePolicyRights = 4
PolicyRights = c_int # enum
IsRightsAuthorized = _lib.IsRightsAuthorized
IsRightsAuthorized.restype = MagickBooleanType
IsRightsAuthorized.argtypes = [PolicyDomain, PolicyRights, STRING]
ListPolicyInfo = _lib.ListPolicyInfo
ListPolicyInfo.restype = MagickBooleanType
ListPolicyInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
PolicyComponentGenesis = _lib.PolicyComponentGenesis
PolicyComponentGenesis.restype = MagickBooleanType
PolicyComponentGenesis.argtypes = []
PolicyComponentTerminus = _lib.PolicyComponentTerminus
PolicyComponentTerminus.restype = None
PolicyComponentTerminus.argtypes = []
GetImageTotalInkDensity = _lib.GetImageTotalInkDensity
GetImageTotalInkDensity.restype = c_double
GetImageTotalInkDensity.argtypes = [POINTER(Image)]
GetNextImageProfile = _lib.GetNextImageProfile
GetNextImageProfile.restype = STRING
GetNextImageProfile.argtypes = [POINTER(Image)]
GetImageProfile = _lib.GetImageProfile
GetImageProfile.restype = POINTER(StringInfo)
GetImageProfile.argtypes = [POINTER(Image), STRING]
CloneImageProfiles = _lib.CloneImageProfiles
CloneImageProfiles.restype = MagickBooleanType
CloneImageProfiles.argtypes = [POINTER(Image), POINTER(Image)]
DeleteImageProfile = _lib.DeleteImageProfile
DeleteImageProfile.restype = MagickBooleanType
DeleteImageProfile.argtypes = [POINTER(Image), STRING]
ProfileImage = _lib.ProfileImage
ProfileImage.restype = MagickBooleanType
ProfileImage.argtypes = [POINTER(Image), STRING, c_void_p, size_t, MagickBooleanType]
SetImageProfile = _lib.SetImageProfile
SetImageProfile.restype = MagickBooleanType
SetImageProfile.argtypes = [POINTER(Image), STRING, POINTER(StringInfo)]
SyncImageProfiles = _lib.SyncImageProfiles
SyncImageProfiles.restype = MagickBooleanType
SyncImageProfiles.argtypes = [POINTER(Image)]
RemoveImageProfile = _lib.RemoveImageProfile
RemoveImageProfile.restype = POINTER(StringInfo)
RemoveImageProfile.argtypes = [POINTER(Image), STRING]
DestroyImageProfiles = _lib.DestroyImageProfiles
DestroyImageProfiles.restype = None
DestroyImageProfiles.argtypes = [POINTER(Image)]
ResetImageProfileIterator = _lib.ResetImageProfileIterator
ResetImageProfileIterator.restype = None
ResetImageProfileIterator.argtypes = [POINTER(Image)]
GetNextImageProperty = _lib.GetNextImageProperty
GetNextImageProperty.restype = STRING
GetNextImageProperty.argtypes = [POINTER(Image)]
InterpretImageProperties = _lib.InterpretImageProperties
InterpretImageProperties.restype = STRING
InterpretImageProperties.argtypes = [POINTER(ImageInfo), POINTER(Image), STRING]
RemoveImageProperty = _lib.RemoveImageProperty
RemoveImageProperty.restype = STRING
RemoveImageProperty.argtypes = [POINTER(Image), STRING]
GetImageProperty = _lib.GetImageProperty
GetImageProperty.restype = STRING
GetImageProperty.argtypes = [POINTER(Image), STRING]
GetMagickProperty = _lib.GetMagickProperty
GetMagickProperty.restype = STRING
GetMagickProperty.argtypes = [POINTER(ImageInfo), POINTER(Image), STRING]
CloneImageProperties = _lib.CloneImageProperties
CloneImageProperties.restype = MagickBooleanType
CloneImageProperties.argtypes = [POINTER(Image), POINTER(Image)]
DefineImageProperty = _lib.DefineImageProperty
DefineImageProperty.restype = MagickBooleanType
DefineImageProperty.argtypes = [POINTER(Image), STRING]
DeleteImageProperty = _lib.DeleteImageProperty
DeleteImageProperty.restype = MagickBooleanType
DeleteImageProperty.argtypes = [POINTER(Image), STRING]
FormatImageProperty = _lib.FormatImageProperty
FormatImageProperty.restype = MagickBooleanType
FormatImageProperty.argtypes = [POINTER(Image), STRING, STRING]
SetImageProperty = _lib.SetImageProperty
SetImageProperty.restype = MagickBooleanType
SetImageProperty.argtypes = [POINTER(Image), STRING, STRING]
DestroyImageProperties = _lib.DestroyImageProperties
DestroyImageProperties.restype = None
DestroyImageProperties.argtypes = [POINTER(Image)]
ResetImagePropertyIterator = _lib.ResetImagePropertyIterator
ResetImagePropertyIterator.restype = None
ResetImagePropertyIterator.argtypes = [POINTER(Image)]
CompressImageColormap = _lib.CompressImageColormap
CompressImageColormap.restype = MagickBooleanType
CompressImageColormap.argtypes = [POINTER(Image)]
GetImageQuantizeError = _lib.GetImageQuantizeError
GetImageQuantizeError.restype = MagickBooleanType
GetImageQuantizeError.argtypes = [POINTER(Image)]
PosterizeImage = _lib.PosterizeImage
PosterizeImage.restype = MagickBooleanType
PosterizeImage.argtypes = [POINTER(Image), size_t, MagickBooleanType]
PosterizeImageChannel = _lib.PosterizeImageChannel
PosterizeImageChannel.restype = MagickBooleanType
PosterizeImageChannel.argtypes = [POINTER(Image), ChannelType, size_t, MagickBooleanType]
QuantizeImage = _lib.QuantizeImage
QuantizeImage.restype = MagickBooleanType
QuantizeImage.argtypes = [POINTER(QuantizeInfo), POINTER(Image)]
QuantizeImages = _lib.QuantizeImages
QuantizeImages.restype = MagickBooleanType
QuantizeImages.argtypes = [POINTER(QuantizeInfo), POINTER(Image)]
RemapImage = _lib.RemapImage
RemapImage.restype = MagickBooleanType
RemapImage.argtypes = [POINTER(QuantizeInfo), POINTER(Image), POINTER(Image)]
RemapImages = _lib.RemapImages
RemapImages.restype = MagickBooleanType
RemapImages.argtypes = [POINTER(QuantizeInfo), POINTER(Image), POINTER(Image)]
AcquireQuantizeInfo = _lib.AcquireQuantizeInfo
AcquireQuantizeInfo.restype = POINTER(QuantizeInfo)
AcquireQuantizeInfo.argtypes = [POINTER(ImageInfo)]
CloneQuantizeInfo = _lib.CloneQuantizeInfo
CloneQuantizeInfo.restype = POINTER(QuantizeInfo)
CloneQuantizeInfo.argtypes = [POINTER(QuantizeInfo)]
DestroyQuantizeInfo = _lib.DestroyQuantizeInfo
DestroyQuantizeInfo.restype = POINTER(QuantizeInfo)
DestroyQuantizeInfo.argtypes = [POINTER(QuantizeInfo)]
GetQuantizeInfo = _lib.GetQuantizeInfo
GetQuantizeInfo.restype = None
GetQuantizeInfo.argtypes = [POINTER(QuantizeInfo)]
class _QuantumInfo(Structure):
    pass
QuantumInfo = _QuantumInfo
SetQuantumDepth = _lib.SetQuantumDepth
SetQuantumDepth.restype = MagickBooleanType
SetQuantumDepth.argtypes = [POINTER(Image), POINTER(QuantumInfo), size_t]

# values for enumeration 'QuantumFormatType'
UndefinedQuantumFormat = 0
FloatingPointQuantumFormat = 1
SignedQuantumFormat = 2
UnsignedQuantumFormat = 3
QuantumFormatType = c_int # enum
SetQuantumFormat = _lib.SetQuantumFormat
SetQuantumFormat.restype = MagickBooleanType
SetQuantumFormat.argtypes = [POINTER(Image), POINTER(QuantumInfo), QuantumFormatType]
SetQuantumPad = _lib.SetQuantumPad
SetQuantumPad.restype = MagickBooleanType
SetQuantumPad.argtypes = [POINTER(Image), POINTER(QuantumInfo), size_t]
GetQuantumFormat = _lib.GetQuantumFormat
GetQuantumFormat.restype = QuantumFormatType
GetQuantumFormat.argtypes = [POINTER(QuantumInfo)]
AcquireQuantumInfo = _lib.AcquireQuantumInfo
AcquireQuantumInfo.restype = POINTER(QuantumInfo)
AcquireQuantumInfo.argtypes = [POINTER(ImageInfo), POINTER(Image)]
DestroyQuantumInfo = _lib.DestroyQuantumInfo
DestroyQuantumInfo.restype = POINTER(QuantumInfo)
DestroyQuantumInfo.argtypes = [POINTER(QuantumInfo)]
GetQuantumType = _lib.GetQuantumType
GetQuantumType.restype = QuantumType
GetQuantumType.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
ExportQuantumPixels = _lib.ExportQuantumPixels
ExportQuantumPixels.restype = size_t
ExportQuantumPixels.argtypes = [POINTER(Image), POINTER(CacheView), POINTER(QuantumInfo), QuantumType, POINTER(c_ubyte), POINTER(ExceptionInfo)]
GetQuantumExtent = _lib.GetQuantumExtent
GetQuantumExtent.restype = size_t
GetQuantumExtent.argtypes = [POINTER(Image), POINTER(QuantumInfo), QuantumType]
ImportQuantumPixels = _lib.ImportQuantumPixels
ImportQuantumPixels.restype = size_t
ImportQuantumPixels.argtypes = [POINTER(Image), POINTER(CacheView), POINTER(QuantumInfo), QuantumType, POINTER(c_ubyte), POINTER(ExceptionInfo)]
GetQuantumPixels = _lib.GetQuantumPixels
GetQuantumPixels.restype = POINTER(c_ubyte)
GetQuantumPixels.argtypes = [POINTER(QuantumInfo)]
GetQuantumInfo = _lib.GetQuantumInfo
GetQuantumInfo.restype = None
GetQuantumInfo.argtypes = [POINTER(ImageInfo), POINTER(QuantumInfo)]

# values for enumeration 'QuantumAlphaType'
UndefinedQuantumAlpha = 0
AssociatedQuantumAlpha = 1
DisassociatedQuantumAlpha = 2
QuantumAlphaType = c_int # enum
SetQuantumAlphaType = _lib.SetQuantumAlphaType
SetQuantumAlphaType.restype = None
SetQuantumAlphaType.argtypes = [POINTER(QuantumInfo), QuantumAlphaType]
SetQuantumImageType = _lib.SetQuantumImageType
SetQuantumImageType.restype = None
SetQuantumImageType.argtypes = [POINTER(Image), QuantumType]
SetQuantumMinIsWhite = _lib.SetQuantumMinIsWhite
SetQuantumMinIsWhite.restype = None
SetQuantumMinIsWhite.argtypes = [POINTER(QuantumInfo), MagickBooleanType]
SetQuantumPack = _lib.SetQuantumPack
SetQuantumPack.restype = None
SetQuantumPack.argtypes = [POINTER(QuantumInfo), MagickBooleanType]
SetQuantumQuantum = _lib.SetQuantumQuantum
SetQuantumQuantum.restype = None
SetQuantumQuantum.argtypes = [POINTER(QuantumInfo), size_t]
SetQuantumScale = _lib.SetQuantumScale
SetQuantumScale.restype = None
SetQuantumScale.argtypes = [POINTER(QuantumInfo), c_double]
GetRandomValue = _lib.GetRandomValue
GetRandomValue.restype = c_double
GetRandomValue.argtypes = [POINTER(RandomInfo)]
GetPseudoRandomValue = _lib.GetPseudoRandomValue
GetPseudoRandomValue.restype = c_double
GetPseudoRandomValue.argtypes = [POINTER(RandomInfo)]
RandomComponentGenesis = _lib.RandomComponentGenesis
RandomComponentGenesis.restype = MagickBooleanType
RandomComponentGenesis.argtypes = []
AcquireRandomInfo = _lib.AcquireRandomInfo
AcquireRandomInfo.restype = POINTER(RandomInfo)
AcquireRandomInfo.argtypes = []
DestroyRandomInfo = _lib.DestroyRandomInfo
DestroyRandomInfo.restype = POINTER(RandomInfo)
DestroyRandomInfo.argtypes = [POINTER(RandomInfo)]
GetRandomKey = _lib.GetRandomKey
GetRandomKey.restype = POINTER(StringInfo)
GetRandomKey.argtypes = [POINTER(RandomInfo), size_t]
RandomComponentTerminus = _lib.RandomComponentTerminus
RandomComponentTerminus.restype = None
RandomComponentTerminus.argtypes = []
SeedPseudoRandomGenerator = _lib.SeedPseudoRandomGenerator
SeedPseudoRandomGenerator.restype = None
SeedPseudoRandomGenerator.argtypes = [c_ulong]
SetRandomKey = _lib.SetRandomKey
SetRandomKey.restype = None
SetRandomKey.argtypes = [POINTER(RandomInfo), size_t, POINTER(c_ubyte)]
SetRandomTrueRandom = _lib.SetRandomTrueRandom
SetRandomTrueRandom.restype = None
SetRandomTrueRandom.argtypes = [MagickBooleanType]
GetNextImageRegistry = _lib.GetNextImageRegistry
GetNextImageRegistry.restype = STRING
GetNextImageRegistry.argtypes = []
DefineImageRegistry = _lib.DefineImageRegistry
DefineImageRegistry.restype = MagickBooleanType
DefineImageRegistry.argtypes = [RegistryType, STRING, POINTER(ExceptionInfo)]
DeleteImageRegistry = _lib.DeleteImageRegistry
DeleteImageRegistry.restype = MagickBooleanType
DeleteImageRegistry.argtypes = [STRING]
RegistryComponentGenesis = _lib.RegistryComponentGenesis
RegistryComponentGenesis.restype = MagickBooleanType
RegistryComponentGenesis.argtypes = []
SetImageRegistry = _lib.SetImageRegistry
SetImageRegistry.restype = MagickBooleanType
SetImageRegistry.argtypes = [RegistryType, STRING, c_void_p, POINTER(ExceptionInfo)]
GetImageRegistry = _lib.GetImageRegistry
GetImageRegistry.restype = c_void_p
GetImageRegistry.argtypes = [RegistryType, STRING, POINTER(ExceptionInfo)]
RegistryComponentTerminus = _lib.RegistryComponentTerminus
RegistryComponentTerminus.restype = None
RegistryComponentTerminus.argtypes = []
RemoveImageRegistry = _lib.RemoveImageRegistry
RemoveImageRegistry.restype = c_void_p
RemoveImageRegistry.argtypes = [STRING]
ResetImageRegistryIterator = _lib.ResetImageRegistryIterator
ResetImageRegistryIterator.restype = None
ResetImageRegistryIterator.argtypes = []
class _ResampleFilter(Structure):
    pass
ResampleFilter = _ResampleFilter
ResamplePixelColor = _lib.ResamplePixelColor
ResamplePixelColor.restype = MagickBooleanType
ResamplePixelColor.argtypes = [POINTER(ResampleFilter), c_double, c_double, POINTER(MagickPixelPacket)]
SetResampleFilterInterpolateMethod = _lib.SetResampleFilterInterpolateMethod
SetResampleFilterInterpolateMethod.restype = MagickBooleanType
SetResampleFilterInterpolateMethod.argtypes = [POINTER(ResampleFilter), InterpolatePixelMethod]
SetResampleFilterVirtualPixelMethod = _lib.SetResampleFilterVirtualPixelMethod
SetResampleFilterVirtualPixelMethod.restype = MagickBooleanType
SetResampleFilterVirtualPixelMethod.argtypes = [POINTER(ResampleFilter), VirtualPixelMethod]
AcquireResampleFilter = _lib.AcquireResampleFilter
AcquireResampleFilter.restype = POINTER(ResampleFilter)
AcquireResampleFilter.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
DestroyResampleFilter = _lib.DestroyResampleFilter
DestroyResampleFilter.restype = POINTER(ResampleFilter)
DestroyResampleFilter.argtypes = [POINTER(ResampleFilter)]
ScaleResampleFilter = _lib.ScaleResampleFilter
ScaleResampleFilter.restype = None
ScaleResampleFilter.argtypes = [POINTER(ResampleFilter), c_double, c_double, c_double, c_double]

# values for enumeration 'FilterTypes'
UndefinedFilter = 0
PointFilter = 1
BoxFilter = 2
TriangleFilter = 3
HermiteFilter = 4
HanningFilter = 5
HammingFilter = 6
BlackmanFilter = 7
GaussianFilter = 8
QuadraticFilter = 9
CubicFilter = 10
CatromFilter = 11
MitchellFilter = 12
JincFilter = 13
SincFilter = 14
SincFastFilter = 15
KaiserFilter = 16
WelshFilter = 17
ParzenFilter = 18
BohmanFilter = 19
BartlettFilter = 20
LagrangeFilter = 21
LanczosFilter = 22
LanczosSharpFilter = 23
Lanczos2Filter = 24
Lanczos2SharpFilter = 25
RobidouxFilter = 26
SentinelFilter = 27
FilterTypes = c_int # enum
SetResampleFilter = _lib.SetResampleFilter
SetResampleFilter.restype = None
SetResampleFilter.argtypes = [POINTER(ResampleFilter), FilterTypes, c_double]
AdaptiveResizeImage = _lib.AdaptiveResizeImage
AdaptiveResizeImage.restype = POINTER(Image)
AdaptiveResizeImage.argtypes = [POINTER(Image), size_t, size_t, POINTER(ExceptionInfo)]
LiquidRescaleImage = _lib.LiquidRescaleImage
LiquidRescaleImage.restype = POINTER(Image)
LiquidRescaleImage.argtypes = [POINTER(Image), size_t, size_t, c_double, c_double, POINTER(ExceptionInfo)]
MagnifyImage = _lib.MagnifyImage
MagnifyImage.restype = POINTER(Image)
MagnifyImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
MinifyImage = _lib.MinifyImage
MinifyImage.restype = POINTER(Image)
MinifyImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
ResampleImage = _lib.ResampleImage
ResampleImage.restype = POINTER(Image)
ResampleImage.argtypes = [POINTER(Image), c_double, c_double, FilterTypes, c_double, POINTER(ExceptionInfo)]
ResizeImage = _lib.ResizeImage
ResizeImage.restype = POINTER(Image)
ResizeImage.argtypes = [POINTER(Image), size_t, size_t, FilterTypes, c_double, POINTER(ExceptionInfo)]
SampleImage = _lib.SampleImage
SampleImage.restype = POINTER(Image)
SampleImage.argtypes = [POINTER(Image), size_t, size_t, POINTER(ExceptionInfo)]
ScaleImage = _lib.ScaleImage
ScaleImage.restype = POINTER(Image)
ScaleImage.argtypes = [POINTER(Image), size_t, size_t, POINTER(ExceptionInfo)]
ThumbnailImage = _lib.ThumbnailImage
ThumbnailImage.restype = POINTER(Image)
ThumbnailImage.argtypes = [POINTER(Image), size_t, size_t, POINTER(ExceptionInfo)]
AcquireUniqueFileResource = _lib.AcquireUniqueFileResource
AcquireUniqueFileResource.restype = c_int
AcquireUniqueFileResource.argtypes = [STRING]

# values for enumeration 'ResourceType'
UndefinedResource = 0
AreaResource = 1
DiskResource = 2
FileResource = 3
MapResource = 4
MemoryResource = 5
ThreadResource = 6
TimeResource = 7
ThrottleResource = 8
ResourceType = c_int # enum
AcquireMagickResource = _lib.AcquireMagickResource
AcquireMagickResource.restype = MagickBooleanType
AcquireMagickResource.argtypes = [ResourceType, MagickSizeType]
ListMagickResourceInfo = _lib.ListMagickResourceInfo
ListMagickResourceInfo.restype = MagickBooleanType
ListMagickResourceInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
RelinquishUniqueFileResource = _lib.RelinquishUniqueFileResource
RelinquishUniqueFileResource.restype = MagickBooleanType
RelinquishUniqueFileResource.argtypes = [STRING]
ResourceComponentGenesis = _lib.ResourceComponentGenesis
ResourceComponentGenesis.restype = MagickBooleanType
ResourceComponentGenesis.argtypes = []
SetMagickResourceLimit = _lib.SetMagickResourceLimit
SetMagickResourceLimit.restype = MagickBooleanType
SetMagickResourceLimit.argtypes = [ResourceType, MagickSizeType]
GetMagickResource = _lib.GetMagickResource
GetMagickResource.restype = MagickSizeType
GetMagickResource.argtypes = [ResourceType]
GetMagickResourceLimit = _lib.GetMagickResourceLimit
GetMagickResourceLimit.restype = MagickSizeType
GetMagickResourceLimit.argtypes = [ResourceType]
AsynchronousResourceComponentTerminus = _lib.AsynchronousResourceComponentTerminus
AsynchronousResourceComponentTerminus.restype = None
AsynchronousResourceComponentTerminus.argtypes = []
RelinquishMagickResource = _lib.RelinquishMagickResource
RelinquishMagickResource.restype = None
RelinquishMagickResource.argtypes = [ResourceType, MagickSizeType]
ResourceComponentTerminus = _lib.ResourceComponentTerminus
ResourceComponentTerminus.restype = None
ResourceComponentTerminus.argtypes = []
GetImageDynamicThreshold = _lib.GetImageDynamicThreshold
GetImageDynamicThreshold.restype = MagickBooleanType
GetImageDynamicThreshold.argtypes = [POINTER(Image), c_double, c_double, POINTER(MagickPixelPacket), POINTER(ExceptionInfo)]
SegmentImage = _lib.SegmentImage
SegmentImage.restype = MagickBooleanType
SegmentImage.argtypes = [POINTER(Image), ColorspaceType, MagickBooleanType, c_double, c_double]
SemaphoreComponentGenesis = _lib.SemaphoreComponentGenesis
SemaphoreComponentGenesis.restype = MagickBooleanType
SemaphoreComponentGenesis.argtypes = []
AllocateSemaphoreInfo = _lib.AllocateSemaphoreInfo
AllocateSemaphoreInfo.restype = POINTER(SemaphoreInfo)
AllocateSemaphoreInfo.argtypes = []
AcquireSemaphoreInfo = _lib.AcquireSemaphoreInfo
AcquireSemaphoreInfo.restype = None
AcquireSemaphoreInfo.argtypes = [POINTER(POINTER(SemaphoreInfo))]
DestroySemaphoreInfo = _lib.DestroySemaphoreInfo
DestroySemaphoreInfo.restype = None
DestroySemaphoreInfo.argtypes = [POINTER(POINTER(SemaphoreInfo))]
LockSemaphoreInfo = _lib.LockSemaphoreInfo
LockSemaphoreInfo.restype = None
LockSemaphoreInfo.argtypes = [POINTER(SemaphoreInfo)]
RelinquishSemaphoreInfo = _lib.RelinquishSemaphoreInfo
RelinquishSemaphoreInfo.restype = None
RelinquishSemaphoreInfo.argtypes = [POINTER(SemaphoreInfo)]
SemaphoreComponentTerminus = _lib.SemaphoreComponentTerminus
SemaphoreComponentTerminus.restype = None
SemaphoreComponentTerminus.argtypes = []
UnlockSemaphoreInfo = _lib.UnlockSemaphoreInfo
UnlockSemaphoreInfo.restype = None
UnlockSemaphoreInfo.argtypes = [POINTER(SemaphoreInfo)]
DeskewImage = _lib.DeskewImage
DeskewImage.restype = POINTER(Image)
DeskewImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
IntegralRotateImage = _lib.IntegralRotateImage
IntegralRotateImage.restype = POINTER(Image)
IntegralRotateImage.argtypes = [POINTER(Image), size_t, POINTER(ExceptionInfo)]
ShearImage = _lib.ShearImage
ShearImage.restype = POINTER(Image)
ShearImage.argtypes = [POINTER(Image), c_double, c_double, POINTER(ExceptionInfo)]
ShearRotateImage = _lib.ShearRotateImage
ShearRotateImage.restype = POINTER(Image)
ShearRotateImage.argtypes = [POINTER(Image), c_double, POINTER(ExceptionInfo)]
SignatureImage = _lib.SignatureImage
SignatureImage.restype = MagickBooleanType
SignatureImage.argtypes = [POINTER(Image)]
class _SplayTreeInfo(Structure):
    pass
SplayTreeInfo = _SplayTreeInfo
AddValueToSplayTree = _lib.AddValueToSplayTree
AddValueToSplayTree.restype = MagickBooleanType
AddValueToSplayTree.argtypes = [POINTER(SplayTreeInfo), c_void_p, c_void_p]
DeleteNodeByValueFromSplayTree = _lib.DeleteNodeByValueFromSplayTree
DeleteNodeByValueFromSplayTree.restype = MagickBooleanType
DeleteNodeByValueFromSplayTree.argtypes = [POINTER(SplayTreeInfo), c_void_p]
DeleteNodeFromSplayTree = _lib.DeleteNodeFromSplayTree
DeleteNodeFromSplayTree.restype = MagickBooleanType
DeleteNodeFromSplayTree.argtypes = [POINTER(SplayTreeInfo), c_void_p]
GetNextKeyInSplayTree = _lib.GetNextKeyInSplayTree
GetNextKeyInSplayTree.restype = c_void_p
GetNextKeyInSplayTree.argtypes = [POINTER(SplayTreeInfo)]
GetNextValueInSplayTree = _lib.GetNextValueInSplayTree
GetNextValueInSplayTree.restype = c_void_p
GetNextValueInSplayTree.argtypes = [POINTER(SplayTreeInfo)]
GetValueFromSplayTree = _lib.GetValueFromSplayTree
GetValueFromSplayTree.restype = c_void_p
GetValueFromSplayTree.argtypes = [POINTER(SplayTreeInfo), c_void_p]
CompareSplayTreeString = _lib.CompareSplayTreeString
CompareSplayTreeString.restype = c_int
CompareSplayTreeString.argtypes = [c_void_p, c_void_p]
CompareSplayTreeStringInfo = _lib.CompareSplayTreeStringInfo
CompareSplayTreeStringInfo.restype = c_int
CompareSplayTreeStringInfo.argtypes = [c_void_p, c_void_p]
CloneSplayTree = _lib.CloneSplayTree
CloneSplayTree.restype = POINTER(SplayTreeInfo)
CloneSplayTree.argtypes = [POINTER(SplayTreeInfo), CFUNCTYPE(c_void_p, c_void_p), CFUNCTYPE(c_void_p, c_void_p)]
DestroySplayTree = _lib.DestroySplayTree
DestroySplayTree.restype = POINTER(SplayTreeInfo)
DestroySplayTree.argtypes = [POINTER(SplayTreeInfo)]
NewSplayTree = _lib.NewSplayTree
NewSplayTree.restype = POINTER(SplayTreeInfo)
NewSplayTree.argtypes = [CFUNCTYPE(c_int, c_void_p, c_void_p), CFUNCTYPE(c_void_p, c_void_p), CFUNCTYPE(c_void_p, c_void_p)]
GetNumberOfNodesInSplayTree = _lib.GetNumberOfNodesInSplayTree
GetNumberOfNodesInSplayTree.restype = size_t
GetNumberOfNodesInSplayTree.argtypes = [POINTER(SplayTreeInfo)]
RemoveNodeByValueFromSplayTree = _lib.RemoveNodeByValueFromSplayTree
RemoveNodeByValueFromSplayTree.restype = c_void_p
RemoveNodeByValueFromSplayTree.argtypes = [POINTER(SplayTreeInfo), c_void_p]
RemoveNodeFromSplayTree = _lib.RemoveNodeFromSplayTree
RemoveNodeFromSplayTree.restype = c_void_p
RemoveNodeFromSplayTree.argtypes = [POINTER(SplayTreeInfo), c_void_p]
ResetSplayTree = _lib.ResetSplayTree
ResetSplayTree.restype = None
ResetSplayTree.argtypes = [POINTER(SplayTreeInfo)]
ResetSplayTreeIterator = _lib.ResetSplayTreeIterator
ResetSplayTreeIterator.restype = None
ResetSplayTreeIterator.argtypes = [POINTER(SplayTreeInfo)]
class _ChannelStatistics(Structure):
    pass
ChannelStatistics = _ChannelStatistics
GetImageChannelStatistics = _lib.GetImageChannelStatistics
GetImageChannelStatistics.restype = POINTER(ChannelStatistics)
GetImageChannelStatistics.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]

# values for enumeration 'MagickEvaluateOperator'
UndefinedEvaluateOperator = 0
AddEvaluateOperator = 1
AndEvaluateOperator = 2
DivideEvaluateOperator = 3
LeftShiftEvaluateOperator = 4
MaxEvaluateOperator = 5
MinEvaluateOperator = 6
MultiplyEvaluateOperator = 7
OrEvaluateOperator = 8
RightShiftEvaluateOperator = 9
SetEvaluateOperator = 10
SubtractEvaluateOperator = 11
XorEvaluateOperator = 12
PowEvaluateOperator = 13
LogEvaluateOperator = 14
ThresholdEvaluateOperator = 15
ThresholdBlackEvaluateOperator = 16
ThresholdWhiteEvaluateOperator = 17
GaussianNoiseEvaluateOperator = 18
ImpulseNoiseEvaluateOperator = 19
LaplacianNoiseEvaluateOperator = 20
MultiplicativeNoiseEvaluateOperator = 21
PoissonNoiseEvaluateOperator = 22
UniformNoiseEvaluateOperator = 23
CosineEvaluateOperator = 24
SineEvaluateOperator = 25
AddModulusEvaluateOperator = 26
MeanEvaluateOperator = 27
AbsEvaluateOperator = 28
ExponentialEvaluateOperator = 29
MedianEvaluateOperator = 30
MagickEvaluateOperator = c_int # enum
EvaluateImages = _lib.EvaluateImages
EvaluateImages.restype = POINTER(Image)
EvaluateImages.argtypes = [POINTER(Image), MagickEvaluateOperator, POINTER(ExceptionInfo)]
EvaluateImage = _lib.EvaluateImage
EvaluateImage.restype = MagickBooleanType
EvaluateImage.argtypes = [POINTER(Image), MagickEvaluateOperator, c_double, POINTER(ExceptionInfo)]
EvaluateImageChannel = _lib.EvaluateImageChannel
EvaluateImageChannel.restype = MagickBooleanType
EvaluateImageChannel.argtypes = [POINTER(Image), ChannelType, MagickEvaluateOperator, c_double, POINTER(ExceptionInfo)]

# values for enumeration 'MagickFunction'
UndefinedFunction = 0
PolynomialFunction = 1
SinusoidFunction = 2
ArcsinFunction = 3
ArctanFunction = 4
MagickFunction = c_int # enum
FunctionImage = _lib.FunctionImage
FunctionImage.restype = MagickBooleanType
FunctionImage.argtypes = [POINTER(Image), MagickFunction, size_t, POINTER(c_double), POINTER(ExceptionInfo)]
FunctionImageChannel = _lib.FunctionImageChannel
FunctionImageChannel.restype = MagickBooleanType
FunctionImageChannel.argtypes = [POINTER(Image), ChannelType, MagickFunction, size_t, POINTER(c_double), POINTER(ExceptionInfo)]
GetImageChannelExtrema = _lib.GetImageChannelExtrema
GetImageChannelExtrema.restype = MagickBooleanType
GetImageChannelExtrema.argtypes = [POINTER(Image), ChannelType, POINTER(size_t), POINTER(size_t), POINTER(ExceptionInfo)]
GetImageChannelMean = _lib.GetImageChannelMean
GetImageChannelMean.restype = MagickBooleanType
GetImageChannelMean.argtypes = [POINTER(Image), ChannelType, POINTER(c_double), POINTER(c_double), POINTER(ExceptionInfo)]
GetImageChannelKurtosis = _lib.GetImageChannelKurtosis
GetImageChannelKurtosis.restype = MagickBooleanType
GetImageChannelKurtosis.argtypes = [POINTER(Image), ChannelType, POINTER(c_double), POINTER(c_double), POINTER(ExceptionInfo)]
GetImageChannelRange = _lib.GetImageChannelRange
GetImageChannelRange.restype = MagickBooleanType
GetImageChannelRange.argtypes = [POINTER(Image), ChannelType, POINTER(c_double), POINTER(c_double), POINTER(ExceptionInfo)]
GetImageExtrema = _lib.GetImageExtrema
GetImageExtrema.restype = MagickBooleanType
GetImageExtrema.argtypes = [POINTER(Image), POINTER(size_t), POINTER(size_t), POINTER(ExceptionInfo)]
GetImageRange = _lib.GetImageRange
GetImageRange.restype = MagickBooleanType
GetImageRange.argtypes = [POINTER(Image), POINTER(c_double), POINTER(c_double), POINTER(ExceptionInfo)]
GetImageMean = _lib.GetImageMean
GetImageMean.restype = MagickBooleanType
GetImageMean.argtypes = [POINTER(Image), POINTER(c_double), POINTER(c_double), POINTER(ExceptionInfo)]
GetImageKurtosis = _lib.GetImageKurtosis
GetImageKurtosis.restype = MagickBooleanType
GetImageKurtosis.argtypes = [POINTER(Image), POINTER(c_double), POINTER(c_double), POINTER(ExceptionInfo)]
ReadStream = _lib.ReadStream
ReadStream.restype = POINTER(Image)
ReadStream.argtypes = [POINTER(ImageInfo), StreamHandler, POINTER(ExceptionInfo)]
WriteStream = _lib.WriteStream
WriteStream.restype = MagickBooleanType
WriteStream.argtypes = [POINTER(ImageInfo), POINTER(Image), StreamHandler]
AcquireString = _lib.AcquireString
AcquireString.restype = STRING
AcquireString.argtypes = [STRING]
CloneString = _lib.CloneString
CloneString.restype = STRING
CloneString.argtypes = [POINTER(STRING), STRING]
ConstantString = _lib.ConstantString
ConstantString.restype = STRING
ConstantString.argtypes = [STRING]
DestroyString = _lib.DestroyString
DestroyString.restype = STRING
DestroyString.argtypes = [STRING]
DestroyStringList = _lib.DestroyStringList
DestroyStringList.restype = POINTER(STRING)
DestroyStringList.argtypes = [POINTER(STRING)]
EscapeString = _lib.EscapeString
EscapeString.restype = STRING
EscapeString.argtypes = [STRING, c_char]
FileToString = _lib.FileToString
FileToString.restype = STRING
FileToString.argtypes = [STRING, size_t, POINTER(ExceptionInfo)]
GetEnvironmentValue = _lib.GetEnvironmentValue
GetEnvironmentValue.restype = STRING
GetEnvironmentValue.argtypes = [STRING]
StringInfoToHexString = _lib.StringInfoToHexString
StringInfoToHexString.restype = STRING
StringInfoToHexString.argtypes = [POINTER(StringInfo)]
StringInfoToString = _lib.StringInfoToString
StringInfoToString.restype = STRING
StringInfoToString.argtypes = [POINTER(StringInfo)]
StringToArgv = _lib.StringToArgv
StringToArgv.restype = POINTER(STRING)
StringToArgv.argtypes = [STRING, POINTER(c_int)]
StringToken = _lib.StringToken
StringToken.restype = STRING
StringToken.argtypes = [STRING, POINTER(STRING)]
StringToList = _lib.StringToList
StringToList.restype = POINTER(STRING)
StringToList.argtypes = [STRING]
GetStringInfoPath = _lib.GetStringInfoPath
GetStringInfoPath.restype = STRING
GetStringInfoPath.argtypes = [POINTER(StringInfo)]
InterpretSiPrefixValue = _lib.InterpretSiPrefixValue
InterpretSiPrefixValue.restype = c_double
InterpretSiPrefixValue.argtypes = [STRING, POINTER(STRING)]
CompareStringInfo = _lib.CompareStringInfo
CompareStringInfo.restype = c_int
CompareStringInfo.argtypes = [POINTER(StringInfo), POINTER(StringInfo)]
LocaleCompare = _lib.LocaleCompare
LocaleCompare.restype = c_int
LocaleCompare.argtypes = [STRING, STRING]
LocaleNCompare = _lib.LocaleNCompare
LocaleNCompare.restype = c_int
LocaleNCompare.argtypes = [STRING, STRING, size_t]
ConcatenateString = _lib.ConcatenateString
ConcatenateString.restype = MagickBooleanType
ConcatenateString.argtypes = [POINTER(STRING), STRING]
SubstituteString = _lib.SubstituteString
SubstituteString.restype = MagickBooleanType
SubstituteString.argtypes = [POINTER(STRING), STRING, STRING]
ConcatenateMagickString = _lib.ConcatenateMagickString
ConcatenateMagickString.restype = size_t
ConcatenateMagickString.argtypes = [STRING, STRING, size_t]
CopyMagickString = _lib.CopyMagickString
CopyMagickString.restype = size_t
CopyMagickString.argtypes = [STRING, STRING, size_t]
GetStringInfoLength = _lib.GetStringInfoLength
GetStringInfoLength.restype = size_t
GetStringInfoLength.argtypes = [POINTER(StringInfo)]
FormatMagickSize = _lib.FormatMagickSize
FormatMagickSize.restype = ssize_t
FormatMagickSize.argtypes = [MagickSizeType, MagickBooleanType, STRING]
__time_t = c_long
time_t = __time_t
FormatMagickTime = _lib.FormatMagickTime
FormatMagickTime.restype = ssize_t
FormatMagickTime.argtypes = [time_t, size_t, STRING]
AcquireStringInfo = _lib.AcquireStringInfo
AcquireStringInfo.restype = POINTER(StringInfo)
AcquireStringInfo.argtypes = [size_t]
BlobToStringInfo = _lib.BlobToStringInfo
BlobToStringInfo.restype = POINTER(StringInfo)
BlobToStringInfo.argtypes = [c_void_p, size_t]
CloneStringInfo = _lib.CloneStringInfo
CloneStringInfo.restype = POINTER(StringInfo)
CloneStringInfo.argtypes = [POINTER(StringInfo)]
ConfigureFileToStringInfo = _lib.ConfigureFileToStringInfo
ConfigureFileToStringInfo.restype = POINTER(StringInfo)
ConfigureFileToStringInfo.argtypes = [STRING]
DestroyStringInfo = _lib.DestroyStringInfo
DestroyStringInfo.restype = POINTER(StringInfo)
DestroyStringInfo.argtypes = [POINTER(StringInfo)]
FileToStringInfo = _lib.FileToStringInfo
FileToStringInfo.restype = POINTER(StringInfo)
FileToStringInfo.argtypes = [STRING, size_t, POINTER(ExceptionInfo)]
SplitStringInfo = _lib.SplitStringInfo
SplitStringInfo.restype = POINTER(StringInfo)
SplitStringInfo.argtypes = [POINTER(StringInfo), size_t]
StringToStringInfo = _lib.StringToStringInfo
StringToStringInfo.restype = POINTER(StringInfo)
StringToStringInfo.argtypes = [STRING]
GetStringInfoDatum = _lib.GetStringInfoDatum
GetStringInfoDatum.restype = POINTER(c_ubyte)
GetStringInfoDatum.argtypes = [POINTER(StringInfo)]
ConcatenateStringInfo = _lib.ConcatenateStringInfo
ConcatenateStringInfo.restype = None
ConcatenateStringInfo.argtypes = [POINTER(StringInfo), POINTER(StringInfo)]
LocaleLower = _lib.LocaleLower
LocaleLower.restype = None
LocaleLower.argtypes = [STRING]
LocaleUpper = _lib.LocaleUpper
LocaleUpper.restype = None
LocaleUpper.argtypes = [STRING]
PrintStringInfo = _lib.PrintStringInfo
PrintStringInfo.restype = None
PrintStringInfo.argtypes = [POINTER(FILE), STRING, POINTER(StringInfo)]
ResetStringInfo = _lib.ResetStringInfo
ResetStringInfo.restype = None
ResetStringInfo.argtypes = [POINTER(StringInfo)]
SetStringInfo = _lib.SetStringInfo
SetStringInfo.restype = None
SetStringInfo.argtypes = [POINTER(StringInfo), POINTER(StringInfo)]
SetStringInfoDatum = _lib.SetStringInfoDatum
SetStringInfoDatum.restype = None
SetStringInfoDatum.argtypes = [POINTER(StringInfo), POINTER(c_ubyte)]
SetStringInfoLength = _lib.SetStringInfoLength
SetStringInfoLength.restype = None
SetStringInfoLength.argtypes = [POINTER(StringInfo), size_t]
SetStringInfoPath = _lib.SetStringInfoPath
SetStringInfoPath.restype = None
SetStringInfoPath.argtypes = [POINTER(StringInfo), STRING]
StripString = _lib.StripString
StripString.restype = None
StripString.argtypes = [STRING]
AdaptiveThresholdImage = _lib.AdaptiveThresholdImage
AdaptiveThresholdImage.restype = POINTER(Image)
AdaptiveThresholdImage.argtypes = [POINTER(Image), size_t, size_t, ssize_t, POINTER(ExceptionInfo)]
class _ThresholdMap(Structure):
    pass
ThresholdMap = _ThresholdMap
DestroyThresholdMap = _lib.DestroyThresholdMap
DestroyThresholdMap.restype = POINTER(ThresholdMap)
DestroyThresholdMap.argtypes = [POINTER(ThresholdMap)]
GetThresholdMap = _lib.GetThresholdMap
GetThresholdMap.restype = POINTER(ThresholdMap)
GetThresholdMap.argtypes = [STRING, POINTER(ExceptionInfo)]
BilevelImage = _lib.BilevelImage
BilevelImage.restype = MagickBooleanType
BilevelImage.argtypes = [POINTER(Image), c_double]
BilevelImageChannel = _lib.BilevelImageChannel
BilevelImageChannel.restype = MagickBooleanType
BilevelImageChannel.argtypes = [POINTER(Image), ChannelType, c_double]
BlackThresholdImage = _lib.BlackThresholdImage
BlackThresholdImage.restype = MagickBooleanType
BlackThresholdImage.argtypes = [POINTER(Image), STRING]
BlackThresholdImageChannel = _lib.BlackThresholdImageChannel
BlackThresholdImageChannel.restype = MagickBooleanType
BlackThresholdImageChannel.argtypes = [POINTER(Image), ChannelType, STRING, POINTER(ExceptionInfo)]
ClampImage = _lib.ClampImage
ClampImage.restype = MagickBooleanType
ClampImage.argtypes = [POINTER(Image)]
ClampImageChannel = _lib.ClampImageChannel
ClampImageChannel.restype = MagickBooleanType
ClampImageChannel.argtypes = [POINTER(Image), ChannelType]
ListThresholdMaps = _lib.ListThresholdMaps
ListThresholdMaps.restype = MagickBooleanType
ListThresholdMaps.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
OrderedDitherImage = _lib.OrderedDitherImage
OrderedDitherImage.restype = MagickBooleanType
OrderedDitherImage.argtypes = [POINTER(Image)]
OrderedDitherImageChannel = _lib.OrderedDitherImageChannel
OrderedDitherImageChannel.restype = MagickBooleanType
OrderedDitherImageChannel.argtypes = [POINTER(Image), ChannelType, POINTER(ExceptionInfo)]
OrderedPosterizeImage = _lib.OrderedPosterizeImage
OrderedPosterizeImage.restype = MagickBooleanType
OrderedPosterizeImage.argtypes = [POINTER(Image), STRING, POINTER(ExceptionInfo)]
OrderedPosterizeImageChannel = _lib.OrderedPosterizeImageChannel
OrderedPosterizeImageChannel.restype = MagickBooleanType
OrderedPosterizeImageChannel.argtypes = [POINTER(Image), ChannelType, STRING, POINTER(ExceptionInfo)]
RandomThresholdImage = _lib.RandomThresholdImage
RandomThresholdImage.restype = MagickBooleanType
RandomThresholdImage.argtypes = [POINTER(Image), STRING, POINTER(ExceptionInfo)]
RandomThresholdImageChannel = _lib.RandomThresholdImageChannel
RandomThresholdImageChannel.restype = MagickBooleanType
RandomThresholdImageChannel.argtypes = [POINTER(Image), ChannelType, STRING, POINTER(ExceptionInfo)]
WhiteThresholdImage = _lib.WhiteThresholdImage
WhiteThresholdImage.restype = MagickBooleanType
WhiteThresholdImage.argtypes = [POINTER(Image), STRING]
WhiteThresholdImageChannel = _lib.WhiteThresholdImageChannel
WhiteThresholdImageChannel.restype = MagickBooleanType
WhiteThresholdImageChannel.argtypes = [POINTER(Image), ChannelType, STRING, POINTER(ExceptionInfo)]
class _TimerInfo(Structure):
    pass
TimerInfo = _TimerInfo
GetElapsedTime = _lib.GetElapsedTime
GetElapsedTime.restype = c_double
GetElapsedTime.argtypes = [POINTER(TimerInfo)]
GetUserTime = _lib.GetUserTime
GetUserTime.restype = c_double
GetUserTime.argtypes = [POINTER(TimerInfo)]
ContinueTimer = _lib.ContinueTimer
ContinueTimer.restype = MagickBooleanType
ContinueTimer.argtypes = [POINTER(TimerInfo)]
AcquireTimerInfo = _lib.AcquireTimerInfo
AcquireTimerInfo.restype = POINTER(TimerInfo)
AcquireTimerInfo.argtypes = []
DestroyTimerInfo = _lib.DestroyTimerInfo
DestroyTimerInfo.restype = POINTER(TimerInfo)
DestroyTimerInfo.argtypes = [POINTER(TimerInfo)]
GetTimerInfo = _lib.GetTimerInfo
GetTimerInfo.restype = None
GetTimerInfo.argtypes = [POINTER(TimerInfo)]
ResetTimer = _lib.ResetTimer
ResetTimer.restype = None
ResetTimer.argtypes = [POINTER(TimerInfo)]
StartTimer = _lib.StartTimer
StartTimer.restype = None
StartTimer.argtypes = [POINTER(TimerInfo), MagickBooleanType]
class _TokenInfo(Structure):
    pass
TokenInfo = _TokenInfo
Tokenizer = _lib.Tokenizer
Tokenizer.restype = c_int
Tokenizer.argtypes = [POINTER(TokenInfo), c_uint, STRING, size_t, STRING, STRING, STRING, STRING, c_char, STRING, POINTER(c_int), STRING]
GlobExpression = _lib.GlobExpression
GlobExpression.restype = MagickBooleanType
GlobExpression.argtypes = [STRING, STRING, MagickBooleanType]
IsGlob = _lib.IsGlob
IsGlob.restype = MagickBooleanType
IsGlob.argtypes = [STRING]
AcquireTokenInfo = _lib.AcquireTokenInfo
AcquireTokenInfo.restype = POINTER(TokenInfo)
AcquireTokenInfo.argtypes = []
DestroyTokenInfo = _lib.DestroyTokenInfo
DestroyTokenInfo.restype = POINTER(TokenInfo)
DestroyTokenInfo.argtypes = [POINTER(TokenInfo)]
GetMagickToken = _lib.GetMagickToken
GetMagickToken.restype = None
GetMagickToken.argtypes = [STRING, POINTER(STRING), STRING]
ChopImage = _lib.ChopImage
ChopImage.restype = POINTER(Image)
ChopImage.argtypes = [POINTER(Image), POINTER(RectangleInfo), POINTER(ExceptionInfo)]
ConsolidateCMYKImages = _lib.ConsolidateCMYKImages
ConsolidateCMYKImages.restype = POINTER(Image)
ConsolidateCMYKImages.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
CropImage = _lib.CropImage
CropImage.restype = POINTER(Image)
CropImage.argtypes = [POINTER(Image), POINTER(RectangleInfo), POINTER(ExceptionInfo)]
CropImageToTiles = _lib.CropImageToTiles
CropImageToTiles.restype = POINTER(Image)
CropImageToTiles.argtypes = [POINTER(Image), STRING, POINTER(ExceptionInfo)]
ExcerptImage = _lib.ExcerptImage
ExcerptImage.restype = POINTER(Image)
ExcerptImage.argtypes = [POINTER(Image), POINTER(RectangleInfo), POINTER(ExceptionInfo)]
ExtentImage = _lib.ExtentImage
ExtentImage.restype = POINTER(Image)
ExtentImage.argtypes = [POINTER(Image), POINTER(RectangleInfo), POINTER(ExceptionInfo)]
FlipImage = _lib.FlipImage
FlipImage.restype = POINTER(Image)
FlipImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
FlopImage = _lib.FlopImage
FlopImage.restype = POINTER(Image)
FlopImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
RollImage = _lib.RollImage
RollImage.restype = POINTER(Image)
RollImage.argtypes = [POINTER(Image), ssize_t, ssize_t, POINTER(ExceptionInfo)]
ShaveImage = _lib.ShaveImage
ShaveImage.restype = POINTER(Image)
ShaveImage.argtypes = [POINTER(Image), POINTER(RectangleInfo), POINTER(ExceptionInfo)]
SpliceImage = _lib.SpliceImage
SpliceImage.restype = POINTER(Image)
SpliceImage.argtypes = [POINTER(Image), POINTER(RectangleInfo), POINTER(ExceptionInfo)]
TransposeImage = _lib.TransposeImage
TransposeImage.restype = POINTER(Image)
TransposeImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
TransverseImage = _lib.TransverseImage
TransverseImage.restype = POINTER(Image)
TransverseImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
TrimImage = _lib.TrimImage
TrimImage.restype = POINTER(Image)
TrimImage.argtypes = [POINTER(Image), POINTER(ExceptionInfo)]
TransformImage = _lib.TransformImage
TransformImage.restype = MagickBooleanType
TransformImage.argtypes = [POINTER(POINTER(Image)), STRING, STRING]
TransformImages = _lib.TransformImages
TransformImages.restype = MagickBooleanType
TransformImages.argtypes = [POINTER(POINTER(Image)), STRING, STRING]
GetTypeList = _lib.GetTypeList
GetTypeList.restype = POINTER(STRING)
GetTypeList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
ListTypeInfo = _lib.ListTypeInfo
ListTypeInfo.restype = MagickBooleanType
ListTypeInfo.argtypes = [POINTER(FILE), POINTER(ExceptionInfo)]
TypeComponentGenesis = _lib.TypeComponentGenesis
TypeComponentGenesis.restype = MagickBooleanType
TypeComponentGenesis.argtypes = []
class _TypeInfo(Structure):
    pass
TypeInfo = _TypeInfo
GetTypeInfo = _lib.GetTypeInfo
GetTypeInfo.restype = POINTER(TypeInfo)
GetTypeInfo.argtypes = [STRING, POINTER(ExceptionInfo)]

# values for enumeration 'StyleType'
UndefinedStyle = 0
NormalStyle = 1
ItalicStyle = 2
ObliqueStyle = 3
AnyStyle = 4
StyleType = c_int # enum

# values for enumeration 'StretchType'
UndefinedStretch = 0
NormalStretch = 1
UltraCondensedStretch = 2
ExtraCondensedStretch = 3
CondensedStretch = 4
SemiCondensedStretch = 5
SemiExpandedStretch = 6
ExpandedStretch = 7
ExtraExpandedStretch = 8
UltraExpandedStretch = 9
AnyStretch = 10
StretchType = c_int # enum
GetTypeInfoByFamily = _lib.GetTypeInfoByFamily
GetTypeInfoByFamily.restype = POINTER(TypeInfo)
GetTypeInfoByFamily.argtypes = [STRING, StyleType, StretchType, size_t, POINTER(ExceptionInfo)]
GetTypeInfoList = _lib.GetTypeInfoList
GetTypeInfoList.restype = POINTER(POINTER(TypeInfo))
GetTypeInfoList.argtypes = [STRING, POINTER(size_t), POINTER(ExceptionInfo)]
TypeComponentTerminus = _lib.TypeComponentTerminus
TypeComponentTerminus.restype = None
TypeComponentTerminus.argtypes = []
Base64Encode = _lib.Base64Encode
Base64Encode.restype = STRING
Base64Encode.argtypes = [POINTER(c_ubyte), size_t, POINTER(size_t)]
GetPathComponents = _lib.GetPathComponents
GetPathComponents.restype = POINTER(STRING)
GetPathComponents.argtypes = [STRING, POINTER(size_t)]
ListFiles = _lib.ListFiles
ListFiles.restype = POINTER(STRING)
ListFiles.argtypes = [STRING, STRING, POINTER(size_t)]
SystemCommand = _lib.SystemCommand
SystemCommand.restype = c_int
SystemCommand.argtypes = [MagickBooleanType, MagickBooleanType, STRING, POINTER(ExceptionInfo)]
AcquireUniqueFilename = _lib.AcquireUniqueFilename
AcquireUniqueFilename.restype = MagickBooleanType
AcquireUniqueFilename.argtypes = [STRING]
AcquireUniqueSymbolicLink = _lib.AcquireUniqueSymbolicLink
AcquireUniqueSymbolicLink.restype = MagickBooleanType
AcquireUniqueSymbolicLink.argtypes = [STRING, STRING]
ExpandFilenames = _lib.ExpandFilenames
ExpandFilenames.restype = MagickBooleanType
ExpandFilenames.argtypes = [POINTER(c_int), POINTER(POINTER(STRING))]
GetPathAttributes = _lib.GetPathAttributes
GetPathAttributes.restype = MagickBooleanType
GetPathAttributes.argtypes = [STRING, c_void_p]
GetExecutionPath = _lib.GetExecutionPath
GetExecutionPath.restype = MagickBooleanType
GetExecutionPath.argtypes = [STRING, size_t]
IsMagickTrue = _lib.IsMagickTrue
IsMagickTrue.restype = MagickBooleanType
IsMagickTrue.argtypes = [STRING]
IsPathAccessible = _lib.IsPathAccessible
IsPathAccessible.restype = MagickBooleanType
IsPathAccessible.argtypes = [STRING]
MultilineCensus = _lib.MultilineCensus
MultilineCensus.restype = size_t
MultilineCensus.argtypes = [STRING]
GetMagickPageSize = _lib.GetMagickPageSize
GetMagickPageSize.restype = ssize_t
GetMagickPageSize.argtypes = []
Base64Decode = _lib.Base64Decode
Base64Decode.restype = POINTER(c_ubyte)
Base64Decode.argtypes = [STRING, POINTER(size_t)]
AppendImageFormat = _lib.AppendImageFormat
AppendImageFormat.restype = None
AppendImageFormat.argtypes = [STRING, STRING]
ChopPathComponents = _lib.ChopPathComponents
ChopPathComponents.restype = None
ChopPathComponents.argtypes = [STRING, size_t]
ExpandFilename = _lib.ExpandFilename
ExpandFilename.restype = None
ExpandFilename.argtypes = [STRING]

# values for enumeration 'PathType'
UndefinedPath = 0
MagickPath = 1
RootPath = 2
HeadPath = 3
TailPath = 4
BasePath = 5
ExtensionPath = 6
SubimagePath = 7
CanonicalPath = 8
PathType = c_int # enum
GetPathComponent = _lib.GetPathComponent
GetPathComponent.restype = None
GetPathComponent.argtypes = [STRING, PathType, STRING]
MagickDelay = _lib.MagickDelay
MagickDelay.restype = None
MagickDelay.argtypes = [MagickSizeType]
GetMagickHomeURL = _lib.GetMagickHomeURL
GetMagickHomeURL.restype = STRING
GetMagickHomeURL.argtypes = []
GetMagickCopyright = _lib.GetMagickCopyright
GetMagickCopyright.restype = STRING
GetMagickCopyright.argtypes = []
GetMagickFeatures = _lib.GetMagickFeatures
GetMagickFeatures.restype = STRING
GetMagickFeatures.argtypes = []
GetMagickPackageName = _lib.GetMagickPackageName
GetMagickPackageName.restype = STRING
GetMagickPackageName.argtypes = []
GetMagickQuantumDepth = _lib.GetMagickQuantumDepth
GetMagickQuantumDepth.restype = STRING
GetMagickQuantumDepth.argtypes = [POINTER(size_t)]
GetMagickQuantumRange = _lib.GetMagickQuantumRange
GetMagickQuantumRange.restype = STRING
GetMagickQuantumRange.argtypes = [POINTER(size_t)]
GetMagickReleaseDate = _lib.GetMagickReleaseDate
GetMagickReleaseDate.restype = STRING
GetMagickReleaseDate.argtypes = []
GetMagickVersion = _lib.GetMagickVersion
GetMagickVersion.restype = STRING
GetMagickVersion.argtypes = [POINTER(size_t)]
CanonicalXMLContent = _lib.CanonicalXMLContent
CanonicalXMLContent.restype = STRING
CanonicalXMLContent.argtypes = [STRING, MagickBooleanType]
class _XMLTreeInfo(Structure):
    pass
XMLTreeInfo = _XMLTreeInfo
XMLTreeInfoToXML = _lib.XMLTreeInfoToXML
XMLTreeInfoToXML.restype = STRING
XMLTreeInfoToXML.argtypes = [POINTER(XMLTreeInfo)]
GetXMLTreeAttribute = _lib.GetXMLTreeAttribute
GetXMLTreeAttribute.restype = STRING
GetXMLTreeAttribute.argtypes = [POINTER(XMLTreeInfo), STRING]
GetXMLTreeContent = _lib.GetXMLTreeContent
GetXMLTreeContent.restype = STRING
GetXMLTreeContent.argtypes = [POINTER(XMLTreeInfo)]
GetXMLTreeProcessingInstructions = _lib.GetXMLTreeProcessingInstructions
GetXMLTreeProcessingInstructions.restype = POINTER(STRING)
GetXMLTreeProcessingInstructions.argtypes = [POINTER(XMLTreeInfo), STRING]
GetXMLTreeTag = _lib.GetXMLTreeTag
GetXMLTreeTag.restype = STRING
GetXMLTreeTag.argtypes = [POINTER(XMLTreeInfo)]
GetXMLTreeAttributes = _lib.GetXMLTreeAttributes
GetXMLTreeAttributes.restype = MagickBooleanType
GetXMLTreeAttributes.argtypes = [POINTER(XMLTreeInfo), POINTER(SplayTreeInfo)]
AddChildToXMLTree = _lib.AddChildToXMLTree
AddChildToXMLTree.restype = POINTER(XMLTreeInfo)
AddChildToXMLTree.argtypes = [POINTER(XMLTreeInfo), STRING, size_t]
AddPathToXMLTree = _lib.AddPathToXMLTree
AddPathToXMLTree.restype = POINTER(XMLTreeInfo)
AddPathToXMLTree.argtypes = [POINTER(XMLTreeInfo), STRING, size_t]
DestroyXMLTree = _lib.DestroyXMLTree
DestroyXMLTree.restype = POINTER(XMLTreeInfo)
DestroyXMLTree.argtypes = [POINTER(XMLTreeInfo)]
GetNextXMLTreeTag = _lib.GetNextXMLTreeTag
GetNextXMLTreeTag.restype = POINTER(XMLTreeInfo)
GetNextXMLTreeTag.argtypes = [POINTER(XMLTreeInfo)]
GetXMLTreeChild = _lib.GetXMLTreeChild
GetXMLTreeChild.restype = POINTER(XMLTreeInfo)
GetXMLTreeChild.argtypes = [POINTER(XMLTreeInfo), STRING]
GetXMLTreeOrdered = _lib.GetXMLTreeOrdered
GetXMLTreeOrdered.restype = POINTER(XMLTreeInfo)
GetXMLTreeOrdered.argtypes = [POINTER(XMLTreeInfo)]
GetXMLTreePath = _lib.GetXMLTreePath
GetXMLTreePath.restype = POINTER(XMLTreeInfo)
GetXMLTreePath.argtypes = [POINTER(XMLTreeInfo), STRING]
GetXMLTreeSibling = _lib.GetXMLTreeSibling
GetXMLTreeSibling.restype = POINTER(XMLTreeInfo)
GetXMLTreeSibling.argtypes = [POINTER(XMLTreeInfo)]
InsertTagIntoXMLTree = _lib.InsertTagIntoXMLTree
InsertTagIntoXMLTree.restype = POINTER(XMLTreeInfo)
InsertTagIntoXMLTree.argtypes = [POINTER(XMLTreeInfo), POINTER(XMLTreeInfo), size_t]
NewXMLTree = _lib.NewXMLTree
NewXMLTree.restype = POINTER(XMLTreeInfo)
NewXMLTree.argtypes = [STRING, POINTER(ExceptionInfo)]
NewXMLTreeTag = _lib.NewXMLTreeTag
NewXMLTreeTag.restype = POINTER(XMLTreeInfo)
NewXMLTreeTag.argtypes = [STRING]
PruneTagFromXMLTree = _lib.PruneTagFromXMLTree
PruneTagFromXMLTree.restype = POINTER(XMLTreeInfo)
PruneTagFromXMLTree.argtypes = [POINTER(XMLTreeInfo)]
SetXMLTreeAttribute = _lib.SetXMLTreeAttribute
SetXMLTreeAttribute.restype = POINTER(XMLTreeInfo)
SetXMLTreeAttribute.argtypes = [POINTER(XMLTreeInfo), STRING, STRING]
SetXMLTreeContent = _lib.SetXMLTreeContent
SetXMLTreeContent.restype = POINTER(XMLTreeInfo)
SetXMLTreeContent.argtypes = [POINTER(XMLTreeInfo), STRING]
class _XImportInfo(Structure):
    pass
XImportInfo = _XImportInfo
XImportImage = _lib.XImportImage
XImportImage.restype = POINTER(Image)
XImportImage.argtypes = [POINTER(ImageInfo), POINTER(XImportInfo)]
XGetImportInfo = _lib.XGetImportInfo
XGetImportInfo.restype = None
XGetImportInfo.argtypes = [POINTER(XImportInfo)]
class _MagickWand(Structure):
    pass
MagickWand = _MagickWand
MagickGetException = _lib.MagickGetException
MagickGetException.restype = STRING
MagickGetException.argtypes = [POINTER(MagickWand), POINTER(ExceptionType)]
MagickGetExceptionType = _lib.MagickGetExceptionType
MagickGetExceptionType.restype = ExceptionType
MagickGetExceptionType.argtypes = [POINTER(MagickWand)]
IsMagickWand = _lib.IsMagickWand
IsMagickWand.restype = MagickBooleanType
IsMagickWand.argtypes = [POINTER(MagickWand)]
MagickClearException = _lib.MagickClearException
MagickClearException.restype = MagickBooleanType
MagickClearException.argtypes = [POINTER(MagickWand)]
MagickSetIteratorIndex = _lib.MagickSetIteratorIndex
MagickSetIteratorIndex.restype = MagickBooleanType
MagickSetIteratorIndex.argtypes = [POINTER(MagickWand), ssize_t]
CloneMagickWand = _lib.CloneMagickWand
CloneMagickWand.restype = POINTER(MagickWand)
CloneMagickWand.argtypes = [POINTER(MagickWand)]
DestroyMagickWand = _lib.DestroyMagickWand
DestroyMagickWand.restype = POINTER(MagickWand)
DestroyMagickWand.argtypes = [POINTER(MagickWand)]
NewMagickWand = _lib.NewMagickWand
NewMagickWand.restype = POINTER(MagickWand)
NewMagickWand.argtypes = []
NewMagickWandFromImage = _lib.NewMagickWandFromImage
NewMagickWandFromImage.restype = POINTER(MagickWand)
NewMagickWandFromImage.argtypes = [POINTER(Image)]
MagickGetIteratorIndex = _lib.MagickGetIteratorIndex
MagickGetIteratorIndex.restype = ssize_t
MagickGetIteratorIndex.argtypes = [POINTER(MagickWand)]
ClearMagickWand = _lib.ClearMagickWand
ClearMagickWand.restype = None
ClearMagickWand.argtypes = [POINTER(MagickWand)]
MagickWandGenesis = _lib.MagickWandGenesis
MagickWandGenesis.restype = None
MagickWandGenesis.argtypes = []
MagickWandTerminus = _lib.MagickWandTerminus
MagickWandTerminus.restype = None
MagickWandTerminus.argtypes = []
MagickRelinquishMemory = _lib.MagickRelinquishMemory
MagickRelinquishMemory.restype = c_void_p
MagickRelinquishMemory.argtypes = [c_void_p]
MagickResetIterator = _lib.MagickResetIterator
MagickResetIterator.restype = None
MagickResetIterator.argtypes = [POINTER(MagickWand)]
MagickSetFirstIterator = _lib.MagickSetFirstIterator
MagickSetFirstIterator.restype = None
MagickSetFirstIterator.argtypes = [POINTER(MagickWand)]
MagickSetLastIterator = _lib.MagickSetLastIterator
MagickSetLastIterator.restype = None
MagickSetLastIterator.argtypes = [POINTER(MagickWand)]
AnimateImageCommand = _lib.AnimateImageCommand
AnimateImageCommand.restype = MagickBooleanType
AnimateImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
CompareImageCommand = _lib.CompareImageCommand
CompareImageCommand.restype = MagickBooleanType
CompareImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
CompositeImageCommand = _lib.CompositeImageCommand
CompositeImageCommand.restype = MagickBooleanType
CompositeImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
ConjureImageCommand = _lib.ConjureImageCommand
ConjureImageCommand.restype = MagickBooleanType
ConjureImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
ConvertImageCommand = _lib.ConvertImageCommand
ConvertImageCommand.restype = MagickBooleanType
ConvertImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
class _PixelView(Structure):
    pass
PixelView = _PixelView
GetPixelViewException = _lib.GetPixelViewException
GetPixelViewException.restype = STRING
GetPixelViewException.argtypes = [POINTER(PixelView), POINTER(ExceptionType)]
class _DrawingWand(Structure):
    pass
DrawingWand = _DrawingWand
DrawGetFillAlpha = _lib.DrawGetFillAlpha
DrawGetFillAlpha.restype = c_double
DrawGetFillAlpha.argtypes = [POINTER(DrawingWand)]
DrawGetStrokeAlpha = _lib.DrawGetStrokeAlpha
DrawGetStrokeAlpha.restype = c_double
DrawGetStrokeAlpha.argtypes = [POINTER(DrawingWand)]
DrawPeekGraphicWand = _lib.DrawPeekGraphicWand
DrawPeekGraphicWand.restype = POINTER(DrawInfo)
DrawPeekGraphicWand.argtypes = [POINTER(DrawingWand)]
MagickDescribeImage = _lib.MagickDescribeImage
MagickDescribeImage.restype = STRING
MagickDescribeImage.argtypes = [POINTER(MagickWand)]
MagickGetImageAttribute = _lib.MagickGetImageAttribute
MagickGetImageAttribute.restype = STRING
MagickGetImageAttribute.argtypes = [POINTER(MagickWand), STRING]
class _PixelIterator(Structure):
    pass
PixelIterator = _PixelIterator
PixelIteratorGetException = _lib.PixelIteratorGetException
PixelIteratorGetException.restype = STRING
PixelIteratorGetException.argtypes = [POINTER(PixelIterator), POINTER(ExceptionType)]
MagickGetImageIndex = _lib.MagickGetImageIndex
MagickGetImageIndex.restype = ssize_t
MagickGetImageIndex.argtypes = [POINTER(MagickWand)]
DuplexTransferPixelViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(PixelView), POINTER(PixelView), POINTER(PixelView), c_void_p)
DuplexTransferPixelViewIterator = _lib.DuplexTransferPixelViewIterator
DuplexTransferPixelViewIterator.restype = MagickBooleanType
DuplexTransferPixelViewIterator.argtypes = [POINTER(PixelView), POINTER(PixelView), POINTER(PixelView), DuplexTransferPixelViewMethod, c_void_p]
GetPixelViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(PixelView), c_void_p)
GetPixelViewIterator = _lib.GetPixelViewIterator
GetPixelViewIterator.restype = MagickBooleanType
GetPixelViewIterator.argtypes = [POINTER(PixelView), GetPixelViewMethod, c_void_p]
IsPixelView = _lib.IsPixelView
IsPixelView.restype = MagickBooleanType
IsPixelView.argtypes = [POINTER(PixelView)]
MagickClipPathImage = _lib.MagickClipPathImage
MagickClipPathImage.restype = MagickBooleanType
MagickClipPathImage.argtypes = [POINTER(MagickWand), STRING, MagickBooleanType]
class _PixelWand(Structure):
    pass
PixelWand = _PixelWand
MagickColorFloodfillImage = _lib.MagickColorFloodfillImage
MagickColorFloodfillImage.restype = MagickBooleanType
MagickColorFloodfillImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), c_double, POINTER(PixelWand), ssize_t, ssize_t]
MagickGetImageChannelExtrema = _lib.MagickGetImageChannelExtrema
MagickGetImageChannelExtrema.restype = MagickBooleanType
MagickGetImageChannelExtrema.argtypes = [POINTER(MagickWand), ChannelType, POINTER(size_t), POINTER(size_t)]
MagickGetImageExtrema = _lib.MagickGetImageExtrema
MagickGetImageExtrema.restype = MagickBooleanType
MagickGetImageExtrema.argtypes = [POINTER(MagickWand), POINTER(size_t), POINTER(size_t)]
MagickGetImageMatte = _lib.MagickGetImageMatte
MagickGetImageMatte.restype = MagickBooleanType
MagickGetImageMatte.argtypes = [POINTER(MagickWand)]
MagickGetImagePixels = _lib.MagickGetImagePixels
MagickGetImagePixels.restype = MagickBooleanType
MagickGetImagePixels.argtypes = [POINTER(MagickWand), ssize_t, ssize_t, size_t, size_t, STRING, StorageType, c_void_p]
MagickMapImage = _lib.MagickMapImage
MagickMapImage.restype = MagickBooleanType
MagickMapImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand), MagickBooleanType]
MagickMatteFloodfillImage = _lib.MagickMatteFloodfillImage
MagickMatteFloodfillImage.restype = MagickBooleanType
MagickMatteFloodfillImage.argtypes = [POINTER(MagickWand), c_double, c_double, POINTER(PixelWand), ssize_t, ssize_t]
MagickOpaqueImage = _lib.MagickOpaqueImage
MagickOpaqueImage.restype = MagickBooleanType
MagickOpaqueImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), POINTER(PixelWand), c_double]
MagickPaintFloodfillImage = _lib.MagickPaintFloodfillImage
MagickPaintFloodfillImage.restype = MagickBooleanType
MagickPaintFloodfillImage.argtypes = [POINTER(MagickWand), ChannelType, POINTER(PixelWand), c_double, POINTER(PixelWand), ssize_t, ssize_t]
MagickPaintOpaqueImage = _lib.MagickPaintOpaqueImage
MagickPaintOpaqueImage.restype = MagickBooleanType
MagickPaintOpaqueImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), POINTER(PixelWand), c_double]
MagickPaintOpaqueImageChannel = _lib.MagickPaintOpaqueImageChannel
MagickPaintOpaqueImageChannel.restype = MagickBooleanType
MagickPaintOpaqueImageChannel.argtypes = [POINTER(MagickWand), ChannelType, POINTER(PixelWand), POINTER(PixelWand), c_double]
MagickPaintTransparentImage = _lib.MagickPaintTransparentImage
MagickPaintTransparentImage.restype = MagickBooleanType
MagickPaintTransparentImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), c_double, c_double]
MagickRecolorImage = _lib.MagickRecolorImage
MagickRecolorImage.restype = MagickBooleanType
MagickRecolorImage.argtypes = [POINTER(MagickWand), size_t, POINTER(c_double)]
MagickSetImageAttribute = _lib.MagickSetImageAttribute
MagickSetImageAttribute.restype = MagickBooleanType
MagickSetImageAttribute.argtypes = [POINTER(MagickWand), STRING, STRING]
MagickSetImageIndex = _lib.MagickSetImageIndex
MagickSetImageIndex.restype = MagickBooleanType
MagickSetImageIndex.argtypes = [POINTER(MagickWand), ssize_t]
MagickSetImageOption = _lib.MagickSetImageOption
MagickSetImageOption.restype = MagickBooleanType
MagickSetImageOption.argtypes = [POINTER(MagickWand), STRING, STRING, STRING]
MagickSetImagePixels = _lib.MagickSetImagePixels
MagickSetImagePixels.restype = MagickBooleanType
MagickSetImagePixels.argtypes = [POINTER(MagickWand), ssize_t, ssize_t, size_t, size_t, STRING, StorageType, c_void_p]
MagickTransparentImage = _lib.MagickTransparentImage
MagickTransparentImage.restype = MagickBooleanType
MagickTransparentImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), c_double, c_double]
SetPixelViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(PixelView), c_void_p)
SetPixelViewIterator = _lib.SetPixelViewIterator
SetPixelViewIterator.restype = MagickBooleanType
SetPixelViewIterator.argtypes = [POINTER(PixelView), SetPixelViewMethod, c_void_p]
TransferPixelViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(PixelView), POINTER(PixelView), c_void_p)
TransferPixelViewIterator = _lib.TransferPixelViewIterator
TransferPixelViewIterator.restype = MagickBooleanType
TransferPixelViewIterator.argtypes = [POINTER(PixelView), POINTER(PixelView), TransferPixelViewMethod, c_void_p]
UpdatePixelViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(PixelView), c_void_p)
UpdatePixelViewIterator = _lib.UpdatePixelViewIterator
UpdatePixelViewIterator.restype = MagickBooleanType
UpdatePixelViewIterator.argtypes = [POINTER(PixelView), UpdatePixelViewMethod, c_void_p]
GetPixelViewWand = _lib.GetPixelViewWand
GetPixelViewWand.restype = POINTER(MagickWand)
GetPixelViewWand.argtypes = [POINTER(PixelView)]
MagickAverageImages = _lib.MagickAverageImages
MagickAverageImages.restype = POINTER(MagickWand)
MagickAverageImages.argtypes = [POINTER(MagickWand)]
MagickFlattenImages = _lib.MagickFlattenImages
MagickFlattenImages.restype = POINTER(MagickWand)
MagickFlattenImages.argtypes = [POINTER(MagickWand)]
MagickMaximumImages = _lib.MagickMaximumImages
MagickMaximumImages.restype = POINTER(MagickWand)
MagickMaximumImages.argtypes = [POINTER(MagickWand)]
MagickMinimumImages = _lib.MagickMinimumImages
MagickMinimumImages.restype = POINTER(MagickWand)
MagickMinimumImages.argtypes = [POINTER(MagickWand)]
MagickMosaicImages = _lib.MagickMosaicImages
MagickMosaicImages.restype = POINTER(MagickWand)
MagickMosaicImages.argtypes = [POINTER(MagickWand)]
MagickRegionOfInterestImage = _lib.MagickRegionOfInterestImage
MagickRegionOfInterestImage.restype = POINTER(MagickWand)
MagickRegionOfInterestImage.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t, ssize_t]
MagickGetImageSize = _lib.MagickGetImageSize
MagickGetImageSize.restype = MagickSizeType
MagickGetImageSize.argtypes = [POINTER(MagickWand)]
ClonePixelView = _lib.ClonePixelView
ClonePixelView.restype = POINTER(PixelView)
ClonePixelView.argtypes = [POINTER(PixelView)]
DestroyPixelView = _lib.DestroyPixelView
DestroyPixelView.restype = POINTER(PixelView)
DestroyPixelView.argtypes = [POINTER(PixelView)]
NewPixelView = _lib.NewPixelView
NewPixelView.restype = POINTER(PixelView)
NewPixelView.argtypes = [POINTER(MagickWand)]
NewPixelViewRegion = _lib.NewPixelViewRegion
NewPixelViewRegion.restype = POINTER(PixelView)
NewPixelViewRegion.argtypes = [POINTER(MagickWand), ssize_t, ssize_t, size_t, size_t]
GetPixelViewPixels = _lib.GetPixelViewPixels
GetPixelViewPixels.restype = POINTER(POINTER(PixelWand))
GetPixelViewPixels.argtypes = [POINTER(PixelView)]
PixelGetNextRow = _lib.PixelGetNextRow
PixelGetNextRow.restype = POINTER(POINTER(PixelWand))
PixelGetNextRow.argtypes = [POINTER(PixelIterator)]
GetPixelViewHeight = _lib.GetPixelViewHeight
GetPixelViewHeight.restype = size_t
GetPixelViewHeight.argtypes = [POINTER(PixelView)]
GetPixelViewWidth = _lib.GetPixelViewWidth
GetPixelViewWidth.restype = size_t
GetPixelViewWidth.argtypes = [POINTER(PixelView)]
GetPixelViewX = _lib.GetPixelViewX
GetPixelViewX.restype = ssize_t
GetPixelViewX.argtypes = [POINTER(PixelView)]
GetPixelViewY = _lib.GetPixelViewY
GetPixelViewY.restype = ssize_t
GetPixelViewY.argtypes = [POINTER(PixelView)]
MagickWriteImageBlob = _lib.MagickWriteImageBlob
MagickWriteImageBlob.restype = POINTER(c_ubyte)
MagickWriteImageBlob.argtypes = [POINTER(MagickWand), POINTER(size_t)]
DrawPopGraphicContext = _lib.DrawPopGraphicContext
DrawPopGraphicContext.restype = None
DrawPopGraphicContext.argtypes = [POINTER(DrawingWand)]
DrawPushGraphicContext = _lib.DrawPushGraphicContext
DrawPushGraphicContext.restype = None
DrawPushGraphicContext.argtypes = [POINTER(DrawingWand)]
DrawSetFillAlpha = _lib.DrawSetFillAlpha
DrawSetFillAlpha.restype = None
DrawSetFillAlpha.argtypes = [POINTER(DrawingWand), c_double]
DrawSetStrokeAlpha = _lib.DrawSetStrokeAlpha
DrawSetStrokeAlpha.restype = None
DrawSetStrokeAlpha.argtypes = [POINTER(DrawingWand), c_double]
DisplayImageCommand = _lib.DisplayImageCommand
DisplayImageCommand.restype = MagickBooleanType
DisplayImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]

# values for enumeration 'AlignType'
UndefinedAlign = 0
LeftAlign = 1
CenterAlign = 2
RightAlign = 3
AlignType = c_int # enum
DrawGetTextAlignment = _lib.DrawGetTextAlignment
DrawGetTextAlignment.restype = AlignType
DrawGetTextAlignment.argtypes = [POINTER(DrawingWand)]
DrawGetClipPath = _lib.DrawGetClipPath
DrawGetClipPath.restype = STRING
DrawGetClipPath.argtypes = [POINTER(DrawingWand)]
DrawGetException = _lib.DrawGetException
DrawGetException.restype = STRING
DrawGetException.argtypes = [POINTER(DrawingWand), POINTER(ExceptionType)]
DrawGetFont = _lib.DrawGetFont
DrawGetFont.restype = STRING
DrawGetFont.argtypes = [POINTER(DrawingWand)]
DrawGetFontFamily = _lib.DrawGetFontFamily
DrawGetFontFamily.restype = STRING
DrawGetFontFamily.argtypes = [POINTER(DrawingWand)]
DrawGetTextEncoding = _lib.DrawGetTextEncoding
DrawGetTextEncoding.restype = STRING
DrawGetTextEncoding.argtypes = [POINTER(DrawingWand)]
DrawGetVectorGraphics = _lib.DrawGetVectorGraphics
DrawGetVectorGraphics.restype = STRING
DrawGetVectorGraphics.argtypes = [POINTER(DrawingWand)]

# values for enumeration 'ClipPathUnits'
UndefinedPathUnits = 0
UserSpace = 1
UserSpaceOnUse = 2
ObjectBoundingBox = 3
ClipPathUnits = c_int # enum
DrawGetClipUnits = _lib.DrawGetClipUnits
DrawGetClipUnits.restype = ClipPathUnits
DrawGetClipUnits.argtypes = [POINTER(DrawingWand)]

# values for enumeration 'DecorationType'
UndefinedDecoration = 0
NoDecoration = 1
UnderlineDecoration = 2
OverlineDecoration = 3
LineThroughDecoration = 4
DecorationType = c_int # enum
DrawGetTextDecoration = _lib.DrawGetTextDecoration
DrawGetTextDecoration.restype = DecorationType
DrawGetTextDecoration.argtypes = [POINTER(DrawingWand)]
DrawGetFillOpacity = _lib.DrawGetFillOpacity
DrawGetFillOpacity.restype = c_double
DrawGetFillOpacity.argtypes = [POINTER(DrawingWand)]
DrawGetFontSize = _lib.DrawGetFontSize
DrawGetFontSize.restype = c_double
DrawGetFontSize.argtypes = [POINTER(DrawingWand)]
DrawGetOpacity = _lib.DrawGetOpacity
DrawGetOpacity.restype = c_double
DrawGetOpacity.argtypes = [POINTER(DrawingWand)]
DrawGetStrokeDashArray = _lib.DrawGetStrokeDashArray
DrawGetStrokeDashArray.restype = POINTER(c_double)
DrawGetStrokeDashArray.argtypes = [POINTER(DrawingWand), POINTER(size_t)]
DrawGetStrokeDashOffset = _lib.DrawGetStrokeDashOffset
DrawGetStrokeDashOffset.restype = c_double
DrawGetStrokeDashOffset.argtypes = [POINTER(DrawingWand)]
DrawGetStrokeOpacity = _lib.DrawGetStrokeOpacity
DrawGetStrokeOpacity.restype = c_double
DrawGetStrokeOpacity.argtypes = [POINTER(DrawingWand)]
DrawGetStrokeWidth = _lib.DrawGetStrokeWidth
DrawGetStrokeWidth.restype = c_double
DrawGetStrokeWidth.argtypes = [POINTER(DrawingWand)]
DrawGetTextKerning = _lib.DrawGetTextKerning
DrawGetTextKerning.restype = c_double
DrawGetTextKerning.argtypes = [POINTER(DrawingWand)]
DrawGetTextInterlineSpacing = _lib.DrawGetTextInterlineSpacing
DrawGetTextInterlineSpacing.restype = c_double
DrawGetTextInterlineSpacing.argtypes = [POINTER(DrawingWand)]
DrawGetTextInterwordSpacing = _lib.DrawGetTextInterwordSpacing
DrawGetTextInterwordSpacing.restype = c_double
DrawGetTextInterwordSpacing.argtypes = [POINTER(DrawingWand)]
PeekDrawingWand = _lib.PeekDrawingWand
PeekDrawingWand.restype = POINTER(DrawInfo)
PeekDrawingWand.argtypes = [POINTER(DrawingWand)]
CloneDrawingWand = _lib.CloneDrawingWand
CloneDrawingWand.restype = POINTER(DrawingWand)
CloneDrawingWand.argtypes = [POINTER(DrawingWand)]
DestroyDrawingWand = _lib.DestroyDrawingWand
DestroyDrawingWand.restype = POINTER(DrawingWand)
DestroyDrawingWand.argtypes = [POINTER(DrawingWand)]
DrawAllocateWand = _lib.DrawAllocateWand
DrawAllocateWand.restype = POINTER(DrawingWand)
DrawAllocateWand.argtypes = [POINTER(DrawInfo), POINTER(Image)]
NewDrawingWand = _lib.NewDrawingWand
NewDrawingWand.restype = POINTER(DrawingWand)
NewDrawingWand.argtypes = []
DrawGetExceptionType = _lib.DrawGetExceptionType
DrawGetExceptionType.restype = ExceptionType
DrawGetExceptionType.argtypes = [POINTER(DrawingWand)]

# values for enumeration 'FillRule'
UndefinedRule = 0
EvenOddRule = 1
NonZeroRule = 2
FillRule = c_int # enum
DrawGetClipRule = _lib.DrawGetClipRule
DrawGetClipRule.restype = FillRule
DrawGetClipRule.argtypes = [POINTER(DrawingWand)]
DrawGetFillRule = _lib.DrawGetFillRule
DrawGetFillRule.restype = FillRule
DrawGetFillRule.argtypes = [POINTER(DrawingWand)]
DrawGetGravity = _lib.DrawGetGravity
DrawGetGravity.restype = GravityType
DrawGetGravity.argtypes = [POINTER(DrawingWand)]

# values for enumeration 'LineCap'
UndefinedCap = 0
ButtCap = 1
RoundCap = 2
SquareCap = 3
LineCap = c_int # enum
DrawGetStrokeLineCap = _lib.DrawGetStrokeLineCap
DrawGetStrokeLineCap.restype = LineCap
DrawGetStrokeLineCap.argtypes = [POINTER(DrawingWand)]

# values for enumeration 'LineJoin'
UndefinedJoin = 0
MiterJoin = 1
RoundJoin = 2
BevelJoin = 3
LineJoin = c_int # enum
DrawGetStrokeLineJoin = _lib.DrawGetStrokeLineJoin
DrawGetStrokeLineJoin.restype = LineJoin
DrawGetStrokeLineJoin.argtypes = [POINTER(DrawingWand)]
DrawClearException = _lib.DrawClearException
DrawClearException.restype = MagickBooleanType
DrawClearException.argtypes = [POINTER(DrawingWand)]
DrawComposite = _lib.DrawComposite
DrawComposite.restype = MagickBooleanType
DrawComposite.argtypes = [POINTER(DrawingWand), CompositeOperator, c_double, c_double, c_double, c_double, POINTER(MagickWand)]
DrawGetFontResolution = _lib.DrawGetFontResolution
DrawGetFontResolution.restype = MagickBooleanType
DrawGetFontResolution.argtypes = [POINTER(DrawingWand), POINTER(c_double), POINTER(c_double)]
DrawGetStrokeAntialias = _lib.DrawGetStrokeAntialias
DrawGetStrokeAntialias.restype = MagickBooleanType
DrawGetStrokeAntialias.argtypes = [POINTER(DrawingWand)]
DrawGetTextAntialias = _lib.DrawGetTextAntialias
DrawGetTextAntialias.restype = MagickBooleanType
DrawGetTextAntialias.argtypes = [POINTER(DrawingWand)]
DrawPopPattern = _lib.DrawPopPattern
DrawPopPattern.restype = MagickBooleanType
DrawPopPattern.argtypes = [POINTER(DrawingWand)]
DrawPushPattern = _lib.DrawPushPattern
DrawPushPattern.restype = MagickBooleanType
DrawPushPattern.argtypes = [POINTER(DrawingWand), STRING, c_double, c_double, c_double, c_double]
DrawRender = _lib.DrawRender
DrawRender.restype = MagickBooleanType
DrawRender.argtypes = [POINTER(DrawingWand)]
DrawSetClipPath = _lib.DrawSetClipPath
DrawSetClipPath.restype = MagickBooleanType
DrawSetClipPath.argtypes = [POINTER(DrawingWand), STRING]
DrawSetFillPatternURL = _lib.DrawSetFillPatternURL
DrawSetFillPatternURL.restype = MagickBooleanType
DrawSetFillPatternURL.argtypes = [POINTER(DrawingWand), STRING]
DrawSetFont = _lib.DrawSetFont
DrawSetFont.restype = MagickBooleanType
DrawSetFont.argtypes = [POINTER(DrawingWand), STRING]
DrawSetFontFamily = _lib.DrawSetFontFamily
DrawSetFontFamily.restype = MagickBooleanType
DrawSetFontFamily.argtypes = [POINTER(DrawingWand), STRING]
DrawSetFontResolution = _lib.DrawSetFontResolution
DrawSetFontResolution.restype = MagickBooleanType
DrawSetFontResolution.argtypes = [POINTER(DrawingWand), c_double, c_double]
DrawSetStrokeDashArray = _lib.DrawSetStrokeDashArray
DrawSetStrokeDashArray.restype = MagickBooleanType
DrawSetStrokeDashArray.argtypes = [POINTER(DrawingWand), size_t, POINTER(c_double)]
DrawSetStrokePatternURL = _lib.DrawSetStrokePatternURL
DrawSetStrokePatternURL.restype = MagickBooleanType
DrawSetStrokePatternURL.argtypes = [POINTER(DrawingWand), STRING]
DrawSetVectorGraphics = _lib.DrawSetVectorGraphics
DrawSetVectorGraphics.restype = MagickBooleanType
DrawSetVectorGraphics.argtypes = [POINTER(DrawingWand), STRING]
IsDrawingWand = _lib.IsDrawingWand
IsDrawingWand.restype = MagickBooleanType
IsDrawingWand.argtypes = [POINTER(DrawingWand)]
PopDrawingWand = _lib.PopDrawingWand
PopDrawingWand.restype = MagickBooleanType
PopDrawingWand.argtypes = [POINTER(DrawingWand)]
PushDrawingWand = _lib.PushDrawingWand
PushDrawingWand.restype = MagickBooleanType
PushDrawingWand.argtypes = [POINTER(DrawingWand)]
DrawGetFontStretch = _lib.DrawGetFontStretch
DrawGetFontStretch.restype = StretchType
DrawGetFontStretch.argtypes = [POINTER(DrawingWand)]
DrawGetFontStyle = _lib.DrawGetFontStyle
DrawGetFontStyle.restype = StyleType
DrawGetFontStyle.argtypes = [POINTER(DrawingWand)]
DrawGetFontWeight = _lib.DrawGetFontWeight
DrawGetFontWeight.restype = size_t
DrawGetFontWeight.argtypes = [POINTER(DrawingWand)]
DrawGetStrokeMiterLimit = _lib.DrawGetStrokeMiterLimit
DrawGetStrokeMiterLimit.restype = size_t
DrawGetStrokeMiterLimit.argtypes = [POINTER(DrawingWand)]
ClearDrawingWand = _lib.ClearDrawingWand
ClearDrawingWand.restype = None
ClearDrawingWand.argtypes = [POINTER(DrawingWand)]
DrawAffine = _lib.DrawAffine
DrawAffine.restype = None
DrawAffine.argtypes = [POINTER(DrawingWand), POINTER(AffineMatrix)]
DrawAnnotation = _lib.DrawAnnotation
DrawAnnotation.restype = None
DrawAnnotation.argtypes = [POINTER(DrawingWand), c_double, c_double, POINTER(c_ubyte)]
DrawArc = _lib.DrawArc
DrawArc.restype = None
DrawArc.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double, c_double, c_double]
class _PointInfo(Structure):
    pass
PointInfo = _PointInfo
DrawBezier = _lib.DrawBezier
DrawBezier.restype = None
DrawBezier.argtypes = [POINTER(DrawingWand), size_t, POINTER(PointInfo)]
DrawGetBorderColor = _lib.DrawGetBorderColor
DrawGetBorderColor.restype = None
DrawGetBorderColor.argtypes = [POINTER(DrawingWand), POINTER(PixelWand)]
DrawCircle = _lib.DrawCircle
DrawCircle.restype = None
DrawCircle.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double]
DrawColor = _lib.DrawColor
DrawColor.restype = None
DrawColor.argtypes = [POINTER(DrawingWand), c_double, c_double, PaintMethod]
DrawComment = _lib.DrawComment
DrawComment.restype = None
DrawComment.argtypes = [POINTER(DrawingWand), STRING]
DrawEllipse = _lib.DrawEllipse
DrawEllipse.restype = None
DrawEllipse.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double, c_double, c_double]
DrawGetFillColor = _lib.DrawGetFillColor
DrawGetFillColor.restype = None
DrawGetFillColor.argtypes = [POINTER(DrawingWand), POINTER(PixelWand)]
DrawGetStrokeColor = _lib.DrawGetStrokeColor
DrawGetStrokeColor.restype = None
DrawGetStrokeColor.argtypes = [POINTER(DrawingWand), POINTER(PixelWand)]
DrawSetTextKerning = _lib.DrawSetTextKerning
DrawSetTextKerning.restype = None
DrawSetTextKerning.argtypes = [POINTER(DrawingWand), c_double]
DrawSetTextInterlineSpacing = _lib.DrawSetTextInterlineSpacing
DrawSetTextInterlineSpacing.restype = None
DrawSetTextInterlineSpacing.argtypes = [POINTER(DrawingWand), c_double]
DrawSetTextInterwordSpacing = _lib.DrawSetTextInterwordSpacing
DrawSetTextInterwordSpacing.restype = None
DrawSetTextInterwordSpacing.argtypes = [POINTER(DrawingWand), c_double]
DrawGetTextUnderColor = _lib.DrawGetTextUnderColor
DrawGetTextUnderColor.restype = None
DrawGetTextUnderColor.argtypes = [POINTER(DrawingWand), POINTER(PixelWand)]
DrawLine = _lib.DrawLine
DrawLine.restype = None
DrawLine.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double]
DrawMatte = _lib.DrawMatte
DrawMatte.restype = None
DrawMatte.argtypes = [POINTER(DrawingWand), c_double, c_double, PaintMethod]
DrawPathClose = _lib.DrawPathClose
DrawPathClose.restype = None
DrawPathClose.argtypes = [POINTER(DrawingWand)]
DrawPathCurveToAbsolute = _lib.DrawPathCurveToAbsolute
DrawPathCurveToAbsolute.restype = None
DrawPathCurveToAbsolute.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double, c_double, c_double]
DrawPathCurveToRelative = _lib.DrawPathCurveToRelative
DrawPathCurveToRelative.restype = None
DrawPathCurveToRelative.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double, c_double, c_double]
DrawPathCurveToQuadraticBezierAbsolute = _lib.DrawPathCurveToQuadraticBezierAbsolute
DrawPathCurveToQuadraticBezierAbsolute.restype = None
DrawPathCurveToQuadraticBezierAbsolute.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double]
DrawPathCurveToQuadraticBezierRelative = _lib.DrawPathCurveToQuadraticBezierRelative
DrawPathCurveToQuadraticBezierRelative.restype = None
DrawPathCurveToQuadraticBezierRelative.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double]
DrawPathCurveToQuadraticBezierSmoothAbsolute = _lib.DrawPathCurveToQuadraticBezierSmoothAbsolute
DrawPathCurveToQuadraticBezierSmoothAbsolute.restype = None
DrawPathCurveToQuadraticBezierSmoothAbsolute.argtypes = [POINTER(DrawingWand), c_double, c_double]
DrawPathCurveToQuadraticBezierSmoothRelative = _lib.DrawPathCurveToQuadraticBezierSmoothRelative
DrawPathCurveToQuadraticBezierSmoothRelative.restype = None
DrawPathCurveToQuadraticBezierSmoothRelative.argtypes = [POINTER(DrawingWand), c_double, c_double]
DrawPathCurveToSmoothAbsolute = _lib.DrawPathCurveToSmoothAbsolute
DrawPathCurveToSmoothAbsolute.restype = None
DrawPathCurveToSmoothAbsolute.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double]
DrawPathCurveToSmoothRelative = _lib.DrawPathCurveToSmoothRelative
DrawPathCurveToSmoothRelative.restype = None
DrawPathCurveToSmoothRelative.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double]
DrawPathEllipticArcAbsolute = _lib.DrawPathEllipticArcAbsolute
DrawPathEllipticArcAbsolute.restype = None
DrawPathEllipticArcAbsolute.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, MagickBooleanType, MagickBooleanType, c_double, c_double]
DrawPathEllipticArcRelative = _lib.DrawPathEllipticArcRelative
DrawPathEllipticArcRelative.restype = None
DrawPathEllipticArcRelative.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, MagickBooleanType, MagickBooleanType, c_double, c_double]
DrawPathFinish = _lib.DrawPathFinish
DrawPathFinish.restype = None
DrawPathFinish.argtypes = [POINTER(DrawingWand)]
DrawPathLineToAbsolute = _lib.DrawPathLineToAbsolute
DrawPathLineToAbsolute.restype = None
DrawPathLineToAbsolute.argtypes = [POINTER(DrawingWand), c_double, c_double]
DrawPathLineToRelative = _lib.DrawPathLineToRelative
DrawPathLineToRelative.restype = None
DrawPathLineToRelative.argtypes = [POINTER(DrawingWand), c_double, c_double]
DrawPathLineToHorizontalAbsolute = _lib.DrawPathLineToHorizontalAbsolute
DrawPathLineToHorizontalAbsolute.restype = None
DrawPathLineToHorizontalAbsolute.argtypes = [POINTER(DrawingWand), c_double]
DrawPathLineToHorizontalRelative = _lib.DrawPathLineToHorizontalRelative
DrawPathLineToHorizontalRelative.restype = None
DrawPathLineToHorizontalRelative.argtypes = [POINTER(DrawingWand), c_double]
DrawPathLineToVerticalAbsolute = _lib.DrawPathLineToVerticalAbsolute
DrawPathLineToVerticalAbsolute.restype = None
DrawPathLineToVerticalAbsolute.argtypes = [POINTER(DrawingWand), c_double]
DrawPathLineToVerticalRelative = _lib.DrawPathLineToVerticalRelative
DrawPathLineToVerticalRelative.restype = None
DrawPathLineToVerticalRelative.argtypes = [POINTER(DrawingWand), c_double]
DrawPathMoveToAbsolute = _lib.DrawPathMoveToAbsolute
DrawPathMoveToAbsolute.restype = None
DrawPathMoveToAbsolute.argtypes = [POINTER(DrawingWand), c_double, c_double]
DrawPathMoveToRelative = _lib.DrawPathMoveToRelative
DrawPathMoveToRelative.restype = None
DrawPathMoveToRelative.argtypes = [POINTER(DrawingWand), c_double, c_double]
DrawPathStart = _lib.DrawPathStart
DrawPathStart.restype = None
DrawPathStart.argtypes = [POINTER(DrawingWand)]
DrawPoint = _lib.DrawPoint
DrawPoint.restype = None
DrawPoint.argtypes = [POINTER(DrawingWand), c_double, c_double]
DrawPolygon = _lib.DrawPolygon
DrawPolygon.restype = None
DrawPolygon.argtypes = [POINTER(DrawingWand), size_t, POINTER(PointInfo)]
DrawPolyline = _lib.DrawPolyline
DrawPolyline.restype = None
DrawPolyline.argtypes = [POINTER(DrawingWand), size_t, POINTER(PointInfo)]
DrawPopClipPath = _lib.DrawPopClipPath
DrawPopClipPath.restype = None
DrawPopClipPath.argtypes = [POINTER(DrawingWand)]
DrawPopDefs = _lib.DrawPopDefs
DrawPopDefs.restype = None
DrawPopDefs.argtypes = [POINTER(DrawingWand)]
DrawPushClipPath = _lib.DrawPushClipPath
DrawPushClipPath.restype = None
DrawPushClipPath.argtypes = [POINTER(DrawingWand), STRING]
DrawPushDefs = _lib.DrawPushDefs
DrawPushDefs.restype = None
DrawPushDefs.argtypes = [POINTER(DrawingWand)]
DrawRectangle = _lib.DrawRectangle
DrawRectangle.restype = None
DrawRectangle.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double]
DrawResetVectorGraphics = _lib.DrawResetVectorGraphics
DrawResetVectorGraphics.restype = None
DrawResetVectorGraphics.argtypes = [POINTER(DrawingWand)]
DrawRotate = _lib.DrawRotate
DrawRotate.restype = None
DrawRotate.argtypes = [POINTER(DrawingWand), c_double]
DrawRoundRectangle = _lib.DrawRoundRectangle
DrawRoundRectangle.restype = None
DrawRoundRectangle.argtypes = [POINTER(DrawingWand), c_double, c_double, c_double, c_double, c_double, c_double]
DrawScale = _lib.DrawScale
DrawScale.restype = None
DrawScale.argtypes = [POINTER(DrawingWand), c_double, c_double]
DrawSetBorderColor = _lib.DrawSetBorderColor
DrawSetBorderColor.restype = None
DrawSetBorderColor.argtypes = [POINTER(DrawingWand), POINTER(PixelWand)]
DrawSetClipRule = _lib.DrawSetClipRule
DrawSetClipRule.restype = None
DrawSetClipRule.argtypes = [POINTER(DrawingWand), FillRule]
DrawSetClipUnits = _lib.DrawSetClipUnits
DrawSetClipUnits.restype = None
DrawSetClipUnits.argtypes = [POINTER(DrawingWand), ClipPathUnits]
DrawSetFillColor = _lib.DrawSetFillColor
DrawSetFillColor.restype = None
DrawSetFillColor.argtypes = [POINTER(DrawingWand), POINTER(PixelWand)]
DrawSetFillOpacity = _lib.DrawSetFillOpacity
DrawSetFillOpacity.restype = None
DrawSetFillOpacity.argtypes = [POINTER(DrawingWand), c_double]
DrawSetFillRule = _lib.DrawSetFillRule
DrawSetFillRule.restype = None
DrawSetFillRule.argtypes = [POINTER(DrawingWand), FillRule]
DrawSetFontSize = _lib.DrawSetFontSize
DrawSetFontSize.restype = None
DrawSetFontSize.argtypes = [POINTER(DrawingWand), c_double]
DrawSetFontStretch = _lib.DrawSetFontStretch
DrawSetFontStretch.restype = None
DrawSetFontStretch.argtypes = [POINTER(DrawingWand), StretchType]
DrawSetFontStyle = _lib.DrawSetFontStyle
DrawSetFontStyle.restype = None
DrawSetFontStyle.argtypes = [POINTER(DrawingWand), StyleType]
DrawSetFontWeight = _lib.DrawSetFontWeight
DrawSetFontWeight.restype = None
DrawSetFontWeight.argtypes = [POINTER(DrawingWand), size_t]
DrawSetGravity = _lib.DrawSetGravity
DrawSetGravity.restype = None
DrawSetGravity.argtypes = [POINTER(DrawingWand), GravityType]
DrawSetOpacity = _lib.DrawSetOpacity
DrawSetOpacity.restype = None
DrawSetOpacity.argtypes = [POINTER(DrawingWand), c_double]
DrawSetStrokeAntialias = _lib.DrawSetStrokeAntialias
DrawSetStrokeAntialias.restype = None
DrawSetStrokeAntialias.argtypes = [POINTER(DrawingWand), MagickBooleanType]
DrawSetStrokeColor = _lib.DrawSetStrokeColor
DrawSetStrokeColor.restype = None
DrawSetStrokeColor.argtypes = [POINTER(DrawingWand), POINTER(PixelWand)]
DrawSetStrokeDashOffset = _lib.DrawSetStrokeDashOffset
DrawSetStrokeDashOffset.restype = None
DrawSetStrokeDashOffset.argtypes = [POINTER(DrawingWand), c_double]
DrawSetStrokeLineCap = _lib.DrawSetStrokeLineCap
DrawSetStrokeLineCap.restype = None
DrawSetStrokeLineCap.argtypes = [POINTER(DrawingWand), LineCap]
DrawSetStrokeLineJoin = _lib.DrawSetStrokeLineJoin
DrawSetStrokeLineJoin.restype = None
DrawSetStrokeLineJoin.argtypes = [POINTER(DrawingWand), LineJoin]
DrawSetStrokeMiterLimit = _lib.DrawSetStrokeMiterLimit
DrawSetStrokeMiterLimit.restype = None
DrawSetStrokeMiterLimit.argtypes = [POINTER(DrawingWand), size_t]
DrawSetStrokeOpacity = _lib.DrawSetStrokeOpacity
DrawSetStrokeOpacity.restype = None
DrawSetStrokeOpacity.argtypes = [POINTER(DrawingWand), c_double]
DrawSetStrokeWidth = _lib.DrawSetStrokeWidth
DrawSetStrokeWidth.restype = None
DrawSetStrokeWidth.argtypes = [POINTER(DrawingWand), c_double]
DrawSetTextAlignment = _lib.DrawSetTextAlignment
DrawSetTextAlignment.restype = None
DrawSetTextAlignment.argtypes = [POINTER(DrawingWand), AlignType]
DrawSetTextAntialias = _lib.DrawSetTextAntialias
DrawSetTextAntialias.restype = None
DrawSetTextAntialias.argtypes = [POINTER(DrawingWand), MagickBooleanType]
DrawSetTextDecoration = _lib.DrawSetTextDecoration
DrawSetTextDecoration.restype = None
DrawSetTextDecoration.argtypes = [POINTER(DrawingWand), DecorationType]
DrawSetTextEncoding = _lib.DrawSetTextEncoding
DrawSetTextEncoding.restype = None
DrawSetTextEncoding.argtypes = [POINTER(DrawingWand), STRING]
DrawSetTextUnderColor = _lib.DrawSetTextUnderColor
DrawSetTextUnderColor.restype = None
DrawSetTextUnderColor.argtypes = [POINTER(DrawingWand), POINTER(PixelWand)]
DrawSetViewbox = _lib.DrawSetViewbox
DrawSetViewbox.restype = None
DrawSetViewbox.argtypes = [POINTER(DrawingWand), ssize_t, ssize_t, ssize_t, ssize_t]
DrawSkewX = _lib.DrawSkewX
DrawSkewX.restype = None
DrawSkewX.argtypes = [POINTER(DrawingWand), c_double]
DrawSkewY = _lib.DrawSkewY
DrawSkewY.restype = None
DrawSkewY.argtypes = [POINTER(DrawingWand), c_double]
DrawTranslate = _lib.DrawTranslate
DrawTranslate.restype = None
DrawTranslate.argtypes = [POINTER(DrawingWand), c_double, c_double]
IdentifyImageCommand = _lib.IdentifyImageCommand
IdentifyImageCommand.restype = MagickBooleanType
IdentifyImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
ImportImageCommand = _lib.ImportImageCommand
ImportImageCommand.restype = MagickBooleanType
ImportImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
MagickGetImageChannelFeatures = _lib.MagickGetImageChannelFeatures
MagickGetImageChannelFeatures.restype = POINTER(ChannelFeatures)
MagickGetImageChannelFeatures.argtypes = [POINTER(MagickWand), size_t]
MagickGetImageChannelStatistics = _lib.MagickGetImageChannelStatistics
MagickGetImageChannelStatistics.restype = POINTER(ChannelStatistics)
MagickGetImageChannelStatistics.argtypes = [POINTER(MagickWand)]
MagickGetImageFilename = _lib.MagickGetImageFilename
MagickGetImageFilename.restype = STRING
MagickGetImageFilename.argtypes = [POINTER(MagickWand)]
MagickGetImageFormat = _lib.MagickGetImageFormat
MagickGetImageFormat.restype = STRING
MagickGetImageFormat.argtypes = [POINTER(MagickWand)]
MagickGetImageSignature = _lib.MagickGetImageSignature
MagickGetImageSignature.restype = STRING
MagickGetImageSignature.argtypes = [POINTER(MagickWand)]
MagickIdentifyImage = _lib.MagickIdentifyImage
MagickIdentifyImage.restype = STRING
MagickIdentifyImage.argtypes = [POINTER(MagickWand)]
MagickGetImageColorspace = _lib.MagickGetImageColorspace
MagickGetImageColorspace.restype = ColorspaceType
MagickGetImageColorspace.argtypes = [POINTER(MagickWand)]
MagickGetImageCompose = _lib.MagickGetImageCompose
MagickGetImageCompose.restype = CompositeOperator
MagickGetImageCompose.argtypes = [POINTER(MagickWand)]

# values for enumeration 'CompressionType'
UndefinedCompression = 0
NoCompression = 1
BZipCompression = 2
DXT1Compression = 3
DXT3Compression = 4
DXT5Compression = 5
FaxCompression = 6
Group4Compression = 7
JPEGCompression = 8
JPEG2000Compression = 9
LosslessJPEGCompression = 10
LZWCompression = 11
RLECompression = 12
ZipCompression = 13
ZipSCompression = 14
PizCompression = 15
Pxr24Compression = 16
B44Compression = 17
B44ACompression = 18
LZMACompression = 19
JBIG1Compression = 20
JBIG2Compression = 21
CompressionType = c_int # enum
MagickGetImageCompression = _lib.MagickGetImageCompression
MagickGetImageCompression.restype = CompressionType
MagickGetImageCompression.argtypes = [POINTER(MagickWand)]

# values for enumeration 'DisposeType'
UnrecognizedDispose = 0
UndefinedDispose = 0
NoneDispose = 1
BackgroundDispose = 2
PreviousDispose = 3
DisposeType = c_int # enum
MagickGetImageDispose = _lib.MagickGetImageDispose
MagickGetImageDispose.restype = DisposeType
MagickGetImageDispose.argtypes = [POINTER(MagickWand)]
MagickGetImageChannelDistortions = _lib.MagickGetImageChannelDistortions
MagickGetImageChannelDistortions.restype = POINTER(c_double)
MagickGetImageChannelDistortions.argtypes = [POINTER(MagickWand), POINTER(MagickWand), MetricType]
MagickGetImageFuzz = _lib.MagickGetImageFuzz
MagickGetImageFuzz.restype = c_double
MagickGetImageFuzz.argtypes = [POINTER(MagickWand)]
MagickGetImageGamma = _lib.MagickGetImageGamma
MagickGetImageGamma.restype = c_double
MagickGetImageGamma.argtypes = [POINTER(MagickWand)]
MagickGetImageTotalInkDensity = _lib.MagickGetImageTotalInkDensity
MagickGetImageTotalInkDensity.restype = c_double
MagickGetImageTotalInkDensity.argtypes = [POINTER(MagickWand)]
MagickGetImageGravity = _lib.MagickGetImageGravity
MagickGetImageGravity.restype = GravityType
MagickGetImageGravity.argtypes = [POINTER(MagickWand)]
MagickDestroyImage = _lib.MagickDestroyImage
MagickDestroyImage.restype = POINTER(Image)
MagickDestroyImage.argtypes = [POINTER(Image)]
GetImageFromMagickWand = _lib.GetImageFromMagickWand
GetImageFromMagickWand.restype = POINTER(Image)
GetImageFromMagickWand.argtypes = [POINTER(MagickWand)]
MagickGetImageType = _lib.MagickGetImageType
MagickGetImageType.restype = ImageType
MagickGetImageType.argtypes = [POINTER(MagickWand)]

# values for enumeration 'InterlaceType'
UndefinedInterlace = 0
NoInterlace = 1
LineInterlace = 2
PlaneInterlace = 3
PartitionInterlace = 4
GIFInterlace = 5
JPEGInterlace = 6
PNGInterlace = 7
InterlaceType = c_int # enum
MagickGetImageInterlaceScheme = _lib.MagickGetImageInterlaceScheme
MagickGetImageInterlaceScheme.restype = InterlaceType
MagickGetImageInterlaceScheme.argtypes = [POINTER(MagickWand)]
MagickGetImageInterpolateMethod = _lib.MagickGetImageInterpolateMethod
MagickGetImageInterpolateMethod.restype = InterpolatePixelMethod
MagickGetImageInterpolateMethod.argtypes = [POINTER(MagickWand)]
MagickAdaptiveBlurImage = _lib.MagickAdaptiveBlurImage
MagickAdaptiveBlurImage.restype = MagickBooleanType
MagickAdaptiveBlurImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickAdaptiveBlurImageChannel = _lib.MagickAdaptiveBlurImageChannel
MagickAdaptiveBlurImageChannel.restype = MagickBooleanType
MagickAdaptiveBlurImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double]
MagickAdaptiveResizeImage = _lib.MagickAdaptiveResizeImage
MagickAdaptiveResizeImage.restype = MagickBooleanType
MagickAdaptiveResizeImage.argtypes = [POINTER(MagickWand), size_t, size_t]
MagickAdaptiveSharpenImage = _lib.MagickAdaptiveSharpenImage
MagickAdaptiveSharpenImage.restype = MagickBooleanType
MagickAdaptiveSharpenImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickAdaptiveSharpenImageChannel = _lib.MagickAdaptiveSharpenImageChannel
MagickAdaptiveSharpenImageChannel.restype = MagickBooleanType
MagickAdaptiveSharpenImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double]
MagickAdaptiveThresholdImage = _lib.MagickAdaptiveThresholdImage
MagickAdaptiveThresholdImage.restype = MagickBooleanType
MagickAdaptiveThresholdImage.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t]
MagickAddImage = _lib.MagickAddImage
MagickAddImage.restype = MagickBooleanType
MagickAddImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand)]
MagickAddNoiseImage = _lib.MagickAddNoiseImage
MagickAddNoiseImage.restype = MagickBooleanType
MagickAddNoiseImage.argtypes = [POINTER(MagickWand), NoiseType]
MagickAddNoiseImageChannel = _lib.MagickAddNoiseImageChannel
MagickAddNoiseImageChannel.restype = MagickBooleanType
MagickAddNoiseImageChannel.argtypes = [POINTER(MagickWand), ChannelType, NoiseType]
MagickAffineTransformImage = _lib.MagickAffineTransformImage
MagickAffineTransformImage.restype = MagickBooleanType
MagickAffineTransformImage.argtypes = [POINTER(MagickWand), POINTER(DrawingWand)]
MagickAnnotateImage = _lib.MagickAnnotateImage
MagickAnnotateImage.restype = MagickBooleanType
MagickAnnotateImage.argtypes = [POINTER(MagickWand), POINTER(DrawingWand), c_double, c_double, c_double, STRING]
MagickAnimateImages = _lib.MagickAnimateImages
MagickAnimateImages.restype = MagickBooleanType
MagickAnimateImages.argtypes = [POINTER(MagickWand), STRING]
MagickAutoGammaImage = _lib.MagickAutoGammaImage
MagickAutoGammaImage.restype = MagickBooleanType
MagickAutoGammaImage.argtypes = [POINTER(MagickWand)]
MagickAutoGammaImageChannel = _lib.MagickAutoGammaImageChannel
MagickAutoGammaImageChannel.restype = MagickBooleanType
MagickAutoGammaImageChannel.argtypes = [POINTER(MagickWand), ChannelType]
MagickAutoLevelImage = _lib.MagickAutoLevelImage
MagickAutoLevelImage.restype = MagickBooleanType
MagickAutoLevelImage.argtypes = [POINTER(MagickWand)]
MagickAutoLevelImageChannel = _lib.MagickAutoLevelImageChannel
MagickAutoLevelImageChannel.restype = MagickBooleanType
MagickAutoLevelImageChannel.argtypes = [POINTER(MagickWand), ChannelType]
MagickBlackThresholdImage = _lib.MagickBlackThresholdImage
MagickBlackThresholdImage.restype = MagickBooleanType
MagickBlackThresholdImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickBlueShiftImage = _lib.MagickBlueShiftImage
MagickBlueShiftImage.restype = MagickBooleanType
MagickBlueShiftImage.argtypes = [POINTER(MagickWand), c_double]
MagickBlurImage = _lib.MagickBlurImage
MagickBlurImage.restype = MagickBooleanType
MagickBlurImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickBlurImageChannel = _lib.MagickBlurImageChannel
MagickBlurImageChannel.restype = MagickBooleanType
MagickBlurImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double]
MagickBorderImage = _lib.MagickBorderImage
MagickBorderImage.restype = MagickBooleanType
MagickBorderImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), size_t, size_t]
MagickBrightnessContrastImage = _lib.MagickBrightnessContrastImage
MagickBrightnessContrastImage.restype = MagickBooleanType
MagickBrightnessContrastImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickBrightnessContrastImageChannel = _lib.MagickBrightnessContrastImageChannel
MagickBrightnessContrastImageChannel.restype = MagickBooleanType
MagickBrightnessContrastImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double]
MagickCharcoalImage = _lib.MagickCharcoalImage
MagickCharcoalImage.restype = MagickBooleanType
MagickCharcoalImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickChopImage = _lib.MagickChopImage
MagickChopImage.restype = MagickBooleanType
MagickChopImage.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t, ssize_t]
MagickClampImage = _lib.MagickClampImage
MagickClampImage.restype = MagickBooleanType
MagickClampImage.argtypes = [POINTER(MagickWand)]
MagickClampImageChannel = _lib.MagickClampImageChannel
MagickClampImageChannel.restype = MagickBooleanType
MagickClampImageChannel.argtypes = [POINTER(MagickWand), ChannelType]
MagickClipImage = _lib.MagickClipImage
MagickClipImage.restype = MagickBooleanType
MagickClipImage.argtypes = [POINTER(MagickWand)]
MagickClipImagePath = _lib.MagickClipImagePath
MagickClipImagePath.restype = MagickBooleanType
MagickClipImagePath.argtypes = [POINTER(MagickWand), STRING, MagickBooleanType]
MagickClutImage = _lib.MagickClutImage
MagickClutImage.restype = MagickBooleanType
MagickClutImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand)]
MagickClutImageChannel = _lib.MagickClutImageChannel
MagickClutImageChannel.restype = MagickBooleanType
MagickClutImageChannel.argtypes = [POINTER(MagickWand), ChannelType, POINTER(MagickWand)]
MagickColorDecisionListImage = _lib.MagickColorDecisionListImage
MagickColorDecisionListImage.restype = MagickBooleanType
MagickColorDecisionListImage.argtypes = [POINTER(MagickWand), STRING]
MagickColorizeImage = _lib.MagickColorizeImage
MagickColorizeImage.restype = MagickBooleanType
MagickColorizeImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), POINTER(PixelWand)]
MagickColorMatrixImage = _lib.MagickColorMatrixImage
MagickColorMatrixImage.restype = MagickBooleanType
MagickColorMatrixImage.argtypes = [POINTER(MagickWand), POINTER(KernelInfo)]
MagickCommentImage = _lib.MagickCommentImage
MagickCommentImage.restype = MagickBooleanType
MagickCommentImage.argtypes = [POINTER(MagickWand), STRING]
MagickCompositeImage = _lib.MagickCompositeImage
MagickCompositeImage.restype = MagickBooleanType
MagickCompositeImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand), CompositeOperator, ssize_t, ssize_t]
MagickCompositeImageChannel = _lib.MagickCompositeImageChannel
MagickCompositeImageChannel.restype = MagickBooleanType
MagickCompositeImageChannel.argtypes = [POINTER(MagickWand), ChannelType, POINTER(MagickWand), CompositeOperator, ssize_t, ssize_t]
MagickConstituteImage = _lib.MagickConstituteImage
MagickConstituteImage.restype = MagickBooleanType
MagickConstituteImage.argtypes = [POINTER(MagickWand), size_t, size_t, STRING, StorageType, c_void_p]
MagickContrastImage = _lib.MagickContrastImage
MagickContrastImage.restype = MagickBooleanType
MagickContrastImage.argtypes = [POINTER(MagickWand), MagickBooleanType]
MagickContrastStretchImage = _lib.MagickContrastStretchImage
MagickContrastStretchImage.restype = MagickBooleanType
MagickContrastStretchImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickContrastStretchImageChannel = _lib.MagickContrastStretchImageChannel
MagickContrastStretchImageChannel.restype = MagickBooleanType
MagickContrastStretchImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double]
MagickConvolveImage = _lib.MagickConvolveImage
MagickConvolveImage.restype = MagickBooleanType
MagickConvolveImage.argtypes = [POINTER(MagickWand), size_t, POINTER(c_double)]
MagickConvolveImageChannel = _lib.MagickConvolveImageChannel
MagickConvolveImageChannel.restype = MagickBooleanType
MagickConvolveImageChannel.argtypes = [POINTER(MagickWand), ChannelType, size_t, POINTER(c_double)]
MagickCropImage = _lib.MagickCropImage
MagickCropImage.restype = MagickBooleanType
MagickCropImage.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t, ssize_t]
MagickCycleColormapImage = _lib.MagickCycleColormapImage
MagickCycleColormapImage.restype = MagickBooleanType
MagickCycleColormapImage.argtypes = [POINTER(MagickWand), ssize_t]
MagickDecipherImage = _lib.MagickDecipherImage
MagickDecipherImage.restype = MagickBooleanType
MagickDecipherImage.argtypes = [POINTER(MagickWand), STRING]
MagickDeskewImage = _lib.MagickDeskewImage
MagickDeskewImage.restype = MagickBooleanType
MagickDeskewImage.argtypes = [POINTER(MagickWand), c_double]
MagickDespeckleImage = _lib.MagickDespeckleImage
MagickDespeckleImage.restype = MagickBooleanType
MagickDespeckleImage.argtypes = [POINTER(MagickWand)]
MagickDisplayImage = _lib.MagickDisplayImage
MagickDisplayImage.restype = MagickBooleanType
MagickDisplayImage.argtypes = [POINTER(MagickWand), STRING]
MagickDisplayImages = _lib.MagickDisplayImages
MagickDisplayImages.restype = MagickBooleanType
MagickDisplayImages.argtypes = [POINTER(MagickWand), STRING]
MagickDistortImage = _lib.MagickDistortImage
MagickDistortImage.restype = MagickBooleanType
MagickDistortImage.argtypes = [POINTER(MagickWand), DistortImageMethod, size_t, POINTER(c_double), MagickBooleanType]
MagickDrawImage = _lib.MagickDrawImage
MagickDrawImage.restype = MagickBooleanType
MagickDrawImage.argtypes = [POINTER(MagickWand), POINTER(DrawingWand)]
MagickEdgeImage = _lib.MagickEdgeImage
MagickEdgeImage.restype = MagickBooleanType
MagickEdgeImage.argtypes = [POINTER(MagickWand), c_double]
MagickEmbossImage = _lib.MagickEmbossImage
MagickEmbossImage.restype = MagickBooleanType
MagickEmbossImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickEncipherImage = _lib.MagickEncipherImage
MagickEncipherImage.restype = MagickBooleanType
MagickEncipherImage.argtypes = [POINTER(MagickWand), STRING]
MagickEnhanceImage = _lib.MagickEnhanceImage
MagickEnhanceImage.restype = MagickBooleanType
MagickEnhanceImage.argtypes = [POINTER(MagickWand)]
MagickEqualizeImage = _lib.MagickEqualizeImage
MagickEqualizeImage.restype = MagickBooleanType
MagickEqualizeImage.argtypes = [POINTER(MagickWand)]
MagickEqualizeImageChannel = _lib.MagickEqualizeImageChannel
MagickEqualizeImageChannel.restype = MagickBooleanType
MagickEqualizeImageChannel.argtypes = [POINTER(MagickWand), ChannelType]
MagickEvaluateImage = _lib.MagickEvaluateImage
MagickEvaluateImage.restype = MagickBooleanType
MagickEvaluateImage.argtypes = [POINTER(MagickWand), MagickEvaluateOperator, c_double]
MagickEvaluateImageChannel = _lib.MagickEvaluateImageChannel
MagickEvaluateImageChannel.restype = MagickBooleanType
MagickEvaluateImageChannel.argtypes = [POINTER(MagickWand), ChannelType, MagickEvaluateOperator, c_double]
MagickExportImagePixels = _lib.MagickExportImagePixels
MagickExportImagePixels.restype = MagickBooleanType
MagickExportImagePixels.argtypes = [POINTER(MagickWand), ssize_t, ssize_t, size_t, size_t, STRING, StorageType, c_void_p]
MagickExtentImage = _lib.MagickExtentImage
MagickExtentImage.restype = MagickBooleanType
MagickExtentImage.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t, ssize_t]
MagickFilterImage = _lib.MagickFilterImage
MagickFilterImage.restype = MagickBooleanType
MagickFilterImage.argtypes = [POINTER(MagickWand), POINTER(KernelInfo)]
MagickFilterImageChannel = _lib.MagickFilterImageChannel
MagickFilterImageChannel.restype = MagickBooleanType
MagickFilterImageChannel.argtypes = [POINTER(MagickWand), ChannelType, POINTER(KernelInfo)]
MagickFlipImage = _lib.MagickFlipImage
MagickFlipImage.restype = MagickBooleanType
MagickFlipImage.argtypes = [POINTER(MagickWand)]
MagickFloodfillPaintImage = _lib.MagickFloodfillPaintImage
MagickFloodfillPaintImage.restype = MagickBooleanType
MagickFloodfillPaintImage.argtypes = [POINTER(MagickWand), ChannelType, POINTER(PixelWand), c_double, POINTER(PixelWand), ssize_t, ssize_t, MagickBooleanType]
MagickFlopImage = _lib.MagickFlopImage
MagickFlopImage.restype = MagickBooleanType
MagickFlopImage.argtypes = [POINTER(MagickWand)]
MagickForwardFourierTransformImage = _lib.MagickForwardFourierTransformImage
MagickForwardFourierTransformImage.restype = MagickBooleanType
MagickForwardFourierTransformImage.argtypes = [POINTER(MagickWand), MagickBooleanType]
MagickFrameImage = _lib.MagickFrameImage
MagickFrameImage.restype = MagickBooleanType
MagickFrameImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), size_t, size_t, ssize_t, ssize_t]
MagickFunctionImage = _lib.MagickFunctionImage
MagickFunctionImage.restype = MagickBooleanType
MagickFunctionImage.argtypes = [POINTER(MagickWand), MagickFunction, size_t, POINTER(c_double)]
MagickFunctionImageChannel = _lib.MagickFunctionImageChannel
MagickFunctionImageChannel.restype = MagickBooleanType
MagickFunctionImageChannel.argtypes = [POINTER(MagickWand), ChannelType, MagickFunction, size_t, POINTER(c_double)]
MagickGammaImage = _lib.MagickGammaImage
MagickGammaImage.restype = MagickBooleanType
MagickGammaImage.argtypes = [POINTER(MagickWand), c_double]
MagickGammaImageChannel = _lib.MagickGammaImageChannel
MagickGammaImageChannel.restype = MagickBooleanType
MagickGammaImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double]
MagickGaussianBlurImage = _lib.MagickGaussianBlurImage
MagickGaussianBlurImage.restype = MagickBooleanType
MagickGaussianBlurImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickGaussianBlurImageChannel = _lib.MagickGaussianBlurImageChannel
MagickGaussianBlurImageChannel.restype = MagickBooleanType
MagickGaussianBlurImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double]
MagickGetImageAlphaChannel = _lib.MagickGetImageAlphaChannel
MagickGetImageAlphaChannel.restype = MagickBooleanType
MagickGetImageAlphaChannel.argtypes = [POINTER(MagickWand)]
MagickGetImageBackgroundColor = _lib.MagickGetImageBackgroundColor
MagickGetImageBackgroundColor.restype = MagickBooleanType
MagickGetImageBackgroundColor.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickGetImageBluePrimary = _lib.MagickGetImageBluePrimary
MagickGetImageBluePrimary.restype = MagickBooleanType
MagickGetImageBluePrimary.argtypes = [POINTER(MagickWand), POINTER(c_double), POINTER(c_double)]
MagickGetImageBorderColor = _lib.MagickGetImageBorderColor
MagickGetImageBorderColor.restype = MagickBooleanType
MagickGetImageBorderColor.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickGetImageChannelDistortion = _lib.MagickGetImageChannelDistortion
MagickGetImageChannelDistortion.restype = MagickBooleanType
MagickGetImageChannelDistortion.argtypes = [POINTER(MagickWand), POINTER(MagickWand), ChannelType, MetricType, POINTER(c_double)]
MagickGetImageChannelKurtosis = _lib.MagickGetImageChannelKurtosis
MagickGetImageChannelKurtosis.restype = MagickBooleanType
MagickGetImageChannelKurtosis.argtypes = [POINTER(MagickWand), ChannelType, POINTER(c_double), POINTER(c_double)]
MagickGetImageChannelMean = _lib.MagickGetImageChannelMean
MagickGetImageChannelMean.restype = MagickBooleanType
MagickGetImageChannelMean.argtypes = [POINTER(MagickWand), ChannelType, POINTER(c_double), POINTER(c_double)]
MagickGetImageChannelRange = _lib.MagickGetImageChannelRange
MagickGetImageChannelRange.restype = MagickBooleanType
MagickGetImageChannelRange.argtypes = [POINTER(MagickWand), ChannelType, POINTER(c_double), POINTER(c_double)]
MagickGetImageColormapColor = _lib.MagickGetImageColormapColor
MagickGetImageColormapColor.restype = MagickBooleanType
MagickGetImageColormapColor.argtypes = [POINTER(MagickWand), size_t, POINTER(PixelWand)]
MagickGetImageDistortion = _lib.MagickGetImageDistortion
MagickGetImageDistortion.restype = MagickBooleanType
MagickGetImageDistortion.argtypes = [POINTER(MagickWand), POINTER(MagickWand), MetricType, POINTER(c_double)]
MagickGetImageGreenPrimary = _lib.MagickGetImageGreenPrimary
MagickGetImageGreenPrimary.restype = MagickBooleanType
MagickGetImageGreenPrimary.argtypes = [POINTER(MagickWand), POINTER(c_double), POINTER(c_double)]
MagickGetImageMatteColor = _lib.MagickGetImageMatteColor
MagickGetImageMatteColor.restype = MagickBooleanType
MagickGetImageMatteColor.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickGetImageLength = _lib.MagickGetImageLength
MagickGetImageLength.restype = MagickBooleanType
MagickGetImageLength.argtypes = [POINTER(MagickWand), POINTER(MagickSizeType)]
MagickGetImagePage = _lib.MagickGetImagePage
MagickGetImagePage.restype = MagickBooleanType
MagickGetImagePage.argtypes = [POINTER(MagickWand), POINTER(size_t), POINTER(size_t), POINTER(ssize_t), POINTER(ssize_t)]
MagickGetImagePixelColor = _lib.MagickGetImagePixelColor
MagickGetImagePixelColor.restype = MagickBooleanType
MagickGetImagePixelColor.argtypes = [POINTER(MagickWand), ssize_t, ssize_t, POINTER(PixelWand)]
MagickGetImageRange = _lib.MagickGetImageRange
MagickGetImageRange.restype = MagickBooleanType
MagickGetImageRange.argtypes = [POINTER(MagickWand), POINTER(c_double), POINTER(c_double)]
MagickGetImageRedPrimary = _lib.MagickGetImageRedPrimary
MagickGetImageRedPrimary.restype = MagickBooleanType
MagickGetImageRedPrimary.argtypes = [POINTER(MagickWand), POINTER(c_double), POINTER(c_double)]
MagickGetImageResolution = _lib.MagickGetImageResolution
MagickGetImageResolution.restype = MagickBooleanType
MagickGetImageResolution.argtypes = [POINTER(MagickWand), POINTER(c_double), POINTER(c_double)]
MagickGetImageWhitePoint = _lib.MagickGetImageWhitePoint
MagickGetImageWhitePoint.restype = MagickBooleanType
MagickGetImageWhitePoint.argtypes = [POINTER(MagickWand), POINTER(c_double), POINTER(c_double)]
MagickHaldClutImage = _lib.MagickHaldClutImage
MagickHaldClutImage.restype = MagickBooleanType
MagickHaldClutImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand)]
MagickHaldClutImageChannel = _lib.MagickHaldClutImageChannel
MagickHaldClutImageChannel.restype = MagickBooleanType
MagickHaldClutImageChannel.argtypes = [POINTER(MagickWand), ChannelType, POINTER(MagickWand)]
MagickHasNextImage = _lib.MagickHasNextImage
MagickHasNextImage.restype = MagickBooleanType
MagickHasNextImage.argtypes = [POINTER(MagickWand)]
MagickHasPreviousImage = _lib.MagickHasPreviousImage
MagickHasPreviousImage.restype = MagickBooleanType
MagickHasPreviousImage.argtypes = [POINTER(MagickWand)]
MagickImplodeImage = _lib.MagickImplodeImage
MagickImplodeImage.restype = MagickBooleanType
MagickImplodeImage.argtypes = [POINTER(MagickWand), c_double]
MagickImportImagePixels = _lib.MagickImportImagePixels
MagickImportImagePixels.restype = MagickBooleanType
MagickImportImagePixels.argtypes = [POINTER(MagickWand), ssize_t, ssize_t, size_t, size_t, STRING, StorageType, c_void_p]
MagickInverseFourierTransformImage = _lib.MagickInverseFourierTransformImage
MagickInverseFourierTransformImage.restype = MagickBooleanType
MagickInverseFourierTransformImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand), MagickBooleanType]
MagickLabelImage = _lib.MagickLabelImage
MagickLabelImage.restype = MagickBooleanType
MagickLabelImage.argtypes = [POINTER(MagickWand), STRING]
MagickLevelImage = _lib.MagickLevelImage
MagickLevelImage.restype = MagickBooleanType
MagickLevelImage.argtypes = [POINTER(MagickWand), c_double, c_double, c_double]
MagickLevelImageChannel = _lib.MagickLevelImageChannel
MagickLevelImageChannel.restype = MagickBooleanType
MagickLevelImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double, c_double]
MagickLinearStretchImage = _lib.MagickLinearStretchImage
MagickLinearStretchImage.restype = MagickBooleanType
MagickLinearStretchImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickLiquidRescaleImage = _lib.MagickLiquidRescaleImage
MagickLiquidRescaleImage.restype = MagickBooleanType
MagickLiquidRescaleImage.argtypes = [POINTER(MagickWand), size_t, size_t, c_double, c_double]
MagickMagnifyImage = _lib.MagickMagnifyImage
MagickMagnifyImage.restype = MagickBooleanType
MagickMagnifyImage.argtypes = [POINTER(MagickWand)]
MagickMedianFilterImage = _lib.MagickMedianFilterImage
MagickMedianFilterImage.restype = MagickBooleanType
MagickMedianFilterImage.argtypes = [POINTER(MagickWand), c_double]
MagickMinifyImage = _lib.MagickMinifyImage
MagickMinifyImage.restype = MagickBooleanType
MagickMinifyImage.argtypes = [POINTER(MagickWand)]
MagickModeImage = _lib.MagickModeImage
MagickModeImage.restype = MagickBooleanType
MagickModeImage.argtypes = [POINTER(MagickWand), c_double]
MagickModulateImage = _lib.MagickModulateImage
MagickModulateImage.restype = MagickBooleanType
MagickModulateImage.argtypes = [POINTER(MagickWand), c_double, c_double, c_double]
MagickMorphologyImage = _lib.MagickMorphologyImage
MagickMorphologyImage.restype = MagickBooleanType
MagickMorphologyImage.argtypes = [POINTER(MagickWand), MorphologyMethod, ssize_t, POINTER(KernelInfo)]
MagickMorphologyImageChannel = _lib.MagickMorphologyImageChannel
MagickMorphologyImageChannel.restype = MagickBooleanType
MagickMorphologyImageChannel.argtypes = [POINTER(MagickWand), ChannelType, MorphologyMethod, ssize_t, POINTER(KernelInfo)]
MagickMotionBlurImage = _lib.MagickMotionBlurImage
MagickMotionBlurImage.restype = MagickBooleanType
MagickMotionBlurImage.argtypes = [POINTER(MagickWand), c_double, c_double, c_double]
MagickMotionBlurImageChannel = _lib.MagickMotionBlurImageChannel
MagickMotionBlurImageChannel.restype = MagickBooleanType
MagickMotionBlurImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double, c_double]
MagickNegateImage = _lib.MagickNegateImage
MagickNegateImage.restype = MagickBooleanType
MagickNegateImage.argtypes = [POINTER(MagickWand), MagickBooleanType]
MagickNegateImageChannel = _lib.MagickNegateImageChannel
MagickNegateImageChannel.restype = MagickBooleanType
MagickNegateImageChannel.argtypes = [POINTER(MagickWand), ChannelType, MagickBooleanType]
MagickNewImage = _lib.MagickNewImage
MagickNewImage.restype = MagickBooleanType
MagickNewImage.argtypes = [POINTER(MagickWand), size_t, size_t, POINTER(PixelWand)]
MagickNextImage = _lib.MagickNextImage
MagickNextImage.restype = MagickBooleanType
MagickNextImage.argtypes = [POINTER(MagickWand)]
MagickNormalizeImage = _lib.MagickNormalizeImage
MagickNormalizeImage.restype = MagickBooleanType
MagickNormalizeImage.argtypes = [POINTER(MagickWand)]
MagickNormalizeImageChannel = _lib.MagickNormalizeImageChannel
MagickNormalizeImageChannel.restype = MagickBooleanType
MagickNormalizeImageChannel.argtypes = [POINTER(MagickWand), ChannelType]
MagickOilPaintImage = _lib.MagickOilPaintImage
MagickOilPaintImage.restype = MagickBooleanType
MagickOilPaintImage.argtypes = [POINTER(MagickWand), c_double]
MagickOpaquePaintImage = _lib.MagickOpaquePaintImage
MagickOpaquePaintImage.restype = MagickBooleanType
MagickOpaquePaintImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), POINTER(PixelWand), c_double, MagickBooleanType]
MagickOpaquePaintImageChannel = _lib.MagickOpaquePaintImageChannel
MagickOpaquePaintImageChannel.restype = MagickBooleanType
MagickOpaquePaintImageChannel.argtypes = [POINTER(MagickWand), ChannelType, POINTER(PixelWand), POINTER(PixelWand), c_double, MagickBooleanType]
MagickOrderedPosterizeImage = _lib.MagickOrderedPosterizeImage
MagickOrderedPosterizeImage.restype = MagickBooleanType
MagickOrderedPosterizeImage.argtypes = [POINTER(MagickWand), STRING]
MagickOrderedPosterizeImageChannel = _lib.MagickOrderedPosterizeImageChannel
MagickOrderedPosterizeImageChannel.restype = MagickBooleanType
MagickOrderedPosterizeImageChannel.argtypes = [POINTER(MagickWand), ChannelType, STRING]
MagickTransparentPaintImage = _lib.MagickTransparentPaintImage
MagickTransparentPaintImage.restype = MagickBooleanType
MagickTransparentPaintImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), c_double, c_double, MagickBooleanType]
MagickPingImage = _lib.MagickPingImage
MagickPingImage.restype = MagickBooleanType
MagickPingImage.argtypes = [POINTER(MagickWand), STRING]
MagickPingImageBlob = _lib.MagickPingImageBlob
MagickPingImageBlob.restype = MagickBooleanType
MagickPingImageBlob.argtypes = [POINTER(MagickWand), c_void_p, size_t]
MagickPingImageFile = _lib.MagickPingImageFile
MagickPingImageFile.restype = MagickBooleanType
MagickPingImageFile.argtypes = [POINTER(MagickWand), POINTER(FILE)]
MagickPolaroidImage = _lib.MagickPolaroidImage
MagickPolaroidImage.restype = MagickBooleanType
MagickPolaroidImage.argtypes = [POINTER(MagickWand), POINTER(DrawingWand), c_double]
MagickPosterizeImage = _lib.MagickPosterizeImage
MagickPosterizeImage.restype = MagickBooleanType
MagickPosterizeImage.argtypes = [POINTER(MagickWand), size_t, MagickBooleanType]
MagickPreviousImage = _lib.MagickPreviousImage
MagickPreviousImage.restype = MagickBooleanType
MagickPreviousImage.argtypes = [POINTER(MagickWand)]
MagickQuantizeImage = _lib.MagickQuantizeImage
MagickQuantizeImage.restype = MagickBooleanType
MagickQuantizeImage.argtypes = [POINTER(MagickWand), size_t, ColorspaceType, size_t, MagickBooleanType, MagickBooleanType]
MagickQuantizeImages = _lib.MagickQuantizeImages
MagickQuantizeImages.restype = MagickBooleanType
MagickQuantizeImages.argtypes = [POINTER(MagickWand), size_t, ColorspaceType, size_t, MagickBooleanType, MagickBooleanType]
MagickRadialBlurImage = _lib.MagickRadialBlurImage
MagickRadialBlurImage.restype = MagickBooleanType
MagickRadialBlurImage.argtypes = [POINTER(MagickWand), c_double]
MagickRadialBlurImageChannel = _lib.MagickRadialBlurImageChannel
MagickRadialBlurImageChannel.restype = MagickBooleanType
MagickRadialBlurImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double]
MagickRaiseImage = _lib.MagickRaiseImage
MagickRaiseImage.restype = MagickBooleanType
MagickRaiseImage.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t, ssize_t, MagickBooleanType]
MagickRandomThresholdImage = _lib.MagickRandomThresholdImage
MagickRandomThresholdImage.restype = MagickBooleanType
MagickRandomThresholdImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickRandomThresholdImageChannel = _lib.MagickRandomThresholdImageChannel
MagickRandomThresholdImageChannel.restype = MagickBooleanType
MagickRandomThresholdImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double]
MagickReadImage = _lib.MagickReadImage
MagickReadImage.restype = MagickBooleanType
MagickReadImage.argtypes = [POINTER(MagickWand), STRING]
MagickReadImageBlob = _lib.MagickReadImageBlob
MagickReadImageBlob.restype = MagickBooleanType
MagickReadImageBlob.argtypes = [POINTER(MagickWand), c_void_p, size_t]
MagickReadImageFile = _lib.MagickReadImageFile
MagickReadImageFile.restype = MagickBooleanType
MagickReadImageFile.argtypes = [POINTER(MagickWand), POINTER(FILE)]
MagickReduceNoiseImage = _lib.MagickReduceNoiseImage
MagickReduceNoiseImage.restype = MagickBooleanType
MagickReduceNoiseImage.argtypes = [POINTER(MagickWand), c_double]

# values for enumeration 'DitherMethod'
UndefinedDitherMethod = 0
NoDitherMethod = 1
RiemersmaDitherMethod = 2
FloydSteinbergDitherMethod = 3
DitherMethod = c_int # enum
MagickRemapImage = _lib.MagickRemapImage
MagickRemapImage.restype = MagickBooleanType
MagickRemapImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand), DitherMethod]
MagickRemoveImage = _lib.MagickRemoveImage
MagickRemoveImage.restype = MagickBooleanType
MagickRemoveImage.argtypes = [POINTER(MagickWand)]
MagickResampleImage = _lib.MagickResampleImage
MagickResampleImage.restype = MagickBooleanType
MagickResampleImage.argtypes = [POINTER(MagickWand), c_double, c_double, FilterTypes, c_double]
MagickResetImagePage = _lib.MagickResetImagePage
MagickResetImagePage.restype = MagickBooleanType
MagickResetImagePage.argtypes = [POINTER(MagickWand), STRING]
MagickResizeImage = _lib.MagickResizeImage
MagickResizeImage.restype = MagickBooleanType
MagickResizeImage.argtypes = [POINTER(MagickWand), size_t, size_t, FilterTypes, c_double]
MagickRollImage = _lib.MagickRollImage
MagickRollImage.restype = MagickBooleanType
MagickRollImage.argtypes = [POINTER(MagickWand), ssize_t, ssize_t]
MagickRotateImage = _lib.MagickRotateImage
MagickRotateImage.restype = MagickBooleanType
MagickRotateImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), c_double]
MagickSampleImage = _lib.MagickSampleImage
MagickSampleImage.restype = MagickBooleanType
MagickSampleImage.argtypes = [POINTER(MagickWand), size_t, size_t]
MagickScaleImage = _lib.MagickScaleImage
MagickScaleImage.restype = MagickBooleanType
MagickScaleImage.argtypes = [POINTER(MagickWand), size_t, size_t]
MagickSegmentImage = _lib.MagickSegmentImage
MagickSegmentImage.restype = MagickBooleanType
MagickSegmentImage.argtypes = [POINTER(MagickWand), ColorspaceType, MagickBooleanType, c_double, c_double]
MagickSelectiveBlurImage = _lib.MagickSelectiveBlurImage
MagickSelectiveBlurImage.restype = MagickBooleanType
MagickSelectiveBlurImage.argtypes = [POINTER(MagickWand), c_double, c_double, c_double]
MagickSelectiveBlurImageChannel = _lib.MagickSelectiveBlurImageChannel
MagickSelectiveBlurImageChannel.restype = MagickBooleanType
MagickSelectiveBlurImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double, c_double]
MagickSeparateImageChannel = _lib.MagickSeparateImageChannel
MagickSeparateImageChannel.restype = MagickBooleanType
MagickSeparateImageChannel.argtypes = [POINTER(MagickWand), ChannelType]
MagickSepiaToneImage = _lib.MagickSepiaToneImage
MagickSepiaToneImage.restype = MagickBooleanType
MagickSepiaToneImage.argtypes = [POINTER(MagickWand), c_double]
MagickSetImage = _lib.MagickSetImage
MagickSetImage.restype = MagickBooleanType
MagickSetImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand)]
MagickSetImageAlphaChannel = _lib.MagickSetImageAlphaChannel
MagickSetImageAlphaChannel.restype = MagickBooleanType
MagickSetImageAlphaChannel.argtypes = [POINTER(MagickWand), AlphaChannelType]
MagickSetImageBackgroundColor = _lib.MagickSetImageBackgroundColor
MagickSetImageBackgroundColor.restype = MagickBooleanType
MagickSetImageBackgroundColor.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickSetImageBias = _lib.MagickSetImageBias
MagickSetImageBias.restype = MagickBooleanType
MagickSetImageBias.argtypes = [POINTER(MagickWand), c_double]
MagickSetImageBluePrimary = _lib.MagickSetImageBluePrimary
MagickSetImageBluePrimary.restype = MagickBooleanType
MagickSetImageBluePrimary.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickSetImageBorderColor = _lib.MagickSetImageBorderColor
MagickSetImageBorderColor.restype = MagickBooleanType
MagickSetImageBorderColor.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickSetImageChannelDepth = _lib.MagickSetImageChannelDepth
MagickSetImageChannelDepth.restype = MagickBooleanType
MagickSetImageChannelDepth.argtypes = [POINTER(MagickWand), ChannelType, size_t]
MagickSetImageClipMask = _lib.MagickSetImageClipMask
MagickSetImageClipMask.restype = MagickBooleanType
MagickSetImageClipMask.argtypes = [POINTER(MagickWand), POINTER(MagickWand)]
MagickSetImageColor = _lib.MagickSetImageColor
MagickSetImageColor.restype = MagickBooleanType
MagickSetImageColor.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickSetImageColormapColor = _lib.MagickSetImageColormapColor
MagickSetImageColormapColor.restype = MagickBooleanType
MagickSetImageColormapColor.argtypes = [POINTER(MagickWand), size_t, POINTER(PixelWand)]
MagickSetImageColorspace = _lib.MagickSetImageColorspace
MagickSetImageColorspace.restype = MagickBooleanType
MagickSetImageColorspace.argtypes = [POINTER(MagickWand), ColorspaceType]
MagickSetImageCompose = _lib.MagickSetImageCompose
MagickSetImageCompose.restype = MagickBooleanType
MagickSetImageCompose.argtypes = [POINTER(MagickWand), CompositeOperator]
MagickSetImageCompression = _lib.MagickSetImageCompression
MagickSetImageCompression.restype = MagickBooleanType
MagickSetImageCompression.argtypes = [POINTER(MagickWand), CompressionType]
MagickSetImageDelay = _lib.MagickSetImageDelay
MagickSetImageDelay.restype = MagickBooleanType
MagickSetImageDelay.argtypes = [POINTER(MagickWand), size_t]
MagickSetImageDepth = _lib.MagickSetImageDepth
MagickSetImageDepth.restype = MagickBooleanType
MagickSetImageDepth.argtypes = [POINTER(MagickWand), size_t]
MagickSetImageDispose = _lib.MagickSetImageDispose
MagickSetImageDispose.restype = MagickBooleanType
MagickSetImageDispose.argtypes = [POINTER(MagickWand), DisposeType]
MagickSetImageCompressionQuality = _lib.MagickSetImageCompressionQuality
MagickSetImageCompressionQuality.restype = MagickBooleanType
MagickSetImageCompressionQuality.argtypes = [POINTER(MagickWand), size_t]
MagickSetImageExtent = _lib.MagickSetImageExtent
MagickSetImageExtent.restype = MagickBooleanType
MagickSetImageExtent.argtypes = [POINTER(MagickWand), size_t, size_t]
MagickSetImageFilename = _lib.MagickSetImageFilename
MagickSetImageFilename.restype = MagickBooleanType
MagickSetImageFilename.argtypes = [POINTER(MagickWand), STRING]
MagickSetImageFormat = _lib.MagickSetImageFormat
MagickSetImageFormat.restype = MagickBooleanType
MagickSetImageFormat.argtypes = [POINTER(MagickWand), STRING]
MagickSetImageFuzz = _lib.MagickSetImageFuzz
MagickSetImageFuzz.restype = MagickBooleanType
MagickSetImageFuzz.argtypes = [POINTER(MagickWand), c_double]
MagickSetImageGamma = _lib.MagickSetImageGamma
MagickSetImageGamma.restype = MagickBooleanType
MagickSetImageGamma.argtypes = [POINTER(MagickWand), c_double]
MagickSetImageGravity = _lib.MagickSetImageGravity
MagickSetImageGravity.restype = MagickBooleanType
MagickSetImageGravity.argtypes = [POINTER(MagickWand), GravityType]
MagickSetImageGreenPrimary = _lib.MagickSetImageGreenPrimary
MagickSetImageGreenPrimary.restype = MagickBooleanType
MagickSetImageGreenPrimary.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickSetImageInterlaceScheme = _lib.MagickSetImageInterlaceScheme
MagickSetImageInterlaceScheme.restype = MagickBooleanType
MagickSetImageInterlaceScheme.argtypes = [POINTER(MagickWand), InterlaceType]
MagickSetImageInterpolateMethod = _lib.MagickSetImageInterpolateMethod
MagickSetImageInterpolateMethod.restype = MagickBooleanType
MagickSetImageInterpolateMethod.argtypes = [POINTER(MagickWand), InterpolatePixelMethod]
MagickSetImageIterations = _lib.MagickSetImageIterations
MagickSetImageIterations.restype = MagickBooleanType
MagickSetImageIterations.argtypes = [POINTER(MagickWand), size_t]
MagickSetImageMatte = _lib.MagickSetImageMatte
MagickSetImageMatte.restype = MagickBooleanType
MagickSetImageMatte.argtypes = [POINTER(MagickWand), MagickBooleanType]
MagickSetImageMatteColor = _lib.MagickSetImageMatteColor
MagickSetImageMatteColor.restype = MagickBooleanType
MagickSetImageMatteColor.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickSetImageOpacity = _lib.MagickSetImageOpacity
MagickSetImageOpacity.restype = MagickBooleanType
MagickSetImageOpacity.argtypes = [POINTER(MagickWand), c_double]

# values for enumeration 'OrientationType'
UndefinedOrientation = 0
TopLeftOrientation = 1
TopRightOrientation = 2
BottomRightOrientation = 3
BottomLeftOrientation = 4
LeftTopOrientation = 5
RightTopOrientation = 6
RightBottomOrientation = 7
LeftBottomOrientation = 8
OrientationType = c_int # enum
MagickSetImageOrientation = _lib.MagickSetImageOrientation
MagickSetImageOrientation.restype = MagickBooleanType
MagickSetImageOrientation.argtypes = [POINTER(MagickWand), OrientationType]
MagickSetImagePage = _lib.MagickSetImagePage
MagickSetImagePage.restype = MagickBooleanType
MagickSetImagePage.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t, ssize_t]
MagickSetImageRedPrimary = _lib.MagickSetImageRedPrimary
MagickSetImageRedPrimary.restype = MagickBooleanType
MagickSetImageRedPrimary.argtypes = [POINTER(MagickWand), c_double, c_double]

# values for enumeration 'RenderingIntent'
UndefinedIntent = 0
SaturationIntent = 1
PerceptualIntent = 2
AbsoluteIntent = 3
RelativeIntent = 4
RenderingIntent = c_int # enum
MagickSetImageRenderingIntent = _lib.MagickSetImageRenderingIntent
MagickSetImageRenderingIntent.restype = MagickBooleanType
MagickSetImageRenderingIntent.argtypes = [POINTER(MagickWand), RenderingIntent]
MagickSetImageResolution = _lib.MagickSetImageResolution
MagickSetImageResolution.restype = MagickBooleanType
MagickSetImageResolution.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickSetImageScene = _lib.MagickSetImageScene
MagickSetImageScene.restype = MagickBooleanType
MagickSetImageScene.argtypes = [POINTER(MagickWand), size_t]
MagickSetImageTicksPerSecond = _lib.MagickSetImageTicksPerSecond
MagickSetImageTicksPerSecond.restype = MagickBooleanType
MagickSetImageTicksPerSecond.argtypes = [POINTER(MagickWand), ssize_t]
MagickSetImageType = _lib.MagickSetImageType
MagickSetImageType.restype = MagickBooleanType
MagickSetImageType.argtypes = [POINTER(MagickWand), ImageType]

# values for enumeration 'ResolutionType'
UndefinedResolution = 0
PixelsPerInchResolution = 1
PixelsPerCentimeterResolution = 2
ResolutionType = c_int # enum
MagickSetImageUnits = _lib.MagickSetImageUnits
MagickSetImageUnits.restype = MagickBooleanType
MagickSetImageUnits.argtypes = [POINTER(MagickWand), ResolutionType]
MagickSetImageWhitePoint = _lib.MagickSetImageWhitePoint
MagickSetImageWhitePoint.restype = MagickBooleanType
MagickSetImageWhitePoint.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickShadeImage = _lib.MagickShadeImage
MagickShadeImage.restype = MagickBooleanType
MagickShadeImage.argtypes = [POINTER(MagickWand), MagickBooleanType, c_double, c_double]
MagickShadowImage = _lib.MagickShadowImage
MagickShadowImage.restype = MagickBooleanType
MagickShadowImage.argtypes = [POINTER(MagickWand), c_double, c_double, ssize_t, ssize_t]
MagickSharpenImage = _lib.MagickSharpenImage
MagickSharpenImage.restype = MagickBooleanType
MagickSharpenImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickSharpenImageChannel = _lib.MagickSharpenImageChannel
MagickSharpenImageChannel.restype = MagickBooleanType
MagickSharpenImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double]
MagickShaveImage = _lib.MagickShaveImage
MagickShaveImage.restype = MagickBooleanType
MagickShaveImage.argtypes = [POINTER(MagickWand), size_t, size_t]
MagickShearImage = _lib.MagickShearImage
MagickShearImage.restype = MagickBooleanType
MagickShearImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), c_double, c_double]
MagickSigmoidalContrastImage = _lib.MagickSigmoidalContrastImage
MagickSigmoidalContrastImage.restype = MagickBooleanType
MagickSigmoidalContrastImage.argtypes = [POINTER(MagickWand), MagickBooleanType, c_double, c_double]
MagickSigmoidalContrastImageChannel = _lib.MagickSigmoidalContrastImageChannel
MagickSigmoidalContrastImageChannel.restype = MagickBooleanType
MagickSigmoidalContrastImageChannel.argtypes = [POINTER(MagickWand), ChannelType, MagickBooleanType, c_double, c_double]
MagickSketchImage = _lib.MagickSketchImage
MagickSketchImage.restype = MagickBooleanType
MagickSketchImage.argtypes = [POINTER(MagickWand), c_double, c_double, c_double]
MagickSolarizeImage = _lib.MagickSolarizeImage
MagickSolarizeImage.restype = MagickBooleanType
MagickSolarizeImage.argtypes = [POINTER(MagickWand), c_double]
MagickSparseColorImage = _lib.MagickSparseColorImage
MagickSparseColorImage.restype = MagickBooleanType
MagickSparseColorImage.argtypes = [POINTER(MagickWand), ChannelType, SparseColorMethod, size_t, POINTER(c_double)]
MagickSpliceImage = _lib.MagickSpliceImage
MagickSpliceImage.restype = MagickBooleanType
MagickSpliceImage.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t, ssize_t]
MagickSpreadImage = _lib.MagickSpreadImage
MagickSpreadImage.restype = MagickBooleanType
MagickSpreadImage.argtypes = [POINTER(MagickWand), c_double]
MagickStatisticImage = _lib.MagickStatisticImage
MagickStatisticImage.restype = MagickBooleanType
MagickStatisticImage.argtypes = [POINTER(MagickWand), ChannelType, StatisticType, size_t, size_t]
MagickStripImage = _lib.MagickStripImage
MagickStripImage.restype = MagickBooleanType
MagickStripImage.argtypes = [POINTER(MagickWand)]
MagickSwirlImage = _lib.MagickSwirlImage
MagickSwirlImage.restype = MagickBooleanType
MagickSwirlImage.argtypes = [POINTER(MagickWand), c_double]
MagickTintImage = _lib.MagickTintImage
MagickTintImage.restype = MagickBooleanType
MagickTintImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand), POINTER(PixelWand)]
MagickTransformImageColorspace = _lib.MagickTransformImageColorspace
MagickTransformImageColorspace.restype = MagickBooleanType
MagickTransformImageColorspace.argtypes = [POINTER(MagickWand), ColorspaceType]
MagickTransposeImage = _lib.MagickTransposeImage
MagickTransposeImage.restype = MagickBooleanType
MagickTransposeImage.argtypes = [POINTER(MagickWand)]
MagickTransverseImage = _lib.MagickTransverseImage
MagickTransverseImage.restype = MagickBooleanType
MagickTransverseImage.argtypes = [POINTER(MagickWand)]
MagickThresholdImage = _lib.MagickThresholdImage
MagickThresholdImage.restype = MagickBooleanType
MagickThresholdImage.argtypes = [POINTER(MagickWand), c_double]
MagickThresholdImageChannel = _lib.MagickThresholdImageChannel
MagickThresholdImageChannel.restype = MagickBooleanType
MagickThresholdImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double]
MagickThumbnailImage = _lib.MagickThumbnailImage
MagickThumbnailImage.restype = MagickBooleanType
MagickThumbnailImage.argtypes = [POINTER(MagickWand), size_t, size_t]
MagickTrimImage = _lib.MagickTrimImage
MagickTrimImage.restype = MagickBooleanType
MagickTrimImage.argtypes = [POINTER(MagickWand), c_double]
MagickUniqueImageColors = _lib.MagickUniqueImageColors
MagickUniqueImageColors.restype = MagickBooleanType
MagickUniqueImageColors.argtypes = [POINTER(MagickWand)]
MagickUnsharpMaskImage = _lib.MagickUnsharpMaskImage
MagickUnsharpMaskImage.restype = MagickBooleanType
MagickUnsharpMaskImage.argtypes = [POINTER(MagickWand), c_double, c_double, c_double, c_double]
MagickUnsharpMaskImageChannel = _lib.MagickUnsharpMaskImageChannel
MagickUnsharpMaskImageChannel.restype = MagickBooleanType
MagickUnsharpMaskImageChannel.argtypes = [POINTER(MagickWand), ChannelType, c_double, c_double, c_double, c_double]
MagickVignetteImage = _lib.MagickVignetteImage
MagickVignetteImage.restype = MagickBooleanType
MagickVignetteImage.argtypes = [POINTER(MagickWand), c_double, c_double, ssize_t, ssize_t]
MagickWaveImage = _lib.MagickWaveImage
MagickWaveImage.restype = MagickBooleanType
MagickWaveImage.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickWhiteThresholdImage = _lib.MagickWhiteThresholdImage
MagickWhiteThresholdImage.restype = MagickBooleanType
MagickWhiteThresholdImage.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickWriteImage = _lib.MagickWriteImage
MagickWriteImage.restype = MagickBooleanType
MagickWriteImage.argtypes = [POINTER(MagickWand), STRING]
MagickWriteImageFile = _lib.MagickWriteImageFile
MagickWriteImageFile.restype = MagickBooleanType
MagickWriteImageFile.argtypes = [POINTER(MagickWand), POINTER(FILE)]
MagickWriteImages = _lib.MagickWriteImages
MagickWriteImages.restype = MagickBooleanType
MagickWriteImages.argtypes = [POINTER(MagickWand), STRING, MagickBooleanType]
MagickWriteImagesFile = _lib.MagickWriteImagesFile
MagickWriteImagesFile.restype = MagickBooleanType
MagickWriteImagesFile.argtypes = [POINTER(MagickWand), POINTER(FILE)]
MagickSetImageProgressMonitor = _lib.MagickSetImageProgressMonitor
MagickSetImageProgressMonitor.restype = MagickProgressMonitor
MagickSetImageProgressMonitor.argtypes = [POINTER(MagickWand), MagickProgressMonitor, c_void_p]
MagickAppendImages = _lib.MagickAppendImages
MagickAppendImages.restype = POINTER(MagickWand)
MagickAppendImages.argtypes = [POINTER(MagickWand), MagickBooleanType]
MagickCoalesceImages = _lib.MagickCoalesceImages
MagickCoalesceImages.restype = POINTER(MagickWand)
MagickCoalesceImages.argtypes = [POINTER(MagickWand)]
MagickCombineImages = _lib.MagickCombineImages
MagickCombineImages.restype = POINTER(MagickWand)
MagickCombineImages.argtypes = [POINTER(MagickWand), ChannelType]
MagickCompareImageChannels = _lib.MagickCompareImageChannels
MagickCompareImageChannels.restype = POINTER(MagickWand)
MagickCompareImageChannels.argtypes = [POINTER(MagickWand), POINTER(MagickWand), ChannelType, MetricType, POINTER(c_double)]
MagickCompareImages = _lib.MagickCompareImages
MagickCompareImages.restype = POINTER(MagickWand)
MagickCompareImages.argtypes = [POINTER(MagickWand), POINTER(MagickWand), MetricType, POINTER(c_double)]
MagickCompareImageLayers = _lib.MagickCompareImageLayers
MagickCompareImageLayers.restype = POINTER(MagickWand)
MagickCompareImageLayers.argtypes = [POINTER(MagickWand), ImageLayerMethod]
MagickDeconstructImages = _lib.MagickDeconstructImages
MagickDeconstructImages.restype = POINTER(MagickWand)
MagickDeconstructImages.argtypes = [POINTER(MagickWand)]
MagickEvaluateImages = _lib.MagickEvaluateImages
MagickEvaluateImages.restype = POINTER(MagickWand)
MagickEvaluateImages.argtypes = [POINTER(MagickWand), MagickEvaluateOperator]
MagickFxImage = _lib.MagickFxImage
MagickFxImage.restype = POINTER(MagickWand)
MagickFxImage.argtypes = [POINTER(MagickWand), STRING]
MagickFxImageChannel = _lib.MagickFxImageChannel
MagickFxImageChannel.restype = POINTER(MagickWand)
MagickFxImageChannel.argtypes = [POINTER(MagickWand), ChannelType, STRING]
MagickGetImage = _lib.MagickGetImage
MagickGetImage.restype = POINTER(MagickWand)
MagickGetImage.argtypes = [POINTER(MagickWand)]
MagickGetImageClipMask = _lib.MagickGetImageClipMask
MagickGetImageClipMask.restype = POINTER(MagickWand)
MagickGetImageClipMask.argtypes = [POINTER(MagickWand)]
MagickGetImageRegion = _lib.MagickGetImageRegion
MagickGetImageRegion.restype = POINTER(MagickWand)
MagickGetImageRegion.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t, ssize_t]
MagickMergeImageLayers = _lib.MagickMergeImageLayers
MagickMergeImageLayers.restype = POINTER(MagickWand)
MagickMergeImageLayers.argtypes = [POINTER(MagickWand), ImageLayerMethod]
MagickMorphImages = _lib.MagickMorphImages
MagickMorphImages.restype = POINTER(MagickWand)
MagickMorphImages.argtypes = [POINTER(MagickWand), size_t]

# values for enumeration 'MontageMode'
UndefinedMode = 0
FrameMode = 1
UnframeMode = 2
ConcatenateMode = 3
MontageMode = c_int # enum
MagickMontageImage = _lib.MagickMontageImage
MagickMontageImage.restype = POINTER(MagickWand)
MagickMontageImage.argtypes = [POINTER(MagickWand), POINTER(DrawingWand), STRING, STRING, MontageMode, STRING]
MagickOptimizeImageLayers = _lib.MagickOptimizeImageLayers
MagickOptimizeImageLayers.restype = POINTER(MagickWand)
MagickOptimizeImageLayers.argtypes = [POINTER(MagickWand)]
MagickPreviewImages = _lib.MagickPreviewImages
MagickPreviewImages.restype = POINTER(MagickWand)
MagickPreviewImages.argtypes = [POINTER(MagickWand), PreviewType]
MagickSimilarityImage = _lib.MagickSimilarityImage
MagickSimilarityImage.restype = POINTER(MagickWand)
MagickSimilarityImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand), POINTER(RectangleInfo), POINTER(c_double)]
MagickSmushImages = _lib.MagickSmushImages
MagickSmushImages.restype = POINTER(MagickWand)
MagickSmushImages.argtypes = [POINTER(MagickWand), MagickBooleanType, ssize_t]
MagickSteganoImage = _lib.MagickSteganoImage
MagickSteganoImage.restype = POINTER(MagickWand)
MagickSteganoImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand), ssize_t]
MagickStereoImage = _lib.MagickStereoImage
MagickStereoImage.restype = POINTER(MagickWand)
MagickStereoImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand)]
MagickTextureImage = _lib.MagickTextureImage
MagickTextureImage.restype = POINTER(MagickWand)
MagickTextureImage.argtypes = [POINTER(MagickWand), POINTER(MagickWand)]
MagickTransformImage = _lib.MagickTransformImage
MagickTransformImage.restype = POINTER(MagickWand)
MagickTransformImage.argtypes = [POINTER(MagickWand), STRING, STRING]
MagickGetImageOrientation = _lib.MagickGetImageOrientation
MagickGetImageOrientation.restype = OrientationType
MagickGetImageOrientation.argtypes = [POINTER(MagickWand)]
MagickGetImageHistogram = _lib.MagickGetImageHistogram
MagickGetImageHistogram.restype = POINTER(POINTER(PixelWand))
MagickGetImageHistogram.argtypes = [POINTER(MagickWand), POINTER(size_t)]
MagickGetImageRenderingIntent = _lib.MagickGetImageRenderingIntent
MagickGetImageRenderingIntent.restype = RenderingIntent
MagickGetImageRenderingIntent.argtypes = [POINTER(MagickWand)]
MagickGetImageUnits = _lib.MagickGetImageUnits
MagickGetImageUnits.restype = ResolutionType
MagickGetImageUnits.argtypes = [POINTER(MagickWand)]
MagickGetImageColors = _lib.MagickGetImageColors
MagickGetImageColors.restype = size_t
MagickGetImageColors.argtypes = [POINTER(MagickWand)]
MagickGetImageCompressionQuality = _lib.MagickGetImageCompressionQuality
MagickGetImageCompressionQuality.restype = size_t
MagickGetImageCompressionQuality.argtypes = [POINTER(MagickWand)]
MagickGetImageDelay = _lib.MagickGetImageDelay
MagickGetImageDelay.restype = size_t
MagickGetImageDelay.argtypes = [POINTER(MagickWand)]
MagickGetImageChannelDepth = _lib.MagickGetImageChannelDepth
MagickGetImageChannelDepth.restype = size_t
MagickGetImageChannelDepth.argtypes = [POINTER(MagickWand), ChannelType]
MagickGetImageDepth = _lib.MagickGetImageDepth
MagickGetImageDepth.restype = size_t
MagickGetImageDepth.argtypes = [POINTER(MagickWand)]
MagickGetImageHeight = _lib.MagickGetImageHeight
MagickGetImageHeight.restype = size_t
MagickGetImageHeight.argtypes = [POINTER(MagickWand)]
MagickGetImageIterations = _lib.MagickGetImageIterations
MagickGetImageIterations.restype = size_t
MagickGetImageIterations.argtypes = [POINTER(MagickWand)]
MagickGetImageScene = _lib.MagickGetImageScene
MagickGetImageScene.restype = size_t
MagickGetImageScene.argtypes = [POINTER(MagickWand)]
MagickGetImageTicksPerSecond = _lib.MagickGetImageTicksPerSecond
MagickGetImageTicksPerSecond.restype = size_t
MagickGetImageTicksPerSecond.argtypes = [POINTER(MagickWand)]
MagickGetImageWidth = _lib.MagickGetImageWidth
MagickGetImageWidth.restype = size_t
MagickGetImageWidth.argtypes = [POINTER(MagickWand)]
MagickGetNumberImages = _lib.MagickGetNumberImages
MagickGetNumberImages.restype = size_t
MagickGetNumberImages.argtypes = [POINTER(MagickWand)]
MagickGetImageBlob = _lib.MagickGetImageBlob
MagickGetImageBlob.restype = POINTER(c_ubyte)
MagickGetImageBlob.argtypes = [POINTER(MagickWand), POINTER(size_t)]
MagickGetImagesBlob = _lib.MagickGetImagesBlob
MagickGetImagesBlob.restype = POINTER(c_ubyte)
MagickGetImagesBlob.argtypes = [POINTER(MagickWand), POINTER(size_t)]
MagickGetImageVirtualPixelMethod = _lib.MagickGetImageVirtualPixelMethod
MagickGetImageVirtualPixelMethod.restype = VirtualPixelMethod
MagickGetImageVirtualPixelMethod.argtypes = [POINTER(MagickWand)]
MagickSetImageVirtualPixelMethod = _lib.MagickSetImageVirtualPixelMethod
MagickSetImageVirtualPixelMethod.restype = VirtualPixelMethod
MagickSetImageVirtualPixelMethod.argtypes = [POINTER(MagickWand), VirtualPixelMethod]
MagickGetFilename = _lib.MagickGetFilename
MagickGetFilename.restype = STRING
MagickGetFilename.argtypes = [POINTER(MagickWand)]
MagickGetFormat = _lib.MagickGetFormat
MagickGetFormat.restype = STRING
MagickGetFormat.argtypes = [POINTER(MagickWand)]
MagickGetFont = _lib.MagickGetFont
MagickGetFont.restype = STRING
MagickGetFont.argtypes = [POINTER(MagickWand)]
MagickGetHomeURL = _lib.MagickGetHomeURL
MagickGetHomeURL.restype = STRING
MagickGetHomeURL.argtypes = []
MagickGetImageArtifact = _lib.MagickGetImageArtifact
MagickGetImageArtifact.restype = STRING
MagickGetImageArtifact.argtypes = [POINTER(MagickWand), STRING]
MagickGetImageArtifacts = _lib.MagickGetImageArtifacts
MagickGetImageArtifacts.restype = POINTER(STRING)
MagickGetImageArtifacts.argtypes = [POINTER(MagickWand), STRING, POINTER(size_t)]
MagickGetImageProfiles = _lib.MagickGetImageProfiles
MagickGetImageProfiles.restype = POINTER(STRING)
MagickGetImageProfiles.argtypes = [POINTER(MagickWand), STRING, POINTER(size_t)]
MagickGetImageProperty = _lib.MagickGetImageProperty
MagickGetImageProperty.restype = STRING
MagickGetImageProperty.argtypes = [POINTER(MagickWand), STRING]
MagickGetImageProperties = _lib.MagickGetImageProperties
MagickGetImageProperties.restype = POINTER(STRING)
MagickGetImageProperties.argtypes = [POINTER(MagickWand), STRING, POINTER(size_t)]
MagickGetOption = _lib.MagickGetOption
MagickGetOption.restype = STRING
MagickGetOption.argtypes = [POINTER(MagickWand), STRING]
MagickGetOptions = _lib.MagickGetOptions
MagickGetOptions.restype = POINTER(STRING)
MagickGetOptions.argtypes = [POINTER(MagickWand), STRING, POINTER(size_t)]
MagickQueryConfigureOption = _lib.MagickQueryConfigureOption
MagickQueryConfigureOption.restype = STRING
MagickQueryConfigureOption.argtypes = [STRING]
MagickQueryConfigureOptions = _lib.MagickQueryConfigureOptions
MagickQueryConfigureOptions.restype = POINTER(STRING)
MagickQueryConfigureOptions.argtypes = [STRING, POINTER(size_t)]
MagickQueryFonts = _lib.MagickQueryFonts
MagickQueryFonts.restype = POINTER(STRING)
MagickQueryFonts.argtypes = [STRING, POINTER(size_t)]
MagickQueryFormats = _lib.MagickQueryFormats
MagickQueryFormats.restype = POINTER(STRING)
MagickQueryFormats.argtypes = [STRING, POINTER(size_t)]
MagickGetColorspace = _lib.MagickGetColorspace
MagickGetColorspace.restype = ColorspaceType
MagickGetColorspace.argtypes = [POINTER(MagickWand)]
MagickGetCompression = _lib.MagickGetCompression
MagickGetCompression.restype = CompressionType
MagickGetCompression.argtypes = [POINTER(MagickWand)]
MagickGetCopyright = _lib.MagickGetCopyright
MagickGetCopyright.restype = STRING
MagickGetCopyright.argtypes = []
MagickGetPackageName = _lib.MagickGetPackageName
MagickGetPackageName.restype = STRING
MagickGetPackageName.argtypes = []
MagickGetQuantumDepth = _lib.MagickGetQuantumDepth
MagickGetQuantumDepth.restype = STRING
MagickGetQuantumDepth.argtypes = [POINTER(size_t)]
MagickGetQuantumRange = _lib.MagickGetQuantumRange
MagickGetQuantumRange.restype = STRING
MagickGetQuantumRange.argtypes = [POINTER(size_t)]
MagickGetReleaseDate = _lib.MagickGetReleaseDate
MagickGetReleaseDate.restype = STRING
MagickGetReleaseDate.argtypes = []
MagickGetVersion = _lib.MagickGetVersion
MagickGetVersion.restype = STRING
MagickGetVersion.argtypes = [POINTER(size_t)]
MagickGetPointsize = _lib.MagickGetPointsize
MagickGetPointsize.restype = c_double
MagickGetPointsize.argtypes = [POINTER(MagickWand)]
MagickGetSamplingFactors = _lib.MagickGetSamplingFactors
MagickGetSamplingFactors.restype = POINTER(c_double)
MagickGetSamplingFactors.argtypes = [POINTER(MagickWand), POINTER(size_t)]
MagickQueryFontMetrics = _lib.MagickQueryFontMetrics
MagickQueryFontMetrics.restype = POINTER(c_double)
MagickQueryFontMetrics.argtypes = [POINTER(MagickWand), POINTER(DrawingWand), STRING]
MagickQueryMultilineFontMetrics = _lib.MagickQueryMultilineFontMetrics
MagickQueryMultilineFontMetrics.restype = POINTER(c_double)
MagickQueryMultilineFontMetrics.argtypes = [POINTER(MagickWand), POINTER(DrawingWand), STRING]
MagickGetGravity = _lib.MagickGetGravity
MagickGetGravity.restype = GravityType
MagickGetGravity.argtypes = [POINTER(MagickWand)]
MagickGetType = _lib.MagickGetType
MagickGetType.restype = ImageType
MagickGetType.argtypes = [POINTER(MagickWand)]
MagickGetInterlaceScheme = _lib.MagickGetInterlaceScheme
MagickGetInterlaceScheme.restype = InterlaceType
MagickGetInterlaceScheme.argtypes = [POINTER(MagickWand)]
MagickGetInterpolateMethod = _lib.MagickGetInterpolateMethod
MagickGetInterpolateMethod.restype = InterpolatePixelMethod
MagickGetInterpolateMethod.argtypes = [POINTER(MagickWand)]
MagickGetOrientation = _lib.MagickGetOrientation
MagickGetOrientation.restype = OrientationType
MagickGetOrientation.argtypes = [POINTER(MagickWand)]
MagickDeleteImageArtifact = _lib.MagickDeleteImageArtifact
MagickDeleteImageArtifact.restype = MagickBooleanType
MagickDeleteImageArtifact.argtypes = [POINTER(MagickWand), STRING]
MagickDeleteImageProperty = _lib.MagickDeleteImageProperty
MagickDeleteImageProperty.restype = MagickBooleanType
MagickDeleteImageProperty.argtypes = [POINTER(MagickWand), STRING]
MagickDeleteOption = _lib.MagickDeleteOption
MagickDeleteOption.restype = MagickBooleanType
MagickDeleteOption.argtypes = [POINTER(MagickWand), STRING]
MagickGetAntialias = _lib.MagickGetAntialias
MagickGetAntialias.restype = MagickBooleanType
MagickGetAntialias.argtypes = [POINTER(MagickWand)]
MagickGetPage = _lib.MagickGetPage
MagickGetPage.restype = MagickBooleanType
MagickGetPage.argtypes = [POINTER(MagickWand), POINTER(size_t), POINTER(size_t), POINTER(ssize_t), POINTER(ssize_t)]
MagickGetResolution = _lib.MagickGetResolution
MagickGetResolution.restype = MagickBooleanType
MagickGetResolution.argtypes = [POINTER(MagickWand), POINTER(c_double), POINTER(c_double)]
MagickGetSize = _lib.MagickGetSize
MagickGetSize.restype = MagickBooleanType
MagickGetSize.argtypes = [POINTER(MagickWand), POINTER(size_t), POINTER(size_t)]
MagickGetSizeOffset = _lib.MagickGetSizeOffset
MagickGetSizeOffset.restype = MagickBooleanType
MagickGetSizeOffset.argtypes = [POINTER(MagickWand), POINTER(ssize_t)]
MagickProfileImage = _lib.MagickProfileImage
MagickProfileImage.restype = MagickBooleanType
MagickProfileImage.argtypes = [POINTER(MagickWand), STRING, c_void_p, size_t]
MagickSetAntialias = _lib.MagickSetAntialias
MagickSetAntialias.restype = MagickBooleanType
MagickSetAntialias.argtypes = [POINTER(MagickWand), MagickBooleanType]
MagickSetBackgroundColor = _lib.MagickSetBackgroundColor
MagickSetBackgroundColor.restype = MagickBooleanType
MagickSetBackgroundColor.argtypes = [POINTER(MagickWand), POINTER(PixelWand)]
MagickSetColorspace = _lib.MagickSetColorspace
MagickSetColorspace.restype = MagickBooleanType
MagickSetColorspace.argtypes = [POINTER(MagickWand), ColorspaceType]
MagickSetCompression = _lib.MagickSetCompression
MagickSetCompression.restype = MagickBooleanType
MagickSetCompression.argtypes = [POINTER(MagickWand), CompressionType]
MagickSetCompressionQuality = _lib.MagickSetCompressionQuality
MagickSetCompressionQuality.restype = MagickBooleanType
MagickSetCompressionQuality.argtypes = [POINTER(MagickWand), size_t]
MagickSetDepth = _lib.MagickSetDepth
MagickSetDepth.restype = MagickBooleanType
MagickSetDepth.argtypes = [POINTER(MagickWand), size_t]
MagickSetExtract = _lib.MagickSetExtract
MagickSetExtract.restype = MagickBooleanType
MagickSetExtract.argtypes = [POINTER(MagickWand), STRING]
MagickSetFilename = _lib.MagickSetFilename
MagickSetFilename.restype = MagickBooleanType
MagickSetFilename.argtypes = [POINTER(MagickWand), STRING]
MagickSetFormat = _lib.MagickSetFormat
MagickSetFormat.restype = MagickBooleanType
MagickSetFormat.argtypes = [POINTER(MagickWand), STRING]
MagickSetFont = _lib.MagickSetFont
MagickSetFont.restype = MagickBooleanType
MagickSetFont.argtypes = [POINTER(MagickWand), STRING]
MagickSetGravity = _lib.MagickSetGravity
MagickSetGravity.restype = MagickBooleanType
MagickSetGravity.argtypes = [POINTER(MagickWand), GravityType]
MagickSetImageArtifact = _lib.MagickSetImageArtifact
MagickSetImageArtifact.restype = MagickBooleanType
MagickSetImageArtifact.argtypes = [POINTER(MagickWand), STRING, STRING]
MagickSetImageProfile = _lib.MagickSetImageProfile
MagickSetImageProfile.restype = MagickBooleanType
MagickSetImageProfile.argtypes = [POINTER(MagickWand), STRING, c_void_p, size_t]
MagickSetImageProperty = _lib.MagickSetImageProperty
MagickSetImageProperty.restype = MagickBooleanType
MagickSetImageProperty.argtypes = [POINTER(MagickWand), STRING, STRING]
MagickSetInterlaceScheme = _lib.MagickSetInterlaceScheme
MagickSetInterlaceScheme.restype = MagickBooleanType
MagickSetInterlaceScheme.argtypes = [POINTER(MagickWand), InterlaceType]
MagickSetInterpolateMethod = _lib.MagickSetInterpolateMethod
MagickSetInterpolateMethod.restype = MagickBooleanType
MagickSetInterpolateMethod.argtypes = [POINTER(MagickWand), InterpolatePixelMethod]
MagickSetOption = _lib.MagickSetOption
MagickSetOption.restype = MagickBooleanType
MagickSetOption.argtypes = [POINTER(MagickWand), STRING, STRING]
MagickSetOrientation = _lib.MagickSetOrientation
MagickSetOrientation.restype = MagickBooleanType
MagickSetOrientation.argtypes = [POINTER(MagickWand), OrientationType]
MagickSetPage = _lib.MagickSetPage
MagickSetPage.restype = MagickBooleanType
MagickSetPage.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t, ssize_t]
MagickSetPassphrase = _lib.MagickSetPassphrase
MagickSetPassphrase.restype = MagickBooleanType
MagickSetPassphrase.argtypes = [POINTER(MagickWand), STRING]
MagickSetPointsize = _lib.MagickSetPointsize
MagickSetPointsize.restype = MagickBooleanType
MagickSetPointsize.argtypes = [POINTER(MagickWand), c_double]
MagickSetResolution = _lib.MagickSetResolution
MagickSetResolution.restype = MagickBooleanType
MagickSetResolution.argtypes = [POINTER(MagickWand), c_double, c_double]
MagickSetResourceLimit = _lib.MagickSetResourceLimit
MagickSetResourceLimit.restype = MagickBooleanType
MagickSetResourceLimit.argtypes = [ResourceType, MagickSizeType]
MagickSetSamplingFactors = _lib.MagickSetSamplingFactors
MagickSetSamplingFactors.restype = MagickBooleanType
MagickSetSamplingFactors.argtypes = [POINTER(MagickWand), size_t, POINTER(c_double)]
MagickSetSize = _lib.MagickSetSize
MagickSetSize.restype = MagickBooleanType
MagickSetSize.argtypes = [POINTER(MagickWand), size_t, size_t]
MagickSetSizeOffset = _lib.MagickSetSizeOffset
MagickSetSizeOffset.restype = MagickBooleanType
MagickSetSizeOffset.argtypes = [POINTER(MagickWand), size_t, size_t, ssize_t]
MagickSetType = _lib.MagickSetType
MagickSetType.restype = MagickBooleanType
MagickSetType.argtypes = [POINTER(MagickWand), ImageType]
MagickSetProgressMonitor = _lib.MagickSetProgressMonitor
MagickSetProgressMonitor.restype = MagickProgressMonitor
MagickSetProgressMonitor.argtypes = [POINTER(MagickWand), MagickProgressMonitor, c_void_p]
MagickGetResource = _lib.MagickGetResource
MagickGetResource.restype = MagickSizeType
MagickGetResource.argtypes = [ResourceType]
MagickGetResourceLimit = _lib.MagickGetResourceLimit
MagickGetResourceLimit.restype = MagickSizeType
MagickGetResourceLimit.argtypes = [ResourceType]
MagickGetBackgroundColor = _lib.MagickGetBackgroundColor
MagickGetBackgroundColor.restype = POINTER(PixelWand)
MagickGetBackgroundColor.argtypes = [POINTER(MagickWand)]
MagickGetCompressionQuality = _lib.MagickGetCompressionQuality
MagickGetCompressionQuality.restype = size_t
MagickGetCompressionQuality.argtypes = [POINTER(MagickWand)]
MagickGetImageProfile = _lib.MagickGetImageProfile
MagickGetImageProfile.restype = POINTER(c_ubyte)
MagickGetImageProfile.argtypes = [POINTER(MagickWand), STRING, POINTER(size_t)]
MagickRemoveImageProfile = _lib.MagickRemoveImageProfile
MagickRemoveImageProfile.restype = POINTER(c_ubyte)
MagickRemoveImageProfile.argtypes = [POINTER(MagickWand), STRING, POINTER(size_t)]
MagickCommand = CFUNCTYPE(MagickBooleanType, POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo))
MagickCommandGenesis = _lib.MagickCommandGenesis
MagickCommandGenesis.restype = MagickBooleanType
MagickCommandGenesis.argtypes = [POINTER(ImageInfo), MagickCommand, c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
MogrifyImage = _lib.MogrifyImage
MogrifyImage.restype = MagickBooleanType
MogrifyImage.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(POINTER(Image)), POINTER(ExceptionInfo)]
MogrifyImageCommand = _lib.MogrifyImageCommand
MogrifyImageCommand.restype = MagickBooleanType
MogrifyImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
MogrifyImageInfo = _lib.MogrifyImageInfo
MogrifyImageInfo.restype = MagickBooleanType
MogrifyImageInfo.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(ExceptionInfo)]
MogrifyImageList = _lib.MogrifyImageList
MogrifyImageList.restype = MagickBooleanType
MogrifyImageList.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(POINTER(Image)), POINTER(ExceptionInfo)]
MogrifyImages = _lib.MogrifyImages
MogrifyImages.restype = MagickBooleanType
MogrifyImages.argtypes = [POINTER(ImageInfo), MagickBooleanType, c_int, POINTER(STRING), POINTER(POINTER(Image)), POINTER(ExceptionInfo)]
MontageImageCommand = _lib.MontageImageCommand
MontageImageCommand.restype = MagickBooleanType
MontageImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
PixelGetIteratorException = _lib.PixelGetIteratorException
PixelGetIteratorException.restype = STRING
PixelGetIteratorException.argtypes = [POINTER(PixelIterator), POINTER(ExceptionType)]
PixelGetIteratorExceptionType = _lib.PixelGetIteratorExceptionType
PixelGetIteratorExceptionType.restype = ExceptionType
PixelGetIteratorExceptionType.argtypes = [POINTER(PixelIterator)]
IsPixelIterator = _lib.IsPixelIterator
IsPixelIterator.restype = MagickBooleanType
IsPixelIterator.argtypes = [POINTER(PixelIterator)]
PixelClearIteratorException = _lib.PixelClearIteratorException
PixelClearIteratorException.restype = MagickBooleanType
PixelClearIteratorException.argtypes = [POINTER(PixelIterator)]
PixelSetIteratorRow = _lib.PixelSetIteratorRow
PixelSetIteratorRow.restype = MagickBooleanType
PixelSetIteratorRow.argtypes = [POINTER(PixelIterator), ssize_t]
PixelSyncIterator = _lib.PixelSyncIterator
PixelSyncIterator.restype = MagickBooleanType
PixelSyncIterator.argtypes = [POINTER(PixelIterator)]
ClonePixelIterator = _lib.ClonePixelIterator
ClonePixelIterator.restype = POINTER(PixelIterator)
ClonePixelIterator.argtypes = [POINTER(PixelIterator)]
DestroyPixelIterator = _lib.DestroyPixelIterator
DestroyPixelIterator.restype = POINTER(PixelIterator)
DestroyPixelIterator.argtypes = [POINTER(PixelIterator)]
NewPixelIterator = _lib.NewPixelIterator
NewPixelIterator.restype = POINTER(PixelIterator)
NewPixelIterator.argtypes = [POINTER(MagickWand)]
NewPixelRegionIterator = _lib.NewPixelRegionIterator
NewPixelRegionIterator.restype = POINTER(PixelIterator)
NewPixelRegionIterator.argtypes = [POINTER(MagickWand), ssize_t, ssize_t, size_t, size_t]
PixelGetCurrentIteratorRow = _lib.PixelGetCurrentIteratorRow
PixelGetCurrentIteratorRow.restype = POINTER(POINTER(PixelWand))
PixelGetCurrentIteratorRow.argtypes = [POINTER(PixelIterator), POINTER(size_t)]
PixelGetNextIteratorRow = _lib.PixelGetNextIteratorRow
PixelGetNextIteratorRow.restype = POINTER(POINTER(PixelWand))
PixelGetNextIteratorRow.argtypes = [POINTER(PixelIterator), POINTER(size_t)]
PixelGetPreviousIteratorRow = _lib.PixelGetPreviousIteratorRow
PixelGetPreviousIteratorRow.restype = POINTER(POINTER(PixelWand))
PixelGetPreviousIteratorRow.argtypes = [POINTER(PixelIterator), POINTER(size_t)]
PixelGetIteratorRow = _lib.PixelGetIteratorRow
PixelGetIteratorRow.restype = ssize_t
PixelGetIteratorRow.argtypes = [POINTER(PixelIterator)]
ClearPixelIterator = _lib.ClearPixelIterator
ClearPixelIterator.restype = None
ClearPixelIterator.argtypes = [POINTER(PixelIterator)]
PixelResetIterator = _lib.PixelResetIterator
PixelResetIterator.restype = None
PixelResetIterator.argtypes = [POINTER(PixelIterator)]
PixelSetFirstIteratorRow = _lib.PixelSetFirstIteratorRow
PixelSetFirstIteratorRow.restype = None
PixelSetFirstIteratorRow.argtypes = [POINTER(PixelIterator)]
PixelSetLastIteratorRow = _lib.PixelSetLastIteratorRow
PixelSetLastIteratorRow.restype = None
PixelSetLastIteratorRow.argtypes = [POINTER(PixelIterator)]
PixelGetColorAsNormalizedString = _lib.PixelGetColorAsNormalizedString
PixelGetColorAsNormalizedString.restype = STRING
PixelGetColorAsNormalizedString.argtypes = [POINTER(PixelWand)]
PixelGetColorAsString = _lib.PixelGetColorAsString
PixelGetColorAsString.restype = STRING
PixelGetColorAsString.argtypes = [POINTER(PixelWand)]
PixelGetException = _lib.PixelGetException
PixelGetException.restype = STRING
PixelGetException.argtypes = [POINTER(PixelWand), POINTER(ExceptionType)]
PixelGetAlpha = _lib.PixelGetAlpha
PixelGetAlpha.restype = c_double
PixelGetAlpha.argtypes = [POINTER(PixelWand)]
PixelGetBlack = _lib.PixelGetBlack
PixelGetBlack.restype = c_double
PixelGetBlack.argtypes = [POINTER(PixelWand)]
PixelGetBlue = _lib.PixelGetBlue
PixelGetBlue.restype = c_double
PixelGetBlue.argtypes = [POINTER(PixelWand)]
PixelGetCyan = _lib.PixelGetCyan
PixelGetCyan.restype = c_double
PixelGetCyan.argtypes = [POINTER(PixelWand)]
PixelGetFuzz = _lib.PixelGetFuzz
PixelGetFuzz.restype = c_double
PixelGetFuzz.argtypes = [POINTER(PixelWand)]
PixelGetGreen = _lib.PixelGetGreen
PixelGetGreen.restype = c_double
PixelGetGreen.argtypes = [POINTER(PixelWand)]
PixelGetMagenta = _lib.PixelGetMagenta
PixelGetMagenta.restype = c_double
PixelGetMagenta.argtypes = [POINTER(PixelWand)]
PixelGetOpacity = _lib.PixelGetOpacity
PixelGetOpacity.restype = c_double
PixelGetOpacity.argtypes = [POINTER(PixelWand)]
PixelGetRed = _lib.PixelGetRed
PixelGetRed.restype = c_double
PixelGetRed.argtypes = [POINTER(PixelWand)]
PixelGetYellow = _lib.PixelGetYellow
PixelGetYellow.restype = c_double
PixelGetYellow.argtypes = [POINTER(PixelWand)]
PixelGetExceptionType = _lib.PixelGetExceptionType
PixelGetExceptionType.restype = ExceptionType
PixelGetExceptionType.argtypes = [POINTER(PixelWand)]
PixelGetIndex = _lib.PixelGetIndex
PixelGetIndex.restype = IndexPacket
PixelGetIndex.argtypes = [POINTER(PixelWand)]
IsPixelWand = _lib.IsPixelWand
IsPixelWand.restype = MagickBooleanType
IsPixelWand.argtypes = [POINTER(PixelWand)]
IsPixelWandSimilar = _lib.IsPixelWandSimilar
IsPixelWandSimilar.restype = MagickBooleanType
IsPixelWandSimilar.argtypes = [POINTER(PixelWand), POINTER(PixelWand), c_double]
PixelClearException = _lib.PixelClearException
PixelClearException.restype = MagickBooleanType
PixelClearException.argtypes = [POINTER(PixelWand)]
PixelSetColor = _lib.PixelSetColor
PixelSetColor.restype = MagickBooleanType
PixelSetColor.argtypes = [POINTER(PixelWand), STRING]
ClonePixelWand = _lib.ClonePixelWand
ClonePixelWand.restype = POINTER(PixelWand)
ClonePixelWand.argtypes = [POINTER(PixelWand)]
ClonePixelWands = _lib.ClonePixelWands
ClonePixelWands.restype = POINTER(POINTER(PixelWand))
ClonePixelWands.argtypes = [POINTER(POINTER(PixelWand)), size_t]
DestroyPixelWand = _lib.DestroyPixelWand
DestroyPixelWand.restype = POINTER(PixelWand)
DestroyPixelWand.argtypes = [POINTER(PixelWand)]
DestroyPixelWands = _lib.DestroyPixelWands
DestroyPixelWands.restype = POINTER(POINTER(PixelWand))
DestroyPixelWands.argtypes = [POINTER(POINTER(PixelWand)), size_t]
NewPixelWand = _lib.NewPixelWand
NewPixelWand.restype = POINTER(PixelWand)
NewPixelWand.argtypes = []
NewPixelWands = _lib.NewPixelWands
NewPixelWands.restype = POINTER(POINTER(PixelWand))
NewPixelWands.argtypes = [size_t]
PixelGetAlphaQuantum = _lib.PixelGetAlphaQuantum
PixelGetAlphaQuantum.restype = Quantum
PixelGetAlphaQuantum.argtypes = [POINTER(PixelWand)]
PixelGetBlackQuantum = _lib.PixelGetBlackQuantum
PixelGetBlackQuantum.restype = Quantum
PixelGetBlackQuantum.argtypes = [POINTER(PixelWand)]
PixelGetBlueQuantum = _lib.PixelGetBlueQuantum
PixelGetBlueQuantum.restype = Quantum
PixelGetBlueQuantum.argtypes = [POINTER(PixelWand)]
PixelGetCyanQuantum = _lib.PixelGetCyanQuantum
PixelGetCyanQuantum.restype = Quantum
PixelGetCyanQuantum.argtypes = [POINTER(PixelWand)]
PixelGetGreenQuantum = _lib.PixelGetGreenQuantum
PixelGetGreenQuantum.restype = Quantum
PixelGetGreenQuantum.argtypes = [POINTER(PixelWand)]
PixelGetMagentaQuantum = _lib.PixelGetMagentaQuantum
PixelGetMagentaQuantum.restype = Quantum
PixelGetMagentaQuantum.argtypes = [POINTER(PixelWand)]
PixelGetOpacityQuantum = _lib.PixelGetOpacityQuantum
PixelGetOpacityQuantum.restype = Quantum
PixelGetOpacityQuantum.argtypes = [POINTER(PixelWand)]
PixelGetRedQuantum = _lib.PixelGetRedQuantum
PixelGetRedQuantum.restype = Quantum
PixelGetRedQuantum.argtypes = [POINTER(PixelWand)]
PixelGetYellowQuantum = _lib.PixelGetYellowQuantum
PixelGetYellowQuantum.restype = Quantum
PixelGetYellowQuantum.argtypes = [POINTER(PixelWand)]
PixelGetColorCount = _lib.PixelGetColorCount
PixelGetColorCount.restype = size_t
PixelGetColorCount.argtypes = [POINTER(PixelWand)]
ClearPixelWand = _lib.ClearPixelWand
ClearPixelWand.restype = None
ClearPixelWand.argtypes = [POINTER(PixelWand)]
PixelGetHSL = _lib.PixelGetHSL
PixelGetHSL.restype = None
PixelGetHSL.argtypes = [POINTER(PixelWand), POINTER(c_double), POINTER(c_double), POINTER(c_double)]
PixelGetMagickColor = _lib.PixelGetMagickColor
PixelGetMagickColor.restype = None
PixelGetMagickColor.argtypes = [POINTER(PixelWand), POINTER(MagickPixelPacket)]
PixelGetQuantumColor = _lib.PixelGetQuantumColor
PixelGetQuantumColor.restype = None
PixelGetQuantumColor.argtypes = [POINTER(PixelWand), POINTER(PixelPacket)]
PixelSetAlpha = _lib.PixelSetAlpha
PixelSetAlpha.restype = None
PixelSetAlpha.argtypes = [POINTER(PixelWand), c_double]
PixelSetAlphaQuantum = _lib.PixelSetAlphaQuantum
PixelSetAlphaQuantum.restype = None
PixelSetAlphaQuantum.argtypes = [POINTER(PixelWand), Quantum]
PixelSetBlack = _lib.PixelSetBlack
PixelSetBlack.restype = None
PixelSetBlack.argtypes = [POINTER(PixelWand), c_double]
PixelSetBlackQuantum = _lib.PixelSetBlackQuantum
PixelSetBlackQuantum.restype = None
PixelSetBlackQuantum.argtypes = [POINTER(PixelWand), Quantum]
PixelSetBlue = _lib.PixelSetBlue
PixelSetBlue.restype = None
PixelSetBlue.argtypes = [POINTER(PixelWand), c_double]
PixelSetBlueQuantum = _lib.PixelSetBlueQuantum
PixelSetBlueQuantum.restype = None
PixelSetBlueQuantum.argtypes = [POINTER(PixelWand), Quantum]
PixelSetColorFromWand = _lib.PixelSetColorFromWand
PixelSetColorFromWand.restype = None
PixelSetColorFromWand.argtypes = [POINTER(PixelWand), POINTER(PixelWand)]
PixelSetColorCount = _lib.PixelSetColorCount
PixelSetColorCount.restype = None
PixelSetColorCount.argtypes = [POINTER(PixelWand), size_t]
PixelSetCyan = _lib.PixelSetCyan
PixelSetCyan.restype = None
PixelSetCyan.argtypes = [POINTER(PixelWand), c_double]
PixelSetCyanQuantum = _lib.PixelSetCyanQuantum
PixelSetCyanQuantum.restype = None
PixelSetCyanQuantum.argtypes = [POINTER(PixelWand), Quantum]
PixelSetFuzz = _lib.PixelSetFuzz
PixelSetFuzz.restype = None
PixelSetFuzz.argtypes = [POINTER(PixelWand), c_double]
PixelSetGreen = _lib.PixelSetGreen
PixelSetGreen.restype = None
PixelSetGreen.argtypes = [POINTER(PixelWand), c_double]
PixelSetGreenQuantum = _lib.PixelSetGreenQuantum
PixelSetGreenQuantum.restype = None
PixelSetGreenQuantum.argtypes = [POINTER(PixelWand), Quantum]
PixelSetHSL = _lib.PixelSetHSL
PixelSetHSL.restype = None
PixelSetHSL.argtypes = [POINTER(PixelWand), c_double, c_double, c_double]
PixelSetIndex = _lib.PixelSetIndex
PixelSetIndex.restype = None
PixelSetIndex.argtypes = [POINTER(PixelWand), IndexPacket]
PixelSetMagenta = _lib.PixelSetMagenta
PixelSetMagenta.restype = None
PixelSetMagenta.argtypes = [POINTER(PixelWand), c_double]
PixelSetMagentaQuantum = _lib.PixelSetMagentaQuantum
PixelSetMagentaQuantum.restype = None
PixelSetMagentaQuantum.argtypes = [POINTER(PixelWand), Quantum]
PixelSetMagickColor = _lib.PixelSetMagickColor
PixelSetMagickColor.restype = None
PixelSetMagickColor.argtypes = [POINTER(PixelWand), POINTER(MagickPixelPacket)]
PixelSetOpacity = _lib.PixelSetOpacity
PixelSetOpacity.restype = None
PixelSetOpacity.argtypes = [POINTER(PixelWand), c_double]
PixelSetOpacityQuantum = _lib.PixelSetOpacityQuantum
PixelSetOpacityQuantum.restype = None
PixelSetOpacityQuantum.argtypes = [POINTER(PixelWand), Quantum]
PixelSetQuantumColor = _lib.PixelSetQuantumColor
PixelSetQuantumColor.restype = None
PixelSetQuantumColor.argtypes = [POINTER(PixelWand), POINTER(PixelPacket)]
PixelSetRed = _lib.PixelSetRed
PixelSetRed.restype = None
PixelSetRed.argtypes = [POINTER(PixelWand), c_double]
PixelSetRedQuantum = _lib.PixelSetRedQuantum
PixelSetRedQuantum.restype = None
PixelSetRedQuantum.argtypes = [POINTER(PixelWand), Quantum]
PixelSetYellow = _lib.PixelSetYellow
PixelSetYellow.restype = None
PixelSetYellow.argtypes = [POINTER(PixelWand), c_double]
PixelSetYellowQuantum = _lib.PixelSetYellowQuantum
PixelSetYellowQuantum.restype = None
PixelSetYellowQuantum.argtypes = [POINTER(PixelWand), Quantum]
StreamImageCommand = _lib.StreamImageCommand
StreamImageCommand.restype = MagickBooleanType
StreamImageCommand.argtypes = [POINTER(ImageInfo), c_int, POINTER(STRING), POINTER(STRING), POINTER(ExceptionInfo)]
class _WandView(Structure):
    pass
WandView = _WandView
GetWandViewException = _lib.GetWandViewException
GetWandViewException.restype = STRING
GetWandViewException.argtypes = [POINTER(WandView), POINTER(ExceptionType)]
DuplexTransferWandViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(WandView), POINTER(WandView), POINTER(WandView), ssize_t, c_int, c_void_p)
DuplexTransferWandViewIterator = _lib.DuplexTransferWandViewIterator
DuplexTransferWandViewIterator.restype = MagickBooleanType
DuplexTransferWandViewIterator.argtypes = [POINTER(WandView), POINTER(WandView), POINTER(WandView), DuplexTransferWandViewMethod, c_void_p]
GetWandViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(WandView), ssize_t, c_int, c_void_p)
GetWandViewIterator = _lib.GetWandViewIterator
GetWandViewIterator.restype = MagickBooleanType
GetWandViewIterator.argtypes = [POINTER(WandView), GetWandViewMethod, c_void_p]
IsWandView = _lib.IsWandView
IsWandView.restype = MagickBooleanType
IsWandView.argtypes = [POINTER(WandView)]
SetWandViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(WandView), ssize_t, c_int, c_void_p)
SetWandViewIterator = _lib.SetWandViewIterator
SetWandViewIterator.restype = MagickBooleanType
SetWandViewIterator.argtypes = [POINTER(WandView), SetWandViewMethod, c_void_p]
TransferWandViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(WandView), POINTER(WandView), ssize_t, c_int, c_void_p)
TransferWandViewIterator = _lib.TransferWandViewIterator
TransferWandViewIterator.restype = MagickBooleanType
TransferWandViewIterator.argtypes = [POINTER(WandView), POINTER(WandView), TransferWandViewMethod, c_void_p]
UpdateWandViewMethod = CFUNCTYPE(MagickBooleanType, POINTER(WandView), ssize_t, c_int, c_void_p)
UpdateWandViewIterator = _lib.UpdateWandViewIterator
UpdateWandViewIterator.restype = MagickBooleanType
UpdateWandViewIterator.argtypes = [POINTER(WandView), UpdateWandViewMethod, c_void_p]
GetWandViewWand = _lib.GetWandViewWand
GetWandViewWand.restype = POINTER(MagickWand)
GetWandViewWand.argtypes = [POINTER(WandView)]
GetWandViewPixels = _lib.GetWandViewPixels
GetWandViewPixels.restype = POINTER(POINTER(PixelWand))
GetWandViewPixels.argtypes = [POINTER(WandView)]
GetWandViewExtent = _lib.GetWandViewExtent
GetWandViewExtent.restype = RectangleInfo
GetWandViewExtent.argtypes = [POINTER(WandView)]
SetWandViewDescription = _lib.SetWandViewDescription
SetWandViewDescription.restype = None
SetWandViewDescription.argtypes = [POINTER(WandView), STRING]
SetWandViewThreads = _lib.SetWandViewThreads
SetWandViewThreads.restype = None
SetWandViewThreads.argtypes = [POINTER(WandView), size_t]
CloneWandView = _lib.CloneWandView
CloneWandView.restype = POINTER(WandView)
CloneWandView.argtypes = [POINTER(WandView)]
DestroyWandView = _lib.DestroyWandView
DestroyWandView.restype = POINTER(WandView)
DestroyWandView.argtypes = [POINTER(WandView)]
NewWandView = _lib.NewWandView
NewWandView.restype = POINTER(WandView)
NewWandView.argtypes = [POINTER(MagickWand)]
NewWandViewExtent = _lib.NewWandViewExtent
NewWandViewExtent.restype = POINTER(WandView)
NewWandViewExtent.argtypes = [POINTER(MagickWand), ssize_t, ssize_t, size_t, size_t]
_CoderInfo._fields_ = [
    ('path', STRING),
    ('magick', STRING),
    ('name', STRING),
    ('exempt', MagickBooleanType),
    ('stealth', MagickBooleanType),
    ('previous', POINTER(_CoderInfo)),
    ('next', POINTER(_CoderInfo)),
    ('signature', size_t),
]
_MagickPixelPacket._fields_ = [
    ('storage_class', ClassType),
    ('colorspace', ColorspaceType),
    ('matte', MagickBooleanType),
    ('fuzz', c_double),
    ('depth', size_t),
    ('red', MagickRealType),
    ('green', MagickRealType),
    ('blue', MagickRealType),
    ('opacity', MagickRealType),
    ('index', MagickRealType),
]
_ColorInfo._fields_ = [
    ('path', STRING),
    ('name', STRING),
    ('compliance', ComplianceType),
    ('color', MagickPixelPacket),
    ('exempt', MagickBooleanType),
    ('stealth', MagickBooleanType),
    ('previous', POINTER(_ColorInfo)),
    ('next', POINTER(_ColorInfo)),
    ('signature', size_t),
]
_ConfigureInfo._fields_ = [
    ('path', STRING),
    ('name', STRING),
    ('value', STRING),
    ('exempt', MagickBooleanType),
    ('stealth', MagickBooleanType),
    ('previous', POINTER(_ConfigureInfo)),
    ('next', POINTER(_ConfigureInfo)),
    ('signature', size_t),
]
_FrameInfo._fields_ = [
    ('width', size_t),
    ('height', size_t),
    ('x', ssize_t),
    ('y', ssize_t),
    ('inner_bevel', ssize_t),
    ('outer_bevel', ssize_t),
]
_DelegateInfo._fields_ = [
    ('path', STRING),
    ('decode', STRING),
    ('encode', STRING),
    ('commands', STRING),
    ('mode', ssize_t),
    ('thread_support', MagickBooleanType),
    ('spawn', MagickBooleanType),
    ('stealth', MagickBooleanType),
    ('previous', POINTER(_DelegateInfo)),
    ('next', POINTER(_DelegateInfo)),
    ('signature', size_t),
]
_ImageAttribute._fields_ = [
    ('key', STRING),
    ('value', STRING),
    ('compression', MagickBooleanType),
    ('previous', POINTER(_ImageAttribute)),
    ('next', POINTER(_ImageAttribute)),
]
_PointInfo._fields_ = [
    ('x', c_double),
    ('y', c_double),
]
_RectangleInfo._fields_ = [
    ('width', size_t),
    ('height', size_t),
    ('x', ssize_t),
    ('y', ssize_t),
]
_AffineMatrix._fields_ = [
    ('sx', c_double),
    ('rx', c_double),
    ('ry', c_double),
    ('sy', c_double),
    ('tx', c_double),
    ('ty', c_double),
]
_PixelPacket._fields_ = [
    ('blue', Quantum),
    ('green', Quantum),
    ('red', Quantum),
    ('opacity', Quantum),
]
class _GradientInfo(Structure):
    pass
_SegmentInfo._fields_ = [
    ('x1', c_double),
    ('y1', c_double),
    ('x2', c_double),
    ('y2', c_double),
]
class _StopInfo(Structure):
    pass
StopInfo = _StopInfo
_GradientInfo._fields_ = [
    ('type', GradientType),
    ('bounding_box', RectangleInfo),
    ('gradient_vector', SegmentInfo),
    ('stops', POINTER(StopInfo)),
    ('number_stops', size_t),
    ('spread', SpreadMethod),
    ('debug', MagickBooleanType),
    ('signature', size_t),
    ('center', PointInfo),
    ('radius', MagickRealType),
]
GradientInfo = _GradientInfo
class _ElementReference(Structure):
    pass

# values for enumeration 'ReferenceType'
UndefinedReference = 0
GradientReference = 1
ReferenceType = c_int # enum
_ElementReference._fields_ = [
    ('id', STRING),
    ('type', ReferenceType),
    ('gradient', GradientInfo),
    ('signature', size_t),
    ('previous', POINTER(_ElementReference)),
    ('next', POINTER(_ElementReference)),
]
ElementReference = _ElementReference

# values for enumeration 'DirectionType'
UndefinedDirection = 0
RightToLeftDirection = 1
LeftToRightDirection = 2
DirectionType = c_int # enum
_DrawInfo._fields_ = [
    ('primitive', STRING),
    ('geometry', STRING),
    ('viewbox', RectangleInfo),
    ('affine', AffineMatrix),
    ('gravity', GravityType),
    ('fill', PixelPacket),
    ('stroke', PixelPacket),
    ('stroke_width', c_double),
    ('gradient', GradientInfo),
    ('fill_pattern', POINTER(Image)),
    ('tile', POINTER(Image)),
    ('stroke_pattern', POINTER(Image)),
    ('stroke_antialias', MagickBooleanType),
    ('text_antialias', MagickBooleanType),
    ('fill_rule', FillRule),
    ('linecap', LineCap),
    ('linejoin', LineJoin),
    ('miterlimit', size_t),
    ('dash_offset', c_double),
    ('decorate', DecorationType),
    ('compose', CompositeOperator),
    ('text', STRING),
    ('face', size_t),
    ('font', STRING),
    ('metrics', STRING),
    ('family', STRING),
    ('style', StyleType),
    ('stretch', StretchType),
    ('weight', size_t),
    ('encoding', STRING),
    ('pointsize', c_double),
    ('density', STRING),
    ('align', AlignType),
    ('undercolor', PixelPacket),
    ('border_color', PixelPacket),
    ('server_name', STRING),
    ('dash_pattern', POINTER(c_double)),
    ('clip_mask', STRING),
    ('bounds', SegmentInfo),
    ('clip_units', ClipPathUnits),
    ('opacity', Quantum),
    ('render', MagickBooleanType),
    ('element_reference', ElementReference),
    ('debug', MagickBooleanType),
    ('signature', size_t),
    ('kerning', c_double),
    ('interword_spacing', c_double),
    ('interline_spacing', c_double),
    ('direction', DirectionType),
]

# values for enumeration 'PrimitiveType'
UndefinedPrimitive = 0
PointPrimitive = 1
LinePrimitive = 2
RectanglePrimitive = 3
RoundRectanglePrimitive = 4
ArcPrimitive = 5
EllipsePrimitive = 6
CirclePrimitive = 7
PolylinePrimitive = 8
PolygonPrimitive = 9
BezierPrimitive = 10
ColorPrimitive = 11
MattePrimitive = 12
TextPrimitive = 13
ImagePrimitive = 14
PathPrimitive = 15
PrimitiveType = c_int # enum
_PrimitiveInfo._fields_ = [
    ('point', PointInfo),
    ('coordinates', size_t),
    ('primitive', PrimitiveType),
    ('method', PaintMethod),
    ('text', STRING),
]
_TypeMetric._fields_ = [
    ('pixels_per_em', PointInfo),
    ('ascent', c_double),
    ('descent', c_double),
    ('width', c_double),
    ('height', c_double),
    ('max_advance', c_double),
    ('underline_position', c_double),
    ('underline_thickness', c_double),
    ('bounds', SegmentInfo),
    ('origin', PointInfo),
]
_ExceptionInfo._fields_ = [
    ('severity', ExceptionType),
    ('error_number', c_int),
    ('reason', STRING),
    ('description', STRING),
    ('exceptions', c_void_p),
    ('relinquish', MagickBooleanType),
    ('semaphore', POINTER(SemaphoreInfo)),
    ('signature', size_t),
]
_ChannelFeatures._fields_ = [
    ('angular_second_moment', c_double * 4),
    ('contrast', c_double * 4),
    ('correlation', c_double * 4),
    ('variance_sum_of_squares', c_double * 4),
    ('inverse_difference_moment', c_double * 4),
    ('sum_average', c_double * 4),
    ('sum_variance', c_double * 4),
    ('sum_entropy', c_double * 4),
    ('entropy', c_double * 4),
    ('difference_variance', c_double * 4),
    ('difference_entropy', c_double * 4),
    ('measure_of_correlation_1', c_double * 4),
    ('measure_of_correlation_2', c_double * 4),
    ('maximum_correlation_coefficient', c_double * 4),
]
_GeometryInfo._fields_ = [
    ('rho', c_double),
    ('sigma', c_double),
    ('xi', c_double),
    ('psi', c_double),
    ('chi', c_double),
]
_HashmapInfo._fields_ = [
]
_LinkedListInfo._fields_ = [
]
_ColorPacket._fields_ = [
    ('pixel', PixelPacket),
    ('index', IndexPacket),
    ('count', MagickSizeType),
]
_ImageView._fields_ = [
]
class _ChromaticityInfo(Structure):
    pass
class _PrimaryInfo(Structure):
    pass
_PrimaryInfo._fields_ = [
    ('x', c_double),
    ('y', c_double),
    ('z', c_double),
]
PrimaryInfo = _PrimaryInfo
_ChromaticityInfo._fields_ = [
    ('red_primary', PrimaryInfo),
    ('green_primary', PrimaryInfo),
    ('blue_primary', PrimaryInfo),
    ('white_point', PrimaryInfo),
]
ChromaticityInfo = _ChromaticityInfo

# values for enumeration 'EndianType'
UndefinedEndian = 0
LSBEndian = 1
MSBEndian = 2
EndianType = c_int # enum
class _ErrorInfo(Structure):
    pass
_ErrorInfo._fields_ = [
    ('mean_error_per_pixel', c_double),
    ('normalized_mean_error', c_double),
    ('normalized_maximum_error', c_double),
]
ErrorInfo = _ErrorInfo
class _Timer(Structure):
    pass
_Timer._fields_ = [
    ('start', c_double),
    ('stop', c_double),
    ('total', c_double),
]
Timer = _Timer

# values for enumeration 'TimerState'
UndefinedTimerState = 0
StoppedTimerState = 1
RunningTimerState = 2
TimerState = c_int # enum
_TimerInfo._fields_ = [
    ('user', Timer),
    ('elapsed', Timer),
    ('state', TimerState),
    ('signature', size_t),
]
class _Ascii85Info(Structure):
    pass
Ascii85Info = _Ascii85Info
class _BlobInfo(Structure):
    pass
BlobInfo = _BlobInfo
class _ProfileInfo(Structure):
    pass
_ProfileInfo._fields_ = [
    ('name', STRING),
    ('length', size_t),
    ('info', POINTER(c_ubyte)),
    ('signature', size_t),
]
ProfileInfo = _ProfileInfo
_Image._fields_ = [
    ('storage_class', ClassType),
    ('colorspace', ColorspaceType),
    ('compression', CompressionType),
    ('quality', size_t),
    ('orientation', OrientationType),
    ('taint', MagickBooleanType),
    ('matte', MagickBooleanType),
    ('columns', size_t),
    ('rows', size_t),
    ('depth', size_t),
    ('colors', size_t),
    ('colormap', POINTER(PixelPacket)),
    ('background_color', PixelPacket),
    ('border_color', PixelPacket),
    ('matte_color', PixelPacket),
    ('gamma', c_double),
    ('chromaticity', ChromaticityInfo),
    ('rendering_intent', RenderingIntent),
    ('profiles', c_void_p),
    ('units', ResolutionType),
    ('montage', STRING),
    ('directory', STRING),
    ('geometry', STRING),
    ('offset', ssize_t),
    ('x_resolution', c_double),
    ('y_resolution', c_double),
    ('page', RectangleInfo),
    ('extract_info', RectangleInfo),
    ('tile_info', RectangleInfo),
    ('bias', c_double),
    ('blur', c_double),
    ('fuzz', c_double),
    ('filter', FilterTypes),
    ('interlace', InterlaceType),
    ('endian', EndianType),
    ('gravity', GravityType),
    ('compose', CompositeOperator),
    ('dispose', DisposeType),
    ('clip_mask', POINTER(_Image)),
    ('scene', size_t),
    ('delay', size_t),
    ('ticks_per_second', ssize_t),
    ('iterations', size_t),
    ('total_colors', size_t),
    ('start_loop', ssize_t),
    ('error', ErrorInfo),
    ('timer', TimerInfo),
    ('progress_monitor', MagickProgressMonitor),
    ('client_data', c_void_p),
    ('cache', c_void_p),
    ('attributes', c_void_p),
    ('ascii85', POINTER(Ascii85Info)),
    ('blob', POINTER(BlobInfo)),
    ('filename', c_char * 4096),
    ('magick_filename', c_char * 4096),
    ('magick', c_char * 4096),
    ('magick_columns', size_t),
    ('magick_rows', size_t),
    ('exception', ExceptionInfo),
    ('debug', MagickBooleanType),
    ('reference_count', ssize_t),
    ('semaphore', POINTER(SemaphoreInfo)),
    ('color_profile', ProfileInfo),
    ('iptc_profile', ProfileInfo),
    ('generic_profile', POINTER(ProfileInfo)),
    ('generic_profiles', size_t),
    ('signature', size_t),
    ('previous', POINTER(_Image)),
    ('list', POINTER(_Image)),
    ('next', POINTER(_Image)),
    ('interpolate', InterpolatePixelMethod),
    ('black_point_compensation', MagickBooleanType),
    ('transparent_color', PixelPacket),
    ('mask', POINTER(_Image)),
    ('tile_offset', RectangleInfo),
    ('properties', c_void_p),
    ('artifacts', c_void_p),
    ('type', ImageType),
    ('dither', MagickBooleanType),
    ('extent', MagickSizeType),
    ('ping', MagickBooleanType),
    ('channels', size_t),
]
_ImageInfo._fields_ = [
    ('compression', CompressionType),
    ('orientation', OrientationType),
    ('temporary', MagickBooleanType),
    ('adjoin', MagickBooleanType),
    ('affirm', MagickBooleanType),
    ('antialias', MagickBooleanType),
    ('size', STRING),
    ('extract', STRING),
    ('page', STRING),
    ('scenes', STRING),
    ('scene', size_t),
    ('number_scenes', size_t),
    ('depth', size_t),
    ('interlace', InterlaceType),
    ('endian', EndianType),
    ('units', ResolutionType),
    ('quality', size_t),
    ('sampling_factor', STRING),
    ('server_name', STRING),
    ('font', STRING),
    ('texture', STRING),
    ('density', STRING),
    ('pointsize', c_double),
    ('fuzz', c_double),
    ('background_color', PixelPacket),
    ('border_color', PixelPacket),
    ('matte_color', PixelPacket),
    ('dither', MagickBooleanType),
    ('monochrome', MagickBooleanType),
    ('colors', size_t),
    ('colorspace', ColorspaceType),
    ('type', ImageType),
    ('preview_type', PreviewType),
    ('group', ssize_t),
    ('ping', MagickBooleanType),
    ('verbose', MagickBooleanType),
    ('view', STRING),
    ('authenticate', STRING),
    ('channel', ChannelType),
    ('attributes', POINTER(Image)),
    ('options', c_void_p),
    ('progress_monitor', MagickProgressMonitor),
    ('client_data', c_void_p),
    ('cache', c_void_p),
    ('stream', StreamHandler),
    ('file', POINTER(FILE)),
    ('blob', c_void_p),
    ('length', size_t),
    ('magick', c_char * 4096),
    ('unique', c_char * 4096),
    ('zero', c_char * 4096),
    ('filename', c_char * 4096),
    ('debug', MagickBooleanType),
    ('tile', STRING),
    ('subimage', size_t),
    ('subrange', size_t),
    ('pen', PixelPacket),
    ('signature', size_t),
    ('virtual_pixel_method', VirtualPixelMethod),
    ('transparent_color', PixelPacket),
    ('profile', c_void_p),
    ('synchronize', MagickBooleanType),
]
_LocaleInfo._fields_ = [
    ('path', STRING),
    ('tag', STRING),
    ('message', STRING),
    ('stealth', MagickBooleanType),
    ('previous', POINTER(_LocaleInfo)),
    ('next', POINTER(_LocaleInfo)),
    ('signature', size_t),
]
_LogInfo._fields_ = [
]
_MagicInfo._fields_ = [
    ('path', STRING),
    ('name', STRING),
    ('target', STRING),
    ('magic', POINTER(c_ubyte)),
    ('length', size_t),
    ('offset', MagickOffsetType),
    ('exempt', MagickBooleanType),
    ('stealth', MagickBooleanType),
    ('previous', POINTER(_MagicInfo)),
    ('next', POINTER(_MagicInfo)),
    ('signature', size_t),
]
IsImageFormatHandler = CFUNCTYPE(MagickBooleanType, POINTER(c_ubyte), size_t)

# values for enumeration 'MagickFormatType'
UndefinedFormatType = 0
ImplicitFormatType = 1
ExplicitFormatType = 2
MagickFormatType = c_int # enum
_MagickInfo._fields_ = [
    ('name', STRING),
    ('description', STRING),
    ('version', STRING),
    ('note', STRING),
    ('module', STRING),
    ('image_info', POINTER(ImageInfo)),
    ('decoder', POINTER(DecodeImageHandler)),
    ('encoder', POINTER(EncodeImageHandler)),
    ('magick', POINTER(IsImageFormatHandler)),
    ('client_data', c_void_p),
    ('adjoin', MagickBooleanType),
    ('raw', MagickBooleanType),
    ('endian_support', MagickBooleanType),
    ('blob_support', MagickBooleanType),
    ('seekable_stream', MagickBooleanType),
    ('format_type', MagickFormatType),
    ('thread_support', MagickStatusType),
    ('stealth', MagickBooleanType),
    ('previous', POINTER(_MagickInfo)),
    ('next', POINTER(_MagickInfo)),
    ('signature', size_t),
]
_MimeInfo._fields_ = [
]
_ModuleInfo._fields_ = [
    ('path', STRING),
    ('tag', STRING),
    ('handle', c_void_p),
    ('unregister_module', CFUNCTYPE(None)),
    ('register_module', CFUNCTYPE(size_t)),
    ('timestamp', time_t),
    ('stealth', MagickBooleanType),
    ('previous', POINTER(_ModuleInfo)),
    ('next', POINTER(_ModuleInfo)),
    ('signature', size_t),
]
_MontageInfo._fields_ = [
    ('geometry', STRING),
    ('tile', STRING),
    ('title', STRING),
    ('frame', STRING),
    ('texture', STRING),
    ('font', STRING),
    ('pointsize', c_double),
    ('border_width', size_t),
    ('shadow', MagickBooleanType),
    ('fill', PixelPacket),
    ('stroke', PixelPacket),
    ('background_color', PixelPacket),
    ('border_color', PixelPacket),
    ('matte_color', PixelPacket),
    ('gravity', GravityType),
    ('filename', c_char * 4096),
    ('debug', MagickBooleanType),
    ('signature', size_t),
]
KernelInfo._fields_ = [
    ('type', KernelInfoType),
    ('width', size_t),
    ('height', size_t),
    ('x', ssize_t),
    ('y', ssize_t),
    ('values', POINTER(c_double)),
    ('minimum', c_double),
    ('maximum', c_double),
    ('negative_range', c_double),
    ('positive_range', c_double),
    ('angle', c_double),
    ('next', POINTER(KernelInfo)),
    ('signature', size_t),
]
_CacheView._fields_ = [
]
_PolicyInfo._fields_ = [
]
_QuantizeInfo._fields_ = [
    ('number_colors', size_t),
    ('tree_depth', size_t),
    ('dither', MagickBooleanType),
    ('colorspace', ColorspaceType),
    ('measure_error', MagickBooleanType),
    ('signature', size_t),
    ('dither_method', DitherMethod),
]
_QuantumInfo._fields_ = [
]
_RandomInfo._fields_ = [
]
_ResampleFilter._fields_ = [
]
SemaphoreInfo._fields_ = [
]
_SplayTreeInfo._fields_ = [
]
_ChannelStatistics._fields_ = [
    ('depth', size_t),
    ('minima', c_double),
    ('maxima', c_double),
    ('sum', c_double),
    ('sum_squared', c_double),
    ('sum_cubed', c_double),
    ('sum_fourth_power', c_double),
    ('mean', c_double),
    ('variance', c_double),
    ('standard_deviation', c_double),
    ('kurtosis', c_double),
    ('skewness', c_double),
]
_StringInfo._fields_ = [
    ('path', c_char * 4096),
    ('datum', POINTER(c_ubyte)),
    ('length', size_t),
    ('signature', size_t),
]
_ThresholdMap._fields_ = [
]
_TokenInfo._fields_ = [
]
_TypeInfo._fields_ = [
    ('face', size_t),
    ('path', STRING),
    ('name', STRING),
    ('description', STRING),
    ('family', STRING),
    ('style', StyleType),
    ('stretch', StretchType),
    ('weight', size_t),
    ('encoding', STRING),
    ('foundry', STRING),
    ('format', STRING),
    ('metrics', STRING),
    ('glyphs', STRING),
    ('stealth', MagickBooleanType),
    ('previous', POINTER(_TypeInfo)),
    ('next', POINTER(_TypeInfo)),
    ('signature', size_t),
]
_XMLTreeInfo._fields_ = [
]
_XImportInfo._fields_ = [
    ('frame', MagickBooleanType),
    ('borders', MagickBooleanType),
    ('screen', MagickBooleanType),
    ('descend', MagickBooleanType),
    ('silent', MagickBooleanType),
]
_MagickWand._fields_ = [
]
_PixelView._fields_ = [
]
_DrawingWand._fields_ = [
]
_PixelIterator._fields_ = [
]
_PixelWand._fields_ = [
]
_WandView._fields_ = [
]
__all__ = ['RGBOQuantum', 'OpaqueImage', 'ManhattanKernel',
           'LocaleLower', 'MagickDelay', 'GrayVirtualPixelMethod',
           'PaletteMatteType', 'SolarizeImage',
           'TransferImageViewMethod', 'MagickSteganoImage',
           'MagickSetBackgroundColor', 'SetLogName',
           'HashPointerType', 'GetMimeInfo',
           'MorphologyMethod', 'ChopImage', 'MagickClipPathImage',
           'ParseImageGeometry', 'SyncNextImageInList',
           'MagickGetAntialias', 'IsImageView', 'DecorationType',
           'LineEndsKernel', 'MagickPolicyOptions',
           'FatalErrorHandler', 'GetOneCacheViewVirtualMethodPixel',
           'ResetMagickMemory', 'OutCompositeOp',
           'GetOneCacheViewAuthenticPixel',
           'DelegatePolicyDomain', 'IsMagickTrue', 'MagickRealType',
           'NewPixelViewRegion', 'StereoAnaglyphImage',
           'AcquireUniqueFileResource', 'DisposeType',
           'UndefinedMetric', 'IsRightsAuthorized',
           'DrawPopGraphicContext', 'PixelGetCyan', 'DrawPoint',
           'BackgroundVirtualPixelMethod', '__va_list_tag',
           'AllocateSemaphoreInfo',
           'ForgetGravity', 'StopInfo', 'UndefinedPathUnits',
           'DistanceMorphology', 'MagickWriteImagesFile',
           'UndefinedPreview', 'GetMagickPrecision', '_PrimitiveInfo',
           'PaintMethod', 'ExceptionType',
           'MagickSetImageBackgroundColor', 'MagickGetImageRegion',
           'AcquireMagickMatrix',
           'ClearPixelWand', 'BlackChannel', '_ErrorInfo',
           'CacheEvent', 'AcquireImageColormap',
           'Cylinder2PlaneDistortion', 'PixelSetBlackQuantum',
           'GetImageFromMagickWand', 'LineJoin',
           'ResizeDistortion', 'LiberateSemaphoreInfo',
           'OrderedPosterizeImage', '_MontageInfo', 'DrawSetClipRule',
           'LeftBottomOrientation', 'MagickSetImageOpacity',
           'MagickGetIteratorIndex', 'GetMagickPageSize',
           'StreamFatalError', 'AcquireExceptionInfo', 'ShortPixel',
           'MagickSetPassphrase', 'MagickGetNumberImages',
           'IsMagickWand', '_Image', 'UndefinedQuantumAlpha',
           'ImageView', 'CoderWarning', 'MagickThumbnailImage',
           'TriangleFilter', 'CopyMagickString',
           'AcquireIndexes', 'DestroyImageProperties',
           'CropImageToTiles', 'GetDelegateCommand',
           'SignedQuantumFormat', 'MagickSetImagePage',
           'DestroyMagickRegistry',
           'DrawGetStrokeLineCap', 'PutEntryInHashmap',
           'GetMagickCopyright', 'DrawSetFont',
           'MagickDecorateOptions', 'RightToLeftDirection',
           'AcquireCacheViewPixels', 'OptionWarning',
           'PrependImageToList', '_RectangleInfo', 'SetImageClipMask',
           '_IO_FILE', 'RotatePreview', 'DestroyMagickMemory',
           'MagickGetImageSignature', 'GeometryInfo',
           'UpdatePixelViewIterator', 'GetImageChannelFeatures',
           'EdgeDetectPreview', 'MagickResizeImage',
           'DrawGetStrokeLineJoin', 'ChannelStatistics',
           'DrawPathMoveToAbsolute', 'StripString', 'GRAYColorspace',
           'ResizeQuantumMemory', 'GrayscaleMatteType',
           'MagickGetImageChannelDistortion',
           'MagickAdaptiveSharpenImageChannel', 'SetXMLTreeContent',
           'CubicFilter', 'ResetImageProfileIterator',
           '_MagicInfo', 'AcquireOneCacheViewPixel',
           'SetLogEventMask', 'QueryMagickColor',
           'MagickDeleteImageProperty',
           'BrightnessContrastImage', 'GetImageGeometry',
           'MagickCoreTerminus', 'RemoteDisplayCommand',
           'GetOnePixel',
           'UnregisterStaticModules', 'RandomChannelThresholdImage',
           'RandomNoise', 'MattePrimitive', 'GetNextImageProfile',
           'ClearLinkedList', 'MagickPaintOpaqueImageChannel',
           'ThresholdBlackEvaluateOperator', 'MogrifyImages',
           'MagickGammaImage', 'GetLocaleList',
           'MagickDelegateOptions', 'GetOneCacheViewVirtualPixel',
           'SetMagickMemoryMethods', 'ThreadResource', 'RightAlign',
           'MagickSigmoidalContrastImage', 'TransferWandViewIterator',
           'RootPath', 'DeskewImage', 'MagickDeskewImage',
           'OpenMorphology', 'PixelSetHSL',
           'SyncCacheViewAuthenticPixels', 'ModulusAddCompositeOp',
           'SetImageBackgroundColor', 'PixelSetOpacity',
           'GetImageViewAuthenticPixels', 'DefineImageArtifact',
           'PixelGetGreenQuantum', 'StringToArgv',
           'MagickDisposeOptions', 'AppendImageFormat',
           'SetImageRegistry', 'DrawGetOpacity',
           'RightTopOrientation', 'BorderImage', 'ConstituteImage',
           'GetLogInfoList', 'GrayChannels', 'DrawPathLineToAbsolute',
           'MosaicLayer', 'NormalizeImage',
           'MagickSetImageVirtualPixelMethod', 'TransverseImage',
           'PaintOpaqueImage', 'MagickSetColorspace',
           'GaussianFilter', 'ParseGravityGeometry',
           'SortColormapByIntensity', 'TransferPixelViewMethod',
           'MissingDelegateWarning', 'GetTypeInfoByFamily',
           'MagickGetImageChannelStatistics', 'PixelGetBlackQuantum',
           'MorphImages', 'DrawGetExceptionType',
           '_LocaleInfo', 'FilterImage', 'ResetImageRegistryIterator',
           'HorizontalTileEdgeVirtualPixelMethod',
           'MagickMosaicImages', 'AnnotateEvent', '_Ascii85Info',
           'X11Compliance', 'MagickSetImageUnits', 'CloneMontageInfo',
           'FreiChenKernel', 'DestroyKernelInfo',
           'MagickHaldClutImageChannel',
           'MagickGetImageBorderColor', 'PixelSetMagenta',
           'MagickColorMatrixImage', 'MagickStyleOptions',
           'FloydSteinbergDitherMethod', 'MagickGetImageType',
           'SplineInterpolatePixel', 'MagickOptimizeImageLayers',
           'StartTimer', 'SouthGravity',
           'UndefinedDitherMethod', 'NormalStretch',
           'InsertTagIntoXMLTree', 'GetImageException',
           'ResourceComponentGenesis', 'GetQuantumFormat',
           'SkeletonKernel', 'DrawInfo', 'QuantumAlphaType',
           'TransformHSL', '_ColorInfo', 'ImplodePreview',
           'MagickNextImage', 'Tokenizer', 'StorageType',
           'LevelColorsImageChannel', 'GaussianKernel',
           'OverlineDecoration',
           'AppendValueToLinkedList', 'ColorPrimitive',
           'ExportQuantumPixels', 'SegmentInfo',
           'IntegralRotateImage', '_ImageInfo', 'UndefinedInterlace',
           'GetNextImageProperty',
           'RGBChannels', 'TransparentPaintImage', 'ImageToFile',
           'MagickVirtualPixelOptions', 'RingKernel',
           'AccelerateConvolveImage', 'MagickGetImageIndex',
           'MagickExportImagePixels',
           'MagickEvaluateOperator', 'MagickClassOptions',
           'ColorizeImage', 'PixelGetYellow',
           'IsPathAccessible', 'MeshInterpolatePixel',
           'LabColorspace', 'MagickGetOptions', 'DrawGetClipRule',
           'UndefinedRule', 'UpdatePixelViewMethod',
           'DestroyPixelView', 'DrawGetFontFamily',
           'ParseAffineGeometry', 'Rec709YCbCrColorspace',
           'DrawGetTextAlignment', 'MagickGetImageGamma',
           'AreaResource', 'CirclePrimitive',
           'SemaphoreComponentTerminus', 'MagickSetImageChannelDepth',
           'PixelSetMagentaQuantum', 'CatchException',
           'SigmoidalContrastImageChannel', 'DrawGetStrokeOpacity',
           'CloneDrawingWand', 'AcquirePixelCachePixels',
           'BlackQuantum', 'sRGBColorspace', 'CloneImageProperties',
           'ComplianceType', 'MagickImportImagePixels',
           'GetImageInfoFile', 'CenterGravity', 'GetTypeInfoList',
           'SetImageDepth', 'ChannelImage',
           'GetNumberOfEntriesInHashmap', 'MagickIdentifyImage',
           'MagickFlattenImages', 'OrEvaluateOperator', 'FileToBlob',
           'SquareCap', 'ReferenceImage', 'DelegateComponentGenesis',
           'Ascii85Encode', 'CoalesceImages', 'ReferenceType',
           'OptimizeLayer', 'SetQuantumFormat', 'CombineImages',
           'GetImageClipMask', 'MagickTransparentPaintImage',
           'UndefinedCompliance', 'RiemersmaDitherMethod',
           'PopImageList', 'ModuleError', 'PixelSetRed',
           'ParseRegionGeometry', 'MagicComponentTerminus',
           'MagickPreviewImages', 'DrawSetViewbox', 'PointFilter',
           'BlurImage', 'MagicInfo', 'DestroyMagickWand',
           'MagickGetImagePixelColor', 'SparseColorMethod',
           'CenterAlign', 'PrimitiveType',
           'RemoveLastElementFromLinkedList', 'PixelGetYellowQuantum',
           'PixelGetColorAsNormalizedString', 'ListMagicInfo',
           'StreamImageCommand', 'MapImages', 'PixelGetMagickColor',
           'ImageRegistryType', 'MagickCommandOptions',
           'GrayAlphaQuantum', 'SegmentImage',
           'BoxFilter', 'InterpretImageProperties', 'CompassKernel',
           'DrawTranslate', 'QuantumFormatType',
           'SetStringInfoLength', 'MagickSetImageFuzz',
           'CloneImageArtifacts', 'MagickReduceNoiseImage',
           'FuzzyColorMatch', 'MagickPrimitiveOptions',
           'GetLastImageInList', 'FlattenLayer',
           'PerspectiveDistortion', 'PixelPacket',
           'GetBlobStreamData', 'DrawComment', 'DrawGetClipUnits',
           'MagickShaveImage', 'GetModuleInfo',
           'ExpandAffine', 'MagickGetInterlaceScheme',
           'GetElapsedTime', 'ColorizeCompositeOp',
           'ThresholdWhiteEvaluateOperator', 'XorCompositeOp',
           'ConcatenateStringInfo', 'ReplaceImageInListReturnLast',
           'GetNextValueInSplayTree', 'IsPixelWand',
           'GammaImage', 'SetWandViewIterator',
           'GetAuthenticPixelQueue', 'DrawSetStrokeMiterLimit',
           'AcquireOneVirtualPixel', 'CloneSplayTree',
           'MagickLineJoinOptions', 'GetImageDepth',
           'DestroyExceptionInfo', 'HSBColorspace',
           'MagickSetImageBias', 'FaxCompression',
           'MagickMinifyImage', 'ProfileImage', 'TransformImages',
           'MagickSetImageMatteColor', 
           'PixelGetColorCount', 'GetClientName',
           'MagickUniqueImageColors', 'DrawFatalError',
           'MagickQueryMultilineFontMetrics', 'GetLogList',
           'SyncImagesSettings', '_ThresholdMap',
           'MagickInverseFourierTransformImage', 'GetImageChannels',
           'GetCacheViewVirtualIndexQueue', 'OrientationType',
           'RandomThresholdImageChannel', 'DrawPushGraphicContext',
           'PeekDrawingWand', 'CopyBlueCompositeOp',
           'GetCommandOptionFlags', 'MagickDistortImage',
           'OpenCacheView', 'ClearCompositeOp',
           'MagickColorFloodfillImage', 'MagickAverageImages',
           'IsImageFormatHandler', '_ModuleInfo',
           'SyncImageSettings', 'DispatchImage', 'GetPreviousImage',
           'FileResource', 'MagickLocaleOptions',
           'RandomFatalError', 'MagickOrderedPosterizeImageChannel',
           'DeleteNodeFromSplayTree', 'DestroyTokenInfo',
           'XorEvaluateOperator', 'StringInfoToString',
           'MagickGetImageWhitePoint', 'WriteImage',
           'MagickMedianFilterImage', 'CloneMemory',
           'SetResampleFilterVirtualPixelMethod',
           'GetNextImageRegistry', 'MagickGetImageProperties',
           'DrawGetStrokeAntialias', 'CopyMagentaCompositeOp',
           'PeakAbsoluteErrorMetric', 'MagickSetSamplingFactors',
           'MinimumImages', 'EqualizeImage',
           'TypeComponentTerminus', 'DivideEvaluateOperator',
           'DrawSetStrokeAlpha', 'SetAlphaChannel',
           'MagickGetGravity', 'LanczosFilter', 'PixelGetCyanQuantum',
           'MagickPolicyRightsOptions', 'GetXMLTreePath',
           'ResourceLimitFatalError', 'SetFatalErrorHandler',
           'MagickGetImageRedPrimary', 'UndefinedEndian',
           'PixelClearIteratorException',
           'EqualizeImageChannel', 'UnderlineDecoration',
           'LeastSquaresAddTerms', 'MagickGetImageColormapColor',
           'MagickImplodeImage', 'CacheView_',
           'StringToStringInfo', 'SpliceImageIntoList',
           'DrawPathClose', 'GetMagickList', 'GetPolicyList',
           'SplitImageList', 'MeanStatistic', 'RoundJoin',
           'IdentifyImage', 'InterpolatePixelColor', 'UndefinedJoin',
           'GetImageDecoder', 'MagickGetImagesBlob',
           'MagickGetOption', 'IsPixelIterator',
           'MagickSetImageGreenPrimary', 'GetOptimalKernelWidth',
           'MagickSetProgressMonitor', 'FormatImageAttributeList',
           'MonitorError', 'MagickFrameImage',
           'DecodeImageHandler', 'MagickCompressOptions',
           'GetMagickDescription', 'HanningFilter',
           'MagickSepiaToneImage', 'PixelGetHSL', 'GetCoderList',
           'DrawPathLineToVerticalRelative', '_ElementReference',
           'GetWandViewWand', 'DistortCompositeOp',
           'AnimateImageCommand', 'ErrorInfo', 'GetImagePixels',
           'GetExceptionInfo', '_FrameInfo', 'JPEG2000Compression',
           'ConsolidateCMYKImages', 'DrawGetStrokeDashArray',
           'MagickSetCompressionQuality', 'CatromFilter',
           'MagickSmushImages', 'SetImageAttribute',
           'DifferenceCompositeOp', 'ResetImageOptionIterator',
           'MontageImageCommand', 'WarningException',
           'CompositeLayers', 'SepiaToneImage', 'SVGCompliance',
           'TemporaryFilename', 'ResizeImage', 'CopyMagickMemory',
           'MagickClearException', 'TypeWarning', 'OpenModules',
           'MontageImages', 'GetWandViewIterator',
           'MedianEvaluateOperator', 'SetImageInfoBlob',
           'CloneImageAttributes', 'MonitorWarning',
           'IsHistogramImage', 'PolicyFatalError', 'CacheFatalError',
           'TrueColorMatteType', 'PingImage', 'FlopImage',
           'MagickFunction', 'SetImageArtifact',
           'EscapeString', 'JBIG2Compression',
           'PixelGetBlueQuantum', 'MagickNewImage',
           '_ProfileInfo',
           'TypeComponentGenesis', 'FloatingPointQuantumFormat',
           'GetMagickInfo', 'ReverseImageList',
           'AverageImages', 'IsMonochromeImage',
           'DisplaceCompositeOp', 'GetPixelViewIterator',
           'PixelGetPreviousIteratorRow',
           'UndefinedVirtualPixelMethod', 'ClearDrawingWand',
           'MaxEvaluateOperator', 'ObjectBoundingBox',
           'FuzzErrorMetric', 'PixelGetIndex',
           'UpdateImageViewMethod', 'ChangeMaskCompositeOp',
           'CompositeImageChannel', 'DestroyStringList',
           'TextureImage', 'ThresholdMap',
           'CoderFatalError', 'NewMagickImage', 'SyncImagePixels',
           'GetCoderInfoList', 'DistortResizeImage',
           'IsBlobExempt', 'AcquireKernelInfo', 'AcquireImage',
           'MagickSetImageDepth', 'ShadePreview', 'QuantizePreview',
           'AcquireImageInfo', 'NoPolicyRights',
           'MagickImageFilterModule', 'PopDrawingWand', 'ClutImage',
           'MagickEdgeImage', 'CheckerTileVirtualPixelMethod',
           'DrawPathCurveToRelative',
           'RemoveEntryFromHashmap', 'AbsEvaluateOperator',
           'DestroyImageArtifacts', 'HardLightCompositeOp',
           'NegateImage', '_PointInfo', 'UnregisterMagickInfo',
           'MagickSetImageInterpolateMethod', 'ReflectSpread',
           'InitializeMagick', 'FileOpenFatalError',
           'UndefinedDistortion', 'YCCColorspace', 'GetLogName',
           'GetCommandOptions', 'GetBlobSize',
           'MagickConvolveImageChannel',
           'TransparentVirtualPixelMethod', 'GetCacheViewPixels',
           'ListCoderInfo', 'GetDelegateMode',
           'AllocateImageColormap', 'GrayChannel', 'GradientInfo',
           'MagickImageCoderModule', 'ListLogInfo', 'ShiftImageList',
           'DePolarDistortion', 'ImageError', 'OpaquePaintImage',
           'MagickFillRuleOptions', 'LinearBurnCompositeOp',
           'AffineMatrix', 'YPbPrColorspace', 'AcquireRandomInfo',
           'VerticalTileVirtualPixelMethod', 'PathType',
           'LogComponentTerminus', 'MagickIntentOptions',
           'GetNextImageInList', 'ResetLinkedListIterator',
           'MagickSetImageInterlaceScheme',
           'StandardDeviationStatistic', 'ColorComponentTerminus',
           'SetImageInfoFile', 'BottomRightOrientation',
           'NoCompliance', 'GradientType', 'IntegerInterpolatePixel',
           'MagickLabelImage', 'StreamWarning', 'DestroyImageOptions',
           'ErodeMorphology', 'DrawGetFont', 'LogEvaluateOperator',
           'MagickFalse', 'DrawRender',
           'ImportImagePixels', 'ChebyshevKernel',
           'MagickSparseColorImage', 'ConjureImageCommand',
           'DarkenCompositeOp', 'MagickRadialBlurImageChannel',
           'GetPolicyInfoList', 'GetImageViewMethod',
           'BlurImageChannel', 'EastGravity', 'GetCacheViewIndexes',
           'DrawSetFillRule', 'DrawPathLineToRelative',
           'InitializeModuleList', 'IsWandView', 'LagrangeFilter',
           'MagickSpliceImage', 'ShepardsDistortion',
           'LZMACompression', 'SquareKernel', 'GetPixelViewWand',
           'GetAuthenticPixels', 'UndefinedResolution',
           'RegistryFatalError', 'DrawSetFillOpacity',
           'MagickFunctionImage', 'GetIndexes', 'CMYKQuantum',
           'TopRightOrientation', 'ExponentialEvaluateOperator',
           'RelinquishAlignedMemory', 'InterpolatePixelMethod',
           'CMYKColorspace', 'SaturationIntent',
           'MagickValidateOptions', 'MagickCommandGenesis',
           'DeleteImageProfile', 'SetRandomTrueRandom',
           'PixelGetQuantumColor', 'CacheComponentTerminus',
           'SwirlImage', 'PushDrawingWand', 'ResourceType',
           'MagickGetFilename', 'QuantumInfo', 'UndefinedDecoration',
           'GetStringInfoPath', 'UndefinedKernel',
           'RGBTransformImage', 'MagickCompareImageChannels',
           'MagickEmbossImage', 'MagickGetImageMatteColor',
           'MagickRemoveImage', 'MagickMorphologyOptions',
           'FormatLocaleString',
           'GetNumberOfElementsInLinkedList', 'MultilineCensus',
           'MagickSetImageProfile', 'GetImageChannelRange',
           'GrayQuantum', 'DarkenIntensityCompositeOp',
           'AddNoisePreview', 'UpdateWandViewMethod',
           'MagickRemoveImageProfile', 'CloneImageInfo',
           'KirschKernel', 'MagickLineCapOptions',
           'MagickQuantumFormatOptions',
           'FilterImageChannel', 'DrawSetFontStretch',
           'PixelSetGreenQuantum', 'OptimizeType',
           '_DrawInfo', 'DisassociateImageStream',
           'PegtopLightCompositeOp', 'SigmoidalContrastImage',
           'HitAndMissMorphology', 'MagickPingImageFile',
           'GetPixelViewHeight', 'OverlayCompositeOp',
           'ReacquireMemory', 'CacheWarning', 'PolylinePrimitive',
           '_MagickInfo', 'DelegateComponentTerminus', 'NewHashmap',
           'MagickSetImageColormapColor',
           'GetMultilineTypeMetrics', 'ImagePrimitive',
           'B44ACompression', 'FilterTypes',
           'PreviewImage', 'MagickTransverseImage', 'DrawWarning',
           'DiskResource', 'SetClientPath',
           'LevelImageColors', 'MagickSetFont',
           'BlackmanFilter', 'IsHashmapEmpty', 'ImagesToBlob',
           'MagickMotionBlurImageChannel', 'MagickCropImage',
           'FilterWarning', 'FileToStringInfo',
           'ScaleGeometryKernelInfo', 'SetWarningHandler',
           'GetNextKeyInHashmap', '_ExceptionInfo', 'AffinityImage',
           'UnrecognizedDispose', 'StereoImage', 'PixelSetYellow',
           'XServerFatalError',
           'DrawPathCurveToQuadraticBezierRelative',
           'SetImageOpacity', 'OptimizePlusImageLayers',
           'UndefinedColorspace', 'DrawRoundRectangle',
           'TileVirtualPixelMethod', 'DestroyMagick',
           'StatisticImage', 'MagickMagnifyImage',
           'DrawPrimitive', 'MagickTextureImage',
           'OpenIntensityMorphology', 'PixelGetBlack',
           'TypeFatalError', 'SpliceImage', 'SolarizePreview',
           'LocaleUpper', 'RidgesKernel', 'GetMagickFeatures',
           'CopyCyanCompositeOp', 'GetImageDynamicThreshold',
           'GetImageExtent', 'PasskeyDecipherImage',
           'LockSemaphoreInfo', 'RollImage', 'MinusDstCompositeOp',
           'PoissonNoise', 'WestGravity', 'PixelGetAlphaQuantum',
           'ResampleImage', 'MagickEqualizeImageChannel',
           'BlobEvent', '_TypeMetric',
           'ColorComponentGenesis', 'RelinquishUniqueFileResource',
           'DestroyImageProfiles', 'DrawAllocateWand',
           'CopyRedCompositeOp', 'MagickGravityOptions', 'Image',
           'IdentifyImageCommand', 'PixelSetAlpha', 'UndefinedEvents',
           'GetImageViewVirtualIndexes',
           'MagickGetImageInterlaceScheme', 'ExceptionEvent',
           'PixelWand', 'FlipImage', 'MagickNegateImage',
           'AverageInterpolatePixel', 'FormatString',
           'RemoveImageProfile',
           'ModuleFatalError', 'PlusKernel', 'NewImageView',
           'AllEvents', 'SharpenImage', 'DrawPolygon',
           'ShowKernelInfo', 'GetFirstImageInList', 'IsPixelView',
           'CropImage', 'GetImageKurtosis',
           'BlackThresholdImageChannel', 'MagickGetSizeOffset',
           'GetMagicInfoList', 'SizeBlob', 'ModuleComponentGenesis',
           'MagickGetImageBlob', 'QueueAuthenticPixels',
           'HuffmanEncodeImage', 'TypeInfo', 'SharpenPreview',
           'GetCacheViewAuthenticIndexQueue',
           'GetMontageInfo', 'RemoveDupsLayer', 'DestroyHashmap',
           'UniformNoiseEvaluateOperator', 'InsertImageInList',
           'InheritException', 'DrawingWand', 'MagickLevelImage',
           'MagickStretchOptions', 'SelectiveBlurImageChannel',
           'SetImageViewThreads', 'MagickModeOptions',
           'MorphologyImage', 'FunctionImageChannel',
           'Rec709LumaColorspace', 'MagickAdaptiveThresholdImage',
           'HashmapInfo', 'PolicyInfo', 'DelegateInfo',
           'MagickWhiteThresholdImage', 'DrawSetFontFamily',
           'EdgeInMorphology', 'GetMagickSeekableStream', 'FILE',
           'DuplexTransferImageViewMethod', 'PixelGetBlue',
           'BarrelDistortion', 'DrawGetStrokeDashOffset',
           'RemoveDuplicateLayers', 'UndefinedGradient',
           'SpreadImage', 'MagickBlurImageChannel', 'NewPixelWands',
           'NearestNeighborInterpolatePixel',
           'MagickSetCompression', 'ReduceNoiseImage',
           'BlueShiftImage', 'ExportImagePixels', 'MagickBlurImage',
           'CMYKOQuantum', 'MagickSigmoidalContrastImageChannel',
           'EvaluateImageChannel', 'MagickGetImageResolution',
           'ArcPrimitive', 'BilinearColorInterpolate',
           'IsCommandOption', 'ContrastImage', 'MagickSetImageOption',
           'SrcOverCompositeOp', 'GreenQuantum', 'MagickInfo',
           'MagickSetImageExtent',
           'DrawGetClipPath', 'MagickSetImageDelay',
           'PoissonNoiseEvaluateOperator', 'HSLTransform',
           'MagickStatisticOptions', 'SignatureImage',
           'MeanErrorPerPixelMetric', 'GetCacheViewVirtualPixels',
           'SeparateImages', '_ImageView',
           'MagickGetBackgroundColor', 'RemoveNodeFromSplayTree',
           'DeleteNodeByValueFromSplayTree', 'UndefinedFilter',
           'ParseSizeGeometry', 'MagickSetImagePixels',
           'UniformNoise', 'SaturateCompositeOp',
           'NormalStyle', 'GetVirtualIndexQueue',
           'MirrorVirtualPixelMethod',
           'MagickSetImageFormat', 'SetPixelViewIterator',
           'GetNextImageOption', 'RedChannel',
           'PixelSetColorFromWand', 'MagickSetImageTicksPerSecond',
           'MagickGetImageGravity', 'GetCoderInfo',
           'ImageAttribute', 'DitherVirtualPixelMethod',
           'PixelGetIteratorRow', 'MeanSquaredErrorMetric',
           'GetNumberScenes', 'MultiplyEvaluateOperator',
           'ClonePixelWands', 'InvokeDelegate', '_PixelIterator',
           'NewMagickWand', 'DrawScale',
           'AcquireImagePixels', 'FormatMagickStringList',
           'XMLTreeInfo',
           'ResizeMagickMemory', 'DissolveCompositeOp',
           'SetLogFormat', 'CorruptImageFatalError',
           'CorruptImageWarning', 'RobidouxFilter',
           'GetPixelViewX', 'ConcatenateString',
           'MergeImageLayers', 'GetMimeList',
           'MagickLinearStretchImage', 'AdaptiveSharpenImage',
           'GetTimerInfo', 'UndefinedDispose',
           'MagickUnsharpMaskImage', 'IsHighDynamicRangeImage',
           'GetImageFromMagickRegistry', 'MagickSharpenImage',
           'RobertsKernel', 'DrawSetTextInterwordSpacing',
           'GetLocaleInfoList', 'OpacityQuantum',
           'CloneImage', 'GetImageHistogram', 'DrawAffineImage',
           'PixelSyncIterator', 'MagickGetImageVirtualPixelMethod',
           'MagickFontsOptions', 'SetQuantumPack', 'RepeatSpread',
           'CyanQuantum', 'BottomLeftOrientation',
           'MagickCycleColormapImage',
           'DestroyXMLTree', 'BZipCompression', 'SetQuantumDepth',
           'ErodeIntensityMorphology', 'DrawSetTextInterlineSpacing',
           'UndefinedMethod', 'DstOutCompositeOp',
           'FuzzyOpacityCompare', 'MagickSetOption', 'PaletteType',
           'LosslessJPEGCompression', 'RoundCap', 'GIFInterlace',
           'SetQuantumPad', 'SetStringInfoPath',
           'InterpretLocaleValue', 'MagickGetImageHistogram',
           'GetQuantumInfo', 'MagickSetImageRedPrimary',
           'VerticalTileEdgeVirtualPixelMethod', 'PeaksKernel',
           'GetXMLTreeAttribute', 'RectanglePrimitive',
           'InjectImageBlob', 'GetTypeList',
           'UnsharpMaskImage', 'FilterError', 'GetImageListIndex',
           'AcquireTokenInfo', 'AnnotateComponentGenesis',
           'DivideDstCompositeOp', 'MagickModuleOptions',
           'FileToImage', 'CopyGreenCompositeOp', 'WandEvent',
           'DrawGradientImage', 'DespecklePreview',
           'MagickGetPointsize', 'ModulateCompositeOp',
           'PixelGetException', 'MagickSimilarityImage',
           'AcquireQuantizeInfo', 'OpacityChannel',
           'ParseMetaGeometry', 'DrawPushDefs', 'GetMagicList',
           'GetWandViewException', 'CompareOverlayLayer',
           'DestroyQuantizeInfo', 'BlobInfo', 'DrawSetTextDecoration',
           'GradientReference', 'DrawSetOpacity', 'GetCacheView',
           'GetNextImage', 'SmushImages', 'ModuleComponentTerminus',
           'DeleteImages', 'UpdateImageViewIterator', 'StreamHandler',
           'DrawSetFontResolution', 'LanczosSharpFilter',
           'SouthEastGravity', 'DrawImage', 'RandomWarning',
           'TimerInfo', 'GetOneVirtualMethodPixel',
           'PixelsPerInchResolution', 'GetImageVirtualPixelMethod',
           'MagickWandTerminus', 'MagickSpreadImage',
           'GetImageBoundingBox', 'TraceEvent', 'MagickAlignOptions',
           'MagickGetImageIterations', 'WandError',
           'DrawPathCurveToSmoothAbsolute', 'MetricType',
           'NoDecoration', 'MagickSetImageArtifact',
           'SetPixelViewMethod', 'Strip', 'AddChildToXMLTree',
           'PixelsPerCentimeterResolution', 'PaletteBilevelMatteType',
           'MagickPolicyDomainOptions', 'ThinningMorphology',
           'WandWarning', 'FormatLocaleStringList',
           'RGBColorspace', 'MagickQueryFonts',
           'MagickGetImageFormat', 'MagickMethodOptions',
           'ConfigureFileToStringInfo',
           'ShearRotateImage', 'GetXMLTreeSibling',
           'CompareHashmapStringInfo', 'DilateMorphology',
           'DirectClass', 'GetImageAlphaChannel',
           'RegisterMagickInfo', 'PackbitsEncodeImage',
           'ConvertImageCommand', 'PreviewType',
           'MagickAdaptiveSharpenImage', 'SrcInCompositeOp',
           'GetImageOption', 'RadialBlurImageChannel',
           'MagickShearImage', 'MagickSetImageBluePrimary',
           'GetStringInfoDatum', 'MagickAddNoiseImageChannel',
           'NonpeakStatistic', 'PasskeyEncipherImage',
           'GetMagickThreadSupport', 'DestroyWandView',
           '_HashmapInfo', 'EvaluateImage',
           'MedianFilterImage', 'PixelClearException', 'CometKernel',
           'LiberateMemory', 'GetConfigurePaths',
           'LevelizeImageChannel', 'StripImage',
           'MagickAnimateImages', 'SharpenImageChannel',
           'IsBlobTemporary', 'DrawGetVectorGraphics',
           'PixelGetColorAsString', 'CommandOption',
           'AdaptiveResizeImage', 'LevelImageChannel',
           'MissingDelegateFatalError',
           'DrawPathLineToVerticalAbsolute', 'MagickSetFilename',
           'LightenCompositeOp',
           'StatisticType', 'CosineEvaluateOperator',
           'SubtractEvaluateOperator', 'SemiCondensedStretch',
           'GetPathComponents', 'RemapImage', 'MagickFormatOptions',
           'FormatMagickSize', 'NewPixelView',
           'MagickGetImageGreenPrimary', 'MagickQueryFontMetrics',
           'ModulusSubtractCompositeOp',
           'GetMagickPixelPacket', 'MeanAbsoluteErrorMetric',
           'DrawGetTextKerning', 'SyncImageProfiles',
           'MagickFunctionImageChannel', 'IndexQuantum',
           'MagickGetType',
           'TransformColorspace', 'CyanChannel', 'DestroyDrawingWand',
           'DrawSetTextEncoding', 'AcquireMagickResource',
           'RegistryError', 'XYZColorspace',
           'UndefinedInterpolatePixel', 'UndefinedFormatType',
           'AbsoluteIntent', 'GetImageRegistry', 'CoderPolicyDomain',
           'MagickSetResourceLimit', 'RegistryWarning',
           'ImageListToArray', 'AllocateString',
           'MagickContrastStretchImageChannel', '_CoderInfo',
           'DrawSetFillPatternURL', 'MagickStatusType',
           'GetMagickAdjoin', 'RandomComponentTerminus',
           '_PixelView', '_XImportInfo', 'MagickMagicOptions',
           'SobelKernel', 'DeleteImageProperty', 'GetPixelViewMethod',
           'MagickMetricOptions', 'BarrelInverseDistortion',
           'DstInCompositeOp', 'MagickSetImageRenderingIntent',
           'AcquireMemoryHandler', 'AddNoiseImage',
           'MagickSetImageOrientation', 'MagickSampleImage',
           'ActivateAlphaChannel', 'ThrottleResource',
           'SetImageStorageClass',
           'AnimateImages', 'GetMagickMemoryMethods',
           'GetMimeInfoList', 'MagickSetFormat',
           'LogColorspace', 'RecolorImage', 'ConvertRGBToHSB',
           'PixelSetGreen', 'ParseAbsoluteGeometry',
           'ConvertRGBToHSL', 'GetModuleInfoList',
           'FrameInfo', '_ChannelStatistics', 'SetGeometry',
           'ConvolveMorphology', 'DoublePixel', 'IsDrawingWand',
           'LaplacianNoise', 'GetLocaleOptions',
           '_PolicyInfo', 'AffineDistortion',
           'MagickThresholdImageChannel', 'MagickSetExtract',
           'ModulateImage', 'UndefinedQuantumFormat', 'GetGeometry',
           '_LogInfo', 'ContrastStretchImageChannel',
           'VoronoiColorInterpolate', 'AllocateNextImage',
           'FatalErrorException', 'PrintStringInfo',
           'GetPixelViewWidth', 'GetMagickToken', '_CacheView',
           'RoundRectanglePrimitive', 'FilterPolicyDomain',
           'DrawPopDefs', 'QueryColorDatabase',
           'MagickGetResourceLimit', 'GetMagickResourceLimit',
           'DeleteImageAttribute', 'ShearImage',
           'BlackThresholdImage', 'MagickShadeImage',
           'DrawSetStrokeDashArray',
           'AdaptiveSharpenImageChannel', 'MagickGetImageAttribute',
           'CloseMagickLog', 'GetColorList',
           'MagickOrientationOptions', 'ThinSEKernel', 'RemapImages',
           'NorthWestGravity',
           'MagickSegmentImage', 'MitchellFilter', 'MontageMode',
           'AcquireKernelBuiltIn', 'AllChannels', 'ObliqueStyle',
           'MagickDistortOptions', 'AcquirePixels',
           'BilinearDistortion', 'SetMagickRegistry',
           'ColorSeparationType', 'MagickGetSamplingFactors',
           'MagickOilPaintImage', 'MagickGetReleaseDate',
           'MagickDebugOptions', 'FormatImageAttribute',
           'ParseGeometry', 'ImageLayerMethod',
           'MagickGetImageProperty', 'SincFastFilter',
           'MagickSizeType', 'MagickModuleType',
           'MagickGetImageClipMask', 'ZLIBEncodeImage',
           'MagickGetImageBluePrimary', 'UndefinedStatistic',
           'SplitStringInfo', 'GammaImageChannel',
           'IsLinkedListEmpty', '_TimerInfo', 'GetExecutionPath',
           'BilevelType', 'TrimBoundsLayer',
           'PolynomialColorInterpolate', 'CommandOptionToMnemonic',
           'MagickGetFont', 'WhiteThresholdImage',
           'UndefinedChannel', 'TokenInfo',
           'PolygonPrimitive', 'MagickAffineTransformImage',
           'UndefinedIntent', 'AppendImages', 'RandomInfo',
           'DeleteImageRegistry', 'GradientImage',
           'GetImageChannelDepth', 'ShapeAlphaChannel',
           'GenerateDifferentialNoise', 'MagickWriteImageFile',
           'DescribeImage', 'MimeInfo', 'AdaptiveBlurImageChannel',
           '_PixelWand', 'TransparentColorspace', 'CloneQuantizeInfo',
           'SetImageViewIterator',
           'MagickSetResolution', 'MagickInterlaceOptions',
           'MagickSetFirstIterator', 'MagickMorphologyImage',
           'MagickSetImage', 'CatchImageException',
           'SetCacheThreshold', 'CloneImageView', 'DestroyString',
           'GetPixelCacheVirtualMethod', 'RemoveLastImageFromList',
           'WhiteThresholdImageChannel',
           'CoderInfo', 'ResourceComponentTerminus',
           'MagickMorphologyImageChannel', 'MagickMinimumImages',
           'HueCompositeOp', 'GetConfigureOptions',
           'SrcAtopCompositeOp', 'CompressImageColormap',
           'ZipSCompression', 'ModuleInfo',
           'DrawGetTextInterlineSpacing', 'DestroyConstitute',
           'MissingDelegateError', 'CloneImages', 'UndefinedStretch',
           'DrawSetTextAlignment', 'MagickMergeImageLayers',
           'SetCacheViewPixels',
           'ParseChannelOption', 'GaussianBlurImage',
           'GaussianNoiseEvaluateOperator', 'AcquireString',
           'MagickGetColorspace', 'CacheComponentGenesis',
           'MagickSetImageIndex', 'QuantumType',
           'AccelerateEvent', 'GetOneVirtualMagickPixel',
           'ClampImage',
           'PixelSetIteratorRow', 'ConvertHWBToRGB', 'ProfileInfo',
           'JPEGPreview', 'WriteStream', 'ResourceLimitWarning',
           'CoalesceLayer', 'MagickAddNoiseImage',
           'MagickResolutionOptions', 'QueryMagickColorname',
           'ListMagickResourceInfo', '_XMLTreeInfo', 'PixelSetFuzz',
           'UltraCondensedStretch', 'CorrelateMorphology',
           'PolicyEvent', 'MagickGetImageArtifact', 'GetTypeMetrics',
           'AcquireOneCacheViewVirtualPixel', 'UndefinedAlphaChannel',
           'EvaluateImages', 'LocaleNCompare',
           'DrawPathCurveToQuadraticBezierAbsolute', 'TimerState',
           'ColorMatrixImage', 'SegmentPreview', 'NewXMLTree',
           'MagickIncarnate', 'AcquireAlignedMemory',
           'ThresholdCompositeOp', 'XImportImage',
           'MagickComponentGenesis', 'RaiseImage', 'GlobExpression',
           'SyncImage', 'TranslateText',
           'MagickBrightnessContrastImageChannel',
           'InterpretImageAttributes', 'CopyAlphaChannel',
           'CrossKernel', 'WaveImage', 'NewPixelWand',
           'PixelSetCyanQuantum', 'MogrifyImageList',
           'PushImagePixels', 'BasePath',
           'DrawGetException', 'IsImagesEqual',
           'SetQuantumMinIsWhite', 'GetMagickBlobSupport',
           'MagickOpaquePaintImage', 'FormatMagickCaption',
           'MagickKernelOptions',
           'MagickSetImageResolution',
           'DrawPathLineToHorizontalRelative', 'LoGKernel',
           'EllipsePrimitive', 'ReadImage', 'NonZeroRule',
           'PixelIterator', 'AdaptiveBlurImage', 'MagickFontOptions',
           'Base64Decode', 'ReadImages',
           'AllCompliance', 'CompareAnyLayer',
           'KernelInfoType', 'GetImageClippingPathAttribute',
           'MagickNoiseOptions', 'AffinityImages', 'AcquireOnePixel',
           'ShadowImage', 'FileOpenWarning', 'MinimumStatistic',
           'MagickGetImageArtifacts', 'GaussianNoise',
           'TextPrimitive', 'AcquireQuantumInfo',
           'LinearDodgeCompositeOp', 'JBIG1Compression',
           'RunningTimerState', 'MagickGetImageHeight',
           'InsertValueInSortedLinkedList', 'DrawGetStrokeAlpha',
           'MagickLogEventOptions', 'GetImageAttribute',
           'RelinquishMagickMatrix', 'ArctanFunction',
           'LeftToRightDirection', 'ClutImageChannel',
           'JPEGInterlace', 'MapImage', 'GetImageMask',
           'MotionBlurImageChannel', 'IdentityAffine',
           'ReadPolicyRights', 'GrayscaleType', 'DestroySplayTree',
           'CopyBlackCompositeOp', 'UndefinedException', 'ShaveImage',
           'SetXMLTreeAttribute',
           'RelinquishSemaphoreInfo', 'MagickExtentImage',
           'ImageInfoRegistryType', 'PixelGetGreen',
           'MagickDecipherImage', 'DrawBezier',
           'OrderedDitherImage', 'EnhanceImage',
           'RedQuantum', 'ZipCompression', 'HashStringType',
           'MinMaxStretchImage', 'LongPixel',
           '_GradientInfo', 'MedianStatistic', 'SyncCacheViewPixels',
           'RandomError', 'ChopPathComponents', 'DrawSetStrokeColor',
           'GetPseudoRandomValue', 'AnyStyle', 'QuantizationError',
           'ConcatenateMode', 'ScaleImage', 'PlusCompositeOp',
           'ClonePixelView', 'MagickChopImage',
           'StreamError', 'FillToBorderMethod',
           'MagickGetImageTicksPerSecond', 'ScreenCompositeOp',
           'ModifyImage', 'SubimagePath', 'AutoGammaImage',
           'TopHatMorphology', 'MagickGetImageChannelFeatures',
           'SpreadPreview', 'MagickRollImage',
           'MagickGetQuantumDepth', 'TransformImageColorspace',
           'GetMagickReleaseDate', 'PixelSetIndex',
           'BicubicInterpolatePixel', 'DrawLine', 'SpliceImageList',
           'IsGeometry', 'GetCacheViewException',
           'DrawPathCurveToAbsolute', 'MultiplicativeGaussianNoise',
           'ChannelType', 'AddEvaluateOperator',
           'MagickSelectiveBlurImage', 'TransformImage',
           'SetQuantumImageType', 'ShadeImage', 'ResetTimer',
           'GetWandViewExtent', 'GetImageList', 'CornersKernel',
           'Quantum', 'Ascii85Info', 'MagickDataTypeOptions',
           'MagickSketchImage', 'BohmanFilter', 'GetQuantumType',
           'OpenMagickStream', 'CycleColormapImage',
           'LaplacianKernel', 'ExclusionCompositeOp',
           'NewWandViewExtent', 'GetCacheViewExtent',
           'MagickTransposeImage', 'GetImageQuantumDepth',
           '_DelegateInfo', 'NorthGravity',
           'YIQColorspace', 'MagickLevelImageChannel',
           'SetImageAlphaChannel', 'PixelGetFuzz', 'BlobError',
           'SentinelDistortion', 'DestroyStringInfo', 'DrawColor',
           'MagickEvaluateOptions', 'EncodeImageHandler',
           'LoadMimeLists', 'RenderingIntent',
           'ArcDistortion', 'MagickGetImageScene',
           'ConfigureFatalError', 'GetMagickRegistry',
           'IsMagickColorSimilar', 'GetColorInfoList',
           'SetMagickInfo', 'DoGKernel', 'MagickLogOptions',
           'SetImageColorspace', 'MagickSetImageCompressionQuality',
           'GetMagickProperty', 'DrawSetStrokeLineJoin',
           'MagickMatteFloodfillImage', 'MagickScaleImage',
           'DrawPushClipPath', 'BezierPrimitive',
           'MagickResourceOptions', 'ColorBurnCompositeOp',
           'DstCompositeOp', 'MagickBlackThresholdImage',
           'CloseMorphology', 'BilevelImage', 'FrameMode',
           'CompositeChannels', 'QuantizeInfo',
           'ColorDodgeCompositeOp', 'CoderComponentTerminus',
           'NewDrawingWand',
           'MagickSetImageFilename', 'DefaultChannels',
           'ResetHashmapIterator', 'BilinearInterpolatePixel',
           'ConcatenateColorComponent', 'IsSubimage', 'BevelJoin',
           'MathematicsCompositeOp', 'MagickFilterImageChannel',
           'GetOneAuthenticPixel', 'SetRandomKey', 'PolicyDomain',
           'MimeComponentTerminus', 'DrawResetVectorGraphics',
           'ContinueTimer', 'ResourceLimitError',
           'PixelGetCurrentIteratorRow', 'BilinearReverseDistortion',
           'MagickSetImageCompose', 'SaturationPreview',
           'GetConfigureBlob', 'MagickSetImageMatte',
           'RemoveZeroLayer', 'PixelSetFirstIteratorRow',
           'GetExceptionMessage', 'GetImageChannelDistortion',
           'PreviousDispose', 'MagickColorDecisionListImage',
           'MagickCompositeImageChannel', 'GammaPreview',
           'LogEventType', 'RemoveImageFromList', 'ConstantString',
           'DestroyQuantumInfo', 'ScaleRotateTranslateDistortion',
           'AffineTransformImage', 'MagicComponentGenesis',
           'TintImage', 'ListModuleInfo', 'FxImageChannel',
           'XPMCompliance', 'EdgesKernel', 'ExtractSubimageFromImage',
           'XServerWarning', 'ColorPacket',
           'MagickRegionOfInterestImage',
           'RemoveElementByValueFromLinkedList',
           'GetConfigureInfoList', 'CoderError', 'CompositeImage',
           'GetMagickQuantumDepth', 'GetImageDistortion',
           'MagickAutoGammaImageChannel', 'GetAffineMatrix',
           'SplayTreeInfo', 'ColorSeparationMatteType',
           'AcquireDrawInfo', 'MagickSetImageScene', 'PointInfo',
           'CoderComponentGenesis', 'GetMagickHomeURL',
           'MontageInfo', '_QuantumInfo',
           'DefineImageRegistry', 'GetMimeType', 'DelegateFatalError',
           'ModeStatistic', 'MagickWarning', 'MogrifyImageCommand',
           'DrawGetTextInterwordSpacing',
           'MagickPingImage', 'AppendImageToList',
           'WhiteVirtualPixelMethod',
           'SetImageInfoProgressMonitor', 'MagickSetPage',
           'SelectiveBlurImage', 'SetQuantumQuantum',
           'GrayscalePreview', 'OptimizePlusLayer', 'PolarDistortion',
           'GetNextImageAttribute', 'MagickGetImagePage',
           'NewPixelRegionIterator', 'DirectionType', 'WelshFilter',
           'MagickAdaptiveBlurImageChannel', 'LiquidRescaleImage',
           'DeactivateAlphaChannel', 'DestroySemaphoreInfo',
           'MagickQueryConfigureOptions', 'MagickGaussianBlurImage',
           'DrawGetFontSize', 'ImageType', 'Rec601YCbCrColorspace',
           'SoftLightCompositeOp', 'NoCompression', 'MagickTintImage',
           'UnsharpMaskImageChannel', 'DestroyImage',
           'GetXMLTreeContent', 'ConvertHSLToRGB',
           'GetDelegateInfoList', 'RootMeanSquaredErrorMetric',
           'MagickTrimImage', 'TransferImageViewIterator',
           'AddValueToSplayTree', 'HammingFilter',
           'SetPixelCacheVirtualMethod', 'ThumbnailImage',
           'ImageEvent', 'MagickDeleteOption', 'MaximumImages',
           'SeedPseudoRandomGenerator', 'ListConfigureInfo',
           'MagickListOptions', 'ScaleResampleFilter',
           'PersistPixelCache', 'MagickSetImageGamma',
           'GetImageViewException', '_SplayTreeInfo',
           'OilPaintPreview', 'DrawSetVectorGraphics', 'BlurPreview',
           'DelegateError', 'FillRule', 'GetPixels',
           'MagickDitherOptions', 'MagickSetType',
           'GetPathComponent', 'GetNumberOfNodesInSplayTree',
           'MagickTransformImage', 'MagickFxImage',
           'MagickProgressMonitor', 'PixelGetMagentaQuantum',
           'LocaleComponentGenesis', 'UserDefinedKernel',
           'ImageInfo', 'AddNoiseImageChannel', 'Pxr24Compression',
           'GetAuthenticIndexQueue', 'AcquireTimerInfo',
           'SetClientName', 'WriteImages', 'FloodfillMethod',
           'MagickSetGravity', 'ConvexHullKernel',
           'DeprecateEvent', 'BlobWarning',
           'GetPixelViewY', 'NoCompositeOp',
           'YellowQuantum', 'UndefinedSpread',
           'MagickWandGenesis', 'AcquireUniqueSymbolicLink',
           'UndefinedFunction', 'OrderedPosterizeImageChannel',
           'DestroyImageList', 'GetXMLTreeAttributes',
           'UserSpaceOnUse', 'Plane2CylinderDistortion',
           'DiamondKernel', 'WritePolicyRights',
           'TransformRGBImage', 'GetOneVirtualPixel',
           'MagickGetImageRenderingIntent', 'LogComponentGenesis',
           'MagickAdaptiveBlurImage', '_QuantizeInfo',
           'PaintOpaqueImageChannel', '_MimeInfo',
           'NormalizedCrossCorrelationErrorMetric', 'PixelSetBlack',
           'FormatLocaleFileList', 'DrawGetStrokeColor',
           'GravityType', 'BlackVirtualPixelMethod',
           'ExpandedStretch', 'GetLocaleMessage', 'DrawSetClipUnits',
           'MagickResetIterator', 'TransferWandViewMethod',
           'GetNextValueInLinkedList', 'SteganoImage',
           'MagickGammaImageChannel', 'StyleType', '_StringInfo',
           'MagickOpaqueImage', 'NoneDispose',
           'DrawSetTextKerning', 'BartlettFilter',
           'MagickSolarizeImage', 'ResetSplayTreeIterator',
           'MagickGetImageDispose',
           'GetCacheViewStorageClass', 'UnshiftImageList',
           'RelinquishMagickMemory', 'SetCacheViewVirtualPixelMethod',
           'UndefinedNoise', 'MagickSharpenImageChannel',
           'GetImageChannelDistortions', 'CacheView',
           'RegistryComponentGenesis',
           'DrawSetStrokePatternURL', 'AnnotateComponentTerminus',
           'DullPreview', 'ChromaticityInfo', 'SpiffPreview',
           'DrawAnnotation', 'MagickGetImageChannelExtrema',
           'AutoLevelImage', 'GetNumberColors', 'SampleImage',
           'MagickModulateImage', 'SentinelFilter',
           'DrawSetFillColor', 'HSLColorspace', 'ErrorHandler',
           'IsMagickInstantiated', 'SetImagePixels',
           'CloseIntensityMorphology', 'YCbCrColorspace',
           'RightBottomOrientation', 'DespeckleImage',
           'MagickLayerOptions', 'CloneImageProfiles',
           'GetLastValueInLinkedList', 'SetCacheViewStorageClass',
           'DrawPopPattern', 'LevelImage', 'AtopCompositeOp',
           '_StopInfo', 'RemoveImageRegistry', 'ThrowMagickException',
           'MagickDescribeImage', 'MagickVignetteImage',
           'InverseFourierTransformImage', 'InvokeDynamicImageFilter',
           'DrawPathCurveToSmoothRelative', 'GetImageTotalInkDensity',
           'MagickSetImageCompression', 'ResetImageOptions',
           'RGBQuantum', 'ExtraExpandedStretch',
           'MagickBrightnessContrastImage', 'PlasmaImage',
           'MagickPath', 'DeconstructImages',
           'PaintTransparentImage', 'MagickNormalizeImage',
           'CanonicalXMLContent', 'PixelSetRedQuantum',
           'PixelSetBlue', 'PolynomialFunction',
           'MultiplicativeNoiseEvaluateOperator', 'GetImageViewImage',
           'MagickRadialBlurImage', 'ExcerptImage',
           'MagickSetSizeOffset', 'PixelView', 'SetImageProperty',
           'MagickReadImageFile', 'MagickFloodfillPaintImage',
           'PixelGetRed', 'YellowChannel',
           'CompareSplayTreeStringInfo',
           'MagickGetImageChannelKurtosis',
           'InterpolateMagickPixelPacket', 'FileToString',
           'MagickGetPage', 'PaintFloodfillImage', 'PlaneInterlace',
           'ConvolveImageChannel', 'MatteChannel',
           'DrawRectangle', 'LinePrimitive',
           'XGetImportInfo', 'DeleteImageFromList',
           'MagickOpaquePaintImageChannel', 'MagickBooleanType',
           'GetBlobStreamHandler',
           'FormatMagickString', 'GaussJordanElimination',
           'DestroyBlob', 'MagickSetImageColor', '_AffineMatrix',
           'GetVirtualPixelQueue', 'PerceptualIntent',
           'ConstituteComponentGenesis', 'ArcsinFunction',
           'MagickSeparateImageChannel', 'GetImageType',
           'DrawSetStrokeLineCap', 'StretchType',
           'SystemPolicyDomain', 'InterpretSiPrefixValue',
           'MagickGetImageColors', 'DestroyTimerInfo',
           'ClipPathImage', 'NorthEastGravity', 'BlurKernel',
           'OHTAColorspace', 'TypeError', 'MeanEvaluateOperator',
           'DrawPathLineToHorizontalAbsolute', 'UndefinedPrimitive',
           'MagickTransformImageColorspace', 'UndefinedPolicyRights',
           'DrawGetBorderColor', 'CMYColorspace',
           'AnnotateImage', '_MagickPixelPacket',
           'MagickGetImageOrientation',
           'SouthWestGravity',
           'DrawSetFontWeight', 'HaldClutImageChannel',
           'PosterizeImage', 'MagickMorphImages', 'BGRAQuantum',
           'UndefinedQuantum',
           'MagickRandomThresholdImage', 'MagickSetImageClipMask',
           'ConvolveImage', 'GetWandViewMethod',
           'AndEvaluateOperator', 'GetImageMean',
           'LinearLightCompositeOp', 'ImageToBlob', 'SetImageList',
           'GetImageChannelKurtosis',
           'MagickGetImageCompressionQuality', 'BlueQuantum',
           'MagickRandomThresholdImageChannel', 'LocaleInfo',
           'BarycentricColorInterpolate', 'ClassType',
           'DestroyDrawInfo', 'ReplaceCompositeOp',
           'DestroyImagePixels', 'DisassociatedQuantumAlpha',
           'NewImageViewRegion', 'ImpulseNoiseEvaluateOperator',
           'MagickSetImageType', 'MogrifyImage', 'DrawEllipse',
           'ResetImageArtifactIterator', 'IndexChannel',
           'MagickNegateImageChannel', 'NewSplayTree',
           'MagickMontageImage', 'MagickDirectionOptions',
           'ConvertHSBToRGB', 'MagickWand', 'MagickGetImageSize',
           'EndianType', 'MagickGetImageChannelRange',
           'MagickBlueShiftImage', 'SetBlobExempt', 'FloatPixel',
           'RGBAQuantum', 'DrawGetFillAlpha',
           'EncipherImage', 'RemoveImageProperty', 'GetQuantumPixels',
           'ImplodeImage', 'GetImageIndexInList', 'ReadStream',
           'ExplicitFormatType', 'MagickAdaptiveResizeImage',
           'GetImageListLength', 'MagickGetImageProfiles',
           'RandomThresholdImage', 'CbYCrAQuantum',
           'QueryColorCompliance', 'DrawSetTextUnderColor',
           'RemoveImageOption', 'SetStringInfo',
           'MagickEndianOptions', 'LocaleEvent',
           'MagickGetImageChannelMean', 'RandomComponentGenesis',
           'PushImageList', 'DrawGetTextEncoding',
           'GetPixelViewPixels', 'GetNextXMLTreeTag',
           'DrawPathCurveToQuadraticBezierSmoothAbsolute',
           'MagickCoderOptions', 'MagickSetInterpolateMethod',
           'GetPreviousImageInList', 'OpenModule', 'GetDelegateList',
           'PeakSignalToNoiseRatioMetric', 'DestroyPixelWand',
           'AcquireSemaphoreInfo', 'MagickHasPreviousImage',
           'MagickComponentTerminus', 'MagickHaldClutImage',
           'MagickLiquidRescaleImage', 'GetLocaleInfo_',
           'DestroyResampleFilter', 'PrewittKernel', 'ButtCap',
           'MagickSwirlImage', 'SyncChannels',
           'ClipImage', 'PolicyRights', 'IsOpacitySimilar',
           'GetOptimalKernelWidth1D', 'DrawPathStart',
           'DestroyCacheView', 'MagickGetImageChannelDistortions',
           'MagickGetVersion', 'MagickPixelPacket',
           'MagickBooleanOptions', 'DuplexTransferPixelViewIterator',
           'HuePreview', 'ConvertRGBToHWB',
           'ResolutionType', 'UndefinedRegistryType',
           'ErrorException', 'DrawClipPath', 'GravityAdjustGeometry',
           'MagickError', 'UserEvent',
           'PathPrimitive', 'MagickInterpolateOptions',
           'MagickGetHomeURL', 'ThrowException',
           'MagickWriteImageBlob', 'GreenChannel',
           'GetWandViewPixels', 'GetCacheViewAuthenticPixels',
           '_Timer', 'DrawCircle', 'BrightnessPreview',
           'MagickRaiseImage', 'DrawSetStrokeWidth', 'HWBColorspace',
           'ThrowMagickExceptionList',
           'DestroyImageInfo', 'LuminizeCompositeOp', '_TokenInfo',
           '_PrimaryInfo', 'PixelSetColorCount', '_ResampleFilter',
           'PixelGetIteratorExceptionType', 'ClampImageChannel',
           'GetMagicInfo', 'PseudoClass',
           'SeparateImageChannel', '_LinkedListInfo', 'PolaroidImage',
           'PadSpread', 'MagickGetSize', 'FunctionImage',
           'CloneKernelInfo', 'MagickSetOrientation', 'Timer',
           'EmbossImage', 'MagickClutImage',
           'GetClientPath', 'DrawSetFontStyle',
           'AssociatedQuantumAlpha', 'MagickMimeOptions',
           'MagickGetImageMatte', 'MagickGetImageFilename',
           'MotionBlurImage', 'GetConfigureValue',
           'ResourcePolicyDomain', 'ClonePixelWand',
           'SetImageMask', 'MagickGetCopyright', 'ConfigureEvent',
           'MagickColorOptions', 'LeftShiftEvaluateOperator',
           'AlignType', 'CompareImageChannels', 'CompressionType',
           'MemoryResource', 'RadialBlurImage', 'SubstituteString',
           'DuplexTransferImageViewIterator', 'UnityKernel',
           'AcquireCacheViewIndexes', '_ImageAttribute',
           'MagickGetImageRange',
           'RegistryComponentTerminus', 'MagickTypeOptions',
           'IsMagickConflict', 'ColorspaceType', 'GetModuleList',
           'ExtensionPath', 'FormatMagickTime', 'IsGrayImage',
           'ModuleWarning', 'MagickEvaluateImageChannel',
           'AdaptiveThresholdImage', 'PathPolicyDomain',
           'FormatImagePropertyList', 'AutoGammaImageChannel',
           'PosterizeImageChannel', 'SetMonitorHandler',
           'MagickTransparentImage', 'DisposeImages',
           'PostscriptGeometry', 'DitherMethod', 'DrawSkewY',
           'DrawSkewX', 'MagickWriteImage', 'ConfigureInfo',
           'AddPathToXMLTree', 'CompareStringInfo', 'ConfigureError',
           'MagickComposeOptions', 'KernelInfo',
           'OptimizeImageLayers', 'DeleteImageArtifact',
           'DistortImageMethod', 'AffineProjectionDistortion',
           'MagickGetQuantumRange', 'MagickClampImage', '_MagickWand',
           'BackgroundAlphaChannel', 'OptimizeImageLayer',
           'SetQuantumAlphaType', 'ReplaceImageInList',
           'MagickSetAntialias', 'GetMagickInfoList',
           'MagickFilterImage', 'FxImage', 'DrawPushPattern',
           'DrawPathMoveToRelative', 'DrawPathEllipticArcRelative',
           'DrawSetStrokeAntialias', 'MagickGetImage',
           'GetImageViewExtent', 'PerspectiveProjectionDistortion',
           'PixelSetAlphaQuantum', 'TransferPixelViewIterator',
           'SetImageChannelDepth', 'GetMagicName', 'SinusoidFunction',
           'MagickGetImageCompose', 'ItalicStyle',
           'DrawGetStrokeMiterLimit', 'BilevelImageChannel',
           'CbYCrQuantum', 'BlurCompositeOp',
           'SetImageProgressMonitor', 'GetImageRange',
           'MaximumStatistic', 'DrawGetTextDecoration',
           'SetEvaluateOperator', 'PixelSetColor', 'QuantizeImage',
           'DrawArc', 'MagickCompositeImage',
           'GetQuantumExtent', 'InCompositeOp', 'PixelSetMagickColor',
           'UndefinedPath', 'ReadInlineImage', 'LevelColorsImage',
           'PixelGetOpacityQuantum', 'MagickTrue',
           'DestroyPixelWands', 'CompareSplayTreeString',
           '_SegmentInfo', 'AlphaQuantum',
           'MagickGetImageBackgroundColor', 'GetPolicyValue',
           'ResetSplayTree', 'GetMagickResource',
           'MagickGetImageWidth', 'ConfigureComponentTerminus',
           'NoiseType', 'LineJunctionsKernel',
           'ResizeMemoryHandler', 'CorruptImageError',
           'ExtractAlphaChannel', 'MagickClampImageChannel',
           'ExtentImage', 'QueueCacheViewAuthenticPixels',
           'EdgeOutMorphology', 'DstAtopCompositeOp', 'SetImageType',
           'MagentaChannel', 'CopyCompositeOp',
           'ExceptionInfo', 'YUVColorspace', 'MagickGetImageDepth',
           'MagickSetLastIterator', 'GetCacheViewVirtualPixelQueue',
           'SketchImage', 'GetMagickQuantumRange', 'MagickModeImage',
           'MagickGetCompressionQuality', 'MagickEvaluateImage',
           'MagickReadImageBlob', 'SyncAuthenticPixels', 'BlobToFile',
           'GetNextKeyInSplayTree', 'DestroyThresholdMap',
           'RelativeIntent', 'MagickAppendImages',
           'ResetImageAttributeIterator',
           'ConfigureWarning', 'MagickStatisticImage',
           'MagickQuantizeImage', 'MagickRelinquishMemory',
           'MagickAlphaOptions', 'GetEnvironmentValue',
           'MagickFlipImage', 'DestroyPixelIterator',
           'MaskVirtualPixelMethod', 'MinusSrcCompositeOp',
           'IndexAlphaQuantum', 'ListLocaleInfo',
           'MagickCommand', 'PrimaryInfo', 'AllocateImage',
           'MagickEqualizeImage', 'SetImageExtent',
           'GetMagickVersion', 'XMLTreeInfoToXML', 'GetImageProperty',
           'DrawSetTextAntialias', 'CondensedStretch',
           'MonitorFatalError', 'ListColorInfo',
           'StringInfoToHexString', 'ParzenFilter',
           'MagickSparseColorOptions', 'PixelSetOpacityQuantum',
           'PixelGetRedQuantum', 'ParsePageGeometry',
           'UndefinedOrientation', 'ListPolicyInfo',
           'MagickThresholdOptions', 'X11Event',
           'UnlockSemaphoreInfo', 'ResetMethod',
           'PixelSetYellowQuantum', 'GetValueFromHashmap',
           'MagickDeconstructImages', 'MagickGetImageLength',
           'DrawMatte', 'GetLocaleExceptionMessage',
           'MagickUndefinedOptions', 'SemiExpandedStretch',
           'DestroyModuleList', 'MontageImageList',
           'LineInterlace', 'GetDelegateInfo', 'Lanczos2Filter',
           'DeleteImageOption', 'AcquireMagickMemory',
           'SetImageColor', 'LSBEndian', 'Base64Encode',
           'MagickFatalError', 'MagickGetImageColorspace',
           'MagickGetException', 'GetImageViewVirtualPixels',
           'ExecutePolicyRights', 'CompareImages', 'RLECompression',
           'DecipherImage', 'BlobFatalError', 'MagickProfileImage',
           'SetImageProfile', 'DXT5Compression',
           'LightenIntensityCompositeOp', 'AbsoluteErrorMetric',
           'MagickDestroyImage', 'IntegerPixel', 'ListDelegateInfo',
           'ForwardFourierTransformImage', 'MagickStorageOptions',
           'AlphaChannel', 'MagickCommentImage',
           'NoEvents',
           'MagickNormalizeImageChannel',
           'CompositeOperator', 'PingBlob',
           'MagickSetInterlaceScheme', 'CompositeImageCommand',
           'DrawGetFillColor', 'QuantumPixel',
           'MagickSelectiveBlurImageChannel', 'MagickGetFormat',
           'GetPixelViewException', 'ZoomImage', 'MiterJoin',
           'SparseColorImage', 'PixelSetQuantumColor',
           'RemoveNodeByValueFromSplayTree', 'GetImageExtrema',
           'BlendCompositeOp', 'SetImageVirtualPixelMethod',
           'SetImageViewDescription', 'GetThresholdMap',
           'DistortImage', 'SincFilter', 'MagickCombineImages',
           'GetPageGeometry', 'StringRegistryType',
           'MagickConvolveImage', 'DestroyLocaleOptions',
           'MagickSetIteratorIndex',
           'CompositeLayer',
           'MagickSetImageColorspace', 'GetValueFromLinkedList',
           'RightShiftEvaluateOperator', 'DrawGetGravity',
           'DrawPathEllipticArcAbsolute', 'ColorInfo',
           'OpaqueAlphaChannel', 'FuzzyColorCompare',
           'SrcCompositeOp', 'InterpretImageFilename', '_WandView',
           'LogMagickEventList', 'UndefinedPolicyDomain',
           'UndefinedEvaluateOperator', 'MagickGetImageChannelDepth',
           'MergeLayer', 'CMYKAQuantum',
           '_ChannelFeatures', 'MagickGetImageTotalInkDensity',
           'QueryColorname', 'GetRandomKey', 'MagickSetPointsize',
           'LeftAlign', 'MagickConfigureOptions',
           'MagickDeleteImageArtifact', 'PruneTagFromXMLTree',
           'MagickMapImage', 'DrawPeekGraphicWand', 'BlobToImage',
           'DuplicateBlob', 'EuclideanKernel',
           'UndefinedColorInterpolate', 'MagickPolaroidImage',
           'MagickDespeckleImage', 'TransparentImage',
           'Rec601LumaColorspace', 'EdgeImage', 'IsPaletteImage',
           'DuplexTransferPixelViewMethod', 'B44Compression',
           'KaiserFilter', 'GetXMLTreeTag', 'MagickBorderImage',
           'BackgroundDispose', 'MagickQueryConfigureOption',
           'ImageFatalError', 'ValidateColormapIndex',
           'MagickSetImageBorderColor', 'MagickFormatType',
           'ListFiles', 'MSBEndian', 'StatisticImageChannel',
           'MagickChannelOptions', 'JincFilter',
           'MagickAutoGammaImage', 'DrawAffine', 'GrayPadQuantum',
           'LevelizeImage', 'AsynchronousResourceComponentTerminus',
           'DrawSetGravity', 'GetNextValueInHashmap', 'DrawComposite',
           'StoppedTimerState', 'IsImageObject', 'LogInfo',
           'DiskKernel', 'GetImageViewAuthenticIndexes',
           'UndefinedCompression', 'GetBlobError', 'DrawPatternPath',
           'PartitionInterlace', 'PingImages',
           'DrawPathCurveToQuadraticBezierSmoothRelative',
           '_TypeInfo', 'MagickClipPathOptions',
           'MagickCharcoalImage', 'OverCompositeOp',
           'VividLightCompositeOp', 'MagickClutImageChannel',
           'ExpandFilename', 'MagickPosterizeImage',
           'RotateImage', 'GetMimeDescription',
           'GetImageProfile', 'PointPrimitive',
           'MagickStereoImage', 'ChannelThresholdImage',
           'EvenOddRule', 'GetXMLTreeProcessingInstructions',
           'CanonicalPath', 'JPEGCompression',
           'MagickGetExceptionType', 'OctagonalKernel',
           'CloseCacheView', 'CompareImageCommand',
           'MagickSetImageProperty',
           'UndefinedDirection', 'DrawSetBorderColor',
           'RemoveZeroDelayLayers', 'SetGeometryInfo',
           'GradientStatistic', 'IsGlob', 'ImplicitFormatType',
           'HaldClutImage', 'UndefinedAlign',
           'CharcoalDrawingPreview', 'OrderedDitherImageChannel',
           'ListCommandOptions', 'RectangleInfo',
           'DestroyMontageInfo', 'MagickCoreGenesis',
           'QuantizeImages', 'PolicyError', 'RaisePreview',
           'ListTypeInfo', 'MagickCompareImageLayers',
           'OpaquePaintImageChannel', 'PNGInterlace',
           'DrawGetFillOpacity', 'MagickDisplayImage',
           'IsOpaqueImage', 'MagickSetSize', 'DXT3Compression',
           'MagickPingImageBlob', 'GetVirtualPixels',
           'ThresholdPreview', 'ResetStringInfo',
           'MagickResampleImage', 'Ascii85Initialize',
           'DrawGetFontStyle', 'PolicyComponentGenesis',
           'Ascii85Flush', 'AcquireStringInfo', 'MagickToMime',
           'ResetAlphaChannel', 'SemaphoreInfo',
           'RemoveElementFromLinkedList', 'GetImageArtifact',
           'ListMagickInfo', 'ResamplePixelColor', 'MagickFlopImage',
           'DrawEvent', 'SmoothMorphology',
           'ResourceEvent', 'ImportQuantumPixels', 'PolicyWarning',
           'RemoveImageArtifact', 'PinLightCompositeOp',
           'NoDitherMethod', 'GetCacheViewAuthenticPixelQueue',
           'MagickGetImageUnits', 'RemoveFirstImageFromList',
           'SetWandViewDescription', 'MagickGetImageExtrema',
           'BrightnessContrastImageChannel', 'MagickCoalesceImages',
           'SystemCommand', 'ReplaceMethod', 'SetMagickResourceLimit',
           'GetCacheViewColorspace', 'MagickSetImageProgressMonitor',
           'DestroyRandomInfo', 'SetImage', 'BumpmapCompositeOp',
           'CompareHashmapString', 'GetQuantizeInfo',
           'SetStringInfoDatum', 'GetImageListSize',
           'RectangleKernel', 'UndefinedMorphology', 'IsBlobSeekable',
           'MagickSetImageAttribute', 'MinEvaluateOperator',
           'GetUserTime', 'DrawPolyline', 'CloneString',
           'MagickConstituteImage', 'PrimitiveInfo',
           'MagickOffsetType', 'MagickSetImageGravity',
           'SetExceptionInfo', 'VoronoiMorphology',
           'SetImageViewMethod', 'DuplicateImages',
           'GetImageViewIterator', 'ClipPathUnits', 'PointMethod',
           'SetImageInfo', 'CloneImageList', 'ReduceNoisePreview',
           'FormatImageProperty', 'PixelSetCyan',
           'AcquireQuantumMemory', 'MagickShadowImage',
           'SpreadMethod', 'TransparentAlphaChannel',
           'UndefinedPixel', 'GetPathAttributes', 'NewImageList',
           'ClipImagePath', 'GetNextImageArtifact', 'SimilarityImage',
           'XImportInfo', 'DrawClearException', 'GetColorInfo',
           'MagickContrastImage', 'GetImageFromList',
           'PowEvaluateOperator', 'InverseColorInterpolate',
           'PolicyComponentTerminus', 'FlattenImages',
           'ThickenMorphology', 'MagickReadImage', 'ElementReference',
           'NegateImageChannel', 'SetWandViewMethod',
           'TransparentPaintImageChroma', 'MagickGetImageCompression',
           'MagickContrastStretchImage', 'PixelSetLastIteratorRow',
           'GetDrawInfo', 'CbYCrYQuantum', 'ConcatenateMagickString',
           'LinearGradient', 'MagickHasNextImage',
           'UniqueImageColors', 'Group4Compression',
           'EdgeVirtualPixelMethod', 'GetConfigureInfo',
           'MagickForwardFourierTransformImage',
           'CharcoalImage', 'GetMagickRawSupport', 'DrawRotate',
           'OptionFatalError', 'CloneImageOptions', 'LZWEncodeImage',
           'UndefinedStyle',
           'DestroyImageView', 'FilterInterpolatePixel',
           'SwirlPreview', 'CopyOpacityCompositeOp',
           'MagickGetResolution', 'AcquireOneMagickPixel',
           'DrawPathFinish', 'DivideSrcCompositeOp',
           'MagickGetImageFuzz', 'CloneDrawInfo',
           'ColorFloodfillImage', 'OptionError', 'SyncImageList',
           'GetMagickPackageName', 'GetXMLTreeOrdered',
           'GetImageEncoder', 'MagickClipImagePath',
           'NewPixelIterator', 'ThresholdEvaluateOperator',
           'DestroyLinkedList', 'OctagonKernel',
           'MagickGaussianBlurImageChannel', 'GetMagickGeometry',
           'MagickGetImageDelay', 'GetImageReferenceCount',
           'DrawSetFillAlpha', 'AcquireNextImage',
           'CompareClearLayer', '_BlobInfo', 'ContrastStretchImage',
           'StringToList', 'DrawPopClipPath',
           'ChannelFeatures', 'ClearMagickException',
           'AddModulusEvaluateOperator', 'MagickAnnotateImage',
           'MagickGetOrientation', 'UltraExpandedStretch',
           'TransformEvent', '_GeometryInfo',
           'BilinearForwardDistortion', 'GetOptimalKernelWidth2D',
           'MagickRotateImage', 'DrawGetFontResolution',
           'MagickFxImageChannel', 'MagickGetPackageName',
           'LineThroughDecoration', 'MagickPaintFloodfillImage',
           'MagickCompareImages', 'PopImagePixels',
           'UpdateWandViewIterator', 'DelegateWarning',
           'MultiplyCompositeOp', 'MagickGetImageAlphaChannel',
           'DrawGetTextAntialias', 'AcquireResampleFilter',
           'GetColorTuple', 'GaussianBlurImageChannel',
           'ConstantVirtualPixelMethod', 'ShearPreview',
           'OptimizeTransLayer',
           'PixelGetNextIteratorRow', 'MagickAddImage',
           'GetMonitorHandler', 'ExtraCondensedStretch',
           'MagickPaintTransparentImage',
           'GetDelegateCommands', 'MagickResetImagePage',
           'DeleteMagickRegistry', 'InsertValueInLinkedList',
           'DrawGetFillRule', 'CompareImageLayers',
           'FloodfillPaintImage', 'MagickThresholdImage',
           'MogrifyImageInfo', 'PolynomialDistortion',
           'UnsignedQuantumFormat', 'LineCap',
           'MagickPaintOpaqueImage', 'ResetImagePage',
           'SetQuantumScale', 'LinearStretchImage',
           'MagickMotionBlurImage', 'RelinquishMagickResource',
           'GetImageInfo', 'NewXMLTreeTag',
           'MagickGetImageDistortion', 'CacheError', 'TimeResource',
           '_DrawingWand', 'SrcOutCompositeOp',
           'DuplexTransferWandViewMethod', 'MimeComponentGenesis',
           'AcquireUniqueFilename', 'LZWCompression', 'RollPreview',
           'OilPaintImage', 'DXT1Compression',
           'GetImageQuantizeError', 'MagnifyImage', 'TrimImage',
           'PizCompression', 'DrawGetTextUnderColor',
           'GetImageChannelMean', 'RegistryType',
           'GetRandomValue', 'ClonePixelIterator', '_ColorPacket',
           'LogMagickEvent', '_PixelPacket',
           'ExpandFilenames', 'DestroyMemoryHandler',
           'DrawSetStrokeOpacity', 'DilateIntensityMorphology',
           'MagickSetImageAlphaChannel',
           'MagickUnsharpMaskImageChannel',
           'ListMimeInfo', 'FormatLocaleFile', 'GetTypeInfo',
           'MagickClipImage', 'PixelSetBlueQuantum', 'MosaicImages',
           'CloneWandView', 'MagickFilterOptions',
           'ImportImageCommand', 'GetBlobFileHandle',
           'MagickWaveImage', 'SetErrorHandler',
           'SetResampleFilter', 'ImageWarning', 'TailPath',
           'SemaphoreComponentGenesis',
           'AutoLevelImageChannel', 'LinkedListInfo',
           'DefineImageOption', 'DestroyConfigureOptions',
           'PixelGetAlpha', 'GetImageChannelExtrema', 'DisplayImages',
           'UserSpace', 'GetValueFromSplayTree', 'TrueAlphaChannel',
           'MagentaQuantum', 'MagickSetImageWhitePoint',
           'RandomVirtualPixelMethod', 'WavePreview',
           'SetWandViewThreads', 'GetConfigureOption',
           'MagickDrawImage', 'IsImageSimilar',
           'MagickQueryFormats', 'ImpulseNoise', 'MonitorHandler',
           'MinifyImage', 'PixelIteratorGetException',
           'LocaleCompare', 'MagickOrderedPosterizeImage',
           'DrawSetStrokeDashOffset', 'PixelGetExceptionType',
           'BlueChannel', '_ChromaticityInfo',
           'DisplayImageCommand', 'IndexPacket',
           'UndefinedMode', 'NewMagickWandFromImage',
           'CopyYellowCompositeOp', 'LeftTopOrientation',
           'RegisterStaticModules', 'GetConfigureList',
           'MagickGetResource', 'MagickFunctionOptions',
           'FilterFatalError', 'DestroyImageAttributes',
           'VirtualPixelMethod', 'ListThresholdMaps',
           'NormalizeImageChannel', 'UndefinedTimerState',
           'TransposeImage', 'EdgeMorphology', 'WandView',
           'BlobToStringInfo', 'GetImageMagick', 'InterlaceType',
           'AlphaChannelType',
           'MagickAutoLevelImageChannel', 'MagickColorizeImage',
           'IsEventLogging', '_ConfigureInfo',
           'MagickPreviewOptions',
           'RGBPadQuantum', 'QuadraticFilter',
           'BGRQuantum', 'PixelGetOpacity',
           'MatteFloodfillImage', 'MagickSetImageDispose',
           'NewLinkedList', 'UndefinedClass', 'GetStringInfoLength',
           'MagickGetImageProfile', 'DrawError', 'MagickMonitor',
           'DrawGetStrokeWidth',
           'HuffmanDecodeImage', 'MagickWriteImages',
           'SetImageChannels', 'ConfigureComponentGenesis',
           'UndefinedReference', 'PixelGetIteratorException',
           'XServerError',
           'MagickGetImageInterpolateMethod', 'LinkedListToArray',
           'GetMagickEndianSupport', 'StringToken', 'ClearMagickWand',
           'HeadPath', 'MagickPreviousImage', 'DrawGetFontStretch',
           'AnyStretch', 'FrameImage', 'CharPixel',
           'SetMagickPrecision', 'ResetImagePropertyIterator',
           'TrueColorType', 'ClearPixelIterator', 'GetXMLTreeChild',
           'RadialGradient', 'MagickEncipherImage', 'DestroyImages',
           'UnframeMode', 'CloneMagickWand',
           'MagickRecolorImage', 'MagickMaximumImages',
           'TopLeftOrientation', 'MagickGetCompression', 'ModeImage',
           'GetDelegateThreadSupport', 'MagickRemapImage',
           'UndefinedResource', 'PixelResetIterator',
           'UndefinedCap', 'CloneStringInfo', 'UndefinedType',
           'ColorDecisionListImage', 'AcquireMemory', 'NoInterlace',
           'NewWandView', 'FileOpenError',
           'MagickSetImageIterations', 'IsTaintImage',
           'UndefinedLayer', 'GetPixelCachePixels', 'TypeMetric',
           'GetImageChannelStatistics',
           'AcquireCacheView', 'WandFatalError', 'IsSceneGeometry',
           'MagickStripImage', 'HorizontalTileVirtualPixelMethod',
           'QueryMagickColorCompliance', 'MagickEvaluateImages',
           'ResampleFilter', 'MagickSetDepth',
           'ThresholdImage', 'DrawGetFontWeight',
           'DrawSetFontSize', '_RandomInfo', 'MagickDisplayImages',
           'Lanczos2SharpFilter', 'DiagonalsKernel',
           'DrawSetClipPath', 'MagickEnhanceImage', 'HermiteFilter',
           'DisposeLayer',
           'MagickGetImagePixels', 'BGROQuantum',
           'IsPixelWandSimilar', 'SimilarityMetricImage',
           'StaticGravity', 'SetImageOption',
           'LocaleComponentTerminus',
           'LaplacianNoiseEvaluateOperator', 'WarningHandler',
           'MorphologyImageChannel', 'HashStringInfoType',
           'MagickGetInterpolateMethod', 'OptimizeImageTransparency',
           'SetResampleFilterInterpolateMethod', 'FormatStringList',
           'UndefinedCompositeOp', 'MagickQuantizeImages',
           'MapResource', 'MagickColorspaceOptions',
           'ThresholdImageChannel', 'ParseCommandOption',
           'PixelGetMagenta', 'MagickAutoLevelImage',
           'DuplexTransferWandViewIterator', 'CoderEvent',
           'VignetteImage', 'StringInfo', 'UndefinedGravity',
           'DstOverCompositeOp', 'SineEvaluateOperator',
           'DefineImageProperty', 'BottomHatMorphology',
           'ShepardsColorInterpolate', 'ConstituteComponentTerminus',
           'CloneCacheView', 'GetCacheViewChannels', 'ModuleEvent',
           'PixelGetNextRow', 'IsColorSimilar']

########NEW FILE########
__FILENAME__ = test_image
#!/usr/bin/env python
# encoding: utf-8
"""
imsto test

Created by liut on 2013-08-28.
Copyright (c) 2010-2012 liut. All rights reserved.
"""

import os
import imp
imsto = imp.load_module('imsto', *imp.find_module('imsto',[os.path.join(os.path.dirname(__file__), '..')]))
from imsto import *


#@profile
def test():
	filename = 'mold.png'
	im = SimpImage(filename)
	print "format {}, length: {}".format(im.format, len(im.getBlob()) )
	im.format = 'JPEG'
	im.quality = 88
	print "format {}, length: {}".format(im.format, len(im.getBlob()) )
	# im.save('mold_new.jpg')


if __name__ == "__main__":
	test()



########NEW FILE########
__FILENAME__ = test_s3

AccessKey = "AKIAIG5G4NXEKQXUQSUA"
SecretKey = "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"

bucketName = "liut"

@profile
def test_s3_simples3():
	from simples3 import S3Bucket
	s = S3Bucket(bucketName, access_key=AccessKey, secret_key=SecretKey)
	for (key, modify, etag, size) in s.listdir():
		print "%r (%r) is size %r, modified %r" % (key, etag, size, modify)


if __name__ == '__main__':
	
	test_s3_simples3()

########NEW FILE########
__FILENAME__ = test_thumb
#!/usr/bin/env python
# encoding: utf-8
"""
imsto test

Created by liut on 2012-11-28.
Copyright (c) 2010-2012 liut. All rights reserved.
"""

import os
import imp
imsto = imp.load_module('imsto', *imp.find_module('imsto',[os.path.join(os.path.dirname(__file__), '..')]))
from imsto import thumbnail_wand


#@profile
def test():
	filename = 'monalisa.jpg'
	print thumbnail_wand(filename, 160, 160, 'monalisa-s160.jpg')
	print thumbnail_wand(filename, 160, 160, 'monalisa-c160.jpg', mode='c')
	print thumbnail_wand(filename, 160, 160, 'monalisa-w160.jpg', mode='w')
	print thumbnail_wand(filename, 160, 160, 'monalisa-h160.jpg', mode='h')
	print thumbnail_wand(filename, 160, 120, 'monalisa-c160x120.jpg', mode='c')


if __name__ == "__main__":
	test()



########NEW FILE########
__FILENAME__ = test_watermark
#!/usr/bin/env python
# encoding: utf-8
"""
test CompositeImageCommand,ModulateCompositeOp

Created by liut on 2012-11-28.
Copyright (c) 2010-2012 liut. All rights reserved.
"""

import os
#from ctypes import cast,c_char_p
import imp
imsto = imp.load_module('imsto', *imp.find_module('imsto',[os.path.join(os.path.dirname(__file__), '..')]))
from imsto import *

#watermark = 'watermark-white.png'
watermark = 'watermark-color.png'
watermark = 'watermark-strike.png'

def watermark(bgnd, result, overlay=watermark):
	im = SimpImage(bgnd)
	im_w = SimpImage(overlay)
	copy = SimpImage('watermark-copy.png')
	#print im.watermark(im_w, 0.5, position='bottom-right')
	if im.watermark(im_w, 0.5, position='golden', copyright=copy):
		if im.save(result):
			print '{} -> {} ok'.format(bgnd, result)

	del im
	del im_w

watermark('monalisa.jpg', 'monalisa_wm.jpg')
# watermark('1.jpg', '1_wm.jpg')
# watermark('2.jpg', '2_wm.jpg')
# watermark('3.jpg', '3_wm.jpg')
# watermark('4.jpg', '4_wm.jpg')
# watermark('5.jpg', '5_wm.jpg')
# watermark('6_1.jpg', '6_1_wm.jpg')
########NEW FILE########
