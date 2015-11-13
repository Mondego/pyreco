__FILENAME__ = base
import os
import logging
import re

from google.appengine.ext import webapp
from google.appengine.api import memcache

from mako import exceptions
from mako.template import Template
from mako.lookup import TemplateLookup

import simplejson

import shrub


class PrintEnvironmentHandler(webapp.RequestHandler):
	def get(self):
		for name in os.environ.keys():
			self.response.out.write("%s = %s<br />\n" % (name, os.environ[name]))


class BasePage(webapp.RequestHandler):
	"""Base request handler to provide template lookup and rendering"""
	
	def __init__(self):
		super(BasePage, self).__init__()
		self._template_lookup = None
		
	def view_path(self):
		return os.path.join(os.path.dirname(__file__), "..", "views")
		
	@property
	def template_lookup(self):
		if not self._template_lookup:
			self._template_lookup = TemplateLookup(directories=[self.view_path()] + shrub.view_paths(), output_encoding='utf-8')
		return self._template_lookup
		
	def get_template(self, name):
		return self.template_lookup.get_template(name)
		
	def set_content_type(self, content_type):
		self.response.headers['Content-Type'] = content_type
		
	def render(self, name, values, content_type=None, cache_key=None):
		template = self.get_template(name)
		if content_type:
			self.set_content_type(content_type)
			
		try:
			self.render_text(template.render(**values), cache_key=cache_key)
		except:
			self.render_text(exceptions.html_error_template().render())
			
	def render_text(self, text, cache_key=None):
		if cache_key:
		# Cache for 5 minutes
			memcache.add(cache_key, text, 5 * 60)
			
		self.response.out.write(text)
		
	def render_with_cache(self, cache_key, content_type=None):
		data = memcache.get(cache_key)
		if data is not None:
			if content_type: self.set_content_type(content_type)
			self.render_text(data)
			return True
		return False


class BaseResponse(object):
	"""Base response when using a front controller"""
	
	def __init__(self, request_handler):
		self.request_handler = request_handler
		self.request = request_handler.request
		
	def render(self, name, values, content_type=None, cache_key=None):
		self.request_handler.render(name, values, content_type=content_type, cache_key=cache_key)


class JSONResponse(BaseResponse):

	ContentType = "text/javascript; charset=utf-8"
	
	def _wrap_in_callback(self, data, callback):
	
	# Callback function names may only use upper and lowercase alphabetic characters (A-Z, a-z),
	# numbers (0-9), the period (.), the underscore (_)
	
		if not re.match("^[a-zA-Z0-9._]+$", callback):
			raise shrub.ShrubException("InvalidCallback", "Callback contains invalid characters")
			
		return "%s(%s)" % (callback, data)
		
	def render_json(self, value, cache_key=None, callback=None):
		json = simplejson.dumps(value)
		self.request_handler.set_content_type(self.ContentType)
		if callback:
			json = self._wrap_in_callback(json, callback)
		self.request_handler.render_text(json, cache_key=cache_key)
		
	def render_json_from_cache(self, cache_key):
		return self.request_handler.render_with_cache(cache_key, content_type=self.ContentType)

	def render_json_error(self, status_code, error):
		self.request_handler.response.set_status(status_code)
		self.render_json(dict(error=dict(code=error.code, message=error.message)))
		
	def handle(self, response):
		callback = self.request.get("callback", None)
		try:
			self.render_json(response, callback=callback)
		except shrub.ShrubException, e:
			self.render_json_error(500, e)
			


########NEW FILE########
__FILENAME__ = s3
import os
import logging
import urllib
import cgi
import datetime

from google.appengine.ext import webapp
from google.appengine.runtime import DeadlineExceededError

from mako.template import Template
from mako.lookup import TemplateLookup

import shrub.utils
import shrub.gae_utils
from shrub.file import S3File
from shrub.s3 import S3

from app.controllers import base
from app.controllers import tape

from shrub import feeds

class DefaultPage(base.BasePage):
	"""Home page"""

	def get(self):
		search = self.request.get('q')
		if search:
			self.redirect("/" + search)
			return

		self.render("index.mako", dict(title="Shrub / Amazon S3 Proxy"))


class S3Page(base.BasePage):
	"""
  Front controller for all S3 style requests (until I figure out how to do more advanced routing). 
  
  Request should be passed off based on their format or response type.
  """
	
	def _get(self):
		format = self.request.get('format', None)
		max_keys = self.request.get('max-keys')
		delimiter = self.request.get('delimiter', '/')
		marker = self.request.get('marker', None)
		prefix = self.request.get('prefix', None)

		cache_key = self.request.url

		bucket_name, prefix_from_request = shrub.gae_utils.parse_gae_request(self.request)
		if prefix is None:
			prefix = prefix_from_request

		if not bucket_name:
			handler = ErrorResponse(self)
			handler.render_error(404)
			return

		if format == 'id3-json':
			s3file = S3File(bucket_name, prefix_from_request)
			tape.ID3Response(self).load_url(s3file.to_url(), 'json', cache_key=cache_key)
			return

		# Make S3 request
		s3response = S3().list(bucket_name, max_keys, prefix, delimiter, marker)

		# If not 2xx, show friendly error page
		if not s3response.ok:
			handler = ErrorResponse(self)
			handler.handle(s3response)
			return

		# If no format use HTML response
		if not format:
			handler = HTMLResponse(self)
			handler.handle(s3response)
			return

		# If truncated with a request format; return 501
		if s3response.is_truncated:
			handler = ErrorResponse(self)
			handler.render_error(501, "There were too many items ( &gt; %s ) in the current bucket to sort and display." % s3response.max_keys)
			return

		# Get handler for format
		if format == 'rss': handler = RSSResponse(self)
		elif format.startswith('xspf'): handler = tape.XSPFResponse(self)
		elif format == 'tape': handler = tape.TapeResponse(self)
		elif format == 'json': handler = JSONResponse(self)
		elif format == 'error': handler = ErrorResponse(self)
		else:
		# If no handler for a format return error page
			handler = ErrorResponse(self)
			handler.render_error(404, "The requested format parameter is unknown.", title="Not found")
			return

		# Render response with handler
		handler.handle(s3response)

	def get(self):
		try:
			self._get()
		except DeadlineExceededError:
			self.response.clear()
			ErrorResponse(self).render_error(500, "The request couldn't be completed in time. Please try again.")


class HTMLResponse(base.BaseResponse):

	def handle(self, s3response):
		files = s3response.files
		path_components = s3response.path_components()
		path_names = s3response.path_components(url_escape=False)
		path = s3response.path
		warning_message = None

		sort = 'name'
		sort_property = 'key'
		sort_asc = True

		if s3response.is_truncated:
			if self.request.get('s', None) is not None:
				warning_message = 'Because the result was truncated, the sort option was ignored.'
		else:
			sort = self.request.get('s', 'name')
			if sort.endswith(':d'): 
				sort_asc = False
				sort = sort[:-2]
			# Change sort aliases
			if sort == 'date': sort_property = 'last_modified'
			elif sort == 'name': sort_property = 'key'
			elif sort == 'size': sort_property = 'size'

		files.sort(cmp=lambda x, y: shrub.utils.file_comparator(x, y, sort_property, sort_asc))

		# Default url options to pass through to links
		url_options = dict()
		max_keys = self.request.get('max-keys', None)
		if max_keys:
			url_options['max-keys'] = max_keys

		next_page_url_options = url_options.copy()
		next_page_url_options['marker'] = s3response.next_marker
		next_page_url = '/%s/?%s' % (path, shrub.utils.params_to_url(next_page_url_options, True))

		# Render response
		template_values = {
			'title': shrub.utils.url_unescape(path),
			'path_names': path_names,
			'path_components': path_components,
			'path': path,
			'sort': sort,
			'sort_asc': sort_asc,
			'url_options': url_options,
			'next_page_url': next_page_url,
			's3response': s3response,
			'warning_message': warning_message
		}

		self.render("list.mako", template_values)


class JSONResponse(base.JSONResponse):

	def handle(self, s3response):
		super(JSONResponse, self).handle(s3response.data)


class RSSResponse(base.BaseResponse):

	def handle(self, s3response):
		files = s3response.files
		path = s3response.path
		
		rss_items = []
		files.sort(cmp=lambda x, y: shrub.utils.file_comparator(x, y, 'last_modified', False))

		for file in files[:50]:
			rss_items.append(file.to_rss_item())

		pub_date = datetime.datetime.now()
		if len(rss_items) > 0:
			pub_date = rss_items[0].pub_date

		title = u'%s (Shrub)' % path
		link = "http://s3hub.appspot.com/%s" % path

		assigns = dict(title=title, description=u'RSS feed for %s' % s3response.url, items=rss_items, link=link, pub_date=pub_date)
		self.render("rss.mako", assigns, 'text/xml;charset=utf-8')


class ErrorResponse(base.BaseResponse):
	"""Handle standard error response."""

	def render_error(self, status_code, error_message=None, title="Error"):
		self.request_handler.response.set_status(status_code)
		self.request_handler.render("error.mako", dict(title=title, s3url=None, status_code=status_code, message=error_message, path=None))

	def handle(self, s3response):
		title = None
		message = None
		url = s3response.url
		request = self.request
		request_url = request.url if request else None

		status_code = s3response.status_code
		error_message = s3response.message

		if status_code == 403:
			title = 'Permission denied'
			message = 'Shrub does not have permission to access this bucket. Shrub can only act on public buckets.'
		elif status_code == 404:
			title = 'Not found'
			message = 'This bucket or folder was not found. Try verifying that it exists.'
		elif status_code in range(400, 500):
			title = 'Client error'
			message = 'There was an error trying to access S3.'
		elif status_code in range(500, 600):
			title = 'Not available. Please try again.'
			message = 'There was an error trying to access S3. Please try again.'
		else:
			title = 'Unknown error'
			message = 'There was an unknown error.'

		if error_message:
			message += ' (%s)' % error_message

		self.request_handler.response.set_status(status_code)
		self.request_handler.render("error.mako", dict(title=title, s3url=url, status_code=status_code, message=message, request_url=request_url))


########NEW FILE########
__FILENAME__ = tape
import logging

from google.appengine.api import urlfetch

from id3 import id3reader
from id3 import id3data

import shrub.utils
from app.controllers.base import BaseResponse, JSONResponse

class TapeResponse(BaseResponse):

	def handle(self, s3response):
	
		list_url = self.request_handler.request.path_url
		xspf_url = '%s?format=xspfm' % list_url

		tracks = [file.xspf_track for file in s3response.files if file.extension == 'mp3']
		id3_urls = ['%s?format=id3-json' % file.appspot_url for file in s3response.files if file.extension == 'mp3']

		title = 'Mix Tape (%s)' % shrub.utils.url_unescape(s3response.path)
		values = dict(title=title, xspf_url=xspf_url, list_url=list_url, tracks=tracks, id3_urls=id3_urls, s3response=s3response)

		self.render("muxtape.mako", values)


class XSPFResponse(BaseResponse):

	def handle(self, s3response):
		url = s3response.url
		files = s3response.files
		path = s3response.path
		title = shrub.utils.url_unescape(path)

		exts = self.request.get('exts', None)
		extensions = None
		if exts:
			extensions = exts.split(',')

		# Special case for muxtape; Not sure why player can't handle larger param values.
		if self.request.get('format', '') == 'xspfm':
			extensions = ['mp3']

		files.sort(cmp=lambda x, y: shrub.utils.file_comparator(x, y, 'key', True))

		tracks = [file.xspf_track for file in files if not extensions or file.extension in extensions]
		#logging.info("Tracks: %s" % ([str(track) for track in tracks]))

		values = dict(title=title, creator='Shrub', info='http://shrub.appspot.com', location=url, tracks=tracks)

		self.render("xspf.mako", values, 'text/xml; charset=utf-8')


class ID3Response(JSONResponse):

	def load_url(self, url, format='json', cache_key=None):

		if self.render_json_from_cache(cache_key):
			return

		callback = self.request.get("callback", None)

		#logging.info("Loading url: %s" % url)
		fetch_headers = dict(Range='bytes=0-1024')
		response = urlfetch.fetch(url, headers=fetch_headers, allow_truncated=True)

		try:
			data = id3data.ID3Data(response.content)
			id3r = id3reader.Reader(data, only_v2=True)
			
			if not id3r.found:
				self.render_json(dict(error='Not found', url=url))
				return

			values = dict(
				album=id3r.getValue('album'),
				performer=id3r.getValue('performer'),
				title=id3r.getValue('title'),
				track=id3r.getValue('track'),
				year=id3r.getValue('year'),
				isTruncated=id3r.is_truncated,
			)

			if format == 'json':
				self.render_json(values, cache_key=cache_key, callback=callback)

		except id3reader.Id3Error, detail:
			self.render_json(dict(error=str(detail), url=url))


########NEW FILE########
__FILENAME__ = base
import os
import simplejson

def current_version(context):
	return str(os.environ.get('CURRENT_VERSION_ID', 'Unknown'))
	
def to_json(context, value):
	return simplejson.dumps(value)

def shrub_version(context):
	return "1.2.17"
########NEW FILE########
__FILENAME__ = examples
import cgi

def xspf_xml(context):
	return """<playlist version="0">
  <title>m1xes/sub-pop-mix-1</title>
  <creator>Shrub</creator>
  <info>http://shrub.appspot.com</info>
  <location>http://s3.amazonaws.com/m1xes?delimiter=%2F&prefix=sub-pop-mix-1%2F</location>
  <trackList>
    <track>
      <location>http://s3.amazonaws.com/m1xes/sub-pop-mix-1%2F01-Dntel-The_Distance_%28ft._Arthur%26Yu%29.mp3</location>
      <meta rel="type">mp3</meta>
      <title>01-Dntel-The_Distance_(ft._Arthur&Yu)</title>
    </track>
    <track>
      <location>http://s3.amazonaws.com/m1xes/sub-pop-mix-1%2F02-No_Age-Eraser.mp3</location>
      <meta rel="type">mp3</meta>
      <title>02-No_Age-Eraser</title>
    </track>
    ...
	"""

def xspf_slim_player(context, url):
	return """<object id="xspf-slim-player" class="xspf-slim-player" 
  width="400" height="15" 
  type="application/x-shockwave-flash" 
  name="xspf-slim-player" 
  data="/shrub/swf/xspf_player_slim.swf?playlist_url=%s">

  <param name="allowscriptaccess" value="always"/>
</object>""" % (url)

def xspf_slim_player_swf_object(context, url):
	return """var loadXspfSlimPlayer = function() {
  var xspfUrl = "http://shrub.appspot.com/m1xes/sub-pop-mix-1/?format=xspf";
  var flashvars = { };
  var params = { allowscriptaccess: "always" };
  var attributes = { id: "xspf-slim-player", name: "xspf-slim-player", styleclass:"xspf-slim-player" };

  swfobject.embedSWF('/shrub/swf/xspf_player_slim.swf?playlist_url=' + encodeURI(xspfUrl), "xspf-slim-player", "400", "15", "8.0.0", false, flashvars, params, attributes);
};

$(document).ready(loadXspfSlimPlayer);"""
########NEW FILE########
__FILENAME__ = list
def header_link(context, label, name, sort, sort_asc, path):

	icon = ''
	class_ = ''
	sort_attr = name
	# Default to descending for first sort option for date
	sort_dir = ':d' if name == 'date' else ''

	if sort == name:
		if not sort_asc:
			class_ = 'asc'
			sort_dir = ''
			icon = 'bullet_arrow_down.png'
		else:
			class_ = 'desc'
			sort_dir = ':d'
			icon = 'bullet_arrow_up.png'

	context.write('''<th class="sorted %s %s" onclick="document.location.href='/%s/?s=%s'">''' % (class_, name, path, sort_attr))
	context.write('''<a href="/%s/?s=%s%s">%s</a>''' % (path, sort_attr, sort_dir, label))

	if icon: context.write('<img src="/shrub/images/%s"/></th>' % icon)
	return ''

def if_even(context, n, if_label, else_label):
	if n % 2 == 0:
		return if_label
	else:
		return else_label


########NEW FILE########
__FILENAME__ = id3data
from id3 import id3reader

class ID3Data:
  """Behaves like a file so ID3Reader can process data we get from other sources."""  
  
  def __init__(self, content):
    self.content = content
    self.buffer = StringBuffer(content)
  
  def read(self, size):
    return self.buffer.read(size)
  
  def seek(self, offset, whence):
    if whence == 1:
      self.buffer.read(offset)
    if whence == 2:      
      # jump_offset = len(self.content) + offset
      # self.buffer = StringBuffer(self.content)
      # self.buffer.read(jump_offset)
      raise id3reader.Id3Error('Trying to search from the end')
    
  def close(self):
    pass

# To allow our data to be read and seekable we wrap the string in a 
# StringBuffer, defined below
# 
# This was taken from: http://coding.derkeiler.com/Archive/Python/comp.lang.python/2004-06/2524.html

class Deque: 
  """A double-ended queue.""" 
  
  def __init__(self): 
    self.a = [] 
    self.b = [] 
    
  def push_last(self, obj): 
    self.b.append(obj) 
    
  def push_first(self, obj): 
    self.a.append(obj) 
    
  def partition(self): 
    if len(self) > 1: 
      self.a.reverse() 
      all = self.a + self.b 
      n = len(all) / 2 
      self.a = all[:n] 
      self.b = all[n:] 
      self.a.reverse() 
      
  def pop_last(self): 
    if not self.b: self.partition() 
    try: return self.b.pop() 
    except: return self.a.pop() 
    
  def pop_first(self): 
    if not self.a: self.partition() 
    try: return self.a.pop() 
    except: return self.b.pop() 
    
  def __len__(self): 
    return len(self.b) + len(self.a) 
    
    
class StringBuffer(Deque): 
  """A FIFO for characters. Strings can be efficiently 
     appended to the end, and read from the beginning. 
     Example: 
       B = StringBuffer('Hello W') 
       B.append('orld!') 
       print B.read(5) # 'Hello' 
       print B.read() # 'World!' 
  """ 
  
  def __init__(self, s=''): 
    Deque.__init__(self) 
    self.length = 0 
    self.append(s) 
    
  def append(self, s): 
    n = 128 
    for block in [s[i:i+n] for i in range(0,len(s),n)]: 
      self.push_last(block) 
    self.length += len(s) 
    
  def prepend(self, s): 
    n = 128 
    blocks = [s[i:i+n] for i in range(0,len(s),n)] 
    blocks.reverse() 
    for block in blocks: 
      self.push_first(block) 
    self.length += len(s) 
    
  def read(self, n=None): 
    if n == None or n > len(self): n = len(self) 
    destlen = len(self) - n 
    ans = [] 
    while len(self) > destlen: 
      ans += [self.pop_first()] 
      self.length -= len(ans[-1]) 
    ans = ''.join(ans) 
    self.prepend(ans[n:]) 
    ans = ans[:n] 
    return ans 
    
  def peek(self, n=None): 
    ans = self.read(n) 
    self.prepend(ans) 
    return ans 
    
  def __len__(self): return self.length 
  def __str__(self): return self.peek() 
  def __repr__(self): return 'StringBuffer(' + str(self) + ')'
########NEW FILE########
__FILENAME__ = id3reader
""" Read ID3 tags from a file.
    Ned Batchelder, http://nedbatchelder.com/code/modules/id3reader.html
"""

__version__ = '1.53.20070415'    # History at the end of the file.

# ID3 specs: http://www.id3.org/develop.html

import struct, sys, zlib

# These are the text encodings, indexed by the first byte of a text value.
_encodings = ['iso8859-1', 'utf-16', 'utf-16be', 'utf-8']

# Simple pseudo-id's, mapped to their various representations.
# Use these ids with getValue, and you don't need to know what
# version of ID3 the file contains.
_simpleDataMapping = {
    'album':        ('TALB', 'TAL', 'v1album', 'TOAL'),
    'performer':    ('TPE1', 'TP1', 'v1performer', 'TOPE'),
    'title':        ('TIT2', 'TT2', 'v1title'),
    'track':        ('TRCK', 'TRK', 'v1track'),
    'year':         ('TYER', 'TYE', 'v1year'),
    'genre':        ('TCON', 'TCO', 'v1genre'),
    'comment':      ('COMM', 'COM', 'v1comment'),
}

# Provide booleans for older Pythons.
try:
    True, False
except NameError:
    True, False = 1==1, 1==0

# Tracing
_t = False
def _trace(msg):
    print msg

# Coverage
_c = False
_features = {}
def _coverage(feat):
    #if _t: _trace('feature '+feat)
    _features[feat] = _features.setdefault(feat, 0)+1

def _safestr(s):
    """ Get a good string for printing, that won't throw exceptions,
        no matter what's in it.
    """
    try:
        return unicode(s).encode(sys.getdefaultencoding())
    except UnicodeError:
        return '?: '+repr(s)

# Can I just say that I think the whole concept of genres is bogus,
# since they are so subjective?  And the idea of letting someone else pick
# one of these things and then have it affect the categorization of my music
# is extra bogus.  And the list itself is absurd. Polsk Punk?
_genres = [
    # 0-19
    'Blues', 'Classic Rock', 'Country', 'Dance', 'Disco', 'Funk', 'Grunge', 'Hip - Hop', 'Jazz', 'Metal',
    'New Age', 'Oldies', 'Other', 'Pop', 'R&B', 'Rap', 'Reggae', 'Rock', 'Techno', 'Industrial',
    # 20-39
    'Alternative', 'Ska', 'Death Metal', 'Pranks', 'Soundtrack', 'Euro - Techno', 'Ambient', 'Trip - Hop', 'Vocal', 'Jazz + Funk',
    'Fusion', 'Trance', 'Classical', 'Instrumental', 'Acid', 'House', 'Game', 'Sound Clip', 'Gospel', 'Noise',
    # 40-59
    'Alt Rock', 'Bass', 'Soul', 'Punk', 'Space', 'Meditative', 'Instrumental Pop', 'Instrumental Rock', 'Ethnic', 'Gothic',
    'Darkwave', 'Techno - Industrial', 'Electronic', 'Pop - Folk', 'Eurodance', 'Dream', 'Southern Rock', 'Comedy', 'Cult', 'Gangsta Rap',
    # 60-79
    'Top 40', 'Christian Rap', 'Pop / Funk', 'Jungle', 'Native American', 'Cabaret', 'New Wave', 'Psychedelic', 'Rave', 'Showtunes',
    'Trailer', 'Lo - Fi', 'Tribal', 'Acid Punk', 'Acid Jazz', 'Polka', 'Retro', 'Musical', 'Rock & Roll', 'Hard Rock',
    # 80-99
    'Folk', 'Folk / Rock', 'National Folk', 'Swing', 'Fast - Fusion', 'Bebob', 'Latin', 'Revival', 'Celtic', 'Bluegrass',
    'Avantgarde', 'Gothic Rock', 'Progressive Rock', 'Psychedelic Rock', 'Symphonic Rock', 'Slow Rock', 'Big Band', 'Chorus', 'Easy Listening', 'Acoustic',
    # 100-119
    'Humour', 'Speech', 'Chanson', 'Opera', 'Chamber Music', 'Sonata', 'Symphony', 'Booty Bass', 'Primus', 'Porn Groove',
    'Satire', 'Slow Jam', 'Club', 'Tango', 'Samba', 'Folklore', 'Ballad', 'Power Ballad', 'Rhythmic Soul', 'Freestyle',
    # 120-139
    'Duet', 'Punk Rock', 'Drum Solo', 'A Cappella', 'Euro - House', 'Dance Hall', 'Goa', 'Drum & Bass', 'Club - House', 'Hardcore',
    'Terror', 'Indie', 'BritPop', 'Negerpunk', 'Polsk Punk', 'Beat', 'Christian Gangsta Rap', 'Heavy Metal', 'Black Metal', 'Crossover',
    # 140-147
    'Contemporary Christian', 'Christian Rock', 'Merengue', 'Salsa', 'Thrash Metal', 'Anime', 'JPop', 'Synthpop'
    ]

class Id3Error(Exception):
    """ An exception caused by id3reader properly handling a bad ID3 tag.
    """
    pass

class _Header:
    """ Represent the ID3 header in a tag.
    """
    def __init__(self):
        self.majorVersion = 0
        self.revision = 0
        self.flags = 0
        self.size = 0
        self.bUnsynchronized = False
        self.bExperimental = False
        self.bFooter = False

    def __str__(self):
        return str(self.__dict__)

class _Frame:
    """ Represent an ID3 frame in a tag.
    """
    def __init__(self):
        self.id = ''
        self.size = 0
        self.flags = 0
        self.rawData = ''
        self.bTagAlterPreserve = False
        self.bFileAlterPreserve = False
        self.bReadOnly = False
        self.bCompressed = False
        self.bEncrypted = False
        self.bInGroup = False

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)

    def _interpret(self):
        """ Examine self.rawData and create a self.value from it.
        """
        if len(self.rawData) == 0:
            # This is counter to the spec, but seems harmless enough.
            #if _c: _coverage('zero data')
            return

        if self.bCompressed:
            # Decompress the compressed data.
            self.rawData = zlib.decompress(self.rawData)

        if self.id[0] == 'T':
            # Text fields start with T
            encoding = ord(self.rawData[0])
            if 0 <= encoding < len(_encodings):
                #if _c: _coverage('encoding%d' % encoding)
                value = self.rawData[1:].decode(_encodings[encoding])
            else:
                #if _c: _coverage('bad encoding')
                value = self.rawData[1:]
            # Don't let trailing zero bytes fool you.
            if value:
                value = value.strip('\0')
            # The value can actually be a list.
            if '\0' in value:
                value = value.split('\0')
                #if _c: _coverage('textlist')
            self.value = value
        elif self.id[0] == 'W':
            # URL fields start with W
            self.value = self.rawData.strip('\0')
            if self.id == 'WXXX':
                self.value = self.value.split('\0')
        elif self.id == 'CDM':
            # ID3v2.2.1 Compressed Data Metaframe
            if self.rawData[0] == 'z':
                self.rawData = zlib.decompress(self.rawData[5:])
            else:
                #if _c: _coverage('badcdm!')
                raise Id3Error, 'Unknown CDM compression: %02x' % self.rawData[0]
            #@TODO: re-interpret the decompressed frame.

        elif self.id in _simpleDataMapping['comment']:
            # comment field

            # In limited testing a typical comment looks like
            # '\x00XXXID3v1 Comment\x00comment test' so in this
            # case we need to find the second \x00 to know where
            # where we start for a comment.  In case we only find
            # one \x00, lets just start at the beginning for the
            # value
            s = str(self.rawData)

            pos = 0
            count = 0
            while pos < len(s) and count < 2:
                if ord(s[pos]) == 0:
                    count = count + 1
                pos = pos + 1
            if count < 2:
                pos = 1

            if pos > 0 and pos < len(s):
                s = s[pos:]
                if ord(s[-1]) == 0:
                    s = s[:-1]

            self.value = s

class Reader:
    """ An ID3 reader.
        Create one on a file object, and then use getValue('TIT2') (for example)
        to pull values.
    """
    def __init__(self, file, only_v2=False):
        """ Create a reader from a file or filename. """
        self.file = file
        self.header = None
        self.frames = {}
        self.allFrames = []
        self.bytesLeft = 0
        self.padbytes = ''
        self.is_truncated = False
        self.found = False

        bCloseFile = False
        # If self.file is a string of some sort, then open it to get a file.
        if isinstance(self.file, (type(''), type(u''))):
            self.file = open(self.file, 'rb')
            bCloseFile = True

        self._readId3(only_v2)

        if bCloseFile:
            self.file.close()

    def _readBytes(self, num, desc=''):
        """ Read some bytes from the file.
            This method implements the "unsynchronization" scheme,
            where 0xFF bytes may have had 0x00 bytes stuffed after
            them.  These zero bytes have to be removed transparently.
        """
        #if _t: _trace("ask %d (%s)" % (num,desc))
        if num > self.bytesLeft:
            #if _c: _coverage('long!')
            raise Id3Error, 'Long read (%s): (%d > %d)' % (desc, num, self.bytesLeft)
        bytes = self.file.read(num)
        self.bytesLeft -= num

        if len(bytes) < num:
            #if _t: _trace("short read with %d left, %d total" % (self.bytesLeft, self.header.size))
            #if _c: _coverage('short!')
            #raise Id3Error, 'Short read (%s): (%d < %d)' % (desc, len(bytes), num)
            self.is_truncated = True
            return bytes

        if self.header.bUnsynchronized:
            nUnsync = 0
            i = 0
            while True:
                i = bytes.find('\xFF\x00', i)
                if i == -1:
                    break
                #if _t: _trace("unsync at %d" % (i+1))
                #if _c: _coverage('unsyncbyte')
                nUnsync += 1
                # This is a stuffed byte to remove
                bytes = bytes[:i+1] + bytes[i+2:]
                # Have to read one more byte from the file to adjust
                bytes += self.file.read(1)
                self.bytesLeft -= 1
                i += 1
            #if _t: _trace("unsync'ed %d" % (nUnsync))

        return bytes

    def _unreadBytes(self, num):
        self.file.seek(-num, 1)
        self.bytesLeft += num

    def _getSyncSafeInt(self, bytes):
        assert len(bytes) == 4
        if type(bytes) == type(''):
            bytes = [ ord(c) for c in bytes ]
        return (bytes[0] << 21) + (bytes[1] << 14) + (bytes[2] << 7) + bytes[3]

    def _getInteger(self, bytes):
        i = 0;
        if type(bytes) == type(''):
            bytes = [ ord(c) for c in bytes ]
        for b in bytes:
            i = i*256+b
        return i

    def _addV1Frame(self, id, rawData):
        if id == 'v1genre':
            assert len(rawData) == 1
            nGenre = ord(rawData)
            try:
                value = _genres[nGenre]
            except IndexError:
                value = "(%d)" % nGenre
        else:
            value = rawData.strip(' \t\r\n').split('\0')[0]
        if value:
            frame = _Frame()
            frame.id = id
            frame.rawData = rawData
            frame.value = value
            self.frames[id] = frame
            self.allFrames.append(frame)

    def _pass(self):
        """ Do nothing, for when we need to plug in a no-op function.
        """
        pass

    def _readId3(self, only_v2=False):
        header = self.file.read(10)
        if len(header) < 10:
            return
        hstuff = struct.unpack('!3sBBBBBBB', header)
        if hstuff[0] != "ID3":
            if only_v2: return
          
            # Doesn't look like an ID3v2 tag,
            # Try reading an ID3v1 tag.
            self._readId3v1()
            return

        self.found = True
        self.header = _Header()
        self.header.majorVersion = hstuff[1]
        self.header.revision = hstuff[2]
        self.header.flags = hstuff[3]
        self.header.size = self._getSyncSafeInt(hstuff[4:8])

        self.bytesLeft = self.header.size

        self._readExtHeader = self._pass

        if self.header.majorVersion == 2:
            #if _c: _coverage('id3v2.2.%d' % self.header.revision)
            self._readFrame = self._readFrame_rev2
        elif self.header.majorVersion == 3:
            #if _c: _coverage('id3v2.3.%d' % self.header.revision)
            self._readFrame = self._readFrame_rev3
        elif self.header.majorVersion == 4:
            #if _c: _coverage('id3v2.4.%d' % self.header.revision)
            self._readFrame = self._readFrame_rev4
        else:
            #if _c: _coverage('badmajor!')
            raise Id3Error, "Unsupported major version: %d" % self.header.majorVersion

        # Interpret the flags
        self._interpretFlags()

        # Read any extended header
        self._readExtHeader()

        # Read the frames
        while self.bytesLeft > 0:
            frame = self._readFrame()
            if frame:
                frame._interpret()
                self.frames[frame.id] = frame
                self.allFrames.append(frame)
            else:
                #if _c: _coverage('padding')
                break

    def _interpretFlags(self):
        """ Interpret ID3v2.x flags.
        """
        if self.header.flags & 0x80:
            self.header.bUnsynchronized = True
            #if _c: _coverage('unsynctag')

        if self.header.majorVersion == 2:
            if self.header.flags & 0x40:
                #if _c: _coverage('compressed')
                # "Since no compression scheme has been decided yet,
                # the ID3 decoder (for now) should just ignore the entire
                # tag if the compression bit is set."
                self.header.bCompressed = True

        if self.header.majorVersion >= 3:
            if self.header.flags & 0x40:
                #if _c: _coverage('extheader')
                if self.header.majorVersion == 3:
                    self._readExtHeader = self._readExtHeader_rev3
                else:
                    self._readExtHeader = self._readExtHeader_rev4
            if self.header.flags & 0x20:
                #if _c: _coverage('experimental')
                self.header.bExperimental = True

        if self.header.majorVersion >= 4:
            if self.header.flags & 0x10:
                #if _c: _coverage('footer')
                self.header.bFooter = True

    def _readExtHeader_rev3(self):
        """ Read the ID3v2.3 extended header.
        """
        # We don't interpret this yet, just eat the bytes.
        size = self._getInteger(self._readBytes(4, 'rev3ehlen'))
        self._readBytes(size, 'rev3ehdata')

    def _readExtHeader_rev4(self):
        """ Read the ID3v2.4 extended header.
        """
        # We don't interpret this yet, just eat the bytes.
        size = self._getSyncSafeInt(self._readBytes(4, 'rev4ehlen'))
        self._readBytes(size-4, 'rev4ehdata')

    def _readId3v1(self):
        """ Read the ID3v1 tag.
            spec: http://www.id3.org/id3v1.html
        """
        self.file.seek(-128, 2)
        tag = self.file.read(128)
        if len(tag) != 128:
            return
        if tag[0:3] != 'TAG':
            return
        self.found = True
        self.header = _Header()
        self.header.majorVersion = 1
        self.header.revision = 0

        self._addV1Frame('v1title', tag[3:33])
        self._addV1Frame('v1performer', tag[33:63])
        self._addV1Frame('v1album', tag[63:93])
        self._addV1Frame('v1year', tag[93:97])
        self._addV1Frame('v1comment', tag[97:127])
        self._addV1Frame('v1genre', tag[127])
        if tag[125] == '\0' and tag[126] != '\0':
            #if _c: _coverage('id3v1.1')
            self.header.revision = 1
            self._addV1Frame('v1track', str(ord(tag[126])))
        else:
            #if _c: _coverage('id3v1.0')
            pass
        return

    _validIdChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

    def _isValidId(self, id):
        """ Determine if the id bytes make a valid ID3 id.
        """
        for c in id:
            if not c in self._validIdChars:
                #if _c: _coverage('bad id')
                return False
        #if _c: _coverage('id '+id)
        return True

    def _readFrame_rev2(self):
        """ Read a frame for ID3v2.2: three-byte ids and lengths.
            spec: http://www.id3.org/id3v2-00.txt
        """
        if self.bytesLeft < 6:
            return None
        id = self._readBytes(3, 'rev2id')
        if len(id) < 3 or not self._isValidId(id):
            self._unreadBytes(len(id))
            return None
        hstuff = struct.unpack('!BBB', self._readBytes(3, 'rev2len'))
        frame = _Frame()
        frame.id = id
        frame.size = self._getInteger(hstuff[0:3])
        frame.rawData = self._readBytes(frame.size, 'rev2data')
        return frame

    def _readFrame_rev3(self):
        """ Read a frame for ID3v2.3: four-byte ids and lengths.
        """
        if self.bytesLeft < 10:
            return None
        id = self._readBytes(4,'rev3id')
        if len(id) < 4 or not self._isValidId(id):
            self._unreadBytes(len(id))
            return None
        hstuff = struct.unpack('!BBBBh', self._readBytes(6,'rev3head'))
        frame = _Frame()
        frame.id = id
        frame.size = self._getInteger(hstuff[0:4])
        cbData = frame.size
        frame.flags = hstuff[4]
        #if _t: _trace('flags = %x' % frame.flags)
        frame.bTagAlterPreserve = (frame.flags & 0x8000 != 0)
        frame.bFileAlterPreserve = (frame.flags & 0x4000 != 0)
        frame.bReadOnly = (frame.flags & 0x2000 != 0)
        frame.bCompressed = (frame.flags & 0x0080 != 0)
        if frame.bCompressed:
            frame.decompressedSize = self._getInteger(self._readBytes(4, 'decompsize'))
            cbData -= 4
            #if _c: _coverage('compress')
        frame.bEncrypted = (frame.flags & 0x0040 != 0)
        if frame.bEncrypted:
            frame.encryptionMethod = self._readBytes(1, 'encrmethod')
            cbData -= 1
            #if _c: _coverage('encrypt')
        frame.bInGroup = (frame.flags & 0x0020 != 0)
        if frame.bInGroup:
            frame.groupid = self._readBytes(1, 'groupid')
            cbData -= 1
            #if _c: _coverage('groupid')

        frame.rawData = self._readBytes(cbData, 'rev3data')
        return frame

    def _readFrame_rev4(self):
        """ Read a frame for ID3v2.4: four-byte ids and lengths.
        """
        if self.bytesLeft < 10:
            return None
        id = self._readBytes(4,'rev4id')
        if len(id) < 4 or not self._isValidId(id):
            self._unreadBytes(len(id))
            return None
        hstuff = struct.unpack('!BBBBh', self._readBytes(6,'rev4head'))
        frame = _Frame()
        frame.id = id
        frame.size = self._getSyncSafeInt(hstuff[0:4])
        cbData = frame.size
        frame.flags = hstuff[4]
        frame.bTagAlterPreserve = (frame.flags & 0x4000 != 0)
        frame.bFileAlterPreserve = (frame.flags & 0x2000 != 0)
        frame.bReadOnly = (frame.flags & 0x1000 != 0)
        frame.bInGroup = (frame.flags & 0x0040 != 0)
        if frame.bInGroup:
            frame.groupid = self._readBytes(1, 'groupid')
            cbData -= 1
            #if _c: _coverage('groupid')

        frame.bCompressed = (frame.flags & 0x0008 != 0)
        if frame.bCompressed:
            #if _c: _coverage('compress')
            pass
        frame.bEncrypted = (frame.flags & 0x0004 != 0)
        if frame.bEncrypted:
            frame.encryptionMethod = self._readBytes(1, 'encrmethod')
            cbData -= 1
            #if _c: _coverage('encrypt')
        frame.bUnsynchronized = (frame.flags & 0x0002 != 0)
        if frame.bUnsynchronized:
            #if _c: _coverage('unsyncframe')
            pass
        if frame.flags & 0x0001:
            frame.datalen = self._getSyncSafeInt(self._readBytes(4, 'datalen'))
            cbData -= 4
            #if _c: _coverage('datalenindic')

        frame.rawData = self._readBytes(cbData, 'rev3data')

        return frame

    def getValue(self, id):
        """ Return the value for an ID3 tag id, or for a
            convenience label ('title', 'performer', ...),
            or return None if there is no such value.
        """
        if self.frames.has_key(id):
            if hasattr(self.frames[id], 'value'):
                return self.frames[id].value
        if _simpleDataMapping.has_key(id):
            for id2 in _simpleDataMapping[id]:
                v = self.getValue(id2)
                if v:
                    return v
        return None

    def getRawData(self, id):
        if self.frames.has_key(id):
            return self.frames[id].rawData
        return None

    def dump(self):
        import pprint
        print "Header:"
        print self.header
        print "Frames:"
        for fr in self.allFrames:
            if len(fr.rawData) > 30:
                fr.rawData = fr.rawData[:30]
        pprint.pprint(self.allFrames)
        for fr in self.allFrames:
            if hasattr(fr, 'value'):
                print '%s: %s' % (fr.id, _safestr(fr.value))
            else:
                print '%s= %s' % (fr.id, _safestr(fr.rawData))
        for label in _simpleDataMapping.keys():
            v = self.getValue(label)
            if v:
                print 'Label %s: %s' % (label, _safestr(v))

    def dumpCoverage(self):
        feats = _features.keys()
        feats.sort()
        for feat in feats:
            print "Feature %-12s: %d" % (feat, _features[feat])

if __name__ == '__main__':
    if len(sys.argv) < 2 or '-?' in sys.argv:
        print "Give me a filename"
    else:
        id3 = Reader(sys.argv[1])
        id3.dump()
        #if _c: id3.dumpCoverage()

# History:
# 20040104: Created.
# 20040105: Two bugs: didn't read v1 properly, and didn't like empty strings in values.
#
# 20040109: Properly reads v2.3 properly (4-byte lens, but not synchsafe)
#           Handles unsynchronized tags properly.
#
# 20040110: Total length was wrong for unsynchronized tags.
#           Treat input filename better so path module can be used.
#           Frame ids are more closely scrutinized for validity.
#           Errors are now thrown as our own exception.
#           Pad bytes aren't retained any more.
#           Frame.value is not set if there is no interpretation performed.
#
# 20040111: Tracing and code coverage more formalized.
#           Exceptions are now all Id3Error.
#           Zero-length data in frames is handled pleasantly.
#           Compressed frames are decompressed.
#           Extended headers are read (but uninterpreted).
#           Non-zero pad bytes are handled.
#           Frame flags are read and interpreted.
#           W*** frames are interpreted.
#           Multi-string frames set .value to a list of strings.
#
# 20040113: Strip all trailing zero bytes from text strings.
#           If we opened the file, we should close the file.
#
# 20040205: Do a better job printing strings without throwing.
#           Support genre information, even if it is stupid.
#
# 20040913: When dumping strings, be more robust when trying to print
#               non-character data. Thanks to Duane Harkness for the fix.
#
# 20061230: Fix ommission of self. in a few places.
#
# 20070415: Extended headers in ID3v2.4 weren't skipped properly, throwing
#               everything out of whack.
#           Be more generous about finding album and performer names in the tag.

########NEW FILE########
__FILENAME__ = iso8601
"""ISO 8601 date time string parsing

Basic usage:
>>> import iso8601
>>> iso8601.parse_date("2007-01-25T12:00:00Z")
datetime.datetime(2007, 1, 25, 12, 0, tzinfo=<iso8601.iso8601.Utc ...>)
>>>

"""

from datetime import datetime, timedelta, tzinfo
import re

__all__ = ["parse_date", "ParseError"]

# Adapted from http://delete.me.uk/2005/03/iso8601.html
ISO8601_REGEX = re.compile(r"(?P<year>[0-9]{4})(-(?P<month>[0-9]{1,2})(-(?P<day>[0-9]{1,2})"
    r"((?P<separator>.)(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2})(:(?P<second>[0-9]{2})(\.(?P<fraction>[0-9]+))?)?"
    r"(?P<timezone>Z|(([-+])([0-9]{2}):([0-9]{2})))?)?)?)?"
)
TIMEZONE_REGEX = re.compile("(?P<prefix>[+-])(?P<hours>[0-9]{2}).(?P<minutes>[0-9]{2})")

class ParseError(Exception):
    """Raised when there is a problem parsing a date string"""

# Yoinked from python docs
ZERO = timedelta(0)
class Utc(tzinfo):
    """UTC
    
    """
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO
UTC = Utc()

class FixedOffset(tzinfo):
    """Fixed offset in hours and minutes from UTC
    
    """
    def __init__(self, offset_hours, offset_minutes, name):
        self.__offset = timedelta(hours=offset_hours, minutes=offset_minutes)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO
    
    def __repr__(self):
        return "<FixedOffset %r>" % self.__name

def parse_timezone(tzstring, default_timezone=UTC):
    """Parses ISO 8601 time zone specs into tzinfo offsets
    
    """
    if tzstring == "Z":
        return default_timezone
    # This isn't strictly correct, but it's common to encounter dates without
    # timezones so I'll assume the default (which defaults to UTC).
    # Addresses issue 4.
    if tzstring is None:
        return default_timezone
    m = TIMEZONE_REGEX.match(tzstring)
    prefix, hours, minutes = m.groups()
    hours, minutes = int(hours), int(minutes)
    if prefix == "-":
        hours = -hours
        minutes = -minutes
    return FixedOffset(hours, minutes, tzstring)

def parse_date(datestring, default_timezone=UTC):
    """Parses ISO 8601 dates into datetime objects
    
    The timezone is parsed from the date string. However it is quite common to
    have dates without a timezone (not strictly correct). In this case the
    default timezone specified in default_timezone is used. This is UTC by
    default.
    """
    if not isinstance(datestring, basestring):
        raise ParseError("Expecting a string %r" % datestring)
    m = ISO8601_REGEX.match(datestring)
    if not m:
        raise ParseError("Unable to parse date string %r" % datestring)
    groups = m.groupdict()
    tz = parse_timezone(groups["timezone"], default_timezone=default_timezone)
    if groups["fraction"] is None:
        groups["fraction"] = 0
    else:
        groups["fraction"] = int(float("0.%s" % groups["fraction"]) * 1e6)
    return datetime(int(groups["year"]), int(groups["month"]), int(groups["day"]),
        int(groups["hour"]), int(groups["minute"]), int(groups["second"]),
        int(groups["fraction"]), tz)

########NEW FILE########
__FILENAME__ = test_iso8601
import iso8601

def test_iso8601_regex():
    assert iso8601.ISO8601_REGEX.match("2006-10-11T00:14:33Z")

def test_timezone_regex():
    assert iso8601.TIMEZONE_REGEX.match("+01:00")
    assert iso8601.TIMEZONE_REGEX.match("+00:00")
    assert iso8601.TIMEZONE_REGEX.match("+01:20")
    assert iso8601.TIMEZONE_REGEX.match("-01:00")

def test_parse_date():
    d = iso8601.parse_date("2006-10-20T15:34:56Z")
    assert d.year == 2006
    assert d.month == 10
    assert d.day == 20
    assert d.hour == 15
    assert d.minute == 34
    assert d.second == 56
    assert d.tzinfo == iso8601.UTC

def test_parse_date_fraction():
    d = iso8601.parse_date("2006-10-20T15:34:56.123Z")
    assert d.year == 2006
    assert d.month == 10
    assert d.day == 20
    assert d.hour == 15
    assert d.minute == 34
    assert d.second == 56
    assert d.microsecond == 123000
    assert d.tzinfo == iso8601.UTC

def test_parse_date_fraction_2():
    """From bug 6
    
    """
    d = iso8601.parse_date("2007-5-7T11:43:55.328Z'")
    assert d.year == 2007
    assert d.month == 5
    assert d.day == 7
    assert d.hour == 11
    assert d.minute == 43
    assert d.second == 55
    assert d.microsecond == 328000
    assert d.tzinfo == iso8601.UTC

def test_parse_date_tz():
    d = iso8601.parse_date("2006-10-20T15:34:56.123+02:30")
    assert d.year == 2006
    assert d.month == 10
    assert d.day == 20
    assert d.hour == 15
    assert d.minute == 34
    assert d.second == 56
    assert d.microsecond == 123000
    assert d.tzinfo.tzname(None) == "+02:30"
    offset = d.tzinfo.utcoffset(None)
    assert offset.days == 0
    assert offset.seconds == 60 * 60 * 2.5

def test_parse_invalid_date():
    try:
        iso8601.parse_date(None)
    except iso8601.ParseError:
        pass
    else:
        assert 1 == 2

def test_parse_invalid_date2():
    try:
        iso8601.parse_date("23")
    except iso8601.ParseError:
        pass
    else:
        assert 1 == 2

def test_parse_no_timezone():
    """issue 4 - Handle datetime string without timezone
    
    This tests what happens when you parse a date with no timezone. While not
    strictly correct this is quite common. I'll assume UTC for the time zone
    in this case.
    """
    d = iso8601.parse_date("2007-01-01T08:00:00")
    assert d.year == 2007
    assert d.month == 1
    assert d.day == 1
    assert d.hour == 8
    assert d.minute == 0
    assert d.second == 0
    assert d.microsecond == 0
    assert d.tzinfo == iso8601.UTC

def test_parse_no_timezone_different_default():
    tz = iso8601.FixedOffset(2, 0, "test offset")
    d = iso8601.parse_date("2007-01-01T08:00:00", default_timezone=tz)
    assert d.tzinfo == tz

def test_space_separator():
    """Handle a separator other than T
    
    """
    d = iso8601.parse_date("2007-06-23 06:40:34.00Z")
    assert d.year == 2007
    assert d.month == 6
    assert d.day == 23
    assert d.hour == 6
    assert d.minute == 40
    assert d.second == 34
    assert d.microsecond == 0
    assert d.tzinfo == iso8601.UTC

########NEW FILE########
__FILENAME__ = ast
# ast.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""utilities for analyzing expressions and blocks of Python code, as well as generating Python from AST nodes"""

from mako import exceptions, pyparser, util
import re

class PythonCode(object):
    """represents information about a string containing Python code"""
    def __init__(self, code, **exception_kwargs):
        self.code = code
        
        # represents all identifiers which are assigned to at some point in the code
        self.declared_identifiers = util.Set()
        
        # represents all identifiers which are referenced before their assignment, if any
        self.undeclared_identifiers = util.Set()
        
        # note that an identifier can be in both the undeclared and declared lists.

        # using AST to parse instead of using code.co_varnames, code.co_names has several advantages:
        # - we can locate an identifier as "undeclared" even if its declared later in the same block of code
        # - AST is less likely to break with version changes (for example, the behavior of co_names changed a little bit
        # in python version 2.5)
        if isinstance(code, basestring):
            expr = pyparser.parse(code.lstrip(), "exec", **exception_kwargs)
        else:
            expr = code

        f = pyparser.FindIdentifiers(self, **exception_kwargs)
        f.visit(expr)

class ArgumentList(object):
    """parses a fragment of code as a comma-separated list of expressions"""
    def __init__(self, code, **exception_kwargs):
        self.codeargs = []
        self.args = []
        self.declared_identifiers = util.Set()
        self.undeclared_identifiers = util.Set()
        if isinstance(code, basestring):
            if re.match(r"\S", code) and not re.match(r",\s*$", code):
                # if theres text and no trailing comma, insure its parsed
                # as a tuple by adding a trailing comma
                code  += ","
            expr = pyparser.parse(code, "exec", **exception_kwargs)
        else:
            expr = code

        f = pyparser.FindTuple(self, PythonCode, **exception_kwargs)
        f.visit(expr)
        
class PythonFragment(PythonCode):
    """extends PythonCode to provide identifier lookups in partial control statements
    
    e.g. 
        for x in 5:
        elif y==9:
        except (MyException, e):
    etc.
    """
    def __init__(self, code, **exception_kwargs):
        m = re.match(r'^(\w+)(?:\s+(.*?))?:\s*(#|$)', code.strip(), re.S)
        if not m:
            raise exceptions.CompileException("Fragment '%s' is not a partial control statement" % code, **exception_kwargs)
        if m.group(3):
            code = code[:m.start(3)]
        (keyword, expr) = m.group(1,2)
        if keyword in ['for','if', 'while']:
            code = code + "pass"
        elif keyword == 'try':
            code = code + "pass\nexcept:pass"
        elif keyword == 'elif' or keyword == 'else':
            code = "if False:pass\n" + code + "pass"
        elif keyword == 'except':
            code = "try:pass\n" + code + "pass"
        else:
            raise exceptions.CompileException("Unsupported control keyword: '%s'" % keyword, **exception_kwargs)
        super(PythonFragment, self).__init__(code, **exception_kwargs)
        
        
class FunctionDecl(object):
    """function declaration"""
    def __init__(self, code, allow_kwargs=True, **exception_kwargs):
        self.code = code
        expr = pyparser.parse(code, "exec", **exception_kwargs)
                
        f = pyparser.ParseFunc(self, **exception_kwargs)
        f.visit(expr)
        if not hasattr(self, 'funcname'):
            raise exceptions.CompileException("Code '%s' is not a function declaration" % code, **exception_kwargs)
        if not allow_kwargs and self.kwargs:
            raise exceptions.CompileException("'**%s' keyword argument not allowed here" % self.argnames[-1], **exception_kwargs)
            
    def get_argument_expressions(self, include_defaults=True):
        """return the argument declarations of this FunctionDecl as a printable list."""
        namedecls = []
        defaults = [d for d in self.defaults]
        kwargs = self.kwargs
        varargs = self.varargs
        argnames = [f for f in self.argnames]
        argnames.reverse()
        for arg in argnames:
            default = None
            if kwargs:
                arg = "**" + arg
                kwargs = False
            elif varargs:
                arg = "*" + arg
                varargs = False
            else:
                default = len(defaults) and defaults.pop() or None
            if include_defaults and default:
                namedecls.insert(0, "%s=%s" % (arg, pyparser.ExpressionGenerator(default).value()))
            else:
                namedecls.insert(0, arg)
        return namedecls

class FunctionArgs(FunctionDecl):
    """the argument portion of a function declaration"""
    def __init__(self, code, **kwargs):
        super(FunctionArgs, self).__init__("def ANON(%s):pass" % code, **kwargs)

########NEW FILE########
__FILENAME__ = cache
from mako import exceptions

try:
    import beaker.container as container
    import beaker.exceptions
    clsmap = {
        'memory':container.MemoryContainer,
        'dbm':container.DBMContainer,
        'file':container.FileContainer,
    }
    try:
        import beaker.ext.memcached as memcached
        # XXX HACK: Python 2.3 under some circumstances will import this module
        #           even though there's no memcached. This ensures its really
        #           there before adding it.
        if hasattr(memcached, 'MemcachedContainer'):
            clsmap['memcached'] = memcached.MemcachedContainer
    except beaker.exceptions.BeakerException:
        pass
except ImportError:
    container = None
    clsmap = {}

class Cache(object):
    def __init__(self, id, starttime, **kwargs):
        self.id = id
        self.starttime = starttime
        if container is not None:
            self.context = container.ContainerContext()
        self._containers = {}
        self.kwargs = kwargs
    def put(self, key, value, type='memory', **kwargs):
        self._get_container(key, type, **kwargs).set_value(value)
    def get(self, key, type='memory', **kwargs):
        return self._get_container(key, type, **kwargs).get_value()
    def _get_container(self, key, type, **kwargs):
        if not container:
            raise exceptions.RuntimeException("the Beaker package is required to use cache functionality.")
        kw = self.kwargs.copy()
        kw.update(kwargs)
        return clsmap[type](key, self.context, self.id, starttime=self.starttime, **kw)
    

########NEW FILE########
__FILENAME__ = codegen
# codegen.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""provides functionality for rendering a parsetree constructing into module source code."""

import time
import re
from mako.pygen import PythonPrinter
from mako import util, ast, parsetree, filters

MAGIC_NUMBER = 4


def compile(node, uri, filename=None, default_filters=None, buffer_filters=None, imports=None, source_encoding=None, generate_unicode=True):
    """generate module source code given a parsetree node, uri, and optional source filename"""

    buf = util.FastEncodingBuffer(unicode=generate_unicode)

    printer = PythonPrinter(buf)
    _GenerateRenderMethod(printer, _CompileContext(uri, filename, default_filters, buffer_filters, imports, source_encoding, generate_unicode), node)
    return buf.getvalue()

class _CompileContext(object):
    def __init__(self, uri, filename, default_filters, buffer_filters, imports, source_encoding, generate_unicode):
        self.uri = uri
        self.filename = filename
        self.default_filters = default_filters
        self.buffer_filters = buffer_filters
        self.imports = imports
        self.source_encoding = source_encoding
        self.generate_unicode = generate_unicode
        
class _GenerateRenderMethod(object):
    """a template visitor object which generates the full module source for a template."""
    def __init__(self, printer, compiler, node):
        self.printer = printer
        self.last_source_line = -1
        self.compiler = compiler
        self.node = node
        self.identifier_stack = [None]
        
        self.in_def = isinstance(node, parsetree.DefTag)

        if self.in_def:
            name = "render_" + node.name
            args = node.function_decl.get_argument_expressions()
            filtered = len(node.filter_args.args) > 0 
            buffered = eval(node.attributes.get('buffered', 'False'))
            cached = eval(node.attributes.get('cached', 'False'))
            defs = None
            pagetag = None
        else:
            defs = self.write_toplevel()
            pagetag = self.compiler.pagetag
            name = "render_body"
            if pagetag is not None:
                args = pagetag.body_decl.get_argument_expressions()
                if not pagetag.body_decl.kwargs:
                    args += ['**pageargs']
                cached = eval(pagetag.attributes.get('cached', 'False'))
            else:
                args = ['**pageargs']
                cached = False
            buffered = filtered = False
        if args is None:
            args = ['context']
        else:
            args = [a for a in ['context'] + args]
            
        self.write_render_callable(pagetag or node, name, args, buffered, filtered, cached)
        
        if defs is not None:
            for node in defs:
                _GenerateRenderMethod(printer, compiler, node)
    
    identifiers = property(lambda self:self.identifier_stack[-1])
    
    def write_toplevel(self):
        """traverse a template structure for module-level directives and generate the
        start of module-level code."""
        inherit = []
        namespaces = {}
        module_code = []
        encoding =[None]

        self.compiler.pagetag = None
        
        class FindTopLevel(object):
            def visitInheritTag(s, node):
                inherit.append(node)
            def visitNamespaceTag(s, node):
                namespaces[node.name] = node
            def visitPageTag(s, node):
                self.compiler.pagetag = node
            def visitCode(s, node):
                if node.ismodule:
                    module_code.append(node)
            
        f = FindTopLevel()
        for n in self.node.nodes:
            n.accept_visitor(f)

        self.compiler.namespaces = namespaces

        module_ident = util.Set()
        for n in module_code:
            module_ident = module_ident.union(n.declared_identifiers())

        module_identifiers = _Identifiers()
        module_identifiers.declared = module_ident
        
        # module-level names, python code
        if not self.compiler.generate_unicode and self.compiler.source_encoding:
            self.printer.writeline("# -*- encoding:%s -*-" % self.compiler.source_encoding)
            
        self.printer.writeline("from mako import runtime, filters, cache")
        self.printer.writeline("UNDEFINED = runtime.UNDEFINED")
        self.printer.writeline("__M_dict_builtin = dict")
        self.printer.writeline("__M_locals_builtin = locals")
        self.printer.writeline("_magic_number = %s" % repr(MAGIC_NUMBER))
        self.printer.writeline("_modified_time = %s" % repr(time.time()))
        self.printer.writeline("_template_filename=%s" % repr(self.compiler.filename))
        self.printer.writeline("_template_uri=%s" % repr(self.compiler.uri))
        self.printer.writeline("_template_cache=cache.Cache(__name__, _modified_time)")
        self.printer.writeline("_source_encoding=%s" % repr(self.compiler.source_encoding))
        if self.compiler.imports:
            buf = ''
            for imp in self.compiler.imports:
                buf += imp + "\n"
                self.printer.writeline(imp)
            impcode = ast.PythonCode(buf, source='', lineno=0, pos=0, filename='template defined imports')
        else:
            impcode = None
        
        main_identifiers = module_identifiers.branch(self.node)
        module_identifiers.topleveldefs = module_identifiers.topleveldefs.union(main_identifiers.topleveldefs)
        [module_identifiers.declared.add(x) for x in ["UNDEFINED"]]
        if impcode:
            [module_identifiers.declared.add(x) for x in impcode.declared_identifiers]
            
        self.compiler.identifiers = module_identifiers
        self.printer.writeline("_exports = %s" % repr([n.name for n in main_identifiers.topleveldefs.values()]))
        self.printer.write("\n\n")

        if len(module_code):
            self.write_module_code(module_code)

        if len(inherit):
            self.write_namespaces(namespaces)
            self.write_inherit(inherit[-1])
        elif len(namespaces):
            self.write_namespaces(namespaces)

        return main_identifiers.topleveldefs.values()

    def write_render_callable(self, node, name, args, buffered, filtered, cached):
        """write a top-level render callable.
        
        this could be the main render() method or that of a top-level def."""
        self.printer.writelines(
            "def %s(%s):" % (name, ','.join(args)),
                "context.caller_stack._push_frame()",
                "try:"
        )
        if buffered or filtered or cached:
            self.printer.writeline("context._push_buffer()")
        
        self.identifier_stack.append(self.compiler.identifiers.branch(self.node))
        if not self.in_def and '**pageargs' in args:
            self.identifier_stack[-1].argument_declared.add('pageargs')

        if not self.in_def and (len(self.identifiers.locally_assigned) > 0 or len(self.identifiers.argument_declared)>0):
            self.printer.writeline("__M_locals = __M_dict_builtin(%s)" % ','.join(["%s=%s" % (x, x) for x in self.identifiers.argument_declared]))

        self.write_variable_declares(self.identifiers, toplevel=True)

        for n in self.node.nodes:
            n.accept_visitor(self)

        self.write_def_finish(self.node, buffered, filtered, cached)
        self.printer.writeline(None)
        self.printer.write("\n\n")
        if cached:
            self.write_cache_decorator(node, name, args, buffered, self.identifiers, toplevel=True)
            
    def write_module_code(self, module_code):
        """write module-level template code, i.e. that which is enclosed in <%! %> tags
        in the template."""
        for n in module_code:
            self.write_source_comment(n)
            self.printer.write_indented_block(n.text)

    def write_inherit(self, node):
        """write the module-level inheritance-determination callable."""
        self.printer.writelines(
            "def _mako_inherit(template, context):",
                "_mako_generate_namespaces(context)",
                "return runtime._inherit_from(context, %s, _template_uri)" % (node.parsed_attributes['file']),
                None
            )

    def write_namespaces(self, namespaces):
        """write the module-level namespace-generating callable."""
        self.printer.writelines(
            "def _mako_get_namespace(context, name):",
                "try:",
                    "return context.namespaces[(__name__, name)]",
                "except KeyError:",
                    "_mako_generate_namespaces(context)",
                "return context.namespaces[(__name__, name)]",
            None,None
            )
        self.printer.writeline("def _mako_generate_namespaces(context):")
        for node in namespaces.values():
            if node.attributes.has_key('import'):
                self.compiler.has_ns_imports = True
            self.write_source_comment(node)
            if len(node.nodes):
                self.printer.writeline("def make_namespace():")
                export = []
                identifiers = self.compiler.identifiers.branch(node)
                class NSDefVisitor(object):
                    def visitDefTag(s, node):
                        self.write_inline_def(node, identifiers, nested=False)
                        export.append(node.name)
                vis = NSDefVisitor()
                for n in node.nodes:
                    n.accept_visitor(vis)
                self.printer.writeline("return [%s]" % (','.join(export)))
                self.printer.writeline(None)
                callable_name = "make_namespace()"
            else:
                callable_name = "None"
            self.printer.writeline("ns = runtime.Namespace(%s, context._clean_inheritance_tokens(), templateuri=%s, callables=%s, calling_uri=_template_uri, module=%s)" % (repr(node.name), node.parsed_attributes.get('file', 'None'), callable_name, node.parsed_attributes.get('module', 'None')))
            if eval(node.attributes.get('inheritable', "False")):
                self.printer.writeline("context['self'].%s = ns" % (node.name))
            self.printer.writeline("context.namespaces[(__name__, %s)] = ns" % repr(node.name))
            self.printer.write("\n")
        if not len(namespaces):
            self.printer.writeline("pass")
        self.printer.writeline(None)
            
    def write_variable_declares(self, identifiers, toplevel=False, limit=None):
        """write variable declarations at the top of a function.
        
        the variable declarations are in the form of callable definitions for defs and/or
        name lookup within the function's context argument.  the names declared are based on the
        names that are referenced in the function body, which don't otherwise have any explicit
        assignment operation.  names that are assigned within the body are assumed to be 
        locally-scoped variables and are not separately declared.
        
        for def callable definitions, if the def is a top-level callable then a 
        'stub' callable is generated which wraps the current Context into a closure.  if the def
        is not top-level, it is fully rendered as a local closure."""
        
        # collection of all defs available to us in this scope
        comp_idents = dict([(c.name, c) for c in identifiers.defs])
        to_write = util.Set()
        
        # write "context.get()" for all variables we are going to need that arent in the namespace yet
        to_write = to_write.union(identifiers.undeclared)
        
        # write closure functions for closures that we define right here
        to_write = to_write.union(util.Set([c.name for c in identifiers.closuredefs.values()]))

        # remove identifiers that are declared in the argument signature of the callable
        to_write = to_write.difference(identifiers.argument_declared)

        # remove identifiers that we are going to assign to.  in this way we mimic Python's behavior,
        # i.e. assignment to a variable within a block means that variable is now a "locally declared" var,
        # which cannot be referenced beforehand.  
        to_write = to_write.difference(identifiers.locally_declared)
        
        # if a limiting set was sent, constraint to those items in that list
        # (this is used for the caching decorator)
        if limit is not None:
            to_write = to_write.intersection(limit)
        
        if toplevel and getattr(self.compiler, 'has_ns_imports', False):
            self.printer.writeline("_import_ns = {}")
            self.compiler.has_imports = True
            for ident, ns in self.compiler.namespaces.iteritems():
                if ns.attributes.has_key('import'):
                    self.printer.writeline("_mako_get_namespace(context, %s)._populate(_import_ns, %s)" % (repr(ident),  repr(re.split(r'\s*,\s*', ns.attributes['import']))))
                        
        for ident in to_write:
            if ident in comp_idents:
                comp = comp_idents[ident]
                if comp.is_root():
                    self.write_def_decl(comp, identifiers)
                else:
                    self.write_inline_def(comp, identifiers, nested=True)
            elif ident in self.compiler.namespaces:
                self.printer.writeline("%s = _mako_get_namespace(context, %s)" % (ident, repr(ident)))
            else:
                if getattr(self.compiler, 'has_ns_imports', False):
                    self.printer.writeline("%s = _import_ns.get(%s, context.get(%s, UNDEFINED))" % (ident, repr(ident), repr(ident)))
                else:
                    self.printer.writeline("%s = context.get(%s, UNDEFINED)" % (ident, repr(ident)))
        
        self.printer.writeline("__M_writer = context.writer()")
        
    def write_source_comment(self, node):
        """write a source comment containing the line number of the corresponding template line."""
        if self.last_source_line != node.lineno:
            self.printer.writeline("# SOURCE LINE %d" % node.lineno)
            self.last_source_line = node.lineno

    def write_def_decl(self, node, identifiers):
        """write a locally-available callable referencing a top-level def"""
        funcname = node.function_decl.funcname
        namedecls = node.function_decl.get_argument_expressions()
        nameargs = node.function_decl.get_argument_expressions(include_defaults=False)
        if not self.in_def and (len(self.identifiers.locally_assigned) > 0 or len(self.identifiers.argument_declared) > 0):
            nameargs.insert(0, 'context.locals_(__M_locals)')
        else:
            nameargs.insert(0, 'context')
        self.printer.writeline("def %s(%s):" % (funcname, ",".join(namedecls)))
        self.printer.writeline("return render_%s(%s)" % (funcname, ",".join(nameargs)))
        self.printer.writeline(None)
        
    def write_inline_def(self, node, identifiers, nested):
        """write a locally-available def callable inside an enclosing def."""
        namedecls = node.function_decl.get_argument_expressions()
        self.printer.writeline("def %s(%s):" % (node.name, ",".join(namedecls)))
        filtered = len(node.filter_args.args) > 0 
        buffered = eval(node.attributes.get('buffered', 'False'))
        cached = eval(node.attributes.get('cached', 'False'))
        self.printer.writelines(
            "context.caller_stack._push_frame()",
            "try:"
            )
        if buffered or filtered or cached:
            self.printer.writelines(
                "context._push_buffer()",
                )

        identifiers = identifiers.branch(node, nested=nested)

        self.write_variable_declares(identifiers)
        
        self.identifier_stack.append(identifiers)
        for n in node.nodes:
            n.accept_visitor(self)
        self.identifier_stack.pop()
        
        self.write_def_finish(node, buffered, filtered, cached)
        self.printer.writeline(None)
        if cached:
            self.write_cache_decorator(node, node.name, namedecls, False, identifiers, inline=True, toplevel=False)
            
    def write_def_finish(self, node, buffered, filtered, cached, callstack=True):
        """write the end section of a rendering function, either outermost or inline.
        
        this takes into account if the rendering function was filtered, buffered, etc.
        and closes the corresponding try: block if any, and writes code to retrieve captured content, 
        apply filters, send proper return value."""
        if not buffered and not cached and not filtered:
            self.printer.writeline("return ''")
            if callstack:
                self.printer.writelines(
                    "finally:",
                        "context.caller_stack._pop_frame()",
                    None
                )
                
        if buffered or filtered or cached:
            if buffered or cached:
                # in a caching scenario, don't try to get a writer
                # from the context after popping; assume the caching
                # implemenation might be using a context with no
                # extra buffers
                self.printer.writelines(
                    "finally:",
                        "__M_buf = context._pop_buffer()"
                )
            else:
                self.printer.writelines(
                    "finally:",
                        "__M_buf, __M_writer = context._pop_buffer_and_writer()"
                )
                
            if callstack:
                self.printer.writeline("context.caller_stack._pop_frame()")
                
            s = "__M_buf.getvalue()"
            if filtered:
                s = self.create_filter_callable(node.filter_args.args, s, False)
            self.printer.writeline(None)
            if buffered and not cached:
                s = self.create_filter_callable(self.compiler.buffer_filters, s, False)
            if buffered or cached:
                self.printer.writeline("return %s" % s)
            else:
                self.printer.writelines(
                    "__M_writer(%s)" % s,
                    "return ''"
                )

    def write_cache_decorator(self, node_or_pagetag, name, args, buffered, identifiers, inline=False, toplevel=False):
        """write a post-function decorator to replace a rendering callable with a cached version of itself."""
        self.printer.writeline("__M_%s = %s" % (name, name))
        cachekey = node_or_pagetag.parsed_attributes.get('cache_key', repr(name))
        cacheargs = {}
        for arg in (('cache_type', 'type'), ('cache_dir', 'data_dir'), ('cache_timeout', 'expiretime'), ('cache_url', 'url')):
            val = node_or_pagetag.parsed_attributes.get(arg[0], None)
            if val is not None:
                if arg[1] == 'expiretime':
                    cacheargs[arg[1]] = int(eval(val))
                else:
                    cacheargs[arg[1]] = val
            else:
                if self.compiler.pagetag is not None:
                    val = self.compiler.pagetag.parsed_attributes.get(arg[0], None)
                    if val is not None:
                        if arg[1] == 'expiretime':
                            cacheargs[arg[1]] == int(eval(val))
                        else:
                            cacheargs[arg[1]] = val
        
        self.printer.writeline("def %s(%s):" % (name, ','.join(args)))
        
        # form "arg1, arg2, arg3=arg3, arg4=arg4", etc.
        pass_args = [ '=' in a and "%s=%s" % ((a.split('=')[0],)*2) or a for a in args]

        self.write_variable_declares(identifiers, toplevel=toplevel, limit=node_or_pagetag.undeclared_identifiers())
        if buffered:
            s = "context.get('local').get_cached(%s, %screatefunc=lambda:__M_%s(%s))" % (cachekey, ''.join(["%s=%s, " % (k,v) for k, v in cacheargs.iteritems()]), name, ','.join(pass_args))
            # apply buffer_filters
            s = self.create_filter_callable(self.compiler.buffer_filters, s, False)
            self.printer.writelines("return " + s,None)
        else:
            self.printer.writelines(
                    "__M_writer(context.get('local').get_cached(%s, %screatefunc=lambda:__M_%s(%s)))" % (cachekey, ''.join(["%s=%s, " % (k,v) for k, v in cacheargs.iteritems()]), name, ','.join(pass_args)),
                    "return ''",
                None
            )

    def create_filter_callable(self, args, target, is_expression):
        """write a filter-applying expression based on the filters present in the given 
        filter names, adjusting for the global 'default' filter aliases as needed."""
        def locate_encode(name):
            if re.match(r'decode\..+', name):
                return "filters." + name
            else:
                return filters.DEFAULT_ESCAPES.get(name, name)
        
        if 'n' not in args:
            if is_expression:
                if self.compiler.pagetag:
                    args = self.compiler.pagetag.filter_args.args + args
                if self.compiler.default_filters:
                    args = self.compiler.default_filters + args
        for e in args:
            # if filter given as a function, get just the identifier portion
            if e == 'n':
                continue
            m = re.match(r'(.+?)(\(.*\))', e)
            if m:
                (ident, fargs) = m.group(1,2)
                f = locate_encode(ident)
                e = f + fargs
            else:
                x = e
                e = locate_encode(e)
                assert e is not None
            target = "%s(%s)" % (e, target)
        return target
        
    def visitExpression(self, node):
        self.write_source_comment(node)
        if len(node.escapes) or (self.compiler.pagetag is not None and len(self.compiler.pagetag.filter_args.args)) or len(self.compiler.default_filters):
            s = self.create_filter_callable(node.escapes_code.args, "%s" % node.text, True)
            self.printer.writeline("__M_writer(%s)" % s)
        else:
            self.printer.writeline("__M_writer(%s)" % node.text)
            
    def visitControlLine(self, node):
        if node.isend:
            self.printer.writeline(None)
        else:
            self.write_source_comment(node)
            self.printer.writeline(node.text)
    def visitText(self, node):
        self.write_source_comment(node)
        self.printer.writeline("__M_writer(%s)" % repr(node.content))
    def visitTextTag(self, node):
        filtered = len(node.filter_args.args) > 0
        if filtered:
            self.printer.writelines(
                "__M_writer = context._push_writer()",
                "try:",
            )
        for n in node.nodes:
            n.accept_visitor(self)
        if filtered:
            self.printer.writelines(
                "finally:",
                "__M_buf, __M_writer = context._pop_buffer_and_writer()",
                "__M_writer(%s)" % self.create_filter_callable(node.filter_args.args, "__M_buf.getvalue()", False),
                None
                )
        
    def visitCode(self, node):
        if not node.ismodule:
            self.write_source_comment(node)
            self.printer.write_indented_block(node.text)

            if not self.in_def and len(self.identifiers.locally_assigned) > 0:
                # if we are the "template" def, fudge locally declared/modified variables into the "__M_locals" dictionary,
                # which is used for def calls within the same template, to simulate "enclosing scope"
                self.printer.writeline('__M_locals.update(__M_dict_builtin([(__M_key, __M_locals_builtin()[__M_key]) for __M_key in [%s] if __M_key in __M_locals_builtin()]))' % ','.join([repr(x) for x in node.declared_identifiers()]))
                
    def visitIncludeTag(self, node):
        self.write_source_comment(node)
        args = node.attributes.get('args')
        if args:
            self.printer.writeline("runtime._include_file(context, %s, _template_uri, %s)" % (node.parsed_attributes['file'], args))
        else:
            self.printer.writeline("runtime._include_file(context, %s, _template_uri)" % (node.parsed_attributes['file']))
            
    def visitNamespaceTag(self, node):
        pass
            
    def visitDefTag(self, node):
        pass

    def visitCallTag(self, node):
        self.printer.writeline("def ccall(caller):")
        export = ['body']
        callable_identifiers = self.identifiers.branch(node, nested=True)
        body_identifiers = callable_identifiers.branch(node, nested=False)
        # we want the 'caller' passed to ccall to be used for the body() function,
        # but for other non-body() <%def>s within <%call> we want the current caller off the call stack (if any)
        body_identifiers.add_declared('caller')
        
        self.identifier_stack.append(body_identifiers)
        class DefVisitor(object):
            def visitDefTag(s, node):
                self.write_inline_def(node, callable_identifiers, nested=False)
                export.append(node.name)
                # remove defs that are within the <%call> from the "closuredefs" defined
                # in the body, so they dont render twice
                if node.name in body_identifiers.closuredefs:
                    del body_identifiers.closuredefs[node.name]

        vis = DefVisitor()
        for n in node.nodes:
            n.accept_visitor(vis)
        self.identifier_stack.pop()
        
        bodyargs = node.body_decl.get_argument_expressions()    
        self.printer.writeline("def body(%s):" % ','.join(bodyargs))
        # TODO: figure out best way to specify buffering/nonbuffering (at call time would be better)
        buffered = False
        if buffered:
            self.printer.writelines(
                "context._push_buffer()",
                "try:"
            )
        self.write_variable_declares(body_identifiers)
        self.identifier_stack.append(body_identifiers)
        
        for n in node.nodes:
            n.accept_visitor(self)
        self.identifier_stack.pop()
        
        self.write_def_finish(node, buffered, False, False, callstack=False)
        self.printer.writelines(
            None,
            "return [%s]" % (','.join(export)),
            None
        )

        self.printer.writelines(
            # get local reference to current caller, if any
            "caller = context.caller_stack._get_caller()",
            # push on caller for nested call
            "context.caller_stack.nextcaller = runtime.Namespace('caller', context, callables=ccall(caller))",
            "try:")
        self.write_source_comment(node)
        self.printer.writelines(
                "__M_writer(%s)" % self.create_filter_callable([], node.attributes['expr'], True),
            "finally:",
                "context.caller_stack.nextcaller = None",
            None
        )

class _Identifiers(object):
    """tracks the status of identifier names as template code is rendered."""
    def __init__(self, node=None, parent=None, nested=False):
        if parent is not None:
            # things that have already been declared in an enclosing namespace (i.e. names we can just use)
            self.declared = util.Set(parent.declared).union([c.name for c in parent.closuredefs.values()]).union(parent.locally_declared).union(parent.argument_declared)
            
            # if these identifiers correspond to a "nested" scope, it means whatever the 
            # parent identifiers had as undeclared will have been declared by that parent, 
            # and therefore we have them in our scope.
            if nested:
                self.declared = self.declared.union(parent.undeclared)
            
            # top level defs that are available
            self.topleveldefs = util.SetLikeDict(**parent.topleveldefs)
        else:
            self.declared = util.Set()
            self.topleveldefs = util.SetLikeDict()
        
        # things within this level that are referenced before they are declared (e.g. assigned to)
        self.undeclared = util.Set()
        
        # things that are declared locally.  some of these things could be in the "undeclared"
        # list as well if they are referenced before declared
        self.locally_declared = util.Set()
    
        # assignments made in explicit python blocks.  these will be propigated to 
        # the context of local def calls.
        self.locally_assigned = util.Set()
        
        # things that are declared in the argument signature of the def callable
        self.argument_declared = util.Set()
        
        # closure defs that are defined in this level
        self.closuredefs = util.SetLikeDict()
        
        self.node = node
        
        if node is not None:
            node.accept_visitor(self)
        
    def branch(self, node, **kwargs):
        """create a new Identifiers for a new Node, with this Identifiers as the parent."""
        return _Identifiers(node, self, **kwargs)
    
    defs = property(lambda self:util.Set(self.topleveldefs.union(self.closuredefs).values()))
    
    def __repr__(self):
        return "Identifiers(declared=%s, locally_declared=%s, undeclared=%s, topleveldefs=%s, closuredefs=%s, argumenetdeclared=%s)" % (repr(list(self.declared)), repr(list(self.locally_declared)), repr(list(self.undeclared)), repr([c.name for c in self.topleveldefs.values()]), repr([c.name for c in self.closuredefs.values()]), repr(self.argument_declared))
        
    def check_declared(self, node):
        """update the state of this Identifiers with the undeclared and declared identifiers of the given node."""
        for ident in node.undeclared_identifiers():
            if ident != 'context' and ident not in self.declared.union(self.locally_declared):
                self.undeclared.add(ident)
        for ident in node.declared_identifiers():
            self.locally_declared.add(ident)
    
    def add_declared(self, ident):
        self.declared.add(ident)
        if ident in self.undeclared:
            self.undeclared.remove(ident)
                        
    def visitExpression(self, node):
        self.check_declared(node)
    def visitControlLine(self, node):
        self.check_declared(node)
    def visitCode(self, node):
        if not node.ismodule:
            self.check_declared(node)
            self.locally_assigned = self.locally_assigned.union(node.declared_identifiers())
    def visitDefTag(self, node):
        if node.is_root():
            self.topleveldefs[node.name] = node
        elif node is not self.node:
            self.closuredefs[node.name] = node
        for ident in node.undeclared_identifiers():
            if ident != 'context' and ident not in self.declared.union(self.locally_declared):
                self.undeclared.add(ident)
        # visit defs only one level deep
        if node is self.node:
            for ident in node.declared_identifiers():
                self.argument_declared.add(ident)
            for n in node.nodes:
                n.accept_visitor(self)
    def visitIncludeTag(self, node):
        self.check_declared(node)
    def visitPageTag(self, node):
        for ident in node.declared_identifiers():
            self.argument_declared.add(ident)
        self.check_declared(node)
                    
    def visitCallTag(self, node):
        if node is self.node:
            for ident in node.undeclared_identifiers():
                if ident != 'context' and ident not in self.declared.union(self.locally_declared):
                    self.undeclared.add(ident)
            for ident in node.declared_identifiers():
                self.argument_declared.add(ident)
            for n in node.nodes:
                n.accept_visitor(self)
        else:
            for ident in node.undeclared_identifiers():
                if ident != 'context' and ident not in self.declared.union(self.locally_declared):
                    self.undeclared.add(ident)
                

########NEW FILE########
__FILENAME__ = exceptions
# exceptions.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""exception classes"""

import traceback, sys, re

class MakoException(Exception):
    pass

class RuntimeException(MakoException):
    pass

def _format_filepos(lineno, pos, filename):
    if filename is None:
        return " at line: %d char: %d" % (lineno, pos)
    else:
        return " in file '%s' at line: %d char: %d" % (filename, lineno, pos)     
class CompileException(MakoException):
    def __init__(self, message, source, lineno, pos, filename):
        MakoException.__init__(self, message + _format_filepos(lineno, pos, filename))
        self.lineno =lineno
        self.pos = pos
        self.filename = filename
        self.source = source
                    
class SyntaxException(MakoException):
    def __init__(self, message, source, lineno, pos, filename):
        MakoException.__init__(self, message + _format_filepos(lineno, pos, filename))
        self.lineno =lineno
        self.pos = pos
        self.filename = filename
        self.source = source
        
class TemplateLookupException(MakoException):
    pass

class TopLevelLookupException(TemplateLookupException):
    pass
    
class RichTraceback(object):
    """pulls the current exception from the sys traceback and extracts Mako-specific 
    template information.
    
    Usage:
    
    RichTraceback()
    
    Properties:
    
    error - the exception instance.  
    source - source code of the file where the error occured.  if the error occured within a compiled template,
    this is the template source.
    lineno - line number where the error occured.  if the error occured within a compiled template, the line number
    is adjusted to that of the template source
    records - a list of 8-tuples containing the original python traceback elements, plus the 
    filename, line number, source line, and full template source for the traceline mapped back to its originating source
    template, if any for that traceline (else the fields are None).
    reverse_records - the list of records in reverse
    traceback - a list of 4-tuples, in the same format as a regular python traceback, with template-corresponding 
    traceback records replacing the originals
    reverse_traceback - the traceback list in reverse
    """
    def __init__(self):
        (self.source, self.lineno) = ("", 0)
        (t, self.error, self.records) = self._init()
        if self.error is None:
            self.error = t
        if isinstance(self.error, CompileException) or isinstance(self.error, SyntaxException):
            import mako.template
            self.source = self.error.source
            self.lineno = self.error.lineno
            self._has_source = True
        self.reverse_records = [r for r in self.records]
        self.reverse_records.reverse()
    def _get_reformatted_records(self, records):
        for rec in records:
            if rec[6] is not None:
                yield (rec[4], rec[5], rec[2], rec[6])
            else:
                yield tuple(rec[0:4])
    traceback = property(lambda self:self._get_reformatted_records(self.records), doc="""
        return a list of 4-tuple traceback records (i.e. normal python format)
        with template-corresponding lines remapped to the originating template
    """)
    reverse_traceback = property(lambda self:self._get_reformatted_records(self.reverse_records), doc="""
        return the same data as traceback, except in reverse order
    """)
    def _init(self):
        """format a traceback from sys.exc_info() into 7-item tuples, containing
        the regular four traceback tuple items, plus the original template 
        filename, the line number adjusted relative to the template source, and
        code line from that line number of the template."""
        import mako.template
        mods = {}
        (type, value, trcback) = sys.exc_info()
        rawrecords = traceback.extract_tb(trcback)
        new_trcback = []
        for filename, lineno, function, line in rawrecords:
            try:
                (line_map, template_lines) = mods[filename]
            except KeyError:
                try:
                    info = mako.template._get_module_info(filename)
                    module_source = info.code
                    template_source = info.source
                    template_filename = info.template_filename or filename
                except KeyError:
                    new_trcback.append((filename, lineno, function, line, None, None, None, None))
                    continue

                template_ln = module_ln = 1
                line_map = {}
                for line in module_source.split("\n"):
                    match = re.match(r'\s*# SOURCE LINE (\d+)', line)
                    if match:
                        template_ln = int(match.group(1))
                    else:
                        template_ln += 1
                    module_ln += 1
                    line_map[module_ln] = template_ln
                template_lines = [line for line in template_source.split("\n")]
                mods[filename] = (line_map, template_lines)

            template_ln = line_map[lineno]
            if template_ln <= len(template_lines):
                template_line = template_lines[template_ln - 1]
            else:
                template_line = None
            new_trcback.append((filename, lineno, function, line, template_filename, template_ln, template_line, template_source))
        if not self.source:
            for l in range(len(new_trcback)-1, 0, -1):
                if new_trcback[l][5]:
                    self.source = new_trcback[l][7]
                    self.lineno = new_trcback[l][5]
                    break
            else:
                try:
                    self.source = file(new_trcback[-1][0]).read()
                except IOError:
                    self.source = ''
                self.lineno = new_trcback[-1][1]
        return (type, value, new_trcback)

                
def text_error_template(lookup=None):
    """provides a template that renders a stack trace in a similar format to the Python interpreter,
    substituting source template filenames, line numbers and code for that of the originating
    source template, as applicable."""
    import mako.template
    return mako.template.Template(r"""
<%!
    from mako.exceptions import RichTraceback
%>\
<%
    tback = RichTraceback()
%>\
Traceback (most recent call last):
% for (filename, lineno, function, line) in tback.traceback:
  File "${filename}", line ${lineno}, in ${function or '?'}
    ${line | unicode.strip}
% endfor
${str(tback.error.__class__.__name__)}: ${str(tback.error)}
""")

def html_error_template():
    """provides a template that renders a stack trace in an HTML format, providing an excerpt of 
    code as well as substituting source template filenames, line numbers and code 
    for that of the originating source template, as applicable.

    the template's default encoding_errors value is 'htmlentityreplace'. the template has
    two options:

    with the full option disabled, only a section of an HTML document is returned.
    with the css option disabled, the default stylesheet won't be included."""
    import mako.template
    return mako.template.Template(r"""
<%!
    from mako.exceptions import RichTraceback
%>
<%page args="full=True, css=True"/>
% if full:
<html>
<head>
    <title>Mako Runtime Error</title>
% endif
% if css:
    <style>
        body { font-family:verdana; margin:10px 30px 10px 30px;}
        .stacktrace { margin:5px 5px 5px 5px; }
        .highlight { padding:0px 10px 0px 10px; background-color:#9F9FDF; }
        .nonhighlight { padding:0px; background-color:#DFDFDF; }
        .sample { padding:10px; margin:10px 10px 10px 10px; font-family:monospace; }
        .sampleline { padding:0px 10px 0px 10px; }
        .sourceline { margin:5px 5px 10px 5px; font-family:monospace;}
        .location { font-size:80%; }
    </style>
% endif
% if full:
</head>
<body>
% endif

<h2>Error !</h2>
<%
    tback = RichTraceback()
    src = tback.source
    line = tback.lineno
    if src:
        lines = src.split('\n')
    else:
        lines = None
%>
<h3>${str(tback.error.__class__.__name__)}: ${str(tback.error)}</h3>

% if lines:
    <div class="sample">
    <div class="nonhighlight">
% for index in range(max(0, line-4),min(len(lines), line+5)):
    % if index + 1 == line:
<div class="highlight">${index + 1} ${lines[index] | h}</div>
    % else:
<div class="sampleline">${index + 1} ${lines[index] | h}</div>
    % endif
% endfor
    </div>
    </div>
% endif

<div class="stacktrace">
% for (filename, lineno, function, line) in tback.reverse_traceback:
    <div class="location">${filename}, line ${lineno}:</div>
    <div class="sourceline">${line | h}</div>
% endfor
</div>

% if full:
</body>
</html>
% endif
""", output_encoding=sys.getdefaultencoding(), encoding_errors='htmlentityreplace')

########NEW FILE########
__FILENAME__ = autohandler
"""adds autohandler functionality to Mako templates.

requires that the TemplateLookup class is used with templates.

usage:

<%!
	from mako.ext.autohandler import autohandler
%>
<%inherit file="${autohandler(template, context)}"/>


or with custom autohandler filename:

<%!
	from mako.ext.autohandler import autohandler
%>
<%inherit file="${autohandler(template, context, name='somefilename')}"/>

"""

import posixpath, os, re

def autohandler(template, context, name='autohandler'):
    lookup = context.lookup
    _template_uri = template.module._template_uri
    if not lookup.filesystem_checks:
        try:
            return lookup._uri_cache[(autohandler, _template_uri, name)]
        except KeyError:
            pass

    tokens = re.findall(r'([^/]+)', posixpath.dirname(_template_uri)) + [name]
    while len(tokens):
        path = '/' + '/'.join(tokens)
        if path != _template_uri and _file_exists(lookup, path):
            if not lookup.filesystem_checks:
                return lookup._uri_cache.setdefault((autohandler, _template_uri, name), path)
            else:
                return path
        if len(tokens) == 1:
            break
        tokens[-2:] = [name]
        
    if not lookup.filesystem_checks:
        return lookup._uri_cache.setdefault((autohandler, _template_uri, name), None)
    else:
        return None

def _file_exists(lookup, path):
    psub = re.sub(r'^/', '',path)
    for d in lookup.directories:
        if os.path.exists(d + '/' + psub):
            return True
    else:
        return False
    

########NEW FILE########
__FILENAME__ = babelplugin
"""gettext message extraction via Babel: http://babel.edgewall.org/"""
from StringIO import StringIO

from babel.messages.extract import extract_python

from mako import lexer, parsetree

def extract(fileobj, keywords, comment_tags, options):
    """Extract messages from Mako templates.

    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples
    :rtype: ``iterator``
    """
    encoding = options.get('input_encoding', options.get('encoding', None))

    template_node = lexer.Lexer(fileobj.read(),
                                input_encoding=encoding).parse()
    for extracted in extract_nodes(template_node.get_children(),
                                        keywords, comment_tags, options):
        yield extracted

def extract_nodes(nodes, keywords, comment_tags, options):
    """Extract messages from Mako's lexer node objects

    :param nodes: an iterable of Mako parsetree.Node objects to extract from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples
    :rtype: ``iterator``
    """
    translator_comments = []
    in_translator_comments = False

    for node in nodes:
        child_nodes = None
        if in_translator_comments and isinstance(node, parsetree.Text) and \
                not node.content.strip():
            # Ignore whitespace within translator comments
            continue

        if isinstance(node, parsetree.Comment):
            value = node.text.strip()
            if in_translator_comments:
                translator_comments.extend(_split_comment(node.lineno, value))
                continue
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    in_translator_comments = True
                    comment = value[len(comment_tag):].strip()
                    translator_comments.extend(_split_comment(node.lineno,
                                                              comment))
            continue

        if isinstance(node, parsetree.DefTag):
            code = node.function_decl.code
            child_nodes = node.nodes
        elif isinstance(node, parsetree.CallTag):
            code = node.code.code
            child_nodes = node.nodes
        elif isinstance(node, parsetree.PageTag):
            code = node.body_decl.code
        elif isinstance(node, parsetree.ControlLine):
            if node.isend:
                translator_comments = []
                in_translator_comments = False
                continue
            code = node.text
        elif isinstance(node, parsetree.Code):
            # <% and <%! blocks would provide their own translator comments
            translator_comments = []
            in_translator_comments = False

            code = node.code.code
        elif isinstance(node, parsetree.Expression):
            code = node.code.code
        else:
            translator_comments = []
            in_translator_comments = False
            continue

        # Comments don't apply unless they immediately preceed the message
        if translator_comments and \
                translator_comments[-1][0] < node.lineno - 1:
            translator_comments = []
        else:
            translator_comments = \
                [comment[1] for comment in translator_comments]

        if isinstance(code, unicode):
            code = code.encode('ascii', 'backslashreplace')
        code = StringIO(code)
        for lineno, funcname, messages, python_translator_comments \
                in extract_python(code, keywords, comment_tags, options):
            yield (node.lineno + (lineno - 1), funcname, messages,
                   translator_comments + python_translator_comments)

        translator_comments = []
        in_translator_comments = False

        if child_nodes:
            for extracted in extract_nodes(child_nodes, keywords, comment_tags,
                                           options):
                yield extracted


def _split_comment(lineno, comment):
    """Return the multiline comment at lineno split into a list of comment line
    numbers and the accompanying comment line"""
    return [(lineno + index, line) for index, line in
            enumerate(comment.splitlines())]

########NEW FILE########
__FILENAME__ = preprocessors
"""preprocessing functions, used with the 'preprocessor' argument on Template, TemplateLookup"""

import re

def convert_comments(text):
    """preprocess old style comments.
    
    example:
    
    from mako.ext.preprocessors import convert_comments
    t = Template(..., preprocessor=preprocess_comments)"""
    return re.sub(r'(?<=\n)\s*#[^#]', "##", text)

# TODO
def create_tag(callable):
    """given a callable, extract the *args and **kwargs, and produce a preprocessor
    that will parse for <%<funcname> <args>> and convert to an appropriate <%call> statement.
    
    this allows any custom tag to be created which looks like a pure Mako-style tag."""
    raise NotImplementedError("Future functionality....")
########NEW FILE########
__FILENAME__ = pygmentplugin
import re
try:
    set
except NameError:
    from sets import Set as set

from pygments.lexers.web import \
     HtmlLexer, XmlLexer, JavascriptLexer, CssLexer
from pygments.lexers.agile import PythonLexer
from pygments.lexer import Lexer, DelegatingLexer, RegexLexer, bygroups, \
     include, using, this
from pygments.token import Error, Punctuation, \
     Text, Comment, Operator, Keyword, Name, String, Number, Other, Literal
from pygments.util import html_doctype_matches, looks_like_xml

class MakoLexer(RegexLexer):
    name = 'Mako'
    aliases = ['mako']
    filenames = ['*.mao']

    tokens = {
        'root': [
            (r'(\s*)(\%)(\s*end(?:\w+))(\n|\Z)',
             bygroups(Text, Comment.Preproc, Keyword, Other)),
            (r'(\s*)(\%)([^\n]*)(\n|\Z)',
             bygroups(Text, Comment.Preproc, using(PythonLexer), Other)),
             (r'(\s*)(##[^\n]*)(\n|\Z)',
              bygroups(Text, Comment.Preproc, Other)),
              (r'''(?s)<%doc>.*?</%doc>''', Comment.Preproc),
            (r'(<%)(def|call|namespace|text)', bygroups(Comment.Preproc, Name.Builtin), 'tag'),
            (r'(</%)(def|call|namespace|text)(>)', bygroups(Comment.Preproc, Name.Builtin, Comment.Preproc)),
            (r'<%(?=(include|inherit|namespace|page))', Comment.Preproc, 'ondeftags'),
            (r'(<%(?:!?))(.*?)(%>)(?s)', bygroups(Comment.Preproc, using(PythonLexer), Comment.Preproc)),
            (r'(\$\{)(.*?)(\})',
             bygroups(Comment.Preproc, using(PythonLexer), Comment.Preproc)),
            (r'''(?sx)
                (.+?)               # anything, followed by:
                (?:
                 (?<=\n)(?=%|\#\#) |  # an eval or comment line
                 (?=\#\*) |          # multiline comment
                 (?=</?%) |         # a python block
                                    # call start or end
                 (?=\$\{) |         # a substitution
                 (?<=\n)(?=\s*%) |
                                    # - don't consume
                 (\\\n) |           # an escaped newline
                 \Z                 # end of string
                )
            ''', bygroups(Other, Operator)),
            (r'\s+', Text),
        ],
        'ondeftags': [
            (r'<%', Comment.Preproc),
            (r'(?<=<%)(include|inherit|namespace|page)', Name.Builtin),
            include('tag'),
        ],
        'tag': [
            (r'((?:\w+)\s*=)\s*(".*?")',
             bygroups(Name.Attribute, String)),
            (r'/?\s*>', Comment.Preproc, '#pop'),
            (r'\s+', Text),
        ],
        'attr': [
            ('".*?"', String, '#pop'),
            ("'.*?'", String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
    }


class MakoHtmlLexer(DelegatingLexer):
    name = 'HTML+Mako'
    aliases = ['html+mako']

    def __init__(self, **options):
        super(MakoHtmlLexer, self).__init__(HtmlLexer, MakoLexer,
                                              **options)

class MakoXmlLexer(DelegatingLexer):
    name = 'XML+Mako'
    aliases = ['xml+mako']

    def __init__(self, **options):
        super(MakoXmlLexer, self).__init__(XmlLexer, MakoLexer,
                                             **options)

class MakoJavascriptLexer(DelegatingLexer):
    name = 'JavaScript+Mako'
    aliases = ['js+mako', 'javascript+mako']

    def __init__(self, **options):
        super(MakoJavascriptLexer, self).__init__(JavascriptLexer,
                                                    MakoLexer, **options)

class MakoCssLexer(DelegatingLexer):
    name = 'CSS+Mako'
    aliases = ['css+mako']

    def __init__(self, **options):
        super(MakoCssLexer, self).__init__(CssLexer, MakoLexer,
                                             **options)

########NEW FILE########
__FILENAME__ = turbogears
import re, inspect
from mako.lookup import TemplateLookup
from mako.template import Template

class TGPlugin(object):
    """TurboGears compatible Template Plugin."""

    def __init__(self, extra_vars_func=None, options=None, extension='mak'):
        self.extra_vars_func = extra_vars_func
        self.extension = extension
        if not options:
            options = {}

        # Pull the options out and initialize the lookup
        lookup_options = {}
        for k, v in options.iteritems():
            if k.startswith('mako.'):
                lookup_options[k[5:]] = v
            elif k in ['directories', 'filesystem_checks', 'module_directory']:
                lookup_options[k] = v
        self.lookup = TemplateLookup(**lookup_options)
        
        self.tmpl_options = {}
        # transfer lookup args to template args, based on those available
        # in getargspec
        for kw in inspect.getargspec(Template.__init__)[0]:
            if kw in lookup_options:
                self.tmpl_options[kw] = lookup_options[kw]

    def load_template(self, templatename, template_string=None):
        """Loads a template from a file or a string"""
        if template_string is not None:
            return Template(template_string, **self.tmpl_options)
        # Translate TG dot notation to normal / template path
        if '/' not in templatename:
            templatename = '/' + templatename.replace('.', '/') + '.' + self.extension

        # Lookup template
        return self.lookup.get_template(templatename)

    def render(self, info, format="html", fragment=False, template=None):
        if isinstance(template, basestring):
            template = self.load_template(template)

        # Load extra vars func if provided
        if self.extra_vars_func:
            info.update(self.extra_vars_func())

        return template.render(**info)


########NEW FILE########
__FILENAME__ = filters
# filters.py
# Copyright (C) 2006, 2007, 2008 Geoffrey T. Dairiki <dairiki@dairiki.org> and Michael Bayer <mike_mp@zzzcomputing.com>
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php


import re, cgi, urllib, htmlentitydefs, codecs
from StringIO import StringIO

xml_escapes = {
    '&' : '&amp;',
    '>' : '&gt;', 
    '<' : '&lt;', 
    '"' : '&#34;',   # also &quot; in html-only
    "'" : '&#39;'    # also &apos; in html-only    
}
# XXX: &quot; is valid in HTML and XML
#      &apos; is not valid HTML, but is valid XML

def html_escape(string):
    return cgi.escape(string, True)

def xml_escape(string):
    return re.sub(r'([&<"\'>])', lambda m: xml_escapes[m.group()], string)

def url_escape(string):
    # convert into a list of octets
    string = string.encode("utf8")
    return urllib.quote_plus(string)

def url_unescape(string):
    text = urllib.unquote_plus(string)
    if not is_ascii_str(text):
        text = text.decode("utf8")
    return text

def trim(string):
    return string.strip()


class Decode(object):
    def __getattr__(self, key):
        def decode(x):
            if isinstance(x, unicode):
                return x
            elif not isinstance(x, str):
                return unicode(str(x), encoding=key)
            else:
                return unicode(x, encoding=key)
        return decode
decode = Decode()
        
            
_ASCII_re = re.compile(r'\A[\x00-\x7f]*\Z')

def is_ascii_str(text):
    return isinstance(text, str) and _ASCII_re.match(text)

################################################################    

class XMLEntityEscaper(object):
    def __init__(self, codepoint2name, name2codepoint):
        self.codepoint2entity = dict([(c, u'&%s;' % n)
                                      for c,n in codepoint2name.iteritems()])
        self.name2codepoint = name2codepoint

    def escape_entities(self, text):
        """Replace characters with their character entity references.

        Only characters corresponding to a named entity are replaced.
        """
        return unicode(text).translate(self.codepoint2entity)

    def __escape(self, m):
        codepoint = ord(m.group())
        try:
            return self.codepoint2entity[codepoint]
        except (KeyError, IndexError):
            return '&#x%X;' % codepoint


    __escapable = re.compile(r'["&<>]|[^\x00-\x7f]')

    def escape(self, text):
        """Replace characters with their character references.

        Replace characters by their named entity references.
        Non-ASCII characters, if they do not have a named entity reference,
        are replaced by numerical character references.

        The return value is guaranteed to be ASCII.
        """
        return self.__escapable.sub(self.__escape, unicode(text)
                                    ).encode('ascii')

    # XXX: This regexp will not match all valid XML entity names__.
    # (It punts on details involving involving CombiningChars and Extenders.)
    #
    # .. __: http://www.w3.org/TR/2000/REC-xml-20001006#NT-EntityRef
    __characterrefs = re.compile(r'''& (?:
                                          \#(\d+)
                                          | \#x([\da-f]+)
                                          | ( (?!\d) [:\w] [-.:\w]+ )
                                          ) ;''',
                                 re.X | re.UNICODE)
    
    def __unescape(self, m):
        dval, hval, name = m.groups()
        if dval:
            codepoint = int(dval)
        elif hval:
            codepoint = int(hval, 16)
        else:
            codepoint = self.name2codepoint.get(name, 0xfffd)
            # U+FFFD = "REPLACEMENT CHARACTER"
        if codepoint < 128:
            return chr(codepoint)
        return unichr(codepoint)
    
    def unescape(self, text):
        """Unescape character references.

        All character references (both entity references and numerical
        character references) are unescaped.
        """
        return self.__characterrefs.sub(self.__unescape, text)


_html_entities_escaper = XMLEntityEscaper(htmlentitydefs.codepoint2name,
                                          htmlentitydefs.name2codepoint)

html_entities_escape = _html_entities_escaper.escape_entities
html_entities_unescape = _html_entities_escaper.unescape


def htmlentityreplace_errors(ex):
    """An encoding error handler.

    This python `codecs`_ error handler replaces unencodable
    characters with HTML entities, or, if no HTML entity exists for
    the character, XML character references.

    >>> u'The cost was \u20ac12.'.encode('latin1', 'htmlentityreplace')
    'The cost was &euro;12.'
    """
    if isinstance(ex, UnicodeEncodeError):
        # Handle encoding errors
        bad_text = ex.object[ex.start:ex.end]
        text = _html_entities_escaper.escape(bad_text)
        return (unicode(text), ex.end)
    raise ex

codecs.register_error('htmlentityreplace', htmlentityreplace_errors)


# TODO: options to make this dynamic per-compilation will be added in a later release
DEFAULT_ESCAPES = {
    'x':'filters.xml_escape',
    'h':'filters.html_escape',
    'u':'filters.url_escape',
    'trim':'filters.trim',
    'entity':'filters.html_entities_escape',
    'unicode':'unicode',
    'decode':'decode',
    'str':'str',
    'n':'n'
}
    


########NEW FILE########
__FILENAME__ = lexer
# lexer.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""provides the Lexer class for parsing template strings into parse trees."""

import re, codecs
from mako import parsetree, exceptions
from mako.pygen import adjust_whitespace

_regexp_cache = {}

class Lexer(object):
    def __init__(self, text, filename=None, disable_unicode=False, input_encoding=None, preprocessor=None):
        self.text = text
        self.filename = filename
        self.template = parsetree.TemplateNode(self.filename)
        self.matched_lineno = 1
        self.matched_charpos = 0
        self.lineno = 1
        self.match_position = 0
        self.tag = []
        self.control_line = []
        self.disable_unicode = disable_unicode
        self.encoding = input_encoding
        if preprocessor is None:
            self.preprocessor = []
        elif not hasattr(preprocessor, '__iter__'):
            self.preprocessor = [preprocessor]
        else:
            self.preprocessor = preprocessor
            
    exception_kwargs = property(lambda self:{'source':self.text, 'lineno':self.matched_lineno, 'pos':self.matched_charpos, 'filename':self.filename})
    
    def match(self, regexp, flags=None):
        """match the given regular expression string and flags to the current text position.
        
        if a match occurs, update the current text and line position."""
        mp = self.match_position
        try:
            reg = _regexp_cache[(regexp, flags)]
        except KeyError:
            if flags:
                reg = re.compile(regexp, flags)
            else:
                reg = re.compile(regexp)
            _regexp_cache[(regexp, flags)] = reg

        match = reg.match(self.text, self.match_position)
        if match:
            (start, end) = match.span()
            if end == start:
                self.match_position = end + 1
            else:
                self.match_position = end
            self.matched_lineno = self.lineno
            lines = re.findall(r"\n", self.text[mp:self.match_position])
            cp = mp - 1
            while (cp >= 0 and cp<self.textlength and self.text[cp] != '\n'):
                cp -=1
            self.matched_charpos = mp - cp
            self.lineno += len(lines)
            #print "MATCHED:", match.group(0), "LINE START:", self.matched_lineno, "LINE END:", self.lineno
        #print "MATCH:", regexp, "\n", self.text[mp : mp + 15], (match and "TRUE" or "FALSE")
        return match
    
    def parse_until_text(self, *text):
        startpos = self.match_position
        while True:
            match = self.match(r'#.*\n')
            if match:
                continue
            match = self.match(r'(\"\"\"|\'\'\'|\"|\')')
            if match:
                m = self.match(r'.*?%s' % match.group(1), re.S)
                if not m:
                    raise exceptions.SyntaxException("Unmatched '%s'" % match.group(1), **self.exception_kwargs)
            else:
                match = self.match(r'(%s)' % r'|'.join(text))
                if match:
                    return (self.text[startpos:self.match_position-len(match.group(1))], match.group(1))
                else:
                    match = self.match(r".*?(?=\"|\'|#|%s)" % r'|'.join(text), re.S)
                    if not match:
                        raise exceptions.SyntaxException("Expected: %s" % ','.join(text), **self.exception_kwargs)
                
    def append_node(self, nodecls, *args, **kwargs):
        kwargs.setdefault('source', self.text)
        kwargs.setdefault('lineno', self.matched_lineno)
        kwargs.setdefault('pos', self.matched_charpos)
        kwargs['filename'] = self.filename
        node = nodecls(*args, **kwargs)
        if len(self.tag):
            self.tag[-1].nodes.append(node)
        else:
            self.template.nodes.append(node)
        if isinstance(node, parsetree.Tag):
            if len(self.tag):
                node.parent = self.tag[-1]
            self.tag.append(node)
        elif isinstance(node, parsetree.ControlLine):
            if node.isend:
                self.control_line.pop()
            elif node.is_primary:
                self.control_line.append(node)
            elif len(self.control_line) and not self.control_line[-1].is_ternary(node.keyword):
                raise exceptions.SyntaxException("Keyword '%s' not a legal ternary for keyword '%s'" % (node.keyword, self.control_line[-1].keyword), **self.exception_kwargs)

    def escape_code(self, text):
        if not self.disable_unicode and self.encoding:
            return text.encode('ascii', 'backslashreplace')
        else:
            return text
            
    def parse(self):
        for preproc in self.preprocessor:
            self.text = preproc(self.text)
        if not isinstance(self.text, unicode) and self.text.startswith(codecs.BOM_UTF8):
            self.text = self.text[len(codecs.BOM_UTF8):]
            parsed_encoding = 'utf-8'
            me = self.match_encoding()
            if me is not None and me != 'utf-8':
                raise exceptions.CompileException("Found utf-8 BOM in file, with conflicting magic encoding comment of '%s'" % me, self.text.decode('utf-8', 'ignore'), 0, 0, self.filename)
        else:
            parsed_encoding = self.match_encoding()
        if parsed_encoding:
            self.encoding = parsed_encoding
        if not self.disable_unicode and not isinstance(self.text, unicode):
            if self.encoding:
                try:
                    self.text = self.text.decode(self.encoding)
                except UnicodeDecodeError, e:
                    raise exceptions.CompileException("Unicode decode operation of encoding '%s' failed" % self.encoding, self.text.decode('utf-8', 'ignore'), 0, 0, self.filename)
            else:
                try:
                    self.text = self.text.decode()
                except UnicodeDecodeError, e:
                    raise exceptions.CompileException("Could not read template using encoding of 'ascii'.  Did you forget a magic encoding comment?", self.text.decode('utf-8', 'ignore'), 0, 0, self.filename)

        self.textlength = len(self.text)
            
        while (True):
            if self.match_position > self.textlength: 
                break
        
            if self.match_end():
                break
            if self.match_expression():
                continue
            if self.match_control_line():
                continue
            if self.match_comment():
                continue
            if self.match_tag_start(): 
                continue
            if self.match_tag_end():
                continue
            if self.match_python_block():
                continue
            if self.match_text(): 
                continue
            
            if self.match_position > self.textlength: 
                break
            raise exceptions.CompileException("assertion failed")
            
        if len(self.tag):
            raise exceptions.SyntaxException("Unclosed tag: <%%%s>" % self.tag[-1].keyword, **self.exception_kwargs)
        if len(self.control_line):
            raise exceptions.SyntaxException("Unterminated control keyword: '%s'" % self.control_line[-1].keyword, self.text, self.control_line[-1].lineno, self.control_line[-1].pos, self.filename)
        return self.template

    def match_encoding(self):
        match = self.match(r'#.*coding[:=]\s*([-\w.]+).*\r?\n')
        if match:
            return match.group(1)
        else:
            return None
            
    def match_tag_start(self):
        match = self.match(r'''
            \<%     # opening tag
            
            (\w+)   # keyword
            
            ((?:\s+\w+|=|".*?"|'.*?')*)  # attrname, = sign, string expression
            
            \s*     # more whitespace
            
            (/)?>   # closing
            
            ''', 
            
            re.I | re.S | re.X)
            
        if match:
            (keyword, attr, isend) = (match.group(1).lower(), match.group(2), match.group(3))
            self.keyword = keyword
            attributes = {}
            if attr:
                for att in re.findall(r"\s*(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\")", attr):
                    (key, val1, val2) = att
                    text = val1 or val2
                    text = text.replace('\r\n', '\n')
                    attributes[key] = self.escape_code(text)
            self.append_node(parsetree.Tag, keyword, attributes)
            if isend:
                self.tag.pop()
            else:
                if keyword == 'text':
                    match = self.match(r'(.*?)(?=\</%text>)',  re.S)
                    if not match:
                        raise exceptions.SyntaxException("Unclosed tag: <%%%s>" % self.tag[-1].keyword, **self.exception_kwargs)
                    self.append_node(parsetree.Text, match.group(1))
                    return self.match_tag_end()
            return True
        else: 
            return False
        
    def match_tag_end(self):
        match = self.match(r'\</%[\t ]*(.+?)[\t ]*>')
        if match:
            if not len(self.tag):
                raise exceptions.SyntaxException("Closing tag without opening tag: </%%%s>" % match.group(1), **self.exception_kwargs)
            elif self.tag[-1].keyword != match.group(1):
                raise exceptions.SyntaxException("Closing tag </%%%s> does not match tag: <%%%s>" % (match.group(1), self.tag[-1].keyword), **self.exception_kwargs)
            self.tag.pop()
            return True
        else:
            return False
            
    def match_end(self):
        match = self.match(r'\Z', re.S)
        if match:
            string = match.group()
            if string:
                return string
            else:
                return True
        else:
            return False
    
    def match_text(self):
        match = self.match(r"""
                (.*?)         # anything, followed by:
                (
                 (?<=\n)(?=[ \t]*(?=%|\#\#)) # an eval or line-based comment preceded by a consumed \n and whitespace
                 |
                 (?=\${)   # an expression
                 |
                 (?=\#\*) # multiline comment
                 |
                 (?=</?[%&])  # a substitution or block or call start or end
                                              # - don't consume
                 |
                 (\\\r?\n)         # an escaped newline  - throw away
                 |
                 \Z           # end of string
                )""", re.X | re.S)
        
        if match:
            text = match.group(1)
            self.append_node(parsetree.Text, text)
            return True
        else:
            return False
    
    def match_python_block(self):
        match = self.match(r"<%(!)?")
        if match:
            (line, pos) = (self.matched_lineno, self.matched_charpos)
            (text, end) = self.parse_until_text(r'%>')
            text = adjust_whitespace(text) + "\n"   # the trailing newline helps compiler.parse() not complain about indentation
            self.append_node(parsetree.Code, self.escape_code(text), match.group(1)=='!', lineno=line, pos=pos)
            return True
        else:
            return False
            
    def match_expression(self):
        match = self.match(r"\${")
        if match:
            (line, pos) = (self.matched_lineno, self.matched_charpos)
            (text, end) = self.parse_until_text(r'\|', r'}')
            if end == '|':
                (escapes, end) = self.parse_until_text(r'}')
            else:
                escapes = ""
            text = text.replace('\r\n', '\n')
            self.append_node(parsetree.Expression, self.escape_code(text), escapes.strip(), lineno=line, pos=pos)
            return True
        else:
            return False

    def match_control_line(self):
        match = self.match(r"(?<=^)[\t ]*(%|##)[\t ]*((?:(?:\\r?\n)|[^\r\n])*)(?:\r?\n|\Z)", re.M)
        if match:
            operator = match.group(1)
            text = match.group(2)
            if operator == '%':
                m2 = re.match(r'(end)?(\w+)\s*(.*)', text)
                if not m2:
                    raise exceptions.SyntaxException("Invalid control line: '%s'" % text, **self.exception_kwargs)
                (isend, keyword) = m2.group(1, 2)
                isend = (isend is not None)
                
                if isend:
                    if not len(self.control_line):
                        raise exceptions.SyntaxException("No starting keyword '%s' for '%s'" % (keyword, text), **self.exception_kwargs)
                    elif self.control_line[-1].keyword != keyword:
                        raise exceptions.SyntaxException("Keyword '%s' doesn't match keyword '%s'" % (text, self.control_line[-1].keyword), **self.exception_kwargs)
                self.append_node(parsetree.ControlLine, keyword, isend, self.escape_code(text))
            else:
                self.append_node(parsetree.Comment, text)
            return True
        else:
            return False

    def match_comment(self):
        """matches the multiline version of a comment"""
        match = self.match(r"<%doc>(.*?)</%doc>", re.S)
        if match:
            self.append_node(parsetree.Comment, match.group(1))
            return True
        else:
            return False
             

########NEW FILE########
__FILENAME__ = lookup
# lookup.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import os, stat, posixpath, re
from mako import exceptions, util
from mako.template import Template

try:
    import threading
except:
    import dummy_threading as threading
    
class TemplateCollection(object):
    def has_template(self, uri):
        try:
            self.get_template(uri)
            return True
        except exceptions.TemplateLookupException, e:
            return False
    def get_template(self, uri, relativeto=None):
        raise NotImplementedError()
    def filename_to_uri(self, uri, filename):
        """convert the given filename to a uri relative to this TemplateCollection."""
        return uri
        
    def adjust_uri(self, uri, filename):
        """adjust the given uri based on the calling filename.
        
        when this method is called from the runtime, the 'filename' parameter 
        is taken directly to the 'filename' attribute of the calling 
        template.  Therefore a custom TemplateCollection subclass can place any string 
        identifier desired in the "filename" parameter of the Template objects it constructs
        and have them come back here."""
        return uri
        
class TemplateLookup(TemplateCollection):
    def __init__(self, directories=None, module_directory=None, filesystem_checks=True, collection_size=-1, format_exceptions=False, 
    error_handler=None, disable_unicode=False, output_encoding=None, encoding_errors='strict', cache_type=None, cache_dir=None, cache_url=None, 
    modulename_callable=None, default_filters=None, buffer_filters=[], imports=None, input_encoding=None, preprocessor=None):
        if isinstance(directories, basestring):
            directories = [directories]        
        self.directories = [posixpath.normpath(d) for d in directories or []]
        self.module_directory = module_directory
        self.modulename_callable = modulename_callable
        self.filesystem_checks = filesystem_checks
        self.collection_size = collection_size
        self.template_args = {'format_exceptions':format_exceptions, 'error_handler':error_handler, 'disable_unicode':disable_unicode, 'output_encoding':output_encoding, 'encoding_errors':encoding_errors, 'input_encoding':input_encoding, 'module_directory':module_directory, 'cache_type':cache_type, 'cache_dir':cache_dir or module_directory, 'cache_url':cache_url, 'default_filters':default_filters, 'buffer_filters':buffer_filters,  'imports':imports, 'preprocessor':preprocessor}
        if collection_size == -1:
            self.__collection = {}
            self._uri_cache = {}
        else:
            self.__collection = util.LRUCache(collection_size)
            self._uri_cache = util.LRUCache(collection_size)
        self._mutex = threading.Lock()
        
    def get_template(self, uri):
        try:
            if self.filesystem_checks:
                return self.__check(uri, self.__collection[uri])
            else:
                return self.__collection[uri]
        except KeyError:
            u = re.sub(r'^\/+', '', uri)
            for dir in self.directories:
                srcfile = posixpath.normpath(posixpath.join(dir, u))
                if os.path.exists(srcfile):
                    return self.__load(srcfile, uri)
            else:
                raise exceptions.TopLevelLookupException("Cant locate template for uri '%s'" % uri)

    def adjust_uri(self, uri, relativeto):
        """adjust the given uri based on the calling filename."""
        
        if uri[0] != '/':
            if relativeto is not None:
                return posixpath.join(posixpath.dirname(relativeto), uri)
            else:
                return '/' + uri
        else:
            return uri
            
    
    def filename_to_uri(self, filename):
        try:
            return self._uri_cache[filename]
        except KeyError:
            value = self.__relativeize(filename)
            self._uri_cache[filename] = value
            return value
                    
    def __relativeize(self, filename):
        """return the portion of a filename that is 'relative' to the directories in this lookup."""
        filename = posixpath.normpath(filename)
        for dir in self.directories:
            if filename[0:len(dir)] == dir:
                return filename[len(dir):]
        else:
            return None
            
    def __load(self, filename, uri):
        self._mutex.acquire()
        try:
            try:
                # try returning from collection one more time in case concurrent thread already loaded
                return self.__collection[uri]
            except KeyError:
                pass
            try:
                self.__collection[uri] = Template(uri=uri, filename=posixpath.normpath(filename), lookup=self, module_filename=(self.modulename_callable is not None and self.modulename_callable(filename, uri) or None), **self.template_args)
                return self.__collection[uri]
            except:
                self.__collection.pop(uri, None)
                raise
        finally:
            self._mutex.release()
            
    def __check(self, uri, template):
        if template.filename is None:
            return template
        if not os.path.exists(template.filename):
            self.__collection.pop(uri, None)
            raise exceptions.TemplateLookupException("Cant locate template for uri '%s'" % uri)
        elif template.module._modified_time < os.stat(template.filename)[stat.ST_MTIME]:
            self.__collection.pop(uri, None)
            return self.__load(template.filename, uri)
        else:
            return template
            
    def put_string(self, uri, text):
        self.__collection[uri] = Template(text, lookup=self, uri=uri, **self.template_args)
    def put_template(self, uri, template):
        self.__collection[uri] = template
            

########NEW FILE########
__FILENAME__ = parsetree
# parsetree.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""defines the parse tree components for Mako templates."""

from mako import exceptions, ast, util, filters
import re

class Node(object):
    """base class for a Node in the parse tree."""
    def __init__(self, source, lineno, pos, filename):
        self.source = source
        self.lineno = lineno
        self.pos = pos
        self.filename = filename
        
    exception_kwargs = property(lambda self:{'source':self.source, 'lineno':self.lineno, 'pos':self.pos, 'filename':self.filename})
    
    def get_children(self):
        return []
    def accept_visitor(self, visitor):
        def traverse(node):
            for n in node.get_children():
                n.accept_visitor(visitor)
        method = getattr(visitor, "visit" + self.__class__.__name__, traverse)
        method(self)

class TemplateNode(Node):
    """a 'container' node that stores the overall collection of nodes."""
    def __init__(self, filename):
        super(TemplateNode, self).__init__('', 0, 0, filename)
        self.nodes = []
        self.page_attributes = {}
    def get_children(self):
        return self.nodes
    def __repr__(self):
        return "TemplateNode(%s, %s)" % (repr(self.page_attributes), repr(self.nodes))
        
class ControlLine(Node):
    """defines a control line, a line-oriented python line or end tag.
    
    % if foo:
        (markup)
    % endif
    """
    def __init__(self, keyword, isend, text, **kwargs):
        super(ControlLine, self).__init__(**kwargs)
        self.text = text
        self.keyword = keyword
        self.isend = isend
        self.is_primary = keyword in ['for','if', 'while', 'try']
        if self.isend:
            self._declared_identifiers = []
            self._undeclared_identifiers = []
        else:
            code = ast.PythonFragment(text, **self.exception_kwargs)
            (self._declared_identifiers, self._undeclared_identifiers) = (code.declared_identifiers, code.undeclared_identifiers)
    def declared_identifiers(self):
        return self._declared_identifiers
    def undeclared_identifiers(self):
        return self._undeclared_identifiers
    def is_ternary(self, keyword):
        """return true if the given keyword is a ternary keyword for this ControlLine"""
        return keyword in {
            'if':util.Set(['else', 'elif']),
            'try':util.Set(['except', 'finally']),
            'for':util.Set(['else'])
        }.get(self.keyword, [])
    def __repr__(self):
        return "ControlLine(%s, %s, %s, %s)" % (repr(self.keyword), repr(self.text), repr(self.isend), repr((self.lineno, self.pos)))

class Text(Node):
    """defines plain text in the template."""
    def __init__(self, content, **kwargs):
        super(Text, self).__init__(**kwargs)
        self.content = content
    def __repr__(self):
        return "Text(%s, %s)" % (repr(self.content), repr((self.lineno, self.pos)))
        
class Code(Node):
    """defines a Python code block, either inline or module level.
    
    inline:
    <%
        x = 12
    %>
    
    module level:
    <%!
        import logger
    %>
    
    """
    def __init__(self, text, ismodule, **kwargs):
        super(Code, self).__init__(**kwargs)
        self.text = text
        self.ismodule = ismodule
        self.code = ast.PythonCode(text, **self.exception_kwargs)
    def declared_identifiers(self):
        return self.code.declared_identifiers
    def undeclared_identifiers(self):
        return self.code.undeclared_identifiers
    def __repr__(self):
        return "Code(%s, %s, %s)" % (repr(self.text), repr(self.ismodule), repr((self.lineno, self.pos)))
        
class Comment(Node):
    """defines a comment line.
    
    # this is a comment
    
    """
    def __init__(self, text, **kwargs):
        super(Comment, self).__init__(**kwargs)
        self.text = text
    def __repr__(self):
        return "Comment(%s, %s)" % (repr(self.text), repr((self.lineno, self.pos)))
        
class Expression(Node):
    """defines an inline expression.
    
    ${x+y}
    
    """
    def __init__(self, text, escapes, **kwargs):
        super(Expression, self).__init__(**kwargs)
        self.text = text
        self.escapes = escapes
        self.escapes_code = ast.ArgumentList(escapes, **self.exception_kwargs)
        self.code = ast.PythonCode(text, **self.exception_kwargs)
    def declared_identifiers(self):
        return []
    def undeclared_identifiers(self):
        # TODO: make the "filter" shortcut list configurable at parse/gen time
        return self.code.undeclared_identifiers.union(self.escapes_code.undeclared_identifiers.difference(util.Set(filters.DEFAULT_ESCAPES.keys())))
    def __repr__(self):
        return "Expression(%s, %s, %s)" % (repr(self.text), repr(self.escapes_code.args), repr((self.lineno, self.pos)))
        
class _TagMeta(type):
    """metaclass to allow Tag to produce a subclass according to its keyword"""
    _classmap = {}
    def __init__(cls, clsname, bases, dict):
        if cls.__keyword__ is not None:
            cls._classmap[cls.__keyword__] = cls
            super(_TagMeta, cls).__init__(clsname, bases, dict)
    def __call__(cls, keyword, attributes, **kwargs):
        try:
            cls = _TagMeta._classmap[keyword]
        except KeyError:
            raise exceptions.CompileException("No such tag: '%s'" % keyword, source=kwargs['source'], lineno=kwargs['lineno'], pos=kwargs['pos'], filename=kwargs['filename'])
        return type.__call__(cls, keyword, attributes, **kwargs)
        
class Tag(Node):
    """abstract base class for tags.
    
    <%sometag/>
    
    <%someothertag>
        stuff
    </%someothertag>
    """
    __metaclass__ = _TagMeta
    __keyword__ = None
    def __init__(self, keyword, attributes, expressions, nonexpressions, required, **kwargs):
        """construct a new Tag instance.
        
        this constructor not called directly, and is only called by subclasses.
        
        keyword - the tag keyword
        
        attributes - raw dictionary of attribute key/value pairs
        
        expressions - a util.Set of identifiers that are legal attributes, which can also contain embedded expressions
        
        nonexpressions - a util.Set of identifiers that are legal attributes, which cannot contain embedded expressions
        
        **kwargs - other arguments passed to the Node superclass (lineno, pos)"""
        super(Tag, self).__init__(**kwargs)
        self.keyword = keyword
        self.attributes = attributes
        self._parse_attributes(expressions, nonexpressions)
        missing = [r for r in required if r not in self.parsed_attributes]
        if len(missing):
            raise exceptions.CompileException("Missing attribute(s): %s" % ",".join([repr(m) for m in missing]), **self.exception_kwargs)
        self.parent = None
        self.nodes = []
    def is_root(self):
        return self.parent is None
    def get_children(self):
        return self.nodes
    def _parse_attributes(self, expressions, nonexpressions):
        undeclared_identifiers = util.Set()
        self.parsed_attributes = {}
        for key in self.attributes:
            if key in expressions:
                expr = []
                for x in re.split(r'(\${.+?})', self.attributes[key]):
                    m = re.match(r'^\${(.+?)}$', x)
                    if m:
                        code = ast.PythonCode(m.group(1), **self.exception_kwargs)
                        undeclared_identifiers = undeclared_identifiers.union(code.undeclared_identifiers)
                        expr.append(m.group(1))
                    else:
                        if x:
                            expr.append(repr(x))
                self.parsed_attributes[key] = " + ".join(expr)
            elif key in nonexpressions:
                if re.search(r'${.+?}', self.attributes[key]):
                    raise exceptions.CompileException("Attibute '%s' in tag '%s' does not allow embedded expressions"  %(key, self.keyword), **self.exception_kwargs)
                self.parsed_attributes[key] = repr(self.attributes[key])
            else:
                raise exceptions.CompileException("Invalid attribute for tag '%s': '%s'" %(self.keyword, key), **self.exception_kwargs)
        self.expression_undeclared_identifiers = undeclared_identifiers
    def declared_identifiers(self):
        return []
    def undeclared_identifiers(self):
        return self.expression_undeclared_identifiers
    def __repr__(self):
        return "%s(%s, %s, %s, %s)" % (self.__class__.__name__, repr(self.keyword), repr(self.attributes), repr((self.lineno, self.pos)), repr([repr(x) for x in self.nodes]))
        
class IncludeTag(Tag):
    __keyword__ = 'include'
    def __init__(self, keyword, attributes, **kwargs):
        super(IncludeTag, self).__init__(keyword, attributes, ('file', 'import', 'args'), (), ('file',), **kwargs)
        self.page_args = ast.PythonCode("__DUMMY(%s)" % attributes.get('args', ''), **self.exception_kwargs)
    def declared_identifiers(self):
        return []
    def undeclared_identifiers(self):
        identifiers = self.page_args.undeclared_identifiers.difference(util.Set(["__DUMMY"]))
        return identifiers.union(super(IncludeTag, self).undeclared_identifiers())
    
class NamespaceTag(Tag):
    __keyword__ = 'namespace'
    def __init__(self, keyword, attributes, **kwargs):
        super(NamespaceTag, self).__init__(keyword, attributes, (), ('name','inheritable','file','import','module'), (), **kwargs)
        self.name = attributes.get('name', '__anon_%s' % hex(abs(id(self))))
        if not 'name' in attributes and not 'import' in attributes:
            raise exceptions.CompileException("'name' and/or 'import' attributes are required for <%namespace>", **self.exception_kwargs)
    def declared_identifiers(self):
        return []

class TextTag(Tag):
    __keyword__ = 'text'
    def __init__(self, keyword, attributes, **kwargs):
        super(TextTag, self).__init__(keyword, attributes, (), ('filter'), (), **kwargs)
        self.filter_args = ast.ArgumentList(attributes.get('filter', ''), **self.exception_kwargs)
        
class DefTag(Tag):
    __keyword__ = 'def'
    def __init__(self, keyword, attributes, **kwargs):
        super(DefTag, self).__init__(keyword, attributes, ('buffered', 'cached', 'cache_key', 'cache_timeout', 'cache_type', 'cache_dir', 'cache_url'), ('name','filter'), ('name',), **kwargs)
        name = attributes['name']
        if re.match(r'^[\w_]+$',name):
            raise exceptions.CompileException("Missing parenthesis in %def", **self.exception_kwargs)
        self.function_decl = ast.FunctionDecl("def " + name + ":pass", **self.exception_kwargs)
        self.name = self.function_decl.funcname
        self.filter_args = ast.ArgumentList(attributes.get('filter', ''), **self.exception_kwargs)
    def declared_identifiers(self):
        return self.function_decl.argnames
    def undeclared_identifiers(self):
        res = []
        for c in self.function_decl.defaults:
            res += list(ast.PythonCode(c, **self.exception_kwargs).undeclared_identifiers)
        return res + list(self.filter_args.undeclared_identifiers.difference(util.Set(filters.DEFAULT_ESCAPES.keys())))

class CallTag(Tag):
    __keyword__ = 'call'
    def __init__(self, keyword, attributes, **kwargs):
        super(CallTag, self).__init__(keyword, attributes, ('args'), ('expr',), ('expr',), **kwargs)
        self.code = ast.PythonCode(attributes['expr'], **self.exception_kwargs)
        self.body_decl = ast.FunctionArgs(attributes.get('args', ''), **self.exception_kwargs)
    def declared_identifiers(self):
        return self.code.declared_identifiers.union(self.body_decl.argnames)
    def undeclared_identifiers(self):
        return self.code.undeclared_identifiers

class InheritTag(Tag):
    __keyword__ = 'inherit'
    def __init__(self, keyword, attributes, **kwargs):
        super(InheritTag, self).__init__(keyword, attributes, ('file',), (), ('file',), **kwargs)

class PageTag(Tag):
    __keyword__ = 'page'
    def __init__(self, keyword, attributes, **kwargs):
        super(PageTag, self).__init__(keyword, attributes, ('cached', 'cache_key', 'cache_timeout', 'cache_type', 'cache_dir', 'cache_url', 'args', 'expression_filter'), (), (), **kwargs)
        self.body_decl = ast.FunctionArgs(attributes.get('args', ''), **self.exception_kwargs)
        self.filter_args = ast.ArgumentList(attributes.get('expression_filter', ''), **self.exception_kwargs)
    def declared_identifiers(self):
        return self.body_decl.argnames
        
    

########NEW FILE########
__FILENAME__ = pygen
# pygen.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""utilities for generating and formatting literal Python code."""

import re, string
from StringIO import StringIO

class PythonPrinter(object):
    def __init__(self, stream):
        # indentation counter
        self.indent = 0
        
        # a stack storing information about why we incremented 
        # the indentation counter, to help us determine if we
        # should decrement it
        self.indent_detail = []
        
        # the string of whitespace multiplied by the indent
        # counter to produce a line
        self.indentstring = "    "
        
        # the stream we are writing to
        self.stream = stream
        
        # a list of lines that represents a buffered "block" of code,
        # which can be later printed relative to an indent level 
        self.line_buffer = []
        
        self.in_indent_lines = False
        
        self._reset_multi_line_flags()

    def write(self, text):
        self.stream.write(text)
        
    def write_indented_block(self, block):
        """print a line or lines of python which already contain indentation.
        
        The indentation of the total block of lines will be adjusted to that of
        the current indent level.""" 
        self.in_indent_lines = False
        for l in re.split(r'\r?\n', block):
            self.line_buffer.append(l)
    
    def writelines(self, *lines):
        """print a series of lines of python."""
        for line in lines:
            self.writeline(line)
                
    def writeline(self, line):
        """print a line of python, indenting it according to the current indent level.
        
        this also adjusts the indentation counter according to the content of the line."""

        if not self.in_indent_lines:
            self._flush_adjusted_lines()
            self.in_indent_lines = True

        decreased_indent = False
    
        if (line is None or 
            re.match(r"^\s*#",line) or
            re.match(r"^\s*$", line)
            ):
            hastext = False
        else:
            hastext = True

        is_comment = line and len(line) and line[0] == '#'
        
        # see if this line should decrease the indentation level
        if (not decreased_indent and 
            not is_comment and 
            (not hastext or self._is_unindentor(line))
            ):
            
            if self.indent > 0: 
                self.indent -=1
                # if the indent_detail stack is empty, the user
                # probably put extra closures - the resulting
                # module wont compile.  
                if len(self.indent_detail) == 0:  
                    raise "Too many whitespace closures"
                self.indent_detail.pop()
        
        if line is None:
            return
                
        # write the line
        self.stream.write(self._indent_line(line) + "\n")
        
        # see if this line should increase the indentation level.
        # note that a line can both decrase (before printing) and 
        # then increase (after printing) the indentation level.

        if re.search(r":[ \t]*(?:#.*)?$", line):
            # increment indentation count, and also
            # keep track of what the keyword was that indented us,
            # if it is a python compound statement keyword
            # where we might have to look for an "unindent" keyword
            match = re.match(r"^\s*(if|try|elif|while|for)", line)
            if match:
                # its a "compound" keyword, so we will check for "unindentors"
                indentor = match.group(1)
                self.indent +=1
                self.indent_detail.append(indentor)
            else:
                indentor = None
                # its not a "compound" keyword.  but lets also
                # test for valid Python keywords that might be indenting us,
                # else assume its a non-indenting line
                m2 = re.match(r"^\s*(def|class|else|elif|except|finally)", line)
                if m2:
                    self.indent += 1
                    self.indent_detail.append(indentor)

    def close(self):
        """close this printer, flushing any remaining lines."""
        self._flush_adjusted_lines()
    
    def _is_unindentor(self, line):
        """return true if the given line is an 'unindentor', relative to the last 'indent' event received."""
                
        # no indentation detail has been pushed on; return False
        if len(self.indent_detail) == 0: 
            return False

        indentor = self.indent_detail[-1]
        
        # the last indent keyword we grabbed is not a 
        # compound statement keyword; return False
        if indentor is None: 
            return False
        
        # if the current line doesnt have one of the "unindentor" keywords,
        # return False
        match = re.match(r"^\s*(else|elif|except|finally).*\:", line)
        if not match: 
            return False
        
        # whitespace matches up, we have a compound indentor,
        # and this line has an unindentor, this
        # is probably good enough
        return True
        
        # should we decide that its not good enough, heres
        # more stuff to check.
        #keyword = match.group(1)
        
        # match the original indent keyword 
        #for crit in [
        #   (r'if|elif', r'else|elif'),
        #   (r'try', r'except|finally|else'),
        #   (r'while|for', r'else'),
        #]:
        #   if re.match(crit[0], indentor) and re.match(crit[1], keyword): return True
        
        #return False
        
    def _indent_line(self, line, stripspace = ''):
        """indent the given line according to the current indent level.
        
        stripspace is a string of space that will be truncated from the start of the line
        before indenting."""
        return re.sub(r"^%s" % stripspace, self.indentstring * self.indent, line)

    def _reset_multi_line_flags(self):
        """reset the flags which would indicate we are in a backslashed or triple-quoted section."""
        (self.backslashed, self.triplequoted) = (False, False) 
        
    def _in_multi_line(self, line):
        """return true if the given line is part of a multi-line block, via backslash or triple-quote."""
        # we are only looking for explicitly joined lines here,
        # not implicit ones (i.e. brackets, braces etc.).  this is just
        # to guard against the possibility of modifying the space inside 
        # of a literal multiline string with unfortunately placed whitespace
         
        current_state = (self.backslashed or self.triplequoted) 
                        
        if re.search(r"\\$", line):
            self.backslashed = True
        else:
            self.backslashed = False
            
        triples = len(re.findall(r"\"\"\"|\'\'\'", line))
        if triples == 1 or triples % 2 != 0:
            self.triplequoted = not self.triplequoted
            
        return current_state

    def _flush_adjusted_lines(self):
        stripspace = None
        self._reset_multi_line_flags()
        
        for entry in self.line_buffer:
            if self._in_multi_line(entry):
                self.stream.write(entry + "\n")
            else:
                entry = string.expandtabs(entry)
                if stripspace is None and re.search(r"^[ \t]*[^# \t]", entry):
                    stripspace = re.match(r"^([ \t]*)", entry).group(1)
                self.stream.write(self._indent_line(entry, stripspace) + "\n")
            
        self.line_buffer = []
        self._reset_multi_line_flags()


def adjust_whitespace(text):
    """remove the left-whitespace margin of a block of Python code."""
    state = [False, False]
    (backslashed, triplequoted) = (0, 1)

    def in_multi_line(line):
        start_state = (state[backslashed] or state[triplequoted])
        
        if re.search(r"\\$", line):
            state[backslashed] = True
        else:
            state[backslashed] = False
        
        def match(reg, t):
            m = re.match(reg, t)
            if m:
                return m, t[len(m.group(0)):]
            else:
                return None, t
                
        while line:
            if state[triplequoted]:
                m, line = match(r"%s" % state[triplequoted], line)
                if m:
                    state[triplequoted] = False
                else:
                    m, line = match(r".*?(?=%s|$)" % state[triplequoted], line)
            else:
                m, line = match(r'#', line)
                if m:
                    return start_state
                
                m, line = match(r"\"\"\"|\'\'\'", line)
                if m:
                    state[triplequoted] = m.group(0)
                    continue

                m, line = match(r".*?(?=\"\"\"|\'\'\'|#|$)", line)
            
        return start_state

    def _indent_line(line, stripspace = ''):
        return re.sub(r"^%s" % stripspace, '', line)

    lines = []
    stripspace = None

    for line in re.split(r'\r?\n', text):
        if in_multi_line(line):
            lines.append(line)
        else:
            line = string.expandtabs(line)
            if stripspace is None and re.search(r"^[ \t]*[^# \t]", line):
                stripspace = re.match(r"^([ \t]*)", line).group(1)
            lines.append(_indent_line(line, stripspace))
    return "\n".join(lines)

########NEW FILE########
__FILENAME__ = pyparser
# ast.py
# Copyright (C) Mako developers
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Handles parsing of Python code.

Parsing to AST is done via _ast on Python > 2.5, otherwise the compiler
module is used.
"""

import sys
from StringIO import StringIO
from mako import exceptions, util

# words that cannot be assigned to (notably smaller than the total keys in __builtins__)
reserved = set(['True', 'False', 'None'])

new_ast = sys.version_info > (2, 5)

if new_ast:
    import _ast
    util.restore__ast(_ast)
    import _ast_util
else:
    from compiler import parse as compiler_parse
    from compiler import visitor


def parse(code, mode='exec', **exception_kwargs):
    """Parse an expression into AST"""
    try:
        if new_ast:
            return _ast_util.parse(code, '<unknown>', mode)
        else:
            return compiler_parse(code, mode)
    except Exception, e:
        raise exceptions.SyntaxException("(%s) %s (%s)" % (e.__class__.__name__, str(e), repr(code[0:50])), **exception_kwargs)


if new_ast:
    class FindIdentifiers(_ast_util.NodeVisitor):
        def __init__(self, listener, **exception_kwargs):
            self.in_function = False
            self.in_assign_targets = False
            self.local_ident_stack = {}
            self.listener = listener
            self.exception_kwargs = exception_kwargs
        def _add_declared(self, name):
            if not self.in_function:
                self.listener.declared_identifiers.add(name)
        def visit_ClassDef(self, node):
            self._add_declared(node.name)
        def visit_Assign(self, node):
            # flip around the visiting of Assign so the expression gets evaluated first, 
            # in the case of a clause like "x=x+5" (x is undeclared)
            self.visit(node.value)
            in_a = self.in_assign_targets
            self.in_assign_targets = True
            for n in node.targets:
                self.visit(n)
            self.in_assign_targets = in_a
        def visit_FunctionDef(self, node):
            self._add_declared(node.name)
            # push function state onto stack.  dont log any
            # more identifiers as "declared" until outside of the function,
            # but keep logging identifiers as "undeclared".
            # track argument names in each function header so they arent counted as "undeclared"
            saved = {}
            inf = self.in_function
            self.in_function = True
            for arg in node.args.args:
                if arg.id in self.local_ident_stack:
                    saved[arg.id] = True
                else:
                    self.local_ident_stack[arg.id] = True
            for n in node.body:
                self.visit(n)
            self.in_function = inf
            for arg in node.args.args:
                if arg.id not in saved:
                    del self.local_ident_stack[arg.id]
        def visit_For(self, node):
            # flip around visit
            self.visit(node.iter)
            self.visit(node.target)
            for statement in node.body:
                self.visit(statement)
            for statement in node.orelse:
                self.visit(statement)
        def visit_Name(self, node):
            if isinstance(node.ctx, _ast.Store):
                self._add_declared(node.id)
            if node.id not in reserved and node.id not in self.listener.declared_identifiers and node.id not in self.local_ident_stack:
                self.listener.undeclared_identifiers.add(node.id)
        def visit_Import(self, node):
            for name in node.names:
                if name.asname is not None:
                    self._add_declared(name.asname)
                else:
                    self._add_declared(name.name.split('.')[0])
        def visit_ImportFrom(self, node):
            for name in node.names:
                if name.asname is not None:
                    self._add_declared(name.asname)
                else:
                    if name.name == '*':
                        raise exceptions.CompileException("'import *' is not supported, since all identifier names must be explicitly declared.  Please use the form 'from <modulename> import <name1>, <name2>, ...' instead.", **self.exception_kwargs)
                    self._add_declared(name.name)

    class FindTuple(_ast_util.NodeVisitor):
        def __init__(self, listener, code_factory, **exception_kwargs):
            self.listener = listener
            self.exception_kwargs = exception_kwargs
            self.code_factory = code_factory
        def visit_Tuple(self, node):
            for n in node.elts:
                p = self.code_factory(n, **self.exception_kwargs)
                self.listener.codeargs.append(p)
                self.listener.args.append(ExpressionGenerator(n).value())
                self.listener.declared_identifiers = self.listener.declared_identifiers.union(p.declared_identifiers)
                self.listener.undeclared_identifiers = self.listener.undeclared_identifiers.union(p.undeclared_identifiers)

    class ParseFunc(_ast_util.NodeVisitor):
        def __init__(self, listener, **exception_kwargs):
            self.listener = listener
            self.exception_kwargs = exception_kwargs
        def visit_FunctionDef(self, node):
            self.listener.funcname = node.name
            argnames = [arg.id for arg in node.args.args]
            if node.args.vararg:
                argnames.append(node.args.vararg)
            if node.args.kwarg:
                argnames.append(node.args.kwarg)
            self.listener.argnames = argnames
            self.listener.defaults = node.args.defaults # ast
            self.listener.varargs = node.args.vararg
            self.listener.kwargs = node.args.kwarg

    class ExpressionGenerator(object):
        def __init__(self, astnode):
            self.generator = _ast_util.SourceGenerator(' ' * 4)
            self.generator.visit(astnode)
        def value(self):
            return ''.join(self.generator.result)
else:
    class FindIdentifiers(object):
        def __init__(self, listener, **exception_kwargs):
            self.in_function = False
            self.local_ident_stack = {}
            self.listener = listener
            self.exception_kwargs = exception_kwargs
        def _add_declared(self, name):
            if not self.in_function:
                self.listener.declared_identifiers.add(name)
        def visitClass(self, node, *args):
            self._add_declared(node.name)
        def visitAssName(self, node, *args):
            self._add_declared(node.name)
        def visitAssign(self, node, *args):
            # flip around the visiting of Assign so the expression gets evaluated first, 
            # in the case of a clause like "x=x+5" (x is undeclared)
            self.visit(node.expr, *args)
            for n in node.nodes:
                self.visit(n, *args)
        def visitFunction(self,node, *args):
            self._add_declared(node.name)
            # push function state onto stack.  dont log any
            # more identifiers as "declared" until outside of the function,
            # but keep logging identifiers as "undeclared".
            # track argument names in each function header so they arent counted as "undeclared"
            saved = {}
            inf = self.in_function
            self.in_function = True
            for arg in node.argnames:
                if arg in self.local_ident_stack:
                    saved[arg] = True
                else:
                    self.local_ident_stack[arg] = True
            for n in node.getChildNodes():
                self.visit(n, *args)
            self.in_function = inf
            for arg in node.argnames:
                if arg not in saved:
                    del self.local_ident_stack[arg]
        def visitFor(self, node, *args):
            # flip around visit
            self.visit(node.list, *args)
            self.visit(node.assign, *args)
            self.visit(node.body, *args)
        def visitName(self, node, *args):
            if node.name not in reserved and node.name not in self.listener.declared_identifiers and node.name not in self.local_ident_stack:
                self.listener.undeclared_identifiers.add(node.name)
        def visitImport(self, node, *args):
            for (mod, alias) in node.names:
                if alias is not None:
                    self._add_declared(alias)
                else:
                    self._add_declared(mod.split('.')[0])
        def visitFrom(self, node, *args):
            for (mod, alias) in node.names:
                if alias is not None:
                    self._add_declared(alias)
                else:
                    if mod == '*':
                        raise exceptions.CompileException("'import *' is not supported, since all identifier names must be explicitly declared.  Please use the form 'from <modulename> import <name1>, <name2>, ...' instead.", **self.exception_kwargs)
                    self._add_declared(mod)
        def visit(self, expr):
            visitor.walk(expr, self) #, walker=walker())

    class FindTuple(object):
        def __init__(self, listener, code_factory, **exception_kwargs):
            self.listener = listener
            self.exception_kwargs = exception_kwargs
            self.code_factory = code_factory
        def visitTuple(self, node, *args):
            for n in node.nodes:
                p = self.code_factory(n, **self.exception_kwargs)
                self.listener.codeargs.append(p)
                self.listener.args.append(ExpressionGenerator(n).value())
                self.listener.declared_identifiers = self.listener.declared_identifiers.union(p.declared_identifiers)
                self.listener.undeclared_identifiers = self.listener.undeclared_identifiers.union(p.undeclared_identifiers)
        def visit(self, expr):
            visitor.walk(expr, self) #, walker=walker())

    class ParseFunc(object):
        def __init__(self, listener, **exception_kwargs):
            self.listener = listener
            self.exception_kwargs = exception_kwargs
        def visitFunction(self, node, *args):
            self.listener.funcname = node.name
            self.listener.argnames = node.argnames
            self.listener.defaults = node.defaults
            self.listener.varargs = node.varargs
            self.listener.kwargs = node.kwargs
        def visit(self, expr):
            visitor.walk(expr, self)

    class ExpressionGenerator(object):
        """given an AST node, generates an equivalent literal Python expression."""
        def __init__(self, astnode):
            self.buf = StringIO()
            visitor.walk(astnode, self) #, walker=walker())
        def value(self):
            return self.buf.getvalue()        
        def operator(self, op, node, *args):
            self.buf.write("(")
            self.visit(node.left, *args)
            self.buf.write(" %s " % op)
            self.visit(node.right, *args)
            self.buf.write(")")
        def booleanop(self, op, node, *args):
            self.visit(node.nodes[0])
            for n in node.nodes[1:]:
                self.buf.write(" " + op + " ")
                self.visit(n, *args)
        def visitConst(self, node, *args):
            self.buf.write(repr(node.value))
        def visitAssName(self, node, *args):
            # TODO: figure out OP_ASSIGN, other OP_s
            self.buf.write(node.name)
        def visitName(self, node, *args):
            self.buf.write(node.name)
        def visitMul(self, node, *args):
            self.operator("*", node, *args)
        def visitAnd(self, node, *args):
            self.booleanop("and", node, *args)
        def visitOr(self, node, *args):
            self.booleanop("or", node, *args)
        def visitBitand(self, node, *args):
            self.booleanop("&", node, *args)
        def visitBitor(self, node, *args):
            self.booleanop("|", node, *args)
        def visitBitxor(self, node, *args):
            self.booleanop("^", node, *args)
        def visitAdd(self, node, *args):
            self.operator("+", node, *args)
        def visitGetattr(self, node, *args):
            self.visit(node.expr, *args)
            self.buf.write(".%s" % node.attrname)
        def visitSub(self, node, *args):
            self.operator("-", node, *args)
        def visitNot(self, node, *args):
            self.buf.write("not ")
            self.visit(node.expr)
        def visitDiv(self, node, *args):
            self.operator("/", node, *args)
        def visitFloorDiv(self, node, *args):
            self.operator("//", node, *args)
        def visitSubscript(self, node, *args):
            self.visit(node.expr)
            self.buf.write("[")
            [self.visit(x) for x in node.subs]
            self.buf.write("]")
        def visitUnarySub(self, node, *args):
            self.buf.write("-")
            self.visit(node.expr)
        def visitUnaryAdd(self, node, *args):
            self.buf.write("-")
            self.visit(node.expr)
        def visitSlice(self, node, *args):
            self.visit(node.expr)
            self.buf.write("[")
            if node.lower is not None:
                self.visit(node.lower)
            self.buf.write(":")
            if node.upper is not None:
                self.visit(node.upper)
            self.buf.write("]")
        def visitDict(self, node):
            self.buf.write("{")
            c = node.getChildren()
            for i in range(0, len(c), 2):
                self.visit(c[i])
                self.buf.write(": ")
                self.visit(c[i+1])
                if i<len(c) -2:
                    self.buf.write(", ")
            self.buf.write("}")
        def visitTuple(self, node):
            self.buf.write("(")
            c = node.getChildren()
            for i in range(0, len(c)):
                self.visit(c[i])
                if i<len(c) - 1:
                    self.buf.write(", ")
            self.buf.write(")")
        def visitList(self, node):
            self.buf.write("[")
            c = node.getChildren()
            for i in range(0, len(c)):
                self.visit(c[i])
                if i<len(c) - 1:
                    self.buf.write(", ")
            self.buf.write("]")
        def visitListComp(self, node):
            self.buf.write("[")
            self.visit(node.expr)
            self.buf.write(" ")
            for n in node.quals:
                self.visit(n)
            self.buf.write("]")
        def visitListCompFor(self, node):
            self.buf.write(" for ")
            self.visit(node.assign)
            self.buf.write(" in ")
            self.visit(node.list)
            for n in node.ifs:
                self.visit(n)
        def visitListCompIf(self, node):
            self.buf.write(" if ")
            self.visit(node.test)
        def visitCompare(self, node):
            self.visit(node.expr)
            for tup in node.ops:
                self.buf.write(tup[0])
                self.visit(tup[1])
        def visitCallFunc(self, node, *args):
            self.visit(node.node)
            self.buf.write("(")
            if len(node.args):
                self.visit(node.args[0])
                for a in node.args[1:]:
                    self.buf.write(", ")
                    self.visit(a)
            self.buf.write(")")

    class walker(visitor.ASTVisitor):
        def dispatch(self, node, *args):
            print "Node:", str(node)
            #print "dir:", dir(node)
            return visitor.ASTVisitor.dispatch(self, node, *args)

########NEW FILE########
__FILENAME__ = runtime
# runtime.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""provides runtime services for templates, including Context, Namespace, and various helper functions."""

from mako import exceptions, util
import inspect, sys
import __builtin__

class Context(object):
    """provides runtime namespace, output buffer, and various callstacks for templates."""
    def __init__(self, buffer, **data):
        self._buffer_stack = [buffer]
        self._data = dict(__builtin__.__dict__)
        self._data.update(data)
        self._kwargs = data.copy()
        self._with_template = None
        self.namespaces = {}
        
        # "capture" function which proxies to the generic "capture" function
        self._data['capture'] = lambda x, *args, **kwargs: capture(self, x, *args, **kwargs)
        
        # "caller" stack used by def calls with content
        self.caller_stack = self._data['caller'] = CallerStack()
        
    lookup = property(lambda self:self._with_template.lookup)
    kwargs = property(lambda self:self._kwargs.copy())
    
    def push_caller(self, caller):
        self.caller_stack.append(caller)
        
    def pop_caller(self):
        del self.caller_stack[-1]
        
    def keys(self):
        return self._data.keys()
        
    def __getitem__(self, key):
        return self._data[key]

    def _push_writer(self):
        """push a capturing buffer onto this Context and return the new Writer function."""
        
        buf = util.FastEncodingBuffer()
        self._buffer_stack.append(buf)
        return buf.write

    def _pop_buffer_and_writer(self):
        """pop the most recent capturing buffer from this Context 
        and return the current writer after the pop.
        
        """

        buf = self._buffer_stack.pop()
        return buf, self._buffer_stack[-1].write
        
    def _push_buffer(self):
        """push a capturing buffer onto this Context."""
        
        self._push_writer()
        
    def _pop_buffer(self):
        """pop the most recent capturing buffer from this Context."""
        
        return self._buffer_stack.pop()
        
    def get(self, key, default=None):
        return self._data.get(key, default)
        
    def write(self, string):
        """write a string to this Context's underlying output buffer."""
        
        self._buffer_stack[-1].write(string)
        
    def writer(self):
        """return the current writer function"""

        return self._buffer_stack[-1].write

    def _copy(self):
        c = Context.__new__(Context)
        c._buffer_stack = self._buffer_stack
        c._data = self._data.copy()
        c._kwargs = self._kwargs
        c._with_template = self._with_template
        c.namespaces = self.namespaces
        c.caller_stack = self.caller_stack
        return c
    def locals_(self, d):
        """create a new Context with a copy of this Context's current state, updated with the given dictionary."""
        if len(d) == 0:
            return self
        c = self._copy()
        c._data.update(d)
        return c
    def _clean_inheritance_tokens(self):
        """create a new copy of this Context with tokens related to inheritance state removed."""
        c = self._copy()
        x = c._data
        x.pop('self', None)
        x.pop('parent', None)
        x.pop('next', None)
        return c

class CallerStack(list):
    def __init__(self):
        self.nextcaller = None
    def __nonzero__(self):
        return self._get_caller() and True or False
    def _get_caller(self):
        return self[-1]
    def __getattr__(self, key):
        return getattr(self._get_caller(), key)
    def _push_frame(self):
        self.append(self.nextcaller or None)
        self.nextcaller = None
    def _pop_frame(self):
        self.nextcaller = self.pop()
        
        
class Undefined(object):
    """represents an undefined value in a template."""
    def __str__(self):
        raise NameError("Undefined")
    def __nonzero__(self):
        return False

UNDEFINED = Undefined()

class _NSAttr(object):
    def __init__(self, parent):
        self.__parent = parent
    def __getattr__(self, key):
        ns = self.__parent
        while ns:
            if hasattr(ns.module, key):
                return getattr(ns.module, key)
            else:
                ns = ns.inherits
        raise AttributeError(key)    
    
class Namespace(object):
    """provides access to collections of rendering methods, which can be local, from other templates, or from imported modules"""
    def __init__(self, name, context, module=None, template=None, templateuri=None, callables=None, inherits=None, populate_self=True, calling_uri=None):
        self.name = name
        if module is not None:
            mod = __import__(module)
            for token in module.split('.')[1:]:
                mod = getattr(mod, token)
            self._module = mod
        else:
            self._module = None
        if templateuri is not None:
            self.template = _lookup_template(context, templateuri, calling_uri)
            self._templateuri = self.template.module._template_uri
        else:
            self.template = template
            if self.template is not None:
                self._templateuri = self.template.module._template_uri
        self.context = context
        self.inherits = inherits
        if callables is not None:
            self.callables = dict([(c.func_name, c) for c in callables])
        else:
            self.callables = None
        if populate_self and self.template is not None:
            (lclcallable, lclcontext) = _populate_self_namespace(context, self.template, self_ns=self)
        
    module = property(lambda s:s._module or s.template.module)
    filename = property(lambda s:s._module and s._module.__file__ or s.template.filename)
    uri = property(lambda s:s.template.uri)
    
    def attr(self):
        if not hasattr(self, '_attr'):
            self._attr = _NSAttr(self)
        return self._attr
    attr = property(attr)

    def get_namespace(self, uri):
        """return a namespace corresponding to the given template uri.
        
        if a relative uri, it is adjusted to that of the template of this namespace"""
        key = (self, uri)
        if self.context.namespaces.has_key(key):
            return self.context.namespaces[key]
        else:
            ns = Namespace(uri, self.context._copy(), templateuri=uri, calling_uri=self._templateuri) 
            self.context.namespaces[key] = ns
            return ns
    
    def get_template(self, uri):
        return _lookup_template(self.context, uri, self._templateuri)
        
    def get_cached(self, key, **kwargs):
        if self.template:
            if self.template.cache_dir:
                kwargs.setdefault('data_dir', self.template.cache_dir)
            if self.template.cache_type:
                kwargs.setdefault('type', self.template.cache_type)
            if self.template.cache_url:
                kwargs.setdefault('url', self.template.cache_url)
        return self.template.module._template_cache.get(key, **kwargs)
        
    def include_file(self, uri, **kwargs):
        """include a file at the given uri"""
        _include_file(self.context, uri, self._templateuri, **kwargs)
        
    def _populate(self, d, l):
        for ident in l:
            if ident == '*':
                for (k, v) in self._get_star():
                    d[k] = v
            else:
                d[ident] = getattr(self, ident)
    
    def _get_star(self):
        if self.callables:
            for key in self.callables:
                yield (key, self.callables[key])
        if self.template:
            def get(key):
                callable_ = self.template.get_def(key).callable_
                return lambda *args, **kwargs:callable_(self.context, *args, **kwargs)
            for k in self.template.module._exports:
                yield (k, get(k))
        if self._module:
            def get(key):
                callable_ = getattr(self._module, key)
                return lambda *args, **kwargs:callable_(self.context, *args, **kwargs)
            for k in dir(self._module):
                if k[0] != '_':
                    yield (k, get(k))
                            
    def __getattr__(self, key):
        if self.callables and key in self.callables:
            return self.callables[key]

        if self.template and self.template.has_def(key):
            callable_ = self.template.get_def(key).callable_
            return lambda *args, **kwargs:callable_(self.context, *args, **kwargs)

        if self._module and hasattr(self._module, key):
            callable_ = getattr(self._module, key)
            return lambda *args, **kwargs:callable_(self.context, *args, **kwargs)

        if self.inherits is not None:
            return getattr(self.inherits, key)
        raise exceptions.RuntimeException("Namespace '%s' has no member '%s'" % (self.name, key))

def supports_caller(func):
    """apply a caller_stack compatibility decorator to a plain Python function."""
    def wrap_stackframe(context,  *args, **kwargs):
        context.caller_stack._push_frame()
        try:
            return func(context, *args, **kwargs)
        finally:
            context.caller_stack._pop_frame()
    return wrap_stackframe
        
def capture(context, callable_, *args, **kwargs):
    """execute the given template def, capturing the output into a buffer."""
    if not callable(callable_):
        raise exceptions.RuntimeException("capture() function expects a callable as its argument (i.e. capture(func, *args, **kwargs))")
    context._push_buffer()
    try:
        callable_(*args, **kwargs)
    finally:
        buf = context._pop_buffer()
    return buf.getvalue()
        
def _include_file(context, uri, calling_uri, **kwargs):
    """locate the template from the given uri and include it in the current output."""
    template = _lookup_template(context, uri, calling_uri)
    (callable_, ctx) = _populate_self_namespace(context._clean_inheritance_tokens(), template)
    callable_(ctx, **_kwargs_for_callable(callable_, context._data, **kwargs))
        
def _inherit_from(context, uri, calling_uri):
    """called by the _inherit method in template modules to set up the inheritance chain at the start
    of a template's execution."""
    if uri is None:
        return None
    template = _lookup_template(context, uri, calling_uri)
    self_ns = context['self']
    ih = self_ns
    while ih.inherits is not None:
        ih = ih.inherits
    lclcontext = context.locals_({'next':ih})
    ih.inherits = Namespace("self:%s" % template.uri, lclcontext, template = template, populate_self=False)
    context._data['parent'] = lclcontext._data['local'] = ih.inherits
    callable_ = getattr(template.module, '_mako_inherit', None)
    if callable_ is not None:
        ret = callable_(template, lclcontext)
        if ret:
            return ret

    gen_ns = getattr(template.module, '_mako_generate_namespaces', None)
    if gen_ns is not None:
        gen_ns(context)
    return (template.callable_, lclcontext)

def _lookup_template(context, uri, relativeto):
    lookup = context._with_template.lookup
    if lookup is None:
        raise exceptions.TemplateLookupException("Template '%s' has no TemplateLookup associated" % context._with_template.uri)
    uri = lookup.adjust_uri(uri, relativeto)
    try:
        return lookup.get_template(uri)
    except exceptions.TopLevelLookupException, e:
        raise exceptions.TemplateLookupException(str(e))

def _populate_self_namespace(context, template, self_ns=None):
    if self_ns is None:
        self_ns = Namespace('self:%s' % template.uri, context, template=template, populate_self=False)
    context._data['self'] = context._data['local'] = self_ns
    if hasattr(template.module, '_mako_inherit'):
        ret = template.module._mako_inherit(template, context)
        if ret:
            return ret
    return (template.callable_, context)

def _render(template, callable_, args, data, as_unicode=False):
    """create a Context and return the string output of the given template and template callable."""

    if as_unicode:
        buf = util.FastEncodingBuffer(unicode=True)
    elif template.output_encoding:
        buf = util.FastEncodingBuffer(unicode=as_unicode, encoding=template.output_encoding, errors=template.encoding_errors)
    else:
        buf = util.StringIO()
    context = Context(buf, **data)
    context._with_template = template
    _render_context(template, callable_, context, *args, **_kwargs_for_callable(callable_, data))
    return context._pop_buffer().getvalue()

def _kwargs_for_callable(callable_, data, **kwargs):
    argspec = inspect.getargspec(callable_)
    namedargs = argspec[0] + [v for v in argspec[1:3] if v is not None]
    for arg in namedargs:
        if arg != 'context' and arg in data and arg not in kwargs:
            kwargs[arg] = data[arg]
    return kwargs
    
def _render_context(tmpl, callable_, context, *args, **kwargs):
    import mako.template as template
    # create polymorphic 'self' namespace for this template with possibly updated context
    if not isinstance(tmpl, template.DefTemplate):
        # if main render method, call from the base of the inheritance stack
        (inherit, lclcontext) = _populate_self_namespace(context, tmpl)
        _exec_template(inherit, lclcontext, args=args, kwargs=kwargs)
    else:
        # otherwise, call the actual rendering method specified
        (inherit, lclcontext) = _populate_self_namespace(context, tmpl.parent)
        _exec_template(callable_, context, args=args, kwargs=kwargs)
        
def _exec_template(callable_, context, args=None, kwargs=None):
    """execute a rendering callable given the callable, a Context, and optional explicit arguments

    the contextual Template will be located if it exists, and the error handling options specified
    on that Template will be interpreted here.
    """
    template = context._with_template
    if template is not None and (template.format_exceptions or template.error_handler):
        error = None
        try:
            callable_(context, *args, **kwargs)
        except Exception, e:
            error = e
        except:                
            e = sys.exc_info()[0]
            error = e
        if error:
            if template.error_handler:
                result = template.error_handler(context, error)
                if not result:
                    raise error
            else:
                error_template = exceptions.html_error_template()
                context._buffer_stack[:] = [util.FastEncodingBuffer(error_template.output_encoding, error_template.encoding_errors)]
                context._with_template = error_template
                error_template.render_context(context, error=error)
    else:
        callable_(context, *args, **kwargs)

########NEW FILE########
__FILENAME__ = template
# template.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""provides the Template class, a facade for parsing, generating and executing template strings,
as well as template runtime operations."""

from mako.lexer import Lexer
from mako import codegen
from mako import runtime, util, exceptions
import imp, os, re, shutil, stat, sys, tempfile, time, types, weakref

    
class Template(object):
    """a compiled template"""
    def __init__(self, text=None, filename=None, uri=None, format_exceptions=False, error_handler=None, 
        lookup=None, output_encoding=None, encoding_errors='strict', module_directory=None, cache_type=None, 
        cache_dir=None, cache_url=None, module_filename=None, input_encoding=None, disable_unicode=False, default_filters=None, 
        buffer_filters=[], imports=None, preprocessor=None):
        """construct a new Template instance using either literal template text, or a previously loaded template module
        
        text - textual template source, or None if a module is to be provided
        
        uri - the uri of this template, or some identifying string. defaults to the 
        full filename given, or "memory:(hex id of this Template)" if no filename
        
        filename - filename of the source template, if any
        
        format_exceptions - catch exceptions and format them into an error display template
        """
        
        if uri:
            self.module_id = re.sub(r'\W', "_", uri)
            self.uri = uri
        elif filename:
            self.module_id = re.sub(r'\W', "_", filename)
            self.uri = filename
        else:
            self.module_id = "memory:" + hex(id(self))
            self.uri = self.module_id
        
        self.input_encoding = input_encoding
        self.output_encoding = output_encoding
        self.encoding_errors = encoding_errors
        self.disable_unicode = disable_unicode
        if default_filters is None:
            if self.disable_unicode:
                self.default_filters = ['str']
            else:
                self.default_filters = ['unicode']
        else:
            self.default_filters = default_filters
        self.buffer_filters = buffer_filters
            
        self.imports = imports
        self.preprocessor = preprocessor
        
        # if plain text, compile code in memory only
        if text is not None:
            (code, module) = _compile_text(self, text, filename)
            self._code = code
            self._source = text
            ModuleInfo(module, None, self, filename, code, text)
        elif filename is not None:
            # if template filename and a module directory, load
            # a filesystem-based module file, generating if needed
            if module_filename is not None:
                path = module_filename
            elif module_directory is not None:
                u = self.uri
                if u[0] == '/':
                    u = u[1:]
                path = os.path.abspath(os.path.join(module_directory.replace('/', os.path.sep), u + ".py"))
            else:
                path = None    
            if path is not None:
                util.verify_directory(os.path.dirname(path))
                filemtime = os.stat(filename)[stat.ST_MTIME]
                if not os.path.exists(path) or os.stat(path)[stat.ST_MTIME] < filemtime:
                    _compile_module_file(self, file(filename).read(), filename, path)
                module = imp.load_source(self.module_id, path, file(path))
                del sys.modules[self.module_id]
                if module._magic_number != codegen.MAGIC_NUMBER:
                    _compile_module_file(self, file(filename).read(), filename, path)
                    module = imp.load_source(self.module_id, path, file(path))
                    del sys.modules[self.module_id]
                ModuleInfo(module, path, self, filename, None, None)
            else:
                # template filename and no module directory, compile code
                # in memory
                (code, module) = _compile_text(self, file(filename).read(), filename)
                self._source = None
                self._code = code
                ModuleInfo(module, None, self, filename, code, None)
        else:
            raise exceptions.RuntimeException("Template requires text or filename")

        self.module = module
        self.filename = filename
        self.callable_ = self.module.render_body
        self.format_exceptions = format_exceptions
        self.error_handler = error_handler
        self.lookup = lookup
        self.cache_type = cache_type
        self.cache_dir = cache_dir
        self.cache_url = cache_url

    source = property(lambda self:_get_module_info_from_callable(self.callable_).source, doc="""return the template source code for this Template.""")
    code = property(lambda self:_get_module_info_from_callable(self.callable_).code, doc="""return the module source code for this Template""")
        
    def render(self, *args, **data):
        """render the output of this template as a string.
        
        if the template specifies an output encoding, the string will be encoded accordingly, else the output
        is raw (raw output uses cStringIO and can't handle multibyte characters).
        a Context object is created corresponding to the given data.  Arguments that are explictly
        declared by this template's internal rendering method are also pulled from the given *args, **data 
        members."""
        return runtime._render(self, self.callable_, args, data)
    
    def render_unicode(self, *args, **data):
        """render the output of this template as a unicode object."""
        
        return runtime._render(self, self.callable_, args, data, as_unicode=True)
        
    def render_context(self, context, *args, **kwargs):
        """render this Template with the given context.  
        
        the data is written to the context's buffer."""
        if getattr(context, '_with_template', None) is None:
            context._with_template = self
        runtime._render_context(self, self.callable_, context, *args, **kwargs)
    
    def has_def(self, name):
        return hasattr(self.module, "render_%s" % name)
        
    def get_def(self, name):
        """return a def of this template as an individual Template of its own."""
        return DefTemplate(self, getattr(self.module, "render_%s" % name))
        
class DefTemplate(Template):
    """a Template which represents a callable def in a parent template."""
    def __init__(self, parent, callable_):
        self.parent = parent
        self.callable_ = callable_
        self.default_filters = parent.default_filters
        self.buffer_filters = parent.buffer_filters
        self.input_encoding = parent.input_encoding
        self.imports = parent.imports
        self.disable_unicode = parent.disable_unicode
        self.output_encoding = parent.output_encoding
        self.encoding_errors = parent.encoding_errors
        self.format_exceptions = parent.format_exceptions
        self.error_handler = parent.error_handler
        self.lookup = parent.lookup
        self.module = parent.module
        self.filename = parent.filename
        self.cache_type = parent.cache_type
        self.cache_dir = parent.cache_dir
        self.cache_url = parent.cache_url

    def get_def(self, name):
        return self.parent.get_def(name)

class ModuleInfo(object):
    """stores information about a module currently loaded into memory,
    provides reverse lookups of template source, module source code based on
    a module's identifier."""
    _modules = weakref.WeakValueDictionary()

    def __init__(self, module, module_filename, template, template_filename, module_source, template_source):
        self.module = module
        self.module_filename = module_filename
        self.template_filename = template_filename
        self.module_source = module_source
        self.template_source = template_source
        self._modules[module.__name__] = template._mmarker = self
        if module_filename:
            self._modules[module_filename] = self
    def _get_code(self):
        if self.module_source is not None:
            return self.module_source
        else:
            return file(self.module_filename).read()
    code = property(_get_code)
    def _get_source(self):
        if self.template_source is not None:
            if self.module._source_encoding and not isinstance(self.template_source, unicode):
                return self.template_source.decode(self.module._source_encoding)
            else:
                return self.template_source
        else:
            if self.module._source_encoding:
                return file(self.template_filename).read().decode(self.module._source_encoding)
            else:
                return file(self.template_filename).read()
    source = property(_get_source)
        
def _compile_text(template, text, filename):
    identifier = template.module_id
    lexer = Lexer(text, filename, disable_unicode=template.disable_unicode, input_encoding=template.input_encoding, preprocessor=template.preprocessor)
    node = lexer.parse()
    source = codegen.compile(node, template.uri, filename, default_filters=template.default_filters, buffer_filters=template.buffer_filters, imports=template.imports, source_encoding=lexer.encoding, generate_unicode=not template.disable_unicode)
    #print source
    cid = identifier
    if isinstance(cid, unicode):
        cid = cid.encode()
    module = types.ModuleType(cid)
    code = compile(source, cid, 'exec')
    exec code in module.__dict__, module.__dict__
    return (source, module)

def _compile_module_file(template, text, filename, outputpath):
    identifier = template.module_id
    lexer = Lexer(text, filename, disable_unicode=template.disable_unicode, input_encoding=template.input_encoding, preprocessor=template.preprocessor)
    node = lexer.parse()
    source = codegen.compile(node, template.uri, filename, default_filters=template.default_filters, buffer_filters=template.buffer_filters, imports=template.imports, source_encoding=lexer.encoding, generate_unicode=not template.disable_unicode)
    (dest, name) = tempfile.mkstemp()
    os.write(dest, source)
    os.close(dest)
    shutil.move(name, outputpath)

def _get_module_info_from_callable(callable_):
    return _get_module_info(callable_.func_globals['__name__'])
    
def _get_module_info(filename):
    return ModuleInfo._modules[filename]
        

########NEW FILE########
__FILENAME__ = util
# util.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import sys
try:
    Set = set
except:
    import sets
    Set = sets.Set

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

import weakref, os, time

try:
    import threading
    import thread
except ImportError:
    import dummy_threading as threading
    import dummy_thread as thread

if sys.platform.startswith('win') or sys.platform.startswith('java'):
    time_func = time.clock
else:
    time_func = time.time 
   
def verify_directory(dir):
    """create and/or verify a filesystem directory."""
    
    tries = 0
    
    while not os.path.exists(dir):
        try:
            tries += 1
            os.makedirs(dir, 0750)
        except:
            if tries > 5:
                raise

class SetLikeDict(dict):
    """a dictionary that has some setlike methods on it"""
    def union(self, other):
        """produce a 'union' of this dict and another (at the key level).
        
        values in the second dict take precedence over that of the first"""
        x = SetLikeDict(**self)
        x.update(other)
        return x

class FastEncodingBuffer(object):
    """a very rudimentary buffer that is faster than StringIO, but doesnt crash on unicode data like cStringIO."""
    
    def __init__(self, encoding=None, errors='strict', unicode=False):
        self.data = []
        self.encoding = encoding
        if unicode:
            self.delim = u''
        else:
            self.delim = ''
        self.unicode = unicode
        self.errors = errors
        self.write = self.data.append
        
    def getvalue(self):
        if self.encoding:
            return self.delim.join(self.data).encode(self.encoding, self.errors)
        else:
            return self.delim.join(self.data)

class LRUCache(dict):
    """A dictionary-like object that stores a limited number of items, discarding
    lesser used items periodically.
    
    this is a rewrite of LRUCache from Myghty to use a periodic timestamp-based
    paradigm so that synchronization is not really needed.  the size management 
    is inexact.
    """
    
    class _Item(object):
        def __init__(self, key, value):
            self.key = key
            self.value = value
            self.timestamp = time_func()
        def __repr__(self):
            return repr(self.value)
    
    def __init__(self, capacity, threshold=.5):
        self.capacity = capacity
        self.threshold = threshold
    
    def __getitem__(self, key):
        item = dict.__getitem__(self, key)
        item.timestamp = time_func()
        return item.value
    
    def values(self):
        return [i.value for i in dict.values(self)]
    
    def setdefault(self, key, value):
        if key in self:
            return self[key]
        else:
            self[key] = value
            return value
    
    def __setitem__(self, key, value):
        item = dict.get(self, key)
        if item is None:
            item = self._Item(key, value)
            dict.__setitem__(self, key, item)
        else:
            item.value = value
        self._manage_size()
    
    def _manage_size(self):
        while len(self) > self.capacity + self.capacity * self.threshold:
            bytime = dict.values(self)
            bytime.sort(lambda a, b: cmp(b.timestamp, a.timestamp))
            for item in bytime[self.capacity:]:
                try:
                    del self[item.key]
                except KeyError:
                    # if we couldnt find a key, most likely some other thread broke in 
                    # on us. loop around and try again
                    break

def restore__ast(_ast):
    """Attempt to restore the required classes to the _ast module if it
    appears to be missing them
    """
    if hasattr(_ast, 'AST'):
        return
    _ast.PyCF_ONLY_AST = 2 << 9
    m = compile("""\
def foo(): pass
class Bar(object): pass
if False: pass
baz = 'mako'
1 + 2 - 3 * 4 / 5
6 // 7 % 8 << 9 >> 10
11 & 12 ^ 13 | 14
15 and 16 or 17
-baz + (not +18) - ~17
baz and 'foo' or 'bar'
(mako is baz == baz) is not baz != mako
mako > baz < mako >= baz <= mako
mako in baz not in mako""", '<unknown>', 'exec', _ast.PyCF_ONLY_AST)
    _ast.Module = type(m)

    for cls in _ast.Module.__mro__:
        if cls.__name__ == 'mod':
            _ast.mod = cls
        elif cls.__name__ == 'AST':
            _ast.AST = cls

    _ast.FunctionDef = type(m.body[0])
    _ast.ClassDef = type(m.body[1])
    _ast.If = type(m.body[2])

    _ast.Name = type(m.body[3].targets[0])
    _ast.Store = type(m.body[3].targets[0].ctx)
    _ast.Str = type(m.body[3].value)

    _ast.Sub = type(m.body[4].value.op)
    _ast.Add = type(m.body[4].value.left.op)
    _ast.Div = type(m.body[4].value.right.op)
    _ast.Mult = type(m.body[4].value.right.left.op)

    _ast.RShift = type(m.body[5].value.op)
    _ast.LShift = type(m.body[5].value.left.op)
    _ast.Mod = type(m.body[5].value.left.left.op)
    _ast.FloorDiv = type(m.body[5].value.left.left.left.op)

    _ast.BitOr = type(m.body[6].value.op)
    _ast.BitXor = type(m.body[6].value.left.op)
    _ast.BitAnd = type(m.body[6].value.left.left.op)

    _ast.Or = type(m.body[7].value.op)
    _ast.And = type(m.body[7].value.values[0].op)

    _ast.Invert = type(m.body[8].value.right.op)
    _ast.Not = type(m.body[8].value.left.right.op)
    _ast.UAdd = type(m.body[8].value.left.right.operand.op)
    _ast.USub = type(m.body[8].value.left.left.op)

    _ast.Or = type(m.body[9].value.op)
    _ast.And = type(m.body[9].value.values[0].op)

    _ast.IsNot = type(m.body[10].value.ops[0])
    _ast.NotEq = type(m.body[10].value.ops[1])
    _ast.Is = type(m.body[10].value.left.ops[0])
    _ast.Eq = type(m.body[10].value.left.ops[1])

    _ast.Gt = type(m.body[11].value.ops[0])
    _ast.Lt = type(m.body[11].value.ops[1])
    _ast.GtE = type(m.body[11].value.ops[2])
    _ast.LtE = type(m.body[11].value.ops[3])

    _ast.In = type(m.body[12].value.ops[0])
    _ast.NotIn = type(m.body[12].value.ops[1])

########NEW FILE########
__FILENAME__ = _ast_util
# -*- coding: utf-8 -*-
"""
    ast
    ~~~

    The `ast` module helps Python applications to process trees of the Python
    abstract syntax grammar.  The abstract syntax itself might change with
    each Python release; this module helps to find out programmatically what
    the current grammar looks like and allows modifications of it.

    An abstract syntax tree can be generated by passing `ast.PyCF_ONLY_AST` as
    a flag to the `compile()` builtin function or by using the `parse()`
    function from this module.  The result will be a tree of objects whose
    classes all inherit from `ast.AST`.

    A modified abstract syntax tree can be compiled into a Python code object
    using the built-in `compile()` function.

    Additionally various helper functions are provided that make working with
    the trees simpler.  The main intention of the helper functions and this
    module in general is to provide an easy to use interface for libraries
    that work tightly with the python syntax (template engines for example).


    :copyright: Copyright 2008 by Armin Ronacher.
    :license: Python License.
"""
from _ast import *


BOOLOP_SYMBOLS = {
    And:        'and',
    Or:         'or'
}

BINOP_SYMBOLS = {
    Add:        '+',
    Sub:        '-',
    Mult:       '*',
    Div:        '/',
    FloorDiv:   '//',
    Mod:        '%',
    LShift:     '<<',
    RShift:     '>>',
    BitOr:      '|',
    BitAnd:     '&',
    BitXor:     '^'
}

CMPOP_SYMBOLS = {
    Eq:         '==',
    Gt:         '>',
    GtE:        '>=',
    In:         'in',
    Is:         'is',
    IsNot:      'is not',
    Lt:         '<',
    LtE:        '<=',
    NotEq:      '!=',
    NotIn:      'not in'
}

UNARYOP_SYMBOLS = {
    Invert:     '~',
    Not:        'not',
    UAdd:       '+',
    USub:       '-'
}

ALL_SYMBOLS = {}
ALL_SYMBOLS.update(BOOLOP_SYMBOLS)
ALL_SYMBOLS.update(BINOP_SYMBOLS)
ALL_SYMBOLS.update(CMPOP_SYMBOLS)
ALL_SYMBOLS.update(UNARYOP_SYMBOLS)


def parse(expr, filename='<unknown>', mode='exec'):
    """Parse an expression into an AST node."""
    return compile(expr, filename, mode, PyCF_ONLY_AST)


def to_source(node, indent_with=' ' * 4):
    """
    This function can convert a node tree back into python sourcecode.  This
    is useful for debugging purposes, especially if you're dealing with custom
    asts not generated by python itself.

    It could be that the sourcecode is evaluable when the AST itself is not
    compilable / evaluable.  The reason for this is that the AST contains some
    more data than regular sourcecode does, which is dropped during
    conversion.

    Each level of indentation is replaced with `indent_with`.  Per default this
    parameter is equal to four spaces as suggested by PEP 8, but it might be
    adjusted to match the application's styleguide.
    """
    generator = SourceGenerator(indent_with)
    generator.visit(node)
    return ''.join(generator.result)


def dump(node):
    """
    A very verbose representation of the node passed.  This is useful for
    debugging purposes.
    """
    def _format(node):
        if isinstance(node, AST):
            return '%s(%s)' % (node.__class__.__name__,
                               ', '.join('%s=%s' % (a, _format(b))
                                         for a, b in iter_fields(node)))
        elif isinstance(node, list):
            return '[%s]' % ', '.join(_format(x) for x in node)
        return repr(node)
    if not isinstance(node, AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return _format(node)


def copy_location(new_node, old_node):
    """
    Copy the source location hint (`lineno` and `col_offset`) from the
    old to the new node if possible and return the new one.
    """
    for attr in 'lineno', 'col_offset':
        if attr in old_node._attributes and attr in new_node._attributes \
           and hasattr(old_node, attr):
            setattr(new_node, attr, getattr(old_node, attr))
    return new_node


def fix_missing_locations(node):
    """
    Some nodes require a line number and the column offset.  Without that
    information the compiler will abort the compilation.  Because it can be
    a dull task to add appropriate line numbers and column offsets when
    adding new nodes this function can help.  It copies the line number and
    column offset of the parent node to the child nodes without this
    information.

    Unlike `copy_location` this works recursive and won't touch nodes that
    already have a location information.
    """
    def _fix(node, lineno, col_offset):
        if 'lineno' in node._attributes:
            if not hasattr(node, 'lineno'):
                node.lineno = lineno
            else:
                lineno = node.lineno
        if 'col_offset' in node._attributes:
            if not hasattr(node, 'col_offset'):
                node.col_offset = col_offset
            else:
                col_offset = node.col_offset
        for child in iter_child_nodes(node):
            _fix(child, lineno, col_offset)
    _fix(node, 1, 0)
    return node


def increment_lineno(node, n=1):
    """
    Increment the line numbers of all nodes by `n` if they have line number
    attributes.  This is useful to "move code" to a different location in a
    file.
    """
    for node in zip((node,), walk(node)):
        if 'lineno' in node._attributes:
            node.lineno = getattr(node, 'lineno', 0) + n


def iter_fields(node):
    """Iterate over all fields of a node, only yielding existing fields."""
    if not hasattr(node, '_fields') or not node._fields:
        return
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def get_fields(node):
    """Like `iter_fiels` but returns a dict."""
    return dict(iter_fields(node))


def iter_child_nodes(node):
    """Iterate over all child nodes or a node."""
    for name, field in iter_fields(node):
        if isinstance(field, AST):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, AST):
                    yield item


def get_child_nodes(node):
    """Like `iter_child_nodes` but returns a list."""
    return list(iter_child_nodes(node))


def get_compile_mode(node):
    """
    Get the mode for `compile` of a given node.  If the node is not a `mod`
    node (`Expression`, `Module` etc.) a `TypeError` is thrown.
    """
    if not isinstance(node, mod):
        raise TypeError('expected mod node, got %r' % node.__class__.__name__)
    return {
        Expression:     'eval',
        Interactive:    'single'
    }.get(node.__class__, 'expr')


def get_docstring(node):
    """
    Return the docstring for the given node or `None` if no docstring can be
    found.  If the node provided does not accept docstrings a `TypeError`
    will be raised.
    """
    if not isinstance(node, (FunctionDef, ClassDef, Module)):
        raise TypeError("%r can't have docstrings" % node.__class__.__name__)
    if node.body and isinstance(node.body[0], Str):
        return node.body[0].s


def walk(node):
    """
    Iterate over all nodes.  This is useful if you only want to modify nodes in
    place and don't care about the context or the order the nodes are returned.
    """
    from collections import deque
    todo = deque([node])
    while todo:
        node = todo.popleft()
        todo.extend(iter_child_nodes(node))
        yield node


class NodeVisitor(object):
    """
    Walks the abstract syntax tree and call visitor functions for every node
    found.  The visitor functions may return values which will be forwarded
    by the `visit` method.

    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `get_visitor` function.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.

    Don't use the `NodeVisitor` if you want to apply changes to nodes during
    traversing.  For this a special visitor exists (`NodeTransformer`) that
    allows modifications.
    """

    def get_visitor(self, node):
        """
        Return the visitor function for this node or `None` if no visitor
        exists for this node.  In that case the generic visit function is
        used instead.
        """
        method = 'visit_' + node.__class__.__name__
        return getattr(self, method, None)

    def visit(self, node):
        """Visit a node."""
        f = self.get_visitor(node)
        if f is not None:
            return f(node)
        return self.generic_visit(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AST):
                        self.visit(item)
            elif isinstance(value, AST):
                self.visit(value)


class NodeTransformer(NodeVisitor):
    """
    Walks the abstract syntax tree and allows modifications of nodes.

    The `NodeTransformer` will walk the AST and use the return value of the
    visitor functions to replace or remove the old node.  If the return
    value of the visitor function is `None` the node will be removed
    from the previous location otherwise it's replaced with the return
    value.  The return value may be the original node in which case no
    replacement takes place.

    Here an example transformer that rewrites all `foo` to `data['foo']`::

        class RewriteName(NodeTransformer):

            def visit_Name(self, node):
                return copy_location(Subscript(
                    value=Name(id='data', ctx=Load()),
                    slice=Index(value=Str(s=node.id)),
                    ctx=node.ctx
                ), node)

    Keep in mind that if the node you're operating on has child nodes
    you must either transform the child nodes yourself or call the generic
    visit function for the node first.

    Nodes that were part of a collection of statements (that applies to
    all statement nodes) may also return a list of nodes rather than just
    a single node.

    Usually you use the transformer like this::

        node = YourTransformer().visit(node)
    """

    def generic_visit(self, node):
        for field, old_value in iter_fields(node):
            old_value = getattr(node, field, None)
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, AST):
                        value = self.visit(value)
                        if value is None:
                            continue
                        elif not isinstance(value, AST):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, AST):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node


class SourceGenerator(NodeVisitor):
    """
    This visitor is able to transform a well formed syntax tree into python
    sourcecode.  For more details have a look at the docstring of the
    `node_to_source` function.
    """

    def __init__(self, indent_with):
        self.result = []
        self.indent_with = indent_with
        self.indentation = 0
        self.new_lines = 0

    def write(self, x):
        if self.new_lines:
            if self.result:
                self.result.append('\n' * self.new_lines)
            self.result.append(self.indent_with * self.indentation)
            self.new_lines = 0
        self.result.append(x)

    def newline(self, n=1):
        self.new_lines = max(self.new_lines, n)

    def body(self, statements):
        self.new_line = True
        self.indentation += 1
        for stmt in statements:
            self.visit(stmt)
        self.indentation -= 1

    def body_or_else(self, node):
        self.body(node.body)
        if node.orelse:
            self.newline()
            self.write('else:')
            self.body(node.orelse)

    def signature(self, node):
        want_comma = []
        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        padding = [None] * (len(node.args) - len(node.defaults))
        for arg, default in zip(node.args, padding + node.defaults):
            write_comma()
            self.visit(arg)
            if default is not None:
                self.write('=')
                self.visit(default)
        if node.vararg is not None:
            write_comma()
            self.write('*' + node.vararg)
        if node.kwarg is not None:
            write_comma()
            self.write('**' + node.kwarg)

    def decorators(self, node):
        for decorator in node.decorator_list:
            self.newline()
            self.write('@')
            self.visit(decorator)

    # Statements

    def visit_Assign(self, node):
        self.newline()
        for idx, target in enumerate(node.targets):
            if idx:
                self.write(', ')
            self.visit(target)
        self.write(' = ')
        self.visit(node.value)

    def visit_AugAssign(self, node):
        self.newline()
        self.visit(node.target)
        self.write(BINOP_SYMBOLS[type(node.op)] + '=')
        self.visit(node.value)

    def visit_ImportFrom(self, node):
        self.newline()
        self.write('from %s%s import ' % ('.' * node.level, node.module))
        for idx, item in enumerate(node.names):
            if idx:
                self.write(', ')
            self.write(item)

    def visit_Import(self, node):
        self.newline()
        for item in node.names:
            self.write('import ')
            self.visit(item)

    def visit_Expr(self, node):
        self.newline()
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.newline(n=2)
        self.decorators(node)
        self.newline()
        self.write('def %s(' % node.name)
        self.signature(node.args)
        self.write('):')
        self.body(node.body)

    def visit_ClassDef(self, node):
        have_args = []
        def paren_or_comma():
            if have_args:
                self.write(', ')
            else:
                have_args.append(True)
                self.write('(')

        self.newline(n=3)
        self.decorators(node)
        self.newline()
        self.write('class %s' % node.name)
        for base in node.bases:
            paren_or_comma()
            self.visit(base)
        # XXX: the if here is used to keep this module compatible
        #      with python 2.6.
        if hasattr(node, 'keywords'):
            for keyword in node.keywords:
                paren_or_comma()
                self.write(keyword.arg + '=')
                self.visit(keyword.value)
            if node.starargs is not None:
                paren_or_comma()
                self.write('*')
                self.visit(node.starargs)
            if node.kwargs is not None:
                paren_or_comma()
                self.write('**')
                self.visit(node.kwargs)
        self.write(have_args and '):' or ':')
        self.body(node.body)

    def visit_If(self, node):
        self.newline()
        self.write('if ')
        self.visit(node.test)
        self.write(':')
        self.body(node.body)
        while True:
            else_ = node.orelse
            if len(else_) == 1 and isinstance(else_[0], If):
                node = else_[0]
                self.newline()
                self.write('elif ')
                self.visit(node.test)
                self.write(':')
                self.body(node.body)
            else:
                self.newline()
                self.write('else:')
                self.body(else_)
                break

    def visit_For(self, node):
        self.newline()
        self.write('for ')
        self.visit(node.target)
        self.write(' in ')
        self.visit(node.iter)
        self.write(':')
        self.body_or_else(node)

    def visit_While(self, node):
        self.newline()
        self.write('while ')
        self.visit(node.test)
        self.write(':')
        self.body_or_else(node)

    def visit_With(self, node):
        self.newline()
        self.write('with ')
        self.visit(node.context_expr)
        if node.optional_vars is not None:
            self.write(' as ')
            self.visit(node.optional_vars)
        self.write(':')
        self.body(node.body)

    def visit_Pass(self, node):
        self.newline()
        self.write('pass')

    def visit_Print(self, node):
        # XXX: python 2.6 only
        self.newline()
        self.write('print ')
        want_comma = False
        if node.dest is not None:
            self.write(' >> ')
            self.visit(node.dest)
            want_comma = True
        for value in node.values:
            if want_comma:
                self.write(', ')
            self.visit(value)
            want_comma = True
        if not node.nl:
            self.write(',')

    def visit_Delete(self, node):
        self.newline()
        self.write('del ')
        for idx, target in enumerate(node):
            if idx:
                self.write(', ')
            self.visit(target)

    def visit_TryExcept(self, node):
        self.newline()
        self.write('try:')
        self.body(node.body)
        for handler in node.handlers:
            self.visit(handler)

    def visit_TryFinally(self, node):
        self.newline()
        self.write('try:')
        self.body(node.body)
        self.newline()
        self.write('finally:')
        self.body(node.finalbody)

    def visit_Global(self, node):
        self.newline()
        self.write('global ' + ', '.join(node.names))

    def visit_Nonlocal(self, node):
        self.newline()
        self.write('nonlocal ' + ', '.join(node.names))

    def visit_Return(self, node):
        self.newline()
        self.write('return ')
        self.visit(node.value)

    def visit_Break(self, node):
        self.newline()
        self.write('break')

    def visit_Continue(self, node):
        self.newline()
        self.write('continue')

    def visit_Raise(self, node):
        # XXX: Python 2.6 / 3.0 compatibility
        self.newline()
        self.write('raise')
        if hasattr(node, 'exc') and node.exc is not None:
            self.write(' ')
            self.visit(node.exc)
            if node.cause is not None:
                self.write(' from ')
                self.visit(node.cause)
        elif hasattr(node, 'type') and node.type is not None:
            self.visit(node.type)
            if node.inst is not None:
                self.write(', ')
                self.visit(node.inst)
            if node.tback is not None:
                self.write(', ')
                self.visit(node.tback)

    # Expressions

    def visit_Attribute(self, node):
        self.visit(node.value)
        self.write('.' + node.attr)

    def visit_Call(self, node):
        want_comma = []
        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        self.visit(node.func)
        self.write('(')
        for arg in node.args:
            write_comma()
            self.visit(arg)
        for keyword in node.keywords:
            write_comma()
            self.write(keyword.arg + '=')
            self.visit(keyword.value)
        if node.starargs is not None:
            write_comma()
            self.write('*')
            self.visit(node.starargs)
        if node.kwargs is not None:
            write_comma()
            self.write('**')
            self.visit(node.kwargs)
        self.write(')')

    def visit_Name(self, node):
        self.write(node.id)

    def visit_Str(self, node):
        self.write(repr(node.s))

    def visit_Bytes(self, node):
        self.write(repr(node.s))

    def visit_Num(self, node):
        self.write(repr(node.n))

    def visit_Tuple(self, node):
        self.write('(')
        idx = -1
        for idx, item in enumerate(node.elts):
            if idx:
                self.write(', ')
            self.visit(item)
        self.write(idx and ')' or ',)')

    def sequence_visit(left, right):
        def visit(self, node):
            self.write(left)
            for idx, item in enumerate(node.elts):
                if idx:
                    self.write(', ')
                self.visit(item)
            self.write(right)
        return visit

    visit_List = sequence_visit('[', ']')
    visit_Set = sequence_visit('{', '}')
    del sequence_visit

    def visit_Dict(self, node):
        self.write('{')
        for idx, (key, value) in enumerate(zip(node.keys, node.values)):
            if idx:
                self.write(', ')
            self.visit(key)
            self.write(': ')
            self.visit(value)
        self.write('}')

    def visit_BinOp(self, node):
        self.write('(')
        self.visit(node.left)
        self.write(' %s ' % BINOP_SYMBOLS[type(node.op)])
        self.visit(node.right)
        self.write(')')

    def visit_BoolOp(self, node):
        self.write('(')
        for idx, value in enumerate(node.values):
            if idx:
                self.write(' %s ' % BOOLOP_SYMBOLS[type(node.op)])
            self.visit(value)
        self.write(')')

    def visit_Compare(self, node):
        self.write('(')
        self.visit(node.left)
        for op, right in zip(node.ops, node.comparators):
            self.write(' %s ' % CMPOP_SYMBOLS[type(op)])
            self.visit(right)
        self.write(')')

    def visit_UnaryOp(self, node):
        self.write('(')
        op = UNARYOP_SYMBOLS[type(node.op)]
        self.write(op)
        if op == 'not':
            self.write(' ')
        self.visit(node.operand)
        self.write(')')

    def visit_Subscript(self, node):
        self.visit(node.value)
        self.write('[')
        self.visit(node.slice)
        self.write(']')

    def visit_Slice(self, node):
        if node.lower is not None:
            self.visit(node.lower)
        self.write(':')
        if node.upper is not None:
            self.visit(node.upper)
        if node.step is not None:
            self.write(':')
            if not (isinstance(node.step, Name) and node.step.id == 'None'):
                self.visit(node.step)

    def visit_ExtSlice(self, node):
        for idx, item in node.dims:
            if idx:
                self.write(', ')
            self.visit(item)

    def visit_Yield(self, node):
        self.write('yield ')
        self.visit(node.value)

    def visit_Lambda(self, node):
        self.write('lambda ')
        self.signature(node.args)
        self.write(': ')
        self.visit(node.body)

    def visit_Ellipsis(self, node):
        self.write('Ellipsis')

    def generator_visit(left, right):
        def visit(self, node):
            self.write(left)
            self.visit(node.elt)
            for comprehension in node.generators:
                self.visit(comprehension)
            self.write(right)
        return visit

    visit_ListComp = generator_visit('[', ']')
    visit_GeneratorExp = generator_visit('(', ')')
    visit_SetComp = generator_visit('{', '}')
    del generator_visit

    def visit_DictComp(self, node):
        self.write('{')
        self.visit(node.key)
        self.write(': ')
        self.visit(node.value)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.write('}')

    def visit_IfExp(self, node):
        self.visit(node.body)
        self.write(' if ')
        self.visit(node.test)
        self.write(' else ')
        self.visit(node.orelse)

    def visit_Starred(self, node):
        self.write('*')
        self.visit(node.value)

    def visit_Repr(self, node):
        # XXX: python 2.6 only
        self.write('`')
        self.visit(node.value)
        self.write('`')

    # Helper Nodes

    def visit_alias(self, node):
        self.write(node.name)
        if node.asname is not None:
            self.write(' as ' + node.asname)

    def visit_comprehension(self, node):
        self.write(' for ')
        self.visit(node.target)
        self.write(' in ')
        self.visit(node.iter)
        if node.ifs:
            for if_ in node.ifs:
                self.write(' if ')
                self.visit(if_)

    def visit_excepthandler(self, node):
        self.newline()
        self.write('except')
        if node.type is not None:
            self.write(' ')
            self.visit(node.type)
            if node.name is not None:
                self.write(' as ')
                self.visit(node.name)
        self.write(':')
        self.body(node.body)

########NEW FILE########
__FILENAME__ = decoder
"""
Implementation of JSONDecoder
"""
import re
import sys

from simplejson.scanner import Scanner, pattern
try:
    from simplejson._speedups import scanstring as c_scanstring
except ImportError:
    pass

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    import struct
    import sys
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    lineno, colno = linecol(doc, pos)
    if end is None:
        return '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    return '%s: line %d column %d - line %d column %d (char %d - %d)' % (
        msg, lineno, colno, endlineno, endcolno, pos, end)


_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
    'true': True,
    'false': False,
    'null': None,
}

def JSONConstant(match, context, c=_CONSTANTS):
    s = match.group(0)
    fn = getattr(context, 'parse_constant', None)
    if fn is None:
        rval = c[s]
    else:
        rval = fn(s)
    return rval, None
pattern('(-?Infinity|NaN|true|false|null)')(JSONConstant)


def JSONNumber(match, context):
    match = JSONNumber.regex.match(match.string, *match.span())
    integer, frac, exp = match.groups()
    if frac or exp:
        fn = getattr(context, 'parse_float', None) or float
        res = fn(integer + (frac or '') + (exp or ''))
    else:
        fn = getattr(context, 'parse_int', None) or int
        res = fn(integer)
    return res, None
pattern(r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?')(JSONNumber)


STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u'"', '\\': u'\\', '/': u'/',
    'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True, _b=BACKSLASH, _m=STRINGCHUNK.match):
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        end = chunk.end()
        content, terminator = chunk.groups()
        if content:
            if not isinstance(content, unicode):
                content = unicode(content, encoding)
            _append(content)
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                raise ValueError(errmsg("Invalid control character %r at", s, end))
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        if esc != 'u':
            try:
                m = _b[esc]
            except KeyError:
                raise ValueError(
                    errmsg("Invalid \\escape: %r" % (esc,), s, end))
            end += 1
        else:
            esc = s[end + 1:end + 5]
            next_end = end + 5
            msg = "Invalid \\uXXXX escape"
            try:
                if len(esc) != 4:
                    raise ValueError
                uni = int(esc, 16)
                if 0xd800 <= uni <= 0xdbff and sys.maxunicode > 65535:
                    msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                    if not s[end + 5:end + 7] == '\\u':
                        raise ValueError
                    esc2 = s[end + 7:end + 11]
                    if len(esc2) != 4:
                        raise ValueError
                    uni2 = int(esc2, 16)
                    uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                    next_end += 6
                m = unichr(uni)
            except ValueError:
                raise ValueError(errmsg(msg, s, end))
            end = next_end
        _append(m)
    return u''.join(chunks), end


# Use speedup
try:
    scanstring = c_scanstring
except NameError:
    scanstring = py_scanstring

def JSONString(match, context):
    encoding = getattr(context, 'encoding', None)
    strict = getattr(context, 'strict', True)
    return scanstring(match.string, match.end(), encoding, strict)
pattern(r'"')(JSONString)


WHITESPACE = re.compile(r'\s*', FLAGS)

def JSONObject(match, context, _w=WHITESPACE.match):
    pairs = {}
    s = match.string
    end = _w(s, match.end()).end()
    nextchar = s[end:end + 1]
    # Trivial empty object
    if nextchar == '}':
        return pairs, end + 1
    if nextchar != '"':
        raise ValueError(errmsg("Expecting property name", s, end))
    end += 1
    encoding = getattr(context, 'encoding', None)
    strict = getattr(context, 'strict', True)
    iterscan = JSONScanner.iterscan
    while True:
        key, end = scanstring(s, end, encoding, strict)
        end = _w(s, end).end()
        if s[end:end + 1] != ':':
            raise ValueError(errmsg("Expecting : delimiter", s, end))
        end = _w(s, end + 1).end()
        try:
            value, end = iterscan(s, idx=end, context=context).next()
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        pairs[key] = value
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar == '}':
            break
        if nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end - 1))
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end - 1))
    object_hook = getattr(context, 'object_hook', None)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end
pattern(r'{')(JSONObject)


def JSONArray(match, context, _w=WHITESPACE.match):
    values = []
    s = match.string
    end = _w(s, match.end()).end()
    # Look-ahead for trivial empty array
    nextchar = s[end:end + 1]
    if nextchar == ']':
        return values, end + 1
    iterscan = JSONScanner.iterscan
    while True:
        try:
            value, end = iterscan(s, idx=end, context=context).next()
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        values.append(value)
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        if nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end))
        end = _w(s, end).end()
    return values, end
pattern(r'\[')(JSONArray)


ANYTHING = [
    JSONObject,
    JSONArray,
    JSONString,
    JSONConstant,
    JSONNumber,
]

JSONScanner = Scanner(ANYTHING)


class JSONDecoder(object):
    """
    Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:
    
    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.
    """

    _scanner = Scanner(ANYTHING)
    __all__ = ['__init__', 'decode', 'raw_decode']

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True):
        """
        ``encoding`` determines the encoding used to interpret any ``str``
        objects decoded by this instance (utf-8 by default).  It has no
        effect when decoding ``unicode`` objects.
        
        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as ``unicode``.

        ``object_hook``, if specified, will be called with the result
        of every JSON object decoded and its return value will be used in
        place of the given ``dict``.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        ``parse_float``, if specified, will be called with the string
        of every JSON float to be decoded. By default this is equivalent to
        float(num_str). This can be used to use another datatype or parser
        for JSON floats (e.g. decimal.Decimal).

        ``parse_int``, if specified, will be called with the string
        of every JSON int to be decoded. By default this is equivalent to
        int(num_str). This can be used to use another datatype or parser
        for JSON integers (e.g. float).

        ``parse_constant``, if specified, will be called with one of the
        following strings: -Infinity, Infinity, NaN, null, true, false.
        This can be used to raise an exception if invalid JSON numbers
        are encountered.
        """
        self.encoding = encoding
        self.object_hook = object_hook
        self.parse_float = parse_float
        self.parse_int = parse_int
        self.parse_constant = parse_constant
        self.strict = strict

    def decode(self, s, _w=WHITESPACE.match):
        """
        Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)
        """
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise ValueError(errmsg("Extra data", s, end, len(s)))
        return obj

    def raw_decode(self, s, **kw):
        """
        Decode a JSON document from ``s`` (a ``str`` or ``unicode`` beginning
        with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.
        """
        kw.setdefault('context', self)
        try:
            obj, end = self._scanner.iterscan(s, **kw).next()
        except StopIteration:
            raise ValueError("No JSON object could be decoded")
        return obj, end

__all__ = ['JSONDecoder']

########NEW FILE########
__FILENAME__ = encoder
"""
Implementation of JSONEncoder
"""
import re
import datetime
import time

try:
    from simplejson._speedups import encode_basestring_ascii as c_encode_basestring_ascii
except ImportError:
    pass

ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

# Assume this produces an infinity on all machines (probably not guaranteed)
INFINITY = float('1e66666')
FLOAT_REPR = repr

def floatstr(o, allow_nan=True):
    # Check for specials.  Note that this type of test is processor- and/or
    # platform-specific, so do tests which don't depend on the internals.

    if o != o:
        text = 'NaN'
    elif o == INFINITY:
        text = 'Infinity'
    elif o == -INFINITY:
        text = '-Infinity'
    else:
        return FLOAT_REPR(o)

    if not allow_nan:
        raise ValueError("Out of range float values are not JSON compliant: %r"
            % (o,))

    return text


def encode_basestring(s):
    """
    Return a JSON representation of a Python string
    """
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return '"' + ESCAPE.sub(replace, s) + '"'


def py_encode_basestring_ascii(s):
    if isinstance(s, str) and HAS_UTF8.search(s) is not None:
        s = s.decode('utf-8')
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'


try:
    encode_basestring_ascii = c_encode_basestring_ascii
except NameError:
    encode_basestring_ascii = py_encode_basestring_ascii


class JSONEncoder(object):
    """
    Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:
    
    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-----------------------------------+
    | datetime          | number (epoch)|    
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+
    

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).
    """
    __all__ = ['__init__', 'default', 'encode', 'iterencode']
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None):
        """
        Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is False, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is True, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is True, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is True, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is True, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be a (item_separator, key_separator)
        tuple.  The default is (', ', ': ').  To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding.
        The default is UTF-8.
        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        self.current_indent_level = 0
        if separators is not None:
            self.item_separator, self.key_separator = separators
        if default is not None:
            self.default = default
        self.encoding = encoding

    def _newline_indent(self):
        return '\n' + (' ' * (self.indent * self.current_indent_level))

    def _iterencode_list(self, lst, markers=None):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        yield '['
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            separator = self.item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                yield separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(self, dct, markers=None):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        key_separator = self.key_separator
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            item_separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = self.item_separator
        first = True
        if self.ensure_ascii:
            encoder = encode_basestring_ascii
        else:
            encoder = encode_basestring
        allow_nan = self.allow_nan
        if self.sort_keys:
            keys = dct.keys()
            keys.sort()
            items = [(k, dct[k]) for k in keys]
        else:
            items = dct.iteritems()
        _encoding = self.encoding
        _do_decode = (_encoding is not None
            and not (_encoding == 'utf-8'))
        for key, value in items:
            if isinstance(key, str):
                if _do_decode:
                    key = key.decode(_encoding)
            elif isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = floatstr(key, allow_nan)
            elif isinstance(key, (int, long)):
                key = str(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif self.skipkeys:
                continue
            else:
                raise TypeError("key %r is not a string" % (key,))
            if first:
                first = False
            else:
                yield item_separator
            yield encoder(key)
            yield key_separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(self, o, markers=None):
        if isinstance(o, basestring):
            if self.ensure_ascii:
                encoder = encode_basestring_ascii
            else:
                encoder = encode_basestring
            _encoding = self.encoding
            if (_encoding is not None and isinstance(o, str)
                    and not (_encoding == 'utf-8')):
                o = o.decode(_encoding)
            yield encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield floatstr(o, self.allow_nan)
        elif isinstance(o, (list, tuple)):
            for chunk in self._iterencode_list(o, markers):
                yield chunk
        elif isinstance(o, dict):
            for chunk in self._iterencode_dict(o, markers):
                yield chunk
        elif isinstance(o, datetime.datetime): 
            yield str(int(time.mktime(o.timetuple())))
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            for chunk in self._iterencode_default(o, markers):
                yield chunk
            if markers is not None:
                del markers[markerid]

    def _iterencode_default(self, o, markers=None):
        newobj = self.default(o)
        return self._iterencode(newobj, markers)

    def default(self, o):
        """
        Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::
            
            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)
        """
        if hasattr(o, '__class__'): 
          if hasattr(o.__class__, '__json__'): return o.__json__()
        
        raise TypeError("%r is not JSON serializable" % (o,))

    def encode(self, o):
        """
        Return a JSON string representation of a Python data structure.

        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'
        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, basestring):
            if isinstance(o, str):
                _encoding = self.encoding
                if (_encoding is not None 
                        and not (_encoding == 'utf-8')):
                    o = o.decode(_encoding)
            if self.ensure_ascii:
                return encode_basestring_ascii(o)
            else:
                return encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = list(self.iterencode(o))
        return ''.join(chunks)

    def iterencode(self, o):
        """
        Encode the given object and yield each string
        representation as available.
        
        For example::
            
            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)
        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        return self._iterencode(o, markers)

__all__ = ['JSONEncoder']

########NEW FILE########
__FILENAME__ = scanner
"""
Iterator based sre token scanner
"""
import re
from re import VERBOSE, MULTILINE, DOTALL
import sre_parse
import sre_compile
import sre_constants
from sre_constants import BRANCH, SUBPATTERN

__all__ = ['Scanner', 'pattern']

FLAGS = (VERBOSE | MULTILINE | DOTALL)

class Scanner(object):
    def __init__(self, lexicon, flags=FLAGS):
        self.actions = [None]
        # Combine phrases into a compound pattern
        s = sre_parse.Pattern()
        s.flags = flags
        p = []
        for idx, token in enumerate(lexicon):
            phrase = token.pattern
            try:
                subpattern = sre_parse.SubPattern(s,
                    [(SUBPATTERN, (idx + 1, sre_parse.parse(phrase, flags)))])
            except sre_constants.error:
                raise
            p.append(subpattern)
            self.actions.append(token)

        s.groups = len(p) + 1 # NOTE(guido): Added to make SRE validation work
        p = sre_parse.SubPattern(s, [(BRANCH, (None, p))])
        self.scanner = sre_compile.compile(p)

    def iterscan(self, string, idx=0, context=None):
        """
        Yield match, end_idx for each match
        """
        match = self.scanner.scanner(string, idx).match
        actions = self.actions
        lastend = idx
        end = len(string)
        while True:
            m = match()
            if m is None:
                break
            matchbegin, matchend = m.span()
            if lastend == matchend:
                break
            action = actions[m.lastindex]
            if action is not None:
                rval, next_pos = action(m, context)
                if next_pos is not None and next_pos != matchend:
                    # "fast forward" the scanner
                    matchend = next_pos
                    match = self.scanner.scanner(string, matchend).match
                yield rval, matchend
            lastend = matchend


def pattern(pattern, flags=FLAGS):
    def decorator(fn):
        fn.pattern = pattern
        fn.regex = re.compile(pattern, flags)
        return fn
    return decorator
########NEW FILE########
__FILENAME__ = main
# !/usr/bin/env python
#
# Copyright 2008 Gabriel Handford
#
"""Shrub: Amazon S3 Proxy (http://shrub.appspot.com)"""

__author__ = "Gabriel Handford"
__email__ = "gabrielh@gmail.com"
__copyright__= "Copyright (c) 2008, Gabriel Handford"
__license__ = "MIT"
__url__ = "http://shrub.appspot.com"

import sys
import os
import logging
sys.path = [ os.path.join(os.path.dirname(__file__), "lib") ] + sys.path

import re
import datetime
import wsgiref.handlers

from google.appengine.ext import webapp

from app.controllers.base import PrintEnvironmentHandler
from app.controllers.s3 import DefaultPage, S3Page

def main():
	application = webapp.WSGIApplication([
		('/', DefaultPage),
		('/shrub-env', PrintEnvironmentHandler),
		('/.*', S3Page),
		], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = rss
import rfc822
import time

class Item:
	'''Item in an RSS feed'''
	
	def __init__(self, title, link, description=None, pub_date=None, guid=None):
		self.title = title
		self.link = link
		self.description = description
		self.pub_date = pub_date
		self.guid = guid
		
	@property
	def rfc822_pub_date(self):
		if self.pub_date is None:
			return None
		return rfc822.formatdate(time.mktime(self.pub_date.timetuple()))


########NEW FILE########
__FILENAME__ = xspf

class Track:
	'''Track in an XSPF feed'''
	
	def __init__(self, location, meta, title, info):
		self.location = location
		self.meta = meta
		self.title = title
		self.info = info
		
	def __str__(self):
		return 'location=%s,meta=%s,title=%s,info=%s' % (self.location, self.meta, self.title, self.info)


########NEW FILE########
__FILENAME__ = file
import urllib
import re

import shrub.feeds.rss
import shrub.feeds.xspf

from shrub.utils import url_escape
from shrub.gae_utils import current_gae_url

class S3File:

	DefaultLocation = 's3.amazonaws.com'
	DefaultContentType = 'application/octet-stream'
	
	def __init__(self, bucket=None, key=None):
		self.id = u'%s/%s' % (bucket, key)
		self.bucket = bucket
		self.key = key
		self.name = key
		self.metadata = {}
		self.content_type = self.DefaultContentType
		self.filename = None
		self.etag = None
		self.last_modified = None
		self.owner = None
		self.storage_class = None
		self.size = None
		self.is_folder = False
		
		self.pretty_last_modified_cache = None
		self.pretty_size_cache = None
		
	def __hash__(self):
		return self.id.__hash__()
		
	def __eq__(self, other):
		return self.id.__eq__(other.id)
		
	def __str__(self):
		return u'%s/%s' % (self.bucket, self.key)
		
	def __json__(self):
		return dict(bucket=self.bucket, key=self.key, etag=self.etag, lastModified=self.last_modified,
		size=self.size, storageClass=self.storage_class)
		
	def name_with_prefix(self, prefix, urlescape=False):
		def maybe_escape(s):
			return url_escape(s, plus=False) if urlescape else s

		name = maybe_escape(self.name)
		if prefix:
			if prefix.endswith('/'): return maybe_escape(prefix) + name
			else: return "%s/%s" % (maybe_escape(prefix), name)

		return name

	def pretty_last_modified(self, default):
		if not self.last_modified: return default
		if not self.pretty_last_modified_cache: self.pretty_last_modified_cache = self.last_modified.strftime("%b %d, %Y, %I:%M %p")
		return self.pretty_last_modified_cache
		
	def __pretty_size(self, size):
		if size == 0: return "-"
		suffixes = [("B",2**10), ("K",2**20), ("M",2**30), ("G",2**40), ("T",2**50)]
		for suf, lim in suffixes:
			if size > lim:
				continue
			else:
				return round(size/float(lim/2**10),2).__str__()+suf
				
	def pretty_size(self, default):
		if not self.size: return default
		if not self.pretty_size_cache: self.pretty_size_cache = self.__pretty_size(self.size)
		return self.pretty_size_cache
		
	@property
	def name_without_extension(self):
		position = self.name.rfind('.')
		if position == -1: return self.name
		return self.name[0:position]
		
	@property
	def extension(self):
		position = self.name.rfind('.')
		if position == -1: return
		return self.name[position + 1:]
		
	def to_appspot_url(self):
		if self.is_folder:
			name = re.sub(re.escape('_\$folder\$\Z'), '/', self.key)
		else:
			name = self.key
			
		return u'http://%s/%s/%s' % (current_gae_url(), url_escape(self.bucket), url_escape(name))
	appspot_url = property(to_appspot_url)
	
	def to_url(self, secure=False):
		scheme = 'http';
		if secure: scheme = 'https'
		if self.bucket.islower():
			return u'%s://%s.%s/%s' % (scheme, url_escape(self.bucket), self.DefaultLocation, url_escape(self.key))
		else:
			return u'%s://%s/%s/%s' % (scheme, self.DefaultLocation, url_escape(self.bucket), url_escape(self.key))
	url = property(to_url)
	
	def to_rss_item(self):
		link = self.url
		if self.is_folder:
			link = self.appspot_url
			
		description = None
		if not self.is_folder:
		#description = ' &nbsp; <a href="%s">Download</a>' % self.to_url(False)
			description = ''
			pretty_size = self.pretty_size(None)
			if pretty_size: description += 'Size: %sb' % pretty_size
			
		return shrub.feeds.rss.Item(self.name, None, description, pub_date=self.last_modified, guid=link)
	rss_item = property(to_rss_item)
	
	def to_xspf_track(self):
		return shrub.feeds.xspf.Track(location=self.url, meta=self.extension, title=self.name_without_extension, info=None)
	xspf_track = property(to_xspf_track)

########NEW FILE########
__FILENAME__ = gae_utils
import os
import logging

import shrub.utils

def current_gae_url():
	name = os.environ['SERVER_NAME']
	port = int(os.environ['SERVER_PORT'])
	
	if port == 80 or port == 443: return name
	return '%s:%s' % (name, port)

def parse_gae_request(request, prefix=None):
	"""Parse bucket name and prefix from gae request."""
	request_path = shrub.utils.url_unescape(request.path)
	#logging.info('request_path=%s (%s); prefix=%s' % (request_path, request.path, prefix))
	if prefix:
		request_path = re.sub('%s$' % prefix, '', request_path)

	bucket_name = None
	prefix = None

	if request_path != '/':
		paths = request_path.split('/')[1:]
		bucket_name = paths[0]
		prefix = '/'.join(paths[1:])

	return bucket_name, prefix
########NEW FILE########
__FILENAME__ = base
from shrub.response.sax.bucket import BucketParser

import shrub.utils

class S3BaseResponse(object):

	def __init__(self, url, status_code, try_count=None, times=None):
		self.url = url
		self.status_code = status_code
		self.try_count = try_count
		self.times = times

	@property
	def ok(self):
		return (self.status_code >= 200 and self.status_code <= 299)


class S3Response(S3BaseResponse):

	def __init__(self, parser_class, url, status_code, content=None, **kwargs):
		super(S3Response, self).__init__(url, status_code, **kwargs)
		self.parser_class = parser_class
		self.content = content
		self.message = None
		self._data = None

	def path_components(self, url_escape=True):
		bucket_name = self.data.name
		prefix = self.data.prefix

		dirs = [ bucket_name ]
		if prefix:
			dirs += [shrub.utils.url_escape(p) if url_escape else p for p in prefix.split("/")[:-1]]

		return dirs

	@property
	def path(self):
		return u'/'.join(self.path_components())

	@property
	def total_time(self):
		if self.times is None: return None
		return reduce(lambda x, y: x+y, self.times)

	@property
	def data(self):
		if not self._data:
			self._data = self.parser_class(self.content)
		return self._data


class S3ErrorResponse(S3BaseResponse):

	def __init__(self, url, status_code, message, **kwargs):
		super(S3ErrorResponse, self).__init__(url, status_code, **kwargs)
		self.message = message
		
	def __str__(self):
		return self.message


class S3BucketResponse(S3Response):

	def __init__(self, url, status_code, content, **kwargs):
		super(S3BucketResponse, self).__init__(BucketParser, url, status_code, content, **kwargs)

		self.is_truncated = self.data.is_truncated
		self.max_keys = self.data.max_keys
		self.files = self.data.files
		self.next_marker = None
		if self.is_truncated:
			self.next_marker = self.data.next_marker

########NEW FILE########
__FILENAME__ = bucket
import re, iso8601, traceback, logging
import xml.sax
from xml.sax.handler import ContentHandler, ErrorHandler

from shrub.file import S3File

from shrub.response.sax.object import ObjectParser

class Parser(ContentHandler):
	pass
	
class BucketParser(Parser):
	"""
	SAX parser for ListBucketResult response.
	
  <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Name>stuff</Name>
    <Prefix></Prefix>
    <Marker></Marker>
    <MaxKeys>1000</MaxKeys>
    <NextMarker>somefile</NextMarker>
    <IsTruncated>false</IsTruncated>
    <Contents>
      <Key>01 Gabe&apos;s Mix Tape 2007-11-17.mp3</Key>
      <LastModified>2007-11-17T22:34:27.000Z</LastModified>
      <ETag>&quot;b034f4ff7eca12eefc2e5c2a207f45eb&quot;</ETag>
      <Size>67653780</Size>
      <StorageClass>STANDARD</StorageClass>
    </Contents>
    <Contents>...</Contents>
    <CommonPrefixes><Prefix>foo/bar</Prefix></CommonPrefixes>
		<CommonPrefixes><Prefix>foo/baz</Prefix></CommonPrefixes>"""
	
	def __init__(self, content=None):
		self.name = None
		self.marker = None
		self.next_marker = None
		self.is_truncated = False
		self.prefix = None
		self.max_keys = None
		self.files = []
		self.prefixes = []
		self.dirs = set([])
		
		self.contents = []
		self.handler = None
		
		try:
			xml.sax.parseString(content, self)
		except:
			logging.info('Error parsing response: %s' % traceback.format_exc())
			raise
			
	def __json__(self):
		return dict(name=self.name, prefix=self.prefix, maxKeys=self.max_keys, isTrucated=self.is_truncated, contents=self.files, commonPrefixes=self.prefixes)
		
	def startElement(self, name, attrs):
		if self.handler != None:
			self.handler.startElement(name, attrs)
			return
			
		if name == 'Contents':
			self.handler = ObjectParser(self.name, self.prefix)
		elif name == 'CommonPrefixes':
			self.handler = PrefixesParser(self.name, self.prefix)
		else:
			self.handler = None
			
		return None
		
	def characters(self, content):
		if self.handler != None:
			self.handler.characters(content)
			return
			
		self.contents.append(content)
		
	def content(self):
		content = u''.join(self.contents)
		self.contents = []
		return content
		
	def endElement(self, name):
	
		content = self.content()
		
		if name == 'Contents':
			file = self.handler.file
			if not file:
				self.handler = None
				return

			self.files.append(file)
			if file.is_folder:
				self.dirs.add(file.name)
				
			self.handler = None
			return
		elif name == 'CommonPrefixes':
			for prefix in self.handler.prefixes:
				if not prefix.name in self.dirs and prefix.name:
					self.files.append(prefix)
					
			self.handler = None
			return
			
		if self.handler != None:
			self.handler.endElement(name)
			return
			
		if name == 'Name':
			self.name = content
		if name == 'IsTruncated':
			self.is_truncated = content == 'true'
		elif name == 'Marker':
			self.marker = content
		elif name == 'NextMarker':
			self.next_marker = content
		elif name == 'Prefix':
			self.prefix = content
		elif name == 'MaxKeys':
			self.max_keys = content


class PrefixesParser(Parser):
	'''SAX parser for CommonPrefixes'''

	def __init__(self, bucket_name, prefix):
		self.bucket_name = bucket_name
		self.prefix = prefix
		self.prefixes = []
		self.contents = []
		
	def startElement(self, name, attrs):
		return None

	def characters(self, content):
		self.contents.append(content)

	def content(self):
		content = u''.join(self.contents)
		self.contents = []
		return content

	def endElement(self, name):

		content = self.content()

		if name == 'Prefix':
			prefix_name = content
			if self.prefix and self.prefix.endswith('/'):
				prefix_name = re.sub('\A%s' % re.escape(self.prefix), '', prefix_name)

			if not prefix_name or prefix_name == '/':
				return

			file = S3File(self.bucket_name, prefix_name)
			file.is_folder = True
			self.prefixes.append(file)


########NEW FILE########
__FILENAME__ = object
import logging, re, iso8601
import xml.sax
from xml.sax.handler import ContentHandler

from shrub.file import S3File

class ObjectParser(ContentHandler):

	def __init__(self, bucket_name, prefix):
		self.bucket_name = bucket_name
		self.prefix = prefix
		self.file = None
		self.contents = []
		
	def startElement(self, name, attrs):
		return None
		
	def characters(self, content):
		self.contents.append(content)
		
	def content(self):
		content = u''.join(self.contents)
		self.contents = []
		return content
		
	def endElement(self, name):
	
		content = self.content()
		
		if name == 'Key':
			key = content
			self.file = S3File(self.bucket_name, key)

			is_folder = False

			if self.prefix and self.prefix.endswith('/'):
				self.file.name = re.sub(re.escape(self.prefix), '', key)

			if not self.file.name:
				self.file = None
				return

			# Check if folder
			p = re.compile('_\$folder\$\Z')
			if p.search(self.file.name):
				self.file.name = p.sub('', self.file.name) + "/"
				self.file.is_folder = True

		elif name == 'ETag':
			if self.file:
				self.file.etag = content
		elif name == 'LastModified':
			if self.file:
				self.file.last_modified = iso8601.parse_date(content)
		elif name == 'Size':
			if self.file:
				self.file.size = long(content)
		elif name == 'StorageClass':
			if self.file:
				self.file.storage_class = content


########NEW FILE########
__FILENAME__ = s3
from __future__ import with_statement
import urllib
import logging
from datetime import datetime

from google.appengine.api import urlfetch

from shrub.response.base import S3BucketResponse, S3ErrorResponse
import shrub.utils

class S3:

	DefaultLocation = 's3.amazonaws.com'

	def _fetch(self, url, retry_count, **kwargs):
		"""Calls urlfetch.fetch with retry count"""
		try_count = 0
		times = []
		response = None
		while try_count < retry_count:
			try:
				try_count += 1

				# Fetch the url
				fetch_start = datetime.now()
				response = urlfetch.fetch(url, **kwargs)
				times.append(datetime.now() - fetch_start)

				# TODO(gabe): Handle PermanentRedirect error messages (no Location header on 301 so need to handle manually)

				# Retry on 5xx errors as well as urlfetch exceptions
				if int(response.status_code) in xrange(500, 600):
					logging.info('Failed with status: %s, retrying' % (response.status_code))
					continue

				return response, try_count, times

			except Exception, error:
				logging.error('Error(%s): %s' % (try_count, error))
				if try_count >= retry_count:
					raise
		return response, try_count, times

	def list(self, bucket_name, max_keys=None, prefix=None, delimiter=None, marker=None, cache=60, retry_count=3):
		if retry_count < 0: raise ValueError, "Invalid retry_count < 0"

		url_options = dict(prefix=prefix, delimiter=delimiter, marker=marker)
		if max_keys: url_options['max-keys'] = str(max_keys)

		# Use http://bucketname.s3.amazonaws.com, instead of http://s3.amazonaws.com/bucketname
		url = u'http://%s.%s/?%s' % (bucket_name, S3.DefaultLocation, shrub.utils.params_to_url(url_options, True))
		logging.info("URL: %s", url)

		headers = {'Cache-Control':'max-age=%s' % (cache)}
		try:
			response, try_count, times = self._fetch(url, retry_count, headers=headers)
			return S3BucketResponse(url, int(response.status_code), response.content, try_count=try_count, times=times)
		except Exception, error:
			# TODO(gabe): Need to disable this in debug mode, so exceptions raise properly
			return S3ErrorResponse(url, 503, str(error))


########NEW FILE########
__FILENAME__ = utils
import urllib
import cgi
import re

def html_escape(string):
	return cgi.escape(string, True)

def url_escape(string, plus=False):
	# convert into a list of octets
	string = string.encode("utf8")
	return urllib.quote_plus(string) if plus else urllib.quote(string)

def url_unescape(string):
	text = urllib.unquote_plus(string)
	if not is_ascii_str(text):
		text = text.decode("utf8")
	return text

_ASCII_re = re.compile(r'\A[\x00-\x7f]*\Z')

def is_ascii_str(text):
	return isinstance(text, str) and _ASCII_re.match(text)

def params_to_url(params, urlescape=False):
	def maybe_escape(s):
		return url_escape(s) if urlescape else s
	pairs = ['%s=%s' % (maybe_escape(key), maybe_escape(value)) for key, value in params.items() if key is not None and value is not None]
	return '&'.join(pairs)

def file_comparator(x, y, sort, sort_asc):

	a = b = None

	if sort == "key" or sort == "size" or sort == "last_modified":
		a = getattr(x, sort)
		b = getattr(y, sort)

	if a is None and b is not None: return 1
	elif a is not None and b is None: return -1
	elif a is None and b is None: return 0

	if isinstance(a, str) or isinstance(a, unicode): a = a.lower()
	if isinstance(b, str) or isinstance(b, unicode): b = b.lower()

	if sort_asc: return cmp(a, b)
	else: return cmp(b, a)

########NEW FILE########
__FILENAME__ = test_formats
import logging
import unittest

from webtest import TestApp

from controllers import test_helper

class TestControllerFormats(unittest.TestCase):
  
  def setUp(self):
    self.application = test_helper.get_application()
  
  def test_html(self):
    app = TestApp(self.application)
    response = app.get('/s3hub/')
    self.assertEqual('200 OK', response.status)
    # XXX: Actually test the data
    self.assertTrue('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">' in response)    
    
  def test_rss(self):
    app = TestApp(self.application)
    response = app.get('/s3hub/?format=rss')
    self.assertEqual('200 OK', response.status)
    # XXX: Actually test the data
    self.assertTrue('<?xml version="1.0" encoding="UTF-8"?>' in response)
    
  def test_json(self):
    app = TestApp(self.application)
    response = app.get('/s3hub/?format=json')
    self.assertEqual('200 OK', response.status)
    # XXX: Actually test the data
    self.assertTrue('"bucket": "s3hub"' in response)
    
  def test_xspf(self):
    app = TestApp(self.application)
    response = app.get('/m1xes/sub-pop-mix-1/?format=xspf')
    self.assertEqual('200 OK', response.status)
    # XXX: Actually test the data
    self.assertTrue('<playlist version="0" xmlns="http://xspf.org/ns/0/">' in response)
    
  def test_tape(self):
    app = TestApp(self.application)
    response = app.get('/m1xes/sub-pop-mix-1/?format=tape')
    self.assertEqual('200 OK', response.status)
    # XXX: Actually test the data
    self.assertTrue('<ul id="songs">' in response)
    
  def test_id3(self):
    app = TestApp(self.application)
    response = app.get('/m1xes/sub-pop-mix-1/01-Dntel-The_Distance_%28ft._Arthur%26Yu%29.mp3?format=id3-json')
    self.assertEqual('200 OK', response.status)
    # XXX: Actually test the data
    self.assertTrue('"title": "The Distance (Ft. Arthur & Yu)"' in response)
########NEW FILE########
__FILENAME__ = test_helper

from app.controllers.s3 import DefaultPage, S3Page
from google.appengine.ext import webapp

def get_application():
  return webapp.WSGIApplication([('/', DefaultPage),('/.*', S3Page)], debug=True)
    
########NEW FILE########
__FILENAME__ = test_s3
import logging
import unittest

from controllers import test_helper
from webtest import TestApp

class TestS3(unittest.TestCase):
  
  def setUp(self):
    self.application = test_helper.get_application()
  
  def test_home(self):
    app = TestApp(self.application)
    response = app.get('/')
    self.assertEqual('200 OK', response.status)
    self.assertTrue('Amazon S3 Proxy' in response)  
########NEW FILE########
__FILENAME__ = gaeunit
#!/usr/bin/env python
'''
GAEUnit: Google App Engine Unit Test Framework

Usage:

1. Put gaeunit.py into your application directory.  Modify 'app.yaml' by
   adding the following mapping below the 'handlers:' section:

   - url: /test.*
     script: gaeunit.py

2. Write your own test cases by extending unittest.TestCase.

3. Launch the development web server.  Point your browser to:

     http://localhost:8080/test?name=my_test_module

   Replace 'my_test_module' with the module that contains your test cases,
   and modify the port if necessary.
   
   For plain text output add '&format=plain' to the URL.

4. The results are displayed as the tests are run.

Visit http://code.google.com/p/gaeunit for more information and updates.

------------------------------------------------------------------------------
Copyright (c) 2008, George Lei and Steven R. Farley.  All rights reserved.

Distributed under the following BSD license:

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
------------------------------------------------------------------------------
'''

__author__ = "George Lei and Steven R. Farley"
__email__ = "George.Z.Lei@Gmail.com"
__version__ = "#Revision: 1.2.2 $"[11:-2]
__copyright__= "Copyright (c) 2008, George Lei and Steven R. Farley"
__license__ = "BSD"
__url__ = "http://code.google.com/p/gaeunit"

import sys
import os
import unittest
import StringIO
import time
import re
import logging
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import apiproxy_stub_map  
from google.appengine.api import datastore_file_stub
from google.appengine.api import urlfetch_stub
from google.appengine.api.memcache import memcache_stub


_DEFAULT_TEST_DIR = 'test'

##############################################################################
# Web Test Runner
##############################################################################
class _WebTestResult(unittest.TestResult):
    def __init__(self):
        unittest.TestResult.__init__(self)
        self.testNumber = 0

    def getDescription(self, test):
        return test.shortDescription() or str(test)

    def printErrors(self):
        stream = StringIO.StringIO()
        stream.write('{')
        self.printErrorList('ERROR', self.errors, stream)
        stream.write(',')
        self.printErrorList('FAIL', self.failures, stream)
        stream.write('}')
        return stream.getvalue()

    def printErrorList(self, flavour, errors, stream):
        stream.write('"%s":[' % flavour)
        for test, err in errors:
            stream.write('{"desc":"%s", "detail":"%s"},' %
                         (self.getDescription(test), self.escape(err)))
        if len(errors):
            stream.seek(-1, 2)
        stream.write("]")

    def escape(self, s):
        newstr = re.sub('"', '&quot;', s)
        newstr = re.sub('\n', '<br/>', newstr)
        return newstr
        

class WebTestRunner:
    def run(self, test):
        "Run the given test case or test suite."
        result = getTestResult(True)
        result.testNumber = test.countTestCases()
        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = stopTime - startTime
        return result

#############################################################
# Http request handler
#############################################################

class GAEUnitTestRunner(webapp.RequestHandler):
    def __init__(self):
        self.package = "test"
        
    def get(self):
        """Execute a test suite in response to an HTTP GET request.

        The request URL supports the following formats:
        
          http://localhost:8080/test?package=test_package
          http://localhost:8080/test?name=test
        
        Parameters 'package' and 'name' should not be used together.  If both
        are specified, 'name' is selected and 'package' is ignored.
        
        When 'package' is set, GAEUnit will run all TestCase classes from
        all modules in the package.
        
        When 'name' is set, GAEUnit will assume it is either a module (possibly
        preceded by its package); a module and test class; or a module,
        test class, and test method.  For example,
        
          http://localhost:8080/test?name=test_package.test_module.TestClass.test_method
        
        runs only test_method() whereas,
        
          http://localhost:8080/test?name=test_package.test_module.TestClass
        
        runs all test methods in TestClass, and
        
          http://localhost:8080/test?name=test_package.test_module
         
        runs all test methods in all test classes in test_module.
        
        If the default URL is requested:
        
          http://localhost:8080/test
        
        it is equivalent to 
        
          http://localhost:8080/test?package=test 

        """
        svcErr = getServiceErrorStream()

        format = self.request.get("format")
        if not format or format not in ["html", "plain"]:
            format = "html"

        unknownArgs = [arg for arg in self.request.arguments() if arg not in ("package", "name", "format")]
        if len(unknownArgs) > 0:
            for arg in unknownArgs:
                _logError("The parameter '%s' is unrecognizable, please check it out." % arg)
        
        package_name = self.request.get("package")
        test_name = self.request.get("name")
        
        loader = unittest.defaultTestLoader
        suite = unittest.TestSuite()

        # As a special case for running tests under the 'test' directory without
        # needing an "__init__.py" file:
        if not _DEFAULT_TEST_DIR in sys.path:
            sys.path.append(_DEFAULT_TEST_DIR)

        if not package_name and not test_name:
            module_names = [mf[0:-3] for mf in os.listdir(_DEFAULT_TEST_DIR) if mf.endswith(".py")]
            for module_name in module_names:
                module = reload(__import__(module_name))
                suite.addTest(loader.loadTestsFromModule(module))
        elif test_name:
            try:
                module = reload(__import__(test_name))
                suite.addTest(loader.loadTestsFromModule(module))
            except:
                pass
        elif package_name:
            try:                
                package = reload(__import__(package_name))
                module_names = package.__all__
                for module_name in module_names:
                    suite.addTest(loader.loadTestsFromName('%s.%s' % (package_name, module_name)))
            except Exception, error:
              _logError("Error loading package '%s': %s" % (package_name, error))
        if suite.countTestCases() > 0:
            runner = None
            if format == "html":
                runner = WebTestRunner()
                self.response.out.write(testResultPageContent)
            else:
                self.response.headers["Content-Type"] = "text/plain"
                if svcErr.getvalue() != "":
                    self.response.out.write(svcErr.getvalue())
                else:
                    self.response.out.write("====================\n" \
                                            "GAEUnit Test Results\n" \
                                            "====================\n\n")
                    runner = unittest.TextTestRunner(self.response.out)
            if runner:
                self._runTestSuite(runner, suite)
        else:
            _logError("'%s' is not found or does not contain any tests." % \
                      (test_name or package_name))


    def _runTestSuite(self, runner, suite):
        """Run the test suite.

        Preserve the current development apiproxy, create a new apiproxy and
        temporary datastore that will be used for this test suite, run the
        test suite, and restore the development apiproxy.  This isolates the
        test and development datastores from each other.

        """        
        original_apiproxy = apiproxy_stub_map.apiproxy
        try:
           apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap() 
           temp_stub = datastore_file_stub.DatastoreFileStub(
               'GAEUnitDataStore', None, None)  
           apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', temp_stub)
           apiproxy_stub_map.apiproxy.RegisterStub('urlfetch', urlfetch_stub.URLFetchServiceStub())
           apiproxy_stub_map.apiproxy.RegisterStub('memcache', memcache_stub.MemcacheServiceStub())
           
           runner.run(suite)
        finally:
           apiproxy_stub_map.apiproxy = original_apiproxy

                
class ResultSender(webapp.RequestHandler):
    def get(self):
        cache = StringIO.StringIO()
        result = getTestResult()
        if svcErr.getvalue() != "":
            cache.write('{"svcerr":%d, "svcinfo":"%s",' %
                        (1, svcErr.getvalue()))
        else:
            cache.write('{"svcerr":%d, "svcinfo":"%s",' % (0, ""))
            cache.write(('"runs":"%d", "total":"%d", ' \
                         '"errors":"%d", "failures":"%d",') %
                        (result.testsRun, result.testNumber,
                         len(result.errors), len(result.failures)))
            cache.write('"details":%s' % result.printErrors())
        cache.write('}')
        self.response.out.write(cache.getvalue())


svcErr = StringIO.StringIO()
testResult = None

def getServiceErrorStream():
    global svcErr
    if svcErr:
        svcErr.truncate(0)
    else:
        svcErr = StringIO.StringIO()
    return svcErr

def _logInfo(s):
    logging.info(s)

def _logError(s):
    # TODO: When using 'plain' format, the error is not returned to
    #       the HTTP client.  To fix this, svcErr must have been previously set
    #       to self.response.out for the plain format.  Also, a non-200 error
    #       code would help 'curl' and other automated clients to determine
    #       the success/fail status of the test suite.
    logging.warn(s)
    svcErr.write(s)
    
def getTestResult(createNewObject=False):
    global testResult
    if createNewObject or not testResult:
        testResult = _WebTestResult()
    return testResult



################################################
# Browser codes
################################################

testResultPageContent = """
<html>
<head>
    <style>
        body {font-family:arial,sans-serif; text-align:center}
        #title {font-family:"Times New Roman","Times Roman",TimesNR,times,serif; font-size:28px; font-weight:bold; text-align:center}
        #version {font-size:87%; text-align:center;}
        #weblink {font-style:italic; text-align:center; padding-top:7px; padding-bottom:20px}
        #results {margin:0pt auto; text-align:center; font-weight:bold}
        #testindicator {width:950px; height:16px; border-style:solid; border-width:2px 1px 1px 2px; background-color:#f8f8f8;}
        #footerarea {text-align:center; font-size:83%; padding-top:25px}
        #errorarea {padding-top:25px}
        .error {border-color: #c3d9ff; border-style: solid; border-width: 2px 1px 2px 1px; width:945px; padding:1px; margin:0pt auto; text-align:left}
        .errtitle {background-color:#c3d9ff; font-weight:bold}
    </style>
    <script language="javascript" type="text/javascript">
        /* Create a new XMLHttpRequest object to talk to the Web server */
        var xmlHttp = false;
        /*@cc_on @*/
        /*@if (@_jscript_version >= 5)
        try {
          xmlHttp = new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {
          try {
            xmlHttp = new ActiveXObject("Microsoft.XMLHTTP");
          } catch (e2) {
            xmlHttp = false;
          }
        }
        @end @*/
        if (!xmlHttp && typeof XMLHttpRequest != 'undefined') {
          xmlHttp = new XMLHttpRequest();
        }

        function callServer() {
          var url = "/testresult";
          xmlHttp.open("GET", url, true);
          xmlHttp.onreadystatechange = updatePage;
          xmlHttp.send(null);
        }

        function updatePage() {
          if (xmlHttp.readyState == 4) {
            var response = xmlHttp.responseText;
            var result = eval('(' + response + ')');
            if (result.svcerr) {
                document.getElementById("errorarea").innerHTML = result.svcinfo;
                testFailed();
            } else {                
                setResult(result.runs, result.total, result.errors, result.failures);
                var errors = result.details.ERROR;
                var failures = result.details.FAIL;
                var details = "";
                for(var i=0; i<errors.length; i++) {
                    details += '<p><div class="error"><div class="errtitle">ERROR '+errors[i].desc+'</div><div class="errdetail"><pre>'+errors[i].detail+'</pre></div></div></p>';
                }
                for(var i=0; i<failures.length; i++) {
                    details += '<p><div class="error"><div class="errtitle">FAILURE '+failures[i].desc+'</div><div class="errdetail"><pre>'+failures[i].detail+'</pre></div></div></p>';
                }
                document.getElementById("errorarea").innerHTML = details;
            }
          }
        }

        function testFailed() {
            document.getElementById("testindicator").style.backgroundColor="red";
            clearInterval(timer);
        }
        
        function testSucceed() {
            document.getElementById("testindicator").style.backgroundColor="green";
            clearInterval(timer);
        }

        function setResult(runs, total, errors, failures) {
            document.getElementById("testran").innerHTML = runs;
            document.getElementById("testtotal").innerHTML = total;
            document.getElementById("testerror").innerHTML = errors;
            document.getElementById("testfailure").innerHTML = failures;
            if (errors==0 && failures==0) {
                testSucceed();
            } else {
                testFailed();
            }
        }

        // Update page every 5 seconds
        var timer = setInterval(callServer, 3000);
    </script>
    <title>GAEUnit: Google App Engine Unit Test Framework</title>
</head>
<body>
    <div id="headerarea">
        <div id="title">GAEUnit: Google App Engine Unit Test Framework</div>
        <div id="version">version 1.2.2</div>
        <div id="weblink">Please check <a href="http://code.google.com/p/gaeunit">http://code.google.com/p/gaeunit</a> for the latest version</div>
    </div>
    <div id="resultarea">
        <table id="results"><tbody>
            <tr><td colspan="3"><div id="testindicator"> </div></td</tr>
            <tr>
                <td>Runs: <span id="testran">0</span>/<span id="testtotal">0</span></td>
                <td>Errors: <span id="testerror">0</span></td>
                <td>Failures: <span id="testfailure">0</span></td>
            </tr>
        </tbody></table>
    </div>
    <div id="errorarea">The test is running, please wait...</div>
    <div id="footerarea">
        Please write to the <a href="mailto:George.Z.Lei@Gmail.com">author</a> to report problems<br/>
        Copyright 2008 George Lei and Steven R. Farley
    </div>
</body>
</html>
"""

application = webapp.WSGIApplication([('/test', GAEUnitTestRunner),
                                      ('/testresult', ResultSender)],
                                      debug=True)

def main():
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = debugapp
from webob import Request
try:
    sorted
except NameError:
    from webtest import sorted

__all__ = ['debug_app']

def debug_app(environ, start_response):
    req = Request(environ)
    if 'error' in req.GET:
        raise Exception('Exception requested')
    status = req.GET.get('status', '200 OK')
    parts = []
    for name, value in sorted(environ.items()):
        if name.upper() != name:
            value = repr(value)
        parts.append('%s: %s\n' % (name, value))
    req_body = req.body
    if req_body:
        parts.append('-- Body ----------\n')
        parts.append(req_body)
    body = ''.join(parts)
    headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(body)))]
    for name, value in req.GET.items():
        if name.startswith('header-'):
            header_name = name[len('header-'):]
            headers.append((header_name, value))
    start_response(status, headers)
    return [body]

def make_debug_app(global_conf):
    """
    An application that displays the request environment, and does
    nothing else (useful for debugging and test purposes).
    """
    return debug_app
########NEW FILE########
__FILENAME__ = test
# !/usr/bin/env python
#
# Copyright 2008 Gabriel Handford
#

import sys
import os
import logging
sys.path = [ 
  os.path.join(os.path.dirname(__file__), "lib"), 
  os.path.join(os.path.dirname(__file__), "test"),
  os.path.join(os.path.dirname(__file__), "test", "lib") ] + sys.path

import gaeunit

if __name__ == '__main__':
  gaeunit.main()
########NEW FILE########
