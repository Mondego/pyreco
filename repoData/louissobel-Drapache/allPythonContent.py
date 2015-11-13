__FILENAME__ = config
"""
Provides configuration for the drapache server
"""

################### flat file
# subdomain file path
SUBDOMAIN_FILE = ""


################## other stuff
DEFAULT_PORT = 5501 #just because

################## dropbox config
# api app-key
APP_KEY = ''

# api app-secret
APP_SECRET = ''


########NEW FILE########
__FILENAME__ = dbpy_doc_parser
import drapache.dbpy.builtins.dbpy as dbpy


import re
import inspect	
import pprint
		
import json		

def get_help_hash(module):
	
	children = []
	doc = {'type':'module','name':module.name,'children':children,'doc':module.__doc__}
		
	if hasattr(module,'submodules'):
		for child in module.submodules:
			
			if hasattr(child,'get_doc'):
				child_hash = child.get_doc()
			else:
				child_hash = get_help_hash(child)
			
			children.append(child_hash)
		
	module_code = inspect.getsource(module)
	
	#go through, finding attributes and functions
	
	mode = 'looking'
	cur_hash = {}
	cur_doc = []
	
	
	target = None
	
	attributes = []
	functions = []
	
	attribute_pattern = re.compile('#DOC:(.+)')
	function_pattern = re.compile('@env.register')
	
	def_pattern = re.compile('def (.+?):')
	
	for line in module_code.split('\n'):
		line = line.strip()
		
		#print "%s === %s" % (mode,line)
		
		if mode == 'looking':
			
			attr_match = attribute_pattern.match(line)
			if attr_match:
				cur_hash['type'] = 'attribute'
				cur_hash['name'] = attr_match.group(1)
				cur_hash['children'] = []
				target = attributes
				mode = 'doc_expecting'
				
			else:
				function_match = function_pattern.match(line)
				if function_match:
					cur_hash['type'] = 'function'
					cur_hash['children'] = []
					target = functions
					mode = 'def_expecting'
		
		elif mode == 'def_expecting':
			def_match = def_pattern.match(line)
			if def_match:
				mode = 'doc_expecting'
				cur_hash['name'] = def_match.group(1)
				
		elif mode == 'doc_expecting':
			if '"""' in line:
				mode = 'doc_sucking'
			function_match = function_pattern.match(line)
			if function_match:
				cur_hash['type'] = 'function'
				cur_hash['children'] = []
				target = functions
				mode = 'def_expecting'
		
		elif mode == 'doc_sucking':
			if '"""' in line:
				cur_hash['doc'] = ' '.join(cur_doc)
				target.append(cur_hash)
				cur_hash = {}
				cur_doc = []
				mode = 'looking'
			else:
				cur_doc.append(line)
		
	children.extend(attributes)
	children.extend(functions)
	
	return doc
		
if __name__ == "__main__":
	print json.dumps(get_help_hash(dbpy))
########NEW FILE########
__FILENAME__ = access
"""
Defines utility classes for connecting to dropbox

"""

import dropbox





class DropboxClientCreator:
	
	
	def __init__(self,app_key,app_secret,access_type='app_folder'):
		
		self.app_key = app_key
		self.app_secret = app_secret
		self.access_type = access_type
		
		
	def get_client(self,oauth_token,oauth_token_secret):
		
		sess = dropbox.session.DropboxSession(self.app_key,self.app_secret,self.access_type)
		sess.set_token(oauth_token,oauth_token_secret)
		client = dropbox.client.DropboxClient(sess)
		return client
		
		
class DropboxClientPool:
	pass
########NEW FILE########
__FILENAME__ = io
"""
Implements a class for locking and unlocking
As well as the FileObjects
"""
import uuid
import sys
import StringIO
import re
import dropbox
import json
import time
import os.path
import StringIO
import threading

class ReadableDropboxFile(StringIO.StringIO):
	
	def __init__(self,path,client):
		
		try:
			response,metadata = client.get_file_and_metadata(path)
		except dropbox.rest.ErrorResponse:
			#or should i throw an exception? hmmm
			#or should i return none
			raise IOError("Unable to read file")
	
		filestring = response.read()
		response.close()
		
		StringIO.StringIO.__init__(self,filestring)
		
		self.metadata = metadata

	def write_error(self,*args,**kwargs):
		raise IOError("Cannot write to a file opened for reading!")
	
	write = write_error
	writelines = write_error


class LiveDropboxFile(StringIO.StringIO):
	"""
	An in-memory file object representing a dropbox file
	It is 'live' in the sense that it once it is closed, all changes made are 
	reflected to dropbox. So it's not really live, but under sufficient pre-conditions
	(locking the file) it will be. A leaky abstraction I guess."""
	
	def __init__(self,path,client,download=True):
		
		self.__open = True
		
		self.path = path
		
		if download:
			readable = ReadableDropboxFile(path,client)
			StringIO.StringIO.__init__(self,readable.read())
			self.metadata = readable.metadata
			
		else:
			StringIO.StringIO.__init__(self)
			self.metadata = {}
		
		
	def is_open(self):
		return self.__open
	
	def _update(self,client):

		if self.__open:
			self.seek(0)
			client.put_file(self.path,self,overwrite=True)

	def _close(self,locker):

		if self.__open:

			try:
				self._update(locker.client)
			finally:
				locker.release(self.path)
				self.__open = False
		else:
			pass
			#this allows for mutliple accidental callings .close()


class WritableDropboxFile(LiveDropboxFile):
	
	def __init__(self,path,client,download=True,mode='append'):
		#mode is either write or append
		#if append, we have to download if download is true, which generally will
		#be set by the caller to True only if the file exists
		#so we only have to download the file if download is true and the mode is append
		do_download = (download and mode == 'append')
		LiveDropboxFile.__init__(self,path,client,do_download)
		if mode == 'append':
			self.seek(0,2)
			
		self.mode = mode
			
	def _update(self,client):
		LiveDropboxFile._update(self,client)
		if self.mode == 'append':
			self.seek(0,2)
		else:
			self.seek(0)
			
			
	def write(self,what):
		
		if not self.is_open():
			raise IOError('Cannot write to a closed file')
			
		if self.mode == 'append':
			self.seek(0,2)
		StringIO.StringIO.write(self,what)
		
	def writeline(self,line):
		self.write(line+'\n')
		
	def writelines(self,sequence):
		
		if not self.is_open():
			raise IOError('Cannot write to a closed file!')
		
		if self.mode == 'append':
			self.seek(0,2)
		StringIO.StringIO.writelines(self,sequence)
			


			
class JSONDropboxFile(LiveDropboxFile):
	
	def __init__(self,path,client,download=False):
		LiveDropboxFile.__init__(self,path,client,download=download)
		
		#throws a value error if the json isn't good
		if download:
			self.json_object = json.load(self)
		else:
			#caller is responseable for making this into an actual object if it wants
			self.json_object = None
			
		
	def _update(self,client):
		self.seek(0)
		
		try:
			json.dump(self.json_object,self,indent=4)
			self.truncate()
		except TypeError:
			self.seek(0)
			self.truncate()
			raise TypeError("cannot make a JSON object")
		
		LiveDropboxFile._update(self,client)
		
		
		
		
			
			
			


class DropboxFileLocker:
	
	def __init__(self,client):
		
		self.client = client
		self.open_files = []
		
		
	def lock(self,path,timeout=None):
		#create a client unique key
		#put a file _lockrequest_<client_key>_<filename>
		client = self.client

		request_folder,filename = path.rsplit('/',1)

		client_uuid = uuid.uuid4().hex[:12] #using first 12 digits of uuid
		flag_file = "_lockrequest_%s_%s" % (client_uuid,filename)
		flag_file_path = request_folder + '/' + flag_file


		try:
			client.put_file(flag_file_path,StringIO.StringIO('flag for file %s'%filename))
		except dropbox.rest.ErrorResponse:
			raise IOError('unable to put flag for locking')

		have_write_permission = False
		timedout = False

		lockrequest_regex = re.compile(r"_lockrequest_([0-9a-f]{12})_%s"%re.escape(filename),flags=re.I)
		lock_regex = re.compile(r"_lock_%s"%re.escape(filename),flags=re.I)
		file_regex = re.compile(re.escape(filename),flags=re.I)

		original_time = time.time()

		while not (have_write_permission or timedout):
			try:
				folder_meta = client.metadata(request_folder)
			except dropbox.rest.ErrorResponse:
				raise IOError('Unable to get metadata for folder to check locks and flags')

			unlocked = True
			first_in_line = False
			file_exists = False

			flag_list = []

			for file_meta in folder_meta['contents']:

				basename = os.path.basename(file_meta['path'])

				if lock_regex.match(basename):
					unlocked = False
					continue

				if file_regex.match(basename):
					file_exists = True
					continue

				flagmatch = lockrequest_regex.match(basename)

				if flagmatch and not file_meta.get('is_deleted'):	
					modtime_string = file_meta['modified']
					modtime_struct = time.strptime(modtime_string,"%a, %d %b %Y %H:%M:%S +0000")
					modtime = time.mktime(modtime_struct)

					this_uid = flagmatch.group(1)

					flag_list.append((modtime,this_uid))

			flag_list.sort()

			if not flag_list:
				raise IOError('There should not be an empty list of flags at this point')

			first_uid = flag_list[0][1]


			first_in_line = (first_uid == client_uuid)

			if unlocked and first_in_line:
				have_write_permission = True

			else:
				elapsed_time = time.time() - original_time
				if timeout:
					if elapsed_time > timeout:
						timedout =True
				time.sleep(.5)

		if have_write_permission:
			lock_file = "_lock_%s"%filename
			lock_file_path = request_folder + '/' + lock_file
	
			try:
				client.put_file(lock_file_path,StringIO.StringIO('lock for file %s'%filename))
			except dropbox.rest.ErrorResponse:
				raise IOError('Unable to put lock')
		
		try:
			client.file_delete(flag_file_path)
		except dropbox.rest.ErrorResponse:
			out =  IOError('unable to delete lock flag')
			out.bad_lock_path = flag_file_path
			raise out
		
		return file_exists
	

	def close_all(self,):
		for file_h in self.open_files:
			file_h._close(self)
			
	def register_open_file(self,file_h):
		self.open_files.append(file_h)

	def release(self,path):
		client = self.client
		
		#just have to delete the right lock file
		
		request_folder,filename = path.rsplit('/',1)
		lock_string = "_lock_%s"%filename
		lock_file_path = request_folder + '/' + lock_string
		try:
			client.file_delete(lock_file_path)
		except dropbox.rest.ErrorResponse:
			raise IOError("Unable to unlock file!")
		
		
		
		
	
########NEW FILE########
__FILENAME__ = jinja
"""
The class that allows templateing from dropbox
"""
import jinja2
import os
import dropbox

class TemplateNotFound(Exception):
	pass

class DropboxLoader(jinja2.BaseLoader):
	
	
	def __init__(self,client,search_root):
		self.client = client
		self.search_root = search_root		
		
	def get_source(self,environment,path):
			
			
		template_path = self.search_root + path
			
		try:
			f = self.client.get_file(template_path).read()
		except dropbox.rest.ErrorResponse as e:
			if e.status == 404:
				raise jinja2.TemplateNotFound(template_path)
			else:
				raise IOError("Error connecting to dropbox to download template")
			
		return f,template_path,True
		
def render_dropbox_template(client,template_path,data):
	
	search_root,path = template_path.rsplit('/',1)
	search_root += '/'
	
	env = jinja2.Environment(loader=DropboxLoader(client,search_root))
	
	try:
		template = env.get_template(path)
		output = template.render(**data)
	except jinja2.TemplateNotFound as e:
		raise TemplateNotFound()
	
	return output
########NEW FILE########
__FILENAME__ = dbfilehandlers
"""
refactors out the logic of handling files from the server itself

"""
from drapache import dbpy
import re
import os
from drapache import util
from drapache.util.http import Response

import markdown

def register(handler_list,checkfunction,func):
	
		
	handler_list.append({'check':checkfunction,'handler':func})


def get_handlers():
	

	handler_list = []
	
	#lookup order:
	
	#directory
	#dbpy
	#markdown
	#static
	
	#directory
	register(handler_list,check_directory,serve_directory)
	#dbpy
	register(handler_list,check_dbpy,serve_dbpy)
	#markdown
	register(handler_list,check_markdown,serve_markdown)
	#the rest
	register(handler_list,check_static,serve_static)
	
	return handler_list
		
### static handler
def check_static(file_meta):
	return True

def serve_static(file_meta,request_path,server):
	"""
	downloads and serves the file in path
	"""
	path = file_meta['path']
	f = server.client.get_file(path).read()
	if f.startswith('#DBPYEXECUTE'):
		#allows arbitrary text files to be run as dbpy code. security risk?
		#any way, it is like a bypass... back to dbpy
		param_dict = dict(client=server.client,request=server.request)
		return dbpy.execute.execute(f,**param_dict)
	headers = {'Content-type':server._get_content_type(file_meta)}
	return Response(200,f,headers)
	
	
#### directory handler
def check_directory(directory_meta):
	return directory_meta['is_dir']
	
def serve_directory(directory_meta,request_path,server):
	"""
	called when asked to serce a directory
	check for the presence of an index file and serve it (without redirect of course)
	or present an index if there isn't one
	lets lok through meta_info[contents], anything with index is of interest
	precedence is .dbpy, .html, .txt, and thats it

	for now, just auto generate an index, fun!
	"""
	
	#redirect like apache if we don't end the path with '/'
	if not request_path.endswith('/'):
		redirect_location = request_path+'/'
		if server.request.query_string:
			redirect_location += '?'+server.request.query_string
			
		return Response(301,'redirect',headers={'Location':redirect_location})


	#ok, lets build our index thing

	extensions_precedence = ('dbpy','html','txt')

	#build the re
	re_string = "^index\.(%s)$"%( '|'.join(extensions_precedence) )
	index_re = re.compile(re_string)

	index_paths = {}

	for file_meta in directory_meta['contents']:
		file_path = file_meta['path']
		base_name = os.path.basename(file_path)

		index_re_match = index_re.match(base_name)

		if index_re_match:
			match_type = index_re_match.group(1)
			index_paths[match_type] = file_meta


	for extension in extensions_precedence:
		if extension in index_paths:
			new_file_meta = index_paths[extension]
			new_request_path = request_path + os.path.basename(new_file_meta['path']) #we know request path ends with a '/'
			return server._serve_file(new_file_meta,new_request_path)

	#there are no index files, so lets return a default one
	index_file = util.index_generator.get_index_file(directory_meta['contents'],request_path,server.client)
	return Response(200,index_file)
	
	
########## dbpy handler
def check_dbpy(file_meta):
	path = file_meta['path']
	return path.endswith('.dbpy')

def serve_dbpy(file_meta,request_path,server):
	path = file_meta['path']
	f = server.client.get_file(path).read()
	if f.startswith("#NOEXECUTE"):
		#allows these files to be shared without getting executed
		headers = {'Content-type':'text/plain'}
		return Response(200,f,headers)

	param_dict = dict(client=server.client,request=server.request)
	return dbpy.execute.execute(f,**param_dict)
	
			
		
####markdown handler
def check_markdown(file_meta):
	path = file_meta['path']
	markdown_extension_re = re.compile("\.(md|mkd|mkdn|mdown|markdown)$")
	return bool( markdown_extension_re.search( os.path.basename(path) ) )

def serve_markdown(file_meta,request_path,server):

	page_template = """
	<html>
	<head>
		<title>
			%s
		</title>
	</head>
	
	<body>
		%s
	</body>
	</html>
	"""
	path = file_meta['path']
	page_title = "%s | Markdown" % path
	page_body = markdown.markdown(server.client.get_file(path).read())
	
	page = page_template % (page_title,page_body)
	
	headers = {'Content-Type':'text/html'}
	return Response(200,page,headers)
	
	

########NEW FILE########
__FILENAME__ = client_wrapper

name = 'api'

__doc__ = "Access to the raw dropbox API methods"




WRAPPED_METHODS = [
	'account_info',
	'add_copy_ref',
	'create_copy_ref',
	'delta',
	'file_copy',
	'file_create_folder',
	'file_delete',
	'file_move',
	'get_file',
	'get_file_and_metadata',
	'media',
	'metadata',
	'put_file',
	'request',
	'restore',
	'revisions',
	'search',
	'share',
	'thumbnail',
	'thumbnail_and_metadata',
	]
	
def get_doc():

	import dropbox
	import inspect

	children = []
	out_hash = {'type':'module','name':name,'children':children,'doc':__doc__}
	
	for method in WRAPPED_METHODS:
		
		db_function = getattr(dropbox.client.DropboxClient,method)
		
		args, varargs, varkw, defaults = inspect.getargspec(db_function)
		argspec = inspect.formatargspec(args, varargs, varkw, defaults)
		
		new_hash = {'type':'function','name':method+argspec,'children':None,'doc':db_function.__doc__}
	
		children.append(new_hash)
	return out_hash

def build(env,path):
	
	self = env.get_new_module(path+'.'+name)
	
	
	def register_client_method(method_name):
		
		method = getattr(env.client,method_name)
		
		@env.register(self)
		@env.protected
		def outer_function(*args,**kwargs):
			return method(*args,**kwargs)
		
		
########NEW FILE########
__FILENAME__ = http


name = 'http'

__doc__ = "The http module provides access to methods concerning the http request and response"

def build(env,path):
	
	self = env.get_new_module(path+'.'+name)
	
	dbpy = env.get_module('dbpy')
	
	
	#TODO:
	#look... all this duplication of data in the request.
	#eh.
	
	#DOC:get_params
	"""
	The parsed parameters from the request url in a multidict
	"""
	self.get_params = env.get_params
	
	#DOC:post_params
	"""
	If the request was a post request, the parsed parameters from the body of the post
	"""
	self.post_params = env.post_params
	
	#DOC:request
	"""
	The raw request object.
	"""
	self.request = env.request
	
	
	@env.register(self)
	def set_response_header(header,value):
		"""
		Sets the header `header` to the value given by `value`
		"""
		env.response.set_header(header,value)
		
	@env.register(self)
	def get_request_header(header):
		"""
		Returns the header specified by `header`
		"""
		return env.request.headers.get(header)
	
	@env.register(self)
	def set_response_status(status):
		"""
		Sets the HTTP Status code of the response to `status`
		"""
		env.response.status = status
		
	@env.register(self)
	def redirect(where,immediately=True,status=302):
		"""
		Redirects the HTTP request to another location.
		The target location is given by `where`.
		If immediately is true, the script will exit immediately once this function is executed.
		The status is 302 by default, but could be set to whatever.
		"""
		
		set_response_status(302)
		set_response_header('Location',where)
		if immediately:
			dbpy.die("redirecting")
			
	@env.register(self)
	def error(which,message,immediately=True):
		"""
		Returns an error response
		"""
		env.response.status = which
		env.response.body = message
		env.response.error = True
		if immediately:
			dbpy.die("User Error - %d" % which)
			
			
	return self
########NEW FILE########
__FILENAME__ = file
import dropbox

from drapache import dbapi

import sys

name = 'file'

__doc__ = "Functions for reading/writing with files that live on dropbox"

def build(env,path):
	
	self = env.get_new_module(path+'.'+name)
	
	dbpy = env.get_module('dbpy')
	
	@env.register(self)
	@env.privileged
	def _get_lock(path,timeout):
		"""
		Internal function, public because, why hide it?
		"""
		try:
			file_exists = env.locker.lock(path,timeout)
		except IOError as e:
			#then I wasn't able to lock
			raise IOError("Timeout waiting to open %s for writing or appending'%path")
			
		return file_exists

	@env.register(self)
	@env.privileged
	def _release_lock(path):
		"""
		Internal function, public because, why hide it?
		"""
		#throws an IOError if it doesn't work
		env.locker.release(path)
	
	@env.register(self)
	@env.privileged
	def open(path,to='read',timeout=None,allow_download=True):
		"""
		Opens a file on your dropbox.
		There are three modes: read, write, append, and json. If the mode is read, the file is simply
		downloaded and a file-like (StringIO) object is returned. If the mode is write, append or json
		the function will try for `timeout` seconds to obtain a lock for the given path. If it fails,
		it will raise an `IOError`. Otherwise, it will then download the file and return either
		a file-like filehandle (in the case of write mode) or a json dictionary handle that will update
		back to the dropbox file (in the case of json mode).
		
		If the mode is append, all writes will start at the end. If the mode is write, all writes will overwrite
		the data starting at the start of the file.
		
		"""
		#if path starts with /, it is absolute.
		#otherwise, it is relative to the request path
		if not path.startswith('/'):
			path = env.request_folder + path
				
		if to == 'read':
			try:
				out_file = dbapi.io.ReadableDropboxFile(path,env.client)
			except IOError:
				raise IOError('unable to open file %s for reading'%path)
			
		elif to == 'write' or to == 'append' or to == 'json':
			
			#this throws an IOError if it doesn't work
			file_exists = _get_lock(path,timeout)
			
			#I have the lock at this point
			#only download the file if it exists and allow_download is set to true
			#this allows a forced overwrite by setting allow_download to false
			download = file_exists and allow_download
			try:
				if to == 'json':
					out_file = dbapi.io.JSONDropboxFile(path,env.client,download=download)
				else:
					out_file = dbapi.io.WritableDropboxFile(path,env.client,download=download,mode=to)
			except IOError as e:
				raise IOError('Unable to open file for writing ')
				
			#register the open file with the locker,
			#and the necessary cleanup action
			def close_file_cleanup():
				out_file._close(env.locker)
			env.add_cleanup(close_file_cleanup)
			
			env.locker.register_open_file(out_file)
					
		else:
			raise TypeError('Invalid mode for opening file. read, write, or append')
			
		return out_file
		
		
	@env.register(self)
	@env.privileged
	def close(file_handle):
		"""
		Closes the given file handle. This will happen automatically,
		but do this to release resources (it releases the lock too)
		"""
		file_handle._close(env.locker)
		
		
	@env.register(self)
	def write(path,string,timeout=None):
		"""
		Writes the given string to the path given by `path`
		"""
		text_file = open(path,to='write',timeout=timeout,allow_download=False)
		text_file.write(string)
		close(text_file)
		
	@env.register(self)
	def read(path):
		"""
		reads the file given by path and returns a string of its contents
		"""
		return open(path).read()
		
	
	@env.register(self)
	def render(path):
		"""
		Will read and print the file given by path, withthe proper content type
		"""
		file_h = open(path)
		content_type = file_h.metadata['mime_type']
		dbpy.http.set_response_header('Content-Type',content_type)
		sys.stdout.write(file_h.read())
		
	
			
			
	return self
########NEW FILE########
__FILENAME__ = json_dbpy

import json
import sys

name = 'json'


__doc__ = "Functions for working with json files that live on dropbox"

def build(env,path):
	
	
	self = env.get_new_module(path+'.'+name)
	
	file = env.get_module('dbpy.io.file')
	http = env.get_module('dbpy.http')
	
	@env.register(self)
	def open(path,from_data=None,timeout=None,default=dict):
		"""
		opens a json dictionary or list, returning a data-handle. Any changes to that
		dictionary or list will be updated back to dropbox once the file handle is closed.
		It can only be a dictionary or list because primitives are hard to keep a reference to in python,
		a work-around for this would be nice.
		Raises an `IOError` if something goes wrong, or a `ValueError` if the json is bad
		
		Use `from_data` to open up a json file from an existing dictionary or list.
		
		If `path` does not exist, it will be created
		"""
		
		out_json = None	
		try:
			if from_data is None:
				json_file = file.open(path,to='json',timeout=timeout) 
				out_json = json_file.json_object
			else:
				json_file = file.open(path,to='json',timeout=Timeout,allow_download=False)
				json_file.json_object = from_data
				out_json = from_data
			
		except IOError as e:
			raise IOError("Unable to open JSON object backed by writable file:\n%s"%e.message)
		except ValueError as e:
			raise ValueError("Error parsing json file")
			
		if out_json is None:
			out_json = default()
			json_file.json_object = out_json
		
		if not (isinstance(out_json,dict) or isinstance(out_json,list)):
			raise ValueError("You can only open a json that is a dictionary or a list")
			
		return out_json
		
	@env.register(self)
	def open_list(path,from_data=None,timeout=None):
		"""
		Opens a json list. A strange, slightly redundant function. I've disliked it ever since I wrote it,
		but I can't bring myself to delete it for some reason."""
		out =  self.open(path,from_data=from_data,timeout=timeout,default=list)
		if not isinstance(out,list):
			raise ValueError("Object opened by open_list is not a list!")
		return out
	

		
	@env.register(self)
	@env.privileged
	def close(inner_dict):
		"""
		Closes the json file handle. This will happen automatically, but this releases locks and resources
		"""
		#look through all the registered open files (file.open adds to this list)
		#and see if the json dictionary we are dealing  with this matches, (then close it if so)
		for open_file_h in env.locker.open_files:
			if hasattr(open_file_h,'json_object'):
				if open_file_h.json_object is inner_dict:
					open_file_h._close(env.locker)
		
	@env.register(self)
	@env.privileged
	def save(path,json_object,timeout=None):
		"""
		Takes any json object and writes it to the given path
		"""
		json_file = file.open(path,to='json',timeout=timeout,allow_download=False)
		json_file.json_object = json_object
		close(json_object) #because of the way that close ^^ works, we pass the dictionary, not the file handle itself
	
	@env.register(self)
	@env.privileged
	def load(path):
		"""
		loads a json file and returns it
		throws a ValueError if the json file is not valid
		"""
		try:
			return json.load(file.open(path))
		except ValueError:
			raise ValueError('Unable to parse json file')
			
	@env.register(self)
	def render(path):
		"""
		Renders the given json path to stdout
		With the proper Content-Type
		"""
		http.set_response_header('Content-Type','application/json')
		sys.stdout.write(file.read(path))
			
	return self
########NEW FILE########
__FILENAME__ = session


name = 'session'

__doc__ = "A dictionary that represents the session of a user on the site"

class DBPYSession(dict):
	
	def __init__(self,env):
		
		session = env.session
		
		@env.register(self)
		@env.privileged
		def start():
			"""
			Starts the session.
			"""
			session.start()
			self.update(session.inner_dict)
		
		@env.register(self)
		@env.privileged	
		def destroy():
			"""
			Destroys the session
			"""
			session.destroy()
			self.clear()
			

def build(env,path):

	
	self = DBPYSession(env)
	env.add_module(self,path+'.'+name)
	
	#adding a cleanup operation
	def finish_session():
		
		if not env.session.is_destroyed:
			env.session.inner_dict.update(self)	
		
		session_header = env.session.get_header()
		if session_header:
			env.response.set_header(*env.session.get_header())
	
	env.add_cleanup(finish_session)		
	
	return self

########NEW FILE########
__FILENAME__ = templates
#big imports
from drapache import dbapi

import sys

name = 'templates'

__doc__ = "Functions for using jinja templates hosted on dropbox"

def build(env,path):
	
	self = env.get_new_module(path+'.'+name)
	
	#no submodules
	
	@env.privileged
	def _render_template_to_string(path,with_data):
		sys.stderr.write("foobar\n")
		return dbapi.jinja.render_dropbox_template(env.client,path,with_data)
	
	@env.register(self)
	def render(path,with_data=None):
		"""
		Renders the jinja template found in `path`. The parameter `with_data` (None by default)
		specifies a dictionary that will be used to fill in the template.
		"""
		print render_to_string(path,with_data)
		
	@env.register(self)
	def render_to_string(path,with_data=None):
		"""
		Renders the template like render_template, but returns it as a a string instead
		of printing it.
		"""
		
		search_hierarchy = [env.request_folder,env.request_folder+'_templates/','/_templates/']
		
		if path.startswith('/'):
			return _render_template_to_string(path,with_data)
		
		else:
			sys.stderr.write(str(_render_template_to_string)+"\n")
			for prefix in search_hierarchy:
				check_path = prefix + path
				try:
					return _render_template_to_string(check_path,with_data)
				except dbapi.jinja.TemplateNotFound:
					pass
			raise dbapi.jinja.TemplateNotFound()
			
	return self
########NEW FILE########
__FILENAME__ = text
import markdown
import pprint


name = 'text'

__doc__ = "Functions for working with text"

def build(env,path):
	
	
	self = env.get_new_module(path+'.'+name)
	

	@env.register(self)
	@env.privileged
	def markdown_to_html(markdown_string):
		"""
		Converts the given markdown string to html, returning it
		"""
		return markdown.markdown(markdown_string)
		
	@env.register(self)
	@env.privileged
	def pretty_print(thingy):
		"""
		Pretty prints the given `thingy`
		"""
		print "<pre>"
		printer = pprint.PrettyPrinter(indent=4)
		printer.pprint(thingy)
		print "</pre>"
		
	return self
########NEW FILE########
__FILENAME__ = builtins_dep
"""
Here are the functions that will ship with python executable code
"""


import sys
import imp
import os.path
import pprint

import dropbox
import markdown
import json

from drapache import dbapi

class UserDieException(Exception):
	pass



def get_builtins(**kwargs):
	"""
	client is the client
	get_params are the params from the get request
	sandbox is the sandbox in which it runs
	"""
	
	client = kwargs['client']
	locker = kwargs['locker']

	
	request = kwargs['request']
	response = kwargs['response']
	
	get_params = request.get_params or {}
	post_params = request.post_params or {}
	
	request_folder = request.folder
	
	session = kwargs['session']
	
	sandbox = kwargs['sandbox']

	#goo... but i need state that is mutable 
	#by any privileged function... this dict becomes visible to all privileged
	#function. this allows the nesting of privilegeds
	in_sandbox = {'is':True}
	
	
	built_in_hash = {'GETPARAMS':get_params,'POSTPARAMS':post_params,'SESSION':None}
		
	
	def register(function):
		built_in_hash[function.func_name] = function
		return function
		
	def privileged(function):
		"""
		A decorator that replaces the given function with 
		one that first takes the current frame out of the sandbox
		and then executes the function, finally replaces the protections of the sandbox
		
		There are some hacks that cater to the way that pysandbox (which is awesome) was written
		
		And a dictionary was defined (in_sandbox) at the same scope os the function itself... this acts as
		a global flag whether or not sandbox is currently enabled. This allows the nesting of privileged functions
		"""
		def outer_wrapper(*args,**kwargs):
            
			retval = None
			
			unrolled = False
			
			try:
				#before I disable protections and restore privileged builtins,
				#i need to change the frame that I am acting on to the current one
				#instead of whatever frame enable was called in
				#find the builtin protection and set its frame
				if in_sandbox['is']:
					for p in reversed(sandbox.protections):
						if p.__class__.__name__ == 'CleanupBuiltins':
							p.frame = sys._getframe()
						p.disable(sandbox)
					unrolled = True
					in_sandbox['is'] = False
			
				retval = function(*args,**kwargs)
			
			
			finally:
		        #redo the protection
				
				#enable for the builtin protection grabs the frame 2 up from enable
				#i want it to enable the protections in the outer_wrapper frame, which is now privileged
				#this ensures that privileged builtins are restored in the next disable
				#so instead of this acting on the 'privileged' frame, I wrap it in a function
				#to push it one place lower in the stack frame so it acts on outer_wrapper
				if unrolled:
					def enable_protections():
						for p in sandbox.protections:
							p.enable(sandbox)
					enable_protections()
					in_sandbox['is'] = True
				
			return retval
		
		#hack to make privileged functions compatible with register
		outer_wrapper.func_name = function.func_name
		outer_wrapper.__doc__ = function.__doc__
		return outer_wrapper
			
	
	def privileged_with_callback(callback,before=False):
		"""
		A decorator factory that returns a decorator that wraps the function
		by privileging it, and composing it with the unprivileged callback
		
		if before is True (false by default) the callback function will actually get executed *before* the privileged one
		"""
		
		def outer_decorator(function):
			
			function_p = privileged(function)
			
			if before:
				def outer_wrapper(*args,**kwargs):
					return function_p(callback(*args,**kwargs))
			else:
				def outer_wrapper(*args,**kwargs):
					return callback(function_p(*args,**kwargs))

			#hack to make privileged functions compatible with register, and docs
			outer_wrapper.func_name = function.func_name
			outer_wrapper.__doc__ = function.__doc__
			return outer_wrapper
		
		return outer_decorator
			
				
		
	####### Template stuff
	@privileged
	def _render_template_to_string(path,with_data):
		return dbapi.jinja.render_dropbox_template(client,path,with_data)
	
	@register
	def render_template(path,with_data=None):
		"""
		Renders the jinja template found in `path`. The parameter `with_data` (None by default)
		specifies a dictionary that will be used to fill in the template.
		"""
		print render_template_to_string(path,with_data)
		
	@register
	def render_template_to_string(path,with_data=None):
		"""
		Renders the template like render_template, but returns it as a a string instead
		of printing it.
		"""
		
		search_hierarchy = [request_folder,request_folder+'_templates/','/_templates/']
		
		if path.startswith('/'):
			return _render_template_to_string(path,with_data)
		
		else:
			for prefix in search_hierarchy:
				check_path = prefix + path
				try:
					return _render_template_to_string(check_path,with_data)
				except dbapi.jinja.TemplateNotFound:
					pass
			raise dbapi.jinja.TemplateNotFound()
		
	
	################### file io stuff
	@register
	@privileged
	def _get_lock(path,timeout):
		try:
			file_exists = locker.lock(path,timeout)
		except IOError as e:
			#then I wasn't able to lock
			raise IOError("Timeout waiting to open %s for writing or appending'%path")
			
		return file_exists

	@register
	@privileged
	def _release_lock(path):
		
		#throws an IOError if it doesn't work
		locker.release(path)
	
	@register
	@privileged
	def open_file(path,to='read',timeout=None,allow_download=True):
		"""
		loads a file from the users dropbox and returns a string with the contents
		"""
		#if path starts with /, it is absolute.
		#otherwise, it is relative to the request path
		if not path.startswith('/'):
			path = request_folder + path
				
		if to == 'read':
			try:
				out_file = dbapi.io.ReadableDropboxFile(path,client)
			except IOError:
				raise IOError('unable to open file %s for reading'%path)
			
		elif to == 'write' or to == 'append' or to == 'json':
			
			#this throws an IOError if it doesn't work
			file_exists = _get_lock(path,timeout)
			
			#I have the lock at this point
			#only download the file if it exists and allow_download is set to true
			#this allows a forced overwrite by setting allow_download to false
			download = file_exists and allow_download
			try:
				if to == 'json':
					out_file = dbapi.io.JSONDropboxFile(path,client,download=download)
				else:
					out_file = dbapi.io.WritableDropboxFile(path,client,download=download,mode=to)
			except IOError as e:
				raise IOError('Unable to open file for writing ')
				
			#register the open file with the locker
			locker.register_open_file(out_file)
					
		else:
			raise TypeError('Invalid mode for opening file. read, write, or append')
			
		return out_file
		
	@register
	def open_json(path,from_data=None,timeout=None,default=dict):
		#opens up a json file handle of sorts
		#it will be backed by a WritableDropboxFile
		
		out_json = None	
		try:
			if from_data is None:
				json_file = open_file(path,to='json',timeout=timeout) 
				out_json = json_file.json_object
			else:
				json_file = open_file(path,to='json',timeout=Timeout,allow_download=False)
				json_file.json_object = from_data
				out_json = from_data
			
		except IOError as e:
			raise IOError("Unable to open JSON object backed by writable file:\n%s"%e.message)
		except ValueError as e:
			raise ValueError("Error parsing json file")
			
		if out_json is None:
			out_json = default()
			json_file.json_object = out_json
		
		if not (isinstance(out_json,dict) or isinstance(out_json,list)):
			raise ValueError("You can only open a json that is a dictionary or a list")
			
		return out_json
		
	@register
	def open_json_list(path,from_data=None,timeout=None):
		out =  open_json(path,from_data=from_data,timeout=timeout,default=list)
		if not isinstance(out,list):
			raise ValueError("Object opened by open_json_list is not a list!")
	
	@register
	@privileged
	def close_file(file_handle):
		file_handle._close(locker)
		
	@register
	@privileged
	def close_json(inner_dict):
		for open_file_h in locker.open_files:
			if hasattr(open_file_h,'json_object'):
				if open_file_h.json_object is inner_dict:
					open_file_h._close(locker)
		
	@register
	@privileged
	def save_json(path,json_object,timeout=None):
		json_file = open_file(path,to='json',timeout=timeout,allow_download=False)
		json_file.json_object = json_object
		close_file(json_file)
		
	@register
	def write_file(path,string,timeout=None):
		text_file = open_file(path,to='write',timeout=timeout,allow_download=False)
		text_file.write(string)
		close_file(text_file)
	
	@register
	def read_file(path):
		return open_file(path).read()
		
	@register
	@privileged
	def load_json(path):
		"""
		loads a json file and returns it
		throws a ValueError if the json file fucks up
		"""
		try:
			return json.load(open_file(path))
		except ValueError:
			raise ValueError('Unable to parse json file')		
	
	@register
	@privileged
	def delete_file(path):
		
		if not path.startswith('/'):
			path = request_folder + path
			
		try:
			client.file_delete(path)
		except dropbox.rest.ErrorResponse:
			raise IOError("Unable to delete file %s"%path)
		
	
	############ session stuff
	@register
	@privileged
	def start_session():
		session.start()
		built_in_hash['SESSION'] = session.inner_dict
		
	@register
	@privileged
	def destroy_session():
		session.destroy()
		
		
	########## http stuff
	@register
	def set_response_header(key,value):
		response.set_header(key,value)
		
	@register
	def get_request_header(key):
		return request.headers.get(key)
	
	@register
	def set_response_status(status):
		response.status = status
		
	@register
	def redirect(where,immediately=True):
		set_response_status(302)
		set_response_header('Location',where)
		
		if immediately:
			die("redirecting")
			
	
	############ text stuff	
	@register
	@privileged
	def markdown_to_html(markdown_string):
		return markdown.markdown(markdown_string)
		
	@register
	@privileged
	def pretty_print(thingy,pre=True):
		"""
		Pretty prints the given thingy
		"""
		print "<pre>"
		printer = pprint.PrettyPrinter(indent=4)
		printer.pprint(thingy)
		print "</pre>"
		
	
	############ import stuff
	
	def dropbox_import_callback(imports):
		#hm... unfortunately, if any of the imports mutate the built_in_hash, they can
		#affect everyones builtins
		#so should I recursively create a new one for each for each?
		#thats the reasoning behind it. I'd love if I didn't have to
		for module_string,module in imports:
			builtins = get_builtins(**kwargs)
			exec module_string in builtins,module.__dict__
	
	@register
	@privileged_with_callback(dropbox_import_callback)
	def dropbox_import(*module_paths):
		#look first in the path given by folder search
		#then look in a '/_scripts' folder? or similarly named?
		#not right now
		
		#NO PACKAGE SUPPORT... SIMPLE FILES ONLY FOR NOW
		imports = []
		for module_path in module_paths:
			filestring = read_file(module_path)
			module_name = os.path.basename(module_path).split('.',1)[0]
			out_module = imp.new_module(module_name)
			built_in_hash[module_name] = out_module
			imports.append( (filestring,out_module) )
		
		return imports
		
	    
	##### other stuff
	@register
	def die(message="",report=True):
		"""
		Raises an Exception
		"""
		if report:
			print message
		raise UserDieException(message)
		
	
	
	return built_in_hash


	



		
		
		
		
		
		
	
########NEW FILE########
__FILENAME__ = environment
import builtins.dbpy
import sys

class DBPYModule:
	
	pass


class DBPYEnvironment:
	
	DBPY_TIMEOUT = 25
	BACKGROUND_THREAD_LIMIT = 10
	
	
	def __init__(self,**kwargs):
		
		for k,v in kwargs.items():
			setattr(self,k,v)
		
		self.request_folder = self.request.folder
		self.get_params = self.request.get_params or {}
		self.post_params = self.request.post_params or {}
		
		
		#things that will be global to the builtins
		self.globals = {}
		
		#environment state stuff
		self.modules = {}
		self.cleanups = []
		
		self.background_thread_count = 0
		
		self.in_sandbox = True
		
		
		def register(target):
						
			def decorator(function):
				setattr(target,function.func_name,function)
				return function
			return decorator
		register(self)(register)
		
		@register(self)	
		def privileged(function):
				"""
				A decorator that replaces the given function with 
				one that first takes the current frame out of the sandbox
				and then executes the function, finally replaces the protections of the sandbox

				There are some hacks that cater to the way that pysandbox (which is awesome) was written

				And a dictionary was defined (in_sandbox) at the same scope os the function itself... this acts as
				a global flag whether or not sandbox is currently enabled. This allows the nesting of privileged functions
				"""
				def outer_wrapper(*args,**kwargs):

					retval = None

					unrolled = False

					try:
						#before I disable protections and restore privileged builtins,
						#i need to change the frame that I am acting on to the current one
						#instead of whatever frame enable was called in
						#find the builtin protection and set its frame
						if self.in_sandbox:
							for p in reversed(self.sandbox.protections):
								if p.__class__.__name__ == 'CleanupBuiltins':
									p.frame = sys._getframe()
								p.disable(self.sandbox)
							unrolled = True
							self.in_sandbox = False

						retval = function(*args,**kwargs)


					finally:
				        #redo the protection

						#enable for the builtin protection grabs the frame 2 up from enable
						#i want it to enable the protections in the outer_wrapper frame, which is now privileged
						#this ensures that privileged builtins are restored in the next disable
						#so instead of this acting on the 'privileged' frame, I wrap it in a function
						#to push it one place lower in the stack frame so it acts on outer_wrapper
						if unrolled:
							def enable_protections():
								for p in self.sandbox.protections:
									p.enable(self.sandbox)
							enable_protections()
							self.in_sandbox = True

					return retval

				#hack to make privileged functions compatible with register
				outer_wrapper.func_name = function.func_name
				outer_wrapper.__doc__ = function.__doc__
				
				return outer_wrapper

		@register(self)
		def privileged_with_callback(callback,before=False):
			"""
			A decorator factory that returns a decorator that wraps the function
			by privileging it, and composing it with the unprivileged callback

			if before is True (false by default) the callback function will actually get executed *before* the privileged one
			"""

			def outer_decorator(function):

				function_p = privileged(function)

				if before:
					def outer_wrapper(*args,**kwargs):
						return function_p(callback(*args,**kwargs))
				else:
					def outer_wrapper(*args,**kwargs):
						return callback(function_p(*args,**kwargs))

				#hack to make privileged functions compatible with register, and docs
				outer_wrapper.func_name = function.func_name
				outer_wrapper.__doc__ = function.__doc__
				return outer_wrapper

			return outer_decorator
			
		#filling builtins with self
		self.globals['dbpy'] = builtins.dbpy.build(self,None)
	
	def add_module(self,mod,name):
		self.modules[name] = mod
		
	def get_module(self,name):
		return self.modules[name]
	
	def get_new_module(self,path):
		new_module = DBPYModule()
		self.add_module(new_module,path)
		return new_module
		
	def add_cleanup(self,function):
		self.cleanups.append(function)

########NEW FILE########
__FILENAME__ = execute
"""
responsible for executing downloaded code
"""

import StringIO
import sys
import traceback
import threading
import trace

import sandbox as pysandbox

from drapache.util.http import Response
from drapache import dbapi
from drapache import util

import builtins
import environment

class Timeout(Exception):
	pass


class KThread(threading.Thread):
	"""
	A subclass of threading.Thread, with a kill()
	method.
	found this @ http://www.velocityreviews.com/forums/t330554-kill-a-thread-in-python.html
	"""
	def __init__(self, *args, **keywords):
			threading.Thread.__init__(self, *args, **keywords)
			self.killed = False
			self.timeout = None

	def start(self):
		"""Start the thread."""
		self.__run_backup = self.run
		self.run = self.__run # Force the Thread to install our trace.
		threading.Thread.start(self)

	def __run(self):
		"""Hacked run function, which installs the
		trace."""
		sys.settrace(self.globaltrace)
		self.__run_backup()
		self.run = self.__run_backup

	def globaltrace(self, frame, why, arg):
		if why == 'call':
			return self.localtrace
		else:
			return None

	def localtrace(self, frame, why, arg):
			if self.killed:
				if why == 'line':
					raise Timeout("DBPY code timed out after %s seconds"%self.timeout)
			return self.localtrace

	def kill(self):
		self.killed = True



class DBPYExecThread(KThread):
	
	def __init__(self,env,code):
		KThread.__init__(self)
		self.env = env
		self.code = code
		
		self.timeout = env.DBPY_TIMEOUT
		
		self.error = None
		self.error_traceback = ""
		
	def run(self):
		
		try:
			
			#enable for the builtin protection grabs the frame 2 up from enable
			#i want it to enable the protections with outer_wrapper, which is now privileged
			#this ensures that privileged builtins are restored in the next disable
			#so instead of this acting the register frame, I wrap it in a function
			#so it acts on outer_wrapper
			def enable_protections():
				for protection in self.env.sandbox.protections:
					protection.enable(self.env.sandbox)
			enable_protections()


			exec self.code in self.env.globals
			
		
		except builtins.UserDieException:
			# this doesn't count as an Exception
			pass
		
		except Exception as e:			
			self.error = e
			
		finally:
			
			#before I disable protections and restore privileged builtins,
			#i need to change the frame that I am acting on to the current one
			#instead of whatever frame enable was called in
			#find the builrin protection and set its frame
			for protection in reversed(self.env.sandbox.protections):
				if protection.__class__.__name__ == 'CleanupBuiltins':
					protection.frame = sys._getframe()
				protection.disable(self.env.sandbox)

			
			#finishing up
			#resource releasing (post-execution actions)
			#are registered here
			try:
				for op in self.env.cleanups:
					op()

			except Exception as e:
				#an issue releasing resources
				#if there is already an error, we do not report it?
				#maybe errors releasing resources should have higher precedence..
				if not self.error:
					self.error = e
				
			if self.error:
				self.error_traceback = traceback.format_exc()


def get_sandbox():
	sandbox_config = pysandbox.SandboxConfig()
	sandbox_config.enable("stdout")
	sandbox_config.enable("time")
	sandbox_config.enable("math")
	sandbox_config.enable("exit")
	sandbox_config.enable("stderr")
	
	sandbox_config.timeout = None
	
	sandbox = pysandbox.Sandbox(sandbox_config)
	return sandbox		
		

def execute(filestring,**kwargs):
	
	
	PRINT_EXCEPTIONS = True

	DEBUG = True
	
	response = Response(None,"")
	
	sandbox = get_sandbox()
	
	#setting up the parameters for the builtin construction
	locker = dbapi.io.DropboxFileLocker(kwargs['client'])
	request = kwargs['request']
	
	cookie = request.headers.get('Cookie',None)
	session = util.sessions.DrapacheSession(cookie)
	
	builtin_params = dict(
							response=response,
							locker=locker,
							sandbox=sandbox,
							session=session,
							**kwargs
							)
							
	env = environment.DBPYEnvironment(**builtin_params)
	
	#replaceing stdout
	old_stdout = sys.stdout
	new_stdout = StringIO.StringIO()
	sys.stdout = new_stdout
	
	try:

		sandbox_thread = DBPYExecThread(env,filestring)
		sandbox_thread.start()
	
		sandbox_thread.join(env.DBPY_TIMEOUT)
	
		if sandbox_thread.isAlive():
			#time to kill it
		
			sandbox_thread.kill()
			sandbox_thread.join()
		
		if sandbox_thread.error is not None:
			

			
			#this is where processing of the traceback should take place
			#so that we can show a meaningful error message
			if DEBUG:
				print "<h1>Debug Traceback</h1>"
				print "<pre>"
				sys.stdout.write(sandbox_thread.error_traceback)
				print "</pre>"

			raise sandbox_thread.error

	except:
		if PRINT_EXCEPTIONS:
			print "<pre>"
			traceback.print_exc(file=new_stdout)
			print "</pre>"
	

	sys.stdout = old_stdout
	response.body = new_stdout.getvalue()

	if response.status is None:
		response.status = 200
	
	if not 'Content-Type' in response.headers:
		response.set_header('Content-Type','text/html')
	
	return response
########NEW FILE########
__FILENAME__ = dbserver
"""
Implements the interaction with the dropbox api
"""

import os.path
import re

import dropbox

from drapache import dbpy
from drapache import util
from drapache.util.http import Response

import dbfilehandlers


class DropboxServer:
	"""
	The class responsable for hitting the dropbox and processing the results
	
	most of the power of the service will come from here
	"""
	
	
	def __init__(self,client,request):
		self.client = client
		self.request = request
		self.handlers = dbfilehandlers.get_handlers()
		
	def serve(self):
		"""
		serves the given path, returning a Response Object
		
		some special rules
		- if it is a directory,
			returns an indexed list of the files
		- if it is a directory without a trailing slash,
			returns a redirect request (these will also be able to come fro)
		"""
		
		request = self.request
		client = self.client
		path = request.path
		
		#anything prefixed with '_' is not accessable
		path_components = path.split('/')
		for component in path_components:
			if component.startswith('_'):
				return Response(403,'Forbidden',error=True)
		
		
		try:
			#fuck this extra request... is there a way to avoid it? probably
			meta_info = self.client.metadata(path)
			
			#### checking for the is_Deleted flag
			try:
				if meta_info['is_deleted']:
					return Response(410,"File is deleted",error=True)
			except KeyError:
				pass #its not deleted
				
			#ok. here is were i need to call the file thing
			return self._serve_file(meta_info,path)

				
		except dropbox.rest.ErrorResponse as e:
			return Response(e.status,e.reason,headers=e.headers,error=True)
			
			
	def _serve_file(self,meta_info,path):
		for handler in self.handlers:
			checkfunc = handler['check']
			if checkfunc(meta_info):
				return handler['handler'](meta_info,path,self)
		#if we get to here we have to return an error
		#415 is unsupported media type, by the way
		return Response(415,'No Handler installed for given path',error=True)
		
		

		
		
	def _get_content_type(self,file_meta):
		given = file_meta['mime_type']
		if given.startswith('text/x-'):
			return 'text/plain'
		else:
			return given
		
		


########NEW FILE########
__FILENAME__ = httpserver
"""
The http server implementation
"""

import BaseHTTPServer
import SocketServer
import socket #for socket.error
import re
import os
import sys
import urlparse
import traceback
import threading

import drapache
from drapache import util



class DropboxHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	"""
	This class is responsible for sub-routing and headers,
	getting/processing content gets farmed out (this will help when i thread?)
	also, pulling out parameters
	"""
	
	
	
	
	#def setup(self):
	#	BaseHTTPServer.BaseHTTPRequestHandler.setup(self)
		#print self.request.settimeout(5)
	
	def do_GET(self):
		return self.serve(method='get')
		
	def do_POST(self):
		return self.serve(method='post')
	
	def serve(self,method=None):
			
		try:
			
			#create an empty request object
			request = util.http.Request()

			#pulling out the host
			host_string = self.headers.get("Host")
			host_rest = host_string.split(".",1) #at most one split
			if len(host_rest) == 1:
				subdomain = None
			else:
				subdomain = host_rest[0]
			
			#setting some request variables
			request.host = host_string
			request.subdomain = subdomain
			request.headers = self.headers
		
			#pulling out the request path and query from the url
			path,query_string = self.parse_raw_path(self.path)
		
			#parsing the query
			if query_string is not None:
				get_params = urlparse.parse_qs(query_string)
			else:
				get_params = None
		
			#setting more request variables IMPORTANT. fragile though. sorry
			request.path = path
			request.folder = path.rsplit('/',1)[0] + '/'
			request.get_params = get_params
			request.query_string = query_string
		
			#there must be a subdomain
			if subdomain is None:
				self.send_error(400,"Dropache requires a username as the route")
				return None
			
			
			#getting a subdomain_manager instance
			#the factory function is an attribute of the server
			#to keep it configurable
			subdomain_manager = self.server.get_subdomain_manager()
		
			#looking up the oauth for the given subdomain
			try:
				subdomain_token = subdomain_manager.get_token(subdomain)
				if subdomain_token is None:
					self.send_error(404,"Subdomain %s does not exist"%subdomain)
					return None
			except util.subdomain_managers.SubdomainException as e:
				self.send_error(503,"Error in subdomain lookup:\n"+e.message)
				return None
			
			#getting a dropbox_client
			#the factory function is an attribute of the server
			#to keep it configurable
			subdomain_client = self.server.get_dropbox_client(subdomain_token)
		
		
			#parsing post parameters if it is a post request
			if method == 'post':
				request_length = int(self.headers.get('Content-length',0))
				foo = self.rfile.read(request_length)
				post_params = urlparse.parse_qs(foo)
				request.post_params = post_params
			else:
				request.post_params = None
		
			#getting the response from dropbox
			response = drapache.dbserver.DropboxServer(subdomain_client,request).serve()
			
			if response.error:
				self.send_error(response.status,response.body)
				return None
		
			else:
				self.send_response(response.status)
				for h,v in response.headers.items():
					self.send_header(h,v)
				self.end_headers()
				self.wfile.write(response.body)
				return None
				
		##### Catchall errors
		except socket.error as e:
			#check if it was a broken pipe
			#... assume it was a broken pipe
			#if it was a broken pipe, the client went away. which is fine. and i don't need a traceback for that.
			#nor should i try to send a 500 message, because there is no way it will get through
			pass
			
		
		except Exception as e:
			### Caught an error, now attempting to send a 500 server error response
			traceback.print_exc()
			self.send_error(500,str(e))
		
		
	def parse_raw_path(self,path):
		"""
		pulls out the user, the path, and the query if any

		"""
		
		#*.drapache:port/<the rest of the path>
		po = urlparse.urlparse(path)
		sub_path = po.path
		query = po.query
		if sub_path == '':
			sub_path = '/'
		if query == '':
			query = None
		
		return sub_path,query
		

class ThreadJoiningForkingMixIn:

	"""
	Mix-in class to handle each request in a new process.
	COPIED FROM STANDARD LIBRARY
	EXCEPT THAT IT WAITS ON ALL BACKGROUND THREADS TO FINISH BEFORE os._exit-ing
	"""

	timeout = 300
	active_children = None
	max_children = 40

	def collect_children(self):
		"""Internal routine to wait for children that have exited."""
		if self.active_children is None: return
		while len(self.active_children) >= self.max_children:
			# XXX: This will wait for any child process, not just ones
			# spawned by this library. This could confuse other
			# libraries that expect to be able to wait for their own
			# children.
			try:
				pid, status = os.waitpid(0, 0)
			except os.error:
				pid = None
			if pid not in self.active_children: continue
			self.active_children.remove(pid)

		# XXX: This loop runs more system calls than it ought
		# to. There should be a way to put the active_children into a
		# process group and then use os.waitpid(-pgid) to wait for any
		# of that set, but I couldn't find a way to allocate pgids
		# that couldn't collide.
		for child in self.active_children:
			try:
				pid, status = os.waitpid(child, os.WNOHANG)
			except os.error:
				pid = None
			if not pid: continue
			try:
				self.active_children.remove(pid)
			except ValueError, e:
				raise ValueError('%s. x=%d and list=%r' % (e.message, pid,
														   self.active_children))

	def handle_timeout(self):
		"""Wait for zombies after self.timeout seconds of inactivity.

		May be extended, do not override.
		"""
		self.collect_children()

	def process_request(self, request, client_address):
		"""Fork a new subprocess to process the request."""
		self.collect_children()
		pid = os.fork()
		if pid:
			# Parent process
			if self.active_children is None:
				self.active_children = []
			self.active_children.append(pid)
			self.close_request(request) #close handle in parent process
			return
		else:
			# Child process.
			# This must never return, hence os._exit()!
			try:
				self.finish_request(request, client_address)
				self.shutdown_request(request)
				
				JOINTHREADS_TIMEOUT = 10 #we will try for ten seconds to wait for background threads to finish
				JOINTHREADS_INCREMENT = .1 #how long we try to join each thread
				
				been_waiting = 0
				while threading.active_count() > 1 and been_waiting < JOINTHREADS_TIMEOUT: #while there are more threads than this one
					for thread in threading.enumerate():
						if not thread is threading.current_thread():
							thread.join(JOINTHREADS_INCREMENT)
							been_waiting += JOINTHREADS_INCREMENT				
				
				#at this point, either all background threads have finished or we've been waiting damn long enough
				os._exit(0)
			except:
				try:
					self.handle_error(request, client_address)
					self.shutdown_request(request)
				finally:
					os._exit(1)
		
class DropboxForkingHTTPServer(ThreadJoiningForkingMixIn,BaseHTTPServer.HTTPServer):
	
	def set_config(self,subdomain_manager_factory,dropbox_client_factory):
		self.get_subdomain_manager = subdomain_manager_factory
		self.get_dropbox_client = dropbox_client_factory
		
	
	#catchall errors
	def finish_request(self,*args,**kwargs):
		try:
			BaseHTTPServer.HTTPServer.finish_request(self,*args,**kwargs)
		except socket.error as e:
			sys.stderr.write("[error] %s\n"%"Client went away")
		except Exception as e:
			traceback.print_exc()
			sys.stderr.write("[error] Uncought response exception: %s\n"%str(e))
			
			
class HttpDrapache:


	def __init__(self):
		self.port = None
		self.subdomain_manager_factory = None
		self.dropbox_client_factory = None

	def start(self):

		assert self.port
		assert self.subdomain_manager_factory
		assert self.dropbox_client_factory


		server_address = ('0.0.0.0',self.port)
		self.httpd = DropboxForkingHTTPServer(server_address,DropboxHTTPRequestHandler)
		self.httpd.set_config(self.subdomain_manager_factory,self.dropbox_client_factory)
		self.httpd.serve_forever()

	

	
########NEW FILE########
__FILENAME__ = twistd_resource
"""
The http server implementation
"""

import BaseHTTPServer
import SocketServer
import re
import os
import sys
import urlparse
import urllib

import subdomain_managers

import threading

from drapache import server as dropbox_server

from twisted.web import server, resource
from twisted.internet import threads, reactor, defer

ErrorPage = resource.ErrorPage

class DrapacheTwistdResource(resource.Resource):

	isLeaf = True
	
	def __init__(self,subdomain_manager_factory,dropbox_client_factory):
		self.get_subdomain_manager = subdomain_manager_factory
		self.get_dropbox_client = dropbox_client_factory
		
	def render_GET(self,request):
		
		try:
			host_string = request.getHeader("Host")
			host_rest = host_string.split(".",1) #at most one split
			if len(host_rest) == 1:
				subdomain = None
			else:
				subdomain = host_rest[0]
				
			path = request.path
			query_dict = request.args
			query_string = urllib.urlencode(request.args)
		
			if subdomain is None:
				return ErrorPage(400,"Dropache requires a username as the route",None).render(request)
			
			
			subdomain_manager = self.get_subdomain_manager()
		
			try:
				subdomain_exists = subdomain_manager.check_subdomain(subdomain)
			except subdomain_managers.SubdomainException as e:
				return ErrorPage(503,"Error in subdomain lookup:\n"+e.message,None).render(request)
		
		
			if not subdomain_exists:
				return ErrorPage(404,"Subdomain %s does not exist"%subdomain,None).render(request)
				return None
			
			
			try:
				subdomain_token = subdomain_manager.get_token(subdomain)
			except subdomain_managers.SubdomainException as e:
				return ErrorPage(503,"Error in subdomain lookup:\n"+e.message,None).render(request)
			
			subdomain_client = self.get_dropbox_client(subdomain_token)
		
			file_server = dbapiserver.FileServer(subdomain_client,query_dict,query_string)
			
			
			#i think i have to overload this beause of threads?
			#deferred = threads.deferToThread(file_server.serve,path)
			deferred = defer.Deferred()
			def on_finish(success,result):
				sys.stderr.write("at leat the thread finished\n")
				if success:
					sys.stderr.write("success\n")
					reactor.wakeUp()
					
					reactor.callFromThread(deferred.callback,result)
				else:
					sys.stderr.write("fail\n")
					reactor.callFromThread(deferred.errback,result)
					
			reactor.getThreadPool().callInThreadWithCallback(on_finish,file_server.serve,path)
			
			
			
			def response_failed(err,deferr):
				sys.stderr.write('foo')
				deferr.cancel()
					
			def response_errback(err):
				sys.stderr.write('here;!!!\n')
			
			def response_callback(response):
				sys.stderr.write('hmm\n')
				if response.error:
					#ErrorPage(response.status,response.body,None).render(request)
					request.write("fuck")
					request.finish()
		
				else:
					request.setResponseCode(response.status)
					for h,v in response.headers.items():
						request.setHeader(h,v)
					request.write(str(response.body))
					request.finish()
					
			request.notifyFinish().addErrback(response_failed,deferred)
			deferred.addErrback(response_errback)
			deferred.addCallback(response_callback)
			
			return server.NOT_DONE_YET

		
		except Exception as e:
			sys.stderr.write('hmmm!!!ahaha\n')
			return ErrorPage(500,str(e),None).render(request)

	


########NEW FILE########
__FILENAME__ = http
"""
HTTP utility classes
Containers for request and response data
"""

class Response:
	
	def __init__(self,status,body,headers=None,error=False):
		self.status = status
		self.body = body
		self.error = error
		if headers is None:
			self.headers = {}
		else:
			self.headers = headers
			
	def set_header(self,key,value):
		self.headers[key] = value
		
class Request:
	pass
########NEW FILE########
__FILENAME__ = index_generator
"""
The index auto generator
"""
import os
import jinja2
from jinja2 import Environment,PackageLoader

from drapache import dbapi



def get_index_file(file_list,folder_path,client):
	
	
	"""
	The index auto generator
	"""

	DEFAULT_INDEX = """
	<html>

		<head>
		<title>Index - {{path}}</title>
		</head>


		<body>

			<h1> Index for {{path}} </h1>

			{% for file in files %}
				<a href="{{file}}">{{file}}</a><br>
			{% endfor %}

		</body>

	</html>
	"""

	files = []
	for filemeta in file_list:
		file_name = os.path.basename(filemeta['path'])
		if filemeta['is_dir']:
			file_name = file_name + '/'
		files.append(file_name)

	dropbox_env = Environment(loader=dbapi.jinja.DropboxLoader(client,'/_templates'))

	try:
		custom_index_template = dropbox_env.get_template('index.html')
		return custom_index_template.render(files=files,path=folder_path)

	except jinja2.TemplateNotFound:
		index_template = jinja2.Template(DEFAULT_INDEX)
		return index_template.render(files=files,path=folder_path)

########NEW FILE########
__FILENAME__ = mysql_connect
"""
Low level API for finding our mysql database, and returning a connection to it
I am not trying to wrap MySQLdb here, just the guts of getting a connection object
well i ended up wrapping it a little.
enjoy.

"""


import MySQLdb
from MySQLdb.cursors import Cursor,DictCursor



class MysqlError(Exception):
	
	def __init__(self,message,errcode=0):
		Exception.__init__(self,message)
		self.errcode = errcode
	
class DBConnection:
	"""
	An object oriented wrapper around a mysql connection
	create it, and the connection is automatically established
	to access the raw API, just use the .db attribute (it is the raw connection)
	"""
	
	def __init__(self,mysql_dict=None):
		self.db = get_db_connection(mysql_dict)
		
	def execute_query(self,query_string,params=None,result_type='DICT'):
		"""
		Executes the given query, and returns a generator containing the rows
		row type can be either DICT, returning a dictionary per row
			or 'LIST' which will return a list per row
		"""
		
		if result_type == 'DICT':
			cursor = self.db.cursor(DictCursor)
		elif result_type == 'LIST':
			cursor = self.db.cursor(Cursor)
		else:
			raise ValueError("result_type must be DICT or LIST")
		
		try:
			if params is None:
				cursor.execute(query_string)
			else:
				cursor.execute(query_string,params)
		except MySQLdb.Error as e:
			#args is a tuple of (errcode,message)
			raise MysqlError(e.args[1],e.args[0])
			
		
		return query_result_set(cursor)
		
	def execute_many(self,query_string,params,result_type='DICT'):
		
		if result_type == 'DICT':
			cursor = self.db.cursor(DictCursor)
		elif result_type == 'LIST':
			cursor = self.db.cursor(Cursor)
		else:
			raise ValueError("Only options for result type is 'DICT' or 'LIST'")
		
		try:
			cursor.executemany(query_string,params)
		except MySQLdb.Error as e:
			raise MysqlError(e.args[1],e.args[0])
		
		return query_result_set(cursor)
		
	def close(self):
		self.db.close()
		
	def escape_string(self,in_string):
		return self.db.escape_string(in_string)
		
	def get_mysql_list(self,input_sequence):
		return "("+','.join(str(s) for s in input_sequence)+")"


def _get_db_params(param_dict):
	"""
	gets the database connection information
	returns it as a dict
	"""
	if param_dict is None:
		import dropache_dbconfig as config
		
		param_dict = {}
		param_dict['user'] = config.USER
		param_dict['passwd'] = config.PASS
		param_dict['host'] = config.HOST
		param_dict['db'] = config.DB
	
	param_dict['use_unicode'] = True
	
	return param_dict
	
def get_db_connection(param_dict):
	param_dict = _get_db_params(param_dict)
	try:
		return MySQLdb.connect(**param_dict)
	except MySQLdb.MySQLError:
		raise MysqlError("Unable to connect to mysql database")
		
		
def query_result_set(cursor):
	
	#for row in cursor.fetchall():
	#	yield row
	#cursor.close()
	#raise StopIteration
	while True:
		row = cursor.fetchone()
		if row is None:
			cursor.close()
			raise StopIteration
		else:
			yield row
########NEW FILE########
__FILENAME__ = sessions
import beaker.session

import uuid
import sys



class DrapacheSession:
	#wraps the beaker session
	#adds
	
	validate_key = str(uuid.uuid4())
	encrypt_key = str(uuid.uuid4())
	
	def __init__(self,cookie=None):
		self.session_started = False
		self.beaker_session = None
		self.beaker_dict = {}
		
		self.inner_dict = {}
		
		self.is_destroyed = False
		
		self.cookie = cookie
	
		
		
	def start(self):
		if not self.session_started:
			self.session_started = True
		
			if self.cookie is not None:
				self.beaker_dict['cookie'] = self.cookie
			
			self.beaker_session = beaker.session.CookieSession(self.beaker_dict,validate_key=self.validate_key,encrypt_key=self.encrypt_key)
						
			self.update_dict()
		
	def destroy(self):
		self.is_destroyed = True
		self.beaker_session.delete()
		self.inner_dict.clear()
		
	def get_header(self):
		#if set cookie is false, return false,
		#else return a Set-Cookie: header, with the cookie as the value
		
		if self.beaker_session is None:
			return False
		
		self.set_dict()
		
		self.beaker_session.save()
		if self.beaker_dict.get('set_cookie',False):
			return ('Set-Cookie',self.beaker_dict['cookie_out'])
		else:
			return False
			
	
	def update_dict(self):
		self.inner_dict.clear()
		self.inner_dict.update(dict((k,v) for k,v in self.beaker_session.items() if not k.startswith('_')))
		
	def set_dict(self):
		
		for k,v in self.beaker_session.items():
			if not k.startswith('_'):
				del self.beaker_session[k]
				
		for k,v in self.inner_dict.items():
			if not k in self.beaker_session:
				self.beaker_session[k] = v
		
		
	
########NEW FILE########
__FILENAME__ = subdomain_managers
"""
Module for handling users, the oauth tokens

THIS COULD AND SHOULD BE OPTIMIZE WITH CACHEING!!!!
"""
import mysql_connect

class SubdomainException(Exception):
	pass


class SubdomainManager:
	"""
	Base class for subdomain manager
	really an interface
	"""
		
	def get_token(self,subdomain):
		"""
		Returns a tuple of (oauth_token,oauth_token_secret)
		If it exists, or None if it does not
		Raises a SubdomainException if there is a problem looking up the subdomain
		"""
		raise SubdomainException("get token not implemented")
		
class MysqlSubdomainManager(SubdomainManager):
	
	def __init__(self,mysql_dict):
		self.db_connection = mysql_connect.DBConnection(mysql_dict)	
	
	def get_token(self,subdomain):
		"""
		returns a (oauth_token,oauth_token_secret) tuple for the given user, or None
		"""
		try:
			SUBDOMAIN_QUERY = "SELECT oauth_token,oauth_token_secret FROM subdomains WHERE subdomain=%s"
			result = self.db_connection.execute_query(SUBDOMAIN_QUERY,subdomain)
			result_list = list(result)
			if result_list:
				row = result_list[0]
				return (row['oauth_token'],row['oauth_token_secret'])
			else:
				return None
		except Exception as e:
			raise SubdomainException(e.message)
			
class FlatFileSubdomainManager(SubdomainManager):
	
	def __init__(self,filename):
		"""
		reads the file into memory
		subdomain|oauth_token|oauth_token_secret
		"""	
		self.subdomains_oauth_map = {}
		f = open(filename)
		for line in f:
			line = line.strip()
			subdomain,oauth_token,oauth_token_secret = line.split('|')
			self.subdomains_oauth_map[subdomain] = (oauth_token,oauth_token_secret)
		f.close()
	
	def get_token(self,subdomain):
		return self.subdomains_oauth_map.get(subdomain)

########NEW FILE########
__FILENAME__ = generate_subdomain_line
import sys

import config
import dropbox

APP_KEY = config.APP_KEY
APP_SECRET = config.APP_SECRET


def get_oauth_credentials():
	sess = dropbox.session.DropboxSession(APP_KEY,APP_SECRET,'app_folder')
	rt = sess.obtain_request_token()
	url = sess.build_authorize_url(rt)
	sys.stderr.write("Go to the following url, then press enter when you have authorized your app:\n%s\n"%url)
	raw_input()
	at = sess.obtain_access_token(rt)
	return at
	
def generate_flat_file_line(subdomain):
	oauth_token = get_oauth_credentials()
	return "%s|%s|%s" % (subdomain,oauth_token.key,oauth_token.secret)
	
if __name__ == "__main__":
	
	try:
		subdomain = sys.argv[1]
	except IndexError:
		sys.stderr.write("You must specify a subdomain that you are registering\n")
		sys.exit(1)
	
	print generate_flat_file_line(subdomain)
	
	
	
########NEW FILE########
__FILENAME__ = server
import drapache
import os
import sys
import config
		
def run():

		
	#to use a flat file
	#where lines are in the format
	#SUBDOMAIN|OAUTH_TOKEN|OAUTH_TOKENSECRET
	def subdomain_manager_factory():
		return drapache.util.subdomain_managers.FlatFileSubdomainManager(config.SUBDOMAIN_FILE)
		
	dropbox_client_generator = drapache.dbapi.access.DropboxClientCreator(config.APP_KEY,config.APP_SECRET)
	def dropbox_client_factory(token_tuple):
		return dropbox_client_generator.get_client(*token_tuple)
	
	instance = drapache.Drapache()
	instance.port = int(os.environ.get('PORT',config.DEFAULT_PORT))
	instance.subdomain_manager_factory = subdomain_manager_factory
	instance.dropbox_client_factory = dropbox_client_factory
	
	sys.stderr.write("Starting drapache instance on port %d\n"%instance.port)
	instance.start()

if __name__=="__main__":
	
	run()
########NEW FILE########
